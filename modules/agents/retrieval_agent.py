"""
Retrieval Agent Service
=======================
Handles strategy selection, hybrid search (dense BGE-M3 + sparse BM25), Reciprocal Rank Fusion (RRF),
neighbor context expansion, and Cross-Encoder reranking (BAAI/bge-reranker-v2-m3) to return clean
educational evidence to the Tutor Agent.
"""
from typing import List, Dict, Any, Optional
import logging
import asyncio
import numpy as np
import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer
from core.database.manager import PDFDatabaseManager
from modules.pdf_processor.services.embedding_generator import EmbeddingGenerator

logger = logging.getLogger(__name__)


class BGEReranker:
    """Cross-Encoder Reranker using BAAI/bge-reranker-v2-m3 model (Singleton)."""
    
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(BGEReranker, cls).__new__(cls, *args, **kwargs)
            cls._instance._initialized = False
        return cls._instance
        
    def __init__(self, model_name: str = "BAAI/bge-reranker-v2-m3"):
        if self._initialized:
            return
        self.model_name = model_name
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.tokenizer = None
        self.model = None
        self._initialize()
        self._initialized = True

    def _initialize(self):
        """Load tokenizer and cross-encoder model on CPU/GPU."""
        try:
            print(f"\n🔄 Initializing local Hugging Face Cross-Encoder Reranker ({self.model_name}) on {self.device}...")
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            self.model = AutoModelForSequenceClassification.from_pretrained(self.model_name).to(self.device)
            self.model.eval()
            print("✅ Cross-Encoder Reranker initialized successfully!")
            logger.info("Cross-Encoder Reranker initialized successfully")
        except Exception as e:
            if "out of memory" in str(e).lower() and self.device == "cuda":
                print("⚠️ CUDA out of memory. Falling back to CPU for Reranker...")
                self.device = "cpu"
                try:
                    self.model = AutoModelForSequenceClassification.from_pretrained(self.model_name).to("cpu")
                    self.model.eval()
                    print("✅ Cross-Encoder Reranker initialized successfully on CPU!")
                    logger.info("Cross-Encoder Reranker initialized on CPU due to CUDA OOM")
                except Exception as e_cpu:
                    print(f"❌ Failed to initialize Reranker on CPU: {e_cpu}")
                    logger.error(f"Failed to initialize Reranker on CPU: {e_cpu}")
                    self.model = None
            else:
                error_msg = f"Failed to initialize Cross-Encoder Reranker: {str(e)}"
                print(f"❌ {error_msg}")
                logger.error(error_msg)
                self.model = None

    def rerank(self, query: str, candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Rerank candidates using Cross-Encoder model and sort descending by score."""
        if not candidates or not self.model or not self.tokenizer:
            return candidates

        try:
            # Pair query and passage for each candidate
            pairs = [[query, c["content"]] for c in candidates]
            
            # Predict scores
            with torch.no_grad():
                inputs = self.tokenizer(
                    pairs, 
                    padding=True, 
                    truncation=True, 
                    return_tensors='pt', 
                    max_length=512
                ).to(self.device)
                
                # Model outputs logits for the binary relevance class
                logits = self.model(**inputs).logits.view(-1).float()
                # Apply sigmoid to convert to a score between 0 and 1
                scores = torch.sigmoid(logits).cpu().numpy().tolist()
                
            # Assign scores to candidates
            for c, score in zip(candidates, scores):
                c["rerank_score"] = score
                
            # Sort by rerank score descending
            return sorted(candidates, key=lambda x: x["rerank_score"], reverse=True)
        except Exception as e:
            logger.error(f"Error during cross-encoder reranking: {str(e)}")
            return candidates


class RetrievalAgent:
    """Service for retrieving curated educational context from PDFs using Hybrid search and RRF"""
    
    def __init__(self, db_manager: PDFDatabaseManager):
        self.db_manager = db_manager
        self.embedding_generator = EmbeddingGenerator()
        self.reranker = BGEReranker()
        
    async def retrieve_context(
        self,
        intent: str,
        query: str,
        user_id: str,
        scope: Optional[Dict[str, Any]] = None,
        match_count: int = 5
    ) -> Dict[str, Any]:
        """
        Main retrieval entrypoint.
        
        Args:
            intent: User intent (teach, doubt_solve, generate_quiz)
            query: Natural language query or concept name
            user_id: The authenticated user's ID
            scope: Optional dictionary specifying book, chapter, section filtering
            match_count: Number of top chunks to return
            
        Returns:
            Dict containing retrieved evidence chunks, citations, and metadata
        """
        logger.info(f"Retrieving context for user {user_id} | Intent: {intent} | Query: {query}")
        
        scope = scope or {}
        pdf_id = scope.get("pdf_id") or scope.get("document_id")
        
        dense_candidates = []
        sparse_candidates = []
        retrieval_strategy = "hybrid"
        
        # 1. Select Search Strategy and Gather Candidates
        # Strategy A: Specific PDF Search (if pdf_id specified)
        if pdf_id:
            logger.info(f"Using document-specific search for PDF: {pdf_id}")
            retrieval_strategy = "document_specific"
            query_embedding = await self._generate_embedding(query)
            
            # Dense Vector search
            doc_results = await self.db_manager.search_within_pdf(
                query_embedding=query_embedding,
                pdf_id=pdf_id,
                user_id=user_id,
                match_threshold=0.1,  # Relaxed threshold for initial retrieval, reranker will refine
                match_count=match_count * 3
            )
            for r in doc_results:
                dense_candidates.append({
                    "id": r.get("id"),
                    "content": r.get("content"),
                    "page_number": r.get("page_number"),
                    "chunk_index": r.get("chunk_index"),
                    "metadata": r.get("metadata", {}),
                    "pdf_title": r.get("document_filename", "Selected Document"),
                    "similarity": r.get("similarity", 0.0),
                    "pdf_id": pdf_id
                })
                
            # Sparse FTS search within the specific PDF
            try:
                fts_result = self.db_manager.service_client.table("document_chunks") \
                    .select("id, content, metadata, page_number, chunk_index, pdf_id, pdf_documents!inner(original_filename, user_id)") \
                    .eq("pdf_id", pdf_id) \
                    .limit(match_count * 3) \
                    .text_search("content", query, options={"type": "web_search"}) \
                    .execute()
                
                if fts_result.data:
                    for row in fts_result.data:
                        pdf_doc = row.get("pdf_documents", {})
                        sparse_candidates.append({
                            "id": row.get("id"),
                            "content": row.get("content"),
                            "page_number": row.get("page_number"),
                            "chunk_index": row.get("chunk_index"),
                            "metadata": row.get("metadata"),
                            "pdf_title": pdf_doc.get("original_filename", "Selected Document"),
                            "pdf_id": row.get("pdf_id"),
                            "similarity": 0.5
                        })
            except Exception as e:
                logger.error(f"FTS search within PDF failed: {e}")
                
        # Strategy B: General Hybrid Search (BM25 Full Text Search + Dense Semantic Vector Search)
        else:
            logger.info("Executing General Hybrid search (vector + text)")
            # Run dense semantic search and text search in background
            vector_task = self._run_vector_search(query, user_id, match_count * 3)
            text_task = self.db_manager.text_search_all_documents(query, user_id, match_count * 3)
            
            vector_results, text_results = await asyncio.gather(vector_task, text_task)
            
            # Map dense vector search results
            for r in vector_results:
                dense_candidates.append({
                    "id": r.get("id"),
                    "content": r.get("content"),
                    "page_number": r.get("page_number"),
                    "chunk_index": r.get("chunk_index"),
                    "metadata": r.get("metadata", {}),
                    "pdf_title": r.get("pdf_title", "Unknown"),
                    "similarity": r.get("similarity", 0.0),
                    "pdf_id": r.get("pdf_id")
                })
            
            # Map sparse text search results
            for r in text_results:
                sparse_candidates.append({
                    "id": r.get("id"),
                    "content": r.get("content"),
                    "page_number": r.get("page_number"),
                    "chunk_index": r.get("chunk_index"),
                    "metadata": r.get("metadata", {}),
                    "pdf_title": r.get("pdf_title", "Unknown"),
                    "similarity": 0.5,
                    "pdf_id": r.get("pdf_id")
                })
                
        # 2. Apply Reciprocal Rank Fusion (RRF)
        fused_candidates = self._apply_rrf(dense_candidates, sparse_candidates, k=60)
        
        # 3. Two-Stage Reranking (Cross-Encoder)
        # Rerank the top 15 fused candidates using BAAI/bge-reranker-v2-m3
        reranked_candidates = self.reranker.rerank(query, fused_candidates[:15])
        
        # 4. Limit to requested match count
        top_candidates = reranked_candidates[:match_count]
        
        # 5. Context Expansion (Neighbor retrieval for the final top matches)
        if top_candidates and retrieval_strategy != "document_specific":
            top_candidates = await self._expand_neighbor_context(top_candidates, user_id)
            
        # 6. Extract citations
        citations = []
        for c in top_candidates:
            pdf_title = c.get("pdf_title", "Unknown Document")
            page = c.get("page_number")
            page_str = f"Page {page}" if page else "Unknown Page"
            citation = f"{pdf_title} ({page_str})"
            if citation not in citations:
                citations.append(citation)
                
        return {
            "evidence": top_candidates,
            "citations": citations,
            "retrieval_strategy_used": retrieval_strategy
        }
        
    def _apply_rrf(self, dense_results: List[Dict[str, Any]], sparse_results: List[Dict[str, Any]], k: int = 60) -> List[Dict[str, Any]]:
        """Apply Reciprocal Rank Fusion (RRF) to combine dense and sparse rankings."""
        rrf_scores = {}
        doc_map = {}
        
        # Process dense results
        for rank, doc in enumerate(dense_results):
            doc_id = doc["id"]
            doc_map[doc_id] = doc
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0.0) + 1.0 / (k + rank + 1)
            
        # Process sparse results
        for rank, doc in enumerate(sparse_results):
            doc_id = doc["id"]
            if doc_id not in doc_map:
                doc_map[doc_id] = doc
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0.0) + 1.0 / (k + rank + 1)
            
        # Build fused candidates list
        fused = []
        for doc_id, score in rrf_scores.items():
            doc = doc_map[doc_id].copy()
            doc["rrf_score"] = score
            fused.append(doc)
            
        # Sort by RRF score descending
        fused.sort(key=lambda x: x["rrf_score"], reverse=True)
        return fused
        
    async def _run_vector_search(self, query: str, user_id: str, count: int) -> List[Dict[str, Any]]:
        """Run vector similarity search over all documents"""
        query_embedding = await self._generate_embedding(query)
        return await self.db_manager.search_all_documents(
            query_embedding=query_embedding,
            user_id=user_id,
            match_threshold=0.1,  # Low threshold to get raw candidates
            match_count=count
        )
        
    async def _generate_embedding(self, text: str) -> List[float]:
        """Generate embedding using local BGE-M3 embedding generator"""
        try:
            emb = await self.embedding_generator.generate_single_embedding(text)
            return emb if emb is not None else [0.0] * 768
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            return [0.0] * 768
            
    async def _expand_neighbor_context(self, candidates: List[Dict[str, Any]], user_id: str) -> List[Dict[str, Any]]:
        """Fetch neighbor chunks for the top 2 candidates to preserve context continuity"""
        # Expand neighbors for top candidates to ensure no teaching from isolated snippets
        expanded = list(candidates)
        # Use rerank_score instead of similarity since we reranked
        top_candidates = sorted(candidates, key=lambda x: x.get("rerank_score", 0.0), reverse=True)[:2]
        
        for tc in top_candidates:
            pdf_id = tc.get("pdf_id") or tc.get("metadata", {}).get("pdf_id")
            chunk_idx = tc.get("chunk_index")
            
            if not pdf_id or chunk_idx is None:
                continue
                
            try:
                # Query sibling chunks (index - 1 and index + 1)
                siblings_result = self.db_manager.service_client.table("document_chunks") \
                    .select("id, content, page_number, chunk_index, pdf_id, pdf_documents(original_filename)") \
                    .eq("pdf_id", pdf_id) \
                    .in_("chunk_index", [chunk_idx - 1, chunk_idx + 1]) \
                    .execute()
                    
                if siblings_result.data:
                    for s in siblings_result.data:
                        # Deduplicate
                        if any(c.get("id") == s.get("id") for c in expanded):
                            continue
                            
                        pdf_doc = s.get("pdf_documents", {})
                        expanded.append({
                            "id": s.get("id"),
                            "content": s.get("content"),
                            "page_number": s.get("page_number"),
                            "chunk_index": s.get("chunk_index"),
                            "metadata": s.get("metadata", {}),
                            "pdf_title": pdf_doc.get("original_filename", "Unknown"),
                            "rerank_score": tc.get("rerank_score", 0.5) * 0.9,  # Slightly penalize neighbor score
                            "pdf_id": s.get("pdf_id")
                        })
            except Exception as e:
                logger.error(f"Failed to fetch neighbor chunks: {e}")
                
        return expanded
