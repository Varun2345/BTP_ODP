# Technical Implementation Report: OPD Consultation Assistant

This report details the technical architecture, ideology, and implementation of the key features added to the OPD Consultation Assistant.

---

## 1. Punctuations & Speech Dynamics
**Ideology**: Capturing the rhythm of speech (pauses and dots) is essential for clinical accuracy, as speech gaps often indicate pain or distress.

### Implementation:
- **Pause Detection**: `disfluency_pipeline.py` calculates gaps between word segments. 
  - **0.5s - 5.0s**: Inserts `...` (Short Pause).
  - **> 5.0s**: Inserts `[Pause: Xs]` (Significant Pause).
- **Rendering**: Frontend regex converts these into user-friendly text like `(5 second pause)`.

---

## 2. Disfluency Processing
**Ideology**: Disfluencies (fillers like "um", "uh") are behavioral data points, NOT noise code to be discarded.

### Implementation:
- **Scoring**: Calculates **Disfluency Probability** (Fillers / Total words).
- **Integration**:
  - **Scribe Mode**: Preserves fillers verbatim.
  - **Demeanor**: The LLM uses filler counts to assess patient hesitation and distress in the **Subjective** section.

---

## 3. Timestamp Auditing
**Ideology**: Accurate chronicity is vital for legal medical records and chronological auditing.

### Implementation:
- **Auditing**: Every log captures a high-res timestamp in the SQLite database.
- **Audit Trail**: The "Full Transcript" module in the summary maintains a precise chronological timeline of the session.

---

## 4. Dual-Mode Summarization
**Ideology**: Providing a switch between a "Pass-through Recorder" and a "Proactive Clinical Partner."

### Implementation:
- **Strict Scribe**: A literal record with the **Zero-Inference Rule**.
- **Expert Assistant**: Proactive analysis, suggesting assessments and exams.

---

## 5. The "Magic Prompt" Engineering
**Ideology**: The "Magic" lies in forcing the LLM to **listen to and analyze** disfluencies instead of ignoring them.

### Implementation:
- **Telemetry, Not Noise**:
  - Most AI systems discard "um" and "uh" as errors. The Magic Prompt explicitly instructs the LLM that these are **primary diagnostic telemetry** for assessing behavioral health.
- **Zero-Inference Guardrail**:
  - While the AI is forced to *consider* fillers, it is strictly forbidden from *guessing* diagnoses in Scribe mode, ensuring objectivity.
- **Proactive Intelligence (Assistant Mode)**:
  - The AI uses the context provided by disfluency markers to judge the severity of symptoms, ranking differential diagnoses more accurately based on patient distress.
- **Confidence Scoring**: 
  - The AI self-evaluates its certainty based on how clear or hesitant the session's audio context was.