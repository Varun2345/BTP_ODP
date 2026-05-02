# OPD Consultation Assistant

## How to Run the Application

1. Clone the repository.
2. Ensure you have your `.env` file with the required API keys (GROQ, GEMINI, BHASHINI, etc.) placed inside the `backend` folder.
3. Run the following command in your terminal from the root directory:
   ```bash
   ./start.sh
   ```

*The script will automatically install any missing dependencies and start both the backend and frontend servers.*
# Alternative 
# OPD Consultation Assistant

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
   Open `OPD/backend/.env` and replace the placeholder values with your real API keys.

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
