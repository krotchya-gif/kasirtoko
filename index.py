"""
Entry point for Vercel Serverless Function
"""
from flask import Flask, jsonify, render_template_string

app = Flask(__name__)

@app.route('/')
def home():
    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head><title>KasirToko</title></head>
    <body>
        <h1>🏪 KasirToko</h1>
        <p>Aplikasi kasir toko sederhana</p>
        <p><a href="/api/health">Health Check</a></p>
        <p><a href="/login">Login</a></p>
    </body>
    </html>
    """)

@app.route('/login')
def login():
    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head><title>Login - KasirToko</title></head>
    <body>
        <h1>Login</h1>
        <form method="post">
            <input type="text" name="username" placeholder="Username"><br>
            <input type="password" name="password" placeholder="Password"><br>
            <button type="submit">Login</button>
        </form>
        <p>Default: pemilik/pemilik123 atau karyawan/karyawan123</p>
    </body>
    </html>
    """)

@app.route('/api/health')
def health():
    return jsonify({'status': 'ok'})

# Vercel handler
handler = app
