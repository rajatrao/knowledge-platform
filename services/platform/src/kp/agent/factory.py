"""Deep agent factory. Onboarding does not call this module."""

from __future__ import annotations

import os

from deepagents import create_deep_agent
from langgraph.checkpoint.memory import MemorySaver

from kp.agent.session_backend import build_session_backend
from kp.agent.skills import mount_skills
from kp.config import get_settings
from kp.llm import CloudKeyRequired, chat_model_for, resolve_llm
from kp.mcp_tools import build_server

_checkpointer: MemorySaver | None = None


def checkpointer() -> MemorySaver:
    global _checkpointer
    if _checkpointer is None:
        _checkpointer = MemorySaver()
    return _checkpointer


async def create_session_agent(session_id: str, selected_ids: list[str], system_prompt: str):
    from langchain.mcp import MCPAdapter

    settings = get_settings()
    try:
        target = resolve_llm()
    except CloudKeyRequired:
        target = None
    if target is not None and target.provider == "ollama":
        model = chat_model_for(target)
    else:
        if settings.llm_api_key:
            os.environ.setdefault("OPENAI_API_KEY", settings.llm_api_key)
        model_name = target.model if target is not None else settings.llm_model
        model = f"openai:{model_name}"
    mounted = mount_skills(selected_ids)
    backend = build_session_backend(session_id, mounted.directories)
    backend.prepare()
    adapter = MCPAdapter(build_server())
    tools = await adapter.list_tools()
    return create_deep_agent(
        model=model,
        tools=tools,
        system_prompt=system_prompt,
        skills=mounted.sources,
        backend=backend,
        checkpointer=checkpointer(),
    )
