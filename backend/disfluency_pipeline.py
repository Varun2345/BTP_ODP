import os
import json
from faster_whisper import WhisperModel


# --- CONFIGURATION ---
MODEL_SIZE = "small" # Start with small for fast execution. Use "large-v3" for best accuracy.
SHORT_PAUSE_THRESHOLD = 0.5 # seconds
LONG_PAUSE_THRESHOLD = 1.2  # seconds

def run_pipeline(audio_path: str):
    print(f"🚀 Starting Pipeline on audio: {audio_path}")
    
    # ==========================================
    # STAGE 1: ASR (Speech -> Text + Timing)
    # ==========================================
    print("\n[STAGE 1] Loading Whisper & Transcribing...")
    # Loading faster-whisper. compute_type="int8" allows it to run very fast on CPU
    model = WhisperModel(MODEL_SIZE, device="cpu", compute_type="int8")
    
    # MAGIC TRICK: This prompt forces Whisper to keep filler words instead of deleting them.
    asr_prompt = "Um, uh, basically, the patient, uh, said they were tired."
    
    # Transcribe the audio
    segments, _ = model.transcribe(
        audio_path, 
        word_timestamps=True,     # Critical for getting exactly when the word ended
        initial_prompt=asr_prompt,  
        condition_on_previous_text=False
    )
    
    # Flatten the generator into a list of word objects
    raw_words = []
    for segment in segments:
        for word in segment.words:
            raw_words.append({
                "word": word.word.strip(),
                "start": round(word.start, 2),
                "end": round(word.end, 2)
            })

    if not raw_words:
        print("❌ No speech detected.")
        return None

    # ==========================================
    # STAGE 2: Pause Structuring (NO DICTIONARY)
    # ==========================================
    print("\n[STAGE 2] Calculating Timings...")
    structured_tokens = []
    
    for i in range(len(raw_words)):
        current_word = raw_words[i]
        
        # Calculate exactly how much silence is between this word and the next
        pause_after = 0.0
        if i < len(raw_words) - 1:
            next_word = raw_words[i + 1]
            # Whisper timestamps sometimes overlap slightly, so we clamp minimum to 0.0
            pause_after = max(0.0, round(next_word["start"] - current_word["end"], 2))
            
        structured_tokens.append({
            "text": current_word["word"],
            "start": current_word["start"],
            "end": current_word["end"],
            "pause_after": pause_after
        })

    # ==========================================
    # STAGE 3: Text Reconstruction
    # ==========================================
    print("\n[STAGE 3] Reconstructing Expressive Text...")
    final_text_parts = []
    
    for token in structured_tokens:
        text = token["text"]
        pause = token["pause_after"]
        
        # Append punctuation based on the calculated physical silence duration
        if pause >= LONG_PAUSE_THRESHOLD:
            final_text_parts.append(f"{text}......")
        elif pause >= SHORT_PAUSE_THRESHOLD:
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
