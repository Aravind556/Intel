"""
Context Retrieval Service
========================
Retrieves relevant context from PDF knowledge base using vector search.
"""
from typing import List, Dict, Any, Optional
from core.database.manager import PDFDatabaseManager
from modules.pdf_processor.services.embedding_generator import EmbeddingGenerator

class ContextRetriever:
    """Service for retrieving relevant context from PDF documents"""
    
    def __init__(self, db_manager: PDFDatabaseManager):
        self.db_manager = db_manager
        self.embedding_generator = EmbeddingGenerator()
    
    async def get_relevant_context(
        self, 
        question_analysis: Dict[str, Any], 
        user_id: str,
        max_chunks: int = 5
    ) -> Dict[str, Any]:
        """
        Retrieve relevant context for answering a question
        
        Args:
            question_analysis: Output from QuestionProcessor
            user_id: User ID for filtering content
            max_chunks: Maximum number of context chunks to retrieve
            
        Returns:
            Dictionary containing relevant context and metadata
        """
        question_text = question_analysis["original_text"]
        subject = question_analysis.get("subject")
        
        # Generate embedding for the question
        question_embedding = await self._generate_embedding(question_text)
        
        # Retrieve context based on different strategies
        context_chunks = []
        
        # Strategy 1: Subject-specific search
        if subject:
            subject_chunks = await self._search_by_subject(
                question_embedding, subject, user_id, max_chunks
            )
            context_chunks.extend(subject_chunks)
        
        # Strategy 2: Cross-subject search if not enough results
        if len(context_chunks) < max_chunks:
            remaining_count = max_chunks - len(context_chunks)
            general_chunks = await self._search_general(
                question_embedding, user_id, remaining_count
            )
            context_chunks.extend(general_chunks)
        
        # Rank and filter context
        ranked_context = self._rank_context_relevance(
            context_chunks, question_analysis
        )
        
        return {
            "context_chunks": ranked_context[:max_chunks],
            "total_found": len(context_chunks),
            "search_strategies_used": self._get_search_strategies(subject),
            "context_summary": self._summarize_context(ranked_context[:max_chunks])
        }
    
    async def _generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text using local sentence transformers"""
        try:
            embedding = await self.embedding_generator.generate_single_embedding(text)
            return embedding if embedding is not None else [0.1] * 384
        except Exception as e:
            print(f"Error generating embedding: {e}")
            # Return dummy embedding as fallback
            return [0.1] * 384
    
    async def _search_by_subject(
        self, 
        query_embedding: List[float], 
        subject: str, 
        user_id: str, 
        count: int
    ) -> List[Dict[str, Any]]:
        """Search for context within a specific subject"""
        try:
            results = await self.db_manager.search_documents_by_subject(
                query_embedding=query_embedding,
                subject_name=subject,
                user_id=user_id,
                match_threshold=0.7,
                match_count=count
            )
            return results
        except Exception as e:
            print(f"Error in subject search: {e}")
            return []
    
    async def _search_general(
        self, 
        query_embedding: List[float], 
        user_id: str, 
        count: int
    ) -> List[Dict[str, Any]]:
        """General search across all user's documents"""
        try:
            # Get all user subjects first
            subjects = await self.db_manager.get_user_subjects(user_id)
            all_results = []
            
            for subject_info in subjects:
                subject_name = subject_info.get("subject_name", "")
                results = await self.db_manager.search_documents_by_subject(
                    query_embedding=query_embedding,
                    subject_name=subject_name,
                    user_id=user_id,
                    match_threshold=0.6,
                    match_count=2  # Fewer per subject for diversity
                )
                all_results.extend(results)
            
            # Sort by similarity and return top results
            all_results.sort(key=lambda x: x.get("similarity", 0), reverse=True)
            return all_results[:count]
            
        except Exception as e:
            print(f"Error in general search: {e}")
            return []
    
    def _rank_context_relevance(
        self, 
        context_chunks: List[Dict[str, Any]], 
        question_analysis: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Rank context chunks by relevance to the question"""
        keywords = set(word.lower() for word in question_analysis.get("keywords", []))
        
        for chunk in context_chunks:
            relevance_score = chunk.get("similarity", 0)
            content = chunk.get("content", "").lower()
            
            # Boost score for keyword matches
            keyword_matches = sum(1 for keyword in keywords if keyword in content)
            keyword_boost = keyword_matches * 0.1
            
            # Boost score for question type relevance
            question_type = question_analysis.get("question_type")
            if question_type and self._matches_question_type(content, question_type):
                relevance_score += 0.15
            
            chunk["final_relevance_score"] = relevance_score + keyword_boost
        
        # Sort by final relevance score
        return sorted(context_chunks, key=lambda x: x.get("final_relevance_score", 0), reverse=True)
    
    def _matches_question_type(self, content: str, question_type) -> bool:
        """Check if content matches the question type"""
        # Simple keyword matching - can be improved
        type_indicators = {
            "factual": ["definition", "is defined as", "refers to"],
            "problem": ["solve", "solution", "calculate", "formula"],
            "conceptual": ["because", "reason", "principle", "concept"],
            "procedural": ["step", "method", "procedure", "process"]
        }
        
        indicators = type_indicators.get(question_type.value, [])
        return any(indicator in content for indicator in indicators)
    
    def _get_search_strategies(self, subject: Optional[str]) -> List[str]:
        """Get list of search strategies used"""
        strategies = ["vector_similarity"]
        if subject:
            strategies.append("subject_specific")
        strategies.append("cross_subject")
        return strategies
    
    def _summarize_context(self, context_chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create a summary of the retrieved context"""
        if not context_chunks:
            return {"total_chunks": 0, "sources": [], "topics_covered": []}
        
        sources = list(set(chunk.get("pdf_title", "Unknown") for chunk in context_chunks))
        
        # Extract topics/concepts mentioned
        all_content = " ".join(chunk.get("content", "") for chunk in context_chunks)
        topics = self._extract_topics(all_content)
        
        return {
            "total_chunks": len(context_chunks),
            "sources": sources,
            "topics_covered": topics,
            "avg_relevance": sum(chunk.get("similarity", 0) for chunk in context_chunks) / len(context_chunks)
        }
    
    def _extract_topics(self, content: str) -> List[str]:
        """Extract key topics from content"""
        # Simple topic extraction - can be improved with NLP
        import re
        
        # Look for capitalized terms that might be concepts
        topics = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', content)
        
        # Filter and deduplicate
        topics = list(set(topic for topic in topics if len(topic) > 3))
        return topics[:10]  # Return top 10 topics
