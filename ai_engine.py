# ai_engine.py
import os
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    raise RuntimeError("GEMINI_API_KEY missing in environment")

client = genai.Client(api_key=API_KEY)

def ask_gemini_grounded(prompt):
    """
    Sends prompt to Gemini with google_search grounding enabled.
    Returns: dict { text: str, grounding_chunks: list(dict) }
    """
    try:
        # Create the google_search tool
        grounding_tool = types.Tool(google_search=types.GoogleSearch())
        config = types.GenerateContentConfig(tools=[grounding_tool])

        resp = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=config,
        )

        # primary text (safe access)
        text = getattr(resp, "text", None) or ""
        if not text:
            # fallback: check candidate parts
            try:
                text = resp.candidates[0].content.parts[0].text
            except Exception:
                text = ""

        # Extract grounding chunks (sources) if present
        grounding_chunks = []
        try:
            gm = resp.candidates[0].grounding_metadata
            grounding_chunks = [
                {
                    "title": c.web.title if hasattr(c.web, "title") else None,
                    "uri": c.web.uri if hasattr(c.web, "uri") else None
                }
                for c in getattr(gm, "grounding_chunks", []) if hasattr(c, "web")
            ]
        except Exception:
            grounding_chunks = []

        return {"text": text, "grounding_chunks": grounding_chunks}

    except Exception as e:
        # return error string for debugging
        return {"text": f"Error: {str(e)}", "grounding_chunks": []}
