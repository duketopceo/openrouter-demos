"""Terminal charts: sparklines, ASCII lines, bars, Braille plots — stdlib only."""

from __future__ import annotations

from typing import Sequence

SPARK_CHARS = "▁▂▃▄▅▆▇█"

# Braille dot offsets (2 wide × 4 tall per character)
_BRAILLE_DOTS = (
    (0x01, 0x08),
    (0x02, 0x10),
    (0x04, 0x20),
    (0x40, 0x80),
)


def _scale(values: Sequence[float], lo: float | None = None, hi: float | None = None) -> tuple[float, float]:
    if not values:
        return 0.0, 1.0
    lo = min(values) if lo is None else lo
    hi = max(values) if hi is None else hi
    if hi <= lo:
        hi = lo + 1.0
    return lo, hi


def sparkline(values: Sequence[float], width: int | None = None) -> str:
    """Compact inline sparkline using Unicode block shading."""
    if not values:
        return ""
    lo, hi = _scale(values)
    chars = list(SPARK_CHARS)
    n = len(chars) - 1
    series = list(values)
    if width is not None and width > 0 and len(series) > width:
        step = len(series) / width
        series = [series[int(i * step)] for i in range(width)]
    out: list[str] = []
    for v in series:
        idx = int(round((float(v) - lo) / (hi - lo) * n))
        out.append(chars[max(0, min(n, idx))])
    return "".join(out)


def horizontal_bar(
    label: str,
    value: float,
    max_value: float,
    *,
    width: int = 24,
    fill: str = "█",
    empty: str = "░",
) -> str:
    """Single horizontal bar: label + shaded bar + numeric value."""
    if max_value <= 0:
        max_value = 1.0
    filled = int(round(min(1.0, max(0.0, value / max_value)) * width))
    bar = fill * filled + empty * (width - filled)
    return f"{label:<14} {bar} {value:>8.2f}"


def ascii_line_chart(
    series: list[tuple[str, Sequence[float]]],
    *,
    height: int = 8,
    width: int = 48,
    colors: tuple[str, ...] = ("*", "+", "x"),
) -> list[str]:
    """Multi-series ASCII line chart. Returns lines to print."""
    if not series or all(not s[1] for s in series):
        return ["(no data)"]

    all_vals = [float(v) for _, vals in series for v in vals]
    lo, hi = _scale(all_vals)
    n = max(len(vals) for _, vals in series)
    n = max(n, 2)

    grids: list[list[list[str | None]]] = []
    for _name, vals in series:
        row: list[list[str | None]] = [[None] * n for _ in range(height)]
        for i, v in enumerate(vals):
            col = int(i / max(len(vals) - 1, 1) * (n - 1))
            row_idx = height - 1 - int((float(v) - lo) / (hi - lo) * (height - 1))
            row_idx = max(0, min(height - 1, row_idx))
            row[row_idx][col] = "·"
        grids.append(row)

    merged: list[list[str]] = []
    markers = list(colors)
    for r in range(height):
        line_chars: list[str] = []
        for c in range(n):
            ch = None
            for si, grid in enumerate(grids):
                if grid[r][c]:
                    ch = markers[si % len(markers)]
            line_chars.append(ch or " ")
        y_val = hi - (hi - lo) * r / max(height - 1, 1)
        merged.append(f"{y_val:6.1f} │{''.join(line_chars)}")

    merged.append(f"{'':>6} └{'─' * n}")
    legend = "  ".join(f"{name} ({markers[i % len(markers)]})" for i, (name, _) in enumerate(series))
    merged.append(legend)
    return merged


def _braille_set(grid: list[list[int]], px: int, py: int, max_x: int, max_y: int) -> None:
    px = max(0, min(max_x - 1, px))
    py = max(0, min(max_y - 1, py))
    col = px // 2
    row = py // 4
    dx = px % 2
    dy = py % 4
    grid[row][col] |= _BRAILLE_DOTS[dy][dx]


def braille_line_chart(
    series: list[tuple[str, Sequence[float]]],
    *,
    width: int = 40,
    height: int = 8,
) -> list[str]:
    """High-resolution Braille line chart (2×4 dots per cell)."""
    if not series or all(not s[1] for s in series):
        return ["(no data)"]

    pixel_w = width * 2
    pixel_h = height * 4
    all_vals = [float(v) for _, vals in series for v in vals]
    lo, hi = _scale(all_vals)

    lines_out: list[str] = []
    for name, vals in series:
        if not vals:
            continue
        grid = [[0] * width for _ in range(height)]
        pts = list(vals)
        for i in range(len(pts) - 1):
            x0 = int(i / max(len(pts) - 1, 1) * (pixel_w - 1))
            x1 = int((i + 1) / max(len(pts) - 1, 1) * (pixel_w - 1))
            y0 = pixel_h - 1 - int((float(pts[i]) - lo) / (hi - lo) * (pixel_h - 1))
            y1 = pixel_h - 1 - int((float(pts[i + 1]) - lo) / (hi - lo) * (pixel_h - 1))
            steps = max(abs(x1 - x0), abs(y1 - y0), 1)
            for s in range(steps + 1):
                t = s / steps
                px = int(x0 + (x1 - x0) * t)
                py = int(y0 + (y1 - y0) * t)
                _braille_set(grid, px, py, pixel_w, pixel_h)
        braille_rows = ["".join(chr(0x2800 + cell) for cell in row) for row in grid]
        lines_out.append(f"  {name}")
        lines_out.extend(f"  {row}" for row in braille_rows)
        lines_out.append("")
    return lines_out


def render_openrouter_terminal_dashboard(payload: dict) -> str:
    """Build full terminal dashboard from /api/viz-data-shaped payload."""
    lines: list[str] = [
        "",
        "╔══════════════════════════════════════════════════════════════╗",
        "║  OpenRouter · terminal observability (gateway I/O only)      ║",
        "╚══════════════════════════════════════════════════════════════╝",
        "",
        "── 01 · token envelope (sparklines) ──",
    ]

    cases = payload.get("token_cases") or []
    if cases:
        prompt = [float(c.get("prompt_tokens") or 0) for c in cases]
        comp = [float(c.get("completion_tokens") or 0) for c in cases]
        lines.append(f"  prompt      {sparkline(prompt)}  ({int(sum(prompt))} total)")
        lines.append(f"  completion  {sparkline(comp)}  ({int(sum(comp))} total)")
    else:
        lines.append("  (run harnesses first)")

    lines.extend(["", "── 02 · token bars ──"])
    if cases:
        mx = max(max(c.get("prompt_tokens", 0) for c in cases), max(c.get("completion_tokens", 0) for c in cases), 1)
        sample = cases[0]
        lines.append(horizontal_bar("prompt", float(sample.get("prompt_tokens", 0)), float(mx)))
        lines.append(horizontal_bar("completion", float(sample.get("completion_tokens", 0)), float(mx)))

    lines.extend(["", "── 03 · bakeoff (ASCII lines) ──"])
    comp = payload.get("bakeoff_compare") or {}
    a_cases = payload.get("bakeoff_cases_a") or []
    b_cases = payload.get("bakeoff_cases_b") or []
    if a_cases and b_cases:
        lines.extend(
            ascii_line_chart(
                [
                    (str(comp.get("a", {}).get("model") or "model A"), [c.get("quality", 0) for c in a_cases]),
                    (str(comp.get("b", {}).get("model") or "model B"), [c.get("quality", 0) for c in b_cases]),
                ],
                height=6,
                width=min(40, len(a_cases)),
            )
        )
    else:
        a, b = comp.get("a") or {}, comp.get("b") or {}
        lines.extend(
            ascii_line_chart(
                [
                    ("quality A/B", [a.get("quality", 0), b.get("quality", 0)]),
                    ("latency/100", [(a.get("mean_latency_ms") or 0) / 100, (b.get("mean_latency_ms") or 0) / 100]),
                ],
                height=5,
                width=20,
            )
        )

    lines.extend(["", "── 04 · routing depth (Braille) ──"])
    flow = payload.get("tool_flow") or []
    tokens = [float(n.get("tokens") or 0) for n in flow]
    tools = [float(len(n.get("tool_calls") or [])) for n in flow]
    if tokens:
        lines.extend(braille_line_chart([("tokens", tokens), ("tool_calls", tools)], width=36, height=5))
    else:
        lines.append("  (no trace data)")

    lines.extend(
        [
            "",
            "  Not available via gateway: attention weights, hidden states, logits.",
            "",
        ]
    )
    return "\n".join(lines)
