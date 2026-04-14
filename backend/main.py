from fastapi import FastAPI, UploadFile, File, Form, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sqlite3
import os
from dotenv import load_dotenv
from typing import List, Optional

load_dotenv()

# ---------------------------------------------------------
# API KEYS (Loaded directly from .env)
# ---------------------------------------------------------
# We're utilizing Groq and Gemini for ultra-fast translation and summarization via LLM.
from groq import Groq
import google.generativeai as genai
import json
import requests

app = FastAPI(title="OPD Conversation Assistant API")

# Setup CORS for the React Frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Groq Client
groq_client = Groq()

# Initialize Gemini Client (Requires GEMINI_API_KEY in .env)
gemini_api_key = os.getenv("GEMINI_API_KEY")
gemini_configured = False
if gemini_api_key and "your_" not in gemini_api_key:
    genai.configure(api_key=gemini_api_key)
    # Using the standard model available in the old sdk version
    gemini_model = genai.GenerativeModel('gemini-2.5-flash')
    gemini_configured = True


# Initialize Sarvam Client
sarvam_api_key = os.getenv("SARVAM_API_KEY")
sarvam_configured = bool(sarvam_api_key and "your_" not in sarvam_api_key)

# Initialize SQLite Database
groq_client = Groq()


# Initialize SQLite Database
def init_db():
    conn = sqlite3.connect("consultations.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS conversation_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            speaker TEXT,
            original_text TEXT,
            translated_text TEXT,
            source_language TEXT,
            target_language TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS consultation_summaries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            overall_summary TEXT,
            symptoms TEXT,
            duration TEXT,
            suggested_tests TEXT,
            full_transcript TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Try to add the column in case the database already exists without it
    try:
        cursor.execute("ALTER TABLE consultation_summaries ADD COLUMN overall_summary TEXT")
    except sqlite3.OperationalError:
        pass # Column already exists
    
    conn.commit()
    conn.close()

init_db()

class TranslationRequest(BaseModel):
    text: str
    source_lang: str
    target_lang: str
    speaker: str
    model_choice: Optional[str] = "gemini-2.5-flash"

@app.post("/api/translate")
async def translate_text(req: TranslationRequest):
    """
    Translation using Google Gemini (Great for Indian Languages) or Fallback to Groq (Llama 3)
    """
    translated_text = ""
    system_prompt = f"You are a medical translator. Translate the following text from {req.source_lang} to {req.target_lang}. Only return the pure translated text, without quotes or explanations."
    
    selected_model = getattr(req, "model_choice", "gemini-2.5-flash")

    if selected_model == "sarvam-translate" and sarvam_configured:
        try:
            lang_map = {
                "english": "en-IN",
                "hindi": "hi-IN",
                "telugu": "te-IN",
                "tamil": "ta-IN",
                "kannada": "kn-IN"
            }
            src = lang_map.get(req.source_lang.lower(), "en-IN")
            tgt = lang_map.get(req.target_lang.lower(), "hi-IN")
            
            payload = {
                "input": req.text,
                "source_language_code": src,
                "target_language_code": tgt,
                "speaker_gender": "Male",
                "mode": "formal",
                "model": "sarvam-translate:v1"
            }
            headers = {
                "api-subscription-key": sarvam_api_key,
                "Content-Type": "application/json"
            }
            resp = requests.post("https://api.sarvam.ai/translate", json=payload, headers=headers)
            if resp.status_code == 200 and "translated_text" in resp.json():
                translated_text = resp.json()["translated_text"]
            else:
                print("Sarvam translation failed:", resp.text)
                selected_model = "llama-3.3-70b-versatile" # trigger fallback
        except Exception as e:
            print("Sarvam translation error:", e)
            selected_model = "llama-3.3-70b-versatile" # trigger fallback

    if selected_model == "gemini-2.5-flash" and gemini_configured:

        try:
            prompt = f"{system_prompt}\n\nText to translate: {req.text}"
            response = gemini_model.generate_content(prompt)
            if response.text:
                translated_text = response.text.strip()
        except Exception as e:
            print("Gemini translation failed, falling back to Groq:", e)
            selected_model = "llama-3.3-70b-versatile" # trigger fallback

    # Use Groq if explicitly requested or if Gemini failed fallback
    if selected_model in ["llama-3.3-70b-versatile", "llama-3.1-8b-instant"] or not translated_text:
        try:
            target_groq_model = selected_model if selected_model in ["llama-3.3-70b-versatile", "llama-3.1-8b-instant"] else "llama-3.3-70b-versatile"
            chat_completion = groq_client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": req.text}
                ],
                model=target_groq_model,
                temperature=0.3,
            )
            translated_text = chat_completion.choices[0].message.content.strip()
        except Exception as e:
            print("Groq Translation error:", e)

    # Save the log to the database
    try:
        conn = sqlite3.connect("consultations.db")
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO conversation_logs (speaker, original_text, translated_text, source_language, target_language) VALUES (?, ?, ?, ?, ?)",
            (req.speaker, req.text, translated_text, req.source_lang, req.target_lang)
        )
        conn.commit()
    except Exception as db_err:
        print("Database logging error:", db_err)
    finally:
        conn.close()

    return {"original": req.text, "translated": translated_text}

class SummaryRequest(BaseModel):
    model_choice: Optional[str] = "llama-3.3-70b-versatile"

@app.post("/api/summarize")
async def summarize_consultation(req: SummaryRequest = SummaryRequest()):
    """
    Actual Summarization using Groq or Gemini.
    1. Fetch all logs from the database
    2. Format into a prompt
    3. Send to LLM expecting JSON output
    4. Store and return the summary
    """
    conn = sqlite3.connect("consultations.db")
    cursor = conn.cursor()
    cursor.execute("SELECT speaker, original_text, translated_text, timestamp FROM conversation_logs ORDER BY timestamp ASC")
    logs = cursor.fetchall()
    
    print(f"DEBUG: Retrieved {len(logs)} logs from database for summarization.")
    if not logs:
        print("DEBUG: No conversation logs found. Returning error.")
        return {"error": "No conversation logs found."}

    transcript = "\n".join([f"[{row[3]}] {row[0]}: {row[1]} (Translated: {row[2]})" for row in logs])
    print(f"DEBUG: Transcript generated:\n{transcript}")
    
    prompt = f"""
    You are an expert medical AI assistant. Analyze the following Doctor-Patient consultation transcript and summarize it.
    Return ONLY a JSON object with the exact keys: 'overall_summary', 'symptoms', 'duration', 'suggested_tests'. Do not include markdown formatting or backticks around the json.
    'overall_summary' should be a comprehensive paragraph detailing the main points of the entire conversation.
    
    Transcript:
    {transcript}
    """
    
    selected_model = getattr(req, "model_choice", "llama-3.3-70b-versatile")
    
    try:
        if selected_model == "gemini-2.5-flash":
            gemini_model = genai.GenerativeModel('gemini-2.5-flash')
            # Just ask Gemini to produce JSON text, as strict mime-type generation requires a schema struct in newer SDKs
            response = gemini_model.generate_content(prompt)
            summary_text = response.text.replace("```json", "").replace("```", "").strip()
            summary_data = json.loads(summary_text)
        else:
            # Default to Groq models
            actual_model = selected_model if "llama" in selected_model else "llama-3.3-70b-versatile"
            chat_completion = groq_client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model=actual_model,
                temperature=0.2,
                response_format={"type": "json_object"}
            )
            summary_text = chat_completion.choices[0].message.content.strip()
            summary_data = json.loads(summary_text)
    except Exception as e:
        print("Summarization error:", e)
        try:
             # Fallback to the latest available model if the old one is decommissioned
            chat_completion = groq_client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="llama-3.1-8b-instant",
                temperature=0.2,
                response_format={"type": "json_object"}
            )
            summary_text = chat_completion.choices[0].message.content.strip()
            summary_data = json.loads(summary_text)
        except Exception as e2:
            print("Second Summarization error:", e2)
            summary_data = {
                "overall_summary": "Could not be extracted",
                "symptoms": "Could not be extracted",
                "duration": "Could not be extracted",
                "suggested_tests": "Could not be extracted"
            }
    
    
    try:
        # Check if values are unexpectedly returned as lists (some LLMs array JSON) and stringify them
        def _safe_str(val):
            return ", ".join(val) if isinstance(val, list) else str(val)

        print(f"DEBUG: Selected Model: {selected_model}")
        print(f"DEBUG: Raw Summary Text from LLM: {summary_text}")
        print(f"DEBUG: Parsed Summary Data: {summary_data}")

        summary = {
            "overall_summary": _safe_str(summary_data.get("overall_summary", "")),
            "symptoms": _safe_str(summary_data.get("symptoms", "")),
            "duration": _safe_str(summary_data.get("duration", "")),
            "suggested_tests": _safe_str(summary_data.get("suggested_tests", "")),
            "full_transcript": transcript
        }
        
        cursor.execute(
            "INSERT INTO consultation_summaries (overall_summary, symptoms, duration, suggested_tests, full_transcript) VALUES (?, ?, ?, ?, ?)",
            (summary["overall_summary"], summary["symptoms"], summary["duration"], summary["suggested_tests"], summary["full_transcript"])
        )
        
        # Remove the conversation completely from the database per user request
        cursor.execute("DELETE FROM conversation_logs")
        
        conn.commit()
    except Exception as db_err:
        print("Database insertion error:", db_err)
    finally:
        conn.close()
    
    if 'summary' in locals():
        return summary
    else: 
        return {
            "error": "Failed to create summary."
        }

@app.get("/api/logs")
async def get_logs():
    """Retrieve all existing logs from the database."""
    conn = sqlite3.connect("consultations.db")
    cursor = conn.cursor()
    cursor.execute("SELECT speaker, original_text, translated_text FROM conversation_logs ORDER BY timestamp ASC")
    rows = cursor.fetchall()
    conn.close()
    
    logs = [{"speaker": r[0], "original": r[1], "translated": r[2]} for r in rows]
    return {"logs": logs}

@app.post("/api/clear")
async def clear_logs():
    """Clear all logs for a new session."""
    conn = sqlite3.connect("consultations.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM conversation_logs")
    cursor.execute("DELETE FROM consultation_summaries")
    conn.commit()
    conn.close()
    return {"message": "Session cleared."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)