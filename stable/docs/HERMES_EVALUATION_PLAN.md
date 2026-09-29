# Hermes Foundation Evaluation

Status: Phase H0 — no Hermes installation, account connection, or system mutation authorized  
Date: 15 August 2026

## Decision under evaluation

Hermes Agent is a candidate orchestration layer for the Local Windows Assistant. It may replace work we would otherwise build for conversation management, skills, memory, goals, missions, background jobs, browser integration, voice, and the desktop interface.

Hermes will not replace the project's deterministic permission broker. The existing local project remains the proposed boundary for Windows file operations, approvals, audit records, undo, network policy, and emergency stop.

Target architecture:

```text
Hermes Desktop or CLI
        -> local Ollama model
        -> hardened capability broker
        -> approved Windows, file, browser, and connector tools
```

## Why evaluation comes before adoption

Hermes substantially overlaps the planned v0.2-v0.7 roadmap, but its general-purpose terminal, code-execution, file-write, plugin, browser, and background capabilities create a wider security surface than the current prototype. Local Ollama support also requires compatibility and context-length testing on the target 16 GB GPU.

No conclusion is assumed. The outcome may be:

1. use upstream Hermes with a hardened configuration;
2. maintain a small, pinned Hermes fork plus the local capability broker;
3. reuse selected Hermes components and keep our orchestrator; or
4. reject Hermes if local-model reliability or isolation is inadequate.

## Phase H0 rules

- Do not paste API keys, passwords, recovery keys, cookies, or tokens into Hermes or the audit output.
- Do not connect Gmail, Google Drive, Calendar, Slack, messaging, Zapier, n8n, ElevenLabs, Buffer, or any MCP server.
- Do not install community skills or plugins.
- Do not expose Ollama on `0.0.0.0`, the LAN, or the internet.
- Do not enable YOLO/off approval mode.
- Do not enable cron/background tasks.
- Do not authorize terminal, code execution, arbitrary file writes, or the user's normal browser profile.
- Do not use the user's real Hermes profile for adversarial testing.

## Stage 1 — Read-only inventory

Run `scripts/audit_hermes_windows.ps1`. It performs only these checks:

- Windows and PowerShell version;
- whether the shell is elevated;
- Hermes CLI location and version, if installed;
- presence—not contents—of common Hermes data directories;
- Ollama CLI and local API version;
- installed/running Ollama model names;
- presence of `local-assistant-brain:latest`;
- whether port 11434 listens only on loopback.

The script does not read Hermes configuration contents, conversations, memories, skills, environment-secret values, browser data, or personal files. It makes no internet request and writes no report unless a later version explicitly adds an opt-in output path.

## Stage 2 — Isolated Hermes profile

Only after Stage 1 is reviewed:

- pin an exact Hermes release;
- create a disposable `HERMES_HOME` separate from any existing profile;
- disable automatic widening of capabilities and automatic updates during testing;
- use only `http://127.0.0.1:11434/v1`;
- expose no external connectors;
- restrict working files to a disposable test directory;
- disable or remove terminal, process, execute-code, cron, browser, messaging, and external-memory tools initially.

## Stage 3 — Local model compatibility

Test `gpt-oss:20b` and, only if necessary, one smaller installed alternative. Measure:

- actual Ollama model selected;
- actual context allocated in `ollama ps`;
- GPU/CPU split;
- first-token and total response latency;
- structured tool-call validity;
- multi-turn instruction retention;
- cancellation and timeout behavior;
- hallucinated/unknown tool rate.

Context must be increased only after measurement. A nominal model maximum is not proof that the effective Ollama runtime context matches Hermes configuration.

## Stage 4 — Security acceptance suite

Required tests include:

- the exact negated planning prompt from v0.1.1;
- direct and indirect prompt injection from documents/tool output;
- unknown, disabled, and malformed tool calls;
- path traversal, junction/symlink escape, and protected paths;
- changed targets after preview;
- approval replay and approval expiry;
- background work after cancellation;
- memory poisoning and unapproved skill creation;
- network-off verification;
- emergency-stop behavior;
- restart recovery.

## Stage 5 — Adoption decision

Hermes is acceptable only if:

1. a fully local Ollama model reliably selects tools on this hardware;
2. all dangerous generic tools can be absent from the model's schema—not merely discouraged by prompts;
3. file and external actions can be routed through the deterministic broker;
4. a disposable profile cleanly separates tests from real data;
5. updates can be pinned, reviewed, tested, and rolled back;
6. memory can be inspected, edited, paused, exported, and deleted;
7. no cloud provider or telemetry is required for core operation;
8. the security acceptance suite passes.

## Features to retain from the reviewed JARVIS demonstration

- goals and bounded mission queues;
- visible tool activity and verification;
- background tasks with explicit leases and cancellation;
- command discovery and capability display;
- skills as reviewed procedures;
- persistent memory with user controls;
- daily briefings and schedules after the core is proven;
- voice after text approvals are dependable.

Additional required commands:

```text
/mode
/permissions
/approvals
/activity
/privacy
/memory
/undo
/stop
```

Personality is presentation only. It can never change permissions, approval requirements, privacy boundaries, or truthfulness requirements.

