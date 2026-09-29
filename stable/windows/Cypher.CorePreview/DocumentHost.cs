using System;
using System.Collections.Generic;
using System.Text.RegularExpressions;
using System.Threading.Tasks;

namespace Cypher.CorePreview
{
    internal sealed partial class CypherHost
    {
        private static bool IsDocumentRequest(string text)
        { return Regex.IsMatch(text ?? "", @"^\s*(Docs|Vision)\s*:", RegexOptions.IgnoreCase | RegexOptions.CultureInvariant); }

        private void BeginDocument(string input)
        {
            if (input.Length > 4096) { ShowError("Document request too long", "Use Docs: help or Vision: help for the supported command format."); return; }
            bool vision = Regex.IsMatch(input, @"^\s*Vision\s*:", RegexOptions.IgnoreCase | RegexOptions.CultureInvariant);
            string python;
            try { python = GetSetting(ReadSettings(), "research_python_path", ""); }
            catch { ShowError("Document settings unavailable", "The installed Python path could not be read."); return; }
            string model = vision ? Router.VisionModel : SelectedMode() == "deep" ? Router.DeepModel : Router.FastModel;
            OwnedFileTask worker = new OwnedFileTask(false, true);
            runtimeDocument = true; runtimeWorker = worker; runtimeActive = true; runtimeExitUnconfirmed = false;
            inputBox.Clear(); HideApproval(); SetInteractive(false);
            modelText.Text = vision ? "LOCAL VISION · ONE MODEL CALL MAX" : "LOCAL DOCUMENT · ONE MODEL CALL MAX";
            responseBox.Text = vision
                ? "Reading one explicitly named PNG in an approved folder. A local vision model will interpret it once; its observations are not verified OCR or exact transcription. No web request, Windows action, file change or chat-history addition."
                : "Searching or reading only the explicitly named granted scope. Search is bounded and model-free; search-all includes extractable PDF and Office text. Answer-all selects bounded excerpts across one approved folder for at most one verified local-model call. Exact file citations follow each checked draft. Explicit single-file answer and multi-file compare remain available. No OCR, file change, saved index, chat-history addition or public web request.";
            lastResponse = "";
            SetStatus("READING", "#ADA6F5"); UpdateTask("READING", "Checking the selected file and local model. Stop cancels this request.");
            Task.Run(delegate
            {
                string state = "FAILED", message = "The document worker did not return a verified result. No retry ran.";
                try
                {
                    Dictionary<string, object> result = worker.Run(installRoot, python, input, null, delegate { }, model);
                    state = (string)result["state"]; message = (string)result["text"];
                }
                catch (OperationCanceledException) { state = "CANCELLED"; message = "Document request cancelled before starting."; }
                catch { }
                Ui(delegate { FinishRuntime(worker, state, message); });
            });
        }

        public static int DocumentSelfTest(string root, string python)
        {
            try
            {
                using (OwnedFileTask worker = new OwnedFileTask(false, true))
                {
                    Dictionary<string, object> result = worker.Run(root, python, "Docs: self-test", null, delegate { }, "fixture:latest");
                    return (string)result["text"] == "DOCUMENT_SELF_TEST_OK" && worker.IsStopped ? 0 : 189;
                }
            }
            catch { return 190; }
        }
    }
}
