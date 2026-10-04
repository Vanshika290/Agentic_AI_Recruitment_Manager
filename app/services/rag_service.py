import os
import re
import threading
import unicodedata
from typing import List, Dict, Any

from openai import OpenAI

from app.models.models import Candidate
from sqlalchemy.orm import Session
import logging

logger = logging.getLogger("rag_service")



CHROMA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "chroma_db")
MODEL_NAME = "all-MiniLM-L6-v2"
COLLECTION_NAME = "candidate_resumes_v2"
MAX_CANDIDATE_POOL = 100
SKILL_TERMS = (
    "Python", "FastAPI", "REST API", "SQL", "Docker", "Kubernetes", "Java",
    "JavaScript", "TypeScript", "React", "Node.js", "AWS", "Azure", "GCP",
    "PostgreSQL", "MySQL", "MongoDB", "Redis", "Git", "CI/CD", "Terraform",
    "Linux", "Machine Learning", "Pandas", "scikit-learn", "Power BI",
    "Tableau", "Excel", "Data Analysis",
)


class VectorStoreUnavailableError(RuntimeError):
    pass


class EmbeddingModelUnavailableError(RuntimeError):
    pass


class EmptyCandidateIndexError(RuntimeError):
    pass


def preprocess_job_description(query: str) -> str:
    normalized = unicodedata.normalize("NFKC", query)
    return re.sub(r"\s+", " ", normalized).strip()


def _contains_term(text: str, term: str) -> bool:
    pattern = re.escape(term.lower()).replace(r"\ ", r"\s+")
    return re.search(rf"(?<![a-z0-9]){pattern}(?![a-z0-9])", text.lower()) is not None


def score_candidate_match(candidate: Dict[str, Any], job_description: str) -> Dict[str, Any]:
    """Return a transparent match estimate using cosine similarity and explicit skill evidence."""
    metadata = candidate.get("metadata") or {}
    resume = candidate.get("document") or ""
    evidence = f"{metadata.get('skills') or ''}\n{resume}"
    required_skills = [
        skill for skill in SKILL_TERMS if _contains_term(job_description, skill)
    ]
    matched_skills = [
        skill for skill in required_skills if _contains_term(evidence, skill)
    ]
    missing_skills = [
        skill for skill in required_skills if skill not in matched_skills
    ]

    try:
        distance = max(0.0, min(2.0, float(candidate.get("distance", 2.0))))
    except (TypeError, ValueError):
        distance = 2.0
    semantic_score = round((1.0 - distance / 2.0) * 100)
    skill_score = (
        round(100 * len(matched_skills) / len(required_skills))
        if required_skills
        else None
    )
    match_score = (
        round(semantic_score * 0.7 + skill_score * 0.3)
        if skill_score is not None
        else semantic_score
    )

    reasons = []
    if matched_skills:
        reasons.append("Resume/profile evidence includes " + ", ".join(matched_skills) + ".")
    if semantic_score >= 50:
        reasons.append("Resume content is semantically relevant to the job description.")
    if not reasons:
        reasons.append("This is one of the closest semantic matches in the indexed resumes.")

    candidate.update(
        {
            "match_score": match_score,
            "score_breakdown": {
                "semantic_similarity": semantic_score,
                "skill_coverage": skill_score,
                "semantic_weight": 70 if skill_score is not None else 100,
                "skill_weight": 30 if skill_score is not None else 0,
            },
            "matched_skills": matched_skills,
            "missing_skills": missing_skills,
            "why_shortlisted": reasons,
            "explanation": " ".join(reasons),
        }
    )
    return candidate


class RAGService:
    def __init__(self, persist_directory: str = CHROMA_DIR):
        self.persist_directory = persist_directory
        self.client = None
        self.collection = None
        self.embedder = None
        self._resource_lock = threading.Lock()

    def _get_collection(self):
        try:
            if self.collection is None:
                with self._resource_lock:
                    if self.collection is None:
                        import chromadb

                        self.client = chromadb.PersistentClient(path=self.persist_directory)
                        self.collection = self.client.get_or_create_collection(
                            COLLECTION_NAME, metadata={"hnsw:space": "cosine"}
                        )
        except Exception as exc:
            logger.exception("Could not connect to the candidate vector store")
            raise VectorStoreUnavailableError("Vector database unavailable.") from exc
        return self.collection

    def _get_embedder(self):
        try:
            if self.embedder is None:
                with self._resource_lock:
                    if self.embedder is None:
                        from sentence_transformers import SentenceTransformer

                        self.embedder = SentenceTransformer(MODEL_NAME)
        except Exception as exc:
            logger.exception("Could not load the sentence embedding model")
            raise EmbeddingModelUnavailableError("Embedding model unavailable.") from exc
        return self.embedder

    def _embed_texts(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        try:
            embs = self._get_embedder().encode(
                texts, convert_to_numpy=True, normalize_embeddings=True
            )
        except EmbeddingModelUnavailableError:
            raise
        except Exception as exc:
            logger.exception("Embedding failure")
            raise EmbeddingModelUnavailableError("Embedding model unavailable.") from exc
        return [e.tolist() for e in embs]

    def build_index_from_db(self, db: Session, batch_size: int = 64) -> Dict[str, Any]:
        """Read all candidates from the DB and (re)build the Chroma collection."""
        candidates = [
            candidate
            for candidate in db.query(Candidate).all()
            if (candidate.resume_text or "").strip()
        ]
        ids = [f"cand_{c.id}" for c in candidates]
        documents = [c.resume_text.strip() for c in candidates]
        metadatas = [
            {
                "name": c.name or "",
                "email": c.email or "",
                "id": c.id,
                "skills": c.skills or "",
            }
            for c in candidates
        ]

        embeddings = self._embed_texts(documents)
        collection = self._get_collection()
        collection.delete()
        if embeddings:
            collection.add(ids=ids, metadatas=metadatas, documents=documents, embeddings=embeddings)

        return {"indexed": len(ids)}

    def retrieve_candidates(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Retrieve top-k matching candidates for a job description query."""
        if not query or not query.strip():
            raise ValueError("query must be a non-empty string")
        if (
            isinstance(top_k, bool)
            or not isinstance(top_k, int)
            or not 1 <= top_k <= MAX_CANDIDATE_POOL
        ):
            raise ValueError(f"top_k must be between 1 and {MAX_CANDIDATE_POOL}")

        clean_query = preprocess_job_description(query)
        q_embs = self._embed_texts([clean_query])
        if not q_embs:
            return []
        q_emb = q_embs[0]

        collection = self._get_collection()
        try:
            count = collection.count()
        except Exception as exc:
            logger.exception("Could not read candidate count from the vector store")
            raise VectorStoreUnavailableError("Vector database unavailable.") from exc
        if not count:
            raise EmptyCandidateIndexError("No candidate resumes are indexed.")

        try:
            result = collection.query(query_embeddings=[q_emb], n_results=min(top_k, count))
        except Exception as exc:
            logger.exception("Candidate vector search failed")
            raise VectorStoreUnavailableError("Vector database unavailable.") from exc
        items = []
        for i, cid in enumerate(result.get("ids", [[]])[0]):
            items.append({
                "id": cid,
                "metadata": result.get("metadatas", [[]])[0][i],
                "document": result.get("documents", [[]])[0][i],
                "distance": result.get("distances", [[]])[0][i],
            })
        return items

    def indexed_candidate_count(self) -> int:
        try:
            return self._get_collection().count()
        except VectorStoreUnavailableError:
            raise
        except Exception as exc:
            logger.exception("Could not read candidate count from the vector store")
            raise VectorStoreUnavailableError("Vector database unavailable.") from exc

    def search_candidates(self, query: str, top_k: int = 5) -> Dict[str, Any]:
        if isinstance(top_k, bool) or not isinstance(top_k, int) or not 1 <= top_k <= 20:
            raise ValueError("top_k must be between 1 and 20")

        candidate_count = self.indexed_candidate_count()
        if not candidate_count:
            raise EmptyCandidateIndexError("No candidate resumes are indexed.")

        pool_size = min(candidate_count, max(top_k, top_k * 5))
        clean_query = preprocess_job_description(query)
        candidates = self.retrieve_candidates(clean_query, top_k=pool_size)
        ranked = [
            score_candidate_match(candidate, clean_query)
            for candidate in candidates
        ]
        ranked.sort(
            key=lambda candidate: (
                candidate["match_score"],
                candidate["score_breakdown"]["semantic_similarity"],
            ),
            reverse=True,
        )
        return {
            "candidate_count": candidate_count,
            "results": ranked[:top_k],
        }

    def explain_candidate_match(self, candidate_resume: str, job_description: str) -> str:
        """Use an LLM to explain why a resume matches a job description."""
        if not job_description or not job_description.strip():
            raise ValueError("job_description must be non-empty")

        prompt = (
            f"Given the following job description:\n{job_description}\n\nAnd the candidate resume text:\n{candidate_resume}\n\n"
            "Provide a short (3-6 bullets) explanation of why this candidate is a good fit for the role."
        )

        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            logger.warning("OPENAI_API_KEY not set; skipping explanation generation")
            raise RuntimeError("OpenAI API key not available")

        try:
            client = OpenAI(api_key=api_key)
            response = client.chat.completions.create(
                model=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
                max_tokens=400,
            )
            return (response.choices[0].message.content or "").strip()
        except Exception:
            logger.exception("OpenAI call failed")
            raise


if __name__ == "__main__":
    # Quick CLI to rebuild the index. Run from repo root: python -m app.services.rag_service
    from app.database import SessionLocal

    db = SessionLocal()
    rag = RAGService()
    stats = rag.build_index_from_db(db)
    print(f"Indexed {stats.get('indexed', 0)} candidates into Chroma at {rag.persist_directory}")
    db.close()
