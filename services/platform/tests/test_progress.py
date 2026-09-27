import asyncio
import inspect
import json

from kp.db import SessionLocal
from kp.knowledge.ask import handle_ask
from kp.knowledge.retrieve import Bundle
from kp.models import KnowledgeSession
from tests.conftest import login


def test_ask_streams_backend_stages(client, monkeypatch):
    async def fake_handle_ask(db, session, query, channel, router_name, provider=None, model=None, progress=None):
        if progress is not None:
            for label in ("routing ask", "retrieving data", "agent synthesizing", "building result"):
                reported = progress(label)
                if inspect.isawaitable(reported):
                    await reported
        return {
            "session_id": session.id,
            "answer": "ok",
            "citations": [],
            "route": {"kind": "skill", "name": "customer-complaints"},
            "artifacts": [],
            "report": None,
            "telemetry": {},
        }

    monkeypatch.setattr("kp.api.handle_ask", fake_handle_ask)
    session_id = login(client, "ceo")["session_id"]
    body = {"query": "billing confusion", "channel": "web", "router": "llm"}
    streamed = client.post(f"/v1/sessions/{session_id}/ask", json=body, headers={"Accept": "application/x-ndjson"})
    assert streamed.status_code == 200
    assert streamed.headers["content-type"].startswith("application/x-ndjson")
    lines = [json.loads(line) for line in streamed.text.splitlines() if line.strip()]
    assert [line["stage"] for line in lines if "stage" in line] == [
        "routing ask",
        "retrieving data",
        "agent synthesizing",
        "building result",
    ]
    assert lines[-1]["done"] is True

    plain = client.post(f"/v1/sessions/{session_id}/ask", json=body)
    assert plain.status_code == 200
    assert plain.headers["content-type"].startswith("application/json")
    assert plain.json()["answer"] == "ok"


def test_knowledge_ask_reports_each_stage(client, monkeypatch):
    session_id = login(client, "ceo")["session_id"]

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

    async def fake_synthesize(*args, **kwargs):
        return "noted", [], []

    monkeypatch.setattr("kp.knowledge.ask.synthesize", fake_synthesize)
    monkeypatch.setattr("kp.knowledge.ask.build_artifacts", lambda *args, **kwargs: [])

    stages = []
    db = SessionLocal()
    try:
        row = db.get(KnowledgeSession, session_id)
        asyncio.run(
            handle_ask(
                db,
                row,
                "what is billing confusion",
                "web",
                "llm",
                progress=stages.append,
            )
        )
    finally:
        db.close()
    assert stages == ["routing ask", "retrieving data", "agent synthesizing", "building result"]
