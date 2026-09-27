"""Runtime configuration. FILESYSTEM=disk is the default virtual filesystem."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[4]


def _flag(name: str, default: str, allowed: set[str]) -> str:
    value = os.getenv(name, default).strip().lower()
    if value not in allowed:
        raise RuntimeError(f"{name} must be one of {sorted(allowed)}, got {value!r}")
    return value


@dataclass(frozen=True)
class Settings:
    database_url: str
    temporal_address: str
    temporal_namespace: str
    onboarding_runner: str
    filesystem: str
    sandbox_runtime_class: str
    s3_bucket: str
    s3_endpoint_url: str
    s3_access_key: str
    s3_secret_key: str
    s3_region: str
    llm_api_key: str
    llm_model: str
    llm_base_url: str
    llm_provider: str
    ollama_base_url: str
    ollama_model: str
    jev_api_key: str
    jev_base_url: str
    jev_model: str
    cors_origins: tuple[str, ...]
    cookie_secure: bool
    tenant_id: str
    workspace_root: Path
    skills_root: Path
    corpus_dir: Path
    repo_root: Path
    seed_passwords: dict[str, str]


@lru_cache
def get_settings() -> Settings:
    load_dotenv(REPO_ROOT / ".env", override=False)
    filesystem = _flag("FILESYSTEM", "disk", {"disk", "s3"})
    origins = tuple(
        item.strip()
        for item in os.getenv(
            "CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
        ).split(",")
        if item.strip()
    )
    return Settings(
        database_url=os.getenv(
            "DATABASE_URL", "postgresql+psycopg://kp:kp@localhost:5432/knowledge"
        ),
        temporal_address=os.getenv("TEMPORAL_ADDRESS", "localhost:7233"),
        temporal_namespace=os.getenv("TEMPORAL_NAMESPACE", "default"),
        onboarding_runner=os.getenv("ONBOARDING_RUNNER", "temporal").strip().lower(),
        filesystem=filesystem,
        sandbox_runtime_class=os.getenv("SANDBOX_RUNTIME_CLASS", "gvisor").strip(),
        s3_bucket=os.getenv("S3_BUCKET", "").strip(),
        s3_endpoint_url=os.getenv("S3_ENDPOINT_URL", "").strip(),
        s3_access_key=os.getenv("S3_ACCESS_KEY", "").strip(),
        s3_secret_key=os.getenv("S3_SECRET_KEY", "").strip(),
        s3_region=os.getenv("S3_REGION", "us-east-1").strip() or "us-east-1",
        llm_api_key=os.getenv("LLM_API_KEY", "").strip(),
        llm_model=os.getenv("LLM_MODEL", "gpt-4o-mini").strip() or "gpt-4o-mini",
        llm_base_url=os.getenv("LLM_BASE_URL", "").strip(),
        llm_provider=os.getenv("LLM_PROVIDER", "ollama").strip().lower() or "ollama",
        ollama_base_url=os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434/v1").strip()
        or "http://127.0.0.1:11434/v1",
        ollama_model=os.getenv("OLLAMA_MODEL", "qwen3:8b").strip() or "qwen3:8b",
        jev_api_key=os.getenv("JEV_API_KEY", "").strip(),
        jev_base_url=os.getenv("JEV_BASE_URL", "http://127.0.0.1:8081").strip()
        or "http://127.0.0.1:8081",
        jev_model=os.getenv("JEV_MODEL", "laya-1.0").strip() or "laya-1.0",
        cors_origins=origins,
        cookie_secure=os.getenv("COOKIE_SECURE", "false").strip().lower() in {"1", "true", "yes"},
        tenant_id=os.getenv("TENANT_ID", "base").strip() or "base",
        workspace_root=Path(os.getenv("WORKSPACE_ROOT", str(REPO_ROOT / "data" / "workspaces"))),
        skills_root=Path(os.getenv("SKILLS_ROOT", str(REPO_ROOT / "skills"))),
        corpus_dir=Path(os.getenv("CORPUS_DIR", str(REPO_ROOT / "data" / "corpus"))),
        repo_root=REPO_ROOT,
        seed_passwords={
            "ceo": os.getenv("KP_SEED_PASSWORD_CEO", "base-ceo-local"),
            "operations_manager": os.getenv(
                "KP_SEED_PASSWORD_OPERATIONS_MANAGER", "base-ops-local"
            ),
            "engineer": os.getenv("KP_SEED_PASSWORD_ENGINEER", "base-eng-local"),
            "marketing": os.getenv("KP_SEED_PASSWORD_MARKETING", "base-mkt-local"),
        },
    )
