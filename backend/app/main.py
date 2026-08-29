"""
FastAPI application entrypoint.

Run locally with:
    uvicorn app.main:app --reload --port 8000
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import init_db
from app.routers import roles, session

app = FastAPI(
    title=settings.APP_NAME,
    description=(
        "AI-powered role-based candidate screening system. Generates a "
        "structured technical interview using a RAG pipeline over a "
        "role-specific knowledge base, personalized by the candidate's "
        "resume."
    ),
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    init_db()


@app.get("/api/health", tags=["health"])
def health_check():
    return {"status": "ok", "env": settings.ENV, "llm_provider": settings.LLM_PROVIDER}


app.include_router(roles.router)
app.include_router(session.router)
