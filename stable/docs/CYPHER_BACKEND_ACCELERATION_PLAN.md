Current sequencing: see CYPHER_NEXT_MILESTONES.md and ../DESKTOP_BETA_SETUP.md. The 9.3 desktop bundle supersedes the research-first next-step notes below.

# Cypher Backend Acceleration Plan

Status: adopted for the post-Preview-7.1.1 development sequence  
Voice status: deliberately deferred; Wispr Flow may be used as an optional external dictation layer  
Priority: make Cypher a dependable, permissioned Windows operator before further visual redesign

## 1. Delivery change

Cypher will no longer ship one tiny user-visible capability per milestone. Work will be grouped into
larger, dependency-aligned backend bundles. Each bundle still keeps a single security boundary and a
single rollback path so that speed does not come from silently broadening authority.

The UI is frozen except for controls required to understand, approve, stop, verify, or undo backend
work. The WPF shell remains a validation client until the backend contract is stable.

## 2. Model policy

The current model names are replaceable role assignments, not permanent product dependencies:

| Role | Current model | Responsibility |
|---|---|---|
| Fast / reflex | `qwen3.5:9b-q4_K_M` | Intent triage, ordinary conversation, short planning, summaries and low-cost tool loops |
| Deep / deliberative | `gpt-oss:20b` | Difficult analysis, debugging, multi-constraint planning, risk review and synthesis |
| Multimodal / fallback | `gemma4:e4b` | Screenshot, image and document-layout interpretation after vision input is connected; compact fallback |

Models may be replaced independently after a candidate passes the Cypher benchmark, tool-call schema
tests, prompt-injection tests, cancellation tests, latency/VRAM measurements and a rollback check. A
model update never grants new tools or permissions. Cypher must not silently download or switch to an
unapproved model.

On the target 16 GB GPU, memory-heavy models run sequentially. Parallelism is used for independent
tools and CPU work; model hand-offs use bounded structured artifacts. Keeping all three models loaded
simultaneously is not a product requirement.

## 3. Multi-model operating pattern

Most tasks use one model. Additional models are invoked only when they add measurable value:

1. Cypher classifies the request using deterministic host rules and the currently available inputs.
2. The fast model handles ordinary work or produces a bounded task brief for a genuinely complex job.
3. The deep model receives the task brief and tool evidence for complex reasoning; it does not receive
   extra authority.
4. The multimodal model is called only when an image/screenshot/document frame is part of the task.
5. The deterministic host validates proposed actions, requests approval where required, executes an
   allowlisted capability, checks the postcondition and records metadata-only evidence.
6. A final response is produced from verified results. Models may disagree; the host never treats a
   second model's opinion as execution evidence.

## 4. Bundled backend releases

### Bundle A — Permissioned Local Operator

Target: first useful backend beta.

Alpha 1 source implementation complete on 2026-08-21; target-Windows acceptance pending.

- configurable, benchmark-gated fast/deep/vision role registry;
- permission center data model for approved user folders and capability scopes;
- bounded content reading for explicitly approved file types and roots;
- approval-gated create, replace, copy, move, rename and create-directory operations;
- quarantine instead of permanent deletion;
- collision protection, source fingerprints, post-action verification and undo;
- batch plans with item and byte limits;
- model/tool workflow state, cancellation and restart reconciliation;
- adversarial path, link, race, prompt-injection and audit-privacy tests.

Implemented in Alpha 1: all listed file-operator primitives, explicit permission records, encrypted
plans/undo, exact external approval, batch limits, postcondition verification, reverse rollback,
restart reconciliation, six MCP tools and human-only management commands. Remaining Bundle A gates:
target-PC DPAPI/PowerShell/Hermes validation, controlled interruption testing, a representative task
suite, and integration of operator lifecycle evidence into the resident Cypher command center.

### Bundle B — Windows and Research Operator

- read-only Windows UI Automation inventory;
- allowlisted, stable-element application actions with exact previews;
- process and window observation without keystroke or clipboard harvesting;
- isolated read-only research browser with citations and provenance;
- prompt-injection separation between external evidence and authority;
- application-specific verification and bounded recovery.

Windows Operator Preview 1 source implementation completed on 2026-08-22. It establishes the first
Bundle B slice: Win32 top-level window inventory, foreground observation, exact registered-app launch,
and verified focus requests. It deliberately stops before control-level UI Automation, keyboard or
mouse injection, screenshot capture, process termination, and research browsing. Those remain the
next Bundle B work rather than being replaced by unrestricted shell access.

### Bundle B update — 27 August 2026

The user's Core Preview 8.4.1 screenshot confirms the existing-Notepad natural write path.
Core Preview 8.5.0 / v0.8.9.0 is now an ordered-workflow source candidate: six steps, three registered
apps, complete native plan approval, exact target revalidation, metadata checkpoints, partial-result
reporting, and cooperative Stop without automatic retries or replay. Supported steps are Open,
Write in, Focus, Minimize, and Restore; model-generated general plans are not executed.

Native compilation, real-app acceptance and interruption checks remain release gates. Research
browsing, reviewed memory and schedules are still separate work. See the current release notes and
`MULTISTEP_WORKFLOW_SETUP.md` before advancing this bundle.

### Bundle B update — 28 August 2026

The user accepted Core Preview 8.5.3's focused Calculator minimize/restore result. The artificial
arming delay remains removed; one-time approval for consequential Windows workflows remains.
Broader live interruption/crash-recovery acceptance is still separate.

Core Preview 9.0.0 / v0.9.0.0 implements the first research slice: one to five explicit public HTTPS
URLs, bounded HTML/plain-text reading with public-address and robots checks, synthesis by the existing
local model without tools, and source-ID/quote provenance checks. Evidence is not appended to Hermes
history or used to create action authority. Stop controls only the owned research worker. This is
process separation, not an OS sandbox. Automatic source search and stronger OS containment remain
future work; no paid API, unverified search scraping interface or model download is introduced.

273 Python checks pass, with one Windows compiler test skipped. Native installation gates and the
first real website/local-model acceptance are still pending. Use `RESEARCH_PREVIEW_SETUP.md` for the
focused check. This does not close all Bundle B production-readiness gates.

### Bundle C — Continuity and Routine Operator

- reviewed personal memory with remember, forget, why, pause and export;
- session/task continuity without raw hidden-reasoning retention;
- fixed, versioned scheduled recipes with resource limits and revocation;
- backup, restore, permissions review and long-run reliability checks;
- signed/reproducible release preparation.

Native voice remains after these backend bundles unless it becomes necessary for an acceptance test.

## 5. Time target

Assuming several focused development and target-PC validation sessions each week:

- Bundle A: 10–14 focused days;
- Bundle B: 2–3 additional weeks;
- Bundle C: 2–3 additional weeks;
- dependable text-first beta: approximately 6–9 weeks;
- hardened v1: approximately 3–5 months including soak testing and recovery work.

These are planning ranges, not release promises. Failed security or target-PC acceptance tests stop a
bundle; they do not cause the relevant gate to be removed.

## 6. Acceptance bar

A backend bundle is accepted only when:

- the target-PC clean install and rollback succeed;
- no requested path or capability can escape its approved scope;
- every consequential action has a host-generated preview and fresh approval;
- every success claim has an independently checked postcondition;
- Stop reaches a verified terminal state;
- restart recovery does not duplicate actions;
- logs and checkpoints contain no prompt, response, file-content, secret or raw reasoning;
- a fixed representative task suite passes repeatedly, not only once.


### Citation correction candidate — 28 August 2026

Core Preview 9.0.1 replaces model-written quotes with reader-assigned passage IDs.
The original exact-source validator remains. This addresses the observed quote
copying failure; real-model acceptance of the corrected request remains pending.
This does not advance automatic search, browser interaction, durable memory, voice
or vision. See `RELEASE_NOTES_CITATION_FIX_1.md` and `RESEARCH_PREVIEW_SETUP.md`.


### Research clarity candidate — 28 August 2026

The user's 9.0.1 one-source result passed the focused UI/source/model check. It exposed repeated
finding wording and an unhelpful prefix-only excerpt. The 9.0.2 candidate adds distinct-finding
instructions, conservative exact text/evidence deduplication after validation, and numbered
source-bound excerpt previews. Source checks, one generation and the absence of arming delays remain.

309 tests discovered: 308 passed, one Windows compiler skip; 86 research tests include two-source
fixture attribution and adversarial duplicate/preview regressions. These are not live-model results.
Next is the single two-source comparison in `RESEARCH_PREVIEW_SETUP.md`, not a broad workflow retest.
Automatic search, reviewed memory, scheduling, voice, vision and production-readiness gates remain
separate future work. Keep 9.0.1 available for reinstall rollback.


### Explanatory evidence candidate — 28 August 2026

The 9.0.2 target-PC screenshot established two-source execution with two findings, but previews
still favored introductory/signature text and the urlopen answer lost important qualifications.
The 9.0.3 correction preserves structural evidence and nearby definition context, excludes labels
from selectable support, prefers selected explanations in previews and asks the existing model to
retain conditions, return types and protocol scope. There is no additional generation or arming
step, no API-specific answer template and no semantic-correctness guarantee.

333 tests discovered: 332 passed, one Windows compiler skip; 110 research tests include 24 new
structural/context regressions. CP1252-default and EncodingWarning-as-error checks pass. The Windows
workflow implementation and native research lifetime are retained (version/hash integration only).
Next is the same two-source question after installing 9.0.3, with explanatory previews and qualified
wording checked on the real local model. Keep 9.0.2 for rollback. This corrective slice does not
advance automatic search, action authority, memory, scheduling, voice, vision or production acceptance.


### Focused qualification candidate — 30 August 2026

The 9.0.3 target-PC run established native installation, two-source execution and corrected
explanatory previews. Its `urlopen` finding still overgeneralized a protocol case and omitted the
returned-response distinction, while an unrelated error-handling limitation appeared.

The 9.0.4 correction adds bounded question-name focus groups over the same reader-validated passages.
It prioritizes direct, return/result and contrasting case-scope evidence in the existing single
generation. Focus metadata is non-citable and grants no authority. Direct questions suppress valid
but unrequested model limitations only after the entire list passes validation; malformed output
still fails closed. Selected return/result evidence can win the display-preview ranking.

340 tests were discovered: 339 passed and one Windows compiler test was skipped; all 117 research
tests pass. CP1252-default and EncodingWarning-as-error checks pass. No automatic retry, arming delay,
extra model call, permission change or Windows workflow change is introduced. Next is the unchanged
two-source target-PC question after installing 9.0.4. Keep 9.0.3 for rollback. This remains a focused
research-quality correction, not automatic search, semantic verification or broader Bundle B acceptance.


### Fail-closed scope-guard candidate — 31 August 2026

The 9.0.4 target-PC run retained corrected previews and removed the unrequested limitation, but its
`urlopen` finding still generalized an HTTP-specific case and added unsupported "actual network
request" wording. Prompt focus alone did not prevent that model behavior.

The 9.0.5 correction adds a deterministic final guard for named-definition findings after selected
passage IDs are revalidated. Case-scope evidence requires explicit conditional wording; unsupported
scope intensifiers and substantive terms of seven or more characters are rejected unless present in
the question or selected evidence, apart from fixed neutral comparison language. Rejection withholds
all claims as `CLAIM_SCOPE_UNSUPPORTED` while keeping source metadata. The same single generation uses
temperature zero and stronger source-vocabulary guidance.

346 tests were discovered: 345 passed and one Windows compiler test was skipped; all 123 research
tests pass. CP1252-default and EncodingWarning-as-error checks pass. No retry, repair call, arming
delay, approval, permission change, or Windows workflow change is introduced. Next is one unchanged
two-source target-PC check after installing 9.0.5, with 9.0.4 retained for rollback. This is a
lexical/structural guard, not semantic verification, automatic search, or broader Bundle B acceptance.


### Research desktop-isolation candidate — 1 September 2026

The user's 9.0.5 result accepted the fail-closed scope path: two sources, zero displayed findings and
`CLAIM_SCOPE_UNSUPPORTED`. Before widening research to automatic discovery, 9.0.6 narrows the owned
worker's Windows desktop surface without changing its request flow.

The existing job now requires every supported UI restriction used by Cypher: foreign USER handles
and hooks, clipboard read/write, system parameters, display settings, global atoms, desktop switching
and Windows exit calls. The host sets and queries the exact mask before process start and fails closed
on any difference. The installer exercises that native boundary with its offline worker rejection.

347 tests were discovered: 346 passed and one Windows compiler test was skipped; all 124 research
tests pass. This is compatible job-level desktop isolation, not AppContainer/filesystem/network
sandboxing. It adds no search provider, model call, retry, approval, delay, Stop stage, permission or
workflow action. Next is target-PC installation only, with 9.0.5 retained for rollback.

### Bounded Wikipedia-discovery candidate — 1 September 2026

The user accepted the 9.0.6 native installation gate. Core Preview 9.1.0 now adds one fixed official
English Wikipedia Action API request for a question-only `Research:` command. It sends only the typed
question, accepts at most three namespace-0 title/page-ID records, constructs candidate URLs locally,
and never treats search snippets or provider URLs as evidence. Candidate page and robots redirects
remain pinned to `en.wikipedia.org`; the accepted reader, evidence, citation, scope and job boundaries
then apply unchanged.

The explicit one-to-five-URL route bypasses discovery. There is no paid API, API key, HTML search-
result scraping, pagination, provider fallback, retry, added local-model generation, approval, arming
delay, Stop stage, permission or Windows workflow change. This is bounded English Wikipedia
discovery, not general web/current-news search. Target acceptance is one live question-only request;
9.0.6 remains the rollback baseline.

### Bounded Wikipedia reader reliability candidate — 1 September 2026

The user accepted Core Preview 9.1.0's live provider path with two sources and four findings. Its
third candidate failed `CONTENT_LIMIT`. Core Preview 9.1.1 keeps provider relevance order, reads only
until two usable discovered sources exist, and uses a disclosed 1 MiB prefix from an oversized
readable page instead of discarding it. Discovery JSON and robots policy remain strict.

There is no additional provider request, retry, fallback, model generation, approval, arming delay,
Stop stage, permission or Windows workflow change. Explicit one-to-five-URL research remains
separate and attempts all selected sources. Keep accepted 9.1.0 for rollback; the only live gate is
the unchanged question-only robots.txt request.

### Bounded academic-research candidate — 1 September 2026

The user accepted Core Preview 9.1.1's live two-usable-source stopping behavior. Core Preview 9.2.0
adds a distinct `Research papers:` route backed by one keyless OpenAlex Works query. It considers no
more than three returned English non-retracted records, strictly reconstructs their inverted abstract
text, and supplies at most two eligible abstracts to one existing local-model call. Titles, IDs,
ranking/relevance scores, citation counts and other metadata are excluded from model evidence.

The fast-path contract is structural: one provider request, no record-page/PDF/full-text fetch, no
retry or provider fallback, and one synthesis call. There is no new approval, arming delay, Stop
stage, model installation, permission or Windows workflow change. Target-PC cold/warm latency and
VRAM are observed with the single acceptance request; 9.1.1 remains the rollback baseline.

### OpenAlex connectivity reliability correction — 1 September 2026

The target-PC 9.2.0 request selected the academic route but returned the generic
`PAPERS_UNAVAILABLE` diagnostic with zero sources. The exact query and response schema validate.
Core Preview 9.2.1 therefore tries up to four addresses from one fully validated public-IPv4 DNS
result only during pre-request TCP/TLS establishment. It stops immediately on certificate failure
and never retries after an HTTP request begins.

Status-specific diagnostics now distinguish connection exhaustion, interrupted exchange, anonymous
rate limiting, access denial, provider service failure, and other unsuccessful responses. This adds
no provider request, provider fallback, credential, model generation, approval, arming delay, Stop
stage, permission, or Windows workflow change. The same one target-PC academic request is the gate.

### Bounded Crossref 503 fallback — 2 September 2026

The target-PC status check then proved a complete OpenAlex TLS/HTTP exchange ending in exact HTTP 503
while anonymous search was paused under provider load. Core Preview 9.2.2 keeps OpenAlex primary and
permits one immediate keyless Crossref Works request with the same question only for that exact
status. Other statuses, invalid data, empty results, connection failures, and post-send failures do
not transition providers. Neither request is retried or delayed.

Crossref contributes only bounded normalized publisher-deposited journal-article abstract text.
Strict schema, DOI, type, optional language/score, markup, size, duplicate, and English-text checks
run before at most two abstracts enter the retained single local-model synthesis. Titles, DOI values,
provider rank/scores, and response metadata do not enter model evidence. Reports disclose the
fallback and Crossref's language/retraction coverage limitation. The change adds no account, key,
payment, warning, approval, arming stage, action authority, Stop stage, or Windows workflow change.

### OpenAlex natural-question correction — 2 September 2026

The subsequent target-PC status check completed the OpenAlex exchange but returned HTTP 400. Its
provider message proved that the ordinary final `?` in the question was interpreted as wildcard
syntax. Core Preview 9.2.3 keeps the original question unchanged for the installed local model and
uses a separate provider query in which only ASCII `?` and `*` become spaces and whitespace is
collapsed. It deliberately retains ordinary stemmed search instead of switching a natural-language
question to literal no-stem search.

OpenAlex receives the normalized terms first; only the retained exact-503 transition can send those
same terms to Crossref. HTTP 400 now fails closed as `PAPERS_REQUEST_REJECTED`. The correction adds no
request, retry, provider loop, key, payment, wait, model generation, approval, arming delay, Stop
stage, permission, or Windows workflow change.

### Direct evidence relevance correction — 3 September 2026

The user's subsequent 9.2.3 request completed with two sources and three cited findings, accepting
the natural-question transport path. The result also exposed an evidence-selection weakness: an
earlier abstract could support an indirect chain through a third construct while the question asked
for a direct relationship between two named concepts.

Core Preview 9.2.4 validates up to three abstracts from the same provider response, computes a
bounded local score from the original question and abstract text, and supplies the strongest at most
two to the unchanged single synthesis call. Provider order breaks only exact score ties; titles,
identifiers, rank, provider scores, and other metadata remain excluded. For recognized two-concept
relationship questions, a deterministic post-check requires both literal concept groups and
relationship wording in one cited sentence and withholds recognized indirect/mediated chains.

This adds no provider request, fallback transition, retry, wait, model call, warning, approval,
arming delay, Stop stage, permission, persistence, or Windows workflow change. The check is lexical,
not semantic: it can miss synonyms or subtle constructions and does not prove causality, study
quality, or truth.

### Academic discovery precision — 7 September 2026

The 9.2.6 target-PC result produced local draft findings and safely withheld all three for missing
direct evidence. It establishes that synthesis completed in that session, not that the selected
abstracts answered the question or that unattended cold-start recovery was independently tested.

Core Preview 9.2.7 focuses unambiguous two-concept relationship questions into normalized literal
OpenAlex phrases joined by fixed AND. Qualified or ambiguous questions retain the punctuation-safe
query. It requests at most eight candidates in the same single bounded response, validates all
records, and supplies the strongest at most two to the unchanged one-model synthesis. Crossref
remains exact-503-only and receives provider-neutral terms; local ranking always uses the original
question. Citation and directness checks, runtime startup, Stop, and Windows workflows are retained.

Offline verification covers query preservation, malformed late records, eighth-candidate selection,
both provider flows, and request/model-call bounds. Target-PC relevance and cold/warm timing remain
unverified. The next gates are research-worker containment and measured runtime acceptance before
broader research, memory, or voice; see `CYPHER_NEXT_MILESTONES.md`.
### Academic evidence preflight — 7 September 2026

The 9.2.7 live result confirms focused discovery and synthesis but no accepted direct answer.
Preview 9.2.8 adds a pre-generation check over the existing selected passage catalog, reusing the
final lexical relationship predicate. When all counts are zero, it returns a partial result with
no worker Ollama API call. It distinguishes that passage gap from a draft's failed wording or
citations. Search, model prompt/budgets, evidence guards and Windows authority remain unchanged.
Offline verification: 189 focused tests, 412 full-suite passes and one Windows compiler skip.
This removes unnecessary generation in the specified case; actual speed/VRAM and discovery-quality
improvements are not claimed. See `CYPHER_NEXT_MILESTONES.md` for the still-open quality evaluation.

### Dark Workspace — 8 September 2026

The 9.2.8 target-PC screenshot verifies its observed zero-passage preflight and skipped synthesis.
It does not establish better retrieval or measured runtime savings. At the user's request, 9.2.9
updates the native UI to an opaque minimalist conversation window, retaining the exact 9.2.8 worker.
Native WPF layout self-tests run during installation before host replacement; actual UI observation
still requires Windows. Retrieval comparison remains open; see `ACADEMIC_DISCOVERY_EVALUATION.md`.

### Refined Workspace — 8 September 2026

The user requested Dribbble-informed typography and color. Preview 9.2.10 implements that native
visual refinement with a welcome screen and input-only prompt starters. The research worker stays
byte-identical to 9.2.8; retrieval quality is still the open comparison gate. Native UI execution
requires Windows. See `../RELEASE_NOTES_REFINED_WORKSPACE.md`.

## Observation Deadline Fix — 8 September 2026

The user's 9.2.10 installation passed all 189 Python research tests, then returned native self-test
126 before host replacement. That code checks a 25 ms workflow budget during a 10-second requested
observation wait; it is separate from the later WPF layout check. The screenshot does not distinguish
the assertion's missing-fault and elapsed-time branches.

9.2.11 corrects a concrete early-wake defect: observation waits keep their original monotonic
deadline, capped by the existing budget, and recheck Stop before waiting only the remainder.
The original wall-clock test is retained unchanged. Eight deterministic C# cases cover early wakes,
fixed interval, cancellation, expiry, late wake, fractional remainder and invalid intervals.
The refined UI and research worker are preserved. Target-PC installation and appearance remain
pending; this does not close the discovery-quality milestone. See
`RELEASE_NOTES_OBSERVATION_DEADLINE_FIX.md` for validation and limitations.

## 10 September 2026 — captured evidence adjudicated; 9.2.12 guard correction

The user installed 9.2.11 and supplied READY native UI evidence. The four-question comparison and
15 matching abstract captures are now available. Raw lexical counts overstated the candidate:
job-autonomy hits were an aim and an indirect proposal, phone-use outcomes did not link sleep to
memory, and an adolescent study reported a null correlation. The candidate also lost a direct
teacher social-support/stress result. Proximity is not promoted; production AND discovery stays.
9.2.12 corrects these reproduced guard defects and checks null-result wording consistency, without
claiming broad entailment or complete coverage. Native 9.2.12 installation is unverified here.
See `docs/ACADEMIC_EVIDENCE_REVIEW.md` (from the package root). Next research work must distinguish
retrieval misses, fragmentation and lexical false negatives using the existing captured evidence;
no repeat user diagnostic is needed. Containment and runtime measurements remain separate gates.
