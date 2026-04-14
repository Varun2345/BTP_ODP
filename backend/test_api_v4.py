import os
from dotenv import load_dotenv
from groq import Groq
load_dotenv()
groq_client = Groq()
chat_completion = groq_client.chat.completions.create(
    messages=[{"role": "user", "content": "Translate 'Hello' to Hindi"}],
    model="llama-3.3-70b-versatile",
)
print("Groq Success:", chat_completion.choices[0].message.content.strip())
