"""
FastAPI main application
"""
from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
import uuid
import os

from core.database.config import DatabaseConfig
from core.database.manager import PDFDatabaseManager
from modules.doubt_solver.services.response_generator import ResponseGenerator
from modules.pdf_processor.services.pdf_processor import PDFProcessor
from modules.pdf_processor.models.pdf_models import ProcessingResponse, PDFDocument

app = FastAPI(
    title="AI Tutor Backend",
    description="AI-powered teaching assistant with doubt solving capabilities",
    version="1.0.0"
)

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global variables for dependency injection
db_config = None
db_manager = None
response_generator = None
pdf_processor = None

# Request/Response Models
class QuestionRequest(BaseModel):
    question: str
    user_id: Optional[str] = None
    session_id: Optional[str] = None

class QuestionResponse(BaseModel):
    success: bool
    session_id: str
    question: str
    answer: Dict[str, Any]
    sources: Dict[str, Any]
    metadata: Dict[str, Any]
    next_steps: Dict[str, Any]
    error: Optional[str] = None

class UserCreateRequest(BaseModel):
    name: str
    email: str
    role: str = "student"

class SubjectCreateRequest(BaseModel):
    user_id: str
    name: str
    description: str = ""
    color: str = "#3B82F6"

# Dependency to get database manager
async def get_db_manager():
    global db_config, db_manager
    if db_manager is None:
        db_config = DatabaseConfig()
        db_manager = PDFDatabaseManager(db_config)
    return db_manager

# Dependency to get response generator
async def get_response_generator():
    global response_generator
    if response_generator is None:
        db_mgr = await get_db_manager()
        response_generator = ResponseGenerator(db_mgr)
    return response_generator

# Dependency to get PDF processor
async def get_pdf_processor():
    global pdf_processor
    if pdf_processor is None:
        pdf_processor = PDFProcessor()
    return pdf_processor

@app.on_event("startup")
async def startup_event():
    """Initialize components on startup"""
    global db_config, db_manager, response_generator, pdf_processor
    try:
        db_config = DatabaseConfig()
        db_manager = PDFDatabaseManager(db_config)
        response_generator = ResponseGenerator(db_manager)
        pdf_processor = PDFProcessor()
        print("✅ FastAPI app initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize app: {e}")

# Health check endpoint
@app.get("/")
async def root():
    return {"message": "AI Tutor Backend is running!", "status": "healthy"}

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        db_mgr = await get_db_manager()
        stats = await db_mgr.get_processing_stats()
        return {
            "status": "healthy",
            "database": "connected",
            "stats": stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")

# Doubt Solver Endpoints
@app.post("/api/v1/ask", response_model=QuestionResponse)
async def ask_question(
    request: QuestionRequest,
    response_gen: ResponseGenerator = Depends(get_response_generator)
):
    """
    Ask a question to the AI tutor
    """
    try:
        # Use default user ID if not provided
        user_id = request.user_id or "550e8400-e29b-41d4-a716-446655440000"
        
        # Generate response
        result = await response_gen.solve_doubt(
            question=request.question,
            user_id=user_id,
            session_id=request.session_id
        )
        
        if result.get("success", False):
            return QuestionResponse(
                success=True,
                session_id=result["session_id"],
                question=result["question"],
                answer=result.get("answer", {}),
                sources=result.get("sources", {}),
                metadata=result.get("metadata", {}),
                next_steps=result.get("next_steps", {})
            )
        else:
            # Return fallback response if main process failed
            fallback = result.get("fallback_response", {})
            return QuestionResponse(
                success=False,
                session_id=result.get("session_id", str(uuid.uuid4())),
                question=request.question,
                answer=fallback.get("answer", {}),
                sources=fallback.get("sources", {}),
                metadata=fallback.get("metadata", {}),
                next_steps=fallback.get("next_steps", {}),
                error=result.get("error", "Unknown error occurred")
            )
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process question: {str(e)}")

@app.get("/api/v1/analyze/{question}")
async def analyze_question(question: str):
    """
    Analyze a question without generating full response
    """
    try:
        from modules.doubt_solver.services.question_processor import QuestionProcessor
        processor = QuestionProcessor()
        analysis = await processor.analyze_question(question)
        
        # Convert enum values to strings for JSON serialization
        return {
            "question": question,
            "analysis": {
                "question_type": analysis["question_type"].value,
                "difficulty": analysis["difficulty"].value,
                "subject": analysis.get("subject"),
                "keywords": analysis.get("keywords", []),
                "intent": analysis.get("intent"),
                "requires_calculation": analysis.get("requires_calculation", False),
                "requires_visual": analysis.get("requires_visual", False)
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to analyze question: {str(e)}")

# User Management Endpoints
@app.post("/api/v1/users")
async def create_user(
    request: UserCreateRequest,
    db_mgr: PDFDatabaseManager = Depends(get_db_manager)
):
    """Create a new user"""
    try:
        result = await db_mgr.create_user(
            name=request.name,
            email=request.email,
            role=request.role
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create user: {str(e)}")

@app.get("/api/v1/users/{user_id}")
async def get_user(
    user_id: str,
    db_mgr: PDFDatabaseManager = Depends(get_db_manager)
):
    """Get user by ID"""
    try:
        user = await db_mgr.get_user(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return user
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get user: {str(e)}")

@app.get("/api/v1/users/{user_id}/subjects")
async def get_user_subjects(
    user_id: str,
    db_mgr: PDFDatabaseManager = Depends(get_db_manager)
):
    """Get all subjects for a user"""
    try:
        subjects = await db_mgr.get_user_subjects(user_id)
        return {"user_id": user_id, "subjects": subjects}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get subjects: {str(e)}")

@app.post("/api/v1/subjects")
async def create_subject(
    request: SubjectCreateRequest,
    db_mgr: PDFDatabaseManager = Depends(get_db_manager)
):
    """Create a new subject"""
    try:
        result = await db_mgr.create_subject(
            user_id=request.user_id,
            name=request.name,
            description=request.description,
            color=request.color
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create subject: {str(e)}")

# System Info Endpoints
@app.get("/api/v1/stats")
async def get_system_stats(db_mgr: PDFDatabaseManager = Depends(get_db_manager)):
    """Get system processing statistics"""
    try:
        stats = await db_mgr.get_processing_stats()
        overview = await db_mgr.get_pdf_overview()
        return {
            "processing_stats": stats,
            "pdf_count": len(overview),
            "system_status": "operational"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")

# PDF Processing Endpoints
@app.post("/api/v1/process-pdf")
async def process_pdf(
    file: UploadFile = File(...),
    user_id: str = Form(...),
    db_mgr: PDFDatabaseManager = Depends(get_db_manager),
    pdf_proc: PDFProcessor = Depends(get_pdf_processor)
):
    """Get system health and status"""
    try:
        db_mgr = await get_db_manager()
        pdf_proc = await get_pdf_processor()
        
        # Check database connection
        try:
            stats = await pdf_proc.get_processing_stats()
            db_status = "connected"
        except Exception:
            stats = {"total_pdfs": 0, "processed_pdfs": 0, "processing_pdfs": 0, 
                    "failed_pdfs": 0, "total_chunks": 0, "avg_chunks_per_pdf": 0}
            db_status = "disconnected"
        
        return {
            "status": "healthy",
            "database": db_status,
            "stats": stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")

# PDF Processing Endpoints
@app.post("/api/v1/pdfs/upload")
async def upload_pdf(
    file: UploadFile = File(...),
    subject: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    pdf_proc: PDFProcessor = Depends(get_pdf_processor)
) -> ProcessingResponse:
    """Upload and process a PDF file"""
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        logger.info(f"🚀 Received PDF upload request: {file.filename}")
        logger.info(f"📊 File size: {file.size} bytes")
        logger.info(f"📝 Subject: {subject}, Description: {description}")
        
        # Validate file type
        if not file.filename.lower().endswith('.pdf'):
            logger.error("❌ Invalid file type - not a PDF")
            raise HTTPException(status_code=400, detail="File must be a PDF")
        
        if file.size > 50 * 1024 * 1024:  # 50MB limit
            logger.error(f"❌ File too large: {file.size} bytes")
            raise HTTPException(status_code=400, detail="File size too large (max 50MB)")
        
        logger.info("✅ File validation passed")
        
        # Read file content
        logger.info("📖 Reading file content...")
        file_content = await file.read()
        logger.info(f"✅ Read {len(file_content)} bytes from file")
        
        # Process the PDF
        logger.info("🔄 Starting PDF processing pipeline...")
        result = await pdf_proc.process_pdf(
            file_content=file_content,
            original_filename=file.filename,
            subject=subject,
            description=description
        )
        
        logger.info(f"✅ PDF processing completed: {result.success}")
        logger.info(f"📊 Processing result: {result.message}")
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Unexpected error during PDF upload: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to process PDF: {str(e)}")

@app.get("/api/v1/pdfs")
async def list_pdfs(
    limit: int = 50,
    offset: int = 0,
    pdf_proc: PDFProcessor = Depends(get_pdf_processor)
) -> List[PDFDocument]:
    """List processed PDFs with pagination"""
    try:
        return await pdf_proc.list_pdfs(limit=limit, offset=offset)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list PDFs: {str(e)}")

@app.get("/api/v1/pdfs/stats")
async def get_pdf_stats(
    pdf_proc: PDFProcessor = Depends(get_pdf_processor)
):
    """Get PDF processing statistics"""
    try:
        return await pdf_proc.get_processing_stats()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")

@app.get("/api/v1/pdfs/{pdf_id}")
async def get_pdf(
    pdf_id: str,
    pdf_proc: PDFProcessor = Depends(get_pdf_processor)
) -> PDFDocument:
    """Get information about a specific PDF"""
    try:
        pdf_doc = await pdf_proc.get_pdf_info(pdf_id)
        if not pdf_doc:
            raise HTTPException(status_code=404, detail="PDF not found")
        return pdf_doc
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get PDF: {str(e)}")

@app.delete("/api/v1/pdfs/{pdf_id}")
async def delete_pdf(
    pdf_id: str,
    pdf_proc: PDFProcessor = Depends(get_pdf_processor)
):
    """Delete a PDF and all its chunks"""
    try:
        success = await pdf_proc.delete_pdf(pdf_id)
        if not success:
            raise HTTPException(status_code=404, detail="PDF not found or could not be deleted")
        return {"message": "PDF deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete PDF: {str(e)}")

# Serve static files (for the frontend)
if os.path.exists("frontend"):
    app.mount("/static", StaticFiles(directory="frontend"), name="static")
    
    @app.get("/frontend", response_class=HTMLResponse)
    async def serve_frontend():
        """Serve the frontend HTML"""
        try:
            with open("frontend/index.html", "r", encoding="utf-8") as f:
                return HTMLResponse(content=f.read())
        except FileNotFoundError:
            return HTMLResponse(content="<h1>Frontend not found</h1><p>Please create the frontend files.</p>")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
