# Changelog

## 0.1.0 — 2026-09-17

Initial release.

- `/hallucination-score` skill: transcript extraction, fresh-context grader rubric, deterministic scorer, per-session history.
- Recovers assistant messages that Claude Code 2.1.273 persists only as thinking-block paraphrases (`channel: "paraphrase"`).
- Optional statusline snippet.

## Unreleased

- `extract_turns.py --max-packet-bytes` (default 150000): packets now cut on size as well as turn count, so one tool-heavy turn gets its own grader instead of swamping a chunk.
