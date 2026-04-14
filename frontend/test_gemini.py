import requests

res = requests.post("http://127.0.0.1:8000/api/summarize", json={"model_choice": "gemini-2.5-flash"})
print(res.status_code, res.json())
