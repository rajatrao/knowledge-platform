"""OpenAI-compatible LLM targets. Local runs use Ollama and do not need a key."""

from __future__ import annotations

from contextvars import ContextVar, Token
from dataclasses import dataclass

import httpx

from kp.config import get_settings

OLLAMA_PLACEHOLDER_KEY = "ollama"
DEFAULT_OLLAMA_BASE_URL = "http://127.0.0.1:11434/v1"
DEFAULT_OLLAMA_MODEL = "qwen3:8b"

_choice: ContextVar[tuple[str | None, str | None] | None] = ContextVar("kp_llm_choice", default=None)


class CloudKeyRequired(RuntimeError):
    """A cloud model was selected and LLM_API_KEY is missing."""


@dataclass(frozen=True)
class LlmTarget:
    provider: str
    base_url: str
    model: str
    api_key: str


def set_llm_choice(provider: str | None, model: str | None) -> Token:
    return _choice.set((provider, model))


def reset_llm_choice(token: Token) -> None:
    _choice.reset(token)


def _selected() -> tuple[str | None, str | None]:
    current = _choice.get()
    if current is None:
        return None, None
    return current


def resolve_llm(provider: str | None = None, model: str | None = None) -> LlmTarget:
    """Pick the endpoint for this call.

    Ollama is the local default and accepts a placeholder key. A cloud model
    is used only when that provider is selected and LLM_API_KEY is set.
    """
    settings = get_settings()
    if provider is None or model is None:
        selected_provider, selected_model = _selected()
        if provider is None:
            provider = selected_provider
        if model is None:
            model = selected_model
    chosen = (provider or settings.llm_provider or "ollama").strip().lower()
    if chosen in {"cloud", "openai"}:
        if not settings.llm_api_key:
            raise CloudKeyRequired("LLM_API_KEY is required for a cloud model")
        base = (settings.llm_base_url or "https://api.openai.com/v1").rstrip("/")
        chosen_model = (model or settings.llm_model).strip() or settings.llm_model
        return LlmTarget("openai", base, chosen_model, settings.llm_api_key)
    if chosen not in {"ollama", "local"}:
        raise ValueError(f"Unknown LLM provider {chosen!r}")
    base = (settings.ollama_base_url or DEFAULT_OLLAMA_BASE_URL).rstrip("/")
    chosen_model = (model or settings.ollama_model or DEFAULT_OLLAMA_MODEL).strip() or DEFAULT_OLLAMA_MODEL
    return LlmTarget("ollama", base, chosen_model, OLLAMA_PLACEHOLDER_KEY)


class OpenAICompatibleClient:
    """Chat-completions client. Ollama and OpenAI share this request shape."""

    def __init__(self, *, base_url: str, api_key: str, model: str, provider: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.provider = provider

    def chat_completion(
        self,
        messages: list[dict],
        timeout: float | None = None,
        num_predict: int | None = None,
        num_ctx: int | None = None,
    ) -> dict:
        if timeout is None:
            timeout = 120 if self.provider == "ollama" else 30
        payload = {
            "model": self.model,
            "messages": messages,
            "response_format": {"type": "json_object"},
        }
        if self.provider == "ollama":
            return self._ollama_chat(messages, timeout, num_predict or 192, num_ctx or 2048)
        response = httpx.post(
            f"{self.base_url}/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json=payload,
            timeout=timeout,
        )
        response.raise_for_status()
        return response.json()

    def _ollama_chat(self, messages: list[dict], timeout: float, num_predict: int, num_ctx: int = 2048) -> dict:
        """Native /api/chat. The OpenAI route still spends the token budget on reasoning."""
        base = self.base_url.removesuffix("/v1").rstrip("/")
        response = httpx.post(
            f"{base}/api/chat",
            json={
                "model": self.model,
                "messages": messages,
                "stream": False,
                "think": False,
                "format": "json",
                "options": {"num_predict": num_predict, "num_ctx": num_ctx},
            },
            timeout=timeout,
        )
        response.raise_for_status()
        body = response.json()
        message = body.get("message") or {}
        return {
            "choices": [{"message": {"role": message.get("role") or "assistant", "content": message.get("content") or ""}}],
            "usage": {
                "input_tokens": body.get("prompt_eval_count") or 0,
                "output_tokens": body.get("eval_count") or 0,
            },
            "model": body.get("model") or self.model,
        }


def build_openai_compatible_client(provider: str | None = None, model: str | None = None) -> OpenAICompatibleClient:
    target = resolve_llm(provider, model)
    return OpenAICompatibleClient(
        base_url=target.base_url,
        api_key=target.api_key,
        model=target.model,
        provider=target.provider,
    )


def chat_model_for(target: LlmTarget):
    """LangChain chat model aimed at an OpenAI-compatible /v1 server.

    Ollama does not implement the OpenAI Responses API, so chat completions
    stay on.
    """
    from langchain_openai import ChatOpenAI

    kwargs = {
        "model": target.model,
        "base_url": target.base_url,
        "api_key": target.api_key,
        "use_responses_api": False,
        "max_tokens": 512,
        "timeout": 120,
    }
    if target.provider == "ollama":
        # Qwen thinking traces run for minutes at local token rates and the
        # ask endpoint stays open until the agent call returns.
        kwargs["extra_body"] = {"think": False}
    return ChatOpenAI(**kwargs)
