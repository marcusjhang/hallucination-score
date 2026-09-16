# Hallucination scorecard — codex session 01a08fb9 (turns 1–2)

**Band: excellent** — hallucination rate 1.8% over 56 asserted, checkable claims.

| Metric | Value | Benchmark analogue |
|---|---|---|
| Hallucination rate (wrong ÷ attempted) | 1.8% (1/56) | SimpleQA incorrect-given-attempted; HalluLens hallucinated-when-not-refused |
| ├ Contradiction rate (intrinsic) | 1.8% (1) | RAGTruth evident/subtle conflict |
| └ Baseless rate (extrinsic) | 0.0% (0) | RAGTruth baseless info; FActScore/SAFE not-supported |
| Omniscience index | +93.1 | AA-Omniscience: +1 correct, 0 abstain, −1 wrong, over 58 checkable |
| Accuracy (correct ÷ checkable) | 94.8% | SimpleQA overall-correct |
| Abstention rate | 3.5% (2) | SimpleQA not-attempted; HalluLens refusal |
| Severity-weighted hallucination rate | 1.1% | house: action/verification/entity ×3, tool_output/code/completion ×2, external/history ×1 |
| Grounding rate (asserted with evidence in hand) | 96.4% | house: how often the claim was made after observing it, not recalled |

## By claim type

| Type | Attempted | Supported | Contradicted | Unsupported | Halluc. rate |
|---|---|---|---|---|---|
| action | 1 | 1 | 0 | 0 | 0.0% |
| entity | 6 | 6 | 0 | 0 | 0.0% |
| tool_output | 1 | 1 | 0 | 0 | 0.0% |
| code_behaviour | 18 | 18 | 0 | 0 | 0.0% |
| external | 30 | 29 | 1 | 0 | 3.3% |

## Hallucinated claims (most severe first)

1. `t1-m3-c37` **external** · contradicted — “[Chrome’s security guidance](https://developer.chrome.com/docs/ai/webmcp/secure-tools) also stresses server-side authorization”
   - claim: Chrome's WebMCP tool-security page (docs/ai/webmcp/secure-tools) stresses server-side authorization.
   - check: t1 evidence #4's secure-tools excerpt contains no server/authorization guidance; live: curl -sL https://developer.chrome.com/docs/ai/webmcp/secure-tools?hl=en (2026-09-17) stripped to text has 0 occurrences of 'server', 'backend', 'authoriz', 'authenticat' or 'validate' — the page covers annotation hints, exposedTo origin scoping and prompt injection only; sibling pages docs/agents/security and docs/ai/webmcp/best-practices also have 0 'server-side'/'backend' mentions

## Hedge calibration

2 hedged claims: 0 turned out wrong (hedge warranted), 2 were right (over-hedged).

## Coverage

Messages with at least one claim: 4 of 5. Claims: 58 total, 58 checkable, 0 excluded as not checkable.
Graders: claude-opus-5 (chunk 1).
