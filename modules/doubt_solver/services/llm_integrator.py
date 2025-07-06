"""
LLM Integration Service
======================
Handles communication with Large Language Models for response generation using Google Gemini.
"""
from typing import Dict, Any, List, Optional
import google.generativeai as genai
import os
from enum import Enum
import logging

logger = logging.getLogger(__name__)

class LLMProvider(Enum):
    """Supported LLM providers"""
    GEMINI_FLASH = "gemini-1.5-flash"
    GEMINI_PRO = "gemini-1.5-pro"

class LLMIntegrator:
    """Service for integrating with Google Gemini"""
    
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.default_model = LLMProvider.GEMINI_FLASH
        self.client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize Gemini client."""
        if not self.api_key:
            print("\n❌ ERROR: Gemini API key not found in environment variables")
            print("Please set the GEMINI_API_KEY environment variable")
            print("LLM integration will be disabled - the system won't be able to respond to questions")
            logger.warning("Gemini API key not found. LLM integration will be disabled.")
            return
            
        try:
            print("\n🔄 Initializing Gemini client...")
            genai.configure(api_key=self.api_key)
            self.client = genai.GenerativeModel(self.default_model.value)
            print(f"✅ Gemini client initialized with model {self.default_model.value}")
            logger.info("Gemini client initialized successfully")
        except Exception as e:
            error_msg = f"Failed to initialize Gemini client: {str(e)}"
            print(f"\n❌ {error_msg}")
            logger.error(error_msg)
            self.client = None
    
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
            if not self.client:
                return self._get_fallback_response(question_analysis)
                
            # Choose appropriate model based on question complexity
            model = self._select_model(question_analysis)
            
            # Build the prompt
            system_prompt = self._build_system_prompt(question_analysis, user_preferences)
            user_prompt = self._build_user_prompt(question_analysis, context_data)
            
            full_prompt = f"{system_prompt}\n\n{user_prompt}"
            
            # Generate response using Gemini with improved settings
            generation_config = {
                'temperature': 0.7,
                'top_p': 0.8,
                'top_k': 40,
                'max_output_tokens': 2048,
            }
            
            response = self.client.generate_content(
                full_prompt,
                generation_config=generation_config
            )
            
            return {
                "response_text": response.text,
                "model_used": model.value,
                "token_usage": {
                    "prompt_tokens": len(full_prompt.split()),  # Approximate
                    "completion_tokens": len(response.text.split()),  # Approximate
                    "total_tokens": len(full_prompt.split()) + len(response.text.split())
                },
                "confidence_score": self._calculate_confidence(context_data, question_analysis),
                "sources_used": self._extract_sources(context_data)
            }
            
        except Exception as e:
            logger.error(f"Error generating LLM response: {e}")
            return self._get_fallback_response(question_analysis)
    
    def _get_fallback_response(self, question_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback response when Gemini is unavailable"""
        return {
            "response_text": f"I'm currently unable to process your question: '{question_analysis.get('question', 'Unknown question')}'. Please check the AI service configuration.",
            "model_used": "fallback",
            "token_usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            "confidence_score": 0.0,
            "sources_used": []
        }
    
    def _select_model(self, question_analysis: Dict[str, Any]) -> LLMProvider:
        """Select appropriate model based on question complexity"""
        difficulty = question_analysis.get("difficulty", "intermediate")
        question_type = question_analysis.get("question_type", "conceptual")
        
        # Use Gemini Pro for complex questions, Flash for simpler ones
        if (difficulty == "advanced" or 
            question_type in ["problem", "procedural"]):
            return LLMProvider.GEMINI_PRO
        
        return LLMProvider.GEMINI_FLASH
    
    def _build_system_prompt(
        self, 
        question_analysis: Dict[str, Any], 
        user_preferences: Dict[str, Any] = None
    ) -> str:
        """Build the system prompt for the LLM"""
        
        difficulty = question_analysis.get("difficulty", "intermediate")
        question_type = question_analysis.get("question_type", "conceptual")
        subject = question_analysis.get("subject", "general")
        
        base_prompt = f"""You are an expert AI tutor specializing in {subject}. Your mission is to provide exceptionally clear, accurate, and educational responses based EXCLUSIVELY on the provided study materials.

🚨 CRITICAL CONTEXT RULES 🚨
1. You MUST ONLY use information from the provided context material
2. You are ABSOLUTELY FORBIDDEN from using your general knowledge or training data
3. If the context doesn't contain enough information, you MUST say so clearly and stop there
4. You CANNOT make up information or supplement from external sources under any circumstances
5. Every statement must be traceable to the provided context
6. If doing a document-specific search and NO relevant context is found, you MUST state the document doesn't contain that information

CORE TEACHING PHILOSOPHY:
- Always prioritize student understanding over showing off knowledge
- Break down complex concepts into digestible, logical steps
- Use encouraging, supportive language that builds confidence
- Connect abstract concepts to concrete, relatable examples from the PROVIDED CONTEXT ONLY
- Always cite sources when using provided material

MANDATORY RESPONSE STRUCTURE:
You MUST structure your response using this EXACT format with these EXACT emoji headings:

🎯 **DIRECT ANSWER FROM DOCUMENT**
Answer based ONLY on the provided context. If context is insufficient, state: "The provided document does not contain enough information to fully answer this question."

📚 **EXPLANATION FROM CONTEXT**
Explain using ONLY information found in the provided material:
• Core concepts mentioned in the context
• Key definitions found in the documents
• Information flow as presented in the source material
• Any connections explicitly made in the documents

💡 **EXAMPLES FROM DOCUMENT**
Provide examples ONLY from the provided context:
• Specific examples mentioned in the documents
• Case studies or scenarios described in the material
• Applications explicitly discussed in the context

🔧 **PROCESS FROM DOCUMENT** (if applicable)
Show steps ONLY as described in the provided material:
• Follow procedures exactly as outlined in the documents
• Use formulas or methods mentioned in the context
• Reference specific approaches described in the material

📖 **SOURCE CITATIONS**
MANDATORY for every piece of information: (Source: Document Name, Page Number)

⚠️ **CONTEXT LIMITATIONS**
Clearly state what information is missing from the provided context and what additional sources would be needed.

QUESTION CONTEXT: {question_type} question at {difficulty} level"""

        # Add type-specific instructions
        if question_type == "problem":
            base_prompt += """

PROBLEM-SOLVING REQUIREMENTS:
- You MUST include the "🔧 **PROCESS FROM DOCUMENT**" section
- Use ONLY methods and formulas mentioned in the provided context
- If the context doesn't contain solution methods, clearly state this limitation
- Show every calculation step with clear explanations
- Explain the reasoning and principles behind each step
- Include formulas and show how to apply them
- Verify your final answer and explain how you checked it
- Point out common errors students make with this type of problem"""
        elif question_type == "conceptual":
            base_prompt += """

CONCEPTUAL UNDERSTANDING REQUIREMENTS:
- Focus heavily on the "📚 **COMPREHENSIVE EXPLANATION**" section
- Explain the deeper meaning and significance of concepts
- Use multiple analogies in the "💡 **PRACTICAL EXAMPLES**" section
- Connect to broader themes and show relationships between ideas
- Help students build mental models for understanding
- Address common misconceptions students have about this topic"""
        elif question_type == "factual":
            base_prompt += """

FACTUAL INFORMATION REQUIREMENTS:
- Provide precise, accurate information in "🎯 **DIRECT ANSWER**"
- Include relevant context and background in explanation
- Be very thorough with "📖 **SOURCE CITATIONS**"
- Explain the significance and implications of the facts
- Distinguish clearly between established facts and interpretations
- Provide multiple perspectives when topics have different viewpoints"""
        elif question_type == "procedural":
            base_prompt += """

PROCEDURAL LEARNING REQUIREMENTS:
- You MUST include the "🔧 **STEP-BY-STEP PROCESS**" section
- Break down every action into clear, sequential steps
- Explain the logic and reasoning behind each step
- Provide practical tips for effective execution
- Mention common variations and when to use alternatives
- Include troubleshooting advice for when things go wrong"""
        
        base_prompt += f"""

DIFFICULTY LEVEL: {difficulty}"""
        
        if difficulty == "beginner":
            base_prompt += """
BEGINNER LEVEL ADAPTATIONS:
- Use simple, clear language avoiding unnecessary jargon
- Define all technical terms when first introduced
- Provide extra context and background information
- Break complex ideas into smaller, digestible parts
- Use encouraging language and build confidence
- Include more basic examples and simpler analogies
- Check understanding frequently and recap key points"""
        elif difficulty == "intermediate":
            base_prompt += """
INTERMEDIATE LEVEL ADAPTATIONS:
- Use appropriate technical terminology with brief explanations
- Connect to previous knowledge and build upon existing foundation
- Provide moderate detail with opportunities for deeper exploration
- Challenge the student to think critically and make connections
- Include examples that bridge basic and advanced concepts
- Encourage independent thinking while providing guidance"""
        elif difficulty == "advanced":
            base_prompt += """
ADVANCED LEVEL ADAPTATIONS:
- Use precise technical language and advanced terminology
- Assume solid foundational knowledge in the subject area
- Provide in-depth analysis and multiple perspectives
- Encourage independent thinking and original research
- Include cutting-edge developments and current debates
- Challenge students to synthesize information from multiple sources
- Focus on critical analysis and evaluation of ideas"""
        
        if user_preferences:
            learning_style = user_preferences.get("learning_style", "balanced")
            base_prompt += f"""

USER LEARNING PREFERENCES:
Learning Style: {learning_style}"""
            if learning_style == "visual":
                base_prompt += """
VISUAL LEARNER ADAPTATIONS:
- Describe visual elements, diagrams, charts, or graphs in detail
- Use spatial metaphors and visual analogies
- Suggest creating mind maps, diagrams, or visual organizers
- Reference colors, shapes, and spatial relationships
- Recommend drawing or sketching exercises to reinforce learning"""
            elif learning_style == "auditory":
                base_prompt += """
AUDITORY LEARNER ADAPTATIONS:
- Use rhythm, patterns, and verbal mnemonics
- Suggest reading aloud or discussing concepts with others
- Include sound-based analogies and musical references
- Recommend recording and listening to explanations
- Use repetition and verbal reinforcement techniques"""
            elif learning_style == "kinesthetic":
                base_prompt += """
KINESTHETIC LEARNER ADAPTATIONS:
- Suggest hands-on activities, experiments, or demonstrations
- Use physical analogies and movement-based examples
- Recommend practical applications and real-world practice
- Include interactive exercises and role-playing scenarios
- Connect learning to physical activities and manipulative experiences"""
        
        base_prompt += """

CRITICAL FORMATTING REQUIREMENTS:
✅ ALWAYS start each section with the exact emoji and header format shown above
✅ NEVER skip any of the 6 mandatory sections
✅ Use bullet points (•) and numbered lists for clarity
✅ Keep Quick Answer to 1-2 sentences maximum
✅ Make Detailed Explanation comprehensive but readable
✅ Always include at least one example or application
✅ Cite every piece of information from provided sources
✅ End with encouraging and helpful next steps

EXAMPLE OF PERFECT FORMATTING:
🎯 **QUICK ANSWER**
Your concise answer here.

📚 **DETAILED EXPLANATION**
Your detailed explanation with bullet points:
• First key point
• Second key point

[Continue with all sections...]

QUALITY STANDARDS & REQUIREMENTS:
✅ ACCURACY: Only state information you are confident about
✅ COMPLETENESS: Address all aspects of the student's question
✅ CLARITY: Use clear, engaging, and appropriate language
✅ STRUCTURE: Follow the mandatory response structure exactly
✅ ENGAGEMENT: Make learning enjoyable and accessible
✅ ENCOURAGEMENT: Always end with positive reinforcement and next steps
✅ CITATIONS: Properly cite all source material used

NEVER make up information - if unsure, acknowledge uncertainty clearly."""
        
        return base_prompt
    
    def _build_user_prompt(
        self, 
        question_analysis: Dict[str, Any], 
        context_data: Dict[str, Any]
    ) -> str:
        """Build the user prompt with question and context"""
        
        question = question_analysis["original_text"]
        context_chunks = context_data.get("context_chunks", [])
        context_summary = context_data.get("context_summary", {})
        search_strategies = context_data.get("search_strategies_used", [])
        
        # Check if this is a document-specific search
        is_document_specific = "document_specific" in search_strategies
        
        prompt = f"""
═══════════════════════════════════════════════════════════════
                          STUDENT QUESTION
═══════════════════════════════════════════════════════════════

QUESTION: "{question}"

ANALYSIS:
• Type: {question_analysis.get('question_type', 'general')}
• Subject Area: {question_analysis.get('subject', 'general')}
• Difficulty Level: {question_analysis.get('difficulty', 'intermediate')}
• Key Terms: {', '.join(question_analysis.get('keywords', []))}"""
        
        if question_analysis.get("requires_calculation"):
            prompt += "\n• Special Requirements: Mathematical calculations needed"
        if question_analysis.get("requires_visual"):
            prompt += "\n• Special Requirements: Visual explanation needed"
        
        # Check if we have meaningful context content and handle document-specific searches more strictly
        has_meaningful_context = bool(context_chunks and any(
            chunk.get("content", "").strip() and len(chunk.get("content", "").strip()) > 50
            for chunk in context_chunks
        ))
        
        # For document-specific searches, be extra strict about relevance
        if is_document_specific and context_chunks:
            # Check if context is actually relevant (similarity threshold)
            relevant_chunks = [
                chunk for chunk in context_chunks 
                if chunk.get("similarity", 0) > 0.4  # Higher threshold for document-specific
            ]
            has_meaningful_context = bool(relevant_chunks and any(
                chunk.get("content", "").strip() and len(chunk.get("content", "").strip()) > 50
                for chunk in relevant_chunks
            ))
            if has_meaningful_context:
                context_chunks = relevant_chunks  # Use only the relevant ones

        if has_meaningful_context:
            prompt += f"""

═══════════════════════════════════════════════════════════════
                       RELEVANT STUDY MATERIALS
═══════════════════════════════════════════════════════════════

SEARCH SUMMARY:
• Strategy Used: {', '.join(search_strategies)}
• Total Sources: {len(context_chunks)} relevant chunks from {len(context_summary.get('sources', []))} documents
• Topics Covered: {', '.join(context_summary.get('topics_covered', [])[:10])}

CONTEXT MATERIAL:"""
            
            for i, chunk in enumerate(context_chunks[:5], 1):  # Limit to top 5 chunks
                content = chunk.get("content", "").strip()
                filename = chunk.get("document_filename", "Unknown document")
                page = chunk.get("page_number", "Unknown")
                similarity = chunk.get("similarity", 0)
                
                # Clean and truncate content if too long
                if len(content) > 1000:
                    content = content[:1000] + "... [content truncated]"
                
                prompt += f"""

┌─ SOURCE {i} ────────────────────────────────────────────────────
│ Document: {filename}
│ Page: {page}
│ Relevance Score: {similarity:.2f}
└─────────────────────────────────────────────────────────────────

{content}"""
            
            if len(context_chunks) > 5:
                prompt += f"""

[📚 Note: {len(context_chunks) - 5} additional relevant sources are available but not shown to keep this manageable]"""
            
            prompt += f"""

═══════════════════════════════════════════════════════════════
                           INSTRUCTIONS
═══════════════════════════════════════════════════════════════

TASK: Provide a comprehensive educational response using the above context material."""

            if is_document_specific:
                prompt += """

🚨 DOCUMENT-SPECIFIC SEARCH MODE 🚨
The student has selected a specific document to search within. You MUST:

🛑 STRICT REQUIREMENTS 🛑
✅ ONLY use information from the provided context material above
✅ NEVER supplement with general knowledge or information from other sources
✅ If the provided context doesn't contain enough information, clearly state this limitation
✅ Focus your entire response on what can be found in the selected document
✅ If the question cannot be answered from the document, explain what parts ARE covered and what parts are missing

🔒 FORBIDDEN ACTIONS 🔒
❌ DO NOT use any information not explicitly present in the context
❌ DO NOT supplement with general knowledge
❌ DO NOT make assumptions beyond what's written in the context
❌ DO NOT provide information from your training data

RESPONSE REQUIREMENTS:
✅ Follow the mandatory response structure (Direct Answer, Explanation, etc.)
✅ Cite sources using format: (Source: {filename}, Page {page}) for EVERY piece of information
✅ Base your response EXCLUSIVELY on the provided context material
✅ If context is insufficient, acknowledge this clearly and explain what additional information would be needed
✅ Start responses with "Based on the provided document..." to remind yourself to use only context"""
            else:
                prompt += """

🚨 GENERAL SEARCH MODE 🚨
You found relevant material from the uploaded documents. You MUST:

🛑 PRIMARY REQUIREMENTS 🛑
✅ PRIORITIZE information from the provided context material above
✅ Use context material as your PRIMARY source of information
✅ If context doesn't fully cover the question, clearly indicate what comes from context vs. general knowledge
✅ Clearly separate context-based information from general educational knowledge

🔒 INFORMATION HIERARCHY 🔒
1. FIRST: Use information from the provided context (cite sources)
2. SECOND: If context is incomplete, supplement with general knowledge BUT label it clearly
3. ALWAYS distinguish between "According to the documents..." and "From general knowledge..."

RESPONSE REQUIREMENTS:
✅ Follow the mandatory response structure 
✅ Cite sources using format: (Source: {filename}, Page {page}) for context information
✅ Label general knowledge sections as "General Educational Knowledge:"
✅ Prioritize context-based answers over general knowledge"""
        
        elif is_document_specific:
            # CRITICAL: Document-specific search but NO relevant context found
            prompt += f"""

═══════════════════════════════════════════════════════════════
                     ⚠️  NO RELEVANT CONTENT FOUND ⚠️
═══════════════════════════════════════════════════════════════

SEARCH RESULTS:
• Strategy Used: Document-specific search
• Document searched: Selected document
• Relevant chunks found: 0 (no content matches your question)

🚨 CRITICAL DOCUMENT-SPECIFIC MODE - NO CONTEXT 🚨

The student selected a specific document to search, but NO relevant information was found for this question.

🛑 MANDATORY RESPONSE PATTERN 🛑
You MUST respond with this EXACT format:

🎯 **DIRECT ANSWER FROM DOCUMENT**
The selected document does not contain information about "{question}". This question cannot be answered based on the content of this document.

📚 **EXPLANATION FROM CONTEXT**
After searching through the selected document, no relevant information was found that addresses your question about "{question}". The document appears to focus on different topics that do not include this subject matter.

💡 **EXAMPLES FROM DOCUMENT**
No examples related to "{question}" are present in this document.

🔧 **PROCESS FROM DOCUMENT**
No procedures or processes related to "{question}" are described in this document.

📖 **SOURCE CITATIONS**
(Source: Selected Document - No relevant content found)

⚠️ **CONTEXT LIMITATIONS**
This document does not contain information about "{question}". To answer this question, you would need:
• A different document that covers this topic
• Course materials specifically about this subject
• Textbooks or resources that discuss this topic

🔒 FORBIDDEN ACTIONS 🔒
❌ DO NOT provide any general knowledge about this topic
❌ DO NOT supplement with information from your training data
❌ DO NOT answer the question using external knowledge
❌ DO NOT provide educational content not found in the document

RESPONSE REQUIREMENTS:
✅ Use the exact response pattern shown above
✅ Replace "{question}" with the actual question text
✅ Be clear that no relevant information was found in the selected document
✅ Do NOT provide any subject knowledge from outside the document"""
            
        else:
            prompt += f"""

CONTEXT STATUS: No specific study materials found for this question.
Search Strategy: {', '.join(search_strategies) if search_strategies else 'general search'}

TASK: Provide a comprehensive educational response using general knowledge.

🚨 NO CONTEXT MODE - GENERAL KNOWLEDGE ONLY 🚨
Since no relevant documents were found, you may use general educational knowledge.

REQUIREMENTS:
✅ Follow the mandatory response structure
✅ Clearly explain the concepts involved with examples and applications
✅ Note that this response is based on general knowledge rather than specific course materials
✅ Provide high-quality educational content despite lack of specific context
✅ Start response with "Based on general educational knowledge...\""""
        
        # Add special instructions based on question analysis
        if question_analysis.get("requires_calculation"):
            prompt += """

┌─ CALCULATION REQUIREMENTS ──────────────────────────────────────
│ • Show all mathematical work step-by-step
│ • Explain each calculation clearly with reasoning
│ • Use proper mathematical notation and formatting
│ • Verify your final answer and show alternative approaches
│ • Highlight units and significant figures where applicable
└─────────────────────────────────────────────────────────────────"""
        
        if question_analysis.get("requires_visual"):
            prompt += """

┌─ VISUAL EXPLANATION REQUIREMENTS ───────────────────────────────
│ • Describe any relevant diagrams, charts, or visual elements
│ • Suggest visual aids that would help understanding
│ • Use spatial and visual metaphors when appropriate
│ • Recommend drawing or sketching exercises
│ • Reference visual patterns and relationships
└─────────────────────────────────────────────────────────────────"""
        
        # Add context about learning level
        difficulty = question_analysis.get("difficulty", "intermediate")
        if difficulty == "beginner":
            prompt += """

┌─ BEGINNER LEVEL GUIDANCE ───────────────────────────────────────
│ • Use simple, clear language and define technical terms
│ • Provide extra background context and foundational concepts
│ • Build confidence with encouraging language
│ • Break complex ideas into smaller, manageable parts
│ • Include basic examples and simple analogies
└─────────────────────────────────────────────────────────────────"""
        elif difficulty == "advanced":
            prompt += """

┌─ ADVANCED LEVEL EXPECTATIONS ───────────────────────────────────
│ • Use appropriate technical terminology
│ • Provide in-depth analysis and multiple perspectives
│ • Connect to broader theoretical frameworks
│ • Challenge critical thinking and encourage research
│ • Include cutting-edge developments when relevant
└─────────────────────────────────────────────────────────────────"""
        
        prompt += """

═══════════════════════════════════════════════════════════════
                    FINAL RESPONSE CHECKLIST
═══════════════════════════════════════════════════════════════

Before submitting your response, ensure you have:
□ Started with a clear, direct "Quick Answer"
□ Provided comprehensive "Detailed Explanation"
□ Included relevant "Examples & Applications"
□ Added "Step-by-Step Breakdown" if applicable
□ Listed all "Sources Referenced" with proper citations
□ Suggested "Next Steps & Related Topics"
□ Used encouraging and supportive language throughout
□ Addressed the student's question completely and accurately"""
        
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
