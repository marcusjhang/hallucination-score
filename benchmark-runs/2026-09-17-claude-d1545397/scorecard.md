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
2. `t2-m4-c14` **completion** · contradicted — “nothing else feeds it”
   - claim: Nothing other than gbrain sync from ~/brain writes content into the PGLite DB.
   - check: The `remember` MCP verb writes facts directly into the DB (t1 evidence #1 fact with source 'setup'; t5 evidence #1 'remembered as fact #2'); t2 evidence #3 `gbrain --help` lists `import <dir>`, `transcripts ingest`, `files sync <dir>` as other feeders; the assistant also said it could not run `gbrain sources list` to confirm registered sources.

## Hedge calibration

3 hedged claims: 0 turned out wrong (hedge warranted), 3 were right (over-hedged).

## Coverage

Messages with at least one claim: 19 of 22 (4 of the 22 survive only as harness paraphrases, not verbatim). Claims: 103 total, 101 checkable, 2 excluded as not checkable.
Graders: claude-opus-5 (chunk 1).
