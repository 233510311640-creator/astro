# Cypher 10.12.0 — vision access and model tuning

The Ctrl+Alt+Space window now shows **ASK IMAGE** in the left rail. It fills `Vision: ask ROOT "image.png" : ` in the input box but does not send a request. Use `Files: folders` to see approved folder names, replace `ROOT` and the image name, add your question, then Send. `Vision: describe ROOT "image.png"` remains available.

The default vision role now uses the already installed `qwen3.5:9b-q4_K_M`, instead of `gemma4:e4b`. In a local sanity check, Qwen identified a synthetic solid-red PNG and the central robot-like illustration in the user-provided Cypher reference image. Gemma answered black for the red image and described only the artwork background. These two checks informed this local default; they are not a broad benchmark or an accuracy guarantee. The configured role remains explicit and replaceable, with no automatic model fallback.

The in-app details and capability disclosure now describe the explicit approved-PNG route accurately. There is still no image attachment, screenshot, live camera, web access, Windows action, OCR guarantee, or history entry from the vision route. Existing folder grants and worker checks remain in force.

The worker now accepts the `caBX` ancillary metadata chunk found in the supplied Cypher artwork when it is at most 64 KiB and appears before image data. It validates the chunk checksum, removes the metadata in memory before local inference, and keeps the displayed SHA-256 tied to the original file. Other unrecognized chunks still fail closed. The supplied 1672 × 941 PNG passed this check; the normalized image also passed one local Qwen inference that identified its central robotic illustration. Cypher does not alter the source file.
