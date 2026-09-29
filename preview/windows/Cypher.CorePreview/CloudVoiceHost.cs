using System;
using System.Collections.Generic;
using System.Collections.Concurrent;
using System.Diagnostics;
using System.IO;
using System.Net.Http;
using System.Net.Http.Headers;
using System.Net.WebSockets;
using System.Security.Cryptography;
using System.Text;
using System.Text.RegularExpressions;
using System.Threading;
using System.Threading.Tasks;
using System.Web.Script.Serialization;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;

namespace Cypher.CorePreview
{
    internal sealed partial class CypherHost
    {
        private bool cloudAnswerActive;
        private bool cloudLiveUnavailable;
        private LiveCloudCapture cloudVoiceLive;
        private LiveCloudCapture activeCloudVoiceCapture;
        private CancellationTokenSource cloudAnswerCancellation;
        private readonly object cloudUsageGate = new object();
        private string CloudKeyPath { get { return Path.Combine(installRoot, "openai-cloud-key.dpapi"); } }
        private string CloudUsagePath { get { return Path.Combine(installRoot, "cloud-usage.json"); } }

        private bool CloudVoiceEnabled()
        {
            return string.Equals(GetSetting(ReadSettings(), "cloud_voice_enabled", "false"), "true", StringComparison.OrdinalIgnoreCase)
                && File.Exists(CloudKeyPath);
        }

        private string ReadCloudKey()
        {
            byte[] protectedBytes = Convert.FromBase64String(File.ReadAllText(CloudKeyPath, Encoding.ASCII).Trim());
            byte[] plain = ProtectedData.Unprotect(protectedBytes, null, DataProtectionScope.CurrentUser);
            try { return Encoding.UTF8.GetString(plain); }
            finally { Array.Clear(plain, 0, plain.Length); }
        }

        private static int LimitSetting(Dictionary<string, object> settings, string name, int fallback, int minimum, int maximum)
        {
            object raw;
            int value;
            if (settings.TryGetValue(name, out raw) && int.TryParse(Convert.ToString(raw), out value) && value >= minimum && value <= maximum)
                return value;
            return fallback;
        }

        private bool ReserveCloudUsage(int audioSeconds, bool answer)
        {
            lock (cloudUsageGate)
            {
                Dictionary<string, object> settings = ReadSettings();
                int audioLimit = LimitSetting(settings, "cloud_max_audio_seconds_per_day", 600, 60, 3600);
                int answerLimit = LimitSetting(settings, "cloud_max_answers_per_day", 30, 1, 200);
                string today = DateTime.UtcNow.ToString("yyyy-MM-dd");
                Dictionary<string, object> usage = new Dictionary<string, object>();
                if (File.Exists(CloudUsagePath))
                {
                    try { usage = HermesClient.AsDictionary(new JavaScriptSerializer().DeserializeObject(File.ReadAllText(CloudUsagePath, Encoding.UTF8))); }
                    catch { return false; } // fail closed if the ledger is unreadable
                }
                int usedAudio = 0, usedAnswers = 0;
                if (Convert.ToString(HermesClient.Get(usage, "date")) == today)
                {
                    int.TryParse(Convert.ToString(HermesClient.Get(usage, "audio_seconds")), out usedAudio);
                    int.TryParse(Convert.ToString(HermesClient.Get(usage, "answers")), out usedAnswers);
                    if (usedAudio < 0 || usedAnswers < 0) return false;
                }
                if (usedAudio + audioSeconds > audioLimit || usedAnswers + (answer ? 1 : 0) > answerLimit) return false;
                usage["date"] = today;
                usage["audio_seconds"] = usedAudio + audioSeconds;
                usage["answers"] = usedAnswers + (answer ? 1 : 0);
                File.WriteAllText(CloudUsagePath, new JavaScriptSerializer().Serialize(usage), new UTF8Encoding(false));
                return true;
            }
        }

        private string TranscribeVoice(byte[] wave, int epoch, int preRollFrames, LiveCloudCapture live = null)
        {
            Stopwatch latency = Stopwatch.StartNew();
            if (live != null)
            {
                try
                {
                    string text = live.Result.GetAwaiter().GetResult();
                    if (epoch != voiceEpoch) throw new OperationCanceledException();
                    WriteEvent("cloud_voice", "transcribed_live", 0);
                    WriteEvent("voice_latency", "speech_to_transcript_cloud", (int)latency.ElapsedMilliseconds);
                    return text;
                }
                catch (OperationCanceledException) { throw; }
                catch
                {
                    WriteEvent("cloud_voice", "local_fallback", 0);
                    Ui(delegate { SetStatus("LOCAL FALLBACK", "#F2C66D"); UpdateTask("LOCAL FALLBACK", "Cloud transcription was unavailable. Retrying with the local voice model."); });
                }
                finally { live.Dispose(); }
            }
            else if (preRollFrames == 0 && CloudVoiceEnabled())
            {
                int rate = wave.Length >= 44 ? BitConverter.ToInt32(wave, 24) : 0;
                int seconds = rate > 0 ? Math.Max(1, (int)Math.Ceiling((wave.Length - 44 - preRollFrames * 2.0) / (rate * 2.0))) : 20;
                if (ReserveCloudUsage(seconds, false))
                {
                    try
                    {
                        Ui(delegate { SetStatus("CLOUD AUDIO", "#83E7FF"); UpdateTask("CLOUD AUDIO", "Only the command audio is being sent for transcription. Local wake detection and action approvals remain on this PC."); });
                        string text = TranscribeCloud(wave, preRollFrames);
                        if (epoch != voiceEpoch) throw new OperationCanceledException();
                        WriteEvent("cloud_voice", "transcribed", 0);
                        WriteEvent("voice_latency", "speech_to_transcript_cloud", (int)latency.ElapsedMilliseconds);
                        return text;
                    }
                    catch (OperationCanceledException) { throw; }
                    catch
                    {
                        WriteEvent("cloud_voice", "local_fallback", 0);
                        Ui(delegate { SetStatus("LOCAL FALLBACK", "#F2C66D"); UpdateTask("LOCAL FALLBACK", "Cloud transcription was unavailable. Retrying with the local voice model."); });
                    }
                }
                else WriteEvent("cloud_voice", "limit_fallback", 0);
            }
            string local = RunVoiceWorker(wave, epoch);
            WriteEvent("voice_latency", "speech_to_transcript_local", (int)latency.ElapsedMilliseconds);
            return local;
        }

        private void FeedCloudVoiceChunk(string encoded)
        {
            if (cloudLiveUnavailable) return;
            try
            {
                byte[] chunk = Convert.FromBase64String(encoded);
                if (chunk.Length != 1280 * 2) throw new InvalidOperationException("Invalid command audio chunk.");
                if (cloudVoiceLive == null)
                {
                    if (!CloudVoiceEnabled() || !ReserveCloudUsage(12, false))
                    {
                        cloudLiveUnavailable = true;
                        WriteEvent("cloud_voice", "limit_fallback", 0);
                        return;
                    }
                    cloudVoiceLive = new LiveCloudCapture(ReadCloudKey());
                    Ui(delegate
                    {
                        SetStatus("CLOUD AUDIO", "#83E7FF");
                        UpdateTask("CLOUD AUDIO", "Sending only post-wake command audio. Local wake detection and action approvals remain on this PC.");
                    });
                }
                if (!cloudVoiceLive.Add(chunk))
                {
                    cloudVoiceLive.Dispose();
                    cloudVoiceLive = null;
                    cloudLiveUnavailable = true;
                    WriteEvent("cloud_voice", "queue_fallback", 0);
                }
            }
            catch
            {
                if (cloudVoiceLive != null) { cloudVoiceLive.Dispose(); cloudVoiceLive = null; }
                cloudLiveUnavailable = true;
                WriteEvent("cloud_voice", "stream_fallback", 0);
            }
        }

        private sealed class LiveCloudCapture : IDisposable
        {
            private readonly BlockingCollection<byte[]> chunks = new BlockingCollection<byte[]>(160);
            private readonly CancellationTokenSource deadline = new CancellationTokenSource(TimeSpan.FromSeconds(40));
            private int disposed;
            internal Task<string> Result { get; private set; }

            internal LiveCloudCapture(string key)
            {
                Result = Task.Run(delegate
                {
                    using (ClientWebSocket socket = new ClientWebSocket())
                    {
                        socket.Options.SetRequestHeader("Authorization", "Bearer " + key);
                        socket.ConnectAsync(new Uri("wss://api.openai.com/v1/realtime?model=gpt-live-transcribe"), deadline.Token).GetAwaiter().GetResult();
                        SendCloudEvent(socket, "{\"type\":\"session.update\",\"session\":{\"type\":\"transcription\",\"audio\":{\"input\":{\"format\":{\"type\":\"audio/pcm\",\"rate\":24000},\"transcription\":{\"model\":\"gpt-live-transcribe\",\"delay\":\"low\"},\"turn_detection\":null}}}}", deadline.Token);
                        foreach (byte[] chunk in chunks.GetConsumingEnumerable(deadline.Token))
                        {
                            byte[] wave = VoiceCapture.BuildWave(chunk, 16000);
                            byte[] pcm = Pcm24k(wave, 0);
                            SendCloudEvent(socket, "{\"type\":\"input_audio_buffer.append\",\"audio\":\"" + Convert.ToBase64String(pcm) + "\"}", deadline.Token);
                        }
                        SendCloudEvent(socket, "{\"type\":\"input_audio_buffer.commit\"}", deadline.Token);
                        for (int events = 0; events < 80; events++)
                        {
                            Dictionary<string, object> item = ReceiveCloudEvent(socket, deadline.Token);
                            string type = Convert.ToString(HermesClient.Get(item, "type"));
                            if (type == "error") throw new InvalidOperationException("Cloud transcription rejected the request.");
                            if (type == "conversation.item.input_audio_transcription.completed")
                            {
                                string transcript = Convert.ToString(HermesClient.Get(item, "transcript")) ?? "";
                                if (transcript.Length > 1200) throw new InvalidOperationException("Cloud transcript was too long.");
                                return transcript.Trim();
                            }
                        }
                        throw new TimeoutException("Cloud transcription did not finish.");
                    }
                });
            }

            internal bool Add(byte[] pcm)
            {
                return !chunks.IsAddingCompleted && chunks.TryAdd(pcm);
            }

            internal void Complete()
            {
                if (!chunks.IsAddingCompleted) chunks.CompleteAdding();
            }

            public void Dispose()
            {
                if (Interlocked.Exchange(ref disposed, 1) != 0) return;
                Complete();
                deadline.Cancel();
            }
        }

        private static byte[] Pcm24k(byte[] wave, int skipFrames)
        {
            if (wave == null || wave.Length < 44 || Encoding.ASCII.GetString(wave, 0, 4) != "RIFF" ||
                Encoding.ASCII.GetString(wave, 8, 4) != "WAVE" || BitConverter.ToInt16(wave, 22) != 1 ||
                BitConverter.ToInt16(wave, 34) != 16) throw new InvalidOperationException("Invalid voice recording.");
            int rate = BitConverter.ToInt32(wave, 24);
            if (rate != 16000 && rate != 48000) throw new InvalidOperationException("Unsupported voice sample rate.");
            int available = (wave.Length - 44) / 2;
            if (skipFrames < 0 || skipFrames >= available) throw new InvalidOperationException("No post-wake audio to transcribe.");
            int sourceFrames = available - skipFrames;
            int targetFrames = (int)((long)sourceFrames * 24000 / rate);
            byte[] output = new byte[targetFrames * 2];
            for (int index = 0; index < targetFrames; index++)
            {
                double source = (double)index * rate / 24000;
                int left = Math.Min(sourceFrames - 1, (int)source);
                int right = Math.Min(sourceFrames - 1, left + 1);
                short a = BitConverter.ToInt16(wave, 44 + (skipFrames + left) * 2);
                short b = BitConverter.ToInt16(wave, 44 + (skipFrames + right) * 2);
                short value = (short)Math.Round(a + (b - a) * (source - left));
                output[index * 2] = (byte)value;
                output[index * 2 + 1] = (byte)(value >> 8);
            }
            return output;
        }

        private static void SendCloudEvent(ClientWebSocket socket, string value, CancellationToken token)
        {
            byte[] bytes = Encoding.UTF8.GetBytes(value);
            socket.SendAsync(new ArraySegment<byte>(bytes), WebSocketMessageType.Text, true, token).GetAwaiter().GetResult();
        }

        private static Dictionary<string, object> ReceiveCloudEvent(ClientWebSocket socket, CancellationToken token)
        {
            using (MemoryStream stream = new MemoryStream())
            {
                byte[] buffer = new byte[8192];
                WebSocketReceiveResult result;
                do
                {
                    result = socket.ReceiveAsync(new ArraySegment<byte>(buffer), token).GetAwaiter().GetResult();
                    if (result.MessageType == WebSocketMessageType.Close || stream.Length + result.Count > 65536)
                        throw new InvalidOperationException("Cloud transcription connection ended.");
                    stream.Write(buffer, 0, result.Count);
                } while (!result.EndOfMessage);
                return HermesClient.AsDictionary(new JavaScriptSerializer().DeserializeObject(Encoding.UTF8.GetString(stream.ToArray())));
            }
        }

        private string TranscribeCloud(byte[] wave, int skipFrames)
        {
            byte[] pcm = Pcm24k(wave, skipFrames);
            string key = ReadCloudKey();
            using (CancellationTokenSource deadline = new CancellationTokenSource(TimeSpan.FromSeconds(35)))
            using (ClientWebSocket socket = new ClientWebSocket())
            {
                socket.Options.SetRequestHeader("Authorization", "Bearer " + key);
                socket.ConnectAsync(new Uri("wss://api.openai.com/v1/realtime?model=gpt-live-transcribe"), deadline.Token).GetAwaiter().GetResult();
                SendCloudEvent(socket, "{\"type\":\"session.update\",\"session\":{\"type\":\"transcription\",\"audio\":{\"input\":{\"format\":{\"type\":\"audio/pcm\",\"rate\":24000},\"transcription\":{\"model\":\"gpt-live-transcribe\",\"delay\":\"low\",\"keywords\":[\"Cypher\"]},\"turn_detection\":null}}}}", deadline.Token);
                for (int offset = 0; offset < pcm.Length; offset += 9600)
                {
                    int count = Math.Min(9600, pcm.Length - offset);
                    string chunk = Convert.ToBase64String(pcm, offset, count);
                    SendCloudEvent(socket, "{\"type\":\"input_audio_buffer.append\",\"audio\":\"" + chunk + "\"}", deadline.Token);
                }
                SendCloudEvent(socket, "{\"type\":\"input_audio_buffer.commit\"}", deadline.Token);
                for (int events = 0; events < 80; events++)
                {
                    Dictionary<string, object> item = ReceiveCloudEvent(socket, deadline.Token);
                    string type = Convert.ToString(HermesClient.Get(item, "type"));
                    if (type == "error") throw new InvalidOperationException("Cloud transcription rejected the request.");
                    if (type == "conversation.item.input_audio_transcription.completed")
                    {
                        string transcript = Convert.ToString(HermesClient.Get(item, "transcript")) ?? "";
                        if (transcript.Length > 1200) throw new InvalidOperationException("Cloud transcript was too long.");
                        return transcript.Trim();
                    }
                }
                throw new TimeoutException("Cloud transcription did not finish.");
            }
        }

        private static bool CloudQuestion(string request)
        {
            string text = (request ?? "").Trim();
            if (text.Length == 0 || text.Length > 500) return false;
            if (!Regex.IsMatch(text, @"^(?:what|who|why|when|where|how|explain|tell me about)\b", RegexOptions.IgnoreCase)) return false;
            return !Regex.IsMatch(text, @"\b(?:open|launch|click|type|write|send|delete|move|copy|save|install|search|browse|read|summarize|compare|remind|schedule|file|folder|screen|window|browser|app)\b", RegexOptions.IgnoreCase);
        }

        internal static bool CloudVoiceSelfTest()
        {
            byte[] wave = VoiceCapture.BuildWave(new byte[32000], 16000);
            byte[] postWake = Pcm24k(wave, 8000);
            return postWake.Length == 24000 && CloudQuestion("What is gravity?") &&
                !CloudQuestion("Open Brave") && !CloudQuestion("How do I delete a file?");
        }

        private bool TryBeginCloudAnswer(string request)
        {
            if (!CloudVoiceEnabled() || !CloudQuestion(request) || !ReserveCloudUsage(0, true)) return false;
            cloudAnswerActive = true;
            cloudAnswerCancellation = new CancellationTokenSource(TimeSpan.FromSeconds(30));
            CancellationTokenSource owned = cloudAnswerCancellation;
            inputBox.Clear();
            SetInteractive(false);
            SetStatus("CLOUD ANSWER", "#83E7FF");
            UpdateTask("CLOUD ANSWER", "Sending this question to GPT-6 Luna without tools or PC access. Charges and daily limits apply.");
            WriteEvent("cloud_answer", "started", 0);
            Task.Run(async delegate
            {
                string reply = null;
                try { reply = await GetCloudAnswer(request, owned.Token).ConfigureAwait(false); }
                catch { WriteEvent("cloud_answer", "failed", 0); }
                Ui(delegate
                {
                    if (cloudAnswerCancellation != owned) return;
                    cloudAnswerActive = false;
                    cloudAnswerCancellation = null;
                    owned.Dispose();
                    if (reply == null)
                    {
                        inputBox.Text = request; // retain the request for the local route
                        SetStatus("LOCAL READY", "#F2C66D");
                        UpdateTask("LOCAL READY", "Cloud answer unavailable. Your question is back in the input box; press Send to use the local model.");
                    }
                    else
                    {
                        responseBox.Text = "YOUR REQUEST\r\n" + request + "\r\n\r\nCYPHER\r\n" + reply;
                        lastResponse = reply;
                        SetStatus("READY", "#4DE3C1");
                        UpdateTask("COMPLETED", "No-tool cloud answer completed. No Windows or file action was available to the cloud model.");
                        WriteEvent("cloud_answer", "completed", 0);
                    }
                    SetInteractive(true);
                    MaybeSpeakWakeReply();
                });
            });
            return true;
        }

        private async Task<string> GetCloudAnswer(string request, CancellationToken token)
        {
            using (HttpClient client = new HttpClient())
            using (HttpRequestMessage message = new HttpRequestMessage(HttpMethod.Post, "https://api.openai.com/v1/responses"))
            {
                client.Timeout = TimeSpan.FromSeconds(28);
                message.Headers.Authorization = new AuthenticationHeaderValue("Bearer", ReadCloudKey());
                var payload = new Dictionary<string, object>();
                payload["model"] = "gpt-6-luna";
                payload["store"] = false;
                payload["tools"] = new object[0];
                payload["max_output_tokens"] = 450;
                payload["reasoning"] = new Dictionary<string, object> { { "effort", "none" } };
                payload["instructions"] = "You are Cypher. Give a concise answer to the user's general question. You have no tools or access to their PC. Never claim to have performed an action or inspected a device.";
                payload["input"] = request;
                message.Content = new StringContent(new JavaScriptSerializer().Serialize(payload), Encoding.UTF8, "application/json");
                using (HttpResponseMessage response = await client.SendAsync(message, token).ConfigureAwait(false))
                {
                    if (!response.IsSuccessStatusCode) throw new InvalidOperationException("Cloud answer failed.");
                    string body = await response.Content.ReadAsStringAsync().ConfigureAwait(false);
                    if (body.Length > 100000) throw new InvalidOperationException("Cloud answer was too large.");
                    Dictionary<string, object> document = HermesClient.AsDictionary(new JavaScriptSerializer().DeserializeObject(body));
                    object output;
                    if (!document.TryGetValue("output", out output) || !(output is object[])) throw new InvalidOperationException("Cloud answer was invalid.");
                    foreach (object item in (object[])output)
                    {
                        Dictionary<string, object> entry = item as Dictionary<string, object>;
                        object content;
                        if (entry == null || !entry.TryGetValue("content", out content) || !(content is object[])) continue;
                        foreach (object block in (object[])content)
                        {
                            Dictionary<string, object> part = block as Dictionary<string, object>;
                            if (part == null || Convert.ToString(HermesClient.Get(part, "type")) != "output_text") continue;
                            string answer = Convert.ToString(HermesClient.Get(part, "text")) ?? "";
                            if (answer.Length > 0 && answer.Length <= 4000) return answer.Trim();
                        }
                    }
                    throw new InvalidOperationException("Cloud answer was empty.");
                }
            }
        }

        private void CancelCloudAnswer()
        {
            if (!cloudAnswerActive) return;
            cloudAnswerActive = false;
            CancellationTokenSource current = cloudAnswerCancellation;
            cloudAnswerCancellation = null;
            if (current != null) current.Cancel();
            SetInteractive(true);
            SetStatus("CANCELLED", "#F2C66D");
            UpdateTask("CANCELLED", "Cloud answer stopped. No action was available to the cloud model.");
            WriteEvent("cloud_answer", "cancelled", 0);
        }

        private void ShowCloudVoiceSetup()
        {
            Dictionary<string, object> settings = ReadSettings();
            Window dialog = new Window { Title = "Cypher cloud voice", Width = 470, Height = 500,
                WindowStartupLocation = WindowStartupLocation.CenterScreen, ResizeMode = ResizeMode.NoResize,
                Background = new SolidColorBrush(Color.FromRgb(20, 20, 20)), Foreground = Brushes.White };
            StackPanel panel = new StackPanel { Margin = new Thickness(22) };
            dialog.Content = panel;
            panel.Children.Add(new TextBlock { Text = "OPTIONAL CLOUD VOICE", FontSize = 18, Margin = new Thickness(0, 0, 0, 14) });
            panel.Children.Add(new TextBlock { Text = "Wake detection stays on your PC. Only post-wake command audio and eligible question text go to OpenAI. API use has usage-based charges; these local limits are not an account billing cap. OpenAI says API data is not used for training by default; standard abuse-monitoring retention can still apply for up to 30 days.", TextWrapping = TextWrapping.Wrap, Margin = new Thickness(0, 0, 0, 15) });
            CheckBox enabled = new CheckBox { Content = "Enable cloud voice and fast no-tool answers", IsChecked = CloudVoiceEnabled(), Margin = new Thickness(0, 0, 0, 12) };
            panel.Children.Add(enabled);
            panel.Children.Add(new TextBlock { Text = "OpenAI API key (leave blank to keep saved key)" });
            PasswordBox keyBox = new PasswordBox { Margin = new Thickness(0, 4, 0, 12) };
            panel.Children.Add(keyBox);
            panel.Children.Add(new TextBlock { Text = "Daily audio limit in seconds (60–3600)" });
            TextBox audioLimit = new TextBox { Text = GetSetting(settings, "cloud_max_audio_seconds_per_day", "600"), Margin = new Thickness(0, 4, 0, 12) };
            panel.Children.Add(audioLimit);
            panel.Children.Add(new TextBlock { Text = "Daily no-tool answer limit (1–200)" });
            TextBox answerLimit = new TextBox { Text = GetSetting(settings, "cloud_max_answers_per_day", "30"), Margin = new Thickness(0, 4, 0, 12) };
            panel.Children.Add(answerLimit);
            CheckBox consent = new CheckBox { Content = "I understand the data sharing, retention, and charges above", Margin = new Thickness(0, 0, 0, 16) };
            panel.Children.Add(consent);
            Button save = new Button { Content = "SAVE CLOUD SETTINGS", Height = 34 };
            panel.Children.Add(save);
            save.Click += delegate
            {
                int seconds, answers;
                if (!int.TryParse(audioLimit.Text, out seconds) || seconds < 60 || seconds > 3600 ||
                    !int.TryParse(answerLimit.Text, out answers) || answers < 1 || answers > 200 ||
                    (enabled.IsChecked == true && (consent.IsChecked != true || (keyBox.Password.Length == 0 && !File.Exists(CloudKeyPath)))))
                {
                    MessageBox.Show(dialog, "Check the limits, key, and consent before enabling cloud mode.", "Cypher cloud voice");
                    return;
                }
                try
                {
                    if (keyBox.Password.Length > 0)
                    {
                        string key = keyBox.Password.Trim();
                        if (!key.StartsWith("sk-", StringComparison.Ordinal) || key.Length > 256) throw new InvalidOperationException("Enter a valid OpenAI API key.");
                        byte[] plain = Encoding.UTF8.GetBytes(key);
                        try { File.WriteAllText(CloudKeyPath, Convert.ToBase64String(ProtectedData.Protect(plain, null, DataProtectionScope.CurrentUser)), Encoding.ASCII); }
                        finally { Array.Clear(plain, 0, plain.Length); }
                        keyBox.Clear();
                    }
                    settings["cloud_voice_enabled"] = enabled.IsChecked == true;
                    settings["cloud_max_audio_seconds_per_day"] = seconds;
                    settings["cloud_max_answers_per_day"] = answers;
                    string pending = configPath + ".pending";
                    File.WriteAllText(pending, new JavaScriptSerializer().Serialize(settings), new UTF8Encoding(false));
                    File.Replace(pending, configPath, null);
                    if (!voiceListening && !voiceStopping && !cloudAnswerActive)
                    {
                        StopWakeListening();
                        TryStartWakeListening();
                    }
                    WriteEvent("cloud_voice", enabled.IsChecked == true ? "enabled" : "disabled", 0);
                    dialog.Close();
                }
                catch { MessageBox.Show(dialog, "Cloud settings could not be saved. Existing settings were kept.", "Cypher cloud voice"); }
            };
            dialog.ShowDialog();
        }
    }
}
