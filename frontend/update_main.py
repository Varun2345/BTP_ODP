import re

with open('/home/home/Desktop/BTP/OPD/backend/main.py', 'r') as f:
    content = f.read()

pattern = r'async def translate_text\(.*?return \{"original": req\.text, "translated": translated_text\}'

new_content = """async def translate_text(req: TranslationRequest):
    \"\"\"
    Translation using Google Gemini (Great for Indian Languages) or Fallback to Groq (Llama 3)
    \"\"\"
    translated_text = ""
    system_prompt = f"You are a medical translator. Translate the following text from {req.source_lang} to {req.target_lang}. Only return the pure translated text, without quotes or explanations."
    
    selected_model = getattr(req, "model_choice", "gemini-pro")

    if selected_model == "gemini-pro" and gemini_configured:
        try:
            prompt = f"{system_prompt}\\n\\nText to translate: {req.text}"
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

    return {"original": req.text, "translated": translated_text}"""

content = re.sub(pattern, new_content, content, flags=re.DOTALL)

with open('/home/home/Desktop/BTP/OPD/backend/main.py', 'w') as f:
    f.write(content)
