#!/usr/bin/env python3
"""
Example script showing how to ask questions from a specific PDF
NOW WITH DYNAMIC FRONTEND INTEGRATION!

This demonstrates the programmatic approach, but the recommended way
is to use the enhanced frontend at http://localhost:8000/frontend
"""
import requests
import json

# Server configuration
BASE_URL = "http://localhost:8000"

def list_all_pdfs():
    """Get all PDFs from the system"""
    response = requests.get(f"{BASE_URL}/api/v1/pdfs")
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error: {response.status_code} - {response.text}")
        return None

def ask_question_from_pdf(question, user_id=None, document_id=None):
    """Ask a question from a specific PDF or all PDFs"""
    payload = {
        "question": question
    }
    
    if user_id:
        payload["user_id"] = user_id
    
    # If document_id is provided, search only in that specific PDF
    if document_id:
        payload["document_id"] = document_id
        
    response = requests.post(f"{BASE_URL}/api/v1/ask", json=payload)
    
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error: {response.status_code} - {response.text}")
        return None

def interactive_pdf_qa():
    """Interactive function to demonstrate PDF selection"""
    print("🎯 AI Tutor - Document-Specific Q&A Demo")
    print("=" * 50)
    
    # Get PDFs
    print("📚 Loading your documents...")
    pdfs = list_all_pdfs()
    
    if not pdfs:
        print("❌ No PDFs found. Please upload some documents first!")
        print("� Visit http://localhost:8000/frontend to upload PDFs")
        return
    
    # Show processed PDFs only
    processed_pdfs = [pdf for pdf in pdfs if pdf.get('processing_status') == 'completed']
    
    if not processed_pdfs:
        print("❌ No processed PDFs found. Please wait for processing to complete!")
        print("💡 Visit http://localhost:8000/frontend to check processing status")
        return
    
    print(f"✅ Found {len(processed_pdfs)} processed documents:")
    print("0. 🌐 Search ALL documents")
    
    for i, pdf in enumerate(processed_pdfs, 1):
        chunks = pdf.get('total_chunks', 0)
        print(f"{i}. 📄 {pdf['original_filename']} ({chunks} chunks)")
    
    print("\n" + "=" * 50)
    
    # Get user selection
    try:
        choice = input("Select a document (0 for all, or number): ").strip()
        
        if choice == "0":
            selected_pdf = None
            search_scope = "all documents"
        else:
            pdf_index = int(choice) - 1
            if 0 <= pdf_index < len(processed_pdfs):
                selected_pdf = processed_pdfs[pdf_index]
                search_scope = f"'{selected_pdf['original_filename']}'"
            else:
                print("❌ Invalid selection!")
                return
    except (ValueError, KeyboardInterrupt):
        print("\n👋 Goodbye!")
        return
    
    # Get question
    print(f"\n🔍 You'll search in: {search_scope}")
    question = input("❓ Enter your question: ").strip()
    
    if not question:
        print("❌ No question provided!")
        return
    
    # Ask question
    print(f"\n🤔 Asking: '{question}'")
    print(f"📚 Searching in: {search_scope}")
    print("⏳ Processing...")
    
    document_id = selected_pdf['id'] if selected_pdf else None
    result = ask_question_from_pdf(question, document_id=document_id)
    
    if result and result.get('success'):
        print("\n" + "✅ ANSWER" + "=" * 43)
        print(f"📝 {result['answer']['quick_answer']}")
        
        sources = result.get('sources', {}).get('primary_sources', [])
        print(f"\n📊 Sources: {len(sources)} chunks referenced")
        
        if selected_pdf:
            print(f"🎯 Document: {selected_pdf['original_filename']}")
        else:
            print(f"🌐 Searched across all documents")
            
    else:
        print("❌ Failed to get answer")
    
    print("\n" + "=" * 50)
    print("💡 TIP: Use the web interface at http://localhost:8000/frontend")
    print("   for a better user experience with dropdown selection!")

# Example usage
if __name__ == "__main__":
    print("🚀 AI Tutor Backend - PDF Question Answering")
    print("\n🎯 RECOMMENDED: Use the web frontend!")
    print("   Visit: http://localhost:8000/frontend")
    print("   - Beautiful interface with PDF dropdown")
    print("   - Real-time document selection")
    print("   - Visual feedback and better UX")
    
    print("\n📖 Or run this interactive demo:")
    choice = input("Run interactive demo? (y/n): ").strip().lower()
    
    if choice in ['y', 'yes']:
        interactive_pdf_qa()
    else:
        print("\n👋 Visit http://localhost:8000/frontend for the best experience!")
        
    print(f"\n💡 Frontend features:")
    print(f"   ✅ PDF dropdown with processed documents")
    print(f"   ✅ Document-specific vs global search toggle") 
    print(f"   ✅ Visual feedback on search scope")
    print(f"   ✅ Real-time processing status")
    print(f"   ✅ Beautiful, responsive interface")
