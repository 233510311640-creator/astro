# Cypher 10.11.0 — approved PNG vision

This release adds explicit local image interpretation to the Ctrl+Alt+Space command center.

1. Approve a folder for reading with the existing Files permission flow.
2. Enter `Vision: describe ROOT "relative/image.png"` or `Vision: ask ROOT "relative/image.png" : What is visible?` using that folder's grant name.
3. Cypher reads only the named PNG, checks its size, dimensions, chunk structure and CRCs, verifies that the configured installed local model advertises vision support, and makes one local inference call. Stop can cancel the worker; permissions are checked again before and after inference.

The limit is 4 MiB, 8 megapixels and 4,096 pixels per side. Unrecognized PNG chunks and non-PNG formats fail closed. The output includes the file name, dimensions and SHA-256 so the user can identify what was read. Image descriptions are model interpretations, not verified OCR or exact evidence. Images are untrusted data and cannot authorize actions.

There is no image attachment picker, screenshot capture, live camera, browser integration, cloud vision provider, model download, file change, retry, model substitution or chat-history addition. The ordinary vision mode button remains disabled; only the explicit `Vision:` commands use this capability.
