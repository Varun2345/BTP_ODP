import os
import re
from gtts import gTTS
from pydub import AudioSegment

output_dir = "audio_clips/simulated_conversation"
os.makedirs(output_dir, exist_ok=True)

# Format: "Text [PAUSE:seconds] Text"
# Patient has lots of ums, uhs, and long pauses
# Doctor is mostly clear, with very few/short pauses.
conversation = [
    {
        "filename": "doctor_1.mp3",
        "text": "Good morning. I was looking over your intake forms, and it looks like you're coming in for some back issues. [PAUSE:1.0] Could you tell me a little bit more about what seems to be the main problem today?",
        "lang": "en",
        "tld": "com"
    },
    {
        "filename": "patient_1.mp3",
        "text": "Yeah, well, uh [PAUSE:1.5] I've been having this, um, really bad, kind of throbbing pain in my lower back. [PAUSE:3.0] It started a few days ago... and honestly, uh, um, it's just been getting progressively worse, especially in the mornings.",
        "lang": "en",
        "tld": "co.uk"
    },
    {
        "filename": "doctor_2.mp3",
        "text": "I see, that sounds quite uncomfortable. [PAUSE:1.0] How exactly did this start? Were you doing any heavy lifting or sitting in an awkward position for an extended period of time?",
        "lang": "en",
        "tld": "com"
    },
    {
        "filename": "patient_2.mp3",
        "text": "Ah, basically [PAUSE:2.0] I think it started since last Tuesday when I was helping a friend move a couch. [PAUSE:6.0] It's, like, really sharp when I try to bend over, and sometimes the pain, um... [PAUSE:2.5] shoots down my left leg when I walk.",
        "lang": "en",
        "tld": "co.uk"
    },
    {
        "filename": "doctor_3.mp3",
        "text": "Okay, that shooting pain might indicate some nerve compression. [PAUSE:1.5] We should get an X-ray just to be safe. Depending on what that shows, we might need to schedule an MRI later this week.",
        "lang": "en",
        "tld": "com"
    }
]

print(f"Generating {len(conversation)} audio files with accurate silence gaps...")

def generate_with_pauses(text, lang, tld, output_path):
    # Split text by [PAUSE:X]
    parts = re.split(r'\[PAUSE:([\d\.]+)\]', text)
    
    final_audio = AudioSegment.empty()
    
    # parts will alternate: text, pause_duration, text, pause_duration, text
    # e.g., ["Hello", "2.0", "World"]
    for i in range(len(parts)):
        if i % 2 == 0:
            # It's text
            chunk_text = parts[i].strip()
            if chunk_text:
                temp_file = f"temp_{i}.mp3"
                tts = gTTS(text=chunk_text, lang=lang, tld=tld, slow=False)
                tts.save(temp_file)
                
                audio_chunk = AudioSegment.from_mp3(temp_file)
                final_audio += audio_chunk
                os.remove(temp_file)
        else:
            # It's a pause duration
            pause_sec = float(parts[i])
            silence = AudioSegment.silent(duration=int(pause_sec * 1000)) # ms
            final_audio += silence
            
    final_audio.export(output_path, format="mp3")

for line in conversation:
    filepath = os.path.join(output_dir, line["filename"])
    print(f"Generating {line['filename']}...")
    generate_with_pauses(line["text"], line["lang"], line["tld"], filepath)

print(f"\n✅ All accurate-pause audio files have been saved to '{output_dir}'!")
