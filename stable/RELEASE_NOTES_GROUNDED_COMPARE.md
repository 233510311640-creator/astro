# Cypher 9.9.0 — Grounded Two-Document Compare

Core Preview 9.9.0; Python distribution 0.9.9a1. 18 September 2026.

## What changed

Cypher adds an explicit comparison command for two granted UTF-8 text files:

```text
Docs: compare ROOT "first.txt" with ROOT "second.txt" : your question
```

The two files may use the same granted root or two different granted roots. Cypher reads each named
file as a separate snapshot, balances a bounded evidence set between Source A and Source B, and
makes at most one verified installed-local-model generation. A non-empty comparison must cite at
least one selected passage from each source. The generated sentences are followed by every exact
supporting passage, source label, source line, byte count, snapshot time and SHA-256 digest.

The native system rail adds **04 DOC COMPARE**. It fills the command prefix but never dispatches a
request. `Docs: answer`, `Docs: ask` and `Docs: summarize` remain available.

## Validation and failure behavior

- passage IDs are source-scoped (`A-P1`, `B-P1`) and only offered IDs are accepted;
- each source receives at most six excerpts and 2,048 evidence bytes;
- combined model evidence remains capped at 4,096 text bytes;
- duplicate command references to the same granted file reject before reading or generation;
- both grants are checked immediately before model input and again before display;
- an empty file returns a partial result without a model call;
- empty comparison arrays truthfully withhold an unsupported comparison;
- one-sided, forged, duplicate, unused or unknown citations reject;
- exact-number, conservative lexical, formatting and remote-model checks from 9.8.0 remain;
- invalid output is never retried, repaired or sent to another model.

These rules reduce unsupported output; they do not prove semantic entailment or that either source
is true. The exact passages remain the authoritative material for human review.

## Preserved boundaries

There is no folder indexing, automatic file choice, broad content search, embedding database, PDF or
Office parser, public request, model download, action tool, file change, hidden retry, conversation
history addition or durable document memory. The 9.8.0 grounded-answer route and 9.7.1 Monochrome
Signal interface remain the rollback and visual foundations.
