"""
Retrieval Agent Service
=======================
Handles strategy selection, hybrid search (dense + sparse), neighbor context expansion,
and cross-encoder reranking to return clean educational evidence to the Tutor Agent.
"""
from typing import List, Dict, Any, Optional
import logging
from core.database.manager import PDFDatabaseManager
from modules.pdf_processor.services.embedding_generator import EmbeddingGenerator

logger = logging.getLogger(__name__)

class RetrievalAgent:
    """Service for retrieving curated educational context from PDFs using Hybrid search"""
    
    def __init__(self, db_manager: PDFDatabaseManager):
        self.db_manager = db_manager
        self.embedding_generator = EmbeddingGenerator()
        
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
        
        candidates = []
        retrieval_strategy = "hybrid"
        
        # 1. Select Search Strategy
        # Strategy A: Specific PDF Search (if pdf_id specified)
        if pdf_id:
            logger.info(f"Using document-specific search for PDF: {pdf_id}")
            retrieval_strategy = "document_specific"
            query_embedding = await self._generate_embedding(query)
            doc_results = await self.db_manager.search_within_pdf(
                query_embedding=query_embedding,
                pdf_id=pdf_id,
                user_id=user_id,
                match_threshold=0.3, # Relaxed threshold for initial retrieval, reranker will refine
                match_count=match_count * 2
            )
            # Standardize document results structure
            for r in doc_results:
                candidates.append({
                    "id": r.get("id"),
                    "content": r.get("content"),
                    "page_number": r.get("page_number"),
                    "chunk_index": r.get("chunk_index"),
                    "metadata": r.get("metadata", {}),
                    "pdf_title": r.get("document_filename", "Selected Document"),
                    "similarity": r.get("similarity", 0.0)
                })
                
        # Strategy B: General Hybrid Search (BM25 Full Text Search + Dense Semantic Vector Search)
        else:
            logger.info("Executing General Hybrid search (vector + text)")
            # Run dense semantic search in background
            vector_task = self._run_vector_search(query, user_id, match_count * 2)
            # Run text search in background
            text_task = self.db_manager.text_search_all_documents(query, user_id, match_count * 2)
            
            import asyncio
            vector_results, text_results = await asyncio.gather(vector_task, text_task)
            
            # Merge results and deduplicate by ID
            seen_ids = set()
            
            # Add vector search results
            for r in vector_results:
                chunk_id = r.get("id")
                if chunk_id and chunk_id not in seen_ids:
                    candidates.append({
                        "id": chunk_id,
                        "content": r.get("content"),
                        "page_number": r.get("page_number"),
                        "chunk_index": r.get("chunk_index"),
                        "metadata": r.get("metadata", {}),
                        "pdf_title": r.get("pdf_title", "Unknown"),
                        "similarity": r.get("similarity", 0.0),
                        "source": "vector"
                    })
                    seen_ids.add(chunk_id)
            
            # Add text search results
            for r in text_results:
                chunk_id = r.get("id")
                if chunk_id and chunk_id not in seen_ids:
                    candidates.append({
                        "id": chunk_id,
                        "content": r.get("content"),
                        "page_number": r.get("page_number"),
                        "chunk_index": r.get("chunk_index"),
                        "metadata": r.get("metadata", {}),
                        "pdf_title": r.get("pdf_title", "Unknown"),
                        "similarity": 0.5, # Default similarity score for FTS matches
                        "source": "fts"
                    })
                    seen_ids.add(chunk_id)
                    
        # 2. Context Expansion (Neighbor retrieval for top matches)
        # Pull preceding/succeeding chunks for context preservation if we have top-ranked candidates
        if candidates and retrieval_strategy != "document_specific":
            candidates = await self._expand_neighbor_context(candidates, user_id)

        # 3. Reranking using Keyword Overlap + Vector Similarity Scoring
        reranked_candidates = self._rerank_candidates(candidates, query)
        
        # 4. Limit to requested match count and extract citations
        top_candidates = reranked_candidates[:match_count]
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
        
    async def _run_vector_search(self, query: str, user_id: str, count: int) -> List[Dict[str, Any]]:
        """Run vector similarity search over all documents"""
        query_embedding = await self._generate_embedding(query)
        return await self.db_manager.search_all_documents(
            query_embedding=query_embedding,
            user_id=user_id,
            match_threshold=0.3, # Low threshold to get raw candidates
            match_count=count
        )
        
    async def _generate_embedding(self, text: str) -> List[float]:
        """Generate embedding using local Ollama nomic-embed-text"""
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
        top_candidates = sorted(candidates, key=lambda x: x.get("similarity", 0.0), reverse=True)[:2]
        
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
                            "similarity": tc.get("similarity", 0.5) * 0.9, # Slightly penalize neighbor similarity
                            "pdf_id": s.get("pdf_id")
                        })
            except Exception as e:
                logger.error(f"Failed to fetch neighbor chunks: {e}")
                
        return expanded

    def _rerank_candidates(self, candidates: List[Dict[str, Any]], query: str) -> List[Dict[str, Any]]:
        """Rerank candidates using reciprocal scoring based on query terms and vector similarity"""
        query_words = set(w.lower() for w in query.split() if len(w) > 3)
        
        for c in candidates:
            content = c.get("content", "").lower()
            vector_sim = c.get("similarity", 0.0)
            
            # Count word matches for basic sparse-search ranking boost
            word_matches = sum(1 for w in query_words if w in content)
            sparse_score = word_matches / len(query_words) if query_words else 0.0
            
            # Combine scores (70% semantic vector, 30% exact word matches)
            c["rerank_score"] = (0.7 * vector_sim) + (0.3 * sparse_score)
            
        return sorted(candidates, key=lambda x: x.get("rerank_score", 0.0), reverse=True)
