# 📚 Notionary: AI-Powered Interactive Learning Assistant

## 🚀 Overview

**Notionary** is an advanced, AI-powered backend platform that empowers educators and students by enabling real-time, document-specific doubt resolution through LLMs and secure vector search. Built with **FastAPI**, **Ollama**, **Google Gemini** and **Supabase**, this system is designed to handle contextual Q\&A from uploaded PDFs with high precision and strict data isolation.

> "Notionary is not just an assistant—it's your classroom companion, ensuring every student gets the help they need from the material they trust."
> 

## 💡 Why Notionary Matters

Modern classrooms struggle with:

* ❓ **Generic Responses** from traditional AI tools
* 🧠 **Information Overload**
* 🔐 **Data Privacy Concerns**
* 🧪 **Hallucinations** in AI answers

**Notionary solves these problems through:**

* 🔍 Context-grounded answers using *only* user-uploaded content
* 🧬 Local embeddings via **Ollama** for performance and privacy
* 🔒 **Row-Level Security (RLS)** in Supabase for strict user isolation
* 🧠 LLMs (Gemini) instructed with **strict prompting** to avoid hallucination

## 🌟 Key Features

### 📄 Document-Specific QA

* Ask questions about specific PDFs or search across all documents
* Get source-cited responses from the relevant page and file

### 🤖 Local Embeddings (Ollama)

* 768-dimensional embeddings generated locally
* Fast and private with no cloud dependency

### 🧠 Gemini LLM Integration

* Accurate and concise answers
* Strict prompting to avoid general knowledge outside the document

### 🎯 Smart Context Retrieval

* Embedding-based semantic search
* Custom similarity threshold and chunk filtering

### 🌐 Enhanced Web Interface

* Upload, manage and interact with PDFs in a modern UI
* PDF selector with real-time document status

### 📊 Processing Dashboard

* Track upload, embedding, and availability status

### 🔒 Complete User Isolation

* Full RLS enforcement: each user sees only their own PDFs and data
* Secure authentication with Supabase JWT

### 🚫 Strict Document-Only Mode

* If LLM finds no relevant context, it **refuses** to generate general knowledge
* Clear citation and reference model for transparency

## 🏁 Quick Start Guide

### ✅ Prerequisites

* Python 3.8+
* [Ollama](https://ollama.ai/download)
* [Supabase](https://supabase.com)
* Google Gemini API Key (free tier available)

### 🔧 Installation Steps

#### 1. Install Ollama

```bash
# macOS
brew install ollama

# Windows
winget install ollama

# Linux
curl -fsSL https://ollama.ai/install.sh | sh
```

Start the Ollama service:

```bash
ollama serve
ollama pull nomic-embed-text
```

#### 2. Python Environment Setup

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

#### 3. Configuration

Create a `.env` file:

```env
SUPABASE_URL=your_url
SUPABASE_KEY=your_anon_key
SUPABASE_SERVICE_KEY=your_service_key
GEMINI_API_KEY=your_gemini_key
DATABASE_URL=postgresql://... (optional)
```

#### 4. Start the Server

```bash
ollama serve
python run_server.py
```

Visit:

* 🌐 UI: `http://localhost:8000/frontend`
* 📚 API Docs: `http://localhost:8000/docs`
* 💚 Health: `http://localhost:8000/health`


## ❓ How to Use

### 📤 Upload PDFs

* Drag & drop files into the UI
* Embeddings are generated using Ollama
* Each file is user-scoped

### 💬 Ask Questions

**Option A: Web UI**

* Select a document and type a query
* Get sourced answers

**Option B: API**

```bash
curl -X POST "http://localhost:8000/api/v1/ask" -H "Content-Type: application/json" -d '{"question": "What is X?", "document_id": "..."}'
```

### 🚫 Strict Mode Example

> "Who is Ramanujan?" → "The selected document does not contain information about Ramanujan."

## 🧬 Architecture

```
+------------+       REST        +-----------+
|  Frontend  | <---------------> |  FastAPI  |
+------------+                   +-----------+
                                  |   |   |
                             Embedding  LLM
                             (Ollama)  (Gemini)
                                  |
                            +-----------+
                            | Supabase  |
                            +-----------+
```

## 🛠️ Project Structure

```
ai-tutor-backend/
├── api/                      # FastAPI routes
├── core/                     # DB + config
├── modules/                  # PDF and AI logic
├── frontend/                 # Static web interface
├── tests/                    # Test suite
├── run_server.py             # Entry point
└── .env                      # Environment vars
```

## 🧪 Test Coverage

* ✅ PDF Upload
* ✅ User RLS Enforcement
* ✅ Document-only LLM Answers
* ✅ No General Knowledge Leakage
* ✅ Chunk Filtering

Test scripts:

* `test_strict_document_mode.py`
* `test_subjects_endpoint.py`
* `debug_document_restriction.py`

## 📈 Scaling & Cost

* **Local Embeddings**: Free with Ollama
* **Gemini API**: Free tier (15 req/min)
* **Supabase Free Tier**: 500MB storage, 2GB bandwidth

Estimated Monthly Cost: `$0 – $3` for moderate usage

## 🔮 Future Plans

* [ ] Mobile App
* [ ] Add Proctored Mode for examinations
* [ ] Analytics Dashboard
* [ ] Claude / GPT Integration
* [ ] Multi-language Support
* [ ] Teacher Dashboard

## 🤝 Contributing

PRs are welcome! Please follow conventions, write clean code and add tests.

## 📬 Contact

For support or feedback:

* Open an [issue](https://github.com/Aravind556/Intel/issues)
