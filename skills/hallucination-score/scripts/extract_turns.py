#!/usr/bin/env python3
"""Phase 1 of the hallucination-score skill: the deterministic transcript extract.

    python3 <skill dir>/scripts/extract_turns.py [--last N] [--chunk-turns 8]

Packets land in ``~/.claude/hallucination-scores/<session>/packets/`` by default: outside
the repo, because they carry session content that must never be committed.

Reads the Claude Code session transcript (``~/.claude/projects/<cwd-slug>/<session>.jsonl``)
and writes one "grading packet" JSON per chunk of turns. A packet is what a benchmark
grader would call the *evidence set*: every user-facing assistant message, plus every
tool call and tool result in the same turn, in order, so the grader can check each
claim against what the model actually observed (RAGTruth-style faithfulness) before
it goes to the live repo (SAFE-style retrieval).

Only user-facing text is graded. ``thinking`` blocks are dropped: benchmarks score the
answer, not the scratchpad. One exception: Claude Code (seen on 2.1.273) sometimes
persists prose the assistant wrote between tool calls not as a ``text`` block but as a
short paraphrase in a second ``thinking`` block, after the signature-only redacted one.
Those are the only surviving record of a user-visible message, so they are emitted as
messages with ``channel: "paraphrase"`` and counted separately in the index. Sidechain
(subagent) records are dropped; their conclusions re-enter the main chain as an
``Agent`` tool result and are graded there as evidence the assistant chose to relay.
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys
from pathlib import Path

SYSTEM_REMINDER_RE = re.compile(r"<system-reminder>.*?</system-reminder>", re.S)
PROJECTS_DIR = Path.home() / ".claude" / "projects"
SCORES_DIR = Path.home() / ".claude" / "hallucination-scores"


def main() -> None:
    args = parse_args()
    transcript = resolve_transcript(args.file, args.session)
    turns = read_turns(transcript, args.max_result_chars, args.max_input_chars)
    if not turns:
        fail(f"no human turns found in {transcript}")

    selected = select_turns(turns, args.last, args.turns)
    if not selected:
        fail("turn selection matched nothing")

    session_id = args.session or turns[0]["session_id"]
    out_dir = Path(args.out_dir) if args.out_dir else SCORES_DIR / session_id / "packets"
    out_dir.mkdir(parents=True, exist_ok=True)
    for stale in out_dir.glob("packet-*.json"):
        stale.unlink()

    prompts_index = [
        {"turn": t["turn"], "prompt": truncate(t["prompt"], 240), "origin": t["origin"]}
        for t in turns
    ]
    chunks = chunk_turns(selected, args.chunk_turns, args.max_packet_bytes)
    written = []
    for n, chunk in enumerate(chunks, start=1):
        packet = {
            "session_id": session_id,
            "transcript": str(transcript),
            "cwd": chunk[0]["cwd"],
            "chunk": n,
            "chunks_total": len(chunks),
            "turn_range": [chunk[0]["turn"], chunk[-1]["turn"]],
            "all_prompts": prompts_index,
            "turns": [strip_internal(t) for t in chunk],
        }
        path = out_dir / f"packet-{n:03d}.json"
        path.write_text(json.dumps(packet, indent=1, ensure_ascii=False))
        written.append({"path": str(path), "turn_range": packet["turn_range"], "bytes": path.stat().st_size})

    index = {
        "session_id": session_id,
        "transcript": str(transcript),
        "cwd": turns[0]["cwd"],
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
    p.add_argument("--session", default=os.environ.get("CLAUDE_CODE_SESSION_ID"), help="session id (default: $CLAUDE_CODE_SESSION_ID)")
    p.add_argument("--file", help="explicit transcript .jsonl (overrides --session lookup)")
    p.add_argument("--out-dir", help="directory for packet-NNN.json + index.json (default ~/.claude/hallucination-scores/<session>/packets)")
    p.add_argument("--last", type=int, help="only the last N human turns")
    p.add_argument("--turns", help="inclusive turn range, e.g. 4-9")
    p.add_argument("--chunk-turns", type=int, default=8, help="max turns per packet (default 8)")
    p.add_argument("--max-packet-bytes", type=int, default=150_000, help="start a new packet before exceeding this size; one oversize turn still gets its own packet (default 150000)")
    p.add_argument("--max-result-chars", type=int, default=1500, help="tool result excerpt size (head; a 400-char tail is kept too)")
    p.add_argument("--max-input-chars", type=int, default=600, help="tool input excerpt size")
    return p.parse_args()


def resolve_transcript(file: str | None, session: str | None) -> Path:
    if file:
        path = Path(file).expanduser()
        if not path.is_file():
            fail(f"transcript not found: {path}")
        return path
    if not session:
        fail("no session: set $CLAUDE_CODE_SESSION_ID, pass --session, or pass --file")
    hits = glob.glob(str(PROJECTS_DIR / "*" / f"{session}.jsonl"))
    if len(hits) != 1:
        fail(f"expected exactly one transcript for session {session}, found {len(hits)}: {hits}")
    return Path(hits[0])


def read_turns(transcript: Path, max_result_chars: int, max_input_chars: int) -> list[dict]:
    """Group the append-only log into human turns: prompt → assistant messages + tool evidence."""
    turns: list[dict] = []
    pending_calls: dict[str, dict] = {}
    current: dict | None = None
    # One API response is logged as several records sharing a requestId, one block each.
    # Buffer them so the text-vs-paraphrase decision sees the whole response.
    response: list[tuple[dict, dict]] = []
    response_id: str | None = None

    def flush_response() -> None:
        nonlocal response, response_id
        if response and current is not None:
            emit_response(current, response, pending_calls)
        response, response_id = [], None

    with transcript.open(encoding="utf-8") as fh:
        for raw in fh:
            try:
                rec = json.loads(raw)
            except json.JSONDecodeError:
                continue
            kind = rec.get("type")
            if kind not in ("user", "assistant") or rec.get("isSidechain"):
                continue
            message = rec.get("message") or {}
            content = message.get("content")
            blocks = content if isinstance(content, list) else [{"type": "text", "text": content or ""}]

            if kind == "assistant":
                if current is None:
                    continue
                if rec.get("requestId") != response_id:
                    flush_response()
                    response_id = rec.get("requestId")
                response.extend((rec, b) for b in blocks)
                continue

            flush_response()
            if kind == "user":
                results = [b for b in blocks if b.get("type") == "tool_result"]
                if results:
                    if current is None:
                        continue
                    for block in results:
                        call = pending_calls.pop(block.get("tool_use_id"), None)
                        current["evidence"].append(evidence_item(call, block, rec, max_result_chars, max_input_chars))
                    continue
                prompt = clean_prompt("\n".join(b.get("text", "") for b in blocks if b.get("type") == "text"))
                if not prompt:
                    continue
                origin = (rec.get("origin") or {}).get("kind") or ("human" if rec.get("promptSource") else "system")
                if origin != "human" and current is not None:
                    # Hook output, task notifications, etc: context the assistant saw, not a new turn.
                    current["evidence"].append({
                        "tool": "<injected-context>",
                        "input": "",
                        "result": truncate(prompt, max_result_chars),
                        "is_error": False,
                        "timestamp": rec.get("timestamp"),
                    })
                    continue
                current = {
                    "turn": len(turns) + 1,
                    "session_id": rec.get("sessionId") or rec.get("session_id"),
                    "cwd": rec.get("cwd"),
                    "origin": origin,
                    "timestamp": rec.get("timestamp"),
                    "prompt": prompt,
                    "messages": [],
                    "evidence": [],
                }
                turns.append(current)
    flush_response()
    return turns


def emit_response(turn: dict, response: list[tuple[dict, dict]], pending_calls: dict[str, dict]) -> None:
    """Append one API response's user-facing messages and tool calls to the turn."""
    texts = [(rec, b) for rec, b in response if b.get("type") == "text" and (b.get("text") or "").strip()]
    channel = "text"
    if not texts:
        thinking = [(rec, b) for rec, b in response if b.get("type") == "thinking"]
        redacted_first = bool(thinking) and not (thinking[0][1].get("thinking") or "") and thinking[0][1].get("signature")
        summaries = [(rec, b) for rec, b in thinking[1:] if (b.get("thinking") or "").strip()]
        if redacted_first and summaries:
            texts = [(rec, {"text": b["thinking"]}) for rec, b in summaries]
            channel = "paraphrase"
    for rec, block in texts:
        turn["messages"].append({
            "id": f"t{turn['turn']}-m{len(turn['messages']) + 1}",
            "uuid": rec.get("uuid"),
            "timestamp": rec.get("timestamp"),
            "channel": channel,
            "after_evidence": len(turn["evidence"]),
            "text": block["text"].strip(),
        })
    for rec, block in response:
        if block.get("type") == "tool_use":
            pending_calls[block.get("id")] = {
                "name": block.get("name"),
                "input": block.get("input"),
                "timestamp": rec.get("timestamp"),
            }


def evidence_item(call: dict | None, block: dict, rec: dict, max_result_chars: int, max_input_chars: int) -> dict:
    content = block.get("content")
    if isinstance(content, list):
        text = "\n".join(b.get("text", "") for b in content if b.get("type") == "text")
        if any(b.get("type") == "image" for b in content):
            text += "\n[image omitted]"
    else:
        text = content if isinstance(content, str) else json.dumps(content)
    call = call or {"name": "<unknown>", "input": None}
    return {
        "tool": call["name"],
        "input": truncate(summarise_input(call["name"], call["input"]), max_input_chars),
        "result": truncate(text, max_result_chars),
        "is_error": bool(block.get("is_error")),
        "timestamp": rec.get("timestamp"),
    }


def summarise_input(tool: str, tool_input) -> str:
    if not isinstance(tool_input, dict):
        return json.dumps(tool_input)
    for key in ("command", "file_path", "pattern", "query", "url", "prompt", "description"):
        if key in tool_input and isinstance(tool_input[key], str):
            extra = {k: v for k, v in tool_input.items() if k != key and isinstance(v, (str, int, bool))}
            extra_s = f" {json.dumps(extra)}" if extra else ""
            return f"{key}={tool_input[key]}{extra_s}"
    return json.dumps(tool_input)


def strip_internal(turn: dict) -> dict:
    out = {k: v for k, v in turn.items() if k not in ("session_id", "cwd")}
    out["evidence"] = [{"index": i, **item} for i, item in enumerate(out["evidence"])]
    return out


def chunk_turns(turns: list[dict], max_turns: int, max_bytes: int) -> list[list[dict]]:
    """Greedy packets: cut on turn count or on size, so one tool-heavy turn does not swamp a grader."""
    chunks: list[list[dict]] = []
    current: list[dict] = []
    current_bytes = 0
    for turn in turns:
        size = len(json.dumps(turn, ensure_ascii=False))
        if current and (len(current) >= max_turns or current_bytes + size > max_bytes):
            chunks.append(current)
            current, current_bytes = [], 0
        current.append(turn)
        current_bytes += size
    if current:
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


def fail(msg: str) -> None:
    print(f"extract_turns: {msg}", file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    main()
