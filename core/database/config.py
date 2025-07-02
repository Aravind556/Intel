"""
Database configuration for AI Tutor PDF storage and vector retrieval
"""
import os
from typing import Optional
from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class DatabaseConfig:
    """Configuration class for Supabase database operations"""
    
    def __init__(self):
        # Supabase configuration
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_key = os.getenv("SUPABASE_KEY")
        self.supabase_service_key = os.getenv("SUPABASE_SERVICE_KEY")
        
        # Validate required environment variables
        if not all([self.supabase_url, self.supabase_key]):
            raise ValueError(
                "Missing required environment variables: SUPABASE_URL, SUPABASE_KEY"
            )
        
        # Initialize clients
        self._client = None
        self._service_client = None
    
    @property
    def client(self) -> Client:
        """Get regular Supabase client"""
        if self._client is None:
            self._client = create_client(self.supabase_url, self.supabase_key)
        return self._client
    
    @property
    def service_client(self) -> Client:
        """Get Supabase service client (admin privileges)"""
        if self._service_client is None:
            if not self.supabase_service_key:
                raise ValueError("SUPABASE_SERVICE_KEY not found")
            self._service_client = create_client(self.supabase_url, self.supabase_service_key)
        return self._service_client
