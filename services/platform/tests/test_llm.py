"""Local Ollama client. Network calls are mocked."""

import json
import sys
import types

from kp.agent.skills import select_skills
from kp.config import get_settings
from kp.knowledge.intent import router_for
from kp.llm import (
    build_openai_compatible_client,
    chat_model_for,
    reset_llm_choice,
    resolve_llm,
    set_llm_choice,
)


class _Response:
    def __init__(self, content: str) -> None:
        self._content = content

    def raise_for_status(self):
        return None

    def json(self):
        return {
            "message": {"role": "assistant", "content": self._content},
            "prompt_eval_count": 10,
            "eval_count": 3,
            "model": "qwen3:8b",
        }


def _use_local(monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "")
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    monkeypatch.delenv("OLLAMA_BASE_URL", raising=False)
    monkeypatch.delenv("OLLAMA_MODEL", raising=False)
    monkeypatch.delenv("LLM_BASE_URL", raising=False)
    get_settings.cache_clear()


def test_local_provider_builds_an_openai_compatible_client_without_a_key(monkeypatch):
    _use_local(monkeypatch)
    captured = {}

    def fake_post(url, headers=None, json=None, timeout=None):
        captured["url"] = url
        captured["headers"] = headers
        captured["json"] = json
        captured["timeout"] = timeout
        return _Response(json_dumps_skill())

    monkeypatch.setattr("kp.llm.httpx.post", fake_post)
    constructed = {}

    class FakeChat:
        def __init__(self, **kwargs):
            constructed.update(kwargs)

    fake_module = types.ModuleType("langchain_openai")
    fake_module.ChatOpenAI = FakeChat
    monkeypatch.setitem(sys.modules, "langchain_openai", fake_module)
    try:
        client = build_openai_compatible_client()
        assert client.provider == "ollama"
        assert client.base_url == "http://127.0.0.1:11434/v1"
        assert client.model == "qwen3:8b"
        assert client.api_key == "ollama"
        client.chat_completion([{"role": "user", "content": "hi"}])
        assert captured["url"] == "http://127.0.0.1:11434/api/chat"
        assert captured["json"]["model"] == "qwen3:8b"
        assert captured["json"]["think"] is False
        assert captured["json"]["format"] == "json"
        assert captured["json"]["options"]["num_predict"] == 192
        assert captured["json"]["options"]["num_ctx"] == 2048
        assert get_settings().llm_api_key == ""

        chosen = select_skills("What broke in the field?", "ceo")
        assert chosen == ["complaint-incidents"]
        assert captured["url"] == "http://127.0.0.1:11434/api/chat"
        assert captured["json"]["model"] == "qwen3:8b"

        model = chat_model_for(resolve_llm())
        assert isinstance(model, FakeChat)
        assert constructed["base_url"] == "http://127.0.0.1:11434/v1"
        assert constructed["model"] == "qwen3:8b"
        assert constructed["api_key"] == "ollama"
        assert constructed["use_responses_api"] is False
        assert constructed["max_tokens"] == 512
        assert constructed["timeout"] == 120
        assert constructed["extra_body"] == {"think": False}
    finally:
        get_settings.cache_clear()


def test_selected_ollama_provider_overrides_a_cloud_default(monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "")
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    get_settings.cache_clear()
    captured = {}

    def fake_post(url, headers=None, json=None, timeout=None):
        del headers, timeout
        captured["url"] = url
        captured["json"] = json
        payload = '{"kind": "skill", "name": "customer-complaints", "params": {}, "reason": "local"}'
        return _Response(payload)

    monkeypatch.setattr("kp.llm.httpx.post", fake_post)
    token = set_llm_choice("ollama", None)
    try:
        decision = router_for("llm").route("ceo", "What are the top customer complaints?", [])
    finally:
        reset_llm_choice(token)
        get_settings.cache_clear()
    assert captured["url"] == "http://127.0.0.1:11434/api/chat"
    assert captured["json"]["model"] == "qwen3:8b"
    assert captured["json"]["think"] is False
    assert decision.telemetry.router == "llm"
    assert decision.telemetry.model == "qwen3:8b"
    assert decision.telemetry.estimated_cost_usd == 0.0


def test_truncated_router_json_uses_the_deterministic_route(monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "")
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    get_settings.cache_clear()

    def fake_post(url, headers=None, json=None, timeout=None):
        del url, headers, json, timeout
        return _Response('{"kind": "skill", "name": "customer-complaints", "reason": "cut')

    monkeypatch.setattr("kp.llm.httpx.post", fake_post)
    token = set_llm_choice("ollama", None)
    try:
        decision = router_for("llm").route("ceo", "create a chart for complaints across customer regions", [])
    finally:
        reset_llm_choice(token)
        get_settings.cache_clear()
    assert decision.kind == "skill"
    assert decision.name == "customer-complaints"
    assert "deterministic" in decision.reason


def json_dumps_skill() -> str:
    return json.dumps({"skill_ids": ["complaint-incidents"]})
