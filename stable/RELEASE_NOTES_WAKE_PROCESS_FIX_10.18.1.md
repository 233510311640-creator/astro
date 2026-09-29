# Cypher 10.18.1 — wake-process ownership and audio signal diagnostics

The first streaming wake build launched a virtual-environment Python redirector, which then spawned the actual interpreter. Stopping only the redirector could leave its child holding the microphone. This hotfix launches the one real Python 3.12 interpreter directly with isolated imports and an explicitly supplied, local wake-dependency directory. The resident host now owns and stops the process that captures microphone audio.

The worker emits one metadata-only `SIGNAL` marker after sustained microphone amplitude. This becomes the `wake_word: audio_detected` event, allowing microphone-path failures to be distinguished from phrase-model misses without storing audio or surrounding speech. It still emits only fixed markers, not recognized ambient words.

The model self-test, compiled host self-test, and offline suite pass. After installation, one live wake activation was observed: the command was submitted about nine seconds later and the local request completed in 36.9 seconds. That verifies one successful end-to-end activation, not consistent recognition accuracy or audible speaker output; the user must confirm those. No cloud service has been enabled.
