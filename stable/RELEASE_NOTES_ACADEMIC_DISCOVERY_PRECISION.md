# Core Preview 9.2.7 — academic discovery precision

Package **v0.9.2.7** · Python package **0.9.2a8** · 7 September 2026

## Starting evidence

The 9.2.6 target-PC screenshot showed two selected OpenAlex abstracts and three local-draft findings
withheld as `DIRECT_EVIDENCE_MISSING`. Local synthesis completed in that session. The sources were
related organizational-psychology material but did not yield a supported direct answer to the
relationship between job autonomy and task performance. A safe partial result is not proof of good
discovery precision. The accepted runtime/evidence baseline remains 9.2.6.

## Implemented changes

1. **Deterministic focused discovery.** An unambiguous complete two-concept relationship question
   uses two normalized literal phrases with fixed OpenAlex Boolean AND. The acceptance query becomes
   `"job autonomy" AND "task performance"`. No model, synonym generator, extra request, or term
   expansion is involved. OpenAlex documents [phrase and Boolean search](https://help.openalex.org/api/searching/).
2. **Phrase preservation.** Retrieval retains meaningful stop words, numbers, word order and
   repetitions, such as “locus of control,” “type 2 diabetes,” and “day-to-day stress.” Only
   letter/number tokens enter generated quoted syntax. Ambiguous concepts, unrecognized wording,
   extra scope, or additional questions keep the existing punctuation-safe full query. This is
   conservative parsing, not a general natural-language understanding claim.
3. **Eight candidates, still two evidence sources.** The same provider request asks for up to
   eight records instead of three. All records must validate, including late unselected records.
   The existing local abstract-only score selects at most two sources, with provider order breaking
   exact ties. Titles, identifiers, provider scores and publication metadata remain excluded.
4. **Correct original-question transfer.** An exact OpenAlex HTTP 503 still permits the one Crossref
   request. It receives provider-neutral query terms, not OpenAlex Boolean syntax. Its local
   selector now receives the original question rather than a transport-normalized copy, retaining
   the relationship signal used by the relevance scorer.
5. **Checkable in-memory disclosure.** The report shows the focused query plan and bounded count of
   eligible records left outside model evidence. Query-plan language does not falsely claim an
   invalid pre-network request ran. No query, abstract, draft, or report is saved by the worker.

## Retained limits

| Boundary | Maximum / behavior |
| --- | --- |
| Primary provider requests | One OpenAlex GET |
| Fallback | One Crossref GET, exact OpenAlex HTTP 503 only |
| Candidate records | Eight in the active provider's single response |
| Provider response body | Existing 512 KiB cap |
| Local evidence sources | Two abstracts |
| Local generation | One selected installed-model call |
| Model budget | Existing 16,384 context / 2,048 output tokens |
| Retrieval/model/host deadlines | Existing limits unchanged |
| Keys, payment, new provider, downloads | None added |
| Retry, pagination, extra approval/countdown/wait | None added |

9.2.6's pinned Ollama autostart, Windows workflow engine, capability broker, standard-user execution,
desktop restrictions, Stop lifecycle, citation/directness guard, and Wikipedia/explicit-URL routes
remain unchanged in behavior. Version and disclosure text are updated to 9.2.7.

## Verification and limits

The focused suite passes **184 tests**. The complete suite discovers **408 tests**: **407 pass** and
the native Windows compiler test is skipped on Linux. New fixtures cover both providers selecting
the eighth direct abstract, original-question preservation, exact query/request bounds, malformed
late records, too many records, impossible skip totals, ambiguous scope, safe generated syntax,
and complete discovery-to-one-model flows. Existing CP1252-default source checks remain in the suite.

Offline fixtures verify code contracts, not live search relevance or model quality. The build
environment could not probe the live API; implementation relies on official documented grammar
and strict fixtures. Native compilation, actual 9.2.7 provider/model execution, cold boot, latency,
and VRAM usage require target-PC evidence. Phrase matching can exclude synonyms or variants, and
even exact phrases may match a title or full text rather than the returned abstract. Local ranking
and the unchanged evidence guard remain necessary. There is no automatic widening on empty or
indirect-only results.

Extract into a fresh folder, run `INSTALL_CYPHER_RESEARCH_PREVIEW.cmd` normally, confirm
**CORE PREVIEW 9.2.7**, and perform the single Auto prompt in
[RESEARCH_PREVIEW_SETUP.md](RESEARCH_PREVIEW_SETUP.md). Keep **9.2.6** for reinstall rollback.
The older manager's legacy rollback target remains 0.6.3; reinstalling the retained 9.2.6 package is
the way to return specifically to 9.2.6.

Further gates are recorded in [next milestones](docs/CYPHER_NEXT_MILESTONES.md); they are plans, not
claims of implemented capabilities.
