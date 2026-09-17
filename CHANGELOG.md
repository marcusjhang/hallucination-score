# Changelog

## 0.3.0 — 2026-09-17

- Second judge: `scripts/jev_second_judge.py` re-labels every claim with TypeSafe's Jev (a different model family, calibrated probabilities) from the session evidence alone, never seeing the grader's label or check. Default mode retrieves the tool calls that bear on each claim (lexical + a Jev ranking question), reloads them untruncated from the transcript, and asks the three-way question on that small state; `--mode turn` sends the whole turn and is kept for comparison. `score.py --jev` adds a "Second judge" section — Cohen's κ on the packet-checkable set, the confusion matrix, and the confident disagreements in both directions — and annotates each hallucinated claim with the second verdict. Opt-in with `/hallucination-score jev`; needs `TYPESAFE_API_KEY`.
- Measured on 15 of the 16 benchmark runs (jev-1.13.0; the `9fc58012` run's packets were overwritten by a later scoring of that session): hallucination-or-not agreement 78.5%, κ 0.18 (whole-turn mode: κ 0.10). Jev over-flags — 22% of the grader's `supported` claims come back hallucinated, and a manual sample found most of those to be Jev errors — so the number bounds the second judge's noise more than the grader's leniency. Documented as such; the harness stays so a newer model can be re-measured.
- `benchmark-runs/`: 15 runs re-exported with the second judge; the index gains a κ column and a pooled agreement section. `score.py` history lines carry `jev_hallucination_kappa` when present.

## 0.1.0 — 2026-09-17

Initial release.

- `/hallucination-score` skill: transcript extraction, fresh-context grader rubric, deterministic scorer, per-session history.
- Recovers assistant messages that Claude Code 2.1.273 persists only as thinking-block paraphrases (`channel: "paraphrase"`).
- Optional statusline snippet.

## 0.2.1 — 2026-09-17

- Rubric: graders must never change credential or account state (`gh auth switch`, `git config --global`, `kill`, …). A grader probing repo access during the 0.2.0 runs switched the machine's active `gh` account and left it switched.

## 0.2.0 — 2026-09-17

- Harness adapters: Codex CLI, Prime Agent and OpenCode sessions are extracted into the same packet format as Claude Code; `--list` shows recent sessions across all four, `--session` accepts an id or unique prefix from any of them, `--harness` forces one. Subagent transcripts (Claude sidechains, Codex `thread_source: subagent`, OpenCode child sessions) are skipped.
- `extract_turns.py --evidence TURN:INDEX` prints one tool call and its untruncated result, so graders no longer parse raw transcripts to recover an excerpt.
- `extract_turns.py --max-packet-bytes` (default 150000): packets cut on size as well as turn count, so one tool-heavy turn gets its own grader.
- `score.py --export DIR` writes `scorecard.md` + `scorecard.json` for a `benchmark-runs/` folder; the harness now appears in the scorecard header and in `--history`.
- Rubric: generalisations ("only X works", "nothing else") are claims and are `unsupported` when evidence covers a subset; a search that proves nothing makes a claim `unsupported`, never `contradicted`; `external` vs `code_behaviour` boundary defined; same-turn later evidence rule made explicit.
- `benchmark-runs/`: 16 real sessions (4 Claude Code, 5 Codex, 5 Prime Agent, 2 OpenCode) with per-claim verdicts and a regenerable index.
