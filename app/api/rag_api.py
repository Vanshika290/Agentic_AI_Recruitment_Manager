from typing import Optional
import logging

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.api.auth_api import router as auth_router
from app.database import SessionLocal
from app.models.models import User
from app.services.auth_service import get_current_user
from app.services.rag_service import RAGService

logger = logging.getLogger("rag_api")
logging.basicConfig(level=logging.INFO)

app = FastAPI(title="RAG Candidate Search")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth_router)

rag = RAGService()


class SearchRequest(BaseModel):
    query: str
    top_k: Optional[int] = 5


@app.post("/rag/search")
def rag_search(req: SearchRequest):
    if not req.query or not req.query.strip():
        raise HTTPException(status_code=400, detail="Query must be a non-empty string")

    logger.info("Received RAG search request: %s", req.query)
    try:
        results = rag.retrieve_candidates(req.query, top_k=req.top_k)
    except Exception as e:
        logger.exception("Failed retrieving candidates: %s", e)
        raise HTTPException(status_code=500, detail="Retrieval failed")

    for item in results:
        try:
            explanation = rag.explain_candidate_match(item.get("document", ""), req.query)
            item["explanation"] = explanation
        except Exception as e:
            logger.warning("Explanation generation failed for %s: %s", item.get("id"), e)
            item["explanation"] = None

    return {"query": req.query, "results": results}


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
