# My Voice Assistant

A simple, free voice assistant for Windows. You speak, it understands you, thinks of a reply, and answers out loud in a calm British voice.

## How it works

1. **You talk:** your microphone records what you say.
2. **It thinks:** Google Gemini (free tier) works out what you said and writes a short reply.
3. **It speaks:** the reply is read out using a Fish Audio voice of your choice, with a free Microsoft voice (`en-GB-RyanNeural`) as a backup.

## What you need

- A Windows PC with a microphone and speakers
- [Python](https://www.python.org/downloads/) (tick **"Add python.exe to PATH"** when installing)
- A free Gemini API key from [Google AI Studio](https://aistudio.google.com/)
- *(Optional)* A Fish Audio API key and voice model ID from [fish.audio](https://fish.audio/)

## How to run it

1. Download this project (green **Code** button → **Download ZIP**) and extract it.
2. Double-click **`START.bat`**.
3. The first time, paste your keys when asked. They're saved in `settings.json` on your own computer.
4. Press **Enter**, speak, then press **Enter** again. Type **`q`** to quit.

## Customise it

Open `assistant.py` in Notepad and edit the section marked **"Things you can change"**:

- `VOICE` sets the backup voice (e.g. `en-GB-ThomasNeural`)
- `SPEED` sets how fast it talks
- `PERSONALITY` sets how the assistant behaves and speaks

## Files

| File | Purpose |
|---|---|
| `START.bat` | Installs what's needed and starts the assistant |
| `assistant.py` | The assistant itself |
| `settings.json` | Your private keys. Created on first run and **never uploaded** (see `.gitignore`) |

## Privacy note

The free Gemini tier may use your conversations to improve Google's products. Don't share anything sensitive with it.
