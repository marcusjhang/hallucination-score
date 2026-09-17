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
   - second judge: Jev unsupported (0.52) — disagrees

## Hedge calibration

2 hedged claims: 0 turned out wrong (hedge warranted), 2 were right (over-hedged).

## Second judge — jev-1.13.0 (TypeSafe, different model family)

| Comparison set | Claims | Label agreement | κ | Hallucination agreement | κ |
|---|---|---|---|---|---|
| Packet-checkable (reference in the session evidence) | 57 | 77.2% | 0.05 | 79.0% | 0.11 |
| All checkable claims both judges labelled | 58 | 75.9% | 0.05 | 77.6% | 0.10 |

Grader × second judge, packet-checkable: grader supported → supported 44, contradicted 3, unsupported 9; grader contradicted → unsupported 1. 0 checkable claims were out of the second judge's reach (no evidence in the packet).

Spot-check first (the two judges disagree, second judge confident):

- `t2-m2-c7` **external** grader supported, Jev unsupported (0.98) — “whose test agent defaults to a Gemini model” — possible miss by the grader
- `t2-m2-c8` **external** grader supported, Jev unsupported (0.97) — “That inspector is separate from Gemini in Chrome.” — possible miss by the grader
- `t2-m2-c6` **external** grader supported, Jev unsupported (0.92) — “Right now the clearest testing setup is Chrome’s experimental WebMCP support and its inspector extension” — possible miss by the grader
- `t1-m3-c30` **entity** grader supported, Jev contradicted (0.71) — “/app/src/lib/components/guidance/GuidanceLightsHost.svelte:17” — possible miss by the grader
- `t2-m2-c12` **code_behaviour** grader supported, Jev unsupported (0.69) — “Server-side Claude cannot directly see `document.modelContext` inside the user’s tab.” — possible miss by the grader
- `t2-m2-c1` **external** grader supported, Jev unsupported (0.64) — “WebMCP is not “on Claude.”” — possible miss by the grader
- `t1-m3-c34` **code_behaviour** grader supported, Jev unsupported (0.62) — “Unless Ask itself becomes that browser agent—or you add a bridge—it cannot call them.” — possible miss by the grader
- `t1-m3-c31` **external** grader supported, Jev contradicted (0.60) — “WebMCP is primarily an actuation interface.” — possible miss by the grader

## Coverage

Messages with at least one claim: 4 of 5. Claims: 58 total, 58 checkable, 0 excluded as not checkable.
Graders: claude-opus-5 (chunk 1). Second judge: jev-1.13.0 on 58 claims, 29 requests, ~$0.0175.
