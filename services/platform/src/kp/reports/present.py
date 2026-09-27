"""Turn a report payload into the text the chat shows."""

from __future__ import annotations


def format_report(report: dict) -> str:
    name = report["workflow"]
    if name == "issue_trend_report":
        lines = ["Issue trend report, ordered by complaint count:"]
        for issue in report["issues"]:
            lines.append(
                f"- {issue['name']}: {issue['complaint_count']} complaints, "
                f"trend {issue['trend']}, severity {issue['severity']}, "
                f"first seen {issue['first_seen']}, last seen {issue['last_seen']}"
            )
        return "\n".join(lines)
    if name == "severity_digest":
        lines = ["Severity digest:"]
        for group in report["severities"]:
            lines.append(group["severity"])
            for issue in group["issues"]:
                lines.append(
                    f"- {issue['name']}: {issue['complaint_count']} complaints "
                    f"({len(issue['complaint_ids'])} supporting complaint ids)"
                )
        return "\n".join(lines)
    if name == "blocker_ranking":
        lines = ["Blocker ranking, in counted order:"]
        for index, blocker in enumerate(report["blockers"], start=1):
            lines.append(
                f"{index}. {blocker['label']}: {blocker['count']} tickets, "
                f"{len(blocker['complaint_ids'])} supporting complaints"
            )
        return "\n".join(lines)
    if name == "installation_risk_report":
        lines = ["Installation risk report:"]
        for group in report["installations"]:
            lines.append(f"- {group['label']}: {group['count']} ({len(group['source_ids'])} source rows)")
        return "\n".join(lines)
    if name == "technical_issue_counts":
        lines = ["Technical issue counts:"]
        for issue in report["technical_issues"]:
            linked = ", ".join(issue["incident_ids"]) or "none"
            lines.append(f"- {issue['label']}: {issue['complaint_count']} complaints, incidents {linked}")
        return "\n".join(lines)
    if name == "related_incident_report":
        lines = ["Related incidents, ordered by linked complaints:"]
        for incident in report["incidents"]:
            lines.append(f"- {incident['id']}: {incident['linked_complaints']} complaints")
        return "\n".join(lines)
    if name == "sentiment_breakdown":
        lines = ["Sentiment breakdown:"]
        for row in report["sentiments"]:
            lines.append(
                f"- {row['label']}: {row['count']} of {report['total']} "
                f"(share {row['share']}), {len(row['complaint_ids'])} complaint ids, "
                f"{len(row['document_ids'])} document ids"
            )
        return "\n".join(lines)
    if name == "value_theme_counts":
        lines = ["Value theme counts:"]
        for theme in report["value_themes"]:
            lines.append(f"- {theme['label']}: {theme['count']} source documents")
        return "\n".join(lines)
    return name
