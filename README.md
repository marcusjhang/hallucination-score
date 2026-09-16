# hallucination-score

A Claude Code skill that scores how much Claude hallucinated in the current session — the way the published hallucination benchmarks score it, not by asking the model to rate itself.

```
/hallucination-score            # whole session
/hallucination-score last 5     # last 5 turns
/hallucination-score judge=sonnet
/hallucination-score history    # trend across sessions
```

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

One grader over an 8-turn packet (~20 messages, ~45 tool calls) took about 140k tokens and 11 minutes on Opus. Use `last N` for a cheap check on recent turns.

## Limitations

- The judge is usually the same model family as the assistant, which is measurably lenient toward its own output. Treat the rate as a floor; `judge=<model>` is the benchmark-faithful configuration.
- Only assistant prose is scored. Claims in commit messages, PR bodies or comments the assistant posted are not extracted yet.
- Claude Code (observed on 2.1.273) sometimes persists prose written between tool calls only as a short paraphrase in a thinking block. The extractor recovers those as `channel: "paraphrase"` messages and the scorecard says how many there were.
- No judge-vs-human agreement figure. Spot-check the hallucinated-claims list before acting on the band.

## Development

```
python3 skills/hallucination-score/scripts/test_hallucination_score.py
```

## License

MIT
