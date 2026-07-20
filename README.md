# Agentic AI Recruitment Manager

Project that indexes candidate resumes, embeds them locally, and provides a retrieval API with optional LLM explanations.

**Architecture**

mermaid
flowchart LR
    A[Candidate Ingestion] --> B[Embedding (sentence-transformers)]
    B --> C[ChromaDB (local, persist)]
    D[Job Description / Query] --> E[Embed Query]
    E --> C
    C --> F[Retrieve Top-K Candidates]
    F --> G[LLM Explanation (OpenAI) - optional]


**Tech stack**

- FastAPI — API server and auto `/docs`
- sentence-transformers (`all-MiniLM-L6-v2`) — local embeddings
- ChromaDB (`chromadb`) — local vector store (persisted to `chroma_db/`)
- OpenAI (`openai`) — optional LLM explanations (requires `OPENAI_API_KEY`)
- SQLAlchemy + SQLite — application DB (`interview_scheduler.db`)
- Google Calendar API (credentials via `credentials.json` / `token.json`)
- SMTP / email utilities

**Quick setup**

1. Create and activate a Python venv, then install requirements:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

2. Seed the database (creates tables + sample data):

```bash
python scripts/seed_data.py
```

3. Build the local vector index (persists to `chroma_db/`):

```bash
python scripts/build_vector_index.py
```

4. Run the API server locally:

```bash
uvicorn app.api.rag_api:app --reload --port 8000
```

**Environment variables**

- `OPENAI_API_KEY` — optional; if missing the system returns similarity-only results and explanations will be `null`.
- `OPENAI_MODEL` — optional; default `gpt-3.5-turbo`.
- `GOOGLE_CREDENTIALS` / `token.json` — used for Google Calendar integration (keep `token.json` private).

**API endpoints**

- `POST /rag/search` — body: `{ "query": "<job description>", "top_k": 5 }`

Example response (when `OPENAI_API_KEY` is missing):

```json
{
  "query": "Python backend engineer with FastAPI",
  "results": [
    {
      "id": "cand_2",
      "metadata": { "name": "Jane Smith", "email": "jane@example.com", "id": 2 },
      "document": "Frontend developer with 5 years...",
      "distance": 1.5022,
      "explanation": null
    }
  ]
}
```

- `POST /rag/rebuild` — rebuilds the Chroma index from the SQL DB. Returns `{ "status": "ok", "indexed": <n> }` on success.

**Notes / safety**

- The project persists the Chroma DB under `chroma_db/`. Ensure this directory is in `.gitignore` (already present) before committing.
- `token.json` contains OAuth tokens for Google; never commit it. It's ignored by `.gitignore`.
- Explanations are optional — if the OpenAI key is not configured the API will still return candidate matches.

If you'd like, I can also prepare a short PR message and the exact `git` commands to push these changes to GitHub.
# Agentic_AI_Recruitment_Manager

Live Demo 👉 https://agentic-ai-recruitment-manager.vercel.app/

Interview Schedular Agent

The Interview Scheduler Backend is a RESTful API service designed to manage and automate interview scheduling between candidates and recruiters.
It handles user data, interview slots, scheduling logic, and notification management efficiently.

This backend can easily integrate with a frontend (like React, Vue, or HTML/JS) to provide a complete interview management system.

🚀 Features

👤 User Management (Candidates & Recruiters)

📅 Interview Creation & Scheduling

🔄 Update or Reschedule Interviews

🗑️ Cancel/Delete Interviews

🔍 Fetch All Scheduled Interviews

⏰ Availability Management

📧 Email Notification Integration (optional)

🧩 Database Integration (SQLite/MySQL/PostgreSQL)


   Structure of folder:

     Agentic_AI/
├── app/
│   ├── __init__.py
│   ├── database.py
│   ├── models/
│   │   ├── __init__.py
│   │   └── models.py
│   └── services/
│       ├── __init__.py
│       └── calendar_service.py
├── scripts/
│   └── seed_data.py
└── main.py

