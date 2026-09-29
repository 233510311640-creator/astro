# Cypher 10.20.2 — separate chat shortcut

Ctrl+Win+Alt opens the command center, regardless of which of the three keys is pressed last. Ctrl+Alt+Space remains the voice shortcut. The tray menu and tray double-click remain alternative ways to open chat.

This update uses the normal Windows hotkey registration API, not a global keyboard hook. No keystrokes are recorded or intercepted. The app reports if some or all key-order variants cannot be registered. Because a modifier is the hotkey's final virtual key, live behavior still needs a supervised check on this Windows desktop; registration and automated build checks alone cannot prove that the chord is delivered in every key order.

No model, microphone, cloud, Windows-action, or approval permissions are changed. The installed 10.20.1 app is backed up before this update.
