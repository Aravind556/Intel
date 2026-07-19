"""
PDF Embedding Generator with Hugging Face BGE-M3 Local Embeddings

Handles generation of vector embeddings for PDF text chunks using Hugging Face sentence-transformers.
Automatically reduces dimensions to 768 to match the Supabase pgvector column constraint.
"""

import logging
from typing import List, Optional
import os
import numpy as np
import torch
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)


class EmbeddingGenerator:
    """Generates vector embeddings for text chunks using Hugging Face BGE-M3 local model (Singleton)."""
    
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(EmbeddingGenerator, cls).__new__(cls, *args, **kwargs)
            cls._instance._initialized = False
        return cls._instance
        
    def __init__(self):
        if self._initialized:
            return
        self.model_name = "BAAI/bge-m3"
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = None
        self._initialize_model()
        self._initialized = True
    
    def _initialize_model(self):
        """Initialize sentence-transformers client and pull embedding model."""
        try:
            print(f"\n🔄 Initializing local Hugging Face BGE-M3 embeddings on {self.device}...")
            
            # Load SentenceTransformer model
            self.model = SentenceTransformer(self.model_name, device=self.device)
            print("✅ BGE-M3 embeddings initialized successfully!")
            logger.info("BGE-M3 embeddings initialized successfully")
            
        except Exception as e:
            if "out of memory" in str(e).lower() and self.device == "cuda":
                print("⚠️ CUDA out of memory. Falling back to CPU for Embeddings...")
                self.device = "cpu"
                try:
                    self.model = SentenceTransformer(self.model_name, device="cpu")
                    print("✅ BGE-M3 embeddings initialized successfully on CPU!")
                    logger.info("BGE-M3 embeddings initialized on CPU due to CUDA OOM")
                except Exception as e_cpu:
                    print(f"❌ Failed to initialize BGE-M3 on CPU: {e_cpu}")
                    logger.error(f"Failed to initialize BGE-M3 on CPU: {e_cpu}")
                    self.model = None
            else:
                error_msg = f"Failed to initialize BGE-M3 model: {str(e)}"
                print(f"❌ {error_msg}")
                logger.error(error_msg)
                self.model = None
    
    async def generate_embeddings(self, chunks: List[dict]) -> List[dict]:
        """
        Generate embeddings for a list of text chunks using BGE-M3.
        Reduces dimension from 1024 to 768 via Matryoshka slicing and L2 normalizes.
        
        Args:
            chunks: List of chunk dictionaries with 'content' field
            
        Returns:
            List of chunks with 'embedding' field added
        """
        if not self.model:
            logger.warning("BGE-M3 model not available. Skipping embedding generation.")
            for chunk in chunks:
                chunk["embedding"] = None
            return chunks
        
        try:
            total_chunks = len(chunks)
            print(f"⏳ Generating BGE-M3 embeddings for {total_chunks} chunks on {self.device}...")
            
            texts = [chunk["content"] for chunk in chunks]
            
            # SentenceTransformers encode is synchronous but fast on GPU.
            # Run on CPU/GPU depending on device detection.
            embeddings = self.model.encode(
                texts,
                normalize_embeddings=True,
                show_progress_bar=False,
                device=self.device
            )
            
            # Slice embeddings to 768 dimensions (Matryoshka representation)
            embeddings_768 = embeddings[:, :768]
            
            # Re-normalize sliced embeddings to make them valid unit vectors for cosine similarity
            norms = np.linalg.norm(embeddings_768, axis=1, keepdims=True)
            norms = np.where(norms == 0, 1.0, norms)  # Avoid division by zero
            embeddings_768 = embeddings_768 / norms
            
            # Add embeddings to chunks
            for chunk, embedding in zip(chunks, embeddings_768):
                chunk["embedding"] = embedding.tolist()
            
            print(f"✅ Generated BGE-M3 embeddings for {total_chunks} chunks successfully!")
            return chunks
            
        except Exception as e:
            logger.error(f"Embedding generation failed: {str(e)}")
            # Return chunks without embeddings
            for chunk in chunks:
                chunk["embedding"] = None
            return chunks
    
    async def generate_single_embedding(self, text: str) -> Optional[List[float]]:
        """Generate embedding for a single text (reduced to 768 dimensions and L2 normalized)."""
        if not self.model:
            return None
            
        try:
            # Clean text
            cleaned_text = " ".join(text.split())
            if len(cleaned_text) > 8000:
                cleaned_text = cleaned_text[:8000]
            
            # Encode single text
            embedding = self.model.encode(
                [cleaned_text],
                normalize_embeddings=True,
                show_progress_bar=False,
                device=self.device
            )[0]
            
            # Matryoshka slice to 768 dimensions
            emb_768 = embedding[:768]
            
            # Re-normalize
            norm = np.linalg.norm(emb_768)
            if norm > 0:
                emb_768 = emb_768 / norm
                
            return emb_768.tolist()
            
        except Exception as e:
            logger.error(f"Failed to generate single embedding: {str(e)}")
            return None
    
    def is_available(self) -> bool:
        """Check if embedding generation is available."""
        return self.model is not None
