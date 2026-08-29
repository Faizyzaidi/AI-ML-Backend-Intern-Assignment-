"""
Interview session lifecycle endpoints.

    POST /api/session/start              -> upload resume + role, get session + first question
    GET  /api/session/{id}/next-question -> serve the next unanswered question
    POST /api/session/{id}/answer        -> submit an answer, persist it
    GET  /api/session/{id}/summary       -> structured final report
"""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.orm import Session as DBSession

from app.database import get_db
from app.models import InterviewSession, Question, Answer, SessionStatus
from app.schemas import (
    SessionStartResponse,
    ResumeProfile,
    QuestionOut,
    AnswerIn,
    AnswerOut,
    NextQuestionResponse,
    SessionSummaryResponse,
    QAPair,
)
from app.services.resume_parser import extract_text_from_upload, extract_resume_profile
from app.services.question_generator import generate_questions
from app.services.summary_generator import generate_summary, score_answer

router = APIRouter(prefix="/api/session", tags=["session"])

MAX_RESUME_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB


@router.post("/start", response_model=SessionStartResponse)
async def start_session(
    role: str = Form(...),
    resume: UploadFile = File(...),
    db: DBSession = Depends(get_db),
):
    if not role.strip():
        raise HTTPException(status_code=400, detail="A target role is required.")

    file_bytes = await resume.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Uploaded resume file is empty.")
    if len(file_bytes) > MAX_RESUME_SIZE_BYTES:
        raise HTTPException(status_code=400, detail="Resume file exceeds 5MB limit.")
    if not resume.filename.lower().endswith((".pdf", ".txt")):
        raise HTTPException(
            status_code=400, detail="Only .pdf and .txt resumes are supported."
        )

    resume_text = extract_text_from_upload(resume.filename, file_bytes)
    if not resume_text.strip():
        raise HTTPException(
            status_code=422,
            detail="Could not extract any text from the resume. Try a different file.",
        )

    resume_profile = extract_resume_profile(resume_text)

    session = InterviewSession(
        role=role.strip(),
        resume_filename=resume.filename,
        resume_text=resume_text,
        resume_profile=resume_profile,
        status=SessionStatus.IN_PROGRESS,
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    generated = generate_questions(role=session.role, resume_profile=resume_profile)
    if not generated:
        raise HTTPException(
            status_code=422,
            detail=(
                f"No knowledge base is ingested for role '{role}' yet. "
                "Run the ingestion script (see README) before starting an interview "
                "for this role."
            ),
        )

    question_rows = []
    for i, q in enumerate(generated):
        row = Question(
            session_id=session.id,
            order_index=i,
            text=q["text"],
            topic=q["topic"],
            difficulty=q["difficulty"],
            source_query=q["source_query"],
            source_chunks=q["source_chunks"],
        )
        db.add(row)
        question_rows.append(row)
    db.commit()

    first_question = min(question_rows, key=lambda q: q.order_index)
    db.refresh(first_question)

    return SessionStartResponse(
        session_id=session.id,
        role=session.role,
        resume_profile=ResumeProfile(**resume_profile),
        total_questions=len(question_rows),
        first_question=QuestionOut.model_validate(first_question),
    )


def _get_session_or_404(db: DBSession, session_id: str) -> InterviewSession:
    session = db.query(InterviewSession).filter(InterviewSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")
    return session


@router.get("/{session_id}/next-question", response_model=NextQuestionResponse)
def next_question(session_id: str, db: DBSession = Depends(get_db)):
    session = _get_session_or_404(db, session_id)

    answered_question_ids = {
        a.question_id
        for a in db.query(Answer).filter(Answer.session_id == session_id).all()
    }
    total = len(session.questions)
    answered_count = len(answered_question_ids)

    next_q: Optional[Question] = next(
        (q for q in session.questions if q.id not in answered_question_ids), None
    )

    if next_q is None:
        if session.status != SessionStatus.COMPLETED:
            session.status = SessionStatus.COMPLETED
            session.completed_at = datetime.utcnow()
            db.commit()
        return NextQuestionResponse(
            done=True, question=None, progress={"answered": answered_count, "total": total}
        )

    return NextQuestionResponse(
        done=False,
        question=QuestionOut.model_validate(next_q),
        progress={"answered": answered_count, "total": total},
    )


@router.post("/{session_id}/answer", response_model=AnswerOut)
def submit_answer(session_id: str, payload: AnswerIn, db: DBSession = Depends(get_db)):
    session = _get_session_or_404(db, session_id)

    question = (
        db.query(Question)
        .filter(Question.id == payload.question_id, Question.session_id == session_id)
        .first()
    )
    if not question:
        raise HTTPException(status_code=404, detail="Question not found in this session.")

    existing = db.query(Answer).filter(Answer.question_id == payload.question_id).first()
    if existing:
        raise HTTPException(status_code=409, detail="This question has already been answered.")

    quality_score = score_answer(payload.answer_text)

    answer = Answer(
        question_id=question.id,
        session_id=session_id,
        text=payload.answer_text,
        quality_score=quality_score,
    )
    db.add(answer)
    db.commit()
    db.refresh(answer)

    return AnswerOut.model_validate(answer)


@router.get("/{session_id}/summary", response_model=SessionSummaryResponse)
def session_summary(session_id: str, db: DBSession = Depends(get_db)):
    session = _get_session_or_404(db, session_id)

    qa_pairs_raw = []
    for q in session.questions:
        answer = db.query(Answer).filter(Answer.question_id == q.id).first()
        qa_pairs_raw.append(
            {
                "question": q.text,
                "topic": q.topic,
                "difficulty": q.difficulty,
                "answer": answer.text if answer else None,
                "quality_score": answer.quality_score if answer else None,
            }
        )

    scored = [qa["quality_score"] for qa in qa_pairs_raw if qa["quality_score"] is not None]
    avg_score = sum(scored) / len(scored) if scored else None

    llm_summary = generate_summary(
        role=session.role, resume_profile=session.resume_profile, qa_pairs=qa_pairs_raw
    )

    return SessionSummaryResponse(
        session_id=session.id,
        role=session.role,
        resume_profile=ResumeProfile(**session.resume_profile),
        status=session.status.value,
        started_at=session.created_at,
        completed_at=session.completed_at,
        qa_pairs=[QAPair(**qa) for qa in qa_pairs_raw],
        topics_covered=llm_summary.get("topics_covered", []),
        average_quality_score=avg_score,
        insights=llm_summary.get("insights", []),
    )
