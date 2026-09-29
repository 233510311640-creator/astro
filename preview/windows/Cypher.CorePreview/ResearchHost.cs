using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Runtime.InteropServices;
using System.Security.Cryptography;
using System.Text;
using System.Text.RegularExpressions;
using System.Threading;
using System.Threading.Tasks;
using System.Web.Script.Serialization;
using System.Windows.Threading;

namespace Cypher.CorePreview
{
    internal sealed class ResearchWorkerFault : Exception
    {
        public readonly string Code;
        public ResearchWorkerFault(string code) : base(code) { Code = code; }
    }

    internal sealed class ResearchTranscript
    {
        public const string WorkerSha256 = "9954dd3c37ba5a6553782769a143f4791410174bfc5e9aec9d4e1f84b0b43261";
        private readonly string nonce;
        private readonly JavaScriptSerializer json = new JavaScriptSerializer { MaxJsonLength = 524288, RecursionLimit = 24 };
        private int frames;
        private int observedSources;
        private int progressOrder;
        public Dictionary<string, object> Result { get; private set; }

        public ResearchTranscript(string requestNonce) { nonce = requestNonce; }
        public static bool IsRequest(string input)
        { return Regex.IsMatch(input ?? "", @"^\s*(?:Research(?:\s+papers)?|Web)\s*:", RegexOptions.IgnoreCase | RegexOptions.CultureInvariant); }
        public static bool IsPapersRequest(string input)
        { return Regex.IsMatch(input ?? "", @"^\s*Research\s+papers\s*:", RegexOptions.IgnoreCase | RegexOptions.CultureInvariant); }
        public static bool IsWebReadRequest(string input)
        { return Regex.IsMatch(input ?? "", @"^\s*Web\s*:\s*(?:read|preview)\s+https://\S+\s*$", RegexOptions.IgnoreCase | RegexOptions.CultureInvariant); }
        public static bool IsWebLinksRequest(string input)
        { return Regex.IsMatch(input ?? "", @"^\s*Web\s*:\s*(?:links|map)\s+https://\S+\s*$", RegexOptions.IgnoreCase | RegexOptions.CultureInvariant); }
        public static bool IsWebFollowRequest(string input)
        { return Regex.IsMatch(input ?? "", @"^\s*Web\s*:\s*follow\s+https://\S+\s+:\s*[1-6]\s*$", RegexOptions.IgnoreCase | RegexOptions.CultureInvariant); }
        public static bool IsWebFormsRequest(string input)
        { return Regex.IsMatch(input ?? "", @"^\s*Web\s*:\s*forms\s+https://\S+\s*$", RegexOptions.IgnoreCase | RegexOptions.CultureInvariant); }
        public static bool IsWebSearchRequest(string input)
        { return Regex.IsMatch(input ?? "", @"^\s*Web\s*:\s*search\s+https://\S+\s+:\s*\S[\s\S]*$", RegexOptions.IgnoreCase | RegexOptions.CultureInvariant); }
        public static bool IsWebAskRequest(string input)
        { return Regex.IsMatch(input ?? "", @"^\s*Web\s*:\s*ask\s+https://\S+\s+:\s*\S[\s\S]*$", RegexOptions.IgnoreCase | RegexOptions.CultureInvariant); }

        private static int Count(Dictionary<string, object> frame, string key, int maximum)
        {
            object value;
            if (!frame.TryGetValue(key, out value) || !(value is int) || (int)value < 0 || (int)value > maximum)
                throw new ResearchWorkerFault("INVALID_WORKER_RESULT");
            return (int)value;
        }

        public void Accept(string line, Action<string, int> progress)
        {
            if (Result != null || ++frames > 16 || line.Length > 524288) throw new ResearchWorkerFault("INVALID_WORKER_RESULT");
            Dictionary<string, object> frame;
            try { frame = json.DeserializeObject(line) as Dictionary<string, object>; }
            catch { throw new ResearchWorkerFault("INVALID_WORKER_RESULT"); }
            if (frame == null) throw new ResearchWorkerFault("INVALID_WORKER_RESULT");
            object kind;
            if (!frame.TryGetValue("type", out kind) || !(kind is string)) throw new ResearchWorkerFault("INVALID_WORKER_RESULT");
            int sources = Count(frame, "sources", 5);
            if ((string)kind == "progress")
            {
                object phase;
                if (frame.Count != 3 || !frame.TryGetValue("phase", out phase) || !(phase is string))
                    throw new ResearchWorkerFault("INVALID_WORKER_RESULT");
                string name = (string)phase;
                int order = name == "DISCOVERING" ? 1 : name == "READING" ? 2 : name == "SUMMARIZING" ? 3 : 0;
                if (order == 0 || order < progressOrder || sources < observedSources ||
                    (name == "DISCOVERING" && (progressOrder != 0 || sources != 0)) ||
                    (name == "SUMMARIZING" && sources == 0)) throw new ResearchWorkerFault("INVALID_WORKER_RESULT");
                observedSources = sources;
                progressOrder = order;
                progress(name, sources);
                return;
            }
            object rawNonce, rawState, rawCode, rawText;
            if ((string)kind != "result" || frame.Count != 7 ||
                !frame.TryGetValue("nonce", out rawNonce) || !(rawNonce is string) || (string)rawNonce != nonce ||
                !frame.TryGetValue("state", out rawState) || !(rawState is string) ||
                !frame.TryGetValue("code", out rawCode) || !(rawCode is string) ||
                !frame.TryGetValue("text", out rawText) || !(rawText is string)) throw new ResearchWorkerFault("INVALID_WORKER_RESULT");
            string state = (string)rawState, code = (string)rawCode, text = (string)rawText;
            int findings = Count(frame, "findings", 6);
            if (!Regex.IsMatch(code, @"^[A-Z_]{1,64}$") || text.Length == 0 || text.Length > 80000 ||
                (state != "COMPLETED" && state != "PARTIAL" && state != "FAILED" && state != "REJECTED") ||
                (state == "COMPLETED" && (sources == 0 || findings == 0 || code != "OK")) ||
                (state == "PARTIAL" && sources == 0) ||
                ((state == "FAILED" || state == "REJECTED") && (sources != 0 || findings != 0 || code == "OK")) ||
                (state != "REJECTED" && sources < observedSources)) throw new ResearchWorkerFault("INVALID_WORKER_RESULT");
            Result = frame;
        }

        public static int SelfTest()
        {
            string id = new string('a', 32);
            JavaScriptSerializer serializer = new JavaScriptSerializer();
            Dictionary<string, object> valid = new Dictionary<string, object>
            { { "type", "result" }, { "nonce", id }, { "state", "COMPLETED" }, { "code", "OK" }, { "sources", 1 }, { "findings", 1 }, { "text", "A cited finding. [S1]" } };
            try
            {
                if (!IsRequest("Research: question\nhttps://example.org") || !IsRequest("Research papers: question") ||
                    !IsRequest("Web: read https://example.org/") || !IsWebReadRequest("Web: preview https://example.org/") ||
                    !IsWebLinksRequest("Web: links https://example.org/") || IsWebLinksRequest("Web: links http://example.org/") ||
                    !IsWebFollowRequest("Web: follow https://example.org/ : 1") || IsWebFollowRequest("Web: follow https://example.org/ : 7") ||
                    !IsWebFormsRequest("Web: forms https://example.org/") || IsWebFormsRequest("Web: forms http://example.org/") ||
                    !IsWebSearchRequest("Web: search https://example.org/ : chess") || IsWebSearchRequest("Web: search https://example.org/ : ") ||
                    !IsWebAskRequest("Web: ask https://example.org/ : What is this page?") ||
                    IsWebAskRequest("Web: ask https://example.org/ : ") ||
                    !IsPapersRequest("Research papers: question") || IsPapersRequest("Research: papers") ||
                    IsRequest("Please research later")) return 150;
                ResearchTranscript transcript = new ResearchTranscript(id);
                transcript.Accept("{\"type\":\"progress\",\"phase\":\"DISCOVERING\",\"sources\":0}", delegate { });
                transcript.Accept("{\"type\":\"progress\",\"phase\":\"READING\",\"sources\":0}", delegate { });
                transcript.Accept(serializer.Serialize(valid), delegate { });
                if (transcript.Result == null) return 151;
                try { transcript.Accept(serializer.Serialize(valid), delegate { }); return 152; } catch (ResearchWorkerFault) { }
                valid["nonce"] = new string('b', 32);
                try { new ResearchTranscript(id).Accept(serializer.Serialize(valid), delegate { }); return 153; } catch (ResearchWorkerFault) { }
                valid["nonce"] = id; valid["sources"] = 0;
                try { new ResearchTranscript(id).Accept(serializer.Serialize(valid), delegate { }); return 154; } catch (ResearchWorkerFault) { }
                valid["sources"] = 1; valid["tool_calls"] = "not permitted";
                try { new ResearchTranscript(id).Accept(serializer.Serialize(valid), delegate { }); return 155; } catch (ResearchWorkerFault) { }
                valid.Remove("tool_calls"); valid["text"] = new string('x', 80001);
                try { new ResearchTranscript(id).Accept(serializer.Serialize(valid), delegate { }); return 156; } catch (ResearchWorkerFault) { }
                transcript = new ResearchTranscript(id);
                transcript.Accept("{\"type\":\"progress\",\"phase\":\"SUMMARIZING\",\"sources\":2}", delegate { });
                try { transcript.Accept("{\"type\":\"progress\",\"phase\":\"DISCOVERING\",\"sources\":2}", delegate { }); return 157; } catch (ResearchWorkerFault) { }
                // A passage preflight may end normally before any synthesis phase.
                transcript = new ResearchTranscript(id);
                transcript.Accept("{\"type\":\"progress\",\"phase\":\"DISCOVERING\",\"sources\":0}", delegate { });
                Dictionary<string, object> noPassage = new Dictionary<string, object>
                { { "type", "result" }, { "nonce", id }, { "state", "PARTIAL" },
                  { "code", "PAPERS_DIRECT_PASSAGE_MISSING" }, { "sources", 2 },
                  { "findings", 0 }, { "text", "No bounded passage passed; synthesis was skipped." } };
                transcript.Accept(serializer.Serialize(noPassage), delegate { });
                if (transcript.Result == null) return 159;
                return 0;
            }
            catch { return 158; }
        }
    }

    internal sealed class OwnedResearchWorker : IDisposable
    {
        private const uint JobObjectUiLimitHandles = 0x00000001U;
        private const uint JobObjectUiLimitReadClipboard = 0x00000002U;
        private const uint JobObjectUiLimitWriteClipboard = 0x00000004U;
        private const uint JobObjectUiLimitSystemParameters = 0x00000008U;
        private const uint JobObjectUiLimitDisplaySettings = 0x00000010U;
        private const uint JobObjectUiLimitGlobalAtoms = 0x00000020U;
        private const uint JobObjectUiLimitDesktop = 0x00000040U;
        private const uint JobObjectUiLimitExitWindows = 0x00000080U;
        private const uint ResearchUiRestrictions =
            JobObjectUiLimitHandles | JobObjectUiLimitReadClipboard | JobObjectUiLimitWriteClipboard |
            JobObjectUiLimitSystemParameters | JobObjectUiLimitDisplaySettings | JobObjectUiLimitGlobalAtoms |
            JobObjectUiLimitDesktop | JobObjectUiLimitExitWindows;

        [StructLayout(LayoutKind.Sequential)] private struct BasicLimits
        {
            public long PerProcessUserTimeLimit, PerJobUserTimeLimit;
            public uint LimitFlags;
            public UIntPtr MinimumWorkingSetSize, MaximumWorkingSetSize;
            public uint ActiveProcessLimit;
            public UIntPtr Affinity;
            public uint PriorityClass, SchedulingClass;
        }
        [StructLayout(LayoutKind.Sequential)] private struct IoCounters
        { public ulong ReadOperationCount, WriteOperationCount, OtherOperationCount, ReadTransferCount, WriteTransferCount, OtherTransferCount; }
        [StructLayout(LayoutKind.Sequential)] private struct ExtendedLimits
        {
            public BasicLimits Basic;
            public IoCounters Io;
            public UIntPtr ProcessMemoryLimit, JobMemoryLimit, PeakProcessMemoryUsed, PeakJobMemoryUsed;
        }
        [StructLayout(LayoutKind.Sequential)] private struct BasicUiRestrictions
        { public uint UiRestrictionsClass; }
        [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)] private static extern IntPtr CreateJobObject(IntPtr security, string name);
        [DllImport("kernel32.dll", EntryPoint = "SetInformationJobObject", SetLastError = true)] private static extern bool SetExtendedLimits(IntPtr job, int kind, ref ExtendedLimits info, uint length);
        [DllImport("kernel32.dll", EntryPoint = "SetInformationJobObject", SetLastError = true)] private static extern bool SetUiRestrictions(IntPtr job, int kind, ref BasicUiRestrictions info, uint length);
        [DllImport("kernel32.dll", EntryPoint = "QueryInformationJobObject", SetLastError = true)] private static extern bool QueryUiRestrictions(IntPtr job, int kind, ref BasicUiRestrictions info, uint length, IntPtr returnedLength);
        [DllImport("kernel32.dll", SetLastError = true)] private static extern bool AssignProcessToJobObject(IntPtr job, IntPtr process);
        [DllImport("kernel32.dll")] private static extern bool CloseHandle(IntPtr handle);

        private readonly object gate = new object();
        private Process process;
        private IntPtr job;
        private bool started;
        private bool stopRequested;
        public bool IsStopped
        {
            get { lock (gate) { try { return !started || process.HasExited; } catch { return false; } } }
        }

        public void RequestStop()
        {
            lock (gate)
            {
                stopRequested = true;
                // Only the process created by this instance can be terminated.
                if (job != IntPtr.Zero) { CloseHandle(job); job = IntPtr.Zero; }
                try { if (started && !process.HasExited) process.Kill(); } catch { }
            }
        }

        private void Start(string root, string python)
        {
            string worker = Path.Combine(root, "research_worker.py");
            if (!Path.IsPathRooted(python) || python.StartsWith(@"\\", StringComparison.Ordinal) ||
                !Regex.IsMatch(Path.GetFileName(python), @"^python(?:3(?:\.12)?)?\.exe$", RegexOptions.IgnoreCase) ||
                !File.Exists(python) || !File.Exists(worker)) throw new ResearchWorkerFault("WORKER_NOT_INSTALLED");
            using (SHA256 hash = SHA256.Create())
            using (FileStream stream = File.OpenRead(worker))
                if (BitConverter.ToString(hash.ComputeHash(stream)).Replace("-", "").ToLowerInvariant() != ResearchTranscript.WorkerSha256)
                    throw new ResearchWorkerFault("WORKER_HASH_CHANGED");
            if (worker.IndexOf('"') >= 0) throw new ResearchWorkerFault("WORKER_NOT_INSTALLED");
            ProcessStartInfo start = new ProcessStartInfo
            {
                FileName = python, Arguments = "-I -S -B -X utf8 \"" + worker + "\"", WorkingDirectory = root,
                UseShellExecute = false, CreateNoWindow = true, RedirectStandardInput = true,
                RedirectStandardOutput = true, RedirectStandardError = true,
                StandardOutputEncoding = Encoding.UTF8, StandardErrorEncoding = Encoding.UTF8
            };
            start.EnvironmentVariables.Clear();
            string windows = Environment.GetFolderPath(Environment.SpecialFolder.Windows);
            start.EnvironmentVariables["SystemRoot"] = windows;
            start.EnvironmentVariables["WINDIR"] = windows;
            lock (gate)
            {
                if (stopRequested) throw new OperationCanceledException();
                job = CreateJobObject(IntPtr.Zero, null);
                ExtendedLimits limits = new ExtendedLimits();
                // Kill our worker on host exit; no child processes; bounded worker memory.
                limits.Basic.LimitFlags = 0x2000 | 0x8 | 0x100;
                limits.Basic.ActiveProcessLimit = 1;
                limits.ProcessMemoryLimit = new UIntPtr(512U * 1024U * 1024U);
                if (job == IntPtr.Zero || !SetExtendedLimits(job, 9, ref limits, (uint)Marshal.SizeOf(typeof(ExtendedLimits))))
                    throw new ResearchWorkerFault("WORKER_JOB_UNAVAILABLE");
                BasicUiRestrictions ui = new BasicUiRestrictions { UiRestrictionsClass = ResearchUiRestrictions };
                BasicUiRestrictions verifiedUi = new BasicUiRestrictions();
                if (!SetUiRestrictions(job, 4, ref ui, (uint)Marshal.SizeOf(typeof(BasicUiRestrictions))) ||
                    !QueryUiRestrictions(job, 4, ref verifiedUi, (uint)Marshal.SizeOf(typeof(BasicUiRestrictions)), IntPtr.Zero) ||
                    verifiedUi.UiRestrictionsClass != ResearchUiRestrictions)
                    throw new ResearchWorkerFault("WORKER_UI_ISOLATION_UNAVAILABLE");
                process = new Process { StartInfo = start };
                if (!process.Start()) throw new ResearchWorkerFault("WORKER_START_FAILED");
                started = true;
                if (!AssignProcessToJobObject(job, process.Handle)) throw new ResearchWorkerFault("WORKER_JOB_UNAVAILABLE");
                // The script blocks on stdin until assignment is confirmed; no request was sent yet.
            }
        }

        private static void ReadFrames(StreamReader reader, ResearchTranscript transcript, Action<string, int> progress)
        {
            char[] buffer = new char[2048];
            StringBuilder line = new StringBuilder();
            int total = 0, count;
            while ((count = reader.Read(buffer, 0, buffer.Length)) != 0)
            {
                total += count;
                if (total > 600000) throw new ResearchWorkerFault("INVALID_WORKER_RESULT");
                for (int i = 0; i < count; i++)
                {
                    char value = buffer[i];
                    if (value == '\n') { transcript.Accept(line.ToString().TrimEnd('\r'), progress); line.Clear(); }
                    else line.Append(value);
                }
            }
            if (line.Length != 0 || transcript.Result == null) throw new ResearchWorkerFault("INVALID_WORKER_RESULT");
        }

        public Dictionary<string, object> Run(string root, string python, string input, string model,
            CancellationToken cancellation, Action<string, int> progress)
        {
            string nonce = Guid.NewGuid().ToString("N");
            ResearchTranscript transcript = new ResearchTranscript(nonce);
            Task<int> stderr = null;
            using (CancellationTokenSource timeout = CancellationTokenSource.CreateLinkedTokenSource(cancellation))
            {
                timeout.CancelAfter(TimeSpan.FromSeconds(180));
                try
                {
                    timeout.Token.ThrowIfCancellationRequested();
                    Start(root, python);
                    using (timeout.Token.Register(RequestStop))
                    {
                        timeout.Token.ThrowIfCancellationRequested();
                        StreamReader errorReader = process.StandardError;
                        stderr = Task.Run(delegate
                        {
                            int count, total = 0; char[] buffer = new char[1024];
                            try
                            {
                                while ((count = errorReader.Read(buffer, 0, buffer.Length)) != 0)
                                { total += count; if (total > 4096) { RequestStop(); break; } }
                            }
                            catch { return -1; }
                            return total; // Never retain or log stderr contents.
                        });
                        JavaScriptSerializer serializer = new JavaScriptSerializer();
                        string request = serializer.Serialize(new Dictionary<string, object> { { "input", input }, { "model", model }, { "nonce", nonce } });
                        byte[] bytes = Encoding.UTF8.GetBytes(request + "\n");
                        process.StandardInput.BaseStream.Write(bytes, 0, bytes.Length);
                        process.StandardInput.Close();
                        ReadFrames(process.StandardOutput, transcript, progress);
                        if (!process.WaitForExit(2000) || !stderr.Wait(2000) || stderr.Result != 0)
                            throw new ResearchWorkerFault("INVALID_WORKER_RESULT");
                        timeout.Token.ThrowIfCancellationRequested();
                        string state = (string)transcript.Result["state"];
                        if (process.ExitCode != 0 && !(process.ExitCode == 2 && state == "REJECTED"))
                            throw new ResearchWorkerFault("INVALID_WORKER_RESULT");
                        return transcript.Result;
                    }
                }
                catch (Exception)
                {
                    if (cancellation.IsCancellationRequested) throw new OperationCanceledException(cancellation);
                    if (timeout.IsCancellationRequested) throw new ResearchWorkerFault("RESEARCH_TIME_LIMIT");
                    throw;
                }
                finally
                {
                    RequestStop();
                    try { if (started) process.WaitForExit(2000); } catch { }
                    try { if (stderr != null) stderr.Wait(2000); } catch { }
                }
            }
        }

        public void Dispose()
        {
            RequestStop();
            lock (gate) { if (process != null && IsStopped) { process.Dispose(); process = null; started = false; } }
        }

        public static int SelfTest(string root, string python)
        {
            try
            {
                using (CancellationTokenSource deadline = new CancellationTokenSource(TimeSpan.FromSeconds(15)))
                using (OwnedResearchWorker worker = new OwnedResearchWorker())
                {
                    int events = 0;
                    Dictionary<string, object> result = worker.Run(root, python,
                        "Research: installer boundary check\nhttps://127.0.0.1/", Router.FastModel,
                        deadline.Token, delegate { events++; });
                    if ((string)result["state"] != "REJECTED" || (string)result["code"] != "URL_BLOCKED" ||
                        (int)result["sources"] != 0 || events != 0 || !worker.IsStopped) return 160;
                }
                using (OwnedResearchWorker worker = new OwnedResearchWorker())
                {
                    worker.RequestStop();
                    try
                    {
                        worker.Run(root, python, "Research: installer boundary check\nhttps://127.0.0.1/",
                            Router.FastModel, CancellationToken.None, delegate { });
                        return 161;
                    }
                    catch (OperationCanceledException) { if (!worker.IsStopped) return 162; }
                }
                return 0;
            }
            catch { return 163; }
        }
    }

    internal sealed partial class CypherHost
    {
        private volatile bool researchActive;
        private CancellationTokenSource researchCancellation;
        private OwnedResearchWorker researchWorker;
        private bool researchStopUnconfirmed;

        private void BeginResearch(string input)
        {
            if (input.Length > 16000) { ShowError("Read-only web input too long", "Use Web: links, Web: read or Web: forms followed by one public HTTPS URL, Web: follow URL : NUMBER for one mapped link, Web: search URL : QUERY for one same-site GET search, Web: ask URL : question for one grounded page answer, a short Research question, Research papers: question, or at most five public HTTPS URLs under Research:."); return; }
            string python;
            try { python = GetSetting(ReadSettings(), "research_python_path", ""); }
            catch { ShowError("Research settings unavailable", "Reinstall this research package to restore its local worker settings."); return; }
            string model = SelectedMode() == "deep" ? Router.DeepModel : Router.FastModel;
            researchActive = true;
            researchStopUnconfirmed = false;
            researchCancellation = new CancellationTokenSource();
            CancellationToken token = researchCancellation.Token;
            OwnedResearchWorker worker = new OwnedResearchWorker();
            researchWorker = worker;
            inputBox.Clear(); HideApproval(); SetInteractive(false);
            bool papers = ResearchTranscript.IsPapersRequest(input);
            bool webRead = ResearchTranscript.IsWebReadRequest(input);
            bool webLinks = ResearchTranscript.IsWebLinksRequest(input);
            bool webFollow = ResearchTranscript.IsWebFollowRequest(input);
            bool webForms = ResearchTranscript.IsWebFormsRequest(input);
            bool webSearch = ResearchTranscript.IsWebSearchRequest(input);
            bool webAsk = ResearchTranscript.IsWebAskRequest(input);
            modelText.Text = webSearch ? "ISOLATED · SITE SEARCH"
                : webForms ? "ISOLATED · FORM INSPECTION"
                : webFollow ? "ISOLATED · FOLLOW LINK"
                : webLinks ? "ISOLATED · SAFE LINK MAP"
                : webRead ? "ISOLATED · PUBLIC PAGE READ"
                : webAsk ? "LOCAL · GROUNDED PAGE ANSWER · " + (SelectedMode() == "deep" ? "DEEP" : "FAST")
                : (papers ? "SCHOLARLY RESEARCH · " : "READ-ONLY RESEARCH · ") + (SelectedMode() == "deep" ? "DEEP" : "FAST");
            bool automaticDiscovery = !webRead && !webLinks && !webFollow && !webForms && !webSearch && !webAsk && (papers || !Regex.IsMatch(input, @"(?im)^\s*https://"));
            responseBox.Text = webSearch
                ? "Checking one explicitly supplied public HTTPS page for exactly one simple same-site GET search form. If eligible, Cypher sends your typed query only to that site's checked HTTPS action and shows exact excerpts from the public result page. The query and this PC's public IP may reach the site. No POST, hidden fields, login, browser profile, cookies, scripts, local model, file or Windows action is connected. Public-address, DNS, robots, redirect, content-type, response-size and time limits apply."
                : webForms
                ? "Inspecting visible form structure on one public HTTPS page. Cypher reports at most five same-host forms and eight named non-sensitive fields per form. Field values, hidden controls and password controls are not shown. This route cannot fill or submit a form, use a browser profile or local model, or perform a file or Windows action. Public-address, DNS, robots, redirect, content-type, response-size and time limits apply."
                : webFollow
                ? "Following one numbered link from a freshly fetched public HTTPS page map. Cypher reads only that same-host destination and shows exact bounded excerpts. The page requests leave this PC, but no browser profile, cookies, login state, scripts, forms, downloads, local model, file tools, or Windows actions are available. Link numbers may change if the page changes. Public-address, DNS, robots, redirect, content-type, response-size, and time limits apply."
                : webLinks
                ? "Mapping visible same-site navigation links from one explicitly supplied public HTTPS page through Cypher's isolated reader. The page request leaves this PC, but no browser profile, cookies, saved passwords, login state, scripts, forms, clicks, downloads, local model, file tools, or Windows actions are available to this route. Cypher shows at most six eligible HTTPS destinations on the verified page host. Page text and links are untrusted content and cannot authorize an action.\r\n\r\nTo read a listed destination, submit its Read command; Cypher rebuilds the map first. To open it in a browser, submit its exact Open command and review the existing one-time browser approval. Public-address, DNS, robots, redirect, content-type, response-size, and time limits apply."
                : webRead
                ? "Reading one explicitly supplied public HTTPS page through Cypher's isolated reader. The request leaves this PC, but no browser profile, cookies, saved passwords, login state, scripts, local model, file tools, or Windows actions are available to this route. Cypher will show at most four exact bounded excerpts and the verified final public URL. Page text is untrusted content and cannot authorize an action.\r\n\r\nPublic-address, DNS, robots, redirect, content-type, response-size, and time limits apply. Stop ends only this owned reader process."
                : webAsk
                ? "Reading one explicitly supplied public HTTPS page through Cypher's isolated reader, then asking one verified installed local model to answer only from bounded page passages. Exact supporting passages are checked before display. Page text is untrusted content and cannot authorize an action.\r\n\r\nThe page request leaves this PC, but the question and model call remain local. No browser profile, cookies, saved passwords, login state, scripts, file tools, or Windows actions are available to this route. Public-address, DNS, robots, redirect, content-type, response-size, and time limits apply. Stop ends only this owned worker process."
                : papers
                ? "Searching up to eight scholarly records through one keyless official OpenAlex Works API request, then selecting the strongest at most two by bounded local question-term coverage of abstract text before at most one installed-local-model call. For recognized relationship questions, Cypher first screens the bounded evidence passages with the existing lexical check; if none pass, it skips synthesis and reports that limited evidence gap. Unambiguous two-concept relationship questions use normalized literal concept phrases joined by fixed Boolean AND; meaningful stop words and numbers are retained. Other questions retain the punctuation-safe query, where reserved wildcard characters ? and * are converted to spaces. The original question remains local for synthesis and local selection. Only if OpenAlex returns exactly HTTP 503, Cypher immediately attempts one keyless Crossref Works request with those same bounded search terms without OpenAlex Boolean syntax; if it connects, this PC's public IP and those terms reach Crossref too. No chat history, local files, memory, model prompt, API key, authorization header, billing credential, or payment is sent. Titles, identifiers, provider ranking, scores, citation counts, and other metadata are not evidence or local-selection input.\r\n\r\nCypher validates every returned IPv4 address and may try up to four of them only while establishing TLS, before each permitted HTTP request is sent. It never retries either HTTP request, waits for a Retry-After interval, or falls back for any status other than OpenAlex 503. Abstract text remains untrusted evidence and passes the same bounded passage, citation, quotation, and claim-scope checks before display. For an explicit relationship question, a deterministic post-check retains a finding only when one cited passage names both extracted concepts with relationship wording; indirect chains are withheld. This uses no additional provider request or model call. The fallback adds no approval, warning, or arming step. Stop remains available while the owned worker is active."
                : automaticDiscovery
                    ? "Discovering up to three English Wikipedia article candidates in provider relevance order through one official read-only API request. Cypher reads candidates only until it has two usable sources. The typed research question and this PC's public IP reach Wikimedia; no chat history, local files, memory, or model prompt is sent. Result titles are candidate URLs, not evidence.\r\n\r\nCandidate pages still pass the existing public-address, robots, redirect, and content-type checks. An oversized readable page contributes only its bounded 1 MiB prefix; the remaining body is not read. Stop ends this research worker; no approval countdown is added."
                    : "Reading the public HTTPS URLs you supplied. Page requests leave this PC; the question and model summary stay local. No browser login, scripts, file tools or Windows actions are used.\r\n\r\nStop ends this research worker; no approval countdown is added.";
            lastResponse = "";
            SetStatus(automaticDiscovery ? "DISCOVERING" : "READING", "#58CFF5");
            UpdateTask(automaticDiscovery ? "DISCOVERING" : "READING", webLinks
                ? "One isolated public page link map is memory-only; no browser session, page action, or model is connected."
                : webRead
                ? "One isolated public page preview is memory-only; no browser session or model is connected."
                : webAsk
                ? "One isolated public page answer is memory-only; one local model call has no browser, file, or action tools."
                : "Research state is memory-only; the previous workflow checkpoint is unchanged.");
            Task.Run(delegate
            {
                string state = "FAILED", message = "Research could not finish. No file or Windows action ran.", code = "RESEARCH_FAILED";
                try
                {
                    Dictionary<string, object> result = worker.Run(installRoot, python, input, model, token,
                        delegate(string phase, int sources)
                        {
                            window.Dispatcher.BeginInvoke(DispatcherPriority.Background, new Action(delegate
                            {
                                if (researchWorker != worker || !researchActive || token.IsCancellationRequested) return;
                                SetStatus(phase, "#58CFF5");
                                string detail = webSearch
                                    ? "A bounded same-site GET search is being checked or read; the typed query may be sent to that site, with no POST, browser profile, model or local action."
                                    : webForms
                                    ? "One public HTTPS page is being inspected for bounded visible form metadata; no values, model, browser profile, submission, or action is connected."
                                    : webFollow
                                    ? "One current numbered same-host link is being read through the isolated public HTTPS reader; no model, browser profile, form, click, or download is connected."
                                    : webLinks
                                    ? "One isolated public HTTPS page is being checked for at most six visible same-site navigation links; no model, browser profile, form, click, or download is connected."
                                    : webRead
                                    ? "One isolated public HTTPS page is being checked and converted to at most four exact bounded excerpts; no model or browser profile is connected."
                                    : webAsk
                                    ? phase == "SUMMARIZING"
                                        ? "One installed local model is answering from bounded passages; selected citations and exact source text will be checked before display."
                                        : "One isolated public HTTPS page is being checked; no browser profile, cookie, login, file, or action context is connected."
                                    : phase == "DISCOVERING"
                                    ? papers
                                        ? "OpenAlex receives focused concept phrases where unambiguous, otherwise punctuation-safe search terms; only its exact HTTP 503 permits one immediate keyless Crossref request. Neither request is retried; up to eight checked abstracts are ranked locally and at most two become evidence."
                                        : "One official Wikipedia API request receives only the typed question; candidates stay in relevance order and titles are not evidence."
                                    : phase == "SUMMARIZING"
                                        ? "The local model has no tools; citations will be checked before display."
                                        : "Checking public addresses, robots policy and bounded page text until two usable discovered sources are available.";
                                UpdateTask(phase, sources + " source(s) read. " + detail);
                            }));
                        });
                    token.ThrowIfCancellationRequested();
                    state = (string)result["state"]; message = (string)result["text"]; code = (string)result["code"];
                }
                catch (OperationCanceledException) { state = "CANCELLED"; code = "STOP_REQUESTED"; message = "Research cancelled. No further page requests or result will be accepted. An already-submitted local model call may take time to stop; no app action or saved report was created."; }
                catch (ResearchWorkerFault fault) { code = fault.Code; message = "Research could not finish. Diagnostic: " + code + ". No file or Windows action ran. If the worker is missing or changed, reinstall this research package; do not change app permissions."; }
                catch { }
                Ui(delegate { FinishResearch(worker, state, message, code); });
            });
        }

        private void FinishResearch(OwnedResearchWorker worker, string state, string message, string code)
        {
            if (researchWorker != worker) return;
            if (!worker.IsStopped)
            {
                researchStopUnconfirmed = true;
                SetStatus("STOP UNCONFIRMED", "#FF7D88");
                UpdateTask("STOP UNCONFIRMED", "The owned research worker's exit could not be confirmed. New requests remain blocked; use Stop again.");
                stopButton.IsEnabled = true;
                return;
            }
            researchActive = false; researchWorker = null; researchStopUnconfirmed = false;
            worker.Dispose();
            if (researchCancellation != null) { researchCancellation.Dispose(); researchCancellation = null; }
            responseBox.Text = message; lastResponse = message;
            SetStatus(state == "COMPLETED" ? "READY" : state, state == "COMPLETED" ? "#4DE3C1" : state == "FAILED" || state == "REJECTED" ? "#FF7D88" : "#F3C969");
            UpdateTask(state, "Read-only web worker exited. " + (code == "OK" ? "Verified source output is memory-only; no workflow was executed." : "Diagnostic: " + code));
            SetInteractive(true);
        }

        private void CancelResearch()
        {
            if (!researchActive || researchWorker == null) return;
            SetStatus("STOPPING", "#F3C969");
            UpdateTask("STOPPING", "Stopping only Cypher's owned research worker; waiting for confirmed exit.");
            if (researchCancellation != null) researchCancellation.Cancel();
            OwnedResearchWorker worker = researchWorker;
            worker.RequestStop();
            // Do not dispose streams or permit another request while Run is still unwinding.
            // A retry is handled here only after Run returned with an unconfirmed process exit.
            if (researchStopUnconfirmed && worker.IsStopped) FinishResearch(worker, "CANCELLED", "Research cancelled. No app action or saved report was created. An already-submitted local model call may take time to stop.", "STOP_REQUESTED");
        }
    }
}
