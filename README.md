# AI-Powered Role-Based Candidate Screening System

A structured, RAG-driven technical interview system. A candidate uploads a
resume and picks a target role; the system generates interview questions
grounded in a role-specific knowledge base and personalized to the resume,
serves them one at a time, records answers, and produces a structured
summary at the end.

Built for the PGAGI AI/ML & Backend Intern Assignment.

---

## 1. Quick Start

The system runs with **zero external API keys or paid services** out of the
box (see [Zero-config demo mode](#7-zero-config-demo-mode) below), so you
can get it running in a couple of minutes.

### Backend

```bash
cd backend
python -m venv venv && source venv/bin/activate   # optional but recommended
pip install -r requirements.txt

cp .env.example .env          # defaults already work as-is

# Ingest the included sample knowledge bases (backend-engineer, ai-ml-engineer)
python -m app.rag.ingest

# Run the API
uvicorn app.main:app --reload --port 8000
```

The API is now live at `http://localhost:8000` (interactive docs at
`http://localhost:8000/docs`).

### Frontend

```bash
cd frontend
npm install
cp .env.local.example .env.local   # points at http://localhost:8000 by default
npm run dev
```

Open `http://localhost:3000`, upload a resume (PDF or TXT), pick a role,
and start the interview.

---

## 2. System Architecture

```
┌─────────────┐      REST/JSON       ┌──────────────────────┐
│  Next.js    │ <──────────────────> │      FastAPI          │
│  Frontend   │                      │      Backend          │
└─────────────┘                      └──────────┬───────────┘
                                                 │
                     ┌───────────────────────────┼────────────────────────┐
                     │                           │                        │
             ┌───────▼───────┐          ┌────────▼────────┐      ┌────────▼────────┐
             │  SQLite/       │          │   RAG Pipeline   │      │   LLM Client     │
             │  Postgres      │          │  (chunk/embed/   │      │  (Anthropic /    │
             │  (sessions,    │          │   retrieve)      │      │   OpenAI /       │
             │  questions,    │          └────────┬─────────┘      │   fallback)      │
             │  answers)      │                   │                └─────────────────┘
             └────────────────┘          ┌────────▼─────────┐
                                          │   ChromaDB        │
                                          │  (vector store,   │
                                          │  one collection   │
                                          │  per role)         │
                                          └────────────────────┘
```

### Backend module layout

```
backend/
  app/
    main.py              FastAPI app, CORS, startup
    config.py             All configuration via environment variables
    database.py            SQLAlchemy engine/session
    models.py               ORM: InterviewSession, Question, Answer
    schemas.py                Pydantic request/response contracts
    routers/
      roles.py                 GET /api/roles
      session.py                 Session lifecycle endpoints
    services/
      resume_parser.py           Resume text extraction + structured profile
      llm_client.py                Anthropic / OpenAI / fallback abstraction
      question_generator.py          RAG-grounded question generation
      summary_generator.py             Final report generation + scoring
    rag/
      chunking.py                       Word-based sliding-window chunker
      embeddings.py                       Hashing embedder / sentence-transformers
      vector_store.py                       ChromaDB wrapper (per-role collections)
      retriever.py                            Dynamic query construction + retrieval
      ingest.py                                 CLI ingestion pipeline
  data/
    knowledge_base/<role>/*.pdf|.txt            Source documents per role
    vector_store/                                Chroma persistence (generated)
    app.db                                        SQLite DB (generated)
```

### Frontend layout

```
frontend/
  app/
    page.tsx           Resume upload + role selection
    interview/page.tsx  One-question-at-a-time interview flow
    summary/page.tsx     Structured results view
  lib/api.ts          Typed API client
```

---

## 3. System Flow

1. **Candidate entry** — resume upload (PDF/TXT) + role selection.
2. **Resume processing** — text extracted, then a structured profile
   (`skills`, `technologies`, `domains`, `experience_level`) is derived.
3. **Context construction** — `rag/retriever.py::build_queries()` turns the
   role + resume profile into a diverse set of retrieval queries — some
   driven by the candidate's specific technologies/skills (personalization),
   some fixed "core fundamentals" queries (baseline topic coverage).
4. **Knowledge retrieval (RAG)** — each query is embedded and used to pull
   the top-k most relevant chunks from that role's ChromaDB collection.
5. **Question generation** — the LLM (or fallback generator) is given the
   retrieved chunks + role + resume profile and asked to produce one
   grounded, non-generic question per retrieved-context item, each tagged
   with a difficulty (`conceptual` / `applied` / `advanced`).
6. **Interactive interview** — the frontend polls `next-question`, shows one
   question at a time with a progress bar, and posts answers.
7. **Response handling** — every answer is persisted against its question,
   with a lightweight quality-signal score computed at submission time.
8. **Final output** — `GET /session/{id}/summary` returns the full
   transcript, topics covered, an average quality signal, and LLM-generated
   (or heuristic) qualitative insights.

Every generated question retains **RAG provenance**: which query produced
it and which source chunks (document + chunk index + snippet) it was
grounded in — satisfying the traceability requirement in the assignment
(section 7.5).

---

## 4. API Reference

| Method | Path                                | Description                                  |
|--------|--------------------------------------|-----------------------------------------------|
| GET    | `/api/health`                        | Liveness + current config summary             |
| GET    | `/api/roles`                         | Roles with an ingested knowledge base         |
| POST   | `/api/session/start`                 | multipart: `role`, `resume` → session + Q1    |
| GET    | `/api/session/{id}/next-question`    | Next unanswered question, or `done: true`     |
| POST   | `/api/session/{id}/answer`           | `{question_id, answer_text}`                  |
| GET    | `/api/session/{id}/summary`          | Full structured summary                       |

Full interactive schema at `/docs` (Swagger UI) once the backend is running.

---

## 5. Key Design Decisions

**Chunking (word-based, sliding overlap).** Chunks are built from word
counts (approximating tokens) rather than raw characters, which keeps
chunk boundaries closer to natural sentence/paragraph breaks. A sliding
overlap (default 400 words per chunk, 60-word overlap) preserves context
that would otherwise be lost right at a chunk boundary — important for
textbook material where a concept's explanation often spans what would
otherwise be a hard cut.

**One vector collection per role.** Rather than a single collection with a
role metadata filter, each role gets its own ChromaDB collection. This
makes retrieval correctness-by-construction (no risk of cross-role leakage
from a filter bug), keeps ingestion of one role's documents fully
independent of another's, and makes adding a new role a pure addition with
zero risk to existing collections.

**Dynamic, resume-aware query construction.** Retrieval queries are not a
static "give me content about {role}" lookup. They combine resume-derived
technology/skill terms with fixed core-fundamentals queries, so the
interview is both personalized and guaranteed a baseline of topic coverage
even for a thin or unusual resume.

**Deterministic, idempotent ingestion.** Chunk IDs are derived
deterministically from `role + filename + chunk_index` (SHA-256 hash), so
re-running ingestion on unchanged files **upserts** rather than duplicates,
making the pipeline safe to re-run as documents are added or updated.

**Swappable LLM & embedding providers via configuration only.** All
AI-provider choices are environment-variable driven
(`LLM_PROVIDER=anthropic|openai|fallback`,
`EMBEDDING_PROVIDER=hashing|sentence-transformers`) and sit behind a single
interface (`get_llm_client()`, `get_embedder()`). No calling code needs to
change to switch providers.

**A genuinely usable zero-key fallback mode.** See section 7 below — this
was a deliberate choice so the full system is runnable, testable, and
demoable without requiring anyone (grader included) to provision API keys
or pay for embedding/LLM calls, while still exercising the real RAG
pipeline (chunking, embedding, vector search, grounded generation) rather
than mocking it out.

**Full traceability from question back to source.** Every `Question` row
stores `source_query` and `source_chunks` (document name, chunk index, and
a snippet), satisfying the "Context → Question → Answer → Storage" pipeline
requirement with actual auditability, not just a claim of it.

**Lightweight adaptive signal, not black-box scoring.** Each answer gets a
transparent, explainable heuristic quality score (length, specificity,
lexical diversity) rather than an opaque model-only judgment, so the score
is inspectable and its limitations are obvious rather than hidden.

---

## 6. Adding a Real Role / Knowledge Base

1. Create `backend/data/knowledge_base/<role-slug>/` and drop in PDFs (or
   `.txt` files) — e.g. the books referenced in the assignment brief
   (*Machine Learning* — Tom Mitchell; *The Hundred-Page Machine Learning
   Book* — Andriy Burkov; *Introduction to Machine Learning with Python*).
2. Run `python -m app.rag.ingest --role <role-slug>` from `backend/`.
3. The role now appears in `GET /api/roles` and in the frontend's role
   dropdown automatically.

---

## 7. Zero-Config Demo Mode

By default (`LLM_PROVIDER=fallback`, `EMBEDDING_PROVIDER=hashing`) the
system runs entirely offline with no API keys and no model downloads:

- **Embeddings**: a deterministic hashed-n-gram embedder (`rag/embeddings.py`)
  stands in for a real sentence-embedding model.
- **Generation**: a rule-based generator (`services/llm_client.py`) still
  produces grounded, role-relevant questions and summaries directly from
  retrieved context, rather than a canned/mocked response.

This is intentionally honest about being a lower-quality stand-in, not a
hidden shortcut: retrieval quality and question phrasing are noticeably
better with a real embedding model and LLM. **For a stronger demo**, set:

```bash
LLM_PROVIDER=anthropic          # or openai
ANTHROPIC_API_KEY=sk-ant-...
EMBEDDING_PROVIDER=sentence-transformers   # requires: pip install sentence-transformers
```

and re-run ingestion so the (better) embeddings are recomputed.

**Known limitation of the sample/demo corpus specifically**: the two
included sample knowledge-base files are short (~800 words each), so they
only produce ~3 chunks per role. With that few chunks, several different
retrieval queries can legitimately retrieve the same top chunk, especially
under the hashing embedder. This is a corpus-size/embedding-quality
artifact of the demo data, not a flaw in the retrieval or chunking logic —
ingesting the full textbooks referenced in the assignment (hundreds of
pages each) resolves it by giving the retriever enough distinct chunks per
topic to differentiate between queries.

---

## 8. Environment Variables

See `backend/.env.example` and `frontend/.env.local.example` for the full,
documented list. Nothing is hardcoded.

---

## 9. Possible Extensions (Not Implemented, Noted as Stretch)

- Adaptive follow-up questions based on LLM-judged (rather than heuristic)
  answer quality.
- Session resumability across browser refreshes/devices via a resumable
  link rather than `sessionStorage`.
- Multi-role sessions / role-switching mid-interview.
- Re-ranking retrieved chunks with a cross-encoder before generation.
# AI-ML-Backend-Intern-Assignment-
