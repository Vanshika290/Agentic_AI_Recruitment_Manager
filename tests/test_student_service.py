from io import BytesIO
import zipfile

import pytest

from app.services.student_service import (
    analyze_resume,
    coach_reply,
    evaluate_interview_answer,
    extract_resume_text,
    generate_interview_questions,
)


def test_analyze_resume_reports_role_keywords_and_missing_sections():
    resume = """Jordan Lee
jordan@example.com | 555-123-4567
Skills
Python, FastAPI, SQL, Git
Experience
Automated deployment checks for three services.
"""

    result = analyze_resume(resume, "Software Engineer", "Build REST APIs with Docker using Python")

    assert 0 <= result["score"] <= 100
    assert "Python" in result["matched_keywords"]
    assert "Docker" in result["matched_keywords"] or "Docker" in result["missing_keywords"]
    assert "education" in result["missing_sections"]
    assert result["has_email"] is True
    assert result["has_phone"] is True
    assert result["scoring_breakdown"]["keyword_coverage"] <= 70


def test_analyze_resume_uses_custom_job_description_instead_of_role_template():
    resume = """Jordan Lee
Skills
Excel, Tableau
Experience
Created sales dashboards in Tableau and Excel.
Education
Bachelor degree
Projects
Monthly sales reporting dashboard
"""

    result = analyze_resume(
        resume,
        "Data Analyst",
        "Tableau, Excel, SQL",
    )

    assert result["scoring_basis"] == "job_description"
    assert result["matched_keywords"] == ["Tableau", "Excel"]
    assert result["missing_keywords"] == ["SQL"]
    assert result["scoring_breakdown"]["keyword_coverage"] == 47


def test_analyze_resume_falls_back_to_role_template_without_job_description():
    result = analyze_resume("Python and SQL experience.", "Data Analyst")

    assert result["scoring_basis"] == "role_template"
    assert result["matched_keywords"] == ["SQL", "Python"]


def test_coach_tailors_skill_advice_to_selected_role():
    result = coach_reply("Which skills should I learn?", "Data Analyst", "SQL, Excel")

    assert "Tableau" in result["answer"]
    assert "Power BI" in result["recommended_skills"]


def test_analyze_resume_requires_resume_and_role():
    with pytest.raises(ValueError, match="resume"):
        analyze_resume("", "Software Engineer")

    with pytest.raises(ValueError, match="target role"):
        analyze_resume("Resume content", "")


def test_extract_resume_text_reads_docx_xml():
    document = BytesIO()
    xml = (
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        "<w:body><w:p><w:r><w:t>Candidate resume content</w:t></w:r></w:p></w:body></w:document>"
    )
    with zipfile.ZipFile(document, "w") as archive:
        archive.writestr("word/document.xml", xml)

    assert extract_resume_text("resume.docx", document.getvalue()) == "Candidate resume content"


def test_generate_interview_questions_reference_resume_experience():
    resume = """Jordan Lee
Experience
- Built a Python API that reduced data processing time by 30 percent.
Projects
- Created a candidate search dashboard using FastAPI and SQL.
"""

    result = generate_interview_questions(resume, "Backend Engineer")

    assert result["role"] == "Backend Engineer"
    assert result["total_questions"] == 5
    assert len(result["questions"]) == 5
    assert "Built a Python API" in result["questions"][0]
    assert "Created a candidate search dashboard" in result["questions"][1]


def test_generate_interview_questions_requires_resume_evidence():
    with pytest.raises(ValueError, match="project or experience"):
        generate_interview_questions("Python SQL FastAPI", "Backend Engineer")


def test_evaluate_interview_answer_returns_actionable_feedback():
    resume = "Built a Python API for processing job applications."
    question = 'Your resume mentions: "Built a Python API for processing job applications." How did you approach the work?'

    result = evaluate_interview_answer(
        question,
        "I built the API and improved processing time by 25 percent by optimizing the database queries.",
        resume,
    )

    assert "You described actions or ownership." in result["strengths"]
    assert "You included an outcome or impact." in result["strengths"]
    assert "Your answer stayed connected to the resume example in the question." in result["strengths"]
    assert result["improvements"]


def test_evaluate_interview_answer_rejects_empty_answer():
    with pytest.raises(ValueError, match="Write an answer"):
        evaluate_interview_answer("Tell me about your project.", " ", "Built a Python API.")