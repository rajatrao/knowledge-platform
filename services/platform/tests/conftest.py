import os

os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://kp:kp@localhost:5432/knowledge_test")
os.environ["ONBOARDING_RUNNER"] = "memory"
os.environ["FILESYSTEM"] = "disk"
os.environ["LLM_API_KEY"] = ""
os.environ["JEV_API_KEY"] = ""
# Pin the cloud provider so existing asks stay on the deterministic router.
# Production defaults to Ollama; tests that cover it set LLM_PROVIDER=ollama.
os.environ["LLM_PROVIDER"] = "openai"
os.environ["KP_SEED_PASSWORD_CEO"] = "base-ceo-local"
os.environ["KP_SEED_PASSWORD_OPERATIONS_MANAGER"] = "base-ops-local"
os.environ["KP_SEED_PASSWORD_ENGINEER"] = "base-eng-local"
os.environ["KP_SEED_PASSWORD_MARKETING"] = "base-mkt-local"

import pytest

PASSWORDS = {
    "ceo": "base-ceo-local",
    "operations_manager": "base-ops-local",
    "engineer": "base-eng-local",
    "marketing": "base-mkt-local",
}


@pytest.fixture(scope="session", autouse=True)
def database():
    import psycopg

    from kp.config import get_settings
    from kp.db import SessionLocal, ensure_schema, reset_engine
    from kp.seed import seed_all

    conn = psycopg.connect("postgresql://kp:kp@localhost:5432/knowledge", autocommit=True)
    if conn.execute("SELECT 1 FROM pg_database WHERE datname = 'knowledge_test'").fetchone() is None:
        conn.execute("CREATE DATABASE knowledge_test")
    conn.close()
    get_settings.cache_clear()
    reset_engine()
    ensure_schema()
    db = SessionLocal()
    try:
        seed_all(db)
        db.commit()
    finally:
        db.close()
    yield


@pytest.fixture(autouse=True)
def clean_runtime():
    from kp.config import get_settings

    get_settings.cache_clear()
    yield
    from sqlalchemy import delete

    from kp.db import SessionLocal
    from kp.models import Artifact, AuthSession, CustomerRecord, DirectoryRecord, KnowledgeSession, ManagerNotification, Turn

    db = SessionLocal()
    try:
        for model in (Turn, Artifact, KnowledgeSession, AuthSession, ManagerNotification, DirectoryRecord, CustomerRecord):
            db.execute(delete(model))
        db.commit()
    finally:
        db.close()
    get_settings.cache_clear()


@pytest.fixture
def client(database):
    from fastapi.testclient import TestClient

    from kp.api import create_app

    with TestClient(create_app()) as test_client:
        yield test_client


@pytest.fixture
def inject_skill_selector(monkeypatch):
    """Stand in for the LLM selector. Production code is unchanged."""

    def _select(_question, _role):
        return ["base-power-orientation"]

    monkeypatch.setattr("kp.agent.skills.select_skills", _select)


def login(client, username: str):
    response = client.post(
        "/v1/auth/login",
        json={"username": username, "password": PASSWORDS[username]},
    )
    assert response.status_code == 200, response.text
    return response.json()
