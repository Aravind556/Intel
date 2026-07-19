# AI Tutor — Learning Registry & Retrospective (Updated)

This document tracks all features added to the platform and documents structural mistakes, design gaps, and lessons learned.

---

## 1. Feature Registry

| Feature Name | Status | Description | Added In |
|---|---|---|---|
| **Ollama Local Embeddings** | Completed | Local 768-dim embedding generation (`nomic-embed-text`) for data privacy and low latency. | Initial Release |
| **PDF Extraction & Chunking** | Completed | Automated PDF ingestion, text extraction, semantic paragraph splitting, and token counts. | Initial Release |
| **User Data Isolation (RLS)** | Completed | Row-Level Security policy enforcement on Supabase tables to keep PDF libraries user-scoped. | Database Setup |
| **Simple Doubt Solver** | Completed | Basic endpoint (`/api/v1/ask`) returning context-grounded LLM answers from specific PDFs. | Core Release |
| **Concept Graph & Profiles** | Completed | Prerequisite schemas, student learning preferences, and mastery logs applied in Supabase. | Database Setup & Migration |
| **Agentic AI Tutor Loop** | Completed | Two-agent system (AITutorAgent + RetrievalAgent) built and connected to Groq. | Core Implementation |
| **Hybrid Search Support** | Completed | Cosine similarity vector search combined with full-text search and reranked in python. | Core Implementation |
| **Rust-based Package Management (uv)** | Completed | Transitioned package resolution and virtual environment runs to Astral's uv tool. | Tooling Update |


---

## 2. Retrospective: Previous Mistakes & Design Gaps

Prior to refining the AI Tutor specification, several structural weaknesses and architectural gaps were identified in the early prototype stage:

### 2.1 Naive Semantic Retrieval
* **Mistake**: Standard vector search queries returned fragmented chunks, selecting text segments simply because they contained similar keywords.
* **Pedagogical Impact**: Chunks were retrieved out of order, and the LLM attempted to explain advanced topics using isolated snippets. It lacked context about preceding sections, formulas, or prerequisite terms.
* **Correction**: Implementing **Hybrid Search** (combining PostgreSQL full-text search with vector similarity) and applying a **Cross-Encoder Reranker** to evaluate logical relevance rather than raw semantic distance.

### 2.2 Lack of Prerequisite Verification
* **Mistake**: The system introduced any requested concept immediately without checking whether the student possessed the foundational knowledge.
* **Pedagogical Impact**: Students became frustrated when presented with formulas or theorems whose components they had not yet studied.
* **Correction**: Integrated a progressive concept teaching flowchart. The AI Tutor Agent is instructed to identify prerequisite milestones in the curriculum text and verify or teach them before proceeding.

### 2.3 General Knowledge Hallucinations
* **Mistake**: When document retrieval was insufficient or returned empty results, the system filled the gap using general, pre-trained knowledge.
* **Pedagogical Impact**: This bypassed teacher-approved course materials and led to hallucinations or explanations that conflicted with the curriculum.
* **Correction**: Enforced strict prompting constraints and a hard grounding rule. If the Retrieval Agent returns empty results, the AI Tutor Agent must disclose the missing context instead of using general training assumptions.

### 2.4 Monolithic Bloated Pipelines
* **Mistake**: A single service attempted to handle user dialogue, execute database vector queries, format answers, generate quizzes, and evaluate responses.
* **Development Impact**: Prompts became large and fragile, database edits interfered with dialog flow, and debugging latency grew.
* **Correction**: Decoupled the backend into two distinct components: the **Retrieval Agent** (focuses solely on searching, combining strategies, and ranking) and the **AI Tutor Agent** (focuses on teaching, dialog, quiz construction, and evaluation).

### 2.5 Binary Grading (Correct/Incorrect)
* **Mistake**: Student response verification was treated as a binary classification check (i.e., is the student's answer correct or not).
* **Pedagogical Impact**: The system could not pinpoint *why* a student failed a quiz (e.g., misapplying a sign in math vs. not understanding the underlying formula).
* **Correction**: Implemented rubric-based evaluation. The AI Tutor Agent reviews answers against target rubrics, diagnoses specific misconceptions (Foundational, Execution, Logic, Vocabulary), and provides corrective feedback.
