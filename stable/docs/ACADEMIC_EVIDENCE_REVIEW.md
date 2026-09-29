# Academic evidence review — 10 September 2026

Decision: **do not promote the proximity query**. Keep the existing production AND query and
correct reproduced lexical-screening defects in 9.2.12. The original job-autonomy question remains
an unmet discovery-quality goal. A partial result is not a successful answer.

## Evidence and verification

The user supplied `CYPHER_RELEVANCE_REPORT_a531a8f7c09e.json` and
`CYPHER_EVIDENCE_REVIEW_c56f3a4100df.json`. The second capture reports one HTTP-200 request,
zero model requests, 15 matching abstracts and no missing requested work IDs. The evidence capture
was created on 9 September 2026; no live retrieval was repeated during this review.

- Relevance report SHA-256: `b57f88b1e06f23b8712435ffb1f4c00be4bf106fda63b2da4f25a1a24b83ecf8`.
- Evidence capture SHA-256: `b422b809228e43dd859f3aaa28f0f78492977fc62e458c47c7367b79545919bb`.
- All 15 abstract hashes match both their captured hash and the previous expected hash.
- All 120 catalog passages across 16 source uses reproduce the baseline worker's text, offsets,
  IDs, fragment flags and lexical flags. One source occurs in both query variants.
- The table below applies the corrected predicate to those **same previously selected passages**.
  It is not a new provider run, re-ranking of the complete eight-record candidate sets, model
  evaluation, precision/recall estimate or scientific validation. The full candidate sets were
  not captured in these files.

| Question concepts | Current AND, old → corrected count | Candidate proximity, old → corrected count |
|---|---:|---:|
| Job autonomy / task performance | 0 → 0 | 2 → 0 |
| Sleep duration / working memory | 1 → 1 | 4 → 1 |
| Social support / job stress | 5 → 3 | 5 → 1 |
| Job insecurity / burnout | 2 → 1 | 5 → 2 |

Counts screen wording only. Several passages can restate the same study finding; counts are not
independent studies or effect estimates. Fewer counts alone do not establish better quality.
The manual adjudication below explains the defects rather than treating either regex as ground truth.

## Manual adjudication of captured abstracts

These are paraphrased reviews of the user-supplied bounded abstracts, not independently verified
full-paper conclusions. Links identify public works; titles and metadata were not evidence.
No complete abstract or user capture is redistributed in this package.

| Work / DOI | Query use | Evidence interpretation and retained limits |
|---|---|---|
| [Ethical leadership and job characteristics](https://doi.org/10.1002/job.627) | AND: autonomy/performance | Purpose and mediated leadership/effort pathway do not establish the requested direct pair. The passage-loss flag was not evidence of a missed direct finding. |
| [Humble leadership, trust and autonomy](https://doi.org/10.1177/1548051820979634) | AND: autonomy/performance | Trust mediation and autonomy moderation; no direct pair finding in the captured passages. |
| [Autonomy and innovative work behaviour](https://doi.org/10.1111/caim.70014) | Proximity: autonomy/performance | The passing sentence described the research aim. Reported findings concern mediation through innovative behaviour and moderation; do not present the aim as a result. |
| [Autonomy as a double-edged sword](https://doi.org/10.1111/joop.70087) | Proximity: autonomy/performance | The passing sentence proposed an indirect pathway through problem-solving pondering. It is not direct passage support for the requested pair. |
| [Sleep duration and cognition in older adults](https://doi.org/10.1016/j.sleep.2015.08.021) | AND: sleep/memory | Contains an association between extreme sleep duration and poorer working memory in the cross-sectional studies. Retain older-adult and study-design scope; not causal evidence. |
| [Manipulated sleep duration in children](https://doi.org/10.1093/jpepsy/jst033) | AND: sleep/memory | The abstract reports a working-memory difference between short- and long-sleep conditions. Literal concept wording is missing from the same bounded passage. A known conservative false negative, not repaired in this release. |
| [Sleep duration and adolescent working memory](https://doi.org/10.4103/jfmpc.jfmpc_600_20) | Proximity: sleep/memory | The hypothesis is not a finding. The conclusion reports no significant sleep-duration/working-memory correlation. Preserve the null result; it cannot support a positive association. |
| [Bedtime phone restriction pilot](https://doi.org/10.1371/journal.pone.0228756) | Proximity: sleep/memory | Sleep and memory improved as outcomes of a phone-use intervention. This does not by itself link the two outcomes to one another. Both reproduced false positives are rejected. |
| [Support and stress among hospital nurses](https://doi.org/10.1111/j.1547-5069.2004.04016.x) | Both: support/stress | Retain the coworkers-support/reported-stress finding with observational scope. Reject the aim and future-research conclusion as direct findings. |
| [Coping and job stress in teachers](https://doi.org/10.1348/000709999157879) | AND: support/stress | Contains an association between low support and high stress, with regression covariates. One passing fragment truncates the covariate list; retain full-study context and avoid causal claims. Candidate selection loses this source. |
| [Clinicians' support, stress and intent to leave](https://doi.org/10.3390/healthcare10020229) | Proximity: support/stress | A comparison aim and a list of contributors to intent to leave do not establish the requested support/stress pair. |
| [Burnout in nursing review](https://doi.org/10.1186/s12960-020-00469-9) | AND: insecurity/burnout | A long sentence lists job insecurity among reviewed predictors of burnout, mostly from cross-sectional studies. Fragmentation loses the same-passage pair. Known evidence loss requiring separate work. |
| [Job insecurity and married couples](https://doi.org/10.1002/job.91) | AND: insecurity/burnout | Contains an association. The direct pattern differs between husbands and wives; those qualifications matter. The corrected screen retains one passage and conservatively rejects a sentence containing mediation wording. |
| [Insecurity, burnout and affectivity](https://doi.org/10.4102/sajip.v31i4.199) | Proximity: insecurity/burnout | Reject the objective and instrument list: an instrument name previously matched the broad affect-prefix regex. Retain the reported relationship with affectivity qualifications and cross-sectional limits. |
| [Insecurity and organisational commitment](https://doi.org/10.4102/sajip.v31i4.210) | Proximity: insecurity/burnout | Reject the objective. Retain the association with increased burnout, without claiming causality from a cross-sectional study. |

## Correction and limits

The shared paper guard now locates concept terms in order, allows intervening stop words, and
checks where relation wording occurs. Recognized aims, hypotheses, proposals, future-work and
indirect-pathway wording cannot satisfy it. Relation words no longer match arbitrary prefixes or
bare affect/level adjectives. These changes remove the reproduced instrument and joint-outcome
cases. A narrow final check withholds claims whose recognized null wording disagrees with support.
Source ranking, preflight and final support checks all use the corrected relation predicate.

This is conservative lexical screening, **not general semantic entailment**. It can reject valid
synonyms, reversed term order, intervening explanatory terms, long fragments and legitimate
statements containing indirect wording. It does not prove causal interpretation, positive/negative
effect direction, full population scope, all forms of negation, or every possible third-variable
construction. Model instructions still require faithful scope and qualifications, but instructions
and provenance checks do not guarantee scientific interpretation. One null-pattern check does not
constitute a semantic verifier.

The proximity candidate does not meet promotion criteria: it does not solve the target question
and loses useful support/stress evidence. The initial comparison was one fixed-order run, with
request totals of 5,734 ms for AND and 6,438 ms for proximity. These timings do not establish a
repeatable speed difference. Do not tune the candidate or claim precision gains from this small set.

Next work can use the existing captures to study fragmentation and literal mismatch before another
retrieval change. Full candidate re-ranking, scientific adjudication beyond these abstracts,
model answer quality, latency/VRAM and OS containment remain open gates. No further user diagnostic
capture is needed for this correction.
