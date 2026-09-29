using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;

namespace Cypher.CorePreview
{
    // Executed by the compiled host's --self-test BEFORE installation switches the resident host.
    // These run the production parser, runner, approval gate, and checkpoint store with a fake
    // Windows executor. They do not launch, observe, focus, or write to any real application.
    internal static class WindowsWorkflowSelfTest
    {
        private const string PrivateText = "workflow-selftest-private-payload";

        private static void Check(bool value) { if (!value) throw new InvalidOperationException("Workflow self-test failed."); }
        private static void Rejects(Action action)
        {
            bool rejected = false;
            try { action(); } catch (WorkflowFault) { rejected = true; }
            Check(rejected);
        }

        private sealed class MemoryStore : IWorkflowCheckpointStore
        {
            public int Writes;
            public int FailOnWrite;
            public WorkflowCheckpoint Last;
            public void Save(WorkflowCheckpoint checkpoint)
            {
                Writes++;
                if (Writes == FailOnWrite) throw new IOException("Simulated checkpoint failure.");
                Last = checkpoint.Copy();
            }
        }
        private sealed class Executor : IWindowsWorkflowExecutor
        {
            public MemoryStore Store;
            public int Calls;
            public int Validations;
            public int FailAt;
            public int ThrowAt;
            public bool RejectValidation;
            public Action<int> AfterAction;
            public Action<int, WorkflowExecution> DuringAction;
            public Action BeforeValidation;
            public readonly List<WorkflowAction> Actions = new List<WorkflowAction>();
            public void ValidatePlan(WindowsWorkflowPlan plan, WorkflowExecution execution)
            {
                Validations++;
                if (BeforeValidation != null) BeforeValidation();
                if (RejectValidation) throw new WorkflowFault("TARGET_CHANGED", "Simulated target change.");
            }
            public WorkflowStepResult Execute(WorkflowStep step, WorkflowExecution execution)
            {
                execution.CheckBeforeAction();
                Calls++;
                if (Store != null) Check(Store.Last != null && Store.Last.Started == Calls && Store.Last.Verified == Calls - 1);
                Actions.Add(step.Action);
                if (ThrowAt == Calls) throw new InvalidOperationException("Simulated native error.");
                if (DuringAction != null) DuringAction(Calls, execution);
                if (AfterAction != null) AfterAction(Calls);
                return new WorkflowStepResult { Verified = Calls != FailAt, Summary = "simulated", Evidence = "fake executor receipt" };
            }
        }
        private static WindowsWorkflowPlan Plan(DateTimeOffset created, params WorkflowAction[] actions)
        {
            List<WorkflowStep> steps = new List<WorkflowStep>();
            foreach (WorkflowAction action in actions)
                steps.Add(new WorkflowStep(action, "notepad", "Notepad", action == WorkflowAction.WriteText ? PrivateText : null,
                    WindowsWorkflowPlan.Hash("native-binding"), null));
            return new WindowsWorkflowPlan(steps, created);
        }
        private static WindowsWorkflowPlan Plan()
        {
            return Plan(DateTimeOffset.UtcNow, WorkflowAction.Open, WorkflowAction.WriteText, WorkflowAction.Minimize);
        }
        private static WorkflowRunResult Run(WindowsWorkflowPlan plan, Executor executor, MemoryStore store, CancellationToken token)
        {
            executor.Store = store;
            return WindowsWorkflowRunner.Run(plan, plan.Fingerprint, executor, store, token, null);
        }

        private static WorkflowWindowDiagnostic HostedFrame(bool minimized)
        {
            return new WorkflowWindowDiagnostic { Handle = 100, ProcessId = 200, Root = 100,
                ClassName = WorkflowHostedWindowPair.FrameClass, AppUserModelId = "package!App", Cloaked = 0, Minimized = minimized };
        }
        private static WorkflowWindowDiagnostic HostedCore(bool detached)
        {
            return new WorkflowWindowDiagnostic { Handle = 101, ProcessId = 201, Root = detached ? 101 : 100,
                ClassName = WorkflowHostedWindowPair.CoreClass, AppUserModelId = "package!App", Cloaked = detached ? (uint?)2 : (uint?)0 };
        }
        private static List<WorkflowWindowDiagnostic> Actionable(WorkflowHostedWindowPair pair, params WorkflowWindowDiagnostic[] windows)
        {
            return WorkflowHostedWindowPair.Actionable(windows, pair);
        }

        public static int Run()
        {
            int test = 100;
            try
            {
                List<WorkflowIntent> parsed = WindowsWorkflowParser.Parse("Workflow:\r\nOpen Notepad and write: hello\r\nThen minimize Notepad");
                Check(parsed.Count == 3 && parsed[0].Action == WorkflowAction.Open &&
                    parsed[1].Action == WorkflowAction.WriteText && parsed[1].Text == "hello" &&
                    parsed[2].Action == WorkflowAction.Minimize);

                test = 101;
                parsed = WindowsWorkflowParser.Parse("Workflow:\nWrite in Notepad: say then minimize Calculator: literally  ");
                Check(parsed.Count == 1 && parsed[0].Text == "say then minimize Calculator: literally  ");
                Check(!WindowsWorkflowParser.IsRequest("Focus on my assignment"));
                Check(!WindowsWorkflowParser.IsRequest("Focus the window with ID: 12345."));
                Check(WindowsWorkflowParser.IsRequest("Focus Notepad"));
                Check(WindowsWorkflowParser.Parse("Restore Notepad").Count == 1);

                test = 102;
                string[] invalid = {
                    "Workflow:", "Workflow:\nOpen Notepad\nClick a random button", "Workflow:\nOpen C:\\Windows\\notepad.exe",
                    "Workflow:\nOpen Notepad --run", "Workflow:\nWrite in Notepad: ", "Workflow:\nWrite in Notepad: a\tb",
                    "Workflow:\nWrite in Notepad: a\u202Eb", "Workflow:\nWrite in Notepad: first\nsecond",
                    "Workflow:\nWrite in Notepad: " + new string('x', 501),
                    "Workflow:\nOpen Notepad\nOpen Notepad\nOpen Notepad\nOpen Notepad\nOpen Notepad\nOpen Notepad\nOpen Notepad"
                };
                foreach (string value in invalid) Rejects(delegate { WindowsWorkflowParser.Parse(value); });
                Check(WindowsWorkflowParser.Parse("Workflow:\nWrite in Notepad: " + new string('x', 500))[0].Text.Length == 500);

                test = 103;
                WindowsWorkflowPlan plan = Plan();
                MemoryStore store = new MemoryStore();
                Executor executor = new Executor();
                WorkflowRunResult result = Run(plan, executor, store, CancellationToken.None);
                Check(result.Checkpoint.State == "COMPLETED" && result.Checkpoint.Verified == 3 && executor.Calls == 3);
                Check(executor.Actions[0] == WorkflowAction.Open && executor.Actions[1] == WorkflowAction.WriteText &&
                    executor.Actions[2] == WorkflowAction.Minimize && store.Last.State == "COMPLETED");
                Check(plan.Steps[1].TextValue == null);

                test = 104;
                result = Run(plan, executor, store, CancellationToken.None);
                Check(result.ErrorCode == "APPROVAL_CONSUMED" && executor.Calls == 3);
                plan = Plan(DateTimeOffset.UtcNow, WorkflowAction.Minimize);
                Run(plan, new Executor(), new MemoryStore(), CancellationToken.None);
                result = Run(plan, new Executor(), new MemoryStore(), CancellationToken.None);
                Check(result.ErrorCode == "APPROVAL_CONSUMED");

                test = 105;
                plan = Plan(); executor = new Executor(); store = new MemoryStore();
                result = WindowsWorkflowRunner.Run(plan, new string('0', 64), executor, store, CancellationToken.None, null);
                Check(result.ErrorCode == "PLAN_CHANGED" && executor.Calls == 0 && store.Writes == 0);

                test = 106;
                plan = Plan(DateTimeOffset.UtcNow.AddMinutes(-2), WorkflowAction.Open);
                executor = new Executor(); store = new MemoryStore();
                result = Run(plan, executor, store, CancellationToken.None);
                Check(result.ErrorCode == "APPROVAL_EXPIRED" && executor.Calls == 0);

                test = 107;
                plan = Plan(); plan.Reject(); executor = new Executor();
                result = Run(plan, executor, new MemoryStore(), CancellationToken.None);
                Check(result.ErrorCode == "APPROVAL_CONSUMED" && executor.Calls == 0);

                test = 108;
                plan = Plan(); plan.Steps[1].ForgetText(); executor = new Executor();
                result = Run(plan, executor, new MemoryStore(), CancellationToken.None);
                Check(result.ErrorCode == "PLAN_CHANGED" && executor.Calls == 0);

                test = 109;
                using (CancellationTokenSource stop = new CancellationTokenSource())
                {
                    stop.Cancel(); executor = new Executor();
                    result = Run(Plan(), executor, new MemoryStore(), stop.Token);
                    Check(result.Checkpoint.State == "CANCELLED" && executor.Calls == 0 && result.Checkpoint.Verified == 0);
                }

                test = 110;
                using (CancellationTokenSource stop = new CancellationTokenSource())
                {
                    executor = new Executor { AfterAction = delegate(int count) { if (count == 1) stop.Cancel(); } };
                    result = Run(Plan(), executor, new MemoryStore(), stop.Token);
                    Check(result.Checkpoint.State == "CANCELLED" && executor.Calls == 1 && result.Checkpoint.Verified == 1);
                }

                test = 111;
                executor = new Executor { RejectValidation = true }; store = new MemoryStore();
                result = Run(Plan(), executor, store, CancellationToken.None);
                Check(result.Checkpoint.State == "FAILED" && executor.Calls == 0 && result.Checkpoint.Started == 0);

                test = 112;
                executor = new Executor { FailAt = 2 };
                result = Run(Plan(), executor, new MemoryStore(), CancellationToken.None);
                Check(result.Checkpoint.State == "FAILED" && executor.Calls == 2 &&
                    result.Checkpoint.Verified == 1 && result.Receipts.Count == 2 && result.ErrorCode == "POSTCONDITION_UNVERIFIED");

                test = 113;
                executor = new Executor { ThrowAt = 2 };
                result = Run(Plan(), executor, new MemoryStore(), CancellationToken.None);
                Check(result.Checkpoint.State == "FAILED" && executor.Calls == 2 && result.Checkpoint.Verified == 1);

                test = 114;
                executor = new Executor(); store = new MemoryStore { FailOnWrite = 1 };
                result = Run(Plan(), executor, store, CancellationToken.None);
                Check(result.Checkpoint.State == "RECOVERY REQUIRED" && executor.Calls == 0 && result.Checkpoint.Started == 0);

                test = 115;
                executor = new Executor(); store = new MemoryStore { FailOnWrite = 2 };
                result = Run(Plan(), executor, store, CancellationToken.None);
                Check(result.Checkpoint.State == "RECOVERY REQUIRED" && executor.Calls == 1 && result.Checkpoint.Verified == 1 &&
                    store.Last.Started == 1 && store.Last.Verified == 0);

                test = 116;
                executor = new Executor(); plan = Plan();
                result = WindowsWorkflowRunner.RunWithBudget(plan, plan.Fingerprint, executor, new MemoryStore(),
                    CancellationToken.None, null, TimeSpan.Zero);
                Check(result.Checkpoint.State == "TIMED_OUT" && executor.Calls == 0);

                test = 117;
                using (CancellationTokenSource stop = new CancellationTokenSource())
                {
                    plan = Plan(); executor = new Executor(); store = new MemoryStore();
                    result = WindowsWorkflowRunner.RunWithBudget(plan, plan.Fingerprint, executor, store, stop.Token,
                        delegate(WorkflowCheckpoint checkpoint, WorkflowStepResult receipt) { if (receipt == null) stop.Cancel(); },
                        TimeSpan.FromSeconds(60));
                    Check(result.Checkpoint.State == "CANCELLED" && executor.Calls == 0 && result.Checkpoint.Started == 0);
                }

                test = 118;
                WindowsWorkflowPlan parallelPlan = Plan(DateTimeOffset.UtcNow, WorkflowAction.Open);
                int claims = 0;
                Parallel.For(0, 16, delegate(int ignored)
                {
                    try { parallelPlan.ConsumeApproval(parallelPlan.Fingerprint); Interlocked.Increment(ref claims); }
                    catch (WorkflowFault) { }
                });
                Check(claims == 1);

                test = 119;
                string directory = Path.Combine(Path.GetTempPath(), "cypher-workflow-selftest-" + Guid.NewGuid().ToString("N"));
                Directory.CreateDirectory(directory);
                try
                {
                    string path = Path.Combine(directory, "last-workflow.json");
                    WorkflowCheckpointStore disk = new WorkflowCheckpointStore(path);
                    plan = Plan(); executor = new Executor();
                    result = WindowsWorkflowRunner.Run(plan, plan.Fingerprint, executor, disk, CancellationToken.None, null);
                    Check(result.Checkpoint.State == "COMPLETED");
                    string data = File.ReadAllText(path);
                    Check(!data.Contains(PrivateText) && !data.Contains(WindowsWorkflowPlan.Hash(PrivateText)) &&
                        !data.Contains("notepad") && !data.Contains("fingerprint") && !data.Contains("approval"));
                    WorkflowCheckpoint loaded;
                    Check(disk.TryLoad(out loaded) && loaded.State == "COMPLETED" && loaded.Verified == 3);

                    test = 120;
                    loaded.State = "RUNNING"; loaded.Started = 2; loaded.Verified = 1;
                    disk.Save(loaded);
                    Check(disk.RecoverInterrupted(out loaded) && loaded.State == "INTERRUPTED" && loaded.Started == 2 && loaded.Verified == 1);
                    Check(!disk.RecoverInterrupted(out loaded));

                    test = 121;
                    File.WriteAllText(path, File.ReadAllText(path).Replace("\"schema_version\":1", "\"schema_version\":1,\"text\":\"unexpected\""));
                    Rejects(delegate { WorkflowCheckpoint ignored; disk.TryLoad(out ignored); });

                    test = 122;
                    loaded.State = "COMPLETED"; loaded.Verified = 1; loaded.Started = 2;
                    Rejects(delegate { disk.Save(loaded); });
                }
                finally { Directory.Delete(directory, true); }

                test = 123;
                // The public production entry point must not impose the old two-second pause.
                plan = Plan(); store = new MemoryStore();
                Stopwatch startTimer = Stopwatch.StartNew();
                executor = new Executor
                {
                    BeforeValidation = delegate { Check(startTimer.ElapsedMilliseconds < 1000); }
                };
                result = Run(plan, executor, store, CancellationToken.None);
                Check(result.Checkpoint.State == "COMPLETED" && executor.Validations == 1 && executor.Calls == 3);

                test = 124;
                using (CancellationTokenSource stop = new CancellationTokenSource())
                using (ManualResetEvent observing = new ManualResetEvent(false))
                {
                    plan = Plan(); executor = new Executor(); store = new MemoryStore();
                    executor.DuringAction = delegate(int count, WorkflowExecution execution)
                    {
                        if (count == 2)
                        {
                            observing.Set();
                            execution.WaitForObservation(TimeSpan.FromSeconds(10));
                        }
                    };
                    Task<WorkflowRunResult> running = Task.Run(delegate { return Run(plan, executor, store, stop.Token); });
                    bool entered = observing.WaitOne(TimeSpan.FromSeconds(5));
                    stop.Cancel();
                    Check(running.Wait(TimeSpan.FromSeconds(2)));
                    result = running.Result;
                    Check(entered);
                    Check(result.Checkpoint.State == "CANCELLED" && result.ErrorCode == "STOP_REQUESTED" &&
                        result.Checkpoint.Started == 2 && result.Checkpoint.Verified == 1 && result.Receipts.Count == 1 &&
                        executor.Validations == 1 && executor.Calls == 2 && plan.IsConsumed &&
                        store.Last.State == "CANCELLED" && store.Last.Started == 2 && store.Last.Verified == 1 &&
                        plan.Steps[1].TextValue == null);
                    result = Run(plan, executor, store, CancellationToken.None);
                    Check(result.ErrorCode == "APPROVAL_CONSUMED" && executor.Calls == 2);
                }

                test = 125;
                using (CancellationTokenSource stop = new CancellationTokenSource())
                {
                    executor = new Executor { AfterAction = delegate(int count) { if (count == 3) stop.Cancel(); } };
                    result = Run(Plan(), executor, new MemoryStore(), stop.Token);
                    // A final verified receipt wins over a late Stop; don't claim undo/cancellation.
                    Check(result.Checkpoint.State == "COMPLETED" && result.Checkpoint.Verified == 3 && result.ErrorCode == null);
                }

                test = 126;
                Stopwatch budgetTimer = Stopwatch.StartNew();
                string budgetCode = null;
                try
                {
                    new WorkflowExecution(CancellationToken.None, TimeSpan.FromMilliseconds(25))
                        .WaitForObservation(TimeSpan.FromSeconds(10));
                }
                catch (WorkflowFault fault) { budgetCode = fault.Code; }
                Check(budgetCode == "TIME_BUDGET_EXCEEDED" && budgetTimer.ElapsedMilliseconds < 2000);

                test = 127;
                using (CancellationTokenSource stop = new CancellationTokenSource())
                {
                    plan = Plan(); executor = new Executor(); store = new MemoryStore();
                    result = WindowsWorkflowRunner.Run(plan, plan.Fingerprint, executor, store, stop.Token,
                        delegate(WorkflowCheckpoint checkpoint, WorkflowStepResult receipt)
                        {
                            if (checkpoint.Started == 2 && receipt == null) stop.Cancel();
                        });
                    // Step 2's intent was checkpointed, but it never entered the native executor.
                    Check(result.Checkpoint.State == "CANCELLED" && result.Checkpoint.Started == 1 &&
                        result.Checkpoint.Verified == 1 && executor.Calls == 1 && store.Last.Started == 1);
                }

                test = 128;
                List<WorkflowWindowDiagnostic> candidates = new List<WorkflowWindowDiagnostic>();
                for (int i = 0; i < 7; i++)
                    candidates.Add(new WorkflowWindowDiagnostic
                    {
                        Handle = 100 + i, ProcessId = (uint)(200 + i), Owner = 0,
                        ClassName = "Class\r\n" + new string('x', 200), Minimized = i == 0,
                        Cloaked = i == 1 ? (uint?)null : (uint?)2
                    });
                string diagnostic = WorkflowWindowDiagnostics.Ambiguity("Calculator\r\nFAKE", 7, candidates);
                Check(diagnostic.Contains("Calculator??FAKE (7 matches)") &&
                    diagnostic.Contains("cloaked=unknown") && diagnostic.Contains("cloaked=0x00000002") &&
                    diagnostic.Contains("minimized=yes") && diagnostic.Contains("Further matches omitted.") &&
                    !diagnostic.Contains("HWND 105") && !diagnostic.Contains(new string('x', 81)) &&
                    !diagnostic.Contains("\r\nFAKE") && !diagnostic.Contains("Class\r\n"));

                test = 129;
                executor = new Executor
                {
                    DuringAction = delegate(int count, WorkflowExecution execution)
                    { execution.WaitForObservation(TimeSpan.FromMilliseconds(1)); }
                };
                result = Run(Plan(), executor, new MemoryStore(), CancellationToken.None);
                Check(result.Checkpoint.State == "COMPLETED" && result.Checkpoint.Verified == 3);

                test = 130;
                WorkflowWindowDiagnostic frameInfo = HostedFrame(false), coreInfo = HostedCore(false);
                WorkflowHostedWindowPair hosted = WorkflowHostedWindowPair.Capture(frameInfo, coreInfo, true);
                Check(hosted != null && hosted.FrameHandle == 100 && hosted.CoreHandle == 101);
                string hostedFingerprint = hosted.Fingerprint;
                frameInfo.Handle = 500; coreInfo.ProcessId = 999;
                Check(hosted.FrameHandle == 100 && hosted.CoreProcessId == 201 && hosted.Fingerprint == hostedFingerprint);

                test = 131;
                frameInfo = HostedFrame(true); coreInfo = HostedCore(true);
                List<WorkflowWindowDiagnostic> selected = Actionable(hosted, coreInfo, frameInfo);
                Check(selected.Count == 1 && selected[0] == frameInfo);
                selected = Actionable(hosted, frameInfo, coreInfo);
                Check(selected.Count == 1 && selected[0] == frameInfo);

                test = 132;
                Check(Actionable(null, HostedFrame(true), HostedCore(true)).Count == 2);
                Check(WorkflowHostedWindowPair.Capture(HostedFrame(false), HostedCore(false), false) == null);
                Check(WorkflowHostedWindowPair.Capture(HostedFrame(true), HostedCore(true), true) == null);

                test = 133;
                Action<WorkflowWindowDiagnostic>[] changeCore = {
                    delegate(WorkflowWindowDiagnostic w) { w.Handle = 102; w.Root = 102; },
                    delegate(WorkflowWindowDiagnostic w) { w.ProcessId = 999; },
                    delegate(WorkflowWindowDiagnostic w) { w.ClassName = "DifferentWindow"; },
                    delegate(WorkflowWindowDiagnostic w) { w.AppUserModelId = "different!App"; },
                    delegate(WorkflowWindowDiagnostic w) { w.Owner = 888; },
                    delegate(WorkflowWindowDiagnostic w) { w.Root = 888; },
                    delegate(WorkflowWindowDiagnostic w) { w.Cloaked = null; },
                    delegate(WorkflowWindowDiagnostic w) { w.Cloaked = 0; },
                    delegate(WorkflowWindowDiagnostic w) { w.Cloaked = 1; },
                    delegate(WorkflowWindowDiagnostic w) { w.Cloaked = 3; },
                    delegate(WorkflowWindowDiagnostic w) { w.Cloaked = 4; },
                    delegate(WorkflowWindowDiagnostic w) { w.Cloaked = 6; }
                };
                foreach (Action<WorkflowWindowDiagnostic> change in changeCore)
                {
                    coreInfo = HostedCore(true); change(coreInfo);
                    Check(Actionable(hosted, HostedFrame(true), coreInfo).Count == 2);
                }

                test = 134;
                Action<WorkflowWindowDiagnostic>[] changeFrame = {
                    delegate(WorkflowWindowDiagnostic w) { w.Handle = 102; w.Root = 102; },
                    delegate(WorkflowWindowDiagnostic w) { w.ProcessId = 999; },
                    delegate(WorkflowWindowDiagnostic w) { w.ClassName = "DifferentWindow"; },
                    delegate(WorkflowWindowDiagnostic w) { w.AppUserModelId = "different!App"; },
                    delegate(WorkflowWindowDiagnostic w) { w.Root = 888; },
                    delegate(WorkflowWindowDiagnostic w) { w.Cloaked = null; },
                    delegate(WorkflowWindowDiagnostic w) { w.Cloaked = 2; }
                };
                foreach (Action<WorkflowWindowDiagnostic> change in changeFrame)
                {
                    frameInfo = HostedFrame(true); change(frameInfo);
                    Check(Actionable(hosted, frameInfo, HostedCore(true)).Count == 2);
                }
                coreInfo = HostedCore(true);
                Check(Actionable(hosted, coreInfo).Count == 1); // Missing frame cannot erase the core or substitute it.

                test = 135;
                WorkflowWindowDiagnostic extra = HostedFrame(false); extra.Handle = 102; extra.Root = 102;
                Check(Actionable(hosted, HostedFrame(true), HostedCore(true), extra).Count == 2);
                extra = HostedCore(true); extra.Handle = 102; extra.Root = 102;
                Check(Actionable(hosted, HostedFrame(true), HostedCore(true), extra).Count == 2);
                extra = HostedFrame(false); extra.Handle = 102; extra.Root = 102; extra.ClassName = "Notepad";
                Check(Actionable(hosted, HostedFrame(true), HostedCore(true), extra).Count == 2);

                test = 136;
                // A stale top-level inventory may contain the exact core after it reattaches.
                frameInfo = HostedFrame(false); coreInfo = HostedCore(false);
                selected = Actionable(hosted, frameInfo, coreInfo);
                Check(selected.Count == 1 && selected[0] == frameInfo);
                Check(Actionable(hosted, frameInfo).Count == 1);
                coreInfo.Root = 777;
                Check(Actionable(hosted, frameInfo, coreInfo).Count == 2);

                test = 137;
                frameInfo = HostedFrame(false); coreInfo = HostedCore(false); coreInfo.Root = 777;
                Check(WorkflowHostedWindowPair.Capture(frameInfo, coreInfo, true) == null);
                coreInfo = HostedCore(false); coreInfo.AppUserModelId = "";
                Check(WorkflowHostedWindowPair.Capture(frameInfo, coreInfo, true) == null);
                coreInfo = HostedCore(false); coreInfo.ClassName = "DifferentWindow";
                Check(WorkflowHostedWindowPair.Capture(frameInfo, coreInfo, true) == null);
                coreInfo = HostedCore(false); frameInfo.Cloaked = null;
                Check(WorkflowHostedWindowPair.Capture(frameInfo, coreInfo, true) == null);

                test = 138;
                frameInfo = HostedFrame(false); coreInfo = HostedCore(false); coreInfo.ProcessId = 202;
                Check(WorkflowHostedWindowPair.Capture(frameInfo, coreInfo, true).Fingerprint != hostedFingerprint);
                coreInfo = HostedCore(false); frameInfo.AppUserModelId = coreInfo.AppUserModelId = "other!App";
                Check(WorkflowHostedWindowPair.Capture(frameInfo, coreInfo, true).Fingerprint != hostedFingerprint);

                test = 139;
                plan = Plan(DateTimeOffset.UtcNow, WorkflowAction.Minimize, WorkflowAction.Restore,
                    WorkflowAction.Minimize, WorkflowAction.Restore, WorkflowAction.Minimize, WorkflowAction.Restore);
                executor = new Executor
                {
                    DuringAction = delegate(int count, WorkflowExecution execution)
                    {
                        bool minimized = count % 2 != 0;
                        List<WorkflowWindowDiagnostic> targets = Actionable(hosted, HostedFrame(minimized), HostedCore(minimized));
                        Check(targets.Count == 1 && targets[0].Handle == hosted.FrameHandle);
                    }
                };
                result = Run(plan, executor, new MemoryStore(), CancellationToken.None);
                Check(result.Checkpoint.State == "COMPLETED" && result.Checkpoint.Verified == 6 && executor.Calls == 6);

                test = 140;
                // An early OS wake must not complete a wait that is bounded by the budget.
                TimeSpan clock = TimeSpan.Zero;
                List<int> waits = new List<int>();
                WorkflowExecution timed = new WorkflowExecution(CancellationToken.None, TimeSpan.FromMilliseconds(25),
                    delegate { return clock; }, delegate(int milliseconds)
                    {
                        waits.Add(milliseconds);
                        Check(waits.Count <= 3);
                        clock += TimeSpan.FromMilliseconds(waits.Count == 1 ? 10 : milliseconds);
                    });
                string deadlineCode = null;
                try { timed.WaitForObservation(TimeSpan.FromSeconds(10)); }
                catch (WorkflowFault fault) { deadlineCode = fault.Code; }
                Check(deadlineCode == "TIME_BUDGET_EXCEEDED" && clock == TimeSpan.FromMilliseconds(25));
                Check(waits.SequenceEqual(new int[] { 25, 15 }));

                test = 141;
                // Repeated early wakes must keep the original observation deadline.
                clock = TimeSpan.FromMilliseconds(5); waits.Clear();
                timed = new WorkflowExecution(CancellationToken.None, TimeSpan.FromMilliseconds(100),
                    delegate { return clock; }, delegate(int milliseconds)
                    {
                        waits.Add(milliseconds);
                        Check(waits.Count <= 3);
                        clock += TimeSpan.FromMilliseconds(waits.Count < 3 ? 7 : milliseconds);
                    });
                timed.WaitForObservation(TimeSpan.FromMilliseconds(20));
                Check(clock == TimeSpan.FromMilliseconds(25) && waits.SequenceEqual(new int[] { 20, 13, 6 }));
                timed.CheckBeforeAction();

                test = 142;
                // Stop after an early wake must prevent another wait or action.
                using (CancellationTokenSource stop = new CancellationTokenSource())
                {
                    clock = TimeSpan.Zero; waits.Clear();
                    timed = new WorkflowExecution(stop.Token, TimeSpan.FromMilliseconds(100),
                        delegate { return clock; }, delegate(int milliseconds)
                        { waits.Add(milliseconds); clock += TimeSpan.FromMilliseconds(1); stop.Cancel(); });
                    bool stopped = false;
                    try { timed.WaitForObservation(TimeSpan.FromMilliseconds(20)); }
                    catch (OperationCanceledException) { stopped = true; }
                    Check(stopped && waits.Count == 1);
                    stopped = false;
                    try { timed.CheckBeforeAction(); } catch (OperationCanceledException) { stopped = true; }
                    Check(stopped);
                }

                test = 143;
                // An exhausted budget must fail without entering the wait primitive.
                clock = TimeSpan.FromMilliseconds(25); waits.Clear();
                timed = new WorkflowExecution(CancellationToken.None, clock,
                    delegate { return clock; }, delegate(int milliseconds) { waits.Add(milliseconds); });
                deadlineCode = null;
                try { timed.WaitForObservation(TimeSpan.FromSeconds(1)); }
                catch (WorkflowFault fault) { deadlineCode = fault.Code; }
                Check(deadlineCode == "TIME_BUDGET_EXCEEDED" && waits.Count == 0);

                test = 144;
                // A late wake past the execution budget must not authorize a later action.
                clock = TimeSpan.Zero; waits.Clear();
                timed = new WorkflowExecution(CancellationToken.None, TimeSpan.FromMilliseconds(25),
                    delegate { return clock; }, delegate(int milliseconds)
                    { waits.Add(milliseconds); clock = TimeSpan.FromMilliseconds(30); });
                deadlineCode = null;
                try { timed.WaitForObservation(TimeSpan.FromMilliseconds(10)); }
                catch (WorkflowFault fault) { deadlineCode = fault.Code; }
                Check(deadlineCode == "TIME_BUDGET_EXCEEDED" && waits.SequenceEqual(new int[] { 10 }));

                test = 145;
                // A sub-millisecond remainder is a positive wait, never a busy zero poll.
                clock = TimeSpan.Zero; waits.Clear();
                timed = new WorkflowExecution(CancellationToken.None, TimeSpan.FromMilliseconds(100),
                    delegate { return clock; }, delegate(int milliseconds)
                    {
                        waits.Add(milliseconds); Check(waits.Count <= 2);
                        clock += waits.Count == 1 ? TimeSpan.FromTicks(195000) : TimeSpan.FromMilliseconds(milliseconds);
                    });
                timed.WaitForObservation(TimeSpan.FromMilliseconds(20));
                Check(waits.SequenceEqual(new int[] { 20, 1 }));

                test = 146;
                foreach (TimeSpan invalidInterval in new TimeSpan[] { TimeSpan.Zero, TimeSpan.FromMilliseconds(-1), TimeSpan.FromSeconds(11) })
                {
                    waits.Clear(); bool rejected = false;
                    try { timed.WaitForObservation(invalidInterval); }
                    catch (ArgumentOutOfRangeException) { rejected = true; }
                    Check(rejected && waits.Count == 0);
                }

                test = 147;
                using (CancellationTokenSource stop = new CancellationTokenSource())
                {
                    stop.Cancel(); clock = TimeSpan.FromMilliseconds(25); waits.Clear();
                    timed = new WorkflowExecution(stop.Token, clock,
                        delegate { return clock; }, delegate(int milliseconds) { waits.Add(milliseconds); });
                    bool stopped = false;
                    try { timed.WaitForObservation(TimeSpan.FromSeconds(1)); }
                    catch (OperationCanceledException) { stopped = true; }
                    Check(stopped && waits.Count == 0);
                }

                return 0;
            }
            catch { return test; }
        }
    }
}
