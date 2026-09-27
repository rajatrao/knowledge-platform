from kp.db import SessionLocal
from kp.models import Complaint, Document, Issue, IssueComplaint
from tests.conftest import login


def _ask(client, session_id, query):
    response = client.post(
        f"/v1/sessions/{session_id}/ask",
        json={"query": query, "channel": "web", "router": "llm"},
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_headline_counts_come_from_postgres(client, inject_skill_selector):
    ops = login(client, "operations_manager")
    dashboard = client.get("/v1/dashboards/operations_manager")
    assert dashboard.status_code == 200
    body = dashboard.json()
    metrics = {row["key"]: row["value"] for row in body["metrics"]}
    assert metrics == {"at_risk": 47, "open_incident": 12, "delayed": 31}
    assert [row["key"] for row in body["blockers"]] == [
        "permitting",
        "installer_capacity",
        "customer_scheduling",
    ]
    assert all(row["count"] == len(row["records"]) for row in body["blockers"])
    assert body["sample_question"] == "Which operational problems are driving customer complaints?"

    denied = client.get("/v1/dashboards/engineer")
    assert denied.status_code == 403

    from fastapi.testclient import TestClient

    from kp.api import create_app

    with TestClient(create_app()) as engineer:
        login(engineer, "engineer")
        engineering = engineer.get("/v1/dashboards/engineer").json()
    counts = {row["key"]: row["complaint_count"] for row in engineering["technical_issues"]}
    assert counts == {"battery_telemetry": 31, "mobile_app": 22, "firmware": 17}
    assert [row["id"] for row in engineering["related_incidents"]] == ["INC-421", "INC-427", "INC-433"]
    assert all(row["complaint_count"] == len(row["records"]) for row in engineering["technical_issues"])

    with TestClient(create_app()) as marketing:
        login(marketing, "marketing")
        market = marketing.get("/v1/dashboards/marketing").json()
    sentiment = {row["key"]: row["count"] for row in market["sentiment"]}
    assert sentiment == {"positive": 305, "neutral": 120, "negative": 75}
    assert [round(row["share"], 2) for row in market["sentiment"]] == [0.61, 0.24, 0.15]
    labels = [row["label"] for row in market["value_themes"]]
    assert labels[:3] == ["Energy independence", "Installation experience", "Battery reliability"]

    with TestClient(create_app()) as ceo:
        login(ceo, "ceo")
        assert ceo.get("/v1/dashboards/operations_manager").status_code == 403
        themes = ceo.get("/v1/themes").json()["themes"]
        page = ceo.get("/v1/investigations/installation_delays").json()
    assert themes[0]["slug"] == "installation_delays"
    assert themes[0]["complaint_count"] == 175
    assert page["current_period_count"] == 105
    assert page["previous_period_count"] == 70
    assert page["trend_percent"] == 50.0
    assert page["complaint_count"] == 175
    assert abs(sum(item["share"] for item in page["causes"]) - 1) < 1e-9
    assert [item["cause"] for item in page["causes"]] == [
        "permitting_delays",
        "installer_scheduling",
        "customer_communication",
        "other",
    ]
    assert page["evidence_counts"]["support_conversations"] == len(page["support_conversations"])
    assert page["evidence_counts"]["operations_tickets"] == len(page["operations_tickets"])
    assert page["evidence_counts"]["related_incidents"] == len(page["related_incidents"])
    assert len(page["quotes"]) >= 2

    db = SessionLocal()
    try:
        assert db.query(Complaint).filter(Complaint.document_id.is_(None)).count() == 0
        issue = db.query(Issue).filter(Issue.slug == "installation_delays").one()
        assert db.query(IssueComplaint).filter(IssueComplaint.issue_id == issue.id).count() == issue.complaint_count
        for quote in page["quotes"]:
            document = db.get(Document, quote["document_id"])
            assert quote["quote"] == document.body
        for action in page["recommended_actions"]:
            document = db.get(Document, action["document_id"])
            assert action["text"] == document.recommended_action
            assert action["text"] in document.body
    finally:
        db.close()

    answer = _ask(client, ops["session_id"], body["sample_question"])
    assert answer["artifacts"] == []
    assert answer["route"]["name"] == "complaint-drivers"
    assert answer["answer"].find("Permitting") < answer["answer"].find("Installer capacity")
    assert answer["answer"].find("Installer capacity") < answer["answer"].find("Customer scheduling")
    assert answer["telemetry"]["router"] == "llm"
    assert "estimated_cost_usd" in answer["telemetry"]
    _assert_citations(answer["citations"])

    chart = _ask(client, ops["session_id"], "Chart the operational blockers")
    assert chart["artifacts"]
    assert chart["artifacts"][0]["kind"] == "chart"
    assert chart["artifacts"][0]["spec"]["data"]["values"][0]["label"] == "Permitting"
    assert all(citation["kind"] != "knowledge_item" for citation in chart["citations"])
    png = client.get(chart["artifacts"][0]["image_uri"])
    assert png.status_code == 200
    assert png.headers["content-type"].startswith("image/png")


def test_persona_answers_cite_only_retrieved_text(client, inject_skill_selector):
    ceo = login(client, "ceo")
    answer = _ask(client, ceo["session_id"], "What are the top customer complaints and recommended solutions?")
    assert "/investigations/installation_delays" in answer["answer"]
    assert "175" not in answer["answer"]
    assert answer["route"]["name"] == "customer-complaints"
    _assert_citations(answer["citations"])

    from fastapi.testclient import TestClient

    from kp.api import create_app

    with TestClient(create_app()) as engineer:
        session_id = login(engineer, "engineer")["session_id"]
        technical = _ask(
            engineer,
            session_id,
            "Which customer complaints appear related to technical incidents?",
        )
    for incident_id in ("INC-421", "INC-427", "INC-433"):
        assert incident_id in technical["answer"]
    assert "INC-999" not in technical["answer"]
    _assert_citations(technical["citations"])

    with TestClient(create_app()) as marketing:
        session_id = login(marketing, "marketing")["session_id"]
        language = _ask(
            marketing,
            session_id,
            "What language are customers using when they describe why they value Base Power?",
        )
    assert "Energy independence" in language["answer"]
    _assert_citations(language["citations"])
    for citation in language["citations"]:
        assert citation["quote"].startswith("What I value is")


def _assert_citations(citations):
    assert citations
    db = SessionLocal()
    try:
        for citation in citations:
            if citation["kind"] == "complaint":
                row = db.get(Complaint, citation["id"])
                assert row is not None
                assert citation["quote"] in row.text
                assert citation["document_id"] == row.document_id
            elif citation["kind"] == "issue":
                row = db.get(Issue, citation["id"])
                assert citation["quote"] in f"{row.name}\n{row.description}"
            elif citation["kind"] == "incident":
                from kp.models import Incident

                row = db.get(Incident, citation["id"])
                assert citation["quote"] in row.summary
            elif citation["kind"] == "document":
                row = db.get(Document, citation["id"])
                assert citation["quote"] in row.body
            else:
                raise AssertionError(citation["kind"])
    finally:
        db.close()
