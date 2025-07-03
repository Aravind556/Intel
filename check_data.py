import asyncio
from core.database.config import DatabaseConfig

async def check_sample_data():
    print("🔍 Checking sample data...")
    
    try:
        db_config = DatabaseConfig()
        client = db_config.client
        
        # Check users
        users = client.table("users").select("*").execute()
        print(f"Users: {users.data}")
        
        # Check subjects  
        subjects = client.table("subjects").select("*").execute()
        print(f"Subjects: {subjects.data}")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    asyncio.run(check_sample_data())
