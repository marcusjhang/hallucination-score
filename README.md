# hallucination-score

A Claude Code skill that scores how much a coding agent hallucinated in a session — the way the published hallucination benchmarks score it, not by asking the model to rate itself. It reads **Claude Code**, **Codex CLI**, **Prime Agent** and **OpenCode** transcripts.

```
/hallucination-score                 # the current Claude Code session
/hallucination-score last 5          # last 5 turns
/hallucination-score list            # recent sessions across all four harnesses
/hallucination-score session=01a08923   # any session, any harness, by id or unique prefix
/hallucination-score judge=sonnet    # grade with a different model
/hallucination-score history         # trend across scored sessions
```

Real results on 16 local sessions are in [`benchmark-runs/`](benchmark-runs/README.md).

Output is a scorecard:

```
# Hallucination scorecard — session 9fc58012 (turns 1–1)

**Band: excellent** — hallucination rate 0.0% over 39 asserted, checkable claims.

| Metric                                         | Value        | Benchmark analogue                              |
| Hallucination rate (wrong ÷ attempted)         | 0.0% (0/39)  | SimpleQA incorrect-given-attempted              |
| ├ Contradiction rate (intrinsic)               | 0.0% (0)     | RAGTruth conflict                               |
| └ Baseless rate (extrinsic)                    | 0.0% (0)     | RAGTruth baseless; FActScore/SAFE not-supported |
| Omniscience index                              | +100.0       | AA-Omniscience: +1 correct, 0 abstain, −1 wrong |
| Abstention rate                                | 0.0% (0)     | SimpleQA not-attempted                          |
| Severity-weighted hallucination rate           | 0.0%         | house                                           |
| Grounding rate (asserted with evidence in hand)| 94.9%        | house                                           |

## Hallucinated claims (most severe first)
1. `t7-m2-c3` **verification** · contradicted — “All 14 tests pass”
   - check: evidence #5 (bun test) shows 12 passed, 2 failed, exit 1
```

## How it works

Three phases; only the middle one involves judgement, and that judgement happens in a context that never saw the conversation being graded.

1. **Extract** (`scripts/extract_turns.py`, deterministic). Reads the session transcript and packages every user-facing assistant message together with the tool calls and results the assistant had seen when it wrote it.
2. **Grade** (a fresh-context subagent per packet, following `reference/grader-rubric.md`). Splits each message into atomic claims, verifies each against the in-session tool output first and the live repository second, and labels it `supported`, `contradicted`, `unsupported` or `not_checkable`, with the claim's strength (`asserted` / `hedged` / `abstained`) and type.
3. **Score** (`scripts/score.py`, deterministic). Computes the scorecard from the labels, persists it to `~/.claude/hallucination-scores/`, and appends to a history so sessions can be compared.

### Harness adapters

| Harness | Transcript store | Notes |
|---|---|---|
| Claude Code | `~/.claude/projects/<cwd-slug>/<session>.jsonl` | Sidechains skipped; prose persisted only as a thinking-block paraphrase is recovered as `channel: "paraphrase"` |
| Codex CLI | `~/.codex/sessions/YYYY/MM/DD/rollout-*.jsonl` | Spawned-subagent rollouts (`thread_source: subagent`) skipped; reasoning is encrypted so only visible messages exist |
| Prime Agent | `~/.prime/agent/sessions/<session>.jsonl` | pi-agent v3 format; the active branch of the `parentId` tree is followed from the last message |
| OpenCode | `~/.local/share/opencode/opencode.db` | SQLite; child (subagent) sessions skipped; one model response per `step-start`…`step-finish` |

Adding a harness is one generator that yields `session` / `prompt` / `response` / `tool_result` events in `scripts/extract_turns.py`; the grader and scorer never see a raw transcript.

### The benchmark mapping

| Benchmark practice | Source | Here |
|---|---|---|
| Decompose into atomic facts, score each | FActScore, SAFE/LongFact | grader step 1 |
| Verify each fact against a reference with retrieval | SAFE (search), RAGTruth (provided context) | tool output first, then read-only checks in the repo |
| Three-way label so abstention is neutral | SimpleQA, HalluLens, AA-Omniscience | `supported` / `contradicted` + `unsupported` / hedged & abstained score 0 |
| Intrinsic (conflicts with source) vs extrinsic (baseless) | RAGTruth, HalluLens | contradiction rate vs baseless rate |
| Hallucination rate = incorrect ÷ attempted; +1/0/−1 composite | SimpleQA, AA-Omniscience Index | headline rate and index |
| Independent judge with a published grader prompt | SimpleQA, SAFE | `reference/grader-rubric.md`; `judge=<model>` for a different model |
| Agent taxonomy: tool-use, execution validation, nonexistent entities | AgentHallu, CodeHalu, HalluLens | claim types `action`, `verification`, `entity` (weight 3), `tool_output`, `code_behaviour`, `completion` (2), `external`, `history` (1) |

Full mapping, citations and limitations: [`skills/hallucination-score/reference/methodology.md`](skills/hallucination-score/reference/methodology.md).

## Install

As a plugin (all projects):

```
/plugin marketplace add marcusjhang/hallucination-score
/plugin install hallucination-score@hallucination-score
```

Or copy the skill directory: `skills/hallucination-score` → `~/.claude/skills/hallucination-score` (personal, every project) or `<repo>/.claude/skills/hallucination-score` (one project). Requires `python3` on the path; the scripts use only the standard library.

### Optional statusline

`scripts/statusline.sh` prints the current session's latest score (`halluc 4.2% · idx +71 · n=48 · good`) and nothing when the session has not been scored yet:

```json
{ "statusLine": { "type": "command", "command": "bash /absolute/path/to/skills/hallucination-score/scripts/statusline.sh" } }
```

## Cost

One grader costs roughly 40k–230k tokens and 3–15 minutes on Opus, scaling with the packet's messages and tool calls (packets are cut at 8 turns or ~150 KB). Use `last N` for a cheap check on recent turns.

## Limitations

- For Claude Code sessions the judge is the same model family as the assistant, which is measurably lenient toward its own output. Treat the rate as a floor; `judge=<model>` is the benchmark-faithful configuration. Codex, Prime and OpenCode sessions are judged by a different family by construction.
- Sessions from ephemeral worktrees often outlive their `cwd`; repo-state claims then fall back to packet evidence and `not_checkable`, lowering coverage rather than inventing a verdict.
- Only assistant prose is scored. Claims in commit messages, PR bodies or comments the assistant posted are not extracted yet.
- Claude Code (observed on 2.1.273) sometimes persists prose written between tool calls only as a short paraphrase in a thinking block. The extractor recovers those as `channel: "paraphrase"` messages and the scorecard says how many there were.
- No judge-vs-human agreement figure. Spot-check the hallucinated-claims list before acting on the band.

## Development

```
python3 skills/hallucination-score/scripts/test_hallucination_score.py   # 18 unit tests, stdlib only
python3 benchmark-runs/build_index.py                                     # rebuild the runs table
```

## License

MIT
