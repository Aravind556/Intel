"""
PDF Processing Pipeline

Main service that orchestrates the complete PDF processing workflow.
"""

import logging
import os
import time
import tempfile
from typing import Optional, IO, Dict, Any
from datetime import datetime
from ..models.pdf_models import (
    PDFDocument, PDFChunk, ProcessingStatus, 
    ProcessingResponse, ProcessingError
)
from .text_extractor import PDFTextExtractor
from .embedding_generator import EmbeddingGenerator
from core.database.manager import PDFDatabaseManager

logger = logging.getLogger(__name__)


class PDFProcessor:
    """Main PDF processing pipeline that coordinates all processing steps."""
    
    def __init__(self):
        from core.database.config import DatabaseConfig
        self.text_extractor = PDFTextExtractor()
        self.embedding_generator = EmbeddingGenerator()
        db_config = DatabaseConfig()
        self.db_manager = PDFDatabaseManager(db_config)
    
    async def process_pdf(self, 
                         file_content: bytes,
                         original_filename: str,
                         subject: Optional[str] = None,
                         description: Optional[str] = None,
                         metadata: Optional[Dict[str, Any]] = None,
                         user_id: Optional[str] = None) -> ProcessingResponse:
        """
        Process a PDF file through the complete pipeline.
        
        Args:
            file_content: Raw PDF file content as bytes
            original_filename: Original filename of the uploaded PDF
            subject: Subject category (optional)
            description: Description of the PDF content (optional)
            metadata: Additional metadata (optional)
            user_id: User ID for user-specific storage (required for new user-specific model)
            
        Returns:
            ProcessingResponse with results and status
        """
        start_time = time.time()
        pdf_id = None
        
        try:
            logger.info(f"📄 Starting PDF processing pipeline for: {original_filename}")
            logger.info(f"📊 File size: {len(file_content)} bytes")
            
            # Validate file content and size
            if not file_content or len(file_content) == 0:
                logger.error("❌ Empty file content provided")
                return ProcessingResponse(
                    success=False,
                    message="Empty file content provided",
                    error=ProcessingError(
                        error_type="VALIDATION_ERROR",
                        error_message="Empty file content"
                    )
                )
            
            # Check file size limit (50MB)
            max_file_size = 50 * 1024 * 1024  # 50MB
            if len(file_content) > max_file_size:
                logger.error(f"❌ File too large: {len(file_content)} bytes (max: {max_file_size})")
                return ProcessingResponse(
                    success=False,
                    message=f"File too large. Maximum size is {max_file_size // 1024 // 1024}MB",
                    error=ProcessingError(
                        error_type="VALIDATION_ERROR",
                        error_message=f"File size {len(file_content)} exceeds limit {max_file_size}"
                    )
                )
            
            # Basic PDF format validation
            if not file_content.startswith(b'%PDF'):
                logger.error("❌ Invalid PDF format")
                return ProcessingResponse(
                    success=False,
                    message="Invalid PDF format",
                    error=ProcessingError(
                        error_type="VALIDATION_ERROR",
                        error_message="File does not appear to be a valid PDF"
                    )
                )
            
            logger.info("✅ File validation passed")
            
            # Create PDF document record
            pdf_doc = PDFDocument(
                filename=self._generate_filename(original_filename),
                original_filename=original_filename,
                file_size=len(file_content),
                upload_timestamp=datetime.now(),
                processing_status=ProcessingStatus.PENDING,
                subject=subject,
                description=description,
                metadata=metadata or {}
            )
            
            logger.info("💾 Saving initial PDF document record...")
            # Save initial document record with user-specific access
            try:
                # Get or create subject for the user
                if user_id:
                    subject_name = subject or "General"
                    user_subject = await self.db_manager.get_subject_by_name(user_id, subject_name)
                    if not user_subject:
                        # Create subject for the user
                        subject_result = await self.db_manager.create_subject(
                            user_id=user_id,
                            name=subject_name,
                            description=f"Auto-created subject for {subject_name} uploads"
                        )
                        if subject_result.get('success'):
                            subject_id = subject_result['data']['id']
                        else:
                            raise Exception(f"Failed to create subject: {subject_result}")
                    else:
                        subject_id = user_subject['id']
                else:
                    # Fallback to system user (for backward compatibility)
                    subject_id = "6866db7e-0acc-43fe-8d02-1069d59a3798"  # Use existing "General" subject
                
                # Store user_id in metadata for the PDF document
                metadata_with_user = {**(metadata or {}), "user_id": user_id} if user_id else (metadata or {})
                
                pdf_record = await self.db_manager.create_pdf_record(
                    filename=pdf_doc.filename,
                    original_filename=pdf_doc.original_filename,
                    subject_id=subject_id,
                    file_path="",  # We're not storing files, just processing them
                    file_size=pdf_doc.file_size,
                    total_pages=getattr(pdf_doc, 'total_pages', None),
                    metadata=metadata_with_user,
                    user_id=user_id  # Pass user_id to database manager
                )
                print(f"DEBUG: pdf_record = {pdf_record}")
                if pdf_record.get('success'):
                    pdf_id = pdf_record['data']['id']
                else:
                    raise Exception(f"Database operation failed: {pdf_record}")
                logger.info(f"✅ PDF document saved with ID: {pdf_id} for user: {user_id}")
            except Exception as db_error:
                print(f"DEBUG: Database error: {str(db_error)}")
                raise db_error
            
            # Update status to processing
            logger.info("🔄 Updating status to PROCESSING...")
            await self.db_manager.update_pdf_processing_status(pdf_id, "processing")
            logger.info("✅ Status updated to PROCESSING")
            
            logger.info(f"🚀 Starting PDF processing for {original_filename} (ID: {pdf_id})")
            
            # Step 1: Extract text from PDF
            logger.info("📖 Step 1: Starting text extraction...")
            try:
                chunks_data, extraction_metadata = await self.text_extractor.extract_text(
                    file_content, original_filename
                )
                
                if not chunks_data:
                    raise ValueError("No text content extracted from PDF")
                
                logger.info(f"✅ Extracted {len(chunks_data)} text chunks from {original_filename}")
                logger.info(f"📊 Extraction metadata: {extraction_metadata}")
                
            except Exception as e:
                error_msg = f"Text extraction failed: {str(e)}"
                logger.error(f"❌ {error_msg}")
                await self.db_manager.update_pdf_processing_status(
                    pdf_id, "failed", error_message=error_msg
                )
                return ProcessingResponse(
                    success=False,
                    message=error_msg,
                    pdf_id=pdf_id,
                    error=ProcessingError(
                        error_type="TEXT_EXTRACTION_ERROR",
                        error_message=str(e)
                    )
                )
            
            # Step 2: Generate embeddings
            logger.info("🔮 Step 2: Starting embedding generation...")
            try:
                chunks_with_embeddings = await self.embedding_generator.generate_embeddings(chunks_data)
                logger.info(f"✅ Generated embeddings for {original_filename}")
                
            except Exception as e:
                logger.warning(f"⚠️ Embedding generation failed: {str(e)}. Proceeding without embeddings.")
                chunks_with_embeddings = chunks_data
                # Set embeddings to None for all chunks
                for chunk in chunks_with_embeddings:
                    chunk["embedding"] = None
            
            # Step 3: Create PDFChunk objects
            logger.info("🧩 Step 3: Creating PDF chunk objects...")
            pdf_chunks = []
            for i, chunk_data in enumerate(chunks_with_embeddings):
                logger.debug(f"Processing chunk {i+1}/{len(chunks_with_embeddings)}")
                pdf_chunk = PDFChunk(
                    pdf_id=pdf_id,
                    chunk_index=chunk_data["chunk_index"],
                    content=chunk_data["content"],
                    page_number=chunk_data["page_number"],
                    chunk_size=chunk_data["chunk_size"],
                    embedding=chunk_data.get("embedding"),
                    metadata={
                        "start_char": chunk_data.get("start_char"),
                        "end_char": chunk_data.get("end_char"),
                        "extraction_method": extraction_metadata.get("extraction_method")
                    }
                )
                pdf_chunks.append(pdf_chunk)
            
            logger.info(f"✅ Created {len(pdf_chunks)} PDF chunk objects")
            
            # Step 4: Save chunks to database
            logger.info(f"💾 Step 4: Saving {len(pdf_chunks)} chunks to database...")
            try:
                # Convert PDFChunk objects to dictionaries for database insertion
                # Only include fields that exist in the database schema
                chunk_dicts = []
                for chunk in pdf_chunks:
                    chunk_dict = {
                        "pdf_id": chunk.pdf_id,
                        "content": chunk.content,
                        "chunk_index": chunk.chunk_index,
                        "page_number": chunk.page_number,
                        "embedding": chunk.embedding,
                        "token_count": len(chunk.content.split()) if chunk.content else 0,  # Approximate token count
                        "metadata": chunk.metadata or {}
                    }
                    chunk_dicts.append(chunk_dict)
                
                success = await self.db_manager.batch_create_chunks(chunk_dicts)
                if not success.get('success', False):
                    raise ValueError(f"Failed to save chunks to database: {success.get('error', 'Unknown error')}")
                logger.info("✅ Chunks saved to database successfully")
                    
            except Exception as e:
                error_msg = f"Database save failed: {str(e)}"
                logger.error(f"❌ {error_msg}")
                await self.db_manager.update_pdf_processing_status(
                    pdf_id, "failed", error_message=error_msg
                )
                return ProcessingResponse(
                    success=False,
                    message=error_msg,
                    pdf_id=pdf_id,
                    error=ProcessingError(
                        error_type="DATABASE_ERROR",
                        error_message=str(e)
                    )
                )
            
            # Step 5: Update final status
            logger.info("🏁 Step 5: Updating final status to COMPLETED...")
            await self.db_manager.update_pdf_processing_status(
                pdf_id, "completed", chunk_count=len(pdf_chunks)
            )
            logger.info("✅ Status updated to COMPLETED")
            
            processing_time = time.time() - start_time
            
            logger.info(f"🎉 Successfully processed {original_filename} in {processing_time:.2f}s")
            logger.info(f"📊 Final stats: {len(pdf_chunks)} chunks processed")
            
            return ProcessingResponse(
                success=True,
                message=f"Successfully processed PDF with {len(pdf_chunks)} chunks",
                pdf_id=pdf_id,
                total_chunks=len(pdf_chunks),
                processing_time=processing_time
            )
            
        except Exception as e:
            processing_time = time.time() - start_time
            error_msg = f"Unexpected error during PDF processing: {str(e)}"
            
            # Update status if we have a PDF ID
            if pdf_id:
                await self.db_manager.update_pdf_processing_status(
                    pdf_id, "failed", error_message=error_msg
                )
            
            logger.error(f"PDF processing failed for {original_filename}: {str(e)}")
            
            return ProcessingResponse(
                success=False,
                message=error_msg,
                pdf_id=pdf_id,
                processing_time=processing_time,
                error=ProcessingError(
                    error_type="PROCESSING_ERROR",
                    error_message=str(e)
                )
            )
    
    async def get_pdf_info(self, pdf_id: str, user_id: Optional[str] = None) -> Optional[PDFDocument]:
        """Get information about a processed PDF - user-specific access."""
        return await self.db_manager.get_pdf_document(pdf_id, user_id=user_id)
    
    async def list_pdfs(self, limit: int = 50, offset: int = 0, user_id: Optional[str] = None):
        """List PDFs with user-specific filtering."""
        return await self.db_manager.list_pdf_documents(limit=limit, offset=offset, user_id=user_id)
    
    async def get_processing_stats(self, user_id: Optional[str] = None):
        """Get processing statistics - user-specific."""
        return await self.db_manager.get_processing_stats(user_id=user_id)
    
    async def delete_pdf(self, pdf_id: str, user_id: Optional[str] = None) -> bool:
        """Delete a PDF and all its chunks - user-specific access."""
        return await self.db_manager.delete_pdf_document(pdf_id, user_id=user_id)
    
    def _generate_filename(self, original_filename: str) -> str:
        """Generate a unique filename for storage."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        name_part = os.path.splitext(original_filename)[0]
        # Clean filename for safe storage
        clean_name = "".join(c for c in name_part if c.isalnum() or c in (' ', '-', '_')).rstrip()
        return f"{timestamp}_{clean_name}.pdf"
    
    def is_embedding_available(self) -> bool:
        """Check if embedding generation is available."""
        return self.embedding_generator.is_available()
