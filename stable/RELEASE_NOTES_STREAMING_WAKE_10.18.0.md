# Cypher 10.18.0 — streaming wake-word detector

Cypher's legacy Windows US-English `SpeechRecognitionEngine` remained active but repeatedly rejected the user's spoken wake phrase. Manual MIC continued to produce a draft, so the failure was isolated to wake detection rather than microphone access or Whisper transcription.

This release replaces only the continuous wake detector with a dedicated, on-device Sherpa-ONNX keyword spotter. It recognizes the configured "Hello Cypher", "Hey Cypher", or "Cypher" phrase and the "Cypher stop" command, including the homophone "cipher". The model is loaded once per listening session and processes 80 ms microphone frames. It emits only `READY`, `WAKE`, `STOP`, or `ERROR` markers to the resident host; no ambient transcript or microphone recording is saved or uploaded. Existing offline Whisper command transcription, auto-send, spoken acknowledgement, maximum command duration, and action approvals are unchanged.

The one-time wake runtime is isolated under `%LOCALAPPDATA%\Cypher\WakeRuntime`. Run `scripts/setup_cypher_wake_runtime_windows.ps1` before installation on another Windows PC. The script pins package versions and the SHA-256 of the official Sherpa-ONNX English model archive. The resident host pins the worker source hash and checks the runtime before listening. If it cannot start, manual MIC remains available and the tray reports wake unavailability.

The official [Sherpa-ONNX](https://github.com/k2-fsa/sherpa-onnx) engine and the [Hermes wake-word implementation](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/features/wake-word.md) informed this design. The model is not bundled with the source package. Acoustic accuracy with the user's own pronunciation must be verified after installation; the pre-install self-test confirms model initialization and microphone format, not recognition performance.

No cloud mode is enabled. A future opt-in cloud reply/transcription route requires an explicit provider, credential, cost, data-flow, and retention choice.
