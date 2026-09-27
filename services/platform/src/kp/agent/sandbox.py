"""Knowledge-agent execution in a Kubernetes sandbox. There is no local subprocess fallback."""

from __future__ import annotations

import os
import re
from pathlib import Path

from deepagents.backends.protocol import ExecuteResponse

from kp.flow import event

NAMESPACE_RE = re.compile(r"[a-z0-9]([-a-z0-9]*[a-z0-9])?")
DEFAULT_KIND_CLUSTER = "knowledge"

SANDBOX_REQUIRED = (
    "A Kubernetes sandbox is required for knowledge asks. "
    "Configure a cluster, kubectl access, and a SandboxTemplate."
)


class SandboxUnavailable(RuntimeError):
    pass


def namespace_for(session_id: str) -> str:
    label = f"sess-{session_id}".lower()
    if len(label) > 63 or NAMESPACE_RE.fullmatch(label) is None:
        raise ValueError(f"namespace {label!r} is not a valid DNS label")
    return label


def claim_name_for(session_id: str) -> str:
    label = f"claim-{session_id}".lower()
    if len(label) > 63:
        raise ValueError(label)
    return label


def kind_cluster_name() -> str:
    name = os.getenv("KIND_CLUSTER", DEFAULT_KIND_CLUSTER).strip() or DEFAULT_KIND_CLUSTER
    if NAMESPACE_RE.fullmatch(name) is None:
        return DEFAULT_KIND_CLUSTER
    return name


def kind_kubeconfig_path(cluster: str | None = None) -> Path:
    """Kubeconfig written by scripts/kind-up.sh for this kind cluster."""
    name = cluster or kind_cluster_name()
    return Path.home() / ".kube" / f"kind-{name}.yaml"


def use_kind_kubeconfig() -> str | None:
    """Select the kind kubeconfig when KUBECONFIG is unset and the cluster file exists.

    An explicit KUBECONFIG is left unchanged. A missing kind file leaves KUBECONFIG
    unset so load_kube_config fails closed with no local subprocess fallback.
    """
    from kp.config import get_settings

    get_settings()
    explicit = os.environ.get("KUBECONFIG", "").strip()
    if explicit:
        return explicit
    path = kind_kubeconfig_path()
    if not path.is_file():
        return None
    os.environ["KUBECONFIG"] = str(path)
    return str(path)


def _activate_kubeconfig() -> str | None:
    """Point this process at the kind kubeconfig before the client caches a path.

    kubernetes.config reads KUBECONFIG once, at import. An API started without
    that variable would keep looking at ~/.kube/config even after we set the env.
    """
    selected = use_kind_kubeconfig()
    if not selected:
        return None
    from kubernetes.config import kube_config as kube_mod

    kube_mod.KUBE_CONFIG_DEFAULT_LOCATION = selected
    return selected


class K8sSandbox:
    """Namespace-per-session sandbox. Does not fall back to a local subprocess."""

    def __init__(self, session_id: str) -> None:
        self.session_id = session_id
        self.namespace = namespace_for(session_id)
        self._backend = None

    def execute(self, command: str, timeout: int | None = None) -> ExecuteResponse:
        backend = self.provision()
        files = self._workspace_files()
        backend.upload_files(files)
        result = backend.execute(command, timeout=timeout)
        self._pull_back(backend)
        return result

    def provision(self):
        if self._backend is None:
            event("sandbox.start", session=self.session_id, namespace=self.namespace)
            try:
                self._backend = self._connect()
            except SandboxUnavailable as exc:
                cause = exc.__cause__
                event(
                    "sandbox.failed",
                    session=self.session_id,
                    namespace=self.namespace,
                    error=type(cause).__name__ if cause else "SandboxUnavailable",
                )
                raise
            except Exception as exc:
                event("sandbox.failed", session=self.session_id, namespace=self.namespace, error=type(exc).__name__)
                raise SandboxUnavailable(SANDBOX_REQUIRED) from exc
            event("sandbox.ready", session=self.session_id, namespace=self.namespace)
        return self._backend

    def _connect(self):
        kubeconfig = _activate_kubeconfig()
        from kubernetes import config as k8s_config
        from kubernetes.client import ApiException

        try:
            k8s_config.load_kube_config(config_file=kubeconfig)
        except Exception as exc:
            raise SandboxUnavailable(SANDBOX_REQUIRED) from exc
        self._ensure_namespace()
        self._apply_guards()
        try:
            from k8s_agent_sandbox import SandboxClient
            from langchain_k8s import create_kubernetes_sandbox
        except Exception as exc:
            raise SandboxUnavailable(SANDBOX_REQUIRED) from exc
        client = SandboxClient()
        try:
            return create_kubernetes_sandbox(
                client=client,
                claim_name=claim_name_for(self.session_id),
                warmpool_name="warm",
                namespace=self.namespace,
            )
        except ApiException as exc:
            raise SandboxUnavailable(SANDBOX_REQUIRED) from exc

    def _ensure_namespace(self) -> None:
        from kubernetes import client

        core = client.CoreV1Api()
        try:
            core.read_namespace(name=self.namespace)
        except Exception:
            core.create_namespace(client.V1Namespace(metadata=client.V1ObjectMeta(name=self.namespace)))

    def _apply_guards(self) -> None:
        from pathlib import Path as FsPath

        import yaml
        from kubernetes import client, config

        config.load_kube_config(config_file=_activate_kubeconfig())
        manifest_dir = FsPath(__file__).resolve().parents[5] / "deploy" / "sandbox"
        # parents: agent, kp, src, platform, services, repo -> 5 is services? 
        # file: services/platform/src/kp/agent/sandbox.py
        # parents[0]=agent ... let me not use a fragile index. Use settings.repo_root.
        from kp.config import get_settings

        manifest_dir = get_settings().repo_root / "deploy" / "sandbox"
        text = (manifest_dir / "session-resources.yaml").read_text()
        text = text.replace("NAMESPACE", self.namespace).replace("SESSION_ID", self.session_id)
        for document in yaml.safe_load_all(text):
            if not document:
                continue
            _apply_custom(document)

    def _workspace_files(self) -> list[tuple[str, bytes]]:
        from kp.auth import session_dir

        root = session_dir(self.session_id)
        files = []
        for path in root.rglob("*"):
            if path.is_file():
                virtual = "/" + path.relative_to(root).as_posix()
                files.append((virtual, path.read_bytes()))
        return files

    def _pull_back(self, backend) -> None:
        from kp.auth import session_dir
        from kp.storage import write_session_bytes

        listing = backend.execute("find . -type f")
        root = session_dir(self.session_id)
        for line in (listing.output or "").splitlines():
            relative = line.strip().removeprefix("./")
            if not relative or relative.startswith("."):
                continue
            downloaded = backend.download_files(["/" + relative])
            if downloaded and downloaded[0].content is not None and downloaded[0].error is None:
                target = root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(downloaded[0].content)
                write_session_bytes(self.session_id, relative, downloaded[0].content)


def _already_exists(exc: BaseException) -> bool:
    return getattr(exc, "status", None) == 409


def _apply_custom(document: dict) -> None:
    from kubernetes import client

    group, _, version = document["apiVersion"].partition("/")
    kind = document["kind"]
    namespace = document.get("metadata", {}).get("namespace")
    plural = {
        "ResourceQuota": None,
        "NetworkPolicy": None,
        "SandboxTemplate": "sandboxtemplates",
        "SandboxWarmPool": "sandboxwarmpools",
        "SandboxClaim": "sandboxclaims",
    }[kind]
    if kind == "ResourceQuota":
        try:
            client.CoreV1Api().create_namespaced_resource_quota(namespace=namespace, body=_quota(document))
        except Exception as exc:
            if not _already_exists(exc):
                raise
        return
    if kind == "NetworkPolicy":
        try:
            client.NetworkingV1Api().create_namespaced_network_policy(namespace=namespace, body=_netpol(document))
        except Exception as exc:
            if not _already_exists(exc):
                raise
        return
    api = client.CustomObjectsApi()
    try:
        api.create_namespaced_custom_object(
            group=group,
            version=version,
            namespace=namespace,
            plural=plural,
            body=document,
        )
    except Exception as exc:
        if not _already_exists(exc):
            raise
        if kind != "SandboxTemplate":
            return
        name = document["metadata"]["name"]
        existing = api.get_namespaced_custom_object(
            group=group,
            version=version,
            namespace=namespace,
            plural=plural,
            name=name,
        )
        api.replace_namespaced_custom_object(
            group=group,
            version=version,
            namespace=namespace,
            plural=plural,
            name=name,
            body={
                "apiVersion": document["apiVersion"],
                "kind": kind,
                "metadata": {
                    "name": name,
                    "namespace": namespace,
                    "resourceVersion": existing["metadata"]["resourceVersion"],
                },
                "spec": document["spec"],
            },
        )


def _quota(document: dict):
    from kubernetes import client

    hard = document["spec"]["hard"]
    return client.V1ResourceQuota(
        metadata=client.V1ObjectMeta(name=document["metadata"]["name"], namespace=document["metadata"]["namespace"]),
        spec=client.V1ResourceQuotaSpec(hard=hard),
    )


def _netpol(document: dict):
    from kubernetes import client

    return client.V1NetworkPolicy(
        metadata=client.V1ObjectMeta(name=document["metadata"]["name"], namespace=document["metadata"]["namespace"]),
        spec=client.V1NetworkPolicySpec(
            pod_selector=client.V1LabelSelector(match_labels={}),
            policy_types=["Ingress", "Egress"],
        ),
    )
