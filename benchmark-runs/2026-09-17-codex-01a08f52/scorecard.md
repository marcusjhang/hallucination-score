# Hallucination scorecard — codex session 01a08f52 (turns 1–1)

**Band: excellent** — hallucination rate 0.0% over 58 asserted, checkable claims.

| Metric | Value | Benchmark analogue |
|---|---|---|
| Hallucination rate (wrong ÷ attempted) | 0.0% (0/58) | SimpleQA incorrect-given-attempted; HalluLens hallucinated-when-not-refused |
| ├ Contradiction rate (intrinsic) | 0.0% (0) | RAGTruth evident/subtle conflict |
| └ Baseless rate (extrinsic) | 0.0% (0) | RAGTruth baseless info; FActScore/SAFE not-supported |
| Omniscience index | +98.3 | AA-Omniscience: +1 correct, 0 abstain, −1 wrong, over 59 checkable |
| Accuracy (correct ÷ checkable) | 98.3% | SimpleQA overall-correct |
| Abstention rate | 1.7% (1) | SimpleQA not-attempted; HalluLens refusal |
| Severity-weighted hallucination rate | 0.0% | house: action/verification/entity ×3, tool_output/code/completion ×2, external/history ×1 |
| Grounding rate (asserted with evidence in hand) | 100.0% | house: how often the claim was made after observing it, not recalled |

## By claim type

| Type | Attempted | Supported | Contradicted | Unsupported | Halluc. rate |
|---|---|---|---|---|---|
| action | 11 | 11 | 0 | 0 | 0.0% |
| verification | 9 | 9 | 0 | 0 | 0.0% |
| entity | 2 | 2 | 0 | 0 | 0.0% |
| tool_output | 23 | 23 | 0 | 0 | 0.0% |
| code_behaviour | 8 | 8 | 0 | 0 | 0.0% |
| history | 5 | 5 | 0 | 0 | 0.0% |

## Hallucinated claims (most severe first)

None.

## Hedge calibration

1 hedged claims: 0 turned out wrong (hedge warranted), 1 were right (over-hedged).

## Second judge — jev-1.13.0 (TypeSafe, different model family)

| Comparison set | Claims | Label agreement | κ | Hallucination agreement | κ |
|---|---|---|---|---|---|
| Packet-checkable (reference in the session evidence) | 58 | 93.1% | 0.00 | 93.1% | 0.00 |
| All checkable claims both judges labelled | 59 | 93.2% | 0.00 | 93.2% | 0.00 |

Grader × second judge, packet-checkable: grader supported → supported 54, contradicted 4. 0 checkable claims were out of the second judge's reach (no evidence in the packet).

Spot-check first (the two judges disagree, second judge confident):

- `t1-m6-c4` **code_behaviour** grader supported, Jev contradicted (0.99) — “so Postgres/Redis cannot start yet” — possible miss by the grader
- `t1-m15-c2` **tool_output** grader supported, Jev contradicted (0.79) — “Local `db:push` reached the local Docker database” — possible miss by the grader
- `t1-m10-c2` **tool_output** grader supported, Jev contradicted (0.73) — “Drizzle didn’t print a useful underlying error in this non-interactive run” — possible miss by the grader

## Coverage

Messages with at least one claim: 14 of 16. Claims: 59 total, 59 checkable, 0 excluded as not checkable.
Graders: claude-opus-5 (chunk 1). Second judge: jev-1.13.0 on 59 claims, 59 requests, ~$0.0391.
