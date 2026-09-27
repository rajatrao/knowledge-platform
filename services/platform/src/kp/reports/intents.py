"""Clear-ask routing for persona report workflows."""

from __future__ import annotations

import re

from kp.onboarding.fields import is_customer_onboarding_text, is_onboarding_text, match_specialist_workflow

ONBOARD_WORKFLOW = "onboard_employee"
CUSTOMER_ONBOARD_WORKFLOW = "onboard_customer"

PERSONA_WORKFLOWS: dict[str, tuple[str, ...]] = {
    "ceo": ("issue_trend_report", "severity_digest"),
    "operations_manager": ("blocker_ranking", "installation_risk_report"),
    "engineer": ("technical_issue_counts", "related_incident_report"),
    "marketing": ("sentiment_breakdown", "value_theme_counts"),
}

REPORT_WORKFLOW_NAMES = frozenset(
    name for names in PERSONA_WORKFLOWS.values() for name in names
)

WORKFLOW_DESCRIPTIONS = {
    "issue_trend_report": (
        "Issues ordered by complaint count, with trend, severity, first seen, and last seen."
    ),
    "severity_digest": "Issues grouped by severity, with the complaint ids that support each issue.",
    "blocker_ranking": (
        "Operational blockers in counted order, with the complaints and tickets that support each."
    ),
    "installation_risk_report": (
        "At-risk installations, open operational incidents, and delayed installations, with source row ids."
    ),
    "technical_issue_counts": (
        "Battery telemetry, mobile app, and firmware complaint counts, with linked incident ids."
    ),
    "related_incident_report": "Incidents ordered by how many complaints they link to.",
    "sentiment_breakdown": (
        "Positive, neutral, and negative shares from stored complaints, with the row ids behind each share."
    ),
    "value_theme_counts": (
        "Energy independence, installation experience, and battery reliability, with source document ids."
    ),
}

# Phrases that name one report. Sample knowledge questions do not match these.
_PATTERNS: dict[str, tuple[str, ...]] = {
    "issue_trend_report": (
        r"\bissue[_\s-]?trends?(?:\s+report)?\b",
        r"\btrend report\b",
    ),
    "severity_digest": (
        r"\bseverity[_\s-]?digest\b",
        r"\bissues?\s+(?:grouped\s+)?by\s+severity\b",
        r"\bseverity report\b",
    ),
    "blocker_ranking": (
        r"\bblocker[_\s-]?ranking\b",
        r"\brank(?:ed|ing)?\s+(?:the\s+)?(?:operational\s+)?blockers?\b",
    ),
    "installation_risk_report": (
        r"\binstallation[_\s-]?risk(?:\s+report)?\b",
        r"\bat[- ]risk installations\b",
        r"\bdelayed installations\b",
        r"\bopen operational incidents\b",
    ),
    "technical_issue_counts": (r"\btechnical[_\s-]?issue[_\s-]?counts?\b",),
    "related_incident_report": (
        r"\brelated[_\s-]?incidents?(?:[_\s-]+report)?\b",
        r"\bincidents?\s+ordered\s+by\b",
    ),
    "sentiment_breakdown": (
        r"\bsentiment[_\s-]?breakdown\b",
        r"\bsentiment report\b",
        r"\bpositive,?\s+neutral,?\s+(?:and\s+)?negative\b",
    ),
    "value_theme_counts": (
        r"\bvalue[_\s-]?theme[_\s-]?counts?\b",
        r"\bvalue themes?\s+counts?\b",
        r"\benergy independence,?\s+installation experience,?\s+(?:and\s+)?battery reliability\b",
    ),
}

_COMPILED: list[tuple[str, re.Pattern[str]]] = [
    (
        name,
        re.compile("|".join((rf"\b{re.escape(name)}\b", *patterns)), re.I),
    )
    for name, patterns in _PATTERNS.items()
]


def matching_workflows(query: str) -> list[str]:
    """Workflow names the text clearly asks for, earliest mention first."""
    hits: list[tuple[int, str]] = []
    text = query or ""
    for name, pattern in _COMPILED:
        match = pattern.search(text)
        if match:
            hits.append((match.start(), name))
    hits.sort(key=lambda item: (item[0], item[1]))
    return [name for _, name in hits]


def allowed_workflow(persona: str, query: str) -> str | None:
    """Onboarding for any persona, otherwise only that persona's reports."""
    specialist = match_specialist_workflow(query)
    if specialist:
        return specialist
    if is_customer_onboarding_text(query) and not is_onboarding_text(query):
        return CUSTOMER_ONBOARD_WORKFLOW
    if is_onboarding_text(query):
        return ONBOARD_WORKFLOW
    allowed = PERSONA_WORKFLOWS.get(persona, ())
    for name in matching_workflows(query):
        if name in allowed:
            return name
    return None


def catalog_workflows(persona: str) -> list[dict]:
    reports = []
    for name in PERSONA_WORKFLOWS.get(persona, ()):
        reports.append(
            {
                "name": name,
                "description": (
                    f"{WORKFLOW_DESCRIPTIONS[name]} No extra params; runs on the full corpus."
                ),
                "params": [],
            }
        )
    return reports
