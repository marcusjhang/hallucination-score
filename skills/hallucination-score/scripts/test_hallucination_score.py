"""Unit tests for the hallucination-score scripts.

    python3 <skill dir>/scripts/test_hallucination_score.py
"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))

import extract_turns  # noqa: E402
import score  # noqa: E402


_req = 0


def rec(kind, content, **extra):
    global _req
    _req += 1
    base = {"type": kind, "message": {"content": content}, "sessionId": "s1", "cwd": "/repo", "requestId": f"req{_req}"}
    return json.dumps({**base, **extra})


def response(blocks, **extra):
    """One API response: several records sharing a requestId, one block each."""
    global _req
    _req += 1
    return [json.dumps({"type": "assistant", "message": {"content": [b]}, "requestId": f"req{_req}", "sessionId": "s1", "cwd": "/repo", **extra}) for b in blocks]


def redacted_thinking():
    return {"type": "thinking", "thinking": "", "signature": "sig"}


def human(text):
    return rec("user", text, origin={"kind": "human"}, promptSource="typed", timestamp="t")


def tool_use(tool_id, name, inp):
    return rec("assistant", [{"type": "tool_use", "id": tool_id, "name": name, "input": inp}])


def tool_result(tool_id, text, is_error=False):
    return rec("user", [{"type": "tool_result", "tool_use_id": tool_id, "content": text, "is_error": is_error}])


def assistant_text(text):
    return rec("assistant", [{"type": "thinking", "thinking": "private"}, {"type": "text", "text": text}], uuid="u")


class ExtractTurnsTest(unittest.TestCase):
    def _turns(self, lines):
        with tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False) as fh:
            fh.write("\n".join(lines) + "\n")
        return extract_turns.read_turns(Path(fh.name), max_result_chars=50, max_input_chars=40)

    def test_groups_prompt_messages_and_evidence_into_turns(self):
        turns = self._turns([
            human("fix the bug <system-reminder>ignore me</system-reminder>"),
            assistant_text("Looking now."),
            tool_use("a", "Bash", {"command": "ls", "description": "list"}),
            tool_result("a", "file.ts"),
            assistant_text("There is one file."),
            human("thanks"),
            assistant_text("Done."),
        ])
        self.assertEqual([t["turn"] for t in turns], [1, 2])
        first = turns[0]
        self.assertEqual(first["prompt"], "fix the bug")
        self.assertEqual([m["text"] for m in first["messages"]], ["Looking now.", "There is one file."])
        self.assertEqual([m["after_evidence"] for m in first["messages"]], [0, 1])
        self.assertEqual(first["messages"][1]["id"], "t1-m2")
        self.assertEqual(first["evidence"][0]["tool"], "Bash")
        self.assertTrue(first["evidence"][0]["input"].startswith("command=ls"))
        self.assertEqual(first["evidence"][0]["result"], "file.ts")

    def test_thinking_blocks_and_sidechains_are_not_graded(self):
        turns = self._turns([
            human("go"),
            assistant_text("visible"),
            rec("assistant", [{"type": "text", "text": "subagent chatter"}], isSidechain=True),
            rec("user", "subagent prompt", isSidechain=True),
        ])
        self.assertEqual(len(turns), 1)
        self.assertEqual([m["text"] for m in turns[0]["messages"]], ["visible"])

    def test_non_human_user_records_become_injected_context_not_turns(self):
        turns = self._turns([
            human("go"),
            rec("user", "<task-notification>agent finished</task-notification>", origin={"kind": "task-notification"}, promptSource="system"),
            rec("user", "[Request interrupted by user]"),
            assistant_text("ok"),
        ])
        self.assertEqual(len(turns), 1)
        self.assertEqual([e["tool"] for e in turns[0]["evidence"]], ["<injected-context>", "<injected-context>"])
        self.assertEqual(turns[0]["messages"][0]["after_evidence"], 2)

    def test_paraphrase_thinking_recovered_only_when_text_is_missing(self):
        turns = self._turns([
            human("go"),
            *response([redacted_thinking(), {"type": "thinking", "thinking": "Paraphrase of what I told the user.", "signature": "s"},
                       {"type": "tool_use", "id": "a", "name": "Bash", "input": {"command": "ls"}}]),
            tool_result("a", "ok"),
            *response([redacted_thinking(), {"type": "thinking", "thinking": "ignored: text exists", "signature": "s"},
                       {"type": "text", "text": "Verbatim answer."}]),
            *response([{"type": "thinking", "thinking": "real visible thinking, no redacted block first", "signature": "s"},
                       {"type": "tool_use", "id": "b", "name": "Bash", "input": {"command": "pwd"}}]),
            tool_result("b", "/repo"),
        ])
        msgs = turns[0]["messages"]
        self.assertEqual([(m["channel"], m["text"]) for m in msgs],
                         [("paraphrase", "Paraphrase of what I told the user."), ("text", "Verbatim answer.")])
        self.assertEqual([m["after_evidence"] for m in msgs], [0, 1])
        self.assertEqual(len(turns[0]["evidence"]), 2)

    def test_tool_errors_and_truncation(self):
        long = "x" * 500
        turns = self._turns([
            human("go"),
            tool_use("a", "Bash", {"command": "false"}),
            tool_result("a", long, is_error=True),
        ])
        ev = turns[0]["evidence"][0]
        self.assertTrue(ev["is_error"])
        self.assertIn("chars omitted", ev["result"])
        self.assertLess(len(ev["result"]), len(long))

    def test_select_turns(self):
        turns = [{"turn": n} for n in range(1, 8)]
        self.assertEqual([t["turn"] for t in extract_turns.select_turns(turns, last=2, rng=None)], [6, 7])
        self.assertEqual([t["turn"] for t in extract_turns.select_turns(turns, last=None, rng="3-5")], [3, 4, 5])
        self.assertEqual([t["turn"] for t in extract_turns.select_turns(turns, last=None, rng="4")], [4])


def claim(cid, turn, ctype, strength, label, **extra):
    base = {
        "id": cid, "turn": turn, "message": cid.rsplit("-", 1)[0], "quote": "q", "claim": "c",
        "type": ctype, "strength": strength, "label": label, "check": "checked", "evidenced_in_session": False,
    }
    return {**base, **extra}


class ScoreTest(unittest.TestCase):
    def test_metrics_follow_simpleqa_and_omniscience_definitions(self):
        claims = [
            claim("t1-m1-c1", 1, "tool_output", "asserted", "supported", evidenced_in_session=True),
            claim("t1-m1-c2", 1, "verification", "asserted", "contradicted"),
            claim("t2-m1-c1", 2, "entity", "asserted", "unsupported"),
            claim("t2-m1-c2", 2, "code_behaviour", "hedged", "contradicted"),
            claim("t3-m1-c1", 3, "completion", "asserted", "not_checkable"),
            claim("t3-m2-c1", 3, "code_behaviour", "abstained", "unsupported"),
            claim("t3-m2-c2", 3, "history", "asserted", "supported", evidenced_in_session=True),
        ]
        m = score.score(claims)["metrics"]
        self.assertEqual((m["claims_total"], m["claims_checkable"], m["attempted"]), (7, 6, 4))
        self.assertEqual((m["supported"], m["contradicted"], m["unsupported"], m["abstained"]), (2, 1, 1, 2))
        self.assertEqual(m["hallucination_rate"], 0.5)          # (1 + 1) / 4 attempted
        self.assertEqual(m["omniscience_index"], 0.0)           # (2 − 2) / 6 checkable
        self.assertAlmostEqual(m["accuracy"], 2 / 6, places=4)
        self.assertAlmostEqual(m["abstention_rate"], 2 / 6, places=4)
        # weights: wrong = verification 3 + entity 3; attempted = 2 + 3 + 3 + 1
        self.assertAlmostEqual(m["weighted_hallucination_rate"], 6 / 9, places=4)
        self.assertEqual(m["grounding_rate"], 0.5)
        self.assertEqual(m["hedge_calibration"], {"hedged": 1, "hedged_wrong": 1, "hedged_supported": 0})
        self.assertEqual(m["band"], "failing")

    def test_empty_window_scores_na_not_zero(self):
        m = score.score([])["metrics"]
        self.assertIsNone(m["hallucination_rate"])
        self.assertIsNone(m["omniscience_index"])
        self.assertEqual(m["band"], "n/a")

    def test_bands(self):
        self.assertEqual(score.band(0.0), "excellent")
        self.assertEqual(score.band(0.019), "excellent")
        self.assertEqual(score.band(0.02), "good")
        self.assertEqual(score.band(0.099), "watch")
        self.assertEqual(score.band(0.5), "failing")

    def test_hallucinations_sorted_by_severity_then_contradicted_first(self):
        claims = [
            claim("t1-m1-c1", 1, "history", "asserted", "contradicted"),
            claim("t1-m1-c2", 1, "verification", "asserted", "unsupported"),
            claim("t1-m1-c3", 1, "verification", "asserted", "contradicted"),
        ]
        ids = [c["id"] for c in score.score(claims)["hallucinations"]]
        self.assertEqual(ids, ["t1-m1-c3", "t1-m1-c2", "t1-m1-c1"])

    def test_drift_needs_three_turns(self):
        self.assertEqual(score.drift([claim("t1-m1-c1", 1, "entity", "asserted", "supported")]), [])
        rows = score.drift([claim(f"t{n}-m1-c1", n, "entity", "asserted", "supported" if n < 3 else "unsupported") for n in (1, 2, 3)])
        self.assertEqual([r["segment"] for r in rows], ["early", "middle", "late"])
        self.assertEqual(rows[-1]["hallucination_rate"], 1.0)

    def test_validate_rejects_open_set_labels_and_missing_checks(self):
        with self.assertRaises(SystemExit):
            score.validate(claim("t1-m1-c1", 1, "entity", "asserted", "wrongish"), "f")
        with self.assertRaises(SystemExit):
            score.validate(claim("t1-m1-c1", 1, "made_up_type", "asserted", "supported"), "f")
        with self.assertRaises(SystemExit):
            score.validate(claim("t1-m1-c1", 1, "entity", "asserted", "supported", check=""), "f")
        score.validate(claim("t1-m1-c1", 1, "entity", "asserted", "not_checkable", check=""), "f")

    def test_load_verdicts_rejects_duplicate_ids_and_mixed_sessions(self):
        with tempfile.TemporaryDirectory() as d:
            a = Path(d) / "a.json"
            b = Path(d) / "b.json"
            a.write_text(json.dumps({"session_id": "s", "claims": [claim("t1-m1-c1", 1, "entity", "asserted", "supported")]}))
            b.write_text(json.dumps({"session_id": "s", "claims": [claim("t1-m1-c1", 1, "entity", "asserted", "supported")]}))
            with self.assertRaises(SystemExit):
                score.load_verdicts([str(a), str(b)])
            b.write_text(json.dumps({"session_id": "other", "claims": [claim("t2-m1-c1", 2, "entity", "asserted", "supported")]}))
            with self.assertRaises(SystemExit):
                score.load_verdicts([str(a), str(b)])


if __name__ == "__main__":
    unittest.main()
