import os
from dotenv import load_dotenv
from groq import Groq
load_dotenv()
try:
    groq_client = Groq()
    models = groq_client.models.list()
    for m in models.data:
        print(m.id)
except Exception as e:
    print(e)
