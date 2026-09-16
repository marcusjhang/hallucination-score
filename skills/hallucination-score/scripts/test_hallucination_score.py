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

    def test_chunk_turns_cuts_on_count_and_on_size(self):
        m = [{"text": "x"}]
        small = [{"turn": n, "messages": m, "x": "a" * 10} for n in range(1, 6)]
        self.assertEqual([[t["turn"] for t in c] for c in extract_turns.chunk_turns(small, 2, 10_000)], [[1, 2], [3, 4], [5]])
        sized = [{"turn": 1, "messages": m, "x": "a" * 10}, {"turn": 2, "messages": m, "x": "a" * 500}, {"turn": 3, "messages": m, "x": "a" * 10}, {"turn": 4, "messages": m, "x": "a" * 10}]
        self.assertEqual([[t["turn"] for t in c] for c in extract_turns.chunk_turns(sized, 8, 120)], [[1], [2], [3, 4]])

    def test_chunk_turns_never_emits_a_packet_without_prose(self):
        m = [{"text": "x"}]
        turns = [{"turn": 1, "messages": [], "x": "a" * 10}, {"turn": 2, "messages": m, "x": "a" * 500}, {"turn": 3, "messages": [], "x": "a" * 10}]
        # turn 1 has no prose so it rides along with the oversize turn 2; the trailing prose-less turn 3 folds into the last packet
        self.assertEqual([[t["turn"] for t in c] for c in extract_turns.chunk_turns(turns, 8, 100)], [[1, 2, 3]])
        self.assertEqual([[t["turn"] for t in c] for c in extract_turns.chunk_turns([{"turn": 1, "messages": [], "x": ""}], 8, 100)], [[1]])

    def test_select_turns(self):
        turns = [{"turn": n} for n in range(1, 8)]
        self.assertEqual([t["turn"] for t in extract_turns.select_turns(turns, last=2, rng=None)], [6, 7])
        self.assertEqual([t["turn"] for t in extract_turns.select_turns(turns, last=None, rng="3-5")], [3, 4, 5])
        self.assertEqual([t["turn"] for t in extract_turns.select_turns(turns, last=None, rng="4")], [4])


class CodexAdapterTest(unittest.TestCase):
    def _events(self, records, name="rollout-2026-09-15T13-38-06-01a0a392-8f8c-7131-88c8-3f25db350c3b.jsonl"):
        d = tempfile.mkdtemp()
        path = Path(d) / name
        path.write_text("\n".join(json.dumps(r) for r in records) + "\n")
        return list(extract_turns.codex_events(path)), path

    def test_codex_rollout_maps_to_events(self):
        recs = [
            {"type": "session_meta", "payload": {"id": "01a0a392-8f8c-7131-88c8-3f25db350c3b", "session_id": "parent", "cwd": "/repo", "thread_source": "user"}},
            {"type": "response_item", "payload": {"type": "message", "role": "developer", "content": [{"type": "input_text", "text": "<skills_instructions>"}]}},
            {"type": "response_item", "payload": {"type": "message", "role": "user", "content": [{"type": "input_text", "text": "<environment_context>cwd</environment_context>"}]}},
            {"type": "response_item", "payload": {"type": "message", "role": "user", "content": [{"type": "input_text", "text": "fix it"}]}},
            {"type": "response_item", "payload": {"type": "reasoning", "summary": [], "encrypted_content": "x"}},
            {"type": "response_item", "payload": {"type": "message", "role": "assistant", "content": [{"type": "output_text", "text": "Looking."}]}},
            {"type": "response_item", "payload": {"type": "function_call", "call_id": "c1", "name": "shell", "arguments": "{\"cmd\":\"ls\"}"}},
            {"type": "response_item", "payload": {"type": "function_call_output", "call_id": "c1", "output": "a.ts"}},
            {"type": "response_item", "payload": {"type": "message", "role": "assistant", "content": [{"type": "output_text", "text": "One file."}]}},
        ]
        events, path = self._events(recs)
        self.assertEqual(events[0], ("session", {"session_id": "01a0a392-8f8c-7131-88c8-3f25db350c3b", "cwd": "/repo", "harness": "codex"}))
        turns = extract_turns.build_turns(events, 200, 100)
        self.assertEqual(len(turns), 1)
        self.assertEqual(turns[0]["prompt"], "fix it")
        self.assertEqual([m["text"] for m in turns[0]["messages"]], ["Looking.", "One file."])
        self.assertEqual([m["after_evidence"] for m in turns[0]["messages"]], [0, 1])
        self.assertEqual(turns[0]["evidence"][0]["tool"], "shell")
        self.assertEqual(turns[0]["evidence"][0]["result"], "a.ts")
        self.assertFalse(extract_turns.codex_is_subagent(path))

    def test_codex_subagent_rollouts_are_flagged(self):
        recs = [{"type": "session_meta", "payload": {"id": "child", "session_id": "parent", "cwd": "/repo", "thread_source": "subagent"}}]
        events, path = self._events(recs, name="rollout-2026-09-15T13-38-06-01a0a392-8f8c-7131-88c8-3f25db350c3c.jsonl")
        self.assertTrue(extract_turns.codex_is_subagent(path))
        self.assertEqual(events[0][1]["session_id"], "child")


class PrimeAdapterTest(unittest.TestCase):
    def test_prime_follows_the_active_branch_and_maps_roles(self):
        entries = [
            {"type": "session", "version": 3, "id": "s1", "cwd": "/repo"},
            {"type": "message", "id": "u1", "parentId": None, "message": {"role": "user", "content": [{"type": "text", "text": "hello"}]}},
            {"type": "message", "id": "a1", "parentId": "u1", "message": {"role": "assistant", "content": [
                {"type": "thinking", "thinking": "real thinking"}, {"type": "toolCall", "id": "tc1", "name": "bash", "arguments": {"command": "ls"}}]}},
            {"type": "message", "id": "r1", "parentId": "a1", "message": {"role": "toolResult", "toolCallId": "tc1", "toolName": "bash", "content": [{"type": "text", "text": "a.ts"}], "isError": False}},
            {"type": "message", "id": "a2-abandoned", "parentId": "r1", "message": {"role": "assistant", "content": [{"type": "text", "text": "abandoned branch"}]}},
            {"type": "message", "id": "a2", "parentId": "r1", "message": {"role": "assistant", "content": [{"type": "text", "text": "One file."}]}},
        ]
        d = tempfile.mkdtemp()
        path = Path(d) / "s1.jsonl"
        path.write_text("\n".join(json.dumps(e) for e in entries) + "\n")
        events = list(extract_turns.prime_events(path))
        self.assertEqual(events[0], ("session", {"session_id": "s1", "cwd": "/repo", "harness": "prime"}))
        turns = extract_turns.build_turns(events, 200, 100)
        self.assertEqual([m["text"] for m in turns[0]["messages"]], ["One file."])  # thinking dropped, abandoned branch dropped
        self.assertEqual(turns[0]["messages"][0]["channel"], "text")
        self.assertEqual(turns[0]["evidence"][0]["tool"], "bash")
        self.assertEqual(turns[0]["evidence"][0]["result"], "a.ts")


class OpenCodeAdapterTest(unittest.TestCase):
    def test_opencode_steps_become_responses(self):
        import sqlite3
        d = tempfile.mkdtemp()
        db = Path(d) / "opencode.db"
        con = sqlite3.connect(db)
        con.executescript("""
            create table session (id text primary key, parent_id text, directory text);
            create table message (id text primary key, session_id text, time_created integer, time_updated integer, data text);
            create table part (id text primary key, message_id text, session_id text, time_created integer, data text);
        """)
        con.execute("insert into session values ('ses1', null, '/repo')")
        con.execute("insert into message values ('m1','ses1',1000,1000,?)", (json.dumps({"role": "user"}),))
        con.execute("insert into part values ('p1','m1','ses1',1000,?)", (json.dumps({"type": "text", "text": "explain"}),))
        con.execute("insert into message values ('m2','ses1',2000,2000,?)", (json.dumps({"role": "assistant"}),))
        parts = [
            {"type": "step-start"}, {"type": "reasoning", "text": "hmm"},
            {"type": "tool", "tool": "bash", "callID": "c1", "state": {"status": "completed", "input": {"command": "ls"}, "output": "a.ts"}},
            {"type": "step-finish"}, {"type": "step-start"}, {"type": "text", "text": "One file."}, {"type": "step-finish"},
        ]
        for i, p in enumerate(parts):
            con.execute("insert into part values (?,?,?,?,?)", (f"pp{i}", "m2", "ses1", 2000 + i, json.dumps(p)))
        con.commit(); con.close()
        original = extract_turns.STORES["opencode"]
        extract_turns.STORES["opencode"] = db
        try:
            events = list(extract_turns.opencode_events("ses1"))
        finally:
            extract_turns.STORES["opencode"] = original
        self.assertEqual(events[0], ("session", {"session_id": "ses1", "cwd": "/repo", "harness": "opencode"}))
        turns = extract_turns.build_turns(events, 200, 100)
        self.assertEqual(turns[0]["prompt"], "explain")
        self.assertEqual([(m["text"], m["after_evidence"]) for m in turns[0]["messages"]], [("One file.", 1)])
        self.assertEqual(turns[0]["evidence"][0]["result"], "a.ts")


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
