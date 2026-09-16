# Hallucination scorecard — prime session 01a0a0a4 (turns 1–1)

**Band: excellent** — hallucination rate 0.0% over 45 asserted, checkable claims.

| Metric | Value | Benchmark analogue |
|---|---|---|
| Hallucination rate (wrong ÷ attempted) | 0.0% (0/45) | SimpleQA incorrect-given-attempted; HalluLens hallucinated-when-not-refused |
| ├ Contradiction rate (intrinsic) | 0.0% (0) | RAGTruth evident/subtle conflict |
| └ Baseless rate (extrinsic) | 0.0% (0) | RAGTruth baseless info; FActScore/SAFE not-supported |
| Omniscience index | +100.0 | AA-Omniscience: +1 correct, 0 abstain, −1 wrong, over 45 checkable |
| Accuracy (correct ÷ checkable) | 100.0% | SimpleQA overall-correct |
| Abstention rate | 0.0% (0) | SimpleQA not-attempted; HalluLens refusal |
| Severity-weighted hallucination rate | 0.0% | house: action/verification/entity ×3, tool_output/code/completion ×2, external/history ×1 |
| Grounding rate (asserted with evidence in hand) | 100.0% | house: how often the claim was made after observing it, not recalled |

## By claim type

| Type | Attempted | Supported | Contradicted | Unsupported | Halluc. rate |
|---|---|---|---|---|---|
| action | 12 | 12 | 0 | 0 | 0.0% |
| verification | 6 | 6 | 0 | 0 | 0.0% |
| entity | 5 | 5 | 0 | 0 | 0.0% |
| tool_output | 15 | 15 | 0 | 0 | 0.0% |
| code_behaviour | 2 | 2 | 0 | 0 | 0.0% |
| completion | 4 | 4 | 0 | 0 | 0.0% |
| history | 1 | 1 | 0 | 0 | 0.0% |

## Hallucinated claims (most severe first)

None.

## Hedge calibration

No hedged claims.

## Coverage

Messages with at least one claim: 14 of 15. Claims: 45 total, 45 checkable, 0 excluded as not checkable.
Graders: claude-opus-5 (chunk 1).
