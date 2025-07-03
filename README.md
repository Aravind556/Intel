# AI Tutor Backend

A simplified AI-powered teaching assistant backend with PDF processing and doubt-solving capabilities using Google Gemini API.

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Supabase account (for vector database)
- Google Gemini API key

### Setup

```bash
# Create virtual environment
python -m venv venv
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Configuration

Create a `.env` file in the root directory:

```env
# Supabase Configuration
SUPABASE_URL=your_supabase_project_url
SUPABASE_KEY=your_supabase_anon_key

# Gemini API Key
GEMINI_API_KEY=your_gemini_api_key

# Database Configuration
DATABASE_URL=postgresql://postgres:your_password@db.your_project.supabase.co:5432/postgres
```

### Get API Keys

#### Supabase Setup:
1. Create an account at [supabase.com](https://supabase.com)
2. Create a new project
3. Go to Settings → API
4. Copy:
   - Project URL → `SUPABASE_URL`
   - anon/public key → `SUPABASE_KEY`
   - service_role key → `SUPABASE_SERVICE_KEY`
5. Go to Settings → Database
6. Copy connection string → `DATABASE_URL`

#### Google Gemini Setup (FREE):
1. Go to [Google AI Studio](https://aistudio.google.com/app/apikey)
2. Sign in with your Google account
3. Create a new API key
4. Copy the key → `GEMINI_API_KEY`
5. **No billing required** - Free tier includes 15 requests/minute!

### 4. Database Setup

The database schema will be automatically created when you first run the application.

### 5. Run the Application

```bash
# Start the server
python run_server.py
```

The application will be available at:
- **Frontend:** http://localhost:8000/frontend
- **API Documentation:** http://localhost:8000/docs
- **Health Check:** http://localhost:8000/health

## 📁 Project Structure

```
ai-tutor-backend/
├── core/                      # Core infrastructure
│   └── database/             # Database management
├── modules/                  # Feature modules
│   ├── doubt_solver/         # AI question answering
│   └── pdf_processor/        # PDF processing pipeline
├── api/                      # FastAPI endpoints
├── frontend/                 # Web interface
├── requirements.txt          # Dependencies
├── run_server.py            # Application entry point
└── .env                     # Environment variables
```

## 🔧 Features

### ✅ PDF Processing
- Upload and process PDF documents
- Text extraction and chunking
- **Local vector embeddings** (sentence-transformers)
- Automatic storage in Supabase

### ✅ AI Doubt Solver
- Question analysis and classification
- Context retrieval from PDFs
- AI-powered response generation with **Google Gemini**
- Source citations and suggestions

### ✅ Web Interface
- Modern, responsive design
- File upload with progress tracking
- PDF management dashboard
- Real-time processing status

## 💰 Cost Considerations

### **NEW: Gemini + Local Embeddings (Current)**
- **Embeddings**: FREE (local processing)
- **LLM**: FREE (15 requests/minute) then $0.35/1M tokens
- **Total**: $0-2/month for moderate usage 🎉

### Google Gemini Pricing (FREE TIER):
- **Gemini 1.5 Flash**: 15 requests/minute FREE
- **Gemini 1.5 Pro**: 2 requests/minute FREE
- **No billing required** for free usage!

### Typical Usage (FREE):
- **Small PDF processing**: Free with local embeddings
- **Question answering**: Free up to rate limits
- **Monthly cost**: $0 for moderate usage!

### Paid Alternatives Available:
- OpenAI GPT models
- Claude from Anthropic
- Local models via Ollama

## 🧪 Testing

```bash
# Test the PDF processing pipeline
python test_pipeline.py

# Check if everything is working
curl http://localhost:8000/health
```

## 📝 Usage Examples

### Upload a PDF via API:
```bash
curl -X POST "http://localhost:8000/api/v1/pdfs/upload" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@document.pdf" \
  -F "subject=Mathematics" \
  -F "description=Calculus textbook"
```

### Ask a Question:
```bash
curl -X POST "http://localhost:8000/api/v1/ask" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What is the derivative of x^2?",
    "user_id": "optional",
    "session_id": "optional"
  }'
```

## 🐛 Troubleshooting

### Common Issues:

1. **Gemini API Error**: Check your API key
   - Get free key at aistudio.google.com/app/apikey
   - No billing setup required
   - Verify key is correctly set in .env

2. **Rate Limit Exceeded**: You've hit the free tier limit
   - Gemini Flash: 15 requests/minute
   - Wait a minute and try again
   - Consider upgrading to paid tier if needed

3. **Supabase Connection Error**: 
   - Verify your SUPABASE_URL and keys
   - Check if project is active
   - Ensure RLS policies are set up

4. **PDF Processing Stuck**:
   - Check server logs for errors
   - Verify file is a valid PDF
   - Ensure local embedding model downloads properly

5. **Import Errors**:
   - Install new dependencies: `pip install -r requirements.txt`
   - Activate virtual environment
   - Check Python version (3.8+)

## 🔒 Security Notes

- Never commit `.env` file to version control
- Use service keys only on server-side
- Regularly rotate API keys
- Monitor API usage and costs

## 🤝 Contributing

1. Fork the repository
2. Create feature branch
3. Make changes
4. Test thoroughly
5. Submit pull request

## 📞 Support

For questions or issues:
1. Check the troubleshooting section
2. Review server logs
3. Test with simple examples
4. Create an issue with details

---

**Happy coding! 🎉**
