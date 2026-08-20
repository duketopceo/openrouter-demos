"""Keyless full demo — copy baked results and replay captured stream."""

from __future__ import annotations

import json
import shutil
import time
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from src.dev_stream import sse_event

BAKED_DIR_NAME = "demo/baked"


def baked_root(repo_dir: Path) -> Path:
    return repo_dir / BAKED_DIR_NAME


def is_baked_available(repo_dir: Path) -> bool:
    root = baked_root(repo_dir)
    return (root / "stream.jsonl").is_file() and (root / "results").is_dir()


def load_manifest(repo_dir: Path) -> dict[str, Any]:
    path = baked_root(repo_dir) / "manifest.json"
    if not path.is_file():
        return {"available": False}
    data = json.loads(path.read_text(encoding="utf-8"))
    data["available"] = True
    return data


def materialize_baked(repo_dir: Path) -> list[str]:
    """Copy demo/baked/results/* → results/. Returns relative paths written."""
    src = baked_root(repo_dir) / "results"
    dst = repo_dir / "results"
    if not src.is_dir():
        raise FileNotFoundError(f"baked results missing: {src}")
    dst.mkdir(parents=True, exist_ok=True)
    written: list[str] = []
    for path in sorted(src.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(src)
        target = dst / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
        written.append(str(rel))
    return written


def stream_baked_replay(
    repo_dir: Path,
    *,
    delay_s: float = 0.04,
) -> Iterator[bytes]:
    """Replay captured offline run and materialize results before final done event."""
    stream_path = baked_root(repo_dir) / "stream.jsonl"
    if not stream_path.is_file():
        yield sse_event({"type": "error", "message": "baked stream.jsonl not found — run scripts/bake_demo.py"})
        return

    materialized = False
    for raw in stream_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line:
            continue
        payload = json.loads(line)
        if payload.get("type") == "done" and not materialized:
            files = materialize_baked(repo_dir)
            payload = {**payload, "materialized": files, "message": "Baked results copied to results/"}
            materialized = True
        yield sse_event(payload)
        if payload.get("type") in ("line", "progress", "phase"):
            time.sleep(delay_s)

    if not materialized:
        files = materialize_baked(repo_dir)
        yield sse_event(
            {
                "type": "done",
                "code": 0,
                "baked": True,
                "materialized": files,
                "message": "Baked results copied to results/",
            }
        )
