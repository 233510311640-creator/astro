# v0.5.0 security boundary and limitations

## Tool boundary

The MCP server exposes exactly sixteen tools:

- eight bounded `Hermes Sandbox` read/propose/apply tools inherited from v0.3.3;
- four metadata-only inventory tools inherited from v0.4.0; and
- four organization tools: status, propose graphic plan, get plan, and validate plan.

There is no organization apply, move, copy, rename, replace, delete, directory-create, raw shell, code-execution, process, network, browser, UI-control, credential, messaging, scheduling, or administrator tool.

## Organization-planning invariants

- Organization is explicitly `dry-run-only`; real-file execution is absent.
- Sources must be under a separately human-approved metadata inventory root.
- Destinations must be under a separately human-approved planning root.
- Source and destination permissions cannot be identical; a destination cannot contain its source root.
- v0.5 accepts only files classified as graphic candidates by extension.
- It preserves the exact source basename, rejects overwrite, and permits at most 50 distinct source-to-destination entries.
- Traversal, absolute targets, drive syntax, hidden/protected components, unsafe Windows names, reserved device names, links, junctions, reparse points, control characters, and Unicode formatting characters are rejected.
- Plans store source size, nanosecond modification time, device/file identifiers, destination nonexistence, expiry, and a SHA-256 fingerprint over the immutable plan fields.
- Stored plan data is rechecked against its fingerprint when read.
- Validation detects missing or changed sources, changed permissions, unsafe roots, duplicate destinations, and destination conflicts without reading contents.
- Proposals expire after 60 minutes. At most 10 proposals may be created per 10 minutes, 20 proposed plans may remain active, and 1,000 plans may be stored before the broker stops creating more.
- Human-side review revalidates the plan and requires a fingerprint-derived typed code. Review changes only local plan status; it grants no execution permission.

## Filesystem effects

MCP startup creates or opens its local SQLite plan-state database. Proposing, reviewing, rejecting, and expiring a plan update only that local state database and metadata audit. They do not create proposed destination directories or modify source/destination files.

The separate human-side destination manager can update the destination allowlist after typed confirmation. Hermes cannot invoke that manager.

## Privacy

- Inventory and planning do not open real-folder files, render images, create thumbnails, hash contents, parse project files, read EXIF, or inspect archives.
- Approved source metadata and organization plans are visible to the local model and local Hermes session.
- `%LOCALAPPDATA%\LocalAssistantBroker\organization_plan_state.db` stores absolute approved roots, relative filenames, proposed destination paths, model-generated reasons, metadata snapshots, statuses, expiry, and fingerprints. Anyone able to read that Windows-user file can see those values.
- Inventory and organization audit events exclude scanned filenames, proposed paths, reasons, and file contents. They retain operation names, root/plan IDs, counts, statuses, success, and timestamps.
- Paths and filenames remain untrusted data, never instructions or permission. The organizer additionally rejects control and Unicode formatting characters in planned paths and reasons, but this does not make arbitrary filenames trustworthy.
- No data is intentionally sent to a paid inference API. Ollama is configured on loopback; Hermes session/configuration behavior remains a separate component that must be kept local and reviewed.

## Accuracy limitations

- Graphic classification is based only on extensions. It can produce false positives and false negatives.
- v0.5 cannot know whether a file is referenced by a PSD, Illustrator project, document, application, or workflow because it deliberately does not inspect contents or dependencies.
- Metadata validation is not a content hash. A change that preserves the checked size, timestamp, and file identity may not be detected. This release cannot execute the plan, limiting the consequence of that uncertainty.
- A human must judge the proposed categories and destinations. Marking a plan reviewed does not assert that the classification is correct.
- BitLocker protects powered-off data; it does not isolate an unlocked Windows account. Malware or another process running as the same user can access files independently of this broker.

## Stop conditions

Remove the MCP integration immediately if the tool count is not exactly sixteen, any organization execution or unrestricted tool appears, a plan/review changes a real source or destination, traversal or a link escape succeeds, filenames/reasons appear in the metadata audit, or an unrestricted Hermes built-in becomes enabled.
