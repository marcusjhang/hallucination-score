# Hallucination scorecard — prime session 01a09df0 (turns 1–7)

**Band: excellent** — hallucination rate 1.2% over 80 asserted, checkable claims.

| Metric | Value | Benchmark analogue |
|---|---|---|
| Hallucination rate (wrong ÷ attempted) | 1.2% (1/80) | SimpleQA incorrect-given-attempted; HalluLens hallucinated-when-not-refused |
| ├ Contradiction rate (intrinsic) | 1.2% (1) | RAGTruth evident/subtle conflict |
| └ Baseless rate (extrinsic) | 0.0% (0) | RAGTruth baseless info; FActScore/SAFE not-supported |
| Omniscience index | +94.0 | AA-Omniscience: +1 correct, 0 abstain, −1 wrong, over 83 checkable |
| Accuracy (correct ÷ checkable) | 95.2% | SimpleQA overall-correct |
| Abstention rate | 3.6% (3) | SimpleQA not-attempted; HalluLens refusal |
| Severity-weighted hallucination rate | 1.2% | house: action/verification/entity ×3, tool_output/code/completion ×2, external/history ×1 |
| Grounding rate (asserted with evidence in hand) | 97.5% | house: how often the claim was made after observing it, not recalled |

## By claim type

| Type | Attempted | Supported | Contradicted | Unsupported | Halluc. rate |
|---|---|---|---|---|---|
| action | 14 | 14 | 0 | 0 | 0.0% |
| verification | 10 | 10 | 0 | 0 | 0.0% |
| entity | 1 | 1 | 0 | 0 | 0.0% |
| tool_output | 33 | 33 | 0 | 0 | 0.0% |
| code_behaviour | 9 | 8 | 1 | 0 | 11.1% |
| external | 13 | 13 | 0 | 0 | 0.0% |

## Drift across the session

| Segment | Turns | Attempted | Halluc. rate |
|---|---|---|---|
| early | 1–2 | 42 | 0.0% |
| middle | 3–4 | 12 | 0.0% |
| late | 6–7 | 26 | 3.9% |

## Hallucinated claims (most severe first)

1. `t6-m3-c14` **code_behaviour** · contradicted — “because this account has no other login method”
   - claim: The app refuses to unlink GitHub because this particular account has no other login method.
   - check: t6 evidence #5: the endpoint refuses GitHub unconditionally — 'GitHub is permanently not unlinkable. The GitHub OAuth token on the user row is what backs every repository capability … Google is the only provider a user may disconnect' — the refusal does not depend on the account having another login method
   - second judge: Jev contradicted (0.85) — agrees

## Hedge calibration

3 hedged claims: 0 turned out wrong (hedge warranted), 3 were right (over-hedged).

## Second judge — jev-1.13.0 (TypeSafe, different model family)

| Comparison set | Claims | Label agreement | κ | Hallucination agreement | κ |
|---|---|---|---|---|---|
| Packet-checkable (reference in the session evidence) | 83 | 90.4% | 0.19 | 90.4% | 0.18 |
| All checkable claims both judges labelled | 83 | 90.4% | 0.19 | 90.4% | 0.18 |

Grader × second judge, packet-checkable: grader supported → supported 74, unsupported 8; grader contradicted → contradicted 1. 0 checkable claims were out of the second judge's reach (no evidence in the packet).

Spot-check first (the two judges disagree, second judge confident):

- `t1-m3-c4` **external** grader supported, Jev unsupported (0.98) — “`railway variable list` shows values” — possible miss by the grader
- `t2-m3-c24` **tool_output** grader supported, Jev unsupported (0.95) — “`railway config migrate` converts it to `.railway/railway.ts`” — possible miss by the grader
- `t2-m3-c18` **external** grader supported, Jev unsupported (0.86) — “`railway shell` also works — it drops you into a subshell where `$DATABASE_URL` is already set” — possible miss by the grader
- `t1-m3-c3` **external** grader supported, Jev unsupported (0.61) — “`railway connect` opens a `psql` shell against the linked database” — possible miss by the grader

## Coverage

Messages with at least one claim: 13 of 19. Claims: 85 total, 83 checkable, 2 excluded as not checkable.
Graders: claude-opus-5 (chunk 1). Second judge: jev-1.13.0 on 83 claims, 81 requests, ~$0.0203.
