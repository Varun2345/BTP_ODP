# Task Breakdown

## 1. Planning
- [x] Analyze requirements for Groq Whisper and DeepMultilingualPunctuation
- [ ] Create Implementation Plan
- [ ] Get User Approval

## 2. Backend Enhancements
- [x] Update [requirements.txt](file:///home/sigullapalliakash/Documents/BTP/BTP_ODP-main/backend/requirements.txt) and install `deepmultilingualpunctuation`
- [x] Implement DeepMultilingualPunctuation service in [main.py](file:///home/sigullapalliakash/Documents/BTP/BTP_ODP-main/backend/main.py)
- [x] Create `/api/transcribe` endpoint for Groq Whisper
- [x] Create `/api/punctuate` endpoint for DeepMultilingualPunctuation

## 3. Frontend Enhancements
- [ ] Add ASR Engine Dropdown (Web Speech + DP vs Groq Whisper)
- [ ] Implement `MediaRecorder` logically alongside `SpeechRecognition`
- [ ] Update state to handle audio blobs
- [ ] Update UI to display Word-level Timestamps

## 4. Verification
- [ ] Backend endpoint tests
- [ ] Frontend recording testing
