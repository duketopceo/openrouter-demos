"""Tests for terminal chart helpers."""

from __future__ import annotations

from src.terminal_viz import (
    ascii_line_chart,
    braille_line_chart,
    horizontal_bar,
    render_openrouter_terminal_dashboard,
    sparkline,
)
from src.viz_data import build_viz_payload


def test_sparkline_non_empty() -> None:
    s = sparkline([1, 4, 2, 8, 3])
    assert len(s) == 5
    assert all(c in "▁▂▃▄▅▆▇█" for c in s)


def test_horizontal_bar_contains_fill() -> None:
    line = horizontal_bar("prompt", 50, 100, width=10)
    assert "█" in line
    assert "prompt" in line


def test_ascii_line_chart_returns_axis() -> None:
    lines = ascii_line_chart([("a", [1, 2, 3])], height=4, width=10)
    assert any("│" in ln for ln in lines)


def test_braille_line_chart_unicode() -> None:
    lines = braille_line_chart([("s", [0, 1, 2, 1, 0])], width=10, height=3)
    joined = "\n".join(lines)
    assert any(ord(c) >= 0x2800 for c in joined)


def test_render_dashboard_from_payload() -> None:
    text = render_openrouter_terminal_dashboard(build_viz_payload())
    assert "token envelope" in text
    assert "Not available via gateway" in text
