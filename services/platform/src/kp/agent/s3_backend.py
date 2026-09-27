"""Optional S3 backend. Constructing it requires a reachable bucket."""

from __future__ import annotations

import fnmatch
from datetime import datetime, timezone

from deepagents.backends.protocol import (
    BackendProtocol,
    DeleteResult,
    EditResult,
    FileDownloadResponse,
    FileUploadResponse,
    GlobResult,
    GrepMatch,
    GrepResult,
    LsResult,
    WriteResult,
)
from deepagents.backends.utils import perform_string_replacement, slice_read_response

from kp.storage import require_s3, s3_client


class S3Backend(BackendProtocol):
    def __init__(self, *, bucket: str, prefix: str, settings=None) -> None:
        if settings is not None:
            require_s3(settings)
        elif not bucket:
            raise RuntimeError("FILESYSTEM=s3 requires S3_BUCKET; refusing to fall back to disk")
        self.bucket = bucket
        self.prefix = prefix.strip("/") + "/"
        self.client = s3_client(settings) if settings is not None else s3_client(__import__("kp.config", fromlist=["get_settings"]).get_settings())

    def _key(self, path: str) -> str:
        relative = (path or "/").lstrip("/")
        if any(part == ".." for part in relative.split("/")):
            raise ValueError("invalid path")
        return self.prefix + relative

    def _virtual(self, key: str) -> str:
        relative = key[len(self.prefix) :] if key.startswith(self.prefix) else key
        return "/" + relative

    def write(self, file_path: str, content: str) -> WriteResult:
        try:
            self.client.put_object(Bucket=self.bucket, Key=self._key(file_path), Body=content.encode())
        except Exception as exc:
            return WriteResult(error=f"Error writing file '{file_path}': {exc}")
        return WriteResult(path=file_path)

    def read(self, file_path: str, offset: int = 0, limit: int = 2000):
        try:
            obj = self.client.get_object(Bucket=self.bucket, Key=self._key(file_path))
            content = obj["Body"].read().decode()
        except Exception as exc:
            from deepagents.backends.protocol import ReadResult

            return ReadResult(error=f"Error reading file '{file_path}': {exc}")
        return slice_read_response({"content": content, "encoding": "utf-8"}, offset, limit)

    def edit(self, file_path: str, old_string: str, new_string: str, replace_all: bool = False) -> EditResult:
        current = self.read(file_path, offset=0, limit=100000)
        if current.error or not current.file_data:
            return EditResult(error=current.error or "File not found")
        replaced = perform_string_replacement(current.file_data["content"], old_string, new_string, replace_all)
        if isinstance(replaced, str):
            return EditResult(error=replaced)
        content, occurrences = replaced
        written = self.write(file_path, content)
        if written.error:
            return EditResult(error=written.error)
        return EditResult(path=file_path, occurrences=occurrences)

    def ls(self, path: str) -> LsResult:
        prefix = self._key(path)
        if prefix and not prefix.endswith("/"):
            prefix += "/"
        if path in {"", "/"}:
            prefix = self.prefix
        try:
            response = self.client.list_objects_v2(Bucket=self.bucket, Prefix=prefix, Delimiter="/")
        except Exception as exc:
            return LsResult(error=str(exc))
        entries = []
        for item in response.get("CommonPrefixes") or []:
            entries.append({"path": self._virtual(item["Prefix"].rstrip("/")), "is_dir": True})
        for item in response.get("Contents") or []:
            if item["Key"].endswith("/"):
                continue
            entries.append(
                {
                    "path": self._virtual(item["Key"]),
                    "is_dir": False,
                    "size": item.get("Size", 0),
                    "modified_at": (item.get("LastModified") or datetime.now(timezone.utc)).isoformat(),
                }
            )
        return LsResult(entries=entries)

    def glob(self, pattern: str, path: str | None = None) -> GlobResult:
        listed = self._all_keys()
        matches = []
        for key in listed:
            virtual = self._virtual(key)
            if fnmatch.fnmatch(virtual, pattern) or fnmatch.fnmatch(virtual.lstrip("/"), pattern.lstrip("/")):
                matches.append({"path": virtual, "is_dir": False})
        return GlobResult(matches=matches)

    def grep(self, pattern: str, path: str | None = None, glob: str | None = None, *, max_count: int | None = None, context_lines: int = 0) -> GrepResult:
        matches: list[GrepMatch] = []
        for key in self._all_keys():
            virtual = self._virtual(key)
            if path and path not in {"/", ""} and not virtual.startswith(path.rstrip("/")):
                continue
            if glob and not fnmatch.fnmatch(virtual, glob):
                continue
            body = self.client.get_object(Bucket=self.bucket, Key=key)["Body"].read().decode(errors="replace")
            for number, line in enumerate(body.splitlines(), start=1):
                if pattern in line:
                    matches.append({"path": virtual, "line": number, "text": line})
                    if max_count is not None and len(matches) >= max_count:
                        return GrepResult(matches=matches, truncated=True)
        return GrepResult(matches=matches)

    def delete(self, file_path: str) -> DeleteResult:
        try:
            self.client.delete_object(Bucket=self.bucket, Key=self._key(file_path))
        except Exception as exc:
            return DeleteResult(error=str(exc))
        return DeleteResult(path=file_path)

    def upload_files(self, files: list[tuple[str, bytes]]) -> list[FileUploadResponse]:
        results = []
        for path, content in files:
            try:
                self.client.put_object(Bucket=self.bucket, Key=self._key(path), Body=content)
                results.append(FileUploadResponse(path=path, error=None))
            except Exception as exc:
                results.append(FileUploadResponse(path=path, error=str(exc)))
        return results

    def download_files(self, paths: list[str]) -> list[FileDownloadResponse]:
        results = []
        for path in paths:
            try:
                obj = self.client.get_object(Bucket=self.bucket, Key=self._key(path))
                results.append(FileDownloadResponse(path=path, content=obj["Body"].read(), error=None))
            except Exception as exc:
                results.append(FileDownloadResponse(path=path, content=None, error=str(exc)))
        return results

    def _all_keys(self) -> list[str]:
        keys = []
        token = None
        while True:
            kwargs = {"Bucket": self.bucket, "Prefix": self.prefix}
            if token:
                kwargs["ContinuationToken"] = token
            response = self.client.list_objects_v2(**kwargs)
            keys.extend(item["Key"] for item in response.get("Contents") or [] if not item["Key"].endswith("/"))
            if not response.get("IsTruncated"):
                break
            token = response.get("NextContinuationToken")
        return keys
