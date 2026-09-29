# Cypher 10.13.2 — Voice Draft Handoff Fix

This update fixes the reported sequence: Cypher showed **WORDS HEARD** while MIC was active, but after **END MIC** the input box stayed empty. The local event log recorded those attempts as cancelled. Cypher had treated the recognizer's asynchronous completion flag as if the user had pressed **Stop**, discarding words already recognized.

**END MIC** now retains the in-memory transcript when there is no recognition error, even if the Windows recognition engine reports a cancelled completion. Only the user's **Stop**, Hide, Pause or Exit discards the draft. The words appear in the command input for correction; **Send** is still required, and Windows actions retain their normal approvals. Audio and transcript text are never written to the diagnostic log.

The native self-test now checks both the cancelled-completion policy and the actual insertion of an editable draft into a bounded WPF input box. Recognition accuracy and a live spoken phrase still need a user test.

Install with `INSTALL_CYPHER_VOICE_DRAFT_HANDOFF.cmd`. Keep the 10.13.1 bundle for rollback.
