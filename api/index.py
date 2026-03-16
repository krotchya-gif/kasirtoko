"""
Entry point for Vercel Serverless Function
"""
import sys
import os
import traceback

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

print("Loading application...")
print(f"Python path: {sys.path}")
print(f"Current dir: {os.getcwd()}")
print(f"POSTGRES_URL exists: {'POSTGRES_URL' in os.environ}")
print(f"POSTGRES_PRISMA_URL exists: {'POSTGRES_PRISMA_URL' in os.environ}")

try:
    from app import app as application
    app = application
    print("✅ App loaded successfully")
except Exception as e:
    error_msg = f"❌ Error loading app: {e}\n{traceback.format_exc()}"
    print(error_msg)
    
    # Create fallback app that shows error
    from flask import Flask, jsonify
    app = Flask(__name__)
    
    @app.route('/')
    @app.route('/<path:path>')
    def error_page(path=None):
        return f"""
        <html>
        <head><title>Startup Error</title></head>
        <body>
        <h1>Application Startup Error</h1>
        <pre style="background:#f5f5f5;padding:20px;overflow:auto;">{error_msg}</pre>
        </body>
        </html>
        """, 500
    
    @app.route('/api/health')
    def health_error():
        return jsonify({'error': str(e), 'traceback': traceback.format_exc()}), 500

# Health check endpoint
if 'app' in dir() and hasattr(app, 'route'):
    @app.route('/api/health', methods=['GET'])
    def health_check():
        from flask import jsonify
        import psycopg2
        from app import USE_POSTGRES, POSTGRES_URL, DB_PATH
        
        status = {
            'status': 'ok',
            'postgres': USE_POSTGRES,
            'postgres_url_set': bool(POSTGRES_URL),
            'db_path': DB_PATH if not USE_POSTGRES else None
        }
        
        if USE_POSTGRES:
            try:
                conn = psycopg2.connect(POSTGRES_URL)
                cur = conn.cursor()
                cur.execute('SELECT version()')
                version = cur.fetchone()[0]
                cur.close()
                conn.close()
                status['db_connection'] = 'ok'
                status['db_version'] = version
            except Exception as e:
                status['db_connection'] = 'error'
                status['db_error'] = str(e)
        
        return jsonify(status)
