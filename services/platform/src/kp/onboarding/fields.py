"""Onboarding field rules shared by the Temporal workflow and the memory runner."""

from __future__ import annotations

import re
from datetime import datetime

from kp.labels import ROLES

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
TASK_QUEUE = "kp-onboarding"
_NAME_STOP = {"email", "role", "as", "a", "an", "the", "new", "is", "and", "with"}
_NOT_A_NAME = _NAME_STOP | {
    "engineer",
    "engineering",
    "ceo",
    "marketing",
    "manager",
    "operations",
    "director",
    "employee",
    "onboard",
    "onboarding",
}
_ROLE_PATTERNS = (
    (r"operations[_\s\-]?managers?", "operations_manager"),
    (r"\bops\s+managers?\b", "operations_manager"),
    (r"\b(?:ceo|chief executive(?:\s+officer)?)\b", "ceo"),
    (r"\bmarketing\b", "marketing"),
    (r"\bengineers?\b", "engineer"),
    (r"\bengineering\b", "engineer"),
)


def missing_fields(details: dict | None) -> list[str]:
    details = details or {}
    flow = FLOW_BY_KIND.get(str(details.get("kind") or ""))
    if flow is not None:
        return [label for key, label in flow.fields if not str(details.get(key) or "").strip()]
    missing: list[str] = []
    name = str(details.get("name") or "").strip()
    email = str(details.get("email") or "").strip()
    role = str(details.get("role") or "").strip()
    if len(name) < 2:
        missing.append("name")
    if EMAIL_RE.fullmatch(email) is None:
        missing.append("email")
    if role not in ROLES:
        missing.append("role")
    return missing


def merge_details(current: dict | None, incoming: dict | None) -> dict:
    merged = {
        "name": (current or {}).get("name"),
        "email": (current or {}).get("email"),
        "role": (current or {}).get("role"),
    }
    incoming = incoming or {}
    name = str(incoming.get("name") or "").strip()
    email = str(incoming.get("email") or "").strip().lower()
    role = str(incoming.get("role") or "").strip()
    if len(name) >= 2:
        merged["name"] = name
    if EMAIL_RE.fullmatch(email):
        merged["email"] = email
    if role in ROLES:
        merged["role"] = role
    return merged


def _clean_name(raw: str) -> str | None:
    parts: list[str] = []
    for word in raw.replace(",", " ").split():
        token = word.strip(".,;:\"'`")
        if not token:
            continue
        if token.lower() in _NAME_STOP:
            break
        if not re.fullmatch(r"[A-Za-z][A-Za-z'\-]*", token):
            break
        parts.append(token)
        if len(parts) == 4:
            break
    if not parts or all(part.lower() in _NOT_A_NAME for part in parts):
        return None
    name = " ".join(parts)
    if len(name) < 2:
        return None
    return name


def _role_from(text: str) -> str | None:
    for pattern, role in _ROLE_PATTERNS:
        if re.search(pattern, text or "", re.I):
            return role
    return None


def extract_params(text: str) -> dict:
    """Pull name, email, and role out of a chat message. Missing keys stay absent."""
    params: dict[str, str] = {}
    source = text or ""
    email = EMAIL_RE.search(source)
    if email:
        params["email"] = email.group(0).lower()

    labeled_role = re.search(
        r"\brole\s*(?:is|:)\s+['\"]?(?:an?\s+)?([A-Za-z]+(?:\s+[A-Za-z]+){0,3})",
        source,
        re.I,
    )
    role = _role_from(labeled_role.group(1) if labeled_role else "") or _role_from(source)
    if role:
        params["role"] = role

    labeled_name = re.search(
        r"\b(?:name\s*(?:is|:)|named)\s+['\"]?([A-Za-z]+(?:\s+[A-Za-z]+){0,3})",
        source,
        re.I,
    )
    onboarded = re.search(r"\bonboard\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)", source)
    introduced = re.search(r"\bfor\s+['\"]?([A-Za-z]+(?:\s+[A-Za-z]+){0,3})", source, re.I)
    raw = ""
    if labeled_name:
        raw = labeled_name.group(1)
    elif introduced and (is_onboarding_text(source) or "email" in params or "role" in params):
        raw = introduced.group(1)
    elif onboarded:
        raw = onboarded.group(1)
    name = _clean_name(raw) if raw else None
    if name:
        params["name"] = name
    return params


# Customer phrases are matched before the generic "onboard" employee rule.
_CUSTOMER_ONBOARDING = re.compile(
    r"\bonboard(?:ing)?\s+(?:(?:a|an|the|our|new)\s+){0,3}customers?\b"
    r"|\bcustomers?\s+onboard(?:ing)?\b",
    re.I,
)
_EMPLOYEE_ONBOARDING = re.compile(r"\bonboard(?:ing)?\b|\bnew hire\b|\bnew employee\b", re.I)
_EMPLOYEE_NAMED = re.compile(r"\b(?:employees?|new hire)\b", re.I)

SYSTEM_TYPES = ("whole-home battery", "commercial storage", "backup")
_SYSTEM_PATTERNS = (
    (r"\bwhole[\s\-]*home\s+batter(?:y|ies)\b", "whole-home battery"),
    (r"\bcommercial\s+storage\b", "commercial storage"),
    (r"\bbackup\b", "backup"),
)
_LABELED_SYSTEM = re.compile(
    r"\bsystem(?:[\s\-]+type)?\s*(?:is|:)\s+['\"]?(?:an?\s+)?"
    r"([A-Za-z][A-Za-z\-]*(?:[\s\-][A-Za-z][A-Za-z\-]*){0,4})",
    re.I,
)
_LABELED_CITY = re.compile(
    r"\bcity\s*(?:is|:|of)\s+['\"]?([A-Za-z][A-Za-z'\-]*(?:\s+[A-Za-z][A-Za-z'\-]*){0,3})",
    re.I,
)
_LABELED_CUSTOMER_NAME = re.compile(
    r"\b(?:customer\s+)?(?:name\s*(?:is|:)|named)\s+['\"]?"
    r"([A-Za-z][A-Za-z'\-]*(?:\s+[A-Za-z][A-Za-z'\-]*){0,5})",
    re.I,
)
_INTRODUCED_NAME = re.compile(
    r"\bfor\s+['\"]?([A-Za-z][A-Za-z'\-]*(?:\s+[A-Za-z][A-Za-z'\-]*){0,5})",
    re.I,
)
_AFTER_CUSTOMER_NAME = re.compile(
    r"\bcustomers?\s+['\"]?([A-Za-z][A-Za-z'\-]*(?:\s+[A-Za-z][A-Za-z'\-]*){0,5})",
    re.I,
)
_CUSTOMER_NAME_STOP = {
    "email",
    "role",
    "as",
    "a",
    "an",
    "the",
    "new",
    "is",
    "and",
    "with",
    "city",
    "system",
    "type",
    "contact",
    "customer",
    "customers",
    "onboard",
    "onboarding",
    "for",
    "in",
    "please",
    "start",
    "to",
    "of",
}
_CITY_STOP = {
    "system",
    "type",
    "email",
    "name",
    "contact",
    "and",
    "with",
    "role",
    "onboard",
    "onboarding",
    "customer",
    "customers",
    "for",
    "is",
    "please",
}
_NOT_A_CUSTOMER_NAME = _CUSTOMER_NAME_STOP | {"employee", "engineer", "manager", "households"}


def is_customer_onboarding_text(text: str) -> bool:
    return _CUSTOMER_ONBOARDING.search(text or "") is not None


def is_onboarding_text(text: str) -> bool:
    """Employee onboarding. Customer and specialist phrases do not match."""
    source = text or ""
    if match_specialist_workflow(source):
        return False
    generic = _EMPLOYEE_ONBOARDING.search(source) is not None
    if _EMPLOYEE_NAMED.search(source) and generic:
        return True
    if is_customer_onboarding_text(source):
        return False
    return generic


def workflow_id(session_id: str, kind: str = "employee") -> str:
    if kind == "customer":
        return f"onboard-customer-{session_id}"
    if kind in FLOW_BY_KIND:
        return f"onboard-specialist-{kind}-{session_id}"
    return f"onboard-employee-{session_id}"


def _clean_words(raw: str, stop: set[str], limit: int, *, keep_articles: bool = False) -> str | None:
    parts: list[str] = []
    for word in (raw or "").replace(",", " ").split():
        token = word.strip(".,;:\"'`()[]")
        if not token:
            continue
        lower = token.lower()
        if not parts and not keep_articles and lower in {"a", "an", "the"}:
            continue
        if lower in stop:
            break
        if not re.fullmatch(r"[A-Za-z][A-Za-z'\-]*", token):
            break
        parts.append(token)
        if len(parts) == limit:
            break
    if not parts:
        return None
    cleaned = " ".join(parts)
    if len(cleaned) < 2:
        return None
    return cleaned


def _clean_customer_name(raw: str) -> str | None:
    cleaned = _clean_words(raw, _CUSTOMER_NAME_STOP, 6)
    if cleaned is None:
        return None
    if all(part.lower() in _NOT_A_CUSTOMER_NAME for part in cleaned.split()):
        return None
    return cleaned


def _clean_place(raw: str) -> str | None:
    return _clean_words(raw, _CITY_STOP, 3, keep_articles=True)


def _system_type_from(text: str) -> str | None:
    source = text or ""
    for pattern, canonical in _SYSTEM_PATTERNS:
        if re.search(pattern, source, re.I):
            return canonical
    return None


def _system_from_message(source: str, name: str | None) -> str | None:
    labeled = _LABELED_SYSTEM.search(source)
    if labeled:
        return _system_type_from(labeled.group(1))
    haystack = source
    if name:
        haystack = re.sub(re.escape(name), " ", source, count=1, flags=re.I)
    return _system_type_from(haystack)


def _customer_name(source: str, params: dict) -> str | None:
    labeled = _LABELED_CUSTOMER_NAME.search(source)
    introduced = _INTRODUCED_NAME.search(source)
    after = _AFTER_CUSTOMER_NAME.search(source)
    raw = ""
    if labeled:
        raw = labeled.group(1)
    elif introduced and (is_customer_onboarding_text(source) or "email" in params or "city" in params):
        raw = introduced.group(1)
    elif after and is_customer_onboarding_text(source):
        raw = after.group(1)
    return _clean_customer_name(raw) if raw else None


def missing_customer_fields(details: dict | None) -> list[str]:
    details = details or {}
    missing: list[str] = []
    name = str(details.get("name") or "").strip()
    email = str(details.get("email") or "").strip()
    city = str(details.get("city") or "").strip()
    system_type = str(details.get("system_type") or "").strip()
    if len(name) < 2:
        missing.append("name")
    if EMAIL_RE.fullmatch(email) is None:
        missing.append("email")
    if _clean_place(city) is None:
        missing.append("city")
    if system_type not in SYSTEM_TYPES:
        missing.append("system type")
    return missing


def merge_customer_details(current: dict | None, incoming: dict | None) -> dict:
    merged = {"name": None, "email": None, "city": None, "system_type": None}
    for source in (current or {}, incoming or {}):
        name = _clean_customer_name(str(source.get("name") or ""))
        email = str(source.get("email") or "").strip().lower()
        city = _clean_place(str(source.get("city") or ""))
        system = source.get("system_type")
        canonical = system if isinstance(system, str) and system in SYSTEM_TYPES else _system_type_from(str(system or ""))
        if name:
            merged["name"] = name
        if EMAIL_RE.fullmatch(email):
            merged["email"] = email
        if city:
            merged["city"] = city
        if canonical in SYSTEM_TYPES:
            merged["system_type"] = canonical
    return merged


def extract_customer_params(text: str) -> dict:
    """Pull customer name, email, city, and system type out of a chat message."""
    params: dict[str, str] = {}
    source = text or ""
    email = EMAIL_RE.search(source)
    if email:
        params["email"] = email.group(0).lower()
    city_match = _LABELED_CITY.search(source)
    if city_match:
        city = _clean_place(city_match.group(1))
        if city:
            params["city"] = city
    name = _customer_name(source, params)
    if name:
        params["name"] = name
    system = _system_from_message(source, name)
    if system:
        params["system_type"] = system
    return params


# Specialist flows share one Temporal workflow and branch on kind.
# Employee and customer phrases are reserved and are not matched here.
_EMPLOYEE_LOCK = re.compile(
    r"\b(?:employee onboard|onboard employee|new employee|new hire)\b",
    re.I,
)
_SPECIALTIES = ("battery", "inverter", "firmware", "thermal")
_TEXAS_CANONICAL = (
    "Abilene", "Allen", "Amarillo", "Arlington", "Austin", "Bastrop", "Baytown",
    "Beaumont", "Brownsville", "Bryan", "Buda", "Carrollton", "Cedar Park",
    "College Station", "Corpus Christi", "Dallas", "Denton", "Dripping Springs",
    "Edinburg", "El Paso", "Elgin", "Fort Worth", "Frisco", "Galveston", "Garland",
    "Georgetown", "Grand Prairie", "Houston", "Hutto", "Irving", "Killeen", "Kyle",
    "Laredo", "Lakeway", "League City", "Leander", "Lewisville", "Lockhart",
    "Lubbock", "Manor", "Marble Falls", "McAllen", "McKinney", "Mesquite",
    "Midland", "Mission", "New Braunfels", "Odessa", "Pasadena", "Pearland",
    "Pflugerville", "Plano", "Richardson", "Round Rock", "San Antonio", "San Marcos",
    "Sugar Land", "Taylor", "Temple", "The Woodlands", "Tyler", "Waco", "Wichita Falls",
)
_TEXAS_CITIES = {name.lower(): name for name in _TEXAS_CANONICAL}
_DATE_FORMATS = (
    "%Y-%m-%d",
    "%m/%d/%Y",
    "%m-%d-%Y",
    "%B %d, %Y",
    "%B %d %Y",
    "%b %d, %Y",
    "%b %d %Y",
    "%d %B %Y",
    "%d %b %Y",
)
_DATE_PATTERNS = (
    r"\b\d{4}-\d{2}-\d{2}\b",
    r"\b\d{1,2}/\d{1,2}/\d{4}\b",
    r"\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}\b",
    r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2},?\s+\d{4}\b",
    r"\b\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}\b",
    r"\b\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{4}\b",
)


class SpecialistFlow:
    def __init__(self, kind: str, workflow: str, phrases: tuple[str, ...], fields: tuple[tuple[str, str], ...], aliases: dict[str, str], criteria: str, description: str) -> None:
        self.kind = kind
        self.workflow = workflow
        self.phrases = phrases
        self.fields = fields
        self.aliases = aliases
        self.criteria = criteria
        self.description = description


def _flow(kind: str, workflow: str, phrases: tuple[str, ...], fields: tuple[tuple[str, str], ...], aliases: dict[str, str], criteria: str) -> SpecialistFlow:
    labels = ", ".join(label for _, label in fields)
    spoken = ", ".join(phrases)
    return SpecialistFlow(
        kind,
        workflow,
        phrases,
        fields,
        aliases,
        criteria,
        f"Onboard when the user says {spoken}. Params: {labels}.",
    )


SPECIALIST_FLOWS: tuple[SpecialistFlow, ...] = (
    _flow(
        "field_technician",
        "onboard_field_technician",
        ("onboard field technician", "onboard electrician", "field technician onboard", "electrician onboard"),
        (("name", "name"), ("email", "email"), ("trade", "trade"), ("home_city", "home city")),
        {"home city": "home_city", "city": "home_city", "trade": "trade", "name": "name", "email": "email"},
        "Start onboard_field_technician only for onboard field technician, onboard electrician, field technician onboard, or electrician onboard.",
    ),
    _flow(
        "installer_partner",
        "onboard_installer_partner",
        ("onboard installer partner", "onboard contractor", "installer partner onboard", "contractor onboard"),
        (("company_name", "company name"), ("contact_name", "contact name"), ("email", "email"), ("city", "city")),
        {"company name": "company_name", "contact name": "contact_name", "email": "email", "city": "city"},
        "Start onboard_installer_partner only for onboard installer partner, onboard contractor, installer partner onboard, or contractor onboard.",
    ),
    _flow(
        "warehouse_associate",
        "onboard_warehouse_associate",
        ("onboard warehouse associate", "warehouse associate onboard"),
        (("name", "name"), ("email", "email"), ("warehouse_city", "warehouse city"), ("shift", "shift")),
        {"warehouse city": "warehouse_city", "city": "warehouse_city", "shift": "shift", "name": "name", "email": "email"},
        "Start onboard_warehouse_associate only for onboard warehouse associate or warehouse associate onboard.",
    ),
    _flow(
        "engineer",
        "onboard_engineer",
        ("onboard engineer", "engineer onboard"),
        (("name", "name"), ("email", "email"), ("specialty", "specialty")),
        {"specialty": "specialty", "name": "name", "email": "email"},
        "Start onboard_engineer only for the phrases onboard engineer or engineer onboard. A role of engineer inside employee onboard stays onboard_employee.",
    ),
    _flow(
        "operations_manager",
        "onboard_operations_manager",
        ("onboard operations manager", "operations manager onboard"),
        (("name", "name"), ("email", "email"), ("region", "region")),
        {"region": "region", "name": "name", "email": "email"},
        "Start onboard_operations_manager only for onboard operations manager or operations manager onboard. Setting an employee role to operations manager stays onboard_employee.",
    ),
    _flow(
        "warehouse_launch",
        "onboard_warehouse_launch",
        ("onboard new market", "warehouse launch", "onboard warehouse launch"),
        (("market_city", "market city"), ("warehouse_name", "warehouse name"), ("launch_date", "launch date"), ("manager_email", "manager email")),
        {
            "market city": "market_city",
            "city": "market_city",
            "warehouse name": "warehouse_name",
            "launch date": "launch_date",
            "manager email": "manager_email",
            "email": "manager_email",
        },
        "Start onboard_warehouse_launch only for onboard new market, warehouse launch, or onboard warehouse launch.",
    ),
)
FLOW_BY_KIND = {flow.kind: flow for flow in SPECIALIST_FLOWS}
FLOW_BY_WORKFLOW = {flow.workflow: flow for flow in SPECIALIST_FLOWS}
SPECIALIST_WORKFLOW_NAMES = frozenset(FLOW_BY_WORKFLOW)


def match_specialist_workflow(text: str) -> str | None:
    """Workflow name for one of the six specialist start phrases, else None."""
    source = text or ""
    if _EMPLOYEE_LOCK.search(source) or is_customer_onboarding_text(source):
        return None
    hits: list[tuple[int, int, str]] = []
    for flow in SPECIALIST_FLOWS:
        for phrase in flow.phrases:
            match = re.search(rf"\b{re.escape(phrase)}\b", source, re.I)
            if match:
                hits.append((match.start(), -len(phrase), flow.workflow))
    if not hits:
        return None
    hits.sort()
    return hits[0][2]


def kind_for_workflow(name: str) -> str | None:
    flow = FLOW_BY_WORKFLOW.get(name or "")
    return flow.kind if flow else None


def specialist_catalog() -> list[dict]:
    return [
        {
            "name": flow.workflow,
            "description": flow.description,
            "params": [label for _, label in flow.fields],
            "criteria": flow.criteria,
        }
        for flow in SPECIALIST_FLOWS
    ]


def _labeled(text: str, aliases: dict[str, str]) -> dict[str, str]:
    if not text or not aliases:
        return {}
    ordered = sorted(aliases, key=len, reverse=True)
    pattern = re.compile(
        r"\b(" + "|".join(re.escape(label) for label in ordered) + r")\s*(?:is|:)\s*",
        re.I,
    )
    matches = list(pattern.finditer(text))
    found: dict[str, str] = {}
    for index, match in enumerate(matches):
        key = aliases.get(match.group(1).lower())
        if key is None or key in found:
            continue
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        raw = text[match.end():end].split("\n", 1)[0]
        value = re.sub(r"[\s,;]+$", "", raw.strip()).strip("\"'`")
        value = re.sub(r"\s+", " ", value).strip(" ,;")
        if value:
            found[key] = value
    return found


def _person(raw: str | None) -> str | None:
    return _clean_name(raw or "") if raw else None


def _free_text(raw: str | None) -> str | None:
    if not raw:
        return None
    text = re.sub(r"\s+", " ", raw).strip(" .,;\"'`")
    if len(text) < 2 or EMAIL_RE.search(text):
        return None
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9 &'./\-]*", text):
        return None
    return text


def _place(raw: str | None) -> str | None:
    if not raw:
        return None
    text = re.sub(r"\s+", " ", raw).strip(" .,;\"'`")
    text = re.sub(r",?\s+(?:texas|tx)$", "", text, flags=re.I).strip(" .,;")
    if len(text) < 2 or not re.fullmatch(r"[A-Za-z][A-Za-z .'\-]*", text):
        return None
    if text.lower() in {"email", "name", "trade", "shift", "day", "night", "the", "a", "an"}:
        return None
    return text


def _email_value(raw: str | None, text: str) -> str | None:
    if raw:
        match = EMAIL_RE.search(raw)
        if match:
            return match.group(0).lower()
    match = EMAIL_RE.search(text or "")
    return match.group(0).lower() if match else None


def _trade_value(raw: str | None, text: str) -> str | None:
    def one(blob: str) -> str | None:
        electrician = re.search(r"\belectrician\b", blob or "", re.I) is not None
        technician = re.search(r"\bfield technician\b", blob or "", re.I) is not None
        if electrician and not technician:
            return "electrician"
        if technician and not electrician:
            return "field technician"
        return None

    if raw and one(raw):
        return one(raw)
    hits: list[tuple[int, str]] = []
    for phrase, trade in (
        ("onboard electrician", "electrician"),
        ("electrician onboard", "electrician"),
        ("onboard field technician", "field technician"),
        ("field technician onboard", "field technician"),
    ):
        match = re.search(rf"\b{re.escape(phrase)}\b", text or "", re.I)
        if match:
            hits.append((match.start(), trade))
    if not hits:
        return one(text or "")
    hits.sort()
    return hits[0][1]


def _shift_value(raw: str | None, text: str) -> str | None:
    def one(blob: str) -> str | None:
        night = re.search(r"\bnight\b", blob or "", re.I) is not None
        day = re.search(r"\bday\b", blob or "", re.I) is not None
        if night and not day:
            return "night"
        if day and not night:
            return "day"
        return None

    if raw and one(raw):
        return one(raw)
    if re.search(r"\bnight\s+shift\b", text or "", re.I):
        return "night"
    if re.search(r"\bday\s+shift\b", text or "", re.I):
        return "day"
    return None


def _specialty_value(raw: str | None, text: str) -> str | None:
    def hits(blob: str) -> list[str]:
        return [item for item in _SPECIALTIES if re.search(rf"\b{item}\b", blob or "", re.I)]

    if raw:
        found = hits(raw)
        if len(found) == 1:
            return found[0]
        if len(found) > 1:
            return None
    found = hits(text or "")
    return found[0] if len(found) == 1 else None


def _region_value(raw: str | None) -> str | None:
    if not raw:
        return None
    text = re.sub(r"\s+", " ", raw).strip(" .,;\"'`")
    lowered = re.sub(r"[\s\-]+", " ", text.lower()).strip()
    lowered = re.sub(r"^(?:the|for)\s+", "", lowered)
    if lowered in {"central texas"}:
        return "central Texas"
    place = _place(raw)
    if place is None:
        return None
    return _TEXAS_CITIES.get(place.lower())


def _parse_date(raw: str) -> str | None:
    text = re.sub(r"(\d+)(st|nd|rd|th)\b", r"\1", raw or "", flags=re.I)
    text = re.sub(r"\bSept\b", "Sep", text, flags=re.I)
    words = []
    for word in re.sub(r"\s+", " ", text).strip(" .,;").split():
        words.append(word[:1].upper() + word[1:] if word[:1].isalpha() else word)
    text = " ".join(words)
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def _search_date(blob: str | None) -> str | None:
    if not blob:
        return None
    cleaned = re.sub(r"(\d+)(st|nd|rd|th)\b", r"\1", blob, flags=re.I)
    cleaned = re.sub(r"\bSept\b", "Sep", cleaned)
    for pattern in _DATE_PATTERNS:
        match = re.search(pattern, cleaned, re.I)
        if not match:
            continue
        parsed = _parse_date(match.group(0))
        if parsed:
            return parsed
    return None


def _date_value(raw: str | None, text: str) -> str | None:
    if raw:
        parsed = _parse_date(raw) or _search_date(raw)
        if parsed:
            return parsed
    return _search_date(text)


def _field_value(kind: str, key: str, raw: str | None, text: str) -> str | None:
    if key in {"name", "contact_name"}:
        return _person(raw)
    if key in {"email", "manager_email"}:
        return _email_value(raw, text)
    if key in {"company_name", "warehouse_name"}:
        return _free_text(raw)
    if key in {"home_city", "city", "warehouse_city", "market_city"}:
        return _place(raw)
    if key == "trade":
        return _trade_value(raw, text)
    if key == "shift":
        return _shift_value(raw, text)
    if key == "specialty":
        return _specialty_value(raw, text)
    if key == "region":
        return _region_value(raw)
    if key == "launch_date":
        return _date_value(raw, text)
    del kind
    return None


def parse_specialist(kind: str, text: str) -> dict:
    flow = FLOW_BY_KIND[kind]
    labeled = _labeled(text or "", flow.aliases)
    params: dict[str, str] = {"kind": kind, "workflow": flow.workflow}
    for key, _label in flow.fields:
        value = _field_value(kind, key, labeled.get(key), text or "")
        if value:
            params[key] = value
    return params


def merge_specialist(kind: str, current: dict | None, incoming: dict | None) -> dict:
    flow = FLOW_BY_KIND[kind]
    current = current or {}
    incoming = incoming or {}
    merged: dict = {"kind": kind, "workflow": flow.workflow}
    for key, _label in flow.fields:
        new = str(incoming.get(key) or "").strip()
        old = str(current.get(key) or "").strip()
        merged[key] = new or old or None
    return merged


def success_sentence(details: dict) -> str:
    kind = str(details.get("kind") or "")
    if kind == "field_technician":
        return f"Onboarded {details['name']} ({details['email']}) as {details['trade']} in {details['home_city']}."
    if kind == "installer_partner":
        return (
            f"Onboarded installer partner {details['company_name']} ({details['email']}) "
            f"in {details['city']}, contact {details['contact_name']}."
        )
    if kind == "warehouse_associate":
        return (
            f"Onboarded {details['name']} ({details['email']}) as warehouse associate "
            f"in {details['warehouse_city']} on the {details['shift']} shift."
        )
    if kind == "engineer":
        return f"Onboarded {details['name']} ({details['email']}) as engineer, specialty {details['specialty']}."
    if kind == "operations_manager":
        return f"Onboarded {details['name']} ({details['email']}) as operations manager for {details['region']}."
    if kind == "warehouse_launch":
        return (
            f"Onboarded warehouse {details['warehouse_name']} in {details['market_city']}, "
            f"launch {details['launch_date']}, manager {details['manager_email']}."
        )
    raise KeyError(kind)
