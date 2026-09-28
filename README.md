# AI Tutor

AI Tutor is a document-grounded learning platform that helps students learn from their own course material. It is designed around a simple principle: retrieval supplies evidence, while the tutor supplies teaching.

Students can upload PDFs, ask questions, start guided lessons, generate assessments, receive rubric-based feedback, and track concept mastery. The application pairs a FastAPI backend with a lightweight browser interface and stores learning content in Supabase PostgreSQL with pgvector.

> **Project status:** active prototype. The core PDF, retrieval, tutoring, quiz, evaluation, profile, and authentication flows are implemented. Review the [Production considerations](#production-considerations) before deploying for real users.

## Contents

- [What it does](#what-it-does)
- [Architecture](#architecture)
- [Technology](#technology)
- [Quick start](#quick-start)
- [Configuration](#configuration)
- [Database setup](#database-setup)
- [Run the application](#run-the-application)
- [API overview](#api-overview)
- [Repository layout](#repository-layout)
- [Development notes](#development-notes)
- [Production considerations](#production-considerations)
- [Roadmap](#roadmap)

## What it does

- Uploads and processes PDF learning material.
- Extracts text, creates overlapping chunks, and produces local BGE-M3 embeddings.
- Retrieves evidence using vector search, PostgreSQL full-text search, reciprocal-rank fusion, cross-encoder reranking, and nearby-chunk expansion.
- Delivers guided lessons with explanations, examples, analogies, and comprehension checks.
- Supports document-grounded doubt solving with source information.
- Generates MCQ, subjective, and coding quizzes.
- Evaluates submitted answers against a rubric, identifies misconception categories, and updates per-concept mastery.
- Stores learner preferences, mastery records, PDFs, and subjects per user.

## Architecture

```text
Browser client
    |
    v
FastAPI application
    |
    +-- AI Tutor Agent
    |     lesson flow, conversational teaching, quizzes, evaluation
    |
    +-- Retrieval Agent
    |     vector + full-text retrieval -> RRF -> reranking -> context expansion
    |
    +-- PDF processing pipeline
          extraction -> chunking -> BGE-M3 embeddings -> persistence
    |
    v
Supabase PostgreSQL + pgvector
    users, subjects, PDFs, chunks, profiles, mastery, assessments
```

The tutor agent is responsible for the learning interaction. The retrieval agent is responsible for selecting evidence. Keeping those responsibilities separate makes it possible to improve retrieval without rewriting teaching behavior.

## Technology

| Area             | Implementation                                         |
| ---------------- | ------------------------------------------------------ |
| API              | FastAPI and Uvicorn                                    |
| Frontend         | Vanilla HTML, CSS, and JavaScript                      |
| Database         | Supabase PostgreSQL with pgvector and full-text search |
| Embeddings       | `BAAI/bge-m3` via Sentence Transformers                |
| Reranking        | `BAAI/bge-reranker-v2-m3` via Transformers             |
| Tutor model      | Groq `llama-3.3-70b-versatile`                         |
| Legacy Q&A model | Google Gemini integration                              |
| PDF extraction   | pdfplumber with PyPDF2 fallback                        |

The embedding pipeline slices BGE-M3 vectors to 768 dimensions and normalizes them to match the current pgvector schema.

## Quick start

### Prerequisites

- Python 3.14 or later (the version declared in `pyproject.toml`).
- A Supabase project with the `vector` extension available.
- A Groq API key for tutor, quiz, and evaluation features.
- A Gemini API key if using the legacy `/api/v1/ask` doubt-solver flow.
- Internet access the first time Hugging Face models are downloaded.

A CUDA-capable GPU is recommended for faster embedding and reranking. The code falls back to CPU when CUDA is unavailable or runs out of memory.

### Install

```powershell
git clone https://github.com/Aravind556/Intel.git
Set-Location Intel

python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

If you use `uv`, install from the project lockfile instead:

```powershell
uv sync
```

> The checked-in `pyproject.toml` and `requirements.txt` currently target different dependency sets. For the running FastAPI application, `requirements.txt` is the authoritative installation path until these manifests are consolidated.

## Configuration

Create a `.env` file at the repository root. Never commit real credentials.

```env
SUPABASE_URL=https://<project-ref>.supabase.co
SUPABASE_KEY=<supabase-anon-key>
SUPABASE_SERVICE_KEY=<supabase-service-role-key>
GROQ_API_KEY=<groq-api-key>
GEMINI_API_KEY=<gemini-api-key>
```

`SUPABASE_SERVICE_KEY` is used by server-side database operations and must only be available to the backend. Keep it out of client code, logs, and version control.

## Database setup

1. Create a Supabase project.
2. Enable the `vector` extension in its SQL editor.
3. Run [core/database/setup.sql](core/database/setup.sql) to create the base schema, indexes, search functions, and row-level-security policies.
4. Run the migrations in `core/database/` in their intended order:
   - `migration_user_pdfs.sql`
   - `migration_tutor_profiles.sql`

The database stores users, subjects, PDF documents, document chunks, processing status, learner profiles, mastery data, and assessment history. The current schema uses a 768-dimensional vector column.

## Run the application

```powershell
python run_server.py
```

Open:

| Resource             | Address                                   |
| -------------------- | ----------------------------------------- |
| Sign-in page         | http://localhost:8000/frontend/auth.html  |
| Application          | http://localhost:8000/frontend/index.html |
| Interactive API docs | http://localhost:8000/docs                |
| Health check         | http://localhost:8000/health              |

The server begins serving requests while model initialization continues in a background thread. PDF embedding and reranking features may not be immediately ready on first boot.

## API overview

All routes are mounted under `/api/v1` unless noted. Authentication-protected routes use the `session_id` cookie established by the auth endpoints.

| Area                | Endpoints                                                                                          |
| ------------------- | -------------------------------------------------------------------------------------------------- |
| Service             | `GET /health`, `GET /system/status`, `GET /stats`                                                  |
| Authentication      | `POST /auth/register`, `/auth/login`, `/auth/logout`, `/auth/change-password`; `GET /auth/profile` |
| PDFs                | `POST /pdfs/upload`, `GET /pdfs`, `GET /pdfs/stats`, `GET /pdfs/{pdf_id}`, `DELETE /pdfs/{pdf_id}` |
| Tutoring            | `POST /tutor/start-lesson`, `/tutor/chat`, `/tutor/quiz`, `/tutor/evaluate`                        |
| Learner profile     | `GET /profile/mastery`, `GET /profile/preferences`, `POST /profile/preferences`                    |
| Legacy doubt solver | `POST /ask`, `GET /analyze/{question}`                                                             |
| Users and subjects  | `POST /users`, `GET /users/{user_id}`, `GET /users/{user_id}/subjects`, `POST /subjects`           |

The generated OpenAPI reference at `/docs` is the source of truth for request and response schemas.

## Repository layout

```text
.
|-- api/
|   `-- main.py                    # FastAPI app, routes, dependencies
|-- core/
|   |-- simple_auth.py             # Cookie-session authentication
|   `-- database/
|       |-- setup.sql              # Base Supabase schema
|       |-- migration_*.sql        # Schema migrations
|       |-- config.py              # Supabase client configuration
|       `-- manager.py             # Database access layer
|-- modules/
|   |-- agents/
|   |   |-- tutor_agent.py         # Teaching, quizzes, evaluation
|   |   `-- retrieval_agent.py     # Hybrid evidence retrieval
|   |-- doubt_solver/              # Legacy document Q&A pipeline
|   `-- pdf_processor/             # Extraction, chunking, embeddings, storage
|-- frontend/                      # Browser UI and authentication screens
|-- tests/                         # Database inspection and test utilities
|-- docs/
|   `-- system_architecture.md     # Detailed architecture notes
|-- run_server.py                  # Local server entry point
`-- requirements.txt               # Runtime dependency list
```

## Development notes

- Model artifacts are downloaded on demand by Hugging Face libraries; allow time and disk space for the first run.
- PDF extraction uses `pdfplumber` first and falls back to `PyPDF2`. Image-only/scanned PDFs need OCR support, which is not yet part of the pipeline.
- Chunks are generated with a 2,000-character target size and 150-character overlap, subject to the processor's safeguards.
- Use `tests/check_db.py` for basic database inspection. There is not yet a comprehensive automated test suite.
- [docs/system_architecture.md](docs/system_architecture.md) contains a deeper technical design reference.

## Production considerations

This repository is suitable for development and prototyping. Before a production deployment, prioritize the following work:

- Replace in-memory sessions with durable, secure session storage; configure secure, HttpOnly, and SameSite cookie attributes.
- Replace the permissive CORS policy with explicit frontend origins.
- Confirm that Supabase RLS policies are enabled and tested for every user-owned table.
- Move PDF processing and model initialization to durable background jobs with retries and observable status.
- Consolidate `pyproject.toml`, `uv.lock`, and `requirements.txt` into one reproducible dependency strategy.
- Add integration tests for authentication, isolation, uploads, retrieval quality, and evaluation results.
- Introduce structured logging, monitoring, rate limiting, error reporting, and a secret-management system.

## Roadmap

- Hierarchical book, unit, chapter, section, and topic metadata.
- Better prerequisite detection and personalized lesson sequencing.
- OCR for scanned material and multimodal diagram explanation.
- Adaptive revision plans based on mastery trends and spaced repetition.
- Durable user sessions, background processing, and production observability.
- Broader automated coverage and retrieval-quality evaluation.

## License

No license file is currently included. Add an explicit license before distributing or accepting external contributions.
