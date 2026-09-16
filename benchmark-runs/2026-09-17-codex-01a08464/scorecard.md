# Hallucination scorecard — codex session 01a08464 (turns 1–2)

**Band: watch** — hallucination rate 5.1% over 39 asserted, checkable claims.

| Metric | Value | Benchmark analogue |
|---|---|---|
| Hallucination rate (wrong ÷ attempted) | 5.1% (2/39) | SimpleQA incorrect-given-attempted; HalluLens hallucinated-when-not-refused |
| ├ Contradiction rate (intrinsic) | 5.1% (2) | RAGTruth evident/subtle conflict |
| └ Baseless rate (extrinsic) | 0.0% (0) | RAGTruth baseless info; FActScore/SAFE not-supported |
| Omniscience index | +83.3 | AA-Omniscience: +1 correct, 0 abstain, −1 wrong, over 42 checkable |
| Accuracy (correct ÷ checkable) | 88.1% | SimpleQA overall-correct |
| Abstention rate | 7.1% (3) | SimpleQA not-attempted; HalluLens refusal |
| Severity-weighted hallucination rate | 4.7% | house: action/verification/entity ×3, tool_output/code/completion ×2, external/history ×1 |
| Grounding rate (asserted with evidence in hand) | 89.7% | house: how often the claim was made after observing it, not recalled |

## By claim type

| Type | Attempted | Supported | Contradicted | Unsupported | Halluc. rate |
|---|---|---|---|---|---|
| action | 4 | 4 | 0 | 0 | 0.0% |
| verification | 2 | 2 | 0 | 0 | 0.0% |
| entity | 4 | 4 | 0 | 0 | 0.0% |
| tool_output | 18 | 18 | 0 | 0 | 0.0% |
| code_behaviour | 9 | 7 | 2 | 0 | 22.2% |
| external | 2 | 2 | 0 | 0 | 0.0% |

## Hallucinated claims (most severe first)

1. `t1-m3-c2` **code_behaviour** · contradicted — “The first check shows this is Superset’s bundled Codex binary”
   - claim: The file at /Users/marcusjhang/.superset/bin/codex is a Codex binary that Superset bundles.
   - check: t1 #2 (seen) shows a 6813-byte file, far too small to be the Codex binary; t1 #7 shows it is a bash script (`# Superset agent-wrapper v3`) whose find_real_binary() searches PATH for a non-Superset `codex` and exits 127 with 'codex not found in PATH. Install it' when none exists, i.e. Superset does not bundle Codex. Live: `grep -n REAL_BIN /Users/marcusjhang/.superset/bin/codex` line 215 execs the found binary. The assistant itself reverses this in t1-m5/t1-m7 ('Superset's wrapper ... forwards to the real Codex binary').
2. `t1-m6-c3` **code_behaviour** · contradicted — “the practical path is Homebrew cask install/upgrade because the binary is under `/opt/homebrew/bin`”
   - claim: The codex at /opt/homebrew/bin/codex is a Homebrew-cask-managed install, so `brew install`/`brew upgrade` of the cask is the way to update it.
   - check: t1 #8 (seen before this message) `brew info codex` -> 'Not installed'; t1 #13 `ls -l /opt/homebrew/bin/codex` -> symlink to ../lib/node_modules/@openai/codex/bin/codex.js and t1 #14 reads its package.json, i.e. an npm global install under the Homebrew prefix, not a cask. The assistant drops the cask route in t1-m7 and recommends `codex update` / `npm install --prefix /opt/homebrew` instead. Live: `ls -l /opt/homebrew/bin/codex` still a symlink into node_modules.

## Hedge calibration

3 hedged claims: 0 turned out wrong (hedge warranted), 3 were right (over-hedged).

## Coverage

Messages with at least one claim: 12 of 14. Claims: 43 total, 42 checkable, 1 excluded as not checkable.
Graders: claude-opus-5 (chunk 1).
