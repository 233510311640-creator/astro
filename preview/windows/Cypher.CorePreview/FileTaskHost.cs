using System;
using System.Collections.Generic;
using System.Text.RegularExpressions;
using System.Threading.Tasks;
using System.Windows;
using WF = System.Windows.Forms;

namespace Cypher.CorePreview
{
    internal sealed partial class CypherHost
    {
        private sealed class FileDialogOwner : WF.IWin32Window
        {
            public IntPtr Handle { get; private set; }
            public FileDialogOwner(IntPtr handle) { Handle = handle; }
        }
        private volatile bool fileTaskActive;
        private OwnedFileTask fileTaskWorker;
        private string pendingFileFingerprint;
        private bool fileStopUnconfirmed;
        private bool fileTaskReadOnly;

        private void BeginFileTask(string input)
        {
            if (input.Length > 16384) { ShowError("File request too long", "Use a file command under 16,384 characters."); return; }
            string python;
            try { python = GetSetting(ReadSettings(), "research_python_path", ""); }
            catch { ShowError("File settings unavailable", "Reinstall the desktop package to restore its local worker settings."); return; }
            string folder = null;
            if (Regex.IsMatch(input, @"\A\s*Files\s*:\s*add\s+folder\s*\z", RegexOptions.IgnoreCase))
            {
                fileTaskActive = true; SetInteractive(false);
                try
                {
                    using (WF.FolderBrowserDialog picker = new WF.FolderBrowserDialog())
                    {
                        picker.Description = "Choose one existing folder for Cypher file tasks. You will review its permission next.";
                        picker.ShowNewFolderButton = false;
                        FileDialogOwner owner = new FileDialogOwner(new System.Windows.Interop.WindowInteropHelper(window).Handle);
                        if (picker.ShowDialog(owner) != WF.DialogResult.OK) return;
                        folder = picker.SelectedPath;
                    }
                }
                finally { fileTaskActive = false; SetInteractive(true); }
                input = "Files: add folder";
            }
            fileTaskReadOnly = Regex.IsMatch(input, @"\A\s*Files\s*:\s*(list|find|read|folders|status|help)(?:\s|$)", RegexOptions.IgnoreCase);
            OwnedFileTask worker = new OwnedFileTask();
            fileTaskActive = true; fileStopUnconfirmed = false; fileTaskWorker = worker; pendingFileFingerprint = null;
            inputBox.Clear(); HideApproval(); SetInteractive(false);
            modelText.Text = "LOCAL FILE TASK · NO MODEL CALL";
            responseBox.Text = fileTaskReadOnly ? "Reading within your approved folders. No file change or model call." : "Preparing the file task. Changes will be shown for your approval.";
            lastResponse = "";
            SetStatus("PREPARING", "#ADA6F5"); UpdateTask("PREPARING", fileTaskReadOnly ? "Checking the requested read-only file scope." : "Checking approved folders and exact file changes.");
            Task.Run(delegate
            {
                string state = fileTaskReadOnly ? "FAILED" : "RECOVERY REQUIRED", message = fileTaskReadOnly ? "The read-only worker did not return a verified result. No file change was requested." : "The file worker did not return a verified result. Send Files: recover to inspect any interrupted changes before proceeding.";
                try
                {
                    Dictionary<string, object> result = worker.Run(installRoot, python, input, folder,
                        delegate(Dictionary<string, object> value)
                        {
                            if ((string)value["type"] == "result") return; // Never display success until verified process exit.
                            Ui(delegate
                            {
                                if (fileTaskWorker != worker || !fileTaskActive || worker.StopRequested) return;
                                if ((string)value["type"] == "review")
                                {
                                    pendingFileFingerprint = (string)value["fingerprint"];
                                    responseBox.Text = (string)value["text"];
                                    responseBox.ScrollToHome();
                                    approvalSummaryText.Text = "Review the complete plan in the conversation above. Approve once applies exactly those changes.";
                                    approvalDetailsText.Text = "Local file task · one approval · review expires after two minutes.";
                                    approveOnceButton.IsEnabled = true; denyApprovalButton.IsEnabled = true;
                                    RevealApprovalCard();
                                    SetStatus("APPROVAL REQUIRED", "#F3C969"); UpdateTask("WAITING APPROVAL", "Review all changes before approving once.");
                                }
                                else
                                {
                                    HideApproval(); pendingFileFingerprint = null;
                                    SetStatus("WORKING", "#ADA6F5");
                                    UpdateTask("WORKING", value["verified"] + " / " + value["total"] + " file actions verified. Stop rolls back forward changes.");
                                }
                            });
                        });
                    state = (string)result["state"]; message = (string)result["text"];
                }
                catch (OperationCanceledException) { state = "CANCELLED"; message = "Cancelled before starting the file worker. No file action ran."; }
                catch { }
                Ui(delegate { FinishFileTask(worker, state, message); });
            });
        }
        private void ResolveFileApproval(string choice)
        {
            OwnedFileTask worker = fileTaskWorker;
            string fingerprint = pendingFileFingerprint;
            if (worker == null || fingerprint == null) return;
            pendingFileFingerprint = null; HideApproval();
            bool approve = choice == "once";
            SetStatus(approve ? "WORKING" : "CANCELLING", "#ADA6F5");
            UpdateTask(approve ? "WORKING" : "CANCELLING", approve ? "Applying the reviewed file task." : "Waiting for the worker to confirm cancellation.");
            try { worker.Decide(approve, fingerprint); }
            catch { CancelFileTask(); }
        }
        private void FinishFileTask(OwnedFileTask worker, string state, string message)
        {
            if (fileTaskWorker != worker) return;
            HideApproval(); pendingFileFingerprint = null;
            if (!worker.IsStopped)
            {
                fileStopUnconfirmed = true;
                SetStatus("STOP UNCONFIRMED", "#FF7D88");
                UpdateTask("STOP UNCONFIRMED", "The file worker has not exited. New tasks remain blocked. Use Stop again.");
                stopButton.IsEnabled = true; return;
            }
            fileTaskActive = false; fileTaskWorker = null; fileStopUnconfirmed = false; worker.Dispose();
            responseBox.Text = message; lastResponse = message;
            SetStatus(state == "COMPLETED" ? "READY" : state, state == "COMPLETED" ? "#4DE3C1" : "#F3C969");
            UpdateTask(state, "File worker exited. Use Files: status for local task receipts.");
            SetInteractive(true);
        }
        private void CancelFileTask()
        {
            OwnedFileTask worker = fileTaskWorker;
            if (!fileTaskActive || worker == null) return;
            pendingFileFingerprint = null; HideApproval(); worker.RequestStop();
            SetStatus("STOPPING", "#F3C969");
            UpdateTask("STOPPING", fileTaskReadOnly ? "Stopping the read-only request and waiting for worker exit." : "Stopping between file steps. Waiting for rollback or a recovery report before another task can start.");
            if (fileStopUnconfirmed && worker.IsStopped)
                FinishFileTask(worker, fileTaskReadOnly ? "CANCELLED" : "RECOVERY REQUIRED", fileTaskReadOnly ? "Read-only worker exit confirmed. No file action ran." : "File worker exit confirmed. Send Files: recover to inspect interrupted changes. Rollback has not been assumed.");
        }
    }
}
