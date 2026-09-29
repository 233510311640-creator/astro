using System;
using System.Text;
using System.Text.RegularExpressions;
using System.Threading;
using System.Threading.Tasks;
using System.Windows;

namespace Cypher.CorePreview
{
    internal sealed partial class CypherHost
    {
        private readonly WorkflowCheckpointStore workflowCheckpointStore;
        private volatile bool workflowActive;
        private WindowsWorkflowPlan pendingWorkflow;
        private CancellationTokenSource workflowCancellation;
        private string workflowInput;
        private string workflowPreview;

        private static bool IsWorkflowStatusRequest(string input)
        {
            return Regex.IsMatch(input ?? "", @"^\s*(?:show\s+(?:my\s+|the\s+|last\s+)?)?workflow\s+status[.!]?\s*$",
                RegexOptions.IgnoreCase | RegexOptions.CultureInvariant);
        }

        private static string WorkflowPreview(WindowsWorkflowPlan plan)
        {
            StringBuilder text = new StringBuilder("PROPOSED WORKFLOW\r\n");
            for (int i = 0; i < plan.Steps.Count; i++)
            {
                WorkflowStep step = plan.Steps[i];
                text.Append(i + 1).Append(". ");
                if (step.Action == WorkflowAction.WriteText)
                    text.Append("Replace the eligible editor's text in ").Append(step.AppLabel)
                        .Append(" [").Append(step.AppId).Append("] with exactly ").Append(step.TextValue.Length)
                        .Append(" characters:\r\n“").Append(step.TextValue).Append("”");
                else if (step.Action == WorkflowAction.Open)
                    text.Append("Open or reuse ").Append(step.AppLabel).Append(" [").Append(step.AppId).Append("].");
                else if (step.Action == WorkflowAction.Focus)
                    text.Append("Restore if minimized, then focus ").Append(step.AppLabel).Append(" [").Append(step.AppId).Append("].");
                else
                    text.Append(step.Action).Append(" ").Append(step.AppLabel).Append(" [").Append(step.AppId).Append("].");
                text.Append("\r\n");
            }
            text.Append("\r\nOne approval covers only these ordered steps. No automatic retry or restart replay.");
            text.Append("\r\nExecution starts after approval without an added countdown.");
            bool writes = false;
            foreach (WorkflowStep step in plan.Steps) if (step.Action == WorkflowAction.WriteText) writes = true;
            if (writes)
                text.Append("\r\nText entry REPLACES the editor's current contents. Use a blank document. Cypher does not read back, save, or undo the text.");
            text.Append("\r\nStop prevents later actions; an in-flight Windows action may finish. Completed changes remain.");
            return text.ToString();
        }

        private void BeginWorkflow(string input)
        {
            workflowActive = true;
            workflowInput = input;
            workflowCancellation = new CancellationTokenSource();
            CancellationToken token = workflowCancellation.Token;
            inputBox.Clear();
            HideApproval();
            SetInteractive(false);
            modelText.Text = "DIRECT · ORDERED WINDOWS WORKFLOW";
            lastResponse = "";
            SetStatus("PREPARING", "#58CFF5");
            UpdateTask("PLAN", "Checking all app identities and permissions before approval. No action has run.");
            responseBox.Text = "Preparing the ordered workflow. No app has been changed.";
            Task.Run(delegate
            {
                WindowsWorkflowPlan plan = null;
                try
                {
                    plan = windowsObservation.PrepareWorkflow(input, token);
                    token.ThrowIfCancellationRequested();
                    Ui(delegate
                    {
                        if (token.IsCancellationRequested)
                        {
                            plan.Reject();
                            FinishWorkflow("CANCELLED", "Workflow cancelled before approval. No action ran.", "#F3C969");
                            return;
                        }
                        pendingWorkflow = plan;
                        workflowPreview = WorkflowPreview(plan);
                        responseBox.Text = workflowPreview + "\r\n\r\nNo action has run. Review the complete plan below.";
                        approvalSummaryText.Text = workflowPreview;
                        approvalDetailsText.Text = windowsObservation.DescribeWorkflowBindings(plan) +
                            "Plan " + plan.Id.Substring(0, 12) + " · fingerprint " + plan.Fingerprint.Substring(0, 16) +
                            "… · expires at " + plan.ExpiresAtUtc.ToLocalTime().ToString("T") + " · no lasting permission";
                        approveOnceButton.IsEnabled = true;
                        denyApprovalButton.IsEnabled = true;
                        RevealApprovalCard();
                        SetStatus("APPROVAL REQUIRED", "#F3C969");
                        UpdateTask("WAITING APPROVAL", plan.Steps.Count + " ordered steps, exact app bindings, 60-second approval expiry.");
                    });
                    string id = plan.Id;
                    Task.Delay(TimeSpan.FromSeconds(61)).ContinueWith(delegate(Task ignored)
                    {
                        Ui(delegate
                        {
                            if (pendingWorkflow != null && pendingWorkflow.Id == id && DateTimeOffset.UtcNow > pendingWorkflow.ExpiresAtUtc)
                            {
                                pendingWorkflow.Reject();
                                pendingWorkflow = null;
                                FinishWorkflow("EXPIRED", "Workflow approval expired. No action ran. Submit a new request.", "#F3C969");
                            }
                        });
                    });
                }
                catch (OperationCanceledException)
                {
                    if (plan != null) plan.Reject();
                    Ui(delegate { FinishWorkflow("CANCELLED", "Workflow cancelled during preparation. No action ran.", "#F3C969"); });
                }
                catch (Exception error)
                {
                    if (plan != null) plan.Reject();
                    WorkflowFault fault = error as WorkflowFault;
                    string detail = fault == null ? "App identity or accessibility preparation failed. Check the registered apps and open windows." : fault.Message;
                    string code = fault == null ? "PREPARATION_FAILED" : fault.Code;
                    Ui(delegate { FinishWorkflow("REJECTED", "Workflow rejected before approval. No action ran.\r\n\r\n" + detail + "\r\nDiagnostic: " + code, "#FF7D88"); });
                }
            });
        }

        private void ResolveWorkflowApproval(string choice)
        {
            WindowsWorkflowPlan plan = pendingWorkflow;
            if (plan == null || plan.IsConsumed || (choice != "once" && choice != "deny")) return;
            pendingWorkflow = null;
            HideApproval();
            approveOnceButton.IsEnabled = false;
            denyApprovalButton.IsEnabled = false;
            if (choice == "deny" || DateTimeOffset.UtcNow > plan.ExpiresAtUtc)
            {
                plan.Reject();
                FinishWorkflow(choice == "deny" ? "DENIED" : "EXPIRED",
                    choice == "deny" ? "Workflow denied. No action ran; the approval cannot be reused." :
                        "Workflow approval expired. No action ran; submit a new request.", "#F3C969");
                return;
            }
            CancellationToken token = workflowCancellation.Token;
            SetInteractive(false);
            SetStatus("EXECUTING", "#58CFF5");
            UpdateTask("EXECUTING", "Approved once. Revalidating targets and starting the ordered steps without an added countdown.");
            responseBox.Text = workflowPreview + "\r\n\r\nEXECUTING\r\n" +
                "Stop remains available while this workflow is active. Completed changes are not undone.";
            StringBuilder evidence = new StringBuilder();
            Task.Run(delegate
            {
                try
                {
                    WorkflowRunResult result = WindowsWorkflowRunner.Run(plan, plan.Fingerprint, windowsObservation, workflowCheckpointStore, token,
                        delegate(WorkflowCheckpoint checkpoint, WorkflowStepResult receipt)
                        {
                            WorkflowProgressUi(delegate
                            {
                                // Never overwrite STOPPING with a queued progress message.
                                if (!workflowActive || token.IsCancellationRequested) return;
                                SetStatus("EXECUTING", "#58CFF5");
                                if (receipt != null)
                                    evidence.Append(checkpoint.Verified).Append(". ").Append(receipt.Summary).Append("\r\n");
                                responseBox.Text = workflowPreview + "\r\n\r\nPROGRESS\r\n" + evidence +
                                    "\r\n" + checkpoint.Verified + "/" + checkpoint.Total + " steps verified.";
                                UpdateTask("STEP " + checkpoint.Started + "/" + checkpoint.Total,
                                    receipt == null ? "Revalidating the target, then executing the approved step." : receipt.Summary);
                            });
                        });
                    StringBuilder answer = new StringBuilder();
                    answer.Append(result.Checkpoint.State).Append(" · ").Append(result.Checkpoint.Verified)
                        .Append("/").Append(result.Checkpoint.Total).Append(" steps verified.\r\n\r\n");
                    for (int i = 0; i < result.Receipts.Count; i++)
                        answer.Append(i + 1).Append(". ").Append(result.Receipts[i].Summary)
                            .Append("\r\n").Append(result.Receipts[i].Evidence).Append("\r\n\r\n");
                    if (!string.IsNullOrEmpty(result.ErrorCode))
                        answer.Append(result.Detail).Append("\r\nDiagnostic: ").Append(result.ErrorCode).Append("\r\n\r\n");
                    if (result.Checkpoint.Started > result.Checkpoint.Verified)
                        answer.Append("Step ").Append(result.Checkpoint.Started).Append(" was attempted but not verified. It may have changed the app.\r\n");
                    answer.Append("No automatic retry, replay, save, or undo. This approval is consumed. Checkpoints contain counts and state only.");
                    string response = answer.ToString();
                    Ui(delegate
                    {
                        if (result.Checkpoint.State == "COMPLETED") AddHistory(workflowInput, response);
                        FinishWorkflow(result.Checkpoint.State, response, result.Checkpoint.State == "COMPLETED" ? "#4DE3C1" :
                            result.Checkpoint.State == "CANCELLED" ? "#F3C969" : "#FF7D88");
                    });
                }
                catch (Exception)
                {
                    plan.ForgetText();
                    Ui(delegate { FinishWorkflow("RECOVERY REQUIRED",
                        "Workflow reporting failed. Inspect the apps and ask Show workflow status. Do not assume a step was undone or repeat it without review.", "#FF7D88"); });
                }
            });
        }

        private void WorkflowProgressUi(Action action)
        {
            if (window.Dispatcher.CheckAccess()) action();
            else window.Dispatcher.Invoke(System.Windows.Threading.DispatcherPriority.Background, action);
        }

        private void CancelWorkflow()
        {
            if (!workflowActive) return;
            if (workflowCancellation != null) workflowCancellation.Cancel();
            if (pendingWorkflow != null)
            {
                pendingWorkflow.Reject(); pendingWorkflow = null;
                FinishWorkflow("CANCELLED", "Workflow cancelled before approval. No action ran.", "#F3C969");
                return;
            }
            stopButton.IsEnabled = false;
            SetStatus("STOPPING", "#F3C969");
            UpdateTask("STOPPING", "Cancelling pending observation waits and later actions. A Windows call already in flight may finish; completed changes remain.");
        }

        private void FinishWorkflow(string state, string message, string color)
        {
            workflowActive = false; pendingWorkflow = null;
            HideApproval();
            if (workflowCancellation != null) { workflowCancellation.Dispose(); workflowCancellation = null; }
            workflowInput = null; workflowPreview = null;
            lastResponse = message; responseBox.Text = message;
            SetStatus(state == "COMPLETED" ? "READY" : state, color);
            UpdateTask(state, message.Split(new string[] { "\r\n" }, StringSplitOptions.None)[0]);
            SetInteractive(true);
            WriteEvent("windows_workflow", state.ToLowerInvariant().Replace(' ', '_'), 0);
        }

        private void RecoverWorkflowCheckpoint()
        {
            try
            {
                WorkflowCheckpoint checkpoint;
                if (!workflowCheckpointStore.RecoverInterrupted(out checkpoint)) return;
                string message = "A previous Windows workflow was interrupted. " + checkpoint.Verified + "/" + checkpoint.Total +
                    " steps had verified receipts; " + checkpoint.Started + " had started.\r\n\r\n" +
                    "No action was resumed or replayed. Inspect the affected apps before submitting a new plan. Previous text and approval were not saved.";
                responseBox.Text = message; lastResponse = message;
                UpdateTask("INTERRUPTED", "Previous workflow metadata recovered. No action resumed; fresh approval is required.");
                SetStatus("REVIEW LAST WORKFLOW", "#F3C969");
            }
            catch
            {
                responseBox.Text = "The last workflow checkpoint could not be read. No workflow was resumed. Review the affected apps before another request.";
                lastResponse = responseBox.Text;
                UpdateTask("RECOVERY REQUIRED", "Workflow checkpoint unavailable. No replay was attempted.");
            }
        }

        private void ShowWorkflowStatus()
        {
            try
            {
                WorkflowCheckpoint checkpoint;
                string message = !workflowCheckpointStore.TryLoad(out checkpoint) ? "No executed workflow checkpoint is present." :
                    "Last executed workflow\r\nState: " + checkpoint.State + "\r\nSteps verified: " + checkpoint.Verified + "/" + checkpoint.Total +
                    "\r\nSteps started: " + checkpoint.Started + "\r\nUpdated: " + checkpoint.UpdatedAtUtc.ToLocalTime().ToString("g") +
                    "\r\n\r\nMetadata only. No text, app names, titles, or reusable approval was saved. No action ran for this status request.";
                responseBox.Text = message; lastResponse = message;
                UpdateTask("STATUS", "Read the last executed workflow's metadata; no action ran.");
            }
            catch
            {
                responseBox.Text = "Workflow checkpoint unavailable or invalid. No action ran.";
                lastResponse = responseBox.Text;
                UpdateTask("RECOVERY REQUIRED", "Checkpoint could not be validated. No action ran.");
            }
        }
    }
}
