import json
from pathlib import Path

from kp.agent.skills import (
    SkillSelectorRequired,
    catalog_metadata,
    mount_skills,
    select_skills,
    skill_catalog,
)
from kp.config import get_settings
from kp.db import SessionLocal
from kp.knowledge.intent import RouteDecision, Telemetry
from kp.models import User
from kp.seed import SEEDED_SKILL_IDS
from tests.conftest import login


def _write_skill(root: Path, relative: str, name: str, description: str) -> None:
    path = root / relative / "SKILL.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"---\nname: {name}\ndescription: {description}\n---\n\nUse {name}.\n")


def _stub_router(monkeypatch):
    def router_for(_name):
        class Router:
            def route(self, persona, query, turns):
                return RouteDecision(
                    kind="skill",
                    name="customer-complaints",
                    params={},
                    reason="test",
                    telemetry=Telemetry("llm", "deterministic-router", 0, 1, 1, 0.0),
                )

        return Router()

    monkeypatch.setattr("kp.knowledge.ask.router_for", router_for)


def _fake_adapter():
    class FakeAdapter:
        def __init__(self, target):
            self.target = target

        async def list_tools(self):
            return []

    return FakeAdapter


class _Message:
    def __init__(self, content: str) -> None:
        self.content = content


def test_catalog_metadata_names_tier_and_role_without_bodies():
    catalog = skill_catalog()
    by_id = {skill.id: skill for skill in catalog}
    assert by_id["base-power-orientation"].tier == "foundational"
    assert by_id["base-power-orientation"].role is None
    assert by_id["complaint-incidents"].tier == "function"
    assert by_id["complaint-incidents"].role == "engineer"
    assert by_id["engineering-agent"].tier == "agent"
    assert by_id["engineering-agent"].role == "engineer"
    assert by_id["weekly-complaint-readout"].tier == "user"
    rows = catalog_metadata(catalog)
    incident = next(row for row in rows if row["id"] == "complaint-incidents")
    assert incident == {
        "id": "complaint-incidents",
        "name": "complaint-incidents",
        "description": by_id["complaint-incidents"].description,
        "tier": "function",
        "role": "engineer",
    }
    foundational = next(row for row in rows if row["id"] == "data-access")
    assert "role" not in foundational
    assert "body" not in incident


def test_mount_follows_selected_ids_including_outside_the_callers_role():
    mounted = mount_skills(["complaint-incidents", "engineering-agent"])
    assert mounted.names == ["complaint-incidents", "engineering-agent"]
    assert mounted.sources == [
        "/skills/functions/engineer/",
        "/skills/agents/engineer/",
    ]
    assert "customer-complaints" not in mounted.names
    assert "investigation-agent" not in mounted.names


def test_unknown_ids_are_not_replaced_with_a_persona_stack():
    mounted = mount_skills(["no-such-skill", "../secrets"])
    assert mounted.names == []
    assert mounted.sources == []
    assert mounted.directories == []


def test_a_new_user_skill_file_mounts_without_a_loader_change(tmp_path):
    root = tmp_path / "skills"
    _write_skill(root, "users/desk-notes", "desk-notes", "A personal desk notes workflow.")
    catalog = skill_catalog(root)
    assert [skill.id for skill in catalog] == ["desk-notes"]
    assert catalog[0].tier == "user"
    mounted = mount_skills(["desk-notes", "missing-skill"], skills_root=root)
    assert mounted.names == ["desk-notes"]
    assert mounted.sources == ["/skills/users/"]
    loader = Path(__file__).resolve().parents[1] / "src" / "kp" / "agent" / "skills.py"
    text = loader.read_text()
    assert "desk-notes" not in text
    assert "weekly-complaint-readout" not in text
    assert "PERSONA_SKILLS" not in text
    assert "user.skill_ids" not in text
    assert "resolve_skill_stack" not in text


def test_selector_sends_metadata_role_and_question(monkeypatch):
    captured = {}

    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "choices": [
                    {
                        "message": {
                            "content": json.dumps({"skill_ids": ["complaint-incidents"]}),
                        }
                    }
                ]
            }

    def fake_post(url, headers=None, json=None, timeout=None):
        captured["url"] = url
        captured["json"] = json
        return Response()

    monkeypatch.setenv("LLM_API_KEY", "test-key")
    get_settings.cache_clear()
    monkeypatch.setattr("kp.llm.httpx.post", fake_post)
    try:
        chosen = select_skills("What broke in the field?", "ceo")
    finally:
        get_settings.cache_clear()
    assert chosen == ["complaint-incidents"]
    assert captured["url"] == "https://api.openai.com/v1/chat/completions"
    assert "jev" not in captured["url"]
    payload = json.loads(captured["json"]["messages"][1]["content"])
    assert payload["role"] == "ceo"
    assert payload["question"] == "What broke in the field?"
    assert any(row["id"] == "complaint-incidents" and row["role"] == "engineer" for row in payload["skills"])
    assert "You are answering the CEO" not in captured["json"]["messages"][1]["content"]
    system = captured["json"]["messages"][0]["content"]
    assert "role is context" in system


def test_selector_requires_an_llm_key(monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "")
    get_settings.cache_clear()
    try:
        try:
            select_skills("What broke?", "ceo")
            raised = False
        except SkillSelectorRequired as exc:
            raised = True
            assert "LLM_API_KEY" in str(exc)
        assert raised
    finally:
        get_settings.cache_clear()


def test_knowledge_ask_without_a_selector_key_fails(client):
    session_id = login(client, "ceo")["session_id"]
    response = client.post(
        f"/v1/sessions/{session_id}/ask",
        json={
            "query": "What are the top customer complaints and recommended solutions?",
            "channel": "web",
            "router": "llm",
        },
    )
    assert response.status_code == 400
    assert "LLM_API_KEY" in response.json()["detail"]


def test_selection_modules_do_not_read_user_skill_ids():
    root = Path(__file__).resolve().parents[1] / "src" / "kp"
    for relative in (
        "knowledge/ask.py",
        "knowledge/synthesize.py",
        "knowledge/retrieve.py",
        "agent/factory.py",
        "agent/skills.py",
    ):
        text = (root / relative).read_text()
        assert "user.skill_ids" not in text
        assert "users.skill_ids" not in text


def test_mocked_selector_is_what_gets_mounted(client, monkeypatch):
    db = SessionLocal()
    user = db.query(User).filter(User.username == "ceo").one()
    original = list(user.skill_ids or [])
    user.skill_ids = ["weekly-complaint-readout", "not-mounted"]
    db.commit()
    db.close()

    captured = {}
    seen = {}

    def selector(question, role):
        seen["question"] = question
        seen["role"] = role
        return ["complaint-incidents"]

    def fake_create_deep_agent(**kwargs):
        captured.update(kwargs)

        class Agent:
            async def ainvoke(self, *_args, **_kwargs):
                return {"messages": [_Message(json.dumps({"answer": "mounted", "citations": []}))]}

        return Agent()

    monkeypatch.setenv("LLM_API_KEY", "test-key")
    get_settings.cache_clear()
    monkeypatch.setattr("kp.agent.skills.select_skills", selector)
    monkeypatch.setattr("kp.agent.sandbox.K8sSandbox.provision", lambda self: object())
    monkeypatch.setattr("langchain.mcp.MCPAdapter", _fake_adapter())
    monkeypatch.setattr("kp.agent.factory.create_deep_agent", fake_create_deep_agent)
    _stub_router(monkeypatch)
    try:
        session_id = login(client, "ceo")["session_id"]
        response = client.post(
            f"/v1/sessions/{session_id}/ask",
            json={
                "query": "What are the top customer complaints and recommended solutions?",
                "channel": "web",
                "router": "llm",
            },
        )
        assert response.status_code == 200, response.text
        assert response.json()["answer"] == "mounted"
        assert seen["role"] == "ceo"
        assert "complaints" in seen["question"]
        assert captured["skills"] == ["/skills/functions/engineer/"]
        assert "/skills/functions/ceo/" not in captured["skills"]
        assert "/skills/agents/ceo/" not in captured["skills"]
        assert "/skills/users/" not in captured["skills"]
        assert "/skills/foundational/" not in captured["skills"]
        db = SessionLocal()
        try:
            stored = db.query(User).filter(User.username == "ceo").one()
            assert stored.skill_ids == ["weekly-complaint-readout", "not-mounted"]
        finally:
            db.close()
    finally:
        get_settings.cache_clear()
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.username == "ceo").one()
            user.skill_ids = original or list(SEEDED_SKILL_IDS["ceo"])
            db.commit()
        finally:
            db.close()
