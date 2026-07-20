import os
from typing import List, Dict, Any

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer

import openai

from app.models.models import Candidate
from sqlalchemy.orm import Session
import logging

logger = logging.getLogger("rag_service")



CHROMA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "chroma_db")
MODEL_NAME = "all-MiniLM-L6-v2"


class RAGService:
    def __init__(self, persist_directory: str = CHROMA_DIR):
        self.persist_directory = persist_directory
        # Use modern Chroma Settings: persist directory + persistent flag
        self.client = chromadb.Client(Settings(persist_directory=self.persist_directory, is_persistent=True))
        self.collection = self.client.get_or_create_collection("resumes")
        self.embedder = SentenceTransformer(MODEL_NAME)

    def _embed_texts(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        try:
            embs = self.embedder.encode(texts, convert_to_numpy=True)
        except Exception as e:
            logger.exception("Embedding failure: %s", e)
            raise
        # ensure lists
        return [e.tolist() for e in embs]

    def build_index_from_db(self, db: Session, batch_size: int = 64) -> Dict[str, Any]:
        """Read all candidates from the DB and (re)build the Chroma collection."""
        candidates = db.query(Candidate).all()
        ids = [f"cand_{c.id}" for c in candidates]
        documents = [ (c.resume_text or "") for c in candidates]
        metadatas = [{"name": c.name, "email": c.email, "id": c.id} for c in candidates]

        # clear existing collection
        try:
            # remove all existing docs
            self.collection.delete()
        except Exception:
            # some backends may not support delete without args
            pass

        embeddings = self._embed_texts(documents)
        if embeddings:
            self.collection.add(ids=ids, metadatas=metadatas, documents=documents, embeddings=embeddings)

        # persist is handled by the client settings; return stats
        return {"indexed": len(ids)}

    def retrieve_candidates(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Retrieve top-k matching candidates for a job description query."""
        if not query or not query.strip():
            raise ValueError("query must be a non-empty string")

        q_embs = self._embed_texts([query])
        if not q_embs:
            return []
        q_emb = q_embs[0]

        try:
            result = self.collection.query(query_embeddings=[q_emb], n_results=top_k)
        except Exception as e:
            logger.exception("Chroma query failed: %s", e)
            raise
        # result keys: ids, documents, metadatas, distances
        items = []
        for i, cid in enumerate(result.get("ids", [[]])[0]):
            items.append({
                "id": cid,
                "metadata": result.get("metadatas", [[]])[0][i],
                "document": result.get("documents", [[]])[0][i],
                "distance": result.get("distances", [[]])[0][i],
            })
        return items

    def explain_candidate_match(self, candidate_resume: str, job_description: str) -> str:
        """Use an LLM to explain why a resume matches a job description."""
        if not job_description or not job_description.strip():
            raise ValueError("job_description must be non-empty")

        prompt = (
            f"Given the following job description:\n{job_description}\n\nAnd the candidate resume text:\n{candidate_resume}\n\n"
            "Provide a short (3-6 bullets) explanation of why this candidate is a good fit for the role."
        )

        # Use OpenAI ChatCompletion directly. Requires OPENAI_API_KEY in environment.
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            logger.warning("OPENAI_API_KEY not set; skipping explanation generation")
            raise RuntimeError("OpenAI API key not available")

        try:
            resp = openai.ChatCompletion.create(
                model=os.environ.get("OPENAI_MODEL", "gpt-3.5-turbo"),
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
                max_tokens=400,
            )
            return resp["choices"][0]["message"]["content"].strip()
        except Exception as e:
            logger.exception("OpenAI call failed: %s", e)
            raise


if __name__ == "__main__":
    # Quick CLI to rebuild the index. Run from repo root: python -m app.services.rag_service
    from app.database import SessionLocal

    db = SessionLocal()
    rag = RAGService()
    stats = rag.build_index_from_db(db)
    print(f"Indexed {stats.get('indexed', 0)} candidates into Chroma at {rag.persist_directory}")
    db.close()
