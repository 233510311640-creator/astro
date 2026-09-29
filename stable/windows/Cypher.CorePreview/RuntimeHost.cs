using System;
using System.Collections.Generic;
using System.Text.RegularExpressions;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Controls;

namespace Cypher.CorePreview
{
    internal sealed partial class CypherHost
    {
        private volatile bool runtimeActive;
        private OwnedFileTask runtimeWorker;
        private bool runtimeExitUnconfirmed;
        private bool runtimeDocument;
        private Button runtimeStatusButton, recentTasksButton;

        private static bool IsRuntimeRequest(string text)
        { return Regex.IsMatch(text ?? "", @"^\s*Runtime\s*:", RegexOptions.IgnoreCase | RegexOptions.CultureInvariant); }

        private void BeginRuntime(string input)
        {
            if (input.Length > 256) { ShowError("Unknown runtime command", "Use Runtime: status or Runtime: benchmark."); return; }
            string python;
            try { python = GetSetting(ReadSettings(), "research_python_path", ""); }
            catch { ShowError("Runtime settings unavailable", "The installed Python path could not be read."); return; }
            string model = SelectedMode() == "deep" ? Router.DeepModel : Router.FastModel;
            bool benchmark = Regex.IsMatch(input, @"\A\s*Runtime\s*:\s*benchmark\s*\z", RegexOptions.IgnoreCase);
            runtimeDocument = false;
            OwnedFileTask worker = new OwnedFileTask(true);
            runtimeWorker = worker; runtimeActive = true; runtimeExitUnconfirmed = false;
            inputBox.Clear(); HideApproval(); SetInteractive(false);
            modelText.Text = benchmark ? "LOCAL PERFORMANCE CHECK · ONE GENERATION" : "LOCAL STATUS · NO GENERATION";
            responseBox.Text = benchmark
                ? "Checking the selected model's local weights, then measuring one short synthetic generation. Model: " + model + ". No files or conversation content are sent. The model may load into memory; Stop cancels this check."
                : "Checking local Ollama, installed model metadata and current residency. No generation will run.";
            lastResponse = "";
            SetStatus("CHECKING", "#ADA6F5"); UpdateTask("CHECKING", benchmark ? "One selected-model measurement; no retry or substitute model." : "Local runtime metadata only.");
            Task.Run(delegate
            {
                string state = "FAILED", message = "The runtime worker did not return a verified result. No retry ran.";
                try
                {
                    Dictionary<string, object> result = worker.Run(installRoot, python, input, null, delegate { }, model);
                    state = (string)result["state"]; message = (string)result["text"];
                }
                catch (OperationCanceledException) { state = "CANCELLED"; message = "Runtime check cancelled before starting."; }
                catch { }
                Ui(delegate { FinishRuntime(worker, state, message); });
            });
        }

        private void FinishRuntime(OwnedFileTask worker, string state, string message)
        {
            if (runtimeWorker != worker) return;
            if (!worker.IsStopped)
            {
                runtimeExitUnconfirmed = true;
                SetStatus("STOP UNCONFIRMED", "#F3C969");
                UpdateTask("STOP UNCONFIRMED", "Waiting for the local worker to exit. New requests remain blocked; use Stop again.");
                stopButton.IsEnabled = true; return;
            }
            runtimeActive = false; runtimeWorker = null; runtimeExitUnconfirmed = false; worker.Dispose();
            responseBox.Text = message; lastResponse = message;
            SetStatus(state == "COMPLETED" ? "READY" : state, state == "COMPLETED" ? "#4DE3C1" : "#F3C969");
            UpdateTask(state, runtimeDocument ? "Document worker exited. Quotes stay in this view only; no chat history was added." : "Runtime worker exited. Measurements remain in this view only; no generated answer was retained.");
            SetInteractive(true);
        }

        private void CancelRuntime()
        {
            OwnedFileTask worker = runtimeWorker;
            if (!runtimeActive || worker == null) return;
            worker.RequestStop(); SetStatus("STOPPING", "#F3C969");
            UpdateTask("STOPPING", "Cancelling local requests and waiting for worker exit. A submitted Ollama generation may still finish on the server.");
            if (runtimeExitUnconfirmed && worker.IsStopped)
                FinishRuntime(worker, "CANCELLED", "Local worker exit confirmed. A submitted Ollama generation may still finish; no additional request was made.");
        }

        public static int RuntimeSelfTest(string root, string python)
        {
            try
            {
                using (OwnedFileTask worker = new OwnedFileTask(true))
                {
                    Dictionary<string, object> result = worker.Run(root, python, "Runtime: self-test", null, delegate { }, "fixture:latest");
                    return (string)result["text"] == "RUNTIME_SELF_TEST_OK" && worker.IsStopped ? 0 : 187;
                }
            }
            catch { return 188; }
        }
    }
}
