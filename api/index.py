
from flask import Flask, jsonify
app = Flask(__name__)

@app.route("/")
def home():
    return jsonify({"status": "ok", "app": "KasirToko"})

@app.route("/api/health")
def health():
    return jsonify({"status": "ok"})

