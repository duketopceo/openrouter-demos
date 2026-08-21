"""Print terminal charts from latest harness results."""

from __future__ import annotations

import sys

from src.terminal_viz import render_openrouter_terminal_dashboard
from src.viz_data import build_viz_payload


def main() -> int:
    payload = build_viz_payload()
    print(render_openrouter_terminal_dashboard(payload))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
