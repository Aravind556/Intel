"""
FastAPI main application
"""
from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Form, Header, Cookie
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, Response, FileResponse
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
from simple_auth import SimpleAuth

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
auth_system = SimpleAuth()

# Authentication Models
class RegisterRequest(BaseModel):
    name: str
    email: str
    password: str
    role: str = "student"

class LoginRequest(BaseModel):
    email: str
    password: str

class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str

# Request/Response Models
class QuestionRequest(BaseModel):
    question: str
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    document_id: Optional[str] = None

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

# Authentication Models
class RegisterRequest(BaseModel):
    name: str
    email: str
    password: str
    role: str = "student"

class LoginRequest(BaseModel):
    email: str
    password: str

class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str

class SessionRequest(BaseModel):
    session_id: str

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
        print("⏳ PDF processor not fully initialized yet. Creating a new instance...")
        pdf_processor = PDFProcessor()
        print("✅ Created new PDF processor instance")
    return pdf_processor

# Authentication dependency
async def get_current_user(session_id: Optional[str] = Cookie(None)):
    """Get current user from session cookie"""
    if not session_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    user_data = await auth_system.get_user_from_session(session_id)
    
    if not user_data:
        raise HTTPException(status_code=401, detail="Invalid session")
    
    return user_data

# Optional authentication (for endpoints that work with or without auth)
async def get_current_user_optional(session_id: Optional[str] = Cookie(None)):
    """Get current user if session exists, otherwise return None"""
    if not session_id:
        return None
    
    user_data = await auth_system.get_user_from_session(session_id)
    return user_data

@app.on_event("startup")
async def startup_event():
    """Initialize components on startup"""
    global db_config, db_manager, response_generator
    try:
        print("\n🔄 Initializing database connection...")
        db_config = DatabaseConfig()
        print("✅ Database config initialized")
        
        print("🔄 Setting up database manager...")
        db_manager = PDFDatabaseManager(db_config)
        print("✅ Database manager ready")
        
        print("🔄 Preparing response generator...")
        response_generator = ResponseGenerator(db_manager)
        print("✅ Response generator ready")
        
        # Announce that we're starting server now without waiting for model downloads
        print("\n🚀 Server is ready - starting now!")
        print("⏳ Models will continue loading in the background.")
        print("⚠️ Some features may not be available until model initialization completes.")
        
        # Start model initialization in background using a separate thread to avoid blocking
        import threading
        thread = threading.Thread(target=lambda: _initialize_models_thread())
        thread.daemon = True
        thread.start()
        
    except Exception as e:
        print(f"\n❌ Failed to initialize app: {str(e)}\n")

def _initialize_models_thread():
    """Initialize models in the background after server starts (non-async version)"""
    global pdf_processor
    try:
        print("\n🔄 Initializing PDF processor (downloading models in background)...")
        pdf_processor = PDFProcessor()
        print("✅ PDF processor initialized")
        print("\n✅ All components initialized successfully!\n")
    except Exception as e:
        print(f"\n❌ Failed to initialize models: {str(e)}\n")

# Health check endpoint
@app.get("/")
async def root():
    return {"message": "AI Tutor Backend is running!", "status": "healthy"}

@app.get("/health")
async def health_check():
    """Simple health check endpoint"""
    return {
        "status": "healthy",
        "message": "AI Tutor Backend is running"
    }

@app.get("/api/v1/system/status")
async def get_detailed_system_status():
    """Get detailed system status with database stats"""
    try:
        db_mgr = await get_db_manager()
        stats = await db_mgr.get_processing_stats()
        return {
            "status": "healthy",
            "database": "connected",
            "stats": stats
        }
    except Exception as e:
        return {
            "status": "partial",
            "database": "error",
            "error": str(e),
            "stats": {"total_pdfs": 0, "processed_pdfs": 0}
        }

# Doubt Solver Endpoints
@app.post("/api/v1/ask", response_model=QuestionResponse)
async def ask_question(
    request: QuestionRequest,
    response_gen: ResponseGenerator = Depends(get_response_generator),
    current_user: dict = Depends(get_current_user)
):
    """
    Ask a question to the AI tutor - user-specific access
    """
    try:
        # Use authenticated user's ID
        user_id = current_user["user_id"]
        
        # Generate response
        result = await response_gen.solve_doubt(
            question=request.question,
            user_id=user_id,
            session_id=request.session_id,
            document_id=request.document_id
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
@app.post("/api/v1/pdfs/upload")
async def upload_pdf(
    file: UploadFile = File(...),
    subject: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    pdf_proc: PDFProcessor = Depends(get_pdf_processor),
    current_user: dict = Depends(get_current_user)
) -> ProcessingResponse:
    """Upload and process a PDF file - user-specific storage"""
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        logger.info(f"🚀 Received PDF upload request from user {current_user['user_id']}: {file.filename}")
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
        
        # Process the PDF with user context
        logger.info("🔄 Starting PDF processing pipeline...")
        result = await pdf_proc.process_pdf(
            file_content=file_content,
            original_filename=file.filename,
            subject=subject,
            description=description,
            user_id=current_user["user_id"]  # Pass user ID for user-specific storage
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
    pdf_proc: PDFProcessor = Depends(get_pdf_processor),
    current_user: dict = Depends(get_current_user)
) -> List[PDFDocument]:
    """List processed PDFs with pagination - user-specific access"""
    try:
        return await pdf_proc.list_pdfs(
            limit=limit, 
            offset=offset, 
            user_id=current_user["user_id"]  # Use user_id key from session
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list PDFs: {str(e)}")

@app.get("/api/v1/pdfs/stats")
async def get_pdf_stats(
    pdf_proc: PDFProcessor = Depends(get_pdf_processor),
    current_user: dict = Depends(get_current_user)
):
    """Get PDF processing statistics - user-specific"""
    try:
        return await pdf_proc.get_processing_stats(user_id=current_user["user_id"])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")

@app.get("/api/v1/pdfs/{pdf_id}")
async def get_pdf(
    pdf_id: str,
    pdf_proc: PDFProcessor = Depends(get_pdf_processor),
    current_user: dict = Depends(get_current_user)
) -> PDFDocument:
    """Get information about a specific PDF - user-specific access"""
    try:
        pdf_doc = await pdf_proc.get_pdf_info(pdf_id, user_id=current_user["user_id"])
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
    pdf_proc: PDFProcessor = Depends(get_pdf_processor),
    current_user: dict = Depends(get_current_user)
):
    """Delete a PDF and all its chunks - user-specific access"""
    try:
        success = await pdf_proc.delete_pdf(pdf_id, user_id=current_user["user_id"])
        if not success:
            raise HTTPException(status_code=404, detail="PDF not found or could not be deleted")
        return {"message": "PDF deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete PDF: {str(e)}")

@app.post("/api/v1/auth/register")
async def register_user(request: RegisterRequest, response: Response):
    """Register a new user"""
    try:
        result = await auth_system.register_user(
            name=request.name,
            email=request.email,
            password=request.password,
            role=request.role
        )
        
        if result["success"]:
            # Set session cookie for auto-login after registration
            response.set_cookie(
                key="session_id",
                value=result["session_id"],
                httponly=True,
                secure=False,  # Set to True in production with HTTPS
                samesite="lax"
            )
            return {
                "success": True,
                "message": result["message"],
                "user": result["user"]
            }
        else:
            raise HTTPException(status_code=400, detail=result["error"])
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Registration failed: {str(e)}")

@app.post("/api/v1/auth/login")
async def login_user(request: LoginRequest, response: Response):
    """Login user"""
    try:
        result = await auth_system.login_user(request.email, request.password)
        
        if result["success"]:
            # Set session cookie
            response.set_cookie(
                key="session_id",
                value=result["session_id"],
                httponly=True,
                secure=False,  # Set to True in production with HTTPS
                samesite="lax"
            )
            return {
                "success": True,
                "message": result["message"],
                "user": result["user"]
            }
        else:
            raise HTTPException(status_code=401, detail=result["error"])
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Login failed: {str(e)}")

@app.post("/api/v1/auth/logout")
async def logout_user(response: Response, session_id: Optional[str] = Cookie(None)):
    """Logout user"""
    try:
        if session_id:
            result = await auth_system.logout_user(session_id)
            # Clear session cookie
            response.delete_cookie(key="session_id")
            
            if result["success"]:
                return {"success": True, "message": result["message"]}
            else:
                return {"success": True, "message": "Logged out"}
        else:
            return {"success": True, "message": "No active session"}
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Logout failed: {str(e)}")

@app.get("/api/v1/auth/profile")
async def get_user_profile(current_user = Depends(get_current_user)):
    """Get current user profile"""
    return {"success": True, "user": current_user}

@app.post("/api/v1/auth/change-password")
async def change_password(
    request: ChangePasswordRequest,
    session_id: Optional[str] = Cookie(None)
):
    """Change user password"""
    try:
        if not session_id:
            raise HTTPException(status_code=401, detail="Not authenticated")
            
        result = await auth_system.change_password(
            session_id=session_id,
            old_password=request.old_password,
            new_password=request.new_password
        )
        
        if result["success"]:
            return {"success": True, "message": result["message"]}
        else:
            raise HTTPException(status_code=400, detail=result["error"])
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Password change failed: {str(e)}")

# Static file serving - only mount if directory exists
if os.path.exists("frontend"):
    app.mount("/static", StaticFiles(directory="frontend"), name="static")

@app.get("/", response_class=HTMLResponse)
async def root():
    """Redirect to frontend"""
    return HTMLResponse("""
    <html>
        <head>
            <title>AI Tutor</title>
            <meta http-equiv="refresh" content="0; url=/frontend/auth.html">
        </head>
        <body>
            <p>Redirecting to AI Tutor...</p>
        </body>
    </html>
    """)

@app.get("/frontend/auth.html", response_class=HTMLResponse)
async def auth_page():
    """Serve authentication page"""
    try:
        with open("frontend/auth.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Authentication page not found")

@app.get("/frontend/index.html", response_class=HTMLResponse)
async def app_page():
    """Serve main application page"""
    try:
        with open("frontend/index.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Application page not found")

@app.get("/frontend/{path:path}")
async def frontend_files(path: str):
    """Serve frontend static files"""
    try:
        # Handle empty path (directory request)
        if not path or path == "/":
            path = "auth.html"
            
        file_path = f"frontend/{path}"
        
        # Check if file exists
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail=f"File {path} not found")
        
        # Check if it's actually a file (not a directory)
        if not os.path.isfile(file_path):
            raise HTTPException(status_code=404, detail=f"Path {path} is not a file")
            
        if path.endswith('.html'):
            with open(file_path, "r", encoding="utf-8") as f:
                return HTMLResponse(content=f.read())
        elif path.endswith('.css'):
            with open(file_path, "r", encoding="utf-8") as f:
                return Response(content=f.read(), media_type="text/css")
        elif path.endswith('.js'):
            with open(file_path, "r", encoding="utf-8") as f:
                return Response(content=f.read(), media_type="application/javascript")
        else:
            # For other file types, return as FileResponse
            return FileResponse(file_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error serving file: {str(e)}")
