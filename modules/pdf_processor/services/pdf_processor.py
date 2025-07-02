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
from .database_manager import PDFDatabaseManager

logger = logging.getLogger(__name__)


class PDFProcessor:
    """Main PDF processing pipeline that coordinates all processing steps."""
    
    def __init__(self):
        self.text_extractor = PDFTextExtractor()
        self.embedding_generator = EmbeddingGenerator()
        self.db_manager = PDFDatabaseManager()
    
    async def process_pdf(self, 
                         file_content: bytes,
                         original_filename: str,
                         subject: Optional[str] = None,
                         description: Optional[str] = None,
                         metadata: Optional[Dict[str, Any]] = None) -> ProcessingResponse:
        """
        Process a PDF file through the complete pipeline.
        
        Args:
            file_content: Raw PDF file content as bytes
            original_filename: Original filename of the uploaded PDF
            subject: Subject category (optional)
            description: Description of the PDF content (optional)
            metadata: Additional metadata (optional)
            
        Returns:
            ProcessingResponse with results and status
        """
        start_time = time.time()
        pdf_id = None
        
        try:
            logger.info(f"📄 Starting PDF processing pipeline for: {original_filename}")
            logger.info(f"📊 File size: {len(file_content)} bytes")
            
            # Validate file content
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
            # Save initial document record
            pdf_id = await self.db_manager.save_pdf_document(pdf_doc)
            logger.info(f"✅ PDF document saved with ID: {pdf_id}")
            
            # Update status to processing
            logger.info("🔄 Updating status to PROCESSING...")
            await self.db_manager.update_pdf_status(pdf_id, ProcessingStatus.PROCESSING)
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
                await self.db_manager.update_pdf_status(
                    pdf_id, ProcessingStatus.FAILED, error_message=error_msg
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
                success = await self.db_manager.save_pdf_chunks(pdf_chunks)
                if not success:
                    raise ValueError("Failed to save chunks to database")
                logger.info("✅ Chunks saved to database successfully")
                    
            except Exception as e:
                error_msg = f"Database save failed: {str(e)}"
                logger.error(f"❌ {error_msg}")
                await self.db_manager.update_pdf_status(
                    pdf_id, ProcessingStatus.FAILED, error_message=error_msg
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
            await self.db_manager.update_pdf_status(
                pdf_id, ProcessingStatus.COMPLETED, total_chunks=len(pdf_chunks)
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
                await self.db_manager.update_pdf_status(
                    pdf_id, ProcessingStatus.FAILED, error_message=error_msg
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
    
    async def get_pdf_info(self, pdf_id: str) -> Optional[PDFDocument]:
        """Get information about a processed PDF."""
        return await self.db_manager.get_pdf_document(pdf_id)
    
    async def list_pdfs(self, limit: int = 50, offset: int = 0):
        """List processed PDFs with pagination."""
        return await self.db_manager.list_pdf_documents(limit, offset)
    
    async def get_processing_stats(self) -> Dict[str, Any]:
        """Get processing statistics."""
        return await self.db_manager.get_processing_stats()
    
    async def delete_pdf(self, pdf_id: str) -> bool:
        """Delete a PDF and all its chunks."""
        return await self.db_manager.delete_pdf_document(pdf_id)
    
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
