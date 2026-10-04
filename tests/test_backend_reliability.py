from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.api.rag_api import app
from app.services import rag_service


client = TestClient(app)


@pytest.mark.parametrize("top_k", [0, -1, 21])
def test_rag_search_rejects_out_of_range_top_k(top_k):
    response = client.post("/rag/search", json={"query": "backend engineer", "top_k": top_k})

    assert response.status_code == 422


def test_rag_service_defers_model_and_vector_store_initialization(tmp_path):
    service = rag_service.RAGService(str(tmp_path))

    assert service.embedder is None
    assert service.client is None
    assert service.collection is None


def test_startup_initializes_database_and_health_check_succeeds():
    with TestClient(app) as startup_client:
        response = startup_client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_student_analysis_cors_allows_deployed_site():
    response = client.options(
        "/student/analyze",
        headers={
            "Origin": "https://agenticairecruitmentmanager-two.vercel.app",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == (
        "https://agenticairecruitmentmanager-two.vercel.app"
    )


def test_candidate_explanation_uses_current_openai_client(monkeypatch):
    captured = {}

    class FakeOpenAI:
        def __init__(self, api_key):
            captured["api_key"] = api_key
            self.chat = SimpleNamespace(
                completions=SimpleNamespace(
                    create=lambda **kwargs: SimpleNamespace(
                        choices=[
                            SimpleNamespace(
                                message=SimpleNamespace(content="A strong match.")
                            )
                        ]
                    )
                )
            )

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(rag_service, "OpenAI", FakeOpenAI)

    result = rag_service.RAGService().explain_candidate_match(
        "Python backend experience", "Build Python APIs"
    )

    assert result == "A strong match."
    assert captured["api_key"] == "test-key"


def test_match_score_exposes_skill_evidence_and_missing_terms():
    candidate = {
        "metadata": {"skills": "Python, FastAPI"},
        "document": "Built backend APIs using Python and FastAPI.",
        "distance": 0.2,
    }

    scored = rag_service.score_candidate_match(
        candidate, "Build Python and FastAPI services with Docker."
    )

    assert scored["matched_skills"] == ["Python", "FastAPI"]
    assert scored["missing_skills"] == ["Docker"]
    assert scored["score_breakdown"]["semantic_similarity"] == 90
    assert scored["match_score"] == 83
    assert scored["why_shortlisted"]


def test_search_reranks_semantic_candidates_using_resume_skill_evidence(tmp_path, monkeypatch):
    service = rag_service.RAGService(str(tmp_path))
    requested_pool_sizes = []
    candidates = [
        {
            "metadata": {"name": "Semantic only"},
            "document": "Relevant backend work.",
            "distance": 0.1,
        },
        {
            "metadata": {"name": "Skill evidence", "skills": "Python, FastAPI"},
            "document": "Built Python services with FastAPI.",
            "distance": 0.3,
        },
    ]
    monkeypatch.setattr(service, "indexed_candidate_count", lambda: 30)
    monkeypatch.setattr(
        service,
        "retrieve_candidates",
        lambda query, top_k: requested_pool_sizes.append(top_k) or candidates,
    )

    result = service.search_candidates("Python FastAPI", top_k=1)

    assert requested_pool_sizes == [5]
    assert result["candidate_count"] == 30
    assert result["results"][0]["metadata"]["name"] == "Skill evidence"


def test_search_reports_empty_index_as_actionable_unavailable_state(monkeypatch):
    from app.api import rag_api

    monkeypatch.setattr(rag_api.rag, "indexed_candidate_count", lambda: 0)

    response = client.post("/rag/search", json={"query": "Python engineer"})

    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "empty_candidate_index"


def test_search_reports_vector_store_failure_with_retryable_code(monkeypatch):
    from app.api import rag_api

    def fail_count():
        raise rag_service.VectorStoreUnavailableError("offline")

    monkeypatch.setattr(rag_api.rag, "indexed_candidate_count", fail_count)

    response = client.post("/rag/search", json={"query": "Python engineer"})

    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "vector_store_unavailable"
