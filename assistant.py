"""
My Voice Assistant (free version)
You talk -> Google Gemini (free tier) listens and answers -> a free Microsoft
British voice speaks the answer.
Start it by double-clicking START.bat (not this file).
"""

import asyncio
import base64
import io
import json
import os
import re
import sys
import tempfile

try:
    import edge_tts
    import numpy as np
    import requests
    import sounddevice as sd
    import soundfile as sf
    from openai import OpenAI
except ImportError:
    print("Some parts are missing. Please start the assistant with START.bat.")
    input("Press Enter to close...")
    sys.exit(1)

HERE = os.path.dirname(os.path.abspath(__file__))
SETTINGS_FILE = os.path.join(HERE, "settings.json")

# ---------------------------------------------------------------------------
# Things you can change (open this file in Notepad, edit, save):
#
# VOICE: free Microsoft voices. Good British male options:
#   "en-GB-RyanNeural"   (default, calm and clear)
#   "en-GB-ThomasNeural" (a little deeper)
#   "en-GB-OliverNeural"
VOICE = "en-GB-RyanNeural"
SPEED = "-5%"   # "-10%" is slower, "+10%" is faster

PERSONALITY = """You are a calm, highly capable AI assistant with a refined British manner
and a dry, understated wit. Address the user as "sir". Keep every reply short
(one to three sentences) because it will be spoken aloud. Never use lists,
bullet points, emojis or special formatting."""
# ---------------------------------------------------------------------------

FISH_MODEL = "s2.1-pro-free"   # Fish Audio's free model (fair-use limits)
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"
MODELS = ["gemini-flash-latest", "gemini-2.5-flash", "gemini-flash-lite-latest"]
SAMPLE_RATE = 16000

TURN_INSTRUCTION = """The attached audio is what the user just said to you.
Reply ONLY with JSON in exactly this form, nothing else:
{"heard": "<exactly what the user said>", "reply": "<your spoken reply>"}
If the audio is silent or unclear, use "" for heard and politely ask them to repeat in reply."""


def ask(question):
    answer = ""
    while not answer:
        answer = input(question).strip()
    return answer


def load_settings():
    s = {}
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            s = json.load(f)
    if s.get("gemini_key") and "fish_key" in s:
        return s

    print("=" * 60)
    print(" Setup (you only do this once)")
    print(" Tip: to paste, right-click inside this window.")
    print("=" * 60)
    if not s.get("gemini_key"):
        s["gemini_key"] = ask("\nPaste your free Gemini API key, then press Enter:\n> ")
    s["fish_key"] = input("\nPaste your Fish Audio API key, then press Enter.\n"
                          "(No Fish voice? Just press Enter to skip.)\n> ").strip()
    s["voice_id"] = ""
    if s["fish_key"]:
        s["voice_id"] = ask("\nPaste the Fish Audio voice model ID, then press Enter:\n> ")
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(s, f, indent=2)
    print("\nSaved! Next time it will start straight away.\n")
    return s


def record():
    """Records from the microphone between two Enter presses. Returns WAV bytes, 'quit' or None."""
    typed = input("\nPress Enter, then speak.  (Type q and press Enter to quit)  ").strip().lower()
    if typed == "q":
        return "quit"

    frames = []

    def on_audio(indata, frame_count, time_info, status):
        frames.append(indata.copy())

    try:
        with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="int16", callback=on_audio):
            input("  Listening... press Enter when you have finished speaking.")
    except Exception:
        print("  I couldn't use your microphone. Check it is plugged in and allowed in")
        print("  Windows Settings > Privacy & security > Microphone.")
        return None

    if not frames:
        return None
    audio = np.concatenate(frames)
    if len(audio) < SAMPLE_RATE * 0.3:
        print("  That was too short. Try again.")
        return None
    buf = io.BytesIO()
    sf.write(buf, audio, SAMPLE_RATE, format="WAV")
    return buf.getvalue()


def think(client, history, wav_bytes, s):
    audio_b64 = base64.b64encode(wav_bytes).decode("ascii")
    messages = history + [{
        "role": "user",
        "content": [
            {"type": "text", "text": TURN_INSTRUCTION},
            {"type": "input_audio", "input_audio": {"data": audio_b64, "format": "wav"}},
        ],
    }]
    models = [s["model"]] if s.get("model") else MODELS
    last_error = None
    for m in models:
        try:
            r = client.chat.completions.create(model=m, messages=messages)
            s["model"] = m
            return parse(r.choices[0].message.content or "")
        except Exception as e:
            last_error = e
            if is_key_or_quota_problem(e):
                break
    raise last_error


def parse(text):
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group(0))
            return str(data.get("heard", "")).strip(), str(data.get("reply", "")).strip()
        except Exception:
            pass
    return "", text.strip()


def speak_fish(text, s):
    """Speaks with the Fish Audio voice (free model). Returns True if it worked."""
    r = requests.post(
        "https://api.fish.audio/v1/tts",
        headers={
            "Authorization": f"Bearer {s['fish_key']}",
            "Content-Type": "application/json",
            "model": FISH_MODEL,
        },
        json={"text": text, "reference_id": s["voice_id"], "format": "wav"},
        timeout=90,
    )
    if r.status_code != 200:
        if r.status_code == 401:
            reason = "your Fish Audio key is wrong (delete settings.json and start again)"
        elif r.status_code in (402, 429):
            reason = "the free Fish Audio limit has been reached for now"
        else:
            reason = f"Fish Audio problem {r.status_code}: {r.text[:150]}"
        print(f"  (Switching to the backup voice: {reason}.)")
        return False
    data, rate = sf.read(io.BytesIO(r.content))
    sd.play(data, rate)
    sd.wait()
    return True


def speak(text, s, state):
    if s.get("fish_key") and s.get("voice_id") and state.get("fish_ok", True):
        try:
            if speak_fish(text, s):
                return
        except Exception as e:
            print(f"  (Switching to the backup voice: {str(e)[:150]})")
        state["fish_ok"] = False
    speak_edge(text)


def speak_edge(text):
    path = os.path.join(tempfile.gettempdir(), "assistant_reply.mp3")

    async def make():
        await edge_tts.Communicate(text, VOICE, rate=SPEED).save(path)

    asyncio.run(make())
    data, rate = sf.read(path)
    sd.play(data, rate)
    sd.wait()


def is_key_or_quota_problem(e):
    t = str(e).lower()
    return any(x in t for x in ("401", "403", "api key", "api_key", "429", "quota", "resource_exhausted"))


def explain_error(e):
    t = str(e).lower()
    if "429" in t or "quota" in t or "resource_exhausted" in t:
        print("  (Gemini says you've hit the free limit for now. Wait a minute and try again,")
        print("   or try again tomorrow if you've used it a lot today.)")
    elif "401" in t or "403" in t or "api key" in t or "api_key" in t:
        print("  (Gemini says your API key is wrong. Delete settings.json and start again.)")
    else:
        print(f"  (Problem talking to Gemini: {str(e)[:250]})")


def main():
    s = load_settings()
    client = OpenAI(api_key=s["gemini_key"], base_url=GEMINI_URL)
    history = [{"role": "system", "content": PERSONALITY}]
    state = {}

    if s.get("fish_key"):
        print("\nAssistant is ready (using your Fish Audio voice).")
    else:
        print("\nAssistant is ready.")
    while True:
        wav = record()
        if wav == "quit":
            print("Goodbye.")
            break
        if not wav:
            continue

        print("  Thinking...")
        try:
            heard, reply = think(client, history, wav, s)
        except Exception as e:
            explain_error(e)
            continue

        if heard:
            print(f"\nYou: {heard}")
            history.append({"role": "user", "content": heard})
            history.append({"role": "assistant", "content": reply})
            history[:] = history[:1] + history[-20:]  # keep the chat short
        if not reply:
            print("  I didn't catch that. Try again.")
            continue
        print(f"Assistant: {reply}")

        try:
            speak(reply, s, state)
        except Exception as e:
            print(f"  (Couldn't play the voice - check your internet connection: {str(e)[:150]})")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nGoodbye.")
