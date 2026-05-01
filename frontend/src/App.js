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
  const [consultantMode, setConsultantMode] = useState('scribe'); 
  const [doctorInput, setDoctorInput] = useState('');
  const [patientInput, setPatientInput] = useState('');
  const [transcriptionModel, setTranscriptionModel] = useState('whisper');
  const doctorInputRef = useRef('');
  const patientInputRef = useRef('');
  const speakerContextRef = useRef('Doctor');
  const [logs, setLogs] = useState([]);
  const [summary, setSummary] = useState(null);
  const [isRecording, setIsRecording] = useState(false);
  const [isSummarizing, setIsSummarizing] = useState(false);
  const [showSummary, setShowSummary] = useState(false);
  const [speakerContextState, setSpeakerContextState] = useState('Doctor');
  const [leftWidth, setLeftWidth] = useState(66.666); // Percentage
  const [expandedSection, setExpandedSection] = useState(null); // 'doctor', 'patient', 'logs'
  const isResizing = useRef(false);
  const recordingStartTimeRef = useRef(null);

  const cleanTranscription = (text) => {
    // Strips [filler:word] -> word and converts [Pause: Xs] -> (Paused for X seconds)
    return text
      .replace(/\[filler:(.*?)\]/g, '$1')
      .replace(/\[Pause: (\d+)s\]/g, '($1 second pause)')
      .replace(/\.{3,}/g, '...');
  };

  const setSpeakerContext = (ctx) => {
    setSpeakerContextState(ctx);
    speakerContextRef.current = ctx;
  };

  const updateInputText = (text, speaker) => {
    if (speaker === 'Doctor') {
      setDoctorInput(text);
      doctorInputRef.current = text;
    } else {
      setPatientInput(text);
      patientInputRef.current = text;
    }
  };

  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
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

  const toggleMic = async (speaker) => {
    // If the mic is toggled off manually
    if (isRecordingRef.current && speakerContextState === speaker) {
      isRecordingRef.current = false;
      setIsRecording(false);
      if (mediaRecorderRef.current && mediaRecorderRef.current.state === "recording") {
         mediaRecorderRef.current.stop();
      }
      return;
    }

    // Stop current recording before starting a new speaker context
    if (isRecordingRef.current) {
        if (mediaRecorderRef.current && mediaRecorderRef.current.state === "recording") {
           mediaRecorderRef.current.stop();
        }
    }

    setSpeakerContext(speaker);
    updateInputText('Listening... (Click Stop to Process)', speaker);
    setIsRecording(true);
    isRecordingRef.current = true;

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      recordingStartTimeRef.current = new Date();
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;
      audioChunksRef.current = [];

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = async () => {
        updateInputText('Processing exactly what you said with Whisper...', speakerContextRef.current);
        const endTime = new Date();
        const formatTime = (d) => d ? d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }) : '';
        const timeStr = `${formatTime(recordingStartTimeRef.current)} - ${formatTime(endTime)}`;
        
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/mp3' });
        const formData = new FormData();
        formData.append('audio', audioBlob, `recording_${Date.now()}.mp3`);
        
        try {
           const res = await axios.post(`${API_BASE_URL}/transcribe`, formData, {
              headers: { 'Content-Type': 'multipart/form-data' }
           });
            if (res.data && res.data.transcription) {
               const rawText = res.data.transcription;
               const cleanText = cleanTranscription(rawText);
               const currentSpeaker = speakerContextRef.current;
               
               // 1. Update Workspace (Clears processing message)
               const currentVal = currentSpeaker === 'Doctor' ? doctorInputRef.current : patientInputRef.current;
               const finalTranscription = currentVal.replace('Processing exactly what you said with Whisper...', '') + cleanText;
               updateInputText(finalTranscription, currentSpeaker);

               // 2. AUTO-LOG: Push to central conversation history immediately
               if (finalTranscription.trim()) {
                 try {
                   const logRes = await axios.post(`${API_BASE_URL}/log`, {
                     speaker: currentSpeaker,
                     text: finalTranscription,
                     source_lang: 'english',
                     target_lang: 'english'
                   });
                   if (logRes.data.status === 'success') {
                     setLogs(prev => [...prev, {
                       speaker: currentSpeaker,
                       original: finalTranscription,
                       translated: finalTranscription,
                       timestamp: timeStr
                     }]);
                     // Optionally clear input after auto-logging if session feels "live"
                     // Text is preserved in workspace as requested

                   }
                 } catch (logErr) {
                   console.error("Auto-log failed:", logErr);
                 }
               }
            } else {
               updateInputText('', speakerContextRef.current);
               alert("No speech detected or transcription failed.");
           }
        } catch(e) {
           console.error(e);
           updateInputText('', speakerContextRef.current);
           alert("Failed to reach transcription server.");
        }
        
        // Stop stream tracks to free up the microphone
        stream.getTracks().forEach(track => track.stop());
      };

      mediaRecorder.start();
    } catch(err) {
      console.error(err);
      alert("Microphone permission denied or not supported.");
      setIsRecording(false);
      isRecordingRef.current = false;
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

      const timeStr = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });

      setLogs(prev => {
        const lastIdx = [...prev].reverse().findIndex(l => l.speaker === speaker);
        const idx = lastIdx === -1 ? -1 : prev.length - 1 - lastIdx;
        
        if (idx !== -1 && prev[idx].original === res.data.original) {
          const newLogs = [...prev];
          newLogs[idx] = { ...newLogs[idx], translated: res.data.translated, timestamp: timeStr };
          return newLogs;
        } else {
          return [...prev, {
            speaker: speaker,
            original: res.data.original,
            translated: res.data.translated,
            timestamp: timeStr
          }];
        }
      });
      
      updateInputText('', speaker);
      playTTS(res.data.translated, targetLang);
    } catch (err) {
      console.error("Translation ERROR:", err);
      const errorMsg = err.response?.data?.error || err.message;
      alert(`Translation failed: ${errorMsg}`);
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
       if (mediaRecorderRef.current && mediaRecorderRef.current.state === "recording") {
          mediaRecorderRef.current.stop();
       }
       setIsRecording(false);
    }
    
      setIsSummarizing(true);
      try {
          const res = await axios.get(`${API_BASE_URL}/summarize?selected_model=${summaryModel}&consultant_mode=${consultantMode}`);
          if (res.data && res.data.subjective) {
            setSummary(res.data);
            setShowSummary(true);
          } else if (res.data && res.data.error) {
            alert("Summarization stopped: " + res.data.error);
          } else {
            alert("Summarization failed. Please check your internet connection or try again.");
          }
      } catch (err) {
        console.error("Summarization CRASH:", err);
        const detail = err.response?.data?.error || err.message;
        alert(`Summarization failed: ${detail}`);
      } finally {
        setIsSummarizing(false);
      }
    };

    const downloadSummary = () => {
      if (!summary) return;
      const content = `
OPD Clinical Consultation Note (SOAP)
Mode: ${consultantMode === 'scribe' ? 'Strict Scribe' : 'Expert Assistant'}
Model: ${summaryModel}
Date: ${new Date().toLocaleString()}

SUBJECTIVE (S):
${summary.subjective}

OBJECTIVE (O):
${summary.objective}

ASSESSMENT (A):
${summary.assessment}

PLAN (P):
${summary.plan}

${consultantMode === 'scribe' ? 'Speech Behavior' : 'Clinical Confidence'}:
${consultantMode === 'scribe' ? (summary.metadata?.observation || summary.metadata?.demeanor_note || 'N/A') : (summary.metadata?.clinical_confidence || 'N/A')}

Generated by OPD Consultation Assistant
      `.trim();
      
      const element = document.createElement("a");
      const file = new Blob([content], {type: 'text/plain'});
      element.href = URL.createObjectURL(file);
      element.download = `SOAP_Note_${new Date().getTime()}.txt`;
      document.body.appendChild(element);
      element.click();
      document.body.removeChild(element);
    };

    const startNewSession = async () => {
      try {
        await axios.post(`${API_BASE_URL}/clear`);
        setSummary(null);
        setLogs([]);
        setDoctorInput('');
        setPatientInput('');
      } catch (err) {
        console.error("Failed to clear session:", err);
      }    };

    const logsEndRef = useRef(null);
    useEffect(() => {
      logsEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [logs]);

    const startResizing = (e) => {
      isResizing.current = true;
      document.addEventListener('mousemove', handleResize);
      document.addEventListener('mouseup', stopResizing);
    };

    const handleResize = (e) => {
      if (!isResizing.current) return;
      const newWidth = (e.clientX / window.innerWidth) * 100;
      if (newWidth > 20 && newWidth < 80) {
        setLeftWidth(newWidth);
      }
    };

    const stopResizing = () => {
      isResizing.current = false;
      document.removeEventListener('mousemove', handleResize);
      document.removeEventListener('mouseup', stopResizing);
    };
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
          <h2>Generating Summary...</h2>
          <p>Please wait while the AI analyzes the consultation.</p>
        </div>
      ) : showSummary && summary ? (
        <div className="summary-section">
          <h2>OPD Clinical Consultation Note (SOAP)</h2>
          
          <div className="soap-container">
            <div className="soap-card subjective">
              <h3>Subjective (S)</h3>
              <p>{summary.subjective || "No subjective data captured."}</p>
            </div>
            
            <div className="soap-card objective">
              <h3>Objective (O)</h3>
              <p>{summary.objective || "Not recorded."}</p>
            </div>
            
            <div className="soap-card assessment">
              <h3>Assessment (A)</h3>
              <p>{summary.assessment || "Clinical impression pending."}</p>
            </div>
            
            <div className="soap-card plan">
              <h3>Plan (P)</h3>
              <p>{summary.plan || "Follow-up required."}</p>
            </div>
          </div>

            <div className="summary-metadata-footer">
              <div className="metadata-card disfluency">
                <strong>Speech Disfluency Level</strong>
                <div className={`disfluency-badge ${summary.metadata?.disfluency_level?.toLowerCase() || 'not-assigned'}`}>
                  {summary.metadata?.disfluency_level || "N/A"}
                </div>
              </div>
              <div className="metadata-card demeanor">
                <strong>{consultantMode === 'scribe' ? 'Speech Behavior Overview' : 'Clinical Confidence Score'}</strong>
                <p>
                  {consultantMode === 'scribe' 
                    ? (summary.metadata?.observation || summary.metadata?.demeanor_note || "No specific disfluencies recorded.")
                    : `AI Certainty: ${summary.metadata?.clinical_confidence || 'N/A'}`
                  }
                </p>
              </div>
            </div>

            {consultantMode === 'assistant' && (
              <div className="safety-disclaimer">
                ⚠️ <strong>Safety Note:</strong> AI suggestions must be verified by a medical professional before clinical implementation.
              </div>
            )}

            <div className="summary-actions">
              <button className="download-btn" onClick={downloadSummary}>Download SOAP Note</button>
              <button className="go-back-btn" onClick={() => setShowSummary(false)}>Go Back to Conversation</button>
              <button className="new-consultation-btn danger" onClick={startNewSession}>Start New Consultation</button>
            </div>
        </div>
      ) : (
        <div className="main-layout" onMouseMove={handleResize}>
          {/* LEFT PANEL: Workspaces */}
          <div className={`left-panel ${expandedSection === 'logs' ? 'hidden' : expandedSection ? 'full' : ''}`} style={expandedSection ? {} : { flex: `0 0 ${leftWidth}%`, maxWidth: `${leftWidth}%` }}>
            <div className="split-screen-horizontal">
              <div className={`half doctor-side ${expandedSection === 'doctor' ? 'full' : expandedSection ? 'hidden' : ''}`}>
                <div className="section-header">
                  <h2>Doctor Workspace</h2>
                  <button className="expand-btn" onClick={() => setExpandedSection(expandedSection === 'doctor' ? null : 'doctor')}>
                    {expandedSection === 'doctor' ? 'Collapse' : '↔'}
                  </button>
                </div>
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
                  <div className="stt-controls">
                    <button 
                      className={`dictation-btn ${isRecording && speakerContextState === 'Doctor' ? 'mic-active' : ''}`}
                      onClick={() => toggleMic('Doctor')}>
                      {isRecording && speakerContextState === 'Doctor' ? 'Stop' : 'Start Dictation'}
                    </button>
                    <select 
                      className="stt-model-selector"
                      value={transcriptionModel} 
                      onChange={(e) => setTranscriptionModel(e.target.value)}>
                      <option value="whisper">Faster-Whisper (Local)</option>
                    </select>
                  </div>
                  <textarea 
                    placeholder="Doctor's transcription will appear here. You can also type manually..." 
                    value={doctorInput} 
                    onChange={(e) => updateInputText(e.target.value, 'Doctor')} 
                  />
                  <button onClick={() => handleSpeakText('Doctor', doctorInput)}>Translate & Send</button>
                </div>
              </div>

              <div className={`half patient-side ${expandedSection === 'patient' ? 'full' : expandedSection ? 'hidden' : ''}`}>
                <div className="section-header">
                  <h2>Patient Workspace</h2>
                  <button className="expand-btn" onClick={() => setExpandedSection(expandedSection === 'patient' ? null : 'patient')}>
                    {expandedSection === 'patient' ? 'Collapse' : '↔'}
                  </button>
                </div>
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
                    <div className="stt-controls">
                      <button 
                        className={`dictation-btn ${isRecording && speakerContextState === 'Patient' ? 'mic-active' : ''}`}
                        onClick={() => toggleMic('Patient')}>
                        {isRecording && speakerContextState === 'Patient' ? 'Stop' : 'Start Dictation'}
                      </button>
                      <select 
                        className="stt-model-selector"
                        value={transcriptionModel} 
                        onChange={(e) => setTranscriptionModel(e.target.value)}>
                        <option value="whisper">Faster-Whisper (Local)</option>
                      </select>
                    </div>
                   <textarea 
                    placeholder="Patient's transcription will appear here. You can also type manually..." 
                    value={patientInput} 
                    onChange={(e) => updateInputText(e.target.value, 'Patient')} 
                   />
                   <button onClick={() => handleSpeakText('Patient', patientInput)}>Translate & Send</button>
                </div>
              </div>
            </div>
            <div className="controls">
                <div className="selector-group" style={{ display: 'inline-block', marginRight: '10px' }}>
                  <label>Mode: </label>
                  <div className="mode-toggle-group">
                    <button 
                      className={`mode-btn ${consultantMode === 'scribe' ? 'active' : ''}`}
                      onClick={() => setConsultantMode('scribe')}
                    >
                      Strict Scribe
                    </button>
                    <button 
                      className={`mode-btn ${consultantMode === 'assistant' ? 'active' : ''}`}
                      onClick={() => setConsultantMode('assistant')}
                    >
                      Expert Assistant
                    </button>
                  </div>
                </div>
                <div className="selector-group" style={{ display: 'inline-block', marginRight: '20px' }}>
                  <label>Summary Model: </label>
                  <select value={summaryModel} onChange={(e) => setSummaryModel(e.target.value)}>
                    <option value="llama-3.3-70b-versatile">Groq: Llama 3.3 70b</option>
                    <option value="llama-3.1-8b-instant">Groq: Llama 3.1 8b</option>
                    <option value="gemini-2.5-flash">Google Gemini 2.5 Flash</option>
                  </select>
                </div>
                <button className="end-session" onClick={endSession}>
                  {summary ? 'Update SOAP Summary' : 'Generate SOAP Summary'}
                </button>
                {summary && !showSummary && (
                  <button className="view-summary-btn" onClick={() => setShowSummary(true)} style={{ marginLeft: '10px' }}>
                    View Last Summary
                  </button>
                )}
            </div>
          </div>
          
          {/* DRAGGABLE DIVIDER */}
          <div className="resizer-v" onMouseDown={startResizing} />

          {/* RIGHT PANEL: Chat Logs */}
          <div className={`right-panel ${expandedSection === 'logs' ? 'full' : expandedSection ? 'hidden' : ''}`} style={expandedSection ? {} : { flex: `0 0 ${100 - leftWidth}%`, maxWidth: `${100 - leftWidth}%` }}>
            <div className="section-header">
              <h2>Conversation History</h2>
              <button className="expand-btn" onClick={() => setExpandedSection(expandedSection === 'logs' ? null : 'logs')}>
                {expandedSection === 'logs' ? 'Collapse' : '↔'}
              </button>
            </div>
            <div className="logs">
              {logs.length === 0 && <p style={{textAlign: "center", color: "#888", marginTop: "20px"}}>No conversation started yet. Dictate on the left!</p>}
              {logs.map((log, index) => {
                const isTranslated = log.translated && 
                  cleanTranscription(log.original).toLowerCase().replace(/[.,?!]/g, '').trim() !== 
                  log.translated.toLowerCase().replace(/[.,?!]/g, '').trim();
                return (
                  <div key={index} className={`log-entry ${log.speaker}`}>
                    <strong>{log.speaker} said:</strong> {cleanTranscription(log.original)} 
                    {isTranslated && (
                      <>
                        <br/>
                        <em>↳ {log.translated}</em>
                      </>
                    )}
                    <div className="audio-actions">
                      <button className="play-audio" onClick={() => playTTS(log.translated || log.original, log.speaker === 'Doctor' ? patientLang : docLang)}>Play Audio</button>
                      <button className="stop-audio" onClick={() => window.speechSynthesis.cancel()}>Stop</button>
                    </div>
                    <div className="log-timestamp">{log.timestamp}</div>
                  </div>
                );
              })}
              <div ref={logsEndRef} />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
