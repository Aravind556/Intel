"""
Question Processing Service
==========================
Analyzes incoming questions and extracts relevant metadata.
"""
from typing import Dict, Any, Optional
from enum import Enum
import re

class QuestionType(Enum):
    """Types of questions the system can handle"""
    FACTUAL = "factual"           # "What is calculus?"
    PROBLEM_SOLVING = "problem"   # "Solve this equation"
    CONCEPTUAL = "conceptual"     # "Explain the relationship between..."
    PROCEDURAL = "procedural"     # "How do I derive..."
    VERIFICATION = "verification" # "Is this answer correct?"

class DifficultyLevel(Enum):
    """Difficulty levels for questions"""
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"

class QuestionProcessor:
    """Service for analyzing and processing student questions"""
    
    def __init__(self):
        self.question_patterns = {
            QuestionType.FACTUAL: [
                r'\bwhat is\b', r'\bdefine\b', r'\bdefinition\b', 
                r'\bwho is\b', r'\bwhen did\b'
            ],
            QuestionType.PROBLEM_SOLVING: [
                r'\bsolve\b', r'\bcalculate\b', r'\bfind\b', 
                r'\bcompute\b', r'\bequation\b'
            ],
            QuestionType.CONCEPTUAL: [
                r'\bexplain\b', r'\bwhy\b', r'\bhow does\b', 
                r'\brelationship\b', r'\bdifference\b'
            ],
            QuestionType.PROCEDURAL: [
                r'\bhow to\b', r'\bhow do i\b', r'\bsteps\b', 
                r'\bprocedure\b', r'\bmethod\b'
            ],
            QuestionType.VERIFICATION: [
                r'\bis this correct\b', r'\bcheck\b', r'\bverify\b', 
                r'\bvalidate\b'
            ]
        }
        
        self.subject_keywords = {
            "mathematics": ["math", "calculus", "algebra", "geometry", "trigonometry", "statistics"],
            "physics": ["force", "energy", "motion", "wave", "particle", "quantum"],
            "chemistry": ["molecule", "atom", "reaction", "compound", "element"],
            "biology": ["cell", "organism", "genetics", "evolution", "ecosystem"],
            "computer_science": ["algorithm", "programming", "data structure", "software"]
        }
    
    async def analyze_question(self, question_text: str, user_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Analyze a question and extract relevant metadata
        
        Args:
            question_text: The student's question
            user_context: Additional context about the user (subjects, level, etc.)
            
        Returns:
            Dictionary containing question analysis results
        """
        question_text = question_text.lower().strip()
        
        analysis = {
            "original_text": question_text,
            "question_type": self._classify_question_type(question_text),
            "subject": self._detect_subject(question_text, user_context),
            "difficulty": self._assess_difficulty(question_text),
            "keywords": self._extract_keywords(question_text),
            "intent": self._determine_intent(question_text),
            "requires_calculation": self._needs_calculation(question_text),
            "requires_visual": self._needs_visual_explanation(question_text)
        }
        
        return analysis
    
    def _classify_question_type(self, question_text: str) -> QuestionType:
        """Classify the type of question based on patterns"""
        for question_type, patterns in self.question_patterns.items():
            for pattern in patterns:
                if re.search(pattern, question_text, re.IGNORECASE):
                    return question_type
        
        # Default to conceptual if no clear pattern
        return QuestionType.CONCEPTUAL
    
    def _detect_subject(self, question_text: str, user_context: Dict[str, Any] = None) -> Optional[str]:
        """Detect the academic subject from question content"""
        # Check for explicit subject keywords
        for subject, keywords in self.subject_keywords.items():
            for keyword in keywords:
                if keyword in question_text:
                    return subject
        
        # If user has active subjects, try to match
        if user_context and "subjects" in user_context:
            for subject in user_context["subjects"]:
                if subject.lower() in question_text:
                    return subject
        
        return None
    
    def _assess_difficulty(self, question_text: str) -> DifficultyLevel:
        """Assess the difficulty level of the question"""
        # Simple heuristics - can be improved with ML models
        advanced_indicators = ["derive", "prove", "theorem", "lemma", "corollary", "complex"]
        beginner_indicators = ["basic", "simple", "introduction", "what is", "define"]
        
        for indicator in advanced_indicators:
            if indicator in question_text:
                return DifficultyLevel.ADVANCED
        
        for indicator in beginner_indicators:
            if indicator in question_text:
                return DifficultyLevel.BEGINNER
        
        return DifficultyLevel.INTERMEDIATE
    
    def _extract_keywords(self, question_text: str) -> list:
        """Extract important keywords from the question"""
        # Remove common stop words and extract meaningful terms
        stop_words = {"what", "is", "the", "a", "an", "and", "or", "but", "how", "why", "when", "where"}
        words = re.findall(r'\b[a-zA-Z]{3,}\b', question_text)
        keywords = [word for word in words if word.lower() not in stop_words]
        return keywords[:10]  # Limit to top 10 keywords
    
    def _determine_intent(self, question_text: str) -> str:
        """Determine the user's intent behind the question"""
        if any(word in question_text for word in ["explain", "understand", "concept"]):
            return "explanation"
        elif any(word in question_text for word in ["solve", "calculate", "find"]):
            return "solution"
        elif any(word in question_text for word in ["example", "show me"]):
            return "example"
        elif any(word in question_text for word in ["step", "how to", "procedure"]):
            return "step_by_step"
        else:
            return "general_help"
    
    def _needs_calculation(self, question_text: str) -> bool:
        """Check if question requires mathematical calculations"""
        calc_indicators = ["solve", "calculate", "compute", "find", "=", "+", "-", "*", "/"]
        return any(indicator in question_text for indicator in calc_indicators)
    
    def _needs_visual_explanation(self, question_text: str) -> bool:
        """Check if question would benefit from visual explanations"""
        visual_indicators = ["graph", "diagram", "chart", "plot", "visualize", "draw", "geometry"]
        return any(indicator in question_text for indicator in visual_indicators)
