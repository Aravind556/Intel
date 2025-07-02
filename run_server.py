"""
AI Tutor Backend Startup Script
Run this to start the FastAPI server
"""
import uvicorn
import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    print("🚀 Starting AI Tutor Backend Server...")
    print("📖 Documentation will be available at: http://localhost:8000/docs")
    print("🌐 Frontend will be available at: http://localhost:8000/frontend")
    print("💚 Health check: http://localhost:8000/health")
    print("⚠️  Press Ctrl+C to stop the server")
    print("-" * 60)
    
    try:
        uvicorn.run(
            "api.main:app",
            host="0.0.0.0",
            port=8000,
            reload=True,
            log_level="info"
        )
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
    except Exception as e:
        print(f"❌ Failed to start server: {e}")
        sys.exit(1)
