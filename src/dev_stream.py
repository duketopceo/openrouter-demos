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


def _emit_new_runs(since_id: int) -> Iterator[bytes]:
    from src.db import get_recent_runs

    for row in get_recent_runs(30):
        rid = int(row.get("id") or 0)
        if rid > since_id:
            yield sse_event(
                {
                    "type": "run_saved",
                    "run_id": rid,
                    "demo": row.get("demo"),
                    "model": row.get("model"),
                }
            )


def stream_run_batch(
    body: dict[str, Any],
    *,
    repo_dir: Path,
    venv_python: str,
    env: dict[str, str],
) -> Iterator[bytes]:
    """Run selected harnesses; bakeoff + multiple models triggers sweep."""
    from src.db import get_recent_runs

    tests = [str(t).strip() for t in (body.get("tests") or []) if str(t).strip()]
    models = [str(m).strip() for m in (body.get("models") or []) if str(m).strip()]
    if not tests:
        yield sse_event({"type": "error", "message": "no tests selected"})
        yield sse_event({"type": "done", "code": 1, "message": "nothing to run"})
        return
    if not models:
        yield sse_event({"type": "error", "message": "no models selected"})
        yield sse_event({"type": "done", "code": 1, "message": "nothing to run"})
        return

    last_id = max((int(r.get("id") or 0) for r in get_recent_runs(1)), default=0)

    module_map = {
        "deflect": "deflect.harness",
        "motion": "motion.harness",
        "bakeoff": "bakeoff.runner",
        "caesar": "caesar.harness",
        "probe": "probe.harness",
    }
    labels = {
        "deflect": "Support Deflection",
        "motion": "GTM Motion",
        "bakeoff": "Provider Ops Bakeoff",
        "caesar": "Caesar Debate",
        "probe": "Guardrail Probe",
    }

    run_env = dict(env)
    if models:
        run_env["OPENROUTER_MODEL"] = models[0]
        run_env["OPENROUTER_MODEL_A"] = models[0]
        run_env["OPENROUTER_MODEL_B"] = models[1] if len(models) > 1 else models[0]
        run_env["CAESAR_MODEL"] = models[0]

    overall = 0
    for test in tests:
        label = labels.get(test, test)
        yield sse_event({"type": "phase", "label": label})

        if test == "bakeoff" and len(models) > 1:
            run_env["BAKEOFF_SWEEP_MODELS"] = ",".join(models)
            cmd = [venv_python, "-m", "bakeoff.sweep"]
        else:
            mod = module_map.get(test)
            if not mod:
                yield sse_event({"type": "error", "message": f"unknown test: {test}"})
                overall = 1
                continue
            cmd = [venv_python, "-m", mod]

        for chunk in stream_subprocess(cmd, cwd=repo_dir, env=run_env):
            yield chunk
            if chunk.startswith(b"data:") and b'"done"' in chunk:
                try:
                    payload = json.loads(chunk.decode().split("data:", 1)[1].strip())
                    if payload.get("type") == "done":
                        overall = max(overall, int(payload.get("code", 1)))
                except Exception:
                    pass

        for ev in _emit_new_runs(last_id):
            yield ev
            try:
                payload = json.loads(ev.decode().split("data:", 1)[1].strip())
                if payload.get("type") == "run_saved":
                    last_id = max(last_id, int(payload.get("run_id", last_id)))
            except Exception:
                pass

    yield sse_event(
        {
            "type": "done",
            "code": overall,
            "message": "Batch complete" if overall == 0 else f"Batch finished with code {overall}",
        }
    )
