"""Tests for viz payload builder."""

from __future__ import annotations

from src.viz_data import build_viz_payload


def test_build_viz_payload_has_three_sections() -> None:
    data = build_viz_payload()
    assert data["token_cases"]
    assert data["bakeoff_compare"]["a"]
    assert data["tool_flow"]
    assert data["openrouter_fields"]["not_available"]
