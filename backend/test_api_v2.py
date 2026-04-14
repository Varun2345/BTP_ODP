import os
from dotenv import load_dotenv
from groq import Groq
import google.generativeai as genai

load_dotenv()

print("Testing Gemini...")
try:
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    genai.configure(api_key=gemini_api_key)
    model = genai.GenerativeModel('gemini-pro')
    response = model.generate_content("Translate 'Hello' to Hindi")
    print("Gemini Success:", response.text.strip())
except Exception as e:
    print("Gemini Failed:", str(e))

print("\nTesting Groq...")
try:
    groq_client = Groq()
    chat_completion = groq_client.chat.completions.create(
        messages=[{"role": "user", "content": "Translate 'Hello' to Hindi"}],
        model="llama3.1-8b-instant",
    )
    print("Groq Success:", chat_completion.choices[0].message.content.strip())
except Exception as e:
    print("Groq Failed:", str(e))
