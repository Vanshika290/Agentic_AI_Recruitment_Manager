"""Utility script to (re)build the resume vector index using RAGService."""
import os
import sys

# Add project root to Python path (same pattern as scripts/seed_data.py)
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.insert(0, project_root)

from app.database import SessionLocal
from app.services.rag_service import RAGService


def main():
    db = SessionLocal()
    rag = RAGService()
    stats = rag.build_index_from_db(db)
    print(f"Indexed {stats.get('indexed', 0)} candidates into Chroma.")
    db.close()


if __name__ == "__main__":
    main()
