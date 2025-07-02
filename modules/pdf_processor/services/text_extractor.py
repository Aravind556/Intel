"""
PDF Text Extractor

Handles extraction of text content from PDF files.
"""

import io
import logging
from typing import List, Dict, Any, Tuple
import PyPDF2
import pdfplumber
from ..models.pdf_models import ProcessingError

logger = logging.getLogger(__name__)


class PDFTextExtractor:
    """Extracts text content from PDF files with multiple fallback methods."""
    
    def __init__(self):
        self.chunk_size = 1000  # Default chunk size in characters
        self.chunk_overlap = 200  # Overlap between chunks
    
    async def extract_text(self, pdf_content: bytes, filename: str) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Extract text from PDF using multiple methods as fallbacks.
        
        Args:
            pdf_content: Raw PDF file content as bytes
            filename: Original filename for error reporting
            
        Returns:
            Tuple of (chunks_list, metadata_dict)
        """
        logger.info(f"📖 Starting text extraction for {filename}")
        logger.info(f"📊 PDF content size: {len(pdf_content)} bytes")
        
        try:
            # Try pdfplumber first (better for complex layouts)
            logger.info("🔍 Attempting extraction with pdfplumber...")
            chunks, metadata = await self._extract_with_pdfplumber(pdf_content)
            if chunks:
                logger.info(f"✅ Successfully extracted {len(chunks)} chunks from {filename} using pdfplumber")
                return chunks, metadata
                
        except Exception as e:
            logger.warning(f"⚠️ pdfplumber extraction failed for {filename}: {str(e)}")
            
        try:
            # Fallback to PyPDF2
            logger.info("🔍 Attempting extraction with PyPDF2...")
            chunks, metadata = await self._extract_with_pypdf2(pdf_content)
            if chunks:
                logger.info(f"✅ Successfully extracted {len(chunks)} chunks from {filename} using PyPDF2")
                return chunks, metadata
                
        except Exception as e:
            logger.error(f"All PDF extraction methods failed for {filename}: {str(e)}")
            raise ProcessingError(
                error_type="PDF_EXTRACTION_FAILED",
                error_message=f"Could not extract text from PDF: {str(e)}",
                stack_trace=str(e)
            )
    
    async def _extract_with_pdfplumber(self, pdf_content: bytes) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """Extract text using pdfplumber library."""
        chunks = []
        metadata = {
            "extraction_method": "pdfplumber",
            "total_pages": 0,
            "total_characters": 0
        }
        
        with io.BytesIO(pdf_content) as pdf_file:
            with pdfplumber.open(pdf_file) as pdf:
                metadata["total_pages"] = len(pdf.pages)
                
                all_text = ""
                for page_num, page in enumerate(pdf.pages, 1):
                    try:
                        page_text = page.extract_text() or ""
                        if page_text.strip():
                            all_text += f"\\n\\n--- Page {page_num} ---\\n\\n{page_text}"
                    except Exception as e:
                        logger.warning(f"Failed to extract text from page {page_num}: {str(e)}")
                        continue
                
                if not all_text.strip():
                    raise ValueError("No text content found in PDF")
                
                # Split into chunks
                chunks = self._create_chunks(all_text, metadata["total_pages"])
                metadata["total_characters"] = len(all_text)
                
        return chunks, metadata
    
    async def _extract_with_pypdf2(self, pdf_content: bytes) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """Extract text using PyPDF2 library."""
        chunks = []
        metadata = {
            "extraction_method": "PyPDF2", 
            "total_pages": 0,
            "total_characters": 0
        }
        
        with io.BytesIO(pdf_content) as pdf_file:
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            metadata["total_pages"] = len(pdf_reader.pages)
            
            all_text = ""
            for page_num, page in enumerate(pdf_reader.pages, 1):
                try:
                    page_text = page.extract_text() or ""
                    if page_text.strip():
                        all_text += f"\\n\\n--- Page {page_num} ---\\n\\n{page_text}"
                except Exception as e:
                    logger.warning(f"Failed to extract text from page {page_num}: {str(e)}")
                    continue
            
            if not all_text.strip():
                raise ValueError("No text content found in PDF")
            
            # Split into chunks
            chunks = self._create_chunks(all_text, metadata["total_pages"])
            metadata["total_characters"] = len(all_text)
            
        return chunks, metadata
    
    def _create_chunks(self, text: str, total_pages: int) -> List[Dict[str, Any]]:
        """Split text into overlapping chunks."""
        chunks = []
        text = text.strip()
        
        if len(text) <= self.chunk_size:
            # If text is smaller than chunk size, return as single chunk
            chunks.append({
                "content": text,
                "chunk_index": 0,
                "page_number": 1,  # Approximate
                "chunk_size": len(text),
                "start_char": 0,
                "end_char": len(text)
            })
            return chunks
        
        start = 0
        chunk_index = 0
        
        while start < len(text):
            # Calculate end position
            end = start + self.chunk_size
            
            # If we're not at the end, try to break at a sentence or word boundary
            if end < len(text):
                # Look for sentence ending
                sentence_end = text.rfind('.', start, end)
                if sentence_end > start:
                    end = sentence_end + 1
                else:
                    # Look for word boundary
                    word_end = text.rfind(' ', start, end)
                    if word_end > start:
                        end = word_end
            
            chunk_content = text[start:end].strip()
            if chunk_content:
                # Estimate page number based on position
                estimated_page = min(int((start / len(text)) * total_pages) + 1, total_pages)
                
                chunks.append({
                    "content": chunk_content,
                    "chunk_index": chunk_index,
                    "page_number": estimated_page,
                    "chunk_size": len(chunk_content),
                    "start_char": start,
                    "end_char": end
                })
                chunk_index += 1
            
            # Move start position (with overlap)
            start = end - self.chunk_overlap
            if start >= len(text):
                break
        
        return chunks
    
    def set_chunk_parameters(self, chunk_size: int, chunk_overlap: int):
        """Configure chunk size and overlap parameters."""
        self.chunk_size = max(100, chunk_size)  # Minimum chunk size
        self.chunk_overlap = min(chunk_overlap, chunk_size // 2)  # Overlap can't exceed half chunk size
