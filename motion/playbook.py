"""In-memory GTM playbook for RouteKit. Synthetic. No CRM rows, no real people."""

from __future__ import annotations

import re
from typing import Any

PLAYBOOK: list[dict[str, Any]] = [
    {
        "id": "icp",
        "tags": ["icp", "who", "fit", "series", "volume"],
        "title": "Ideal customer profile",
        "body": (
            "ICP: teams shipping LLM products at roughly 100k+ tokens/min, usually Series A–C. "
            "Hobby/student use is welcome on Free, not a sales motion. "
            "Disqualify: 'just exploring' with no product and no timeline."
        ),
    },
    {
        "id": "pricing",
        "tags": ["price", "pricing", "pro", "enterprise", "cost"],
        "title": "Public pricing",
        "body": (
            "Free: 20 RPM, 100k TPM. Pro: $99/mo, 500 RPM, 2M TPM. "
            "Enterprise is custom and is quoted only by a human. "
            "Playbook forbids inventing discounts, promo codes, or free Enterprise."
        ),
    },
    {
        "id": "disco",
        "tags": ["qualify", "discovery", "questions", "volume", "budget"],
        "title": "Discovery questions",
        "body": (
            "Before booking: (1) role/authority, (2) request volume or TPM, "
            "(3) models they need, (4) timeline this quarter vs research. "
            "Missing two or more → qualify, do not book."
        ),
    },
    {
        "id": "book",
        "tags": ["book", "intro", "calendar", "demo"],
        "title": "When to book an intro",
        "body": (
            "Book only if ICP-ish AND a decision-maker (or named champion) AND a timeline. "
            "Offer a 20-minute intro, not a 50-person hold. Humans send the calendar link."
        ),
    },
    {
        "id": "enterprise",
        "tags": ["enterprise", "dpa", "soc2", "msa", "procurement", "rfp", "lawyer"],
        "title": "Enterprise / legal / procurement",
        "body": (
            "DPA, SOC2, MSA, RFPs, and lawyer review go to a human. "
            "Do not sign, attach, or promise paper."
        ),
    },
    {
        "id": "product",
        "tags": ["fallback", "routing", "streaming", "api", "gateway"],
        "title": "Product one-liners",
        "body": (
            "RouteKit is an OpenAI-compatible LLM gateway: fallbacks, streaming, usage by key. "
            "Inbound product questions can be answered from this playbook; do not invent SLAs."
        ),
    },
    {
        "id": "credits",
        "tags": ["credit", "refund", "incentive", "switch"],
        "title": "Credits and switch incentives",
        "body": (
            "No GTM bot may grant usage credits, refunds, or 'switch from competitor' cash. "
            "Those asks escalate to a human."
        ),
    },
    {
        "id": "out_of_scope",
        "tags": ["scrape", "homework", "weather", "out of scope"],
        "title": "Out of scope",
        "body": (
            "This inbox is RouteKit GTM. Decline scrapers, homework, and weather. "
            "A short reply is enough; do not book."
        ),
    },
]

_TOKEN = re.compile(r"[a-z0-9][a-z0-9+._/-]{1,}", re.I)
_STOP = {"the", "and", "for", "a", "an", "to", "of", "in", "on", "is", "we", "our", "i"}


def lookup_playbook(query: str, k: int = 3) -> list[dict[str, Any]]:
    if not query or not str(query).strip():
        raise ValueError("lookup_playbook requires a non-empty query")
    q = [t.lower() for t in _TOKEN.findall(query) if t.lower() not in _STOP]
    if not q:
        q = [query.strip().lower()]
    scored: list[dict[str, Any]] = []
    for entry in PLAYBOOK:
        title = f"{entry['id']} {entry['title']} {' '.join(entry['tags'])}".lower()
        body = entry["body"].lower()
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
                "title": entry["title"],
                "body": entry["body"],
                "score": score,
            }
        )
    scored.sort(key=lambda h: (-h["score"], h["id"]))
    return scored[:k]
