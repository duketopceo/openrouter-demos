"""SSE streaming helpers for dev_server harness runs."""

from __future__ import annotations

import json
import subprocess
import time
from collections.abc import Iterator
from pathlib import Path
from typing import Any, Callable


def sse_event(payload: dict[str, Any]) -> bytes:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n".encode("utf-8")


def stream_subprocess(
    cmd: list[str],
    *,
    cwd: Path,
    env: dict[str, str],
) -> Iterator[bytes]:
    run_env = {
        **env,
        "PROGRESS": "1",
        "PROGRESS_JSON": "1",
        "PYTHONUNBUFFERED": "1",
    }
    proc = subprocess.Popen(
        cmd,
        cwd=str(cwd),
        env=run_env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    if proc.stdout is None:
        yield sse_event({"type": "error", "message": "failed to capture subprocess output"})
        return
    for raw in proc.stdout:
        line = raw.rstrip("\n")
        if line.startswith("{") and '"event"' in line:
            try:
                payload = json.loads(line)
                if payload.get("event") == "progress":
                    yield sse_event({"type": "progress", **payload})
                    continue
                if payload.get("event") == "progress_done":
                    yield sse_event({"type": "progress_done", **payload})
                    continue
            except json.JSONDecodeError:
                pass
        yield sse_event({"type": "line", "text": line})
    code = proc.wait()
    yield sse_event({"type": "done", "code": code})


def run_caesar_live(
    body: dict[str, Any],
    *,
    repo_dir: Path,
    env: dict[str, str],
    emit: Callable[[dict[str, Any]], None],
) -> None:
    from caesar.debate import run_debate
    from caesar.harness import build_clients
    from caesar.topics import list_presets
    from caesar.trace import write_match

    category = str(body.get("category") or "english").strip().lower()
    preset_id = str(body.get("preset_id") or "").strip()
    topic = str(body.get("topic") or "").strip()
    side_a = str(body.get("side_a") or "Side A").strip()
    side_b = str(body.get("side_b") or "Side B").strip()
    max_rounds = int(body.get("max_rounds") or 3)

    if preset_id:
        for preset in list_presets():
            if preset["id"] == preset_id:
                topic = str(preset["topic"])
                side_a = str(preset["side_a"])
                side_b = str(preset["side_b"])
                break

    if not topic:
        raise ValueError("topic is required (or choose a preset)")

    if max_rounds < 1 or max_rounds > 12:
        raise ValueError("max_rounds must be between 1 and 12")

    case_id = f"live-{int(time.time())}"
    case = {
        "id": case_id,
        "topic": topic,
        "side_a": side_a,
        "side_b": side_b,
        "max_rounds": max_rounds,
        "expected_end": "max_rounds",
    }

    want_live = env.get("RUN_LIVE", "0") == "1"
    clients = build_clients(live=want_live)

    emit({"type": "start", "case_id": case_id, "topic": topic, "max_rounds": max_rounds})

    def on_turn(turn: dict[str, Any]) -> None:
        emit({"type": "turn", "turn": turn})

    match = run_debate(
        case,
        **clients,
        max_rounds=max_rounds,
        on_turn=on_turn,
        judge_each_turn=False,
        caesar_opens=True,
        category=category if category in ("english", "math", "routekit") else "english",
    )
    out_dir = repo_dir / "results" / "caesar"
    write_match(match, out_dir)
    emit(
        {
            "type": "done",
            "case_id": case_id,
            "path": f"/results/caesar/{case_id}.json",
            "winner": match.get("winner"),
            "end": match.get("end"),
            "reason": match.get("reason"),
            "rounds": match.get("rounds"),
        }
    )
