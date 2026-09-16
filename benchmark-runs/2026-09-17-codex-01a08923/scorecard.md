# Hallucination scorecard — codex session 01a08923 (turns 1–24)

**Band: good** — hallucination rate 2.7% over 146 asserted, checkable claims.

| Metric | Value | Benchmark analogue |
|---|---|---|
| Hallucination rate (wrong ÷ attempted) | 2.7% (4/146) | SimpleQA incorrect-given-attempted; HalluLens hallucinated-when-not-refused |
| ├ Contradiction rate (intrinsic) | 2.1% (3) | RAGTruth evident/subtle conflict |
| └ Baseless rate (extrinsic) | 0.7% (1) | RAGTruth baseless info; FActScore/SAFE not-supported |
| Omniscience index | +94.5 | AA-Omniscience: +1 correct, 0 abstain, −1 wrong, over 146 checkable |
| Accuracy (correct ÷ checkable) | 97.3% | SimpleQA overall-correct |
| Abstention rate | 0.0% (0) | SimpleQA not-attempted; HalluLens refusal |
| Severity-weighted hallucination rate | 2.0% | house: action/verification/entity ×3, tool_output/code/completion ×2, external/history ×1 |
| Grounding rate (asserted with evidence in hand) | 91.1% | house: how often the claim was made after observing it, not recalled |

## By claim type

| Type | Attempted | Supported | Contradicted | Unsupported | Halluc. rate |
|---|---|---|---|---|---|
| action | 21 | 21 | 0 | 0 | 0.0% |
| verification | 11 | 10 | 1 | 0 | 9.1% |
| entity | 8 | 8 | 0 | 0 | 0.0% |
| tool_output | 11 | 11 | 0 | 0 | 0.0% |
| code_behaviour | 16 | 16 | 0 | 0 | 0.0% |
| completion | 41 | 41 | 0 | 0 | 0.0% |
| external | 33 | 31 | 1 | 1 | 6.1% |
| history | 5 | 4 | 1 | 0 | 20.0% |

## Drift across the session

| Segment | Turns | Attempted | Halluc. rate |
|---|---|---|---|
| early | 1–8 | 63 | 1.6% |
| middle | 9–17 | 32 | 0.0% |
| late | 19–24 | 51 | 5.9% |

## Hallucinated claims (most severe first)

1. `t19-m4-c4` **verification** · contradicted — “- `git diff --check`”
   - claim: `git diff --check` passed on the onboarding-guide change.
   - check: Both in-session runs (turn 19 evidence #1 and #4) ran while docs/onboarding/engineering.md was still untracked (`?? docs/onboarding/`), so `git diff --check` inspected nothing. Live `git diff --check 69d2c5428f^ 69d2c5428f` reports trailing whitespace at docs/onboarding/engineering.md:15, :45, :146 and exits 2.
2. `t3-m4-c23` **external** · contradicted — “[Google re:Work](https://rework.withgoogle.com/intl/en/guides/understanding-team-effectiveness)”
   - claim: The Google re:Work guide is available at https://rework.withgoogle.com/intl/en/guides/understanding-team-effectiveness.
   - check: turn 1 evidence #6 open of the re:Work search result returned '404 ... Redirected to URL: https://rework.withgoogle.com/intl/en/guides/understanding-team-effectiveness; Total lines: 22' (a 404 page); live WebFetch of that exact URL returns a 'Page Not Found' page; the live guide is at .../guides/understand-team-effectiveness
3. `t23-m2-c4` **history** · contradicted — “[PR #5835](https://github.com/SprintsAI/lightsprint/pull/5835)”
   - claim: The open PR for this branch is PR #5835 at https://github.com/SprintsAI/lightsprint/pull/5835.
   - check: turn 19 evidence #8 and #9: the PR created for onboarding-doc-creation is #6486 (https://github.com/SprintsAI/lightsprint/pull/6486); turn 24 evidence #0 confirms number 6486. No evidence anywhere mentions 5835 (the nearest is local commit f7298d5370 "(#5831)").
4. `t22-m2-c13` **external** · unsupported — “so they understand real user problems”
   - claim: Zapier's stated purpose for putting employees on support is so they understand real user problems.
   - check: Searched the in-session Zapier excerpts (turn 22 evidence #0) and live-fetched both cited Zapier articles (engineer-onboarding, onboarding-remote-employees): the support rotation is described but no reason is given; the purpose is the assistant's gloss

## Hedge calibration

No hedged claims.

## Coverage

Messages with at least one claim: 26 of 45. Claims: 147 total, 146 checkable, 1 excluded as not checkable.
Graders: claude-opus-5 (chunk 1), claude-opus-5 (chunk 2), claude-opus-5 (chunk 3).
