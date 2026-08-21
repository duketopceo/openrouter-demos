#!/usr/bin/env python3
"""Capture offline harness output + results into demo/baked/ for keyless demos."""

from __future__ import annotations

import json
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BAKED = ROOT / "demo" / "baked"
BAKED_RESULTS = BAKED / "results"
STREAM_PATH = BAKED / "stream.jsonl"
MANIFEST_PATH = BAKED / "manifest.json"
VENV_PYTHON = ROOT / ".venv" / "bin" / "python"
PYTHON = str(VENV_PYTHON if VENV_PYTHON.exists() else sys.executable)

sys.path.insert(0, str(ROOT))

from src.dev_stream import sse_event, stream_subprocess  # noqa: E402


def _parse_sse_chunk(chunk: bytes) -> dict | None:
    text = chunk.decode("utf-8").strip()
    if not text.startswith("data:"):
        return None
    return json.loads(text.split("data:", 1)[1].strip())


def main() -> int:
    env = os.environ.copy()
    env["RUN_LIVE"] = "0"
    env["PROGRESS"] = "1"
    env["PROGRESS_JSON"] = "1"

    demos: list[tuple[str, list[str]]] = [
        ("Support Deflection", [PYTHON, "-m", "deflect.harness"]),
        ("GTM Motion", [PYTHON, "-m", "motion.harness"]),
        ("Provider Ops Bakeoff", [PYTHON, "-m", "bakeoff.runner"]),
        ("Caesar Debate", [PYTHON, "-m", "caesar.harness"]),
        ("Guardrail Probe", [PYTHON, "-m", "probe.harness"]),
    ]

    results_dir = ROOT / "results"
    if results_dir.exists():
        shutil.rmtree(results_dir)
    results_dir.mkdir(parents=True, exist_ok=True)

    events: list[dict] = []
    overall = 0

    for label, cmd in demos:
        events.append({"type": "phase", "label": label})
        for chunk in stream_subprocess(cmd, cwd=ROOT, env=env):
            payload = _parse_sse_chunk(chunk)
            if payload:
                events.append(payload)
                if payload.get("type") == "done":
                    overall = max(overall, int(payload.get("code", 1)))

    events.append({"type": "done", "code": overall, "baked": True})

    if BAKED.exists():
        shutil.rmtree(BAKED)
    BAKED_RESULTS.mkdir(parents=True, exist_ok=True)
    shutil.copytree(results_dir, BAKED_RESULTS, dirs_exist_ok=True)

    with STREAM_PATH.open("w", encoding="utf-8") as fh:
        for ev in events:
            fh.write(json.dumps(ev, ensure_ascii=False) + "\n")

    manifest = {
        "version": 1,
        "description": "Offline stub run — no API key. Materialized to results/ on Run Full Demo.",
        "files": [
            str(p.relative_to(BAKED_RESULTS))
            for p in sorted(BAKED_RESULTS.rglob("*"))
            if p.is_file()
        ],
        "event_count": len(events),
        "exit_code": overall,
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    print(f"Wrote {len(manifest['files'])} files under {BAKED_RESULTS}")
    print(f"Stream log: {STREAM_PATH} ({len(events)} events)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
