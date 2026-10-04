from contextlib import asynccontextmanager
import logging

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import text

from app.api.auth_api import router as auth_router
from app.api.student_api import router as student_router
from app.database import SessionLocal, engine, init_db
from app.models.models import User
from app.services.auth_service import get_current_user
from app.services.rag_service import (
    EmbeddingModelUnavailableError,
    EmptyCandidateIndexError,
    RAGService,
    VectorStoreUnavailableError,
)

logger = logging.getLogger("rag_api")
logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    yield


app = FastAPI(title="RAG Candidate Search", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "https://agentic-ai-recruitment-manager.vercel.app",
        "https://agenticairecruitmentmanager-two.vercel.app",
    ],
    allow_origin_regex=r"https://agenticairecruitmentmanager(?:-[a-z0-9-]+)?\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth_router)
app.include_router(student_router)

rag = RAGService()


@app.get("/health")
def health_check():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception as exc:
        logger.exception("Database health check failed")
        raise HTTPException(status_code=503, detail="Database is unavailable.") from exc
    return {"status": "ok"}


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=15000)
    top_k: int = Field(default=5, ge=1, le=20)


@app.post("/rag/search")
def rag_search(req: SearchRequest):
    if not req.query or not req.query.strip():
        raise HTTPException(status_code=400, detail="Query must be a non-empty string")

    logger.info("Received RAG search request")
    try:
        search_result = rag.search_candidates(req.query, top_k=req.top_k)
    except EmptyCandidateIndexError as exc:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "empty_candidate_index",
                "message": "No candidate resumes are indexed. Add resumes and rebuild the candidate index.",
            },
        ) from exc
    except VectorStoreUnavailableError as exc:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "vector_store_unavailable",
                "message": "The candidate vector database is unavailable. Retry the search.",
            },
        ) from exc
    except EmbeddingModelUnavailableError as exc:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "embedding_model_unavailable",
                "message": "The candidate search model is unavailable. Retry the search.",
            },
        ) from exc
    except Exception as exc:
        logger.exception("Failed retrieving candidates")
        raise HTTPException(
            status_code=500,
            detail={
                "code": "candidate_search_failed",
                "message": "Candidate search failed. Check the API logs and retry.",
            },
        ) from exc

    return {
        "query": req.query,
        "candidate_count": search_result["candidate_count"],
        "results": search_result["results"],
    }


@app.post("/rag/rebuild")
def rag_rebuild(current_user: User = Depends(get_current_user)):
    logger.info("Rebuilding Chroma index from DB for user_id=%s", current_user.id)
    db = SessionLocal()
    try:
        stats = rag.build_index_from_db(db)
        return {"status": "ok", "indexed": stats.get("indexed", 0), "user": {"id": current_user.id, "email": current_user.email}}
    except Exception as e:
        logger.exception("Index rebuild failed: %s", e)
        raise HTTPException(status_code=500, detail="Index rebuild failed")
    finally:
        db.close()
