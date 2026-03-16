"""
Entry point for Vercel Serverless Function
"""
import sys
import os
import traceback

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from app import app as application
    app = application
    print("✅ App loaded successfully")
except Exception as e:
    print(f"❌ Error loading app: {e}")
    print(traceback.format_exc())
    raise

# For debugging
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
