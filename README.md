# AI Tutor — Intelligent Educational Platform

An AI-powered educational platform built on a two-agent cooperative architecture that teaches students like an experienced human teacher — not just answering questions, but delivering structured lessons, generating adaptive assessments, diagnosing misconceptions, and tracking conceptual mastery.

Built with **FastAPI**, **Hugging Face BGE-M3**, **Groq (Llama 3.3 70B)**, **Google Gemini**, and **Supabase (PostgreSQL + pgvector)**.

---

## Table of Contents

- [Architecture](#architecture)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [API Reference](#api-reference)
- [Getting Started](#getting-started)
- [Future Extensions](#future-extensions)

---

## Architecture

The platform separates teaching logic from retrieval logic through two cooperative agents communicating over a structured service boundary.

```
   Student (Frontend)
     │
     ▼
┌──────────────────────────────────────────────────┐
│                 AI Tutor Agent                   │
│  Intent Recognition · Concept Teaching           │
│  Doubt Resolution   · Quiz Generation            │
│  Answer Evaluation  · Misconception Diagnosis    │
│  Mastery Tracking   · Adaptive Difficulty        │
└────────────────────────┬─────────────────────────┘
                         │  Requests curated context
                         ▼
┌──────────────────────────────────────────────────┐
│               Retrieval Agent                    │
│  Strategy Routing   · Metadata Filtering         │
│  Dense Vector Search (BGE-M3)                    │
│  Sparse BM25 Search (PostgreSQL FTS)             │
│  Reciprocal Rank Fusion (k=60)                   │
│  Cross-Encoder Reranking (bge-reranker-v2-m3)    │
│  Sibling Context Expansion                       │
└────────────────────────┬─────────────────────────┘
                         │  Queries content & metadata
                         ▼
┌──────────────────────────────────────────────────┐
│               Knowledge Base                     │
│  Supabase PostgreSQL · pgvector                  │
│  PDF Documents       · Chunked Embeddings (768d) │
│  Student Profiles    · Mastery Records           │
│  Assessment History  · Learning Preferences      │
└──────────────────────────────────────────────────┘
```

**Design Principle:** The AI Tutor Agent never directly accesses the database or generates embeddings. The Retrieval Agent never generates explanations or conversational responses. Each component has a single, clearly defined responsibility.

---

## Features

### Conversational Tutoring
- Structured lesson delivery following a progressive teaching flow: **Prerequisites → Concept Explanation → Analogy → Worked Example → Comprehension Check**
- Multi-turn conversational context maintained across the session
- Strict document grounding — the system refuses to answer from general knowledge when retrieved context is insufficient, citing the limitation explicitly

### Advanced Hybrid RAG Pipeline
- **Dense vector search** using local BAAI/bge-m3 embeddings (1024-dim, normalized to 768-dim) running on GPU
- **Sparse BM25 search** via PostgreSQL full-text search indexes
- **Reciprocal Rank Fusion (RRF)** combining dense and sparse candidate rankings (k=60)
- **Cross-encoder reranking** using local BAAI/bge-reranker-v2-m3 for high-precision passage selection
- **Sibling context expansion** — retrieves neighboring chunks around top-ranked candidates for coherent context

### Dynamic Assessment & Evaluation
- MCQ, subjective, and coding question generation calibrated to configurable difficulty levels
- Batch quiz generation for full assessments across multiple concepts
- **Rubric-based evaluation** — not binary correct/incorrect grading
- **Misconception diagnosis** — classifies errors into Foundational, Execution, Logic, and Vocabulary categories
- Corrective feedback with specific revision topic recommendations

### Student Mastery Tracking
- Per-concept mastery scores (0.0–1.0) tracked over time with test count and timestamp metadata
- Mastery scores updated automatically after each quiz evaluation
- Visual mastery dashboard in the frontend

### PDF Processing Pipeline
- Drag-and-drop PDF upload with real-time progress tracking
- Automated text extraction with semantic paragraph chunking (800–1200 characters, 150-character overlap)
- BGE-M3 embedding generation for all extracted chunks
- Performance profiling instrumented across extraction, embedding, and database persistence phases
- File validation (50MB limit, PDF format verification)

### Student Learning Preferences
- Configurable analogy style (practical, abstract, visual)
- Adjustable explanation depth (brief, medium, detailed)
- Preferred coding language for worked examples
- Preferences stored per-user and injected into tutoring prompts

### Authentication & Data Isolation
- Session-based authentication with cookie management (register, login, logout, password change)
- Row-Level Security (RLS) enforcement on Supabase — each user's PDFs, assessments, and profiles are fully isolated

### Legacy Doubt Solver
- Direct document Q&A endpoint (`/api/v1/ask`) with source-cited responses
- Strict document-only mode — refuses to generate answers when context is insufficient

---

## Tech Stack

| Component | Technology | Details |
|-----------|-----------|---------|
| Backend Framework | FastAPI | Async Python web framework |
| Database | Supabase | PostgreSQL + pgvector + Row-Level Security |
| Dense Embeddings | BAAI/bge-m3 | Local GPU inference via sentence-transformers |
| Cross-Encoder Reranker | BAAI/bge-reranker-v2-m3 | Local GPU inference via transformers |
| LLM (Tutor Agent) | Groq | Llama 3.3 70B Versatile |
| LLM (Doubt Solver) | Google Gemini | Gemini 1.5 Flash / Pro |
| Package Manager | uv | Rust-based Python package management (Astral) |
| Frontend | Vanilla HTML/CSS/JS | Dark-themed UI with glassmorphism design |

**Model Evolution:** The embedding system was migrated from Ollama (`nomic-embed-text`, 768-dim) to Hugging Face BGE-M3 (1024-dim, sliced to 768-dim) for improved retrieval accuracy and multilingual support. The retrieval pipeline was upgraded from naive vector search to a full hybrid RAG system with RRF fusion and cross-encoder reranking.

---

## Project Structure

```
Intel/
├── AGENTS.md                          # Project specification
├── README.md
├── pyproject.toml
├── requirements.txt
├── run_server.py                      # Application entry point
│
├── api/
│   └── main.py                        # FastAPI route definitions
│
├── core/
│   ├── simple_auth.py                 # Session-based authentication
│   └── database/
│       ├── config.py                  # Supabase connection configuration
│       ├── manager.py                 # PDFDatabaseManager (all DB operations)
│       ├── setup.sql                  # Initial database schema
│       ├── migration_tutor_profiles.sql
│       ├── migration_user_pdfs.sql
│       └── run_migrations.py
│
├── modules/
│   ├── agents/
│   │   ├── retrieval_agent.py         # Hybrid RAG, RRF fusion, cross-encoder reranking
│   │   └── tutor_agent.py             # Teaching, quiz generation, evaluation
│   ├── doubt_solver/
│   │   └── services/                  # Legacy Q&A pipeline
│   └── pdf_processor/
│       ├── models/pdf_models.py       # Pydantic data models
│       └── services/                  # Text extraction, embedding generation
│
├── utils/
│   └── performance_monitor.py         # PDF pipeline profiler
│
├── frontend/
│   ├── index.html / style.css / script.js   # Main application
│   └── auth.html / auth.css / auth.js       # Authentication pages
│
├── tests/
│   ├── test_retrieval.py              # Retrieval agent integration test
│   ├── test_verify_tutor.py           # Agent initialization verification
│   └── check_db.py                    # Database inspection utility
│
└── docs/                              # Design documentation (not tracked in git)
    ├── system_architecture.md
    ├── implementation.md
    ├── learning.md
    └── future_extensions_research.md
```

---

## API Reference

### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/auth/register` | Register a new user |
| `POST` | `/api/v1/auth/login` | Authenticate with email and password |
| `POST` | `/api/v1/auth/logout` | Terminate current session |
| `GET` | `/api/v1/auth/profile` | Retrieve authenticated user profile |
| `POST` | `/api/v1/auth/change-password` | Update password |

### Tutoring
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/tutor/start-lesson` | Begin a structured lesson on a concept |
| `POST` | `/api/v1/tutor/chat` | Continue conversation during a lesson or doubt-solving turn |
| `POST` | `/api/v1/tutor/quiz` | Generate quiz questions (MCQ, subjective, coding) |
| `POST` | `/api/v1/tutor/evaluate` | Submit an answer for rubric-based evaluation |

### Student Profile
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/profile/mastery` | Retrieve mastery scores for all tested concepts |
| `GET` | `/api/v1/profile/preferences` | Retrieve learning preferences |
| `POST` | `/api/v1/profile/preferences` | Update learning preferences |

### PDF Management
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/pdfs/upload` | Upload and process a PDF document |
| `GET` | `/api/v1/pdfs` | List all PDFs for the authenticated user |
| `GET` | `/api/v1/pdfs/{pdf_id}` | Retrieve details for a specific PDF |
| `DELETE` | `/api/v1/pdfs/{pdf_id}` | Delete a PDF and its associated chunks |
| `GET` | `/api/v1/pdfs/stats` | Retrieve PDF processing statistics |

### Legacy Doubt Solver
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/ask` | Submit a document-grounded question |
| `GET` | `/api/v1/analyze/{question}` | Analyze question intent and complexity |

---

## Getting Started

### Prerequisites
- Python 3.11+
- CUDA-capable GPU (required for local BGE-M3 embeddings and cross-encoder reranking)
- [Supabase](https://supabase.com) project with the pgvector extension enabled
- [Groq API Key](https://console.groq.com)
- [Google Gemini API Key](https://aistudio.google.com/apikey)

### Installation

```bash
git clone https://github.com/Aravind556/Intel.git
cd Intel

# Create and activate virtual environment
uv venv .venv
source .venv/bin/activate

# Install dependencies
uv pip install -r requirements.txt
```

### Configuration

Create a `.env` file in the project root:

```env
SUPABASE_URL=<your_supabase_project_url>
SUPABASE_KEY=<your_supabase_anon_key>
SUPABASE_SERVICE_KEY=<your_supabase_service_role_key>
GROQ_API_KEY=<your_groq_api_key>
GEMINI_API_KEY=<your_gemini_api_key>
```

### Running the Server

```bash
python run_server.py
```

| Resource | URL |
|----------|-----|
| Application | http://localhost:8000/frontend |
| API Documentation | http://localhost:8000/docs |
| Health Check | http://localhost:8000/health |

---

## Future Extensions

The architecture is designed to support the following capabilities without requiring major redesign:

- **Voice Conversations** — Web Speech API for real-time STT with Faster-Whisper server-side fallback
- **OCR for Scanned PDFs** — Tesseract, EasyOCR, or Surya integration as a fallback in the text extraction pipeline
- **Diagram Explanation** — Multimodal LLM support for visual content understanding
- **Knowledge Graphs** — Structured concept relationship mapping across textbooks
- **Adaptive Revision Planning** — Spaced repetition scheduling based on mastery decay curves

---

## License

This project is developed as part of the Intel AIoT initiative.

## Contact

For issues or feedback, please open an [issue](https://github.com/Aravind556/Intel/issues).
