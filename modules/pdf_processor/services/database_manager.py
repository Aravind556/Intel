"""
PDF Database Manager

Handles database operations for PDF documents and chunks.
"""

import logging
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple
from ..models.pdf_models import PDFDocument, PDFChunk, ProcessingStatus

logger = logging.getLogger(__name__)


class PDFDatabaseManager:
    """Manages database operations for PDF processing."""
    
    def __init__(self):
        from core.database.config import DatabaseConfig
        self.db_config = DatabaseConfig()
        # Use service client to bypass RLS for PDF processing
        self.client = self.db_config.service_client
    
    async def save_pdf_document(self, pdf_doc: PDFDocument) -> str:
        """
        Save PDF document metadata to database.
        
        Args:
            pdf_doc: PDFDocument instance
            
        Returns:
            PDF document ID
        """
        try:
            logger.info(f"💾 Starting to save PDF document: {pdf_doc.original_filename}")
            
            # Generate ID if not provided
            if not pdf_doc.id:
                pdf_doc.id = str(uuid.uuid4())
                logger.info(f"🔧 Generated new PDF ID: {pdf_doc.id}")
            
            # Create or get a default subject for general uploads
            logger.info(f"🔍 Getting or creating subject: {pdf_doc.subject or 'General'}")
            subject_id = await self._get_or_create_default_subject(pdf_doc.subject or "General")
            logger.info(f"✅ Subject ID: {subject_id}")
            
            # Map to existing database schema
            doc_data = {
                "id": pdf_doc.id,
                "filename": pdf_doc.filename,
                "original_filename": pdf_doc.original_filename,
                "subject_id": subject_id,  # Required for RLS
                "file_size": pdf_doc.file_size,
                "upload_date": pdf_doc.upload_timestamp.isoformat() if pdf_doc.upload_timestamp else datetime.now().isoformat(),
                "processing_status": pdf_doc.processing_status.value,
                "total_pages": pdf_doc.total_pages,
                "chunk_count": pdf_doc.total_chunks or 0,
                "processed": pdf_doc.processing_status == ProcessingStatus.COMPLETED,
                "processing_error": pdf_doc.processing_error,
                "metadata": {
                    **(pdf_doc.metadata or {}),
                    "subject": pdf_doc.subject,
                    "description": pdf_doc.description
                }
            }
            
            logger.info("💾 Inserting document record into pdf_documents table...")
            logger.debug(f"Document data: {doc_data}")
            
            # Insert into database using Supabase service client
            result = self.client.table("pdf_documents").insert(doc_data).execute()
            
            logger.info(f"✅ Saved PDF document {pdf_doc.filename} with ID {pdf_doc.id}")
            logger.debug(f"Database response: {result.data if result.data else 'No data returned'}")
            return pdf_doc.id
            
        except Exception as e:
            logger.error(f"❌ Failed to save PDF document: {str(e)}")
            raise
    
    async def _get_or_create_default_subject(self, subject_name: str) -> str:
        """Get or create a default subject for PDF uploads."""
        try:
            # First, try to get or create a default user for system uploads
            default_user_id = await self._get_or_create_system_user()
            
            # Check if subject already exists for this user
            result = self.client.table("subjects").select("id").eq("user_id", default_user_id).eq("name", subject_name).execute()
            
            if result.data:
                return result.data[0]["id"]
            
            # Create new subject
            subject_data = {
                "name": subject_name,
                "user_id": default_user_id,
                "description": f"Auto-created subject for {subject_name} uploads",
                "color": "#6366f1"  # Default color
            }
            
            result = self.client.table("subjects").insert(subject_data).execute()
            return result.data[0]["id"]
            
        except Exception as e:
            logger.error(f"Failed to create subject: {str(e)}")
            # Return a hardcoded UUID as fallback (this might fail due to FK constraint)
            return "00000000-0000-0000-0000-000000000000"
    
    async def _get_or_create_system_user(self) -> str:
        """Get or create a system user for PDF uploads."""
        try:
            system_email = "system@ai-tutor.local"
            
            # Check if system user exists
            result = self.client.table("users").select("id").eq("email", system_email).execute()
            
            if result.data:
                return result.data[0]["id"]
            
            # Create system user
            user_data = {
                "name": "System User",
                "email": system_email,
                "role": "system"
            }
            
            result = self.client.table("users").insert(user_data).execute()
            return result.data[0]["id"]
            
        except Exception as e:
            logger.error(f"Failed to create system user: {str(e)}")
            # Return a hardcoded UUID as fallback
            return "00000000-0000-0000-0000-000000000001"
    
    async def update_pdf_status(self, pdf_id: str, status: ProcessingStatus, 
                              total_chunks: Optional[int] = None, 
                              error_message: Optional[str] = None) -> bool:
        """
        Update PDF processing status.
        
        Args:
            pdf_id: PDF document ID
            status: New processing status
            total_chunks: Number of chunks created (if completed)
            error_message: Error message (if failed)
            
        Returns:
            True if update was successful
        """
        try:
            update_data = {
                "processing_status": status.value,
                "processed": status == ProcessingStatus.COMPLETED,
                "processing_error": error_message
            }
            
            if total_chunks is not None:
                update_data["chunk_count"] = total_chunks
            
            # Remove None values
            update_data = {k: v for k, v in update_data.items() if v is not None}
            
            result = self.client.table("pdf_documents").update(update_data).eq("id", pdf_id).execute()
            
            logger.info(f"Updated PDF {pdf_id} status to {status.value}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update PDF status: {str(e)}")
            return False
    
    async def save_pdf_chunks(self, chunks: List[PDFChunk]) -> bool:
        """
        Save PDF chunks to database.
        
        Args:
            chunks: List of PDFChunk instances
            
        Returns:
            True if all chunks were saved successfully
        """
        try:
            logger.info(f"💾 Starting to save {len(chunks)} PDF chunks to database...")
            
            if not chunks:
                logger.info("✅ No chunks to save, returning True")
                return True
            
            # Prepare chunk data for batch insert - use existing table schema with optimized batching
            logger.info("🔧 Preparing chunk data for optimized batch insert...")
            
            batch_size = 100  # Larger batch size for better performance
            total_inserted = 0
            
            for batch_start in range(0, len(chunks), batch_size):
                batch_end = min(batch_start + batch_size, len(chunks))
                current_batch = chunks[batch_start:batch_end]
                
                chunk_data = []
                for chunk in current_batch:
                    if not chunk.id:
                        chunk.id = str(uuid.uuid4())
                    
                    chunk_data.append({
                        "id": chunk.id,
                        "pdf_id": chunk.pdf_id,
                        "content": chunk.content,
                        "chunk_index": chunk.chunk_index,
                        "page_number": chunk.page_number,
                        "embedding": chunk.embedding,
                        "token_count": chunk.chunk_size,  # Approximate
                        "metadata": chunk.metadata or {}
                    })
                
                # Insert current batch
                batch_num = (batch_start // batch_size) + 1
                total_batches = (len(chunks) + batch_size - 1) // batch_size
                logger.info(f"💾 Inserting batch {batch_num}/{total_batches} ({len(chunk_data)} chunks)...")
                
                result = self.client.table("document_chunks").insert(chunk_data).execute()
                inserted_count = len(result.data) if result.data else 0
                total_inserted += inserted_count
                
                logger.info(f"✅ Batch {batch_num} inserted successfully ({inserted_count} records)")
            
            logger.info(f"✅ Successfully saved {total_inserted}/{len(chunks)} chunks to database")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save PDF chunks: {str(e)}")
            return False
    
    async def get_pdf_document(self, pdf_id: str) -> Optional[PDFDocument]:
        """
        Retrieve PDF document by ID.
        
        Args:
            pdf_id: PDF document ID
            
        Returns:
            PDFDocument instance or None if not found
        """
        try:
            result = self.client.table("pdf_documents").select("*").eq("id", pdf_id).execute()
            
            if result.data:
                data = result.data[0]
                return PDFDocument(
                    id=data["id"],
                    filename=data["filename"],
                    original_filename=data["original_filename"],
                    file_size=data["file_size"],
                    upload_timestamp=datetime.fromisoformat(data["upload_date"]) if data["upload_date"] else None,
                    processing_status=ProcessingStatus(data["processing_status"]),
                    total_pages=data["total_pages"],
                    total_chunks=data.get("chunk_count", 0),
                    subject=data.get("metadata", {}).get("subject"),
                    description=data.get("metadata", {}).get("description"),
                    processing_error=data["processing_error"],
                    metadata=data["metadata"]
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to retrieve PDF document: {str(e)}")
            return None
    
    async def list_pdf_documents(self, limit: int = 50, offset: int = 0) -> List[PDFDocument]:
        """
        List PDF documents with pagination.
        
        Args:
            limit: Maximum number of documents to return
            offset: Number of documents to skip
            
        Returns:
            List of PDFDocument instances
        """
        try:
            result = self.client.table("pdf_documents").select("*").order("upload_date", desc=True).limit(limit).offset(offset).execute()
            
            documents = []
            for data in result.data:
                documents.append(PDFDocument(
                    id=data["id"],
                    filename=data["filename"],
                    original_filename=data["original_filename"],
                    file_size=data["file_size"],
                    upload_timestamp=datetime.fromisoformat(data["upload_date"]) if data["upload_date"] else None,
                    processing_status=ProcessingStatus(data["processing_status"]),
                    total_pages=data["total_pages"],
                    total_chunks=data.get("chunk_count", 0),
                    subject=data.get("metadata", {}).get("subject"),
                    description=data.get("metadata", {}).get("description"),
                    processing_error=data["processing_error"],
                    metadata=data["metadata"]
                ))
            
            return documents
            
        except Exception as e:
            logger.error(f"Failed to list PDF documents: {str(e)}")
            return []
    
    async def get_processing_stats(self) -> Dict[str, Any]:
        """Get PDF processing statistics."""
        try:
            # Get document counts using the correct column names
            result = self.client.table("pdf_documents").select("processing_status, chunk_count").execute()
            
            total_pdfs = len(result.data)
            processed_pdfs = len([d for d in result.data if d["processing_status"] == "completed"])
            processing_pdfs = len([d for d in result.data if d["processing_status"] == "processing"])
            failed_pdfs = len([d for d in result.data if d["processing_status"] == "failed"])
            
            total_chunks = sum(d["chunk_count"] or 0 for d in result.data)
            avg_chunks_per_pdf = total_chunks / processed_pdfs if processed_pdfs > 0 else 0
            
            return {
                "total_pdfs": total_pdfs,
                "processed_pdfs": processed_pdfs,
                "processing_pdfs": processing_pdfs,
                "failed_pdfs": failed_pdfs,
                "total_chunks": total_chunks,
                "avg_chunks_per_pdf": round(avg_chunks_per_pdf, 2)
            }
            
        except Exception as e:
            logger.error(f"Failed to get processing stats: {str(e)}")
            return {
                "total_pdfs": 0,
                "processed_pdfs": 0,
                "processing_pdfs": 0,
                "failed_pdfs": 0,
                "total_chunks": 0,
                "avg_chunks_per_pdf": 0
            }
    
    async def delete_pdf_document(self, pdf_id: str) -> bool:
        """
        Delete PDF document and all its chunks.
        
        Args:
            pdf_id: PDF document ID
            
        Returns:
            True if deletion was successful
        """
        try:
            # Delete chunks first (foreign key constraint)
            self.client.table("document_chunks").delete().eq("pdf_id", pdf_id).execute()
            
            # Delete document
            self.client.table("pdf_documents").delete().eq("id", pdf_id).execute()
            
            logger.info(f"Deleted PDF document {pdf_id} and all its chunks")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete PDF document: {str(e)}")
            return False
