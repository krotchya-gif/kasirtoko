"""
Entry point for Vercel Serverless Function - Debug Version
"""
import sys
import os
import traceback

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Force SQLite for testing
os.environ['POSTGRES_URL'] = ''
os.environ['POSTGRES_PRISMA_URL'] = ''

print("="*50)
print("STARTUP DEBUG - Forcing SQLite")
print("="*50)

from flask import Flask, jsonify

try:
    from app import app as application
    app = application
    print("✅ App loaded successfully with SQLite")
except Exception as e:
    error_msg = f"Error loading app: {e}\n{traceback.format_exc()}"
    print(error_msg)
    
    app = Flask(__name__)
    @app.route('/')
    def startup_error():
        return f"<h1>Startup Error</h1><pre>{error_msg}</pre>", 500

@app.route('/api/health')
def health():
    return jsonify({'status': 'ok', 'mode': 'sqlite_fallback'})
