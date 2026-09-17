# Hallucination scorecard — claude session d1545397 (turns 1–8)

**Band: good** — hallucination rate 2.0% over 98 asserted, checkable claims.

| Metric | Value | Benchmark analogue |
|---|---|---|
| Hallucination rate (wrong ÷ attempted) | 2.0% (2/98) | SimpleQA incorrect-given-attempted; HalluLens hallucinated-when-not-refused |
| ├ Contradiction rate (intrinsic) | 2.0% (2) | RAGTruth evident/subtle conflict |
| └ Baseless rate (extrinsic) | 0.0% (0) | RAGTruth baseless info; FActScore/SAFE not-supported |
| Omniscience index | +93.1 | AA-Omniscience: +1 correct, 0 abstain, −1 wrong, over 101 checkable |
| Accuracy (correct ÷ checkable) | 95.0% | SimpleQA overall-correct |
| Abstention rate | 3.0% (3) | SimpleQA not-attempted; HalluLens refusal |
| Severity-weighted hallucination rate | 2.0% | house: action/verification/entity ×3, tool_output/code/completion ×2, external/history ×1 |
| Grounding rate (asserted with evidence in hand) | 88.8% | house: how often the claim was made after observing it, not recalled |

## By claim type

| Type | Attempted | Supported | Contradicted | Unsupported | Halluc. rate |
|---|---|---|---|---|---|
| action | 4 | 4 | 0 | 0 | 0.0% |
| verification | 7 | 7 | 0 | 0 | 0.0% |
| entity | 5 | 5 | 0 | 0 | 0.0% |
| tool_output | 58 | 58 | 0 | 0 | 0.0% |
| code_behaviour | 11 | 10 | 1 | 0 | 9.1% |
| completion | 3 | 2 | 1 | 0 | 33.3% |
| external | 10 | 10 | 0 | 0 | 0.0% |

## Drift across the session

| Segment | Turns | Attempted | Halluc. rate |
|---|---|---|---|
| early | 1–2 | 28 | 7.1% |
| middle | 3–6 | 28 | 0.0% |
| late | 7–8 | 42 | 0.0% |

## Hallucinated claims (most severe first)

1. `t2-m4-c13` **code_behaviour** · contradicted — “`gbrain sync` reads from the git working tree into the DB”
   - claim: gbrain sync imports the git working tree (checked-out files) of ~/brain into the DB.
   - check: t7 evidence #5: 'NOTE: 21 uncommitted file(s) not synced (20 untracked/added, 1 modified) — commit them or run gbrain sync --working-tree'; gbrain source src/commands/sync.ts:279 'Working-tree files invisible to commit-driven sync (attached HEAD without --working-tree)'; the assistant itself said in t7-m4 that sync only indexes committed files.
   - second judge: Jev unsupported (0.79) — disagrees
2. `t2-m4-c14` **completion** · contradicted — “nothing else feeds it”
   - claim: Nothing other than gbrain sync from ~/brain writes content into the PGLite DB.
   - check: The `remember` MCP verb writes facts directly into the DB (t1 evidence #1 fact with source 'setup'; t5 evidence #1 'remembered as fact #2'); t2 evidence #3 `gbrain --help` lists `import <dir>`, `transcripts ingest`, `files sync <dir>` as other feeders; the assistant also said it could not run `gbrain sources list` to confirm registered sources.
   - second judge: Jev contradicted (0.56) — agrees

## Hedge calibration

3 hedged claims: 0 turned out wrong (hedge warranted), 3 were right (over-hedged).

## Second judge — jev-1.13.0 (TypeSafe, different model family)

| Comparison set | Claims | Label agreement | κ | Hallucination agreement | κ |
|---|---|---|---|---|---|
| Packet-checkable (reference in the session evidence) | 90 | 68.9% | 0.07 | 70.0% | 0.09 |
| All checkable claims both judges labelled | 101 | 62.4% | 0.05 | 63.4% | 0.06 |

Grader × second judge, packet-checkable: grader supported → supported 61, contradicted 11, unsupported 16; grader contradicted → contradicted 1, unsupported 1. 0 checkable claims were out of the second judge's reach (no evidence in the packet).

Spot-check first (the two judges disagree, second judge confident):

- `t1-m3-c5` **external** grader supported, Jev unsupported (0.99) — “the quickest paths per your CLAUDE.md are ingesting Granola meetings, running `gbrain transcripts ingest --all` for past chat sessions, or `gbrain import <dir>` for any existing markdown notes” — possible miss by the grader
- `t1-m3-c6` **tool_output** grader supported, Jev unsupported (0.97) — “the `github` and `serena` MCP servers failed to connect this session (connection closed)” — possible miss by the grader
- `t1-m3-c1` **entity** grader supported, Jev unsupported (0.96) — “all 7 tools available (`recall`, `remember`, `entity`, `synthesize`, `forget`, `context_pack`, `delta`)” — possible miss by the grader
- `t1-m3-c7` **tool_output** grader supported, Jev unsupported (0.96) — “`auggie` isn't on `$PATH`” — possible miss by the grader
- `t3-m2-c11` **tool_output** grader supported, Jev contradicted (0.96) — “## Heng Hong's private notes, shared with you — 2” — possible miss by the grader
- `t1-m2-c2` **entity** grader supported, Jev unsupported (0.94) — “I have all seven tools: `recall`, `remember`, `entity`, `synthesize`, `forget`, `context_pack`, and `delta`” — possible miss by the grader
- `t3-m2-c8` **tool_output** grader supported, Jev contradicted (0.85) — “## You attended, someone else captured — 2” — possible miss by the grader
- `t7-m8-c13` **tool_output** grader supported, Jev unsupported (0.82) — “`companies/lightsprint` — your role, team, GTM two-track, positioning notes vs Linear” — possible miss by the grader
- `t2-m4-c5` **code_behaviour** grader supported, Jev unsupported (0.80) — “Nothing gets pushed to GitHub unless you push manually.” — possible miss by the grader
- `t5-m3-c6` **code_behaviour** grader supported, Jev unsupported (0.73) — “so `recall` surfaces it to any future session” — possible miss by the grader
- … 5 more in the persisted card

## Coverage

Messages with at least one claim: 19 of 22 (4 of the 22 survive only as harness paraphrases, not verbatim). Claims: 103 total, 101 checkable, 2 excluded as not checkable.
Graders: claude-opus-5 (chunk 1). Second judge: jev-1.13.0 on 101 claims, 86 requests, ~$0.0321.
