"""
Scam Shield for WhatsApp
-------------------------
A RAG + Agentic AI powered scam/spam detector and privacy assistant for
WhatsApp-style messages.

Run with:
    python app.py
Then open http://localhost:5000
"""

import os

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request

load_dotenv()

from agents.orchestrator import analyze_message  # noqa: E402  (after load_dotenv)
from agents.smalltalk import small_talk_reply  # noqa: E402
from utils.gemini_client import is_available  # noqa: E402

app = Flask(__name__)


@app.route("/")
def index():
    return render_template("index.html", gemini_live=is_available())


@app.route("/api/analyze", methods=["POST"])
def api_analyze():
    payload = request.get_json(silent=True) or {}
    message = (payload.get("message") or "").strip()

    if not message:
        return jsonify({"error": "Please paste a message to analyze."}), 400

    if len(message) > 4000:
        return jsonify({"error": "Message is too long (max 4000 characters)."}), 400

    chat_reply = small_talk_reply(message)
    if chat_reply:
        return jsonify({"chat_reply": chat_reply})

    try:
        result = analyze_message(message)
        return jsonify(result)
    except Exception as exc:  # pragma: no cover - defensive
        return jsonify({"error": f"Analysis failed: {exc}"}), 500


@app.route("/api/status")
def api_status():
    return jsonify({"gemini_live": is_available()})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
