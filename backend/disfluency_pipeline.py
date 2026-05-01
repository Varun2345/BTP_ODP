import os
import json
from faster_whisper import WhisperModel


# --- CONFIGURATION ---
MODEL_SIZE = "small" # Start with small for fast execution. Use "large-v3" for best accuracy.
SHORT_PAUSE_THRESHOLD = 0.5 # Reverted to stable value
LONG_PAUSE_THRESHOLD = 3.0  # seconds
VERY_LONG_PAUSE_THRESHOLD = 5.0 # seconds
# Silences > 5s show as [Pause: Xs]

# ==========================================
# SINGLETON MODEL LOADING (Speed Optimization)
# ==========================================
print(f"⌛ Loading Whisper model ({MODEL_SIZE})...")
MODEL = WhisperModel(MODEL_SIZE, device="cpu", compute_type="int8")
print("✅ Whisper model loaded and ready.")

def run_pipeline(audio_path: str):
    print(f"🚀 Starting Pipeline on audio: {audio_path}")
    
    # ==========================================
    # STAGE 1: ASR (Speech -> Text + Timing)
    # ==========================================
    print("\n[STAGE 1] Transcribing with Singleton Model...")
    
    # MAGIC TRICK: This prompt forces Whisper to keep filler words instead of deleting them.
    asr_prompt = "Uhm, well, uh, basically, I mean, the patient, um, said... like... they were tired, ah."
    
    # Transcribe the audio
    segments, _ = MODEL.transcribe(
        audio_path, 
        word_timestamps=True,     # Critical for getting exactly when the word ended
        initial_prompt=asr_prompt,  
        condition_on_previous_text=False,
        vad_filter=False,          # Capture silence as requested
        no_speech_threshold=0.6,   # Security guard against static/ambient noise
        suppress_blank=False,      # Allow the model to output blank/hesitation tokens
        suppress_tokens=None,      # Remove all built-in token suppressions to keep fillers
        temperature=[0.0, 0.2, 0.4] # Try literal first, then loosen up for less common tokens
    )
    
    # Flatten the generator into a list of word objects with HALLUCINATION GUARD
    raw_words = []
    filler_words = ["um", "uh", "uhm", "err", "ah", "basically", "like", "actually", "mean"]
    
    # regex for allowed characters: English, Hindi, Telugu, Tamil, Kannada + basic punctuation
    # \u0000-\u007F: Basic Latin
    # \u0900-\u097F: Devanagari
    # \u0C00-\u0C7F: Telugu
    # \u0B80-\u0BFF: Tamil
    # \u0C80-\u0CFF: Kannada
    import re
    ALLOWED_CHARS_REGEX = re.compile(r'^[\u0000-\u007F\u0900-\u097F\u0C00-\u0C7F\u0B80-\u0BFF\u0C80-\u0CFF\s.,?!\'\"\[\]:()\-]+$')

    for segment in segments:
        # pyre-ignore
        words = segment.words
        for word in words:
            clean_word = word.word.strip().lower()
            original_word = word.word.strip()
            
            # 1. Catch noise hallucinations (like ʰʰʰ or ʃʃʃ) using regex
            is_legal_chars = bool(ALLOWED_CHARS_REGEX.match(original_word))
            
            # 2. Filler-specific logic: We allow these even at very low probability
            # USER REQUEST: Set min_prob to 0.0 for now to see EVERYTHING
            is_filler = clean_word in filler_words or any(f in clean_word for f in ["um", "uh", "ah"])
            
            # ZERO threshold as per user request to ensure nothing is ignored
            min_prob = 0.0
            
            if not is_legal_chars or word.probability < min_prob:
                continue
            
            # Tag fillers for LLM
            if is_filler:
                original_word = f"[filler:{original_word}]"
                
            raw_words.append({
                "word": original_word,
                "start": round(word.start, 2),
                "end": round(word.end, 2),
                "prob": round(word.probability, 2)
            })

    if not raw_words:
        print("❌ No speech detected.")
        return None

    # ==========================================
    # STAGE 2: Pause Structuring
    # ==========================================
    print("\n[STAGE 2] Calculating Timings...")
    structured_tokens = []
    
    for i in range(len(raw_words)):
        current_word = raw_words[i]
        
        # Calculate exactly how much silence is between this word and the next
        pause_after = 0.0
        if i < len(raw_words) - 1:
            next_word = raw_words[i + 1]
            # Cast to float explicitly for Pyre2
            diff = float(next_word["start"]) - float(current_word["end"])
            pause_after = max(0.0, round(diff, 2))
            
        structured_tokens.append({
            "text": current_word["word"],
            "start": float(current_word["start"]),
            "end": float(current_word["end"]),
            "pause_after": float(pause_after)
        })

    # ==========================================
    # STAGE 3: Text Reconstruction (ADVANCED PAUSES)
    # ==========================================
    print("\n[STAGE 3] Reconstructing Expressive Text...")
    final_text_parts = []
    
    for token in structured_tokens:
        text = token["text"]
        pause = token["pause_after"]
        
        # Determine punctuation/tags based on physical silence
        pause_val = float(pause)
        if pause_val >= VERY_LONG_PAUSE_THRESHOLD:
             # Significant duration -> Pause tag
            final_text_parts.append(f"{text} [Pause: {int(pause_val)}s]")
        elif pause_val >= LONG_PAUSE_THRESHOLD:
            # 3 to 5 seconds -> 5 dots
            final_text_parts.append(f"{text}.....")
        elif pause_val >= SHORT_PAUSE_THRESHOLD:
            # 0.5 to 3 seconds -> 3 dots
            final_text_parts.append(f"{text}...")
        else:
            final_text_parts.append(text)
            
    reconstructed_text = " ".join(final_text_parts)
    print(f"\n📃 Reconstructed Text:\n> {reconstructed_text}")
    
    # ==========================================
    # FINAL PAYLOAD RETURN
    # ==========================================
    payload = {
        "tokens": structured_tokens,
        "final_text": reconstructed_text
    }
    
    return payload

if __name__ == "__main__":
    import sys
    print("Welcome to the Disfluency-Preserving ASR Pipeline!")
    
    if len(sys.argv) > 1:
        test_audio = sys.argv[1]
        if os.path.exists(test_audio):
            result = run_pipeline(test_audio)
            print("\nFinal Output Dictionary:")
            import pprint
            pprint.pprint(result)
        else:
            print(f"❌ Error: The file '{test_audio}' was not found.")
    else:
        print("\nTo test this, provide a path to a .wav or .mp3 file:")
        print("Usage: python disfluency_pipeline.py <path_to_audio_file>")
