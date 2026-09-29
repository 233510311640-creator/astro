Current bundle: **9.5.0 File Explorer**. Start with [FILE_EXPLORER_SETUP.md](FILE_EXPLORER_SETUP.md).
The component guidance below is historical or supplemental.

Current 9.4.0 release: see RUNTIME_READINESS_SETUP.md and SECURITY_RUNTIME_READINESS.md. Previously verified file tests do not need repeating. Historical component documentation follows.

# Security boundary: Cypher Core Preview 9.3.0

The new native file-task route reuses the permissioned operator and brings exact folder/action/undo
reviews into the human approval panel. See [SECURITY_DESKTOP_FILE_TASKS.md](SECURITY_DESKTOP_FILE_TASKS.md).
The installer does not grant user-folder permission. A user can explicitly grant or revoke a folder
through the new native review. File tasks make no model/network call and receive no research output.
The old claim that the host cannot edit folder configuration applies to earlier versions only.

ResearchHost.cs, research_worker.py and all four workflow engine/bridge files retain 9.2.12 bytes.
Historical research and app boundaries follow. Their descriptions of earlier releases are retained
for context; the file-task boundary above describes the new authority path.

---

# Security boundary: Cypher Core Preview 9.2.12

Preview 9.2.12 changes only the academic evidence guard, its version and host integrity pin.
Preview 9.8.0 changes presentation only. Its opaque monochrome shell keeps the same named approval,
Stop, recovery, input, response and routing controls. The layout self-test exercises both side rails
and the central workspace at the supported minimum. The geometry schema advances to 9.8.0 so the
new default layout is shown once; no conversation, prompt or response content is persisted.

The native workflow/approval/UI behavior remains as accepted in 9.2.11. Research findings still
do not authorize Windows actions. See `SECURITY_READONLY_RESEARCH.md` for lexical-check limits.

Preview 9.2.11 preserves the original observation deadline across early Windows wakes and checks
cancellation before each remaining wait. It does not extend execution budgets or skip installer
self-tests. The internal injected clock/wait constructor is used only by the in-assembly test
harness; production constructs the stopwatch and cancellation wait directly.

Preview 9.2.10 refines the native UI. Prompt starter cards only fill enabled input, never submit
requests. The 9.2.9 geometry preferences are retained. Research worker bytes,
runtime startup and action permissions are retained. Review details remain scrollable with the
one-time approval buttons outside the collapsed session details section.

The retained 9.2.8 correction screens selected academic sources' existing bounded passage catalog before
generation for recognized two-concept questions. It reuses the shared lexical predicate (corrected in 9.2.12) from
the final evidence guard. If all counts are zero, the worker makes no Ollama API request and
reports `PAPERS_DIRECT_PASSAGE_MISSING`. A rejected draft instead reports its wording/citation
failure without claiming that the abstracts lack evidence. Counts and reports are memory-only.
The predicate can miss synonyms, fragmented long sentences, or subtle relations; passing it does
not establish entailment or causality. Search terms and all authority boundaries below are retained.

This release adds no Windows or filesystem authority. It retains 9.2.6's pinned, standard-user
Ollama autostart and its fixed loopback endpoints unchanged.

For unambiguous complete two-concept relationship questions, a deterministic local builder makes
OpenAlex's query from two normalized literal concept phrases joined with fixed Boolean AND.
Meaningful stop words, numbers, order, and repetitions are retained. Query syntax is generated,
not copied from user punctuation. Unknown or qualified forms retain the existing punctuation-safe
transport query. No model-generated terms or synonyms are introduced.

The primary path makes one keyless OpenAlex Works request with a fixed eight-record ceiling and
the existing 512 KiB response cap. Only an exact HTTP 503 permits one immediate keyless Crossref
Works request, also capped at eight records, with provider-neutral terms. The original question
remains local for both providers' source-selection logic and the same single synthesis call.
No additional provider, key, account, payment, retry, pagination, delay, PDF/full-text read, or
record-page fetch is added.

All returned records are validated before any abstract enters the model. The local selector uses
only abstract text and the original question, with provider order as the exact-score tie-breaker.
It returns at most two abstracts. Existing OpenAlex reconstruction, Crossref JATS normalization,
DOI/language/schema checks, citations, quotation bounds, and direct-relationship checks remain.
Provider titles, identifiers, scores, rankings, and publication metadata are excluded from local
relevance scoring and model evidence. Crossref's language/retraction coverage limitation remains
disclosed.

Focused phrase matching may miss synonyms, qualifiers, and nuanced evidence. The conservative lexical
directness guard does not establish causality, truth, or study quality. Failed/empty discovery never
triggers a broader search or a substitute model. A partial result is not claimed as proof of improved
source precision.

Wikipedia/explicit-URL routes, job desktop restrictions, bounded public-address/TLS handling,
model selection/budgets, consequential-action approvals, and Stop lifecycle are retained. Research
has no action tools and is not appended to chat/workflow history. No extra research warning,
approval, countdown, or fixed waiting stage is added. See
[SECURITY_READONLY_RESEARCH.md](SECURITY_READONLY_RESEARCH.md) for the complete boundary and
[release notes](RELEASE_NOTES_ACADEMIC_EVIDENCE_PREFLIGHT.md) for validation limits.

## Authority

Cypher runs with the signed-in standard user's token. It does not self-elevate, install a service, create a Scheduled Task, or request UAC. Hermes and the capability broker—not the language model or UI—decide which tools exist, which roots are accessible, and which actions require approval. This preview does not edit that configuration.

## Local communication

The compiled host accepts only a Hermes endpoint on `127.0.0.1`, `localhost`, or `::1`. Every Hermes call uses the existing random bearer key. The key is stored as DPAPI `CurrentUser` protected data and is never placed in the preview configuration, checkpoint, or log.

For Hermes communication, the host uses only the authenticated capability, toolset, Runs API, event-stream, stop, and approval routes. Run IDs are syntax-validated before use. HTTP error bodies are suppressed because a server may echo private request content in an error. Research uses a separate public HTTPS reader and the fixed local Ollama endpoint; it does not use Hermes sessions.

## Privacy and persisted data

The host log does not contain prompts, model answers, tool arguments, API keys, approval content, filenames, or conversation history. Recent conversation context remains in memory and is cleared by **New Chat** or process exit.

Preview 7.1 displays a bounded copy of the active request, elapsed activity, lifecycle phase, and streamed answer in the command center. That activity display is memory-only and is not added to the log, UI-state file, or task checkpoint.

`ui-state.json` stores only numeric command-center geometry, a layout version, and one Boolean pin value.

`active-task.json` is the Preview 7 recovery checkpoint. Its schema permits exactly:

- schema version;
- validated Hermes run ID;
- `fast` or `deep` model profile;
- lifecycle phase and recovery state;
- start and last-update timestamps;
- aggregate tool-started, tool-completed, and tool-failed counters.

The file is capped at 16 KiB, written through an atomic temporary replacement, rejected if it has any unexpected field, and rejected if it is malformed, future-dated, or more than seven days old. It cannot contain prompts, answers, filenames, paths, tool arguments, approval details, credentials, or hidden reasoning. An invalid checkpoint is preserved for human inspection and never executed.

`last-failure.json` is a separate diagnostic receipt. Its exact schema permits only a validated run
ID, `fast` or `deep` profile, one bounded failure-stage enum, failure timestamp, three aggregate
tool-event counters and a Boolean response-observed flag. It is capped at 8 KiB, atomically replaced,
expires after 30 days and is rejected if a field is missing or unexpected. It contains no prompt,
answer, filename, path, tool argument, approval content, provider error text, credential or hidden
reasoning. A successful or newly started run clears the prior receipt.

## Recovery truthfulness

The checkpoint is a locator, not proof of completion. After restart Cypher asks Hermes for the authoritative run state:

- a confirmed active run is reattached to its event stream;
- a confirmed terminal run is reported as completed, cancelled, or failed and then clears the checkpoint;
- an unknown or unreachable state becomes **Recovery required** and preserves the checkpoint;
- no replacement run is silently created;
- no success is inferred from a closed stream or missing checkpoint;
- a pending approval is shown only if Hermes returns the current review details.

The tray exit command refuses to close Cypher while a run is active, stopping, or awaiting recovery. The installer likewise refuses an upgrade while the current heartbeat reports active work.

## Approval and cancellation

Cypher exposes only one-time approval and denial. It deliberately omits session-wide and permanent approval. Approval payloads are not persisted by the host. Fingerprinted capability-broker plans remain a separate exact-plan boundary.

**Stop** closes the local event stream, sends Hermes' safe-interruption request, and polls the run status. Cypher reports a terminal result only after Hermes confirms it. If confirmation fails, the checkpoint remains and the UI exposes a retry instead of claiming cancellation or completion.

## Direct permissioned-tool reliability

When Hermes already exposes an exact permissioned MCP schema, Cypher calls it directly. It does not wrap that eager schema in `tool_search`, `tool_describe` or `tool_call`. If Hermes exposes only its progressive-disclosure bridge, Cypher performs at most one bounded search for an explicitly requested named capability, preserves the returned wire name verbatim, and describes it only if the schema remains unavailable. Discovery does not grant authority: the broker still enforces its approved roots, fingerprints, external approval and verification rules.

Cypher must fail closed if the discovery brokers are absent or no exact schema is returned. It must not substitute terminal, shell, built-in file operations, or invented commands for a requested permissioned workflow.

## Deterministic Windows observation and approved control

Preview 8 moves four narrow request classes ahead of model and Hermes dispatch: registered application listing, titled visible-window listing, titled foreground-window observation, and observation-boundary status. The compiled host reads only the existing human-managed app-registry metadata or Win32 top-level-window metadata. It returns bounded display data in memory and records only a content-free event name, outcome, and duration.

Preview 8.1 adds a separate deterministic control route for two exact actions only:

- launch one application already present in the human-managed app registry, with no arguments; or
- focus one currently visible titled top-level window by the exact numeric ID returned by observation.

Preview 10.1.1 adds a third separately parsed action: send one validated public HTTPS destination to
one exact human-registered application. A bare DNS domain receives the fixed `https://` prefix. The
route rejects other schemes, credentials, whitespace, IP literals, local/reserved names and multiple
destinations. App identity, executable metadata/full SHA-256, normalized URL length/SHA-256, action,
selection policy and expiry are bound into the one-time approval and revalidated before execution.
Execution uses the exact executable, `UseShellExecute=false`, and one quoted URL argument. It does
not use a shell, raw input, clipboard, clicks or screenshots. Verification is limited to accepted
invocation plus an observed registered-app window or live process; the address bar, page and network
are not read, so page load is never claimed.

Preparation is not execution. Cypher resolves the app or window first, creates an in-memory approval object, binds its canonical action and target metadata to a SHA-256 fingerprint, and displays the exact evidence in a native approval card. The user must choose **Approve once** or **Deny**. The approval expires after 60 seconds, is marked consumed before execution, cannot be replayed, and is lost safely if Cypher exits or restarts.

Immediately before execution, app launch rechecks the registry record, executable path, reparse-point status, length, last-write timestamp and full SHA-256. Window focus rechecks the exact handle, class and PID. The reviewed title remains in the approval fingerprint and display evidence, but is not treated as stable live identity because packaged Windows apps may refresh presentation text without replacing the window. A changed or missing stable target fails closed and requires a new request. Launch uses `Process.Start` on the exact `.exe` with `UseShellExecute=false` and no arguments; focus uses only the exact validated Win32 handle. Cypher claims success only when it observes a matching process/window or the exact foreground handle. Dispatch without a postcondition is reported as not verified.

The direct routes still cannot accept arbitrary paths or arguments: the sole argument-bearing route
accepts exactly one validated public HTTPS URL under the 10.1.1 boundary above. They cannot click,
type, capture the screen, run a command, close or kill a process, write a file, modify broker
configuration, grant a lasting permission, or perform arbitrary multi-step work. The explicit
five-action workflow described below is the only new composition route. App closure and focus
reversal remain ordinary user actions rather than hidden automatic undo.

Preview 8.2 adds one bounded Windows UI Automation layer. Read-only inspection is permitted only for a currently visible top-level window whose process executable exactly matches a human-managed application-registry entry. The host examines at most 600 Control View elements to depth 6 and returns at most 120 actionable controls. It reads only bounded accessibility metadata needed to identify the control and advertise supported Invoke, Toggle, SelectionItem, or ExpandCollapse patterns. Password controls and sensitive application processes are excluded.

Credential/sign-in/security processes and common password-manager executables are refused even if someone registers them. A requested action must use the exact fresh `uia-` control ID and exact current window ID shown by inspection. Preparation binds the action, registered-app record and executable hash, window ID/title/class/PID, control accessible metadata/tree path, and expiry into the same one-time SHA-256 approval boundary. Immediately before execution, Cypher rechecks every identity field, current enabled/on-screen state, and requested pattern. Toggle, Select, Expand, and Collapse verify their exposed state; Invoke reports only that Windows UI Automation delivered the exact pattern without error and does not overclaim an app-specific downstream result.

Preview 8.3 extends application identity without treating a packaged app's shared host executable as sufficient authority. A version-2 registry entry may hold an exact Windows `AppUserModelID`. Cypher reads the top-level window's AppUserModelID from the Windows property store and accepts the window only when its executable or its nonempty packaged identity exactly matches the human-managed record. The optional identity, plus the independent `allow_text_entry` Boolean, are bound into every prepared action and revalidated before execution. A valid version-1 registry migrates with both new capabilities disabled unless the human-side seed/manager explicitly supplies them.

For a registered app with `allow_text_entry=true`, a fresh Edit or Document control may expose `set-text` only when Windows UI Automation reports a writable managed `ValuePattern`. `IsPassword` controls and fields whose accessible metadata indicates passwords, passcodes, PINs, OTPs, verification/security/recovery codes, secrets, API keys, payment-card data, private keys, or seed phrases are omitted. The request accepts at most 500 printable single-line characters. The raw payload stays only in the in-memory pending action; the canonical approval binds its length and SHA-256. Denial, expiry, execution, and shutdown discard it.

Immediately before Set Text, Cypher rechecks the registered app identity and permission, executable metadata/hash, window identity, control identity/path, enabled/on-screen state, supported value pattern, text length, and text hash. It then calls only `ValuePattern.SetValue`. It does not read the field's current Value/Document content and therefore cannot generically prove every app-specific downstream effect; the result truthfully reports only delivery to the exact control without an exception.

Preview 8.4.1 composes those existing primitives into one bounded natural workflow: `Open <registered app> and write: <text>`. This is still one approval and one Set Text effect, not a general macro. Preparation requires an exact registered app with `allow_text_entry=true`. If one matching window already exists, exactly one safe writable editor must exist and its full identity is bound before approval. If no matching window exists, the approval instead binds the deterministic `single-existing-or-single-new-editor-v1` selection policy and the exact registered executable; execution may launch it without arguments and then requires exactly one matching window and exactly one safe writable editor. More than one matching app window or editor fails closed. The app identity, executable metadata/hash, selection policy, bounded text length/hash, action, expiry, and any pre-resolved window/control identity are included in the approval fingerprint and revalidated immediately before use. A top-level title remains reviewed and fingerprinted context, while live execution uses the stable HWND, PID, class, packaged/desktop app identity, executable and editor identity so a harmless title refresh cannot invalidate an otherwise exact target.

The bounded UI layer uses no raw mouse or keyboard API, SendKeys, coordinates, clipboard automation, screenshot, shell, or process termination. It does not chain actions. UI trees are dynamic, so stale IDs fail closed and require a new inspection and approval.

The optional `CONFIGURE_CYPHER_HERMES_TOOLS.cmd` helper requires an exact human phrase, changes only
`tools.tool_search.enabled` and `tools.tool_search.listing`, restarts the loopback gateway and verifies the registered
`hermes-sandbox` server. It refuses administrator execution and active Cypher work. If verification
fails, it restores the previous setting. It does not change models, MCP roots, approvals, operator
permissions or built-in terminal/file authority.

## Human checkpoint management

The installed manager can print only whitelisted checkpoint or failure-receipt metadata. `forget-checkpoint` requires the preview to be stopped and the exact confirmation phrase `FORGET RECOVERY CHECKPOINT`. Forgetting local recovery metadata does not stop or modify the Hermes run and therefore should be used only after the operator has independently resolved its state.

## Installation and rollback

The installer runs source tests, compilation, executable self-test, and authenticated Hermes capability checks before switching the login shortcut. The executable self-test writes, replaces, reloads, rejects a contaminated checkpoint, and removes its temporary recovery store. The prior v0.6.3 shortcut is preserved for cooperative rollback. No process-kill command is used.

## Deliberately excluded

- administrator or SYSTEM authority;
- silent, permanent, or recovered-blind approval;
- arbitrary shell/code execution from the UI or command-line arguments for launched apps;
- LAN or public API binding;
- cloud model/API fallback;
- image, microphone, or wake-word input;
- persistent personal memory;
- prompt/response or content logging;
- unrestricted application/window control, existing text/value/document reads, raw keyboard typing, clipboard pasting, raw mouse input, coordinates, screenshots, arbitrary process termination, unrestricted action chains, or hidden replay;
- changes to MCP servers, broker roots, permissions, models, or approval policy. The separately
  consented reliability helper may switch only Hermes' schema-loading mode as documented above.

## Ordered workflow boundary in Preview 8.5.0

`Workflow:` is an explicit user-input route, evaluated before model routing and before broad read-only
intent detection. Model output cannot itself trigger it. Up to six steps across three registered
apps are allowed. Only Open, Write in, Focus, Minimize, and Restore are implemented.

The entire plan is prepared without mutation. Approval includes full text and ordered actions,
an exact app/executable binding, the existing target window/editor when available, and the rule
for an app that must be opened. The one-time claim uses Interlocked.CompareExchange. A wrong,
expired, already consumed, or changed fingerprint cannot run. Denial discards the text.

A pre-existing app window is never silently substituted. A previously absent app can be bound only
through an explicit approved Open step. Dynamic automatic editor selection requires a complete
bounded accessibility scan and exactly one enabled, on-screen writable editor. Unreadable elements
and truncation cause refusal. Existing-value reads, password controls, raw input, and clipboard/shell
fallback remain absent.

The runner checkpoints before mutation and after a verified receipt. Failed storage or verification
blocks later steps. Partial effects are reported; there is no retry or implied rollback. A blocked
native call can outlast the scheduling budget; cooperative Stop does not claim otherwise.

The checkpoint schema excludes target names, window titles, text, paths, hashes, and reusable consent.
Recovery only marks metadata as interrupted; it never reconstructs or executes a plan. Automatic
save, append, Undo, close/kill, arbitrary control chains, and unattended routines are not added.

## Bounded Office documents in Preview 10.2.0

DOCX, PPTX and XLSX are treated as untrusted ZIP/XML containers. The document worker reads one
explicitly selected file through an existing named read grant, then gives only the verified snapshot
bytes to a separately SHA-256-pinned Office parser child. The child receives no path, permission
store, question, prompt, model endpoint, network client, shell, Office application or action engine.

The parser accepts only the modern non-macro OOXML main content types and enforces input, archive,
entry, expanded-size, per-part, compression-ratio, XML-element, extracted-unit, extracted-text,
response and time limits. It rejects encryption, traversal, duplicate names, unsupported compression,
DTD/entity declarations, external required relationships, malformed relationships and a requested
extension that does not match the detected package type. It never loads an embedded object, follows
an external relationship, starts Microsoft Office, executes a macro or evaluates a formula.

The parent validates the complete parser response and exact byte totals before any optional local
model request. Extracted Office text remains untrusted evidence under the existing 4,096-byte model
budget. It cannot grant permission, initiate an action, modify a file or enter chat history.
