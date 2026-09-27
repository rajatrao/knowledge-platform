"""Session file storage. Disk is the default. S3 is used only when selected."""

from __future__ import annotations

from kp.auth import session_dir
from kp.config import Settings, get_settings


def s3_client(settings: Settings):
    import boto3
    from botocore.config import Config

    kwargs = {
        "region_name": settings.s3_region,
        "aws_access_key_id": settings.s3_access_key or None,
        "aws_secret_access_key": settings.s3_secret_key or None,
    }
    if settings.s3_endpoint_url:
        kwargs["endpoint_url"] = settings.s3_endpoint_url
        kwargs["config"] = Config(s3={"addressing_style": "path"})
    return boto3.client("s3", **kwargs)


def require_s3(settings: Settings | None = None) -> None:
    settings = settings or get_settings()
    if settings.filesystem != "s3":
        return
    if not settings.s3_bucket:
        raise RuntimeError("FILESYSTEM=s3 requires S3_BUCKET; refusing to fall back to disk")
    client = s3_client(settings)
    try:
        client.head_bucket(Bucket=settings.s3_bucket)
    except Exception as exc:
        raise RuntimeError(
            f"FILESYSTEM=s3 bucket {settings.s3_bucket!r} is not available; refusing to fall back to disk"
        ) from exc


def session_key(session_id: str, relative: str) -> str:
    settings = get_settings()
    suffix = relative.lstrip("/")
    return f"tenants/{settings.tenant_id}/sessions/{session_id}/{suffix}"


def write_session_bytes(session_id: str, relative: str, data: bytes) -> None:
    settings = get_settings()
    if settings.filesystem == "s3":
        require_s3(settings)
        s3_client(settings).put_object(Bucket=settings.s3_bucket, Key=session_key(session_id, relative), Body=data)
        return
    path = session_dir(session_id) / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def read_session_bytes(session_id: str, relative: str) -> bytes:
    settings = get_settings()
    if settings.filesystem == "s3":
        obj = s3_client(settings).get_object(Bucket=settings.s3_bucket, Key=session_key(session_id, relative))
        return obj["Body"].read()
    return (session_dir(session_id) / relative).read_bytes()
