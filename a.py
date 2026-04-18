# from gtts import gTTS
# from pydub import AudioSegment

# # ----------- Helper function to generate speech -----------
# def text_to_audio(text, filename):
#     tts = gTTS(text=text, lang='en')
#     tts.save(filename)
#     return AudioSegment.from_file(filename, format="mp3")

# # ----------- Create segments -----------

# segments = []

# # 1
# segments.append(text_to_audio("Um... well...", "part1.mp3"))
# segments.append(AudioSegment.silent(duration=1000))  # 1 second pause

# # 2
# segments.append(text_to_audio("I’ve been having this really bad pain in my, uh, lower back.", "part2.mp3"))

# # 3
# segments.append(text_to_audio("It’s been going on for...", "part3.mp3"))
# segments.append(AudioSegment.silent(duration=5000))  # 5 seconds pause

# # 4
# segments.append(text_to_audio("basically three weeks now.", "part4.mp3"))

# # 5
# segments.append(text_to_audio("It’s a sharp pain, you know?", "part5.mp3"))

# # 6
# segments.append(text_to_audio("Like...", "part6.mp3"))
# segments.append(AudioSegment.silent(duration=12000))  # 12 seconds pause

# # 7
# segments.append(text_to_audio("I mean, it hurts most when I sit down.", "part7.mp3"))

# # 8
# segments.append(text_to_audio("I also feel, uh, a bit of numbness in my left leg.", "part8.mp3"))

# # ----------- Combine everything -----------

# final_audio = AudioSegment.empty()

# for seg in segments:
#     final_audio += seg

# # ----------- Export final file -----------

# final_audio.export("final_output.mp3", format="mp3")

# print("✅ Audio generated: final_output.mp3")


from gtts import gTTS
from pydub import AudioSegment

# ----------- Helper function -----------
def text_to_audio(text, filename):
    tts = gTTS(text=text, lang='en')
    tts.save(filename)
    return AudioSegment.from_file(filename, format="mp3")

# =========================================================
# 🎧 CLIP 1: Doctor
# =========================================================

doctor_audio = text_to_audio(
    "I see. Have you taken any medication for it?",
    "doctor.mp3"
)

doctor_audio.export("doctor_final.mp3", format="mp3")

print("✅ Doctor audio generated: doctor_final.mp3")


# =========================================================
# 🎧 CLIP 2: Patient (with 10s silence)
# =========================================================

segments = []

# Part 1
segments.append(text_to_audio(
    "Just some, um, paracetamol.",
    "p1.mp3"
))

# Part 2
segments.append(text_to_audio(
    "But it didn't really help.",
    "p2.mp3"
))

# Part 3
segments.append(text_to_audio(
    "Oh, and...",
    "p3.mp3"
))

# 🔴 REAL SILENCE (10 seconds)
segments.append(AudioSegment.silent(duration=10000))

# Part 4
segments.append(text_to_audio(
    "I think I also had a fever yesterday.",
    "p4.mp3"
))

# Combine
patient_audio = AudioSegment.empty()
for seg in segments:
    patient_audio += seg

# Export
patient_audio.export("patient_final.mp3", format="mp3")

print("✅ Patient audio generated: patient_final.mp3")