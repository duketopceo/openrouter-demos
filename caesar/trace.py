"""Dense per-turn / per-match records. JSONL under results/caesar/ (gitignored)."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

SECRET_RE = re.compile(
    r"(?:"
    r"sk-or-[A-Za-z0-9_\-]+|"
    r"rk_(?:live|test)_[A-Za-z0-9_\-]+|"
    r"Bearer\s+\S+|"
    r"(?:OPENROUTER_API_KEY|ROUTKIT_API_KEY|API_KEY)\s*=\s*\S+"
    r")",
    re.I,
)

TURN_REQUIRED = (
    "round",
    "speaker",
    "role",
    "model",
    "text",
    "latency_ms",
    "prompt_tokens",
    "completion_tokens",
    "cost_usd",
    "chars",
    "searched",
    "info_gathered",
    "claims",
    "points",
    "grounding",
    "concession",
)

MATCH_REQUIRED = (
    "id",
    "topic",
    "model_a",
    "model_b",
    "caesar_model",
    "end",
    "winner",
    "reason",
    "scores",
    "rounds",
    "total_cost_usd",
    "total_latency_ms",
    "turns",
)


def scrub_text(text: str) -> str:
    return SECRET_RE.sub("[REDACTED]", text)


def scrub(obj: Any) -> Any:
    if isinstance(obj, str):
        return scrub_text(obj)
    if isinstance(obj, list):
        return [scrub(x) for x in obj]
    if isinstance(obj, dict):
        return {k: scrub(v) for k, v in obj.items()}
    return obj


def assert_turn_schema(turn: dict[str, Any]) -> None:
    missing = [k for k in TURN_REQUIRED if k not in turn]
    if missing:
        raise ValueError(f"turn missing fields: {missing}")


def assert_match_schema(match: dict[str, Any]) -> None:
    missing = [k for k in MATCH_REQUIRED if k not in match]
    if missing:
        raise ValueError(f"match missing fields: {missing}")
    if not isinstance(match["turns"], list):
        raise ValueError("match.turns must be a list")
    for turn in match["turns"]:
        assert_turn_schema(turn)


def write_match(match: dict[str, Any], results_dir: Path) -> Path:
    """Scrub secrets, validate schema, write pretty JSON + append jsonl."""
    cleaned = scrub(match)
    assert_match_schema(cleaned)
    results_dir.mkdir(parents=True, exist_ok=True)
    cid = str(cleaned["id"])
    path = results_dir / f"{cid}.json"
    path.write_text(json.dumps(cleaned, indent=2) + "\n", encoding="utf-8")
    jsonl_path = results_dir / "matches.jsonl"
    with jsonl_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(cleaned, ensure_ascii=False) + "\n")
    return path
