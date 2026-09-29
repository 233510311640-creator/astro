# Cypher project status

**Updated:** 30 September 2026

**Repository:** [233510311640-creator/astro](https://github.com/233510311640-creator/astro)

**Purpose:** A resident Windows assistant for asking questions, finding information, working with approved files, and preparing bounded computer actions through a monochrome command-center interface.

## Current position

| Bundle | Status | What it means |
| --- | --- | --- |
| [`stable/`](stable/) — 10.20.3 | Installed on the development PC; automated validation passed | Current version to use. The user confirmed that `Ctrl+Win+Alt` opened chat at least once. `Ctrl+Alt+Space` starts the voice-command flow. |
| [`preview/`](preview/) — 10.21.0 | Builds and passes automated checks; **not installed as the replacement** | Adds a more robust wake/voice pipeline and optional cloud paths, but the real-microphone release gate remains open. |

This is a working preview, **not a finished, fully autonomous or reliably hands-free assistant**. Some capabilities require local models, permissions, a supported application, or explicit approval.

## What we have built

### Command center and local runtime

- A resident Windows application with a black-and-white command-center UI, tray controls, conversation input/output, status, Stop, and approval review.
- `Ctrl+Win+Alt` to show the chat; `Ctrl+Alt+Space` to begin a spoken command without opening chat. The tray also opens chat. The modifier-only chat shortcut was fixed in 10.20.3 after Windows accepted but did not deliver the earlier shortcut registration.
- Local model routing for fast, deeper, and vision tasks, with bounded requests, status, cancellation, and recovery information. The app uses its configured local runtime and Hermes integration rather than unrestricted shell access.

### Web, documents, images, and files

- Bounded public-web search, page reading, link following, site search, and inspected links/forms. Registered or supported browsers can open an approved HTTPS destination. This is **not** unrestricted control of logged-in websites or a browser profile.
- Search, summarize, answer, and compare documents in explicitly approved folders. Supported paths include text, PDF, and Office document workflows; answers show source evidence and disclose coverage limits. File tasks have scoped grants, review/approval, and supported undo paths.
- Ask about or describe a specifically named PNG in an approved folder using the configured local vision model. It does **not** provide live camera vision, general screen understanding, or guaranteed OCR.
- Bounded Windows actions such as discovering/launching supported apps, focusing an identified window, inspecting supported controls, and selected UI Automation actions. Consequential actions retain a visible one-time approval boundary. Cypher cannot freely operate every app or perform arbitrary computer actions.

### Voice

- Manual MIC recording uses local offline transcription and leaves an editable draft. READ ALOUD uses a local Windows speech voice; the user confirmed that playback works.
- The voice shortcut acknowledges, records, transcribes locally, and can auto-send a recognized command. It cannot approve Windows or file actions on its own. Speech quality and response speed still need improvement on the user's microphone and workload.
- Local wake-word listening exists, but repeated live tests have **not** established dependable “Cypher” activation. Do not treat wake-only control after Windows sign-in as solved.
- The 10.21 preview includes one-stream wake/command capture, speech-end detection, a warm Whisper worker, selectable microphone/voice settings, and an opt-in cloud transcription/ordinary-answer path. Cloud mode is off by default, requires an API key and consent, may incur charges, and has not completed a live API validation.

## Verification and boundaries

- The stable 10.20.3 installer completed the compiled-host self-test, Python tests, owned-worker checks, and local compatibility preflight before installation. The installed process reported READY after the update. The chat shortcut opened in one user test; repeated key-order and latency testing remain worthwhile.
- The 10.21 preview passed validation-only builds and synthetic tests. In supervised real-voice trials, the wake listener detected **0/20** prompted phrases, then **0/5** in a follow-up despite microphone signal on all five. These results block release; they are not evidence of a working hands-free wake word.
- No raw microphone audio is saved by default. The public repository excludes API credentials, runtime models, user files, installed application data, caches, and older duplicate release folders.
- Web pages, documents, images, and model output are treated as data, not permission to take a Windows or file action. Existing grants and approvals stay in force for both typed and spoken commands.

## Development path so far

1. Built the local assistant foundation, model routing, Windows host, safe action broker, and monochrome command-center UI.
2. Added bounded web research/navigation and approved document, file, Windows-operator, and PNG-vision workflows.
3. Added local dictation, draft handoff fixes, offline Whisper, READ ALOUD, wake-word experiments, and voice-command auto-send with action approvals preserved.
4. Split the shortcuts: voice on `Ctrl+Alt+Space`, chat on `Ctrl+Win+Alt`; fixed the modifier-only chat chord in 10.20.3.
5. Developed the 10.21 hands-free/cloud preview but held its installation behind live wake and privacy/cost checks.
6. Published the current stable and preview bundles in the public `astro` repository.

## What remains

1. **Reliable hands-free wake:** tune or replace the wake model using the user's real voice; pass at least 19/20 wake attempts and a two-hour background false-trigger check before installing 10.21.
2. **End-to-end voice quality:** measure wake-to-acknowledgement, transcription accuracy and delay, and time to first spoken answer. Test voice commands, cancellation, and approval prompts on the actual PC.
3. **Optional cloud validation:** only with the user's configured API key and explicit opt-in, compare local/cloud transcription on the same consented commands, verify fallback and cost limits, and test that ordinary cloud answers cannot invoke actions.
4. **Product polish:** reconcile older historical README statements with the current behavior, simplify setup and first-run guidance, expand supported tasks only within reviewed permissions, and rerun integrated regression tests before calling the project complete.

For detailed implementation and evidence, start with the [`stable` README](stable/README.md), [10.20.3 shortcut notes](stable/RELEASE_NOTES_CHAT_SHORTCUT_FIX_10.20.3.md), and [10.21 hands-free preview notes](preview/RELEASE_NOTES_HANDS_FREE_10.21.0.md). Older bundled release notes describe their own historical versions and may not describe today's installed behavior.
