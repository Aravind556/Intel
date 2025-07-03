"""
PDF Embedding Generator with Google Text Embeddings API

Handles generation of vector embeddings for PDF text chunks using Google's embedding API.
Uses batching and parallel processing for improved efficiency.
"""

import logging
from typing import List, Optional
import os
import asyncio
import numpy as np
import google.generativeai as genai
from ..models.pdf_models import ProcessingError

logger = logging.getLogger(__name__)


class EmbeddingGenerator:
    """Generates vector embeddings for text chunks using Google's text embeddings API."""
    
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.model_name = "models/text-embedding-004"  # Latest model
        self.max_batch_size = 50  # Increased for better performance
        self.max_parallel_requests = 10  # More parallel requests
        self.request_delay = 0.1  # Reduced delay between batches
        self.model = None
        self._initialize_model()
    
    def _initialize_model(self):
        """Initialize Google embedding API client."""
        try:
            if not self.api_key:
                print("\n❌ ERROR: Google API key not found in environment variables")
                print("Please set the GEMINI_API_KEY environment variable")
                print("Embeddings will not be available - PDFs can be uploaded but not searched")
                logger.warning("Google API key not found. Embedding generation will be disabled.")
                return
                
            print("\n🔄 Initializing Google Text Embeddings API client...")
            genai.configure(api_key=self.api_key)
            # No actual model object needed, just configure the API
            self.model = True  # Just a flag to indicate API is ready
            print("✅ Google Text Embeddings API initialized successfully!")
            logger.info("Google Text Embeddings API initialized successfully")
            
        except Exception as e:
            error_msg = f"Failed to initialize embedding API: {str(e)}"
            print(f"❌ {error_msg}")
            logger.error(error_msg)
            logger.error(error_msg)
            self.model = None
    
    async def generate_embeddings(self, chunks: List[dict]) -> List[dict]:
        """
        Generate embeddings for a list of text chunks with efficient batching and parallelization.
        
        Args:
            chunks: List of chunk dictionaries with 'content' field
            
        Returns:
            List of chunks with 'embedding' field added
        """
        if not self.model:
            logger.warning("Google Text Embeddings API not available. Skipping embedding generation.")
            # Return chunks without embeddings
            for chunk in chunks:
                chunk["embedding"] = None
            return chunks
        
        try:
            # Create result dictionary to maintain original order
            result_chunks = chunks.copy()
            total_chunks = len(chunks)
            
            print(f"⏳ Generating embeddings for {total_chunks} chunks using Google Text Embeddings API...")
            print(f"📊 Using batch size: {self.max_batch_size}, parallel requests: {self.max_parallel_requests}")
            
            # Split into optimized batches
            batches = []
            for i in range(0, total_chunks, self.max_batch_size):
                batch = chunks[i:i + self.max_batch_size]
                batches.append(batch)
            
            print(f"📦 Created {len(batches)} batches for processing")
            
            # Define a function to process a batch with progress tracking
            async def process_batch(batch_index, batch):
                try:
                    batch_start_time = asyncio.get_event_loop().time()
                    batch_texts = [chunk["content"] for chunk in batch]
                    embeddings = await self._generate_batch_embeddings_async(batch_texts)
                    
                    # Add embeddings to chunks
                    success_count = 0
                    for chunk, embedding in zip(batch, embeddings):
                        if embedding is not None:
                            chunk["embedding"] = embedding
                            success_count += 1
                        else:
                            chunk["embedding"] = None
                    
                    batch_time = asyncio.get_event_loop().time() - batch_start_time
                    print(f"✅ Batch {batch_index + 1}/{len(batches)} completed in {batch_time:.1f}s ({success_count}/{len(batch)} successful)")
                    logger.info(f"Generated embeddings for batch {batch_index + 1}/{len(batches)} - {success_count}/{len(batch)} successful")
                    return success_count
                except Exception as e:
                    logger.error(f"Failed to generate embeddings for batch {batch_index + 1}: {str(e)}")
                    # Mark chunks without embeddings
                    for chunk in batch:
                        chunk["embedding"] = None
                    return 0
            
            # Process batches with optimized parallelization and rate limiting
            total_successful = 0
            start_time = asyncio.get_event_loop().time()
            
            for i in range(0, len(batches), self.max_parallel_requests):
                current_batches = batches[i:i + self.max_parallel_requests]
                batch_tasks = [process_batch(i+j, batch) for j, batch in enumerate(current_batches)]
                
                # Wait for all batches in this group to complete
                results = await asyncio.gather(*batch_tasks, return_exceptions=True)
                
                # Count successful embeddings
                for result in results:
                    if isinstance(result, int):
                        total_successful += result
                
                # Progress update
                processed_batches = min(i + self.max_parallel_requests, len(batches))
                elapsed_time = asyncio.get_event_loop().time() - start_time
                avg_time_per_batch = elapsed_time / processed_batches if processed_batches > 0 else 0
                remaining_batches = len(batches) - processed_batches
                eta = remaining_batches * avg_time_per_batch
                
                print(f"📊 Progress: {processed_batches}/{len(batches)} batches ({processed_batches/len(batches)*100:.1f}%) - ETA: {eta:.1f}s")
                
                # Brief delay between batch groups to avoid API rate limits
                if i + self.max_parallel_requests < len(batches):
                    await asyncio.sleep(self.request_delay)
            
            total_time = asyncio.get_event_loop().time() - start_time
            logger.info(f"Successfully generated embeddings for {total_successful}/{total_chunks} chunks "
                        f"in {total_time:.1f}s ({len(batches)} batches)")
            print(f"✅ Generated embeddings for {total_successful}/{total_chunks} chunks in {total_time:.1f}s")
            
            return result_chunks
            
        except Exception as e:
            logger.error(f"Embedding generation failed: {str(e)}")
            # Return chunks without embeddings
            for chunk in chunks:
                chunk["embedding"] = None
            return chunks
    
    async def _generate_batch_embeddings_async(self, texts: List[str]) -> List[Optional[List[float]]]:
        """Generate embeddings for a batch of texts asynchronously using Google Text Embeddings API."""
        return self._generate_batch_embeddings(texts)  # Use the sync method for now
    
    def _generate_batch_embeddings(self, texts: List[str]) -> List[Optional[List[float]]]:
        """Generate embeddings for a batch of texts using Google Text Embeddings API."""
        try:
            if not self.model:
                return [None] * len(texts)
            
            # Clean texts
            cleaned_texts = []
            for text in texts:
                cleaned_text = " ".join(text.split())
                if len(cleaned_text) > 2000:  # API limit is about 2048 tokens
                    cleaned_text = cleaned_text[:2000]
                cleaned_texts.append(cleaned_text)
            
            # Generate embeddings using Google API
            embeddings = []
            for text in cleaned_texts:
                try:
                    result = genai.embed_content(
                        model=self.model_name,
                        content=text,
                        task_type="retrieval_document"
                    )
                    if result and hasattr(result, "embedding"):
                        embeddings.append(result.embedding)
                    else:
                        embeddings.append(None)
                except Exception as e:
                    logger.error(f"Error generating embedding for text: {str(e)}")
                    embeddings.append(None)
            
            return embeddings
            
        except Exception as e:
            logger.error(f"Unexpected error in embedding generation: {str(e)}")
            return [None] * len(texts)
    
    async def generate_single_embedding(self, text: str) -> Optional[List[float]]:
        """Generate embedding for a single text (used for query embeddings)."""
        if not self.model:
            return None
            
        try:
            # Clean text
            cleaned_text = " ".join(text.split())
            if len(cleaned_text) > 2000:
                cleaned_text = cleaned_text[:2000]
            
            result = genai.embed_content(
                model=self.model_name,
                content=cleaned_text,
                task_type="retrieval_query"
            )
            
            if result and hasattr(result, "embedding"):
                return result.embedding
            return None
            
        except Exception as e:
            logger.error(f"Failed to generate single embedding: {str(e)}")
            return None
    
    def is_available(self) -> bool:
        """Check if embedding generation is available."""
        return self.model is not None
