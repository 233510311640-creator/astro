using System;
using System.Diagnostics;
using System.IO;
using System.Security.Cryptography;
using System.Threading.Tasks;
using System.Windows.Threading;

namespace Cypher.CorePreview
{
    internal sealed partial class CypherHost
    {
        private const string WakeWorkerSha256 = "47b4b98a1b78f39024ec2c42cab6ed8e31a765750b5221cfbb8bb6f132f5b891";
        private Process wakeProcess;
        private DispatcherTimer wakeTimer;
        private bool wakeEnabled;
        private DateTime wakeRetryAfterUtc;

        private void InitializeWakeWord()
        {
            wakeEnabled = string.Equals(GetSetting(ReadSettings(), "wake_word_enabled", "false"), "true", StringComparison.OrdinalIgnoreCase);
            if (!wakeEnabled) return;
            wakeTimer = new DispatcherTimer { Interval = TimeSpan.FromSeconds(3) };
            wakeTimer.Tick += delegate { TryStartWakeListening(); };
            wakeTimer.Start();
            TryStartWakeListening();
        }

        private void TryStartWakeListening()
        {
            if (!wakeEnabled || closing || paused || voiceListening || voiceStopping || voiceSpeaking ||
                wakeProcess != null || DateTime.UtcNow < wakeRetryAfterUtc) return;
            Process process = null;
            try
            {
                string python = GetSetting(ReadSettings(), "wake_python_path", "");
                string model = GetSetting(ReadSettings(), "wake_model_path", "");
                string dependencies = GetSetting(ReadSettings(), "wake_deps_path", "");
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
                ProcessStartInfo start = new ProcessStartInfo(python, "-I -B \"" + worker + "\" --model-dir \"" + model + "\" --deps-dir \"" + dependencies + "\"");
                start.UseShellExecute = false;
                start.CreateNoWindow = true;
                start.RedirectStandardOutput = true;
                start.EnvironmentVariables["HF_HUB_OFFLINE"] = "1";
                process = new Process { StartInfo = start };
                if (!process.Start()) throw new InvalidOperationException("The wake worker could not start.");
                wakeProcess = process;
                Process owned = process;
                Task.Run(delegate
                {
                    string outcome = "ERROR";
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
                                    if (tray != null) tray.Text = assistantName + " — listening locally for Cypher";
                                    WriteEvent("wake_word", "listening", 0);
                                });
                            }
                            else if (line == "SIGNAL")
                            {
                                Ui(delegate { if (wakeProcess == owned) WriteEvent("wake_word", "audio_detected", 0); });
                            }
                            else if (line == "WAKE" || line == "STOP")
                            {
                                outcome = line;
                                break;
                            }
                        }
                    }
                    catch { }
                    Ui(delegate { CompleteWakeWorker(owned, outcome); });
                });
            }
            catch
            {
                if (process != null) try { process.Dispose(); } catch { }
                wakeProcess = null;
                wakeRetryAfterUtc = DateTime.UtcNow.AddSeconds(30);
                if (tray != null) tray.Text = assistantName + " — wake word unavailable; MIC still works";
                WriteEvent("wake_word", "unavailable", 0);
            }
        }

        private void CompleteWakeWorker(Process process, string outcome)
        {
            if (process != wakeProcess) return;
            StopWakeListening();
            if (paused || closing) return;
            if (outcome == "STOP")
            {
                CancelActive();
                WriteEvent("wake_word", "spoken_stop", 0);
                return;
            }
            if (outcome != "WAKE")
            {
                wakeRetryAfterUtc = DateTime.UtcNow.AddSeconds(30);
                if (tray != null) tray.Text = assistantName + " — wake word unavailable; MIC still works";
                WriteEvent("wake_word", "unavailable", 0);
                return;
            }
            if (!inputBox.IsEnabled || !string.IsNullOrWhiteSpace(inputBox.Text))
            {
                ShowWindow();
                SetStatus("VOICE WAIT", "#F2C66D");
                UpdateTask("VOICE WAIT", "Cypher heard its name, but a task or unsent draft is already present. Finish or clear it first.");
                return;
            }
            AcknowledgeWake();
            WriteEvent("wake_word", "activated", 0);
        }

        private void StopWakeListening()
        {
            Process process = wakeProcess;
            wakeProcess = null;
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
