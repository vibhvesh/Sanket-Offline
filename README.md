# Sanket Offline V2

Raspberry Pi 5 offline audio transcription prototype with VAD-based clip segmentation, local Whisper Base.en, administrator-defined keyword rules and a four-channel **software relay simulator**.

## V2 workflow

1. Receive audio through a 3.5 mm source cable connected to a compatible USB audio interface (Pi 5 has no analog audio input).
2. WebRTC VAD segments speech automatically at 16 kHz mono.
3. Each clip includes a 1-second pre-roll and closes after 2 seconds of silence.
4. A separate transcription worker processes clips using local whisper.cpp / Whisper Base.en.
5. Completed transcripts are matched against administrator-defined phrase rules.
6. Matching rules create simulated Channel 1–4 ON/OFF/TOGGLE events in the dashboard.

## One-line Raspberry Pi installer

On a 64-bit Raspberry Pi OS / Ubuntu ARM64 installation:

```bash
curl -fsSL https://raw.githubusercontent.com/vibhvesh/Sanket-Offline/main/install.sh | sudo bash
```

Internet is needed during installation to install packages, build whisper.cpp and download the model. Transcription is local after installation.

Dashboard: `http://PI-IP:8080`

## Dashboard

- Live audio and model status
- VAD recording status and input level
- Transcript and recording event history
- Keyword rule editor: phrase, channel, action and enable state
- Four-channel software relay-state simulator
- WAV upload transcription test

## Configuration

`/etc/sanket-offline/config.yaml`

Default VAD settings: 16 kHz mono, 20 ms frames, 1 second pre-roll, 2 seconds silence ending, WebRTC VAD aggressiveness 2.

## Service

```bash
sudo systemctl status sanket-offline
sudo journalctl -u sanket-offline -f
sudo systemctl restart sanket-offline
```

## Prototype safety and limitations

This release implements keyword-to-output mapping in software only. It does **not** drive GPIO pins, energize a physical relay board, or switch connected equipment. Validate segmentation, transcription accuracy, phrase matching and event logging in simulation. Do not connect this prototype to weapons, safety-critical systems or operational command-and-control equipment.

The dashboard has no login or HTTPS. Keep port 8080 on a trusted private LAN. Automatic retention cleanup is not implemented yet.
