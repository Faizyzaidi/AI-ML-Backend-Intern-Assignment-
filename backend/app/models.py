"""
ORM models representing the persistence layer.

InterviewSession  -> one candidate screening run (resume + role)
Question          -> a generated question tied to a session, with RAG
                      provenance (which query & chunks produced it)
Answer            -> the candidate's response to a question
"""
import uuid
import enum
from datetime import datetime

from sqlalchemy import (
    Column,
    String,
    Text,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    Enum as SAEnum,
)
from sqlalchemy.orm import relationship

from app.database import Base


def gen_uuid() -> str:
    return str(uuid.uuid4())


class SessionStatus(str, enum.Enum):
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class InterviewSession(Base):
    __tablename__ = "sessions"

    id = Column(String, primary_key=True, default=gen_uuid)
    role = Column(String, nullable=False, index=True)
    resume_filename = Column(String, nullable=True)
    resume_text = Column(Text, nullable=True)
    # Structured extraction result: {"skills": [...], "technologies": [...],
    # "domains": [...], "experience_level": "..."}
    resume_profile = Column(JSON, nullable=True)
    status = Column(SAEnum(SessionStatus), default=SessionStatus.IN_PROGRESS)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    questions = relationship(
        "Question", back_populates="session", cascade="all, delete-orphan",
        order_by="Question.order_index",
    )


class Question(Base):
    __tablename__ = "questions"

    id = Column(String, primary_key=True, default=gen_uuid)
    session_id = Column(String, ForeignKey("sessions.id"), nullable=False, index=True)
    order_index = Column(Integer, nullable=False)
    text = Column(Text, nullable=False)
    topic = Column(String, nullable=True)
    difficulty = Column(String, nullable=True)  # "conceptual" | "applied" | "advanced"

    # RAG provenance for traceability (assignment requirement 7.5)
    source_query = Column(Text, nullable=True)
    source_chunks = Column(JSON, nullable=True)  # list of {doc, chunk_id, snippet}

    created_at = Column(DateTime, default=datetime.utcnow)

    session = relationship("InterviewSession", back_populates="questions")
    answer = relationship(
        "Answer", back_populates="question", uselist=False,
        cascade="all, delete-orphan",
    )


class Answer(Base):
    __tablename__ = "answers"

    id = Column(String, primary_key=True, default=gen_uuid)
    question_id = Column(String, ForeignKey("questions.id"), nullable=False, unique=True)
    session_id = Column(String, ForeignKey("sessions.id"), nullable=False, index=True)
    text = Column(Text, nullable=False)
    # Lightweight heuristic/LLM-assessed signal used for adaptive follow-ups
    quality_score = Column(Integer, nullable=True)  # 0-100
    created_at = Column(DateTime, default=datetime.utcnow)

    question = relationship("Question", back_populates="answer")
