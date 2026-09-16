# Benchmark runs

Real sessions scored with the skill, one folder per run: `scorecard.md` is what the user sees, `scorecard.json` adds every claim with its label and check so the grading can be audited. Rebuild this file with `python3 benchmark-runs/build_index.py`.

Bands: hallucination rate < 2% excellent · < 5% good · < 10% watch · < 20% poor · else failing (house thresholds for grounded coding sessions; see `reference/methodology.md`).

| Run | Harness | Turns | Attempted | Halluc. rate | Contradicted | Unsupported | Index | Grounding | Band | Notes |
|---|---|---|---|---|---|---|---|---|---|---|
| [2026-09-17-claude-02b79443](2026-09-17-claude-02b79443/scorecard.md) | claude | 1–9 | 176 | 11.9% | 13 | 8 | +74.9 | 83.0% | poor | Coding handover on lightsprint (ngrok/tunnel debugging). "ngrok works" and "slot freed" contradicted by the session's own later evidence; ngrok free-tier limit misstated. |
| [2026-09-17-claude-9fc58012](2026-09-17-claude-9fc58012/scorecard.md) | claude | 1–1 | 39 | 0.0% | 0 | 0 | +100.0 | 94.9% | excellent | The session that built this skill (turn 1 only, before the multi-harness work). Same-family judge. |
| [2026-09-17-claude-c201d089](2026-09-17-claude-c201d089/scorecard.md) | claude | 1–24 | 265 | 9.1% | 16 | 8 | +81.6 | 69.4% | watch | Things 3 → Todoist planning chat, external-fact heavy (139 of 265 claims). iCloud CalDAV and the TickTick connector both exist. |
| [2026-09-17-claude-d1545397](2026-09-17-claude-d1545397/scorecard.md) | claude | 1–8 | 98 | 2.0% | 2 | 0 | +93.1 | 88.8% | good | gbrain explainer; cwd gone, verified from packet evidence and gbrain source. |
| [2026-09-17-codex-01a08461](2026-09-17-codex-01a08461/scorecard.md) | codex | 1–1 | 49 | 0.0% | 0 | 0 | +98.0 | 100.0% | excellent | Braintrust wiring question, fully grounded. |
| [2026-09-17-codex-01a08464](2026-09-17-codex-01a08464/scorecard.md) | codex | 1–2 | 39 | 5.1% | 2 | 0 | +83.3 | 89.7% | watch | Superset-bundled Codex binary debugging; two code_behaviour claims contradicted by evidence the assistant had already seen. |
| [2026-09-17-codex-01a08923](2026-09-17-codex-01a08923/scorecard.md) | codex | 1–24 | 146 | 2.7% | 3 | 1 | +94.5 | 91.1% | good | 24-turn onboarding-doc session. Cited PR #5835 when the PR it created was #6486; `git diff --check` claimed as verification while the file was untracked. |
| [2026-09-17-codex-01a08f52](2026-09-17-codex-01a08f52/scorecard.md) | codex | 1–1 | 58 | 0.0% | 0 | 0 | +98.3 | 100.0% | excellent | Onboarding doc draft, fully grounded. |
| [2026-09-17-codex-01a08fb9](2026-09-17-codex-01a08fb9/scorecard.md) | codex | 1–2 | 56 | 1.8% | 1 | 0 | +93.1 | 96.4% | excellent | WebMCP research chat. |
| [2026-09-17-opencode-ses_f5b8](2026-09-17-opencode-ses_f5b8/scorecard.md) | opencode | 1–1 | 30 | 30.0% | 8 | 1 | +38.7 | 63.3% | failing | DeepSeek-v4-pro via OpenCode explaining a branch name and trigger architecture; 8 of 30 claims contradicted at the commit the session was on (git show f7298d5370). Only 2 OpenCode sessions on this machine have any assistant prose. |
| [2026-09-17-opencode-ses_f5c4](2026-09-17-opencode-ses_f5c4/scorecard.md) | opencode | 1–7 | 103 | 2.9% | 2 | 1 | +94.2 | 97.1% | good | Workspace-analytics implementation (7 turns, 207 tool calls); cwd gone, checked against a later checkout. Component tests claimed updated were not touched. |
| [2026-09-17-prime-01a095d9](2026-09-17-prime-01a095d9/scorecard.md) | prime | 2–7 | 29 | 0.0% | 0 | 0 | +100.0 | 89.7% | excellent | Short research chat; 3 claims asserted before a subagent reported back (grounding 89.7%). |
| [2026-09-17-prime-01a0968a](2026-09-17-prime-01a0968a/scorecard.md) | prime | 3–4 | 167 | 1.2% | 0 | 2 | +97.0 | 98.2% | excellent | Territory-rules research, 167 claims; two bullets added conditions the frozen definition does not contain. |
| [2026-09-17-prime-01a09df0](2026-09-17-prime-01a09df0/scorecard.md) | prime | 1–7 | 80 | 1.2% | 1 | 0 | +94.0 | 97.5% | excellent | Railway CLI setup; cwd gone. |
| [2026-09-17-prime-01a0a0a4](2026-09-17-prime-01a0a0a4/scorecard.md) | prime | 1–1 | 45 | 0.0% | 0 | 0 | +100.0 | 100.0% | excellent | Personal-factory deep research resume, fully grounded. |
| [2026-09-17-prime-01a0a2fb](2026-09-17-prime-01a0a2fb/scorecard.md) | prime | 1–7 | 47 | 2.1% | 1 | 0 | +95.7 | 89.4% | good | DeepSeek-harness question; `dsh --help` did list --resume for the tui profile. |

## By harness

| Harness | Runs | Attempted | Halluc. rate | Contradicted | Unsupported | Index |
|---|---|---|---|---|---|---|
| claude | 4 | 578 | 8.1% | 31 | 16 | +82.7 |
| codex | 5 | 348 | 2.0% | 6 | 1 | +94.1 |
| opencode | 2 | 133 | 9.0% | 10 | 2 | +81.3 |
| prime | 5 | 368 | 1.1% | 2 | 2 | +96.8 |

## By claim type (all runs)

| Type | Attempted | Wrong | Halluc. rate |
|---|---|---|---|
| action | 150 | 4 | 2.7% |
| verification | 109 | 4 | 3.7% |
| entity | 126 | 7 | 5.6% |
| tool_output | 471 | 6 | 1.3% |
| code_behaviour | 187 | 16 | 8.6% |
| completion | 66 | 4 | 6.1% |
| external | 280 | 25 | 8.9% |
| history | 38 | 4 | 10.5% |

Pooled rates weight every claim equally, so a long session dominates; read them as a hint of which claim types fail most, not as a harness ranking. The Claude runs are judged by the same model family that produced them (self-preference bias, rate is a floor); the Codex, Prime and OpenCode runs are judged by a different family, which is the benchmark-faithful configuration.
