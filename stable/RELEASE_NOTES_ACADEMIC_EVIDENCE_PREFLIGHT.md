# Core Preview 9.2.8 — academic evidence preflight

Package **v0.9.2.8** · Python package **0.9.2a9** · 7 September 2026

## Confirmed problem

The 9.2.7 screenshot shows the focused query, two selected sources from eight eligible records,
and two draft findings withheld. The duplicate image has the same retrieval timestamp and is
not an independent repeat run. Discovery and local synthesis worked in that session; the requested
autonomy/performance answer remains unmet. The image does not expose the rejected text/citations.

Publisher abstracts for the [ethical-leadership paper](https://onlinelibrary.wiley.com/doi/abs/10.1002/job.627)
and [humble-leadership paper](https://journals.sagepub.com/doi/abs/10.1177/1548051820979634) discuss
leadership, mediated effects and trust. Neither abstract supplies a direct result for the requested
pair of concepts. These publisher reads support diagnosis; they are not a byte-verified replay of
the user's OpenAlex responses or hidden model draft. No paper text is embedded in this release.

Two code problems are reproducible independently with synthetic fixtures: the worker could call
Ollama even when none of the available passages could pass its own relationship check; and the
same final diagnostic blamed the abstracts even if only model wording or selected support failed.

## Correction

- Before academic synthesis, recognized two-concept questions screen the exact bounded model
  passage catalog using the unchanged lexical relationship predicate.
- If all selected sources have zero passing passages, return `PARTIAL / PAPERS_DIRECT_PASSAGE_MISSING`.
  No worker Ollama inventory, model-details or generation request runs. No SUMMARIZING event is emitted.
- Otherwise retain the existing one-model synthesis and all citation/directness checks. No new
  model prompt, context limit, repair generation or evidence substitution is introduced.
- Report bounded per-source integer passage counts. A rejected draft's `DIRECT_EVIDENCE_MISSING`
  message now describes failed wording or selected citations without claiming the abstracts lack evidence.
- Add a native protocol self-test for discovery followed directly by a partial result.

This is passage screening, not semantic understanding. The unchanged predicate can miss synonyms,
negated mediation markers, long sentences split into fragments, and nuanced relationships; it can
also accept misleading lexical co-occurrence. Passing counts do not establish entailment, a study's
quality, causality or completeness. The release does not claim to fix academic discovery precision.

## Preserved boundaries

The delivered 9.2.7 archive is the source baseline. OpenAlex search syntax, candidate count (eight),
two-source selection, exact-503-only Crossref fallback, provider body/deadline bounds and network
transport are unchanged. Wikipedia and explicit-URL research retain their prior synthesis path.
Recognized relationship requests now use zero or one local generation; other requests retain their
prior behavior. The model prompt and 16,384-context / 2,048-output-token settings are unchanged.

Ollama autostart, Windows workflows, broker permissions, owned-worker lifetime and Stop remain.
The host's existing loopback health/start checks are retained; zero worker Ollama calls does not
mean the resident host stops checking or starting its local server.
No account, key, paid provider, query retry, pagination, new download, warning, approval, countdown,
saved research content or action authority is added. Preflight counts stay in the memory-only report.

## Verification

The focused suite runs 189 tests. The full suite runs 413 tests: 412 pass and the native Windows
compiler test is skipped on Linux. Cases cover both providers' zero-Ollama path, bad draft wording
with available evidence, wrong selected citation, passage fragmentation, invalid count metadata,
and unchanged Wikipedia/explicit-URL paths. Existing tests retain positive direct evidence through
the single model call and exact request-count/late-invalid-record guards.

Native compilation and live 9.2.8 behavior still require Windows. Tests establish that generation is
skipped in the specified case; actual elapsed-time/VRAM savings are not measured. The same-query
discovery quality remains open. No immediate user repeat-test is required for this correction.

Install when ready using `INSTALL_CYPHER_RESEARCH_PREVIEW.cmd` from a freshly extracted folder,
normally as the standard user. Confirm **CORE PREVIEW 9.2.8** and retain 9.2.7 for reinstall rollback.
The legacy manager rollback target remains 0.6.3; reinstall the retained 9.2.7 package to return to it.

See [setup and diagnostic meanings](RESEARCH_PREVIEW_SETUP.md) and
[next milestones](docs/CYPHER_NEXT_MILESTONES.md).
