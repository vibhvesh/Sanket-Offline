# Sanket Offline — Administrator Guide

**Audience:** System administrators responsible for installation, configuration, maintenance and data protection.

## 1. Architecture and scope

The current release runs on one Raspberry Pi and consists of:
- PortAudio / `sounddevice` for USB audio capture.
- A Python audio segmenter that saves WAV files after silence.
- whisper.cpp with the quantized Whisper Base.en model for local English transcription.
- FastAPI / Uvicorn for the local dashboard and API.
- SQLite for event and transcript history.
- systemd for startup and restart management.

All inference is local after installation. No cloud transcription is configured.

**Safety boundary:** keyword events are informational only. The relay display is simulated. This release contains no physical GPIO relay driver, no relay actuation, no command authentication and no operational control interface.

## 2. Installation

On a 64-bit Raspberry Pi OS or Ubuntu system, use the installer documented in the repository README:

```bash
curl -fsSL https://raw.githubusercontent.com/vibhvesh/Sanket-Offline/main/install.sh | sudo bash
```

The installer requires internet access to install packages, clone/build whisper.cpp and download the model. Once installed, transcription runs locally.

Recommended hardware:
- Raspberry Pi 5 (8 GB recommended).
- Active cooling and reliable power supply.
- USB audio interface compatible with ALSA/PortAudio.
- Adequate local storage for recordings.

## 3. Important paths

| Item | Path |
|---|---|
| Application | `/opt/sanket-offline/app.py` |
| Python environment | `/opt/sanket-offline/venv/` |
| whisper.cpp source/build | `/opt/sanket-offline/whisper.cpp/` |
| Whisper model | `/opt/sanket-offline/whisper.cpp/models/ggml-base.en-q5_0.bin` |
| Configuration | `/etc/sanket-offline/config.yaml` |
| Recordings | `/var/lib/sanket-offline/recordings/` |
| SQLite database | `/var/lib/sanket-offline/events.sqlite3` |
| systemd unit | `/etc/systemd/system/sanket-offline.service` |

## 4. Service management

Check service:
```bash
sudo systemctl status sanket-offline
```

Follow logs:
```bash
sudo journalctl -u sanket-offline -f
```

Restart after configuration changes:
```bash
sudo systemctl restart sanket-offline
```

Stop/start:
```bash
sudo systemctl stop sanket-offline
sudo systemctl start sanket-offline
```

Enable at boot:
```bash
sudo systemctl enable sanket-offline
```

## 5. Configure audio and transcription

Edit the configuration:
```bash
sudo nano /etc/sanket-offline/config.yaml
```

Relevant settings:

| Setting | Meaning |
|---|---|
| `audio.device` | Numeric PortAudio input device index; `null` uses the system default |
| `audio.sample_rate` | Capture sample rate; default 16000 Hz |
| `audio.silence_seconds` | Silence duration that ends a segment; default 1.8 |
| `audio.speech_threshold` | RMS level threshold for starting a segment; tune carefully for the input source |
| `transcription.language` | English in this release |
| `transcription.model` | Path to the local Whisper model |
| `transcription.cli` | Path to the whisper.cpp CLI executable |
| `transcription.threads` | CPU threads used by Whisper |
| `storage.data_dir` | Local data directory |
| `storage.retention_days` | Reserved configuration value; automatic cleanup is not implemented yet |
| `keywords.phrases` | List of phrases matched against transcript text |
| `keywords.beep_on_match` | Reserved setting; dashboard beep/notification is not implemented yet |

After editing, validate YAML formatting and restart the service.

## 6. Identify the correct USB audio device

List devices from the application's virtual environment:
```bash
/opt/sanket-offline/venv/bin/python -c "import sounddevice as s; print(s.query_devices())"
```

For ALSA-level checks:
```bash
arecord -l
aplay -l
```

Set `audio.device` to the numeric input index shown by PortAudio. Restart the service and confirm that the dashboard reports `connected`.

If the device does not support 16 kHz, choose a supported input rate and update `audio.sample_rate`. Confirm the source is mono-compatible. Check cable routing, input gain and clipping.

## 7. Whisper model checks

The dashboard's **Check Whisper model** button checks whether the configured CLI and model paths exist.

Check files directly:
```bash
ls -lh /opt/sanket-offline/whisper.cpp/build/bin/whisper-cli
ls -lh /opt/sanket-offline/whisper.cpp/models/ggml-base.en-q5_0.bin
```

If either is missing, review installer/build output and the service logs. Do not download model files from untrusted sources.

## 8. Keyword configuration

Edit `keywords.phrases` in the YAML file. Phrase matching is case-insensitive and operates on the recognized transcript. It is not a live audio detector, a guaranteed alert, or a secure command parser.

After changes, restart the service. Review the event history to confirm the phrase matching behavior with harmless test recordings.

## 9. Data, backup and restore

The database and WAV files are stored under `/var/lib/sanket-offline/`.

Stop the service before making a consistent filesystem backup:
```bash
sudo systemctl stop sanket-offline
sudo tar -czf sanket-offline-backup-$(date +%F).tar.gz /etc/sanket-offline /var/lib/sanket-offline
sudo systemctl start sanket-offline
```

Restore only onto a trusted system with the service stopped. Preserve file ownership and permissions, then restart and verify the dashboard.

The current release does not implement automatic retention cleanup, scheduled backups, or an in-dashboard backup/restore workflow. Monitor free disk space and establish an organization-approved backup and deletion policy.

## 10. Network and security

The service listens on `0.0.0.0:8080` on the local network. The current dashboard/API has no authentication, authorization, TLS or audit trail for administrator changes.

- Keep port 8080 on a trusted, segmented LAN.
- Do not port-forward it to the public internet.
- Restrict access with network firewall rules and trusted Wi-Fi/VLAN controls.
- Use SSH keys and standard OS hardening for administration.
- Protect physical access to the Pi and its storage.
- Treat WAV files, transcripts and database backups as potentially sensitive information.

## 11. Troubleshooting

| Symptom | Checks |
|---|---|
| Dashboard unavailable | `systemctl status`, IP address, port 8080, firewall |
| Audio status is error | USB connection, `arecord -l`, PortAudio device list, sample rate |
| Input level stays near zero | Correct input device, cable, source volume and input gain |
| No recordings saved | Confirm input crosses `speech_threshold`; check service logs and free disk |
| Model not ready | Confirm CLI and model paths exist and are readable |
| Transcription fails | Check journal logs, model file integrity, CPU/RAM and WAV format |
| Disk filling up | Inspect recording directory and implement an approved manual archive/deletion policy |

## 12. API endpoints

These local endpoints are used by the dashboard and are not an authenticated public API:

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/status` | Audio/model status and device list |
| GET | `/api/events?limit=100` | Recent event/transcript rows |
| GET | `/api/recordings` | List recent WAV recordings |
| GET | `/api/recordings/{name}` | Retrieve a WAV recording |
| POST | `/api/transcribe` | Upload a WAV file for transcription |
| POST | `/api/test` | Check Whisper CLI/model presence |

Do not expose these endpoints beyond the trusted LAN.

## 13. Operational safety

Whisper output can be incomplete or incorrect. Noise, static, accents, overlapping speakers and similar-sounding words can cause errors. A keyword can be missed or falsely detected.

Never treat a transcript or keyword match as authentication, authorization, confirmation of identity, or an instruction to actuate equipment. Do not connect this software to weapons, emergency dispatch controls, vehicles, industrial machinery or safety-critical systems. Keep relay/output behavior simulated and verify all information independently.
