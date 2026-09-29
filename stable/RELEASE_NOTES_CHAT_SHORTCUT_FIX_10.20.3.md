# Cypher 10.20.3 — modifier-only chat shortcut fix

The previous Ctrl+Win+Alt registration was accepted by Windows but did not deliver a shortcut event when pressed on this PC. This release detects the three modifier keys directly and opens the chat when all are held together, in any order. Release the chord before invoking it again. Ctrl+Alt+Space remains the voice shortcut.

The keyboard callback reads only virtual-key codes for Ctrl, Win, and Alt, discards every other key, never records typed text, and never blocks another application from receiving its keyboard events. It is removed when Cypher exits. If Windows does not allow the listener, the tray menu remains a fallback.

No model, microphone, cloud, Windows-action, or approval permissions changed. Automated checks cover compilation and callback wiring. A physical keypress check on the user's desktop is still required to confirm behavior.
