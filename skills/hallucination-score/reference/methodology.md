# Methodology: how the benchmarks score hallucination, and how this skill maps onto them

The published hallucination benchmarks disagree on datasets but converge on a pipeline. This skill reproduces that pipeline over a Claude Code session, with the session's own tool results standing in for the benchmark's reference answers.

## The benchmark pipeline

| Stage | What the benchmarks do | Where |
|---|---|---|
| 1. Unit of measurement | Decompose a response into **atomic facts** — short self-contained sentences carrying one piece of information — and score each one; a response-level score is the precision over its facts | FActScore ([Min et al. 2023](https://arxiv.org/abs/2305.14251)); SAFE/LongFact ([Wei et al. 2024](https://arxiv.org/abs/2403.18802)) |
| 2. Relevance filter | Drop facts that are not about the question (opinions, meta-commentary) before scoring | SAFE's *irrelevant* label |
| 3. Grounding source | Two regimes: **factuality** against world knowledge (TruthfulQA, SimpleQA) and **faithfulness** against a provided context (RAGTruth, Vectara HHEM, FACTS Grounding). Faithfulness benchmarks label *conflict* (contradicts the source) separately from *baseless* (not in the source) | RAGTruth ([Niu et al. 2024](https://arxiv.org/abs/2401.00396)); HalluLens intrinsic vs extrinsic ([Bang et al. 2025](https://arxiv.org/abs/2504.17550)) |
| 4. Judge | An LLM judge with access to the reference (SimpleQA hands it the gold answer; SAFE lets it search) labels each fact from a closed set. Judges are validated against human labels | SimpleQA ([Wei et al. 2024](https://openai.com/index/introducing-simpleqa/)); SAFE |
| 5. Three-way label | **correct / incorrect / not attempted**. Abstention is its own class so a model cannot look better by guessing | SimpleQA; HalluLens *false refusal* and *hallucinated when not refused*; AA-Omniscience ([Artificial Analysis 2025](https://arxiv.org/abs/2511.13029)) |
| 6. Metrics | *Hallucination rate* = incorrect ÷ attempted; *accuracy* = correct ÷ all; *abstention rate*; a composite that scores +1 correct / 0 abstain / −1 incorrect so guessing is punished | SimpleQA "correct given attempted"; AA-Omniscience Index (−100..100) |
| 7. Calibration | Compare stated confidence with outcome; a well-calibrated model hedges where it is wrong | SimpleQA calibration study; Kalai et al. 2025, *Why language models hallucinate* ([arXiv](https://arxiv.org/abs/2509.04664)) — binary grading rewards guessing, so score abstention neutrally |
| 8. Agent-specific taxonomy | In agent trajectories, hallucinations cluster by step: planning, retrieval, reasoning, human-interaction, **tool-use** (claiming a call or result that did not happen). Span-level detection over code and tool output is the current frontier | AgentHallu ([2026](https://arxiv.org/abs/2601.06818)); span-level detection over code/tool output ([2026](https://arxiv.org/abs/2607.00895)); CodeHalu execution-based validation ([Tian et al. 2024](https://arxiv.org/abs/2405.00253)) |

## The mapping

| Benchmark concept | In this skill |
|---|---|
| Response | One user-facing assistant text block (`t<turn>-m<n>`). Thinking blocks are not scored: benchmarks score the answer, not the scratchpad |
| Atomic fact | A claim extracted by the grader with a verbatim quote and a self-contained restatement (`grader-rubric.md`, step 1) |
| Reference answer / provided context | The tool calls and results in the session (the packet). This makes the session a **faithfulness** problem first: did the assistant report what it saw? |
| Search (SAFE) | Live read-only checks in the repo: `Grep`, `Read`, `git log`, running the named test command |
| Judge | A **fresh-context subagent** that did not produce the transcript. Same model family unless `judge=<model>` is given; see limitations |
| correct / incorrect / not attempted | `supported` / `contradicted` + `unsupported` / `hedged` + `abstained` |
| conflict vs baseless (RAGTruth) | `contradicted` (intrinsic) vs `unsupported` (extrinsic) |
| Irrelevant (SAFE) | `not_checkable` — excluded from every rate |
| Hallucination rate | `(contradicted + unsupported) ÷ attempted` |
| Omniscience Index | `100 × (supported − contradicted − unsupported) ÷ checkable`, hedged/abstained score 0 |
| Calibration | Hedge calibration: how many hedged claims turned out wrong (hedge warranted) vs right (over-hedged) |
| Tool-use hallucination (AgentHallu) | `action` type: "I ran/edited/committed X" verified against the actual tool calls |
| Execution validation (CodeHalu) | `verification` type: "tests pass" needs a run in the session; a run that failed makes it `contradicted`, no run makes it `unsupported` |
| Nonexistent entity (HalluLens) | `entity` type: files, symbols, packages, flags |

Two house additions, kept separate from the benchmark metrics so they never contaminate the comparable numbers:

- **Severity weight** (3/2/1 by type). A fabricated test pass costs more than a wrong PR number. Reported as `weighted hallucination rate` alongside the unweighted one.
- **Grounding rate**: share of asserted claims made *after* the assistant had observed supporting evidence. A true claim asserted before looking is `supported` but not grounded. This is the process metric Kalai et al. argue for: reward looking, not guessing.

## Bands

Hallucination rate < 2% excellent · < 5% good · < 10% watch · < 20% poor · otherwise failing. These are house thresholds for a *grounded* coding session, where the closest published comparable — grounded-summarisation faithfulness leaderboards such as Vectara's HHEM board — puts frontier models in the low single digits. World-knowledge benchmarks (SimpleQA, AA-Omniscience) report far higher rates because they ask obscure trivia; do not compare against those. Recalibrate the bands once `score.py --history` has a few dozen sessions.

## Limitations to state when reporting

1. **Self-preference bias.** The judge is usually the same model family as the assistant. LLM judges are measurably lenient toward their own outputs. Mitigations: fresh context (the judge never sees the reasoning that produced the claim), evidence-first labelling, closed label set, the `judge=<model>` override. A different-model judge is the benchmark-faithful configuration.
2. **Decomposition variance.** Claim counts differ between graders, which moves the denominator. The rate is more stable than the count; compare rates, and read the per-claim list rather than trusting one number.
3. **Truncated evidence.** Tool results are excerpted (head 1500 + tail 400 chars by default). The rubric sends unrecoverable cases to `not_checkable`, not `supported`. Raise `--max-result-chars` if coverage suffers.
4. **Post-hoc live checks.** The repo may have moved since the claim. The rubric judges claims at the turn they were made; where the packet cannot settle it and history is ambiguous the grader must say so.
5. **Scope.** Only assistant text is scored. Claims embedded in tool inputs — commit messages, PR bodies, comments the assistant posted — are not extracted yet.
6. **Lossy transcripts.** Claude Code (observed on 2.1.273) sometimes persists prose written between tool calls only as a ~150–300 character paraphrase inside a second `thinking` block, not verbatim. The extractor recovers these as `channel: "paraphrase"` messages and the scorecard reports how many there were; claims quoted from them are graded against a paraphrase, so wording-level discrepancies are sent to `not_checkable` rather than counted as hallucinations.
7. **No human agreement figure.** Benchmarks report judge-vs-human agreement. This skill has none; spot-check the hallucinated-claims list before acting on the band.
