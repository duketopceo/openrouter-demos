"""Live debate topic presets — English, math, RouteKit, and custom."""

from __future__ import annotations

from typing import Any

TOPIC_PRESETS: dict[str, list[dict[str, Any]]] = {
    "english": [
        {
            "id": "english-em-dash",
            "topic": "Resolved: the em dash is overused in modern prose and weakens clarity.",
            "side_a": "The em dash is a legitimate, flexible punctuation tool.",
            "side_b": "Overuse of em dashes makes writing sloppy and hard to parse.",
        },
        {
            "id": "english-active-voice",
            "topic": "Resolved: active voice should be the default in technical writing.",
            "side_a": "Active voice improves clarity and accountability.",
            "side_b": "Passive voice is sometimes clearer or more appropriate.",
        },
    ],
    "math": [
        {
            "id": "math-pi-tau",
            "topic": "Resolved: tau (2π) is a better circle constant than pi for teaching and formulas.",
            "side_a": "Tau simplifies radians and many formulas.",
            "side_b": "Pi is entrenched, sufficient, and changing constants adds confusion.",
        },
        {
            "id": "math-order-ops",
            "topic": "Resolved: PEMDAS/BODMAS is taught correctly in standard curricula.",
            "side_a": "Standard order-of-operations rules are unambiguous when taught with grouping.",
            "side_b": "Ambiguous expressions show PEMDAS is underspecified without explicit grouping.",
        },
        {
            "id": "math-bayes-base-rate",
            "topic": "Resolved: in a disease test with 99% sensitivity, 99% specificity, and 1% prevalence, a positive result implies ~50% chance of disease (not 99%).",
            "side_a": "Bayes' theorem with base rates yields ~50%; ignoring prevalence is the base-rate fallacy.",
            "side_b": "A 99% accurate test means a positive is ~99% likely to be a true positive.",
        },
        {
            "id": "math-primes-infinitude",
            "topic": "Resolved: there are infinitely many prime numbers.",
            "side_a": "Euclid's proof by contradiction shows no finite list of primes can be complete.",
            "side_b": "Primes thin out fast enough that the set could be finite — intuition beats proof.",
        },
        {
            "id": "math-derivative-power",
            "topic": "Resolved: d/dx(x^n) = n·x^(n-1) for positive integers n, proven by the limit definition (not just pattern matching).",
            "side_a": "The binomial theorem + limit definition gives the power rule rigorously.",
            "side_b": "The power rule is a mnemonic pattern; the limit definition is unnecessary pedantry.",
        },
        {
            "id": "math-monty-hall",
            "topic": "Resolved: on Monty Hall (3 doors, host opens a goat), switching doors wins 2/3 of the time.",
            "side_a": "Conditional probability: switching wins iff your first pick was wrong (2/3).",
            "side_b": "Two remaining doors ⇒ 50/50; switching cannot beat symmetry.",
        },
    ],
    "routekit": [
        {
            "id": "routing-vs-direct",
            "topic": "Resolved: RouteKit-style multi-model routing beats a single direct provider SDK for production agents.",
            "side_a": "Gateway routing with fallbacks improves reliability and ops.",
            "side_b": "Direct SDK calls are simpler, faster, and easier to debug.",
        },
    ],
}

CATEGORY_HINTS: dict[str, str] = {
    "english": (
        "Debate in clear English. Use rhetoric, definitions, and concrete examples. "
        "Quote or paraphrase when citing sources. No code unless illustrating a point."
    ),
    "math": (
        "Debate with explicit steps, equations, and numeric reasoning. "
        "Show work. Challenge incorrect algebra or logic directly."
    ),
    "routekit": (
        "RouteKit is a synthetic OpenAI-compatible LLM gateway. "
        "You may call recall_fact over the synthetic brief. No web search."
    ),
}


def list_presets(category: str | None = None) -> list[dict[str, Any]]:
    if category and category in TOPIC_PRESETS:
        return TOPIC_PRESETS[category]
    out: list[dict[str, Any]] = []
    for items in TOPIC_PRESETS.values():
        out.extend(items)
    return out
