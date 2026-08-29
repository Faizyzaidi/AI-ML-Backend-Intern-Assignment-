"""Pydantic schemas — the API's request/response contracts."""
from typing import Optional, List, Any, Dict
from datetime import datetime
from pydantic import BaseModel, Field


class ResumeProfile(BaseModel):
    skills: List[str] = Field(default_factory=list)
    technologies: List[str] = Field(default_factory=list)
    domains: List[str] = Field(default_factory=list)
    experience_level: str = "unknown"


class QuestionOut(BaseModel):
    id: str
    order_index: int
    text: str
    topic: Optional[str] = None
    difficulty: Optional[str] = None

    class Config:
        from_attributes = True


class QuestionWithProvenance(QuestionOut):
    source_query: Optional[str] = None
    source_chunks: Optional[List[Dict[str, Any]]] = None


class SessionStartResponse(BaseModel):
    session_id: str
    role: str
    resume_profile: ResumeProfile
    total_questions: int
    first_question: Optional[QuestionOut] = None


class AnswerIn(BaseModel):
    question_id: str
    answer_text: str = Field(..., min_length=1)


class AnswerOut(BaseModel):
    id: str
    question_id: str
    text: str
    quality_score: Optional[int] = None

    class Config:
        from_attributes = True


class NextQuestionResponse(BaseModel):
    done: bool
    question: Optional[QuestionOut] = None
    progress: Dict[str, int]


class QAPair(BaseModel):
    question: str
    topic: Optional[str] = None
    difficulty: Optional[str] = None
    answer: Optional[str] = None
    quality_score: Optional[int] = None


class SessionSummaryResponse(BaseModel):
    session_id: str
    role: str
    resume_profile: ResumeProfile
    status: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    qa_pairs: List[QAPair]
    topics_covered: List[str]
    average_quality_score: Optional[float] = None
    insights: List[str]


class RoleInfo(BaseModel):
    role: str
    display_name: str
    document_count: int
