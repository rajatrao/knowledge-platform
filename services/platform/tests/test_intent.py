"""Local openJev routing. The HTTP call is mocked."""

import httpx

from kp.agent.skills import select_skills_with_jev
from kp.config import get_settings
from kp.knowledge.intent import JevUnavailable, router_for
from kp.labels import PERSONA_SKILLS


class _Response:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            request = httpx.Request("POST", "http://127.0.0.1:8081/v1/systemone")
            response = httpx.Response(self.status_code, request=request)
            raise httpx.HTTPStatusError("error", request=request, response=response)

    def json(self):
        return self._payload


def _systemone(choice, model="laya-1.0"):
    return {
        "model": model,
        "answers": {
            "route": {
                "type": "choice",
                "choice": choice,
                "probabilities": {choice: 1.0},
                "confidence": 0.91,
            }
        },
        "usage": {"input_tokens": 40, "output_tokens": 0},
    }


def _capture(monkeypatch, payload, status_code=200):
    captured = {}

    def post(url, headers=None, json=None, timeout=None):
        captured["url"] = url
        captured["headers"] = headers or {}
        captured["json"] = json
        captured["timeout"] = timeout
        return _Response(payload, status_code)

    monkeypatch.setattr("kp.knowledge.intent.httpx.post", post)
    monkeypatch.setenv("JEV_API_KEY", "")
    monkeypatch.setenv("JEV_BASE_URL", "http://127.0.0.1:8081")
    monkeypatch.setenv("JEV_MODEL", "laya-1.0")
    get_settings.cache_clear()
    return captured


def test_openjev_workflow_choice_needs_no_api_key(monkeypatch):
    captured = _capture(monkeypatch, _systemone("onboard_employee"))
    decision = router_for("jev").route("ceo", "Please onboard Ada Lovelace", [])
    assert captured["url"] == "http://127.0.0.1:8081/v1/systemone"
    assert "Authorization" not in captured["headers"]
    assert captured["json"]["model"] == "laya-1.0"
    assert captured["json"]["questions"]["route"]["type"] == "choice"
    assert "onboard_employee" in captured["json"]["questions"]["route"]["criteria"]
    assert decision.kind == "workflow"
    assert decision.name == "onboard_employee"
    assert decision.telemetry.router == "jev"
    assert decision.telemetry.model == "laya-1.0"
    assert decision.telemetry.input_tokens == 40
    assert decision.telemetry.estimated_cost_usd == 0.0


def test_openjev_knowledge_choice_is_the_persona_skill(monkeypatch):
    _capture(monkeypatch, _systemone("knowledge"))
    decision = router_for("jev").route("marketing", "What language are customers using?", [])
    assert decision.kind == "skill"
    assert decision.name == PERSONA_SKILLS["marketing"]


def test_openjev_weak_workflow_label_stays_a_skill(monkeypatch):
    payload = _systemone("issue_trend_report")
    payload["answers"]["route"]["probabilities"] = {
        "issue_trend_report": 0.34,
        "knowledge": 0.26,
    }
    payload["answers"]["route"]["confidence"] = 0.04
    _capture(monkeypatch, payload)
    decision = router_for("jev").route("ceo", "create a chart for complaints across regions", [])
    assert decision.kind == "skill"
    assert decision.name == PERSONA_SKILLS["ceo"]
    assert "knowledge skill" in decision.reason


def test_openjev_sends_a_key_only_when_one_is_set(monkeypatch):
    captured = _capture(monkeypatch, _systemone("knowledge"))
    monkeypatch.setenv("JEV_API_KEY", "local-only")
    get_settings.cache_clear()
    router_for("jev").route("ceo", "hello", [])
    assert captured["headers"]["Authorization"] == "Bearer local-only"


def test_openjev_selects_skills_above_the_yes_threshold(monkeypatch):
    payload = {
        "model": "laya-1.0",
        "answers": {
            "customer-complaints": {
                "choice": "yes",
                "probabilities": {"yes": 0.82, "no": 0.18},
            },
            "value-language": {
                "choice": "yes",
                "probabilities": {"yes": 0.51, "no": 0.49},
            },
            "data-access": {
                "choice": "no",
                "probabilities": {"yes": 0.2, "no": 0.8},
            },
        },
        "usage": {"input_tokens": 10, "output_tokens": 0},
    }
    _capture(monkeypatch, payload)
    chosen = select_skills_with_jev("What are the top complaints?", "ceo")
    assert chosen == ["customer-complaints"]


def test_openjev_all_no_mounts_no_skill(monkeypatch):
    from kp.agent.skills import skill_catalog

    payload = {
        "model": "laya-1.0",
        "answers": {
            skill.id: {"choice": "no", "probabilities": {"yes": 0.48, "no": 0.52}}
            for skill in skill_catalog()
        },
        "usage": {"input_tokens": 10, "output_tokens": 0},
    }
    _capture(monkeypatch, payload)
    assert select_skills_with_jev("chart company revenue quarter over quarter", "ceo") == []


def test_openjev_http_error_is_not_a_route(monkeypatch):
    _capture(monkeypatch, {}, status_code=503)
    try:
        router_for("jev").route("ceo", "hello", [])
    except JevUnavailable as exc:
        assert "503" in str(exc)
    else:
        raise AssertionError("expected JevUnavailable")


def test_openjev_unexpected_body_fails(monkeypatch):
    _capture(monkeypatch, {"model": "laya-1.0", "answers": {}})
    try:
        router_for("jev").route("ceo", "hello", [])
    except JevUnavailable as exc:
        assert "unexpected" in str(exc)
    else:
        raise AssertionError("expected JevUnavailable")
