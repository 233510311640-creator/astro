# Public source research boundary — Preview 9.2.12

## 9.2.12 correction

The shared academic lexical guard now checks ordered concept spans and relation placement,
rejects recognized aims/proposals/indirect pathways/future-work wording, and removes broad word
prefixes that admitted instrument names. A narrow null-wording consistency check applies to final
academic claims and their support. These checks are not semantic entailment or causal proof and
may increase false negatives. Full scientific scope, all forms of negation and adversarial prose
remain outside their guarantee. Retrieval, passage limits, prompts and model budgets are unchanged.
The worker version and pinned host hash are synchronized; no permission boundary is widened.

## Request authority and trust boundary

Only an explicit `Research:` or `Research papers:` command in the native input box enters this
route. `Research:` with no URL lines selects bounded English Wikipedia discovery; adding URL lines
selects the retained explicit-source route. `Research papers:` accepts only a bounded question and
selects bounded abstract-only academic discovery. OpenAlex is primary; Crossref is permitted only as
a one-request fallback after an exact OpenAlex HTTP 503. All supplied URLs are parsed before the worker constructs a
reader. Research is not a Hermes/MCP tool. It cannot
prepare or approve a workflow, execute model-generated code, invoke app/file tools, or add page
content to the action-capable chat history. A new research request has no earlier conversation or
research context. A user can manually copy text out; that is separate from automatic forwarding.

The standard-library Python worker is launched through a fixed executable path and a pinned script
hash, with `-I -S -B -X utf8`. The question is a JSON stdin payload, never command-line text. Shell
execution is disabled; inherited environment variables are cleared except Windows system paths.
No credentials, browser profile or proxy settings are passed to the worker.

The worker also receives fail-closed Windows job-level desktop isolation. Before process start, the
host sets and reads back restrictions covering clipboard reads/writes, USER handles and hooks owned
outside the job, desktop creation/switching, display and system-parameter changes, Windows exit calls,
and global atoms. Failure or a weakened returned mask prevents the worker from starting.

This is **process and desktop-surface isolation, not AppContainer**. The worker still runs under the
current user's token. Its filesystem, registry and outbound network access are not newly constrained
by an OS sandbox. A Python/runtime exploit or same-user code tampering is outside this preview's
containment guarantee. The model has no tool interface, and page text is never evaluated as code. A
hash check detects worker drift; it is not a signed release or protection against an attacker who can
replace the host itself. AppContainer/LPAC or another stable filesystem/network boundary remains
future hardening.

## Network reads

- Academic discovery makes one keyless GET to fixed `https://api.openalex.org/works`.
  The original cleaned question remains bounded to 400 UTF-8 bytes and unchanged for local
  selection/synthesis. An unambiguous complete two-concept relationship form uses two quoted
  normalized literal phrases joined by a fixed Boolean AND. Retrieval phrases preserve meaningful
  words, numbers, order and repetitions; only letter/number tokens can enter generated syntax.
  Unknown forms, compound concepts, or appended scope retain the existing full punctuation-safe
  query (ASCII `?`/`*` become spaces). No synonym expansion or model-written query occurs.
- Provider-derived query text is capped at 512 UTF-8 bytes and the existing 2,048-character
  canonical-URL cap still applies. The OpenAlex request retains the fixed English/non-retracted/
  has-abstract filters and exact selected fields. Its record ceiling is eight and its response
  body remains capped at 512 KiB. This increases the candidate pool, not network/model request
  counts, response-byte limits, or deadlines.
- Only an exact OpenAlex HTTP 503 permits one immediate keyless GET to fixed
  `https://api.crossref.org/works`. Crossref receives the same provider-neutral terms without
  OpenAlex Boolean syntax, a has-abstract/journal-article filter, eight-record ceiling, and selected
  DOI/title/abstract/type/language fields. Both local selectors retain the original question.
  No other status, invalid response, empty result, connection failure, or interrupted exchange
  permits fallback. Neither request is retried, paginated, or delayed. No credential, payment,
  PDF/full-text read, or record-page request is used.
- Every returned OpenAlex record is validated before local synthesis, including records that
  would not be selected. Valid records have canonical public work IDs, English language,
  bounded metadata, and strict contiguous unique abstract positions. Retracted and too-short
  records are ineligible. Malformed records reject the response; they are not silently ignored.
- Every returned Crossref record is likewise validated for DOI, type, title, language/score
  types and bounded deposited abstract markup. Explicitly non-English records are skipped;
  a conservative English-text check also applies. Active/script-like markup content is discarded.
  The worker derives canonical DOI links locally. Crossref does not independently guarantee
  retraction status, which remains disclosed in the report.
- Up to eight unique eligible abstracts are ranked using abstract text and the original question
  only; the strongest at most two become model evidence. Provider order breaks exact score ties.
  Titles, identifiers, scores, citation counts and publication metadata are not local-selection
  input or model evidence. Source labels/provenance remain visible only in the final report.
  In-memory skipped counts cannot exceed the eight-record total.

- Question-only discovery makes exactly one GET to the fixed
  `https://en.wikipedia.org/w/api.php` MediaWiki Action API endpoint. The request contains fixed
  read-only query parameters and the cleaned typed question, bounded to 400 UTF-8 bytes. It requests
  three namespace-0 results in explicit provider relevance order and only validated title/page-ID
  fields are accepted. The JSON body is
  bounded to 64 KiB. Snippets, result URLs, suggestions, scores and other metadata are ignored and
  never become model evidence. Candidate article URLs are constructed locally on the fixed
  `en.wikipedia.org` host.
- Up to three discovered candidates are attempted in that returned order only until two usable
  sources exist. A failed or duplicate earlier candidate permits the next candidate to be tried; no
  lower-ranked candidate is fetched after the target is met. This is a local stopping rule, not an
  added provider request, retry or relevance judgment. Explicitly supplied URLs retain their separate
  one-to-five-source behavior and are all attempted.
- Wikipedia discovery has no API key, browser cookie, account, paid provider, HTML search-page scraping,
  pagination, retry or alternate-provider fallback. A non-200 response, network failure, empty set,
  unexpected content type, malformed JSON, more than three results, non-article namespace, invalid
  page ID or unsafe title fails closed. An explicit-source request makes no discovery call.
- One to five explicit HTTPS source URLs, port 443 only; no userinfo, IP literals, local suffixes,
  obvious credential/token query keys, control characters or ambiguous backslash syntax.
- Every returned IPv4 DNS address must pass the public-address policy. IPv6-only sources are
  rejected. Up to four validated addresses may be tried during the pre-request TCP/TLS connection
  phase within one bounded connection window; TLS always validates the original hostname and no second DNS lookup occurs. Certificate
  rejection stops immediately. Once an HTTP request begins, it is never retried.
- Only GET requests, a fixed user agent, bounded headers/body handling, validated TLS and no cookies,
  Authorization, browser sessions or environment proxies. A public URL can still expose private
  information through an opaque token not recognized by the filter; the user must supply public URLs.
- Robots policy is checked per origin. Longest rule, Allow ties, wildcard/anchor matches, applicable
  user-agent groups and declared pacing are considered. Unavailable or oversized policy blocks
  page access. Only a missing policy response (404/410) permits the default unrestricted read.
  Redirects repeat URL/address checks and, for page redirects, destination robots checks.
- At most four request hops per page/policy chain, 30 total requests, a 1 MiB retained body prefix per
  page (plus at most one byte when the response length is not announced and overflow must be detected),
  128 KiB robots response, and a 45-second retrieval budget. Socket timeouts and host lifetime
  bounds also apply; OS DNS resolution may outlast the retrieval budget until the host stops it.
- No retry, CAPTCHA bypass, challenge workaround, PDF parser, JavaScript or authenticated browsing.
  Only uncompressed HTML/XHTML/plain text is accepted. Scripts, forms, navigation and common hidden
  content are stripped; passage catalogs derive from at most 8,000 extracted characters per source.
  A readable page larger than 1 MiB uses only that prefix as evidence and discloses that the remainder
  was not read. Truncated discovery JSON is invalid, and a truncated robots response blocks page access.
  HTML nesting is bounded at 128, captured visible HTML text at 100,000 characters and structural
  records at 2,048. A short final tail may repeat preceding context within the same block. CSS visibility
  and rendered-browser semantics are not fully reproduced. Truncation is disclosed.

An HTTP GET is treated as a read, but a remote server can implement side effects incorrectly.
This reader cannot prove the server's internal behavior. Websites receive the client's IP and URL;
DNS providers see queried hostnames. For question-only Wikipedia discovery, Wikimedia receives the
exact cleaned typed question. For `Research papers:`, OpenAlex receives the focused literal-phrase
query or punctuation-safe copy described above. Only after OpenAlex returns HTTP 503 does Crossref
receive the provider-neutral terms without generated OpenAlex Boolean syntax. Cypher keeps the
original academic question local for selection and synthesis. Each
contacted provider receives ordinary request metadata and a Cypher name/version user agent. No chat
history, local file, durable memory, application state, prior research, model prompt, generated
answer, API key, authorization header, or billing credential is sent. The explicit-source route does
not disclose its question to a discovery provider.
If a user includes information inside a question or URL, that information is part of the applicable
external request.

## Local model and citations

The worker talks only to `http://127.0.0.1:11434` for Ollama. `/api/tags` and `/api/show` must identify
the selected installed GGUF model, with no cloud naming or remote-model alias. There is no pull,
model fallback or paid inference path. The existing trusted local Ollama service is part of this
boundary; its settings and implementation are not an adversarial attestation target.

`/api/chat` receives the fixed research instructions and one JSON evidence payload, a constrained
output schema, no tools, no prior history, bounded context/output and a separate model time budget.
External source text remains untrusted data. A prompt cannot grant an absent capability. Prompt
injection can still influence the wording or cause bad analysis; instructions alone do not prevent
that, and this release does not claim semantic resistance to every injection. For the academic route,
the evidence payload labels sources generically (for example `Scholarly abstract S1`) so the provider
title, identifier, rank, relevance score, and publication metadata cannot influence synthesis.
For a recognized two-concept relationship form, that same payload also contains two arrays of
literal lowercase question terms. They are derived deterministically from the local question and do
not add provider data, a second prompt, or another `/api/chat` call.

The reader creates at most 48 passages per source, each an exact 12–240 character slice with
reader-assigned ID, source identity and offsets. The model receives these passages and selects
IDs; it cannot supply quotation text. Its output schema is also included in the system prompt,
and its reference enum contains only the current catalog IDs. The worker independently rejects
unknown or duplicate IDs, old quote objects, extra fields and duplicate JSON keys. It checks each
selected passage against its source identity, offsets and actual fetched text before resolving it.
The retained exact-quotation rules then check the resolved findings. Invented IDs,
cross-assigned passages, model-supplied URLs, tool fields and malformed drafts remain rejected. The
renderer supplies the actual final source URL, title, UTC retrieval timestamp and a SHA-256. For page
routes the hash covers fetched bytes, including only the disclosed retained prefix for an oversized
page. For OpenAlex it covers the validated reconstructed abstract; for Crossref it covers the
validated normalized deposited abstract. The timestamp is not a publication date and the hash is
not independent verification of a publisher, OpenAlex, or Crossref.

The HTML reader retains paragraph/definition/code boundaries and nearby visible headings or
definition terms. Their labels are exact substrings from earlier retained source text, bounded to
160 characters. The model receives deduplicated context labels as untrusted JSON data, not system
instructions. A heading/signature/source-path record is not independently selectable evidence;
context IDs cannot be cited. Code examples are selectable and labeled separately from prose.
Block offsets, text, kind and context are validated before model calls. Resolved passage metadata
must match the reader's catalog; no model-supplied label can rebind its source or authority.

For identifier names present in the question, the reader may group passages sharing a validated
definition context and reorder that source's same bounded passage records. Generic lexical cues mark
a likely direct description, return/result wording and conditional/case wording. At most eight focus
groups and three recommended IDs per group are emitted. Group/context IDs and facet labels are
navigation metadata only: the output schema accepts only real passage IDs, and every selected passage
still receives the full source/offset/structure/exact-text validation. A cue may be wrong and the model
is told to replace it when its passage does not support the claim. This is evidence placement, not a
truth database, API-specific rule or semantic authority.

After selected passage IDs receive those provenance checks, a final deterministic guard applies only
to findings whose selected passages have a validated definition context matching a named subject in
the question. A selected `case_scope` passage requires an explicit condition marker in the finding.
Unsupported scope intensifiers and substantive words of seven or more characters must occur in the
question or selected evidence, apart from a fixed neutral comparison/reporting vocabulary. Failure
withholds the entire draft and reports `CLAIM_SCOPE_UNSUPPORTED`; it does not retry, repair, salvage
other findings, or select different evidence. The model prompt uses the same rule and temperature
zero, but there is still one `/api/chat` call.

This is a lexical/structural guard, not semantic verification. It may reject a valid novel paraphrase;
unsupported shorter wording or misleading evidence can pass. Source vocabulary remains untrusted and
matching it does not establish truth, relevance, completeness, or entailment. The guard adds no tool
or execution authority and does not make the worker an OS sandbox.

For a recognized two-concept relationship question on the academic route, a second narrow post-check
applies after the ordinary citation and claim-scope validation. The finding text must contain every
literal term in both extracted concept groups plus recognized relationship wording. At least one of
its already-selected exact support passages must meet the same requirement within one sentence.
Passages containing recognized indirect or mediated markers are not accepted as direct relationship
support. Failing findings are individually withheld. If none remain, checked sources are retained and
the report uses `DIRECT_EVIDENCE_MISSING`; no model repair or retry occurs. This indicates rejected
draft wording or selected support, not a determination that the entire abstract lacks evidence.

Preview 9.2.8 first applies that same lexical predicate to the selected sources' actual bounded
passage catalog (at most 48 passages per source). For a recognized two-concept academic question,
zero passing passages bypass all worker Ollama API calls and return `PAPERS_DIRECT_PASSAGE_MISSING`.
Per-source integer counts appear only in the in-memory text report. Nonrelationship questions and
Wikipedia/explicit-URL routes keep the existing synthesis path. Preflight does not grant trust,
relax citations, assert scientific entailment, expand the candidate pool, or perform another request.

This directness check is deliberately conservative and lexical. It does not infer synonyms, resolve
coreference, distinguish correlation from causation, evaluate study design, or prove entailment. It
can reject sound evidence with different wording, and an unrecognized indirect construction can pass.
The source-ranking score and finding guard run only over already-returned abstract text and already-
selected passages; neither adds a network request, provider fallback, model call, warning, approval,
arming step, or delay.

Passages stay within one block, prefer complete sentence boundaries and mark cut fragments.
If more than 48 candidates exist, deterministic structural/lexical relevance chooses a subset and
restores document order. That omission is disclosed as bounded text; no second fetch or model call
is triggered. The model is instructed to preserve conditions, exceptions, return types and protocol
scope, compare different case-scope passages, and qualify missing information as absent from the read
excerpts. These are instructions, not an entailment checker or a guarantee against unsupported
generalizations.

Quotation output is limited to 25 words per source; finding summaries to 140 words per source.
Matching citations establish provenance, **not truth, relevance or logical entailment**. Disagreeing
or misleading sources may still produce a poor interpretation. Inspect important claims against
the originals. For a direct question, model-noted limitations are displayed only when the question
explicitly asks for limitations, caveats, risks, errors, uncertainty or a related facet. The complete
returned limitations list is validated first: malformed or unsafe output still rejects the draft;
otherwise a valid unrequested tangent is omitted. The default no-question summary still requests
limitations. This is deterministic output scoping, not a judgment that a hidden limitation is false.
A failed model/citation check returns source metadata without the rejected claims; failed pages never
become model evidence.

The complete draft is validated before duplicate removal or summary-word budgeting. Only identical
cleaned, case-sensitive finding text and the same source/quote evidence may collapse. Different
numbers, negation, conditions, case, evidence and paraphrases are not treated as equivalent by the
deterministic filter. Repeated/empty limitation strings are omitted. Model instructions ask for
distinct facts and material limitations, but this does not guarantee semantic deduplication.

Each cited source has one preview labeled with its finding number. Sentence-prefix candidates are
ranked by structural context and lexical overlap with that finding and the question, solely inside
already-selected exact passages. Explanatory definitions can outrank keyword-rich introductory text;
recognized signature blocks rank below selected explanations. Ambiguous contexts for identical quote text do
not receive a guessed label. No unselected passage is substituted, text rewritten, source attribution merged or extra
model call made. Long sentences retain their prefix, not a middle keyword window; basic abbreviation
handling reduces false boundaries. Ellipses indicate omitted context. This is a display heuristic,
not semantic verification or a full sentence parser; a catalog slice may itself be a fragment.
At most 25 words per source are quoted, so previews cannot display every supporting detail.

## Process lifetime, Stop and data retention

The host configures a Windows job before starting its Python process. It requires kill-on-close, a
one-process limit, a 512 MiB process-memory limit and the complete desktop restriction mask described
above. `QueryInformationJobObject` must return that exact mask before `Process.Start`; the process is
then assigned to the same job before request JSON is written to stdin. The host enforces a 180-second
worker deadline and bounded stdout/stderr/frame counts. No arbitrary process ID or registered-app
termination is exposed. Stop closes this owned job/process; an in-flight Ollama generation may take
time to stop on the separate server after the client connection disappears.

The UI accepts only a bounded protocol and matching request nonce, waits for confirmed worker exit,
and refuses new requests if exit is unconfirmed. It never treats a stopped reader as a completed
report. Stream disposal waits for the runner to unwind. There is no added warning, arming delay, or
research approval card. Send starts research immediately, and Stop is enabled only while the owned worker is
active. Existing consequential Windows actions retain their full one-time approval.

Fetched bodies, question, model response and report are held in process memory only by this code.
No report, page cache, prompt, quote or research checkpoint is written by the worker or host.
The previous Windows workflow checkpoint is left unchanged. **Copy Last Response** is an explicit
user clipboard action, not automatic research clipboard access. OS paging/crash dumps and the local
Ollama server's own logging/retention are separate and are not covered by this no-content-write claim.

## Verification limits

Offline Python tests cover policy, pinning, robots, extraction, adversarial citation shapes, local
model metadata, partial results and real invalid-input subprocess behavior. Host source assertions
are not native execution tests. Installation compiles the full host, runs the retained workflow
harness and protocol self-tests, then sets/reads back the complete job restriction mask and starts an
owned worker with an invalid local URL before checking pre-start cancellation. These native checks
have not run in the Linux build environment and make no public page/model call. All 189 focused
research tests pass. The complete suite discovers 413 tests: 412 pass and the one native Windows
compiler test is expectedly skipped on Linux. Coverage includes the
exact 503 transition, non-503 refusal, two-request ceiling, Crossref normalization and schema
rejection, transport-only wildcard neutralization, preservation of the original local question,
local selection of a direct third returned abstract, metadata exclusion from relevance scoring,
same-sentence two-concept directness, indirect-chain withholding, provider disclosure,
EncodingWarning-as-error, bytecode compilation,
and the retained CP1252-default source-reader subprocess check.
The user's 9.0.5
result accepted the scope guard by withholding the unsupported draft as `CLAIM_SCOPE_UNSUPPORTED`
while retaining two sources and zero findings, and successful 9.0.6 installation accepted the native
desktop-isolation gate. The user's 9.1.0 question-only target-PC result accepted the live provider
route with two read sources and four cited findings; its third discovered candidate was discarded as
`CONTENT_LIMIT`, motivating Preview 9.1.1's bounded-prefix and two-usable-source rules. The user then
accepted 9.1.1's live two-usable-source behavior, making it the rollback baseline. The user's 9.2.0
target-PC request reached the academic route but ended as `PAPERS_UNAVAILABLE`; Preview 9.2.1 added
bounded pre-request address failover and status-specific diagnostics. The resulting target-PC status
check proved a complete TLS/HTTP exchange and an exact OpenAlex HTTP 503 under provider load.
Preview 9.2.2 added only the disclosed one-request Crossref fallback for that status. Its subsequent
target-PC request proved that the ordinary final question mark was being interpreted as an OpenAlex
wildcard and rejected with HTTP 400. Preview 9.2.3 neutralizes only ASCII `?` and `*` in the provider
transport copy, retains the original question locally, and gives HTTP 400 its own fail-closed
`PAPERS_REQUEST_REJECTED` diagnostic. The exact-503 transition remains unchanged. The user's
subsequent 9.2.3 run completed with two sources and three cited findings, accepting the transport fix
while exposing an indirect relationship chain. Preview 9.2.4 ranks up to three already-returned
abstracts locally, selects the strongest two, and applies the narrow direct-evidence guard described
above without changing the request or model-call ceilings. Broader Windows Stop/exit, rollback and repeated-run latency/VRAM
acceptance remain separate. A completed protocol result does not establish
semantic completeness or correctness.

The 9.2.6 target-PC run completed local synthesis and withheld three indirect findings with
`DIRECT_EVIDENCE_MISSING`. It establishes working local synthesis for that session, not an
independent cold-boot or source-quality result. 9.2.7 adds conservative literal-phrase discovery,
an eight-record pool in one response, original-question ranking on Crossref, truthful query-plan
disclosure, and tests for late invalid records, eighth-record selection, exact request counts,
phrase preservation, ambiguous-scope fallback, and one-model-call end-to-end fixtures.
Live provider probing from the build environment was unavailable; official documented grammar
and adversarial offline fixtures informed that release. The subsequent 9.2.7 screenshot confirms
the focused query, two selected sources and two withheld drafts; discovery quality remains unmet.
The two repeated images show the same retrieval timestamp, not independent test runs. They do not
reveal rejected draft text or prove the specific rejection reason. Publisher abstracts were checked
separately during diagnosis; they were not substituted for the runtime's hashed OpenAlex evidence.
Preview 9.2.8 adds synthetic regression fixtures for zero-call passage failure on both providers,
available evidence with rejected draft wording/citations, fragment limits and unchanged other routes.
The 9.2.8 target-PC screenshot confirms zero passage counts and skipped synthesis in that run.
Actual latency, VRAM use, cold-boot behavior and discovery quality remain unverified. Preview 9.2.9
changes only the native workspace UI and its local layout preferences; the research worker bytes
and authority boundary remain unchanged.

## Primary implementation references

- [Ollama structured outputs](https://docs.ollama.com/capabilities/structured-outputs)
- [Ollama chat API](https://docs.ollama.com/api/chat)
- [Ollama installed models API](https://docs.ollama.com/api/tags)
- [Python HTTP client](https://docs.python.org/3.12/library/http.client.html)
- [Robots Exclusion Protocol, RFC 9309](https://www.rfc-editor.org/rfc/rfc9309.html)
- [MediaWiki Action API search](https://www.mediawiki.org/wiki/API:Search)
- [Wikimedia API usage guidelines](https://foundation.wikimedia.org/wiki/Policy:Wikimedia_Foundation_API_Usage_Guidelines)
- [Wikimedia User-Agent policy](https://foundation.wikimedia.org/wiki/Policy:Wikimedia_Foundation_User-Agent_Policy)
- [OpenAlex API overview](https://help.openalex.org/api/)
- [OpenAlex search](https://help.openalex.org/api/searching/)
- [OpenAlex selected fields](https://help.openalex.org/api/selecting-fields/)
- [OpenAlex Work attributes](https://help.openalex.org/data/works/attributes/)
- [OpenAlex API errors](https://help.openalex.org/api/errors/)
- [Crossref REST API](https://www.crossref.org/documentation/retrieve-metadata/rest-api/)
- [Crossref REST API filters](https://www.crossref.org/documentation/retrieve-metadata/rest-api/rest-api-filters/)
- [Microsoft Windows job objects](https://learn.microsoft.com/en-us/windows/win32/procthread/job-objects)
- [Microsoft job-object UI restrictions](https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-jobobject_basic_ui_restrictions)
- [Microsoft SetInformationJobObject](https://learn.microsoft.com/en-us/windows/win32/api/jobapi2/nf-jobapi2-setinformationjobobject)

The constrained subset above is the implemented contract, not a claim of complete browser or
robots-protocol compliance.
