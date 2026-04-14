import re

with open('/home/home/Desktop/BTP/OPD/backend/main.py', 'r') as f:
    content = f.read()

pattern = r'(    selected_model = getattr\(req, "model_choice", "gemini-2\.5-flash"\))'

replacement = r'''\1

    if selected_model == "google-cloud-translate":
        gct_key = os.getenv("GOOGLE_TRANSLATE_API_KEY")
        if gct_key:
            try:
                lang_map = {"english": "en", "hindi": "hi", "telugu": "te", "tamil": "ta", "kannada": "kn"}
                src = lang_map.get(req.source_lang.lower(), "en")
                tgt = lang_map.get(req.target_lang.lower(), "en")
                url = f"https://translation.googleapis.com/language/translate/v2?key={gct_key}"
                payload = {"q": req.text, "target": tgt, "source": src, "format": "text"}
                res = requests.post(url, json=payload)
                data = res.json()
                if "data" in data and "translations" in data["data"]:
                    translated_text = data["data"]["translations"][0]["translatedText"]
            except Exception as e:
                print("Google Cloud Translation error:", e)
                selected_model = "gemini-2.5-flash"  # fallback
        else:
            print("GOOGLE_TRANSLATE_API_KEY not found. Falling back to Gemini.")
            selected_model = "gemini-2.5-flash"'''

content = re.sub(pattern, replacement, content)

with open('/home/home/Desktop/BTP/OPD/backend/main.py', 'w') as f:
    f.write(content)
