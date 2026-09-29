# Cypher 10.14.0 — offline voice accuracy update

Cypher now records a bounded clip from the Windows default microphone after the user presses **MIC**, transcribes it with the locally cached faster-whisper base model after **END MIC**, and places the result in the editable command input. It never sends the command automatically. **Stop**, Hide, Pause, and Exit discard an active recording or transcription.

The former Windows System.Speech dictation engine is no longer the active input path. **READ ALOUD** still uses the installed Windows speech voice.

## Privacy and limits

- Recording is capped at 20 seconds, kept in memory, and not saved as an audio file.
- The worker receives one bounded PCM WAV stream through stdin. It uses an explicit local model directory, CPU inference, and offline mode; it does not download a model.
- The worker script is hash-checked by the host. The model and Python speech dependencies must already be installed.
- Recognized text is limited to 1,200 characters and still requires review and a separate **Send** action.
- Near-silence is rejected before loading the model. A quiet recording or unsupported default-mic format may still need input-device adjustment.

## Verification completed

- Python voice-worker tests pass for WAV validation, silence handling, and the local-model call contract.
- The full package validation and compiled-host self-tests pass.
- The cached model loads successfully in offline CPU mode.
- The installed host heartbeat reports `0.7.0-core-preview10.14.0` and the packaged worker hash matches its pinned value.

Live accuracy with the user's voice and microphone has **not** been verified yet. Test with **MIC → say a short phrase → END MIC**, then inspect the editable text before Send. If recognition is still wrong, note the exact spoken phrase and the resulting draft so the model/capture settings can be tuned without guessing.

## Design references

The local push-to-talk, transcribe, review-before-send flow follows patterns documented by [faster-whisper](https://github.com/SYSTRAN/faster-whisper) and [Kiro voice input](https://kiro.dev/docs/cli/voice/). Cypher's implementation is its own bounded Windows capture and worker integration; no third-party app code was copied.
