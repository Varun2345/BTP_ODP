import React, { useState, useRef, useEffect } from 'react';
import axios from 'axios';
import './App.css';

const API_BASE_URL = 'http://localhost:8000/api';

function App() {
  const [patientLang, setPatientLang] = useState('telugu');
  const [docLang, setDocLang] = useState('english'); 
  const [patientModel, setPatientModel] = useState('gemini-2.5-flash');
  const [docModel, setDocModel] = useState('gemini-2.5-flash');
  const [summaryModel, setSummaryModel] = useState('llama-3.3-70b-versatile');
  const [inputText, setInputText] = useState('');
  const inputTextRef = useRef('');
  const speakerContextRef = useRef('Doctor');
  const [logs, setLogs] = useState([]);
  const [summary, setSummary] = useState(null);
  const [isRecording, setIsRecording] = useState(false);
  const [isSummarizing, setIsSummarizing] = useState(false);
  const [speakerContextState, setSpeakerContextState] = useState('Doctor');

  const setSpeakerContext = (ctx) => {
    setSpeakerContextState(ctx);
    speakerContextRef.current = ctx;
  };

  const updateInputText = (text) => {
    setInputText(text);
    inputTextRef.current = text;
  };

  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  const recognitionRef = useRef(null);
  const isRecordingRef = useRef(false);

  useEffect(() => {
    axios.get(`${API_BASE_URL}/logs`)
      .then(res => {
        if (res.data && res.data.logs) {
          setLogs(res.data.logs);
        }
      })
      .catch(err => console.error("Error fetching logs:", err));
  }, []);

  if (!recognitionRef.current && SpeechRecognition) {
    recognitionRef.current = new SpeechRecognition();
    recognitionRef.current.continuous = true;
    recognitionRef.current.interimResults = true;
    
    recognitionRef.current.onresult = (event) => {
      let finalTranscript = '';
      for (let i = event.resultIndex; i < event.results.length; ++i) {
        if (event.results[i].isFinal) {
          finalTranscript += event.results[i][0].transcript + ' ';
        }
      }
      if (finalTranscript) {
        updateInputText(inputTextRef.current + finalTranscript);
      }
    };

    recognitionRef.current.onerror = (event) => {
      console.error('Speech recognition error', event.error);
      if (event.error !== 'not-allowed' && event.error !== 'no-speech') {
        setIsRecording(false);
        isRecordingRef.current = false;
      }
    };

    recognitionRef.current.onend = () => {
      if (isRecordingRef.current) {
         try {
           recognitionRef.current.start();
         } catch(e) {
           console.log("Could not restart immediately", e);
         }
      } else {
        setIsRecording(false);
      }
    };
  }

  const toggleMic = (speaker) => {
    if (isRecordingRef.current && speakerContextState === speaker) {
      isRecordingRef.current = false;
      recognitionRef.current.stop();
      setIsRecording(false);
      return;
    }

    if (isRecordingRef.current) {
        recognitionRef.current.stop();
    }

    setSpeakerContext(speaker);
    updateInputText('');
    setIsRecording(true);
    isRecordingRef.current = true;

    let langCode = 'en-US';
    const currentLang = speaker === 'Doctor' ? docLang : patientLang;
    if (currentLang === 'hindi') langCode = 'hi-IN';
    if (currentLang === 'telugu') langCode = 'te-IN';
    if (currentLang === 'tamil') langCode = 'ta-IN';
    if (currentLang === 'kannada') langCode = 'kn-IN';

    if (recognitionRef.current) {
      recognitionRef.current.lang = langCode;
      try {
        recognitionRef.current.start();
      } catch (e) { }
    } else {
      alert("Your browser does not support Speech Recognition. Try Chrome.");
    }
  };

  const handleSpeakText = async (speaker, textToTranslate) => {
    if (!textToTranslate.trim()) return;
    const sourceLang = speaker === 'Doctor' ? docLang : patientLang;
    const targetLang = speaker === 'Doctor' ? patientLang : docLang;
    const modelChoice = speaker === 'Doctor' ? docModel : patientModel;

    try {
      const res = await axios.post(`${API_BASE_URL}/translate`, {
        text: textToTranslate,
        source_lang: sourceLang,
        target_lang: targetLang,
        speaker: speaker,
        model_choice: modelChoice
      });

      setLogs(prev => [...prev, {
        speaker: speaker,
        original: res.data.original,
        translated: res.data.translated
      }]);
      
      updateInputText('');
      playTTS(res.data.translated, targetLang);
    } catch (err) {
      console.error("Translation ERROR:", err);
      alert('Translation failed. Check backend connection.');
    }
  };

  const playTTS = (text, lang) => {
    if (!('speechSynthesis' in window)) return;
    
    let langCode = 'en-US';
    if (lang === 'hindi') langCode = 'hi-IN';
    if (lang === 'telugu') langCode = 'te-IN';
    if (lang === 'tamil') langCode = 'ta-IN';
    if (lang === 'kannada') langCode = 'kn-IN';

    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = langCode;
    window.speechSynthesis.speak(utterance);
  };

  const endSession = async () => {
    if (isRecordingRef.current) {
       isRecordingRef.current = false;
       recognitionRef.current.stop();
       setIsRecording(false);
    }
    
      setIsSummarizing(true);
      try {
          const res = await axios.post(`${API_BASE_URL}/summarize`, {
            model_choice: summaryModel
          });
          setSummary(res.data);
      } catch (err) {
        console.error(err);
        alert('Summarization failed.');
      } finally {
        setIsSummarizing(false);
      }
    };

    const startNewSession = async () => {
      try {
        await axios.post(`${API_BASE_URL}/clear`);
        setSummary(null);
        setLogs([]);
        updateInputText('');
      } catch (err) {
        console.error("Failed to clear session:", err);
      }    };

    const logsEndRef = useRef(null);
    useEffect(() => {
      logsEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [logs]);
  return (
    <div className="App">
      <header className="header">
        <div className="header-left">
          <h1>Doctor-Patient Conversation Assistant</h1>
        </div>
        {!summary && (
          <div className="header-right">
            <h2>Conversation Till now</h2>
          </div>
        )}
      </header>

      {isSummarizing ? (
        <div className="summary-section" style={{ textAlign: 'center', padding: '40px' }}>
          <h2>⏳ Generating Summary...</h2>
          <p>Please wait while the AI analyzes the consultation.</p>
        </div>
      ) : summary ? (
        <div className="summary-section">
          <h2>OPD Consultation Summary</h2>
          <p><strong>Overall Summary:</strong> {summary.overall_summary || "Not available"}</p>
          <p><strong>Symptoms:</strong> {summary.symptoms || "Not clearly identified"}</p>
          <p><strong>Duration:</strong> {summary.duration || "Not specified"}</p>
          <p><strong>Suggested Tests:</strong> {summary.suggested_tests || "None recommended"}</p>
          <button onClick={startNewSession}>Start New Consultation</button>
        </div>
      ) : (
        <div className="main-layout">
          {/* LEFT PANEL: Workspaces */}
          <div className="left-panel">
            <div className="split-screen-horizontal">
              <div className="half doctor-side">
                <h2>🩺 Doctor Workspace</h2>
                <div className="selectors-container">
                  <div className="selector-group">
                    <label>Translation Language</label>
                    <select value={docLang} onChange={(e) => setDocLang(e.target.value)}>
                      <option value="english">English</option>
                      <option value="hindi">Hindi</option>
                      <option value="telugu">Telugu</option>
                      <option value="tamil">Tamil</option>
                      <option value="kannada">Kannada</option>
                    </select>
                  </div>
                  <div className="selector-group">
                    <label>Translation Model</label>
                    <select value={docModel} onChange={(e) => setDocModel(e.target.value)}>
                      <option value="gemini-2.5-flash">Google Gemini 2.5 Flash</option>
                      <option value="sarvam-translate">Sarvam AI (Indian Languages)</option>
                      <option value="llama-3.3-70b-versatile">Groq: Llama 3.3 70b</option>
                      <option value="llama-3.1-8b-instant">Groq: Llama 3.1 8b</option>
                    </select>
                  </div>
                </div>
                <div className="input-box">
                  <button 
                    className={isRecording && speakerContextState === 'Doctor' ? 'mic-active' : ''}
                    onClick={() => toggleMic('Doctor')}>
                    {isRecording && speakerContextState === 'Doctor' ? '⏹️ Stop Recording' : '🎤 Start Dictation'}
                  </button>
                  <textarea 
                    placeholder="Doctor's transcription will appear here. You can also type manually..." 
                    value={speakerContextState === 'Doctor' ? inputText : ''} 
                    onChange={(e) => {updateInputText(e.target.value); setSpeakerContext('Doctor');}} 
                  />
                  <button onClick={() => handleSpeakText('Doctor', inputText)}>Translate & Send ➡️</button>
                </div>
              </div>

              <div className="half patient-side">
                <h2>🩼 Patient Workspace</h2>
                <div className="selectors-container">
                  <div className="selector-group">
                    <label>Translation Language</label>
                    <select value={patientLang} onChange={(e) => setPatientLang(e.target.value)}>
                      <option value="english">English</option>
                      <option value="telugu">Telugu</option>
                      <option value="hindi">Hindi</option>
                      <option value="tamil">Tamil</option>
                      <option value="kannada">Kannada</option>
                    </select>
                  </div>
                  <div className="selector-group">
                    <label>Translation Model</label>
                    <select value={patientModel} onChange={(e) => setPatientModel(e.target.value)}>
                      <option value="gemini-2.5-flash">Google Gemini 2.5 Flash</option>
                      <option value="sarvam-translate">Sarvam AI (Indian Languages)</option>
                      <option value="llama-3.3-70b-versatile">Groq: Llama 3.3 70b</option>
                      <option value="llama-3.1-8b-instant">Groq: Llama 3.1 8b</option>
                    </select>
                  </div>
                </div>
                <div className="input-box">
                   <button 
                    className={isRecording && speakerContextState === 'Patient' ? 'mic-active' : ''}
                    onClick={() => toggleMic('Patient')}>
                    {isRecording && speakerContextState === 'Patient' ? '⏹️ Stop Recording' : '🎤 Start Dictation'}
                   </button>
                   <textarea 
                    placeholder="Patient's transcription will appear here. You can also type manually..." 
                    value={speakerContextState === 'Patient' ? inputText : ''} 
                    onChange={(e) => {updateInputText(e.target.value); setSpeakerContext('Patient');}} 
                   />
                   <button onClick={() => handleSpeakText('Patient', inputText)}>Translate & Send ➡️</button>
                </div>
              </div>
            </div>
            <div className="controls">
               <div className="selector-group" style={{ display: 'inline-block', marginRight: '10px' }}>
                 <label>Summary Model: </label>
                 <select value={summaryModel} onChange={(e) => setSummaryModel(e.target.value)}>
                   <option value="llama-3.3-70b-versatile">Groq: Llama 3.3 70b</option>
                   <option value="llama-3.1-8b-instant">Groq: Llama 3.1 8b</option>
                   <option value="gemini-2.5-flash">Google Gemini 2.5 Flash</option>
                 </select>
               </div>
               <button className="end-session" onClick={endSession}>📝 End Session & Generate Summary</button>
            </div>
          </div>
          
          {/* RIGHT PANEL: Chat Logs */}
          <div className="right-panel">
            <div className="logs">
              {logs.length === 0 && <p style={{textAlign: "center", color: "#888", marginTop: "20px"}}>No conversation started yet. Dictate on the left!</p>}
              {logs.map((log, index) => (
                <div key={index} className={`log-entry ${log.speaker}`}>
                  <strong>{log.speaker} said:</strong> {log.original} 
                  <br/>
                  <em>↳ {log.translated}</em>
                  <button className="play-audio" onClick={() => playTTS(log.translated, log.speaker === 'Doctor' ? patientLang : docLang)}>🔊 Play Audio</button>
                </div>
              ))}
              <div ref={logsEndRef} />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
