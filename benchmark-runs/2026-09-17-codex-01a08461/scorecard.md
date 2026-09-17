# Hallucination scorecard — codex session 01a08461 (turns 1–1)

**Band: excellent** — hallucination rate 0.0% over 49 asserted, checkable claims.

| Metric | Value | Benchmark analogue |
|---|---|---|
| Hallucination rate (wrong ÷ attempted) | 0.0% (0/49) | SimpleQA incorrect-given-attempted; HalluLens hallucinated-when-not-refused |
| ├ Contradiction rate (intrinsic) | 0.0% (0) | RAGTruth evident/subtle conflict |
| └ Baseless rate (extrinsic) | 0.0% (0) | RAGTruth baseless info; FActScore/SAFE not-supported |
| Omniscience index | +98.0 | AA-Omniscience: +1 correct, 0 abstain, −1 wrong, over 50 checkable |
| Accuracy (correct ÷ checkable) | 98.0% | SimpleQA overall-correct |
| Abstention rate | 2.0% (1) | SimpleQA not-attempted; HalluLens refusal |
| Severity-weighted hallucination rate | 0.0% | house: action/verification/entity ×3, tool_output/code/completion ×2, external/history ×1 |
| Grounding rate (asserted with evidence in hand) | 100.0% | house: how often the claim was made after observing it, not recalled |

## By claim type

| Type | Attempted | Supported | Contradicted | Unsupported | Halluc. rate |
|---|---|---|---|---|---|
| entity | 16 | 16 | 0 | 0 | 0.0% |
| tool_output | 6 | 6 | 0 | 0 | 0.0% |
| code_behaviour | 27 | 27 | 0 | 0 | 0.0% |

## Hallucinated claims (most severe first)

None.

## Hedge calibration

1 hedged claims: 0 turned out wrong (hedge warranted), 1 were right (over-hedged).

## Second judge — jev-1.13.0 (TypeSafe, different model family)

| Comparison set | Claims | Label agreement | κ | Hallucination agreement | κ |
|---|---|---|---|---|---|
| Packet-checkable (reference in the session evidence) | 48 | 97.9% | 0.00 | 97.9% | 0.00 |
| All checkable claims both judges labelled | 50 | 98.0% | 0.00 | 98.0% | 0.00 |

Grader × second judge, packet-checkable: grader supported → supported 47, contradicted 1. 0 checkable claims were out of the second judge's reach (no evidence in the packet).

Spot-check first (the two judges disagree, second judge confident):

- `t1-m5-c26` **tool_output** grader supported, Jev contradicted (0.50) — “package.json:46” — possible miss by the grader

## Coverage

Messages with at least one claim: 4 of 5. Claims: 51 total, 50 checkable, 1 excluded as not checkable.
Graders: claude-opus-5 (chunk 1). Second judge: jev-1.13.0 on 50 claims, 49 requests, ~$0.0319.
