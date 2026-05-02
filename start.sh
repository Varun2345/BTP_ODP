#!/bin/bash

echo "=========================================="
echo " Starting OPD Consultation Assistant      "
echo "=========================================="

if [ ! -f "backend/.env" ]; then
    echo "backend/.env file not found!"
    echo "Creating a template .env file..."
    echo "GROQ_API_KEY=your_key_here" > backend/.env
    echo "GEMINI_API_KEY=your_key_here" >> backend/.env
    echo "BHASHINI_API_KEY=your_key_here" >> backend/.env
    echo "Setup paused: Please open backend/.env, add your real API keys, and run ./start.sh again."
    exit 1
fi

if [ ! -d "frontend/node_modules" ]; then
    echo "First time setup: Installing Frontend Dependencies..."
    cd frontend
    npm install
    cd ..
fi

echo "Verifying Backend Dependencies..."
pip3 install -r backend/requirements.txt -q
echo "Starting Backend (FastAPI) on port 8000..."
cd backend
python3 main.py &
BACKEND_PID=$!
cd ..

echo "Starting Frontend (React) on port 3000..."
cd frontend
npm start &
FRONTEND_PID=$!
cd ..

echo ""
echo "Starting up the services!"
echo "Backend: http://localhost:8000"
echo "Frontend: http://localhost:3000"
echo ""
echo "Press Ctrl+C to stop the entire application."

trap "echo -e '\nStopping all services...'; kill $BACKEND_PID $FRONTEND_PID; exit" SIGINT SIGTERM

wait $BACKEND_PID $FRONTEND_PID
