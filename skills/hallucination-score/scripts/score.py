#!/usr/bin/env python3
"""Phase 3 of the hallucination-score skill: deterministic scoring of grader verdicts.

    python3 <skill dir>/scripts/score.py <verdicts-*.json ...> \
        [--packets-dir DIR] [--jev jev-*.json ...] [--json] [--no-persist]
    python3 <skill dir>/scripts/score.py --history [N]
    python3 <skill dir>/scripts/score.py <verdicts...> --export benchmark-runs/<name>

Takes the claim-level verdicts the grader agents wrote, validates them against the
closed label set, and computes the session scorecard exactly the way the published
benchmarks compute theirs. Nothing here is estimated: every number is a count over
the verdict files, so two runs over the same verdicts print the same card.

Per-claim score, following AA-Omniscience / SimpleQA:
  asserted + supported            → +1   (correct)
  asserted + contradicted         → −1   (intrinsic hallucination: conflicts with evidence)
  asserted + unsupported          → −1   (extrinsic hallucination: baseless, could not be verified)
  hedged or abstained             →  0   (not attempted; abstention is neutral, never rewarded)
  not_checkable                   → excluded (SAFE's relevance filter: opinions, plans, questions)

With ``--jev`` (the files written by ``jev_second_judge.py``) every claim also carries the
second judge's label, and the card gains a judge-vs-judge agreement block (Cohen's κ) plus the
disagreements to spot-check. The headline numbers never change: the second judge is a check
on the grader, not a replacement for it.

Persists ``~/.claude/hallucination-scores/<session>.json`` and appends one line to
``history.jsonl`` so the score can be shown in a statusline or compared across sessions.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

SCORES_DIR = Path.home() / ".claude" / "hallucination-scores"

CLAIM_TYPES = {
    # type: (severity weight, benchmark analogue)
    "action": (3, "AgentHallu tool-use: 'I ran/edited/committed X' with no matching tool call"),
    "verification": (3, "CodeHalu execution validation: 'tests pass / typecheck clean / it works'"),
    "entity": (3, "HalluLens nonexistent-entity: file, symbol, API, package, flag or config key"),
    "tool_output": (2, "RAGTruth conflict: misreporting what a tool result actually said"),
    "code_behaviour": (2, "FActScore atomic fact about what the code does or why a bug happens"),
    "completion": (2, "AgentHallu planning: 'done / fixed / all cases handled' overclaim"),
    "external": (1, "SimpleQA world knowledge: library, API docs, protocol, vendor facts"),
    "history": (1, "attribution: git history, PRs, who/when"),
}
STRENGTHS = ("asserted", "hedged", "abstained")
LABELS = ("supported", "contradicted", "unsupported", "not_checkable")

# House thresholds for a grounded coding session, keyed on hallucination rate.
# Closest published comparable: grounded-summarisation faithfulness leaderboards, where
# frontier models sit in the low single digits. Recalibrate once you have a history.
BANDS = [(0.02, "excellent"), (0.05, "good"), (0.10, "watch"), (0.20, "poor"), (1.01, "failing")]


def main() -> None:
    args = parse_args()
    if args.history is not None:
        print_history(args.history or 10)
        return
    if not args.verdicts:
        fail("pass at least one verdict file, or --history")

    claims, meta = load_verdicts(args.verdicts)
    coverage = load_coverage(args.packets_dir, claims)
    jev_meta = join_second_judge(args.jev, claims, meta["session_id"]) if args.jev else None
    card = score(claims)
    card["session_id"] = meta["session_id"]
    card["turn_range"] = meta["turn_range"]
    card["graders"] = meta["graders"]
    card["coverage"] = coverage
    if jev_meta:
        card["second_judge"] = second_judge(claims, jev_meta)
    card["scored_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")

    if not args.no_persist:
        persist(card, claims)
    if args.export:
        export(Path(args.export), card, claims)
    print(json.dumps(card, indent=1) if args.json else render(card))


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("verdicts", nargs="*", help="verdict JSON files written by the grader agents")
    p.add_argument("--packets-dir", help="packets dir from extract_turns.py, for message coverage")
    p.add_argument("--jev", nargs="*", help="jev-*.json files from jev_second_judge.py; adds the judge-agreement block")
    p.add_argument("--json", action="store_true", help="print the scorecard as JSON instead of markdown")
    p.add_argument("--no-persist", action="store_true", help="do not write to ~/.claude/hallucination-scores")
    p.add_argument("--export", help="also write scorecard.md + scorecard.json into this directory (for a benchmark-runs folder)")
    p.add_argument("--history", nargs="?", type=int, const=10, help="print the last N scored sessions and exit")
    return p.parse_args()


def load_verdicts(paths: list[str]) -> tuple[list[dict], dict]:
    claims: list[dict] = []
    session_ids: set[str] = set()
    graders: list[dict] = []
    seen_ids: set[str] = set()
    for path in paths:
        doc = json.loads(Path(path).read_text())
        session_ids.add(doc.get("session_id") or "?")
        graders.append({"chunk": doc.get("chunk"), **(doc.get("grader") or {})})
        for claim in doc.get("claims", []):
            validate(claim, path)
            if claim["id"] in seen_ids:
                fail(f"{path}: duplicate claim id {claim['id']}")
            seen_ids.add(claim["id"])
            claims.append(claim)
    if len(session_ids) != 1:
        fail(f"verdict files span several sessions: {sorted(session_ids)}")
    turns = sorted({c["turn"] for c in claims}) or [0]
    return claims, {"session_id": session_ids.pop(), "turn_range": [turns[0], turns[-1]], "graders": graders}


def validate(claim: dict, path: str) -> None:
    cid = claim.get("id", "<no id>")
    for field in ("id", "turn", "message", "quote", "claim", "type", "strength", "label"):
        if field not in claim:
            fail(f"{path}: claim {cid} is missing '{field}'")
    if claim["type"] not in CLAIM_TYPES:
        fail(f"{path}: claim {cid} has unknown type '{claim['type']}' (allowed: {', '.join(CLAIM_TYPES)})")
    if claim["strength"] not in STRENGTHS:
        fail(f"{path}: claim {cid} has unknown strength '{claim['strength']}' (allowed: {', '.join(STRENGTHS)})")
    if claim["label"] not in LABELS:
        fail(f"{path}: claim {cid} has unknown label '{claim['label']}' (allowed: {', '.join(LABELS)})")
    if claim["label"] != "not_checkable" and not claim.get("check"):
        fail(f"{path}: claim {cid} is labelled {claim['label']} but records no 'check'")
    claim.setdefault("evidenced_in_session", False)


def load_coverage(packets_dir: str | None, claims: list[dict]) -> dict:
    graded = {c["message"] for c in claims}
    if not packets_dir:
        return {"messages_total": None, "messages_with_claims": len(graded)}
    index_path = Path(packets_dir) / "index.json"
    if not index_path.is_file():
        fail(f"no index.json in {packets_dir}")
    index = json.loads(index_path.read_text())
    return {
        "harness": index.get("harness", "claude"),
        "messages_total": index["assistant_messages"],
        "messages_paraphrased": index.get("paraphrased_messages", 0),
        "messages_with_claims": len(graded),
        "tool_calls": index["tool_calls"],
        "turns_selected": index["turns_selected"],
    }


def score(claims: list[dict]) -> dict:
    checkable = [c for c in claims if c["label"] != "not_checkable"]
    attempted = [c for c in checkable if c["strength"] == "asserted"]
    abstained = [c for c in checkable if c["strength"] != "asserted"]
    supported = [c for c in attempted if c["label"] == "supported"]
    contradicted = [c for c in attempted if c["label"] == "contradicted"]
    unsupported = [c for c in attempted if c["label"] == "unsupported"]
    wrong = contradicted + unsupported

    weight = lambda c: CLAIM_TYPES[c["type"]][0]  # noqa: E731
    hedged = [c for c in checkable if c["strength"] == "hedged"]
    hedged_wrong = [c for c in hedged if c["label"] in ("contradicted", "unsupported")]

    metrics = {
        "claims_total": len(claims),
        "claims_checkable": len(checkable),
        "attempted": len(attempted),
        "supported": len(supported),
        "contradicted": len(contradicted),
        "unsupported": len(unsupported),
        "abstained": len(abstained),
        "hallucination_rate": ratio(len(wrong), len(attempted)),
        "contradiction_rate": ratio(len(contradicted), len(attempted)),
        "baseless_rate": ratio(len(unsupported), len(attempted)),
        "omniscience_index": None if not checkable else round(100 * (len(supported) - len(wrong)) / len(checkable), 1),
        "accuracy": ratio(len(supported), len(checkable)),
        "abstention_rate": ratio(len(abstained), len(checkable)),
        "weighted_hallucination_rate": ratio(sum(map(weight, wrong)), sum(map(weight, attempted))),
        "grounding_rate": ratio(sum(1 for c in attempted if c["evidenced_in_session"]), len(attempted)),
        "hedge_calibration": {
            "hedged": len(hedged),
            "hedged_wrong": len(hedged_wrong),
            "hedged_supported": sum(1 for c in hedged if c["label"] == "supported"),
        },
    }
    metrics["band"] = band(metrics["hallucination_rate"])

    by_type = {}
    for name in CLAIM_TYPES:
        rows = [c for c in attempted if c["type"] == name]
        if not rows:
            continue
        bad = [c for c in rows if c["label"] != "supported"]
        by_type[name] = {
            "attempted": len(rows),
            "supported": len(rows) - len(bad),
            "contradicted": sum(1 for c in rows if c["label"] == "contradicted"),
            "unsupported": sum(1 for c in rows if c["label"] == "unsupported"),
            "hallucination_rate": ratio(len(bad), len(rows)),
        }

    return {
        "metrics": metrics,
        "by_type": by_type,
        "drift": drift(attempted),
        "hallucinations": sorted(
            (slim(c) for c in wrong),
            key=lambda c: (-CLAIM_TYPES[c["type"]][0], c["label"] != "contradicted", c["turn"]),
        ),
        "hedged_wrong": [slim(c) for c in hedged_wrong],
    }


def drift(attempted: list[dict]) -> list[dict]:
    """Hallucination rate by session third, so context-length degradation is visible."""
    turns = sorted({c["turn"] for c in attempted})
    if len(turns) < 3:
        return []
    cut = len(turns) // 3
    segments = [("early", turns[:cut]), ("middle", turns[cut : len(turns) - cut]), ("late", turns[len(turns) - cut :])]
    out = []
    for name, seg in segments:
        rows = [c for c in attempted if c["turn"] in seg]
        bad = sum(1 for c in rows if c["label"] != "supported")
        out.append({"segment": name, "turns": [seg[0], seg[-1]], "attempted": len(rows), "hallucination_rate": ratio(bad, len(rows))})
    return out


def slim(c: dict) -> dict:
    keys = ("id", "turn", "message", "type", "strength", "label", "quote", "claim", "check", "evidenced_in_session", "jev")
    return {k: c.get(k) for k in keys if k != "jev" or c.get("jev")}


# --- second judge (Jev) -----------------------------------------------------------------

JEV_LABELS = ("supported", "contradicted", "unsupported")
JEV_CONFIDENT = 0.5  # below this Jev is saying "not sure"; a disagreement there is noise, not a signal


def join_second_judge(paths: list[str], claims: list[dict], session_id: str) -> dict:
    """Attach each claim's Jev verdict as claim["jev"]; return the judge metadata."""
    verdicts: dict[str, dict] = {}
    models: set[str] = set()
    usage = {"requests": 0, "input_tokens": 0, "estimated_cost_usd": 0.0}
    for path in paths:
        doc = json.loads(Path(path).read_text())
        if doc.get("session_id") != session_id:
            fail(f"{path}: second-judge file is session {doc.get('session_id')}, verdicts are {session_id}")
        if any(v.get("label") for v in (doc.get("claims") or {}).values()):
            models.add(str((doc.get("judge") or {}).get("model") or "jev"))
        for k in usage:
            usage[k] += (doc.get("usage") or {}).get(k, 0)
        verdicts.update(doc.get("claims") or {})
    for c in claims:
        v = verdicts.get(c["id"])
        if v and v.get("label") in JEV_LABELS:
            c["jev"] = {"label": v["label"], "confidence": v.get("confidence"), "p": v.get("p"), "truncated": v.get("truncated", False)}
    usage["estimated_cost_usd"] = round(usage["estimated_cost_usd"], 5)
    return {"model": ", ".join(sorted(models)), "usage": usage, "verdicts": len(verdicts)}


def second_judge(claims: list[dict], meta: dict) -> dict:
    """Judge-vs-judge agreement, the benchmark's judge-vs-human figure with Jev standing in for the human.

    Two comparison sets. *Packet-checkable* claims are the ones whose reference is inside the
    packet — the grader saw the evidence before the message (`evidenced_in_session`), cited an
    evidence item in its check, or found nothing anywhere (`unsupported`). That is the fair
    comparison: Jev never sees the repository, so a claim the grader settled with a live check is
    outside its reach. *All checkable* is every claim both judges labelled, for completeness.
    """
    judged = [c for c in claims if c.get("jev") and c["label"] != "not_checkable"]
    packet = [c for c in judged if reference_in_packet(c)]

    def hallucinated(label: str) -> bool:
        return label in ("contradicted", "unsupported")

    def agreement(rows: list[dict]) -> dict:
        grader = [c["label"] for c in rows]
        jev = [c["jev"]["label"] for c in rows]
        confusion = {g: {j: 0 for j in JEV_LABELS} for g in JEV_LABELS}
        for g, j in zip(grader, jev):
            confusion[g][j] += 1
        return {
            "n": len(rows),
            "label_agreement": ratio(sum(g == j for g, j in zip(grader, jev)), len(rows)),
            "label_kappa": kappa(grader, jev, JEV_LABELS),
            "hallucination_agreement": ratio(sum(hallucinated(g) == hallucinated(j) for g, j in zip(grader, jev)), len(rows)),
            "hallucination_kappa": kappa([hallucinated(g) for g in grader], [hallucinated(j) for j in jev], (False, True)),
            "confusion": confusion,
        }

    # Where the two judges part ways, ranked by how sure Jev is. Grader `supported` with a
    # confident Jev `contradicted` is the leniency signal this block exists to surface.
    possible_misses = sorted(
        (slim(c) for c in judged if c["label"] == "supported" and c["strength"] == "asserted"
         and (c["jev"]["label"] == "contradicted" or (c["jev"]["label"] == "unsupported" and c["evidenced_in_session"]))
         and (c["jev"].get("confidence") or 0) >= JEV_CONFIDENT),
        key=lambda c: -(c["jev"].get("confidence") or 0),
    )
    possible_false_alarms = sorted(
        (slim(c) for c in judged if hallucinated(c["label"]) and c["strength"] == "asserted"
         and c["jev"]["label"] == "supported" and (c["jev"].get("confidence") or 0) >= JEV_CONFIDENT),
        key=lambda c: -(c["jev"].get("confidence") or 0),
    )
    return {
        "model": meta["model"],
        "usage": meta["usage"],
        "claims_judged": len(judged),
        "claims_out_of_reach": len([c for c in claims if c["label"] != "not_checkable"]) - len(judged),
        "packet_checkable": agreement(packet),
        "all_checkable": agreement(judged),
        "possible_misses": possible_misses,
        "possible_false_alarms": possible_false_alarms,
    }


def reference_in_packet(c: dict) -> bool:
    """Did the grader settle this claim from the session evidence (which Jev sees) rather than a live check?"""
    check = (c.get("check") or "").lower()
    cites_evidence = bool(re.search(r"(evidence\s*#\d|\bt\d+\s*#\d|#\d+\b)", check))
    if c["label"] == "unsupported" or cites_evidence:
        return True
    return bool(c.get("evidenced_in_session")) and "live" not in check


def kappa(a: list, b: list, labels: tuple) -> float | None:
    """Cohen's κ between two label sequences; None when it is undefined (empty, or chance agreement is 1)."""
    n = len(a)
    if n == 0:
        return None
    po = sum(x == y for x, y in zip(a, b)) / n
    pe = sum((a.count(k) / n) * (b.count(k) / n) for k in labels)
    if pe >= 1.0:
        return None
    return round((po - pe) / (1 - pe), 3)


def ratio(num: int, den: int) -> float | None:
    return None if den == 0 else round(num / den, 4)


def band(rate: float | None) -> str:
    if rate is None:
        return "n/a"
    return next(label for cap, label in BANDS if rate < cap)


def persist(card: dict, claims: list[dict]) -> None:
    SCORES_DIR.mkdir(parents=True, exist_ok=True)
    (SCORES_DIR / f"{card['session_id']}.json").write_text(json.dumps({**card, "claims": claims}, indent=1))
    m = card["metrics"]
    line = {
        "session_id": card["session_id"],
        "harness": card["coverage"].get("harness") or "claude",
        "scored_at": card["scored_at"],
        "turn_range": card["turn_range"],
        "attempted": m["attempted"],
        "hallucination_rate": m["hallucination_rate"],
        "omniscience_index": m["omniscience_index"],
        "band": m["band"],
    }
    if card.get("second_judge"):
        line["jev_hallucination_kappa"] = card["second_judge"]["packet_checkable"]["hallucination_kappa"]
    with (SCORES_DIR / "history.jsonl").open("a") as fh:
        fh.write(json.dumps(line) + "\n")


def export(out_dir: Path, card: dict, claims: list[dict]) -> None:
    """Write the run in the shape kept under benchmark-runs/: the card, plus every claim so the labels can be audited."""
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "scorecard.md").write_text(render(card) + "\n")
    (out_dir / "scorecard.json").write_text(json.dumps({**card, "claims": claims}, indent=1, ensure_ascii=False) + "\n")


def print_history(n: int) -> None:
    path = SCORES_DIR / "history.jsonl"
    if not path.is_file():
        print("no scored sessions yet")
        return
    rows = [json.loads(l) for l in path.read_text().splitlines() if l.strip()][-n:]
    print("| scored at | harness | session | turns | attempted | halluc. rate | index | band |")
    print("|---|---|---|---|---|---|---|---|")
    for r in rows:
        print(f"| {r['scored_at'][:16]} | {r.get('harness', 'claude')} | {r['session_id'][:8]} | {r['turn_range'][0]}–{r['turn_range'][1]} | {r['attempted']} | {pct(r['hallucination_rate'])} | {signed(r['omniscience_index'])} | {r['band']} |")


def render(card: dict) -> str:
    m = card["metrics"]
    cov = card["coverage"]
    lo, hi = card["turn_range"]
    lines = [
        f"# Hallucination scorecard — {cov.get('harness') or 'claude'} session {card['session_id'][:8]} (turns {lo}–{hi})",
        "",
        f"**Band: {m['band']}** — hallucination rate {pct(m['hallucination_rate'])} over {m['attempted']} asserted, checkable claims.",
        "",
        "| Metric | Value | Benchmark analogue |",
        "|---|---|---|",
        f"| Hallucination rate (wrong ÷ attempted) | {pct(m['hallucination_rate'])} ({m['contradicted'] + m['unsupported']}/{m['attempted']}) | SimpleQA incorrect-given-attempted; HalluLens hallucinated-when-not-refused |",
        f"| ├ Contradiction rate (intrinsic) | {pct(m['contradiction_rate'])} ({m['contradicted']}) | RAGTruth evident/subtle conflict |",
        f"| └ Baseless rate (extrinsic) | {pct(m['baseless_rate'])} ({m['unsupported']}) | RAGTruth baseless info; FActScore/SAFE not-supported |",
        f"| Omniscience index | {signed(m['omniscience_index'])} | AA-Omniscience: +1 correct, 0 abstain, −1 wrong, over {m['claims_checkable']} checkable |",
        f"| Accuracy (correct ÷ checkable) | {pct(m['accuracy'])} | SimpleQA overall-correct |",
        f"| Abstention rate | {pct(m['abstention_rate'])} ({m['abstained']}) | SimpleQA not-attempted; HalluLens refusal |",
        f"| Severity-weighted hallucination rate | {pct(m['weighted_hallucination_rate'])} | house: action/verification/entity ×3, tool_output/code/completion ×2, external/history ×1 |",
        f"| Grounding rate (asserted with evidence in hand) | {pct(m['grounding_rate'])} | house: how often the claim was made after observing it, not recalled |",
        "",
        "## By claim type",
        "",
        "| Type | Attempted | Supported | Contradicted | Unsupported | Halluc. rate |",
        "|---|---|---|---|---|---|",
    ]
    for name, row in card["by_type"].items():
        lines.append(f"| {name} | {row['attempted']} | {row['supported']} | {row['contradicted']} | {row['unsupported']} | {pct(row['hallucination_rate'])} |")

    if card["drift"]:
        lines += ["", "## Drift across the session", "", "| Segment | Turns | Attempted | Halluc. rate |", "|---|---|---|---|"]
        for d in card["drift"]:
            lines.append(f"| {d['segment']} | {d['turns'][0]}–{d['turns'][1]} | {d['attempted']} | {pct(d['hallucination_rate'])} |")

    lines += ["", "## Hallucinated claims (most severe first)", ""]
    if not card["hallucinations"]:
        lines.append("None.")
    for i, c in enumerate(card["hallucinations"], start=1):
        lines.append(f"{i}. `{c['id']}` **{c['type']}** · {c['label']} — “{c['quote']}”")
        lines.append(f"   - claim: {c['claim']}")
        lines.append(f"   - check: {c['check']}")
        if c.get("jev"):
            lines.append(f"   - second judge: {jev_verdict(c)}")

    hc = m["hedge_calibration"]
    lines += ["", "## Hedge calibration", ""]
    if hc["hedged"] == 0:
        lines.append("No hedged claims.")
    else:
        lines.append(f"{hc['hedged']} hedged claims: {hc['hedged_wrong']} turned out wrong (hedge warranted), {hc['hedged_supported']} were right (over-hedged).")
        for c in card["hedged_wrong"]:
            lines.append(f"- `{c['id']}` — “{c['quote']}” — {c['check']}")

    sj = card.get("second_judge")
    if sj:
        pc, al = sj["packet_checkable"], sj["all_checkable"]
        lines += [
            "",
            f"## Second judge — {sj['model']} (TypeSafe, different model family)",
            "",
            "| Comparison set | Claims | Label agreement | κ | Hallucination agreement | κ |",
            "|---|---|---|---|---|---|",
            f"| Packet-checkable (reference in the session evidence) | {pc['n']} | {pct(pc['label_agreement'])} | {kap(pc['label_kappa'])} | {pct(pc['hallucination_agreement'])} | {kap(pc['hallucination_kappa'])} |",
            f"| All checkable claims both judges labelled | {al['n']} | {pct(al['label_agreement'])} | {kap(al['label_kappa'])} | {pct(al['hallucination_agreement'])} | {kap(al['hallucination_kappa'])} |",
            "",
            "Grader × second judge, packet-checkable: " + "; ".join(
                f"grader {g} → " + ", ".join(f"{j} {n}" for j, n in row.items() if n) for g, row in pc["confusion"].items() if any(row.values())
            ) + f". {sj['claims_out_of_reach']} checkable claims were out of the second judge's reach (no evidence in the packet).",
        ]
        if sj["possible_misses"] or sj["possible_false_alarms"]:
            lines += ["", "Spot-check first (the two judges disagree, second judge confident):", ""]
            for c in sj["possible_misses"][:10]:
                lines.append(f"- `{c['id']}` **{c['type']}** grader supported, {jev_verdict(c, plain=True)} — “{c['quote']}” — possible miss by the grader")
            for c in sj["possible_false_alarms"][:10]:
                lines.append(f"- `{c['id']}` **{c['type']}** grader {c['label']}, {jev_verdict(c, plain=True)} — “{c['quote']}” — possible false alarm")
            hidden = len(sj["possible_misses"]) + len(sj["possible_false_alarms"]) - min(10, len(sj["possible_misses"])) - min(10, len(sj["possible_false_alarms"]))
            if hidden > 0:
                lines.append(f"- … {hidden} more in the persisted card")
        else:
            lines += ["", "No confident disagreements."]

    total = cov.get("messages_total")
    lines += [
        "",
        "## Coverage",
        "",
        f"Messages with at least one claim: {cov['messages_with_claims']}" + (f" of {total}" if total else "")
        + (f" ({cov['messages_paraphrased']} of the {total} survive only as harness paraphrases, not verbatim)" if cov.get("messages_paraphrased") else "")
        + f". Claims: {m['claims_total']} total, {m['claims_checkable']} checkable, {m['claims_total'] - m['claims_checkable']} excluded as not checkable.",
        f"Graders: {', '.join(str(g.get('model') or '?') + ' (chunk ' + str(g.get('chunk')) + ')' for g in card['graders'])}."
        + (f" Second judge: {sj['model']} on {sj['claims_judged']} claims, {sj['usage']['requests']} requests, ~${sj['usage']['estimated_cost_usd']:.4f}." if sj else ""),
    ]
    return "\n".join(lines)


def jev_verdict(c: dict, plain: bool = False) -> str:
    j = c["jev"]
    conf = f" ({j['confidence']:.2f})" if j.get("confidence") is not None else ""
    verdict = f"Jev {j['label']}{conf}"
    return verdict if plain else f"{verdict} — {'agrees' if j['label'] == c['label'] else 'disagrees'}"


def kap(v: float | None) -> str:
    return "n/a" if v is None else f"{v:.2f}"


def pct(v: float | None) -> str:
    return "n/a" if v is None else f"{100 * v:.1f}%"


def signed(v: float | None) -> str:
    return "n/a" if v is None else f"{v:+.1f}"


def fail(msg: str) -> None:
    print(f"score: {msg}", file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    main()
