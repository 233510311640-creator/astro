# Core Preview 9.2.4 — direct evidence relevance

Package **v0.9.2.4** · Python package **0.9.2a5** · 3 September 2026

## Why this release exists

The target-PC 9.2.3 run proved that natural-question transport, OpenAlex access, abstract
reconstruction, citations, and the installed local model all worked. It also exposed a quality gap:
the first returned abstract supported an indirect chain from job autonomy through perceived
organizational support to performance, while a later returned abstract could be more directly
relevant to the relationship the user actually asked about.

## Exact correction

Cypher still makes one OpenAlex request and receives at most three records. It now validates every
returned record in that same bounded response, then ranks eligible abstract text locally against the
original question. It supplies the strongest at most two abstracts to the existing one local-model
call. Provider order is used only to break an exact local-score tie.

For questions with an explicit two-concept relationship form, such as “the relationship between X
and Y,” Cypher derives the two literal concept term groups locally. A relationship finding is retained
only when:

- the finding itself names both concept groups and uses relationship wording; and
- at least one of its cited exact passages names both groups with relationship wording in one
  sentence.

Passages marked as indirect or mediated are not accepted as direct relationship evidence. If every
draft finding fails this check, the report remains source-visible and returns
`DIRECT_EVIDENCE_MISSING`. If a direct finding survives while an indirect extra does not, the report
keeps the direct finding and discloses the withheld count.

This is a conservative lexical check. It does not infer synonyms, prove causality, rank study
quality, or establish that a source is true. A valid paraphrase may be withheld when it does not use
the literal question terms, and subtle indirect wording can still pass if it lacks the recognized
markers.

## Request and latency boundary

The change adds no network request, provider retry, fallback path, model call, approval, warning,
arming countdown, or fixed delay:

| Stage | 9.2.4 maximum |
|---|---:|
| OpenAlex requests | 1 |
| Crossref requests | 1, only after exact OpenAlex HTTP 503 |
| Returned records validated | 3 |
| Abstracts selected locally | 2 |
| Installed-local-model synthesis calls | 1 |

The original question remains local for selection and synthesis. Only its punctuation-safe transport
copy reaches OpenAlex and, after exact HTTP 503 only, Crossref. Titles, identifiers, provider scores,
rank, citation counts, and other metadata are excluded from the local relevance score and model
evidence.

## Unchanged boundaries

- no account, API key, authorization header, billing credential, or payment;
- no wait, automatic retry, pagination, paper-page read, PDF, or full-text fetch;
- no action tools or change to Hermes, registered apps, workflow authority, or persistence;
- no change to the owned-worker Stop lifecycle or Windows desktop restriction mask;
- no extra approval or alarming/arming step; research starts immediately after Send.

## Verification

Five new regressions cover selection of a directly relevant third returned abstract without another
request, conservative same-passage relationship checks, complete withholding of an indirect chain,
retention of a direct finding while an indirect extra is withheld, and inclusion of literal
relationship concepts in the same model call.

All **172 focused research tests pass**. The complete suite discovers **395 tests**: **394 pass** and
the one native Windows compiler test is expectedly skipped in the Linux build environment. The
default-encoding warning gate, CP1252 source-read regression, bytecode compilation, worker hash, and
fresh-archive checksum checks are retained.

Use [RESEARCH_PREVIEW_SETUP.md](RESEARCH_PREVIEW_SETUP.md) for the one target-PC acceptance request.
No Stop, approval, warning, workflow, or repeated latency test is required.
