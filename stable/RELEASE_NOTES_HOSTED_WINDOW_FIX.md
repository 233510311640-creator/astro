# Cypher v0.8.9.3 / Core Preview 8.5.3

## Evidence and purpose

The user's Core Preview 8.5.2 Notepad screenshot reports COMPLETED 4/4: reused window, delivered text, minimized, restored. The screenshot alone does not independently confirm the visible editor text or timing.

The subsequent Calculator report failed at 0/2 verified, after entering step 1. It lists:

| HWND | PID | Class | Minimized | Cloak flags |
| --- | --- | --- | --- | --- |
| 2492882 | 27408 | Windows.UI.Core.CoreWindow | No | 0x00000002 (shell) |
| 9766660 | 24232 | ApplicationFrameWindow | Yes | 0x00000000 |

Both owner HWNDs were zero. This supports investigating a hosted frame/content transition; it does not prove that these two particular windows belong together. The candidate therefore adds direct relationship proof instead of treating all cloaked windows as harmless.

## Changes

1. **Bounded child observation.** For an existing restored ApplicationFrameWindow with the exact registered AppUserModelID, scan at most 64 descendants. An eligible Windows.UI.Core.CoreWindow must have the same exact registered identity, be a confirmed child, and have that frame as its parent-chain root. Fresh confirmation must reproduce the same frame/core HWNDs, PIDs, classes and identity. Incomplete or ambiguous child scans fail; no arbitrary child is selected.
2. **Plan-bound proof.** Store an immutable copy of the relationship in memory and include its fingerprint in the approval binding. If an explicit Open action launches an absent app, a runtime pair may be derived from the uniquely observed new frame. No unrelated window is adopted, and the target remains the original bound frame.
3. **Narrow transition matching.** When multiple matching windows are reported, the only removable candidate is the exact previously proved content window. Its HWND, PID, class and AppUserModelID must still match. It must either be attached to the bound frame, or be its own root with owner zero and exactly the shell cloak flag 2. The exact frame must still be a root with cloak state zero. All other candidates remain and can cause AMBIGUOUS_WINDOWS. The attached branch handles reattachment during an inventory scan without inventing a new target.
4. **Approval visibility and guidance.** Approval details show the proved content HWND/PID. Ambiguity guidance explains that an already-minimized hosted app may need manual restoration before a fresh request. There is no persistent pair cache and no automatic restoration before approval.

The implementation does not depend on a guarantee that every Windows Calculator version has this layout. Missing proof retains the refusal. No fixed delay, retry, arming phase, raw input, clipboard automation, or forced foreground bypass was added.

## Windows API basis

The read-only relationship checks use Microsoft's [EnumChildWindows](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-enumchildwindows) and [IsChild](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-ischild). [GetAncestor with GA_ROOT](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-getancestor) walks parent windows, not the owner chain. [DWM cloak attributes](https://learn.microsoft.com/en-us/windows/win32/api/dwmapi/ne-dwmapi-dwmwindowattribute) distinguish app, shell and inherited cloaking. Those documented fields support the checks; none establishes an app-specific pairing on its own.

## Verification

- Linux source/regression suite: **223 discovered, 222 passed, one Windows-only compiler test skipped**.
- Five C# files receive lexical delimiter checks, and the existing suite parses the embedded XAML. These checks are not native compilation.
- The existing native behavioral harness now includes **40 scenarios (100–139)**. New cases exercise immutable pairing, both inventory orders, unproved pairs, changed identities, detached cloak/owner/root mismatches, extra windows, reattachment, fingerprint changes and six simulated minimize/restore transitions. They exercise the production pure matching rule and runner using fake observations; they do not reproduce native desktop behavior.
- The Windows installer must compile/run that harness, compile the full host, and pass its self-test before replacing the installed host. No Windows desktop or C#/.NET Framework compiler is available in the Linux workspace, so those gates have not run here.
- **Target-PC acceptance of 8.5.3 is pending.** Follow [the focused Calculator check](HOSTED_WINDOW_FIX_SETUP.md). Earlier 8.5.1/8.5.2 observations do not verify this change.

## Preserved behavior

The two-second arming pause remains absent. The six-step/three-app limit, one-time full-plan approval, expiry, exact app/window/control validation, human-managed text permission, cancellation-aware observation waits, metadata-only checkpoints, no retry/replay, no automatic undo and standard-user installation remain. Pair metadata is not added to checkpoint storage. Existing text entry still never reads back, saves or undoes editor content.

This release does not add voice, vision, durable chat memory, unrestricted desktop control, model downloads or paid APIs. It is a focused reliability patch, not completion of the broader assistant roadmap.
