from io import BytesIO
import zipfile

import pytest

from app.services.student_service import analyze_resume, coach_reply, extract_resume_text


def test_analyze_resume_reports_role_keywords_and_missing_sections():
    resume = """Jordan Lee
jordan@example.com | 555-123-4567
Skills
Python, FastAPI, SQL, Git
Experience
Automated deployment checks for three services.
"""

    result = analyze_resume(resume, "Software Engineer", "Build REST APIs with Docker")

    assert 0 <= result["score"] <= 100
    assert "Python" in result["matched_keywords"]
    assert "Docker" in result["matched_keywords"] or "Docker" in result["missing_keywords"]
    assert "education" in result["missing_sections"]
    assert result["has_email"] is True
    assert result["has_phone"] is True
    assert result["scoring_breakdown"]["keyword_coverage"] <= 70


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