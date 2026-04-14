import re

with open('/home/home/Desktop/BTP/OPD/backend/main.py', 'r') as f:
    content = f.read()

# Add config parsing
sarvam_config = """
# Initialize Sarvam Client
sarvam_api_key = os.getenv("SARVAM_API_KEY")
sarvam_configured = bool(sarvam_api_key and "your_" not in sarvam_api_key)

# Initialize SQLite Database
groq_client = Groq()
"""

content = content.replace("# Initialize SQLite Database\ngroq_client = Groq()", sarvam_config)

# Add logic
sarvam_logic = """
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
                "input": [req.text],
                "source_language_code": src,
                "target_language_code": tgt,
                "speaker_gender": "Male",
                "mode": "formal",
                "model": "sarvam-translate"
            }
            headers = {
                "api-subscription-key": sarvam_api_key,
                "Content-Type": "application/json"
            }
            resp = requests.post("https://api.sarvam.ai/translate", json=payload, headers=headers)
            if resp.status_code == 200 and "translated_text" in resp.json():
                translated_text = resp.json()["translated_text"][0]
            else:
                print("Sarvam translation failed:", resp.text)
                selected_model = "llama-3.3-70b-versatile" # trigger fallback
        except Exception as e:
            print("Sarvam translation error:", e)
            selected_model = "llama-3.3-70b-versatile" # trigger fallback

    if selected_model == "gemini-2.5-flash" and gemini_configured:
"""

content = content.replace("    if selected_model == \"gemini-2.5-flash\" and gemini_configured:", sarvam_logic)

with open('/home/home/Desktop/BTP/OPD/backend/main.py', 'w') as f:
    f.write(content)
