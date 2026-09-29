Current bundle: **10.2.0 Bounded Office Documents**. Start with [OFFICE_DOCUMENTS_SETUP.md](OFFICE_DOCUMENTS_SETUP.md).
The component guide below is supplemental.

Current bundle: **9.5.0 File Explorer**. Start with [FILE_EXPLORER_SETUP.md](FILE_EXPLORER_SETUP.md).
The component guidance below is historical or supplemental.

Current 9.4.0 release: see RUNTIME_READINESS_SETUP.md and SECURITY_RUNTIME_READINESS.md. Previously verified file tests do not need repeating. Historical component documentation follows.

# Setup for the current desktop bundle

For **9.3.0**, use [DESKTOP_BETA_SETUP.md](DESKTOP_BETA_SETUP.md). Run the same
**INSTALL_CYPHER_RESEARCH_PREVIEW.cmd** launcher from this package. No repeated academic test is
required. The research component below remains byte-identical to 9.2.12; its limits still apply.

The remainder is the historical 9.2.12 component guide, not the current installation sequence.

---

# Cypher Academic Evidence Guard setup

Package **v0.9.2.12** · **Core Preview 9.2.12** · 10 September 2026

This release corrects academic evidence-screening defects found in the supplied review.
The installed 9.2.11 dark native interface and workflow observation fix are retained.

## Install

1. Finish any active request and keep the working 9.2.11 ZIP or folder for rollback.
2. Extract the complete **9.2.12** ZIP into a fresh folder.
3. Double-click **INSTALL_CYPHER_RESEARCH_PREVIEW.cmd** normally, not as administrator.
   Windows may hide `.cmd`, showing **INSTALL_CYPHER_RESEARCH_PREVIEW**.
4. Open with **Ctrl+Alt+Space** and confirm **CORE PREVIEW 9.2.12**.

The installer compiles and tests the native host before replacement. There is no additional
research repeat or diagnostic capture. Saved geometry/pin, prompt cards, local fonts, model
settings, startup, registered apps and action permissions retain their behavior.

## What the result means

Recognized two-concept academic questions are screened in the existing bounded passage catalog.
The corrected lexical check requires ordered concept terms and relation wording in a compatible
position. It rejects recognized aims/hypotheses, indirect-pathway and future-research wording,
as well as reproduced instrument-name and joint-outcome false positives. Final draft checking also
rejects a mismatch between recognized null-result wording in the claim and in its support.

- **PAPERS_DIRECT_PASSAGE_MISSING:** all selected sources have zero passing passages. All worker
  Ollama calls, including inventory and generation, are skipped. This does not establish that full
  papers or the wider literature lack an answer.
- **DIRECT_EVIDENCE_MISSING:** synthesis ran, but the wording or cited support failed screening.
- **COMPLETED:** provenance and wording checks passed. This does not prove scientific truth,
  semantic entailment, causal interpretation or complete preservation of scope/qualifiers.

The stricter rule can reject valid synonyms, reordered concepts, fragmented sentences and some
legitimate statements containing proposal/indirect wording. Null detection is a limited lexical
pattern check, not general negation understanding. Discovery coverage remains open.

## Retained boundaries and validation

One keyless OpenAlex request retrieves at most eight records; only exact HTTP 503 permits one
immediate keyless Crossref request. At most two abstracts enter one installed local generation.
The current exact-phrase AND query, prompt, 16,384-token context and 2,048-token output ceiling stay.
There is no new provider, key, payment, retry, model download, approval, countdown or waiting step.
Stop and Windows action approvals retain their existing rules. Research is not saved to history.

203 focused research tests and 428 full-suite passes verify source behavior; one native Windows
compiler test is skipped on Linux. Fresh-extraction hashes and encoding checks pass. Windows 9.2.12
installation remains a target-PC gate. The accepted 9.2.11 installation is the rollback baseline.
See [release notes](RELEASE_NOTES_ACADEMIC_EVIDENCE_GUARD.md) and
[evidence adjudication](docs/ACADEMIC_EVIDENCE_REVIEW.md).

## Fail-closed diagnostics

| Diagnostic | Meaning |
|---|---|
| `PAPERS_QUERY_INVALID` | The paper question is empty, exceeds 400 UTF-8 bytes, or contains only provider-reserved `?`/`*` plus whitespace; no request ran. |
| `PAPERS_REQUEST_REJECTED` | OpenAlex rejected the bounded punctuation-safe request with HTTP 400; Crossref was not used. |
| `PAPERS_CONNECT_FAILED` | TLS could not be established to a bounded validated OpenAlex address before sending. |
| `PAPERS_NETWORK_UNAVAILABLE` | The OpenAlex exchange ended after its request began; it was not retried. |
| `PAPERS_RATE_LIMITED` | OpenAlex returned rate limiting, not HTTP 503; Crossref was not used. |
| `PAPERS_ACCESS_BLOCKED` | OpenAlex or the network denied access; Crossref was not used. |
| `PAPERS_SERVICE_UNAVAILABLE` | OpenAlex returned a 5xx status other than 503; Crossref was not used. |
| `PAPERS_UNAVAILABLE` | OpenAlex returned another unsuccessful status; Crossref was not used. |
| `PAPERS_RESPONSE_INVALID` | OpenAlex response type, size, JSON, schema, record, or abstract validation failed. |
| `PAPERS_NO_RESULTS` | OpenAlex completed but had no eligible abstract. Crossref was not used. |
| `CROSSREF_CONNECT_FAILED` | OpenAlex returned 503, then TLS to Crossref could not be established. |
| `CROSSREF_NETWORK_UNAVAILABLE` | The one Crossref exchange ended after sending; neither request was retried. |
| `CROSSREF_RATE_LIMITED` | OpenAlex returned 503, then Crossref rate-limited the keyless request. |
| `CROSSREF_ACCESS_BLOCKED` | OpenAlex returned 503, then Crossref or the network denied access. |
| `CROSSREF_SERVICE_UNAVAILABLE` | OpenAlex returned 503, then Crossref returned a 5xx status. |
| `CROSSREF_UNAVAILABLE` | OpenAlex returned 503, then Crossref returned another unsuccessful status. |
| `CROSSREF_RESPONSE_INVALID` | Crossref response type, size, JSON, schema, DOI, language, or abstract validation failed. |
| `CROSSREF_NO_RESULTS` | Crossref returned no eligible journal-article abstract. |
| `MODEL_UNAVAILABLE` | Abstract evidence was prepared, but the selected installed local model did not complete its one bounded call. |
| `CITATION_CHECK_FAILED` | The draft did not cite an exact reader-assigned abstract passage. |
| `CLAIM_SCOPE_UNSUPPORTED` | Sources remain visible, but unsupported local-draft wording was withheld. |
| `PAPERS_DIRECT_PASSAGE_MISSING` | No selected bounded passage passed the lexical preflight; no worker Ollama API request ran. |
| `DIRECT_EVIDENCE_MISSING` | The model draft's wording or selected citations failed the relationship check; this does not establish that the abstracts lack evidence. |

Do not add a provider key, broaden permissions, or install another model in response to a diagnostic.
Capture the exact code instead.

## Limits

This remains abstract-only scholarly discovery, not a systematic literature review, full-text/PDF
reader, semantic reranker, study-quality ranking, causal or truth verifier, general web search, or
current-news service. Local ranking uses literal question-term coverage and a small deterministic
relationship vocabulary; it can miss synonyms and nuanced evidence. Provider coverage and metadata
can be incomplete or wrong. Citations prove which checked passage Cypher used, not that every
interpretation is true.

The worker has process lifetime and Windows job desktop restrictions, not AppContainer filesystem or
network isolation. See [SECURITY_READONLY_RESEARCH.md](SECURITY_READONLY_RESEARCH.md).
