# Cypher 10.17.0 — faster wake-to-command handoff

The prior wake flow always recorded for 12 seconds before starting offline transcription. Two observed sessions took about 21–23 seconds from activation to request submission, followed by 37–63 seconds for local-model response generation. Wake detection itself remained intermittent in ambient speech; this release does not claim to solve that separate recognition issue.

This release keeps the 12-second maximum but uses completed 200 ms microphone buffers to detect the end of a spoken command. After at least two speech-level buffers, six quiet buffers (about 1.2 seconds) finish the wake recording early. Silence alone never triggers early submission. A quiet voice or noisy room can still use the 12-second fallback. Manual MIC behavior remains unchanged: up to 20 seconds, with an editable draft before sending.

Only aggregate audio levels are inspected for this decision. Raw microphone audio stays in memory and is handed only to the existing integrity-pinned offline Whisper worker. No new network request, saved recording, transcript log, or change to Windows/file-action approvals was added. The `voice_input: speech_end` event records metadata only.

Validation covers the 200 ms buffer logic, amplitude calculation, wake-flow wiring, compiled host self-test, and existing offline suite. Live microphone and acoustic wake reliability require a user test after installation.
