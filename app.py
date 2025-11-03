from flask import Flask, request, jsonify, render_template
import os
import requests
import google.generativeai as genai
from dotenv import load_dotenv
from flask_cors import CORS
import uuid
import fitz  # PyMuPDF

load_dotenv()

app = Flask(__name__)
CORS(app)

# Config & keys
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
SEARCH_ENGINE_ID = os.getenv("SEARCH_ENGINE_ID")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

genai.configure(api_key=GEMINI_API_KEY)

# In-memory conversation history per chat_id
CONVERSATION_HISTORY = {}
MAX_HISTORY_TURNS = 15  # each turn = user + AI

# -------------------------------
# Helper: Google Custom Search
# -------------------------------
def fetch_live_search(query):
    try:
        if not GOOGLE_API_KEY or not SEARCH_ENGINE_ID:
            return None
        url = "https://www.googleapis.com/customsearch/v1"
        params = {"key": GOOGLE_API_KEY, "cx": SEARCH_ENGINE_ID, "q": query, "num": 3}
        res = requests.get(url, params=params, timeout=8)
        if res.status_code == 200:
            return res.json()
        else:
            app.logger.warning("Search API returned %s: %s", res.status_code, res.text)
            return None
    except Exception as e:
        app.logger.exception("Error in fetch_live_search: %s", e)
        return None

# -------------------------------
# Generate AI reply (uses history + web context + PDF text)
# -------------------------------
def generate_ai_reply(message, chat_context_str, web_context_snippets, pdf_text=""):
    model = genai.GenerativeModel("gemini-2.5-flash")

    prompt = f"""
You are ASK AI — a smart, friendly, and conversational assistant. 
Adjust your tone based on the question:

1. Casual or fun questions (jokes, riddles, entertainment): Be humorous, light, and friendly. Grammar corrections are not needed.
2. Factual, technical, or academic questions (history, science, math, definitions, technology, latest devices): Be clear, concise, and confident. Avoid jokes, unnecessary apologies, or filler.

Use ongoing chat context if needed, web info only to verify or update facts, and PDF content only if relevant.

Guidelines:
- Keep answers short, clear, and conversational.
- Maintain context from previous messages without repeating the question unnecessarily.
- Avoid unrelated brands, products, or extra commentary.

Conversation context (most recent first):
{chat_context_str}

Web context summary (use only if directly relevant):
{web_context_snippets}

PDF content (use only if directly relevant):
{pdf_text}

User question: {message}

Now respond naturally, conversationally, and context-aware.
"""
    try:
        response = model.generate_content(prompt)
        return (response.text or "").strip()
    except Exception as e:
        app.logger.exception("generate_ai_reply error: %s", e)
        return "Sorry — I couldn’t get an answer right now."

# -------------------------------
# Routes
# -------------------------------
@app.route("/")
def home():
    return render_template("index.html")

@app.route("/new_chat", methods=["POST"])
def new_chat():
    chat_id = "chat_" + uuid.uuid4().hex[:8]
    CONVERSATION_HISTORY[chat_id] = []
    return jsonify({"chat_id": chat_id, "title": "New Chat"})

@app.route("/ask", methods=["POST"])
def ask():
    try:
        pdf_text = ""
        if request.content_type and request.content_type.startswith("multipart/form-data"):
            user_message = (request.form.get("message") or "").strip()
            chat_id = request.form.get("chat_id") or None
            file = request.files.get("file")

            if file and file.filename.lower().endswith(".pdf"):
                pdf_bytes = file.read()
                pdf_doc = fitz.open(stream=pdf_bytes, filetype="pdf")
                pdf_text = ""
                for page in pdf_doc:
                    pdf_text += page.get_text()
                pdf_text = pdf_text.strip()
                user_message = (user_message + " ").strip() + "[PDF content attached]"

        else:
            data = request.get_json(silent=True) or {}
            user_message = (data.get("message") or "").strip()
            chat_id = data.get("chat_id") or None

        if not user_message:
            return jsonify({"reply": "Please enter a message."}), 400

        if not chat_id:
            chat_id = "chat_" + uuid.uuid4().hex[:8]
            CONVERSATION_HISTORY[chat_id] = []

        hist = CONVERSATION_HISTORY.setdefault(chat_id, [])
        hist.append(f"User: {user_message}")
        if len(hist) > MAX_HISTORY_TURNS * 2:
            hist = hist[-(MAX_HISTORY_TURNS * 2):]
            CONVERSATION_HISTORY[chat_id] = hist

        search_results = fetch_live_search(user_message)
        web_context = ""
        if search_results and "items" in search_results:
            snippets = [f"{item.get('title','')}: {item.get('snippet','')}" for item in search_results["items"][:3]]
            web_context = "\n".join(snippets)

        context_slice = CONVERSATION_HISTORY.get(chat_id, [])[-(MAX_HISTORY_TURNS * 2):]
        chat_context = "\n".join(reversed(context_slice))

        ai_reply = generate_ai_reply(user_message, chat_context, web_context, pdf_text)
        hist.append(f"AI: {ai_reply}")
        if len(hist) > MAX_HISTORY_TURNS * 2:
            hist = hist[-(MAX_HISTORY_TURNS * 2):]
            CONVERSATION_HISTORY[chat_id] = hist

        title = user_message[:40] if user_message else "New Chat"

        return jsonify({"reply": ai_reply, "chat_id": chat_id, "title": title})
    except Exception as e:
        app.logger.exception("ask route error: %s", e)
        return jsonify({"reply": f"Error: {str(e)}"}), 500

@app.route("/chats", methods=["GET"])
def chats():
    out = {}
    for cid, hist in CONVERSATION_HISTORY.items():
        title = hist[0].replace("User: ", "")[:30] if hist else "Chat"
        out[cid] = {"title": title, "messages": []}
    return jsonify(out)

# -------------------------------
# Run
# -------------------------------
if __name__ == "__main__":
    app.run(port=9000, debug=True)
