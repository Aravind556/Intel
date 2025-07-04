# AI Tutor Backend

A powerful AI-powered teaching assistant backend with **document-specific PDF processing** and intelligent doubt-solving capabilities using **Ollama local embeddings** and **Google Gemini LLM**.

## 🌟 Key Features

- 📄 **Document-Specific QA**: Ask questions about specific PDFs or search across all documents
- 🤖 **Local Embeddings**: Using Ollama for fast, private, local vector embeddings (768-dim)
- 🧠 **Google Gemini LLM**: Intelligent response generation with high-quality answers
- 🎯 **Smart Context Retrieval**: Advanced search with document filtering and relevance scoring
- 🌐 **Modern Web Interface**: Enhanced frontend with PDF selection and real-time processing
- 📊 **Processing Dashboard**: Upload, manage, and monitor PDF processing status

## 🚀 Quick Start

### Prerequisites
- **Python 3.8+**
- **Ollama** (for local embeddings)
- **Supabase account** (for vector database)
- **Google Gemini API key** (FREE tier available)

### 1. Install Ollama

**Windows:**
```bash
# Download and install from: https://ollama.ai/download
# Or use winget:
winget install ollama
```

**macOS:**
```bash
# Download from: https://ollama.ai/download
# Or use brew:
brew install ollama
```

**Linux:**
```bash
curl -fsSL https://ollama.ai/install.sh | sh
```

**Start Ollama service:**
```bash
ollama serve
```

**Pull the embedding model:**
```bash
ollama pull nomic-embed-text
```

### 2. Python Environment Setup

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configuration

Create a `.env` file in the root directory:

```env
# Supabase Configuration
SUPABASE_URL=your_supabase_project_url
SUPABASE_KEY=your_supabase_anon_key
SUPABASE_SERVICE_KEY=your_supabase_service_key

# Google Gemini API Key
GEMINI_API_KEY=your_gemini_api_key

# Database Configuration (optional, auto-configured from Supabase)
DATABASE_URL=postgresql://postgres:your_password@db.your_project.supabase.co:5432/postgres
```

### 4. Get API Keys

#### Supabase Setup:
1. Create an account at [supabase.com](https://supabase.com)
2. Create a new project
3. Go to Settings → API
4. Copy:
   - Project URL → `SUPABASE_URL`
   - anon/public key → `SUPABASE_KEY`
   - service_role key → `SUPABASE_SERVICE_KEY`
5. Go to Settings → Database
6. Copy connection string → `DATABASE_URL` (optional)

#### Google Gemini Setup (FREE):
1. Go to [Google AI Studio](https://aistudio.google.com/app/apikey)
2. Sign in with your Google account
3. Create a new API key
4. Copy the key → `GEMINI_API_KEY`
5. **No billing required** - Free tier includes 15 requests/minute!

### 5. Database Setup

The database schema will be automatically created when you first run the application. The system uses **768-dimensional vectors** optimized for Ollama embeddings.

### 6. Start the Server

```bash
# Ensure Ollama is running first:
ollama serve

# In another terminal, start the AI Tutor server:
python run_server.py
```

The application will be available at:
- **🌐 Frontend Interface:** http://localhost:8000/frontend
- **📚 API Documentation:** http://localhost:8000/docs  
- **💚 Health Check:** http://localhost:8000/health
- **📊 System Stats:** http://localhost:8000/api/v1/stats

## 🎯 How to Use

### 📄 Upload PDFs
1. Go to http://localhost:8000/frontend
2. Drag & drop or browse to select PDF files
3. Wait for processing (embeddings generated locally with Ollama)
4. PDFs appear in your document list

### ❓ Ask Questions

**Option A: Web Interface (Recommended)**
1. Select a specific PDF from the dropdown (optional)
2. Type your question
3. Click "Ask Question"
4. Get answers with source citations

**Option B: API Calls**
```bash
# Ask about a specific document
curl -X POST "http://localhost:8000/api/v1/ask" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Summarize the main points in this document",
    "document_id": "your-pdf-document-id"
  }'

# Search across all documents  
curl -X POST "http://localhost:8000/api/v1/ask" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What is machine learning?"
  }'
```

## 📁 Project Structure

```
ai-tutor-backend/
├── core/                      # Core infrastructure
│   ├── database/             # Database management & RPC functions
│   └── config/               # Configuration management
├── modules/                  # Feature modules
│   ├── doubt_solver/         # AI question answering with context retrieval
│   │   └── services/         # Context retrieval, response generation
│   └── pdf_processor/        # PDF processing pipeline
│       ├── services/         # PDF processing, Ollama embeddings
│       └── models/           # Data models and schemas
├── api/                      # FastAPI endpoints and routes
│   └── main.py              # Main API application with document-specific endpoints
├── frontend/                 # Enhanced web interface
│   ├── index.html           # Main interface with PDF selector
│   ├── script.js            # Frontend logic with document selection
│   └── style.css            # Modern responsive styling
├── requirements.txt          # Python dependencies (includes ollama)
├── run_server.py            # Application entry point
└── .env                     # Environment variables
```

## 🔧 Features

### ✅ Advanced PDF Processing
- **Local Ollama Embeddings**: Fast, private 768-dimensional vectors
- **Smart Text Extraction**: Robust PDF text extraction with metadata
- **Intelligent Chunking**: Context-aware text segmentation
- **Real-time Processing**: Live progress tracking and status updates
- **Batch Processing**: Handle multiple PDFs efficiently

### ✅ Document-Specific AI Doubt Solver
- **📋 Document Selection**: Choose specific PDFs or search all documents
- **🎯 Context-Aware Retrieval**: Advanced semantic search within selected documents
- **🧠 Intelligent Responses**: Google Gemini-powered answer generation
- **📖 Source Citations**: Detailed references with page numbers and relevance scores
- **🔄 Session Management**: Conversation context and follow-up support

### ✅ Enhanced Web Interface
- **🎨 Modern Design**: Clean, responsive interface with real-time updates
- **📄 PDF Selector**: Dynamic dropdown with processed document selection
- **📊 Processing Dashboard**: Upload progress, status monitoring, and file management
- **💡 Smart Examples**: Context-aware question suggestions
- **🔍 Search Indicators**: Visual feedback showing which documents were searched

### ✅ Robust Architecture
- **🏗️ Modular Design**: Clean separation of concerns with dependency injection
- **🔒 Type Safety**: Full typing support with Pydantic models
- **⚡ Performance**: Optimized database queries with vector similarity search
- **🛡️ Error Handling**: Comprehensive error handling and graceful fallbacks
- **📈 Scalable**: Ready for production deployment with proper logging

## 💰 Cost Considerations

### **Current Setup: Ollama + Gemini (Recommended)**
- **🆓 Embeddings**: Completely FREE (local Ollama processing)
- **🤖 LLM**: FREE tier (15 requests/minute) then $0.35/1M tokens
- **💾 Storage**: Supabase free tier (500MB, 2GB bandwidth)
- **📊 Total**: $0-3/month for moderate usage 🎉

### Google Gemini Pricing:
- **✨ Gemini 1.5 Flash**: 15 requests/minute FREE, then $0.35/$0.53 per 1M tokens
- **🚀 Gemini 1.5 Pro**: 2 requests/minute FREE, then $3.50/$10.50 per 1M tokens
- **📈 No billing required** for free tier usage!

### Typical Usage Costs (FREE Tier):
- **📄 PDF Processing**: FREE (local Ollama embeddings)
- **❓ Question Answering**: FREE up to rate limits (15 req/min)
- **💰 Monthly Cost**: $0 for light-moderate usage
- **🔄 Processing**: Unlimited local embedding generation

### Scaling Options:
- **📈 Increase Limits**: Enable billing for higher rate limits
- **🔄 Alternative LLMs**: Easy switch to OpenAI, Claude, or local models
- **⚡ Local Models**: Full offline operation with Ollama LLMs

## 🧪 Testing & Verification

### Quick Health Check:
```bash
# Verify server is running
curl http://localhost:8000/health

# Check system stats
curl http://localhost:8000/api/v1/stats

# List uploaded PDFs
curl http://localhost:8000/api/v1/pdfs
```

### Test Document-Specific QA:
```bash
# Upload a test PDF first, then:
curl -X POST "http://localhost:8000/api/v1/ask" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What are the main topics covered?",
    "document_id": "your-document-id-here"
  }'
```

### Verify Ollama Integration:
```bash
# Check if Ollama is running
ollama list

# Test embedding model
ollama run nomic-embed-text "test embedding"
```

## 📝 API Documentation

### Core Endpoints:

#### Upload PDF:
```bash
curl -X POST "http://localhost:8000/api/v1/pdfs/upload" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@document.pdf" \
  -F "subject=Mathematics" \
  -F "description=Calculus textbook"
```

#### List PDFs:
```bash
curl "http://localhost:8000/api/v1/pdfs"
```

#### Ask Question (Document-Specific):
```bash
curl -X POST "http://localhost:8000/api/v1/ask" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Explain the concept of derivatives",
    "document_id": "123e4567-e89b-12d3-a456-426614174000",
    "user_id": "optional"
  }'
```

#### Ask Question (All Documents):
```bash
curl -X POST "http://localhost:8000/api/v1/ask" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What is machine learning?",
    "user_id": "optional"
  }'
```

### Response Format:
```json
{
  "success": true,
  "session_id": "uuid",
  "question": "Your question",
  "answer": {
    "quick_answer": "Brief answer",
    "detailed_explanation": "Detailed explanation",
    "examples": "Relevant examples",
    "step_by_step": "Step-by-step guide"
  },
  "sources": {
    "primary_sources": [
      {
        "title": "Document name",
        "page": "1",
        "relevance": 0.95
      }
    ],
    "search_strategies": ["document_specific"]
  },
  "metadata": {
    "confidence_score": 0.92,
    "model_used": "gemini-1.5-flash"
  }
}
```

## 🐛 Troubleshooting

### Common Issues:

#### 1. **Ollama Connection Error**
```
Error: Failed to connect to Ollama
```
**Solution:**
- Ensure Ollama is installed and running: `ollama serve`
- Check if the service is running: `ollama list`
- Restart Ollama service if needed
- Verify the embedding model is downloaded: `ollama pull nomic-embed-text`

#### 2. **Gemini API Error**
```
Error: Invalid API key or rate limit exceeded
```
**Solution:**
- Verify your API key at [aistudio.google.com](https://aistudio.google.com/app/apikey)
- Check rate limits (15 requests/minute for free tier)
- Wait a minute and retry
- No billing setup required for free tier

#### 3. **Supabase Connection Error**
```
Error: Failed to connect to database
```
**Solution:**
- Verify SUPABASE_URL and SUPABASE_SERVICE_KEY in .env
- Check if your Supabase project is active
- Ensure RLS policies allow your operations
- Test connection with provided health endpoint

#### 4. **PDF Processing Stuck**
```
PDF processing status: pending
```
**Solution:**
- Check server logs for embedding generation errors
- Verify Ollama is running and accessible
- Ensure PDF is valid and readable
- Check available disk space for embedding storage

#### 5. **Document Not Found in Selector**
```
PDF uploaded but not showing in dropdown
```
**Solution:**
- Wait for processing to complete (check status in PDF list)
- Only processed PDFs appear in the selector
- Refresh the page to reload the PDF list
- Check processing status via API: `/api/v1/pdfs`

#### 6. **Empty Search Results**
```
No context found for document-specific search
```
**Solution:**
- Ensure the document is fully processed (status: completed)
- Try more general questions about the document content
- Check if the document contains searchable text
- Verify embeddings were generated successfully

### Debug Commands:

```bash
# Check system health
curl http://localhost:8000/health

# Verify Ollama status
ollama list
ollama ps

# Check embedding model
ollama show nomic-embed-text

# View server logs
python run_server.py  # Check console output

# Test embedding generation
curl -X POST "http://localhost:8000/api/v1/pdfs/upload" -F "file=@test.pdf"
```

## 🚀 Advanced Usage

### Custom Configuration:
```python
# Modify embedding settings in core/database/config.py
EMBEDDING_DIMENSIONS = 768  # Ollama nomic-embed-text
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200

# Customize Gemini model in response_generator.py
MODEL_NAME = "gemini-1.5-flash"  # or gemini-1.5-pro
```

### Deployment Options:
- **🐳 Docker**: Containerized deployment (Dockerfile included)
- **☁️ Cloud**: Deploy to AWS, GCP, or Azure
- **🔧 Local**: Run on local network for team access
- **📱 API-Only**: Use as backend for mobile/web apps

### Integration Examples:
```javascript
// Frontend JavaScript integration
async function askQuestion(question, documentId = null) {
    const response = await fetch('/api/v1/ask', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            question: question,
            document_id: documentId
        })
    });
    return await response.json();
}
```

## 🔒 Security & Privacy

- **🔐 Local Processing**: Embeddings generated locally with Ollama
- **🛡️ Data Privacy**: Your documents never leave your infrastructure
- **🔑 API Security**: Environment-based configuration
- **🚫 No External Data**: Embeddings stored in your Supabase instance
- **⚡ HTTPS Ready**: SSL/TLS support for production deployment

## 🤝 Contributing

1. **Fork** the repository
2. **Create** feature branch: `git checkout -b feature/amazing-feature`
3. **Make** your changes with proper testing
4. **Test** thoroughly with the test suite
5. **Commit** changes: `git commit -m 'Add amazing feature'`
6. **Push** to branch: `git push origin feature/amazing-feature`
7. **Submit** a Pull Request

### Development Setup:
```bash
# Install dev dependencies
pip install -r requirements-dev.txt

# Run tests
python -m pytest tests/

# Format code
black .
isort .

# Type checking
mypy .
```

## 📞 Support & Community

**For questions or issues:**
1. 📖 Check this README and troubleshooting section
2. 🔍 Search existing GitHub issues
3. 🆕 Create a new issue with detailed information
4. 💬 Join our community discussions

**When reporting issues, include:**
- Python version and OS
- Ollama version (`ollama --version`)
- Error messages and logs
- Steps to reproduce
- Configuration (without sensitive keys)

## 🎉 What's Next?

**Planned Features:**
- 🔄 **Multi-model Support**: Switch between different LLMs
- 📊 **Analytics Dashboard**: Usage stats and insights
- 🔗 **API Integrations**: Connect with external services
- 📱 **Mobile App**: Native mobile interface
- 🎯 **Advanced Search**: Semantic filters and faceted search
- 🤖 **Custom Models**: Train domain-specific embeddings

---

## 🌟 **Ready to Get Started?**

1. **Install Ollama**: `ollama serve` and `ollama pull nomic-embed-text`
2. **Set up environment**: Create `.env` with your API keys
3. **Start server**: `python run_server.py`
4. **Visit frontend**: http://localhost:8000/frontend
5. **Upload PDFs** and start asking questions!

**Happy learning with your AI Tutor! 🎓✨**
