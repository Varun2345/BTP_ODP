# OPD Consultation Assistant
This project uses a React frontend and FastAPI Python backend.

## How to Set Up and Run

### 1. Backend Setup
1. Navigate to the backend folder:
   ```bash
   cd OPD/backend 
   ```
2. Create a virtual environment (optional but recommended):
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Configure your API Keys:
   Open `OPD/backend/.env` and replace the placeholder values with your real API keys:
   * `BHASHINI_API_KEY` (for translations/ASR/TTS)
   * `GROQ_API_KEY` / `GEMINI_API_KEY` (for consultation summarization)

5. Run the backend server:
   ```bash
   uvicorn main:app --reload
   ```
   *The backend will run on `http://localhost:8000`.*

### 2. Frontend Setup
1. Open a new terminal and navigate to the frontend folder:
   ```bash
   cd OPD/frontend
   ```
2. Install Node modules:
   ```bash
   npm install
   ```
3. Run the React app:
   ```bash
   npm start
   ```
   *The frontend will open in your browser at `http://localhost:3000`.*

---

## Where to Place Your API Hooks
Your scaffolding is prepared! To make it fully functional:

**Backend (`OPD/backend/main.py`)**:
- Look for `@app.post("/api/translate")`: This is where you should replace the `dummy_translation` using the `google-generativeai`, `groq`, or Bhashini API calls using the keys loaded from `.env`.
- Look for `@app.post("/api/summarize")`: Pass the `transcript` variable to your chosen LLM instead of returning the dummy summary dictionary.

**Frontend (`OPD/frontend/src/App.js`)**:
- Right now, interaction uses text boxes as substitutes for Speech-to-Text.
- Integrate the standard Web Speech API (or external ASR API) to populate `inputText` automatically.
- Look for `// NOTE: Here is where you would hook up TTS` inside `handleSpeak` to trigger browser speech synthesis using the `res.data.translated` response from your backend.