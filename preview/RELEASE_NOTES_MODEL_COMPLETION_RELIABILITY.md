# Core Preview 9.2.5 — local model completion reliability

Package **v0.9.2.5** · Python package **0.9.2a6** · 4 September 2026

Two consecutive 9.2.4 target-PC runs completed academic discovery and selected two sources, then
returned `MODEL_UNAVAILABLE` before producing a finding. This release reduces the compact structured
synthesis budget from a 16,384-token context and 2,048 generated tokens to 8,192 and 768.

The selected installed model is still called exactly once. Cypher does not retry, substitute the
deep or vision model, download a model, add a warning or approval, or wait before starting. Provider
behavior, source selection, direct-evidence validation, Stop behavior, and approved Windows
workflows are unchanged.
