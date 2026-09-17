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
        "| Run | Harness | Turns | Attempted | Halluc. rate | Contradicted | Unsupported | Index | Grounding | Band | Jev κ | Notes |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    per_harness: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    per_type: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    pooled_confusion: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    pooled = {"runs": 0, "misses": 0, "false_alarms": 0, "out_of_reach": 0, "models": set()}
    for folder, card in runs:
        name = folder.name
        m = card["metrics"]
        harness = card.get("coverage", {}).get("harness") or "claude"
        lo, hi = card["turn_range"]
        notes_file = folder / "notes.txt"
        note = (notes_file.read_text().strip() if notes_file.is_file() else "").replace("|", "/")
        sj = card.get("second_judge")
        kappa_cell = kap(sj["packet_checkable"]["hallucination_kappa"]) if sj else "—"
        lines.append(
            f"| [{name}]({name}/scorecard.md) | {harness} | {lo}–{hi} | {m['attempted']} | {pct(m['hallucination_rate'])} | {m['contradicted']} | {m['unsupported']} | {signed(m['omniscience_index'])} | {pct(m['grounding_rate'])} | {m['band']} | {kappa_cell} | {note} |"
        )
        if sj:
            pooled["runs"] += 1
            pooled["misses"] += len(sj["possible_misses"])
            pooled["false_alarms"] += len(sj["possible_false_alarms"])
            pooled["out_of_reach"] += sj["claims_out_of_reach"]
            pooled["models"].add(sj["model"])
            for g, row in sj["packet_checkable"]["confusion"].items():
                for j, n in row.items():
                    pooled_confusion[g][j] += n
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
    ]

    if pooled["runs"]:
        labels = ("supported", "contradicted", "unsupported")
        n = sum(pooled_confusion[g][j] for g in labels for j in labels)
        agree = sum(pooled_confusion[g][g] for g in labels)
        halluc = lambda k: k != "supported"  # noqa: E731
        agree_bin = sum(pooled_confusion[g][j] for g in labels for j in labels if halluc(g) == halluc(j))
        lines += [
            "",
            f"## Second judge ({', '.join(sorted(pooled['models']))}) — agreement with the grader",
            "",
            f"Pooled over the {pooled['runs']} runs with a second judge, packet-checkable claims only (reference inside the session evidence; {pooled['out_of_reach']} checkable claims were out of Jev's reach).",
            "",
            "| | Claims | Label agreement | κ | Hallucination agreement | κ |",
            "|---|---|---|---|---|---|",
            f"| Pooled | {n} | {pct(agree / n if n else None)} | {kap(kappa_from_confusion(pooled_confusion, labels))} | {pct(agree_bin / n if n else None)} | {kap(kappa_from_confusion(binarise(pooled_confusion, labels), ('ok', 'wrong')))} |",
            "",
            "| grader \\ Jev | supported | contradicted | unsupported |",
            "|---|---|---|---|",
        ]
        for g in labels:
            lines.append(f"| {g} | " + " | ".join(str(pooled_confusion[g][j]) for j in labels) + " |")
        lines += [
            "",
            f"Confident disagreements across the runs: {pooled['misses']} possible misses by the grader (grader `supported`, Jev `contradicted` or `unsupported` with the evidence in hand) and {pooled['false_alarms']} possible false alarms (grader hallucinated, Jev `supported`). Each run's `scorecard.md` lists them. Two judges agreeing can both be wrong; κ bounds label noise, it does not certify the labels.",
            "",
            "Read with care: a manual check of ten of the highest-confidence \"possible misses\" found seven to be the second judge's errors (the evidence stated the claim outright), two to be claims the grader settled with a live repository check the second judge cannot make, and one a claim about text the user pasted. Whole-turn states (`--mode turn`) scored κ 0.08–0.10 on the same claims. A κ column of 0.00 means the grader found no hallucination in that run, so κ is undefined and reported as zero.",
        ]

    lines.append("")
    (ROOT / "README.md").write_text("\n".join(lines))
    print(f"indexed {len(runs)} runs")


def kappa_from_confusion(confusion: dict, labels: tuple) -> float | None:
    n = sum(confusion[g][j] for g in labels for j in labels)
    if n == 0:
        return None
    po = sum(confusion[g][g] for g in labels) / n
    pe = sum((sum(confusion[g][j] for j in labels) / n) * (sum(confusion[h][g] for h in labels) / n) for g in labels)
    return None if pe >= 1.0 else round((po - pe) / (1 - pe), 3)


def binarise(confusion: dict, labels: tuple) -> dict:
    """Collapse the 3×3 matrix to hallucinated-or-not for the binary κ."""
    out: dict[str, dict[str, int]] = {"ok": defaultdict(int), "wrong": defaultdict(int)}
    for g in labels:
        for j in labels:
            out["ok" if g == "supported" else "wrong"]["ok" if j == "supported" else "wrong"] += confusion[g][j]
    return out


def kap(v: float | None) -> str:
    return "n/a" if v is None else f"{v:.2f}"


def pct(v: float | None) -> str:
    return "n/a" if v is None else f"{100 * v:.1f}%"


def signed(v: float | None) -> str:
    return "n/a" if v is None else f"{v:+.1f}"


if __name__ == "__main__":
    main()
