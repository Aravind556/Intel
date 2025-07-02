"""
Google Gemini Integration for AI Tutor

Alternative to OpenAI with generous free tier.
"""

import logging
import os
from typing import Dict, Any, List, Optional
import google.generativeai as genai

logger = logging.getLogger(__name__)


class GeminiIntegrator:
    """Service for integrating with Google Gemini AI"""
    
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.model_name = "gemini-1.5-flash"  # Free tier model
        self.embedding_model = "models/embedding-001"
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize Gemini client."""
        if not self.api_key:
            logger.warning("Gemini API key not found. Gemini integration will be disabled.")
            self.client = None
            return
            
        try:
            genai.configure(api_key=self.api_key)
            self.client = genai.GenerativeModel(self.model_name)
            logger.info("Gemini client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Gemini client: {str(e)}")
            self.client = None
    
    async def generate_response(
        self, 
        question_analysis: Dict[str, Any], 
        context_data: Dict[str, Any],
        user_preferences: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Generate a response using Gemini based on question and context
        """
        if not self.client:
            return self._get_fallback_response(question_analysis)
            
        try:
            # Build the prompt
            system_prompt = self._build_system_prompt(question_analysis, user_preferences)
            user_prompt = self._build_user_prompt(question_analysis, context_data)
            
            full_prompt = f"{system_prompt}\n\nUser Question: {user_prompt}"
            
            # Generate response
            response = self.client.generate_content(full_prompt)
            
            return {
                "response_text": response.text,
                "model_used": self.model_name,
                "token_usage": {
                    "prompt_tokens": len(full_prompt.split()),  # Approximate
                    "completion_tokens": len(response.text.split()),  # Approximate
                    "total_tokens": len(full_prompt.split()) + len(response.text.split())
                },
                "confidence_score": 0.85,  # Default confidence
                "sources_used": self._extract_sources(context_data)
            }
            
        except Exception as e:
            logger.error(f"Error generating Gemini response: {e}")
            return self._get_fallback_response(question_analysis)
    
    async def generate_embeddings(self, texts: List[str]) -> List[Optional[List[float]]]:
        """Generate embeddings using Gemini embedding model"""
        if not self.api_key:
            logger.warning("Gemini API key not available for embeddings")
            return [None] * len(texts)
            
        try:
            embeddings = []
            for text in texts:
                result = genai.embed_content(
                    model=self.embedding_model,
                    content=text,
                    task_type="retrieval_document"
                )
                embeddings.append(result['embedding'])
            
            logger.info(f"Generated {len(embeddings)} embeddings using Gemini")
            return embeddings
            
        except Exception as e:
            logger.error(f"Error generating Gemini embeddings: {e}")
            return [None] * len(texts)
    
    def _build_system_prompt(self, question_analysis: Dict[str, Any], user_preferences: Dict[str, Any] = None) -> str:
        """Build system prompt for Gemini"""
        return """You are an AI tutor assistant helping students learn from their uploaded documents. 
        Provide clear, educational responses based on the provided context. 
        Focus on helping students understand concepts rather than just giving answers.
        Be encouraging and supportive in your tone."""
    
    def _build_user_prompt(self, question_analysis: Dict[str, Any], context_data: Dict[str, Any]) -> str:
        """Build user prompt with context"""
        question = question_analysis.get('question', 'No question provided')
        context = context_data.get('relevant_chunks', [])
        
        context_text = "\n\n".join([chunk.get('content', '') for chunk in context[:3]])  # Top 3 chunks
        
        return f"""Question: {question}

Relevant Context from Documents:
{context_text}

Please provide a helpful educational response based on this context."""
    
    def _extract_sources(self, context_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract source information"""
        chunks = context_data.get('relevant_chunks', [])
        return [{"pdf_id": chunk.get('pdf_id'), "page": chunk.get('page_number')} for chunk in chunks[:3]]
    
    def _get_fallback_response(self, question_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback response when Gemini is unavailable"""
        return {
            "response_text": f"I'm currently unable to process your question: '{question_analysis.get('question', 'Unknown question')}'. Please check the AI service configuration.",
            "model_used": "fallback",
            "token_usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            "confidence_score": 0.0,
            "sources_used": []
        }
    
    def is_available(self) -> bool:
        """Check if Gemini is available"""
        return self.client is not None
