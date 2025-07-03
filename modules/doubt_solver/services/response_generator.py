"""
Response Generator Service
=========================
Orchestrates the complete response generation process and formats the final output.
"""
from typing import Dict, Any, List, Optional
from .question_processor import QuestionProcessor
from .context_retriever import ContextRetriever
from .llm_integrator import LLMIntegrator
from core.database.manager import PDFDatabaseManager
import uuid
from datetime import datetime

class ResponseGenerator:
    """Main service that orchestrates the doubt-solving process"""
    
    def __init__(self, db_manager: PDFDatabaseManager):
        self.db_manager = db_manager
        self.question_processor = QuestionProcessor()
        self.context_retriever = ContextRetriever(db_manager)
        self.llm_integrator = LLMIntegrator()
    
    async def solve_doubt(
        self, 
        question: str, 
        user_id: str,
        user_preferences: Dict[str, Any] = None,
        session_id: str = None
    ) -> Dict[str, Any]:
        """
        Complete doubt-solving pipeline
        
        Args:
            question: Student's question
            user_id: User identifier
            user_preferences: User's learning preferences
            session_id: Optional session ID for tracking
            
        Returns:
            Complete response with answer, sources, and metadata
        """
        # Generate session ID if not provided
        if not session_id:
            session_id = str(uuid.uuid4())
        
        response_data = {
            "session_id": session_id,
            "timestamp": datetime.utcnow().isoformat(),
            "question": question,
            "user_id": user_id,
            "processing_steps": [],
            "success": False
        }
        
        try:
            # Step 1: Analyze the question
            response_data["processing_steps"].append("question_analysis")
            user_context = await self._get_user_context(user_id)
            question_analysis = await self.question_processor.analyze_question(
                question, user_context
            )
            response_data["question_analysis"] = question_analysis
            
            # Step 2: Retrieve relevant context
            response_data["processing_steps"].append("context_retrieval")
            context_data = await self.context_retriever.get_relevant_context(
                question_analysis, user_id
            )
            response_data["context_data"] = context_data
            
            # Step 3: Generate LLM response
            response_data["processing_steps"].append("response_generation")
            llm_response = await self.llm_integrator.generate_response(
                question_analysis, context_data, user_preferences
            )
            response_data["llm_response"] = llm_response
            
            # Step 4: Format final response
            response_data["processing_steps"].append("response_formatting")
            formatted_response = self._format_final_response(
                question_analysis, context_data, llm_response
            )
            response_data.update(formatted_response)
            
            response_data["success"] = True
            
            # Step 5: Log the interaction (optional)
            await self._log_interaction(response_data)
            
        except Exception as e:
            response_data["error"] = str(e)
            response_data["fallback_response"] = self._generate_fallback_response(question)
        
        return response_data
    
    async def _get_user_context(self, user_id: str) -> Dict[str, Any]:
        """Get user context including subjects and preferences"""
        try:
            subjects = await self.db_manager.get_user_subjects(user_id)
            user_info = await self.db_manager.get_user(user_id)
            
            return {
                "subjects": [s.get("subject_name", "") for s in subjects],
                "user_info": user_info,
                "available_pdfs": sum(s.get("pdf_count", 0) for s in subjects)
            }
        except Exception as e:
            print(f"Error getting user context: {e}")
            return {"subjects": [], "user_info": None, "available_pdfs": 0}
    
    def _format_final_response(
        self, 
        question_analysis: Dict[str, Any], 
        context_data: Dict[str, Any], 
        llm_response: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Format the final structured response"""
        
        response_text = llm_response.get("response_text", "")
        
        # Parse the response into sections (this could be improved with better parsing)
        sections = self._parse_response_sections(response_text)
        
        formatted_response = {
            "answer": {
                "response_text": response_text,  # Keep original full response
                "quick_answer": sections.get("quick_answer", ""),
                "detailed_explanation": sections.get("explanation", response_text),
                "examples": sections.get("examples", ""),
                "step_by_step": sections.get("steps", []),
                "model_used": llm_response.get("model_used", "unknown")
            },
            "sources": {
                "primary_sources": llm_response.get("sources_used", []),
                "context_summary": context_data.get("context_summary", {}),
                "search_strategies": context_data.get("search_strategies_used", [])
            },
            "metadata": {
                "confidence_score": llm_response.get("confidence_score", 0.0),
                "question_type": question_analysis.get("question_type", "").value if hasattr(question_analysis.get("question_type", ""), 'value') else str(question_analysis.get("question_type", "")),
                "difficulty_level": question_analysis.get("difficulty", "").value if hasattr(question_analysis.get("difficulty", ""), 'value') else str(question_analysis.get("difficulty", "")),
                "subject": question_analysis.get("subject", ""),
                "model_used": llm_response.get("model_used", ""),
                "token_usage": llm_response.get("token_usage", {})
            },
            "next_steps": {
                "related_questions": self._generate_related_questions(question_analysis),
                "practice_suggestions": self._generate_practice_suggestions(question_analysis),
                "further_reading": self._suggest_further_reading(context_data)
            }
        }
        
        return formatted_response
    
    def _parse_response_sections(self, response_text: str) -> Dict[str, Any]:
        """Parse LLM response into structured sections"""
        # Simple parsing - can be improved with better NLP
        sections = {}
        
        lines = response_text.split('\n')
        current_section = "explanation"
        current_content = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Look for section headers
            if any(keyword in line.lower() for keyword in ["step 1", "first", "1."]):
                if current_content:
                    sections[current_section] = '\n'.join(current_content)
                current_section = "steps"
                current_content = [line]
            elif any(keyword in line.lower() for keyword in ["example", "for instance"]):
                if current_content:
                    sections[current_section] = '\n'.join(current_content)
                current_section = "examples"
                current_content = [line]
            else:
                current_content.append(line)
        
        # Add remaining content
        if current_content:
            sections[current_section] = '\n'.join(current_content)
        
        # Extract quick answer (first sentence or paragraph)
        if "explanation" in sections:
            explanation = sections["explanation"]
            sentences = explanation.split('. ')
            if sentences:
                sections["quick_answer"] = sentences[0] + '.'
        
        return sections
    
    def _generate_related_questions(self, question_analysis: Dict[str, Any]) -> List[str]:
        """Generate related questions based on the current question"""
        subject = question_analysis.get("subject", "")
        question_type = question_analysis.get("question_type", "")
        keywords = question_analysis.get("keywords", [])
        
        # Simple template-based generation - can be improved with LLM
        related_questions = []
        
        if keywords:
            main_keyword = keywords[0] if keywords else "this topic"
            related_questions.extend([
                f"What are the applications of {main_keyword}?",
                f"How does {main_keyword} relate to other concepts?",
                f"What are common mistakes when working with {main_keyword}?"
            ])
        
        if subject:
            related_questions.extend([
                f"What are the fundamentals of {subject} I should know?",
                f"What are advanced topics in {subject}?"
            ])
        
        return related_questions[:5]  # Limit to 5 suggestions
    
    def _generate_practice_suggestions(self, question_analysis: Dict[str, Any]) -> List[str]:
        """Generate practice suggestions based on question type"""
        question_type = question_analysis.get("question_type", "")
        difficulty = question_analysis.get("difficulty", "")
        
        suggestions = []
        
        if str(question_type) == "problem":
            suggestions.extend([
                "Practice similar problems with different values",
                "Try solving without looking at the solution first",
                "Work through the problem step-by-step on paper"
            ])
        elif str(question_type) == "conceptual":
            suggestions.extend([
                "Create concept maps to connect related ideas",
                "Explain the concept to someone else",
                "Find real-world examples of this concept"
            ])
        elif str(question_type) == "procedural":
            suggestions.extend([
                "Practice the procedure with different examples",
                "Create a checklist of steps to follow",
                "Time yourself to improve efficiency"
            ])
        
        return suggestions
    
    def _suggest_further_reading(self, context_data: Dict[str, Any]) -> List[str]:
        """Suggest further reading based on retrieved context"""
        sources = context_data.get("context_summary", {}).get("sources", [])
        topics = context_data.get("context_summary", {}).get("topics_covered", [])
        
        suggestions = []
        
        # Suggest reviewing the sources that were most helpful
        for source in sources[:3]:  # Top 3 sources
            suggestions.append(f"Review more sections from {source}")
        
        # Suggest exploring related topics
        for topic in topics[:2]:  # Top 2 topics
            suggestions.append(f"Explore more about {topic}")
        
        return suggestions
    
    def _generate_fallback_response(self, question: str) -> Dict[str, Any]:
        """Generate a fallback response when the main process fails"""
        return {
            "answer": {
                "quick_answer": "I'm having trouble processing your question right now.",
                "detailed_explanation": f"I apologize, but I encountered an issue while trying to answer your question: '{question}'. Please try rephrasing your question or contact support if the problem persists.",
                "examples": [],
                "step_by_step": []
            },
            "sources": {"primary_sources": [], "context_summary": {}, "search_strategies": []},
            "metadata": {"confidence_score": 0.0, "error": True},
            "next_steps": {
                "related_questions": ["Try asking a simpler version of this question"],
                "practice_suggestions": ["Review your study materials"],
                "further_reading": []
            }
        }
    
    async def _log_interaction(self, response_data: Dict[str, Any]) -> None:
        """Log the interaction for analytics and improvement"""
        # This could be implemented to store interaction data
        # For now, just print for debugging
        print(f"Interaction logged: Session {response_data.get('session_id', 'Unknown')}")
        pass
