# Bounded PDF document security boundary - 10.1.0

## Verified input

Cypher first resolves the explicit relative path through the existing granted-folder view. Reparse
points, protected names, traversal, non-regular files and files outside the grant remain blocked.
The binary reader verifies path and open-handle identity, size and timestamps before and after one
bounded read, and reloads the grant before returning bytes. The PDF snapshot is capped at 8 MiB.

## Separate parser process

The document worker verifies the parser archive SHA-256 immediately before every launch. The native
host also verifies that archive before starting the document job and before installation. Exactly one
parser child is permitted inside a document job; other worker modes remain limited to one process.

The parser starts with isolated Python flags, a cleared/minimal environment, no shell and no window.
It receives raw PDF bytes through standard input and returns bounded JSON through standard output.
It is not given a file path, permission store, question, prompt, model endpoint, credential, action
engine or network client. Stderr, a nonzero exit, an invalid schema, an unknown diagnostic, excessive
output, timeout or hash mismatch fails closed before model access.

This is process and capability separation, not a hardened AppContainer. Both processes still run as
the signed-in standard user. The job limits process count and per-process memory, and closing the job
terminates both. The bundled parser code exposes no network or action API.

## Extraction and model boundary

pypdf strict parsing is used. Encrypted PDFs reject without a password attempt. At most 100 pages,
64 KiB per page and 1 MiB total extracted text are accepted. Controls and bidirectional override
characters are escaped before text can become evidence. Parser output is remeasured and validated.

Only selected passages enter the existing local Ollama request; paths, filenames, unselected text,
PDF objects, scripts, attachments, forms and metadata do not. The model evidence budget remains
4,096 passage-text bytes. Grant checks run again before model input and before display. Extracted
text is untrusted data and cannot request an action.

## Deliberate exclusions

No OCR, image interpretation, PDF rendering, signature validation, form filling, attachment access,
embedded JavaScript, password handling, repair mode, public service, persistent cache or index is
added. Strict parsing can reject PDFs that permissive readers open, and extraction may not preserve
complex visual reading order. Exact displayed passages remain the review authority.

