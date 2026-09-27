"""Session filesystem. /skills stays shared and read-only. The default store is local disk."""

from __future__ import annotations

import shutil
from pathlib import Path

from deepagents.backends import CompositeBackend
from deepagents.backends.filesystem import FilesystemBackend
from deepagents.backends.protocol import (
    BackendProtocol,
    DeleteResult,
    EditResult,
    FileDownloadResponse,
    FileUploadResponse,
    SandboxBackendProtocol,
    WriteResult,
)

from kp.agent.sandbox import K8sSandbox
from kp.auth import session_dir
from kp.config import get_settings


class ReadOnlyBackend(BackendProtocol):
    def __init__(self, inner: BackendProtocol) -> None:
        self._inner = inner

    def ls(self, path: str):
        return self._inner.ls(path)

    def read(self, file_path: str, offset: int = 0, limit: int = 2000):
        return self._inner.read(file_path, offset=offset, limit=limit)

    def grep(self, pattern: str, path: str | None = None, glob: str | None = None, *, max_count: int | None = None, context_lines: int = 0):
        return self._inner.grep(pattern, path, glob, max_count=max_count, context_lines=context_lines)

    def glob(self, pattern: str, path: str | None = None):
        return self._inner.glob(pattern, path)

    def download_files(self, paths: list[str]):
        return self._inner.download_files(paths)

    def write(self, file_path: str, content: str) -> WriteResult:
        return WriteResult(error="skills are read-only")

    def edit(self, file_path: str, old_string: str, new_string: str, replace_all: bool = False) -> EditResult:
        return EditResult(error="skills are read-only")

    def upload_files(self, files: list[tuple[str, bytes]]) -> list[FileUploadResponse]:
        return [FileUploadResponse(path=path, error="permission_denied") for path, _ in files]

    def delete(self, file_path: str) -> DeleteResult:
        return DeleteResult(error="skills are read-only")


class SessionBackend(SandboxBackendProtocol):
    """Routes file tools to the selected store and shell commands to the sandbox."""

    def __init__(self, session_id: str, inner: BackendProtocol, sandbox, filesystem: str) -> None:
        self.session_id = session_id
        self.filesystem = filesystem
        self._inner = inner
        self._sandbox = sandbox

    @property
    def id(self) -> str:
        return f"sess-{self.session_id}"

    def prepare(self) -> None:
        """Provision the Kubernetes sandbox before the agent runs a task."""
        self._sandbox.provision()

    def execute(self, command: str, *, timeout: int | None = None):
        return self._sandbox.execute(command, timeout=timeout)

    def ls(self, path: str):
        return self._inner.ls(path)

    def read(self, file_path: str, offset: int = 0, limit: int = 2000):
        return self._inner.read(file_path, offset=offset, limit=limit)

    def write(self, file_path: str, content: str):
        return self._inner.write(file_path, content)

    def edit(self, file_path: str, old_string: str, new_string: str, replace_all: bool = False):
        return self._inner.edit(file_path, old_string, new_string, replace_all=replace_all)

    def grep(self, pattern: str, path: str | None = None, glob: str | None = None, *, max_count: int | None = None, context_lines: int = 0):
        return self._inner.grep(pattern, path, glob, max_count=max_count, context_lines=context_lines)

    def glob(self, pattern: str, path: str | None = None):
        return self._inner.glob(pattern, path)

    def download_files(self, paths: list[str]) -> list[FileDownloadResponse]:
        return self._inner.download_files(paths)

    def upload_files(self, files: list[tuple[str, bytes]]) -> list[FileUploadResponse]:
        return self._inner.upload_files(files)

    def delete(self, file_path: str) -> DeleteResult:
        return self._inner.delete(file_path)


def skill_view(session_id: str, skill_names: list[str]) -> Path:
    settings = get_settings()
    root = settings.workspace_root / ".skill-views" / session_id
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True)
    for name in skill_names:
        src = settings.skills_root / name
        if not src.is_dir():
            continue
        dest = root / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(src, dest)
    return root


def build_session_backend(session_id: str, skill_names: list[str]) -> SessionBackend:
    settings = get_settings()
    root = session_dir(session_id)
    skills = ReadOnlyBackend(FilesystemBackend(root_dir=str(skill_view(session_id, skill_names)), virtual_mode=True))
    if settings.filesystem == "s3":
        from kp.agent.s3_backend import S3Backend

        default = S3Backend(
            bucket=settings.s3_bucket,
            prefix=f"tenants/{settings.tenant_id}/sessions/{session_id}",
            settings=settings,
        )
        filesystem = "s3"
    else:
        default = FilesystemBackend(root_dir=str(root), virtual_mode=True)
        filesystem = "disk"
    inner = CompositeBackend(default=default, routes={"/skills/": skills})
    return SessionBackend(session_id, inner, K8sSandbox(session_id), filesystem)
