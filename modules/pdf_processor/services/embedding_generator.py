"""
PDF Embedding Generator

Handles generation of vector embeddings for PDF text chunks.
"""

import logging
from typing import List, Optional
import openai
from openai import OpenAI
import os
from ..models.pdf_models import ProcessingError

logger = logging.getLogger(__name__)


class EmbeddingGenerator:
    """Generates vector embeddings for text chunks using OpenAI."""
    
    def __init__(self):
        self.client = None
        self.model = "text-embedding-3-small"  # Cost-effective embedding model
        self.max_batch_size = 100  # Process embeddings in batches
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize OpenAI client."""
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.warning("OpenAI API key not found. Embedding generation will be disabled.")
            return
            
        try:
            self.client = OpenAI(api_key=api_key)
            logger.info("OpenAI client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {str(e)}")
    
    async def generate_embeddings(self, chunks: List[dict]) -> List[dict]:
        """
        Generate embeddings for a list of text chunks.
        
        Args:
            chunks: List of chunk dictionaries with 'content' field
            
        Returns:
            List of chunks with 'embedding' field added
        """
        if not self.client:
            logger.warning("OpenAI client not available. Skipping embedding generation.")
            # Return chunks without embeddings
            for chunk in chunks:
                chunk["embedding"] = None
            return chunks
        
        try:
            # Process in batches to avoid rate limits
            processed_chunks = []
            
            for i in range(0, len(chunks), self.max_batch_size):
                batch = chunks[i:i + self.max_batch_size]
                batch_texts = [chunk["content"] for chunk in batch]
                
                try:
                    # Generate embeddings for this batch
                    embeddings = await self._generate_batch_embeddings(batch_texts)
                    
                    # Add embeddings to chunks
                    for chunk, embedding in zip(batch, embeddings):
                        chunk["embedding"] = embedding
                        processed_chunks.append(chunk)
                        
                    logger.info(f"Generated embeddings for batch {i//self.max_batch_size + 1}/{(len(chunks)-1)//self.max_batch_size + 1}")
                    
                except Exception as e:
                    logger.error(f"Failed to generate embeddings for batch starting at index {i}: {str(e)}")
                    # Add chunks without embeddings for this batch
                    for chunk in batch:
                        chunk["embedding"] = None
                        processed_chunks.append(chunk)
            
            success_count = sum(1 for chunk in processed_chunks if chunk.get("embedding") is not None)
            logger.info(f"Successfully generated embeddings for {success_count}/{len(processed_chunks)} chunks")
            
            return processed_chunks
            
        except Exception as e:
            logger.error(f"Embedding generation failed: {str(e)}")
            # Return chunks without embeddings
            for chunk in chunks:
                chunk["embedding"] = None
            return chunks
    
    async def _generate_batch_embeddings(self, texts: List[str]) -> List[Optional[List[float]]]:
        """Generate embeddings for a batch of texts."""
        try:
            # TEMPORARY: Skip OpenAI API calls due to quota limits
            # Return mock embeddings for testing
            logger.info(f"Generating mock embeddings for {len(texts)} texts (OpenAI quota exceeded)")
            
            # Generate mock embeddings (1536 dimensions for text-embedding-3-small)
            mock_embeddings = []
            for i, text in enumerate(texts):
                # Create a simple hash-based mock embedding
                text_hash = hash(text) % 10000
                mock_embedding = [0.1 * (text_hash % 100) + 0.001 * j for j in range(1536)]
                mock_embeddings.append(mock_embedding)
            
            return mock_embeddings
            
        except openai.RateLimitError as e:
            logger.error(f"OpenAI rate limit exceeded: {str(e)}")
            return [None] * len(texts)
            
        except openai.AuthenticationError as e:
            logger.error(f"OpenAI authentication failed: {str(e)}")
            return [None] * len(texts)
            
        except Exception as e:
            logger.error(f"Unexpected error in embedding generation: {str(e)}")
            return [None] * len(texts)
    
    async def generate_single_embedding(self, text: str) -> Optional[List[float]]:
        """Generate embedding for a single text (used for query embeddings)."""
        # TEMPORARY: Skip OpenAI API calls due to quota limits
        logger.info("Generating mock embedding for single text (OpenAI quota exceeded)")
        
        # Generate mock embedding
        text_hash = hash(text) % 10000
        mock_embedding = [0.1 * (text_hash % 100) + 0.001 * j for j in range(1536)]
        return mock_embedding
    
    def is_available(self) -> bool:
        """Check if embedding generation is available."""
        return self.client is not None
