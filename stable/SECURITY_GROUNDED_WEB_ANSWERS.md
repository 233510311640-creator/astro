# Security boundary — Grounded Public Page Answers

`Web: ask` is a narrow read-only network and local-inference route. It receives one user-supplied
public HTTPS URL and one question. The reader canonicalizes the URL, rejects non-public targets,
validates DNS results and redirects, applies robots policy, accepts only supported public text, and
enforces response-size and time limits.

The model receives only bounded reader-assigned passages, the local question, and structural
metadata needed for citation selection. It has no tools. Every accepted finding must select passage
IDs from the current request; Cypher resolves those IDs back to exact page slices and applies the
existing citation, quotation, number, vocabulary, condition, and claim-scope checks before display.

Page titles, headings, and passages are untrusted data. They cannot modify the system prompt, call a
tool, approve an operation, grant a folder, or become an action request. The route has no browser
profile, cookies, login credentials, local file paths, action approvals, Windows-control handles,
shell, provider fallback, or automatic retry. Results remain memory-only and outside chat history
and action checkpoints.

