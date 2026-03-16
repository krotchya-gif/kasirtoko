"""
Entry point for Vercel Serverless Function - Debug Version
"""
import sys
import os
import traceback

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

print("="*50)
print("STARTUP DEBUG")
print(f"Python path: {sys.path}")
print(f"Current dir: {os.getcwd()}")
print(f"Files in dir: {os.listdir('.')}")
print("="*50)

# Test imports
errors = []

try:
    from flask import Flask
    print("✅ Flask imported")
except Exception as e:
    errors.append(f"Flask import: {e}")

try:
    import psycopg2
    print("✅ psycopg2 imported")
except Exception as e:
    errors.append(f"psycopg2 import: {e}")

try:
    from werkzeug.security import generate_password_hash
    print("✅ werkzeug imported")
except Exception as e:
    errors.append(f"werkzeug import: {e}")

# Check env vars
print(f"POSTGRES_URL exists: {'POSTGRES_URL' in os.environ}")
print(f"POSTGRES_PRISMA_URL exists: {'POSTGRES_PRISMA_URL' in os.environ}")

if errors:
    print("❌ Import errors:")
    for err in errors:
        print(f"  - {err}")
    
    app = Flask(__name__)
    @app.route('/')
    def error_page():
        return f"<h1>Import Errors</h1><pre>{'</pre><pre>'.join(errors)}</pre>", 500
else:
    print("All imports OK, loading app...")
    try:
        from app import app as application
        app = application
        print("✅ App loaded successfully")
    except Exception as e:
        error_msg = f"Error loading app: {e}\n{traceback.format_exc()}"
        print(error_msg)
        
        app = Flask(__name__)
        @app.route('/')
        def startup_error():
            return f"<h1>Startup Error</h1><pre>{error_msg}</pre>", 500

@app.route('/api/health')
def health():
    from flask import jsonify
    return jsonify({'status': 'ok', 'errors': errors})
