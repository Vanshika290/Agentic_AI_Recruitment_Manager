import re
import zipfile
from io import BytesIO
from typing import Any
from xml.etree import ElementTree

from pypdf import PdfReader
from pypdf.errors import PdfReadError


ROLE_SKILLS = {
    "software engineer": ["Python", "Java", "JavaScript", "SQL", "REST APIs", "Git", "testing", "Docker"],
    "software developer": ["Python", "Java", "JavaScript", "SQL", "REST APIs", "Git", "testing", "Docker"],
    "data analyst": ["SQL", "Excel", "Python", "Tableau", "Power BI", "statistics", "dashboards", "data visualization"],
    "data scientist": ["Python", "SQL", "statistics", "machine learning", "pandas", "scikit-learn", "data visualization", "experimentation"],
    "product manager": ["product strategy", "roadmaps", "user research", "analytics", "stakeholder management", "prioritization", "Agile", "product launches"],
    "ux designer": ["Figma", "prototyping", "wireframing", "user research", "usability testing", "accessibility", "interaction design", "design systems"],
    "cybersecurity analyst": ["SIEM", "incident response", "network security", "penetration testing", "vulnerability assessment", "threat modeling", "cloud security", "IAM"],
    "devops engineer": ["Linux", "AWS", "Azure", "Docker", "Kubernetes", "CI/CD", "Terraform", "monitoring"],
}

GENERIC_SKILLS = ["communication", "problem solving", "teamwork", "project management"]
MAX_RESUME_CHARACTERS = 30000
MAX_RESUME_FILE_BYTES = 5 * 1024 * 1024
STOP_WORDS = {
    "about", "across", "after", "allow", "and", "are", "based", "being", "build", "can", "candidate",
    "company", "demonstrated", "develop", "development", "experience", "experienced", "for", "from", "have",
    "ideal", "in", "include", "including", "into", "is", "job", "looking", "must", "our", "preferred", "role",
    "skills", "strong", "team", "the", "their", "this", "to", "using", "with", "work", "years",
}

SECTION_PATTERNS = {
    "experience": r"\b(experience|employment|work history|professional history)\b",
    "education": r"\b(education|academic background|degree)\b",
    "skills": r"\b(skills|technical skills|core competencies)\b",
    "projects": r"\b(projects|selected projects|portfolio)\b",
}
INTERVIEW_QUESTION_ANGLES = (
    "What was your specific contribution, and how did you approach the work?",
    "What was the most challenging part, and how did you work through it?",
    "How did you decide what to do, and what alternatives did you consider?",
    "What impact did your work have, and how did you measure the result?",
    "What did you learn, and what would you do differently next time?",
)
RESUME_SECTION_HEADINGS = {
    "education", "experience", "employment", "work experience", "work history",
    "professional experience", "projects", "skills", "technical skills",
    "certifications", "summary", "profile", "contact", "references",
}
ANSWER_ACTION_PATTERN = re.compile(
    r"\b(i|led|built|created|developed|designed|implemented|improved|analyzed|"
    r"automated|organized|coordinated|tested|delivered|owned|solved)\b",
    re.IGNORECASE,
)
ANSWER_OUTCOME_PATTERN = re.compile(
    r"\b(result|impact|improved|increased|reduced|saved|launched|delivered|"
    r"measured|percent|percentage|users|faster|accuracy)\b|\b\d+(?:\.\d+)?%?\b",
    re.IGNORECASE,
)


def extract_resume_text(filename: str, contents: bytes) -> str:
    extension = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
    if len(contents) > MAX_RESUME_FILE_BYTES:
        raise ValueError("Resume files must be 5 MB or smaller.")

    try:
        if extension == "txt":
            text = contents.decode("utf-8-sig", errors="replace")
        elif extension == "pdf":
            reader = PdfReader(BytesIO(contents))
            if len(reader.pages) > 80:
                raise ValueError("Resume PDFs must contain 80 pages or fewer.")
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
        elif extension == "docx":
            with zipfile.ZipFile(BytesIO(contents)) as archive:
                document_xml = archive.read("word/document.xml")
            if len(document_xml) > 20 * 1024 * 1024:
                raise ValueError("The document contains too much text to process.")
            root = ElementTree.fromstring(document_xml)
            text = " ".join(node.text or "" for node in root.iter("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t"))
        else:
            raise ValueError("Upload a PDF, DOCX, or TXT resume.")
    except (PdfReadError, zipfile.BadZipFile, KeyError, ElementTree.ParseError) as exc:
        raise ValueError("This resume file could not be read. Try another PDF, DOCX, or TXT file.") from exc

    text = text.strip()
    if not text:
        raise ValueError("No readable text was found. Try a text-based PDF or paste your resume instead.")
    if len(text) > MAX_RESUME_CHARACTERS:
        raise ValueError("Resume text must be 30,000 characters or fewer.")
    return text


def _role_skills(role: str) -> list[str]:
    normalized_role = re.sub(r"[^a-z0-9]+", " ", role.lower()).strip()
    for known_role, skills in ROLE_SKILLS.items():
        if known_role in normalized_role or normalized_role in known_role:
            return skills
    return GENERIC_SKILLS


def _job_keywords(job_description: str) -> list[str]:
    words = re.findall(r"[a-z][a-z0-9+#.-]{2,}", job_description.lower())
    return list(dict.fromkeys(word for word in words if word not in STOP_WORDS))[:12]


def _contains_term(text: str, term: str) -> bool:
    escaped = re.escape(term.lower()).replace(r"\ ", r"\s+")
    return re.search(rf"(?<![a-z0-9]){escaped}(?![a-z0-9])", text.lower()) is not None


def generate_interview_questions(resume_text: str, role: str) -> dict[str, Any]:
    resume = (resume_text or "").strip()
    target_role = (role or "").strip()
    if not resume:
        raise ValueError("Upload a resume or paste resume text to start a mock interview.")
    if len(resume) > MAX_RESUME_CHARACTERS:
        raise ValueError("Resume text must be 30,000 characters or fewer.")
    if not target_role:
        raise ValueError("Choose your target role before starting a mock interview.")

    facts = []
    for line in resume.splitlines():
        fact = re.sub(r"^\s*(?:[-*•▪◦]|\d+[.)])\s*", "", line).strip()
        normalized = re.sub(r"[^a-z]+", " ", fact.lower()).strip()
        if (
            len(fact.split()) >= 4
            and len(fact) <= 240
            and normalized not in RESUME_SECTION_HEADINGS
            and not re.search(r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b", fact)
            and not re.search(r"(?:\+?\d[\d(). -]{7,}\d)", fact)
        ):
            facts.append(fact)

    if not facts:
        sentences = re.split(r"(?<=[.!?])\s+", resume)
        facts = [sentence.strip() for sentence in sentences if len(sentence.split()) >= 4][:20]
    if not facts:
        raise ValueError("Add a project or experience description to your resume before starting.")

    questions = []
    for index, angle in enumerate(INTERVIEW_QUESTION_ANGLES):
        fact = facts[index % len(facts)]
        questions.append(
            f"Your resume mentions: “{fact}” Tell me about this experience. {angle}"
        )

    return {"role": target_role, "questions": questions, "total_questions": len(questions)}


def evaluate_interview_answer(question: str, answer: str, resume_text: str) -> dict[str, Any]:
    prompt = (question or "").strip()
    response = (answer or "").strip()
    resume = (resume_text or "").strip()
    if not prompt:
        raise ValueError("The interview question is missing. Start a new mock interview.")
    if not response:
        raise ValueError("Write an answer before asking for feedback.")
    if len(response) > 5000:
        raise ValueError("Interview answers must be 5,000 characters or fewer.")
    if not resume:
        raise ValueError("Upload your resume or paste its text to get interview feedback.")
    if len(resume) > MAX_RESUME_CHARACTERS:
        raise ValueError("Resume text must be 30,000 characters or fewer.")

    words = response.split()
    strengths = []
    improvements = []
    if len(words) >= 25:
        strengths.append("You gave enough detail to build on.")
    else:
        improvements.append("Add a little more detail about the situation and your specific task.")
    if ANSWER_ACTION_PATTERN.search(response):
        strengths.append("You described actions or ownership.")
    else:
        improvements.append("Make your personal contribution clear by explaining what you did.")
    if ANSWER_OUTCOME_PATTERN.search(response):
        strengths.append("You included an outcome or impact.")
    else:
        improvements.append("Finish with the result, impact, or lesson; use numbers when you can support them.")

    topic_terms = {
        word.lower()
        for word in re.findall(r"[A-Za-z][A-Za-z0-9+#.-]{2,}", prompt)
        if word.lower() not in STOP_WORDS
    }
    answer_terms = {
        word.lower()
        for word in re.findall(r"[A-Za-z][A-Za-z0-9+#.-]{2,}", response)
    }
    resume_terms = {
        word.lower()
        for word in re.findall(r"[A-Za-z][A-Za-z0-9+#.-]{2,}", resume)
    }
    if topic_terms & answer_terms:
        strengths.append("Your answer stayed connected to the resume example in the question.")
    elif topic_terms & resume_terms:
        improvements.append("Tie your explanation back to the specific project or experience named in the question.")

    if not improvements:
        improvements.append("Keep the story concise and be ready to explain any technical or project details you mention.")

    return {"strengths": strengths, "improvements": improvements}


def analyze_resume(resume_text: str, role: str, job_description: str = "") -> dict[str, Any]:
    resume = (resume_text or "").strip()
    target_role = (role or "").strip()
    if not resume:
        raise ValueError("Add resume text or upload a resume before analyzing.")
    if len(resume) > MAX_RESUME_CHARACTERS:
        raise ValueError("Resume text must be 30,000 characters or fewer.")
    if not target_role:
        raise ValueError("Choose a target role before analyzing your resume.")

    keywords = list(dict.fromkeys(_role_skills(target_role) + _job_keywords(job_description or "")))
    matched = [keyword for keyword in keywords if _contains_term(resume, keyword)]
    missing = [keyword for keyword in keywords if keyword not in matched]
    present_sections = [name for name, pattern in SECTION_PATTERNS.items() if re.search(pattern, resume, re.IGNORECASE)]
    missing_sections = [name for name in SECTION_PATTERNS if name not in present_sections]
    has_email = re.search(r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b", resume) is not None
    has_phone = re.search(r"(?:\+?\d[\d(). -]{7,}\d)", resume) is not None

    keyword_score = round(70 * len(matched) / len(keywords)) if keywords else 0
    structure_score = round(20 * len(present_sections) / len(SECTION_PATTERNS))
    contact_score = 5 * (int(has_email) + int(has_phone))
    score = min(100, keyword_score + structure_score + contact_score)

    suggestions = []
    if missing:
        suggestions.append(
            "If accurate, make these role-relevant terms visible in your skills or experience: "
            + ", ".join(missing[:6])
            + "."
        )
    if missing_sections:
        suggestions.append("Add clear sections for " + ", ".join(missing_sections) + ".")
    if not has_email or not has_phone:
        suggestions.append("Add reliable contact details, including an email address and phone number.")
    if not re.search(r"\b(increased|reduced|improved|delivered|saved|launched|grew|automated)\b", resume, re.IGNORECASE):
        suggestions.append("Strengthen experience bullets with outcomes and numbers where you can support them.")
    suggestions.append("Only include skills and achievements you can honestly explain in an interview.")

    return {
        "role": target_role,
        "score": score,
        "matched_keywords": matched,
        "missing_keywords": missing,
        "present_sections": present_sections,
        "missing_sections": missing_sections,
        "has_email": has_email,
        "has_phone": has_phone,
        "scoring_breakdown": {
            "keyword_coverage": keyword_score,
            "resume_sections": structure_score,
            "contact_details": contact_score,
        },
        "suggestions": suggestions,
        "disclaimer": "This is an estimate based on common resume signals and the selected role, not a guarantee of any employer's ATS result.",
    }


def coach_reply(question: str, role: str, resume_text: str, job_description: str = "") -> dict[str, Any]:
    prompt = (question or "").strip()
    target_role = (role or "").strip()
    resume = (resume_text or "").strip()
    if not prompt:
        raise ValueError("Ask a question to get resume guidance.")
    if not target_role:
        raise ValueError("Choose a target role so the coach can tailor its advice.")

    skills = _role_skills(target_role)
    analysis = analyze_resume(resume, target_role, job_description) if resume else None
    missing = analysis["missing_keywords"][:5] if analysis else skills[:5]
    lower_prompt = prompt.lower()

    if any(term in lower_prompt for term in ("skill", "learn", "technology", "tool", "stack")):
        answer = (
            f"For a {target_role}, prioritize {', '.join(skills[:6])}. "
            "Choose one skill that appears in your target job descriptions, then show evidence through a project or work example. "
            "Do not add a skill to your resume until you can describe how you used it."
        )
    elif any(term in lower_prompt for term in ("resume", "ats", "improve", "change", "bullet", "keyword", "edit")):
        if missing:
            answer = (
                f"For your {target_role} target, start by checking whether your experience genuinely supports: "
                f"{', '.join(missing)}. Add supported terms to the relevant skills or experience sections. "
            )
        else:
            answer = f"Your resume already mentions the role signals I checked for {target_role}. Make the strongest evidence easy to scan by placing it near the top. "
        answer += "Rewrite bullets as action + scope + outcome; quantify the result where you have reliable numbers."
    else:
        answer = (
            f"For {target_role}, build evidence around {', '.join(skills[:4])}. "
            "A focused project that demonstrates two or three of those skills is more useful than a long list without examples. "
            "Ask me about role skills, resume keywords, or rewriting an experience bullet for more specific guidance."
        )

    return {"answer": answer, "recommended_skills": missing or skills[:4]}