# Core Preview 9.0.5 — fail-closed research scope guard

Package v0.9.0.5 · Python package 0.9.0a6 · 31 August 2026

> Historical milestone. The user's target-PC result accepted the protective path with two retained
> sources, zero findings and `CLAIM_SCOPE_UNSUPPORTED`. The current candidate is 9.2.4; use
> [current setup](RESEARCH_PREVIEW_SETUP.md).

## Starting evidence

The user's 9.0.4 installation passed. Its unchanged two-source comparison first returned
`MODEL_UNAVAILABLE`, then completed with two sources and two findings on the installed Fast model.
The `RobotFileParser.can_fetch` finding was appropriately scoped. The `urlopen` finding still said it
handled the "actual network request" and presented an HTTP-specific case as general behavior. Both
excerpt previews were relevant and the earlier unrequested limitation was gone.

That result means focus ordering and prompt wording alone are not an adequate output boundary. The
complete private prompt and raw local-model response were not collected; the new regression uses the
visible wording and synthetic generic API documentation rather than claiming a replay.

## Changes

- Add a deterministic final guard for findings about a named definition in the question. It runs
  after passage IDs are resolved and revalidated but before any draft claim can be displayed.
- If a finding selects a passage marked as a distinct case, require explicit conditional wording
  such as `For`, `If`, `When`, `While`, `Whereas`, or `Under`. A case-specific passage cannot silently
  become the callable's unqualified general scope.
- Reject unsupported scope intensifiers and substantive words of seven or more characters that do
  not occur in the question or selected passages, apart from a small fixed neutral comparison and
  reporting vocabulary. This catches the observed unsupported `actual`, `network`, and `handling`
  wording without hardcoding either Python API as an answer.
- Withhold the whole draft on failure and return source metadata with
  `CLAIM_SCOPE_UNSUPPORTED`. There is no automatic retry, repair generation, partial claim salvage,
  or substitution of an unselected passage.
- Strengthen the same single model prompt to prefer direct plus general-return evidence for a
  general claim, retain explicit case conditions, and reuse source vocabulary. Set sampling
  temperature to zero for this structured local call.

There remains exactly one local `/api/chat` generation per research request. This release adds no
approval, arming pause, Stop stage, model download, search provider, Windows action, file authority,
or change to the accepted workflow implementation.

## Security and accuracy limits

The scope guard is lexical and structural, not a semantic entailment verifier. It can reject a valid
novel paraphrase, and unsupported short words or misleading source wording can still pass. It applies
only when selected passages have a validated definition context matching a named subject in the
question. Matching vocabulary does not prove that a claim is true, complete, or logically supported.
Important findings still require comparison with the linked source.

External page text remains untrusted evidence. The guard does not execute it or treat it as system
instructions; however, words present in selected evidence are eligible vocabulary. All prior source,
offset, structure, passage-ID, exact-quotation, process, network, and output bounds remain.

## Verification

- Python 3.12.13: 346 tests discovered; 345 passed and one Windows-only compiler test was skipped.
- All 123 research tests pass. Six new regressions cover the exact visible overgeneralization,
  unqualified case evidence, valid general and explicitly scoped wording, unsupported mechanism and
  intensifier terms, non-definition prose, and metadata-only fail-closed rendering.
- The full suite passes with the default text encoding forced to Windows CP1252. The research suite
  passes with default-encoding warnings treated as errors.
- Existing Windows workflow source is byte-identical to 9.0.4. Native research integration changes
  only the pinned worker hash, while the core host and installer/manager changes are version labels.
- The packaged ZIP is checked against its internal SHA-256 manifest and retested after extraction.
  Native compilation/self-tests remain required installer gates and are not replaced by Linux tests.

The real 9.0.5 target result subsequently accepted the protective path: Qwen repeated the unsupported
scope class, and Cypher retained two sources while displaying zero findings with
`CLAIM_SCOPE_UNSUPPORTED`.

## Completed target-PC check

Keep the installed 9.0.4 package for rollback. Extract 9.0.5 into a new folder, run
`INSTALL_CYPHER_RESEARCH_PREVIEW.cmd` normally, and confirm **CORE PREVIEW 9.0.5**. With Ollama
running and Auto selected, send the unchanged comparison in
[RESEARCH_PREVIEW_SETUP.md](RESEARCH_PREVIEW_SETUP.md) once.

A correct complete answer should distinguish the parsed-rules permission decision from opening a URL
or request and returning an object. Any HTTP/HTTPS-specific detail must remain explicitly conditional.
The unsupported "actual network request" wording must never be displayed. If the local draft repeats
that class of error, the acceptable protective result is **PARTIAL** with
`CLAIM_SCOPE_UNSUPPORTED`, two source records, and zero findings.

No workflow, approval, Stop-race, or model-installation retest was required. The diagnostic path above
was observed and accepted before 9.0.6 desktop-isolation work began.
