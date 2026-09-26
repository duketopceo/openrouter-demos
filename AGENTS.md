# openrouter-demos — agent notes

A Python workspace of offline-capable demos and research harnesses built on
OpenRouter: `deflect` (support deflection), `motion` (GTM motion), `bakeoff`
(provider bakeoff), and `caesar` (debate). Plus `probe/`, `viz/`, `src/`, a
`dev_server.py`, and a `dashboard/`. `README.md` and `ROADMAP.md` are the user
docs; this file is what an agent needs and they do not say.

## Commands

```bash
python -m venv .venv && .venv/bin/pip install -r requirements.txt

# The whole suite, offline. RUN_LIVE=0 is the switch that keeps every
# harness from reaching the network.
RUN_LIVE=0 python -m pytest            # 63 passed

# CI also smoke-runs each harness as a module, after the suite:
RUN_LIVE=0 python -m deflect.harness
RUN_LIVE=0 python -m motion.harness
RUN_LIVE=0 python -m bakeoff.runner
RUN_LIVE=0 python -m caesar.harness
```

`requirements.txt` is two pins and nothing else: `httpx==0.28.1`,
`pytest==8.4.2`. There is no lockfile, no linter, and no formatter. Do not add
one as part of an unrelated change.

## The pytest config is in `pyproject.toml` — read it before debugging imports

```toml
[tool.pytest.ini_options]
pythonpath = ["."]        # this is why `import deflect` resolves in tests
testpaths = ["tests"]     # bare `pytest` only collects tests/
addopts = "-q"
filterwarnings = ["ignore::DeprecationWarning"]
```

Consequences worth knowing:

- `pythonpath = ["."]` is why the top-level packages import as `deflect`,
  `motion`, `bakeoff`, `caesar` rather than as installed distributions. They
  are **not** pip-installed; adding them to `dependencies` would be wrong.
- `addopts = "-q"` means you do not need to pass `-q` yourself.
- Deprecation warnings are filtered. If you are chasing a warning that
  "should" appear, it is being swallowed here.
- `requires-python = ">=3.11"`; CI pins `3.12`.

## CI, and what it means for your change

`.github/workflows/ci.yml` runs on push to `main` and on PRs to `main`:
install `requirements.txt`, then `RUN_LIVE=0 pytest -q`, then the four harness
smokes. **A change that passes `pytest` but breaks a harness still breaks
CI** — run the five commands, not just the first.

`.github/workflows/supply-chain-security.yml` runs OSV-Scanner with
`fail-on-vuln: true`, plus `pip-audit -r requirements.txt` and Socket, on push,
on PRs, and weekly on Mondays. Bumping a pin can therefore fail a build for a
published CVE even when every test passes. That is intended, not a flake.

## Offline discipline is the point

`RUN_LIVE=0` is not a CI convenience. The harnesses are built to run with no
network and no keys, and `tests/` asserts that. If you add a code path that
egresses, gate it behind the live flag and keep offline the default. Do not
"temporarily" un-gate it to make a test pass.

`.env.example` documents the environment. There is no `.env` in the repo and
none should be committed.

## Layout

| Path | What it is |
|---|---|
| `deflect/`, `motion/`, `caesar/`, `bakeoff/` | The four harnesses. Each is an importable package *and* a `python -m` entry point via its `harness.py` / `runner.py`. |
| `deflect/cases.jsonl`, `caesar/cases.jsonl`, `bakeoff/cases.jsonl` | Case fixtures, one per harness. |
| `*/fixtures/` | Per-harness JSON fixtures. Tests read these, not the network. |
| `bakeoff/baseline.json`, `bakeoff/sweep.py` | The bakeoff baseline and its sweep. |
| `probe/` | Probe generation and replay. |
| `viz/`, `dashboard/` | Rendering and the dashboard. |
| `tests/` | `pytest` suite, one module per area. |
| `bin/`, `scripts/`, `dev_server.py` | CLI wrappers, dev helpers, local dev server. |
| `demo/` | Runnable demo entry points, not a library. |
| `docs/` | Design notes. |
