import logging
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.services import student_service

logger = logging.getLogger("student_api")
router = APIRouter(prefix="/student", tags=["student tools"])


async def _resume_text(resume: Optional[UploadFile], pasted_text: str) -> str:
    if resume is not None:
        contents = await resume.read(student_service.MAX_RESUME_FILE_BYTES + 1)
        return student_service.extract_resume_text(resume.filename or "", contents)

    text = (pasted_text or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="Upload a resume or paste resume text.")
    if len(text) > student_service.MAX_RESUME_CHARACTERS:
        raise HTTPException(status_code=400, detail="Resume text must be 30,000 characters or fewer.")
    return text


@router.post("/analyze")
async def analyze_student_resume(
    role: str = Form(..., max_length=100),
    job_description: str = Form("", max_length=15000),
    resume_text: str = Form("", max_length=student_service.MAX_RESUME_CHARACTERS),
    resume: Optional[UploadFile] = File(None),
):
    try:
        text = await _resume_text(resume, resume_text)
        return student_service.analyze_resume(text, role, job_description)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/interview/start")
async def start_student_interview(
    role: str = Form(..., max_length=100),
    resume_text: str = Form("", max_length=student_service.MAX_RESUME_CHARACTERS),
    resume: Optional[UploadFile] = File(None),
):
    try:
        text = await _resume_text(resume, resume_text)
        return student_service.generate_interview_questions(text, role)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Mock interview could not be started")
        raise HTTPException(status_code=500, detail="The mock interview could not be started.") from exc


@router.post("/interview/answer")
async def answer_student_interview(
    role: str = Form(..., max_length=100),
    question: str = Form(..., max_length=2000),
    answer: str = Form(..., max_length=5000),
    resume_text: str = Form("", max_length=student_service.MAX_RESUME_CHARACTERS),
    resume: Optional[UploadFile] = File(None),
):
    try:
        text = await _resume_text(resume, resume_text)
        return student_service.evaluate_interview_answer(question, answer, text)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Mock interview feedback failed")
        raise HTTPException(status_code=500, detail="Interview feedback is unavailable right now.") from exc


@router.post("/coach")
async def coach_student(
    role: str = Form(..., max_length=100),
    question: str = Form(..., max_length=2000),
    job_description: str = Form("", max_length=15000),
    resume_text: str = Form("", max_length=student_service.MAX_RESUME_CHARACTERS),
    resume: Optional[UploadFile] = File(None),
):
    try:
        text = await _resume_text(resume, resume_text) if resume is not None or resume_text.strip() else ""
        return student_service.coach_reply(question, role, text, job_description)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception:
        logger.exception("Career coach request failed")
        raise HTTPException(status_code=500, detail="The career coach could not answer right now.")