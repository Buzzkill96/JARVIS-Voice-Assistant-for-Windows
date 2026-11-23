@echo off
title My Voice Assistant
cd /d "%~dp0"

python --version >nul 2>nul
if errorlevel 1 (
  echo.
  echo  Python is not installed yet.
  echo  Please install it from python.org first, and tick "Add python.exe to PATH".
  echo.
  pause
  exit /b
)

echo Getting things ready... (the first time can take a minute or two)
python -m pip install --quiet --disable-pip-version-check --upgrade openai requests edge-tts sounddevice soundfile numpy
echo.
python assistant.py
echo.
pause
