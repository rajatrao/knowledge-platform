"""Temporal report workflows. This module does not import the deep agent."""

from __future__ import annotations

from datetime import timedelta

from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from kp.reports.activities import (
        blocker_ranking,
        installation_risk_report,
        issue_trend_report,
        related_incident_report,
        sentiment_breakdown,
        severity_digest,
        technical_issue_counts,
        value_theme_counts,
    )

_TIMEOUT = timedelta(seconds=30)


@workflow.defn(name="issue_trend_report")
class IssueTrendReport:
    @workflow.run
    async def run(self, params: dict | None = None) -> dict:
        return await workflow.execute_activity(
            issue_trend_report,
            params or {},
            start_to_close_timeout=_TIMEOUT,
        )


@workflow.defn(name="severity_digest")
class SeverityDigest:
    @workflow.run
    async def run(self, params: dict | None = None) -> dict:
        return await workflow.execute_activity(
            severity_digest,
            params or {},
            start_to_close_timeout=_TIMEOUT,
        )


@workflow.defn(name="blocker_ranking")
class BlockerRanking:
    @workflow.run
    async def run(self, params: dict | None = None) -> dict:
        return await workflow.execute_activity(
            blocker_ranking,
            params or {},
            start_to_close_timeout=_TIMEOUT,
        )


@workflow.defn(name="installation_risk_report")
class InstallationRiskReport:
    @workflow.run
    async def run(self, params: dict | None = None) -> dict:
        return await workflow.execute_activity(
            installation_risk_report,
            params or {},
            start_to_close_timeout=_TIMEOUT,
        )


@workflow.defn(name="technical_issue_counts")
class TechnicalIssueCounts:
    @workflow.run
    async def run(self, params: dict | None = None) -> dict:
        return await workflow.execute_activity(
            technical_issue_counts,
            params or {},
            start_to_close_timeout=_TIMEOUT,
        )


@workflow.defn(name="related_incident_report")
class RelatedIncidentReport:
    @workflow.run
    async def run(self, params: dict | None = None) -> dict:
        return await workflow.execute_activity(
            related_incident_report,
            params or {},
            start_to_close_timeout=_TIMEOUT,
        )


@workflow.defn(name="sentiment_breakdown")
class SentimentBreakdown:
    @workflow.run
    async def run(self, params: dict | None = None) -> dict:
        return await workflow.execute_activity(
            sentiment_breakdown,
            params or {},
            start_to_close_timeout=_TIMEOUT,
        )


@workflow.defn(name="value_theme_counts")
class ValueThemeCounts:
    @workflow.run
    async def run(self, params: dict | None = None) -> dict:
        return await workflow.execute_activity(
            value_theme_counts,
            params or {},
            start_to_close_timeout=_TIMEOUT,
        )


REPORT_WORKFLOWS = [
    IssueTrendReport,
    SeverityDigest,
    BlockerRanking,
    InstallationRiskReport,
    TechnicalIssueCounts,
    RelatedIncidentReport,
    SentimentBreakdown,
    ValueThemeCounts,
]

WORKFLOW_BY_NAME = {
    cls.__temporal_workflow_definition.name: cls for cls in REPORT_WORKFLOWS
}
