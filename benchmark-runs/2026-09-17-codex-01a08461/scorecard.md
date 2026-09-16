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

## Coverage

Messages with at least one claim: 4 of 5. Claims: 51 total, 50 checkable, 1 excluded as not checkable.
Graders: claude-opus-5 (chunk 1).
