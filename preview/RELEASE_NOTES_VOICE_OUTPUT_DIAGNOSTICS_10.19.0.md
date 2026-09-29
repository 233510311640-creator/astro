# Cypher 10.19.0 — voice-output diagnostics

The wake path has activated at least once, but the user reported no audible "Yes?" or spoken answer. The Windows default output currently resolves to the CA-2890 USB speaker bar, while the selected microphone is the HyperX headset. This can route speech away from the headset. Cypher does not change the system audio device without the user's choice.

This release records metadata-only start, completion, or playback failure for the greeting and response. It explicitly sets speech volume to 100 and reports a Windows playback error in the UI without discarding the on-screen response. No response text or microphone audio is logged. Manual READ ALOUD uses the same checked playback path.

The audio endpoint used by Windows speech synthesis still follows the Windows default. If the user wants speech through HyperX headphones while keeping another system default, application-level output selection needs a separate implementation. Cloud speech would not by itself solve a wrong local playback device.
