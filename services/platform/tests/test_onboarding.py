import inspect

import httpx
import pytest
from sqlalchemy.exc import DBAPIError

from kp.models import CustomerRecord, DirectoryRecord, Issue, IssueComplaint, ManagerNotification
from kp.onboarding.fields import (
    extract_customer_params,
    extract_params,
    is_customer_onboarding_text,
    is_onboarding_text,
    missing_customer_fields,
    missing_fields,
)
from tests.conftest import login


def test_extracts_onboarding_fields():
    params = extract_params("Name is Ada Lovelace, email ada@basepower.com, role engineer")
    assert params == {"name": "Ada Lovelace", "email": "ada@basepower.com", "role": "engineer"}
    assert missing_fields({}) == ["name", "email", "role"]
    assert missing_fields(params) == []
    spoken = extract_params("name is Raj, role is engineer")
    assert spoken["name"] == "Raj"
    assert spoken["role"] == "engineer"
    labeled = extract_params("name: Raj role: engineer")
    assert labeled["name"] == "Raj"
    assert labeled["role"] == "engineer"
    titled = extract_params(
        "employee onboard start for 'su kim', email is su.kim@gmail.com, role is 'engineering manager'"
    )
    assert titled == {"name": "su kim", "email": "su.kim@gmail.com", "role": "engineer"}
    assert missing_fields(titled) == []
    assert extract_params("role is operations manager")["role"] == "operations_manager"


def test_customer_phrases_are_not_employee_onboarding():
    for phrase in ("onboard customer", "customer onboard", "onboard a customer"):
        assert is_customer_onboarding_text(phrase)
        assert not is_onboarding_text(phrase)
    for phrase in ("employee onboard", "onboard employee", "Please onboard a new employee"):
        assert is_onboarding_text(phrase)
        assert not is_customer_onboarding_text(phrase)
    params = extract_customer_params(
        "onboard customer Lone Star Power email is hello@lonestar.com, "
        "city is Austin, system type is whole-home battery"
    )
    assert params == {
        "name": "Lone Star Power",
        "email": "hello@lonestar.com",
        "city": "Austin",
        "system_type": "whole-home battery",
    }
    assert "role" not in params
    assert missing_customer_fields(params) == []
    spoken = extract_customer_params(
        "customer onboard name is Garcia Household, contact email is garcia@example.com"
    )
    assert spoken["name"] == "Garcia Household"
    assert spoken["email"] == "garcia@example.com"
    assert missing_customer_fields(spoken) == ["city", "system type"]
    labeled = extract_customer_params(
        "name: Northwind Home email: hello@northwind.example city: Georgetown system type: backup"
    )
    assert labeled == {
        "name": "Northwind Home",
        "email": "hello@northwind.example",
        "city": "Georgetown",
        "system_type": "backup",
    }
    commercial = extract_customer_params("city is Round Rock, system type is commercial storage")
    assert commercial["city"] == "Round Rock"
    assert commercial["system_type"] == "commercial storage"


def _ask(client, session_id, query):
    response = client.post(
        f"/v1/sessions/{session_id}/ask",
        json={"query": query, "channel": "web", "router": "llm"},
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_customer_onboarding_collects_fields_across_turns(client):
    session_id = login(client, "ceo")["session_id"]
    done = _ask(
        client,
        session_id,
        "onboard customer Lone Star Power email is hello@lonestar.com, "
        "city is Austin, system type is whole-home battery",
    )
    assert done["route"] == {"kind": "workflow", "name": "onboard_customer"}
    assert "Still need" not in done["answer"]
    assert done["answer"] == (
        "Onboarded Lone Star Power (hello@lonestar.com) in Austin with whole-home battery."
    )
    assert done["artifacts"] == []

    from kp.db import SessionLocal

    db = SessionLocal()
    try:
        record = db.query(CustomerRecord).filter(CustomerRecord.email == "hello@lonestar.com").one()
        assert record.name == "Lone Star Power"
        assert record.city == "Austin"
        assert record.system_type == "whole-home battery"
        assert db.query(DirectoryRecord).filter(DirectoryRecord.email == "hello@lonestar.com").one_or_none() is None
    finally:
        db.close()

    partial_id = client.post("/v1/sessions").json()["id"]
    opening = _ask(
        client,
        partial_id,
        "onboard a customer name is Garcia Household, contact email is garcia@example.com",
    )
    assert opening["route"]["name"] == "onboard_customer"
    assert opening["answer"].startswith("Still need city, system type.")
    assert "Still need name" not in opening["answer"]
    assert "role" not in opening["answer"]
    finished = _ask(client, partial_id, "city is Round Rock, system type is commercial storage")
    assert "Still need" not in finished["answer"]
    assert finished["answer"] == (
        "Onboarded Garcia Household (garcia@example.com) in Round Rock with commercial storage."
    )
    assert finished["route"]["name"] == "onboard_customer"

    phrase_id = client.post("/v1/sessions").json()["id"]
    phrase = _ask(client, phrase_id, "customer onboard")
    assert phrase["route"]["name"] == "onboard_customer"
    assert phrase["answer"].startswith("Still need name, email, city, system type.")


def test_employee_onboarding_is_not_a_customer(client):
    session_id = login(client, "ceo")["session_id"]
    done = _ask(
        client,
        session_id,
        "employee onboard start for su kim email is su.kim@gmail.com, role is engineering manager",
    )
    assert done["route"] == {"kind": "workflow", "name": "onboard_employee"}
    assert "Still need" not in done["answer"]
    assert "Onboarded su kim (su.kim@gmail.com) as engineer." in done["answer"]
    assert "system type" not in done["answer"]

    employee_id = client.post("/v1/sessions").json()["id"]
    opening = _ask(client, employee_id, "onboard employee")
    assert opening["route"]["name"] == "onboard_employee"
    assert opening["answer"].startswith("Still need name, email, role.")
    assert "system type" not in opening["answer"]
    supplied = _ask(client, employee_id, "name is Raj, role is engineer")
    assert supplied["route"]["name"] == "onboard_employee"
    assert supplied["answer"].startswith("Still need email")
    assert "system type" not in supplied["answer"]
    finished = _ask(client, employee_id, "name: Raj role: engineer email raj@basepower.com")
    assert finished["route"]["name"] == "onboard_employee"
    assert "Still need" not in finished["answer"]
    assert "Raj" in finished["answer"]
    assert "engineer" in finished["answer"]


def test_message_with_name_and_role_is_not_asked_again(client):
    session_id = login(client, "ceo")["session_id"]
    together = client.post(
        f"/v1/sessions/{session_id}/ask",
        json={
            "query": (
                "employee onboard start for su kim email is su.kim@gmail.com, "
                "role is engineering manager"
            ),
            "channel": "web",
            "router": "llm",
        },
    )
    assert together.status_code == 200, together.text
    answer = together.json()["answer"]
    assert "Still need name, role" not in answer
    assert "su kim" in answer
    assert "su.kim@gmail.com" in answer

    follow_up = client.post("/v1/sessions")
    assert follow_up.status_code == 200, follow_up.text
    next_id = follow_up.json()["id"]
    opening = client.post(
        f"/v1/sessions/{next_id}/ask",
        json={"query": "Please onboard a new employee", "channel": "web", "router": "llm"},
    )
    assert opening.status_code == 200, opening.text
    supplied = client.post(
        f"/v1/sessions/{next_id}/ask",
        json={"query": "name is Raj, role is engineer", "channel": "web", "router": "llm"},
    )
    assert supplied.status_code == 200, supplied.text
    assert "Still need name, role" not in supplied.json()["answer"]
    assert supplied.json()["answer"].startswith("Still need email")
    finished = client.post(
        f"/v1/sessions/{next_id}/ask",
        json={
            "query": "name: Raj role: engineer email raj@basepower.com",
            "channel": "web",
            "router": "llm",
        },
    )
    assert finished.status_code == 200, finished.text
    assert "Still need name, role" not in finished.json()["answer"]
    assert "Raj" in finished.json()["answer"]
    assert "engineer" in finished.json()["answer"]


def test_onboarding_modules_do_not_call_the_agent():
    import kp.onboarding.activities as activities
    import kp.onboarding.service as service
    import kp.onboarding.workflow as workflow

    for module in (activities, service, workflow):
        source = inspect.getsource(module)
        assert "create_deep_agent" not in source
        assert "create_session_agent" not in source
        assert "select_skills" not in source
        assert "resolve_skill_stack" not in source
        assert "sandbox" not in source.lower()


def test_onboarding_does_not_call_the_knowledge_path(client, monkeypatch):
    called = []

    async def boom(*_args, **_kwargs):
        called.append("knowledge")
        raise AssertionError("knowledge path")

    def stack_boom(*_args, **_kwargs):
        called.append("stack")
        raise AssertionError("skill stack")

    monkeypatch.setattr("kp.knowledge.ask.synthesize", boom)
    monkeypatch.setattr("kp.agent.factory.create_session_agent", boom)
    monkeypatch.setattr("kp.agent.skills.select_skills", stack_boom)
    monkeypatch.setattr("kp.agent.sandbox.K8sSandbox.provision", stack_boom)
    session_id = login(client, "ceo")["session_id"]
    first = client.post(
        f"/v1/sessions/{session_id}/ask",
        json={"query": "Please onboard a new employee", "channel": "web", "router": "llm"},
    )
    assert first.status_code == 200, first.text
    body = first.json()
    assert body["route"] == {"kind": "workflow", "name": "onboard_employee"}
    assert body["artifacts"] == []
    assert "name" in body["answer"] and "email" in body["answer"]
    assert called == []

    second = client.post(
        f"/v1/sessions/{session_id}/ask",
        json={
            "query": "Which operational problems are driving customer complaints?",
            "channel": "web",
            "router": "llm",
        },
    )
    assert second.status_code == 200, second.text
    assert second.json()["route"]["name"] == "onboard_employee"
    assert called == []

    done = client.post(
        f"/v1/sessions/{session_id}/ask",
        json={
            "query": "Name is Ada Lovelace, email ada@basepower.com, role engineer",
            "channel": "web",
            "router": "llm",
        },
    )
    assert done.status_code == 200, done.text
    assert "Ada Lovelace" in done.json()["answer"]
    assert "ada@basepower.com" in done.json()["answer"]
    assert done.json()["artifacts"] == []
    assert called == []

    from kp.db import SessionLocal

    db = SessionLocal()
    try:
        record = db.query(DirectoryRecord).filter(DirectoryRecord.email == "ada@basepower.com").one()
        assert record.persona_granted is True
        assert record.manager_notified is True
        assert record.role == "engineer"
        note = db.query(ManagerNotification).filter(ManagerNotification.directory_id == record.id).one()
        assert "Ada Lovelace" in note.message
    finally:
        db.close()


def test_jev_unreachable_does_not_fall_back(client, monkeypatch):
    called = []

    async def boom(*_args, **_kwargs):
        called.append("knowledge")

    def refuse(*_args, **_kwargs):
        raise httpx.ConnectError("connection refused")

    monkeypatch.setattr("kp.knowledge.ask.synthesize", boom)
    monkeypatch.setattr("kp.knowledge.intent.httpx.post", refuse)
    session_id = login(client, "marketing")["session_id"]
    response = client.post(
        f"/v1/sessions/{session_id}/ask",
        json={"query": "What language are customers using?", "channel": "web", "router": "jev"},
    )
    assert response.status_code == 502
    assert "openJev" in response.json()["detail"]
    assert "unreachable" in response.json()["detail"]
    assert called == []


def test_complaint_count_must_match_the_join():
    from datetime import datetime, timezone

    from kp.db import SessionLocal

    db = SessionLocal()
    try:
        db.add(
            Issue(
                id="iss_bad_count",
                slug="bad_count",
                name="Bad count",
                description="This row should be rejected.",
                complaint_count=4,
                trend=0,
                severity="low",
                first_seen=datetime.now(timezone.utc),
                last_seen=datetime.now(timezone.utc),
                kind="theme",
            )
        )
        with pytest.raises(DBAPIError, match="complaint_count"):
            db.commit()
    finally:
        db.rollback()
        db.close()

    db = SessionLocal()
    try:
        issue = db.query(Issue).filter(Issue.slug == "installation_delays").one()
        joined = db.query(IssueComplaint).filter(IssueComplaint.issue_id == issue.id).count()
        assert issue.complaint_count == joined
        assert db.get(Issue, "iss_bad_count") is None
    finally:
        db.close()


def test_specialist_phrases_parse_and_complete():
    from kp.onboarding.fields import SPECIALIST_WORKFLOW_NAMES, merge_specialist, parse_specialist, success_sentence
    from kp.reports.intents import CUSTOMER_ONBOARD_WORKFLOW, ONBOARD_WORKFLOW, allowed_workflow

    cases = [
        (
            "onboard field technician",
            "onboard field technician name is Ada Lovelace email is ada@basepower.com trade is electrician home city is Austin",
            "onboard_field_technician",
            "field_technician",
            "Onboarded Ada Lovelace (ada@basepower.com) as electrician in Austin.",
        ),
        (
            "electrician onboard",
            "electrician onboard name: Ada Lovelace email: ada@basepower.com home city: Austin",
            "onboard_field_technician",
            "field_technician",
            "Onboarded Ada Lovelace (ada@basepower.com) as electrician in Austin.",
        ),
        (
            "onboard installer partner",
            "onboard installer partner company name is Bright Grid contact name is Mia Chen email is mia@brightgrid.com city is Dallas",
            "onboard_installer_partner",
            "installer_partner",
            "Onboarded installer partner Bright Grid (mia@brightgrid.com) in Dallas, contact Mia Chen.",
        ),
        (
            "contractor onboard",
            "contractor onboard company name: Bright Grid contact name: Mia Chen email: mia@brightgrid.com city: Dallas",
            "onboard_installer_partner",
            "installer_partner",
            "Onboarded installer partner Bright Grid (mia@brightgrid.com) in Dallas, contact Mia Chen.",
        ),
        (
            "onboard warehouse associate",
            "onboard warehouse associate name is Sam Lee email is sam.lee@basepower.com warehouse city is Dallas shift is night",
            "onboard_warehouse_associate",
            "warehouse_associate",
            "Onboarded Sam Lee (sam.lee@basepower.com) as warehouse associate in Dallas on the night shift.",
        ),
        (
            "warehouse associate onboard",
            "warehouse associate onboard name: Sam Lee email: sam.lee@basepower.com warehouse city: Dallas shift: day",
            "onboard_warehouse_associate",
            "warehouse_associate",
            "Onboarded Sam Lee (sam.lee@basepower.com) as warehouse associate in Dallas on the day shift.",
        ),
        (
            "onboard engineer",
            "onboard engineer name is Priya Shah email is priya@basepower.com specialty is battery",
            "onboard_engineer",
            "engineer",
            "Onboarded Priya Shah (priya@basepower.com) as engineer, specialty battery.",
        ),
        (
            "engineer onboard",
            "engineer onboard name: Priya Shah email: priya@basepower.com specialty: firmware",
            "onboard_engineer",
            "engineer",
            "Onboarded Priya Shah (priya@basepower.com) as engineer, specialty firmware.",
        ),
        (
            "onboard operations manager",
            "onboard operations manager name is Lee Tran email is lee@basepower.com region is central Texas",
            "onboard_operations_manager",
            "operations_manager",
            "Onboarded Lee Tran (lee@basepower.com) as operations manager for central Texas.",
        ),
        (
            "operations manager onboard",
            "operations manager onboard name: Lee Tran email: lee@basepower.com region: Austin",
            "onboard_operations_manager",
            "operations_manager",
            "Onboarded Lee Tran (lee@basepower.com) as operations manager for Austin.",
        ),
        (
            "onboard new market",
            "onboard new market market city is Waco warehouse name is Brazos Hub launch date is 2026-11-02 manager email is lead@basepower.com",
            "onboard_warehouse_launch",
            "warehouse_launch",
            "Onboarded warehouse Brazos Hub in Waco, launch 2026-11-02, manager lead@basepower.com.",
        ),
        (
            "warehouse launch",
            "warehouse launch market city: Waco warehouse name: Brazos Hub launch date: November 2, 2026 manager email: lead@basepower.com",
            "onboard_warehouse_launch",
            "warehouse_launch",
            "Onboarded warehouse Brazos Hub in Waco, launch 2026-11-02, manager lead@basepower.com.",
        ),
    ]
    for phrase, query, workflow, kind, expected in cases:
        assert allowed_workflow("ceo", phrase) == workflow
        assert workflow in SPECIALIST_WORKFLOW_NAMES
        parsed = parse_specialist(kind, query)
        assert missing_fields(parsed) == []
        assert success_sentence(parsed) == expected
    partial = parse_specialist("field_technician", "onboard field technician name is Ada Lovelace")
    assert missing_fields(partial) == ["email", "home city"]
    finished = merge_specialist(
        "field_technician",
        partial,
        parse_specialist("field_technician", "email is ada@basepower.com home city: Austin trade is electrician"),
    )
    assert missing_fields(finished) == []
    assert success_sentence(finished) == "Onboarded Ada Lovelace (ada@basepower.com) as electrician in Austin."
    invalid = parse_specialist("operations_manager", "onboard operations manager region is Chicago")
    assert "region" not in invalid
    assert missing_fields(invalid) == ["name", "email", "region"]


def test_employee_and_customer_are_not_specialist_flows():
    from kp.onboarding.fields import SPECIALIST_WORKFLOW_NAMES
    from kp.reports.intents import CUSTOMER_ONBOARD_WORKFLOW, ONBOARD_WORKFLOW, allowed_workflow

    for phrase in (
        "employee onboard name is Raj role is engineer",
        "onboard employee, role is operations manager",
        "Please onboard a new employee, role engineer",
        "employee onboard start for su kim, role is engineering manager",
    ):
        assert allowed_workflow("ceo", phrase) == ONBOARD_WORKFLOW
        assert allowed_workflow("ceo", phrase) not in SPECIALIST_WORKFLOW_NAMES
        assert not is_customer_onboarding_text(phrase)
    for phrase in ("onboard customer", "customer onboard", "onboard a customer"):
        assert allowed_workflow("ceo", phrase) == CUSTOMER_ONBOARD_WORKFLOW
        assert allowed_workflow("ceo", phrase) not in SPECIALIST_WORKFLOW_NAMES


def test_specialist_onboarding_completes_and_follow_up_remembers_fields(client):
    login(client, "ceo")
    cases = [
        (
            "onboard electrician name is Ada Lovelace email is ada.lovelace@basepower.com home city is Austin",
            "onboard_field_technician",
            "Onboarded Ada Lovelace (ada.lovelace@basepower.com) as electrician in Austin.",
        ),
        (
            "onboard contractor company name: Bright Grid contact name: Mia Chen email: mia.chen@brightgrid.com city: Dallas",
            "onboard_installer_partner",
            "Onboarded installer partner Bright Grid (mia.chen@brightgrid.com) in Dallas, contact Mia Chen.",
        ),
        (
            "onboard engineer name is Priya Shah email is priya.shah@basepower.com specialty is thermal",
            "onboard_engineer",
            "Onboarded Priya Shah (priya.shah@basepower.com) as engineer, specialty thermal.",
        ),
        (
            "operations manager onboard name is Lee Tran email is lee.tran@basepower.com region is Round Rock",
            "onboard_operations_manager",
            "Onboarded Lee Tran (lee.tran@basepower.com) as operations manager for Round Rock.",
        ),
        (
            "onboard warehouse launch market city is Houston warehouse name is Gulf Hub launch date is 2026-12-01 manager email is gulf.lead@basepower.com",
            "onboard_warehouse_launch",
            "Onboarded warehouse Gulf Hub in Houston, launch 2026-12-01, manager gulf.lead@basepower.com.",
        ),
    ]
    for query, workflow, expected in cases:
        session_id = client.post("/v1/sessions").json()["id"]
        body = _ask(client, session_id, query)
        assert body["route"] == {"kind": "workflow", "name": workflow}
        assert body["answer"] == expected
        assert body["artifacts"] == []

    session_id = client.post("/v1/sessions").json()["id"]
    opening = _ask(client, session_id, "onboard warehouse associate name is Sam Lee")
    assert opening["route"]["name"] == "onboard_warehouse_associate"
    assert opening["answer"] == (
        "Still need email, warehouse city, shift. "
        "Send the missing fields in this chat to continue onboarding."
    )
    assert "specialty" not in opening["answer"]
    assert "company name" not in opening["answer"]
    assert "role" not in opening["answer"]
    finished = _ask(
        client,
        session_id,
        "email: sam.lee@basepower.com warehouse city is Dallas shift: night",
    )
    assert finished["route"]["name"] == "onboard_warehouse_associate"
    assert finished["answer"] == (
        "Onboarded Sam Lee (sam.lee@basepower.com) as warehouse associate in Dallas on the night shift."
    )

    employee_id = client.post("/v1/sessions").json()["id"]
    employee = _ask(
        client,
        employee_id,
        "employee onboard name is Raj email is raj.ops@basepower.com role is operations manager",
    )
    assert employee["route"]["name"] == "onboard_employee"
    assert "as operations_manager" in employee["answer"]
    assert "operations manager for" not in employee["answer"]
    engineer_id = client.post("/v1/sessions").json()["id"]
    hired = _ask(
        client,
        engineer_id,
        "onboard employee name is Raj email is raj.eng@basepower.com role is engineer",
    )
    assert hired["route"]["name"] == "onboard_employee"
    assert "specialty" not in hired["answer"]
    assert "as engineer." in hired["answer"]
