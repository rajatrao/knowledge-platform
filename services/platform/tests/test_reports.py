import asyncio
import inspect
from concurrent.futures import ThreadPoolExecutor

from kp.db import SessionLocal
from kp.labels import PERSONA_SKILLS, SAMPLE_QUESTIONS
from kp.models import Complaint, Document, Incident, IncidentComplaint, Issue, IssueComplaint
from kp.onboarding.worker import ACTIVITIES, WORKFLOWS
from kp.reports.intents import PERSONA_WORKFLOWS, REPORT_WORKFLOW_NAMES, allowed_workflow
from tests.conftest import login

ASKS = {
    "ceo": (
        ("Run the issue trend report", "issue_trend_report"),
        ("Give me the severity digest", "severity_digest"),
    ),
    "operations_manager": (
        ("Show the blocker ranking", "blocker_ranking"),
        ("Run the installation risk report", "installation_risk_report"),
    ),
    "engineer": (
        ("Show technical issue counts", "technical_issue_counts"),
        ("Run the related incident report", "related_incident_report"),
    ),
    "marketing": (
        ("Show the sentiment breakdown", "sentiment_breakdown"),
        ("Run value theme counts", "value_theme_counts"),
    ),
}

MISMATCHED = (
    ("ceo", "Run the related incident report", "related_incident_report"),
    ("ceo", "Show technical issue counts", "technical_issue_counts"),
    ("operations_manager", "Give me the severity digest", "severity_digest"),
    ("engineer", "Run the issue trend report", "issue_trend_report"),
    ("marketing", "Show the blocker ranking", "blocker_ranking"),
)


def _ask(client, session_id, query):
    response = client.post(
        f"/v1/sessions/{session_id}/ask",
        json={"query": query, "channel": "web", "router": "llm"},
    )
    assert response.status_code == 200, response.text
    return response.json()


def _block_agent(monkeypatch):
    called = []

    async def synthesize(*_args, **_kwargs):
        called.append("synthesize")
        raise AssertionError("knowledge path")

    def boom(*_args, **_kwargs):
        called.append("agent")
        raise AssertionError("deep agent")

    monkeypatch.setattr("kp.knowledge.ask.synthesize", synthesize)
    monkeypatch.setattr("kp.agent.factory.create_session_agent", boom)
    monkeypatch.setattr("kp.agent.factory.create_deep_agent", boom)
    monkeypatch.setattr("kp.agent.skills.select_skills", boom)
    monkeypatch.setattr("kp.agent.sandbox.K8sSandbox.provision", boom)
    return called


def test_each_persona_resolves_to_its_workflows(client, monkeypatch):
    called = _block_agent(monkeypatch)
    for persona, asks in ASKS.items():
        session_id = login(client, persona)["session_id"]
        for query, workflow in asks:
            body = _ask(client, session_id, query)
            assert body["route"] == {"kind": "workflow", "name": workflow}
            assert body["citations"] == []
            assert body["artifacts"] == []
            assert body["report"]["workflow"] == workflow
    assert called == []


def test_a_mismatched_persona_does_not_start_the_workflow(client, monkeypatch, inject_skill_selector):
    called = []

    def boom(*_args, **_kwargs):
        called.append("agent")
        raise AssertionError("deep agent")

    monkeypatch.setattr("kp.agent.factory.create_session_agent", boom)
    monkeypatch.setattr("kp.agent.factory.create_deep_agent", boom)
    for persona, query, foreign in MISMATCHED:
        session_id = login(client, persona)["session_id"]
        body = _ask(client, session_id, query)
        assert body["route"] == {"kind": "skill", "name": PERSONA_SKILLS[persona]}
        assert body["route"]["name"] != foreign
        assert body["report"] is None
    ceo = login(client, "ceo")["session_id"]
    question = _ask(client, ceo, "Which customer complaints appear related to technical incidents?")
    assert question["route"]["name"] == "customer-complaints"
    assert question["route"]["name"] != "related_incident_report"
    assert called == []


def test_sample_questions_stay_on_the_skill_path():
    for persona, question in SAMPLE_QUESTIONS.items():
        assert allowed_workflow(persona, question) is None
    assert allowed_workflow("operations_manager", "Chart the operational blockers") is None
    assert allowed_workflow("ceo", "Run the related incident report") is None
    assert allowed_workflow("engineer", "Run the related incident report") == "related_incident_report"


def test_report_without_extra_fields_reads_the_full_corpus(client, monkeypatch):
    called = _block_agent(monkeypatch)
    session_id = login(client, "ceo")["session_id"]
    body = _ask(client, session_id, "issue_trend_report")
    db = SessionLocal()
    try:
        assert len(body["report"]["issues"]) == db.query(Issue).count()
        assert body["report"]["issues"]
    finally:
        db.close()
    assert called == []


def test_report_payloads_match_postgres(client, monkeypatch):
    _block_agent(monkeypatch)
    db = SessionLocal()
    try:
        ceo = login(client, "ceo")["session_id"]
        trend = _ask(client, ceo, "Run the issue trend report")["report"]
        counts = [row["complaint_count"] for row in trend["issues"]]
        assert counts == sorted(counts, reverse=True)
        assert trend["issues"][0]["slug"] == "installation_delays"
        assert trend["issues"][0]["complaint_count"] == 175
        assert trend["issues"][0]["trend"] == 50.0
        assert trend["issues"][0]["severity"] == "high"
        for row in trend["issues"]:
            issue = db.get(Issue, row["id"])
            assert row["complaint_count"] == issue.complaint_count
            assert row["trend"] == issue.trend
            assert row["severity"] == issue.severity
            assert row["first_seen"]
            assert row["last_seen"]

        digest = _ask(client, ceo, "Give me the severity digest")["report"]
        seen = []
        for group in digest["severities"]:
            for issue in group["issues"]:
                seen.append(issue["id"])
                joined = [
                    row[0]
                    for row in db.query(IssueComplaint.complaint_id)
                    .filter(IssueComplaint.issue_id == issue["id"])
                    .order_by(IssueComplaint.complaint_id.asc())
                    .all()
                ]
                assert issue["complaint_ids"] == joined
                assert issue["complaint_count"] == len(joined)
                assert db.get(Issue, issue["id"]).severity == group["severity"]
        assert seen
        assert [group["severity"] for group in digest["severities"]] == ["high", "medium", "low"]

        ops = login(client, "operations_manager")["session_id"]
        blockers = _ask(client, ops, "Show the blocker ranking")["report"]["blockers"]
        assert [row["key"] for row in blockers] == [
            "permitting",
            "installer_capacity",
            "customer_scheduling",
        ]
        for row in blockers:
            tickets = [
                item[0]
                for item in db.query(Document.id)
                .filter(Document.source_type == "operations_ticket", Document.blocker == row["key"])
                .order_by(Document.id.asc())
                .all()
            ]
            assert row["ticket_ids"] == tickets
            assert row["count"] == len(tickets)
            assert row["complaint_ids"]
            for complaint_id in row["complaint_ids"]:
                assert db.get(Complaint, complaint_id) is not None

        installations = _ask(client, ops, "Run the installation risk report")["report"]["installations"]
        assert [row["key"] for row in installations] == ["at_risk", "open_incident", "delayed"]
        assert [row["count"] for row in installations] == [47, 12, 31]
        for row in installations:
            ids = [
                item[0]
                for item in db.query(Document.id)
                .filter(
                    Document.source_type == "operations_ticket",
                    Document.installation_state == row["key"],
                )
                .order_by(Document.id.asc())
                .all()
            ]
            assert row["source_ids"] == ids
            assert row["count"] == len(ids)

        engineer = login(client, "engineer")["session_id"]
        technical = _ask(client, engineer, "Show technical issue counts")["report"]["technical_issues"]
        assert [row["key"] for row in technical] == ["battery_telemetry", "mobile_app", "firmware"]
        assert [row["complaint_count"] for row in technical] == [31, 22, 17]
        for row in technical:
            assert row["complaint_count"] == len(row["complaint_ids"])
            assert row["incident_ids"]
            for incident_id in row["incident_ids"]:
                incident = db.get(Incident, incident_id)
                assert incident.technical_issue == row["key"]

        related = _ask(client, engineer, "Run the related incident report")["report"]["incidents"]
        assert [row["id"] for row in related[:3]] == ["INC-421", "INC-427", "INC-433"]
        linked_counts = [row["linked_complaints"] for row in related]
        assert linked_counts == sorted(linked_counts, reverse=True)
        for row in related:
            ids = [
                item[0]
                for item in db.query(IncidentComplaint.complaint_id)
                .filter(IncidentComplaint.incident_id == row["id"])
                .order_by(IncidentComplaint.complaint_id.asc())
                .all()
            ]
            assert row["complaint_ids"] == ids
            assert row["linked_complaints"] == len(ids)

        marketing = login(client, "marketing")["session_id"]
        sentiment = _ask(client, marketing, "Show the sentiment breakdown")["report"]
        assert sentiment["total"] == db.query(Complaint).count()
        shares = {row["key"]: row for row in sentiment["sentiments"]}
        assert [row["key"] for row in sentiment["sentiments"][:3]] == ["positive", "neutral", "negative"]
        assert [shares[key]["count"] for key in ("positive", "neutral", "negative")] == [305, 120, 75]
        assert [round(shares[key]["share"], 2) for key in ("positive", "neutral", "negative")] == [
            0.61,
            0.24,
            0.15,
        ]
        for row in sentiment["sentiments"]:
            assert row["count"] == len(row["complaint_ids"]) == len(row["document_ids"])
            for complaint_id, document_id in zip(row["complaint_ids"], row["document_ids"], strict=True):
                complaint = db.get(Complaint, complaint_id)
                document = db.get(Document, document_id)
                assert complaint.sentiment == row["key"]
                assert complaint.document_id == document_id
                assert document.sentiment == row["key"]

        themes = _ask(client, marketing, "Run value theme counts")["report"]["value_themes"]
        assert [row["key"] for row in themes] == [
            "energy_independence",
            "installation_experience",
            "battery_reliability",
        ]
        assert [row["count"] for row in themes] == [122, 102, 81]
        for row in themes:
            assert row["count"] == len(row["document_ids"])
            for document_id in row["document_ids"]:
                document = db.get(Document, document_id)
                assert document.value_theme == row["key"]
                assert document.body
    finally:
        db.close()


def test_onboarding_still_works(client, monkeypatch):
    called = _block_agent(monkeypatch)
    session_id = login(client, "marketing")["session_id"]
    body = _ask(client, session_id, "Please onboard a new employee")
    assert body["route"] == {"kind": "workflow", "name": "onboard_employee"}
    assert body["report"] is None
    assert body["artifacts"] == []
    assert "name" in body["answer"] and "email" in body["answer"]
    assert called == []


def test_report_modules_do_not_call_the_agent():
    import kp.reports.activities as activities
    import kp.reports.queries as queries
    import kp.reports.service as service
    import kp.reports.workflows as workflows

    for module in (activities, queries, service, workflows):
        source = inspect.getsource(module)
        assert "create_deep_agent" not in source
        assert "create_session_agent" not in source
        assert "select_skills" not in source
        assert "resolve_skill_stack" not in source
        assert "K8sSandbox" not in source
    workflow_source = inspect.getsource(workflows)
    assert "execute_activity" in workflow_source
    for token in ("175", "INC-421", "305", "47", "122"):
        assert token not in inspect.getsource(queries)


def test_worker_registers_onboarding_and_persona_reports():
    names = [item.__temporal_workflow_definition.name for item in WORKFLOWS]
    assert names[0] == "OnboardEmployee"
    assert names[1] == "OnboardCustomer"
    assert names[2] == "OnboardSpecialist"
    assert set(names[3:]) == set(REPORT_WORKFLOW_NAMES)
    assert len(ACTIVITIES) == 4 + len(REPORT_WORKFLOW_NAMES)
    for persona, workflows in PERSONA_WORKFLOWS.items():
        assert len(workflows) == 2
        assert set(workflows) <= REPORT_WORKFLOW_NAMES
        del persona


def test_temporal_workflows_run_in_process(database):
    asyncio.run(_run_workflows_in_process())


async def _run_workflows_in_process():
    from temporalio.testing import WorkflowEnvironment
    from temporalio.worker import Worker

    from kp.onboarding.fields import TASK_QUEUE
    from kp.reports.queries import READERS
    from kp.reports.workflows import WORKFLOW_BY_NAME

    db = SessionLocal()
    try:
        expected = {name: reader(db, {}) for name, reader in READERS.items()}
    finally:
        db.close()
    async with await WorkflowEnvironment.start_time_skipping() as env:
        async with Worker(
            env.client,
            task_queue=TASK_QUEUE,
            workflows=list(WORKFLOWS),
            activities=list(ACTIVITIES),
            activity_executor=ThreadPoolExecutor(max_workers=8),
        ):
            for name, payload in expected.items():
                result = await env.client.execute_workflow(
                    WORKFLOW_BY_NAME[name].run,
                    {},
                    id=f"report-{name}",
                    task_queue=TASK_QUEUE,
                )
                assert result == payload
