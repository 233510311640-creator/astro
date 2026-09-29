# Cypher 10.20.1 — voice shortcut

Ctrl+Alt+Space starts the existing voice-command flow instead of toggling the chat window. Cypher says “Yes?”, records up to 12 seconds, transcribes locally, and auto-sends a recognized command. Its existing Windows and file approvals still require explicit review. The shortcut does not replace an unsent draft or start another command while Cypher is busy.

Open the command center from the tray menu or double-click its tray icon. A request needing approval brings the command center forward so the user can inspect and decide. A hidden voice session with no clear command shows a notification rather than silently failing.

This is a small backport onto the installed 10.20.0 base. It does not include the unaccepted 10.21 wake-word model or cloud-voice changes. The microphone and spoken reply still need a user-supervised end-to-end check after installation; passing build and synthetic tests alone does not prove recognition quality.
