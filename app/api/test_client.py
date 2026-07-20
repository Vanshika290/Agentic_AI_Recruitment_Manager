from fastapi.testclient import TestClient
from app.api.rag_api import app

client = TestClient(app)

def quick_search(query: str):
    resp = client.post('/rag/search', json={'query': query, 'top_k': 3})
    return resp.status_code, resp.json()

if __name__ == '__main__':
    status, data = quick_search('Python backend engineer with FastAPI')
    print(status)
    print(data)
