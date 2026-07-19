"""
Migration runner script to apply SQL schemas to Supabase database.
"""
import os
import re
import psycopg2
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def get_db_connection():
    supabase_url = os.getenv("SUPABASE_URL", "")
    match = re.search(r"https://(.*?)\.supabase\.co", supabase_url)
    if not match:
        raise ValueError(f"Invalid SUPABASE_URL: {supabase_url}")
    
    project_ref = match.group(1)
    password = "aravind123*4564"
    
    try:
        host = f"db.{project_ref}.supabase.co"
        print(f"🔌 Attempting connection to: {host} (port 5432)...")
        conn = psycopg2.connect(
            host=host,
            port=5432,
            database="postgres",
            user="postgres",
            password=password,
            connect_timeout=10
        )
        print("✅ Connected successfully using Connection Option 1 (Direct host)!")
        return conn
    except Exception as e:
        print(f"⚠️ Connection Option 1 failed: {e}")
        
    try:
        host = "aws-0-us-east-1.pooler.supabase.com"
        user = f"postgres.{project_ref}"
        print(f"🔌 Attempting connection to connection pooler: {host} (port 6543) as {user}...")
        conn = psycopg2.connect(
            host=host,
            port=6543,
            database="postgres",
            user=user,
            password=password,
            connect_timeout=10
        )
        print("✅ Connected successfully using Connection Option 2 (Connection Pooler)!")
        return conn
    except Exception as e:
        print(f"❌ Connection Option 2 failed: {e}")
        raise ConnectionError("Failed to connect to Supabase PostgreSQL database using any connection method.")

def run_migrations():
    db_dir = os.path.dirname(os.path.abspath(__file__))
    setup_path = os.path.join(db_dir, "setup.sql")
    migration_path = os.path.join(db_dir, "migration_tutor_profiles.sql")
    
    try:
        conn = get_db_connection()
        conn.autocommit = True
        cursor = conn.cursor()
        
        # Check if users table exists
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'users'
            );
        """)
        users_table_exists = cursor.fetchone()[0]
        
        if not users_table_exists:
            print("⏳ Database is uninitialized. Running setup.sql first...")
            if os.path.exists(setup_path):
                with open(setup_path, "r") as f:
                    setup_sql = f.read()
                cursor.execute(setup_sql)
                print("✅ Base setup.sql executed successfully!")
            else:
                print(f"❌ Base setup.sql not found at: {setup_path}")
        else:
            print("✅ Base tables (users, etc.) already exist.")
            
        print(f"📖 Reading migration SQL script: {migration_path}...")
        if os.path.exists(migration_path):
            with open(migration_path, "r") as f:
                migration_sql = f.read()
            
            # Execute migration sql
            cursor.execute(migration_sql)
            print("✅ Migrations applied successfully!")
        else:
            print(f"❌ Migration file not found at: {migration_path}")
            
        # Verify if tables exist
        cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public';")
        tables = [row[0] for row in cursor.fetchall()]
        print(f"📊 Available tables in public schema: {tables}")
        
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"❌ Migration execution failed: {e}")

if __name__ == "__main__":
    run_migrations()
