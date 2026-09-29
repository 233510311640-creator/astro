# Claude tools installed for Astro

**Checked:** 30 September 2026. This records installation checks, not a claim that every tool has completed a live Claude session or connected to an external provider.

| Tool | Scope and source | Verified state |
| --- | --- | --- |
| Claude Code Setup | Existing user plugin from [Anthropic's official marketplace](https://github.com/anthropics/claude-plugins-official) | Preserved; enabled, v1.0.0 |
| Ponytail | Astro-scoped plugin from [DietrichGebert/ponytail](https://github.com/DietrichGebert/ponytail) | Enabled, v4.10.0 |
| Caveman | Astro-scoped plugin from [JuliusBrussee/caveman](https://github.com/JuliusBrussee/caveman) | Enabled, v2.7.0; the separate proxy installer was not run |
| Graphify | User-level `graphifyy` CLI from [Graphify-Labs/graphify](https://github.com/Graphify-Labs/graphify), with its skill in `.claude/skills/graphify/` | CLI v0.9.72; Claude skill directory validates; project hooks installed |
| Task Observer | `.claude/skills/task-observer/` copied from [rebelytics/one-skill-to-rule-them-all](https://github.com/rebelytics/one-skill-to-rule-them-all) | Full skill, references, scripts, and CC BY 4.0 license present; Claude skill directory validates. Activation needs checking in a fresh Claude session. |
| Herdr | User-level Windows binary from [herdrdev/herdr](https://github.com/herdrdev/herdr) | v0.9.2; release SHA-256 matched GitHub's published digest; Claude integration reports `current (v10)` |
| OmniRoute | User-level npm package from [diegosouzapw/OmniRoute](https://github.com/diegosouzapw/OmniRoute) | CLI v3.8.50 responds; optional postinstall initialization was skipped; no provider login, server start, or Claude routing change |
| Claude Usage Tracker | **Pending exact product choice** | Several unrelated Windows, VS Code, and browser products use this name; none was installed by guesswork |

Project-specific Claude settings and skills are stored in this Astro repository. Generated Graphify graphs and Task Observer notes are ignored by Git because they can contain local work context. Existing global Claude settings were preserved; a backup was made before adding Herdr's hook.

Read-only verification commands:

```powershell
claude plugin list --json
claude plugin validate .claude\skills
graphify --version
herdr --version
herdr integration status
omniroute --version
```

The Graphify and Task Observer files can be verified locally without a Claude login. To prove Task Observer actually activates, open a **new** Claude session in this repository and check its Session Start Protocol; file validation alone cannot establish that behavior. Connecting OmniRoute to a provider or launching a Herdr workspace is a separate setup step, not part of the installation checks above.
