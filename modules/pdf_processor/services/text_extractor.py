"""
PDF Text Extractor

Handles extraction of text content from PDF files with automatic fallbacks.
"""

import io
import logging
import asyncio
from typing import List, Dict, Any, Tuple
import PyPDF2
import pdfplumber
from ..models.pdf_models import ProcessingError

logger = logging.getLogger(__name__)


class PDFTextExtractor:
    """
    Extracts text content from PDF files with multiple fallback methods.
    
    Features:
    - Multiple extraction methods with fallbacks (pdfplumber → PyPDF2 → basic)
    - Automatic timeout handling to prevent hanging on problematic PDFs
    - Chunking text for embedding and retrieval
    - Robust error handling with graceful degradation
    """
    
    def __init__(self):
        self.chunk_size = 2000  # Increased chunk size for better efficiency
        self.chunk_overlap = 150  # Reduced overlap
        self.extraction_timeout = 45  # Increased timeout for large PDFs
        self.max_file_size = 100 * 1024 * 1024  # Increased to 100MB limit
        self.max_pages = 1000  # Increased page limit
        self.max_chars_per_page = 15000  # Increased character limit
    
    async def extract_text(self, pdf_content: bytes, filename: str) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Extract text from PDF using multiple methods with fallbacks and timeouts.
        
        Args:
            pdf_content: Raw PDF file content as bytes
            filename: Original filename for error reporting
            
        Returns:
            Tuple of (chunks_list, metadata_dict)
        """
        logger.info(f"📖 Starting text extraction for {filename}")
        logger.info(f"📊 PDF content size: {len(pdf_content) // 1024} KB")
        
        # Safety check: file size limit
        if len(pdf_content) > self.max_file_size:
            error_msg = f"PDF file too large: {len(pdf_content) // 1024 // 1024}MB (max: {self.max_file_size // 1024 // 1024}MB)"
            logger.error(error_msg)
            return [{
                "content": f"PDF file '{filename}' is too large to process safely. Maximum size is {self.max_file_size // 1024 // 1024}MB.",
                "chunk_index": 0,
                "page_number": 1,
                "chunk_size": 50,
                "start_char": 0,
                "end_char": 50
            }], {
                "extraction_method": "size_limit_exceeded",
                "total_pages": 0,
                "error": error_msg
            }
        
        # Store errors for diagnostic purposes
        extraction_errors = []
        
        # Attempt pdfplumber extraction with timeout
        try:
            logger.info("🔍 Attempting extraction with pdfplumber (timeout: %ds)...", self.extraction_timeout)
            extraction_task = self._extract_with_pdfplumber(pdf_content)
            chunks, metadata = await asyncio.wait_for(extraction_task, timeout=self.extraction_timeout)
            
            if chunks:
                logger.info(f"✅ Successfully extracted {len(chunks)} chunks from {filename} using pdfplumber")
                return chunks, metadata
                
        except asyncio.TimeoutError:
            error_msg = f"⚠️ pdfplumber extraction timed out after {self.extraction_timeout}s for {filename}"
            logger.warning(error_msg)
            extraction_errors.append(f"pdfplumber error: Timed out after {self.extraction_timeout}s")
            
        except Exception as e:
            error_msg = f"⚠️ pdfplumber extraction failed for {filename}: {str(e)}"
            logger.warning(error_msg)
            extraction_errors.append(f"pdfplumber error: {str(e)}")
            
        # Attempt PyPDF2 extraction with timeout
        try:
            logger.info("🔍 Attempting extraction with PyPDF2 (timeout: %ds)...", self.extraction_timeout)
            extraction_task = self._extract_with_pypdf2(pdf_content)
            chunks, metadata = await asyncio.wait_for(extraction_task, timeout=self.extraction_timeout)
            
            if chunks:
                logger.info(f"✅ Successfully extracted {len(chunks)} chunks from {filename} using PyPDF2")
                return chunks, metadata
                
        except asyncio.TimeoutError:
            error_msg = f"⚠️ PyPDF2 extraction timed out after {self.extraction_timeout}s for {filename}"
            logger.warning(error_msg)
            extraction_errors.append(f"PyPDF2 error: Timed out after {self.extraction_timeout}s")
            
        except Exception as e:
            error_msg = f"⚠️ PyPDF2 extraction failed for {filename}: {str(e)}"
            logger.warning(error_msg)
            extraction_errors.append(f"PyPDF2 error: {str(e)}")
        
        # Use basic fallback extraction if all else fails
        logger.info("🔍 Using basic fallback extraction method")
        try:
            chunks, metadata = await self._extract_basic(pdf_content)
            logger.info(f"✅ Created fallback content for {filename}")
            
            # Add error information to metadata
            if extraction_errors:
                metadata["extraction_errors"] = extraction_errors
                metadata["extraction_note"] = "Using fallback content due to extraction failures"
            
            return chunks, metadata
                
        except Exception as e:
            logger.error(f"All PDF extraction methods failed for {filename}: {str(e)}")
            
            # Emergency fallback - never fail the PDF upload
            minimal_fallback = [{
                "content": f"This PDF ({filename}) could not be processed due to formatting issues.",
                "chunk_index": 0,
                "page_number": 1,
                "chunk_size": 60,
                "start_char": 0,
                "end_char": 60
            }]
            return minimal_fallback, {
                "extraction_method": "emergency_fallback", 
                "total_pages": 1, 
                "error": str(e),
                "extraction_errors": extraction_errors
            }
    
    async def _extract_with_pdfplumber(self, pdf_content: bytes) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """Extract text using pdfplumber library with robust error handling."""
        chunks = []
        metadata = {
            "extraction_method": "pdfplumber",
            "total_pages": 0,
            "total_characters": 0
        }
        
        try:
            with io.BytesIO(pdf_content) as pdf_file:
                # Proper file handle management for stderr redirection
                devnull_file = None
                try:
                    import sys
                    import os
                    from contextlib import redirect_stderr
                    
                    devnull_file = open(os.devnull, 'w')
                    with redirect_stderr(devnull_file):
                        with pdfplumber.open(pdf_file) as pdf:
                            metadata["total_pages"] = len(pdf.pages)
                            
                            # Safety check: page limit
                            if metadata["total_pages"] > self.max_pages:
                                logger.warning(f"PDF has {metadata['total_pages']} pages, limiting to {self.max_pages}")
                                pages_to_process = self.max_pages
                            else:
                                pages_to_process = metadata["total_pages"]
                            
                            all_text = ""
                            successful_pages = 0
                            
                            for page_num, page in enumerate(pdf.pages[:pages_to_process], 1):
                                try:
                                    # More robust text extraction with memory safety
                                    page_text = None
                                    
                                    # Method 1: Standard extraction
                                    try:
                                        page_text = page.extract_text() or ""
                                        # Memory safety check
                                        if len(page_text) > self.max_chars_per_page:
                                            page_text = page_text[:self.max_chars_per_page] + "...[truncated for safety]"
                                    except Exception:
                                        pass
                                    
                                    # Method 2: Extract with different settings if first failed
                                    if not page_text or not page_text.strip():
                                        try:
                                            page_text = page.extract_text(x_tolerance=2, y_tolerance=2) or ""
                                            if len(page_text) > self.max_chars_per_page:
                                                page_text = page_text[:self.max_chars_per_page] + "...[truncated for safety]"
                                        except Exception:
                                            pass
                                    
                                    # Method 3: Character-by-character extraction with strict limits
                                    if not page_text or not page_text.strip():
                                        try:
                                            chars = page.chars
                                            if chars and len(chars) < 5000:  # Limit character extraction to prevent memory issues
                                                page_text = ''.join([char.get('text', '') for char in chars[:5000]])
                                            else:
                                                page_text = f"[Page {page_num} - content extraction failed]"
                                        except Exception:
                                            page_text = f"[Page {page_num} - content extraction failed]"
                                    
                                    if page_text and page_text.strip():
                                        all_text += f"\\n\\n--- Page {page_num} ---\\n\\n{page_text}"
                                        successful_pages += 1
                                    
                                    # Memory safety: prevent text from growing too large
                                    if len(all_text) > 10 * 1024 * 1024:  # 10MB text limit
                                        logger.warning("Text extraction stopped due to size limit (10MB)")
                                        all_text += "\\n\\n[Extraction stopped - content too large]"
                                        break
                                        
                                except Exception as e:
                                    logger.warning(f"Failed to extract text from page {page_num}: {str(e)[:100]}...")
                                    continue
                finally:
                    # Ensure devnull file is properly closed
                    if devnull_file:
                        devnull_file.close()
                        
                        logger.info(f"Successfully extracted text from {successful_pages}/{metadata['total_pages']} pages")
                        
                        if not all_text.strip():
                            raise ValueError(f"No text content found in PDF (tried {metadata['total_pages']} pages)")
                        
                        # Split into chunks
                        chunks = self._create_chunks(all_text, metadata["total_pages"])
                        metadata["total_characters"] = len(all_text)
                        metadata["successful_pages"] = successful_pages
                        
        except Exception as e:
            logger.error(f"pdfplumber extraction failed: {str(e)}")
            raise e
                
        return chunks, metadata
    
    async def _extract_with_pypdf2(self, pdf_content: bytes) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """Extract text using PyPDF2 library with robust error handling."""
        chunks = []
        metadata = {
            "extraction_method": "PyPDF2", 
            "total_pages": 0,
            "total_characters": 0
        }
        
        try:
            with io.BytesIO(pdf_content) as pdf_file:
                # Suppress warnings from PyPDF2
                import warnings
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    
                    pdf_reader = PyPDF2.PdfReader(pdf_file)
                    metadata["total_pages"] = len(pdf_reader.pages)
                    
                    # Safety check: page limit
                    if metadata["total_pages"] > self.max_pages:
                        logger.warning(f"PDF has {metadata['total_pages']} pages, limiting to {self.max_pages}")
                        pages_to_process = self.max_pages
                    else:
                        pages_to_process = metadata["total_pages"]
                    
                    all_text = ""
                    successful_pages = 0
                    
                    for page_num, page in enumerate(pdf_reader.pages[:pages_to_process], 1):
                        try:
                            page_text = page.extract_text() or ""
                            
                            # Memory safety check
                            if len(page_text) > self.max_chars_per_page:
                                page_text = page_text[:self.max_chars_per_page] + "...[truncated for safety]"
                            
                            if page_text.strip():
                                all_text += f"\\n\\n--- Page {page_num} ---\\n\\n{page_text}"
                                successful_pages += 1
                            
                            # Memory safety: prevent text from growing too large
                            if len(all_text) > 10 * 1024 * 1024:  # 10MB text limit
                                logger.warning("PyPDF2: Text extraction stopped due to size limit (10MB)")
                                all_text += "\\n\\n[Extraction stopped - content too large]"
                                break
                                
                        except Exception as e:
                            logger.warning(f"Failed to extract text from page {page_num}: {str(e)[:100]}...")
                            continue
                    
                    logger.info(f"PyPDF2: Successfully extracted text from {successful_pages}/{metadata['total_pages']} pages")
                    
                    if not all_text.strip():
                        raise ValueError(f"No text content found in PDF (tried {metadata['total_pages']} pages)")
                    
                    # Split into chunks
                    chunks = self._create_chunks(all_text, metadata["total_pages"])
                    metadata["total_characters"] = len(all_text)
                    metadata["successful_pages"] = successful_pages
                    
        except Exception as e:
            logger.error(f"PyPDF2 extraction failed: {str(e)}")
            raise e
            
        return chunks, metadata
    
    def _create_chunks(self, text: str, total_pages: int) -> List[Dict[str, Any]]:
        """Split text into overlapping chunks with memory safety."""
        chunks = []
        text = text.strip()
        
        # Safety check: prevent processing extremely large texts
        max_text_size = 20 * 1024 * 1024  # 20MB limit
        if len(text) > max_text_size:
            logger.warning(f"Text too large ({len(text)} chars), truncating to {max_text_size} chars")
            text = text[:max_text_size] + "\\n\\n[Text truncated for memory safety]"
        
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
        max_chunks = 100  # Reasonable limit for a small PDF
        
        while start < len(text) and chunk_index < max_chunks:
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
        
        if chunk_index >= max_chunks:
            logger.warning(f"Chunk limit reached ({max_chunks}), text may be truncated")
        
        return chunks
    
    def set_chunk_parameters(self, chunk_size: int, chunk_overlap: int):
        """Configure chunk size and overlap parameters."""
        self.chunk_size = max(100, chunk_size)  # Minimum chunk size
        self.chunk_overlap = min(chunk_overlap, chunk_size // 2)  # Overlap can't exceed half chunk size
    
    async def _extract_basic(self, pdf_content: bytes) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """Basic fallback extraction method for problematic PDFs."""
        chunks = []
        metadata = {
            "extraction_method": "basic_fallback", 
            "total_pages": 1,
            "total_characters": 0
        }
        
        try:
            # Create a minimal chunk with placeholder content
            fallback_text = """
            This PDF could not be properly parsed due to formatting issues.
            
            The system attempted multiple extraction methods:
            1. pdfplumber (advanced layout detection)
            2. PyPDF2 (standard PDF parsing)
            3. Basic fallback (this method)
            
            Unfortunately, the PDF appears to have corrupted font information or 
            complex formatting that prevents automatic text extraction.
            
            Possible solutions:
            - Try re-saving the PDF from the original source
            - Use a different PDF file
            - Convert the PDF to a simpler format
            
            For now, you can still ask questions and the AI will provide general 
            educational assistance, but it won't be able to reference specific 
            content from this document.
            """
            
            # Try to get some basic info about the PDF
            try:
                with io.BytesIO(pdf_content) as pdf_file:
                    try:
                        # Try PyPDF2 just to get page count
                        import PyPDF2
                        pdf_reader = PyPDF2.PdfReader(pdf_file)
                        page_count = len(pdf_reader.pages)
                        if page_count > 0:
                            metadata["total_pages"] = page_count
                            fallback_text += f"\n\nThe PDF appears to have {page_count} pages."
                    except:
                        pass  # Ignore errors here
            except:
                pass  # Ignore any errors
            
            chunks = self._create_chunks(fallback_text.strip(), metadata["total_pages"])
            metadata["total_characters"] = len(fallback_text)
            metadata["extraction_note"] = "Fallback content due to extraction failure"
            
            logger.warning("Using fallback extraction - PDF content could not be parsed")
            
        except Exception as e:
            logger.error(f"Even basic extraction failed: {str(e)}")
            # Don't raise, just return minimal chunks
            chunks = [{
                "content": "PDF extraction failed completely. This is an emergency fallback.",
                "chunk_index": 0,
                "page_number": 1,
                "chunk_size": 57,
                "start_char": 0,
                "end_char": 57
            }]
            metadata["extraction_note"] = f"Emergency fallback: {str(e)}"
            
        return chunks, metadata
