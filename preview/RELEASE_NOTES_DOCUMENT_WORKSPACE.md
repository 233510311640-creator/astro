# Cypher 10.0.0 — Bounded Document Workspace

Core Preview 10.0.0; Python distribution 0.10.0a1. 18 September 2026.

## What changed

Cypher combines three related local-document improvements:

- `Docs: search ROOT : query` scans supported text content inside one explicitly named read grant;
- ask, answer and summarize accept explicitly named UTF-8 text files up to 1 MiB instead of 32 KiB;
- compare accepts two, three or four explicitly named files and requires cited evidence from every
  supplied source for any non-empty draft.

Search is deterministic and model-free. It creates no index, embedding database, cache or durable
document memory. Results include bounded line excerpts, relative paths, line numbers, file byte
counts and SHA-256 snapshot digests.

Larger files do not broaden model context. Evidence supplied to the local model remains at most 12
passages / 4,096 passage-text bytes. A comparison divides that budget evenly between its sources;
four files receive at most three passages / 1,024 passage-text bytes each. The model still runs at
most once, with no retry, repair call or substitute.

## Search limits

- one explicitly named root with existing `read_text` permission;
- supported plain-text extensions only;
- at most 2,000 entries and 100 directories through depth six;
- at most 200 successfully read files and 4 MiB total text bytes;
- at most 1 MiB per file, 20 displayed matches and five seconds of scan time;
- exact phrase match or deterministic all-query-word line match;
- partial coverage is disclosed when any resource limit is reached.

The native system rail adds **03 DOC SEARCH** and retains document answer/compare as **04** and
**05**. These controls fill command prefixes but never dispatch them.

## Preserved boundaries

Folder search does not contact Ollama, send filenames/content to a model, or persist an index.
Generative document routes do not receive paths or filenames. File text remains untrusted and cannot
grant authority. No PDF/Office parsing, public request, upload, automatic file selection, file
modification, new permission, paid API, hidden retry or chat-history addition is introduced.
