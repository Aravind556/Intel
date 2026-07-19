# AI Tutor — Implementation Blueprint (Updated)

This document details the code refactoring plan to align the platform with the updated two-agent cooperative architecture (AI Tutor Agent + Retrieval Agent).

---

## 1. Directory Structure Changes

The backend services will be organized into a simplified `modules/agents/` package containing the AI Tutor Agent and the Retrieval Agent.

```diff
  ai-tutor-backend/
  ├── api/
  │   ├── __init__.py
  │   └── main.py                 # <-- Add Tutor conversational, quiz, and evaluation routes
  ├── core/
  │   ├── __init__.py
  │   └── database/
  │       ├── __init__.py
  │       ├── config.py
  │       ├── manager.py          # <-- Add methods for hybrid retrieval and profile data
  │       ├── setup.sql
+ │       └── migration_tutor_profiles.sql  # <-- SQL file for student tracking tables
  ├── modules/
  │   ├── __init__.py
+ │   ├── agents/                 # <-- Core Agent orchestrators
+ │   │   ├── __init__.py
+ │   │   ├── tutor_agent.py      # <-- AI Tutor Agent (Dialogue, Explanation, Quizzes, Evaluation)
+ │   │   └── retrieval_agent.py  # <-- Retrieval Agent (Strategy router, Hybrid Search, Reranker)
  │   ├── doubt_solver/           # <-- Existing package (to be deprecated or integrated)
  │   └── pdf_processor/          # <-- Keeps PDF text processing & chunk vectorization
  ├── .env
  ├── implementation.md
  └── learning.md
```

---

## 2. Database Layer Extensions (`core/database/`)

### 2.1 Schema Migration (`core/database/migration_tutor_profiles.sql`)
To support the conversational history, learning state, and progress profiling of the AI Tutor:
```sql
-- 1. Student Profiles Table
CREATE TABLE student_profiles (
    id UUID REFERENCES users(id) ON DELETE CASCADE PRIMARY KEY,
    learning_preferences JSONB DEFAULT '{
        "analogy_style": "practical",
        "explanation_depth": "medium",
        "coding_language": "python"
    }'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 2. Lesson Progress & Mastery Tracking
CREATE TABLE student_topic_mastery (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    student_id UUID REFERENCES users(id) ON DELETE CASCADE NOT NULL,
    concept_name VARCHAR(255) NOT NULL,
    mastery_score FLOAT DEFAULT 0.0 CHECK (mastery_score >= 0.0 AND mastery_score <= 1.0),
    times_tested INTEGER DEFAULT 0,
    last_tested_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    UNIQUE(student_id, concept_name)
);

-- 3. Quiz and Evaluation History
CREATE TABLE student_assessment_history (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    student_id UUID REFERENCES users(id) ON DELETE CASCADE NOT NULL,
    concept_name VARCHAR(255) NOT NULL,
    question_text TEXT NOT NULL,
    student_answer TEXT,
    is_correct BOOLEAN NOT NULL,
    score FLOAT,
    misconceptions_detected JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### 2.2 Manager Updates (`core/database/manager.py`)
Add methods supporting:
* **Hybrid Search Queries**:
  - `hybrid_search_chunks(query_embedding: List[float], query_text: str, subject_id: UUID, match_count: int) -> List[Dict]`: Executes a combined SQL query merging BM25 full-text matching with dense vector similarity.
* **Student Progress Queries**:
  - `get_student_preferences(user_id: UUID) -> Dict`
  - `get_mastery_record(user_id: UUID, concept: str) -> Dict`
  - `update_mastery_record(user_id: UUID, concept: str, score: float) -> None`
  - `log_assessment(user_id: UUID, assessment: Dict) -> None`

---

## 3. Agent Implementation Layer (`modules/agents/`)

### 3.1 Retrieval Agent (`modules/agents/retrieval_agent.py`)
* **Class**: `RetrievalAgent`
* **Workflow**:
  1. Accepts requests detailing the target query, filters, and intent.
  2. Routes structured queries (e.g. "Chapter 4") directly to metadata filters.
  3. Executes `hybrid_search_chunks` for natural language conceptual queries.
  4. Runs a Cross-Encoder reranking model to prioritize chunks.
  5. Returns a structured payload mapping matching content, citations, and metadata.

### 3.2 AI Tutor Agent (`modules/agents/tutor_agent.py`)
* **Class**: `AITutorAgent`
* **Workflow**:
  1. **Tutoring Loop**: Coordinates dialog states, requests context from `RetrievalAgent`, explains concepts step-by-step, includes analogies and worked examples, and delivers a comprehension check.
  2. **Doubt Solving Loop**: Takes conceptual, factual, or applied student questions, requests context from `RetrievalAgent`, and returns sourced, cited answers.
  3. **Assessment Loop**: Generates MCQ, subjective, or coding questions.
  4. **Evaluation Loop**: Compares student responses against rubrics using LLM grading prompts, identifies misconceptions, and updates the student profile database.

---

## 4. API Endpoints (`api/main.py`)

FastAPI will serve as the entry boundary, routing endpoints directly into `AITutorAgent`:

```python
# 1. Active Conversational Tutoring Endpoints
@app.post("/api/v1/tutor/start-lesson")
async def start_lesson(concept: str, current_user = Depends(get_current_user)):
    """Initialize a tutoring block for a given concept. Returns explanation & check."""
    # Calls AITutorAgent.start_lesson()
    pass

@app.post("/api/v1/tutor/chat")
async def tutor_chat(message: str, session_id: str, current_user = Depends(get_current_user)):
    """Converses with the tutor during a lesson or doubt-solving turn."""
    # Calls AITutorAgent.process_message()
    pass

# 2. Dynamic Assessment & Evaluation Endpoints
@app.post("/api/v1/tutor/quiz")
async def generate_quiz(concept: str, question_type: str = "mcq", current_user = Depends(get_current_user)):
    """Generate a calibrated question on the target concept."""
    # Calls AITutorAgent.generate_quiz()
    pass

@app.post("/api/v1/tutor/evaluate")
async def evaluate_answer(concept: str, question_text: str, student_answer: str, rubric: dict, current_user = Depends(get_current_user)):
    """Submit an answer to a quiz question. Returns a score and misconception diagnostic."""
    # Calls AITutorAgent.evaluate_answer()
    pass
```
