using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Globalization;
using System.IO;
using System.Security.Cryptography;
using System.Text;
using System.Threading.Tasks;
using System.Web.Script.Serialization;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Threading;

namespace Cypher.CorePreview
{
    internal sealed partial class CypherHost
    {
        private const string WakeWorkerSha256 = "8770df8fffa9998e80e84c418b9daf8bf0889a2b0bb2fe6e95f2ebe17d0ecf61";
        private Process wakeProcess;
        private DispatcherTimer wakeTimer;
        private bool wakeEnabled;
        private bool wakeReady;
        private bool wakeActivated;
        private DateTime wakeStartedUtc;
        private int wakeFailures;
        private DateTime wakeRetryAfterUtc;
        private int wakeDeviceIndex = -1;
        private int wakeDeviceRate;

        private sealed class WakeMicChoice
        {
            internal string Name, Api;
            internal int Index, Rate;
        }

        private void InitializeWakeWord()
        {
            wakeEnabled = string.Equals(GetSetting(ReadSettings(), "wake_word_enabled", "false"), "true", StringComparison.OrdinalIgnoreCase);
            if (!wakeEnabled) return;
            wakeTimer = new DispatcherTimer { Interval = TimeSpan.FromSeconds(3) };
            wakeTimer.Tick += delegate
            {
                if (wakeProcess != null && !wakeReady && DateTime.UtcNow - wakeStartedUtc > TimeSpan.FromSeconds(15))
                    CompleteWakeWorker(wakeProcess, "STARTUP_TIMEOUT", null, 0);
                TryStartWakeListening();
            };
            wakeTimer.Start();
            TryStartWakeListening();
        }

        private void TryStartWakeListening()
        {
            if (!wakeEnabled || closing || paused || voiceListening || voiceStopping || voiceSpeaking || cloudAnswerActive ||
                wakeProcess != null || DateTime.UtcNow < wakeRetryAfterUtc) return;
            Process process = null;
            try
            {
                string python = GetSetting(ReadSettings(), "wake_python_path", "");
                string model = GetSetting(ReadSettings(), "wake_model_path", "");
                string dependencies = GetSetting(ReadSettings(), "wake_deps_path", "");
                Dictionary<string, object> settings = ReadSettings();
                string deviceSetting = GetSetting(settings, "wake_device_index", "");
                string deviceName = GetSetting(settings, "wake_device_name", "");
                string hostApi = GetSetting(settings, "wake_host_api", "");
                int device;
                string deviceArgument = "";
                if (deviceName.Length > 0 && hostApi.Length > 0 && deviceName.Length <= 200 && hostApi.Length <= 200)
                {
                    deviceArgument = " --device-name-b64 " + Convert.ToBase64String(Encoding.UTF8.GetBytes(deviceName)) +
                        " --host-api-b64 " + Convert.ToBase64String(Encoding.UTF8.GetBytes(hostApi));
                }
                else if (deviceName.Length > 0 || hostApi.Length > 0)
                    throw new InvalidOperationException("The configured wake microphone is invalid.");
                else if (deviceSetting.Length > 0)
                {
                    if (!int.TryParse(deviceSetting, NumberStyles.None, CultureInfo.InvariantCulture, out device) || device < 0 || device > 128)
                        throw new InvalidOperationException("The configured wake microphone index is invalid.");
                    deviceArgument = " --device " + device.ToString(CultureInfo.InvariantCulture);
                }
                double score, threshold;
                if (!double.TryParse(GetSetting(settings, "wake_phrase_score", "1.0"), NumberStyles.Float, CultureInfo.InvariantCulture, out score) ||
                    !double.TryParse(GetSetting(settings, "wake_phrase_threshold", "0.25"), NumberStyles.Float, CultureInfo.InvariantCulture, out threshold) ||
                    score < 0.5 || score > 2.0 || threshold < 0.15 || threshold > 0.8)
                    throw new InvalidOperationException("The wake phrase tuning is invalid.");
                string worker = Path.Combine(installRoot, "wake_worker.py");
                if (string.IsNullOrWhiteSpace(python) || !File.Exists(python) ||
                    string.IsNullOrWhiteSpace(model) || !File.Exists(Path.Combine(model, "tokens.txt")) ||
                    string.IsNullOrWhiteSpace(dependencies) || !File.Exists(Path.Combine(dependencies, "sherpa_onnx", "__init__.py")) ||
                    !File.Exists(worker) || python.IndexOf('"') >= 0 || model.IndexOf('"') >= 0 ||
                    dependencies.IndexOf('"') >= 0 || worker.IndexOf('"') >= 0)
                    throw new InvalidOperationException("The offline wake runtime is unavailable.");
                using (SHA256 sha = SHA256.Create())
                using (FileStream file = File.OpenRead(worker))
                {
                    string hash = BitConverter.ToString(sha.ComputeHash(file)).Replace("-", "").ToLowerInvariant();
                    if (hash != WakeWorkerSha256) throw new InvalidOperationException("The wake worker failed its integrity check.");
                }
                ProcessStartInfo start = new ProcessStartInfo(python, "-I -B \"" + worker + "\" --model-dir \"" + model + "\" --deps-dir \"" + dependencies + "\"" + deviceArgument +
                    " --score " + score.ToString("0.00", CultureInfo.InvariantCulture) + " --threshold " + threshold.ToString("0.00", CultureInfo.InvariantCulture) +
                    (CloudVoiceEnabled() ? " --stream-chunks" : ""));
                start.UseShellExecute = false;
                start.CreateNoWindow = true;
                start.RedirectStandardOutput = true;
                start.EnvironmentVariables["HF_HUB_OFFLINE"] = "1";
                process = new Process { StartInfo = start };
                // A new worker begins a new cloud-capture attempt. Reset before
                // stdout is read, rather than in the later UI wake callback.
                cloudLiveUnavailable = false;
                if (!process.Start()) throw new InvalidOperationException("The wake worker could not start.");
                wakeProcess = process;
                wakeReady = false;
                wakeActivated = false;
                wakeStartedUtc = DateTime.UtcNow;
                Process owned = process;
                Task.Run(delegate
                {
                    string outcome = "WORKER_EXIT", audio = null;
                    int preRollFrames = 0;
                    bool workerWakeSeen = false;
                    try
                    {
                        string line;
                        while ((line = owned.StandardOutput.ReadLine()) != null)
                        {
                            if (line == "READY")
                            {
                                Ui(delegate
                                {
                                    if (wakeProcess != owned) return;
                                    wakeReady = true;
                                    bool recovering = wakeFailures > 0;
                                    if (recovering) WriteEvent("wake_word", "recovered", wakeFailures);
                                    wakeFailures = 0;
                                    if (tray != null) tray.Text = assistantName + " — listening locally for Cypher";
                                    if (recovering && !voiceListening && !voiceStopping && inputBox.IsEnabled)
                                    {
                                        SetStatus("READY", "#4DE3C1");
                                        UpdateTask("READY", "Local wake listening recovered and is ready.");
                                    }
                                    WriteEvent("wake_word", "listening", 0);
                                });
                            }
                            else if (line.StartsWith("DEVICE ", StringComparison.Ordinal) && line.Length <= 20)
                            {
                                string[] parts = line.Split(' ');
                                int index, rate;
                                if (parts.Length != 3 || !int.TryParse(parts[1], out index) ||
                                    !int.TryParse(parts[2], out rate) || index < 0 || index > 256 ||
                                    rate < 8000 || rate > 96000) { outcome = "PROTOCOL_ERROR"; break; }
                                Ui(delegate
                                {
                                    if (wakeProcess != owned) return;
                                    wakeDeviceIndex = index;
                                    wakeDeviceRate = rate;
                                    WriteEvent("wake_word", "input_selected", rate);
                                });
                            }
                            else if (line == "SILENT")
                            {
                                Ui(delegate
                                {
                                    if (wakeProcess != owned) return;
                                    UpdateTask("MIC QUIET", "The selected wake input has supplied almost no signal for 10 seconds. If you are speaking, open Microphone settings in the tray and test another input.");
                                    WriteEvent("wake_word", "input_quiet", 0);
                                });
                            }
                            else if (line == "SIGNAL")
                            {
                                Ui(delegate
                                {
                                    if (wakeProcess != owned)
                                        return;
                                    WriteEvent("wake_word", "audio_detected", 0);
                                    UpdateTask("MIC ACTIVE", "Microphone signal reaches Cypher on input " + wakeDeviceIndex + " at " + wakeDeviceRate + " Hz. Say Cypher to begin.");
                                });
                            }
                            else if (line == "WAKE")
                            {
                                workerWakeSeen = true;
                                Ui(delegate { if (wakeProcess == owned) OnWakeDetected(); });
                            }
                            else if (line.StartsWith("CHUNK ", StringComparison.Ordinal) && line.Length <= 5000)
                            {
                                // The protocol's WAKE marker precedes CHUNK on
                                // this reader thread; the UI callback may lag it.
                                if (workerWakeSeen) FeedCloudVoiceChunk(line.Substring(6));
                            }
                            else if (line == "STOP" || line == "NO_SPEECH")
                            {
                                outcome = line;
                                break;
                            }
                            else if (line.StartsWith("AUDIO ", StringComparison.Ordinal) && line.Length <= 750000)
                            {
                                int split = line.IndexOf(' ', 6);
                                int frames;
                                if (split <= 6 || !int.TryParse(line.Substring(6, split - 6), NumberStyles.None, CultureInfo.InvariantCulture, out frames) ||
                                    frames < 0 || frames > 18 * 1280) { outcome = "PROTOCOL_ERROR"; break; }
                                outcome = "AUDIO";
                                preRollFrames = frames;
                                audio = line.Substring(split + 1);
                                break;
                            }
                            else if (line.StartsWith("ERROR ", StringComparison.Ordinal))
                            {
                                outcome = SafeWakeFailure(line.Substring(6));
                                break;
                            }
                            else { outcome = "PROTOCOL_ERROR"; break; }
                        }
                    }
                    catch { }
                    string finalOutcome = outcome, finalAudio = audio;
                    int finalPreRoll = preRollFrames;
                    Ui(delegate { CompleteWakeWorker(owned, finalOutcome, finalAudio, finalPreRoll); });
                });
            }
            catch (Exception ex)
            {
                if (process != null) try { process.Dispose(); } catch { }
                wakeProcess = null;
                WakeFailed(ex is InvalidOperationException ? "CONFIGURATION" : "START_FAILED");
            }
        }

        private static string SafeWakeFailure(string code)
        {
            switch (code)
            {
                case "MODEL_MISSING": case "DEPENDENCY_MISSING": case "TUNING_INVALID":
                case "INPUT_UNAVAILABLE": case "INPUT_OVERFLOW": case "AUDIO_LIMIT":
                case "DEVICE_NOT_FOUND": case "DEVICE_INVALID": case "FORMAT_UNSUPPORTED":
                case "WORKER_FAILURE": return code;
                default: return "PROTOCOL_ERROR";
            }
        }

        private string RunWakeUtility(string arguments, int timeoutMs)
        {
            Dictionary<string, object> settings = ReadSettings();
            string python = GetSetting(settings, "wake_python_path", "");
            string dependencies = GetSetting(settings, "wake_deps_path", "");
            string worker = Path.Combine(installRoot, "wake_worker.py");
            if (!File.Exists(python) || !File.Exists(worker) ||
                !File.Exists(Path.Combine(dependencies, "sounddevice.py")) ||
                python.IndexOf('"') >= 0 || dependencies.IndexOf('"') >= 0 || worker.IndexOf('"') >= 0)
                throw new InvalidOperationException("The wake microphone runtime is unavailable.");
            using (SHA256 sha = SHA256.Create())
            using (FileStream file = File.OpenRead(worker))
            {
                string hash = BitConverter.ToString(sha.ComputeHash(file)).Replace("-", "").ToLowerInvariant();
                if (hash != WakeWorkerSha256) throw new InvalidOperationException("The wake worker failed its integrity check.");
            }
            ProcessStartInfo start = new ProcessStartInfo(python,
                "-I -B \"" + worker + "\" --deps-dir \"" + dependencies + "\" " + arguments);
            start.UseShellExecute = false;
            start.CreateNoWindow = true;
            start.RedirectStandardOutput = true;
            start.EnvironmentVariables["HF_HUB_OFFLINE"] = "1";
            using (Process process = new Process { StartInfo = start })
            {
                process.Start();
                // Drain stdout while the worker runs. Waiting for exit first
                // can deadlock when a device list fills the redirected pipe.
                Task<string> outputTask = process.StandardOutput.ReadToEndAsync();
                if (!process.WaitForExit(timeoutMs))
                {
                    try { process.Kill(); } catch { }
                    throw new TimeoutException("The wake microphone check timed out.");
                }
                string output = outputTask.GetAwaiter().GetResult().Trim();
                if (process.ExitCode != 0 || output.Length > 32768 || output.Length == 0)
                    throw new InvalidOperationException("The wake microphone check failed.");
                return output;
            }
        }

        private static string MicrophoneSelector(WakeMicChoice choice)
        {
            if (choice == null) return "";
            return " --device-name-b64 " + Convert.ToBase64String(Encoding.UTF8.GetBytes(choice.Name)) +
                " --host-api-b64 " + Convert.ToBase64String(Encoding.UTF8.GetBytes(choice.Api));
        }

        private void ShowWakeMicrophoneSettings()
        {
            if (voiceListening || voiceStopping)
            {
                MessageBox.Show("Finish voice input before checking the wake microphone.", "Cypher microphone");
                return;
            }
            StopWakeListening();
            try
            {
                string output = RunWakeUtility("--list-devices", 12000);
                if (!output.StartsWith("DEVICES ", StringComparison.Ordinal)) throw new InvalidOperationException();
                object[] devices = new JavaScriptSerializer().DeserializeObject(output.Substring(8)) as object[];
                if (devices == null) throw new InvalidOperationException();
                Dictionary<string, object> settings = ReadSettings();
                Window dialog = new Window
                {
                    Title = "Cypher wake microphone", Width = 550, Height = 350,
                    WindowStartupLocation = WindowStartupLocation.CenterScreen,
                    ResizeMode = ResizeMode.NoResize,
                    Background = new System.Windows.Media.SolidColorBrush(System.Windows.Media.Color.FromRgb(20, 20, 20)),
                    Foreground = System.Windows.Media.Brushes.White
                };
                StackPanel panel = new StackPanel { Margin = new Thickness(22) };
                dialog.Content = panel;
                panel.Children.Add(new TextBlock { Text = "WAKE MICROPHONE", FontSize = 18, Margin = new Thickness(0, 0, 0, 12) });
                panel.Children.Add(new TextBlock { Text = "Choose the microphone Cypher should use after Windows sign-in. Automatic prefers the WASAPI copy of your default Windows input. Test while speaking normally; no audio is saved.", TextWrapping = TextWrapping.Wrap, Margin = new Thickness(0, 0, 0, 14) });
                ComboBox choices = new ComboBox { MinHeight = 30, Margin = new Thickness(0, 0, 0, 14) };
                choices.Items.Add(new ComboBoxItem { Content = "Automatic — Windows default, prefer WASAPI", Tag = null });
                string selectedName = GetSetting(settings, "wake_device_name", "");
                string selectedApi = GetSetting(settings, "wake_host_api", "");
                foreach (object item in devices)
                {
                    Dictionary<string, object> data = HermesClient.AsDictionary(item);
                    WakeMicChoice choice = new WakeMicChoice
                    {
                        Index = Convert.ToInt32(HermesClient.Get(data, "index")),
                        Name = Convert.ToString(HermesClient.Get(data, "name")),
                        Api = Convert.ToString(HermesClient.Get(data, "api")),
                        Rate = Convert.ToInt32(HermesClient.Get(data, "rate"))
                    };
                    if (choice.Name == null || choice.Api == null || choice.Name.Length > 200 || choice.Api.Length > 200) continue;
                    ComboBoxItem entry = new ComboBoxItem
                    {
                        Content = choice.Name + "  /  " + choice.Api + "  /  " + choice.Rate + " Hz",
                        Tag = choice
                    };
                    choices.Items.Add(entry);
                    if (choice.Name == selectedName && choice.Api == selectedApi) choices.SelectedItem = entry;
                }
                if (choices.SelectedIndex < 0) choices.SelectedIndex = 0;
                panel.Children.Add(choices);
                TextBlock result = new TextBlock { Text = "Speak during the 3-second test. A signal should be detected before saving.", TextWrapping = TextWrapping.Wrap, Margin = new Thickness(0, 0, 0, 16) };
                panel.Children.Add(result);
                StackPanel buttons = new StackPanel { Orientation = Orientation.Horizontal };
                Button test = new Button { Content = "TEST INPUT", Width = 120, Height = 34, Margin = new Thickness(0, 0, 10, 0) };
                Button save = new Button { Content = "SAVE INPUT", Width = 120, Height = 34 };
                buttons.Children.Add(test);
                buttons.Children.Add(save);
                panel.Children.Add(buttons);
                test.Click += async delegate
                {
                    test.IsEnabled = false;
                    save.IsEnabled = false;
                    choices.IsEnabled = false;
                    try
                    {
                        result.Text = "Testing now — speak clearly for 3 seconds...";
                        WakeMicChoice choice = (WakeMicChoice)((ComboBoxItem)choices.SelectedItem).Tag;
                        string selector = MicrophoneSelector(choice);
                        string probe = await Task.Run(() => RunWakeUtility("--probe-device" + selector, 15000));
                        int peak;
                        if (!probe.StartsWith("PROBE ", StringComparison.Ordinal) ||
                            !int.TryParse(probe.Substring(6), out peak) || peak < 0 || peak > 32768)
                            throw new InvalidOperationException();
                        result.Text = peak >= 1000
                            ? "Signal detected. This input is suitable for a wake-word trial."
                            : "Very little sound reached this input. Try another microphone or Windows audio endpoint.";
                    }
                    catch { result.Text = "This input could not be tested. Try another microphone or Windows audio endpoint."; }
                    finally
                    {
                        test.IsEnabled = true;
                        save.IsEnabled = true;
                        choices.IsEnabled = true;
                    }
                };
                save.Click += delegate
                {
                    try
                    {
                        WakeMicChoice choice = (WakeMicChoice)((ComboBoxItem)choices.SelectedItem).Tag;
                        settings["wake_device_name"] = choice == null ? "" : choice.Name;
                        settings["wake_host_api"] = choice == null ? "" : choice.Api;
                        settings["wake_device_index"] = "";
                        string pending = configPath + ".pending";
                        File.WriteAllText(pending, new JavaScriptSerializer().Serialize(settings), new UTF8Encoding(false));
                        File.Replace(pending, configPath, null);
                        wakeFailures = 0;
                        wakeRetryAfterUtc = DateTime.MinValue;
                        WriteEvent("wake_word", "input_setting_changed", 0);
                        dialog.Close();
                    }
                    catch { MessageBox.Show(dialog, "The microphone choice could not be saved. Existing settings were kept.", "Cypher microphone"); }
                };
                dialog.Closed += delegate { TryStartWakeListening(); };
                dialog.ShowDialog();
            }
            catch
            {
                TryStartWakeListening();
                MessageBox.Show("Cypher could not list microphone inputs. The current input setting was kept.", "Cypher microphone");
            }
        }

        private void WakeFailed(string reason)
        {
            wakeFailures++;
            wakeRetryAfterUtc = DateTime.UtcNow.AddSeconds(Math.Min(60, 5 * (1 << Math.Min(wakeFailures - 1, 4))));
            if (tray != null) tray.Text = assistantName + " — wake unavailable (" + reason + "); MIC still works";
            if (!voiceListening && !voiceStopping && !cloudAnswerActive && inputBox.IsEnabled)
            {
                SetStatus("WAKE OFF", "#F2C66D");
                UpdateTask("WAKE OFF", "Local wake listening stopped (" + reason + "). Cypher will retry automatically; manual MIC remains available.");
            }
            WriteEvent("wake_word", "unavailable_" + reason.ToLowerInvariant(), 0);
        }

        private void OnWakeDetected()
        {
            Stopwatch acknowledgement = Stopwatch.StartNew();
            wakeActivated = true;
            voiceListening = true; // prevents another wake worker while this stream captures the command
            SetStatus("WAKE HEARD", "#83E7FF");
            UpdateTask("WAKE HEARD", "Cypher heard its name. Continue speaking; the same microphone remains open.");
            WriteEvent("wake_word", "activated", 0);
            try { Console.Beep(960, 90); } catch { try { System.Media.SystemSounds.Beep.Play(); } catch { } }
            WriteEvent("voice_latency", "wake_to_ack", (int)acknowledgement.ElapsedMilliseconds);
        }

        private void CompleteWakeWorker(Process process, string outcome, string audio, int preRollFrames)
        {
            if (process != wakeProcess) return;
            bool activated = wakeActivated;
            LiveCloudCapture live = cloudVoiceLive;
            cloudVoiceLive = null;
            StopWakeListening();
            if (paused || closing) { if (live != null) live.Dispose(); voiceListening = false; return; }
            if (outcome == "STOP")
            {
                if (live != null) live.Dispose();
                voiceListening = false;
                CancelActive();
                WriteEvent("wake_word", "spoken_stop", 0);
                return;
            }
            if (outcome == "AUDIO" && activated)
            {
                try
                {
                    byte[] wave = Convert.FromBase64String(audio);
                    if (wave.Length < 44 || wave.Length > 500000) throw new FormatException();
                    if (live != null) live.Complete();
                    ProcessWakeAudio(wave, preRollFrames, live);
                }
                catch (FormatException) { if (live != null) live.Dispose(); voiceListening = false; WakeFailed("AUDIO_INVALID"); }
                return;
            }
            if (live != null) live.Dispose();
            if (outcome == "NO_SPEECH" && activated)
            {
                voiceListening = false;
                SetStatus("NO SPEECH", "#F2C66D");
                UpdateTask("NO SPEECH", "Cypher heard its name but no command followed. Try again.");
                WriteEvent("wake_word", "no_command", 0);
                return;
            }
            voiceListening = false;
            WakeFailed(outcome);
        }

        private void StopWakeListening()
        {
            LiveCloudCapture live = cloudVoiceLive;
            cloudVoiceLive = null;
            if (live != null) live.Dispose();
            Process process = wakeProcess;
            wakeProcess = null;
            wakeReady = false;
            wakeActivated = false;
            if (process == null) return;
            try { if (!process.HasExited) process.Kill(); } catch { }
            try { process.WaitForExit(1000); } catch { }
            try { process.Dispose(); } catch { }
            if (tray != null) tray.Text = assistantName + " local assistant";
        }

        private void DisposeWakeWord()
        {
            if (wakeTimer != null) wakeTimer.Stop();
            StopWakeListening();
        }
    }
}
