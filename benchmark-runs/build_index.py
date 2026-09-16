#!/usr/bin/env python3
"""Rebuild benchmark-runs/README.md from the scorecard.json files in each run folder.

    python3 benchmark-runs/build_index.py

A run folder is written by `score.py --export benchmark-runs/<date>-<harness>-<session8>`
and holds scorecard.md + scorecard.json, plus an optional one-line notes.txt. This script only reads them: the table, the
per-harness aggregate and the per-type aggregate are all recomputed from the claims, so
the README can never drift from the runs.
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TYPES = ("action", "verification", "entity", "tool_output", "code_behaviour", "completion", "external", "history")


def main() -> None:
    runs = []
    for card_path in sorted(ROOT.glob("*/scorecard.json")):
        card = json.loads(card_path.read_text())
        runs.append((card_path.parent, card))
    if not runs:
        raise SystemExit("no runs found")

    lines = [
        "# Benchmark runs",
        "",
        "Real sessions scored with the skill, one folder per run: `scorecard.md` is what the user sees, `scorecard.json` adds every claim with its label and check so the grading can be audited. Rebuild this file with `python3 benchmark-runs/build_index.py`.",
        "",
        "Bands: hallucination rate < 2% excellent · < 5% good · < 10% watch · < 20% poor · else failing (house thresholds for grounded coding sessions; see `reference/methodology.md`).",
        "",
        "| Run | Harness | Turns | Attempted | Halluc. rate | Contradicted | Unsupported | Index | Grounding | Band | Notes |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    per_harness: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    per_type: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for folder, card in runs:
        name = folder.name
        m = card["metrics"]
        harness = card.get("coverage", {}).get("harness") or "claude"
        lo, hi = card["turn_range"]
        notes_file = folder / "notes.txt"
        note = (notes_file.read_text().strip() if notes_file.is_file() else "").replace("|", "/")
        lines.append(
            f"| [{name}]({name}/scorecard.md) | {harness} | {lo}–{hi} | {m['attempted']} | {pct(m['hallucination_rate'])} | {m['contradicted']} | {m['unsupported']} | {signed(m['omniscience_index'])} | {pct(m['grounding_rate'])} | {m['band']} | {note} |"
        )
        agg = per_harness[harness]
        agg["runs"] += 1
        for key in ("attempted", "supported", "contradicted", "unsupported", "abstained", "claims_checkable"):
            agg[key] += m[key]
        for claim in card.get("claims", []):
            if claim["label"] == "not_checkable" or claim["strength"] != "asserted":
                continue
            t = per_type[claim["type"]]
            t["attempted"] += 1
            if claim["label"] != "supported":
                t["wrong"] += 1

    lines += ["", "## By harness", "", "| Harness | Runs | Attempted | Halluc. rate | Contradicted | Unsupported | Index |", "|---|---|---|---|---|---|---|"]
    for harness, agg in sorted(per_harness.items()):
        wrong = agg["contradicted"] + agg["unsupported"]
        rate = wrong / agg["attempted"] if agg["attempted"] else None
        index = 100 * (agg["supported"] - wrong) / agg["claims_checkable"] if agg["claims_checkable"] else None
        lines.append(f"| {harness} | {agg['runs']} | {agg['attempted']} | {pct(rate)} | {agg['contradicted']} | {agg['unsupported']} | {signed(index)} |")

    lines += ["", "## By claim type (all runs)", "", "| Type | Attempted | Wrong | Halluc. rate |", "|---|---|---|---|"]
    for t in TYPES:
        agg = per_type.get(t)
        if not agg:
            continue
        lines.append(f"| {t} | {agg['attempted']} | {agg['wrong']} | {pct(agg['wrong'] / agg['attempted'])} |")

    lines += [
        "",
        "Pooled rates weight every claim equally, so a long session dominates; read them as a hint of which claim types fail most, not as a harness ranking. The Claude runs are judged by the same model family that produced them (self-preference bias, rate is a floor); the Codex, Prime and OpenCode runs are judged by a different family, which is the benchmark-faithful configuration.",
        "",
    ]
    (ROOT / "README.md").write_text("\n".join(lines))
    print(f"indexed {len(runs)} runs")


def pct(v: float | None) -> str:
    return "n/a" if v is None else f"{100 * v:.1f}%"


def signed(v: float | None) -> str:
    return "n/a" if v is None else f"{v:+.1f}"


if __name__ == "__main__":
    main()
