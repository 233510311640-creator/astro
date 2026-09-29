# Validation — Cypher 10.13.0 Local Voice

- Python suite: 594 tests run; 593 passed, one existing platform skip. Voice checks confirm local speech wiring, a 20-second cap, draft-only transcript, explicit Send boundary, cancellation, and no automatic request dispatch from the voice module.
- Native host compiled and passed its self-test, including WPF controls/layout and installed speech recognizer and voice discovery. Research, file, runtime, and document worker self-tests passed before the resident host was replaced. Hermes capability preflight passed.
- An independent Windows speech-engine probe loaded the installed `en-US` dictation grammar and connected to the default microphone, then disposed the engine without saving or submitting audio.
- The 1120 × 720 offscreen workspace render shows the MIC and READ ALOUD controls within the existing monochrome layout.
- Transactional installation succeeded. The resident heartbeat reported `ready`, version `0.7.0-core-preview10.13.0`, on 27 September 2026.

Not verified: recognition of a spoken phrase, accuracy across accents/noise/languages, audio playback audibility, or a live end-to-end dictated request. The local Windows speech components are not equivalent to a streaming voice conversation. OCR is not part of this release.
