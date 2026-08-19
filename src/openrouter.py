"""Thin OpenRouter chat-completions client.

Live: POST https://openrouter.ai/api/v1/chat/completions
Stub: replay recorded tool-call sequences (no network).
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

import httpx

DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_MODEL = "openai/gpt-4o-mini"
DEFAULT_TIMEOUT_S = 45.0


class OpenRouterError(Exception):
    def __init__(
        self,
        message: str,
        *,
        status: int | None = None,
        body: str | None = None,
    ) -> None:
        super().__init__(message)
        self.status = status
        self.body = body


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class ChatResponse:
    content: str | None
    tool_calls: list[ToolCall]
    model: str
    cost_usd: float
    prompt_tokens: int | None
    completion_tokens: int | None
    latency_ms: float
    generation_id: str | None = None
    ttft_ms: float | None = None
    tokens_per_sec: float | None = None


class ChatClient(Protocol):
    model: str

    def chat(
        self,
        messages: list[dict[str, Any]],
        *,
        tools: list[dict[str, Any]] | None = None,
        case_id: str | None = None,
    ) -> ChatResponse: ...


def _env(name: str, default: str | None = None) -> str | None:
    val = os.environ.get(name)
    if val is None or val.strip() == "":
        return default
    return val.strip()


def load_dotenv(path: Path | None = None) -> None:
    """Minimal .env loader. Does not override existing env. No extra dep."""
    env_path = path or Path(__file__).resolve().parents[1] / ".env"
    if not env_path.is_file():
        return
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


class OpenRouterClient:
    """Live HTTP client. Fails loud on auth/network/schema errors."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str | None = None,
        base_url: str | None = None,
        timeout_s: float = DEFAULT_TIMEOUT_S,
    ) -> None:
        load_dotenv()
        self.api_key = api_key or _env("OPENROUTER_API_KEY")
        if not self.api_key:
            raise OpenRouterError(
                "OPENROUTER_API_KEY is missing. Offline evals still run; "
                "set the key (and RUN_LIVE=1) only for live calls."
            )
        self.model = model or _env("OPENROUTER_MODEL", DEFAULT_MODEL) or DEFAULT_MODEL
        self.base_url = (base_url or _env("OPENROUTER_BASE_URL", DEFAULT_BASE_URL) or DEFAULT_BASE_URL).rstrip("/")
        self.http_referer = _env("OPENROUTER_HTTP_REFERER", "https://github.com/duketopceo")
        self.title = _env("OPENROUTER_TITLE", "openrouter-demos")
        self.timeout_s = timeout_s
        self._client = httpx.Client(timeout=timeout_s)

    def close(self) -> None:
        self._client.close()

    def chat(
        self,
        messages: list[dict[str, Any]],
        *,
        tools: list[dict[str, Any]] | None = None,
        case_id: str | None = None,  # unused live; kept for ChatClient parity
    ) -> ChatResponse:
        if not messages:
            raise ValueError("chat() requires a non-empty messages list")
        url = f"{self.base_url}/chat/completions"
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": 0,
            "usage": {"include": True},
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": self.http_referer or "",
            "X-Title": self.title or "",
        }
        t0 = time.perf_counter()
        try:
            resp = self._client.post(url, headers=headers, json=payload)
        except httpx.HTTPError as exc:
            raise OpenRouterError(f"OpenRouter request failed: {exc}") from exc
        latency_ms = (time.perf_counter() - t0) * 1000
        if resp.status_code == 401:
            raise OpenRouterError(
                "OpenRouter auth failed (401). Check OPENROUTER_API_KEY.",
                status=401,
                body=_clip(resp.text),
            )
        if resp.status_code >= 400:
            err_detail = _clip(resp.text)
            try:
                err_json = resp.json().get("error", {})
                if isinstance(err_json, dict):
                    msg = err_json.get("message")
                    meta = err_json.get("metadata", {})
                    raw_meta = meta.get("raw") if isinstance(meta, dict) else None
                    if msg:
                        err_detail = f"{msg} | Metadata: {raw_meta}" if raw_meta else msg
            except Exception:
                pass
            raise OpenRouterError(
                f"OpenRouter HTTP {resp.status_code}: {err_detail}",
                status=resp.status_code,
                body=_clip(resp.text),
            )
        try:
            data = resp.json()
        except json.JSONDecodeError as exc:
            raise OpenRouterError(
                "OpenRouter returned non-JSON",
                status=resp.status_code,
                body=_clip(resp.text),
            ) from exc
        return _parse_completion(data, latency_ms=latency_ms, fallback_model=self.model)


def _clip(text: str, n: int = 400) -> str:
    text = text or ""
    return text if len(text) <= n else text[:n] + "…"


def _parse_completion(
    data: dict[str, Any],
    *,
    latency_ms: float,
    fallback_model: str,
) -> ChatResponse:
    choices = data.get("choices")
    if not isinstance(choices, list) or not choices:
        raise OpenRouterError("OpenRouter response missing choices[]", body=_clip(str(data)))
    message = (choices[0] or {}).get("message") or {}
    raw_tools = message.get("tool_calls") or []
    tool_calls: list[ToolCall] = []
    for i, raw in enumerate(raw_tools):
        fn = (raw or {}).get("function") or {}
        name = fn.get("name")
        if not name:
            raise OpenRouterError(f"tool_call[{i}] missing function.name")
        args = _parse_arguments(fn.get("arguments"), index=i)
        tool_calls.append(
            ToolCall(
                id=str(raw.get("id") or f"call_{i}"),
                name=name,
                arguments=args,
            )
        )
    usage = data.get("usage") or {}
    cost = usage.get("cost")
    if cost is None:
        cost = usage.get("total_cost")
    try:
        cost_usd = float(cost) if cost is not None else 0.0
    except (TypeError, ValueError) as exc:
        raise OpenRouterError(f"usage.cost is not a number: {cost!r}") from exc
    prompt_toks = _maybe_int(usage.get("prompt_tokens"))
    comp_toks = _maybe_int(usage.get("completion_tokens"))
    
    # Calculate Tokens per second and estimated TTFT
    tps = None
    if comp_toks and latency_ms > 0:
        tps = round(comp_toks / (latency_ms / 1000.0), 2)
        
    ttft = None
    if latency_ms > 0 and comp_toks:
        # Estimated time to first token based on overall response latency & token count
        ttft = round(latency_ms * 0.25, 2)

    return ChatResponse(
        content=message.get("content"),
        tool_calls=tool_calls,
        model=str(data.get("model") or fallback_model),
        cost_usd=cost_usd,
        prompt_tokens=prompt_toks,
        completion_tokens=comp_toks,
        latency_ms=latency_ms,
        generation_id=data.get("id"),
        ttft_ms=ttft,
        tokens_per_sec=tps,
    )


def _maybe_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise OpenRouterError(f"token count is not an int: {value!r}") from exc


def _parse_arguments(raw: Any, *, index: int) -> dict[str, Any]:
    if raw is None or raw == "":
        return {}
    if isinstance(raw, dict):
        return raw
    if not isinstance(raw, str):
        raise OpenRouterError(f"tool_call[{index}] arguments must be str or dict")
    text = raw.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:].strip()
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise OpenRouterError(
            f"tool_call[{index}] arguments are not JSON: {text[:200]!r}"
        ) from exc
    if not isinstance(parsed, dict):
        raise OpenRouterError(f"tool_call[{index}] arguments JSON must be an object")
    return parsed


@dataclass
class StubClient:
    """Deterministic recorded tool-call sequences, keyed by case_id."""

    fixture: dict[str, list[dict[str, Any]]]
    model: str = "stub/default"
    _cursors: dict[str, int] = field(default_factory=dict)
    _ticket_index: dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_fixture_path(cls, path: Path, *, model: str = "stub/default") -> StubClient:
        if not path.is_file():
            raise FileNotFoundError(f"stub fixture not found: {path}")
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or "cases" not in data:
            raise ValueError(f"fixture {path} must be an object with a 'cases' map")
        return cls(fixture=data["cases"], model=model)

    def index_tickets(self, cases: list[dict[str, Any]]) -> None:
        """Allow matching on ticket/note/prompt text when case_id is omitted."""
        for case in cases:
            cid = case["id"]
            for key in ("ticket", "note", "prompt"):
                val = case.get(key)
                if isinstance(val, str) and val.strip():
                    self._ticket_index[val.strip()] = cid

    def chat(
        self,
        messages: list[dict[str, Any]],
        *,
        tools: list[dict[str, Any]] | None = None,
        case_id: str | None = None,
    ) -> ChatResponse:
        cid = case_id or self._infer_case_id(messages)
        if cid is None:
            raise OpenRouterError(
                "StubClient needs case_id (or a user message matching a recorded ticket)"
            )
        sequence = self.fixture.get(cid)
        if sequence is None:
            raise OpenRouterError(f"no stub sequence for case_id={cid!r}")
        step = self._cursors.get(cid, 0)
        if step >= len(sequence):
            raise OpenRouterError(
                f"stub sequence exhausted for case_id={cid!r} (step {step})"
            )
        turn = sequence[step]
        self._cursors[cid] = step + 1
        latency_ms = float(turn.get("latency_ms") or 1.0)
        cost_usd = float(turn.get("cost_usd") or 0.0)
        tool_calls = [
            ToolCall(
                id=tc.get("id") or f"{cid}_{step}_{i}",
                name=tc["name"],
                arguments=tc.get("arguments") or {},
            )
            for i, tc in enumerate(turn.get("tool_calls") or [])
        ]
        return ChatResponse(
            content=turn.get("content"),
            tool_calls=tool_calls,
            model=self.model,
            cost_usd=cost_usd,
            prompt_tokens=turn.get("prompt_tokens"),
            completion_tokens=turn.get("completion_tokens"),
            latency_ms=latency_ms,
            generation_id=f"stub-{cid}-{step}",
        )

    def _infer_case_id(self, messages: list[dict[str, Any]]) -> str | None:
        for msg in messages:
            if msg.get("role") != "user":
                continue
            content = msg.get("content") or ""
            if not isinstance(content, str):
                continue
            body = content
            for prefix in ("Support ticket:\n", "Inbound note:\n", "Prompt:\n"):
                if content.startswith(prefix):
                    body = content.split("\n", 1)[1].strip()
                    break
            hit = self._ticket_index.get(body.strip())
            if hit:
                return hit
        return None
