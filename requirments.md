
---

## **Project Title: Doctor–Patient Conversation Assistant (Team 3)**

### **1. Project Overview**
The goal is to build an AI-powered OPD consultation assistant that bridges the language gap between doctors and patients using real-time transcription, translation, and speech synthesis. It aims to reduce consultation time and provide an automated clinical summary.

---

### **2. Functional Requirements**

#### **A. Multilingual Communication**
* **Speech-to-Text (ASR):** Capture audio via a toggle mic and convert it into text in the speaker's original language.
* **Language Detection:** Automatically detect whether the speaker is using Telugu, Hindi, or English (for the initial input).
* **Machine Translation (NMT):** Translate the transcribed text into the recipient’s chosen language (e.g., Doctor speaks English $\rightarrow$ Patient sees Telugu).
* **Text-to-Speech (TTS):** Provide an audio playback button so the patient/doctor can listen to the translated response.
* **Supported Languages:** English, Hindi, Telugu, Tamil, and Kannada (at least 4-5 Indian languages).

#### **B. Model Flexibility & API Integration**
* **Plug-and-Play Models:** The system must allow users to select which engine to use for ASR, NMT, and TTS.
* **Cost Constraint:** Use only **Free Tier APIs** or Open Source models (e.g., Bhashini, Google Translate API free tier, or Groq for LLMs).
* **LLM Integration:** Option to use an LLM (like Gemini or Llama-3 via API) to handle translation and summarization in one go.

#### **C. Data Management & Summarization**
* **Local Storage:** Store all conversation logs (Doctor: [Text], Patient: [Text]) locally on the device (SQLite) to ensure privacy.
* **Timestamps:** Every dialogue turn must be logged with a precise timestamp.
* **Clinical Summarization:** Once the "End Session" button is clicked, the system must generate a structured summary including:
    * Symptoms & Duration
    * Diagnosis Hints
    * Suggested Tests

---

### **3. UI/UX Requirements (The Interface)**

#### **Visual Layout: The "Split-Screen" Approach**
To keep the interaction natural, the UI should be divided vertically or into two distinct bubbles:

| **Feature** | **Doctor’s Side (Left/Top)** | **Patient’s Side (Right/Bottom)** |
| :--- | :--- | :--- |
| **Language Selection** | Dropdown (Default: English) | Dropdown (Default: Telugu/Hindi) |
| **Input** | Large "Mic" Toggle Button | Large "Mic" Toggle Button |
| **Transcription** | Shows English text as they speak | Shows Native text as they speak |
| **Translation** | Shows Patient’s reply in English | Shows Doctor’s reply in Native language |
| **Audio** | Speaker icon to hear the patient | Speaker icon to hear the doctor |

#### **User Experience (UX) Flow:**
1.  **Select Languages:** Both parties pick their preferred languages.
2.  **Toggle Record:** Doctor taps the mic, speaks, and taps again to stop.
3.  **Instant Feedback:** Transcription appears immediately.
4.  **Auto-Translate:** The translated text appears on the other side of the screen.
5.  **Listen:** The recipient taps "Play" to hear the translation.
6.  **Loop:** The process repeats for the patient.

---

### **4. Technical Stack Recommendations (Free/Open Source)**

* **Frontend:** React.js (for a clean, responsive mobile/web view).
* **ASR/NMT/TTS:** * **Bhashini API:** (Government of India) - Best for Indian languages and usually free for research/BTP.
    * **Sarvam Translate API:** 
    * **Whisper (OpenAI):** Can be used via free API credits or run locally if the hardware allows.
* **Summarization:** Gemini API (Google) or Groq API - preferred (extremely fast and has a generous free tier).
* **Database:**  `SQLite` (Mobile/Desktop).

---

### **5. Summary Format (Output)**

At the end of the consultation, the system must output a copy-pastable report:

> **OPD Consultation Summary**
> * **Patient Language:** Telugu
> * **Doctor Language:** English
> * **Symptoms identified:** [List]
> * **Duration:** [Days/Weeks]
> * **Suggested Tests:** [X-Ray, Blood Test, etc.]
> * **Full Transcript:** [Timestamped Log]

