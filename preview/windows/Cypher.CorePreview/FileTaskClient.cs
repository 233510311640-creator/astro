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

namespace Cypher.CorePreview
{
    // A private stdin protocol from the native human approval panel. Never an MCP/model tool.
    internal sealed class FileTaskTranscript
    {
        public const string WorkerSha256 = "3abfa9aedc83d789b8466833bc7e3699df7ef91e8d25880ca0c00b601b06493e";
        public const string DocumentWorkerSha256 = "2faff589366624ac7d2ec65b52cc31c3a28d3cefb99e47d0092e624601053ea7";
        public const string PdfParserSha256 = "cfb71e7aa5efd516600374680c8a7031c8328ec75a4429ee436f429bea26bebd";
        public const string OfficeParserSha256 = "27119c8eaa46064254d0a4de6c31905d3e47a657aeea75e6d9edee3cda9fa442";
        public const string RuntimeWorkerSha256 = "7cb61ac083b5fc74430a900488790540c9a7be560b729e1e8c5e149cd15d2163";
        private readonly string nonce;
        private readonly JavaScriptSerializer json = new JavaScriptSerializer { MaxJsonLength = 262144, RecursionLimit = 16 };
        private bool reviewed, progressing;
        private int frames, verified;
        public Dictionary<string, object> Result { get; private set; }
        public FileTaskTranscript(string nonce) { this.nonce = nonce; }
        public static bool IsRequest(string input)
        { return Regex.IsMatch(input ?? "", @"^\s*Files\s*:", RegexOptions.IgnoreCase | RegexOptions.CultureInvariant); }
        public void Accept(string line, Action<Dictionary<string, object>> onFrame)
        {
            if (Result != null || ++frames > 55 || line.Length > 262144) throw new InvalidDataException("Invalid file-task transcript");
            Dictionary<string, object> value = json.DeserializeObject(line) as Dictionary<string, object>;
            if (value == null || !value.ContainsKey("nonce") || !(value["nonce"] is string) || (string)value["nonce"] != nonce ||
                !value.ContainsKey("type") || !(value["type"] is string)) throw new InvalidDataException("Invalid file-task envelope");
            string kind = (string)value["type"];
            if (kind == "review")
            {
                if (reviewed || progressing || value.Count != 4 || !value.ContainsKey("text") || !(value["text"] is string) ||
                    ((string)value["text"]).Length == 0 || !value.ContainsKey("fingerprint") || !(value["fingerprint"] is string) ||
                    !Regex.IsMatch((string)value["fingerprint"], @"\A[a-f0-9]{64}\z")) throw new InvalidDataException("Invalid file-task review");
                reviewed = true;
            }
            else if (kind == "progress")
            {
                if (!reviewed || value.Count != 4 || !value.ContainsKey("verified") || !(value["verified"] is int) ||
                    !value.ContainsKey("total") || !(value["total"] is int)) throw new InvalidDataException("Invalid file-task progress");
                int done = (int)value["verified"], total = (int)value["total"];
                if (done < verified || done < 0 || total < done || total > 50 || (progressing && done == 0))
                    throw new InvalidDataException("Invalid file-task counts");
                verified = done; progressing = true;
            }
            else if (kind == "result")
            {
                if (value.Count != 4 || !value.ContainsKey("state") || !(value["state"] is string) ||
                    !value.ContainsKey("text") || !(value["text"] is string) || ((string)value["text"]).Length == 0 ||
                    !Regex.IsMatch((string)value["state"], @"\A(?:COMPLETED|CANCELLED|REJECTED|FAILED|PARTIAL|RECOVERY REQUIRED)\z"))
                    throw new InvalidDataException("Invalid file-task result");
                Result = value;
            }
            else throw new InvalidDataException("Unknown file-task frame");
            onFrame(value);
        }
        public static int SelfTest()
        {
            try
            {
                string id = new string('a', 32);
                JavaScriptSerializer json = new JavaScriptSerializer();
                Dictionary<string, object> result = new Dictionary<string, object> {
                    { "nonce", id }, { "type", "result" }, { "state", "COMPLETED" }, { "text", "Checked" } };
                FileTaskTranscript transcript = new FileTaskTranscript(id);
                transcript.Accept(json.Serialize(result), delegate { });
                try { transcript.Accept(json.Serialize(result), delegate { }); return 180; } catch (InvalidDataException) { }
                result["nonce"] = new string('b', 32);
                try { new FileTaskTranscript(id).Accept(json.Serialize(result), delegate { }); return 181; } catch (InvalidDataException) { }
                result["nonce"] = id; result["command"] = "execute";
                try { new FileTaskTranscript(id).Accept(json.Serialize(result), delegate { }); return 182; } catch (InvalidDataException) { }
                if (!IsRequest("Files: help") || IsRequest("Describe Files: help")) return 183;
                return 0;
            }
            catch { return 184; }
        }
    }

    internal sealed class OwnedFileTask : IDisposable
    {
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
        [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)] private static extern IntPtr CreateJobObject(IntPtr security, string name);
        [DllImport("kernel32.dll", EntryPoint = "SetInformationJobObject", SetLastError = true)] private static extern bool SetExtendedLimits(IntPtr job, int kind, ref ExtendedLimits info, uint length);
        [DllImport("kernel32.dll", SetLastError = true)] private static extern bool AssignProcessToJobObject(IntPtr job, IntPtr process);
        [DllImport("kernel32.dll")] private static extern bool CloseHandle(IntPtr handle);

        private readonly bool runtime;
        private readonly bool documents;
        public OwnedFileTask(bool runtime = false, bool documents = false) { if (runtime && documents) throw new ArgumentException("Invalid worker mode"); this.runtime = runtime; this.documents = documents; }
        private readonly object gate = new object();
        private readonly string nonce = Guid.NewGuid().ToString("N");
        private Process process;
        private IntPtr job;
        private bool started, stopped, forced;
        public bool IsStopped
        { get { lock (gate) { try { return !started || process.HasExited; } catch { return false; } } } }
        public bool StopRequested { get { lock (gate) { return stopped; } } }

        private void Send(Dictionary<string, object> value)
        {
            value["nonce"] = nonce;
            byte[] data = Encoding.UTF8.GetBytes(new JavaScriptSerializer { MaxJsonLength = 262144 }.Serialize(value) + "\n");
            process.StandardInput.BaseStream.Write(data, 0, data.Length);
            process.StandardInput.BaseStream.Flush();
        }
        public void Decide(bool approve, string fingerprint)
        {
            lock (gate)
            {
                if (stopped || !started || process.HasExited) return;
                Dictionary<string, object> decision = new Dictionary<string, object> { { "command", approve ? "approve" : "deny" } };
                if (approve) decision["fingerprint"] = fingerprint;
                else stopped = true;
                Send(decision);
            }
        }
        public void RequestStop()
        {
            lock (gate)
            {
                if (stopped) return;
                stopped = true;
                try { if (started && !process.HasExited) Send(new Dictionary<string, object> { { "command", "stop" } }); } catch { }
            }
        }
        // Only crash/transport failure or a hard deadline kills the owned process.
        // The journal survives and the UI requires recovery; this never claims rollback success.
        private void Abort()
        {
            lock (gate)
            {
                if (IsStopped) return;
                forced = true; stopped = true;
                if (job != IntPtr.Zero) { CloseHandle(job); job = IntPtr.Zero; }
                try { if (started && !process.HasExited) process.Kill(); } catch { }
            }
        }
        private void Start(string root, string python, string input, string folder, string model)
        {
            string worker = Path.Combine(root, documents ? "document_worker.pyz" : runtime ? "runtime_worker.py" : "file_operator.pyz");
            if ((runtime || documents) && (folder != null || model == null) || !runtime && !documents && model != null)
                throw new InvalidDataException("Invalid local worker mode");
            if (!Path.IsPathRooted(python) || python.StartsWith(@"\\", StringComparison.Ordinal) ||
                !Regex.IsMatch(Path.GetFileName(python), @"\Apython(?:3(?:\.12)?)?\.exe\z", RegexOptions.IgnoreCase) ||
                !File.Exists(python) || !File.Exists(worker) || worker.IndexOf('"') >= 0)
                throw new InvalidDataException("File worker is not installed");
            using (SHA256 hash = SHA256.Create())
            using (FileStream stream = File.OpenRead(worker))
                if (BitConverter.ToString(hash.ComputeHash(stream)).Replace("-", "").ToLowerInvariant() != (documents ? FileTaskTranscript.DocumentWorkerSha256 : runtime ? FileTaskTranscript.RuntimeWorkerSha256 : FileTaskTranscript.WorkerSha256))
                    throw new InvalidDataException("File worker integrity check failed");
            if (documents)
            {
                string parser = Path.Combine(root, "pdf_parser.pyz");
                if (!File.Exists(parser)) throw new InvalidDataException("PDF parser is not installed");
                using (SHA256 hash = SHA256.Create())
                using (FileStream stream = File.OpenRead(parser))
                    if (BitConverter.ToString(hash.ComputeHash(stream)).Replace("-", "").ToLowerInvariant() != FileTaskTranscript.PdfParserSha256)
                        throw new InvalidDataException("PDF parser integrity check failed");
                parser = Path.Combine(root, "office_parser.pyz");
                if (!File.Exists(parser)) throw new InvalidDataException("Office parser is not installed");
                using (SHA256 hash = SHA256.Create())
                using (FileStream stream = File.OpenRead(parser))
                    if (BitConverter.ToString(hash.ComputeHash(stream)).Replace("-", "").ToLowerInvariant() != FileTaskTranscript.OfficeParserSha256)
                        throw new InvalidDataException("Office parser integrity check failed");
            }
            ProcessStartInfo start = new ProcessStartInfo {
                FileName = python, Arguments = "-I -S -B -X utf8 \"" + worker + "\"", WorkingDirectory = root,
                UseShellExecute = false, CreateNoWindow = true, RedirectStandardInput = true,
                RedirectStandardOutput = true, RedirectStandardError = true,
                StandardOutputEncoding = Encoding.UTF8, StandardErrorEncoding = Encoding.UTF8 };
            start.EnvironmentVariables.Clear();
            foreach (string name in new string[] { "SystemRoot", "WINDIR", "LOCALAPPDATA", "APPDATA", "USERPROFILE",
                "ProgramFiles", "ProgramFiles(x86)", "ProgramData", "SystemDrive", "TEMP", "TMP" })
            {
                string value = Environment.GetEnvironmentVariable(name);
                if (!string.IsNullOrEmpty(value)) start.EnvironmentVariables[name] = value;
            }
            lock (gate)
            {
                if (stopped) throw new OperationCanceledException();
                job = CreateJobObject(IntPtr.Zero, null);
                ExtendedLimits limits = new ExtendedLimits();
                limits.Basic.LimitFlags = 0x2000 | 0x8 | 0x100;
                // Document work may start exactly one separately pinned PDF or Office parser child.
                limits.Basic.ActiveProcessLimit = documents ? 2U : 1U;
                limits.ProcessMemoryLimit = new UIntPtr(512U * 1024U * 1024U);
                if (job == IntPtr.Zero || !SetExtendedLimits(job, 9, ref limits, (uint)Marshal.SizeOf(typeof(ExtendedLimits))))
                    throw new InvalidDataException("File worker job unavailable");
                process = new Process { StartInfo = start };
                if (!process.Start()) throw new InvalidDataException("File worker did not start");
                started = true;
                if (!AssignProcessToJobObject(job, process.Handle)) throw new InvalidDataException("File worker job assignment failed");
                Dictionary<string, object> request = new Dictionary<string, object> { { "input", input } };
                if (folder != null) request["folder"] = folder;
                if (runtime || documents) request["model"] = model;
                Send(request); // No input (and no action) until ownership is established.
            }
        }
        public Dictionary<string, object> Run(string root, string python, string input, string folder,
            Action<Dictionary<string, object>> onFrame, string model = null)
        {
            FileTaskTranscript transcript = new FileTaskTranscript(nonce);
            Task<int> errors = null;
            using (Timer soft = new Timer(delegate { RequestStop(); }, null, 180000, Timeout.Infinite))
            using (Timer hard = new Timer(delegate { Abort(); }, null, 210000, Timeout.Infinite))
            {
                try
                {
                    Start(root, python, input, folder, model);
                    errors = Task.Run(delegate {
                        int count = 0;
                        while (process.StandardError.Read() != -1) if (++count > 4096) { Abort(); break; }
                        return count;
                    });
                    StringBuilder line = new StringBuilder(); int total = 0, next;
                    // Read() yields each frame immediately while stdin stays open for the human's decision.
                    while ((next = process.StandardOutput.Read()) != -1)
                    {
                        if (++total > 1048576 || line.Length > 262144) throw new InvalidDataException("File worker output exceeded limit");
                        if (next == '\n')
                        {
                            transcript.Accept(line.ToString().TrimEnd('\r'), delegate(Dictionary<string, object> value) {
                                if ((runtime || documents) && (string)value["type"] != "result") throw new InvalidDataException("Read-only model worker cannot request actions");
                                onFrame(value);
                            }); line.Clear();
                            if (transcript.Result != null) process.StandardInput.Close();
                        }
                        else line.Append((char)next);
                    }
                    if (line.Length != 0 || transcript.Result == null || !process.WaitForExit(2000) || process.ExitCode != 0 ||
                        !errors.Wait(2000) || errors.Result != 0 || forced) throw new InvalidDataException("File worker exit or result was not verified");
                    return transcript.Result;
                }
                catch { Abort(); throw; }
                finally { try { if (started) process.WaitForExit(2000); } catch { } }
            }
        }
        public void Dispose()
        {
            Abort();
            lock (gate)
            {
                if (job != IntPtr.Zero) { CloseHandle(job); job = IntPtr.Zero; }
                if (process != null && IsStopped) { process.Dispose(); process = null; started = false; }
            }
        }
        public static int SelfTest(string root, string python)
        {
            int transcript = FileTaskTranscript.SelfTest(); if (transcript != 0) return transcript;
            try
            {
                using (OwnedFileTask worker = new OwnedFileTask())
                {
                    Dictionary<string, object> result = worker.Run(root, python, "Files: self-test", null, delegate { });
                    if ((string)result["state"] != "COMPLETED" || (string)result["text"] != "FILE_TASK_SELF_TEST_OK" || !worker.IsStopped) return 185;
                }
                return 0;
            }
            catch { return 186; }
        }
    }
}
