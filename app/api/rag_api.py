from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
import logging

from app.services.rag_service import RAGService

logger = logging.getLogger("rag_api")
logging.basicConfig(level=logging.INFO)

app = FastAPI(title="RAG Candidate Search")

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

    # Attempt explanations, but don't fail if OpenAI key missing or call fails
    for item in results:
        try:
            explanation = rag.explain_candidate_match(item.get("document", ""), req.query)
            item["explanation"] = explanation
        except Exception as e:
            logger.warning("Explanation generation failed for %s: %s", item.get("id"), e)
            item["explanation"] = None

    return {"query": req.query, "results": results}


@app.post("/rag/rebuild")
def rag_rebuild():
    logger.info("Rebuilding Chroma index from DB")
    from app.database import SessionLocal

    db = SessionLocal()
    try:
        stats = rag.build_index_from_db(db)
        return {"status": "ok", "indexed": stats.get("indexed", 0)}
    except Exception as e:
        logger.exception("Index rebuild failed: %s", e)
        raise HTTPException(status_code=500, detail="Index rebuild failed")
    finally:
        db.close()
