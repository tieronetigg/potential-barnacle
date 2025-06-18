#!/usr/bin/env python3
"""
Local development server for the SSA-3373 PDF Form Filler API
Run this script to test the API locally before deploying to Railway
"""

import uvicorn
import os
import sys

def check_requirements():
    """Check if all required files exist"""
    required_files = [
        "main.py",
        "fill_pdf_form.py",
        "templates/ssa-3373-formatted-blank.pdf"
    ]
    
    missing_files = []
    for file in required_files:
        if not os.path.exists(file):
            missing_files.append(file)
    
    if missing_files:
        print("❌ Missing required files:")
        for file in missing_files:
            print(f"   - {file}")
        print("\n💡 Make sure you have:")
        print("   1. Your fill_pdf_form.py file")
        print("   2. Your PDF template in the templates/ folder")
        return False
    
    return True

def main():
    """Start the local development server"""
    print("=== SSA-3373 PDF Form Filler - Local Development ===")
    
    # Check requirements
    if not check_requirements():
        sys.exit(1)
    
    print("✅ All required files found")
    print("🚀 Starting local development server...")
    print("📖 API documentation will be available at: http://localhost:8000/docs")
    print("💻 API base URL: http://localhost:8000")
    print("🏥 Health check: http://localhost:8000/health")
    print("\n⏹️  Press Ctrl+C to stop the server")
    print("-" * 60)
    
    # Start the server
    try:
        uvicorn.run(
            "main:app",
            host="0.0.0.0",
            port=8000,
            reload=True,  # Auto-reload on file changes
            reload_dirs=["./"],
            log_level="info"
        )
    except KeyboardInterrupt:
        print("\n👋 Server stopped by user")
    except Exception as e:
        print(f"\n❌ Error starting server: {e}")

if __name__ == "__main__":
    main()
