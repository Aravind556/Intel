"""
LLM Integration Service
======================
Handles communication with Large Language Models for response generation.
"""
from typing import Dict, Any, List, Optional
import openai
import os
from enum import Enum

class LLMProvider(Enum):
    """Supported LLM providers"""
    OPENAI_GPT4 = "gpt-4"
    OPENAI_GPT35 = "gpt-3.5-turbo"

class LLMIntegrator:
    """Service for integrating with Large Language Models"""
    
    def __init__(self):
        self.openai_client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.default_model = LLMProvider.OPENAI_GPT4
    
    async def generate_response(
        self, 
        question_analysis: Dict[str, Any], 
        context_data: Dict[str, Any],
        user_preferences: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Generate a response using LLM based on question and context
        
        Args:
            question_analysis: Analyzed question data
            context_data: Retrieved context chunks
            user_preferences: User's learning preferences
            
        Returns:
            Generated response with metadata
        """
        # Choose appropriate model based on question complexity
        model = self._select_model(question_analysis)
        
        # Build the prompt
        system_prompt = self._build_system_prompt(question_analysis, user_preferences)
        user_prompt = self._build_user_prompt(question_analysis, context_data)
        
        try:
            # TEMPORARY: Skip OpenAI API calls due to quota limits
            # Return mock response for testing
            mock_response = {
                "response_text": f"This is a mock response for your question: '{question_analysis.get('question', 'Unknown question')}'. The PDF processing and storage functionality is working correctly. OpenAI API calls are temporarily disabled due to quota limits.",
                "model_used": model.value,
                "token_usage": {
                    "prompt_tokens": 50,
                    "completion_tokens": 100,
                    "total_tokens": 150
                },
                "confidence_score": 0.8,
                "sources_used": self._extract_sources(context_data)
            }
            
            return mock_response
            
        except Exception as e:
            print(f"Error generating LLM response: {e}")
            return {
                "response_text": "I apologize, but I'm having trouble generating a response right now. Please try again later.",
                "model_used": None,
                "error": str(e),
                "confidence_score": 0.0,
                "sources_used": []
            }
    
    def _select_model(self, question_analysis: Dict[str, Any]) -> LLMProvider:
        """Select appropriate model based on question complexity"""
        difficulty = question_analysis.get("difficulty", "intermediate")
        question_type = question_analysis.get("question_type", "conceptual")
        
        # Use GPT-4 for complex questions, GPT-3.5 for simpler ones
        if (difficulty == "advanced" or 
            question_type in ["problem", "procedural"] or
            question_analysis.get("requires_calculation", False)):
            return LLMProvider.OPENAI_GPT4
        else:
            return LLMProvider.OPENAI_GPT35
    
    def _build_system_prompt(
        self, 
        question_analysis: Dict[str, Any], 
        user_preferences: Dict[str, Any] = None
    ) -> str:
        """Build the system prompt for the LLM"""
        
        difficulty = question_analysis.get("difficulty", "intermediate")
        question_type = question_analysis.get("question_type", "conceptual")
        subject = question_analysis.get("subject", "general")
        
        base_prompt = f"""You are an expert AI tutor specializing in {subject}. Your role is to provide clear, accurate, and helpful educational responses.

TEACHING STYLE:
- Be patient and encouraging
- Explain concepts step-by-step
- Use analogies and examples when helpful
- Adapt your language to the student's level ({difficulty})

RESPONSE REQUIREMENTS:
- Start with a direct answer to the question
- Provide detailed explanation with reasoning
- Include relevant examples when appropriate
- Cite sources from the provided context material
- End with suggestions for further learning

QUESTION TYPE: {question_type}
- Adjust your response style accordingly"""

        if question_type == "problem":
            base_prompt += "\n- Show step-by-step solution process\n- Explain the reasoning behind each step"
        elif question_type == "conceptual":
            base_prompt += "\n- Focus on understanding and connections\n- Use analogies to clarify complex ideas"
        elif question_type == "factual":
            base_prompt += "\n- Provide accurate, concise information\n- Include relevant context and background"
        elif question_type == "procedural":
            base_prompt += "\n- Break down the process into clear steps\n- Explain when and why to use this procedure"
        
        if user_preferences:
            learning_style = user_preferences.get("learning_style", "visual")
            base_prompt += f"\n\nUSER PREFERENCES:\n- Learning style: {learning_style}"
            if learning_style == "visual":
                base_prompt += "\n- Include descriptions of diagrams or visual elements when helpful"
        
        return base_prompt
    
    def _build_user_prompt(
        self, 
        question_analysis: Dict[str, Any], 
        context_data: Dict[str, Any]
    ) -> str:
        """Build the user prompt with question and context"""
        
        question = question_analysis["original_text"]
        context_chunks = context_data.get("context_chunks", [])
        
        prompt = f"STUDENT QUESTION:\n{question}\n\n"
        
        if context_chunks:
            prompt += "RELEVANT CONTEXT FROM STUDY MATERIALS:\n"
            for i, chunk in enumerate(context_chunks[:5], 1):  # Limit to top 5 chunks
                content = chunk.get("content", "")
                source = chunk.get("pdf_title", "Unknown source")
                page = chunk.get("page_number", "Unknown page")
                
                prompt += f"\n[Source {i}: {source}, Page {page}]\n{content}\n"
            
            prompt += "\nPlease base your answer on the provided context material and cite your sources appropriately."
        else:
            prompt += "No specific context material was found. Please provide a general educational response based on your knowledge."
        
        # Add specific instructions based on question analysis
        if question_analysis.get("requires_calculation"):
            prompt += "\n\nNote: This question requires mathematical calculations. Please show your work step-by-step."
        
        if question_analysis.get("requires_visual"):
            prompt += "\n\nNote: Consider describing visual elements, diagrams, or graphs that would help explain this concept."
        
        return prompt
    
    def _calculate_confidence(
        self, 
        context_data: Dict[str, Any], 
        question_analysis: Dict[str, Any]
    ) -> float:
        """Calculate confidence score for the response"""
        base_confidence = 0.5
        
        # Boost confidence based on context quality
        context_chunks = context_data.get("context_chunks", [])
        if context_chunks:
            avg_similarity = sum(chunk.get("similarity", 0) for chunk in context_chunks) / len(context_chunks)
            base_confidence += avg_similarity * 0.4
        
        # Adjust based on question complexity
        difficulty = question_analysis.get("difficulty", "intermediate")
        if difficulty == "beginner":
            base_confidence += 0.1
        elif difficulty == "advanced":
            base_confidence -= 0.1
        
        # Adjust based on subject match
        if question_analysis.get("subject"):
            base_confidence += 0.1
        
        return min(1.0, max(0.0, base_confidence))
    
    def _extract_sources(self, context_data: Dict[str, Any]) -> List[Dict[str, str]]:
        """Extract source information from context data"""
        sources = []
        context_chunks = context_data.get("context_chunks", [])
        
        seen_sources = set()
        for chunk in context_chunks:
            source_title = chunk.get("pdf_title", "Unknown")
            page_number = chunk.get("page_number", "Unknown")
            source_key = f"{source_title}_{page_number}"
            
            if source_key not in seen_sources:
                sources.append({
                    "title": source_title,
                    "page": str(page_number),
                    "relevance": chunk.get("similarity", 0)
                })
                seen_sources.add(source_key)
        
        return sources
