# Hallucination scorecard — prime session 01a0a2fb (turns 1–7)

**Band: good** — hallucination rate 2.1% over 47 asserted, checkable claims.

| Metric | Value | Benchmark analogue |
|---|---|---|
| Hallucination rate (wrong ÷ attempted) | 2.1% (1/47) | SimpleQA incorrect-given-attempted; HalluLens hallucinated-when-not-refused |
| ├ Contradiction rate (intrinsic) | 2.1% (1) | RAGTruth evident/subtle conflict |
| └ Baseless rate (extrinsic) | 0.0% (0) | RAGTruth baseless info; FActScore/SAFE not-supported |
| Omniscience index | +95.7 | AA-Omniscience: +1 correct, 0 abstain, −1 wrong, over 47 checkable |
| Accuracy (correct ÷ checkable) | 97.9% | SimpleQA overall-correct |
| Abstention rate | 0.0% (0) | SimpleQA not-attempted; HalluLens refusal |
| Severity-weighted hallucination rate | 3.6% | house: action/verification/entity ×3, tool_output/code/completion ×2, external/history ×1 |
| Grounding rate (asserted with evidence in hand) | 89.4% | house: how often the claim was made after observing it, not recalled |

## By claim type

| Type | Attempted | Supported | Contradicted | Unsupported | Halluc. rate |
|---|---|---|---|---|---|
| action | 3 | 3 | 0 | 0 | 0.0% |
| verification | 4 | 4 | 0 | 0 | 0.0% |
| entity | 5 | 4 | 1 | 0 | 20.0% |
| tool_output | 8 | 8 | 0 | 0 | 0.0% |
| code_behaviour | 4 | 4 | 0 | 0 | 0.0% |
| external | 23 | 23 | 0 | 0 | 0.0% |

## Drift across the session

| Segment | Turns | Attempted | Halluc. rate |
|---|---|---|---|
| early | 1–2 | 18 | 0.0% |
| middle | 3–5 | 13 | 7.7% |
| late | 6–7 | 16 | 0.0% |

## Hallucinated claims (most severe first)

1. `t5-m2-c3` **entity** · contradicted — “`dsh` does not expose those CLI options yet”
   - claim: The dsh CLI exposes no resume or fork options.
   - check: t2 evidence #9 (`dsh --help`) lists the example "dsh --profile tui --resume <session>", i.e. dsh does expose a --resume option for the tui profile. Only the headless profile's help (t5 #9) lacks it; no fork option was found anywhere

## Hedge calibration

No hedged claims.

## Coverage

Messages with at least one claim: 11 of 13. Claims: 48 total, 47 checkable, 1 excluded as not checkable.
Graders: claude-opus-5 (chunk 1).
