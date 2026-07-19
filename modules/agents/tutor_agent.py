"""
AI Tutor Agent Service
======================
Drives the dialogue flow, active teaching, doubt solving, quiz construction,
and student answer grading/evaluation using the Groq API client.
"""
from typing import List, Dict, Any, Optional
import os
import json
import logging
from groq import Groq
from core.database.manager import PDFDatabaseManager
from .retrieval_agent import RetrievalAgent

logger = logging.getLogger(__name__)

class AITutorAgent:
    """Tutor Agent coordinating active teaching, doubt solving, and assessments via Groq"""
    
    def __init__(self, db_manager: PDFDatabaseManager, retrieval_agent: RetrievalAgent):
        self.db_manager = db_manager
        self.retrieval_agent = retrieval_agent
        
        # Initialize Groq client
        api_key = os.getenv("GROQ_API_KEY") or os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("Groq API key not found. Please set GROQ_API_KEY or GEMINI_API_KEY in env.")
            
        self.client = Groq(api_key=api_key)
        # Standard model for high-reasoning tasks (tutoring, evaluating, generating quizzes)
        self.model_name = "llama-3.3-70b-versatile"
        
    async def start_lesson(self, student_id: str, concept: str, session_id: str) -> Dict[str, Any]:
        """
        Starts a teaching flow for a specific concept.
        Returns the first lesson explanation, worked example, and comprehension check.
        """
        logger.info(f"Starting lesson for student {student_id} on concept: {concept}")
        
        # 1. Fetch Student Profile and Mastery
        profile = await self.db_manager.get_student_profile(student_id)
        preferences = profile.get("learning_preferences", {}) if profile else {}
        
        mastery_record = await self.db_manager.get_topic_mastery(student_id, concept)
        mastery = mastery_record.get("mastery_score", 0.0) if mastery_record else 0.0
        
        # 2. Retrieve Educational Material
        retrieval_res = await self.retrieval_agent.retrieve_context(
            intent="teach",
            query=concept,
            user_id=student_id,
            match_count=4
        )
        evidence = retrieval_res.get("evidence", [])
        citations = retrieval_res.get("citations", [])
        
        if not evidence:
            return {
                "success": True,
                "response_text": f"I see you want to study **{concept}**, but I couldn't find any relevant sections in our uploaded materials. Could you try uploading a PDF that covers this topic?",
                "session_id": session_id,
                "comprehension_check": None,
                "citations": []
            }
            
        # 3. Build Prompt & Call Groq
        evidence_text = "\n\n".join([f"Source: {c['pdf_title']} (Page {c['page_number']})\n{c['content']}" for c in evidence])
        
        system_prompt = f"""You are an expert AI Tutor modeling a human teacher.
Objective: Introduce and teach the concept of '{concept}' to the student.

Core Instructions:
1. Base your explanation EXCLUSIVELY on the retrieved study materials provided.
2. Structure your lesson block in this exact order:
   - Core concept definition (explain it simply, introduce only 1 new idea).
   - Analogy based on student preferences: {json.dumps(preferences)}.
   - A step-by-step worked example.
   - End with a single comprehension check (e.g. asking the student to solve a simple variation or explain the concept).
3. Ground your explanation in the citations. Do not write wall-of-text explanations. Keep sections distinct.
4. Output your response as a JSON object with keys:
   - "explanation": "The concept explanation, analogy, and worked example formatted in Markdown."
   - "comprehension_check": "The question/prompt to verify the student's understanding."
"""

        user_prompt = f"""Here is the retrieved context from the textbook:
{evidence_text}

Generate the lesson introduction for the concept '{concept}'."""

        try:
            chat_completion = self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                model=self.model_name,
                response_format={"type": "json_object"},
                temperature=0.4
            )
            
            res_json = json.loads(chat_completion.choices[0].message.content)
            explanation = res_json.get("explanation", "")
            comprehension_check = res_json.get("comprehension_check", "")
            
            # Formulate response
            response_text = f"{explanation}\n\n💡 **Comprehension Check**:\n{comprehension_check}"
            
            return {
                "success": True,
                "response_text": response_text,
                "session_id": session_id,
                "comprehension_check": comprehension_check,
                "citations": citations
            }
        except Exception as e:
            logger.error(f"Error starting lesson: {e}")
            return {
                "success": False,
                "error": f"Failed to start lesson due to LLM error: {str(e)}"
            }

    async def process_message(
        self,
        student_id: str,
        message: str,
        session_id: str,
        current_concept: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Handles open dialogue, conceptual doubt solving, and answering student questions.
        Grounds responses strictly in retrieved textbook files.
        """
        logger.info(f"Processing dialogue for user {student_id} | Concept: {current_concept} | Msg: {message}")
        
        # 1. Fetch student preferences
        profile = await self.db_manager.get_student_profile(student_id)
        preferences = profile.get("learning_preferences", {}) if profile else {}
        
        # 2. Retrieve context for the user query
        retrieval_res = await self.retrieval_agent.retrieve_context(
            intent="doubt_solve",
            query=message if not current_concept else f"{current_concept} {message}",
            user_id=student_id,
            match_count=4
        )
        evidence = retrieval_res.get("evidence", [])
        citations = retrieval_res.get("citations", [])
        
        # 3. Format grounded evidence
        if evidence:
            evidence_text = "\n\n".join([f"Source: {c['pdf_title']} (Page {c['page_number']})\n{c['content']}" for c in evidence])
            system_prompt = f"""You are an expert AI Tutor. Ground your answers strictly in the retrieved textbook contents.
Core instructions:
1. Citations are MANDATORY. Cite the textbook/source name and page for every factual assertion, e.g. (Source: calculus.pdf, Page 12).
2. If the context does not support an answer, explicitly declare that you cannot answer it from the provided texts and state what is missing.
3. Align your style with the student's preferences: {json.dumps(preferences)}.
4. Be supportive and encourage active dialogue.
"""
            user_prompt = f"""Study context:
{evidence_text}

Student doubt: "{message}"
Provide a clear, pedagogical answer based only on the study context."""
        else:
            system_prompt = "You are a supportive AI Tutor."
            user_prompt = f"Explain to the student that you couldn't find any relevant uploaded materials to answer their query about '{message}' and guide them to upload relevant PDFs."

        try:
            chat_completion = self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                model=self.model_name,
                temperature=0.5
            )
            response_text = chat_completion.choices[0].message.content
            
            return {
                "success": True,
                "response_text": response_text,
                "session_id": session_id,
                "citations": citations
            }
        except Exception as e:
            logger.error(f"Error in process_message: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def generate_quiz(self, student_id: str, concept: str, question_type: str = "mcq") -> Dict[str, Any]:
        """
        Generates a quiz question calibrated to the student's mastery level.
        Returns the question and the evaluation rubric.
        """
        logger.info(f"Generating {question_type} quiz on {concept} for student {student_id}")
        
        # 1. Fetch Mastery Level and Calibrate Difficulty
        mastery_record = await self.db_manager.get_topic_mastery(student_id, concept)
        mastery = mastery_record.get("mastery_score", 0.0) if mastery_record else 0.0
        
        # Calibration formula: M in [0, 1] maps to D in [1, 5]
        difficulty = min(5, max(1, int(mastery * 5) + 1))
        
        # 2. Retrieve Evidence
        retrieval_res = await self.retrieval_agent.retrieve_context(
            intent="generate_quiz",
            query=concept,
            user_id=student_id,
            match_count=4
        )
        evidence = retrieval_res.get("evidence", [])
        
        if not evidence:
            return {
                "success": False,
                "error": f"No learning materials found to generate a quiz on '{concept}'."
            }
            
        evidence_text = "\n\n".join([f"Source: {c['pdf_title']} (Page {c['page_number']})\n{c['content']}" for c in evidence])
        
        system_prompt = f"""You are a Calibrated Quiz Designer.
Objective: Generate a question of type '{question_type}' on '{concept}' calibrated to difficulty level {difficulty} (out of 5).

Difficulty Scale Guidelines:
- Level 1: Direct definition recall.
- Level 2: Simple conceptual matching or fill-in-the-blank.
- Level 3: Calculation or step-by-step procedural check.
- Level 4: Synthesis, scenario analysis, or guided coding.
- Level 5: Edge-cases, optimization, or debugging.

Output the response in structured JSON with these exact keys:
- "question": "The text of the question (include choices A, B, C, D if MCQ)."
- "rubric": {{
    "ideal_answer": "The target correct answer.",
    "milestones": ["List of core points or steps the student must hit."],
    "misconceptions": [
        {{"code": "MISC_FOUNDATION", "condition": "Student fails to state basic prerequisite X."}},
        {{"code": "MISC_EXECUTION", "condition": "Student applies mathematical calculation error."}},
        {{"code": "MISC_LOGIC", "condition": "Student has correct facts but invalid reasoning."}},
        {{"code": "MISC_VOCAB", "condition": "Student mixes up vocab terms."}}
    ]
}}
"""

        user_prompt = f"""Textbook context:
{evidence_text}

Generate a calibrated {question_type} question on '{concept}'."""

        try:
            chat_completion = self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                model=self.model_name,
                response_format={"type": "json_object"},
                temperature=0.6
            )
            
            quiz_data = json.loads(chat_completion.choices[0].message.content)
            return {
                "success": True,
                "question": quiz_data.get("question"),
                "rubric": quiz_data.get("rubric"),
                "difficulty": difficulty
            }
        except Exception as e:
            logger.error(f"Error generating quiz: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def evaluate_answer(
        self,
        student_id: str,
        concept: str,
        question_text: str,
        student_answer: str,
        rubric: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Grades the student's answer using the rubric, identifies misconceptions,
        updates the student's mastery score, and logs the assessment attempt.
        """
        logger.info(f"Evaluating answer for student {student_id} on concept {concept}")
        
        # 1. Fetch current mastery level
        mastery_record = await self.db_manager.get_topic_mastery(student_id, concept)
        current_mastery = mastery_record.get("mastery_score", 0.0) if mastery_record else 0.0
        
        system_prompt = """You are a Pedagogical Evaluation Specialist.
Objective: Score the student's answer against the grading rubric and identify cognitive misconceptions.

Output your evaluation as a JSON object with these keys:
- "is_correct": boolean (true/false)
- "score": number (between 0.0 and 1.0)
- "misconceptions_detected": [
     {"code": "MISC_CODE", "explanation": "Why this misconception was identified."}
  ]
- "remediation_feedback": "Constructive pedagogical feedback highlighting correct elements and detailing the error."
"""

        user_prompt = f"""
Question: "{question_text}"
Student Answer: "{student_answer}"
Rubric: {json.dumps(rubric)}

Grade the response, determine correctness, and identify if any of the misconceptions defined in the rubric are visible in the answer."""

        try:
            chat_completion = self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                model=self.model_name,
                response_format={"type": "json_object"},
                temperature=0.2
            )
            
            eval_res = json.loads(chat_completion.choices[0].message.content)
            is_correct = eval_res.get("is_correct", False)
            score = eval_res.get("score", 0.0)
            misconceptions = eval_res.get("misconceptions_detected", [])
            feedback = eval_res.get("remediation_feedback", "")
            
            # 2. Calibrate Mastery Update
            # Mastery delta calculations:
            if is_correct:
                # Add score-based weight (higher mastery gains for higher scores)
                delta = 0.15 * score
                new_mastery = min(1.0, current_mastery + delta)
            else:
                # Deduct based on error penalty
                delta = -0.10 * (1.0 - score)
                new_mastery = max(0.0, current_mastery + delta)
                
            # 3. Persist State Changes
            await self.db_manager.update_topic_mastery(student_id, concept, new_mastery)
            await self.db_manager.log_assessment_history(
                student_id=student_id,
                concept_name=concept,
                question_text=question_text,
                student_answer=student_answer,
                is_correct=is_correct,
                score=score,
                misconceptions=misconceptions
            )
            
            return {
                "success": True,
                "is_correct": is_correct,
                "score": score,
                "misconceptions_detected": misconceptions,
                "feedback": feedback,
                "previous_mastery": current_mastery,
                "new_mastery": new_mastery
            }
        except Exception as e:
            logger.error(f"Error evaluating answer: {e}")
            return {
                "success": False,
                "error": str(e)
            }
