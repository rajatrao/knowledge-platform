import asyncio
import json
import re

from kp.db import SessionLocal
from kp.knowledge.ask import handle_ask
from kp.knowledge.retrieve import Bundle
from kp.knowledge.synthesize import (
    _parse_agent_payload,
    derive_suggested_questions,
    model_suggested_questions,
    normalize_suggested_questions,
)
from kp.models import KnowledgeSession
from tests.conftest import login


def _route(monkeypatch):
    class Telemetry:
        model = "test"
        latency_ms = 1

        def as_dict(self):
            return {
                "router": "llm",
                "model": "test",
                "latency_ms": 1,
                "input_tokens": 0,
                "output_tokens": 0,
                "estimated_cost_usd": 0,
            }

    class Decision:
        kind = "skill"
        name = "customer-complaints"
        reason = "test"
        params = {}
        telemetry = Telemetry()

    monkeypatch.setattr(
        "kp.knowledge.ask.router_for",
        lambda name: type("Router", (), {"route": lambda self, *args, **kwargs: Decision()})(),
    )
    monkeypatch.setattr("kp.knowledge.ask.retrieve", lambda *args, **kwargs: Bundle("customer-complaints", {}))
    monkeypatch.setattr("kp.knowledge.ask.include_company_records", lambda *args, **kwargs: None)
    monkeypatch.setattr("kp.knowledge.ask.build_artifacts", lambda *args, **kwargs: [])


def _ask(monkeypatch, session_id, query, synthesize):
    _route(monkeypatch)
    monkeypatch.setattr("kp.knowledge.ask.synthesize", synthesize)
    db = SessionLocal()
    try:
        row = db.get(KnowledgeSession, session_id)
        return asyncio.run(handle_ask(db, row, query, "web", "llm"))
    finally:
        db.close()


def test_parser_keeps_shape_and_normalizes_suggested_questions():
    raw = json.dumps(
        {
            "answer": "Installations are below target.",
            "citations": [],
            "chart": None,
            "suggested_questions": [
                "Which markets are below the installation target?",
                "Want to know more?",
                "Which markets are below the installation target?",
                "not a question",
                "What is the inventory position?",
                "How did rework change?",
            ],
        }
    )
    parsed = _parse_agent_payload(raw)
    assert parsed is not None
    answer, citations, charts = parsed
    assert answer == "Installations are below target."
    assert citations == []
    assert charts == []
    assert model_suggested_questions(raw) == [
        "Which markets are below the installation target?",
        "What is the inventory position?",
        "How did rework change?",
    ]
    assert normalize_suggested_questions(["Want to know more?", "", 4]) == []


def test_omitted_suggestions_are_derived_without_invented_numbers():
    questions = derive_suggested_questions(
        "How are installations tracking?",
        "Installations are 8% below target, concentrated in two markets.\n\n"
        "- technician capacity\n\n"
        "Want to drill into the affected markets?",
        charts=[{"title": "Installations by market", "values": [{"label": "Austin", "count": 8}]}],
    )
    assert questions[0] == "Want to drill into the affected markets?"
    assert len(questions) == 2
    assert questions[1] == "What should we drill into in Installations by market?"
    assert all(not re.search(r"\d", item) for item in questions)


def test_ask_response_includes_suggested_questions(client, monkeypatch):
    session_id = login(client, "ceo")["session_id"]

    async def fake_synthesize(_session_id, _query, bundle, _router_name="llm", prior=""):
        bundle.suggested_questions = [
            "Which markets are below the installation target?",
            "Want to know more?",
        ]
        return "Installations are below target in two markets.", [], []

    result = _ask(monkeypatch, session_id, "How are installations tracking?", fake_synthesize)
    assert result["suggested_questions"] == ["Which markets are below the installation target?"]
    assert result["answer"].startswith("Installations are below target")


def test_ask_response_derives_suggestions_when_the_model_omits_them(client, monkeypatch):
    session_id = login(client, "ceo")["session_id"]

    async def fake_synthesize(*_args, **_kwargs):
        return (
            "Installations are 8% below target in two markets.\n\n- technician capacity",
            [],
            [{"title": "Installations by market", "values": [{"label": "Austin", "count": 8}]}],
        )

    result = _ask(monkeypatch, session_id, "How are installations tracking?", fake_synthesize)
    assert result["suggested_questions"]
    assert len(result["suggested_questions"]) <= 2
    assert all(item.endswith("?") for item in result["suggested_questions"])
    assert all(not re.search(r"\d", item) for item in result["suggested_questions"])
