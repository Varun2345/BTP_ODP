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
import shutil
import uuid
import sys

# Import our new pipeline logic
from disfluency_pipeline import run_pipeline

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
groq_api_key = os.getenv("GROQ_API_KEY", "your-default-key")
groq_client = Groq(api_key=groq_api_key)

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
            overall_summary TEXT, -- Legacy
            subjective TEXT,
            objective TEXT,
            assessment TEXT,
            plan TEXT,
            disfluency_level TEXT,
            demeanor_note TEXT,
            full_transcript TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Try to add the column in case the database already exists without it
    # Migrations for existing databases
    new_cols = [
        ("subjective", "TEXT"),
        ("objective", "TEXT"),
        ("assessment", "TEXT"),
        ("plan", "TEXT"),
        ("disfluency_level", "TEXT"),
        ("demeanor_note", "TEXT")
    ]
    for col_name, col_type in new_cols:
        try:
            cursor.execute(f"ALTER TABLE consultation_summaries ADD COLUMN {col_name} {col_type}")
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

@app.post("/api/transcribe")
async def transcribe_audio(audio: UploadFile = File(...)):
    """Receives audio file from frontend, runs Whisper disfluency pipeline, returns text."""
    temp_file = f"temp_{uuid.uuid4()}.webm"
    
    try:
        with open(temp_file, "wb") as buffer:
            shutil.copyfileobj(audio.file, buffer)
            
        print(f"DEBUG: Processing audio file {temp_file}")
        
        # Run Whisper pipeline
        result = run_pipeline(temp_file)
        
        if result and "final_text" in result:
            return {"transcription": result["final_text"]}
        else:
            return {"transcription": "", "error": "No speech detected"}
            
    except Exception as e:
        print(f"Transcription error: {e}")
        return {"transcription": "", "error": str(e)}
    finally:
        if os.path.exists(temp_file):
            os.remove(temp_file)

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

@app.get("/api/summarize")
async def summarize_consultation(selected_model: str = "llama-3.3-70b-versatile", consultant_mode: str = "scribe"):
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
        return {"error": "No conversation logs found in database. Please click 'Translate & Send' or dictate a message first."}

    transcript = "\n".join([f"[{row[3]}] {row[0]}: {row[1]} (Translated: {row[2]})" for row in logs])
    print(f"DEBUG: Transcript generated:\n{transcript}")
    
    if consultant_mode == "assistant":
        system_instructions = """
        You are an Expert Medical AI Assistant. Your task is to analyze the provided Doctor-Patient transcript and generate a comprehensive SOAP note. 

        ### YOUR DUAL MISSION:
        1. SCRIBE: Accurately summarize the conversation history, including patient demeanor based on disfluency markers ("um", "uh", "...", "......").
        2. ADVISE: Use your medical knowledge to suggest potential assessments and clinical plans, even if the doctor did not explicitly state them during the brief encounter.

        ### SECTION-SPECIFIC INSTRUCTIONS:
        1. SUBJECTIVE (S): 
           - Summarize the patient's complaints and history. 
           - Use the disfluency markers to describe the patient's state (e.g., "appears in distress," "hesitant," or "pain-limited speech").
        2. OBJECTIVE (O): 
           - List any vitals or findings mentioned. 
           - SUGGEST: List physical examinations the doctor SHOULD perform based on the patient's symptoms (label these as "Suggested Exams").
        3. ASSESSMENT (A): 
           - Provide a differential diagnosis based on the symptoms described. 
           - Rank the most likely conditions (e.g., "Highly suspicious for Sciatica").
        4. PLAN (P): 
           - Propose a comprehensive management plan including appropriate imaging (MRI/X-ray), medications (NSAIDs, etc.), and follow-up care that matches standard medical protocols for these symptoms.

        ### OUTPUT FORMAT:
        Return ONLY a JSON object:
        {
          "subjective": "Summary of report + behavioral observations.",
          "objective": "Recorded vitals + Suggested physical exams.",
          "assessment": "Proactive clinical impressions and differential diagnoses.",
          "plan": "Comprehensive suggested next steps and treatments.",
          "metadata": {
            "disfluency_level": "Low/Medium/High",
            "clinical_confidence": "Percentage score of AI certainty"
          }
        }
        """
    else:  # scribe mode (default)
        system_instructions = """
        You are a Precise Medical Scribe. Your sole task is to summarize the provided Doctor-Patient transcript into a SOAP note. You must follow the "Zero-Inference Rule": Do not include any medical advice, diagnoses, or plans that were not explicitly stated by the participants in the audio.

        ### TRANSCRIPT CONSTRAINTS:
        - The transcript contains verbatim speech markers: "um", "uh", "...", and "......".
        - Use these markers ONLY to assess the patient's demeanor in the Subjective section.
        - STRIP these markers from all other clinical data points.

        ### SECTION-SPECIFIC INSTRUCTIONS:
        1. SUBJECTIVE (S): 
           - ONLY include symptoms and history explicitly mentioned by the patient. 
           - Mention the patient's demeanor (e.g., "appeared hesitant," "frequent pauses") based on the disfluency markers.
           - If no symptoms were discussed, state "None mentioned."

        2. OBJECTIVE (O): 
           - ONLY include physical findings, vitals (BP, Temp), or observations explicitly stated by the doctor. 
           - If the doctor did not perform an exam or state vitals, state "Not recorded."

        3. ASSESSMENT (A): 
           - ONLY include the diagnosis or clinical impression if the doctor explicitly named it. 
           - Do not guess a diagnosis based on the symptoms. 
           - If the doctor did not provide a diagnosis, state "Not discussed."

        4. PLAN (P): 
           - ONLY include medications, tests, or follow-ups that were explicitly mentioned by the doctor in the transcript. 
           - If the doctor did not mention a plan, state "No plan discussed."

        ### OUTPUT FORMAT:
        Return ONLY a JSON object with this structure:
        {
          "subjective": "Clean summary of patient report and demeanor.",
          "objective": "Strictly recorded findings or 'Not recorded'.",
          "assessment": "Explicit diagnosis or 'Not discussed'.",
          "plan": "Explicit next steps or 'No plan discussed'.",
          "metadata": {
            "disfluency_level": "Low/Medium/High",
            "observation": "Brief note on speech patterns."
          }
        }
        """

    prompt = f"""
    {system_instructions}

    ### TRANSCRIPT:
    {transcript}
    """
    
    # model is passed directly as an argument now
    
    try:
        if selected_model == "gemini-2.5-flash":
            gemini_model = genai.GenerativeModel('gemini-2.5-flash')
            # Just ask Gemini to produce JSON text, as strict mime-type generation requires a schema struct in newer SDKs
            response = gemini_model.generate_content(prompt)
            summary_text = response.text.replace("```json", "").replace("```", "").strip()
            summary_data = json.loads(summary_text)
        else:
            # Default to provided Groq model or fallback safely
            actual_model = selected_model if selected_model else "llama-3.3-70b-versatile"
            chat_completion = groq_client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model=actual_model,
                temperature=0.2,
                response_format={"type": "json_object"}
            )
            summary_text = chat_completion.choices[0].message.content.strip()
            # Robust JSON cleaning
            cleaned_text = summary_text
            if "```json" in cleaned_text:
                cleaned_text = cleaned_text.split("```json")[-1].split("```")[0].strip()
            elif "```" in cleaned_text:
                cleaned_text = cleaned_text.split("```")[-1].split("```")[0].strip()
            
            try:
                summary_data = json.loads(cleaned_text)
            except json.JSONDecodeError:
                # Attempt to find the first { and last } if parsing failed
                import re
                match = re.search(r"(\{.*\}|\[.*\])", cleaned_text, re.DOTALL)
                if match:
                    summary_data = json.loads(match.group(0))
                else:
                    raise ValueError("No valid JSON found in LLM response")
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        print("CRITICAL Summarization error:\n", error_detail)
        summary_data = {
            "subjective": f"Summarization failed. Backend error: {str(e)}",
            "objective": "Please check backend console logs for details.",
            "assessment": "ERROR",
            "plan": "Retry requested",
            "metadata": {"disfluency_level": "N/A", "demeanor_note": "N/A"}
        }
    
    
    try:
        # Check if values are unexpectedly returned as lists (some LLMs array JSON) and stringify them
        def _safe_str(val):
            return ", ".join(val) if isinstance(val, list) else str(val)

        print(f"DEBUG: Selected Model: {selected_model}")
        print(f"DEBUG: Raw Summary Text from LLM: {summary_text}")
        print(f"DEBUG: Parsed Summary Data: {summary_data}")

        if not isinstance(summary_data, dict):
            summary_data = {
                "subjective": str(summary_data),
                "objective": "Not recorded",
                "assessment": "Summarization produced invalid data",
                "plan": "Review transcript manually",
                "metadata": {"disfluency_level": "Unknown", "demeanor_note": "N/A"}
            }

        metadata = summary_data.get("metadata", {})
        if not isinstance(metadata, dict):
            metadata = {}

        summary = {
            "subjective": _safe_str(summary_data.get("subjective", "")),
            "objective": _safe_str(summary_data.get("objective", "")),
            "assessment": _safe_str(summary_data.get("assessment", "")),
            "plan": _safe_str(summary_data.get("plan", "")),
            "disfluency_level": _safe_str(metadata.get("disfluency_level", "Unknown")),
            "demeanor_note": _safe_str(metadata.get("demeanor_note", "N/A")),
            "full_transcript": transcript
        }
        
        cursor.execute(
            "INSERT INTO consultation_summaries (subjective, objective, assessment, plan, disfluency_level, demeanor_note, full_transcript) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (summary["subjective"], summary["objective"], summary["assessment"], summary["plan"], summary["disfluency_level"], summary["demeanor_note"], summary["full_transcript"])
        )
        
        # We no longer clear here so user can go back and update.
        
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

@app.post("/api/log")
async def log_transcription(req: TranslationRequest):
    # This endpoint is used to auto-log transcription segments
    try:
        conn = sqlite3.connect("consultations.db")
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO conversation_logs (speaker, original_text, translated_text, source_language, target_language) VALUES (?, ?, ?, ?, ?)",
            (req.speaker, req.text, req.text, "en-IN", "en-IN") # Default to en for raw logs
        )
        conn.commit()
        conn.close()
        return {"status": "success", "text": req.text}
    except Exception as e:
        print("Auto-log error:", e)
        return {"status": "error", "message": str(e)}

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