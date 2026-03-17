# Vercel Serverless Function Entry Point
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the Flask app
from app import app

# Vercel handler
from http.server import BaseHTTPRequestHandler
from io import BytesIO

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        
        with app.test_client() as client:
            response = client.get(self.path)
            self.wfile.write(response.data)
    
    def do_POST(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)
        
        with app.test_client() as client:
            response = client.post(
                self.path,
                data=body,
                content_type=self.headers.get('Content-Type', 'application/json')
            )
            self.wfile.write(response.data)

# For Vercel serverless
from flask import Flask
application = app
