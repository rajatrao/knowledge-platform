import json
import os
from pathlib import Path

import pytest
import yaml
from dataclasses import replace
from deepagents.backends.protocol import ExecuteResponse, FileDownloadResponse

from kp.agent.sandbox import (
    K8sSandbox,
    SandboxUnavailable,
    claim_name_for,
    kind_kubeconfig_path,
    namespace_for,
    use_kind_kubeconfig,
)
from kp.agent.session_backend import build_session_backend
from kp.auth import session_dir
from kp.config import get_settings
from kp.knowledge.intent import RouteDecision, Telemetry
from kp.storage import require_s3
from tests.conftest import login


def test_compose_keeps_minio_on_the_s3_profile():
    root = Path(__file__).resolve().parents[3]
    data = yaml.safe_load((root / "docker-compose.yml").read_text())
    assert data["services"]["minio"]["profiles"] == ["s3"]
    assert data["services"]["minio-init"]["profiles"] == ["s3"]
    assert "profiles" not in data["services"]["postgres"]
    assert "profiles" not in data["services"]["temporal"]


def test_disk_is_the_default_filesystem(monkeypatch):
    monkeypatch.delenv("FILESYSTEM", raising=False)
    get_settings.cache_clear()
    try:
        settings = get_settings()
        assert settings.filesystem == "disk"
        assert not hasattr(settings, "sandbox_mode")
    finally:
        monkeypatch.setenv("FILESYSTEM", "disk")
        get_settings.cache_clear()


def test_s3_without_a_bucket_fails():
    settings = replace(get_settings(), filesystem="s3", s3_bucket="")
    with pytest.raises(RuntimeError, match="S3_BUCKET"):
        require_s3(settings)


def test_namespace_uses_the_session_id():
    session_id = "550e8400-e29b-41d4-a716-446655440000"
    label = namespace_for(session_id)
    assert label == f"sess-{session_id}"
    assert len(label) <= 63


class _Remote:
    def __init__(self) -> None:
        self.events: list[tuple] = []
        self.files: dict[str, bytes] = {}

    def upload_files(self, files):
        self.events.append(("upload", [path for path, _content in files]))
        for path, content in files:
            self.files[path] = content

    def execute(self, command, timeout=None):
        self.events.append(("execute", command))
        if "copy.txt" in command and "/workspace/note.txt" in self.files:
            self.files["/workspace/copy.txt"] = self.files["/workspace/note.txt"]
        if "from-sandbox.txt" in command:
            self.files["/workspace/from-sandbox.txt"] = b"synced"
        if "from-shell.txt" in command:
            self.files["/workspace/from-shell.txt"] = b"synced"
        if str(command).startswith("find"):
            lines = [f".{path}" for path in sorted(self.files)]
            return ExecuteResponse(output="\n".join(lines), exit_code=0, truncated=False)
        if str(command).startswith("cat"):
            return ExecuteResponse(
                output=self.files.get("/workspace/copy.txt", b"").decode(),
                exit_code=0,
                truncated=False,
            )
        return ExecuteResponse(output="ok", exit_code=0, truncated=False)

    def download_files(self, paths):
        responses = []
        for path in paths:
            if path in self.files:
                responses.append(FileDownloadResponse(path=path, content=self.files[path], error=None))
            else:
                responses.append(FileDownloadResponse(path=path, content=None, error="file_not_found"))
        return responses


class _Api:
    def read_namespace(self, name=None, **kwargs):
        return object()

    def create_namespace(self, body=None, **kwargs):
        return body

    def create_namespaced_resource_quota(self, namespace=None, body=None, **kwargs):
        return body

    def create_namespaced_network_policy(self, namespace=None, body=None, **kwargs):
        return body

    def create_namespaced_custom_object(self, **kwargs):
        return kwargs


def _install_k8s(monkeypatch, remote):
    created = {}

    def create_kubernetes_sandbox(**kwargs):
        created["kwargs"] = kwargs
        return remote

    class Client:
        def __init__(self, *args, **kwargs):
            created["client"] = True

    monkeypatch.setattr("kubernetes.config.load_kube_config", lambda *args, **kwargs: None)
    monkeypatch.setattr("kubernetes.client.CoreV1Api", _Api)
    monkeypatch.setattr("kubernetes.client.NetworkingV1Api", _Api)
    monkeypatch.setattr("kubernetes.client.CustomObjectsApi", _Api)
    monkeypatch.setattr("k8s_agent_sandbox.SandboxClient", Client)
    monkeypatch.setattr("langchain_k8s.create_kubernetes_sandbox", create_kubernetes_sandbox)
    return created


def _block_subprocess(monkeypatch):
    called = {"subprocess": False}

    def fail_subprocess(*_args, **_kwargs):
        called["subprocess"] = True
        raise AssertionError("local subprocess")

    monkeypatch.setattr("subprocess.run", fail_subprocess)
    return called


def test_k8s_execute_copies_workspace_in_and_outputs_back(monkeypatch):
    session_id = "66666666-6666-6666-6666-666666666666"
    root = session_dir(session_id)
    (root / "workspace" / "note.txt").write_text("hi")
    remote = _Remote()
    _install_k8s(monkeypatch, remote)
    subprocess_calls = _block_subprocess(monkeypatch)
    result = K8sSandbox(session_id).execute("cp workspace/note.txt workspace/copy.txt")
    assert result.exit_code == 0
    assert (root / "workspace" / "copy.txt").read_text() == "hi"
    upload_at = next(index for index, event in enumerate(remote.events) if event[0] == "upload")
    command_at = next(
        index for index, event in enumerate(remote.events) if event[0] == "execute" and "copy.txt" in event[1]
    )
    assert upload_at < command_at
    assert "/workspace/note.txt" in remote.events[upload_at][1]
    again = K8sSandbox(session_id).execute("cat workspace/copy.txt")
    assert "hi" in again.output
    assert subprocess_calls["subprocess"] is False


def test_resumed_session_sees_files_on_disk(monkeypatch):
    session_id = "11111111-1111-1111-1111-111111111111"
    skill_dirs = [
        "foundational/base-power-orientation",
        "functions/ceo/customer-complaints",
    ]
    remote = _Remote()
    _install_k8s(monkeypatch, remote)
    subprocess_calls = _block_subprocess(monkeypatch)
    backend = build_session_backend(session_id, skill_dirs)
    assert isinstance(backend._sandbox, K8sSandbox)
    assert backend.filesystem == "disk"
    written = backend.write("/workspace/hello.txt", "persisted")
    assert written.error is None
    denied = backend.write("/skills/foundational/base-power-orientation/SKILL.md", "overwrite")
    assert denied.error
    skill = backend.read("/skills/foundational/base-power-orientation/SKILL.md")
    assert "Base Power" in skill.file_data["content"]
    executed = backend.execute("printf synced > workspace/from-shell.txt")
    assert executed.exit_code == 0
    resumed = build_session_backend(session_id, skill_dirs)
    assert "persisted" in resumed.read("/workspace/hello.txt").file_data["content"]
    assert "synced" in resumed.read("/workspace/from-shell.txt").file_data["content"]
    assert subprocess_calls["subprocess"] is False


def test_kind_kubeconfig_path_follows_the_cluster_name(monkeypatch):
    monkeypatch.delenv("KIND_CLUSTER", raising=False)
    assert kind_kubeconfig_path().name == "kind-knowledge.yaml"
    monkeypatch.setenv("KIND_CLUSTER", "knowledge")
    assert kind_kubeconfig_path() == Path.home() / ".kube" / "kind-knowledge.yaml"


def test_sandbox_client_uses_the_kind_kubeconfig(monkeypatch, tmp_path):
    kubeconfig = tmp_path / "kind-knowledge.yaml"
    kubeconfig.write_text("apiVersion: v1\nkind: Config\n")
    monkeypatch.delenv("KUBECONFIG", raising=False)
    monkeypatch.setenv("KIND_CLUSTER", "knowledge")
    monkeypatch.setattr("kp.agent.sandbox.kind_kubeconfig_path", lambda cluster=None: kubeconfig)
    seen = {}

    def load_kube_config(*_args, **_kwargs):
        seen["load"] = os.environ.get("KUBECONFIG")

    class Client:
        def __init__(self, *_args, **_kwargs):
            seen["client"] = os.environ.get("KUBECONFIG")

    remote = _Remote()
    created = _install_k8s(monkeypatch, remote)
    monkeypatch.setattr("kubernetes.config.load_kube_config", load_kube_config)
    monkeypatch.setattr("k8s_agent_sandbox.SandboxClient", Client)
    subprocess_calls = _block_subprocess(monkeypatch)
    K8sSandbox("550e8400-e29b-41d4-a716-446655440000").provision()
    assert seen["load"] == str(kubeconfig)
    assert seen["client"] == str(kubeconfig)
    assert created["kwargs"]["namespace"] == namespace_for("550e8400-e29b-41d4-a716-446655440000")
    assert subprocess_calls["subprocess"] is False


def test_kind_kubeconfig_wins_after_kubernetes_cached_another_path(monkeypatch, tmp_path):
    kubeconfig = tmp_path / "kind-knowledge.yaml"
    kubeconfig.write_text("apiVersion: v1\nkind: Config\n")
    monkeypatch.delenv("KUBECONFIG", raising=False)
    monkeypatch.setenv("KIND_CLUSTER", "knowledge")
    monkeypatch.setattr("kp.agent.sandbox.kind_kubeconfig_path", lambda cluster=None: kubeconfig)
    import kubernetes.config.kube_config as kube_mod

    kube_mod.KUBE_CONFIG_DEFAULT_LOCATION = "~/.kube/config"
    seen = {}

    def load_kube_config(config_file=None, **_kwargs):
        seen["file"] = config_file
        seen["default"] = kube_mod.KUBE_CONFIG_DEFAULT_LOCATION

    remote = _Remote()
    _install_k8s(monkeypatch, remote)
    monkeypatch.setattr("kubernetes.config.load_kube_config", load_kube_config)
    _block_subprocess(monkeypatch)
    K8sSandbox("550e8400-e29b-41d4-a716-446655440000").provision()
    assert seen["file"] == str(kubeconfig)
    assert seen["default"] == str(kubeconfig)


def test_missing_kind_kubeconfig_stays_a_503(monkeypatch, tmp_path):
    monkeypatch.delenv("KUBECONFIG", raising=False)
    monkeypatch.setenv("KIND_CLUSTER", "knowledge")
    monkeypatch.setattr("kp.agent.sandbox.kind_kubeconfig_path", lambda cluster=None: tmp_path / "missing.yaml")

    def boom(*_args, **_kwargs):
        raise RuntimeError("no cluster")

    monkeypatch.setattr("kubernetes.config.load_kube_config", boom)
    subprocess_calls = _block_subprocess(monkeypatch)
    with pytest.raises(SandboxUnavailable, match="Kubernetes sandbox is required"):
        K8sSandbox("550e8400-e29b-41d4-a716-446655440000").provision()
    assert os.environ.get("KUBECONFIG", "") == ""
    assert subprocess_calls["subprocess"] is False


def test_explicit_kubeconfig_is_not_replaced(monkeypatch, tmp_path):
    kubeconfig = tmp_path / "kind-knowledge.yaml"
    kubeconfig.write_text("apiVersion: v1\nkind: Config\n")
    monkeypatch.setenv("KUBECONFIG", "/custom/kubeconfig")
    monkeypatch.setattr("kp.agent.sandbox.kind_kubeconfig_path", lambda cluster=None: kubeconfig)
    assert use_kind_kubeconfig() == "/custom/kubeconfig"
    assert os.environ["KUBECONFIG"] == "/custom/kubeconfig"


def test_k8s_mode_does_not_fall_back(monkeypatch):
    import kubernetes.config

    def boom():
        raise RuntimeError("no cluster")

    monkeypatch.setattr(kubernetes.config, "load_kube_config", boom)
    with pytest.raises(SandboxUnavailable):
        K8sSandbox("550e8400-e29b-41d4-a716-446655440000").provision()


def test_factory_mounts_selected_skills_on_the_kubernetes_backend(monkeypatch):
    captured = {}

    def fake_create_deep_agent(**kwargs):
        captured.update(kwargs)
        return object()

    class FakeAdapter:
        def __init__(self, target):
            self.target = target

        async def list_tools(self):
            return []

    import asyncio

    import langchain.mcp as mcp_mod

    monkeypatch.setattr(mcp_mod, "MCPAdapter", FakeAdapter)
    monkeypatch.setattr("kp.agent.factory.create_deep_agent", fake_create_deep_agent)
    remote = _Remote()
    created = _install_k8s(monkeypatch, remote)
    from kp.agent.factory import create_session_agent

    session_id = "22222222-2222-2222-2222-222222222222"
    asyncio.run(
        create_session_agent(
            session_id,
            ["complaint-incidents"],
            "Answer from the bundle.",
        )
    )
    assert captured["backend"].filesystem == "disk"
    assert isinstance(captured["backend"]._sandbox, K8sSandbox)
    assert captured["skills"] == ["/skills/functions/engineer/"]
    assert "/skills/functions/ceo/" not in captured["skills"]
    assert created["kwargs"]["namespace"] == namespace_for(session_id)
    assert created["kwargs"]["claim_name"] == claim_name_for(session_id)
    assert captured["checkpointer"] is not None


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


class _Message:
    def __init__(self, content: str) -> None:
        self.content = content


def test_knowledge_ask_fails_when_the_cluster_is_not_configured(client, monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "test-key")
    get_settings.cache_clear()
    monkeypatch.setattr("kp.agent.skills.select_skills", lambda question, role: ["complaint-incidents"])
    monkeypatch.setattr("kubernetes.config.load_kube_config", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("no cluster")))
    subprocess_calls = _block_subprocess(monkeypatch)
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
        assert response.status_code == 503, response.text
        assert "Kubernetes sandbox is required" in response.json()["detail"]
        assert subprocess_calls["subprocess"] is False
    finally:
        get_settings.cache_clear()


def test_knowledge_ask_executes_in_the_kubernetes_sandbox(client, monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "test-key")
    get_settings.cache_clear()
    remote = _Remote()
    created = _install_k8s(monkeypatch, remote)
    subprocess_calls = _block_subprocess(monkeypatch)
    monkeypatch.setattr("kp.agent.skills.select_skills", lambda question, role: ["complaint-incidents"])
    _stub_router(monkeypatch)

    class FakeAdapter:
        def __init__(self, target):
            self.target = target

        async def list_tools(self):
            return []

    captured = {}

    def fake_create_deep_agent(**kwargs):
        captured.update(kwargs)

        class Agent:
            async def ainvoke(self, *_args, **_kwargs):
                kwargs["backend"].execute("printf synced > workspace/from-sandbox.txt")
                return {"messages": [_Message(json.dumps({"answer": "sandbox-answer", "citations": []}))]}

        return Agent()

    monkeypatch.setattr("langchain.mcp.MCPAdapter", FakeAdapter)
    monkeypatch.setattr("kp.agent.factory.create_deep_agent", fake_create_deep_agent)
    try:
        session_id = login(client, "ceo")["session_id"]
        note = session_dir(session_id) / "workspace" / "note.txt"
        note.write_text("hi")
        response = client.post(
            f"/v1/sessions/{session_id}/ask",
            json={
                "query": "What are the top customer complaints and recommended solutions?",
                "channel": "web",
                "router": "llm",
            },
        )
        assert response.status_code == 200, response.text
        assert response.json()["answer"] == "sandbox-answer"
        assert captured["skills"] == ["/skills/functions/engineer/"]
        assert created["client"] is True
        assert created["kwargs"]["namespace"] == namespace_for(session_id)
        assert created["kwargs"]["claim_name"] == claim_name_for(session_id)
        upload_at = next(index for index, event in enumerate(remote.events) if event[0] == "upload")
        command_at = next(
            index
            for index, event in enumerate(remote.events)
            if event[0] == "execute" and "from-sandbox.txt" in event[1]
        )
        assert upload_at < command_at
        assert "/workspace/note.txt" in remote.events[upload_at][1]
        assert (session_dir(session_id) / "workspace" / "from-sandbox.txt").read_text() == "synced"
        assert subprocess_calls["subprocess"] is False
        assert isinstance(captured["backend"]._sandbox, K8sSandbox)
    finally:
        get_settings.cache_clear()
