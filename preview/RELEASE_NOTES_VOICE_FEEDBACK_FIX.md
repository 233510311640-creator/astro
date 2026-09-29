# Cypher 10.13.1 — Voice Feedback Fix

This update addresses the reported NO SPEECH result after using MIC while the Windows microphone worked in another app. Version 10.13.0 silently discarded every recognition result below a 0.45 confidence score. Version 10.13.1 keeps non-empty low-confidence results as an uncertain draft for review, never as an automatic command.

While listening, the top status now shows the microphone signal level, speech detection, or uncertain speech. After END MIC (or 20 seconds), Cypher either fills the input box for review or explains whether little signal reached Windows or Windows could not recognize words. A five-second completion fallback prevents a stuck TRANSCRIBING state. The local event log records only stage/outcome metadata, never audio or words.

Speech still does not press Send or approve actions. Stop discards the draft; Hide, Pause and Exit stop capture. Recognition quality depends on the installed Windows English recognizer and microphone conditions. If the result is inaccurate, edit it before pressing Send.

Install with `INSTALL_CYPHER_VOICE_FEEDBACK_FIX.cmd`. Keep the 10.13.0 release folder for rollback.
