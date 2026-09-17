# Hallucination scorecard — prime session 01a095d9 (turns 2–7)

**Band: excellent** — hallucination rate 0.0% over 29 asserted, checkable claims.

| Metric | Value | Benchmark analogue |
|---|---|---|
| Hallucination rate (wrong ÷ attempted) | 0.0% (0/29) | SimpleQA incorrect-given-attempted; HalluLens hallucinated-when-not-refused |
| ├ Contradiction rate (intrinsic) | 0.0% (0) | RAGTruth evident/subtle conflict |
| └ Baseless rate (extrinsic) | 0.0% (0) | RAGTruth baseless info; FActScore/SAFE not-supported |
| Omniscience index | +100.0 | AA-Omniscience: +1 correct, 0 abstain, −1 wrong, over 29 checkable |
| Accuracy (correct ÷ checkable) | 100.0% | SimpleQA overall-correct |
| Abstention rate | 0.0% (0) | SimpleQA not-attempted; HalluLens refusal |
| Severity-weighted hallucination rate | 0.0% | house: action/verification/entity ×3, tool_output/code/completion ×2, external/history ×1 |
| Grounding rate (asserted with evidence in hand) | 89.7% | house: how often the claim was made after observing it, not recalled |

## By claim type

| Type | Attempted | Supported | Contradicted | Unsupported | Halluc. rate |
|---|---|---|---|---|---|
| action | 9 | 9 | 0 | 0 | 0.0% |
| verification | 3 | 3 | 0 | 0 | 0.0% |
| entity | 3 | 3 | 0 | 0 | 0.0% |
| tool_output | 2 | 2 | 0 | 0 | 0.0% |
| completion | 1 | 1 | 0 | 0 | 0.0% |
| external | 11 | 11 | 0 | 0 | 0.0% |

## Drift across the session

| Segment | Turns | Attempted | Halluc. rate |
|---|---|---|---|
| early | 2–2 | 22 | 0.0% |
| middle | 4–4 | 2 | 0.0% |
| late | 7–7 | 5 | 0.0% |

## Hallucinated claims (most severe first)

None.

## Hedge calibration

No hedged claims.

## Second judge — jev-1.13.0 (TypeSafe, different model family)

| Comparison set | Claims | Label agreement | κ | Hallucination agreement | κ |
|---|---|---|---|---|---|
| Packet-checkable (reference in the session evidence) | 27 | 88.9% | 0.00 | 88.9% | 0.00 |
| All checkable claims both judges labelled | 29 | 86.2% | 0.00 | 86.2% | 0.00 |

Grader × second judge, packet-checkable: grader supported → supported 24, unsupported 3. 0 checkable claims were out of the second judge's reach (no evidence in the packet).

Spot-check first (the two judges disagree, second judge confident):

- `t2-m1-c7` **entity** grader supported, Jev unsupported (0.89) — “Build order is in §7” — possible miss by the grader

## Coverage

Messages with at least one claim: 5 of 7. Claims: 29 total, 29 checkable, 0 excluded as not checkable.
Graders: claude-opus-5 (chunk 1). Second judge: jev-1.13.0 on 29 claims, 22 requests, ~$0.0053.
