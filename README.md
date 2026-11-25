# Sanket Offline

Offline Raspberry Pi 5 audio capture, local English transcription and informational keyword detection.

- Captures receive-only audio from a USB audio interface.
- Records silence-delimited WAV clips.
- Transcribes locally with **whisper.cpp / Whisper Base.en**.
- Logs transcripts and configurable keyword matches to SQLite.
- Provides a local FastAPI dashboard and systemd service.
- No cloud transcription. Keyword matches are informational only; relay status is simulated.

## Install on Raspberry Pi 5

Use Raspberry Pi OS 64-bit or Ubuntu 64-bit. Connect your receive-only audio source to a USB audio interface, then run:

```bash
curl -fsSL https://raw.githubusercontent.com/vibhvesh/Sanket-Offline/main/install.sh | sudo bash
```

The installer builds whisper.cpp, downloads the quantized Base.en model, creates the Python environment, installs the service and starts it. Internet is required for this one-time installation and model download; runtime transcription is local.

Open `http://sanket-offline.local:8080` (if mDNS is available) or `http://PI-IP:8080`.

## First checks

1. Dashboard → Live Monitor: verify the USB input device and input level.
2. Dashboard → Configuration: set the correct audio device index in `/etc/sanket-offline/config.yaml`.
3. Dashboard → Test Lab: check the Whisper model and upload a WAV for transcription.
4. Dashboard → Recent activity: inspect transcripts and saved recording references.

Configuration: `/etc/sanket-offline/config.yaml`  
Data and recordings: `/var/lib/sanket-offline/`  
Service: `sanket-offline.service`  
Logs: `journalctl -u sanket-offline -f`

## Audio

The app captures mono audio at the configured sample rate (default 16 kHz) using PortAudio. If your USB interface exposes a different native rate, change `sample_rate` to a supported rate. The installer downloads the model; it does not download audio to a cloud service.

## Safety

This is an offline audio-analysis demonstrator. Keyword detections are informational events only. No transcript or detected phrase can energize physical relay hardware. The relay indicator is simulated. Do not connect this software to weapons, safety-critical systems, or operational command-and-control equipment.

Documentation: [User Manual](docs/USER-MANUAL.md) · [Administrator Guide](docs/ADMIN-GUIDE.md) · [Installation](docs/INSTALL.md) · [Safety](docs/SAFETY.md).
