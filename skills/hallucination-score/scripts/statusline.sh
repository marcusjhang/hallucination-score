#!/usr/bin/env bash
# Statusline snippet for the hallucination-score skill.
#
# Claude Code pipes a JSON object to the statusline command; we read session_id
# from it and print the latest persisted scorecard line for that session, e.g.
#   halluc 4.2% · idx +71 · n=48 · good
# Prints nothing when the session has not been scored yet, so it composes with
# other statusline output.
set -euo pipefail

scores_dir="${HOME}/.claude/hallucination-scores"
input="$(cat)"
session_id="$(printf '%s' "$input" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("session_id",""))' 2>/dev/null || true)"
[ -n "$session_id" ] || exit 0
card="${scores_dir}/${session_id}.json"
[ -f "$card" ] || exit 0

python3 - "$card" <<'EOF'
import json, sys
m = json.load(open(sys.argv[1]))["metrics"]
rate = m["hallucination_rate"]
if rate is None:
    print("halluc n/a")
else:
    print(f"halluc {100 * rate:.1f}% · idx {m['omniscience_index']:+.0f} · n={m['attempted']} · {m['band']}")
EOF
