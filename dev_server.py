#!/usr/bin/env python3
"""
OpenRouter Demos Local Dev Server & Interactive Dashboard
Serves a local web interface to trigger, configure, and inspect all 4 OpenRouter demos:
1. Support Deflection (deflect)
2. GTM Motion (motion)
3. Provider Ops Bakeoff (bakeoff)
4. Caesar Model Debate (caesar)
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
from src.dev_stream import run_caesar_live, sse_event, stream_subprocess

PORT = 8080
REPO_DIR = Path(__file__).parent.resolve()
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
  </style>
</head>
<body>
  <header>
    <h1>OpenRouter Demos <span>LOCAL DEV</span></h1>
    <div class="status-badge">Port: 8080 | Mode: <span id="env-status">Loading...</span></div>
  </header>
  <main>
    <div class="env-section">
      <div class="env-section-header">
        <h3>OpenRouter Settings & Model Selector</h3>
        <div class="toggle-bar">
          <button id="toggle-curated" class="toggle-btn active" onclick="setCatalogFilter('curated')">Curated Heavy Hitters (32)</button>
          <button id="toggle-all" class="toggle-btn" onclick="setCatalogFilter('all')">All Models (415)</button>
        </div>
      </div>
      <p id="filter-desc">Filtered to essential open-weight heavyweights (Nemotron, Llama 3.3, Mistral, Phi-4, Solar) & top frontier models per provider.</p>
      <div class="form-group">
        <input type="password" id="api-key" style="flex-grow:1" placeholder="sk-or-v1-..." />
        <button class="btn btn-secondary" onclick="saveConfig()">Save Settings to .env</button>
        <button class="btn" id="btn-run-baked" style="background: var(--purple); color: white;" onclick="runBakedDemo()">Run Full Demo (No API Key)</button>
        <button class="btn" id="btn-run-all" style="background: var(--green); color: white;" onclick="runAllDemos()">Run All Live (API Key)</button>
      </div>

      <div class="model-selector-row">
        <div class="model-field">
          <label>Primary Model (Deflect / Motion / Caesar Judge):</label>
          <select id="model-primary"></select>
        </div>
        <div class="model-field">
          <label>Bakeoff / Debate Model A:</label>
          <select id="model-a"></select>
        </div>
        <div class="model-field">
          <label>Bakeoff / Debate Model B:</label>
          <select id="model-b"></select>
        </div>
      </div>
    </div>

    <div class="grid">
      <div class="card">
        <h3>1. Support Deflection</h3>
        <p>Ticket classification & deflection harness with policy guardrails.</p>
        <div class="btn-group">
          <button class="btn demo-btn" onclick="runDemo('deflect')">Run Harness</button>
          <button class="btn btn-secondary" onclick="viewResult('deflect.json')">Results</button>
        </div>
      </div>
      <div class="card">
        <h3>2. GTM Motion</h3>
        <p>Inbound lead qualification and routing automated workflow.</p>
        <div class="btn-group">
          <button class="btn demo-btn" onclick="runDemo('motion')">Run Harness</button>
          <button class="btn btn-secondary" onclick="viewResult('motion.json')">Results</button>
        </div>
      </div>
      <div class="card">
        <h3>3. Provider Ops Bakeoff</h3>
        <p>Quality & latency benchmarking comparison between two LLM models.</p>
        <div class="btn-group">
          <button class="btn demo-btn" onclick="runDemo('bakeoff')">Run Bakeoff</button>
          <button class="btn btn-secondary" onclick="viewResult('bakeoff.json')">Results</button>
        </div>
      </div>
      <div class="card">
        <h3>4. Caesar Debate</h3>
        <p>Two OpenRouter models in structured debate evaluated by Caesar judge.</p>
        <div class="btn-group">
          <button class="btn demo-btn" onclick="runDemo('caesar')">Run Batch</button>
          <button class="btn btn-secondary" onclick="startCaesarLive()">Live Debate</button>
          <a class="btn btn-secondary" href="/caesar/chat.html" target="_blank">Open Replay</a>
        </div>
      </div>
    </div>

    <div class="console-section">
      <div class="console-header">
        <h3 id="console-title">
          <span id="loading-spinner" class="spinner" style="display:none;"></span>
          <span id="console-title-text">Execution Debug Log</span>
        </h3>
        <button class="btn btn-secondary" onclick="runPytest()">Run Pytest Suite (Offline)</button>
      </div>
      <div id="progress-wrap" style="display:none; margin-bottom:12px;">
        <div id="progress-label" style="font-size:12px; color:var(--muted); margin-bottom:6px;">Starting…</div>
        <div style="background:#21262d; border:1px solid var(--border); border-radius:6px; height:10px; overflow:hidden;">
          <div id="progress-bar" style="background:var(--green); height:100%; width:0%; transition:width 0.25s ease;"></div>
        </div>
      </div>
      <pre id="output">Click Run Full Demo (No API Key) for the baked walkthrough, or run individual harnesses with a live key...</pre>
    </div>

    <div style="margin-top: 24px;">
      <h3 style="color: var(--heading)">Caesar Trace Interactive Viewer</h3>
      <div class="iframe-container">
        <iframe id="caesar-iframe" src="/caesar/chat.html"></iframe>
      </div>
    </div>
  </main>

  <script>
    let rawModelsData = { all: [], curated: [] };
    let currentFilter = "curated";

    loadModelsList();

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
      document.getElementById("toggle-all").classList.toggle("active", filter === "all");
      
      const desc = document.getElementById("filter-desc");
      if (filter === "curated") {
        desc.textContent = "Filtered to essential open-weight heavyweights (Nemotron, Llama 3.3, Mistral, Phi-4, Solar) & top 3-4 frontier models per provider.";
      } else {
        desc.textContent = "Showing all 415 available models on OpenRouter.";
      }
      renderDatalist();
    }

    function renderDatalist() {
      const selects = [
        document.getElementById("model-primary"),
        document.getElementById("model-a"),
        document.getElementById("model-b")
      ];
      const models = currentFilter === "curated" ? (rawModelsData.curated || []) : (rawModelsData.all || []);
      
      const groups = {};
      models.forEach(m => {
        const prov = m.provider || "Other";
        if (!groups[prov]) groups[prov] = [];
        groups[prov].push(m);
      });

      selects.forEach(sel => {
        const curVal = sel.value;
        sel.innerHTML = "";
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
        if (curVal) sel.value = curVal;
      });
    }

    async function checkEnvStatus() {
      try {
        const res = await fetch("/api/key");
        const data = await res.json();
        const badge = document.getElementById("env-status");
        if (data.hasKey) {
          badge.textContent = "Live OpenRouter API Key configured";
          badge.style.color = "#58a6ff";
          if (data.maskedKey) {
            document.getElementById("api-key").placeholder = data.maskedKey;
          }
        } else {
          badge.textContent = "Offline Mode (Using Stub Fixtures)";
          badge.style.color = "#8b949e";
        }
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
            modelB: modelB
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

    function startCaesarLive() {
      document.getElementById("caesar-iframe").src = "/caesar/chat.html?live=1";
      document.getElementById("caesar-iframe").scrollIntoView({ behavior: "smooth" });
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
          body: JSON.stringify({ demo: name })
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
      logAppend("Starting full suite (stream): Deflect, Motion, Bakeoff, Caesar...", "info");
      try {
        const res = await fetch("/api/run-all-stream", { method: "POST" });
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
        elif self.path == "/api/key":
            file_env = load_env_file()
            key = os.environ.get("OPENROUTER_API_KEY") or file_env.get("OPENROUTER_API_KEY", "")
            masked = f"{key[:7]}...{key[-4:]}" if len(key) > 12 else ""
            models_info = {
                "primary": file_env.get("OPENROUTER_MODEL", "nvidia/nemotron-3.5-lightning"),
                "modelA": file_env.get("OPENROUTER_MODEL_A", "nvidia/nemotron-3.5-lightning"),
                "modelB": file_env.get("OPENROUTER_MODEL_B", "openai/gpt-4o-mini"),
            }
            self._send_json({"hasKey": bool(key), "maskedKey": masked, "models": models_info})
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

            file_env["RUN_LIVE"] = "1"

            new_lines = [f"{k}={v}" for k, v in file_env.items()]
            env_file.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
            self._send_json({"ok": True})
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
            }
            target_module = module_map.get(demo)
            if not target_module:
                self._send_json({"error": "Invalid demo name"}, status=400)
                return
            file_env = load_env_file()
            env = os.environ.copy()
            env.update(file_env)
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
            file_env = load_env_file()
            env = os.environ.copy()
            env.update(file_env)
            env["PROGRESS"] = "1"
            demos = [
                ("Support Deflection", [str(VENV_PYTHON), "-m", "deflect.harness"]),
                ("GTM Motion", [str(VENV_PYTHON), "-m", "motion.harness"]),
                ("Provider Ops Bakeoff", [str(VENV_PYTHON), "-m", "bakeoff.runner"]),
                ("Caesar Debate", [str(VENV_PYTHON), "-m", "caesar.harness"]),
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
                ("Caesar Debate", [str(VENV_PYTHON), "-m", "caesar.harness"])
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
                "caesar": "caesar.harness"
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
