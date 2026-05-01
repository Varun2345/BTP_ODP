#!/bin/bash

echo "=========================================="
echo " Starting OPD Consultation Assistant      "
echo "=========================================="

# Start Backend in the background
echo "[1/2] Starting Backend (FastAPI) on port 8000..."
cd backend
python3 main.py &
BACKEND_PID=$!
cd ..

# Start Frontend in the background
echo "[2/2] Starting Frontend (React) on port 3000..."
cd frontend
npm start &
FRONTEND_PID=$!
cd ..

echo ""
echo "✅ Both services are starting up!"
echo "   Backend: http://localhost:8000"
echo "   Frontend: http://localhost:3000"
echo ""
echo "🛑 Press Ctrl+C to stop the entire application."

# Trap Ctrl+C (SIGINT) to cleanly kill both processes when the user wants to stop
trap "echo -e '\nStopping all services...'; kill $BACKEND_PID $FRONTEND_PID; exit" SIGINT SIGTERM

# Wait indefinitely so the script doesn't exit immediately
wait $BACKEND_PID $FRONTEND_PID
