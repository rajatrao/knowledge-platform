"""Fixed-seed fake support corpus. Counts come from the rows, not from the UI."""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta

from kp.corpus.inventory import inventory_documents, inventory_knowledge_items
from kp.corpus.outages import outage_documents, outage_knowledge_items
from kp.corpus.performance import company_documents, company_knowledge_items
from kp.labels import (
    BLOCKER_CAUSE,
    BLOCKER_LABELS,
    CAUSE_LABELS,
    TECHNICAL_LABELS,
    THEME_LABELS,
    VALUE_LABELS,
)
from kp.periods import AS_OF, CURRENT_START, PREVIOUS_START, period_of, trend_percent

SEED = 20260926

REGIONS = ("Houston", "Dallas", "Austin", "San Antonio")
CHANNELS = ("support", "email", "phone")

THEME_PLAN = (
    (
        "installation_delays",
        175,
        105,
        (
            ("permitting_delays", 70),
            ("installer_scheduling", 52),
            ("customer_communication", 35),
            ("other", 18),
        ),
    ),
    (
        "battery_performance",
        110,
        66,
        (
            ("capacity_below_spec", 40),
            ("backup_duration", 30),
            ("charge_rate", 25),
            ("other", 15),
        ),
    ),
    (
        "billing_confusion",
        90,
        54,
        (
            ("rate_plan", 32),
            ("invoice_timing", 26),
            ("credit_application", 20),
            ("other", 12),
        ),
    ),
    (
        "app_problems",
        70,
        42,
        (
            ("login", 24),
            ("telemetry_display", 20),
            ("notifications", 16),
            ("other", 10),
        ),
    ),
    (
        "communication_problems",
        55,
        33,
        (
            ("status_updates", 20),
            ("scheduling_calls", 16),
            ("unclear_next_steps", 12),
            ("other", 7),
        ),
    ),
)

VALUE_SENTENCES = {
    "energy_independence": (
        "What I value is energy independence, because the battery keeps our home powered when the ERCOT grid drops."
    ),
    "installation_experience": (
        "What I value is the installation experience, because the crew walked us through every step of putting the home battery in."
    ),
    "battery_reliability": (
        "What I value is battery reliability, because the unit carries the house through outages without a flicker."
    ),
}

VALUE_QUOTAS = (
    ("energy_independence", 122),
    ("installation_experience", 102),
    ("battery_reliability", 81),
)

ISSUE_DESCRIPTIONS = {
    "installation_delays": "Members are waiting on home battery installation.",
    "battery_performance": "Members are reporting battery performance problems.",
    "billing_confusion": "Members are confused by billing.",
    "app_problems": "Members are having trouble with the mobile app.",
    "communication_problems": "Members are not getting clear updates.",
    "battery_telemetry": "Battery telemetry is failing to report member systems.",
    "mobile_app": "The mobile app is failing for members.",
    "firmware": "Firmware is failing on member batteries.",
}

ACTIONS = {
    ("installation_delays", "permitting_delays"): (
        "Assign a permitting specialist to each delayed installation and send the member a dated permit status every three business days."
    ),
    ("installation_delays", "installer_scheduling"): (
        "Publish installer capacity by metro each Monday and do not book installations beyond the crews on that sheet."
    ),
    ("installation_delays", "customer_communication"): (
        "Send the member a single next-step message within one business day whenever an installation date moves."
    ),
    ("installation_delays", "other"): (
        "Review installation delays that do not match permitting, installer scheduling, or customer communication in the weekly operations standup."
    ),
    ("battery_performance", "capacity_below_spec"): (
        "Compare the installed battery capacity with the member's contract and schedule a site check when the reading is short."
    ),
    ("battery_performance", "backup_duration"): (
        "Log backup duration on every outage ticket and replace packs that fall short of the home-backup window."
    ),
    ("battery_performance", "charge_rate"): (
        "Check the charge rate against the site's electrical panel before telling the member the battery is underperforming."
    ),
    ("battery_performance", "other"): (
        "Open a battery performance review when the complaint does not match capacity, backup duration, or charge rate."
    ),
    ("billing_confusion", "rate_plan"): (
        "Walk the member through the rate plan on the bill and point at the line that changed."
    ),
    ("billing_confusion", "invoice_timing"): (
        "Explain invoice timing in one note that names the service window the charge covers."
    ),
    ("billing_confusion", "credit_application"): (
        "Apply the pending credit on the next bill and tell the member the date it will show."
    ),
    ("billing_confusion", "other"): (
        "Escalate billing confusion that is not a rate plan, invoice timing, or credit question to the billing lead."
    ),
    ("app_problems", "login"): (
        "Reset the mobile app login and confirm the member can open the battery status screen."
    ),
    ("app_problems", "telemetry_display"): (
        "Repair the telemetry display so the app shows the same battery state the device is reporting."
    ),
    ("app_problems", "notifications"): (
        "Turn member notifications back on and send a test alert for the next battery event."
    ),
    ("app_problems", "other"): (
        "File an app problem that is not login, telemetry display, or notifications with the mobile on-call."
    ),
    ("communication_problems", "status_updates"): (
        "Send a status update the same day an installation or incident changes, using the member's preferred channel."
    ),
    ("communication_problems", "scheduling_calls"): (
        "Return scheduling calls within one business day and record the time the member was reached."
    ),
    ("communication_problems", "unclear_next_steps"): (
        "Close every conversation with one unclear-next-steps check so the member can repeat the next step."
    ),
    ("communication_problems", "other"): (
        "Review communication problems that are not status updates, scheduling calls, or unclear next steps."
    ),
}

EXTRA_DOCS = (
    {
        "theme": "operational_blockers",
        "cause": "permitting",
        "title": "Operational blocker — permitting",
        "action": "Track permitting as an operational blocker and pair each permit hold with the member conversation that named it.",
    },
    {
        "theme": "operational_blockers",
        "cause": "installer_capacity",
        "title": "Operational blocker — installer capacity",
        "action": "Treat installer capacity as an operational blocker and stop promising dates the metro crew cannot cover.",
    },
    {
        "theme": "operational_blockers",
        "cause": "customer_scheduling",
        "title": "Operational blocker — customer scheduling",
        "action": "Treat customer scheduling as an operational blocker and confirm the member's availability before the crew rolls.",
    },
    {
        "theme": "technical",
        "cause": "battery_telemetry",
        "title": "Technical issue — battery telemetry",
        "action": "When battery telemetry drops, link the engineering incident to the member complaints that reported the missing data.",
        "issue_slug": "battery_telemetry",
    },
    {
        "theme": "technical",
        "cause": "mobile_app",
        "title": "Technical issue — mobile app",
        "action": "When the mobile app fails, link the engineering incident to the member complaints that described the failure.",
        "issue_slug": "mobile_app",
    },
    {
        "theme": "technical",
        "cause": "firmware",
        "title": "Technical issue — firmware",
        "action": "When firmware misbehaves, link the engineering incident to the member complaints that showed the fault.",
        "issue_slug": "firmware",
    },
    {
        "theme": "value_language",
        "cause": "energy_independence",
        "title": "Value language — energy independence",
        "action": "Keep the customer's words for energy independence verbatim when marketing describes why members stay.",
    },
    {
        "theme": "value_language",
        "cause": "installation_experience",
        "title": "Value language — installation experience",
        "action": "Keep the customer's words for the installation experience verbatim when marketing describes why members stay.",
    },
    {
        "theme": "value_language",
        "cause": "battery_reliability",
        "title": "Value language — battery reliability",
        "action": "Keep the customer's words for battery reliability verbatim when marketing describes why members stay.",
    },
    {
        "theme": "company",
        "cause": None,
        "title": "Base Power company brief",
        "action": "Base Power installs home batteries of about 39 to 78 kWh that back up members and earn grid revenue in ERCOT.",
    },
)


def _stamp(start: datetime, end: datetime, index: int, count: int) -> datetime:
    span = (end - start).total_seconds()
    offset = span * (index + 0.5) / count
    return start + timedelta(seconds=offset)


def _iso(value: datetime) -> str:
    return value.strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def conversation_text(theme: str, cause: str, region: str) -> str:
    theme_label = THEME_LABELS[theme].lower()
    cause_label = CAUSE_LABELS[cause].lower()
    return (
        f"I've been dealing with {theme_label} in {region}. "
        f"The cause is {cause_label}, and I need the home battery team to tell me what happens next."
    )


def severity_for(count: int) -> str:
    if count >= 100:
        return "high"
    if count >= 50:
        return "medium"
    return "low"


def _causes_for(theme: str, total: int, causes: tuple[tuple[str, int], ...]) -> list[str]:
    if sum(count for _, count in causes) != total:
        raise RuntimeError(f"cause counts for {theme} do not add up")
    ordered: list[str] = []
    for cause, count in causes:
        ordered.extend([cause] * count)
    return ordered


def _build_conversations() -> list[dict]:
    conversations: list[dict] = []
    number = 1
    for theme, total, current_n, causes in THEME_PLAN:
        cause_list = _causes_for(theme, total, causes)
        previous_n = total - current_n
        for index, cause in enumerate(cause_list):
            if index < current_n:
                created = _stamp(CURRENT_START, AS_OF, index, current_n)
            else:
                created = _stamp(PREVIOUS_START, CURRENT_START, index - current_n, previous_n)
            region = REGIONS[(number - 1) % len(REGIONS)]
            ticket_id = f"ticket_{number:03d}"
            conversations.append(
                {
                    "id": ticket_id,
                    "complaint_id": f"cmp_{number:03d}",
                    "created_at": _iso(created),
                    "customer_region": region,
                    "channel": CHANNELS[(number - 1) % len(CHANNELS)],
                    "theme": theme,
                    "cause": cause,
                    "text": conversation_text(theme, cause, region),
                    "sentiment": None,
                    "value_theme": None,
                    "technical_issue": None,
                    "theme_index": index,
                    "current_n": current_n,
                }
            )
            number += 1
    if number != 501:
        raise RuntimeError(f"expected 500 conversations, built {number - 1}")
    return conversations


def _assign_sentiment(conversations: list[dict]) -> None:
    import random

    sentiments = (["positive"] * 305) + (["neutral"] * 120) + (["negative"] * 75)
    random.Random(SEED).shuffle(sentiments)
    quotas = [[name, count] for name, count in VALUE_QUOTAS]
    cursor = 0
    for conv, sentiment in zip(conversations, sentiments, strict=True):
        conv["sentiment"] = sentiment
        if sentiment != "positive":
            continue
        while quotas[cursor][1] == 0:
            cursor += 1
        theme = quotas[cursor][0]
        quotas[cursor][1] -= 1
        conv["value_theme"] = theme
        conv["text"] = f"{conv['text']} {VALUE_SENTENCES[theme]}"


def _assign_technical(conversations: list[dict]) -> None:
    by_theme: dict[str, list[dict]] = {}
    for conv in conversations:
        by_theme.setdefault(conv["theme"], []).append(conv)

    def take(theme: str, technical: str, current_take: int, previous_take: int) -> None:
        rows = by_theme[theme]
        current = [row for row in rows if row["theme_index"] < row["current_n"]]
        previous = [row for row in rows if row["theme_index"] >= row["current_n"]]
        chosen = [
            row
            for row in current
            if row["technical_issue"] is None
        ][:current_take]
        chosen += [
            row
            for row in previous
            if row["technical_issue"] is None
        ][:previous_take]
        if len(chosen) != current_take + previous_take:
            raise RuntimeError(f"could not tag {technical}")
        for row in chosen:
            row["technical_issue"] = technical

    take("battery_performance", "battery_telemetry", 19, 12)
    take("battery_performance", "firmware", 10, 7)
    take("app_problems", "mobile_app", 13, 9)


def _operations_tickets() -> list[dict]:
    states = (["at_risk"] * 47) + (["delayed"] * 31) + (["open_incident"] * 12) + (["scheduled"] * 10)
    blockers = (["permitting"] * 42) + (["installer_capacity"] * 33) + (["customer_scheduling"] * 25)
    themes = (
        (["installation_delays"] * 60)
        + (["battery_performance"] * 15)
        + (["billing_confusion"] * 10)
        + (["app_problems"] * 10)
        + (["communication_problems"] * 5)
    )
    tickets = []
    for index in range(100):
        theme = themes[index]
        blocker = blockers[index]
        cause = BLOCKER_CAUSE[blocker] if theme == "installation_delays" else "other"
        if index < 50:
            created = _stamp(CURRENT_START, AS_OF, index, 50)
        else:
            created = _stamp(PREVIOUS_START, CURRENT_START, index - 50, 50)
        region = REGIONS[index % len(REGIONS)]
        state = states[index]
        text = (
            f"Operations note for {region}. Installation state is {state.replace('_', ' ')}. "
            f"The blocker is {BLOCKER_LABELS[blocker].lower()}. "
            f"This ticket follows {THEME_LABELS[theme].lower()} and the linked customer cause is {CAUSE_LABELS[cause].lower()}."
        )
        tickets.append(
            {
                "id": f"ops_{index + 1:03d}",
                "created_at": _iso(created),
                "region": region,
                "channel": "operations",
                "theme": theme,
                "cause": cause,
                "installation_state": state,
                "blocker": blocker,
                "text": text,
            }
        )
    return tickets


def _chunk(ids: list[str], sizes: list[int]) -> list[list[str]]:
    chunks = []
    cursor = 0
    for size in sizes:
        chunks.append(ids[cursor : cursor + size])
        cursor += size
    if cursor != len(ids):
        raise RuntimeError("incident link sizes do not cover the complaints")
    return chunks


def _incidents(conversations: list[dict]) -> list[dict]:
    def ids_for(technical: str) -> list[str]:
        return [row["complaint_id"] for row in conversations if row["technical_issue"] == technical]

    groups = {
        "battery_telemetry": list(
            zip(
                ["INC-421", "INC-401", "INC-402", "INC-403", "INC-404", "INC-405"],
                _chunk(ids_for("battery_telemetry"), [10, 5, 5, 5, 5, 1]),
                strict=True,
            )
        ),
        "mobile_app": list(
            zip(
                ["INC-427", "INC-411", "INC-412", "INC-413", "INC-414"],
                _chunk(ids_for("mobile_app"), [8, 4, 4, 4, 2]),
                strict=True,
            )
        ),
        "firmware": list(
            zip(
                ["INC-433", "INC-416", "INC-417", "INC-418"],
                _chunk(ids_for("firmware"), [6, 4, 4, 3]),
                strict=True,
            )
        ),
    }
    theme_for = {
        "battery_telemetry": "battery_performance",
        "mobile_app": "app_problems",
        "firmware": "battery_performance",
    }
    incidents = []
    serial = 0
    for technical, pairs in groups.items():
        for inc_id, complaint_ids in pairs:
            label = TECHNICAL_LABELS[technical]
            incidents.append(
                {
                    "id": inc_id,
                    "created_at": _iso(CURRENT_START + timedelta(days=1, minutes=serial)),
                    "technical_issue": technical,
                    "theme": theme_for[technical],
                    "cause": "other",
                    "summary": (
                        f"{inc_id} is an engineering incident for {label} and it is linked "
                        "to member complaints about that technical issue."
                    ),
                    "complaint_ids": complaint_ids,
                }
            )
            serial += 1
    install_ids = [row["complaint_id"] for row in conversations if row["theme"] == "installation_delays"]
    for offset in range(35):
        inc_id = f"INC-{440 + offset}"
        incidents.append(
            {
                "id": inc_id,
                "created_at": _iso(CURRENT_START + timedelta(days=2, minutes=offset)),
                "technical_issue": None,
                "theme": "installation_delays",
                "cause": "permitting_delays",
                "summary": (
                    f"{inc_id} is an engineering incident related to installation delays and it is linked "
                    "to member complaints about that theme."
                ),
                "complaint_ids": install_ids[offset * 2 : offset * 2 + 2],
            }
        )
    return incidents


def _internal_documents() -> list[dict]:
    docs = []
    serial = 1
    for (theme, cause), action in ACTIONS.items():
        title = f"{THEME_LABELS[theme]} — {CAUSE_LABELS[cause]}"
        docs.append(
            {
                "id": f"doc_{serial:02d}",
                "source_type": "internal",
                "title": title,
                "body": f"{title}. {action}",
                "region": None,
                "channel": "internal",
                "theme": theme,
                "cause": cause,
                "recommended_action": action,
                "issue_slug": theme,
                "created_at": "2026-09-01T15:00:00Z",
            }
        )
        serial += 1
    for extra in EXTRA_DOCS:
        action = extra["action"]
        docs.append(
            {
                "id": f"doc_{serial:02d}",
                "source_type": "internal",
                "title": extra["title"],
                "body": f"{extra['title']}. {action}",
                "region": None,
                "channel": "internal",
                "theme": extra["theme"],
                "cause": extra["cause"],
                "recommended_action": action,
                "issue_slug": extra.get("issue_slug"),
                "created_at": "2026-09-01T15:00:00Z",
            }
        )
        serial += 1
    if len(docs) != 30:
        raise RuntimeError(f"expected 30 internal documents, built {len(docs)}")
    return docs


def _issue(slug: str, kind: str, complaints: list[dict]) -> dict:
    stamps = [parse_time(row["created_at"]) for row in complaints]
    current = sum(1 for stamp in stamps if period_of(stamp) == "current")
    previous = sum(1 for stamp in stamps if period_of(stamp) == "previous")
    return {
        "id": f"iss_{slug}",
        "slug": slug,
        "name": THEME_LABELS.get(slug) or TECHNICAL_LABELS[slug],
        "description": ISSUE_DESCRIPTIONS[slug],
        "complaint_count": len(complaints),
        "trend": trend_percent(current, previous),
        "severity": severity_for(len(complaints)),
        "first_seen": _iso(min(stamps)),
        "last_seen": _iso(max(stamps)),
        "kind": kind,
        "complaint_ids": [row["id"] for row in complaints],
    }


def generate_corpus() -> dict:
    conversations = _build_conversations()
    _assign_sentiment(conversations)
    _assign_technical(conversations)
    tickets = _operations_tickets()
    incidents = _incidents(conversations)
    internal = _internal_documents()

    complaints = [
        {
            "id": row["complaint_id"],
            "document_id": row["id"],
            "text": row["text"],
            "theme": row["theme"],
            "cause": row["cause"],
            "region": row["customer_region"],
            "sentiment": row["sentiment"],
            "value_theme": row["value_theme"],
            "technical_issue": row["technical_issue"],
            "created_at": row["created_at"],
        }
        for row in conversations
    ]
    documents = []
    for row in conversations:
        documents.append(
            {
                "id": row["id"],
                "source_type": "conversation",
                "title": f"Conversation {row['id']}",
                "body": row["text"],
                "region": row["customer_region"],
                "channel": row["channel"],
                "theme": row["theme"],
                "cause": row["cause"],
                "recommended_action": None,
                "installation_state": None,
                "blocker": None,
                "sentiment": row["sentiment"],
                "value_theme": row["value_theme"],
                "technical_issue": row["technical_issue"],
                "created_at": row["created_at"],
            }
        )
    for row in tickets:
        documents.append(
            {
                "id": row["id"],
                "source_type": "operations_ticket",
                "title": f"Operations {row['id']}",
                "body": row["text"],
                "region": row["region"],
                "channel": row["channel"],
                "theme": row["theme"],
                "cause": row["cause"],
                "recommended_action": None,
                "installation_state": row["installation_state"],
                "blocker": row["blocker"],
                "sentiment": None,
                "value_theme": None,
                "technical_issue": None,
                "created_at": row["created_at"],
            }
        )
    for row in internal:
        documents.append(
            {
                "id": row["id"],
                "source_type": "internal",
                "title": row["title"],
                "body": row["body"],
                "region": row["region"],
                "channel": row["channel"],
                "theme": row["theme"],
                "cause": row["cause"],
                "recommended_action": row["recommended_action"],
                "installation_state": None,
                "blocker": None,
                "sentiment": None,
                "value_theme": None,
                "technical_issue": None,
                "created_at": row["created_at"],
            }
        )
    documents.extend(company_documents())
    documents.extend(inventory_documents())
    documents.extend(outage_documents())

    issues = []
    issue_complaints = []
    for theme, _, _, _ in THEME_PLAN:
        rows = [item for item in complaints if item["theme"] == theme]
        issue = _issue(theme, "theme", rows)
        issues.append(issue)
        issue_complaints.extend(
            {"issue_id": issue["id"], "complaint_id": cid} for cid in issue["complaint_ids"]
        )
    for slug in ("battery_telemetry", "mobile_app", "firmware"):
        rows = [item for item in complaints if item["technical_issue"] == slug]
        issue = _issue(slug, "technical", rows)
        issues.append(issue)
        issue_complaints.extend(
            {"issue_id": issue["id"], "complaint_id": cid} for cid in issue["complaint_ids"]
        )

    incident_complaints = []
    for incident in incidents:
        incident_complaints.extend(
            {"incident_id": incident["id"], "complaint_id": cid} for cid in incident["complaint_ids"]
        )

    knowledge_items = []
    for row in internal:
        issue_id = f"iss_{row['issue_slug']}" if row.get("issue_slug") else None
        knowledge_items.append(
            {
                "id": f"ki_{row['id']}",
                "document_id": row["id"],
                "issue_id": issue_id,
                "title": row["title"],
                "body": row["recommended_action"],
                "kind": "recommended_action" if row["theme"] != "company" else "company_brief",
            }
        )
    knowledge_items.extend(company_knowledge_items())
    knowledge_items.extend(inventory_knowledge_items())
    knowledge_items.extend(outage_knowledge_items())

    corpus = {
        "conversations": [
            {
                "id": row["id"],
                "created_at": row["created_at"],
                "customer_region": row["customer_region"],
                "channel": row["channel"],
                "theme": row["theme"],
                "cause": row["cause"],
                "text": row["text"],
                "sentiment": row["sentiment"],
                "value_theme": row["value_theme"],
                "technical_issue": row["technical_issue"],
            }
            for row in conversations
        ],
        "operations_tickets": tickets,
        "incidents": incidents,
        "documents": [row for row in documents if row["source_type"] == "internal"],
        "complaints": complaints,
        "issues": issues,
        "issue_complaints": issue_complaints,
        "incident_complaints": incident_complaints,
        "knowledge_items": knowledge_items,
        "all_documents": documents,
    }
    validate_corpus(corpus)
    return corpus


def validate_corpus(corpus: dict) -> None:
    conversations = corpus["conversations"]
    if len(conversations) != 500:
        raise AssertionError(len(conversations))
    if len(corpus["operations_tickets"]) != 100:
        raise AssertionError("ops")
    if len(corpus["incidents"]) != 50:
        raise AssertionError("incidents")
    if len(corpus["documents"]) != 30:
        raise AssertionError("docs")
    if len(corpus["complaints"]) != 500:
        raise AssertionError("complaints")
    doc_ids = {row["id"] for row in corpus["all_documents"]}
    for complaint in corpus["complaints"]:
        if not complaint["document_id"] or complaint["document_id"] not in doc_ids:
            raise AssertionError(f"complaint {complaint['id']} missing document")
        source = next(row for row in corpus["all_documents"] if row["id"] == complaint["document_id"])
        if complaint["text"] not in source["body"]:
            raise AssertionError("complaint text is not in its document")

    themes = Counter(row["theme"] for row in conversations)
    expected_themes = {theme: total for theme, total, _, _ in THEME_PLAN}
    if dict(themes) != expected_themes:
        raise AssertionError(themes)

    install = [row for row in conversations if row["theme"] == "installation_delays"]
    causes = Counter(row["cause"] for row in install)
    if dict(causes) != {
        "permitting_delays": 70,
        "installer_scheduling": 52,
        "customer_communication": 35,
        "other": 18,
    }:
        raise AssertionError(causes)

    sentiment = Counter(row["sentiment"] for row in conversations)
    if dict(sentiment) != {"positive": 305, "neutral": 120, "negative": 75}:
        raise AssertionError(sentiment)
    values = Counter(row["value_theme"] for row in conversations if row["sentiment"] == "positive")
    if dict(values) != {
        "energy_independence": 122,
        "installation_experience": 102,
        "battery_reliability": 81,
    }:
        raise AssertionError(values)
    for row in conversations:
        if row["sentiment"] == "positive":
            if VALUE_SENTENCES[row["value_theme"]] not in row["text"]:
                raise AssertionError("value sentence missing")
        elif row["value_theme"] is not None:
            raise AssertionError("value theme on non-positive conversation")

    states = Counter(row["installation_state"] for row in corpus["operations_tickets"])
    if states["at_risk"] != 47 or states["open_incident"] != 12 or states["delayed"] != 31:
        raise AssertionError(states)
    blockers = Counter(row["blocker"] for row in corpus["operations_tickets"])
    ranked = [name for name, _ in blockers.most_common()]
    if ranked != ["permitting", "installer_capacity", "customer_scheduling"]:
        raise AssertionError(ranked)

    technical = Counter(row["technical_issue"] for row in conversations if row["technical_issue"])
    if dict(technical) != {"battery_telemetry": 31, "mobile_app": 22, "firmware": 17}:
        raise AssertionError(technical)

    link_counts = Counter()
    for incident in corpus["incidents"]:
        link_counts[incident["id"]] = len(incident["complaint_ids"])
    top = [item for item, _ in link_counts.most_common(3)]
    if top != ["INC-421", "INC-427", "INC-433"]:
        raise AssertionError(top)
    if link_counts["INC-421"] <= link_counts["INC-427"] or link_counts["INC-427"] <= link_counts["INC-433"]:
        raise AssertionError(link_counts.most_common(3))
    third = link_counts["INC-433"]
    for inc_id, count in link_counts.items():
        if inc_id not in top and count >= third:
            raise AssertionError((inc_id, count))

    joined = Counter(row["issue_id"] for row in corpus["issue_complaints"])
    for issue in corpus["issues"]:
        if issue["complaint_count"] != joined[issue["id"]]:
            raise AssertionError(issue["slug"])
        if issue["complaint_count"] != len(issue["complaint_ids"]):
            raise AssertionError(issue["slug"])
    install_issue = next(issue for issue in corpus["issues"] if issue["slug"] == "installation_delays")
    if install_issue["trend"] != 50.0 or install_issue["complaint_count"] != 175:
        raise AssertionError(install_issue)
