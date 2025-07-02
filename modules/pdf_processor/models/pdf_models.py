"""
PDF Processing Data Models

Defines the data structures for PDF processing pipeline.
"""

from enum import Enum
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class ProcessingStatus(str, Enum):
    """PDF processing status enumeration."""
    PENDING = "pending"
    PROCESSING = "processing" 
    COMPLETED = "completed"
    FAILED = "failed"


class PDFDocument(BaseModel):
    """Model for PDF document metadata."""
    id: Optional[str] = None
    filename: str
    original_filename: str
    file_size: int
    upload_timestamp: Optional[datetime] = None
    processing_status: ProcessingStatus = ProcessingStatus.PENDING
    total_pages: Optional[int] = None
    total_chunks: Optional[int] = None
    subject: Optional[str] = None
    description: Optional[str] = None
    processing_error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class PDFChunk(BaseModel):
    """Model for PDF text chunks."""
    id: Optional[str] = None
    pdf_id: str
    chunk_index: int
    content: str
    page_number: int
    chunk_size: int
    embedding: Optional[List[float]] = None
    metadata: Optional[Dict[str, Any]] = None


class ProcessingError(BaseModel):
    """Model for processing errors."""
    error_type: str
    error_message: str
    stack_trace: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)


class UploadRequest(BaseModel):
    """Model for PDF upload requests."""
    subject: Optional[str] = None
    description: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class ProcessingResponse(BaseModel):
    """Model for processing responses."""
    success: bool
    message: str
    pdf_id: Optional[str] = None
    total_chunks: Optional[int] = None
    processing_time: Optional[float] = None
    error: Optional[ProcessingError] = None
