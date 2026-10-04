from fastapi.testclient import TestClient

from app.api.rag_api import app


client = TestClient(app)


def test_analyze_resume_accepts_txt_upload():
    resume = b"""Jordan Lee
jordan@example.com | 555-123-4567
Skills
Python, FastAPI, SQL, Git, Docker
Experience
Automated API deployment and improved reliability by 20 percent.
Education
Bachelor of Computer Science
Projects
Candidate matching platform
"""

    response = client.post(
        "/student/analyze",
        data={"role": "Software Engineer", "job_description": "Python backend APIs"},
        files={"resume": ("resume.txt", resume, "text/plain")},
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["role"] == "Software Engineer"
    assert 0 <= payload["score"] <= 100
    assert "Python" in payload["matched_keywords"]


def test_analyze_resume_rejects_unsupported_upload_type():
    response = client.post(
        "/student/analyze",
        data={"role": "Software Engineer"},
        files={"resume": ("resume.rtf", b"Resume text", "text/plain")},
    )

    assert response.status_code == 400
    assert "PDF, DOCX, or TXT" in response.json()["detail"]


def test_coach_answers_role_skill_question():
    response = client.post(
        "/student/coach",
        data={"role": "Data Analyst", "question": "Which skills should I learn?"},
    )

    assert response.status_code == 200, response.text
    assert "Tableau" in response.json()["answer"]