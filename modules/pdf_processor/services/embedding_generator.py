"""
PDF Embedding Generator with Ollama Local Embeddings

Handles generation of vector embeddings for PDF text chunks using Ollama local models.
No API rate limits, completely free and local processing.
"""

import logging
from typing import List, Optional
import os
import asyncio
import numpy as np
import ollama
from ..models.pdf_models import ProcessingError

logger = logging.getLogger(__name__)


class EmbeddingGenerator:
    """Generates vector embeddings for text chunks using Ollama local models."""
    
    def __init__(self):
        self.model_name = "nomic-embed-text"  # Ollama embedding model
        self.max_batch_size = 100  # Much higher since it's local
        self.max_parallel_requests = 20  # Higher parallelization for local processing
        self.request_delay = 0.01  # Minimal delay for local processing
        self.model = None
        self._initialize_model()
    
    def _initialize_model(self):
        """Initialize Ollama client and pull embedding model."""
        try:
            print("\n🔄 Initializing Ollama local embeddings...")
            
            # Check if Ollama is running
            try:
                models = ollama.list()
                print("✅ Ollama is running")
            except Exception as e:
                print(f"❌ Ollama not running. Please start Ollama first: {e}")
                logger.error(f"Ollama not running: {e}")
                return
            
            # Check if embedding model is available
            available_models = [model.model for model in models.models]
            if self.model_name not in available_models:
                print(f"🔄 Pulling embedding model: {self.model_name}")
                ollama.pull(self.model_name)
                print(f"✅ Model {self.model_name} downloaded")
            else:
                print(f"✅ Model {self.model_name} already available")
            
            self.model = True  # Flag to indicate Ollama is ready
            print("✅ Ollama embeddings initialized successfully!")
            logger.info("Ollama embeddings initialized successfully")
            
        except Exception as e:
            error_msg = f"Failed to initialize Ollama: {str(e)}"
            print(f"❌ {error_msg}")
            logger.error(error_msg)
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
            logger.warning("Ollama not available. Skipping embedding generation.")
            # Return chunks without embeddings
            for chunk in chunks:
                chunk["embedding"] = None
            return chunks
        
        try:
            # Create result dictionary to maintain original order
            result_chunks = chunks.copy()
            total_chunks = len(chunks)
            
            print(f"⏳ Generating embeddings for {total_chunks} chunks using Ollama local embeddings...")
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
        """Generate embeddings for a batch of texts asynchronously using Ollama."""
        return self._generate_batch_embeddings(texts)  # Ollama is already async-friendly
    
    def _generate_batch_embeddings(self, texts: List[str]) -> List[Optional[List[float]]]:
        """Generate embeddings for a batch of texts using Ollama."""
        try:
            if not self.model:
                return [None] * len(texts)
            
            # Clean texts
            cleaned_texts = []
            for text in texts:
                cleaned_text = " ".join(text.split())
                if len(cleaned_text) > 8000:  # Ollama can handle longer texts
                    cleaned_text = cleaned_text[:8000]
                cleaned_texts.append(cleaned_text)
            
            # Generate embeddings using Ollama
            embeddings = []
            for text in cleaned_texts:
                try:
                    response = ollama.embeddings(
                        model=self.model_name,
                        prompt=text
                    )
                    if response and 'embedding' in response:
                        embeddings.append(response['embedding'])
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
            if len(cleaned_text) > 8000:
                cleaned_text = cleaned_text[:8000]
            
            response = ollama.embeddings(
                model=self.model_name,
                prompt=cleaned_text
            )
            
            if response and 'embedding' in response:
                return response['embedding']
            return None
            
        except Exception as e:
            logger.error(f"Failed to generate single embedding: {str(e)}")
            return None
    
    def is_available(self) -> bool:
        """Check if embedding generation is available."""
        return self.model is not None
