"""
AI Tutor Backend Test Script

This script tests the core functionality of the AI Tutor backend:
1. PDF processing pipeline
2. Question answering with Gemini

Usage:
    python test.py
"""
import os
import sys
import json
import uuid
import asyncio
import argparse
import tempfile
from io import BytesIO
from dotenv import load_dotenv

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import project components
from modules.pdf_processor.services.pdf_processor import PDFProcessor
from modules.doubt_solver.services.response_generator import ResponseGenerator
from core.database.manager import PDFDatabaseManager

# Load environment variables
load_dotenv()

async def test_pdf_processing(pdf_path):
    """Test the PDF processing pipeline"""
    print("\n📄 Testing PDF Processing Pipeline...")
    
    # Initialize components
    pdf_processor = PDFProcessor()
    
    if not os.path.exists(pdf_path):
        print(f"❌ Test PDF not found at {pdf_path}")
        print("   Please update the path to point to a valid PDF file")
        return
    
    try:
        # Read PDF file
        with open(pdf_path, "rb") as f:
            pdf_content = f.read()
        
        # Process the PDF
        result = await pdf_processor.process_pdf(
            file_content=pdf_content,
            original_filename=os.path.basename(pdf_path),
            subject="Test",
            description="Testing PDF processing pipeline"
        )
        
        # Display results
        print(f"✅ PDF Processing Complete")
        print(f"   - Success: {result.success}")
        print(f"   - Message: {result.message}")
        print(f"   - Document ID: {result.pdf_id}")
        print(f"   - Total Chunks: {result.total_chunks}")
        
        return result.pdf_id
    
    except Exception as e:
        print(f"❌ PDF Processing Failed: {str(e)}")
        return None

async def test_question_answering(document_id, question="Summarize the main points in this document"):
    """Test the question answering functionality"""
    print("\n❓ Testing Question Answering...")
    
    # Skip if no document ID
    if not document_id:
        print("❌ No document ID provided, skipping question answering test")
        return
    
    try:
        # Initialize components
        from core.database.config import DatabaseConfig
        db_config = DatabaseConfig()
        db_manager = PDFDatabaseManager(db_config)
        response_generator = ResponseGenerator(db_manager)
        
        # Create session
        session_id = str(uuid.uuid4())
        user_id = str(uuid.uuid4())
        
        print(f"   - Using question: '{question}'")
        print(f"   - For document: {document_id}")
        print(f"   - Generating response...")
        
        # Get answer
        answer = await response_generator.solve_doubt(
            question=question,
            user_id=user_id,
            session_id=session_id
        )
        
        # Display results
        print(f"✅ Question Answering Complete")
        if isinstance(answer, dict) and 'answer' in answer:
            print(f"   - Answer: {answer['answer'][:150]}...")  # Show first 150 chars
        else:
            print(f"   - Answer: {str(answer)[:150]}...")  # Show first 150 chars of whatever we got
        
        if answer.get('sources'):
            print(f"   - Sources: {len(answer['sources'])} chunks referenced")
        
        return answer
        
    except Exception as e:
        print(f"❌ Question Answering Failed: {str(e)}")
        return None

def create_sample_pdf(content="This is a sample PDF document for testing the AI Tutor backend."):
    """Create a sample PDF for testing if none is provided"""
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter
        
        pdf_buffer = BytesIO()
        c = canvas.Canvas(pdf_buffer, pagesize=letter)
        
        # Add title
        c.setFont("Helvetica-Bold", 16)
        c.drawString(100, 750, "AI Tutor Test Document")
        
        # Add paragraphs of content
        c.setFont("Helvetica", 12)
        y_position = 700
        for paragraph in content.split("\n\n"):
            text_object = c.beginText(100, y_position)
            for line in paragraph.split("\n"):
                text_object.textLine(line)
            c.drawText(text_object)
            y_position -= 50
        
        c.showPage()
        c.save()
        
        # Write the PDF to a temporary file
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_file:
            tmp_file.write(pdf_buffer.getvalue())
            return tmp_file.name
            
    except ImportError:
        print("❌ Could not create sample PDF: reportlab not installed")
        print("   To install: pip install reportlab")
        return None

async def main():
    """Main test function"""
    parser = argparse.ArgumentParser(description="Test AI Tutor Backend")
    parser.add_argument("--pdf", help="Path to a test PDF file")
    parser.add_argument("--question", default="Summarize the main points in this document", 
                       help="Question to test with")
    args = parser.parse_args()
    
    print("🧪 Starting AI Tutor Backend Tests")
    
    # Get PDF path
    pdf_path = args.pdf
    generated_pdf = False
    
    # Create a sample PDF if none provided
    if not pdf_path or not os.path.exists(pdf_path):
        sample_content = """
        # Introduction to AI Education
        
        Artificial intelligence (AI) is revolutionizing education by providing personalized learning experiences.
        
        ## Key Benefits
        
        1. Adaptive learning paths based on student performance
        2. Immediate feedback on assignments and questions
        3. 24/7 availability for student support
        
        ## Challenges
        
        Despite its benefits, AI in education faces challenges including:
        - Ensuring privacy and security of student data
        - Maintaining the human element in teaching
        - Addressing algorithmic bias in educational content
        
        ## Future Directions
        
        The future of AI in education will likely see more sophisticated systems that can:
        - Better understand student emotions and engagement
        - Provide more nuanced and contextual explanations
        - Support collaborative learning environments
        """
        
        pdf_path = create_sample_pdf(sample_content)
        generated_pdf = True
        
        if not pdf_path:
            print("❌ Could not create or find a test PDF. Exiting.")
            return
    
    print(f"📄 Using test PDF: {pdf_path}")
    
    try:
        # Test PDF processing
        document_id = await test_pdf_processing(pdf_path)
        
        # Test question answering
        if document_id:
            await test_question_answering(document_id, args.question)
        
        print("\n✅ All tests completed!")
    
    except Exception as e:
        print(f"\n❌ Test failed with error: {str(e)}")
    
    finally:
        # Clean up generated PDF
        if generated_pdf and os.path.exists(pdf_path):
            try:
                os.remove(pdf_path)
                print(f"🧹 Removed temporary PDF: {pdf_path}")
            except:
                pass

if __name__ == "__main__":
    asyncio.run(main())
