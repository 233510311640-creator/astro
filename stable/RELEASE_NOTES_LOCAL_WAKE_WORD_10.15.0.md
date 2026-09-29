# Cypher 10.15.0 — local wake-word voice control

After Windows sign-in, the resident Cypher host listens locally for **“Cypher”** (or **“Hey Cypher”**) through the installed Windows keyword recognizer. When it hears the name with sufficient confidence, it opens Cypher, plays a short cue, and records the next command for up to 12 seconds. The cached offline Whisper model transcribes the command, which is automatically submitted if nonempty. The old manual **MIC** button remains available and still leaves an editable draft rather than auto-sending.

**“Cypher stop”** and **“Cypher cancel”** can stop an active task. The existing one-time approval prompts for consequential Windows and file actions are unchanged; voice activation never auto-approves them. The tray's **Pause activation** turns off wake listening until resumed. Exiting Cypher also releases the microphone; the normal sign-in shortcut starts the resident listener next time.

No raw audio is saved or uploaded. The wake recognizer runs locally, and the post-wake command uses the same bounded offline worker as 10.14.0. The always-on listener does keep the Windows microphone active while Cypher is running and unpaused; the Windows microphone privacy indicator may therefore remain visible.

## First live check

1. Wait for Cypher to start after sign-in (or use the currently running app).
2. Say **“Cypher”**, pause for the cue, then speak a short harmless command such as “system status.”
3. Wait up to 12 seconds for recording to finish and check the submitted text and response.
4. Say **“Cypher stop”** during an active task to check hands-free cancellation.

Wake-word accuracy, false-positive behavior, and the default microphone handoff need a live spoken test; automated tests cannot verify these acoustic conditions. If Cypher misses its name or triggers unexpectedly, pause activation in the tray and use the manual MIC/hotkey while the wake threshold or engine is tuned. A future dedicated custom wake-word model may improve reliability over the installed Windows keyword recognizer.

## Implementation reference

The wake stage uses the [Microsoft SpeechRecognitionEngine asynchronous recognition API](https://learn.microsoft.com/en-us/dotnet/api/system.speech.recognition.speechrecognitionengine.recognizeasync) for a small fixed keyword grammar. Command dictation remains with [faster-whisper](https://github.com/SYSTRAN/faster-whisper). No third-party application code was copied.
