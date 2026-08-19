"""In-memory FAQ for RouteKit, a synthetic OpenAI-compatible LLM gateway.

Not a real product. Entries are the *only* policy the agent is allowed to cite.
"""

from __future__ import annotations

import re
from typing import Any

FAQ: list[dict[str, Any]] = [
    {
        "id": "keys.create",
        "category": "auth",
        "tags": ["api", "key", "create", "dashboard"],
        "question": "How do I create an API key?",
        "answer": (
            "Dashboard → API Keys → Create. Secrets are shown once. "
            "Live keys start with rk_live_, test keys with rk_test_. "
            "Put the secret in an environment variable; do not paste keys into tickets."
        ),
    },
    {
        "id": "keys.rotate",
        "category": "auth",
        "tags": ["rotate", "key", "revoke"],
        "question": "How do I rotate an API key?",
        "answer": (
            "Dashboard → API Keys → Rotate. The previous secret stops working after "
            "10 minutes. Update ROUTKIT_API_KEY in your environment; no request-body "
            "changes are required."
        ),
    },
    {
        "id": "auth.401",
        "category": "auth",
        "tags": ["401", "unauthorized", "bearer", "invalid"],
        "question": "Why am I getting HTTP 401?",
        "answer": (
            "401 means the key is missing, malformed, or revoked. Send "
            "Authorization: Bearer rk_… with no extra whitespace, against "
            "https://api.routekit.dev/v1. HTTP-Referer is not used for auth."
        ),
    },
    {
        "id": "routing.fallback",
        "category": "routing",
        "tags": ["fallback", "models", "retry", "array"],
        "question": "How do I set a fallback model?",
        "answer": (
            "Pass models: [\"openai/gpt-4.1-mini\", \"anthropic/claude-3.5-haiku\"] "
            "on the chat request. RouteKit tries the list in order on 429 or 5xx. "
            "The single model field still works for one-shot routing."
        ),
    },
    {
        "id": "models.streaming",
        "category": "models",
        "tags": ["stream", "sse", "streaming", "chunks"],
        "question": "Does RouteKit support streaming?",
        "answer": (
            "Yes. Set stream: true. RouteKit emits OpenAI-compatible SSE chunks "
            "and a final [DONE] line. Tool-call deltas are streamed the same way."
        ),
    },
    {
        "id": "limits.rates",
        "category": "limits",
        "tags": ["rate", "limit", "rpm", "tpm", "429", "free", "pro"],
        "question": "What are the rate limits?",
        "answer": (
            "Free: 20 RPM and 100k TPM. Pro: 500 RPM and 2M TPM. 429 responses "
            "include Retry-After. A short burst of 2× RPM is allowed for 10 seconds."
        ),
    },
    {
        "id": "billing.usage",
        "category": "billing",
        "tags": ["usage", "invoice", "dashboard", "cost", "spend"],
        "question": "Where do I see usage and invoices?",
        "answer": (
            "Dashboard → Usage. Filter by API key, model, or day. Invoices live "
            "under Billing. Usage is USD at provider list price plus a 2% routing fee."
        ),
    },
    {
        "id": "billing.refunds",
        "category": "billing",
        "tags": ["refund", "credit", "chargeback", "money"],
        "question": "Can I get a refund or usage credit?",
        "answer": (
            "RouteKit does not issue automatic refunds or credits from chat support. "
            "Billing adjustments require a human on the Billing team plus a request id. "
            "Never promise a refund, credit, or chargeback outcome in a ticket reply."
        ),
    },
    {
        "id": "headers.attribution",
        "category": "howto",
        "tags": ["referer", "referrer", "x-title", "header", "attribution"],
        "question": "What are HTTP-Referer and X-Title?",
        "answer": (
            "Optional attribution headers forwarded to providers. HTTP-Referer should "
            "be your app URL. X-Title is a short app name. They are not credentials "
            "and are not used for authentication."
        ),
    },
    {
        "id": "latency.timeouts",
        "category": "limits",
        "tags": ["latency", "slow", "timeout", "502", "p95"],
        "question": "Requests are slow or timing out.",
        "answer": (
            "Default client timeout is 120s. For slow upstreams set extras.timeout_ms. "
            "p95 on OpenAI-class models is typically 2–8s. HTTP 502 means the upstream "
            "failed; configure a fallback list so RouteKit can retry another model."
        ),
    },
    {
        "id": "privacy.retention",
        "category": "howto",
        "tags": ["privacy", "train", "logs", "retention", "prompts"],
        "question": "Do you train on my prompts?",
        "answer": (
            "No. RouteKit does not train on prompts. Request logs are kept 7 days "
            "for debugging, then dropped. Zero-retention is an Enterprise contract option."
        ),
    },
    {
        "id": "account.delete",
        "category": "auth",
        "tags": ["delete", "account", "wipe", "keys", "gdpr"],
        "question": "How do I delete my account?",
        "answer": (
            "Account deletion is not self-serve. It requires identity verification "
            "through the Billing team. Chat support cannot delete accounts, wipe "
            "logs, or revoke every key in bulk."
        ),
    },
]

_TOKEN = re.compile(r"[a-z0-9][a-z0-9+._/-]{1,}", re.I)
_STOP = {
    "the", "and", "for", "how", "do", "i", "a", "an", "to", "of", "in", "on",
    "is", "my", "me", "it", "or", "be", "with", "what", "why", "are", "can",
}


def _tokens(text: str) -> list[str]:
    return [t.lower() for t in _TOKEN.findall(text) if t.lower() not in _STOP]


def search_faq(query: str, k: int = 3) -> list[dict[str, Any]]:
    """Keyword overlap search. Returns up to k hits with score > 0.

    Raises ValueError on empty query so the tool loop cannot silently no-op.
    """
    if not query or not str(query).strip():
        raise ValueError("search_faq requires a non-empty query")
    q = _tokens(query)
    if not q:
        q = [query.strip().lower()]
    scored: list[dict[str, Any]] = []
    for entry in FAQ:
        title = f"{entry['id']} {entry['question']} {' '.join(entry['tags'])} {entry['category']}".lower()
        body = entry["answer"].lower()
        score = 0
        for tok in q:
            if tok in title:
                score += 3
            elif tok in body:
                score += 1
        if score <= 0:
            continue
        scored.append(
            {
                "id": entry["id"],
                "category": entry["category"],
                "question": entry["question"],
                "answer": entry["answer"],
                "score": score,
            }
        )
    scored.sort(key=lambda h: (-h["score"], h["id"]))
    return scored[:k]


def faq_ids() -> set[str]:
    return {e["id"] for e in FAQ}
