"""Follow-up asks that point at the previous answer."""

from __future__ import annotations

import re

_PRIOR = re.compile(r"\b(above|previous|earlier|prior)\b", re.I)


def refers_to_prior(query: str) -> bool:
    return _PRIOR.search(query or "") is not None


def latest_assistant(turns: list[dict]) -> str:
    for turn in reversed(turns):
        if turn.get("role") == "assistant" and str(turn.get("content") or "").strip():
            return str(turn["content"]).strip()
    return ""


def prior_answer(turns: list[dict], query: str) -> str:
    """The earlier answer this question points at. A forecast follow-up skips later replies that are not forecasts."""
    if not refers_to_prior(query):
        return ""
    contents = [
        str(turn.get("content") or "").strip()
        for turn in turns
        if turn.get("role") == "assistant" and str(turn.get("content") or "").strip()
    ]
    if not contents:
        return ""
    if "forecast" in (query or "").casefold():
        from kp.knowledge.artifacts import _forecast_points

        for content in reversed(contents):
            if _forecast_points(content):
                return content
    return contents[-1]
