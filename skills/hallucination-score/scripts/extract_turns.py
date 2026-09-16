#!/usr/bin/env python3
"""Phase 1 of the hallucination-score skill: the deterministic transcript extract.

    python3 <skill dir>/scripts/extract_turns.py [--session ID] [--last N] [--chunk-turns 8]
    python3 <skill dir>/scripts/extract_turns.py --list [N]
    python3 <skill dir>/scripts/extract_turns.py --session ID --evidence TURN:INDEX

Reads a coding-agent session transcript and writes one "grading packet" JSON per chunk
of turns. A packet is what a benchmark grader would call the *evidence set*: every
user-facing assistant message, plus every tool call and tool result in the same turn,
in order, so the grader can check each claim against what the model actually observed
(RAGTruth-style faithfulness) before it goes to the live repo (SAFE-style retrieval).

Harnesses (auto-detected from the session id or file; force with --harness):

    claude    ~/.claude/projects/<cwd-slug>/<session>.jsonl
    codex     ~/.codex/sessions/YYYY/MM/DD/rollout-<ts>-<session>.jsonl
    prime     ~/.prime/agent/sessions/<session>.jsonl      (Prime Agent / pi-agent v3 format)
    opencode  ~/.local/share/opencode/opencode.db          (SQLite: session, message, part)

Each adapter yields one normalised event stream; the turn builder is shared:

    ("session",     {"session_id", "cwd", "harness"})
    ("prompt",      {"text", "origin": "human" | "system", "timestamp"})
    ("response",    {"blocks": [text | thinking | tool_use ...], "timestamp", "uuid"})
    ("tool_result", {"tool_use_id", "text", "is_error", "timestamp"})

Only user-facing text is graded. Thinking blocks are dropped: benchmarks score the
answer, not the scratchpad. One exception: Claude Code (seen on 2.1.273) sometimes
persists prose the assistant wrote between tool calls not as a ``text`` block but as a
short paraphrase in a second ``thinking`` block, after the signature-only redacted one.
Those are the only surviving record of a user-visible message, so they are emitted as
messages with ``channel: "paraphrase"`` and counted separately in the index. Subagent
transcripts (Claude sidechains, OpenCode child sessions) are dropped; their conclusions
re-enter the parent as a tool result and are graded there as evidence the assistant
chose to relay.

Packets land in ``~/.claude/hallucination-scores/<session>/packets/`` by default: outside
the repo, because they carry session content that must never be committed.
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

SYSTEM_REMINDER_RE = re.compile(r"<system-reminder>.*?</system-reminder>", re.S)
CODEX_INJECTED_PREFIXES = ("<environment_context>", "<recommended_plugins>", "<user_instructions>", "<permissions", "<turn_aborted", "<skills_instructions>", "<app_instructions", "<collaboration_mode")
HOME = Path.home()
SCORES_DIR = HOME / ".claude" / "hallucination-scores"
STORES = {
    "claude": HOME / ".claude" / "projects",
    "codex": HOME / ".codex" / "sessions",
    "prime": HOME / ".prime" / "agent" / "sessions",
    "opencode": HOME / ".local" / "share" / "opencode" / "opencode.db",
}
HARNESSES = tuple(STORES)

Event = tuple[str, dict]


def main() -> None:
    args = parse_args()
    if args.list is not None:
        list_sessions(args.list or 15, args.harness)
        return

    harness, source = resolve_source(args)
    events = list(ADAPTERS[harness](source))
    if args.evidence:
        show_evidence(events, args.evidence)
        return
    turns = build_turns(events, args.max_result_chars, args.max_input_chars)
    if not turns:
        fail(f"no human turns found in {harness} session {source}")
    meta = next(payload for kind, payload in events if kind == "session")
    session_id = meta["session_id"]

    selected = select_turns(turns, args.last, args.turns)
    if not selected:
        fail("turn selection matched nothing")

    out_dir = Path(args.out_dir) if args.out_dir else SCORES_DIR / session_id / "packets"
    out_dir.mkdir(parents=True, exist_ok=True)
    for stale in out_dir.glob("packet-*.json"):
        stale.unlink()

    prompts_index = [{"turn": t["turn"], "prompt": truncate(t["prompt"], 240), "origin": t["origin"]} for t in turns]
    chunks = chunk_turns(selected, args.chunk_turns, args.max_packet_bytes)
    written = []
    for n, chunk in enumerate(chunks, start=1):
        packet = {
            "session_id": session_id,
            "harness": harness,
            "transcript": str(source),
            "cwd": meta["cwd"],
            "chunk": n,
            "chunks_total": len(chunks),
            "turn_range": [chunk[0]["turn"], chunk[-1]["turn"]],
            "all_prompts": prompts_index,
            "turns": chunk,
        }
        path = out_dir / f"packet-{n:03d}.json"
        path.write_text(json.dumps(packet, indent=1, ensure_ascii=False))
        written.append({"path": str(path), "turn_range": packet["turn_range"], "bytes": path.stat().st_size})

    index = {
        "session_id": session_id,
        "harness": harness,
        "transcript": str(source),
        "cwd": meta["cwd"],
        "turns_total": len(turns),
        "turns_selected": [t["turn"] for t in selected],
        "assistant_messages": sum(len(t["messages"]) for t in selected),
        "paraphrased_messages": sum(1 for t in selected for m in t["messages"] if m["channel"] == "paraphrase"),
        "tool_calls": sum(len(t["evidence"]) for t in selected),
        "tool_errors": sum(1 for t in selected for e in t["evidence"] if e["is_error"]),
        "packets": written,
    }
    (out_dir / "index.json").write_text(json.dumps(index, indent=1))
    print(json.dumps(index, indent=1))


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--session", default=os.environ.get("CLAUDE_CODE_SESSION_ID"), help="session id or unique prefix, searched across all harnesses (default: $CLAUDE_CODE_SESSION_ID)")
    p.add_argument("--file", help="explicit transcript .jsonl (claude, codex or prime; overrides --session)")
    p.add_argument("--harness", choices=HARNESSES, help="force the harness instead of auto-detecting")
    p.add_argument("--list", nargs="?", type=int, const=15, help="list the N most recent sessions across harnesses and exit")
    p.add_argument("--evidence", metavar="TURN:INDEX", help="print one evidence item untruncated (for graders recovering an excerpt) and exit")
    p.add_argument("--out-dir", help="directory for packet-NNN.json + index.json (default ~/.claude/hallucination-scores/<session>/packets)")
    p.add_argument("--last", type=int, help="only the last N human turns")
    p.add_argument("--turns", help="inclusive turn range, e.g. 4-9")
    p.add_argument("--chunk-turns", type=int, default=8, help="max turns per packet (default 8)")
    p.add_argument("--max-packet-bytes", type=int, default=150_000, help="start a new packet before exceeding this size; one oversize turn still gets its own packet (default 150000)")
    p.add_argument("--max-result-chars", type=int, default=1500, help="tool result excerpt size (head; a 400-char tail is kept too)")
    p.add_argument("--max-input-chars", type=int, default=600, help="tool input excerpt size")
    return p.parse_args()


# --- source resolution -------------------------------------------------------------


def resolve_source(args: argparse.Namespace) -> tuple[str, Path | str]:
    if args.file:
        path = Path(args.file).expanduser()
        if not path.is_file():
            fail(f"transcript not found: {path}")
        return args.harness or sniff_jsonl(path), path
    if not args.session:
        fail("no session: set $CLAUDE_CODE_SESSION_ID, pass --session, or pass --file")
    hits = [(h, s) for h, s in find_sessions(args.session) if not args.harness or h == args.harness]
    if len(hits) != 1:
        fail(f"expected exactly one session matching {args.session!r}, found {len(hits)}: {hits}")
    return hits[0]


def find_sessions(needle: str) -> list[tuple[str, Path | str]]:
    """Exact id first, then unique-prefix, across every harness store present on this machine."""
    exact: list[tuple[str, Path | str]] = []
    prefix: list[tuple[str, Path | str]] = []
    for harness, sid, source in iter_session_sources():
        if sid == needle:
            exact.append((harness, source))
        elif sid.startswith(needle):
            prefix.append((harness, source))
    return exact or prefix


def iter_session_sources() -> Iterator[tuple[str, str, Path | str]]:
    for path in glob.glob(str(STORES["claude"] / "*" / "*.jsonl")):
        yield "claude", Path(path).stem, Path(path)
    for path in glob.glob(str(STORES["codex"] / "*" / "*" / "*" / "rollout-*.jsonl")):
        if not codex_is_subagent(Path(path)):
            yield "codex", codex_session_id(Path(path)), Path(path)
    for path in glob.glob(str(STORES["prime"] / "*.jsonl")):
        yield "prime", Path(path).stem, Path(path)
    if STORES["opencode"].is_file():
        with opencode_db() as cur:
            for (sid,) in cur.execute("select id from session where parent_id is null"):
                yield "opencode", sid, sid


def codex_session_id(path: Path) -> str:
    # rollout-2026-09-15T13-38-06-<uuid>.jsonl → the uuid is the last 36 chars of the stem
    return path.stem[-36:]


def codex_is_subagent(path: Path) -> bool:
    """Spawned-subagent rollouts carry thread_source: subagent; their results re-enter the parent thread."""
    with path.open(encoding="utf-8") as fh:
        first = fh.readline()
    try:
        meta = json.loads(first)
    except json.JSONDecodeError:
        return False
    return meta.get("type") == "session_meta" and (meta.get("payload") or {}).get("thread_source") == "subagent"


def sniff_jsonl(path: Path) -> str:
    with path.open(encoding="utf-8") as fh:
        for raw in fh:
            try:
                rec = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if rec.get("type") == "session_meta":
                return "codex"
            if rec.get("type") == "session" and "version" in rec:
                return "prime"
            return "claude"
    fail(f"empty transcript: {path}")


def list_sessions(n: int, harness: str | None) -> None:
    rows = []
    for h, sid, source in iter_session_sources():
        if harness and h != harness:
            continue
        try:
            mtime = Path(source).stat().st_mtime if h != "opencode" else opencode_mtime(sid)
        except OSError:
            continue
        rows.append((mtime, h, sid, source))
    rows.sort(reverse=True)
    print(f"{'harness':9} {'session':36} {'turns':>5} {'msgs':>4} {'calls':>5}  {'modified':16}  cwd / first prompt")
    for mtime, h, sid, source in rows[:n]:
        try:
            events = list(ADAPTERS[h](source))
            turns = build_turns(events, 200, 100)
        except Exception as exc:  # noqa: BLE001 - a broken transcript should not hide the others
            print(f"{h:9} {sid:36} {'?':>5} {'?':>4} {'?':>5}  {iso(mtime)[:16]}  unreadable: {exc}")
            continue
        meta = next((p for k, p in events if k == "session"), {})
        first = next((t["prompt"] for t in turns if t["origin"] == "human"), "")
        msgs = sum(len(t["messages"]) for t in turns)
        calls = sum(len(t["evidence"]) for t in turns)
        cwd = Path(meta.get("cwd") or "").name
        print(f"{h:9} {sid:36} {len(turns):5} {msgs:4} {calls:5}  {iso(mtime)[:16]}  {cwd} / {first[:60]!r}")


def show_evidence(events: list[Event], ref: str) -> None:
    """Print one tool call and its full result, so graders never have to parse raw transcripts."""
    turn_s, _, index_s = ref.partition(":")
    try:
        turn_n, index_n = int(turn_s), int(index_s)
    except ValueError:
        fail("--evidence wants TURN:INDEX, e.g. 7:12")
    turns = build_turns(events, max_result_chars=10**9, max_input_chars=10**9)
    turn = next((t for t in turns if t["turn"] == turn_n), None)
    if turn is None or not 0 <= index_n < len(turn["evidence"]):
        fail(f"no evidence {ref} (turn {turn_n} has {len(turn['evidence']) if turn else 0} items)")
    item = turn["evidence"][index_n]
    print(f"# turn {turn_n} evidence #{index_n} · tool={item['tool']} · is_error={item['is_error']} · {item['timestamp']}")
    print("## input")
    print(item["input"])
    print("## result")
    print(item["result"])


# --- adapters: each yields the normalised event stream ---------------------------------


def claude_events(path: Path) -> Iterator[Event]:
    """Claude Code: one JSONL record per API block; records of one response share a requestId."""
    response: list[dict] = []
    response_rec: dict | None = None
    announced = False

    def flush() -> Iterator[Event]:
        nonlocal response, response_rec
        if response and response_rec is not None:
            yield "response", {"blocks": response, "timestamp": response_rec.get("timestamp"), "uuid": response_rec.get("uuid")}
        response, response_rec = [], None

    with path.open(encoding="utf-8") as fh:
        for raw in fh:
            try:
                rec = json.loads(raw)
            except json.JSONDecodeError:
                continue
            kind = rec.get("type")
            if kind not in ("user", "assistant") or rec.get("isSidechain"):
                continue
            if not announced:
                announced = True
                yield "session", {"session_id": rec.get("sessionId") or rec.get("session_id") or path.stem, "cwd": rec.get("cwd"), "harness": "claude"}
            message = rec.get("message") or {}
            content = message.get("content")
            blocks = content if isinstance(content, list) else [{"type": "text", "text": content or ""}]

            if kind == "assistant":
                if response_rec is not None and rec.get("requestId") != response_rec.get("requestId"):
                    yield from flush()
                response_rec = response_rec or rec
                for b in blocks:
                    if b.get("type") == "thinking":
                        response.append({"type": "thinking", "text": b.get("thinking") or "", "redacted": not (b.get("thinking") or "") and bool(b.get("signature"))})
                    elif b.get("type") == "text":
                        response.append({"type": "text", "text": b.get("text") or ""})
                    elif b.get("type") == "tool_use":
                        response.append({"type": "tool_use", "id": b.get("id"), "name": b.get("name"), "input": b.get("input")})
                continue

            yield from flush()
            results = [b for b in blocks if b.get("type") == "tool_result"]
            if results:
                for b in results:
                    yield "tool_result", {"tool_use_id": b.get("tool_use_id"), "text": block_text(b.get("content")), "is_error": bool(b.get("is_error")), "timestamp": rec.get("timestamp")}
                continue
            text = clean_prompt("\n".join(b.get("text", "") for b in blocks if b.get("type") == "text"))
            if not text:
                continue
            origin = (rec.get("origin") or {}).get("kind") or ("human" if rec.get("promptSource") else "system")
            yield "prompt", {"text": text, "origin": "human" if origin == "human" else "system", "timestamp": rec.get("timestamp")}
    yield from flush()


def codex_events(path: Path) -> Iterator[Event]:
    """Codex CLI rollouts: response_item records (messages, reasoning, tool calls/outputs) plus turn_context for cwd."""
    cwd = None
    session_id = codex_session_id(path)
    announced = False
    search_results: dict[str, str] = {}
    with path.open(encoding="utf-8") as fh:
        for raw in fh:
            try:
                rec = json.loads(raw)
            except json.JSONDecodeError:
                continue
            kind, p, ts = rec.get("type"), rec.get("payload") or {}, rec.get("timestamp")
            if kind == "session_meta":
                cwd = p.get("cwd") or cwd
                # `id` is this rollout; `session_id` is the parent thread when this is a spawned subagent.
                session_id = p.get("id") or session_id
                announced = True
                yield "session", {"session_id": session_id, "cwd": cwd, "harness": "codex"}
            elif kind == "turn_context":
                cwd = p.get("cwd") or cwd
            elif kind == "event_msg" and p.get("type") == "item_completed":
                item = p.get("item") or {}
                if item.get("type") == "Extension" and item.get("id"):
                    search_results[item["id"]] = json.dumps(item.get("results") or item.get("action") or {})[:4000]
            elif kind == "response_item":
                t = p.get("type")
                if t == "message":
                    text = "\n".join(b.get("text", "") for b in p.get("content", []) if isinstance(b, dict) and b.get("type") in ("input_text", "output_text", "text"))
                    if p.get("role") == "assistant":
                        yield "response", {"blocks": [{"type": "text", "text": text}], "timestamp": ts, "uuid": p.get("id")}
                    elif p.get("role") == "user" and text.strip():
                        injected = text.lstrip().startswith(CODEX_INJECTED_PREFIXES)
                        yield "prompt", {"text": text.strip(), "origin": "system" if injected else "human", "timestamp": ts}
                elif t == "reasoning":
                    summary = "\n".join(s.get("text", "") for s in p.get("summary", []) if isinstance(s, dict))
                    yield "response", {"blocks": [{"type": "thinking", "text": summary, "redacted": not summary}], "timestamp": ts, "uuid": p.get("id")}
                elif t in ("custom_tool_call", "function_call", "local_shell_call"):
                    call_id = p.get("call_id") or p.get("id")
                    tool_input = p.get("input") if t == "custom_tool_call" else p.get("arguments", p.get("action"))
                    yield "response", {"blocks": [{"type": "tool_use", "id": call_id, "name": p.get("name") or t, "input": tool_input}], "timestamp": ts, "uuid": p.get("id")}
                elif t in ("custom_tool_call_output", "function_call_output", "local_shell_call_output"):
                    yield "tool_result", {"tool_use_id": p.get("call_id"), "text": block_text(p.get("output")), "is_error": False, "timestamp": ts}
                elif t == "web_search_call":
                    yield "response", {"blocks": [{"type": "tool_use", "id": p.get("id"), "name": "web_search", "input": p.get("action")}], "timestamp": ts, "uuid": p.get("id")}
                    yield "tool_result", {"tool_use_id": p.get("id"), "text": search_results.get(p.get("id"), "[search results not persisted in rollout]"), "is_error": False, "timestamp": ts}
    if not announced:
        yield "session", {"session_id": session_id, "cwd": cwd, "harness": "codex"}


def prime_events(path: Path) -> Iterator[Event]:
    """Prime Agent (pi-agent v3): a parentId tree; we follow the active branch from the last message to the root."""
    entries: list[dict] = []
    with path.open(encoding="utf-8") as fh:
        for raw in fh:
            try:
                entries.append(json.loads(raw))
            except json.JSONDecodeError:
                continue
    header = next((e for e in entries if e.get("type") == "session"), {})
    yield "session", {"session_id": header.get("id") or path.stem, "cwd": header.get("cwd"), "harness": "prime"}

    by_id = {e["id"]: e for e in entries if e.get("id")}
    leaf = next((e for e in reversed(entries) if e.get("type") in ("message", "custom_message")), None)
    branch: list[dict] = []
    seen: set[str] = set()
    node = leaf
    while node is not None and node.get("id") not in seen:
        seen.add(node["id"])
        branch.append(node)
        node = by_id.get(node.get("parentId") or "")
    for e in reversed(branch):
        ts = e.get("timestamp")
        if e.get("type") == "custom_message":
            yield "prompt", {"text": str(e.get("content") or ""), "origin": "system", "timestamp": ts}
            continue
        if e.get("type") != "message":
            continue
        m = e.get("message") or {}
        role = m.get("role")
        content = m.get("content") or []
        if role == "user":
            text = "\n".join(b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text") if isinstance(content, list) else str(content)
            if text.strip():
                yield "prompt", {"text": text.strip(), "origin": "human", "timestamp": ts}
        elif role == "assistant":
            blocks = []
            for b in content:
                if b.get("type") == "text":
                    blocks.append({"type": "text", "text": b.get("text") or ""})
                elif b.get("type") == "thinking":
                    blocks.append({"type": "thinking", "text": b.get("thinking") or "", "redacted": False})
                elif b.get("type") == "toolCall":
                    blocks.append({"type": "tool_use", "id": b.get("id"), "name": b.get("name"), "input": b.get("arguments")})
            yield "response", {"blocks": blocks, "timestamp": ts, "uuid": e.get("id")}
        elif role == "toolResult":
            yield "tool_result", {"tool_use_id": m.get("toolCallId"), "text": block_text(content), "is_error": bool(m.get("isError")), "timestamp": ts}


def opencode_events(session_id: str) -> Iterator[Event]:
    """OpenCode: message rows (user/assistant) with part rows; each step-start..step-finish is one model response."""
    with opencode_db() as cur:
        row = cur.execute("select directory from session where id = ?", (session_id,)).fetchone()
        if row is None:
            fail(f"opencode session not found: {session_id}")
        messages = cur.execute("select id, time_created, data from message where session_id = ? order by time_created, id", (session_id,)).fetchall()
        parts_by_message: dict[str, list[dict]] = {}
        for mid, data in cur.execute("select message_id, data from part where session_id = ? order by time_created, id", (session_id,)):
            parts_by_message.setdefault(mid, []).append(json.loads(data))
    yield "session", {"session_id": session_id, "cwd": row[0], "harness": "opencode"}

    for mid, created, data in messages:
        m = json.loads(data)
        ts = iso(created / 1000)
        parts = parts_by_message.get(mid, [])
        if m.get("role") == "user":
            text = "\n".join(p.get("text", "") for p in parts if p.get("type") == "text")
            if text.strip():
                yield "prompt", {"text": text.strip(), "origin": "human", "timestamp": ts}
            continue
        blocks: list[dict] = []
        results: list[dict] = []
        for p in parts:
            t = p.get("type")
            if t == "step-start" and blocks:
                yield "response", {"blocks": blocks, "timestamp": ts, "uuid": mid}
                yield from (("tool_result", r) for r in results)
                blocks, results = [], []
            elif t == "text":
                blocks.append({"type": "text", "text": p.get("text") or ""})
            elif t == "reasoning":
                blocks.append({"type": "thinking", "text": p.get("text") or "", "redacted": False})
            elif t == "tool":
                state = p.get("state") or {}
                blocks.append({"type": "tool_use", "id": p.get("callID"), "name": p.get("tool"), "input": state.get("input")})
                results.append({"tool_use_id": p.get("callID"), "text": state.get("output") or state.get("error") or "", "is_error": state.get("status") == "error", "timestamp": ts})
        if blocks:
            yield "response", {"blocks": blocks, "timestamp": ts, "uuid": mid}
            yield from (("tool_result", r) for r in results)


ADAPTERS = {"claude": claude_events, "codex": codex_events, "prime": prime_events, "opencode": opencode_events}


class opencode_db:
    def __enter__(self) -> sqlite3.Cursor:
        self.con = sqlite3.connect(f"file:{STORES['opencode']}?mode=ro", uri=True)
        return self.con.cursor()

    def __exit__(self, *exc) -> None:
        self.con.close()


def opencode_mtime(session_id: str) -> float:
    with opencode_db() as cur:
        row = cur.execute("select max(time_updated) from message where session_id = ?", (session_id,)).fetchone()
    return (row[0] or 0) / 1000


# --- shared turn builder ---------------------------------------------------------------


def build_turns(events: list[Event], max_result_chars: int, max_input_chars: int) -> list[dict]:
    """Group the event stream into human turns: prompt → assistant messages + tool evidence."""
    turns: list[dict] = []
    pending_calls: dict[str, dict] = {}
    current: dict | None = None
    for kind, payload in events:
        if kind == "prompt":
            if payload["origin"] != "human":
                if current is not None:
                    current["evidence"].append({"index": len(current["evidence"]), "tool": "<injected-context>", "input": "", "result": truncate(payload["text"], max_result_chars), "is_error": False, "timestamp": payload.get("timestamp")})
                continue
            current = {"turn": len(turns) + 1, "origin": "human", "timestamp": payload.get("timestamp"), "prompt": payload["text"], "messages": [], "evidence": []}
            turns.append(current)
        elif current is None:
            continue
        elif kind == "response":
            emit_response(current, payload, pending_calls)
        elif kind == "tool_result":
            call = pending_calls.pop(payload.get("tool_use_id"), None) or {"name": "<unknown>", "input": None}
            current["evidence"].append({
                "index": len(current["evidence"]),
                "tool": call["name"],
                "input": truncate(summarise_input(call["name"], call["input"]), max_input_chars),
                "result": truncate(payload.get("text") or "", max_result_chars),
                "is_error": bool(payload.get("is_error")),
                "timestamp": payload.get("timestamp"),
            })
    return turns


def read_turns(transcript: Path, max_result_chars: int, max_input_chars: int) -> list[dict]:
    """Claude Code transcript → turns. Kept as the simple entry point for tests and callers."""
    return build_turns(list(claude_events(transcript)), max_result_chars, max_input_chars)


def emit_response(turn: dict, response: dict, pending_calls: dict[str, dict]) -> None:
    """Append one model response's user-facing messages and tool calls to the turn."""
    blocks = response["blocks"]
    texts = [b for b in blocks if b["type"] == "text" and b["text"].strip()]
    channel = "text"
    if not texts:
        thinking = [b for b in blocks if b["type"] == "thinking"]
        summaries = [b for b in thinking[1:] if b["text"].strip()]
        if thinking and thinking[0].get("redacted") and summaries:
            texts, channel = summaries, "paraphrase"
    for b in texts:
        turn["messages"].append({
            "id": f"t{turn['turn']}-m{len(turn['messages']) + 1}",
            "uuid": response.get("uuid"),
            "timestamp": response.get("timestamp"),
            "channel": channel,
            "after_evidence": len(turn["evidence"]),
            "text": b["text"].strip(),
        })
    for b in blocks:
        if b["type"] == "tool_use":
            pending_calls[b.get("id")] = {"name": b.get("name"), "input": b.get("input"), "timestamp": response.get("timestamp")}


# --- helpers ---------------------------------------------------------------------------


def block_text(content) -> str:
    if isinstance(content, list):
        text = "\n".join(b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") in ("text", "input_text", "output_text"))
        if any(isinstance(b, dict) and b.get("type") in ("image", "input_image") for b in content):
            text += "\n[image omitted]"
        return text
    if isinstance(content, str):
        return content
    return json.dumps(content) if content is not None else ""


def summarise_input(tool: str, tool_input) -> str:
    if isinstance(tool_input, str):
        return tool_input
    if not isinstance(tool_input, dict):
        return json.dumps(tool_input)
    for key in ("command", "code", "cmd", "file_path", "filePath", "path", "pattern", "query", "url", "prompt", "description"):
        if key in tool_input and isinstance(tool_input[key], str):
            extra = {k: v for k, v in tool_input.items() if k != key and isinstance(v, (str, int, bool))}
            extra_s = f" {json.dumps(extra)}" if extra else ""
            return f"{key}={tool_input[key]}{extra_s}"
    return json.dumps(tool_input)


def chunk_turns(turns: list[dict], max_turns: int, max_bytes: int) -> list[list[dict]]:
    """Greedy packets: cut on turn count or on size, so one tool-heavy turn does not swamp a grader.

    A packet is never closed while it holds no assistant message — a grader spawned for
    zero claims is pure cost — and a trailing message-less remainder folds into the last packet.
    """
    chunks: list[list[dict]] = []
    current: list[dict] = []
    current_bytes = 0
    has_message = False
    for turn in turns:
        size = len(json.dumps(turn, ensure_ascii=False))
        if current and has_message and (len(current) >= max_turns or current_bytes + size > max_bytes):
            chunks.append(current)
            current, current_bytes, has_message = [], 0, False
        current.append(turn)
        current_bytes += size
        has_message = has_message or bool(turn["messages"])
    if current and not has_message and chunks:
        chunks[-1].extend(current)
    elif current:
        chunks.append(current)
    return chunks


def select_turns(turns: list[dict], last: int | None, rng: str | None) -> list[dict]:
    if rng:
        lo, _, hi = rng.partition("-")
        lo_i, hi_i = int(lo), int(hi or lo)
        return [t for t in turns if lo_i <= t["turn"] <= hi_i]
    if last:
        return turns[-last:]
    return turns


def clean_prompt(text: str) -> str:
    return SYSTEM_REMINDER_RE.sub("", text).strip()


def truncate(text: str, head: int, tail: int = 400) -> str:
    if len(text) <= head + tail + 40:
        return text
    omitted = len(text) - head - tail
    return f"{text[:head]}\n…[{omitted} chars omitted]…\n{text[-tail:]}"


def iso(epoch_seconds: float) -> str:
    return datetime.fromtimestamp(epoch_seconds, tz=timezone.utc).isoformat(timespec="seconds")


def fail(msg: str) -> None:
    print(f"extract_turns: {msg}", file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    main()
