# Validation — Auto-Discovered Browser Open

Release: **Cypher 10.2.1** / **Core Preview 10.2.1**

Acceptance checks:

- supported browser aliases resolve without a Cypher registry entry;
- discovery is limited to fixed standard Windows installation directories;
- registered matches take priority;
- unknown applications fail closed and continue to require registration;
- symlink/reparse-point executables are rejected;
- both registered and auto-discovered HTTPS policies pass destination integrity validation;
- the exact executable is re-discovered and re-hashed after approval;
- direct launch uses one normalized public HTTPS argument with shell execution disabled;
- no address-bar reading, page inspection, website interaction, clipboard, raw keyboard input, or shell fallback is introduced.
