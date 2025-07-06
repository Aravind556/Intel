"""
Database manager for PDF storage and retrieval operations
"""
from typing import List, Dict, Any, Optional
from .config import DatabaseConfig

class PDFDatabaseManager:
    """Manager class for PDF storage and retrieval operations"""
    
    def __init__(self, db_config: DatabaseConfig):
        self.db_config = db_config
        self.client = db_config.client
        self.service_client = db_config.service_client
    
    # ===== USER MANAGEMENT =====
    
    async def create_user(self, name: str, email: str, role: str = "student") -> Dict[str, Any]:
        """Create a new user"""
        try:
            result = self.service_client.table("users").insert({
                "name": name,
                "email": email,
                "role": role
            }).execute()
            return {"success": True, "data": result.data[0]}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user by ID"""
        try:
            result = self.client.table("users").select("*").eq("id", user_id).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            print(f"Error getting user: {e}")
            return None
    
    # ===== SUBJECT MANAGEMENT =====
    
    async def create_subject(self, user_id: str, name: str, description: str = "", color: str = "#3B82F6") -> Dict[str, Any]:
        """Create a new subject for a user"""
        try:
            result = self.service_client.table("subjects").insert({
                "user_id": user_id,
                "name": name,
                "description": description,
                "color": color
            }).execute()
            return {"success": True, "data": result.data[0]}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def get_user_subjects(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all subjects for a user with PDF statistics"""
        try:
            # Use the correct parameter name that matches the SQL function
            result = self.client.rpc("get_user_subjects", {"p_user_id": user_id}).execute()
            return result.data if result.data else []
        except Exception as e:
            print(f"Error getting user subjects: {e}")
            return []
    
    async def get_subject_by_name(self, user_id: str, subject_name: str) -> Optional[Dict[str, Any]]:
        """Get subject by name for a specific user"""
        try:
            result = self.client.table("subjects").select("*").eq("user_id", user_id).eq("name", subject_name).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            print(f"Error getting subject: {e}")
            return None
    
    # ===== PDF DOCUMENT MANAGEMENT =====
    
    async def create_pdf_record(
        self, 
        filename: str, 
        original_filename: str, 
        subject_id: str, 
        file_path: str,
        file_size: int,
        total_pages: int = None,
        metadata: Dict[str, Any] = None,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a new PDF document record"""
        try:
            pdf_data = {
                "filename": filename,
                "original_filename": original_filename,
                "subject_id": subject_id,
                "file_path": file_path,
                "file_size": file_size,
                "total_pages": total_pages,
                "metadata": metadata or {}
            }
            
            # Add user_id if provided
            if user_id:
                pdf_data["user_id"] = user_id
            
            result = self.service_client.table("pdf_documents").insert(pdf_data).execute()
            return {"success": True, "data": result.data[0]}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def get_pdf_documents(self, subject_id: str) -> List[Dict[str, Any]]:
        """Get all PDF documents for a subject"""
        try:
            result = self.client.table("pdf_documents").select("*").eq("subject_id", subject_id).execute()
            return result.data if result.data else []
        except Exception as e:
            print(f"Error getting PDF documents: {e}")
            return []
    
    async def update_pdf_processing_status(
        self, 
        pdf_id: str, 
        status: str, 
        chunk_count: int = None,
        error_message: str = None
    ) -> bool:
        """Update PDF processing status"""
        try:
            update_data = {
                "processing_status": status,
                "processed": status == "completed"
            }
            
            if chunk_count is not None:
                update_data["chunk_count"] = chunk_count
            
            if error_message:
                update_data["processing_error"] = error_message
            
            # Use service client to bypass RLS for status updates
            result = self.service_client.table("pdf_documents").update(update_data).eq("id", pdf_id).execute()
            return True
        except Exception as e:
            print(f"Error updating PDF processing status: {e}")
            return False
    
    async def list_pdf_documents(self, limit: int = 50, offset: int = 0, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """List PDF documents with pagination and user-specific filtering"""
        try:
            # Use service client when user_id is provided to bypass RLS
            # This is safe because we're explicitly filtering by user_id
            client = self.service_client if user_id else self.client
            
            query = client.table("pdf_documents").select(
                "id, filename, original_filename, file_size, total_pages, upload_date, processed, processing_status, chunk_count, user_id"
            )
            
            # Apply user filtering if user_id is provided
            if user_id:
                query = query.eq("user_id", user_id)
            
            result = query.order("upload_date", desc=True).limit(limit).offset(offset).execute()
            
            # Map database fields to expected model fields
            documents = []
            for doc in result.data if result.data else []:
                # Use filename if available, otherwise use original_filename for both fields
                filename = doc.get('filename') or doc.get('original_filename', 'unknown.pdf')
                documents.append({
                    'id': doc.get('id'),
                    'filename': filename,
                    'original_filename': doc.get('original_filename', filename),
                    'file_size': doc.get('file_size', 0),
                    'total_pages': doc.get('total_pages'),
                    'upload_timestamp': doc.get('upload_date'),
                    'processing_status': doc.get('processing_status', 'pending'),
                    'total_chunks': doc.get('chunk_count', 0),
                    'processing_error': doc.get('processing_error'),
                    'metadata': doc.get('metadata', {}),
                    'user_id': doc.get('user_id')
                })
            
            return documents
        except Exception as e:
            print(f"Error listing PDF documents: {e}")
            return []
    
    async def get_pdf_document(self, pdf_id: str, user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get a specific PDF document with user access control"""
        try:
            # Use service client when user_id is provided to bypass RLS
            # This is safe because we're explicitly filtering by user_id
            client = self.service_client if user_id else self.client
            query = client.table("pdf_documents").select("*")
            
            if user_id:
                # Filter by both pdf_id and user_id to ensure user owns this PDF
                result = query.eq("id", pdf_id).eq("user_id", user_id).execute()
            else:
                # Admin/system access without user filtering
                result = query.eq("id", pdf_id).execute()
            
            if result.data:
                doc = result.data[0]
                return {
                    'id': doc.get('id'),
                    'filename': doc.get('filename') or doc.get('original_filename', 'unknown.pdf'),
                    'original_filename': doc.get('original_filename'),
                    'file_size': doc.get('file_size', 0),
                    'total_pages': doc.get('total_pages'),
                    'upload_timestamp': doc.get('upload_date'),
                    'processing_status': doc.get('processing_status', 'pending'),
                    'total_chunks': doc.get('chunk_count', 0),
                    'processing_error': doc.get('processing_error'),
                    'metadata': doc.get('metadata', {}),
                    'user_id': doc.get('user_id')
                }
            return None
        except Exception as e:
            print(f"Error getting PDF document: {e}")
            return None
    
    async def delete_pdf_document(self, pdf_id: str, user_id: Optional[str] = None) -> bool:
        """Delete a PDF document and all its chunks with user access control"""
        try:
            # First check if user owns this PDF (if user_id provided)
            if user_id:
                pdf_doc = await self.get_pdf_document(pdf_id, user_id)
                if not pdf_doc:
                    return False  # PDF not found or user doesn't own it
            
            # Delete document chunks first (due to foreign key constraint)
            self.client.table("document_chunks").delete().eq("pdf_id", pdf_id).execute()
            
            # Delete the PDF document
            if user_id:
                result = self.client.table("pdf_documents").delete().eq("id", pdf_id).eq("user_id", user_id).execute()
            else:
                result = self.client.table("pdf_documents").delete().eq("id", pdf_id).execute()
            
            return True
        except Exception as e:
            print(f"Error deleting PDF document: {e}")
            return False
    
    async def create_document_chunk(
        self,
        pdf_id: str,
        content: str,
        chunk_index: int,
        page_number: int = None,
        embedding: List[float] = None,
        token_count: int = None,
        metadata: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Create a new document chunk"""
        try:
            result = self.service_client.table("document_chunks").insert({
                "pdf_id": pdf_id,
                "content": content,
                "chunk_index": chunk_index,
                "page_number": page_number,
                "embedding": embedding,
                "token_count": token_count,
                "metadata": metadata or {}
            }).execute()
            return {"success": True, "data": result.data[0]}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def batch_create_chunks(self, chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create multiple document chunks in batch"""
        try:
            result = self.service_client.table("document_chunks").insert(chunks).execute()
            return {"success": True, "data": result.data, "count": len(result.data)}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def update_chunk_embedding(self, chunk_id: str, embedding: List[float]) -> bool:
        """Update embedding for a specific chunk"""
        try:
            result = self.client.table("document_chunks").update({
                "embedding": embedding
            }).eq("id", chunk_id).execute()
            return True
        except Exception as e:
            print(f"Error updating chunk embedding: {e}")
            return False
    
    # ===== VECTOR SEARCH FOR LLM RETRIEVAL =====
    
    async def search_documents_by_subject(
        self,
        query_embedding: List[float],
        subject_name: str,
        user_id: str,
        match_threshold: float = 0.75,
        match_count: int = 5
    ) -> List[Dict[str, Any]]:
        """Search for relevant document chunks by subject using vector similarity"""
        try:
            result = self.client.rpc("match_documents_by_subject", {
                "query_embedding": query_embedding,
                "search_subject_name": subject_name,
                "search_user_id": user_id,
                "match_threshold": match_threshold,
                "match_count": match_count
            }).execute()
            return result.data if result.data else []
        except Exception as e:
            print(f"Error in vector search: {e}")
            return []
    
    async def search_within_pdf(
        self,
        query_embedding: List[float],
        pdf_id: str,
        user_id: str,
        match_threshold: float = 0.75,
        match_count: int = 10
    ) -> List[Dict[str, Any]]:
        """Search within a specific PDF document - user-specific access"""
        try:
            # First verify the user owns this PDF
            pdf_info = await self.get_pdf_document(pdf_id, user_id)
            if not pdf_info:
                print(f"PDF {pdf_id} not found or not accessible by user {user_id}")
                return []
            
            # Use service_client to bypass RLS since we've already verified user access
            result = self.service_client.rpc("search_within_pdf", {
                "query_embedding": query_embedding,
                "pdf_document_id": pdf_id,
                "match_threshold": match_threshold,
                "match_count": match_count
            }).execute()
            
            # Convert the results to the expected format
            search_results = []
            if result.data:
                for row in result.data:
                    search_results.append({
                        "id": row.get("chunk_id"),
                        "content": row.get("content"),
                        "page_number": row.get("page_number"),
                        "similarity": row.get("similarity"),
                        "chunk_index": row.get("chunk_index"),
                        "document_filename": pdf_info.get("filename", "Unknown"),
                        "document_id": pdf_id
                    })
            
            return search_results
        except Exception as e:
            print(f"Error searching within PDF: {e}")
            return []
    
    # ===== PROCESSING QUEUE MANAGEMENT =====
    
    async def add_to_processing_queue(self, pdf_id: str) -> Dict[str, Any]:
        """Add PDF to processing queue"""
        try:
            result = self.service_client.table("processing_queue").insert({
                "pdf_id": pdf_id,
                "status": "queued"
            }).execute()
            return {"success": True, "data": result.data[0]}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def update_processing_status(
        self, 
        queue_id: str, 
        status: str, 
        error_message: str = None
    ) -> bool:
        """Update processing queue status"""
        try:
            update_data = {"status": status}
            
            if status == "processing":
                update_data["started_at"] = "now()"
            elif status in ["completed", "failed"]:
                update_data["completed_at"] = "now()"
            
            if error_message:
                update_data["error_message"] = error_message
            
            result = self.client.table("processing_queue").update(update_data).eq("id", queue_id).execute()
            return True
        except Exception as e:
            print(f"Error updating processing status: {e}")
            return False
    
    async def get_processing_stats(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Get processing statistics with optional user filtering"""
        try:
            # Use service client when user_id is provided to bypass RLS
            client = self.service_client if user_id else self.client
            
            if user_id:
                # Get stats for specific user using the user_id column
                pdf_result = client.table("pdf_documents").select(
                    "id, processed, processing_status, chunk_count"
                ).eq("user_id", user_id).execute()
            else:
                # Get system-wide stats
                pdf_result = client.table("pdf_documents").select(
                    "id, processed, processing_status, chunk_count"
                ).execute()
            
            pdfs = pdf_result.data if pdf_result.data else []
            
            total_pdfs = len(pdfs)
            processed_pdfs = sum(1 for pdf in pdfs if pdf.get('processed', False))
            total_chunks = sum(pdf.get('chunk_count', 0) for pdf in pdfs)
            failed_pdfs = sum(1 for pdf in pdfs if pdf.get('processing_status') == 'failed')
            
            return {
                "total_pdfs": total_pdfs,
                "processed_pdfs": processed_pdfs,
                "failed_pdfs": failed_pdfs,
                "total_chunks": total_chunks,
                "success_rate": (processed_pdfs / total_pdfs * 100) if total_pdfs > 0 else 0
            }
        except Exception as e:
            print(f"Error getting processing stats: {e}")
            return {"total_pdfs": 0, "processed_pdfs": 0, "failed_pdfs": 0, "total_chunks": 0, "success_rate": 0}
    
    # ===== UTILITY FUNCTIONS =====
    
    async def get_pdf_overview(self) -> List[Dict[str, Any]]:
        """Get overview of all PDFs in the system"""
        try:
            result = self.client.table("pdf_documents").select(
                "id, original_filename, processing_status, chunk_count, upload_date"
            ).order("upload_date", desc=True).execute()
            return result.data if result.data else []
        except Exception as e:
            print(f"Error getting PDF overview: {e}")
            return []
