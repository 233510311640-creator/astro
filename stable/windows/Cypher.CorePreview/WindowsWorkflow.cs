using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.Diagnostics;
using System.Globalization;
using System.IO;
using System.Security.Cryptography;
using System.Text;
using System.Text.RegularExpressions;
using System.Threading;
using System.Web.Script.Serialization;

namespace Cypher.CorePreview
{
    internal enum WorkflowAction { Open, WriteText, Focus, Minimize, Restore }

    internal sealed class WorkflowFault : InvalidOperationException
    {
        public readonly string Code;
        public WorkflowFault(string code, string message) : base(message) { Code = code; }
    }

    internal sealed class WorkflowIntent
    {
        public readonly WorkflowAction Action;
        public readonly string Target;
        public readonly string Text;
        public WorkflowIntent(WorkflowAction action, string target, string text)
        {
            Action = action; Target = target; Text = text;
        }
    }

    internal static class WindowsWorkflowParser
    {
        public const int MaximumSteps = 6;
        public const int MaximumTextLength = 500;
        private const RegexOptions Options = RegexOptions.IgnoreCase | RegexOptions.CultureInvariant;

        public static bool IsRequest(string input)
        {
            return Regex.IsMatch(input ?? "", @"^\s*(?:workflow\s*:|/workflow(?:\s|$)|(?:please\s+)?(?:minimize|restore)\s+)", Options) ||
                Regex.IsMatch(input ?? "", @"^\s*(?:please\s+)?focus\s+(?!(?:the\s+)?(?:window|id|on)\b)[A-Za-z]", Options);
        }

        private static string Target(string value)
        {
            string target = value.Trim();
            if (!Regex.IsMatch(target, @"^[A-Za-z0-9][A-Za-z0-9 _.-]{0,63}$") || target.Contains("--"))
                throw new WorkflowFault("INVALID_APP_NAME", "Use the exact registered app name, without paths, arguments, or window IDs.");
            return target;
        }

        private static string Text(string value)
        {
            if (value.Length == 0 || value.Length > MaximumTextLength ||
                Regex.IsMatch(value, @"[\x00-\x1F\x7F\u202A-\u202E\u2066-\u2069]"))
                throw new WorkflowFault("INVALID_TEXT", "Each write must contain 1-500 characters on one line, without control or bidirectional formatting characters.");
            return value;
        }

        public static List<WorkflowIntent> Parse(string input)
        {
            if (input == null || input.Length == 0 || input.Length > 4000)
                throw new WorkflowFault("INVALID_WORKFLOW", "A workflow must contain at most 4,000 characters.");
            string body = input.TrimStart().Replace("\r\n", "\n");
            Match header = Regex.Match(body, @"^(?:workflow\s*:|/workflow(?:[ \t]*\n|[ \t]+|$))[ \t]*", Options);
            if (header.Success) body = body.Substring(header.Length);
            else if (!IsRequest(body) || body.IndexOf('\n') >= 0)
                throw new WorkflowFault("INVALID_WORKFLOW", "Start a multi-step request with Workflow: and put one action on each line.");
            List<WorkflowIntent> steps = new List<WorkflowIntent>();
            foreach (string raw in body.Split('\n'))
            {
                if (string.IsNullOrWhiteSpace(raw)) continue;
                // Line boundaries are the only instruction delimiter. The text after ':' is literal.
                string line = Regex.Replace(raw.TrimStart(), @"^(?:[1-6][.)][ \t]+)?(?:then[ \t]+)?", "", Options);
                Match combined = Regex.Match(line, @"^(?:please[ \t]+)?(?:open|launch|start)[ \t]+(.+?)[ \t]+and[ \t]+(?:write|type|enter)[ \t]*:[ \t]?(.*)$", Options);
                Match write = Regex.Match(line, @"^(?:please[ \t]+)?(?:write|type)[ \t]+(?:in|into)[ \t]+(.+?)[ \t]*:[ \t]?(.*)$", Options);
                Match window = Regex.Match(line.TrimEnd(), @"^(?:please[ \t]+)?(open|launch|start|focus|minimize|restore)[ \t]+(.+?)$", Options);
                if (combined.Success)
                {
                    string target = Target(combined.Groups[1].Value);
                    steps.Add(new WorkflowIntent(WorkflowAction.Open, target, null));
                    steps.Add(new WorkflowIntent(WorkflowAction.WriteText, target, Text(combined.Groups[2].Value)));
                }
                else if (write.Success)
                    steps.Add(new WorkflowIntent(WorkflowAction.WriteText, Target(write.Groups[1].Value), Text(write.Groups[2].Value)));
                else if (window.Success)
                {
                    string verb = window.Groups[1].Value.ToLowerInvariant();
                    WorkflowAction action = WorkflowAction.Open;
                    if (verb == "focus") action = WorkflowAction.Focus;
                    else if (verb == "minimize") action = WorkflowAction.Minimize;
                    else if (verb == "restore") action = WorkflowAction.Restore;
                    steps.Add(new WorkflowIntent(action, Target(window.Groups[2].Value), null));
                }
                else
                    throw new WorkflowFault("UNSUPPORTED_STEP", "A step was not recognized. Supported actions: Open APP; Write in APP: TEXT; Focus APP; Minimize APP; Restore APP. Nothing ran.");
                if (steps.Count > MaximumSteps)
                    throw new WorkflowFault("TOO_MANY_STEPS", "A workflow may contain at most six actions. Open-and-write counts as two actions.");
            }
            if (steps.Count == 0) throw new WorkflowFault("EMPTY_WORKFLOW", "The workflow has no actions.");
            return steps;
        }
    }

    internal sealed class WorkflowStep
    {
        public readonly WorkflowAction Action;
        public readonly string AppId;
        public readonly string AppLabel;
        public readonly string BindingFingerprint;
        public readonly object NativeBinding;
        public string TextValue { get; private set; }
        public WorkflowStep(WorkflowAction action, string appId, string appLabel, string text, string bindingFingerprint, object nativeBinding)
        {
            if (!Enum.IsDefined(typeof(WorkflowAction), action) ||
                !Regex.IsMatch(appId ?? "", @"^[a-z][a-z0-9_-]{0,31}$") ||
                string.IsNullOrWhiteSpace(appLabel) || appLabel.Length > 64 ||
                !Regex.IsMatch(bindingFingerprint ?? "", @"^[a-f0-9]{64}$"))
                throw new WorkflowFault("INVALID_STEP", "The workflow step binding is invalid.");
            if ((action == WorkflowAction.WriteText && (string.IsNullOrEmpty(text) || text.Length > 500 ||
                    Regex.IsMatch(text, @"[\x00-\x1F\x7F\u202A-\u202E\u2066-\u2069]"))) ||
                (action != WorkflowAction.WriteText && text != null))
                throw new WorkflowFault("INVALID_TEXT", "The workflow text binding is invalid.");
            Action = action; AppId = appId; AppLabel = appLabel; TextValue = text;
            BindingFingerprint = bindingFingerprint; NativeBinding = nativeBinding;
        }
        public void ForgetText() { TextValue = null; }
    }

    internal sealed class WindowsWorkflowPlan
    {
        public readonly string Id;
        public readonly DateTimeOffset CreatedAtUtc;
        public readonly DateTimeOffset ExpiresAtUtc;
        public readonly ReadOnlyCollection<WorkflowStep> Steps;
        public readonly string Fingerprint;
        private int consumed;
        public bool IsConsumed { get { return Interlocked.CompareExchange(ref consumed, 0, 0) != 0; } }

        public WindowsWorkflowPlan(IList<WorkflowStep> steps, DateTimeOffset createdAt)
        {
            if (steps == null || steps.Count < 1 || steps.Count > WindowsWorkflowParser.MaximumSteps)
                throw new WorkflowFault("INVALID_WORKFLOW", "A plan requires one to six bound steps.");
            List<WorkflowStep> copy = new List<WorkflowStep>(steps);
            if (copy.Contains(null)) throw new WorkflowFault("INVALID_STEP", "A workflow cannot contain an empty step.");
            Steps = copy.AsReadOnly();
            Id = Guid.NewGuid().ToString("N");
            CreatedAtUtc = createdAt;
            ExpiresAtUtc = createdAt.AddSeconds(60);
            Fingerprint = CurrentFingerprint();
        }

        internal static string Hash(string text)
        {
            using (SHA256 sha = SHA256.Create())
            {
                byte[] bytes = sha.ComputeHash(Encoding.UTF8.GetBytes(text ?? ""));
                StringBuilder value = new StringBuilder();
                foreach (byte b in bytes) value.Append(b.ToString("x2"));
                return value.ToString();
            }
        }
        private static void Field(StringBuilder builder, string value)
        {
            value = value ?? "";
            builder.Append(value.Length).Append(':').Append(value).Append('|');
        }
        private string CurrentFingerprint()
        {
            StringBuilder value = new StringBuilder();
            Field(value, "cypher-ordered-windows-workflow-v1");
            Field(value, Id);
            Field(value, CreatedAtUtc.UtcDateTime.Ticks.ToString(System.Globalization.CultureInfo.InvariantCulture));
            Field(value, ExpiresAtUtc.UtcDateTime.Ticks.ToString(System.Globalization.CultureInfo.InvariantCulture));
            Field(value, "same-bound-window-or-one-window-from-approved-open;no-retry;no-replay");
            foreach (WorkflowStep step in Steps)
            {
                Field(value, step.Action.ToString()); Field(value, step.AppId); Field(value, step.AppLabel);
                Field(value, step.BindingFingerprint); Field(value, Hash(step.TextValue));
            }
            return Hash(value.ToString());
        }
        public void ConsumeApproval(string approvedFingerprint)
        {
            if (Interlocked.CompareExchange(ref consumed, 1, 0) != 0)
                throw new WorkflowFault("APPROVAL_CONSUMED", "This workflow approval was already consumed. Submit a new request.");
            if (DateTimeOffset.UtcNow > ExpiresAtUtc)
                throw new WorkflowFault("APPROVAL_EXPIRED", "The workflow approval expired. Nothing ran.");
            if (!string.Equals(approvedFingerprint, Fingerprint, StringComparison.Ordinal) ||
                !string.Equals(Fingerprint, CurrentFingerprint(), StringComparison.Ordinal))
                throw new WorkflowFault("PLAN_CHANGED", "The approved workflow fingerprint changed. Nothing ran.");
        }
        public void Reject()
        {
            Interlocked.CompareExchange(ref consumed, 1, 0);
            ForgetText();
        }
        public void ForgetText() { foreach (WorkflowStep step in Steps) step.ForgetText(); }
    }

    internal sealed class WorkflowExecution
    {
        private readonly CancellationToken token;
        private readonly Stopwatch elapsed = Stopwatch.StartNew();
        private readonly TimeSpan budget;
        private readonly Func<TimeSpan> elapsedTime;
        private readonly Action<int> waitForStop;
        public WorkflowExecution(CancellationToken token, TimeSpan budget)
        {
            this.token = token;
            this.budget = budget;
            elapsedTime = delegate { return elapsed.Elapsed; };
            waitForStop = delegate(int milliseconds) { token.WaitHandle.WaitOne(milliseconds); };
        }
        // Deterministic clock/wait seam for the in-assembly behavioral self-test.
        internal WorkflowExecution(CancellationToken token, TimeSpan budget,
            Func<TimeSpan> elapsedTime, Action<int> waitForStop) : this(token, budget)
        {
            if (elapsedTime == null || waitForStop == null) throw new ArgumentNullException();
            this.elapsedTime = elapsedTime;
            this.waitForStop = waitForStop;
        }
        public void CheckBeforeAction()
        {
            token.ThrowIfCancellationRequested();
            if (elapsedTime() >= budget)
                throw new WorkflowFault("TIME_BUDGET_EXCEEDED", "The workflow reached its execution time budget. No later step ran.");
        }

        public void WaitForObservation(TimeSpan interval)
        {
            if (interval <= TimeSpan.Zero || interval > TimeSpan.FromSeconds(10))
                throw new ArgumentOutOfRangeException("interval");
            CheckBeforeAction();
            TimeSpan deadline = elapsedTime() + interval;
            if (deadline > budget) deadline = budget;
            // Wait only when an observed app state is not ready. Stop wakes the worker;
            // neither normal approval nor a successful observation adds a timed pause.
            // Windows may return from a timed wait early. Keep the same monotonic
            // deadline and wait only its remainder, checking cancellation each time.
            while (true)
            {
                CheckBeforeAction();
                TimeSpan remaining = deadline - elapsedTime();
                if (remaining <= TimeSpan.Zero) { CheckBeforeAction(); return; }
                waitForStop((int)Math.Ceiling(remaining.TotalMilliseconds));
            }
        }
    }

    internal sealed class WorkflowWindowDiagnostic
    {
        public long Handle;
        public uint ProcessId;
        public long Owner;
        public string ClassName;
        public bool Minimized;
        public uint? Cloaked;
        public long Root;
        public string AppUserModelId;
    }

    internal sealed class WorkflowHostedWindowPair
    {
        public const string FrameClass = "ApplicationFrameWindow";
        public const string CoreClass = "Windows.UI.Core.CoreWindow";
        public readonly long FrameHandle;
        public readonly uint FrameProcessId;
        public readonly long CoreHandle;
        public readonly uint CoreProcessId;
        public readonly string AppUserModelId;
        public readonly string Fingerprint;

        private WorkflowHostedWindowPair(WorkflowWindowDiagnostic frame, WorkflowWindowDiagnostic core)
        {
            FrameHandle = frame.Handle; FrameProcessId = frame.ProcessId;
            CoreHandle = core.Handle; CoreProcessId = core.ProcessId;
            AppUserModelId = frame.AppUserModelId;
            Fingerprint = WindowsWorkflowPlan.Hash("cypher-proved-hosted-child-v1|" +
                FrameHandle.ToString(CultureInfo.InvariantCulture) + "|" + FrameProcessId.ToString(CultureInfo.InvariantCulture) + "|" +
                CoreHandle.ToString(CultureInfo.InvariantCulture) + "|" + CoreProcessId.ToString(CultureInfo.InvariantCulture) + "|" +
                WindowsWorkflowPlan.Hash(AppUserModelId));
        }

        public static WorkflowHostedWindowPair Capture(WorkflowWindowDiagnostic frame, WorkflowWindowDiagnostic core, bool childConfirmed)
        {
            if (!childConfirmed || frame == null || core == null || frame.Handle == 0 || core.Handle == 0 ||
                frame.Handle == core.Handle || frame.ProcessId == 0 || core.ProcessId == 0 ||
                frame.ClassName != FrameClass || core.ClassName != CoreClass ||
                frame.Root != frame.Handle || core.Root != frame.Handle || frame.Minimized || frame.Cloaked != 0 ||
                string.IsNullOrEmpty(frame.AppUserModelId) ||
                !string.Equals(frame.AppUserModelId, core.AppUserModelId, StringComparison.Ordinal)) return null;
            // Copy identity, not mutable observations. This pair is valid only for this approved plan.
            return new WorkflowHostedWindowPair(frame, core);
        }

        public bool MatchesFrame(WorkflowWindowDiagnostic item)
        {
            return item != null && item.Handle == FrameHandle && item.ProcessId == FrameProcessId &&
                item.ClassName == FrameClass && string.Equals(item.AppUserModelId, AppUserModelId, StringComparison.Ordinal);
        }

        private bool IsCompanion(WorkflowWindowDiagnostic item)
        {
            return item != null && item.Handle == CoreHandle && item.ProcessId == CoreProcessId &&
                item.ClassName == CoreClass && string.Equals(item.AppUserModelId, AppUserModelId, StringComparison.Ordinal) &&
                (item.Root == FrameHandle || (item.Root == item.Handle && item.Owner == 0 && item.Cloaked == 2));
        }

        public static List<WorkflowWindowDiagnostic> Actionable(IList<WorkflowWindowDiagnostic> windows, WorkflowHostedWindowPair pair)
        {
            List<WorkflowWindowDiagnostic> result = new List<WorkflowWindowDiagnostic>(windows);
            if (pair == null) return result;
            WorkflowWindowDiagnostic frame = null, companion = null;
            int frames = 0, companions = 0;
            foreach (WorkflowWindowDiagnostic item in windows)
            {
                if (pair.MatchesFrame(item)) { frame = item; frames++; }
                if (pair.IsCompanion(item)) { companion = item; companions++; }
            }
            // A fresh parent-chain check also handles reattachment during an inventory scan.
            // Ignore only the exact child proved earlier, never all cloaked windows or all windows
            // sharing a process/AUMID. A second actual frame/window remains in the result and rejects.
            if (frames == 1 && companions == 1 && frame.Root == frame.Handle && frame.Cloaked == 0)
                result.Remove(companion);
            return result;
        }
    }

    internal static class WorkflowWindowDiagnostics
    {
        public const int MaximumCandidates = 5;

        private static string Label(string value)
        {
            StringBuilder clean = new StringBuilder();
            foreach (char c in value ?? "")
            {
                if (clean.Length == 80) break;
                clean.Append(c >= ' ' && c <= '~' ? c : '?');
            }
            return clean.ToString();
        }

        public static string Ambiguity(string appLabel, int matchCount, IList<WorkflowWindowDiagnostic> candidates)
        {
            StringBuilder detail = new StringBuilder("More than one window matches workflow app ");
            detail.Append(Label(appLabel)).Append(" (").Append(matchCount).Append(" matches). Cypher will not choose between these matches.");
            detail.Append("\r\nMatching-window metadata (up to five; titles and document text omitted):");
            for (int i = 0; i < Math.Min(candidates.Count, MaximumCandidates); i++)
            {
                WorkflowWindowDiagnostic item = candidates[i];
                detail.Append("\r\nHWND ").Append(item.Handle).Append(" · PID ").Append(item.ProcessId)
                    .Append(" · class ").Append(Label(item.ClassName)).Append(" · owner ").Append(item.Owner)
                    .Append(" · minimized=").Append(item.Minimized ? "yes" : "no")
                    .Append(" · cloaked=").Append(item.Cloaked.HasValue ? "0x" + item.Cloaked.Value.ToString("X8") : "unknown");
            }
            if (matchCount > MaximumCandidates) detail.Append("\r\nFurther matches omitted.");
            detail.Append("\r\nCloak flags: 0=none, 1=app, 2=shell, 4=inherited. Cloaking alone never permits ignoring a window or substituting a target.");
            detail.Append("\r\nFor an already-minimized hosted app, restore it manually before a fresh request so its frame/content relationship can be proved.");
            detail.Append("\r\nClose extra windows or dialogs, then submit a new request. If only one is visible, share this diagnostic before retrying.");
            return detail.ToString();
        }
    }

    internal sealed class WorkflowStepResult
    {
        public bool Verified;
        public string Summary;
        public string Evidence;
    }

    internal interface IWindowsWorkflowExecutor
    {
        void ValidatePlan(WindowsWorkflowPlan plan, WorkflowExecution execution);
        WorkflowStepResult Execute(WorkflowStep step, WorkflowExecution execution);
    }

    internal sealed class WorkflowCheckpoint
    {
        public string WorkflowId;
        public string State;
        public int Total;
        public int Started;
        public int Verified;
        public DateTimeOffset StartedAtUtc;
        public DateTimeOffset UpdatedAtUtc;
        public WorkflowCheckpoint Copy() { return (WorkflowCheckpoint)MemberwiseClone(); }
    }

    internal interface IWorkflowCheckpointStore { void Save(WorkflowCheckpoint checkpoint); }

    internal sealed class WorkflowCheckpointStore : IWorkflowCheckpointStore
    {
        private readonly string path;
        private readonly object gate = new object();
        private static readonly HashSet<string> States = new HashSet<string>(StringComparer.Ordinal)
        { "RUNNING", "COMPLETED", "CANCELLED", "TIMED_OUT", "FAILED", "INTERRUPTED" };
        public WorkflowCheckpointStore(string path) { this.path = Path.GetFullPath(path); }
        public bool Exists { get { return File.Exists(path); } }
        private static void Validate(WorkflowCheckpoint checkpoint)
        {
            if (checkpoint == null || !Regex.IsMatch(checkpoint.WorkflowId ?? "", @"^[a-f0-9]{32}$") ||
                !States.Contains(checkpoint.State) || checkpoint.Total < 1 || checkpoint.Total > 6 ||
                checkpoint.Started < 0 || checkpoint.Started > checkpoint.Total ||
                checkpoint.Verified < 0 || checkpoint.Verified > checkpoint.Started ||
                checkpoint.Started - checkpoint.Verified > 1 ||
                (checkpoint.State == "COMPLETED" && checkpoint.Verified != checkpoint.Total) ||
                checkpoint.StartedAtUtc == default(DateTimeOffset) ||
                checkpoint.UpdatedAtUtc < checkpoint.StartedAtUtc ||
                checkpoint.UpdatedAtUtc > DateTimeOffset.UtcNow.AddMinutes(5))
                throw new WorkflowFault("INVALID_CHECKPOINT", "The workflow checkpoint is invalid.");
        }
        private static void RejectLink(string file)
        {
            if ((File.Exists(file) || Directory.Exists(file)) &&
                (File.GetAttributes(file) & FileAttributes.ReparsePoint) != 0)
                throw new WorkflowFault("CHECKPOINT_LINK", "Workflow checkpoints cannot use linked paths.");
        }
        public void Save(WorkflowCheckpoint checkpoint)
        {
            Validate(checkpoint);
            // Deliberately exclude text, titles, targets, paths, hashes, approvals, and exception text.
            Dictionary<string, object> value = new Dictionary<string, object>();
            value["schema_version"] = 1;
            value["workflow_id"] = checkpoint.WorkflowId;
            value["state"] = checkpoint.State;
            value["step_count"] = checkpoint.Total;
            value["steps_started"] = checkpoint.Started;
            value["steps_verified"] = checkpoint.Verified;
            value["started_at_utc"] = checkpoint.StartedAtUtc.ToString("o");
            value["updated_at_utc"] = checkpoint.UpdatedAtUtc.ToString("o");
            byte[] payload = new UTF8Encoding(false).GetBytes(new JavaScriptSerializer().Serialize(value));
            lock (gate)
            {
                string directory = Path.GetDirectoryName(path);
                RejectLink(directory); RejectLink(path);
                if (!Directory.Exists(directory)) throw new IOException("The workflow checkpoint directory is unavailable.");
                string temporary = Path.Combine(directory, "workflow-" + Guid.NewGuid().ToString("N") + ".tmp");
                try
                {
                    using (FileStream stream = new FileStream(temporary, FileMode.CreateNew, FileAccess.Write, FileShare.None, 4096, FileOptions.WriteThrough))
                    {
                        stream.Write(payload, 0, payload.Length);
                        stream.Flush(true);
                    }
                    if (File.Exists(path)) File.Replace(temporary, path, null);
                    else File.Move(temporary, path);
                }
                finally { if (File.Exists(temporary)) File.Delete(temporary); }
            }
        }
        public bool TryLoad(out WorkflowCheckpoint checkpoint)
        {
            checkpoint = null;
            if (!Exists) return false;
            lock (gate)
            {
                RejectLink(Path.GetDirectoryName(path)); RejectLink(path);
                FileInfo file = new FileInfo(path);
                if (file.Length < 1 || file.Length > 4096)
                    throw new WorkflowFault("INVALID_CHECKPOINT", "The workflow checkpoint size is invalid.");
                JavaScriptSerializer json = new JavaScriptSerializer { MaxJsonLength = 4096 };
                Dictionary<string, object> value = json.DeserializeObject(File.ReadAllText(path, Encoding.UTF8)) as Dictionary<string, object>;
                string[] keys = { "schema_version", "workflow_id", "state", "step_count", "steps_started", "steps_verified", "started_at_utc", "updated_at_utc" };
                if (value == null || value.Count != keys.Length)
                    throw new WorkflowFault("INVALID_CHECKPOINT", "Unexpected workflow checkpoint fields.");
                foreach (string key in keys)
                    if (!value.ContainsKey(key)) throw new WorkflowFault("INVALID_CHECKPOINT", "Missing workflow checkpoint fields.");
                foreach (string key in new string[] { "schema_version", "step_count", "steps_started", "steps_verified" })
                    if (!(value[key] is int)) throw new WorkflowFault("INVALID_CHECKPOINT", "Invalid workflow checkpoint number.");
                foreach (string key in new string[] { "workflow_id", "state", "started_at_utc", "updated_at_utc" })
                    if (!(value[key] is string)) throw new WorkflowFault("INVALID_CHECKPOINT", "Invalid workflow checkpoint text.");
                if ((int)value["schema_version"] != 1)
                    throw new WorkflowFault("INVALID_CHECKPOINT", "Unsupported workflow checkpoint schema.");
                DateTimeOffset started, updated;
                if (!DateTimeOffset.TryParse((string)value["started_at_utc"], out started) ||
                    !DateTimeOffset.TryParse((string)value["updated_at_utc"], out updated))
                    throw new WorkflowFault("INVALID_CHECKPOINT", "Invalid workflow checkpoint timestamp.");
                checkpoint = new WorkflowCheckpoint
                {
                    WorkflowId = (string)value["workflow_id"], State = (string)value["state"],
                    Total = (int)value["step_count"], Started = (int)value["steps_started"], Verified = (int)value["steps_verified"],
                    StartedAtUtc = started, UpdatedAtUtc = updated
                };
                Validate(checkpoint);
                return true;
            }
        }
        public bool RecoverInterrupted(out WorkflowCheckpoint checkpoint)
        {
            if (!TryLoad(out checkpoint) || checkpoint.State != "RUNNING") return false;
            // A checkpoint is evidence only. It contains neither a plan nor executable authority.
            checkpoint.State = "INTERRUPTED";
            checkpoint.UpdatedAtUtc = DateTimeOffset.UtcNow;
            Save(checkpoint);
            return true;
        }
    }

    internal sealed class WorkflowRunResult
    {
        public WorkflowCheckpoint Checkpoint;
        public readonly List<WorkflowStepResult> Receipts = new List<WorkflowStepResult>();
        public string ErrorCode;
        public string Detail;
    }

    internal static class WindowsWorkflowRunner
    {
        public static WorkflowRunResult Run(WindowsWorkflowPlan plan, string approvalFingerprint, IWindowsWorkflowExecutor executor,
            IWorkflowCheckpointStore store, CancellationToken token, Action<WorkflowCheckpoint, WorkflowStepResult> progress)
        {
            return RunWithBudget(plan, approvalFingerprint, executor, store, token, progress, TimeSpan.FromSeconds(60));
        }
        internal static WorkflowRunResult RunWithBudget(WindowsWorkflowPlan plan, string approvalFingerprint, IWindowsWorkflowExecutor executor,
            IWorkflowCheckpointStore store, CancellationToken token, Action<WorkflowCheckpoint, WorkflowStepResult> progress, TimeSpan budget)
        {
            if (plan == null || executor == null || store == null) throw new ArgumentNullException("workflow");
            DateTimeOffset now = DateTimeOffset.UtcNow;
            WorkflowRunResult result = new WorkflowRunResult();
            WorkflowCheckpoint checkpoint = new WorkflowCheckpoint
            {
                WorkflowId = plan.Id, State = "RUNNING", Total = plan.Steps.Count,
                StartedAtUtc = now, UpdatedAtUtc = now
            };
            result.Checkpoint = checkpoint;
            bool approvalClaimed = false;
            bool checkpointFailure = false;
            try
            {
                plan.ConsumeApproval(approvalFingerprint);
                approvalClaimed = true;
                WorkflowExecution execution = new WorkflowExecution(token, budget);
                execution.CheckBeforeAction();
                executor.ValidatePlan(plan, execution);
                for (int index = 0; index < plan.Steps.Count; index++)
                {
                    execution.CheckBeforeAction();
                    checkpoint.Started = index + 1;
                    checkpoint.UpdatedAtUtc = DateTimeOffset.UtcNow;
                    // Persist intent before calling any mutating backend. Failure stops the workflow.
                    try { store.Save(checkpoint.Copy()); }
                    catch { checkpointFailure = true; checkpoint.Started = index; throw; }
                    try
                    {
                        if (progress != null) progress(checkpoint.Copy(), null);
                        execution.CheckBeforeAction();
                    }
                    catch
                    {
                        // Intent was saved, but this step never entered the native executor.
                        checkpoint.Started = index;
                        throw;
                    }
                    WorkflowStepResult receipt = executor.Execute(plan.Steps[index], execution);
                    if (receipt == null) throw new WorkflowFault("MISSING_EVIDENCE", "The current step returned no execution evidence.");
                    result.Receipts.Add(receipt);
                    if (!receipt.Verified)
                        throw new WorkflowFault("POSTCONDITION_UNVERIFIED", "The current step did not reach verified completion. It may have changed the app; no later step ran.");
                    checkpoint.Verified++;
                    checkpoint.UpdatedAtUtc = DateTimeOffset.UtcNow;
                    try { store.Save(checkpoint.Copy()); }
                    catch { checkpointFailure = true; throw; }
                    if (progress != null) progress(checkpoint.Copy(), receipt);
                }
                checkpoint.State = "COMPLETED";
            }
            catch (OperationCanceledException)
            {
                checkpoint.State = "CANCELLED";
                result.ErrorCode = "STOP_REQUESTED";
                result.Detail = "Stopped before starting any later action. Completed actions were not undone.";
            }
            catch (Exception error)
            {
                WorkflowFault fault = error as WorkflowFault;
                result.ErrorCode = checkpointFailure ? "CHECKPOINT_FAILED" : fault == null ? "WORKFLOW_FAILED" : fault.Code;
                result.Detail = checkpointFailure ? "Checkpoint storage failed. No later action ran; review the app before submitting another request." :
                    fault == null ? "The current step failed. Review the app; no later action ran." : fault.Message;
                checkpoint.State = result.ErrorCode == "TIME_BUDGET_EXCEEDED" ? "TIMED_OUT" : "FAILED";
            }
            finally
            {
                plan.ForgetText();
                checkpoint.UpdatedAtUtc = DateTimeOffset.UtcNow;
                if (approvalClaimed && !checkpointFailure)
                {
                    try { store.Save(checkpoint.Copy()); }
                    catch
                    {
                        checkpointFailure = true;
                        result.ErrorCode = "CHECKPOINT_FAILED";
                        result.Detail = "Execution stopped, but the final checkpoint could not be saved. Review the app before a new request.";
                    }
                }
                if (checkpointFailure) checkpoint.State = "RECOVERY REQUIRED";
            }
            return result;
        }
    }
}
