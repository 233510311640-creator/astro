from pathlib import Path
import os
import re
import subprocess
import tempfile
import unittest
from xml.etree import ElementTree


ROOT = Path(__file__).parents[1]


def strip_csharp_literals_and_comments(source: str) -> str:
    """Small lexical pass used only to catch truncated release source."""
    output = []
    index = 0
    state = "code"
    while index < len(source):
        char = source[index]
        nxt = source[index + 1] if index + 1 < len(source) else ""
        if state == "code":
            if char == "/" and nxt == "/":
                state = "line_comment"
                output.extend("  ")
                index += 2
                continue
            if char == "/" and nxt == "*":
                state = "block_comment"
                output.extend("  ")
                index += 2
                continue
            if char == "@" and nxt == '"':
                state = "verbatim"
                output.extend("  ")
                index += 2
                continue
            if char == '"':
                state = "string"
                output.append(" ")
                index += 1
                continue
            if char == "'":
                state = "char"
                output.append(" ")
                index += 1
                continue
            output.append(char)
            index += 1
            continue
        if state == "line_comment":
            output.append("\n" if char == "\n" else " ")
            if char == "\n":
                state = "code"
            index += 1
            continue
        if state == "block_comment":
            if char == "*" and nxt == "/":
                output.extend("  ")
                state = "code"
                index += 2
            else:
                output.append("\n" if char == "\n" else " ")
                index += 1
            continue
        if state == "verbatim":
            if char == '"' and nxt == '"':
                output.extend("  ")
                index += 2
            elif char == '"':
                output.append(" ")
                state = "code"
                index += 1
            else:
                output.append("\n" if char == "\n" else " ")
                index += 1
            continue
        if state in {"string", "char"}:
            if char == "\\":
                output.extend("  ")
                index += 2
            elif (state == "string" and char == '"') or (
                state == "char" and char == "'"
            ):
                output.append(" ")
                state = "code"
                index += 1
            else:
                output.append("\n" if char == "\n" else " ")
                index += 1
    if state not in {"code", "line_comment"}:
        raise AssertionError(f"unterminated C# lexical state: {state}")
    return "".join(output)


class CypherCoreWindowsTests(unittest.TestCase):
    def setUp(self):
        self.host = (
            ROOT / "windows" / "Cypher.CorePreview" / "CypherCoreHost.cs"
        ).read_text(encoding="utf-8")
        self.research_host = (
            ROOT / "windows" / "Cypher.CorePreview" / "ResearchHost.cs"
        ).read_text(encoding="utf-8")
        self.installer = (
            ROOT / "scripts" / "install_cypher_core_preview_windows.ps1"
        ).read_text(encoding="utf-8")
        self.manager = (
            ROOT / "scripts" / "manage_cypher_core_preview_windows.ps1"
        ).read_text(encoding="utf-8")
        self.tool_config = (
            ROOT / "scripts" / "configure_cypher_hermes_tools_windows.ps1"
        ).read_text(encoding="utf-8")
        self.direct_observation_launcher = (
            ROOT / "INSTALL_CYPHER_DETERMINISTIC_WINDOWS_OBSERVATION.cmd"
        ).read_text(encoding="utf-8")
        self.direct_control_launcher = (
            ROOT / "INSTALL_CYPHER_DETERMINISTIC_WINDOWS_CONTROL.cmd"
        ).read_text(encoding="utf-8")
        self.focus_routing_launcher = (
            ROOT / "INSTALL_CYPHER_WINDOWS_FOCUS_ROUTING_FIX.cmd"
        ).read_text(encoding="utf-8")
        self.ui_automation_launcher = (
            ROOT / "INSTALL_CYPHER_BOUNDED_UI_AUTOMATION.cmd"
        ).read_text(encoding="utf-8")
        self.text_entry_launcher = (
            ROOT / "INSTALL_CYPHER_PACKAGED_APP_TEXT_ENTRY.cmd"
        ).read_text(encoding="utf-8")
        self.natural_workflow_launcher = (
            ROOT / "INSTALL_CYPHER_NATURAL_WINDOWS_WORKFLOW.cmd"
        ).read_text(encoding="utf-8")
        self.https_open_launcher = (
            ROOT / "INSTALL_CYPHER_REGISTERED_HTTPS_OPEN.cmd"
        ).read_text(encoding="utf-8")
        self.office_launcher = (
            ROOT / "INSTALL_CYPHER_OFFICE_DOCUMENTS.cmd"
        ).read_text(encoding="utf-8")
        self.grounded_web_launcher = (
            ROOT / "INSTALL_CYPHER_GROUNDED_WEB_ANSWERS.cmd"
        ).read_text(encoding="utf-8")
        self.navigation_launcher = (
            ROOT / "INSTALL_CYPHER_BOUNDED_WEB_NAVIGATION.cmd"
        ).read_text(encoding="utf-8")

    def test_compiled_host_source_is_complete_and_xaml_is_valid(self):
        for source in (ROOT / "windows" / "Cypher.CorePreview").glob("*.cs"):
            lexical = strip_csharp_literals_and_comments(source.read_text(encoding="utf-8"))
            stack = []
            pairs = {"}": "{", ")": "(", "]": "["}
            for char in lexical:
                if char in "{([":
                    stack.append(char)
                elif char in "})]":
                    self.assertTrue(stack, source.name)
                    self.assertEqual(stack.pop(), pairs[char], source.name)
            self.assertEqual(stack, [], source.name)
        xaml = self.host.split('const string xaml = @"', 1)[1].split('";', 1)[0]
        ElementTree.fromstring(xaml)
        self.assertIn("--self-test", self.host)

    def test_workflow_route_precedes_observation_and_stop_reaches_runner(self):
        workflow = (ROOT / "windows/Cypher.CorePreview/WindowsWorkflowHost.cs").read_text(encoding="utf-8")
        begin = self.host.split("private void BeginRequest()", 1)[1].split(
            "private static string WindowsObservationFailureCode", 1
        )[0]
        self.assertLess(begin.index("WindowsWorkflowParser.IsRequest"), begin.index("WindowsObservationRouter.TrySelect"))
        self.assertLess(begin.index("BeginWorkflow(inputBox.Text)"), begin.index("Router.Select"))
        self.assertIn("if (workflowActive) { CancelWorkflow(); return; }", self.host)
        self.assertIn("workflowCancellation.Cancel()", workflow)
        self.assertIn("WindowsWorkflowRunner.Run(plan, plan.Fingerprint", workflow)
        self.assertIn("workflowCheckpointStore, token", workflow)
        self.assertIn("Append(step.TextValue)", workflow)
        self.assertNotIn("ApprovalText(step.TextValue", workflow)
        self.assertIn("RecoverInterrupted(out checkpoint)", workflow)
        approval = workflow.split("private void ResolveWorkflowApproval", 1)[1].split("private void WorkflowProgressUi", 1)[0]
        self.assertLess(approval.index("SetInteractive(false)"), approval.index("Task.Run"))
        self.assertIn("WorkflowProgressUi(delegate", approval)
        self.assertIn("if (!workflowActive || token.IsCancellationRequested) return;", approval)
        dispatch = workflow.split("private void WorkflowProgressUi", 1)[1].split("private void CancelWorkflow", 1)[0]
        self.assertIn("DispatcherPriority.Background", dispatch)

    def test_approved_workflow_starts_without_a_timer_and_keeps_revalidation(self):
        core = (ROOT / "windows/Cypher.CorePreview/WindowsWorkflow.cs").read_text(encoding="utf-8")
        workflow = (ROOT / "windows/Cypher.CorePreview/WindowsWorkflowHost.cs").read_text(encoding="utf-8")
        runner = core.split("internal static class WindowsWorkflowRunner", 1)[1]
        for removed in ("ApprovalStopMilliseconds", "RunWithStopWindow", "WaitOne", "Thread.Sleep", "Task.Delay"):
            self.assertNotIn(removed, runner)
        self.assertNotIn("ARMING", workflow)
        self.assertIn("RunWithBudget(plan, approvalFingerprint", runner)
        self.assertLess(runner.index("plan.ConsumeApproval"), runner.index("execution.CheckBeforeAction()"))
        self.assertLess(runner.index("execution.CheckBeforeAction()"), runner.index("executor.ValidatePlan"))
        self.assertLess(runner.index("executor.ValidatePlan"), runner.index("executor.Execute"))

    def test_workflow_readiness_waits_observe_stop_and_execution_budget(self):
        core = (ROOT / "windows/Cypher.CorePreview/WindowsWorkflow.cs").read_text(encoding="utf-8")
        native = (ROOT / "windows/Cypher.CorePreview/WindowsWorkflowNative.cs").read_text(encoding="utf-8")
        wait = core.split("public void WaitForObservation", 1)[1].split("internal sealed class WorkflowWindowDiagnostic", 1)[0]
        self.assertIn("if (deadline > budget) deadline = budget", wait)
        self.assertIn("deadline - elapsedTime()", wait)
        self.assertLess(wait.index("TimeSpan deadline"), wait.index("while (true)"))
        self.assertLess(wait.index("CheckBeforeAction()", wait.index("while (true)")), wait.index("waitForStop("))
        execution = core.split("internal sealed class WorkflowExecution", 1)[1].split("public void WaitForObservation", 1)[0]
        self.assertIn("token.WaitHandle.WaitOne(milliseconds)", execution)
        self.assertIn("return elapsed.Elapsed", execution)
        self.assertNotIn("Thread.Sleep", native)
        for start, end in (
            ("private AutomationControlRecord WaitForWorkflowEditor", "public WindowsWorkflowPlan PrepareWorkflow"),
            ("private WorkflowStepResult OpenWorkflowApplication", "private static void WaitForWorkflowWindowState"),
            ("private static void WaitForWorkflowWindowState", "private WorkflowStepResult ChangeWorkflowWindow"),
            ("private WorkflowStepResult ChangeWorkflowWindow", "public string DescribeWorkflowBindings"),
        ):
            self.assertIn("execution.WaitForObservation", native.split(start, 1)[1].split(end, 1)[0])

    def test_workflow_text_checks_stop_after_control_validation_before_set_value(self):
        text = self.host.split("private WindowsControlResult ExecuteAutomationControl", 1)[1]
        text = text.split("if (request.Kind == WindowsControlKind.InvokeAutomationControl)", 1)[0]
        self.assertLess(text.index("RevalidateAutomationControl"), text.index("beforeTextMutation();"))
        self.assertLess(text.index("valuePattern.Current.IsReadOnly"), text.index("beforeTextMutation();"))
        self.assertLess(text.index("beforeTextMutation();"), text.index("valuePattern.SetValue"))

    def test_workflow_ambiguity_keeps_unproved_windows_and_reports_remaining_matches(self):
        native = (ROOT / "windows/Cypher.CorePreview/WindowsWorkflowNative.cs").read_text(encoding="utf-8")
        find = native.split("private static List<WindowRecord> FindWorkflowWindows", 1)[1].split(
            "private static AutomationControlRecord SingleWorkflowEditor", 1
        )[0]
        self.assertIn("if (matches.Count > 1)", find)
        self.assertLess(find.index("if (hostedPair != null)"), find.index("WorkflowHostedWindowPair.Actionable"))
        self.assertLess(find.index("WorkflowHostedWindowPair.Actionable"), find.index("matches.FindAll"))
        self.assertIn('throw new WorkflowFault("AMBIGUOUS_WINDOWS", WorkflowWindowDiagnostics.Ambiguity', find)
        self.assertIn("Math.Min(matches.Count, WorkflowWindowDiagnostics.MaximumCandidates)", find)
        for forbidden in ("matches.Remove", "matches.Clear", ".Title", "DwmSetWindowAttribute", "ShowWindow"):
            self.assertNotIn(forbidden, find.split("if (matches.Count > 1)", 1)[1])

    def test_workflow_hosted_pair_requires_bounded_child_proof_before_approval(self):
        native = (ROOT / "windows/Cypher.CorePreview/WindowsWorkflowNative.cs").read_text(encoding="utf-8")
        capture = native.split("private static WorkflowHostedWindowPair CaptureWorkflowHostedPair", 1)[1].split(
            "private static string WorkflowBindingFingerprint", 1
        )[0]
        self.assertIn("EnumChildWindows(frameHandle", capture)
        self.assertIn("if (++examined > 64)", capture)
        self.assertIn("IsChild(frameHandle, child)", capture)
        self.assertIn("IsChild(frameHandle, coreHandle)", capture)
        self.assertIn("if (pairs.Count > 1)", capture)
        self.assertIn("confirmed.Fingerprint == pairs[0].Fingerprint", capture)
        preparation = native.split("public WindowsWorkflowPlan PrepareWorkflow", 1)[1].split(
            "private RegisteredAppRecord ValidateWorkflowBinding", 1
        )[0]
        self.assertLess(preparation.index("binding.ApprovedHostedPair = CaptureWorkflowHostedPair"), preparation.index("new WindowsWorkflowPlan"))
        self.assertIn("WorkflowBindingFingerprint(binding)", preparation)
        fingerprint = native.split("private static string WorkflowBindingFingerprint", 1)[1].split(
            "private static PendingWindowsControl CopyWorkflowTarget", 1
        )[0]
        self.assertIn("Fingerprint(binding.Approval)", fingerprint)
        self.assertIn("binding.ApprovedHostedPair.Fingerprint", fingerprint)

    def test_workflow_hosted_pair_guard_is_specific_and_not_a_cloaked_window_filter(self):
        core = (ROOT / "windows/Cypher.CorePreview/WindowsWorkflow.cs").read_text(encoding="utf-8")
        pair = core.split("internal sealed class WorkflowHostedWindowPair", 1)[1].split(
            "internal static class WorkflowWindowDiagnostics", 1
        )[0]
        self.assertIn("if (!childConfirmed", pair)
        self.assertIn("if (pair == null) return result;", pair)
        self.assertIn("frames == 1 && companions == 1", pair)
        for check in ("item.Handle == CoreHandle", "item.ProcessId == CoreProcessId", "item.ClassName == CoreClass",
                      "item.AppUserModelId, AppUserModelId", "item.Root == FrameHandle",
                      "item.Root == item.Handle && item.Owner == 0 && item.Cloaked == 2"):
            self.assertIn(check, pair)
        self.assertIn("result.Remove(companion)", pair)
        self.assertNotIn("RemoveAll", pair)

    def test_workflow_preserves_bound_identity_and_the_proven_text_path(self):
        native = (ROOT / "windows/Cypher.CorePreview/WindowsWorkflowNative.cs").read_text(encoding="utf-8")
        binding = native.split("private RegisteredAppRecord ValidateWorkflowBinding", 1)[1].split(
            "private static WindowRecord RequireWorkflowWindow", 1
        )[0]
        self.assertIn("WorkflowBindingFingerprint(binding)", binding)
        self.assertIn("binding.HostedPair != binding.ApprovedHostedPair", binding)
        self.assertIn("RevalidateApplication(binding.Approval)", binding)
        target = native.split("private static WindowRecord RequireWorkflowWindow", 1)[1].split(
            "public void ValidatePlan", 1
        )[0]
        for field in ("WindowId", "WindowProcessId", "WindowClass"):
            self.assertIn("binding.Window." + field, target)
        self.assertIn("FindWorkflowWindows(app, binding.HostedPair)", target)
        self.assertIn('"HOSTED_BINDING_CHANGED"', target)
        self.assertNotIn(".Title", target)
        self.assertIn("ExecuteAutomationControl(write, execution.CheckBeforeAction)", native)
        self.assertIn("if (!complete)", native)
        for forbidden in ("SendInput", "SendKeys", "Clipboard.", ".Arguments =", ".Kill(", "TextPattern.Pattern"):
            self.assertNotIn(forbidden, native)

    def test_workflow_checkpoints_are_metadata_only_and_precede_mutation(self):
        core = (ROOT / "windows/Cypher.CorePreview/WindowsWorkflow.cs").read_text(encoding="utf-8")
        save = core.split("public void Save(WorkflowCheckpoint checkpoint)", 1)[1].split("public bool TryLoad", 1)[0]
        self.assertEqual(set(re.findall(r'value\["([^"]+)"\]', save)), {
            "schema_version", "workflow_id", "state", "step_count", "steps_started",
            "steps_verified", "started_at_utc", "updated_at_utc",
        })
        self.assertIn("stream.Flush(true)", save)
        runner = core.split("internal static WorkflowRunResult RunWithBudget", 1)[1]
        self.assertLess(runner.index("plan.ConsumeApproval"), runner.index("executor.ValidatePlan"))
        self.assertLess(runner.index("store.Save"), runner.index("executor.Execute"))
        self.assertLess(runner.index("if (!receipt.Verified)"), runner.index("checkpoint.Verified++"))
        self.assertIn("plan.ForgetText()", runner)
        recovery = core.split("public bool RecoverInterrupted", 1)[1].split("internal sealed class WorkflowRunResult", 1)[0]
        self.assertNotIn("executor", recovery)
        self.assertIn('checkpoint.State = "INTERRUPTED"', recovery)
        self.assertIn("Interlocked.CompareExchange(ref consumed, 1, 0)", core)

    def test_workflow_sources_and_behavioral_harness_are_required_before_install_switch(self):
        source_names = {
            p.name for p in (ROOT / "windows/Cypher.CorePreview").glob("WindowsWorkflow*.cs")
        }
        self.assertEqual(len(source_names), 4)
        for name in source_names:
            self.assertIn(name, self.installer)
        self.assertIn("(@($sourcePath, $managerSource) + $workflowSources)", self.installer)
        self.assertIn("$compilerArguments += $workflowSources", self.installer)
        self.assertLess(self.installer.index("$compilerArguments += $workflowSources"), self.installer.index("& $cscPath"))
        self.assertLess(self.installer.index('ArgumentList "--self-test"'), self.installer.index("\n    Stop-ExistingPreviewHost"))
        self.assertIn("WindowsWorkflowSelfTest.Run()", self.host)
        launcher = (ROOT / "INSTALL_CYPHER_MULTISTEP_WORKFLOW.cmd").read_text(encoding="utf-8")
        self.assertIn("Parser]::ParseFile", launcher)

    @unittest.skipUnless(os.name == "nt", "Requires the native Windows .NET Framework compiler")
    def test_workflow_engine_behavior_with_native_compiler(self):
        """Execute the actual C# engine with a fake Windows adapter, without touching apps."""
        framework = Path(os.environ["WINDIR"]) / "Microsoft.NET"
        candidates = [framework / bitness / "v4.0.30319/csc.exe" for bitness in ("Framework64", "Framework")]
        compiler = next((p for p in candidates if p.is_file()), None)
        self.assertIsNotNone(compiler, "Native compiler is required for the workflow behavioral gate")
        sources = ROOT / "windows/Cypher.CorePreview"
        with tempfile.TemporaryDirectory(prefix="cypher-workflow-tests-") as folder:
            directory = Path(folder)
            runner = directory / "WorkflowTestMain.cs"
            runner.write_text(
                "class WorkflowTestMain { static int Main() { return Cypher.CorePreview.WindowsWorkflowSelfTest.Run(); } }",
                encoding="utf-8",
            )
            executable = directory / "WorkflowTests.exe"
            build = subprocess.run([
                str(compiler), "/nologo", "/target:exe", "/codepage:65001", f"/out:{executable}",
                "/reference:System.dll", "/reference:System.Core.dll", "/reference:System.Web.Extensions.dll",
                str(sources / "WindowsWorkflow.cs"), str(sources / "WindowsWorkflowSelfTest.cs"), str(runner),
            ], capture_output=True, text=True, timeout=60)
            self.assertEqual(build.returncode, 0, build.stdout + build.stderr)
            run = subprocess.run([str(executable)], capture_output=True, text=True, timeout=60)
            self.assertEqual(run.returncode, 0, f"Workflow native test case {run.returncode} failed")

    def test_host_uses_authenticated_runs_sse_and_real_cancellation(self):
        self.assertIn('new Uri(endpoint, "/v1/runs")', self.host)
        self.assertIn('"/events"', self.host)
        self.assertIn('"/stop"', self.host)
        self.assertIn("ResponseHeadersRead", self.host)
        self.assertIn('AuthenticationHeaderValue("Bearer", apiKey)', self.host)
        self.assertIn("CancellationTokenSource", self.host)
        self.assertNotIn('"/v1/responses"', self.host)

    def test_model_roles_are_configurable_but_local_name_validated(self):
        self.assertIn('Router.Configure(settings);', self.host)
        self.assertIn('"fast_model"', self.host)
        self.assertIn('"deep_model"', self.host)
        self.assertIn('"vision_model"', self.host)
        self.assertIn('Invalid local model assignment', self.host)
        self.assertIn('https://remote.example/model', self.host)

    def test_native_approval_is_one_time_or_deny_and_never_ambient(self):
        self.assertIn('"run_approval_response"', self.host)
        self.assertIn('"run_approval_response"', self.installer)
        self.assertNotIn('"run_approval"', self.host)
        self.assertNotIn('"run_approval"', self.installer)
        self.assertIn('"/approval"', self.host)
        self.assertIn("Content='APPROVE ONCE'", self.host)
        self.assertIn("DenyApprovalButton", self.host)
        self.assertIn('normalized != "once" && normalized != "deny"', self.host)
        self.assertNotIn("APPROVE ALWAYS", self.host)

    def test_stop_waits_for_a_terminal_hermes_state(self):
        block = self.host.split("public async Task<string> StopAndConfirmAsync", 1)[1].split(
            "public async Task ResolveApprovalAsync", 1
        )[0]
        self.assertIn("GetRunAsync(runId)", block)
        self.assertIn('state == "cancelled"', block)
        self.assertIn('return "unconfirmed"', block)
        self.assertIn("RECOVERY REQUIRED", self.host)

    def test_ui_exposes_task_phase_and_evidence_without_content_logging(self):
        for marker in (
            "Session details",
            "TaskPhaseText",
            "TaskEvidenceText",
            'UpdateTask("VERIFY"',
            "toolCompletedCount",
        ):
            self.assertIn(marker, self.host)

    def test_router_is_local_bounded_and_matches_measured_models(self):
        self.assertIn('FastModel = "qwen3.5:9b-q4_K_M"', self.host)
        self.assertIn('DeepModel = "gpt-oss:20b"', self.host)
        self.assertIn('VisionModel = "qwen3.5:9b-q4_K_M"', self.host)
        self.assertIn('vision_model = "qwen3.5:9b-q4_K_M"', self.installer)
        self.assertIn('"reasoning_effort"] = "medium"', self.host)
        self.assertIn("DeepScore", self.host)
        self.assertNotIn("router endpoint", self.host.lower())
        self.assertIn("copied from Markdown", self.host)
        self.assertIn('Router.Select("`/deep compare the evidence`"', self.host)

    def test_running_request_is_visible_before_the_first_model_token(self):
        for marker in (
            "ShowActivityDisplay(route)",
            "RefreshActivityDisplay()",
            "Reasoning locally",
            "Working locally",
            "Phase: ",
            "Elapsed: ",
            "The window will stream the answer here",
            "StopActivityDisplay()",
        ):
            self.assertIn(marker, self.host)
        begin = self.host.split("private void BeginRequest()", 1)[1].split(
            "private static string NormalizeRunState", 1
        )[0]
        self.assertNotIn('responseBox.Text = "";', begin)
        self.assertIn('UpdateTask("PLAN"', begin)

    def test_streamed_markdown_is_presented_as_clean_plain_text(self):
        self.assertIn("PlainTextForDisplay", self.host)
        self.assertIn('.Replace("**", "")', self.host)
        self.assertIn('Regex.Replace(text, @"(?m)^\\s*-{3,}', self.host)
        append = self.host.split("private void AppendResponse", 1)[1].split(
            "private void SetReadyMessage", 1
        )[0]
        self.assertIn("PlainTextForDisplay(lastResponse)", append)

    def test_host_preserves_privacy_and_does_not_gain_ambient_authority(self):
        endpoint_block = self.host.split("private static Uri ValidateEndpoint", 1)[1].split(
            "private static void ValidateRunId", 1
        )[0]
        self.assertIn('host != "127.0.0.1"', endpoint_block)
        self.assertIn('host != "localhost"', endpoint_block)
        self.assertIn('host != "::1"', endpoint_block)
        log_block = self.host.split("private void WriteEvent", 1)[1].split(
            "private void Ui", 1
        )[0]
        self.assertNotIn("userText", log_block)
        self.assertNotIn("assistantText", log_block)
        self.assertNotIn("responseBox", log_block)
        hermes_request = self.host.split("private void BeginRequest()", 1)[1].split(
            "private void BeginLocalObservation", 1
        )[0]
        self.assertNotIn("Process.Start", hermes_request)
        self.assertNotIn("powershell.exe", self.host.lower())
        self.assertNotIn("cmd.exe", self.host.lower())

    def test_host_supplies_a_bounded_identity_profile_on_every_run(self):
        self.assertIn("internal static class CoreIdentity", self.host)
        self.assertIn("Never introduce yourself as Hermes", self.host)
        self.assertIn("private local Windows 11 resident assistant", self.host)
        self.assertIn("not the Neo4j query language", self.host)
        self.assertIn("Do not invent memories", self.host)
        self.assertIn("AUTHORITATIVE RUNTIME CAPABILITY CONTRACT", self.host)
        self.assertIn('new Uri(endpoint, "/v1/toolsets")', self.host)
        self.assertIn("Never infer a capability from the selected model", self.host)
        self.assertIn("Call a visible exact MCP tool directly", self.host)
        self.assertIn("use tool_search once", self.host)
        self.assertIn("tool_describe", self.host)
        self.assertIn("returned tool name verbatim", self.host)
        self.assertIn("Do not claim the capability is absent", self.host)
        self.assertIn("Never substitute terminal, shell, built-in file tools", self.host)
        self.assertIn("bounded discovery brokers", self.host)
        self.assertIn("CapabilitySnapshot.IsDisclosureRequest", self.host)
        self.assertIn("capabilitySnapshot.Disclosure()", self.host)
        self.assertIn('payload["instructions"] = instructions;', self.host)
        self.assertNotIn('payload["instructions"] = route.Input', self.host)

    def test_local_identity_greeting_bypasses_slow_model_and_can_be_spoken(self):
        begin = self.host.split("private void BeginRequest()", 1)[1].split(
            "private void BeginLocalObservation", 1
        )[0]
        greeting = begin.split("LocalIdentityReply.TryAnswer", 1)[1].split(
            'Regex.IsMatch(requestedText, @"^Remind', 1
        )[0]
        self.assertIn("lastResponse = identityReply", greeting)
        self.assertIn('WriteEvent("identity_greeting", "ok", 0)', greeting)
        self.assertNotIn("hermes.StartRunAsync", greeting)
        self.assertIn('LocalIdentityReply.TryAnswer("hello cypher"', self.host)
        self.assertIn('LocalIdentityReply.TryAnswer("hello cipher"', self.host)
        voice = (ROOT / "windows" / "Cypher.CorePreview" / "VoiceHost.cs").read_text(encoding="utf-8")
        self.assertIn("MaybeSpeakWakeReply()", voice)
        self.assertIn("manual MIC leaves an editable draft while wake-triggered commands auto-send", self.host)

    def test_overlay_has_streaming_controls_and_keeps_existing_activation(self):
        for marker in (
            "Ctrl+Alt+Space",
            "RegisterHotKey",
            "WF.NotifyIcon",
            "STOP",
            "AutoModeButton",
            "Chat context stays in memory.",
            "action approvals remain.",
            "LocalAssistantHostResidentV061",
        ):
            self.assertIn(marker, self.host)

    def test_manual_voice_is_explicit_local_draft_and_does_not_auto_submit(self):
        voice = (ROOT / "windows" / "Cypher.CorePreview" / "VoiceHost.cs").read_text(encoding="utf-8")
        self.assertIn("VoiceHost.cs", self.installer)
        self.assertIn("/reference:$speechAssemblyPath", self.installer)
        self.assertIn("CypherHost.VoiceSelfTest()", self.host)
        self.assertIn("VoiceCapture.cs", self.installer)
        self.assertIn("VoiceActivityGate.cs", self.installer)
        self.assertIn("capture = new VoiceCapture()", voice)
        self.assertIn("voiceCapture.Finish()", voice)
        self.assertIn("voice_worker.py", voice)
        self.assertIn('start.EnvironmentVariables["HF_HUB_OFFLINE"] = "1"', voice)
        self.assertIn("voiceDeadlineUtc = DateTime.UtcNow.AddSeconds(autoSubmit ? 12 : 20)", voice)
        self.assertIn('WriteEvent("voice_input", "speech_end", 0)', voice)
        self.assertIn("ReadCompletedLevels()", voice)
        self.assertIn("process.WaitForExit(120000)", voice)
        self.assertIn("voiceProcess.Kill()", voice)
        self.assertIn("Array.Clear(audio, 0, audio.Length)", voice)
        self.assertIn('destination.Text = existing', voice)
        self.assertIn('AppendVoiceDraft(inputBox, heard)', voice)
        self.assertIn('UpdateTask("REVIEW"', voice)
        self.assertIn("bool autoSend = keepTranscript && voiceAutoSubmit", voice)
        self.assertIn("SpeakAsyncCancelAll()", voice)
        self.assertIn("args.Prompt != activeVoicePrompt", voice)
        self.assertIn('WriteEvent("voice_output", "greeting_started", 0)', voice)
        self.assertIn('WriteEvent("voice_output", "reply_started", 0)', voice)
        self.assertIn('args.Error == null && !args.Cancelled ? "reply_completed" : "reply_failed"', voice)
        self.assertIn("CancelVoiceInput();", self.host)
        self.assertIn("StopSpeaking();", self.host)

    def test_wake_word_auto_sends_only_wake_recordings_and_preserves_approvals(self):
        wake = (ROOT / "windows" / "Cypher.CorePreview" / "WakeHost.cs").read_text(encoding="utf-8")
        voice = (ROOT / "windows" / "Cypher.CorePreview" / "VoiceHost.cs").read_text(encoding="utf-8")
        self.assertIn("WakeHost.cs", self.installer)
        self.assertIn("wake_word_enabled = $true", self.installer)
        self.assertIn("InitializeWakeWord();", self.host)
        self.assertIn("DisposeWakeWord();", self.host)
        self.assertIn("WakeWorkerSha256", wake)
        self.assertIn('wake_python_path', wake)
        self.assertIn('wake_model_path', wake)
        self.assertIn('wake_deps_path', wake)
        self.assertIn('line == "WAKE" || line == "STOP"', wake)
        self.assertIn('outcome == "STOP"', wake)
        self.assertIn('wake_worker.py', self.installer)
        self.assertIn('Offline wake model initialized', self.installer)
        self.assertNotIn('SpeechRecognitionEngine', wake)
        self.assertIn("StartVoiceInput(true)", voice)
        self.assertIn("AcknowledgeWake();", wake)
        self.assertIn('voiceSpeaker.SpeakAsync("Yes?")', voice)
        self.assertIn("MaybeSpeakWakeReply();", self.host)
        self.assertIn("StopWakeListening();", voice)
        self.assertIn("voiceDeadlineUtc = DateTime.UtcNow.AddSeconds(autoSubmit ? 12 : 20)", voice)
        self.assertIn("bool autoSend = keepTranscript && voiceAutoSubmit", voice)
        self.assertIn("if (autoSend)", voice)
        self.assertIn("BeginRequest();", voice)
        self.assertIn("approveOnceButton.Click += delegate { ResolveApproval(\"once\"); };", self.host)
        self.assertNotIn("ResolveApproval(\"once\")", wake)

    def test_monochrome_signal_workspace_keeps_model_selection_and_capability_details(self):
        for marker in (
            "CORE PREVIEW 10.20.3 / MONOCHROME SIGNAL",
            "MONOCHROME SIGNAL / LOCAL COMMAND CENTER",
            "SignalGridBrush",
            "ModeRail",
            "CommandWorkspace",
            "SystemRail",
            "Bahnschrift Condensed",
            "#F1F1ED",
            "#050505",
            "#83E7FF",
            "APPROVALS ON",
            "PRIVATE / LOOPBACK",
            "Session details",
            "Qwen 3.5 9B",
            "GPT-OSS 20B",
            "CapabilitySummaryText",
            "AutoModeButton",
            "FastModeButton",
            "DeepModeButton",
            "VisionModeButton",
            "ModeButton",
            "HeroArtwork",
            "HeroArtworkFallback",
            "cypher-signal-core.png",
            "HeroArtworkSha256",
            "Pin Cypher above other windows",
            "M 2,6 L 2,2 L 6,2",
            "M 3,3 L 13,13",
        ):
            self.assertIn(marker, self.host)
        for forbidden in ("<ComboBox", "<ComboBoxItem", "ModeBox", "modeBox", "LetterSpacing", "#BEB0FF", "#2D2648", "#1B1929"):
            self.assertNotIn(forbidden, self.host)

    def test_dark_workspace_controls_remain_bound_and_approval_is_always_reachable(self):
        xaml = self.host.split('const string xaml = @"', 1)[1].split('";', 1)[0]
        tree = ElementTree.fromstring(xaml)
        ns = "{http://schemas.microsoft.com/winfx/2006/xaml}Name"
        named = [node for node in tree.iter() if ns in node.attrib]
        controls = {node.attrib[ns]: node for node in named}
        self.assertEqual(len(named), len(controls), "Duplicate XAML names")
        # Every C# cast must still resolve to a compatible named control.
        for expected, name in re.findall(r'\((\w+)\)window.FindName\("([^"]+)"\)', self.host):
            self.assertIn(name, controls)
            if expected != "FrameworkElement":
                self.assertEqual(controls[name].tag.rsplit("}", 1)[-1], expected, name)
        ancestors = {child: parent for parent in tree.iter() for child in parent}
        for name in ("ApprovalCard", "ApproveOnceButton", "DenyApprovalButton",
                     "SendButton", "StopButton", "RetryRecoveryButton"):
            parent = controls[name]
            while parent in ancestors:
                parent = ancestors[parent]
                self.assertNotEqual(parent.tag.rsplit("}", 1)[-1], "Expander", name)
        self.assertEqual(tree.attrib["AllowsTransparency"], "False")
        self.assertEqual(controls["VisionModeButton"].attrib["IsEnabled"], "False")
        self.assertEqual(controls["ResponseBox"].attrib["IsReadOnly"], "True")
        self.assertEqual(controls["InputBox"].attrib["MaxLength"], "32000")
        self.assertEqual(controls["HeroArtwork"].tag.rsplit("}", 1)[-1], "Image")
        self.assertIn("$heroArtworkSource", self.installer)
        self.assertIn("$installedHeroArtwork", self.installer)
        self.assertIn("CypherHost.WorkspaceSelfTest()", self.host)
        self.assertLess(self.installer.index('ArgumentList "--self-test"'),
                        self.installer.index("\n    Stop-ExistingPreviewHost"))

    def test_mode_selection_uses_the_themed_radio_controls(self):
        block = self.host.split("private string SelectedMode()", 1)[1].split(
            "private void SetBusy", 1
        )[0]
        for marker in (
            "visionModeButton.IsChecked",
            "deepModeButton.IsChecked",
            "fastModeButton.IsChecked",
        ):
            self.assertIn(marker, block)

    def test_prompt_starters_only_fill_enabled_composer(self):
        block = self.host.split("private static void WirePromptStarter", 1)[1].split(
            "private WF.NotifyIcon BuildTray", 1
        )[0]
        self.assertIn("if (!input.IsEnabled) return;", block)
        self.assertIn("input.Text = prefix;", block)
        for forbidden in ("BeginRequest", "BeginResearch", "Task.Run", "Http", "File."):
            self.assertNotIn(forbidden, block)
        self.assertIn('"ExplorePromptButton", "Web: links https://"', self.host)
        self.assertIn('"PapersPromptButton", "Web: ask https:// : "', self.host)
        self.assertIn('"PlanPromptButton", "Files: help"', self.host)
        self.assertIn('"DocumentSearchButton", "Docs: search-all "', self.host)
        self.assertIn('"DocumentAnswerButton", "Docs: answer-all "', self.host)
        self.assertIn('"DocumentCompareButton", "Docs: compare "', self.host)
        self.assertIn('"RemindButton", "Remind: YYYY-MM-DD HH:MM : message"', self.host)
        self.assertIn('"VisionPromptButton", "Vision: ask ROOT \\"image.png\\" : "', self.host)
        self.assertIn("Use Files: folders to find your ROOT name", self.host)

    def test_explicit_png_vision_uses_isolated_worker_and_configured_model(self):
        document_host = (ROOT / 'windows/Cypher.CorePreview/DocumentHost.cs').read_text(encoding='utf-8')
        self.assertIn('(Docs|Vision)', document_host)
        self.assertIn('vision ? Router.VisionModel', document_host)
        self.assertIn('new OwnedFileTask(false, true)', document_host)
        self.assertIn('Vision: ask', self.host)
        self.assertIn('Explicit Vision: commands read only an approved PNG', self.host)
        self.assertIn('Use Files: folders to see ROOT names', self.host)

    def test_isolated_public_page_read_is_explicit_and_model_free(self):
        for marker in (
            'IsRequest("Web: read https://example.org/")',
            'IsWebReadRequest("Web: preview https://example.org/")',
            '"ISOLATED · PUBLIC PAGE READ"',
            r'(?:read|preview)\s+https://\S+',
        ):
            self.assertIn(marker, self.research_host)
        for marker in (
            "One isolated public HTTPS page",
            "no browser profile, cookies, saved passwords, login state, scripts, local model, file tools, or Windows actions",
            "Page text is untrusted content",
        ):
            self.assertIn(marker, self.research_host)
        self.assertIn("Web: read previews one public page without a model.", self.host)

    def test_grounded_public_page_answer_is_single_page_local_and_cited(self):
        for marker in (
            'IsWebAskRequest("Web: ask https://example.org/ : What is this page?")',
            '"LOCAL · GROUNDED PAGE ANSWER · "',
            "one verified installed local model",
            "Exact supporting passages are checked before display",
            "Page text is untrusted content",
        ):
            self.assertIn(marker, self.research_host)
        for marker in (
            "Web: ask PUBLIC-HTTPS-URL : QUESTION",
            "at most one verified installed local-model call",
            "Every displayed finding must select valid passage IDs",
            "Neither web route can use browser state, files, or actions",
            "ASK PAGE",
            "Answer from exact evidence",
        ):
            self.assertIn(marker, self.host)

    def test_bounded_public_page_navigation_maps_links_before_separate_open(self):
        for marker in (
            'IsWebLinksRequest("Web: links https://example.org/")',
            '"ISOLATED · SAFE LINK MAP"',
            "at most six eligible HTTPS destinations on the verified page host",
            "no browser profile, cookies, saved passwords, login state, scripts, forms, clicks, downloads",
            "submit its exact Open command and review the existing one-time browser approval",
        ):
            self.assertIn(marker, self.research_host)

    def test_bounded_link_follow_is_isolated_and_exposed_in_desktop(self):
        for marker in (
            'IsWebFollowRequest("Web: follow https://example.org/ : 1")',
            '"ISOLATED · FOLLOW LINK"',
            'bool webFollow = ResearchTranscript.IsWebFollowRequest(input)',
            'no browser profile, cookies, login state, scripts, forms, downloads',
        ):
            self.assertIn(marker, self.research_host)
        for marker in (
            "WebFollowButton",
            "06  FOLLOW LINK",
            "Web: follow https:// : 1",
            "CORE PREVIEW 10.20.3 / MONOCHROME SIGNAL",
        ):
            self.assertIn(marker, self.host)

    def test_public_form_inspection_is_exposed_without_submission(self):
        for marker in (
            'IsWebFormsRequest("Web: forms https://example.org/")',
            '"ISOLATED · FORM INSPECTION"',
            'bool webForms = ResearchTranscript.IsWebFormsRequest(input)',
            'This route cannot fill or submit a form',
        ):
            self.assertIn(marker, self.research_host)
        for marker in ("WebFormsButton", "07  INSPECT FORMS", "Web: forms https://",
                       "CORE PREVIEW 10.20.3 / MONOCHROME SIGNAL"):
            self.assertIn(marker, self.host)

    def test_bounded_site_search_is_exposed_without_browser_state(self):
        for marker in (
            'IsWebSearchRequest("Web: search https://example.org/ : chess")',
            '"ISOLATED · SITE SEARCH"',
            'bool webSearch = ResearchTranscript.IsWebSearchRequest(input)',
            "No POST, hidden fields, login, browser profile, cookies, scripts, local model",
        ):
            self.assertIn(marker, self.research_host)
        for marker in ("WebSearchButton", "08  SITE SEARCH", "Web: search https:// : ",
                       "CORE PREVIEW 10.20.3 / MONOCHROME SIGNAL"):
            self.assertIn(marker, self.host)
        for marker in (
            "Web: links PUBLIC-HTTPS-URL",
            "MAP LINKS",
            "Inspect before opening",
            "at most six visible eligible same-site HTTPS links",
            "existing one-time browser approval",
        ):
            self.assertIn(marker, self.host)

    def test_deterministic_read_only_windows_observation_bypasses_model_discovery(self):
        for marker in (
            "internal static class WindowsObservationRouter",
            "internal sealed partial class LocalWindowsObservation",
            "WindowsObservationKind.RegisteredApplications",
            "WindowsObservationKind.VisibleWindows",
            "WindowsObservationKind.ForegroundWindow",
            "BeginLocalObservation(observationRequest)",
            "DIRECT · WINDOWS OBSERVATION",
            "without model inference",
            "EnumWindows",
            "GetForegroundWindow",
            '"windows_apps_path"',
        ):
            self.assertIn(marker, self.host)
        begin = self.host.split("private void BeginRequest()", 1)[1].split(
            "private static string NormalizeRunState", 1
        )[0]
        self.assertLess(
            begin.index("WindowsObservationRouter.TrySelect"),
            begin.index("Router.Select"),
        )
        direct = self.host.split("private void BeginLocalObservation", 1)[1].split(
            "private static string NormalizeRunState", 1
        )[0]
        for forbidden in (
            "hermes.StartRunAsync",
            "Process.Start",
            "SetForegroundWindow",
            "SendInput",
            "BitBlt",
        ):
            self.assertNotIn(forbidden, direct)
        self.assertIn('WindowsObservationRouter.TrySelect("Launch Notepad"', self.host)
        self.assertIn("install_cypher_core_preview_windows.ps1", self.direct_observation_launcher)
        self.assertIn("-ExecutionPolicy Bypass", self.direct_observation_launcher)

    def test_deterministic_windows_control_requires_fresh_native_approval_and_verification(self):
        for marker in (
            "internal static class WindowsControlRouter",
            "WindowsControlKind.LaunchRegisteredApplication",
            "WindowsControlKind.FocusVisibleWindow",
            "TryPrepareControl(requestedText",
            "BeginLocalWindowsControl(controlRequest)",
            "DIRECT · APPROVED WINDOWS CONTROL",
            "ResolveLocalWindowsApproval",
            "ExecuteApprovedControl",
            "Content='APPROVE ONCE'",
            "Fingerprint(prepared)",
            "Sha256File",
            "ExpiresAtUtc = now.AddSeconds(60)",
            "request.Consumed = true",
            "SetForegroundWindow",
            "GetForegroundWindow() == handle",
            "UseShellExecute = false",
            "Matching titled window observed",
            "bool verified = observed != null || processRunning",
            "Executable:",
            "SHA-256",
            "cannot be replayed",
            "LooksLikeFocusRequest",
            "Focus the window with ID: 12345.",
            "No currently visible window has ID",
            "not the list position",
            "literal <ID> placeholder",
        ):
            self.assertIn(marker, self.host)
        begin = self.host.split("private void BeginRequest()", 1)[1].split(
            "private void BeginLocalObservation", 1
        )[0]
        self.assertLess(
            begin.index("windowsObservation.TryPrepareControl"),
            begin.index("Router.Select"),
        )
        execute = self.host.split("public WindowsControlResult ExecuteApprovedControl", 1)[1].split(
            "private static string CapabilityStatus", 1
        )[0]
        for forbidden in (
            ".Arguments =",
            "SendInput",
            "mouse_event",
            "BitBlt",
            ".Kill(",
            "powershell.exe",
            "cmd.exe",
        ):
            self.assertNotIn(forbidden, execute)
        self.assertIn("install_cypher_core_preview_windows.ps1", self.direct_control_launcher)
        self.assertIn("Parser]::ParseFile", self.direct_control_launcher)
        self.assertIn("install_cypher_core_preview_windows.ps1", self.focus_routing_launcher)
        self.assertIn("Parser]::ParseFile", self.focus_routing_launcher)

    def test_bounded_ui_automation_is_registered_app_only_and_approval_gated(self):
        for marker in (
            "using System.Windows.Automation;",
            "WindowsObservationKind.InteractiveControls",
            "AutomationElement.FromHandle",
            "TreeWalker.ControlViewWalker",
            "const int maximumExamined = 600",
            "const int maximumDepth = 6",
            "ReadAutomationControls(window, 120",
            "ResolveRegisteredWindow",
            "IsSensitiveAutomationProcess",
            "info.IsPassword",
            "info.ControlType == ControlType.Edit",
            "info.ControlType == ControlType.Document",
            "InvokePattern.Pattern",
            "TogglePattern.Pattern",
            "SelectionItemPattern.Pattern",
            "ExpandCollapsePattern.Pattern",
            "cypher-bounded-uia-v1",
            "cypher-windows-control-v5",
            "DIRECT · APPROVED UI AUTOMATION",
            "Exact app, executable, window, control, and pattern were revalidated",
            "request.Consumed = true",
            "ExpiresAtUtc = now.AddSeconds(60)",
            "No raw mouse, keyboard, screenshot, shell, or text entry was used.",
            "SHGetPropertyStoreForWindow",
            "AppUserModelID",
            "ValidAppUserModelId",
            "^[A-Za-z0-9][A-Za-z0-9._!+\\-]{0,127}$",
            "duplicate AppUserModelID",
            "duplicate executable",
            "SetAutomationValue",
            "ValuePattern.SetValue",
            "allow_text_entry",
            "Existing control text was not read",
            "No raw mouse, keyboard, clipboard, screenshot, shell, or persisted text content was used",
        ):
            self.assertIn(marker, self.host)
        for blocked_process in (
            '"credentialuibroker"',
            '"logonui"',
            '"winlogon"',
            '"lsass"',
            '"bitwarden"',
            '"1password"',
            '"keepass"',
        ):
            self.assertIn(blocked_process, self.host)
        for forbidden in (
            "SendInput",
            "mouse_event",
            "keybd_event",
            "TextPattern.Pattern",
            "CaptureScreen",
        ):
            self.assertNotIn(forbidden, self.host)
        self.assertIn("ValuePattern.Pattern", self.host)
        self.assertNotIn("LegacyIAccessiblePattern", self.host)
        self.assertNotIn("LegacyValueAvailable", self.host)
        self.assertNotIn("SendKeys", self.host)
        # The resident shell retains its explicit Copy Last Response button.
        # Computer-control execution itself must never use the clipboard.
        execute_automation = self.host.split(
            "private WindowsControlResult ExecuteAutomationControl", 1
        )[1].split("public WindowsControlResult ExecuteApprovedControl", 1)[0]
        self.assertNotIn("Clipboard.Set", execute_automation)
        self.assertEqual(self.host.count("Clipboard.SetText(lastResponse)"), 1)
        self.assertIn(
            "install_cypher_core_preview_windows.ps1",
            self.ui_automation_launcher,
        )
        self.assertIn("Parser]::ParseFile", self.ui_automation_launcher)
        self.assertIn(
            "install_cypher_core_preview_windows.ps1",
            self.text_entry_launcher,
        )
        self.assertIn("Parser]::ParseFile", self.text_entry_launcher)
        self.assertIn(
            "install_cypher_core_preview_windows.ps1",
            self.natural_workflow_launcher,
        )
        self.assertIn("Parser]::ParseFile", self.natural_workflow_launcher)
        self.assertIn("natural Windows workflow", self.natural_workflow_launcher)

    def test_text_entry_uses_only_framework_managed_value_pattern(self):
        self.assertIn("ValuePattern.Pattern", self.host)
        self.assertIn("ValuePattern.SetValue", self.host)
        self.assertNotIn("LegacyIAccessiblePattern", self.host)
        self.assertNotIn("LegacyValueAvailable", self.host)

    def test_natural_registered_app_write_is_one_approval_no_id_workflow(self):
        for marker in (
            "WriteTextInRegisteredApplication",
            "ResolveRegisteredApplicationTarget",
            "FindRegisteredApplicationWindows",
            "EligibleTextControls",
            "ExecuteNaturalTextWorkflow",
            "single-existing-or-single-new-editor-v1",
            "cypher-windows-control-v5",
            "DIRECT · APPROVED APP WORKFLOW",
            "More than one registered ",
            "exposes multiple editable controls",
            "launch the registered executable without arguments only when no matching window exists",
            "Open Notepad and write: Cypher natural workflow passed.",
        ):
            self.assertIn(marker, self.host)

        parser = self.host.split("public static bool TryParse", 1)[1].split(
            "private static string NormalizeAppTarget", 1
        )[0]
        self.assertLess(
            parser.index("Match naturalWrite"),
            parser.index("Match setText"),
        )
        self.assertIn("textValue.Length <= 500", parser)
        self.assertIn("Regex.IsMatch(textValue", parser)

        prepare = self.host.split("public bool TryPrepareControl", 1)[1].split(
            "private static bool PatternAvailable", 1
        )[0]
        self.assertIn("if (!selected.AllowTextEntry)", prepare)
        self.assertIn("if (matches.Count > 1)", prepare)
        self.assertIn("if (editors.Count > 1)", prepare)
        self.assertIn("ExpiresAtUtc = now.AddSeconds(60)", prepare)
        self.assertIn("prepared.Fingerprint = Fingerprint(prepared)", prepare)

        natural = self.host.split("private WindowsControlResult ExecuteNaturalTextWorkflow", 1)[1].split(
            "private WindowsControlResult ExecuteApprovedHttpsOpen", 1
        )[0]
        for marker in (
            "RevalidateApplication(request)",
            "ValidateApprovedText(request)",
            "currentMatches.Count > 1",
            "editors.Count > 1",
            "BindAutomationTarget(request, targetWindow, targetControl)",
            "ExecuteAutomationControl(request)",
            "start.FileName = selected.ExecutablePath",
            "start.UseShellExecute = false",
        ):
            self.assertIn(marker, natural)
        for forbidden in (
            ".Arguments =",
            "SendInput",
            "Clipboard",
            "SendKeys",
            "powershell.exe",
            "cmd.exe",
        ):
            self.assertNotIn(forbidden, natural)

        execute = self.host.split("public WindowsControlResult ExecuteApprovedControl", 1)[1].split(
            "private static string CapabilityStatus", 1
        )[0]
        self.assertIn("request.Consumed", execute)
        self.assertIn("Fingerprint(request)", execute)
        self.assertIn("ExecuteNaturalTextWorkflow(request)", execute)
        self.assertIn("request.TextValue = null", execute)
        self.assertIn('version = "0.7.0-core-preview10.20.3"', self.installer)
        self.assertIn("Core Preview 10.20.3", self.installer)
        self.assertIn("Core Preview 10.20.3", self.manager)
        self.assertIn("Research papers:", self.installer)
        self.assertIn("keyless official OpenAlex Works request", self.installer)
        self.assertIn("exact OpenAlex HTTP 503", self.installer)
        self.assertIn("keyless Crossref Works request", self.installer)
        self.assertIn("reserved ? and * wildcard characters", self.installer)
        self.assertIn("selects the strongest at most two", self.installer)
        self.assertIn("both extracted concepts and relationship wording in one cited passage", self.installer)
        self.assertIn("no extra provider request or model call", self.installer)
        self.assertIn("no action tools", self.installer.lower())

    def test_registered_app_https_open_is_deterministic_approved_and_bounded(self):
        for marker in (
            "OpenHttpsInRegisteredApplication",
            "TryNormalizeHttpsDestination",
            "LooksLikeHttpsOpenRequest",
            "exact-registered-app-one-public-https-v1",
            "exact-auto-discovered-browser-one-public-https-v1",
            "ResolveKnownBrowserTarget",
            "ValidateApprovedHttpsDestination",
            "ExecuteApprovedHttpsOpen",
            "DIRECT · APPROVED HTTPS OPEN",
            "auto-discovered browser",
            "Cypher did not read the address bar or page contents",
            "open brave then search chess.com",
            "https://chess.com/",
        ):
            self.assertIn(marker, self.host)

        parser = self.host.split("public static bool TryParse", 1)[1].split(
            "private static string NormalizeAppTarget", 1
        )[0]
        self.assertLess(parser.index("Match openHttps"), parser.index("Match naturalWrite"))
        self.assertIn("TryNormalizeHttpsDestination", parser)
        self.assertIn("return false;", parser)

        prepare = self.host.split("public bool TryPrepareControl", 1)[1].split(
            "private static bool PatternAvailable", 1
        )[0]
        self.assertLess(
            prepare.index("OpenHttpsInRegisteredApplication"),
            prepare.index("WriteTextInRegisteredApplication"),
        )
        self.assertIn("Cypher can auto-discover Brave, Edge, Chrome, and Firefox", prepare)
        self.assertLess(prepare.index("ResolveRegisteredApplicationTarget"), prepare.index("ResolveKnownBrowserTarget"))
        self.assertIn("TextHash = Sha256Text(intent.TextValue)", prepare)
        self.assertIn("ExpiresAtUtc = now.AddSeconds(60)", prepare)

        https_open = self.host.split(
            "private WindowsControlResult ExecuteApprovedHttpsOpen", 1
        )[1].split("public WindowsControlResult ExecuteApprovedControl", 1)[0]
        self.assertLess(
            https_open.index("ValidateApprovedHttpsDestination(request)"),
            https_open.index("Process.Start(start)"),
        )
        self.assertEqual(https_open.count("start.Arguments ="), 1)
        self.assertIn("start.UseShellExecute = false", https_open)
        self.assertIn("FindRegisteredApplicationWindows(selected)", https_open)
        for forbidden in (
            "UseShellExecute = true",
            "powershell.exe",
            "cmd.exe",
            "SendInput",
            "Clipboard",
        ):
            self.assertNotIn(forbidden, https_open)

        discovery = self.host.split("private static RegisteredAppRecord ResolveKnownBrowserTarget", 1)[1].split(
            "private static bool SameRegisteredApplication", 1
        )[0]
        for marker in (
            "auto-browser-brave", "BraveSoftware\\Brave-Browser\\Application\\brave.exe",
            "auto-browser-edge", "Microsoft\\Edge\\Application\\msedge.exe",
            "auto-browser-chrome", "Google\\Chrome\\Application\\chrome.exe",
            "auto-browser-firefox", "Mozilla Firefox\\firefox.exe",
            "Environment.SpecialFolder.ProgramFiles", "Environment.SpecialFolder.ProgramFilesX86",
            "Environment.SpecialFolder.LocalApplicationData", "FileAttributes.ReparsePoint",
        ):
            self.assertIn(marker, discovery)
        for forbidden in ("PATH", "Registry", "UseShellExecute", "Process.Start", "cmd.exe", "powershell.exe"):
            self.assertNotIn(forbidden, discovery)

    def test_bounded_web_search_is_fixed_provider_reviewed_and_integrity_bound(self):
        for marker in (
            "TryBuildWebSearchDestination",
            "https://duckduckgo.com/?q=",
            "exact-registered-app-one-public-web-search-v1",
            "exact-auto-discovered-browser-one-public-web-search-v1",
            "SearchQueryLength",
            "SearchQueryHash",
            'SearchProvider = intent.WebSearch ? "DuckDuckGo" : null',
            "DIRECT · APPROVED WEB SEARCH",
            "Query sent to DuckDuckGo",
            "containing the reviewed DuckDuckGo query",
        ):
            self.assertIn(marker, self.host)

        parser = self.host.split("public static bool TryParse", 1)[1].split(
            "private static string NormalizeAppTarget", 1
        )[0]
        self.assertLess(parser.index("Match directSearch"), parser.index("Match openHttps"))
        self.assertIn("search(?:\\s+the\\s+web)?", parser)
        self.assertIn("openHttps.Groups[2].Value.StartsWith", parser)
        self.assertIn("TryNormalizeHttpsDestination(openHttps.Groups[3].Value", parser)

        validator = self.host.split("private static void ValidateApprovedHttpsDestination", 1)[1].split(
            "public bool TryPrepareControl", 1
        )[0]
        self.assertIn("TryBuildWebSearchDestination(request.SearchQuery", validator)
        self.assertIn("Sha256Text(request.SearchQuery)", validator)
        self.assertIn("string.Equals(searchDestination, request.TextValue", validator)
        self.assertIn("unexpected search data", validator)

        execute = self.host.split("private WindowsControlResult ExecuteApprovedHttpsOpen", 1)[1].split(
            "public WindowsControlResult ExecuteApprovedControl", 1
        )[0]
        self.assertEqual(execute.count("start.Arguments ="), 1)
        self.assertIn("start.UseShellExecute = false", execute)
        for forbidden in ("WebView", "page contents =", "SendInput", "Clipboard", "UseShellExecute = true"):
            self.assertNotIn(forbidden, execute)

    def test_window_title_is_advisory_but_stable_window_identity_remains_bound(self):
        revalidate = self.host.split(
            "private static WindowRecord RevalidateWindow", 1
        )[1].split("private AutomationControlRecord RevalidateAutomationControl", 1)[0]
        self.assertIn(
            "current.ProcessId != request.WindowProcessId || current.ClassName != request.WindowClass",
            revalidate,
        )
        self.assertNotIn("current.Title != request.WindowTitle", revalidate)
        self.assertIn("top-level title is presentation metadata", revalidate)
        self.assertIn("approved stable window identity changed", revalidate)
        # The originally displayed title remains inside the one-time approval fingerprint;
        # only the live equality check is removed because packaged apps may refresh it.
        fingerprint = self.host.split("private static string Fingerprint", 1)[1].split(
            "private RegisteredAppRecord ResolveRegisteredApplicationTarget", 1
        )[0]
        self.assertIn("AppendCanonical(canonical, request.WindowTitle)", fingerprint)

    def test_packaged_identity_falls_back_from_window_to_process_aumid(self):
        for marker in (
            "GetApplicationUserModelId",
            "ProcessQueryLimitedInformation = 0x1000",
            "OpenProcess(ProcessQueryLimitedInformation",
            "ReadProcessAppUserModelId",
            "ErrorInsufficientBuffer = 122",
            "CloseHandle(process)",
        ):
            self.assertIn(marker, self.host)
        observation = self.host.split("private static List<WindowRecord> ObserveWindows", 1)[1].split(
            "private static string FormatWindow", 1
        )[0]
        self.assertLess(
            observation.index("ReadWindowAppUserModelId(handle)"),
            observation.index("ReadProcessAppUserModelId(processId)"),
        )
        self.assertIn("string.IsNullOrWhiteSpace(appUserModelId)", observation)

    def test_exact_packaged_identity_is_resolved_before_main_module_access(self):
        resolver = self.host.split("private RegisteredAppRecord ResolveRegisteredWindow", 1)[1].split(
            "private static AutomationControlRecord ReadAutomationControl", 1
        )[0]
        self.assertIn("string.Equals(item.AppUserModelId, window.AppUserModelId, StringComparison.Ordinal)", resolver)
        self.assertLess(
            resolver.index("applications.Find"),
            resolver.index("TryReadProcessExecutablePath"),
        )
        self.assertIn(
            "string.Equals(item.ExecutablePath, executablePath, StringComparison.OrdinalIgnoreCase)",
            resolver,
        )

    def test_direct_observation_failure_shows_only_safe_diagnostic_code(self):
        self.assertIn("private static string WindowsObservationFailureCode", self.host)
        direct = self.host.split("private void BeginLocalObservation", 1)[1].split(
            "private void BeginLocalWindowsControl", 1
        )[0]
        self.assertIn("Diagnostic code: \" + diagnosticCode", direct)
        self.assertNotIn("ex.Message", direct)
        for code in (
            "WINDOW_TARGET_STALE",
            "WINDOW_IDENTITY_UNVERIFIED",
            "WINDOW_UIA_UNAVAILABLE",
            "WINDOW_OBSERVATION_FAILED",
        ):
            self.assertIn(code, self.host)

    def test_installer_resolves_ui_automation_references_to_full_paths(self):
        for assembly, variable in (
            ("UIAutomationClient.dll", "uiAutomationClientPath"),
            ("UIAutomationTypes.dll", "uiAutomationTypesPath"),
        ):
            self.assertIn(
                f'${variable} = Resolve-FrameworkAssembly "{assembly}"',
                self.installer,
            )
            self.assertIn(f'"/reference:${variable}"', self.installer)
            self.assertNotIn(f'"/reference:{assembly}"', self.installer)

    def test_each_request_uses_a_fresh_hermes_session_with_explicit_history(self):
        begin = self.host.split("private void BeginRequest()", 1)[1].split(
            "private static string NormalizeRunState", 1
        )[0]
        self.assertIn('string runSessionId = "cypher-run-" + Guid.NewGuid()', begin)
        self.assertIn("hermes.StartRunAsync(route, runSessionId, historySnapshot)", begin)
        self.assertIn('payload["conversation_history"] = history;', self.host)
        self.assertNotIn('GetSetting(settings, "session_id"', self.host)
        self.assertNotIn("session_id =", self.installer)

    def test_core_forbids_hidden_session_recovery_from_overriding_current_task(self):
        self.assertIn("Every submitted chat task uses a fresh Hermes session", self.host)
        self.assertIn("explicit bounded successful-turn history", self.host)
        self.assertIn("never infer an unfinished task from hidden or server-side session state", self.host)

    def test_voice_hotkey_keeps_compact_resizable_chat_panel_and_open_animation(self):
        for forbidden in (
            "private Window BuildWidgetWindow()",
            "widgetWindow",
            "widgetStatusDot",
            "FLOATING CORE",
            "Show / hide Cypher",
        ):
            self.assertNotIn(forbidden, self.host)
        self.assertIn("private void ActivateVoiceHotkey()", self.host)
        self.assertIn("private void ToggleExpanded()", self.host)
        self.assertIn("private void TogglePin()", self.host)
        self.assertIn("Width='1120' Height='720'", self.host)
        self.assertIn("MinWidth='760' MinHeight='560'", self.host)
        self.assertIn("WindowStartupLocation='CenterScreen'", self.host)
        self.assertIn("ShowInTaskbar='False' Topmost='False'", self.host)
        for marker in (
            "private void AnimateWindowOpen(ScaleTransform scale)",
            "TimeSpan.FromMilliseconds(160)",
            "QuadraticEase",
            "EasingMode.EaseOut",
            "DoubleAnimation",
        ):
            self.assertIn(marker, self.host)
        hotkey_block = self.host.split("private IntPtr WindowProcedure", 1)[1].split(
            "private Dictionary<string, object> ReadSettings", 1
        )[0]
        self.assertIn("ActivateVoiceHotkey()", hotkey_block)

        tray_block = self.host.split("private WF.NotifyIcon BuildTray()", 1)[1].split(
            "private void BeginRequest", 1
        )[0]
        self.assertIn('new WF.ToolStripMenuItem("Open command center (Ctrl+Win+Alt)")', tray_block)
        self.assertIn("open.Click += delegate { Ui(ShowWindow); };", tray_block)
        self.assertNotIn("ToggleWindow", tray_block)
        self.assertIn("icon.DoubleClick += delegate { Ui(ShowWindow); };", tray_block)

    def test_modifier_only_chat_chord_filters_keys_without_logging_typing(self):
        registration = self.host.split("bool registered = RegisterHotKey", 1)[1].split("heartbeatTimer.Start()", 1)[0]
        callback = self.host.split("private IntPtr OnKeyboardEvent(", 1)[1].split("private Dictionary<string, object> ReadSettings()", 1)[0]
        self.assertIn("SetWindowsHookEx(WhKeyboardLl, keyboardCallback", registration)
        self.assertIn("keyboardHook != IntPtr.Zero", self.host)
        self.assertIn("UnhookWindowsHookEx(keyboardHook)", self.host)
        self.assertIn("key == VkControl || key == VkLeftControl || key == VkRightControl", callback)
        self.assertIn("key == VkLeftWin || key == VkRightWin", callback)
        self.assertIn("key == VkAlt || key == VkLeftAlt || key == VkRightAlt", callback)
        self.assertIn("else return CallNextHookEx", callback)
        self.assertIn("chatChordArmed = false", callback)
        self.assertIn("window.Dispatcher.BeginInvoke(new Action(ShowWindow))", callback)
        self.assertNotIn("WriteEvent(", callback)
        self.assertNotIn("GetAsyncKeyState", self.host)

    def test_hidden_voice_approval_reveals_review_without_bypassing_it(self):
        hotkey = self.host.split("private void ActivateVoiceHotkey()", 1)[1].split("private void ShowWindow()", 1)[0]
        self.assertIn("AcknowledgeWake();", hotkey)
        self.assertNotIn("ShowWindow();", hotkey)
        self.assertIn("!string.IsNullOrWhiteSpace(inputBox.Text)", hotkey)
        helper = self.host.split("private void RevealApprovalCard()", 1)[1].split("private void AnimateWindowOpen", 1)[0]
        self.assertIn("approvalCard.Visibility = Visibility.Visible;", helper)
        self.assertIn("else ShowWindow();", helper)
        self.assertIn("RevealApprovalCard();", self.host)
        for path in ("FileTaskHost.cs", "WindowsWorkflowHost.cs"):
            source = (ROOT / "windows" / "Cypher.CorePreview" / path).read_text(encoding="utf-8")
            self.assertIn("RevealApprovalCard();", source)

    def test_ui_state_persists_geometry_only_without_conversation_content(self):
        self.assertIn('uiStatePath = Path.Combine(installRoot, "ui-state.json")', self.host)
        save_block = self.host.split("private void SaveUiState()", 1)[1].split(
            "private void TogglePin()", 1
        )[0]
        for key in (
            "layout_version",
            "chat_left",
            "chat_top",
            "chat_width",
            "chat_height",
            "pinned",
        ):
            self.assertIn(f'"{key}"', save_block)
        for forbidden in (
            "widget_left",
            "widget_top",
            "userText",
            "assistantText",
            "responseBox",
            "inputBox",
            "history",
        ):
            self.assertNotIn(forbidden, save_block)

    def test_task_checkpoint_is_metadata_only_bounded_and_atomic(self):
        self.assertIn('taskCheckpointPath = Path.Combine(installRoot, "active-task.json")', self.host)
        store = self.host.split("internal sealed class TaskCheckpointStore", 1)[1].split(
            "internal sealed partial class CypherHost", 1
        )[0]
        save = store.split("public void Save(TaskCheckpoint checkpoint)", 1)[1].split(
            "public bool TryLoad", 1
        )[0]
        expected = {
            "schema_version",
            "run_id",
            "model_profile",
            "phase",
            "state",
            "started_at_utc",
            "updated_at_utc",
            "tool_started",
            "tool_completed",
            "tool_failed",
        }
        for key in expected:
            self.assertIn(f'"{key}"', save)
        for forbidden in (
            'value["prompt"]',
            'value["input"]',
            'value["output"]',
            'value["response"]',
            "lastResponse",
            "responseBox",
            "history",
            "tool_argument",
            "filename",
            "approvalSummaryText",
        ):
            self.assertNotIn(forbidden, save)
        self.assertIn("MaxCheckpointBytes = 16384", store)
        self.assertIn("File.Replace(temporaryPath, path, null)", store)
        self.assertIn("unexpected_field", store)
        self.assertIn("expired_checkpoint", store)
        self.assertIn("TaskCheckpointStore.SelfTest()", self.host)

    def test_terminal_failures_create_only_a_content_free_diagnostic_receipt(self):
        self.assertIn('failureReceiptPath = Path.Combine(installRoot, "last-failure.json")', self.host)
        store = self.host.split("internal sealed class FailureReceiptStore", 1)[1].split(
            "internal sealed partial class CypherHost", 1
        )[0]
        save = store.split("public void Save(FailureReceipt receipt)", 1)[1].split(
            "public bool TryLoad", 1
        )[0]
        for key in (
            "schema_version",
            "run_id",
            "model_profile",
            "failure_stage",
            "failed_at_utc",
            "tool_started",
            "tool_completed",
            "tool_failed",
            "response_observed",
        ):
            self.assertIn(f'"{key}"', save)
        for forbidden in (
            'value["prompt"]',
            'value["input"]',
            'value["output"]',
            'value["response"]',
            "lastResponse",
            "responseBox",
            "history",
            "tool_argument",
            "filename",
            "approvalSummaryText",
            "error_message",
        ):
            self.assertNotIn(forbidden, save)
        self.assertIn("MaxReceiptBytes = 8192", store)
        self.assertIn("File.Replace(temporaryPath, path, null)", store)
        self.assertIn("unexpected_field", store)
        self.assertIn("FailureReceiptStore.SelfTest()", self.host)
        self.assertIn('SaveFailureReceipt(runId)', self.host)
        self.assertIn('"before_tool"', self.host)
        self.assertIn('"tool_failed"', self.host)
        self.assertIn('"tool_incomplete"', self.host)
        self.assertIn('"after_tool"', self.host)
        self.assertIn('"response_generation"', self.host)

    def test_manager_displays_only_whitelisted_failure_metadata(self):
        for marker in (
            '"failure-status"',
            '"last-failure.json"',
            "Cypher content-free failure receipt",
            "No prompt, answer, filename, path, tool argument, approval content, provider error text, or credential",
        ):
            self.assertIn(marker, self.manager)
        read = self.manager.split("function Read-FailureReceiptMetadata", 1)[1].split(
            "function Stop-Preview", 1
        )[0]
        for forbidden in ("Get-Content -Path", "Select-String", "agent.log", "gateway.log"):
            self.assertNotIn(forbidden, read)
        self.assertIn("@($value.PSObject.Properties).Count", read)
        self.assertNotIn("$value.PSObject.Properties.Count -ne", read)

    def test_bounded_tool_repair_is_explicit_reversible_and_does_not_broaden_authority(self):
        for marker in (
            "CONFIGURE BOUNDED CYPHER TOOLS",
            "tools.tool_search.enabled on",
            "tools.tool_search.listing on",
            "hermes gateway restart",
            "hermes mcp test hermes-sandbox",
            "Restore-PreviousModes",
            "normal, non-administrator",
        ):
            self.assertIn(marker, self.tool_config)
        for forbidden in (
            "approvals.mode",
            "security.allow_lazy_installs",
            "operator_permissions",
            "operator_roots",
            "terminal.enabled",
            "file.enabled",
            "RunAs",
            "Remove-Item -Recurse",
            "Stop-Process",
        ):
            self.assertNotIn(forbidden, self.tool_config)

    def test_window_state_loader_has_no_duplicate_local_declarations(self):
        loader = self.host.split("private void LoadUiState()", 1)[1].split(
            "private void SaveUiState()", 1
        )[0]
        declarations = re.findall(
            r"^\s*(?:double|bool|string|object|Rect|Dictionary<[^>]+>)\s+([A-Za-z_][A-Za-z0-9_]*)\s*=",
            loader,
            re.MULTILINE,
        )
        duplicates = sorted({name for name in declarations if declarations.count(name) > 1})
        self.assertEqual(duplicates, [], f"duplicate local declarations: {duplicates}")

    def test_restart_recovery_queries_hermes_and_never_guesses_completion(self):
        recovery = self.host.split("private async Task RecoverCheckpointAsync()", 1)[1].split(
            "private async Task ConsumeEventsAsync", 1
        )[0]
        for marker in (
            "taskCheckpointStore.TryLoad",
            "hermes.GetRunAsync(runId)",
            "NormalizeRunState",
            "IsTerminalRunState",
            "CompleteRecoveredRun",
            "RECOVERY REQUIRED",
            "The checkpoint remains intact and no completion is claimed.",
            "retryRecoveryButton",
        ):
            self.assertIn(marker, recovery)
        self.assertIn("await RecoverCheckpointAsync()", self.host)
        self.assertIn("PersistCheckpoint(\"STOPPING\", \"stopping\")", self.host)
        self.assertIn("ClearCheckpoint();", self.host)

    def test_manager_exposes_only_explicit_checkpoint_review_and_forget(self):
        for marker in (
            '"checkpoint-status"',
            '"forget-checkpoint"',
            "FORGET RECOVERY CHECKPOINT",
            "It does not stop or modify any Hermes run.",
            "No prompt, answer, filename, tool argument, or approval content",
        ):
            self.assertIn(marker, self.manager)
        forget = self.manager.split('"forget-checkpoint" {', 1)[1].split(
            '"rollback" {', 1
        )[0]
        self.assertIn('(Get-PreviewState) -ne "stopped"', forget)
        self.assertNotIn("Stop-Process", forget)

    def test_installer_builds_and_tests_before_switching_startup(self):
        self.assertIn("/target:winexe", self.installer)
        self.assertIn("--self-test", self.installer)
        self.assertIn("function Resolve-CypherPython312", self.installer)
        self.assertIn('"Programs\\Python\\Python312\\python.exe"', self.installer)
        self.assertIn("$researchPythonPath = Resolve-CypherPython312", self.installer)
        self.assertIn("& $researchPythonPath -m unittest discover", self.installer)
        self.assertIn('"test_cypher_core.py"', self.installer)
        self.assertIn('"test_cypher_core_windows.py"', self.installer)
        self.assertIn('"test_windows_operator.py"', self.installer)
        compile_at = self.installer.index("& $cscPath $compilerArguments")
        stop_at = self.installer.index("\n    Stop-LegacyHost\n")
        shortcut_at = self.installer.index("$shortcut = $shell.CreateShortcut($shortcutPath)")
        self.assertLess(compile_at, stop_at)
        self.assertLess(stop_at, shortcut_at)

    def test_compiled_host_starts_only_the_installer_pinned_local_ollama(self):
        runtime = self.host.split("internal static class LocalOllamaRuntime", 1)[1].split(
            "internal static class CoreIdentity", 1
        )[0]
        for marker in (
            'HealthEndpoint = "http://127.0.0.1:11434/api/version"',
            'StartArguments = "serve"',
            "request.Proxy = null",
            "request.AllowAutoRedirect = false",
            "HashFile(fullPath)",
            "FileAttributes.ReparsePoint",
            "start.FileName = fullPath",
            "start.Arguments = StartArguments",
            "start.UseShellExecute = false",
            "start.CreateNoWindow = true",
            'start.EnvironmentVariables["OLLAMA_HOST"] = "127.0.0.1:11434"',
            "DateTime.UtcNow.AddSeconds(25)",
            "OLLAMA_EXECUTABLE_CHANGED",
        ):
            self.assertIn(marker, runtime)
        for forbidden in ("powershell", "cmd.exe", " /c ", "ollama pull", "ollama run"):
            self.assertNotIn(forbidden, runtime.lower())
        constructor = self.host.split("public CypherHost(string root)", 1)[1].split("public void Run()", 1)[0]
        self.assertIn("LocalOllamaRuntime.EnsureReady", constructor)
        self.assertLess(constructor.index("LocalOllamaRuntime.EnsureReady"), constructor.index("new HermesClient"))
        for marker in (
            'Get-Command "ollama.exe" -CommandType Application',
            'Programs\\Ollama\\ollama.exe',
            "$ollamaItem.Attributes -band [IO.FileAttributes]::ReparsePoint",
            "Get-FileHash -LiteralPath $ollamaPath -Algorithm SHA256",
            "ollama_executable_path = $ollamaPath",
            "ollama_executable_sha256 = $ollamaHash",
            "AddSeconds(35)",
        ):
            self.assertIn(marker, self.installer)

    def test_installer_is_complete_and_launcher_parses_it_before_execution(self):
        self.assertIn("$shortcut.Save()", self.installer)
        self.assertIn("Start-Process -FilePath $installedExe", self.installer)
        self.assertIn("[PASS] Cypher Core Preview is running.", self.installer)
        self.assertTrue(
            self.installer.rstrip().endswith(
                "Remove-Item -LiteralPath $buildRoot -Recurse -Force -ErrorAction SilentlyContinue\n}"
            )
        )
        self.assertIn(
            "System.Management.Automation.Language.Parser]::ParseFile",
            self.direct_observation_launcher,
        )
        parser_at = self.direct_observation_launcher.index("Parser]::ParseFile")
        installer_at = self.direct_observation_launcher.index(
            '-File ".\\scripts\\install_cypher_core_preview_windows.ps1"'
        )
        self.assertLess(parser_at, installer_at)
        self.assertIn("if errorlevel 1", self.direct_observation_launcher)
        self.assertIn(
            "System.Management.Automation.Language.Parser]::ParseFile",
            self.https_open_launcher,
        )
        self.assertIn(
            '-File ".\\scripts\\install_cypher_core_preview_windows.ps1"',
            self.https_open_launcher,
        )
        self.assertIn("Cypher 10.2.0 Bounded Office Documents", self.https_open_launcher)
        self.assertIn("Parser]::ParseFile", self.office_launcher)
        self.assertIn('-File ".\\scripts\\install_cypher_core_preview_windows.ps1"', self.office_launcher)
        self.assertIn("Cypher 10.2.0 Bounded Office Documents", self.office_launcher)
        self.assertIn("Parser]::ParseFile", self.grounded_web_launcher)
        self.assertIn('-File ".\\scripts\\install_cypher_core_preview_windows.ps1"', self.grounded_web_launcher)
        self.assertIn("Cypher 10.4.0 Grounded Public Page Answers", self.grounded_web_launcher)
        self.assertIn("Parser]::ParseFile", self.navigation_launcher)
        self.assertIn('-File ".\\scripts\\install_cypher_core_preview_windows.ps1"', self.navigation_launcher)
        self.assertIn("Cypher 10.5.0 Bounded Public Page Navigation", self.navigation_launcher)

    def test_installer_resolves_wpf_references_to_verified_full_paths(self):
        self.assertIn("function Resolve-FrameworkAssembly", self.installer)
        self.assertIn('Join-Path $frameworkRoot "WPF"', self.installer)
        for assembly, variable in (
            ("WindowsBase.dll", "windowsBasePath"),
            ("PresentationCore.dll", "presentationCorePath"),
            ("PresentationFramework.dll", "presentationFrameworkPath"),
            ("System.Xaml.dll", "systemXamlPath"),
        ):
            self.assertIn(
                f'${variable} = Resolve-FrameworkAssembly "{assembly}"',
                self.installer,
            )
            self.assertIn(f'"/reference:${variable}"', self.installer)
            self.assertNotIn(f'"/reference:{assembly}"', self.installer)
        resolve_at = self.installer.index(
            '$windowsBasePath = Resolve-FrameworkAssembly "WindowsBase.dll"'
        )
        compile_at = self.installer.index("& $cscPath $compilerArguments")
        self.assertLess(resolve_at, compile_at)

    def test_installer_uses_current_user_dpapi_and_does_not_change_permissions(self):
        self.assertIn("ProtectedData]::Protect", self.installer)
        self.assertIn("DataProtectionScope]::CurrentUser", self.installer)
        self.assertIn("normal, non-administrator", self.installer)
        self.assertNotIn("RunAs", self.installer)
        self.assertNotIn("hermes config set", self.installer.lower())
        self.assertNotIn("hermes mcp", self.installer.lower())
        self.assertNotIn("API_SERVER_CORS_ORIGINS", self.installer)

    def test_rollback_is_exact_cooperative_and_preserves_other_components(self):
        self.assertIn("ROLLBACK TO V0.6.3", self.manager)
        self.assertIn("REMOVE CYPHER PREVIEW", self.manager)
        self.assertIn("stop.request", self.manager)
        self.assertIn("Refusing to remove an unexpected install path", self.manager)
        self.assertIn("rollback\\Local Assistant Host.v063.lnk", self.manager)
        self.assertNotIn("Stop-Process", self.manager)
        self.assertNotIn("taskkill", self.manager.lower())
        self.assertNotIn("ollama rm", self.manager.lower())

    def test_installer_cooperatively_stops_an_existing_preview_before_upgrade(self):
        self.assertIn("function Stop-ExistingPreviewHost", self.installer)
        self.assertIn('WriteAllText($stopRequestPath', self.installer)
        stop_at = self.installer.index("\n    Stop-ExistingPreviewHost\n")
        copy_at = self.installer.index(
            "Copy-Item -LiteralPath $builtExe -Destination $installedExe -Force"
        )
        self.assertLess(stop_at, copy_at)
        self.assertNotIn("Stop-Process", self.installer)
        self.assertIn('if ($previewStatus -eq "working")', self.installer)
        self.assertIn("active or recovering task", self.installer)


if __name__ == "__main__":
    unittest.main()
