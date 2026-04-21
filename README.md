# KeyPulse Nexus

Polished classroom-safe desktop demo for keyboard analytics, designed for ethical hacking presentations.

## What It Does

- Tracks typing only inside the app's built-in typing pad
- Shows live dashboard metrics, timer, activity feed, and frequency chart
- Exports a clean text summary for presentation
- Opens a detailed frequency report using `matplotlib`

## Why This Version Is Better For Class

This project is designed as a safe educational sandbox.
It demonstrates monitoring, logging, and analysis concepts without capturing system-wide user input.

## Run The App

```powershell
cd Keylogger_Project
python main.py
```

## Build The EXE

```powershell
cd Keylogger_Project
pip install -r requirements.txt
.\build_exe.ps1
```

The generated file will be:

```text
dist\KeyPulseNexus.exe
```

## Demo Flow Suggestion

1. Open the app and explain that it is a controlled analytics sandbox.
2. Press `Start Session`.
3. Type a short paragraph in the typing deck.
4. Show the live metrics and top-frequency pulse chart.
5. Open `Show Frequency Report`.
6. Export `Session Brief` and show the text summary to the professor.

## Project Files

- `main.py`: main application
- `main.spec`: PyInstaller configuration
- `build_exe.ps1`: EXE build script
- `icon.ico`: application icon
