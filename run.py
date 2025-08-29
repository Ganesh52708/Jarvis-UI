#!/usr/bin/env python3
"""
JARVIS Voice Assistant Web Interface
Run this script to start the web application
"""

import sys
import os

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if __name__ == '__main__':
    try:
        from app import app
        print("🚀 Starting JARVIS Voice Assistant...")
        print("🌐 Open http://localhost:5000 in your browser")
        print("🎤 Make sure to allow microphone permissions")
        print("📋 Install dependencies: pip install -r requirements.txt")
        print("=" * 50)
        
        app.run(debug=True, host='0.0.0.0', port=5000, threaded=True)
    except ImportError as e:
        print(f"❌ Import Error: {e}")
        print("📦 Please install required packages: pip install -r requirements.txt")
    except Exception as e:
        print(f"❌ Error starting application: {e}")
