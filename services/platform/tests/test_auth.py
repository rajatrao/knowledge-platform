from kp.db import SessionLocal
from kp.models import User
from tests.conftest import login


def test_login_logout_and_resume(client):
    failed = client.post("/v1/auth/login", json={"username": "ceo", "password": "nope"})
    assert failed.status_code == 401
    assert "kp_auth" not in failed.cookies

    first = login(client, "ceo")
    assert client.cookies.get("kp_auth")
    me = client.get("/v1/auth/me")
    assert me.status_code == 200
    assert me.json()["session_id"] == first["session_id"]
    assert me.json()["persona"] == "ceo"

    created = client.post("/v1/sessions")
    assert created.status_code == 200
    new_id = created.json()["id"]
    assert new_id != first["session_id"]

    logged_out = client.post("/v1/auth/logout")
    assert logged_out.status_code == 204
    assert client.post("/v1/sessions").status_code == 401
    assert client.post(
        f"/v1/sessions/{new_id}/ask",
        json={"query": "hello", "channel": "web", "router": "llm"},
    ).status_code == 401

    resumed = login(client, "ceo")
    assert resumed["session_id"] == new_id


def test_owner_can_delete_a_chat_session(client):
    login(client, "ceo")
    created = client.post("/v1/sessions")
    session_id = created.json()["id"]
    deleted = client.delete(f"/v1/sessions/{session_id}")
    assert deleted.status_code == 204
    assert client.get(f"/v1/sessions/{session_id}").status_code == 404
    ids = [row["id"] for row in client.get("/v1/sessions").json()["sessions"]]
    assert session_id not in ids


def test_session_routes_require_auth_and_ownership(client):
    from fastapi.testclient import TestClient

    from kp.api import create_app

    bare = TestClient(create_app())
    assert bare.post("/v1/sessions").status_code == 401
    ceo = login(client, "ceo")
    with TestClient(create_app()) as other:
        engineer = login(other, "engineer")
        assert other.get(f"/v1/sessions/{ceo['session_id']}").status_code == 404
        assert other.delete(f"/v1/sessions/{ceo['session_id']}").status_code == 404
        assert engineer["session_id"] != ceo["session_id"]

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == "ceo").one()
        assert user.password_hash.startswith("$2")
        assert "base-ceo-local" not in user.password_hash
    finally:
        db.close()
