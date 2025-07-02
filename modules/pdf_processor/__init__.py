"""
PDF Processor Module

Complete PDF processing pipeline for the AI Tutor backend.
Handles PDF upload, text extraction, chunking, embedding generation, and storage.
"""

from .models import (
    PDFDocument,
    PDFChunk,
    ProcessingStatus,
    ProcessingError,
    UploadRequest,
    ProcessingResponse
)

from .services import (
    PDFTextExtractor,
    EmbeddingGenerator,
    PDFDatabaseManager, 
    PDFProcessor
)

__all__ = [
    # Models
    "PDFDocument",
    "PDFChunk",
    "ProcessingStatus", 
    "ProcessingError",
    "UploadRequest",
    "ProcessingResponse",
    
    # Services
    "PDFTextExtractor",
    "EmbeddingGenerator",
    "PDFDatabaseManager",
    "PDFProcessor"
]
