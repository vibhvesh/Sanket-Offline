# Sanket Offline V2 — Administrator Guide

## Architecture

USB audio via PortAudio; WebRTC VAD at 16 kHz / 20 ms PCM16 frames; 1-second pre-roll; 2-second silence end trigger; separate local whisper.cpp Base.en transcription worker; SQLite event history; WAV archive; FastAPI dashboard; keyword-to-simulated-output rules.

## Paths

| Purpose | Path |
|---|---|
| Application | `/opt/sanket-offline/app.py` |
| Whisper | `/opt/sanket-offline/whisper.cpp/` |
| Configuration | `/etc/sanket-offline/config.yaml` |
| Recordings | `/var/lib/sanket-offline/recordings/` |
| Database | `/var/lib/sanket-offline/events.sqlite3` |
| Service | `/etc/systemd/system/sanket-offline.service` |

## Audio

The app expects 16 kHz mono audio and 20 ms frames. `audio.device` is a PortAudio input index; null selects the system default. `vad_aggressiveness` accepts 0–3, with higher values rejecting more non-speech. V2 uses 1-second pre-roll and 2 seconds of silence before a clip closes.

List devices:

```bash
/opt/sanket-offline/venv/bin/python -c "import sounddevice as s; print(s.query_devices())"
arecord -l
```

## Keyword rules

Configure rules in the dashboard or YAML. Each rule has:
- `phrase`: phrase to match in transcript
- `channel`: integer 1–4
- `action`: ON, OFF or TOGGLE
- `enabled`: true/false

Rules run after transcription, not directly on raw audio. Matching updates software-simulated relay state only.

## Service management

```bash
sudo systemctl status sanket-offline
sudo journalctl -u sanket-offline -f
sudo systemctl restart sanket-offline
sudo systemctl stop sanket-offline
```

## Backup

```bash
sudo systemctl stop sanket-offline
sudo tar -czf sanket-offline-backup-$(date +%F).tar.gz /etc/sanket-offline /var/lib/sanket-offline
sudo systemctl start sanket-offline
```

Automatic retention cleanup is not implemented. Monitor disk usage and maintain an approved archive/deletion policy.

## Security and prototype boundary

The dashboard listens on port 8080 without login or HTTPS. Restrict it to a trusted private LAN; do not expose it to the public internet.

Keyword actions update software simulation only. There is no GPIO driver or physical relay control in this release. Any separate equipment interface would require its own electrical and safety design review. Do not use this prototype for weapons, safety-critical equipment or operational command-and-control.
