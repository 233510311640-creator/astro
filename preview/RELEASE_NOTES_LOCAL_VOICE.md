# Cypher 10.13.0 — Local Voice

The Ctrl+Alt+Space desktop window now has two explicit voice controls:

- **MIC** starts the installed Windows speech recognizer on the default microphone. It listens for up to 20 seconds. **END MIC** finishes earlier; **Stop** discards the draft. Recognized words appear in the command input for review and editing. Nothing is submitted until **Send** is pressed. Any Windows action still follows its usual approval flow.
- **READ ALOUD** speaks up to 1,200 characters of the current response through an installed Windows voice. **STOP AUDIO** cancels playback.

Hiding, pausing or exiting Cypher stops capture and playback. The host keeps only an in-memory transcript during capture; it does not save raw microphone audio. There is no wake word or background listening. This is a local desktop feature, not a Hermes audio API or realtime voice model.

The installed recognizer on the development PC is Windows English (United States). Recognition quality depends on that language pack, the microphone and the environment. OCR is still not implemented. Approved-PNG vision remains model interpretation, not verified text extraction; public-page features remain bounded reading/search rather than full browser interaction.

Install with `INSTALL_CYPHER_LOCAL_VOICE.cmd`. The existing 10.12.0 bundle should be kept for rollback.
