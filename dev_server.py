#!/usr/bin/env python3
"""
OpenRouter Demos Local Dev Server & Interactive Dashboard
Serves a local web interface to trigger, configure, and inspect all OpenRouter demos:
1. Support Deflection (deflect)
2. GTM Motion (motion)
3. Provider Ops Bakeoff (bakeoff)
4. Caesar Model Debate (caesar)
5. Guardrail / upstream block probe (probe)
"""

import http.server
import socketserver
import json
import os
import subprocess
import time
from pathlib import Path

from caesar.topics import TOPIC_PRESETS, list_presets
from src.baked_demo import is_baked_available, load_manifest, stream_baked_replay
from src.db import get_recent_runs, get_run_by_id, get_runs_for_chart
from src.dev_stream import run_caesar_live, sse_event, stream_run_batch, stream_subprocess

PORT = 8080
REPO_DIR = Path(__file__).parent.resolve()
RUN_CENTER_HTML = REPO_DIR / "dashboard" / "run_center.html"
VENV_PYTHON = REPO_DIR / ".venv" / "bin" / "python"

if not VENV_PYTHON.exists():
    VENV_PYTHON = "python3"

def load_env_file():
    env_paths = [REPO_DIR / ".env", Path.home() / ".env"]
    env_vars = {}
    for p in env_paths:
        if p.exists():
            with open(p, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        env_vars[k.strip()] = v.strip().strip("'\"")
    return env_vars


def _jsonl_count(path: Path) -> int:
    if not path.is_file():
        return 0
    return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())


def build_dashboard_meta() -> dict:
    harnesses = [
        ("deflect", "Support Deflection", REPO_DIR / "deflect" / "cases.jsonl", "deflect.json"),
        ("motion", "GTM Motion", REPO_DIR / "motion" / "cases.jsonl", "motion.json"),
        ("bakeoff", "Provider Ops Bakeoff", REPO_DIR / "bakeoff" / "cases.jsonl", "bakeoff.json"),
        ("caesar", "Caesar Debate", REPO_DIR / "caesar" / "cases.jsonl", None),
        ("probe", "Guardrail Probe", REPO_DIR / "probe" / "cases.jsonl", "guardrail_probe.json"),
    ]
    results_dir = REPO_DIR / "results"
    result_files: list[dict[str, str]] = []
    if results_dir.is_dir():
        for p in sorted(results_dir.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True):
            result_files.append({"id": p.name, "path": f"/results/{p.name}"})

    math_presets = len(TOPIC_PRESETS.get("math", []))
    return {
        "harnesses": [
            {
                "id": hid,
                "label": label,
                "cases": _jsonl_count(cases_path),
                "result": result_name,
            }
            for hid, label, cases_path, result_name in harnesses
        ],
        "results": result_files,
        "math_presets": math_presets,
        "baked": is_baked_available(REPO_DIR),
    }


def _run_env_from_request(data: dict | None, file_env: dict[str, str]) -> dict[str, str]:
    env = os.environ.copy()
    env.update(file_env)
    mode = (data or {}).get("mode", "").strip().lower()
    if mode == "offline":
        env["RUN_LIVE"] = "0"
    elif mode == "live":
        env["RUN_LIVE"] = "1"
    return env

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>OpenRouter Demos — Local Dev Server</title>
  <style>
    :root {
      --bg: #0d1117;
      --panel: #161b22;
      --border: #30363d;
      --text: #c9d1d9;
      --heading: #f0f6fc;
      --accent: #58a6ff;
      --green: #238636;
      --red: #da3633;
      --purple: #8957e5;
      --muted: #8b949e;
      --code-bg: #010409;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      background: var(--bg);
      color: var(--text);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      line-height: 1.5;
    }
    header {
      background: var(--panel);
      border-bottom: 1px solid var(--border);
      padding: 16px 24px;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    header h1 {
      margin: 0;
      font-size: 20px;
      color: var(--heading);
      display: flex;
      align-items: center;
      gap: 10px;
    }
    header h1 span {
      background: var(--accent);
      color: #000;
      font-size: 12px;
      padding: 2px 8px;
      border-radius: 12px;
      font-weight: bold;
    }
    .status-badge {
      font-size: 13px;
      color: var(--muted);
    }
    main {
      max-width: 1200px;
      margin: 0 auto;
      padding: 24px;
    }
    .grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
      gap: 16px;
      margin-bottom: 24px;
    }
    .card {
      background: var(--panel);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 20px;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
    }
    .card h3 {
      margin: 0 0 8px;
      color: var(--heading);
      font-size: 16px;
    }
    .card p {
      margin: 0 0 16px;
      font-size: 13px;
      color: var(--muted);
      flex-grow: 1;
    }
    .btn {
      background: var(--accent);
      color: #000;
      border: none;
      padding: 8px 16px;
      border-radius: 6px;
      font-weight: 600;
      cursor: pointer;
      font-size: 13px;
      text-align: center;
      text-decoration: none;
      display: inline-block;
      transition: background 0.15s ease;
    }
    .btn:hover { opacity: 0.9; }
    .btn:disabled { opacity: 0.5; cursor: not-allowed; }
    .btn-secondary {
      background: #21262d;
      color: var(--text);
      border: 1px solid var(--border);
    }
    .btn-secondary:hover { border-color: var(--muted); }
    .btn-group {
      display: flex;
      gap: 8px;
    }
    .env-section {
      background: var(--panel);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 20px;
      margin-bottom: 24px;
    }
    .env-section-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 8px;
    }
    .env-section h3 {
      margin: 0;
      color: var(--heading);
    }
    .toggle-bar {
      display: flex;
      background: var(--bg);
      border: 1px solid var(--border);
      border-radius: 6px;
      padding: 2px;
      gap: 4px;
    }
    .toggle-btn {
      background: transparent;
      border: none;
      color: var(--muted);
      padding: 4px 12px;
      border-radius: 4px;
      font-size: 12px;
      font-weight: 600;
      cursor: pointer;
    }
    .toggle-btn.active {
      background: #21262d;
      color: var(--accent);
      border: 1px solid var(--border);
    }
    .env-section p {
      margin: 0 0 12px;
      font-size: 13px;
      color: var(--muted);
    }
    .form-group {
      display: flex;
      gap: 12px;
      align-items: center;
      flex-wrap: wrap;
    }
    input[type=password], input[type=text] {
      background: var(--bg);
      border: 1px solid var(--border);
      color: var(--text);
      padding: 8px 12px;
      border-radius: 6px;
      font-family: inherit;
      font-size: 13px;
    }
    select {
      background: var(--bg);
      border: 1px solid var(--border);
      color: var(--text);
      padding: 8px 12px;
      border-radius: 6px;
      font-family: inherit;
      font-size: 13px;
      appearance: none;
      -webkit-appearance: none;
      cursor: pointer;
      min-width: 100%;
    }
    select:focus {
      outline: 2px solid rgba(88, 166, 255, 0.35);
      border-color: var(--accent);
    }
    select option {
      background: var(--panel);
      color: var(--text);
    }
    select optgroup {
      background: var(--panel);
      color: var(--muted);
      font-weight: 600;
    }
    html { color-scheme: dark; }
    .model-selector-row {
      display: flex;
      gap: 16px;
      margin-top: 16px;
      align-items: center;
      flex-wrap: wrap;
    }
    .model-field {
      display: flex;
      flex-direction: column;
      gap: 6px;
      flex: 1;
      min-width: 250px;
    }
    .model-field label {
      font-size: 12px;
      color: var(--muted);
      font-weight: 600;
    }
    .console-section {
      background: var(--panel);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 20px;
    }
    .console-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 12px;
    }
    .console-header h3 {
      margin: 0;
      color: var(--heading);
      display: flex;
      align-items: center;
      gap: 8px;
    }
    .spinner {
      display: inline-block;
      width: 14px;
      height: 14px;
      border: 2px solid rgba(88, 166, 255, 0.2);
      border-radius: 50%;
      border-top-color: var(--accent);
      animation: spin 0.8s linear infinite;
    }
    @keyframes spin {
      to { transform: rotate(360deg); }
    }
    pre {
      background: var(--code-bg);
      border: 1px solid var(--border);
      border-radius: 6px;
      padding: 16px;
      color: #58a6ff;
      font-family: ui-monospace, SFMono-Regular, SF Mono, Menlo, Consolas, monospace;
      font-size: 13px;
      height: 380px;
      overflow-y: auto;
      margin: 0;
      white-space: pre-wrap;
    }
    .log-line { margin: 2px 0; }
    .log-error { color: #f85149; }
    .log-success { color: #56d364; }
    .log-info { color: #79c0ff; }
    .log-warn { color: #e3b341; }
    .iframe-container {
      width: 100%;
      height: 600px;
      border: 1px solid var(--border);
      border-radius: 8px;
      margin-top: 16px;
      background: #0e1014;
    }
    iframe {
      width: 100%;
      height: 100%;
      border: none;
    }
    .caesar-live-panel {
      margin-top: 24px;
      border: 1px solid var(--green);
    }
    .caesar-live-panel h3 {
      color: var(--heading);
      margin: 0 0 8px;
    }
    .caesar-controls {
      margin-top: 12px;
      align-items: flex-end;
    }
    .caesar-transcript {
      background: var(--code-bg);
      border: 1px solid var(--border);
      border-radius: 6px;
      padding: 16px;
      color: #c9d1d9;
      font-family: ui-monospace, SFMono-Regular, SF Mono, Menlo, Consolas, monospace;
      font-size: 13px;
      height: 280px;
      overflow-y: auto;
      margin-top: 16px;
      white-space: pre-wrap;
    }
    .turn-a { color: #79c0ff; }
    .turn-b { color: #e3b341; }
    .turn-judge { color: #56d364; }
    .turn-caesar { color: #d2a8ff; }
    .select-wrap {
      position: relative;
      width: 100%;
    }
    .select-wrap::after {
      content: "▾";
      position: absolute;
      right: 10px;
      top: 50%;
      transform: translateY(-50%);
      color: var(--muted);
      pointer-events: none;
      font-size: 11px;
    }
    .select-wrap select {
      padding-right: 28px;
      width: 100%;
    }
    .toolbar {
      display: flex;
      flex-wrap: wrap;
      gap: 12px;
      align-items: flex-end;
      margin-bottom: 20px;
      padding: 16px;
      background: var(--panel);
      border: 1px solid var(--border);
      border-radius: 8px;
    }
    .toolbar .model-field { min-width: 180px; flex: 1; }
    .meta-strip {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-bottom: 20px;
    }
    .meta-pill {
      font-size: 12px;
      padding: 4px 10px;
      border-radius: 999px;
      border: 1px solid var(--border);
      background: var(--panel);
      color: var(--muted);
    }
    .meta-pill strong { color: var(--heading); font-weight: 600; }
    .section-title {
      margin: 0 0 16px;
      font-size: 13px;
      font-weight: 600;
      letter-spacing: 0.06em;
      text-transform: uppercase;
      color: var(--muted);
    }
    .card:hover { border-color: #484f58; }
    .card-num {
      display: inline-block;
      font-size: 11px;
      font-weight: 700;
      color: var(--accent);
      margin-bottom: 6px;
      letter-spacing: 0.04em;
    }
    .card-actions {
      display: flex;
      flex-direction: column;
      gap: 10px;
    }
    .card-actions .btn-group { flex-wrap: wrap; }
    .preset-desc, .caesar-preset-desc {
      font-size: 12px;
      color: var(--muted);
      margin-top: 10px;
      padding: 10px 12px;
      background: var(--bg);
      border: 1px solid var(--border);
      border-radius: 6px;
      line-height: 1.45;
    }
    .trace-bar {
      display: flex;
      flex-wrap: wrap;
      gap: 12px;
      align-items: flex-end;
      margin-bottom: 12px;
    }
    .trace-bar .model-field { flex: 1; min-width: 280px; }
    .btn-sm {
      padding: 6px 12px;
      font-size: 12px;
    }
    .btn-purple { background: var(--purple); color: #fff; }
    .btn-green { background: var(--green); color: #fff; }
    header .tagline {
      font-size: 12px;
      color: var(--muted);
      margin-top: 4px;
    }
  </style>
</head>
<body>
  <header>
    <div>
      <h1>OpenRouter Demos <span>LOCAL DEV</span></h1>
      <div class="tagline">Five harnesses · offline stubs or live OpenRouter · streaming progress</div>
    </div>
    <div class="status-badge">Port: 8080 · <span id="env-status">Loading...</span></div>
  </header>
  <main>
    <div class="meta-strip" id="meta-strip"></div>

    <div class="toolbar">
      <div class="model-field">
        <label>Quick run harness</label>
        <div class="select-wrap">
          <select id="quick-harness">
            <option value="deflect">1 — Support Deflection</option>
            <option value="motion">2 — GTM Motion</option>
            <option value="bakeoff">3 — Provider Ops Bakeoff</option>
            <option value="caesar">4 — Caesar Debate (batch)</option>
            <option value="probe">5 — Guardrail Probe</option>
          </select>
        </div>
      </div>
      <div class="model-field" style="max-width:160px">
        <label>Run mode</label>
        <div class="select-wrap">
          <select id="run-mode">
            <option value="offline">Offline (stubs)</option>
            <option value="live">Live (API key)</option>
          </select>
        </div>
      </div>
      <button class="btn" onclick="runQuickHarness()">Run selected</button>
      <button class="btn btn-purple" onclick="runBakedDemo()">Full demo (no key)</button>
      <button class="btn btn-green" onclick="runAllDemos()">Run all</button>
    </div>

    <p class="section-title">Configuration</p>
    <div class="env-section">
      <div class="env-section-header">
        <h3>OpenRouter Settings & Model Selector</h3>
        <div class="toggle-bar">
          <button id="toggle-curated" class="toggle-btn active" onclick="setCatalogFilter('curated')">Curated (32)</button>
          <button id="toggle-probe" class="toggle-btn" onclick="setCatalogFilter('probe')">Safety Probe (5)</button>
          <button id="toggle-all" class="toggle-btn" onclick="setCatalogFilter('all')">All Models (415)</button>
        </div>
      </div>
      <p id="filter-desc">Filtered to essential open-weight heavyweights (Nemotron, Llama 3.3, Mistral, Phi-4, Solar) & top frontier models per provider.</p>
      <div class="form-group">
        <input type="password" id="api-key" style="flex-grow:1" placeholder="sk-or-v1-..." />
        <button class="btn btn-secondary" onclick="saveConfig()">Save to .env</button>
      </div>

      <div class="model-selector-row">
        <div class="model-field">
          <label>Model preset</label>
          <div class="select-wrap">
            <select id="model-preset" onchange="applyModelPreset()">
              <option value="">— choose preset —</option>
              <option value="curated">Curated default (Nemotron + GPT-4o mini)</option>
              <option value="probe">Safety probe trio</option>
              <option value="frontier">Frontier debate (Sonnet + GPT-4o)</option>
              <option value="oss">OSS bakeoff (Llama 3.3 + Nemotron)</option>
            </select>
          </div>
        </div>
        <div class="model-field">
          <label>Primary (Deflect / Motion / Caesar judge)</label>
          <div class="select-wrap">
            <select id="model-primary"></select>
          </div>
        </div>
        <div class="model-field">
          <label>Model A (Bakeoff / Debate)</label>
          <div class="select-wrap">
            <select id="model-a"></select>
          </div>
        </div>
        <div class="model-field">
          <label>Model B (Bakeoff / Debate)</label>
          <div class="select-wrap">
            <select id="model-b"></select>
          </div>
        </div>
      </div>
    </div>

    <p class="section-title">Harnesses</p>

    <div class="grid">
      <div class="card">
        <span class="card-num">01</span>
        <h3>Support Deflection</h3>
        <p>Ticket classification & deflection with policy guardrails.</p>
        <div class="card-actions">
          <div class="btn-group">
            <button class="btn demo-btn" onclick="runDemo('deflect')">Run</button>
            <button class="btn btn-secondary btn-sm" onclick="viewResult('deflect.json')">JSON</button>
          </div>
        </div>
      </div>
      <div class="card">
        <span class="card-num">02</span>
        <h3>GTM Motion</h3>
        <p>Inbound lead qualification and routing workflow.</p>
        <div class="card-actions">
          <div class="btn-group">
            <button class="btn demo-btn" onclick="runDemo('motion')">Run</button>
            <button class="btn btn-secondary btn-sm" onclick="viewResult('motion.json')">JSON</button>
          </div>
        </div>
      </div>
      <div class="card">
        <span class="card-num">03</span>
        <h3>Provider Ops Bakeoff</h3>
        <p>Quality & latency benchmark between two models.</p>
        <div class="card-actions">
          <div class="btn-group">
            <button class="btn demo-btn" onclick="runDemo('bakeoff')">Run</button>
            <button class="btn btn-secondary btn-sm" onclick="viewResult('bakeoff.json')">JSON</button>
          </div>
        </div>
      </div>
      <div class="card">
        <span class="card-num">04</span>
        <h3>Caesar Debate</h3>
        <p>Structured debate — English, math, RouteKit — judged by Caesar.</p>
        <div class="card-actions">
          <div class="model-field">
            <label>Batch category filter</label>
            <div class="select-wrap">
              <select id="caesar-batch-hint" disabled title="Batch runs all cases in cases.jsonl">
                <option>All topics (10 cases)</option>
                <option>Includes 4 math debates</option>
              </select>
            </div>
          </div>
          <div class="btn-group">
            <button class="btn demo-btn" onclick="runDemo('caesar')">Run batch</button>
            <button class="btn btn-green" onclick="startCaesarLiveFromDashboard()">▶ Live Caesar</button>
            <a class="btn btn-secondary btn-sm" href="/caesar/chat.html" target="_blank">Replay UI</a>
          </div>
        </div>
      </div>
      <div class="card">
        <span class="card-num">05</span>
        <h3>Guardrail Probe</h3>
        <p>Upstream blocks vs refusals vs leaks on jailbreak prompts.</p>
        <div class="card-actions">
          <div class="model-field">
            <label>Probe profile (offline stubs)</label>
            <div class="select-wrap">
              <select id="probe-profile" disabled title="Offline run exercises strict + leaky stubs">
                <option>Both profiles (strict + leaky)</option>
                <option>8 prompts × 2 models = 16 checks</option>
              </select>
            </div>
          </div>
          <div class="btn-group">
            <button class="btn demo-btn" onclick="runDemo('probe')">Run probe</button>
            <button class="btn btn-secondary btn-sm" onclick="viewResult('guardrail_probe.json')">JSON</button>
          </div>
        </div>
      </div>
    </div>

    <p class="section-title">Console</p>

    <div class="console-section">
      <div class="console-header">
        <h3 id="console-title">
          <span id="loading-spinner" class="spinner" style="display:none;"></span>
          <span id="console-title-text">Execution Debug Log</span>
        </h3>
        <button class="btn btn-secondary btn-sm" onclick="runPytest()">Pytest (offline)</button>
        <div class="model-field" style="min-width:220px; margin:0;">
          <label>View result file</label>
          <div class="select-wrap">
            <select id="result-picker" onchange="viewResultFromPicker()">
              <option value="">— pick JSON —</option>
            </select>
          </div>
        </div>
      </div>
      <div id="progress-wrap" style="display:none; margin-bottom:12px;">
        <div id="progress-label" style="font-size:12px; color:var(--muted); margin-bottom:6px;">Starting…</div>
        <div style="background:#21262d; border:1px solid var(--border); border-radius:6px; height:10px; overflow:hidden;">
          <div id="progress-bar" style="background:var(--green); height:100%; width:0%; transition:width 0.25s ease;"></div>
        </div>
      </div>
      <pre id="output">Click Run Full Demo (No API Key) for the baked walkthrough, or run individual harnesses with a live key...</pre>
    </div>

    <div class="env-section caesar-live-panel" id="caesar-live-panel">
      <h3>Caesar live debate</h3>
      <p>Stream a single debate on the dashboard. Defaults to <strong>math</strong> — try Monty Hall or Bayes.</p>
      <div class="form-group caesar-controls">
        <div class="model-field">
          <label>Category</label>
          <div class="select-wrap">
            <select id="caesar-category" onchange="refreshCaesarPresets()"></select>
          </div>
        </div>
        <div class="model-field" style="flex:2">
          <label>Preset topic</label>
          <div class="select-wrap">
            <select id="caesar-preset" onchange="updateCaesarPresetDesc()"></select>
          </div>
        </div>
        <div class="model-field" style="max-width:120px">
          <label>Rounds</label>
          <div class="select-wrap">
            <select id="caesar-rounds">
              <option value="2">2</option>
              <option value="3" selected>3</option>
              <option value="4">4</option>
              <option value="5">5</option>
              <option value="6">6</option>
            </select>
          </div>
        </div>
        <button class="btn btn-green" id="btn-caesar-live" onclick="startCaesarLiveFromDashboard()">▶ Start live</button>
      </div>
      <div id="caesar-preset-desc" class="caesar-preset-desc">Select a preset to see the full resolution and sides.</div>
      <div id="caesar-transcript" class="caesar-transcript">Ready.</div>
    </div>

    <p class="section-title">Caesar trace viewer</p>
    <div class="trace-bar">
      <div class="model-field">
        <label>Replay trace</label>
        <div class="select-wrap">
          <select id="caesar-trace-select">
            <option value="">Loading traces…</option>
          </select>
        </div>
      </div>
      <button class="btn btn-secondary btn-sm" onclick="loadSelectedTrace()">Load in viewer</button>
      <button class="btn btn-secondary btn-sm" onclick="refreshTraceList()">Refresh list</button>
    </div>
    <div class="iframe-container">
        <iframe id="caesar-iframe" src="/caesar/chat.html"></iframe>
      </div>
  </main>

  <script>
    let rawModelsData = { all: [], curated: [], probe_picks: [] };
    let currentFilter = "curated";
    let caesarPresets = {};

    loadModelsList();
    loadCaesarPresets();
    loadDashboardMeta();
    refreshTraceList();

    function getRunMode() {
      return document.getElementById("run-mode").value || "offline";
    }

    function runQuickHarness() {
      runDemo(document.getElementById("quick-harness").value);
    }

    async function loadDashboardMeta() {
      try {
        const res = await fetch("/api/dashboard-meta");
        const meta = await res.json();
        const strip = document.getElementById("meta-strip");
        strip.innerHTML = "";
        (meta.harnesses || []).forEach(h => {
          const pill = document.createElement("span");
          pill.className = "meta-pill";
          pill.innerHTML = "<strong>" + h.label + "</strong> · " + h.cases + " cases";
          strip.appendChild(pill);
        });
        if (meta.baked) {
          const pill = document.createElement("span");
          pill.className = "meta-pill";
          pill.innerHTML = "<strong>Baked demo</strong> · ready";
          strip.appendChild(pill);
        }
        const picker = document.getElementById("result-picker");
        const cur = picker.value;
        picker.innerHTML = '<option value="">— pick JSON —</option>';
        (meta.results || []).forEach(r => {
          const opt = document.createElement("option");
          opt.value = r.id;
          opt.textContent = r.id;
          picker.appendChild(opt);
        });
        if (cur) picker.value = cur;
      } catch (e) {
        logAppend("Could not load dashboard meta: " + e, "warn");
      }
    }

    function viewResultFromPicker() {
      const file = document.getElementById("result-picker").value;
      if (file) viewResult(file);
    }

    async function refreshTraceList() {
      try {
        const res = await fetch("/api/caesar-traces");
        const traces = await res.json();
        const sel = document.getElementById("caesar-trace-select");
        sel.innerHTML = "";
        if (!traces.length) {
          sel.innerHTML = '<option value="">No traces yet — run Caesar first</option>';
          return;
        }
        traces.forEach((t, i) => {
          const opt = document.createElement("option");
          opt.value = t.path;
          opt.textContent = t.id + " (" + t.time + ")";
          if (i === 0) opt.selected = true;
          sel.appendChild(opt);
        });
      } catch (e) {
        logAppend("Failed to list Caesar traces: " + e, "warn");
      }
    }

    function loadSelectedTrace() {
      const path = document.getElementById("caesar-trace-select").value;
      if (!path) return;
      document.getElementById("caesar-iframe").src =
        "/caesar/chat.html?trace=" + encodeURIComponent(path);
    }

    function applyModelPreset() {
      const key = document.getElementById("model-preset").value;
      if (!key) return;
      const presets = {
        curated: {
          primary: "nvidia/nemotron-3.5-lightning",
          a: "nvidia/nemotron-3.5-lightning",
          b: "openai/gpt-4o-mini"
        },
        frontier: {
          primary: "anthropic/claude-3.5-sonnet",
          a: "openai/gpt-4o",
          b: "openai/gpt-4o-mini"
        },
        oss: {
          primary: "meta-llama/llama-3.3-70b-instruct",
          a: "meta-llama/llama-3.3-70b-instruct",
          b: "nvidia/nemotron-3.5-lightning"
        }
      };
      if (key === "probe") {
        applyProbeTrio();
        document.getElementById("model-preset").value = "";
        return;
      }
      const p = presets[key];
      if (!p) return;
      document.getElementById("model-primary").value = p.primary;
      document.getElementById("model-a").value = p.a;
      document.getElementById("model-b").value = p.b;
      logAppend("Applied model preset: " + key, "info");
      document.getElementById("model-preset").value = "";
    }

    function updateCaesarPresetDesc() {
      const cat = document.getElementById("caesar-category").value;
      const id = document.getElementById("caesar-preset").value;
      const box = document.getElementById("caesar-preset-desc");
      const list = caesarPresets[cat] || [];
      const preset = list.find(p => p.id === id);
      if (!preset) {
        box.textContent = "Select a preset to see the full resolution and sides.";
        return;
      }
      box.innerHTML = "<strong>" + preset.topic + "</strong><br>A: " + preset.side_a + "<br>B: " + preset.side_b;
    }

    function logAppend(text, type = "info") {
      const out = document.getElementById("output");
      const line = document.createElement("div");
      line.className = "log-line log-" + type;
      line.textContent = `[${new Date().toLocaleTimeString()}] ${text}`;
      out.appendChild(line);
      out.scrollTop = out.scrollHeight;
    }

    function setRunningState(running, titleText = "") {
      const spinner = document.getElementById("loading-spinner");
      const title = document.getElementById("console-title-text");
      const buttons = document.querySelectorAll("button");
      
      spinner.style.display = running ? "inline-block" : "none";
      if (titleText) title.textContent = titleText;
      buttons.forEach(b => b.disabled = running);
    }

    async function loadModelsList() {
      try {
        const res = await fetch("/api/models");
        rawModelsData = await res.json();
        renderDatalist();
        checkEnvStatus();
      } catch(e) {
        logAppend("Failed to load models list: " + e, "error");
      }
    }

    function setCatalogFilter(filter) {
      currentFilter = filter;
      document.getElementById("toggle-curated").classList.toggle("active", filter === "curated");
      document.getElementById("toggle-probe").classList.toggle("active", filter === "probe");
      document.getElementById("toggle-all").classList.toggle("active", filter === "all");
      
      const desc = document.getElementById("filter-desc");
      if (filter === "curated") {
        desc.textContent = "Curated heavy hitters: Nemotron, Llama 3.3, Mistral, Phi-4, Solar, plus top frontier models per provider.";
      } else if (filter === "probe") {
        desc.textContent = "Models chosen for guardrail contrast — strict frontier, fast OSS, uncensored-tuned, and cheap comparator.";
      } else {
        desc.textContent = "Showing all 415 available models on OpenRouter.";
      }
      renderDatalist();
    }

    function applyProbeTrio() {
      const picks = rawModelsData.probe_picks || [];
      if (picks.length < 3) return;
      document.getElementById("model-primary").value = picks[0].id;
      document.getElementById("model-a").value = picks[1].id;
      document.getElementById("model-b").value = picks[2].id;
      logAppend("Applied probe trio: " + picks.slice(0, 3).map(p => p.id).join(", "), "info");
    }

    async function loadCaesarPresets() {
      try {
        const res = await fetch("/api/caesar/presets");
        const data = await res.json();
        caesarPresets = data.presets || {};
        const catSel = document.getElementById("caesar-category");
        catSel.innerHTML = "";
        (data.categories || Object.keys(caesarPresets)).forEach(cat => {
          const opt = document.createElement("option");
          opt.value = cat;
          opt.textContent = cat.charAt(0).toUpperCase() + cat.slice(1);
          catSel.appendChild(opt);
        });
        catSel.value = "math";
        refreshCaesarPresets();
        updateCaesarPresetDesc();
      } catch (e) {
        logAppend("Failed to load Caesar presets: " + e, "warn");
      }
    }

    function refreshCaesarPresets() {
      const cat = document.getElementById("caesar-category").value;
      const presetSel = document.getElementById("caesar-preset");
      presetSel.innerHTML = "";
      const list = caesarPresets[cat] || [];
      list.forEach(p => {
        const opt = document.createElement("option");
        opt.value = p.id;
        opt.textContent = p.topic.slice(0, 72) + (p.topic.length > 72 ? "…" : "");
        presetSel.appendChild(opt);
      });
      if (list.length) presetSel.value = list[0].id;
      updateCaesarPresetDesc();
    }

    function renderDatalist() {
      const selects = [
        document.getElementById("model-primary"),
        document.getElementById("model-a"),
        document.getElementById("model-b")
      ];
      const models = currentFilter === "curated"
        ? (rawModelsData.curated || [])
        : currentFilter === "probe"
          ? (rawModelsData.probe_picks || [])
          : (rawModelsData.all || []);
      
      const groups = {};
      models.forEach(m => {
        const prov = m.provider || "Other";
        if (!groups[prov]) groups[prov] = [];
        groups[prov].push(m);
      });

      selects.forEach(sel => {
        const curVal = sel.value;
        sel.innerHTML = "";
        if (currentFilter === "probe") {
          models.forEach(m => {
            const opt = document.createElement("option");
            opt.value = m.id;
            opt.textContent = m.note ? m.name + " — " + m.note : m.name;
            sel.appendChild(opt);
          });
        } else {
          for (const [prov, list] of Object.entries(groups)) {
            const optgroup = document.createElement("optgroup");
            optgroup.label = prov;
            list.forEach(m => {
              const opt = document.createElement("option");
              opt.value = m.id;
              opt.textContent = m.name;
              optgroup.appendChild(opt);
            });
            sel.appendChild(optgroup);
          }
        }
        if (curVal) sel.value = curVal;
      });
    }

    async function checkEnvStatus() {
      try {
        const res = await fetch("/api/key");
        const data = await res.json();
        const badge = document.getElementById("env-status");
        if (data.hasKey) {
          badge.textContent = "Live API key configured";
          badge.style.color = "#58a6ff";
          if (data.maskedKey) {
            document.getElementById("api-key").placeholder = data.maskedKey;
          }
          document.getElementById("run-mode").value = "live";
        } else {
          badge.textContent = "Offline stubs (no key)";
          badge.style.color = "#8b949e";
          document.getElementById("run-mode").value = "offline";
        }
        if (data.runLive === "1") document.getElementById("run-mode").value = "live";
        if (data.runLive === "0") document.getElementById("run-mode").value = "offline";
        if (data.models) {
          if (data.models.primary) document.getElementById("model-primary").value = data.models.primary || "nvidia/nemotron-3.5-lightning";
          if (data.models.modelA) document.getElementById("model-a").value = data.models.modelA || "nvidia/nemotron-3.5-lightning";
          if (data.models.modelB) document.getElementById("model-b").value = data.models.modelB || "openai/gpt-4o-mini";
        }
      } catch (e) {
        logAppend("Error fetching env status: " + e, "warn");
      }
    }

    async function saveConfig() {
      const keyVal = document.getElementById("api-key").value.trim();
      const primary = document.getElementById("model-primary").value.trim();
      const modelA = document.getElementById("model-a").value.trim();
      const modelB = document.getElementById("model-b").value.trim();

      try {
        const res = await fetch("/api/key", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            apiKey: keyVal,
            primary: primary,
            modelA: modelA,
            modelB: modelB,
            runMode: getRunMode()
          })
        });
        const data = await res.json();
        if (data.ok) {
          logAppend("Settings saved successfully to .env!", "success");
          document.getElementById("api-key").value = "";
          checkEnvStatus();
        }
      } catch (err) {
        logAppend("Failed to save configuration: " + err, "error");
      }
    }


    function updateProgressBar(p) {
      const wrap = document.getElementById("progress-wrap");
      const bar = document.getElementById("progress-bar");
      const label = document.getElementById("progress-label");
      wrap.style.display = "block";
      const pct = p.pct != null ? p.pct : Math.round(100 * (p.done || 0) / Math.max(p.total || 1, 1));
      label.textContent = (p.label || "eval") + " · " + (p.done || 0) + "/" + (p.total || "?") + " (" + pct + "%)" + (p.case_id ? " · " + p.case_id : "");
      bar.style.width = pct + "%";
    }

    async function consumeSseResponse(res, onEvent) {
      if (!res.ok) throw new Error("HTTP " + res.status);
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buf = "";
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buf += decoder.decode(value, { stream: true });
        const chunks = buf.split("\n\n");
        buf = chunks.pop() || "";
        for (const chunk of chunks) {
          const line = chunk.trim();
          if (!line.startsWith("data:")) continue;
          onEvent(JSON.parse(line.slice(5).trim()));
        }
      }
    }

    function appendCaesarTurn(turn) {
      const box = document.getElementById("caesar-transcript");
      const line = document.createElement("div");
      const role = turn.role || turn.speaker || "?";
      const cls = role.includes("A") ? "turn-a" : role.includes("B") ? "turn-b" : role.includes("judge") ? "turn-judge" : "turn-caesar";
      line.className = cls;
      line.textContent = "[" + role + "] " + (turn.content || turn.text || "").slice(0, 1200);
      box.appendChild(line);
      box.scrollTop = box.scrollHeight;
    }

    async function startCaesarLiveFromDashboard() {
      const category = document.getElementById("caesar-category").value;
      const preset_id = document.getElementById("caesar-preset").value;
      const max_rounds = parseInt(document.getElementById("caesar-rounds").value, 10);
      const transcript = document.getElementById("caesar-transcript");
      transcript.innerHTML = "";
      document.getElementById("caesar-live-panel").scrollIntoView({ behavior: "smooth" });
      setRunningState(true, "Caesar Live Debate");
      logAppend("Starting Caesar live (" + category + ", " + max_rounds + " rounds)...", "info");
      try {
        const res = await fetch("/api/caesar/live-stream", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ category, preset_id, max_rounds })
        });
        await consumeSseResponse(res, (ev) => {
          if (ev.type === "start") {
            const head = document.createElement("div");
            head.className = "turn-judge";
            head.textContent = "Topic: " + ev.topic;
            transcript.appendChild(head);
          }
          if (ev.type === "turn" && ev.turn) appendCaesarTurn(ev.turn);
          if (ev.type === "done") {
            logAppend("Caesar live finished — trace: " + (ev.path || "results/caesar"), "success");
            refreshTraceList();
            if (ev.path) {
              document.getElementById("caesar-iframe").src =
                "/caesar/chat.html?trace=" + encodeURIComponent(ev.path);
            }
          }
          if (ev.type === "error") logAppend(ev.message, "error");
        });
      } catch (err) {
        logAppend("Caesar live failed: " + err, "error");
      } finally {
        setRunningState(false, "Console Output — Caesar Live");
      }
    }

    function startCaesarLive() {
      startCaesarLiveFromDashboard();
    }

    async function runDemo(name) {
      document.getElementById("output").innerHTML = "";
      document.getElementById("progress-wrap").style.display = "none";
      setRunningState(true, "Executing Demo: " + name);
      logAppend("Starting " + name + " (live stream)...", "info");
      let exitCode = 1;
      try {
        const res = await fetch("/api/run-stream", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ demo: name, mode: getRunMode() })
        });
        await consumeSseResponse(res, (ev) => {
          if (ev.type === "line" && ev.text) logAppend(ev.text, "info");
          if (ev.type === "progress") updateProgressBar(ev);
          if (ev.type === "progress_done") updateProgressBar({ label: ev.label, done: ev.done, total: ev.total, pct: 100 });
          if (ev.type === "done") exitCode = ev.code;
          if (ev.type === "error") logAppend(ev.message, "error");
        });
        if (exitCode === 0) logAppend("Demo finished successfully.", "success");
        else logAppend("Demo exited with code " + exitCode, "error");
      } catch (err) {
        logAppend("Request execution failed: " + err, "error");
      } finally {
        setRunningState(false, "Console Output — " + name);
        refreshTraceList();
        loadDashboardMeta();
        document.getElementById("caesar-iframe").src = "/caesar/chat.html?live=1";
      }
    }


    async function runBakedDemo() {
      document.getElementById("output").innerHTML = "";
      document.getElementById("progress-wrap").style.display = "none";
      setRunningState(true, "Replaying baked offline demo");
      logAppend("Loading pre-recorded offline run (no API key)...", "info");
      try {
        const res = await fetch("/api/run-baked-stream", { method: "POST" });
        await consumeSseResponse(res, (ev) => {
          if (ev.type === "phase") logAppend("=== " + ev.label + " ===", "warn");
          if (ev.type === "line" && ev.text) logAppend(ev.text, "info");
          if (ev.type === "progress") updateProgressBar(ev);
          if (ev.type === "progress_done") updateProgressBar({ label: ev.label, done: ev.done, total: ev.total, pct: 100 });
          if (ev.type === "done") {
            logAppend(ev.message || "Baked demo materialized.", "success");
            if (ev.materialized) logAppend("Files: " + ev.materialized.join(", "), "info");
          }
          if (ev.type === "error") logAppend(ev.message, "error");
        });
      } catch (err) {
        logAppend("Baked demo failed: " + err, "error");
      } finally {
        setRunningState(false, "Console Output — Baked Demo");
        document.getElementById("caesar-iframe").src = "/caesar/chat.html?live=1";
        checkEnvStatus();
      }
    }

    async function runAllDemos() {
      document.getElementById("output").innerHTML = "";
      document.getElementById("progress-wrap").style.display = "none";
      setRunningState(true, "Running All Live Demos Sequentially");
      logAppend("Starting full suite (stream): Deflect, Motion, Bakeoff, Caesar, Probe...", "info");
      try {
        const res = await fetch("/api/run-all-stream", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ mode: getRunMode() })
        });
        await consumeSseResponse(res, (ev) => {
          if (ev.type === "phase") logAppend("=== " + ev.label + " ===", "warn");
          if (ev.type === "line" && ev.text) logAppend(ev.text, "info");
          if (ev.type === "progress") updateProgressBar(ev);
          if (ev.type === "error") logAppend(ev.message, "error");
          if (ev.type === "done") logAppend("All demos finished (code " + ev.code + ")", ev.code === 0 ? "success" : "error");
        });
      } catch (err) {
        logAppend("Failed to run all demos: " + err, "error");
      } finally {
        setRunningState(false, "Console Output — All Demos Completed");
        refreshTraceList();
        loadDashboardMeta();
        document.getElementById("caesar-iframe").src = "/caesar/chat.html?live=1";
      }
    }

    async function runPytest() {
      document.getElementById("output").innerHTML = "";
      setRunningState(true, "Running Offline Pytest Suite");
      logAppend("Executing pytest against stub fixtures...", "info");

      try {
        const res = await fetch("/api/test", { method: "POST" });
        const data = await res.json();
        if (data.code === 0) {
          logAppend("Pytest passed cleanly!", "success");
        } else {
          logAppend("Pytest reported failures.", "error");
        }
        logAppend(data.output || data.error, "info");
      } catch (err) {
        logAppend("Pytest execution failed: " + err, "error");
      } finally {
        setRunningState(false, "Console Output — Pytest Suite");
      }
    }

    async function viewResult(file) {
      document.getElementById("output").innerHTML = "";
      logAppend("Reading result file: " + file, "info");
      try {
        const res = await fetch("/results/" + file);
        if (res.ok) {
          const json = await res.json();
          logAppend(JSON.stringify(json, null, 2), "success");
        } else {
          logAppend("Result file not found. Run the demo first!", "warn");
        }
      } catch (err) {
        logAppend("Error loading result: " + err, "error");
      }
    }
  </script>
</body>
</html>
"""

class DevServerHandler(http.server.SimpleHTTPRequestHandler):
    def _send_sse_start(self) -> None:
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.end_headers()

    def _sse_write(self, payload: dict) -> None:
        self.wfile.write(sse_event(payload))
        self.wfile.flush()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(REPO_DIR), **kwargs)

    def do_GET(self):
        if self.path == "/" or self.path == "/index.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            html_path = RUN_CENTER_HTML if RUN_CENTER_HTML.is_file() else None
            if html_path:
                self.wfile.write(html_path.read_bytes())
            else:
                self.wfile.write(HTML_TEMPLATE.encode("utf-8"))
            return
        elif self.path == "/api/models":
            models_file = REPO_DIR / "src" / "models.json"
            if models_file.exists():
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(models_file.read_bytes())
            else:
                self._send_json({"all": [], "curated": []})
            return
        elif self.path == "/api/dashboard-meta":
            self._send_json(build_dashboard_meta())
            return
        elif self.path == "/api/baked":
            self._send_json({"ok": is_baked_available(REPO_DIR), **load_manifest(REPO_DIR)})
            return
        elif self.path == "/api/caesar/presets":
            self._send_json({"categories": list(TOPIC_PRESETS.keys()), "presets": TOPIC_PRESETS})
            return
        elif self.path == "/api/caesar-traces":
            caesar_dir = REPO_DIR / "results" / "caesar"
            traces = []
            if caesar_dir.exists():
                for p in sorted(caesar_dir.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True):
                    traces.append({
                        "id": p.stem,
                        "path": f"/results/caesar/{p.name}",
                        "time": time.strftime("%H:%M:%S", time.localtime(p.stat().st_mtime))
                    })
            self._send_json(traces)
            return
        elif self.path.startswith("/api/runs"):
            from urllib.parse import parse_qs, urlparse

            parsed = urlparse(self.path)
            if parsed.path == "/api/runs/chart":
                qs = parse_qs(parsed.query)
                demo = (qs.get("demo") or [None])[0]
                self._send_json(get_runs_for_chart(demo=demo, limit=30))
                return
            if parsed.path == "/api/runs":
                qs = parse_qs(parsed.query)
                limit = int((qs.get("limit") or ["40"])[0])
                rows = get_recent_runs(limit)
                for row in rows:
                    row.pop("raw_payload", None)
                self._send_json(rows)
                return
            parts = parsed.path.strip("/").split("/")
            if len(parts) == 3 and parts[0] == "api" and parts[1] == "runs":
                run = get_run_by_id(int(parts[2]))
                if not run:
                    self._send_json({"error": "not found"}, status=404)
                    return
                self._send_json(run)
                return
        elif self.path == "/api/key":
            file_env = load_env_file()
            key = os.environ.get("OPENROUTER_API_KEY") or file_env.get("OPENROUTER_API_KEY", "")
            masked = f"{key[:7]}...{key[-4:]}" if len(key) > 12 else ""
            models_info = {
                "primary": file_env.get("OPENROUTER_MODEL", "nvidia/nemotron-3.5-lightning"),
                "modelA": file_env.get("OPENROUTER_MODEL_A", "nvidia/nemotron-3.5-lightning"),
                "modelB": file_env.get("OPENROUTER_MODEL_B", "openai/gpt-4o-mini"),
            }
            run_live = file_env.get("RUN_LIVE", "0")
            self._send_json({
                "hasKey": bool(key),
                "maskedKey": masked,
                "models": models_info,
                "runLive": run_live,
            })
            return
        return super().do_GET()

    def do_POST(self):
        if self.path == "/api/key":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            data = json.loads(body.decode("utf-8"))
            new_key = data.get("apiKey", "").strip()
            primary = data.get("primary", "").strip()
            model_a = data.get("modelA", "").strip()
            model_b = data.get("modelB", "").strip()
            run_mode = str(data.get("runMode", "")).strip().lower()

            env_file = REPO_DIR / ".env"
            file_env = load_env_file()
            if new_key:
                file_env["OPENROUTER_API_KEY"] = new_key
            if primary:
                file_env["OPENROUTER_MODEL"] = primary
                file_env["CAESAR_MODEL"] = primary
            if model_a:
                file_env["OPENROUTER_MODEL_A"] = model_a
                file_env["MODEL_A"] = model_a
            if model_b:
                file_env["OPENROUTER_MODEL_B"] = model_b
                file_env["MODEL_B"] = model_b

            if run_mode == "live":
                file_env["RUN_LIVE"] = "1"
            elif run_mode == "offline":
                file_env["RUN_LIVE"] = "0"
            elif new_key:
                file_env["RUN_LIVE"] = "1"

            new_lines = [f"{k}={v}" for k, v in file_env.items()]
            env_file.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
            self._send_json({"ok": True})
            return

        if self.path == "/api/run-batch-stream":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            data = json.loads(body.decode("utf-8"))
            file_env = load_env_file()
            env = _run_env_from_request(data, file_env)
            self._send_sse_start()
            try:
                for chunk in stream_run_batch(
                    data,
                    repo_dir=REPO_DIR,
                    venv_python=str(VENV_PYTHON),
                    env=env,
                ):
                    self.wfile.write(chunk)
                    self.wfile.flush()
            except BrokenPipeError:
                pass
            return

        if self.path == "/api/run-baked-stream":
            if not is_baked_available(REPO_DIR):
                self._send_json(
                    {"error": "baked demo not found — run scripts/bake_demo.py"},
                    status=404,
                )
                return
            self._send_sse_start()
            try:
                for chunk in stream_baked_replay(REPO_DIR):
                    self.wfile.write(chunk)
                    self.wfile.flush()
            except BrokenPipeError:
                pass
            return

        if self.path == "/api/run-stream":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            data = json.loads(body.decode("utf-8"))
            demo = data.get("demo")
            module_map = {
                "deflect": "deflect.harness",
                "motion": "motion.harness",
                "bakeoff": "bakeoff.runner",
                "caesar": "caesar.harness",
                "probe": "probe.harness",
            }
            target_module = module_map.get(demo)
            if not target_module:
                self._send_json({"error": "Invalid demo name"}, status=400)
                return
            file_env = load_env_file()
            env = _run_env_from_request(data, file_env)
            env["PROGRESS"] = "1"
            cmd = [str(VENV_PYTHON), "-m", target_module]
            self._send_sse_start()
            try:
                for chunk in stream_subprocess(cmd, cwd=REPO_DIR, env=env):
                    self.wfile.write(chunk)
                    self.wfile.flush()
            except BrokenPipeError:
                pass
            return

        if self.path == "/api/run-all-stream":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length) if content_length else b"{}"
            data = json.loads(body.decode("utf-8") or "{}")
            file_env = load_env_file()
            env = _run_env_from_request(data, file_env)
            env["PROGRESS"] = "1"
            demos = [
                ("Support Deflection", [str(VENV_PYTHON), "-m", "deflect.harness"]),
                ("GTM Motion", [str(VENV_PYTHON), "-m", "motion.harness"]),
                ("Provider Ops Bakeoff", [str(VENV_PYTHON), "-m", "bakeoff.runner"]),
                ("Caesar Debate", [str(VENV_PYTHON), "-m", "caesar.harness"]),
                ("Guardrail Probe", [str(VENV_PYTHON), "-m", "probe.harness"]),
            ]
            self._send_sse_start()
            overall = 0
            try:
                for label, cmd in demos:
                    self._sse_write({"type": "phase", "label": label})
                    for chunk in stream_subprocess(cmd, cwd=REPO_DIR, env=env):
                        self.wfile.write(chunk)
                        self.wfile.flush()
                        if chunk.startswith(b"data:") and b'"done"' in chunk:
                            try:
                                payload = json.loads(chunk.decode().split("data:", 1)[1].strip())
                                if payload.get("type") == "done":
                                    overall = max(overall, int(payload.get("code", 1)))
                            except Exception:
                                pass
                self._sse_write({"type": "done", "code": overall})
            except BrokenPipeError:
                pass
            return

        if self.path == "/api/caesar/live-stream":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            data = json.loads(body.decode("utf-8"))
            file_env = load_env_file()
            env = os.environ.copy()
            env.update(file_env)
            self._send_sse_start()
            try:
                run_caesar_live(data, repo_dir=REPO_DIR, env=env, emit=self._sse_write)
            except Exception as exc:
                self._sse_write({"type": "error", "message": str(exc)})
            return

        if self.path == "/api/run-all":
            file_env = load_env_file()
            env = os.environ.copy()
            env.update(file_env)

            logs = []
            demos = [
                ("Support Deflection", [str(VENV_PYTHON), "-m", "deflect.harness"]),
                ("GTM Motion", [str(VENV_PYTHON), "-m", "motion.harness"]),
                ("Provider Ops Bakeoff", [str(VENV_PYTHON), "-m", "bakeoff.runner"]),
                ("Caesar Debate", [str(VENV_PYTHON), "-m", "caesar.harness"]),
                ("Guardrail Probe", [str(VENV_PYTHON), "-m", "probe.harness"]),
            ]

            for label, cmd in demos:
                logs.append(f"=== Running: {label} ===")
                try:
                    proc = subprocess.run(
                        cmd,
                        cwd=str(REPO_DIR),
                        env=env,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        text=True,
                        timeout=180
                    )
                    logs.append(proc.stdout)
                except Exception as e:
                    logs.append(f"Error: {e}")
                logs.append("\n")

            self._send_json({"output": "\n".join(logs)})
            return

        if self.path == "/api/run":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            data = json.loads(body.decode("utf-8"))
            demo = data.get("demo")

            file_env = load_env_file()
            env = os.environ.copy()
            env.update(file_env)

            module_map = {
                "deflect": "deflect.harness",
                "motion": "motion.harness",
                "bakeoff": "bakeoff.runner",
                "caesar": "caesar.harness",
                "probe": "probe.harness",
            }

            target_module = module_map.get(demo)
            if not target_module:
                self._send_json({"error": "Invalid demo name"}, status=400)
                return

            cmd = [str(VENV_PYTHON), "-m", target_module]
            try:
                proc = subprocess.run(
                    cmd,
                    cwd=str(REPO_DIR),
                    env=env,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    timeout=180
                )
                self._send_json({"code": proc.returncode, "output": proc.stdout})
            except Exception as e:
                self._send_json({"error": str(e)}, status=500)
            return

        if self.path == "/api/test":
            pytest_bin = REPO_DIR / ".venv" / "bin" / "pytest"
            cmd = [str(pytest_bin)] if pytest_bin.exists() else ["pytest"]
            env = os.environ.copy()
            env["RUN_LIVE"] = "0"
            try:
                proc = subprocess.run(
                    cmd,
                    cwd=str(REPO_DIR),
                    env=env,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    timeout=60
                )
                self._send_json({"code": proc.returncode, "output": proc.stdout})
            except Exception as e:
                self._send_json({"error": str(e)}, status=500)
            return

        self.send_error(404, "Endpoint not found")

    def _send_json(self, data, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))

def main():
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("0.0.0.0", PORT), DevServerHandler) as httpd:
        print(f"=====================================================")
        print(f"  OpenRouter Demos Local Dev Server Running")
        print(f"  Local URL:   http://localhost:{PORT}")
        print(f"=====================================================")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down server.")

if __name__ == "__main__":
    main()
