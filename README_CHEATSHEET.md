# Agentic AI Recruitment Manager — Quick Cheat-Sheet

Project: indexes candidate resumes, embeds locally, retrieves via Chroma, optional OpenAI explanations, exposes FastAPI endpoints.

## Quick commands
- Create venv & install:
```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```
- Seed DB:
```
python scripts/seed_data.py
```
- Build vector index:
```
python scripts/build_vector_index.py
```
- Run API server:
```
uvicorn app.api.rag_api:app --reload --port 8000
```
- Example curl search:
```
curl -X POST http://localhost:8000/rag/search -H "Content-Type: application/json" \
 -d '{"query":"Python backend engineer with FastAPI","top_k":3}'
```

## Files of interest
- `app/services/rag_service.py` — embeddings, Chroma index, retrieval, explanation logic.
- `app/api/rag_api.py` — FastAPI endpoints `/rag/search` and `/rag/rebuild`.
- `scripts/build_vector_index.py` — index builder script.
- `scripts/seed_data.py` — creates sample data and DB.
- `chroma_db/` — local vector DB (ignored by `.gitignore`).
- `interview_scheduler.db` — SQLite DB (consider removing from git).

## Notes
- `OPENAI_API_KEY` optional — if missing, explanations return null and retrieval still works.
- Keep `token.json` and `.env` out of source control; they contain secrets.
