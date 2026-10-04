import os

import pytest
from fastapi.testclient import TestClient

from app.api.rag_api import app
from app.database import Base, SessionLocal
from app.models.models import User
from app.services import auth_service


client = TestClient(app)


@pytest.fixture(autouse=True)
def use_test_jwt_secret(monkeypatch):
    monkeypatch.setattr(auth_service, "JWT_SECRET_KEY", "test-only-jwt-secret")


def override_get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides.clear()
app.dependency_overrides[None] = override_get_db


def setup_function():
    Base.metadata.create_all(bind=SessionLocal.kw['bind'])
    db = SessionLocal()
    try:
        db.query(User).delete()
        db.commit()
    finally:
        db.close()


def test_google_auth_creates_new_user_and_returns_token(monkeypatch):
    def fake_verify_google_credential(credential):
        return {
            "sub": "google-user-123",
            "email": "new.user@example.com",
            "name": "New User",
            "picture": "https://example.com/avatar.png",
        }

    monkeypatch.setattr("app.services.auth_service.verify_google_credential", fake_verify_google_credential)

    response = client.post("/auth/google", json={"credential": "fake-google-token"})
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["user"]["email"] == "new.user@example.com"
    assert "access_token" in payload
    assert payload["token_type"] == "bearer"

    db = SessionLocal()
    try:
        user = db.query(User).filter_by(email="new.user@example.com").first()
        assert user is not None
        assert user.google_id == "google-user-123"
    finally:
        db.close()


def test_google_auth_reuses_existing_user(monkeypatch):
    db = SessionLocal()
    try:
        db.add(User(google_id="google-user-123", email="existing@example.com", name="Existing User"))
        db.commit()
    finally:
        db.close()

    def fake_verify_google_credential(credential):
        return {
            "sub": "google-user-123",
            "email": "existing@example.com",
            "name": "Existing User",
            "picture": "https://example.com/avatar.png",
        }

    monkeypatch.setattr("app.services.auth_service.verify_google_credential", fake_verify_google_credential)

    response = client.post("/auth/google", json={"credential": "fake-google-token"})
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["user"]["email"] == "existing@example.com"

    db = SessionLocal()
    try:
        users = db.query(User).filter_by(google_id="google-user-123").all()
        assert len(users) == 1
    finally:
        db.close()


def test_candidate_search_works_without_auth(monkeypatch):
    from app.api import rag_api

    monkeypatch.setattr(rag_api.rag, "indexed_candidate_count", lambda: 1)
    monkeypatch.setattr(
        rag_api.rag,
        "retrieve_candidates",
        lambda query, top_k: [{
            "id": "cand_1",
            "metadata": {"name": "Jordan Lee", "email": "jordan@example.com", "id": 1},
            "document": "Python engineer with FastAPI experience.",
            "distance": 0.25,
        }],
    )
    monkeypatch.setattr(rag_api.rag, "explain_candidate_match", lambda document, query: None)

    response = client.post("/rag/search", json={"query": "Python backend engineer", "top_k": 3})
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["query"] == "Python backend engineer"
    assert payload["candidate_count"] == 1
    assert payload["results"][0]["metadata"]["name"] == "Jordan Lee"
    assert payload["results"][0]["matched_skills"] == ["Python"]
    assert payload["results"][0]["match_score"] > 0


def test_invalid_google_credential_is_rejected(monkeypatch):
    def fake_verify_google_credential(credential):
        raise ValueError("Invalid Google token")

    monkeypatch.setattr("app.services.auth_service.verify_google_credential", fake_verify_google_credential)

    response = client.post("/auth/google", json={"credential": "bad-token"})
    assert response.status_code == 401, response.text
