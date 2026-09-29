# Cypher 10.20.0 — identity greeting

Cypher now answers an exact “hello Cypher” (or “hello cipher” speech transcription) and direct identity questions immediately in the app. The response uses the configured assistant name, does not call the local language model or Hermes gateway, and remains available to the wake-command read-aloud path. Other requests continue through their existing routes and approvals.

The model instructions explicitly distinguish Cypher’s assistant identity from its internal Hermes gateway. The capability panel also reflects the current wake behavior: manual MIC leaves an editable draft; wake-triggered commands auto-submit after offline transcription. No audio or transcript logging was added.

The user has confirmed manual READ ALOUD plays audibly. This does not by itself prove that the separate wake acknowledgement is consistently audible or that wake detection is reliable; those still need a real-microphone check.
