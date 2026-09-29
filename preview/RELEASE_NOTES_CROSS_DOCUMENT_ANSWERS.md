# Cypher 10.10.0 — grounded cross-document answers

`Docs: answer-all ROOT : question` now answers from current extractable text across an approved folder of supported TXT, PDF, DOCX, PPTX and XLSX files. The command is also filled by the **DOC ANSWER** starter in the Ctrl+Alt+Space workspace. Existing one-file `Docs: answer` and two-to-four-file `Docs: compare` remain available.

The scan keeps the 10.9.0 boundaries: at most 40 files, 16 MiB of source bytes, 2,000 entries, 100 folders and six levels, with a 45-second scan deadline and separately bounded, integrity-pinned PDF and Office parsers. It ranks question-term matches locally, keeps at most 32 candidate excerpts, and sends at most 12 passages / 4,096 UTF-8 text bytes from at most four files to one verified installed local-model call. File paths and hashes are not sent to the model. The response displays only sentences with valid citations and conservative lexical/number support, followed by exact source paths, hashes, locations and quotes. These checks do not prove that the answer is true; verify against the quotes.

If no relevant extractable excerpt is found, Cypher makes no model call. If scan limits, unsupported files, or excerpt selection leave gaps, it reports partial coverage rather than claiming to have checked every document. No saved index, file change, macro/formula execution, public-web request, tool action or chat-history entry is created. Image-only PDFs still require OCR, and password-protected or malformed documents are not included.

The 10.9.0 local reminders and mixed-format `Docs: search-all` remain in this bundle. Open-ended browser interaction, OCR/vision input, voice, external-service integrations and production security review are still outside this milestone.

Install with `INSTALL_CYPHER_CROSS_DOCUMENT_ANSWERS.cmd`; the installer runs the full preflight and retains the existing rollback host. The prior 10.9.0 and 10.8.0 packages remain intact.
