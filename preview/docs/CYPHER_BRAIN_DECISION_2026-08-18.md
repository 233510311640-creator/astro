# Cypher brain decision — 2026-08-18

Status: initial target-PC routing decision for v0.7 development  
Hardware: AMD Radeon RX 9060 XT 16 GB, 32 GB system RAM  
Ollama: 0.32.13, loopback only  
Test context: 16,384 tokens, thinking flag off, one deterministic preflight repetition  
Source report SHA-256: `70c64f7cd81bba5632f88805a72fbbb5538a1819de3b6803b344b05e90094cf6`

## Decision

1. `qwen3.5:9b-q4_K_M` becomes Cypher's initial everyday/reflex model.
2. `gpt-oss:20b` becomes the deep-reasoning escalation model.
3. `gemma4:e4b` remains the on-demand multimodal and compact fallback model.
4. Cypher stops treating a permanent 65K context as the everyday default. The initial normal context is 16K.
5. Model selection never changes tool authority. The capability broker remains the enforcement boundary.

## Evidence

| Model | Automatic tests | Cold first event | Median warm first event | Median warm total | Generation rate on schedule | VRAM residency at 16K |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Qwen 3.5 9B Q4_K_M | 5/5 | 4.578 s | 0.530 s | 1.822 s | 43.42 tok/s | 100% |
| GPT-OSS 20B | 5/5 | 16.508 s | 0.519 s | 4.308 s | 66.06 tok/s | 100% |
| Gemma 4 E4B | 5/5 | 17.400 s | 0.412 s | 1.309 s | 50.99 tok/s | 100% |

Every model followed the exact-response rule, emitted the valid read-only tool call, respected a negated tool instruction, rejected quoted prompt injection, and produced a correct constrained schedule.

GPT-OSS generated substantially more internal reasoning even with the benchmark thinking flag off: 729 output tokens for the schedule versus Qwen's 80 and Gemma's 88. Its raw generation rate was highest, but unnecessary reasoning made completion much slower. Deep mode therefore needs visible progress, cancellation, a task threshold and no raw reasoning retention.

Gemma was the quickest warm model, but switching to it incurred a large cold load in this run. Keeping multiple models warm would compete for the 16 GB GPU. It remains valuable for image/audio testing, not ordinary text routing.

## v0.7 routing policy

- Keep Qwen warm in Ready mode and use it for ordinary conversation, planning, clarification, and routine approved tool calls.
- Escalate to GPT-OSS only for genuinely difficult reasoning, complex debugging, long multi-constraint planning, or explicit Deep mode.
- Show model switching and allow cancellation because switching can take more than 15 seconds.
- Load Gemma only for a multimodal request or if the default model fails a bounded retry.
- Never let the model select a broader capability scope, bypass approval, or silently download another model.
- Do not record raw model reasoning in Cypher logs or memory.

## Remaining validation before stable release

This was a preflight, not the complete benchmark. The compiled v0.7 host must repeat cold/warm trials, test multi-turn tool recovery, structured output, clarification, harder planning, screenshot analysis, cancellation, and 32K deep-context memory pressure before the routing policy is marked stable.
