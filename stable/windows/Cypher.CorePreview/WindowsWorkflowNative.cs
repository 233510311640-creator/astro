using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Runtime.InteropServices;
using System.Text;
using System.Threading;

namespace Cypher.CorePreview
{
    internal sealed partial class LocalWindowsObservation : IWindowsWorkflowExecutor
    {
        [DllImport("dwmapi.dll")]
        private static extern int DwmGetWindowAttribute(IntPtr handle, uint attribute, out uint value, uint size);
        [DllImport("user32.dll", EntryPoint = "GetWindow")]
        private static extern IntPtr GetWorkflowWindowOwner(IntPtr handle, uint command);
        [DllImport("user32.dll")]
        private static extern bool EnumChildWindows(IntPtr parent, EnumWindowsCallback callback, IntPtr parameter);
        [DllImport("user32.dll")]
        private static extern bool IsChild(IntPtr parent, IntPtr child);
        [DllImport("user32.dll")]
        private static extern IntPtr GetAncestor(IntPtr handle, uint flags);

        private static uint? WorkflowCloakState(IntPtr handle)
        {
            try
            {
                uint value;
                // DWMWA_CLOAKED = 14. Observe only; never change visibility or selection.
                return DwmGetWindowAttribute(handle, 14, out value, 4) == 0 ? (uint?)value : null;
            }
            catch (DllNotFoundException) { return null; }
            catch (EntryPointNotFoundException) { return null; }
        }

        private sealed class WorkflowNativeBinding
        {
            // Approval never changes. Window is a runtime result derived only from this approved app.
            public PendingWindowsControl Approval;
            public PendingWindowsControl Window;
            public bool InitiallyMinimized;
            public WorkflowHostedWindowPair ApprovedHostedPair;
            public WorkflowHostedWindowPair HostedPair;
        }

        private static WorkflowWindowDiagnostic ReadWorkflowWindowDiagnostic(IntPtr handle)
        {
            uint processId;
            GetWindowThreadProcessId(handle, out processId);
            StringBuilder className = new StringBuilder(256);
            GetClassNameW(handle, className, className.Capacity);
            string aumid = ReadWindowAppUserModelId(handle);
            if (string.IsNullOrWhiteSpace(aumid)) aumid = ReadProcessAppUserModelId(processId);
            return new WorkflowWindowDiagnostic
            {
                Handle = handle.ToInt64(), ProcessId = processId, ClassName = className.ToString(),
                Owner = GetWorkflowWindowOwner(handle, 4).ToInt64(), // GW_OWNER
                Root = GetAncestor(handle, 2).ToInt64(), // GA_ROOT, parent chain only
                Minimized = IsIconic(handle), Cloaked = WorkflowCloakState(handle), AppUserModelId = aumid
            };
        }

        private static WorkflowHostedWindowPair CaptureWorkflowHostedPair(WindowRecord frame, RegisteredAppRecord app, Action check)
        {
            if (frame.ClassName != WorkflowHostedWindowPair.FrameClass || frame.Minimized || string.IsNullOrEmpty(app.AppUserModelId)) return null;
            check();
            IntPtr frameHandle = WindowHandle(frame);
            WorkflowWindowDiagnostic frameInfo = ReadWorkflowWindowDiagnostic(frameHandle);
            if (frameInfo.ProcessId != frame.ProcessId || frameInfo.ClassName != frame.ClassName ||
                !string.Equals(frameInfo.AppUserModelId, app.AppUserModelId, StringComparison.Ordinal)) return null;
            List<WorkflowHostedWindowPair> pairs = new List<WorkflowHostedWindowPair>();
            int examined = 0;
            bool complete = true;
            Exception failure = null;
            EnumChildWindows(frameHandle, delegate(IntPtr child, IntPtr ignored)
            {
                try
                {
                    check();
                    if (++examined > 64) { complete = false; return false; }
                    StringBuilder childClass = new StringBuilder(256);
                    GetClassNameW(child, childClass, childClass.Capacity);
                    if (childClass.ToString() != WorkflowHostedWindowPair.CoreClass) return true;
                    WorkflowHostedWindowPair pair = WorkflowHostedWindowPair.Capture(frameInfo,
                        ReadWorkflowWindowDiagnostic(child), IsChild(frameHandle, child));
                    if (pair != null) pairs.Add(pair);
                    return true;
                }
                catch (Exception error) { failure = error; return false; }
            }, IntPtr.Zero);
            if (failure != null) throw failure;
            check();
            if (!complete) throw new WorkflowFault("HOSTED_SCAN_LIMIT", "The hosted child-window scan exceeded its bound. No content companion was selected.");
            if (pairs.Count > 1) throw new WorkflowFault("AMBIGUOUS_HOSTED_CONTENT", "More than one core content window belongs to the frame. Cypher will not guess.");
            if (pairs.Count == 0) return null;
            IntPtr coreHandle = new IntPtr(pairs[0].CoreHandle);
            WorkflowHostedWindowPair confirmed = WorkflowHostedWindowPair.Capture(ReadWorkflowWindowDiagnostic(frameHandle),
                ReadWorkflowWindowDiagnostic(coreHandle), IsChild(frameHandle, coreHandle));
            return confirmed != null && confirmed.Fingerprint == pairs[0].Fingerprint ? confirmed : null;
        }

        private static string WorkflowBindingFingerprint(WorkflowNativeBinding binding)
        {
            StringBuilder canonical = new StringBuilder();
            AppendCanonical(canonical, "cypher-workflow-hosted-binding-v2");
            AppendCanonical(canonical, Fingerprint(binding.Approval));
            AppendCanonical(canonical, binding.ApprovedHostedPair == null ? "none" : binding.ApprovedHostedPair.Fingerprint);
            return Sha256Text(canonical.ToString());
        }

        private static PendingWindowsControl CopyWorkflowTarget(PendingWindowsControl source)
        {
            return new PendingWindowsControl
            {
                Kind = source.Kind, TargetId = source.TargetId, TargetLabel = source.TargetLabel,
                ExecutablePath = source.ExecutablePath, AppUserModelId = source.AppUserModelId,
                AllowTextEntry = source.AllowTextEntry, ExecutableHash = source.ExecutableHash,
                ExecutableLength = source.ExecutableLength, ExecutableLastWriteUtcTicks = source.ExecutableLastWriteUtcTicks,
                WindowId = source.WindowId, WindowTitle = source.WindowTitle, WindowClass = source.WindowClass,
                WindowProcessId = source.WindowProcessId, ControlId = source.ControlId, ControlName = source.ControlName,
                ControlTypeName = source.ControlTypeName, ControlAutomationId = source.ControlAutomationId,
                ControlClassName = source.ControlClassName, ControlFrameworkId = source.ControlFrameworkId,
                ControlPath = source.ControlPath, TargetSelectionPolicy = source.TargetSelectionPolicy,
                CreatedAtUtc = source.CreatedAtUtc, ExpiresAtUtc = source.ExpiresAtUtc
            };
        }

        private static void BindWorkflowWindow(PendingWindowsControl target, WindowRecord window)
        {
            target.WindowId = window.Id; target.WindowProcessId = window.ProcessId;
            target.WindowClass = window.ClassName; target.WindowTitle = window.Title;
        }

        private static List<WindowRecord> FindWorkflowWindows(RegisteredAppRecord app, WorkflowHostedWindowPair hostedPair = null)
        {
            List<WindowRecord> windows = ObserveWindows(201);
            if (windows.Count >= 201)
                throw new WorkflowFault("WINDOW_SCAN_LIMIT", "The window inventory exceeded its bound. Cypher cannot prove a unique target.");
            List<WindowRecord> matches = new List<WindowRecord>();
            foreach (WindowRecord window in windows)
            {
                if (!string.IsNullOrEmpty(app.AppUserModelId))
                {
                    if (string.Equals(app.AppUserModelId, window.AppUserModelId, StringComparison.Ordinal)) matches.Add(window);
                }
                else
                {
                    string executable;
                    if (TryReadProcessExecutablePath(window.ProcessId, out executable) &&
                        string.Equals(app.ExecutablePath, executable, StringComparison.OrdinalIgnoreCase)) matches.Add(window);
                }
            }
            if (matches.Count > 1)
            {
                List<WorkflowWindowDiagnostic> diagnostics = new List<WorkflowWindowDiagnostic>();
                if (hostedPair != null)
                {
                    foreach (WindowRecord item in matches) diagnostics.Add(ReadWorkflowWindowDiagnostic(WindowHandle(item)));
                    diagnostics = WorkflowHostedWindowPair.Actionable(diagnostics, hostedPair);
                    HashSet<long> retained = new HashSet<long>();
                    foreach (WorkflowWindowDiagnostic item in diagnostics) retained.Add(item.Handle);
                    matches = matches.FindAll(delegate(WindowRecord item) { return retained.Contains(WindowHandle(item).ToInt64()); });
                }
                else
                    for (int i = 0; i < Math.Min(matches.Count, WorkflowWindowDiagnostics.MaximumCandidates); i++)
                        diagnostics.Add(ReadWorkflowWindowDiagnostic(WindowHandle(matches[i])));
                if (matches.Count > 1)
                    throw new WorkflowFault("AMBIGUOUS_WINDOWS", WorkflowWindowDiagnostics.Ambiguity(app.DisplayName, matches.Count, diagnostics));
            }
            return matches;
        }

        private static AutomationControlRecord SingleWorkflowEditor(WindowRecord window)
        {
            int examined;
            bool complete;
            List<AutomationControlRecord> controls = ReadAutomationControls(window, 120, out examined, out complete);
            if (!complete)
                throw new WorkflowFault("EDITOR_SCAN_INCOMPLETE", "The app's accessibility scan was incomplete or exceeded its bound. No editor was selected.");
            List<AutomationControlRecord> editors = controls.FindAll(delegate(AutomationControlRecord item)
            { return item.ValueAvailable && item.Enabled && !item.Offscreen; });
            if (editors.Count > 1)
                throw new WorkflowFault("EDITOR_NOT_UNIQUE", "The selected app must expose exactly one enabled on-screen writable editor. Cypher will not guess.");
            if (editors.Count == 0)
                throw new WorkflowFault("EDITOR_NOT_READY", "The selected app does not yet expose an enabled on-screen writable editor.");
            return editors[0];
        }

        private AutomationControlRecord WaitForWorkflowEditor(WorkflowNativeBinding binding, WorkflowExecution execution, out WindowRecord window)
        {
            Stopwatch wait = Stopwatch.StartNew();
            window = null;
            while (wait.Elapsed < TimeSpan.FromSeconds(8))
            {
                execution.CheckBeforeAction();
                window = RequireWorkflowWindow(binding, RevalidateApplication(binding.Approval));
                try { return SingleWorkflowEditor(window); }
                catch (WorkflowFault fault)
                {
                    // Poll only readiness/completeness; never retry a mutation or accept ambiguity.
                    if (fault.Code != "EDITOR_NOT_READY" && fault.Code != "EDITOR_SCAN_INCOMPLETE") throw;
                }
                execution.WaitForObservation(TimeSpan.FromMilliseconds(100));
            }
            throw new WorkflowFault("EDITOR_READY_TIMEOUT", "The bound window did not expose one fully inspected writable editor within eight seconds. No text was delivered.");
        }

        public WindowsWorkflowPlan PrepareWorkflow(string input, CancellationToken cancellation)
        {
            List<WorkflowIntent> intents = WindowsWorkflowParser.Parse(input);
            List<WorkflowNativeBinding> resolved = new List<WorkflowNativeBinding>();
            Dictionary<string, WorkflowNativeBinding> apps = new Dictionary<string, WorkflowNativeBinding>(StringComparer.Ordinal);
            DateTimeOffset now = DateTimeOffset.UtcNow;
            foreach (WorkflowIntent intent in intents)
            {
                cancellation.ThrowIfCancellationRequested();
                RegisteredAppRecord app = ResolveRegisteredApplicationTarget(intent.Target);
                if (app == null) throw new WorkflowFault("APP_NOT_REGISTERED", "A workflow app is not registered. Use an exact registered name or ID; nothing ran.");
                if (IsSensitiveAutomationProcess(app.ExecutablePath))
                    throw new WorkflowFault("SENSITIVE_APP", "Credential, sign-in, security, and password-manager apps are excluded.");
                WorkflowNativeBinding binding;
                if (!apps.TryGetValue(app.Id, out binding))
                {
                    if (apps.Count >= 3) throw new WorkflowFault("TOO_MANY_APPS", "A workflow may target at most three registered apps.");
                    FileInfo file = new FileInfo(app.ExecutablePath);
                    PendingWindowsControl snapshot = new PendingWindowsControl
                    {
                        Kind = WindowsControlKind.LaunchRegisteredApplication,
                        TargetId = app.Id, TargetLabel = app.DisplayName, ExecutablePath = app.ExecutablePath,
                        AppUserModelId = app.AppUserModelId, AllowTextEntry = app.AllowTextEntry,
                        ExecutableHash = Sha256File(app.ExecutablePath), ExecutableLength = file.Length,
                        ExecutableLastWriteUtcTicks = file.LastWriteTimeUtc.Ticks,
                        TargetSelectionPolicy = "workflow-same-bound-window-proved-hosted-child-or-approved-open-v2",
                        CreatedAtUtc = now, ExpiresAtUtc = now.AddSeconds(60)
                    };
                    binding = new WorkflowNativeBinding { Approval = snapshot };
                    List<WindowRecord> windows = FindWorkflowWindows(app);
                    if (windows.Count == 1)
                    {
                        BindWorkflowWindow(snapshot, windows[0]);
                        binding.InitiallyMinimized = windows[0].Minimized;
                        binding.ApprovedHostedPair = CaptureWorkflowHostedPair(windows[0], app, cancellation.ThrowIfCancellationRequested);
                        binding.HostedPair = binding.ApprovedHostedPair;
                    }
                    apps.Add(app.Id, binding);
                }
                resolved.Add(binding);
            }

            Dictionary<string, bool> available = new Dictionary<string, bool>();
            Dictionary<string, bool> onScreen = new Dictionary<string, bool>();
            foreach (KeyValuePair<string, WorkflowNativeBinding> app in apps)
            {
                available[app.Key] = !string.IsNullOrEmpty(app.Value.Approval.WindowId);
                onScreen[app.Key] = available[app.Key] && !app.Value.InitiallyMinimized;
            }
            for (int i = 0; i < intents.Count; i++)
            {
                cancellation.ThrowIfCancellationRequested();
                WorkflowIntent intent = intents[i];
                WorkflowNativeBinding binding = resolved[i];
                string id = binding.Approval.TargetId;
                if (intent.Action == WorkflowAction.Open)
                {
                    if (!available[id]) onScreen[id] = true;
                    available[id] = true;
                }
                else if (!available[id])
                    throw new WorkflowFault("OPEN_REQUIRED", "An app is not open. Add Open APP before using it.");
                if (intent.Action == WorkflowAction.Focus || intent.Action == WorkflowAction.Restore) onScreen[id] = true;
                if (intent.Action == WorkflowAction.Minimize) onScreen[id] = false;
                if (intent.Action == WorkflowAction.WriteText)
                {
                    if (!binding.Approval.AllowTextEntry)
                        throw new WorkflowFault("TEXT_PERMISSION_REQUIRED", "Text entry is not enabled for a workflow app. Enable it separately; this plan grants no new app permission.");
                    if (!onScreen[id])
                        throw new WorkflowFault("RESTORE_REQUIRED", "A write would target a minimized editor. Add Restore APP before writing.");
                    if (!string.IsNullOrEmpty(binding.Approval.WindowId) && !binding.InitiallyMinimized &&
                        string.IsNullOrEmpty(binding.Approval.ControlId))
                    {
                        WindowRecord window = RevalidateWindow(binding.Approval);
                        AutomationControlRecord editor = SingleWorkflowEditor(window);
                        BindAutomationTarget(binding.Approval, window, editor);
                    }
                }
            }
            foreach (WorkflowNativeBinding binding in apps.Values)
            {
                if (!string.IsNullOrEmpty(binding.Approval.WindowId))
                    binding.Window = CopyWorkflowTarget(binding.Approval);
            }
            List<WorkflowStep> steps = new List<WorkflowStep>();
            for (int i = 0; i < intents.Count; i++)
            {
                WorkflowNativeBinding binding = resolved[i];
                steps.Add(new WorkflowStep(intents[i].Action, binding.Approval.TargetId, binding.Approval.TargetLabel,
                    intents[i].Text, WorkflowBindingFingerprint(binding), binding));
            }
            cancellation.ThrowIfCancellationRequested();
            return new WindowsWorkflowPlan(steps, DateTimeOffset.UtcNow);
        }

        private RegisteredAppRecord ValidateWorkflowBinding(WorkflowStep step, out WorkflowNativeBinding binding)
        {
            binding = step.NativeBinding as WorkflowNativeBinding;
            if (binding == null || step.AppId != binding.Approval.TargetId || step.AppLabel != binding.Approval.TargetLabel ||
                !string.Equals(step.BindingFingerprint, WorkflowBindingFingerprint(binding), StringComparison.Ordinal) ||
                (binding.ApprovedHostedPair != null && binding.HostedPair != binding.ApprovedHostedPair))
                throw new WorkflowFault("BINDING_CHANGED", "The approved app binding changed. No later action ran.");
            RegisteredAppRecord app = RevalidateApplication(binding.Approval);
            if (IsSensitiveAutomationProcess(app.ExecutablePath))
                throw new WorkflowFault("SENSITIVE_APP", "This app is excluded from workflow control.");
            return app;
        }

        private static WindowRecord RequireWorkflowWindow(WorkflowNativeBinding binding, RegisteredAppRecord app)
        {
            if (binding.HostedPair != null && (binding.Window == null ||
                binding.HostedPair.FrameHandle.ToString(System.Globalization.CultureInfo.InvariantCulture) != binding.Window.WindowId ||
                binding.HostedPair.FrameProcessId != binding.Window.WindowProcessId || binding.Window.WindowClass != WorkflowHostedWindowPair.FrameClass ||
                !string.Equals(binding.HostedPair.AppUserModelId, app.AppUserModelId, StringComparison.Ordinal)))
                throw new WorkflowFault("HOSTED_BINDING_CHANGED", "The frame/content binding changed. No replacement target was selected.");
            List<WindowRecord> matches = FindWorkflowWindows(app, binding.HostedPair);
            if (binding.Window == null || matches.Count != 1)
                throw new WorkflowFault("WINDOW_MISSING", "The bound workflow window is unavailable. Cypher will not reopen or replace it implicitly.");
            WindowRecord current = matches[0];
            if (current.Id != binding.Window.WindowId || current.ProcessId != binding.Window.WindowProcessId ||
                current.ClassName != binding.Window.WindowClass)
                throw new WorkflowFault("WINDOW_CHANGED", "The workflow window was replaced. Submit a new request for the new window.");
            return current;
        }

        public void ValidatePlan(WindowsWorkflowPlan plan, WorkflowExecution execution)
        {
            HashSet<string> seen = new HashSet<string>(StringComparer.Ordinal);
            foreach (WorkflowStep step in plan.Steps)
            {
                execution.CheckBeforeAction();
                WorkflowNativeBinding binding;
                RegisteredAppRecord app = ValidateWorkflowBinding(step, out binding);
                if (!seen.Add(step.AppId)) continue;
                if (binding.Window != null) RequireWorkflowWindow(binding, app);
                else if (FindWorkflowWindows(app).Count != 0)
                    throw new WorkflowFault("WINDOW_APPEARED", "A target app opened after the preview was prepared. Submit a new request to bind its window.");
            }
        }

        public WorkflowStepResult Execute(WorkflowStep step, WorkflowExecution execution)
        {
            execution.CheckBeforeAction();
            WorkflowNativeBinding binding;
            RegisteredAppRecord app = ValidateWorkflowBinding(step, out binding);
            if (step.Action == WorkflowAction.Open)
                return OpenWorkflowApplication(binding, app, execution);
            WindowRecord window = RequireWorkflowWindow(binding, app);
            if (step.Action == WorkflowAction.WriteText)
            {
                if (!app.AllowTextEntry) throw new WorkflowFault("TEXT_PERMISSION_REQUIRED", "Text-entry permission was revoked.");
                if (window.Minimized) throw new WorkflowFault("EDITOR_OFFSCREEN", "The bound editor is minimized. No text was delivered.");
                if (string.IsNullOrEmpty(binding.Window.ControlId))
                {
                    AutomationControlRecord editor = WaitForWorkflowEditor(binding, execution, out window);
                    BindAutomationTarget(binding.Window, window, editor);
                }
                PendingWindowsControl write = CopyWorkflowTarget(binding.Window);
                write.Kind = WindowsControlKind.SetAutomationValue;
                write.TextValue = step.TextValue; write.TextLength = step.TextValue == null ? 0 : step.TextValue.Length;
                write.TextHash = Sha256Text(step.TextValue);
                try
                {
                    execution.CheckBeforeAction();
                    // Reuse the proven app/window/control/pattern and payload revalidation path.
                    WindowsControlResult result = ExecuteAutomationControl(write, execution.CheckBeforeAction);
                    return new WorkflowStepResult
                    {
                        Verified = result.Verified,
                        Summary = "Text delivered to the approved " + app.DisplayName + " editor.",
                        Evidence = result.Evidence
                    };
                }
                finally { write.TextValue = null; }
            }
            return ChangeWorkflowWindow(step.Action, binding, app, window, execution);
        }

        private WorkflowStepResult OpenWorkflowApplication(WorkflowNativeBinding binding, RegisteredAppRecord app, WorkflowExecution execution)
        {
            if (binding.Window != null)
            {
                WindowRecord existing = RequireWorkflowWindow(binding, app);
                return new WorkflowStepResult
                {
                    Verified = true, Summary = "Reused the bound " + app.DisplayName + " window.",
                    Evidence = "Registered app identity and window " + existing.Id + " revalidated; no launch or focus change."
                };
            }
            if (FindWorkflowWindows(app).Count != 0)
                throw new WorkflowFault("WINDOW_APPEARED", "The app opened after the preview. Cypher will not adopt an unbound window.");
            RevalidateApplication(binding.Approval);
            execution.CheckBeforeAction();
            ProcessStartInfo start = new ProcessStartInfo
            {
                FileName = app.ExecutablePath, WorkingDirectory = Path.GetDirectoryName(app.ExecutablePath),
                UseShellExecute = false, CreateNoWindow = false
            };
            using (Process process = Process.Start(start))
            {
                if (process == null) throw new WorkflowFault("LAUNCH_FAILED", "Windows did not accept the approved launch.");
                Stopwatch wait = Stopwatch.StartNew();
                // Cancellation interrupts observation, not the already-submitted launch.
                // Without a receipt the runner keeps this step started but unverified.
                while (wait.Elapsed < TimeSpan.FromSeconds(10))
                {
                    execution.CheckBeforeAction();
                    List<WindowRecord> matches = FindWorkflowWindows(app);
                    if (matches.Count == 1)
                    {
                        RevalidateApplication(binding.Approval);
                        binding.Window = CopyWorkflowTarget(binding.Approval);
                        BindWorkflowWindow(binding.Window, matches[0]);
                        binding.HostedPair = CaptureWorkflowHostedPair(matches[0], app, execution.CheckBeforeAction);
                        RequireWorkflowWindow(binding, app);
                        return new WorkflowStepResult
                        {
                            Verified = true, Summary = "Opened " + app.DisplayName + ".",
                            Evidence = "Launched the approved executable without arguments and observed one exact registered-app window: " + matches[0].Id + "."
                        };
                    }
                    execution.WaitForObservation(TimeSpan.FromMilliseconds(100));
                }
            }
            throw new WorkflowFault("LAUNCH_UNVERIFIED", "Windows accepted the launch, but no unique matching window was observed within ten seconds. The app may remain open; no later step ran.");
        }

        private static void WaitForWorkflowWindowState(IntPtr handle, bool minimized, WorkflowExecution execution)
        {
            Stopwatch wait = Stopwatch.StartNew();
            while (wait.Elapsed < TimeSpan.FromSeconds(2))
            {
                if (!IsWindow(handle) || !IsWindowVisible(handle)) return;
                if (IsIconic(handle) == minimized) return;
                execution.WaitForObservation(TimeSpan.FromMilliseconds(50));
            }
        }

        private WorkflowStepResult ChangeWorkflowWindow(WorkflowAction action, WorkflowNativeBinding binding,
            RegisteredAppRecord app, WindowRecord window, WorkflowExecution execution)
        {
            IntPtr handle = WindowHandle(window);
            execution.CheckBeforeAction();
            if (action == WorkflowAction.Minimize && !window.Minimized)
            {
                ShowWindowAsync(handle, 6);
                WaitForWorkflowWindowState(handle, true, execution);
            }
            else if ((action == WorkflowAction.Restore || action == WorkflowAction.Focus) && window.Minimized)
            {
                ShowWindowAsync(handle, 9);
                WaitForWorkflowWindowState(handle, false, execution);
            }
            else if (action != WorkflowAction.Minimize && action != WorkflowAction.Restore && action != WorkflowAction.Focus)
                throw new WorkflowFault("UNSUPPORTED_STEP", "The workflow action is unsupported.");

            if (action == WorkflowAction.Focus)
            {
                window = RequireWorkflowWindow(binding, RevalidateApplication(binding.Approval));
                if (window.Minimized) throw new WorkflowFault("RESTORE_UNVERIFIED", "The requested restore was not confirmed. Focus was not attempted.");
                execution.CheckBeforeAction();
                SetForegroundWindow(handle);
                Stopwatch wait = Stopwatch.StartNew();
                while (wait.Elapsed < TimeSpan.FromSeconds(2) && GetForegroundWindow() != handle)
                    execution.WaitForObservation(TimeSpan.FromMilliseconds(50));
            }
            WindowRecord after = RequireWorkflowWindow(binding, RevalidateApplication(binding.Approval));
            bool verified = action == WorkflowAction.Minimize ? after.Minimized :
                action == WorkflowAction.Restore ? !after.Minimized : !after.Minimized && GetForegroundWindow() == handle;
            return new WorkflowStepResult
            {
                Verified = verified,
                Summary = verified ? action + " confirmed for " + app.DisplayName + "." : action + " was not confirmed for " + app.DisplayName + ".",
                Evidence = "Exact registered app and bound HWND/PID/class revalidated. Final minimized state: " +
                    (after.Minimized ? "yes" : "no") + (action == WorkflowAction.Focus ? "; foreground equality: " + (verified ? "passed" : "failed") : "") +
                    ". No forced foreground bypass, raw input, or clipboard automation."
            };
        }

        public string DescribeWorkflowBindings(WindowsWorkflowPlan plan)
        {
            StringBuilder text = new StringBuilder();
            HashSet<string> seen = new HashSet<string>(StringComparer.Ordinal);
            foreach (WorkflowStep step in plan.Steps)
            {
                if (!seen.Add(step.AppId)) continue;
                WorkflowNativeBinding binding = (WorkflowNativeBinding)step.NativeBinding;
                PendingWindowsControl app = binding.Approval;
                text.Append(app.TargetLabel).Append(" [").Append(app.TargetId).Append("] · ").Append(app.ExecutablePath)
                    .Append(" · SHA-256 ").Append(app.ExecutableHash.Substring(0, 16)).Append("…")
                    .Append(string.IsNullOrEmpty(app.WindowId) ? " · no window; only an explicit Open step may launch it" :
                        " · bound window " + app.WindowId + ", PID " + app.WindowProcessId)
                    .Append("\r\n");
                if (binding.ApprovedHostedPair != null)
                    text.Append("  Proved hosted content HWND ").Append(binding.ApprovedHostedPair.CoreHandle)
                        .Append(", PID ").Append(binding.ApprovedHostedPair.CoreProcessId)
                        .Append(" belongs to this frame. Only that exact attached or shell-cloaked companion may be excluded; the action target stays the bound frame.\r\n");
            }
            return text.ToString();
        }
    }
}
