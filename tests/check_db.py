import sys
import os
import asyncio
from dotenv import load_dotenv

# Load env variables
load_dotenv()

# Add project root to python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from core.database.config import DatabaseConfig
from core.database.manager import PDFDatabaseManager

async def main():
    db_config = DatabaseConfig()
    db_manager = PDFDatabaseManager(db_config)
    
    # 1. Query PDFs
    try:
        pdfs = await db_manager.list_pdf_documents()
        print(f"PDFs found: {len(pdfs)}")
        for pdf in pdfs:
            print(f" - {pdf.get('original_filename')} (ID: {pdf.get('id')})")
    except Exception as e:
        print("Error listing PDFs:", e)
        
    # 2. Query users
    try:
        print("Querying users...")
        res = db_config.client.table("users").select("*").limit(5).execute()
        print(f"Users found: {len(res.data) if res.data else 0}")
        for u in res.data or []:
            print(f" - {u.get('name')} ({u.get('email')}, ID: {u.get('id')})")
    except Exception as e:
        print("Error listing users:", e)

if __name__ == "__main__":
    asyncio.run(main())
