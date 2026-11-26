# Sanket Offline V2 — User Manual

## Purpose

Sanket Offline captures audio from a USB audio interface, segments speech automatically, transcribes clips locally in English and compares transcripts with configured keyword rules. Matching rules update four **simulated** relay channel indicators.

## Dashboard

1. Power on the Pi and connect it to the trusted local network.
2. Open `http://PI-IP:8080`.
3. Confirm Audio says `connected` and Whisper says `READY`.
4. Play harmless English test speech into the audio input.

## Automatic VAD clipping

- WebRTC VAD at 16 kHz mono.
- 20 ms audio frames.
- 1 second of pre-roll before detected speech.
- Clip closes after 2 seconds of continuous silence.
- Transcription uses a separate worker so Whisper processing does not block audio capture.

## Keyword rules

The administrator configures a phrase, channel number (1–4), action (ON/OFF/TOGGLE) and enabled status. Rules are matched against completed transcripts.

- ON: sets the simulated channel ON.
- OFF: sets it OFF.
- TOGGLE: reverses its simulated state.

These are software indicators only; this release does not switch physical equipment.

## Test Lab and history

Upload a harmless WAV file to test local transcription. Review the transcript and recent event list. Recording links open saved WAV clips. The model check verifies that the local Whisper CLI and model files exist.

## Limitations and privacy

Transcription may be wrong due to noise, clipping, accents or overlapping voices. This prototype has no login/HTTPS, no automatic retention cleanup and no physical relay driver. Keep it on a trusted LAN. Do not use transcripts or keyword matches as the sole basis for safety-critical decisions.
