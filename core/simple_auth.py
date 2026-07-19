#!/usr/bin/env python3
"""
Simple User Authentication System for AI Tutor
==============================================
Simple login/logout system using existing users table.
"""

import hashlib
import secrets
import uuid
from typing import Dict, Any, Optional
from dotenv import load_dotenv
from supabase import create_client, Client
import os

# Load environment variables
load_dotenv()

class SimpleAuth:
    """Simple authentication system without JWT"""
    
    def __init__(self):
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_key = os.getenv("SUPABASE_SERVICE_KEY")
        self.supabase: Client = create_client(self.supabase_url, self.supabase_key)
        self.active_sessions = {}  # Store active sessions in memory
        
    def _hash_password(self, password: str) -> str:
        """Hash password with salt"""
        salt = secrets.token_hex(16)
        password_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
        return f"{salt}:{password_hash.hex()}"
    
    def _verify_password(self, password: str, hashed_password: str) -> bool:
        """Verify password against hash"""
        try:
            salt, password_hash = hashed_password.split(':')
            new_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
            return new_hash.hex() == password_hash
        except:
            return False
    
    def _generate_session_id(self) -> str:
        """Generate a simple session ID"""
        return secrets.token_hex(32)
    
    async def register_user(self, name: str, email: str, password: str, role: str = "student") -> Dict[str, Any]:
        """Register a new user"""
        try:
            # Check if user already exists
            existing_user = self.supabase.table('users').select('*').eq('email', email).execute()
            if existing_user.data:
                return {
                    "success": False,
                    "error": "User with this email already exists"
                }
            
            # Hash password
            password_hash = self._hash_password(password)
            
            # Create user
            user_data = {
                'id': str(uuid.uuid4()),
                'name': name,
                'email': email,
                'password_hash': password_hash,
                'role': role,
                'created_at': 'now()',
                'updated_at': 'now()'
            }
            
            result = self.supabase.table('users').insert(user_data).execute()
            
            if result.data:
                user = result.data[0]
                session_id = self._generate_session_id()
                
                # Store session
                self.active_sessions[session_id] = {
                    'user_id': user['id'],
                    'email': user['email'],
                    'name': user['name'],
                    'role': user['role']
                }
                
                return {
                    "success": True,
                    "message": "User registered successfully",
                    "user": {
                        "id": user['id'],
                        "name": user['name'],
                        "email": user['email'],
                        "role": user['role']
                    },
                    "session_id": session_id
                }
            else:
                return {
                    "success": False,
                    "error": "Failed to create user"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"Registration failed: {str(e)}"
            }
    
    async def login_user(self, email: str, password: str) -> Dict[str, Any]:
        """Login user with email and password"""
        try:
            # Get user from database
            user_result = self.supabase.table('users').select('*').eq('email', email).execute()
            
            if not user_result.data:
                return {
                    "success": False,
                    "error": "Invalid email or password"
                }
            
            user = user_result.data[0]
            
            # Check if password_hash exists
            if not user.get('password_hash'):
                return {
                    "success": False,
                    "error": "Account not set up for login. Please contact administrator."
                }
            
            # Verify password
            if not self._verify_password(password, user['password_hash']):
                return {
                    "success": False,
                    "error": "Invalid email or password"
                }
            
            # Generate session
            session_id = self._generate_session_id()
            
            # Store session
            self.active_sessions[session_id] = {
                'user_id': user['id'],
                'email': user['email'],
                'name': user['name'],
                'role': user['role']
            }
            
            return {
                "success": True,
                "message": "Login successful",
                "user": {
                    "id": user['id'],
                    "name": user['name'],
                    "email": user['email'],
                    "role": user['role']
                },
                "session_id": session_id
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Login failed: {str(e)}"
            }
    
    async def logout_user(self, session_id: str) -> Dict[str, Any]:
        """Logout user"""
        try:
            if session_id in self.active_sessions:
                del self.active_sessions[session_id]
            
            return {
                "success": True,
                "message": "Logout successful"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Logout failed: {str(e)}"
            }
    
    async def get_user_from_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get user from session ID"""
        return self.active_sessions.get(session_id)
    
    async def change_password(self, session_id: str, old_password: str, new_password: str) -> Dict[str, Any]:
        """Change user password"""
        try:
            # Get user from session
            session_data = self.active_sessions.get(session_id)
            if not session_data:
                return {
                    "success": False,
                    "error": "Invalid session"
                }
            
            user_id = session_data['user_id']
            
            # Get current password hash
            user_result = self.supabase.table('users').select('password_hash').eq('id', user_id).execute()
            
            if not user_result.data:
                return {
                    "success": False,
                    "error": "User not found"
                }
            
            user = user_result.data[0]
            
            # Verify old password
            if not self._verify_password(old_password, user['password_hash']):
                return {
                    "success": False,
                    "error": "Current password is incorrect"
                }
            
            # Hash new password
            new_password_hash = self._hash_password(new_password)
            
            # Update password
            self.supabase.table('users').update({
                'password_hash': new_password_hash,
                'updated_at': 'now()'
            }).eq('id', user_id).execute()
            
            return {
                "success": True,
                "message": "Password changed successfully"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Password change failed: {str(e)}"
            }

# CLI Interface for testing
async def main():
    """Main CLI interface for user management"""
    auth = SimpleAuth()
    
    print("🎓 AI Tutor - Simple Authentication System")
    print("=" * 50)
    
    while True:
        print("\n1. Register new user")
        print("2. Login user")
        print("3. Logout user")
        print("4. Change password")
        print("5. Exit")
        
        choice = input("\nChoose an option (1-5): ").strip()
        
        if choice == "1":
            print("\n📝 User Registration")
            print("-" * 20)
            name = input("Full Name: ").strip()
            email = input("Email: ").strip()
            password = input("Password: ").strip()
            role = input("Role (student/teacher) [default: student]: ").strip() or "student"
            
            result = await auth.register_user(name, email, password, role)
            
            if result["success"]:
                print(f"✅ {result['message']}")
                print(f"Session ID: {result['session_id']}")
                print(f"Save this session ID: {result['session_id']}")
            else:
                print(f"❌ {result['error']}")
        
        elif choice == "2":
            print("\n🔑 User Login")
            print("-" * 15)
            email = input("Email: ").strip()
            password = input("Password: ").strip()
            
            result = await auth.login_user(email, password)
            
            if result["success"]:
                print(f"✅ {result['message']}")
                print(f"Welcome, {result['user']['name']}!")
                print(f"Session ID: {result['session_id']}")
                print(f"Save this session ID: {result['session_id']}")
            else:
                print(f"❌ {result['error']}")
        
        elif choice == "3":
            print("\n🚪 Logout")
            print("-" * 10)
            session_id = input("Enter your session ID: ").strip()
            
            result = await auth.logout_user(session_id)
            
            if result["success"]:
                print(f"✅ {result['message']}")
            else:
                print(f"❌ {result['error']}")
        
        elif choice == "4":
            print("\n🔒 Change Password")
            print("-" * 18)
            session_id = input("Enter your session ID: ").strip()
            old_password = input("Current password: ").strip()
            new_password = input("New password: ").strip()
            
            result = await auth.change_password(session_id, old_password, new_password)
            
            if result["success"]:
                print(f"✅ {result['message']}")
            else:
                print(f"❌ {result['error']}")
        
        elif choice == "5":
            print("\n👋 Goodbye!")
            break
        
        else:
            print("❌ Invalid choice. Please select 1-5.")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
