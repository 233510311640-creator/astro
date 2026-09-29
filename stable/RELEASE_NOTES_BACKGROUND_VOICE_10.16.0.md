# Cypher 10.16.0 — background spoken wake and reply

Cypher now accepts **“Cypher”**, **“Hey Cypher”**, and **“Hello Cypher”** from the Windows background listener. It responds aloud with **“Yes?”**, then records a command for up to 12 seconds through the offline Whisper transcription path. A nonempty transcription is submitted automatically, and a bounded response is read aloud. This flow does not need to type into or take focus from the app currently on screen. **Ctrl+Alt+Space** still opens Cypher's own window.

The wake stage uses a small fixed grammar in the installed Windows recognizer, with a lower but still bounded confidence requirement for multiword greetings. The command itself is transcribed by the cached offline Whisper model. A rejected wake attempt writes only a throttled metadata event, never ambient words or audio, to help distinguish a microphone problem from an unrecognized phrase.

**“Cypher stop”** and **“Cypher cancel”** remain available while a task is active. Manual **MIC** still leaves an editable draft rather than auto-sending. Consequential Windows and file actions still require their existing approval prompts. The tray's **Pause activation** disables background listening until resumed.

## Live test needed

While another app is in front, say **“Hello Cypher”** and wait for **“Yes?”** before saying a harmless command such as **“system status.”** If there is no spoken acknowledgement, report whether the Windows microphone indicator appears and whether the Cypher tray icon says it is listening. Wake recognition and speaker output cannot be verified acoustically by automated tests.

The current wake stage still depends on the installed Windows recognizer, which may miss some pronunciations or trigger on unrelated speech. A dedicated trained wake-word model remains the longer-term reliability upgrade. No raw audio is saved or uploaded.
