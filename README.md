# hallucination-score

A Claude Code skill that scores how much a coding agent hallucinated in a session — the way the published hallucination benchmarks score it, not by asking the model to rate itself. It reads **Claude Code**, **Codex CLI**, **Prime Agent** and **OpenCode** transcripts.

```
/hallucination-score                 # the current Claude Code session
/hallucination-score last 5          # last 5 turns
/hallucination-score list            # recent sessions across all four harnesses
/hallucination-score session=01a08923   # any session, any harness, by id or unique prefix
/hallucination-score judge=sonnet    # grade with a different model
/hallucination-score jev             # add a second, different-family judge (TypeSafe Jev) and report agreement
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

### Optional second judge (Jev)

`scripts/jev_second_judge.py` re-labels every claim with [TypeSafe's Jev](https://docs.typesafe.ai/concepts/system-one), a "System One" model that answers typed questions with calibrated probabilities and never generates text. It gets the claim, the verbatim quote and tool evidence from the session — never the grader's label or reasoning — and returns `supported / contradicted / unsupported` with a probability for each. `score.py --jev` then reports what the benchmarks report as judge-vs-human agreement, with Jev standing in for the human: Cohen's κ on the claims whose reference is in the session evidence, the confusion matrix, and the confident disagreements in both directions.

The default mode is retrieve-then-judge, the pattern TypeSafe's own cookbooks use: a lexical pass and a Jev ranking question pick the tool calls that bear on each claim, then the three-way question is asked with only those items — reloaded from the transcript untruncated — as state. `--mode turn` (the whole turn's evidence as one state, every claim as a question) is kept for comparison.

**What it measured on 15 of the 16 benchmark sessions (jev-1.13.0, 1,431 claims, ~$0.55, ~9 minutes; the remaining run's packets no longer exist locally):** label agreement with the Opus grader 77.0%, κ 0.14; hallucination-or-not agreement 78.5%, κ 0.18. Whole-turn mode scored κ 0.08–0.10 on the same claims. Jev found 43 of the grader's 55 hallucinations but also labelled 22% of the grader's `supported` claims as hallucinated; a manual read of ten of those found seven to be Jev errors (the evidence stated the claim outright — "Cannot connect to the Docker daemon" for "the daemon was not running"), two to be claims the grader had settled with a live repo check Jev cannot make, and one a claim about text the user pasted. Rewording the criteria did not move it. So the κ is honest but mostly bounds *Jev's* noise, not the grader's leniency, and the "possible miss" list is a place to look, not a verdict. It stays opt-in and experimental; a newer Jev or a different question design may change this, and the harness is in place to measure it.

It never changes a label and it cannot replace the grader: Jev does not decompose messages into claims and cannot run live checks in the repository. It needs `TYPESAFE_API_KEY` and sends session content to api.typesafe.ai. `--dry-run` prints the plan without sending anything.

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
- No judge-vs-human agreement figure. The `jev` second judge gives a judge-vs-judge κ (0.18 on the benchmark runs), but most of that disagreement traced to the second judge, so it does not yet bound the grader; spot-check the hallucinated-claims list before acting on the band.

## Development

```
python3 skills/hallucination-score/scripts/test_hallucination_score.py   # 32 unit tests, stdlib only
python3 benchmark-runs/build_index.py                                     # rebuild the runs table
```

## License

MIT
