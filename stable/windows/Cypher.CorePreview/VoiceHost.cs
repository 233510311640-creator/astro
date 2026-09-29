using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Globalization;
using System.IO;
using System.Security.Cryptography;
using System.Speech.Recognition;
using System.Speech.Synthesis;
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
        private Button microphoneButton;
        private Button readAloudButton;
        private SpeechRecognitionEngine voiceRecognizer;
        private SpeechSynthesizer voiceSpeaker;
        private Prompt activeVoicePrompt;
        private Prompt wakeGreetingPrompt;
        private DispatcherTimer voiceTimer;
        private DateTime voiceDeadlineUtc;
        private VoiceActivityGate voiceActivityGate;
        private readonly StringBuilder voiceTranscript = new StringBuilder();
        private bool voiceListening;
        private bool voiceStopping;
        private bool voiceSpeaking;
        private bool voiceKeepTranscript;
        private int voicePeakLevel;
        private bool voiceSpeechDetected;
        private bool voiceUncertain;
        private DateTime voiceLastLevelUpdate;
        private VoiceCapture voiceCapture;
        private Process voiceProcess;
        private readonly object voiceProcessGate = new object();
        private int voiceEpoch;
        private bool voiceAutoSubmit;
        private bool wakeReplyPending;
        private const string VoiceWorkerSha256 = "f6ec0c5dd683b8340894ce6e12b151592e561dc7f787686b6b29264118728554";

        private static RecognizerInfo LocalRecognizer()
        {
            RecognizerInfo fallback = null;
            foreach (RecognizerInfo info in SpeechRecognitionEngine.InstalledRecognizers())
            {
                if (fallback == null) fallback = info;
                if (string.Equals(info.Culture.Name, CultureInfo.CurrentUICulture.Name, StringComparison.OrdinalIgnoreCase))
                    return info;
                if (string.Equals(info.Culture.Name, "en-US", StringComparison.OrdinalIgnoreCase))
                    fallback = info;
            }
            return fallback;
        }

        public static bool VoiceSelfTest()
        {
            try
            {
                // RecognizeAsyncStop may report Cancelled even when END MIC was intentional.
                if (!KeepVoiceDraftAfterCompletion(true, true, false) ||
                    KeepVoiceDraftAfterCompletion(false, false, false) ||
                    KeepVoiceDraftAfterCompletion(true, false, true)) return false;
                TextBox draft = new TextBox();
                draft.MaxLength = 32;
                if (!AppendVoiceDraft(draft, "spoken request") || draft.Text != "spoken request") return false;
                if (!AppendVoiceDraft(draft, "continued") || draft.Text != "spoken request continued") return false;
                byte[] fixture = VoiceCapture.BuildWave(new byte[16000], 16000);
                if (fixture.Length != 16044 || Encoding.ASCII.GetString(fixture, 0, 4) != "RIFF") return false;
                if (VoiceCapture.RootMeanSquare(new byte[] { 0, 0, 0, 0 }) != 0 ||
                    VoiceCapture.RootMeanSquare(new byte[] { 0xE8, 0x03, 0x18, 0xFC }) != 1000 ||
                    !VoiceActivityGate.SelfTest()) return false;
                using (SpeechSynthesizer speaker = new SpeechSynthesizer())
                    return speaker.GetInstalledVoices().Count > 0;
            }
            catch { return false; }
        }

        private static bool KeepVoiceDraftAfterCompletion(bool userRequestedFinish, bool recognizerCancelled, bool failed)
        {
            // The engine's Cancelled flag is not the user's Stop intent. Only Stop clears
            // voiceKeepTranscript; a successful END MIC must retain words already heard.
            return userRequestedFinish && !failed;
        }

        private static bool AppendVoiceDraft(TextBox destination, string heard)
        {
            string existing = destination.Text ?? "";
            int limit = destination.MaxLength > 0 ? destination.MaxLength : 32000;
            int separatorLength = existing.Length == 0 ? 0 : 1;
            int remaining = Math.Max(0, limit - existing.Length - separatorLength);
            if (remaining == 0 || string.IsNullOrWhiteSpace(heard)) return false;
            destination.Text = existing + (separatorLength == 0 ? "" : " ") + heard.Substring(0, Math.Min(heard.Length, remaining));
            destination.CaretIndex = destination.Text.Length;
            return true;
        }

        private void StartVoiceInput() { StartVoiceInput(false); }

        private void StartVoiceInput(bool autoSubmit)
        {
            if (!inputBox.IsEnabled || (!autoSubmit && !window.IsVisible) || paused || voiceListening || voiceStopping) return;
            if (autoSubmit && !string.IsNullOrWhiteSpace(inputBox.Text)) return;
            StopWakeListening();
            StopSpeaking();
            VoiceCapture capture = null;
            try
            {
                string model = GetSetting(ReadSettings(), "voice_model_path", "");
                if (string.IsNullOrWhiteSpace(model) || !File.Exists(Path.Combine(model, "model.bin")))
                    throw new InvalidOperationException("The offline voice model is not configured. Install the local Whisper voice package first.");
                capture = new VoiceCapture();
                capture.Start();
                voiceCapture = capture;
                voiceTranscript.Clear();
                voicePeakLevel = 0;
                voiceSpeechDetected = false;
                voiceUncertain = false;
                voiceLastLevelUpdate = DateTime.MinValue;
                voiceListening = true;
                voiceStopping = false;
                voiceKeepTranscript = true;
                voiceAutoSubmit = autoSubmit;
                voiceActivityGate = autoSubmit ? new VoiceActivityGate() : null;
                voiceDeadlineUtc = DateTime.UtcNow.AddSeconds(autoSubmit ? 12 : 20);
                voiceEpoch++;
                if (voiceTimer == null)
                {
                    voiceTimer = new DispatcherTimer();
                    voiceTimer.Interval = TimeSpan.FromMilliseconds(200);
                    voiceTimer.Tick += delegate { PollVoiceInput(); };
                }
                voiceTimer.Start();
                SetInteractive(false);
                microphoneButton.IsEnabled = true;
                microphoneButton.Content = "END MIC";
                microphoneButton.ToolTip = "Finish recording and review the transcript";
                microphoneButton.SetValue(System.Windows.Automation.AutomationProperties.NameProperty, "Finish voice input");
                SetStatus("LISTENING", "#F2C66D");
                UpdateTask("LISTENING", autoSubmit
                    ? "Wake word heard. Speak your command now; Cypher will finish after you pause, or after 12 seconds at most. Approvals still require review."
                    : "Recording locally for up to 20 seconds. Speak now, then press END MIC. Transcription appears after recording; Stop discards it.");
                WriteEvent("voice_input", "started", 0);
            }
            catch (Exception ex)
            {
                voiceCapture = null;
                voiceListening = false;
                voiceStopping = false;
                voiceAutoSubmit = false;
                if (capture != null) capture.Dispose();
                SetInteractive(true);
                ShowError("Voice input unavailable", ex.Message);
            }
        }

        private void PollVoiceInput()
        {
            if (!voiceListening || voiceStopping) return;
            try
            {
                if (voiceActivityGate != null && voiceCapture != null)
                {
                    foreach (int level in voiceCapture.ReadCompletedLevels())
                    {
                        if (level > voicePeakLevel) voicePeakLevel = level;
                        if (voiceActivityGate.Observe(level))
                        {
                            WriteEvent("voice_input", "speech_end", 0);
                            FinishVoiceInput();
                            return;
                        }
                    }
                }
                if (DateTime.UtcNow >= voiceDeadlineUtc) FinishVoiceInput();
            }
            catch (Exception ex)
            {
                CancelVoiceInput();
                ShowError("Voice recording failed", ex.Message);
            }
        }

        private void VoiceSpeechRecognized(object sender, SpeechRecognizedEventArgs args)
        {
            string text = args.Result == null ? "" : args.Result.Text;
            float confidence = args.Result == null ? 0 : args.Result.Confidence;
            if (string.IsNullOrWhiteSpace(text)) return;
            window.Dispatcher.BeginInvoke(new Action(delegate
            {
                if (sender != voiceRecognizer || !voiceListening || voiceTranscript.Length >= 1200) return;
                if (confidence < 0.45f) voiceUncertain = true;
                StringBuilder safe = new StringBuilder(text.Length);
                foreach (char character in text) safe.Append(char.IsControl(character) ? ' ' : character);
                string cleaned = safe.ToString().Trim();
                if (cleaned.Length == 0) return;
                if (voiceTranscript.Length > 0) voiceTranscript.Append(' ');
                voiceTranscript.Append(cleaned.Substring(0, Math.Min(cleaned.Length, 1200 - voiceTranscript.Length)));
                SetStatus("WORDS HEARD", "#F2C66D");
                UpdateTask("LISTENING", "Words detected. Press END MIC to review the draft" + (voiceUncertain ? "; recognition may be inaccurate." : "."));
            }));
        }

        private void VoiceSpeechDetected(object sender, SpeechDetectedEventArgs args)
        {
            window.Dispatcher.BeginInvoke(new Action(delegate
            {
                if (sender != voiceRecognizer || !voiceListening || voiceStopping) return;
                voiceSpeechDetected = true;
                SetStatus("SPEECH HEARD", "#F2C66D");
                UpdateTask("LISTENING", "Speech was detected. Press END MIC to see any recognized words; Stop discards the draft.");
            }));
        }

        private void VoiceSpeechRejected(object sender, SpeechRecognitionRejectedEventArgs args)
        {
            window.Dispatcher.BeginInvoke(new Action(delegate
            {
                if (sender != voiceRecognizer || !voiceListening || voiceStopping) return;
                voiceSpeechDetected = true;
                SetStatus("UNCLEAR SPEECH", "#F2C66D");
                UpdateTask("LISTENING", "The microphone heard speech, but Windows could not make out the words. Try speaking closer to the microphone.");
            }));
        }

        private void VoiceAudioLevelUpdated(object sender, AudioLevelUpdatedEventArgs args)
        {
            int level = args.AudioLevel;
            window.Dispatcher.BeginInvoke(new Action(delegate
            {
                if (sender != voiceRecognizer || !voiceListening || voiceStopping) return;
                if (level > voicePeakLevel) voicePeakLevel = level;
                if (voiceSpeechDetected || voiceTranscript.Length > 0 || DateTime.UtcNow - voiceLastLevelUpdate < TimeSpan.FromMilliseconds(300)) return;
                voiceLastLevelUpdate = DateTime.UtcNow;
                SetStatus("MIC " + level.ToString() + "%", level > 4 ? "#F2C66D" : "#83E7FF");
                UpdateTask("LISTENING", level > 4 ? "Microphone signal detected. Speak now; words appear after END MIC." : "Listening, but little microphone signal is reaching Windows. Check the selected input device and input level.");
            }));
        }

        private void FinishVoiceInput()
        {
            if (!voiceListening || voiceStopping) return;
            voiceStopping = true;
            voiceKeepTranscript = true;
            if (voiceTimer != null) voiceTimer.Stop();
            microphoneButton.IsEnabled = false;
            SetStatus("TRANSCRIBING", "#F2C66D");
            UpdateTask("TRANSCRIBING", "Processing the recording with the offline voice model. Stop discards it; nothing is sent.");
            byte[] audio;
            try
            {
                audio = voiceCapture.Finish();
                voiceCapture.Dispose();
                voiceCapture = null;
            }
            catch (Exception ex)
            {
                if (voiceCapture != null) { voiceCapture.Dispose(); voiceCapture = null; }
                CompleteVoiceInput(false);
                ShowError("Voice recording failed", ex.Message);
                return;
            }
            int epoch = voiceEpoch;
            Task.Run(delegate
            {
                string heard = "", error = "";
                try { heard = RunVoiceWorker(audio, epoch); }
                catch (OperationCanceledException) { return; }
                catch (Exception ex) { error = ex.Message; }
                finally { Array.Clear(audio, 0, audio.Length); }
                Ui(delegate
                {
                    if (epoch != voiceEpoch || !voiceStopping) return;
                    if (error.Length > 0) { CompleteVoiceInput(false); ShowError("Voice transcription failed", error); return; }
                    voiceTranscript.Clear();
                    voiceTranscript.Append(heard);
                    CompleteVoiceInput(true);
                });
            });
        }

        private string RunVoiceWorker(byte[] audio, int epoch)
        {
            string python = GetSetting(ReadSettings(), "research_python_path", "");
            string model = GetSetting(ReadSettings(), "voice_model_path", "");
            string worker = Path.Combine(installRoot, "voice_worker.py");
            if (string.IsNullOrWhiteSpace(python) || !File.Exists(python) ||
                string.IsNullOrWhiteSpace(model) || !File.Exists(Path.Combine(model, "model.bin")) ||
                !File.Exists(worker) || python.IndexOf('"') >= 0 || model.IndexOf('"') >= 0 || worker.IndexOf('"') >= 0)
                throw new InvalidOperationException("The offline voice worker, model, or Python runtime is unavailable.");
            using (SHA256 sha = SHA256.Create())
            using (FileStream file = File.OpenRead(worker))
            {
                string hash = BitConverter.ToString(sha.ComputeHash(file)).Replace("-", "").ToLowerInvariant();
                if (hash != VoiceWorkerSha256) throw new InvalidOperationException("The installed voice worker failed its integrity check.");
            }
            ProcessStartInfo start = new ProcessStartInfo(python, "-I -B \"" + worker + "\" --model \"" + model + "\"");
            start.UseShellExecute = false;
            start.CreateNoWindow = true;
            start.RedirectStandardInput = true;
            start.RedirectStandardOutput = true;
            start.EnvironmentVariables["HF_HUB_OFFLINE"] = "1";
            start.EnvironmentVariables["TRANSFORMERS_OFFLINE"] = "1";
            using (Process process = new Process { StartInfo = start })
            {
                lock (voiceProcessGate)
                {
                    if (epoch != voiceEpoch) throw new OperationCanceledException();
                    if (!process.Start()) throw new InvalidOperationException("The offline voice worker could not start.");
                    voiceProcess = process;
                }
                try
                {
                    process.StandardInput.BaseStream.Write(audio, 0, audio.Length);
                    process.StandardInput.Close();
                    Task<string> output = Task.Run(delegate { return process.StandardOutput.ReadLine(); });
                    if (!process.WaitForExit(120000))
                    {
                        try { process.Kill(); } catch { }
                        throw new TimeoutException("The offline voice model took too long. Try a shorter recording.");
                    }
                    if (!output.Wait(3000) || output.Result == null || output.Result.Length > 4096)
                        throw new InvalidOperationException("The offline voice worker returned an invalid result.");
                    Dictionary<string, object> result = new JavaScriptSerializer().DeserializeObject(output.Result) as Dictionary<string, object>;
                    object status, text;
                    if (result == null || !result.TryGetValue("status", out status) || !(status is string) ||
                        !result.TryGetValue("text", out text) || !(text is string) || ((string)text).Length > 1200)
                        throw new InvalidOperationException("The offline voice worker returned an invalid result.");
                    if ((string)status == "error") throw new InvalidOperationException("The local recognizer could not process this recording. Check the voice model and Python dependencies.");
                    if ((string)status != "ok" && (string)status != "no_speech")
                        throw new InvalidOperationException("The offline voice worker returned an invalid state.");
                    return (string)text;
                }
                finally
                {
                    lock (voiceProcessGate) { if (voiceProcess == process) voiceProcess = null; }
                }
            }
        }

        private void VoiceRecognizeCompleted(object sender, RecognizeCompletedEventArgs args)
        {
            window.Dispatcher.BeginInvoke(new Action(delegate
            {
                if (sender != voiceRecognizer) return;
                if (args.Error != null) { CompleteVoiceInput(false); ShowError("Voice input failed", args.Error.Message); return; }
                WriteEvent("voice_input_complete", args.Cancelled ? "engine_cancelled" : "engine_finished", 0);
                CompleteVoiceInput(KeepVoiceDraftAfterCompletion(voiceKeepTranscript, args.Cancelled, false));
            }));
        }

        private void CompleteVoiceInput(bool keepTranscript)
        {
            SpeechRecognitionEngine recognizer = voiceRecognizer;
            voiceRecognizer = null;
            voiceListening = false;
            voiceStopping = false;
            voiceActivityGate = null;
            if (voiceTimer != null) voiceTimer.Stop();
            if (recognizer != null)
            {
                recognizer.SpeechRecognized -= VoiceSpeechRecognized;
                recognizer.SpeechDetected -= VoiceSpeechDetected;
                recognizer.SpeechRecognitionRejected -= VoiceSpeechRejected;
                recognizer.AudioLevelUpdated -= VoiceAudioLevelUpdated;
                recognizer.RecognizeCompleted -= VoiceRecognizeCompleted;
                try { recognizer.SetInputToNull(); } catch { }
                try { recognizer.Dispose(); } catch { }
            }
            string heard = keepTranscript ? voiceTranscript.ToString().Trim() : "";
            bool autoSend = keepTranscript && voiceAutoSubmit;
            voiceAutoSubmit = false;
            voiceTranscript.Clear();
            microphoneButton.Content = "MIC";
            microphoneButton.ToolTip = "Start local voice input; press again to review the transcript";
            microphoneButton.SetValue(System.Windows.Automation.AutomationProperties.NameProperty, "Start voice input");
            SetInteractive(true);
            if (heard.Length > 0 && AppendVoiceDraft(inputBox, heard))
            {
                inputBox.Focus();
                if (autoSend)
                {
                    SetStatus("VOICE SEND", "#83E7FF");
                    UpdateTask("VOICE SEND", "Wake-triggered words were transcribed locally. Submitting the command; existing action approvals still apply.");
                    WriteEvent("voice_input", "wake_auto_submit", 0);
                    wakeReplyPending = true;
                    lastResponse = "";
                    BeginRequest();
                    MaybeSpeakWakeReply();
                    return;
                }
                SetStatus("REVIEW VOICE", "#83E7FF");
                UpdateTask("REVIEW", voiceUncertain ? "Recognition was uncertain. Correct the text in the input box, then press Send only if it is right." : "Check the recognized text in the input box, then press Send if it is correct.");
                WriteEvent("voice_input", voiceUncertain ? "uncertain_draft" : "draft_ready", 0);
            }
            else if (heard.Length > 0)
            {
                SetStatus("INPUT FULL", "#F2C66D");
                UpdateTask("INPUT FULL", "The input box is full. Shorten its text, then dictate again; no words were sent.");
                WriteEvent("voice_input", "draft_full", 0);
            }
            else
            {
                bool hadSignal = voicePeakLevel > 4 || voiceSpeechDetected;
                SetStatus(keepTranscript ? "NO SPEECH" : "READY", keepTranscript ? "#F2C66D" : "#4DE3C1");
                UpdateTask(keepTranscript ? "NO SPEECH" : "CANCELLED", !keepTranscript ? "Microphone stopped; no transcript was added." : "The offline recognizer found no clear words. Check the microphone input level and try a short, quiet-background recording.");
                WriteEvent("voice_input", !keepTranscript ? "cancelled" : hadSignal ? "no_match" : "no_signal", 0);
                if (keepTranscript && autoSend && !window.IsVisible && tray != null)
                    tray.ShowBalloonTip(3500, assistantName, "No clear command was heard. Press Ctrl+Alt+Space to try again.", System.Windows.Forms.ToolTipIcon.Warning);
            }
        }

        private void CancelVoiceInput()
        {
            if (!voiceListening && !voiceStopping) return;
            voiceKeepTranscript = false;
            voiceEpoch++;
            if (voiceCapture != null) { voiceCapture.Dispose(); voiceCapture = null; }
            lock (voiceProcessGate)
            {
                if (voiceProcess != null) try { if (!voiceProcess.HasExited) voiceProcess.Kill(); } catch { }
            }
            SpeechRecognitionEngine recognizer = voiceRecognizer;
            if (recognizer != null) try { recognizer.RecognizeAsyncCancel(); } catch { }
            CompleteVoiceInput(false);
        }

        private void ToggleVoiceInput()
        {
            if (voiceListening) FinishVoiceInput();
            else StartVoiceInput();
        }

        private void AcknowledgeWake()
        {
            StopWakeListening();
            StopSpeaking();
            try
            {
                if (voiceSpeaker == null)
                {
                    voiceSpeaker = new SpeechSynthesizer();
                    voiceSpeaker.SetOutputToDefaultAudioDevice();
                    voiceSpeaker.SpeakCompleted += VoiceSpeakCompleted;
                }
                voiceSpeaker.Volume = 100;
                voiceSpeaking = true;
                SetStatus("WAKE HEARD", "#83E7FF");
                UpdateTask("WAKE HEARD", "Cypher heard its name and is replying. Speak your command after the acknowledgement.");
                WriteEvent("voice_output", "greeting_started", 0);
                wakeGreetingPrompt = voiceSpeaker.SpeakAsync("Yes?");
            }
            catch
            {
                WriteEvent("voice_output", "greeting_failed", 0);
                StopSpeaking();
                try { System.Media.SystemSounds.Beep.Play(); } catch { }
                StartVoiceInput(true);
            }
        }

        private void MaybeSpeakWakeReply()
        {
            if (!wakeReplyPending || voiceListening || voiceStopping || !inputBox.IsEnabled ||
                string.IsNullOrWhiteSpace(lastResponse)) return;
            wakeReplyPending = false;
            ToggleReadAloud();
        }

        private void ToggleReadAloud()
        {
            if (voiceSpeaking) { StopSpeaking(); return; }
            if (voiceListening || voiceStopping || string.IsNullOrWhiteSpace(lastResponse)) return;
            StopWakeListening();
            try
            {
                if (voiceSpeaker == null)
                {
                    voiceSpeaker = new SpeechSynthesizer();
                    voiceSpeaker.SetOutputToDefaultAudioDevice();
                    voiceSpeaker.SpeakCompleted += VoiceSpeakCompleted;
                }
                voiceSpeaker.Volume = 100;
                string spoken = PlainTextForDisplay(lastResponse).Trim();
                if (spoken.Length > 1200) spoken = spoken.Substring(0, 1200);
                if (spoken.Length == 0) return;
                voiceSpeaking = true;
                readAloudButton.Content = "STOP AUDIO";
                readAloudButton.SetValue(System.Windows.Automation.AutomationProperties.NameProperty, "Stop spoken response");
                WriteEvent("voice_output", "reply_started", 0);
                activeVoicePrompt = voiceSpeaker.SpeakAsync(spoken);
            }
            catch (Exception ex)
            {
                WriteEvent("voice_output", "reply_failed", 0);
                StopSpeaking();
                ShowError("Read aloud unavailable", ex.Message);
            }
        }

        private void VoiceSpeakCompleted(object sender, SpeakCompletedEventArgs args)
        {
            window.Dispatcher.BeginInvoke(new Action(delegate
            {
                if (sender != voiceSpeaker) return;
                if (args.Prompt == wakeGreetingPrompt)
                {
                    wakeGreetingPrompt = null;
                    voiceSpeaking = false;
                    WriteEvent("voice_output", args.Error == null && !args.Cancelled ? "greeting_completed" : "greeting_failed", 0);
                    if (args.Error != null)
                        UpdateTask("AUDIO ERROR", "Cypher recognized its name but Windows could not play the spoken acknowledgement. Check the selected sound output; speak your command now.");
                    if (!args.Cancelled && !paused && !closing && inputBox.IsEnabled)
                        StartVoiceInput(true);
                    return;
                }
                if (args.Prompt != activeVoicePrompt) return;
                activeVoicePrompt = null;
                voiceSpeaking = false;
                WriteEvent("voice_output", args.Error == null && !args.Cancelled ? "reply_completed" : "reply_failed", 0);
                if (args.Error != null)
                {
                    SetStatus("AUDIO ERROR", "#F2C66D");
                    UpdateTask("AUDIO ERROR", "The response is on screen, but Windows could not play it. Check the selected sound output and try READ ALOUD again.");
                }
                readAloudButton.Content = "READ ALOUD";
                readAloudButton.SetValue(System.Windows.Automation.AutomationProperties.NameProperty, "Read response aloud");
            }));
        }

        private void StopSpeaking()
        {
            activeVoicePrompt = null;
            wakeGreetingPrompt = null;
            if (voiceSpeaker != null) try { voiceSpeaker.SpeakAsyncCancelAll(); } catch { }
            voiceSpeaking = false;
            if (readAloudButton != null)
            {
                readAloudButton.Content = "READ ALOUD";
                readAloudButton.SetValue(System.Windows.Automation.AutomationProperties.NameProperty, "Read response aloud");
            }
        }

        private void DisposeVoice()
        {
            CancelVoiceInput();
            StopSpeaking();
            if (voiceSpeaker != null) try { voiceSpeaker.Dispose(); } catch { }
            voiceSpeaker = null;
            if (voiceTimer != null) voiceTimer.Stop();
        }
    }
}
