# Bounded Document Workspace security boundary — 10.0.0

## Model-free content search

`Docs: search` names one existing read grant and one query. The deterministic worker traverses only
that root through the same path/reparse protections as other file views. It reloads the grant before
directories and reads, verifies every file snapshot through the existing bounded reader, and checks
the grant again before display. Revocation rejects the whole result.

Only supported UTF-8 text extensions are considered. Binary, invalid, changed, linked, protected,
oversized or unavailable entries cannot become results. Entry, directory, depth, file, byte, time and
result limits prevent an unbounded scan. Reaching a limit produces an explicit partial result.

Search text never reaches Ollama, Hermes chat, a public service, an embedding system or a saved
index. Relative paths and exact bounded excerpts appear only in the current native view. Source text
is displayed as data and cannot initiate an action.

## Larger explicit documents

The shared file-browser command remains capped at 32 KiB. Only explicit Docs routes may request the
extended 1 MiB reader ceiling. The verified reader preserves extension, regular-file identity,
reparse, size, timestamp, UTF-8, NUL-byte, Stop and grant checks. A document yielding more than
20,000 nonblank line segments rejects before model access.

The model evidence limit does not increase: at most 4,096 passage-text bytes reach loopback Ollama.
Paths, filenames, unselected text, other files, history, credentials and action state are excluded.

## Multi-document comparison

Compare accepts two to four explicit root/path pairs. Canonically identical resolved paths reject,
including normalized aliases. Every source gets a distinct `A` through `D` namespace and a fair
share of the fixed evidence budget. A non-empty result must select/reference all source labels;
selected IDs, sentences, exact numbers, wording overlap and output shape retain the 9.9.0 checks.

These controls do not prove entailment, completeness or source truth. Exact passages remain visible
for human review. The worker has no action engine or public-research engine, makes no hidden retry,
and runs within the signed-in user account rather than a hardened OS sandbox.
