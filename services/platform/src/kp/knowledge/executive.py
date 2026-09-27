"""Executive rows read from data/executive at ask time.

Company questions are aggregated across markets. A named market keeps that
market's series. Staffing and inventory rows are both included when a question
asks why a figure moved, so neither is dropped.
"""

from __future__ import annotations

import csv
import re
from pathlib import Path

from kp.config import get_settings
from kp.knowledge.retrieve import Bundle, _normalized_query, _outage_query

EXECUTIVE_KIND = "executive"

_PATTERNS = (
    r"\bmarkets?\b",
    r"\bmkt-\d+\b",
    r"\bdeployments?\b",
    r"\bworkforce\b",
    r"\bstaffing\b",
    r"\bovertime\b",
    r"\binventory risk\b",
    r"\bengineering health\b",
    r"\bcompany metrics\b",
    r"\bexecutive\b",
    r"\bweeks of supply\b",
    r"\bstockouts?\b",
    r"\bfailure rate\b",
    r"\bbusiness review\b",
    r"\binstallations\b",
    r"\bcsat\b",
    r"\bnps\b",
    r"\bcustomer experience\b",
    r"\bcustomer issues?\b",
    r"\brisks?\b",
    r"\bfunnel\b",
    r"\binitiatives?\b",
    r"\breliability\b",
    r"\bwarehouse metrics\b",
)


def executive_root() -> Path:
    return Path(get_settings().repo_root) / "data" / "executive"


def executive_query(query: str) -> bool:
    """Market, company-metric, risk, and customer-issue questions."""
    text = _normalized_query(query)
    if _legacy_company_query(text) or _value_language_query(text):
        return False
    if re.search(r"\bcomplaints?\b", text) and not re.search(r"\b(markets?|csat|customer issues?)\b", text):
        return False
    if any(re.search(pattern, text) for pattern in _PATTERNS):
        return True
    from kp.knowledge.field_ops import field_ops_query

    if field_ops_query(text):
        return False
    return bool(_named_markets(text, _rows(executive_root(), "markets.csv")))


def include_executive_records(bundle: Bundle, query: str, root: Path | None = None) -> None:
    """Prepend executive rows. root overrides the on-disk directory for tests."""
    text = _normalized_query(query)
    directory = root or executive_root()
    if root is None and not executive_query(text):
        return
    if root is not None and _legacy_company_query(text):
        return
    if root is not None and not _question_wants_executive(text, directory):
        return
    selected = _select(text, directory)
    if not selected:
        return
    existing = list(bundle.records.items())
    bundle.records.clear()
    for record_id, body, document_id in selected:
        bundle.add(EXECUTIVE_KIND, record_id, body, document_id)
    for key, value in existing:
        bundle.records.setdefault(key, value)
    _drill_down(bundle, text, selected)


def _question_wants_executive(text: str, directory: Path) -> bool:
    if any(re.search(pattern, text) for pattern in _PATTERNS):
        return True
    return bool(_named_markets(text, _rows(directory, "markets.csv")))


def _legacy_company_query(text: str) -> bool:
    """Revenue, forecast, and outage questions stay on the existing corpus."""
    if _outage_query(text):
        return True
    if "revenue" in text or ("forecast" in text and "installation" not in text):
        return True
    if "performance" in text and any(word in text for word in ("revenue", "company", "quarter", "fleet", "grid", "homes")):
        return True
    if "quarter" in text and any(word in text for word in ("revenue", "company", "savings", "fleet")):
        return True
    return False


def _value_language_query(text: str) -> bool:
    if "csat" in text or "customer issue" in text or "nps" in text:
        return False
    return "value" in text and any(word in text for word in ("language", "quote", "customers"))


def _why(text: str) -> bool:
    return bool(re.search(r"\b(why|cause|because|decline|down|slowdown|fell|falling|drill)\b", text))


def _rows(directory: Path, filename: str) -> list[dict[str, str]]:
    path = directory / filename
    if not path.is_file():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def _named_markets(text: str, markets: list[dict[str, str]]) -> list[str]:
    found: list[str] = []
    for row in sorted(markets, key=lambda item: len(item.get("market_name") or ""), reverse=True):
        name = (row.get("market_name") or "").casefold()
        market_id = (row.get("market_id") or "").upper()
        if name and name in text:
            found.append(market_id)
        elif market_id and market_id.casefold() in text:
            found.append(market_id)
    if found:
        return _unique(found)
    for row in markets:
        market_id = (row.get("market_id") or "").upper()
        for city in re.split(r"[;,]", row.get("primary_cities") or ""):
            city = city.strip().casefold()
            if city and re.search(rf"\b{re.escape(city)}\b", text):
                found.append(market_id)
                break
    return _unique(found)


def _unique(values: list[str]) -> list[str]:
    found: list[str] = []
    for value in values:
        if value and value not in found:
            found.append(value)
    return found


def _company_level(text: str, named: list[str]) -> bool:
    if re.search(r"\b(company metrics|across markets|company-wide|the company|overall|company installations|company )\b", text):
        return True
    if "company" in text and "market" not in text:
        return True
    if named:
        return False
    if re.search(r"\bmarkets\b", text):
        return False
    return bool(re.search(r"\b(installations|company metrics|csat|stockouts?)\b", text))


def _select(text: str, directory: Path) -> list[tuple[str, str, str]]:
    markets = _rows(directory, "markets.csv")
    named = _named_markets(text, markets)
    company = _company_level(text, named)
    why = _why(text)
    records: list[tuple[str, str, str]] = []
    seen: set[str] = set()

    def add(record_id: str, body: str, document_id: str) -> None:
        if not record_id or record_id in seen:
            return
        seen.add(record_id)
        records.append((record_id, _clip(body), document_id))

    if company:
        _add_company(add, directory)
    if named or re.search(r"\bmarkets?\b", text):
        _add_market_directory(add, markets, named)
    if named:
        _add_filtered(add, directory, "market_performance.csv", "period", named, "market_id", limit=8)
    if re.search(r"\b(daily|deployment)\b", text) and named:
        _add_recent(add, directory, "deployment_metrics.csv", "deployment_date", named, "market_id", limit=14)
    if why or re.search(r"\b(workforce|staffing|overtime|certified|technician count)\b", text):
        _add_filtered(add, directory, "workforce_metrics.csv", "week_start", named, "market_id", limit=6)
    if why or re.search(r"\b(inventory|stockout|weeks of supply|parts?)\b", text):
        _add_inventory(add, directory, named)
    if re.search(r"\b(engineering health|firmware|incidents?)\b", text):
        _add_recent_all(add, directory, "engineering_health_metrics.csv", "week_start", limit=8)
    if re.search(r"\brisks?\b", text) or why:
        _add_filtered(add, directory, "executive_risks.csv", "opened_date", named, "market_id", limit=6)
    if re.search(r"\balerts?\b", text) or why:
        _add_filtered(add, directory, "executive_alerts.csv", "created_at", named, "market_id", limit=4)
    if re.search(r"\b(documents?|memo|review)\b", text):
        _add_filtered(add, directory, "executive_documents.csv", "document_date", named, "market_id", limit=4)
    if re.search(r"\b(reliability|failure rate|hardware)\b", text):
        _add_recent_all(add, directory, "reliability_metrics.csv", "period", limit=8)
    if re.search(r"\bwarehouse metrics\b", text):
        _add_recent_all(add, directory, "warehouse_metrics.csv", "week_start", limit=6)
    if re.search(r"\b(business review|week over week|weekly)\b", text):
        _add_recent_all(add, directory, "weekly_business_review.csv", "week_start", limit=4)
    if re.search(r"\binitiatives?\b", text):
        _add_filtered(add, directory, "executive_initiatives.csv", "start_date", named, "market_id", limit=8)
    if re.search(r"\b(csat|nps|customer experience|satisfaction|response time)\b", text):
        _add_experience(add, directory, named)
    if re.search(r"\bcustomer issues?\b", text) or (re.search(r"\bissues?\b", text) and "complaint" not in text):
        _add_issues(add, directory, text, named)
    if re.search(r"\bfunnel\b|\bleads\b", text):
        _add_filtered(add, directory, "customer_funnel.csv", "week_start", named, "market_id", limit=6)
    if why or re.search(r"\bmetrics?\b", text) or "installation" in text:
        excerpt = _definition_excerpt(directory, text)
        if excerpt:
            add("metric-definitions", excerpt, "metric_definitions.md")
    return records


def _add_company(add, directory: Path) -> None:
    rows = _rows(directory, "company_metrics.csv")
    if rows:
        period_key = "period" if "period" in rows[0] else _period_key(rows[0])
        ordered = sorted(rows, key=lambda row: row.get(period_key) or "") if period_key else rows
        add("company-aggregate", _company_summary(ordered, period_key), "company_metrics.csv")
        for row in ordered:
            period = row.get(period_key) or ""
            add(f"company-{period or len(ordered)}", _company_row(row), "company_metrics.csv")
        return
    performance = _rows(directory, "market_performance.csv")
    if not performance:
        return
    period_key = "period" if "period" in performance[0] else _period_key(performance[0])
    if not period_key:
        return
    grouped: dict[str, float] = {}
    for row in performance:
        period = row.get(period_key) or ""
        value = _number(row.get("installations_completed"))
        if period and value is not None:
            grouped[period] = grouped.get(period, 0.0) + value
    if len(grouped) < 2:
        return
    ordered_periods = sorted(grouped)
    latest, prior = ordered_periods[-1], ordered_periods[-2]
    add(
        "company-aggregate",
        (
            f"Company aggregate installations_completed summed across markets. "
            f"latest {latest} {grouped[latest]:.0f} prior {prior} {grouped[prior]:.0f}. "
            "Not a single market row."
        ),
        "market_performance.csv",
    )
    for period in ordered_periods:
        add(
            f"company-{period}",
            f"Company installations_completed {period} {grouped[period]:.0f} summed across markets.",
            "market_performance.csv",
        )


def _company_summary(ordered: list[dict[str, str]], period_key: str | None) -> str:
    latest = ordered[-1]
    prior = ordered[-2] if len(ordered) > 1 else {}
    latest_period = latest.get(period_key or "") or "latest"
    prior_period = prior.get(period_key or "") or "prior"
    keys = (
        "installations_completed",
        "installations_scheduled",
        "installations_target",
        "installation_attainment_percentage",
        "critical_incidents",
        "stockout_events",
        "average_csat",
        "workforce_utilization_percentage",
        "open_critical_risks",
    )
    bits = [
        f"Company aggregate across markets for {latest_period} compared with {prior_period}. Not a single market row."
    ]
    for key in keys:
        if key in latest:
            bits.append(f"{key} latest {latest.get(key, '')} prior {prior.get(key, '')}")
    return " ".join(bits) + "."


def _company_row(row: dict[str, str]) -> str:
    return "Company metric " + " ".join(f"{key} {value}" for key, value in row.items() if value) + "."


def _add_market_directory(add, markets: list[dict[str, str]], named: list[str]) -> None:
    chosen = [row for row in markets if row.get("market_id") in named] if named else markets
    for row in chosen:
        add(row["market_id"], _market_text(row), "markets.csv")


def _add_filtered(add, directory: Path, filename: str, period_key: str, named: list[str], market_key: str, limit: int) -> None:
    rows = _rows(directory, filename)
    if not rows:
        return
    if named and market_key in rows[0]:
        rows = [row for row in rows if (row.get(market_key) or "").upper() in named or not row.get(market_key)]
    rows = _sorted_recent(rows, period_key)[:limit] if period_key in (rows[0] if rows else {}) else rows[:limit]
    for index, row in enumerate(rows):
        record_id = _record_id(row, filename, index)
        add(record_id, _generic(filename, row), filename)


def _add_recent(add, directory: Path, filename: str, period_key: str, named: list[str], market_key: str, limit: int) -> None:
    _add_filtered(add, directory, filename, period_key, named, market_key, limit)


def _add_recent_all(add, directory: Path, filename: str, period_key: str, limit: int) -> None:
    rows = _sorted_recent(_rows(directory, filename), period_key)[:limit]
    for index, row in enumerate(rows):
        add(_record_id(row, filename, index), _generic(filename, row), filename)


def _add_inventory(add, directory: Path, named: list[str]) -> None:
    rows = _rows(directory, "inventory_risk.csv")
    if named:
        kept = []
        for row in rows:
            markets = (row.get("affected_market_ids") or "").upper()
            if any(market_id in markets for market_id in named):
                kept.append(row)
        rows = kept or rows
    for index, row in enumerate(rows[:8]):
        add(row.get("risk_id") or f"inventory-{index}", _generic("inventory_risk.csv", row), "inventory_risk.csv")


def _add_experience(add, directory: Path, named: list[str]) -> None:
    rows = _rows(directory, "customer_experience_metrics.csv")
    if not rows:
        return
    if named:
        rows = [row for row in rows if (row.get("market_id") or "").upper() in named]
    recent = _sorted_recent(rows, "week_start")
    if not recent:
        return
    latest_week = recent[0].get("week_start")
    latest_rows = [row for row in recent if row.get("week_start") == latest_week]
    if len(latest_rows) > 1 and not named:
        scores = [_number(row.get("csat_score")) for row in latest_rows]
        scores = [score for score in scores if score is not None]
        average = sum(scores) / len(scores) if scores else 0
        add(
            f"csat-{latest_week}",
            (
                f"Customer experience aggregate week {latest_week} average csat_score {average:.1f} "
                f"across {len(latest_rows)} markets. Not a single market row."
            ),
            "customer_experience_metrics.csv",
        )
    for index, row in enumerate(latest_rows[:7]):
        add(_record_id(row, "customer_experience_metrics.csv", index), _generic("customer_experience_metrics.csv", row), "customer_experience_metrics.csv")


def _add_issues(add, directory: Path, text: str, named: list[str]) -> None:
    rows = _rows(directory, "customer_issues.csv")
    if named:
        rows = [row for row in rows if (row.get("market_id") or "").upper() in named]
    if "firmware" in text:
        rows = [row for row in rows if (row.get("category") or "").casefold() == "firmware"]
    open_rows = [row for row in rows if (row.get("status") or "").casefold() == "open"]
    chosen = open_rows or rows
    for index, row in enumerate(chosen[:8]):
        add(row.get("issue_id") or f"issue-{index}", _generic("customer_issues.csv", row), "customer_issues.csv")


def _sorted_recent(rows: list[dict[str, str]], period_key: str) -> list[dict[str, str]]:
    if not rows or period_key not in rows[0]:
        return list(reversed(rows))
    return sorted(rows, key=lambda row: row.get(period_key) or "", reverse=True)


def _record_id(row: dict[str, str], filename: str, index: int) -> str:
    for key in ("market_id", "risk_id", "alert_id", "document_id", "initiative_id", "issue_id", "period", "week_start"):
        if row.get(key) and key != "market_id":
            return f"{filename}-{row[key]}-{index}"
        if key == "market_id" and row.get("market_id") and row.get("week_start"):
            return f"{row['market_id']}-{row['week_start']}"
        if key == "market_id" and row.get("market_id") and row.get("period"):
            return f"{row['market_id']}-{row['period']}"
    if row.get("market_id"):
        return f"{filename}-{row['market_id']}-{index}"
    return f"{filename}-{index}"


def _period_key(row: dict[str, str]) -> str | None:
    for key in row:
        folded = key.casefold()
        if any(token in folded for token in ("date", "month", "week", "period")):
            return key
    return None


def _number(value: str | None) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _generic(filename: str, row: dict[str, str]) -> str:
    label = filename.removesuffix(".csv").replace("_", " ")
    return label + " " + " ".join(f"{key} {value}" for key, value in row.items() if value) + "."


def _market_text(row: dict[str, str]) -> str:
    return (
        f"Market {row.get('market_id', '')} {row.get('market_name', '')} status {row.get('status', '')} "
        f"warehouse {row.get('warehouse_id', '')} cities {row.get('primary_cities', '')} "
        f"technician_count {row.get('technician_count', '')} "
        f"certified_technician_count {row.get('certified_technician_count', '')} "
        f"open_positions {row.get('open_positions', '')}. {row.get('service_note', '')}"
    )


def _definition_excerpt(directory: Path, text: str) -> str:
    path = directory / "metric_definitions.md"
    if not path.is_file():
        return ""
    body = path.read_text(encoding="utf-8")
    intro = body.split("\n## ", 1)[0].strip()
    chunks = [intro]
    if "installation" in text and "## installations_completed" in body:
        section = body.split("## installations_completed", 1)[1].split("\n## ", 1)[0]
        chunks.append("## installations_completed" + section)
    return "\n\n".join(chunks)[:1800]


def _clip(body: str) -> str:
    text = " ".join(body.split())
    if len(text) > 900:
        return text[:897] + "..."
    return text


def _drill_down(bundle: Bundle, text: str, selected: list[tuple[str, str, str]]) -> None:
    """Pull a few engineering or field rows when the question asks to go below the metric."""
    if not _why(text):
        return
    devices: list[str] = []
    incidents: list[str] = []
    jobs: list[str] = []
    want_engineering = bool(re.search(r"\b(firmware|engineering|incidents?|devices?)\b", text))
    want_jobs = bool(re.search(r"\bjobs?\b", text))
    if not want_engineering and not want_jobs:
        return
    for _, body, _document in selected:
        if want_engineering:
            for token in re.findall(r"\bDEV-\d{3}\b", body):
                if token not in devices:
                    devices.append(token)
            for token in re.findall(r"\bINC-\d{3}\b", body):
                if token not in incidents:
                    incidents.append(token)
        if want_jobs:
            for token in re.findall(r"\bJ\d{3}\b", body):
                if token not in jobs:
                    jobs.append(token)
    devices = devices[:2]
    incidents = incidents[:2]
    jobs = jobs[:2]
    if devices or incidents:
        from kp.knowledge.engineering import include_engineering_records

        include_engineering_records(bundle, " ".join(devices + incidents))
    if jobs:
        from kp.knowledge.field_ops import include_field_ops_records

        include_field_ops_records(bundle, "job " + " ".join(jobs))
