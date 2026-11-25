# Sanket Offline — User Manual

**Audience:** Operators using the local dashboard  
**Platform:** Raspberry Pi 5, 64-bit Linux  
**Purpose:** Receive-only audio recording, offline English transcription and informational keyword matching.

## 1. What the application does

Sanket Offline listens to an audio input connected through a USB audio interface. When it detects audio above the configured level, it buffers the audio. After a period of silence, it saves the segment as a WAV file and sends it to the local Whisper Base.en model.

The dashboard shows system status, recent events, transcripts and links to saved recordings. Keyword matches are informational only.

The application does not provide a radio transmitter, dispatch function, command authentication or physical relay control.

## 2. Open the dashboard

1. Make sure the Raspberry Pi is powered on and connected to the same local network as your computer or phone.
2. Find the Pi's IP address (ask your administrator, or run `hostname -I` on the Pi).
3. Open `http://PI-IP:8080` in a browser.
4. If local mDNS is enabled, you can try `http://sanket-offline.local:8080`.

The dashboard is intended for a trusted local network. The current release does not include user accounts, login or HTTPS. Do not expose port 8080 directly to the public internet.

## 3. Understand the dashboard

### Audio input
- **connected:** The application opened the selected USB audio input.
- **error:** The audio stream could not be opened. Ask the administrator to check the device and logs.
- **starting:** The service is starting or has not yet reported its audio state.

### Input level
A changing value indicates signal energy is reaching the application. A steady value near zero can mean there is no audio, the wrong device is selected, the cable is disconnected, or the source volume is too low.

### Whisper model
- **READY:** The Whisper executable and model file were found.
- **NOT READY:** One or both are missing or at the configured path is incorrect.

A READY indication confirms the files exist; it does not guarantee that every transcription will succeed.

### Recording
Shows whether the audio segmenter is currently collecting an above-threshold signal. A recording is saved after the configured silence interval.

### Relay output
The indicator is **SIMULATED / OFF**. It is not connected to physical relay hardware and must not be interpreted as a real output state.

## 4. Read transcripts and events

The activity table displays the newest events first:
- `RECORDING_SAVED`: a WAV segment was written to disk.
- `TRANSCRIPTION_STARTED`: local Whisper processing began.
- `TRANSCRIPTION_COMPLETED`: a transcript was produced.
- `TRANSCRIPTION_FAILED`: the transcription process failed.
- `KEYWORD_DETECTED`: a configured phrase was found in the transcript.
- `USB_AUDIO_CONNECTED` / `USB_AUDIO_ERROR`: audio input status.

Use the recording link in the final column to listen to a saved WAV segment. A transcript is an automated approximation, not a verified record.

## 5. Run a manual transcription test

1. Prepare a WAV file containing clear English speech.
2. Use the **Test Lab** section.
3. Select the WAV file and choose **Transcribe WAV**.
4. Wait for the result to appear beside the test controls.
5. Compare the result with what was actually spoken.

The current test endpoint accepts WAV uploads. If a test fails, ask the administrator to inspect the service log and confirm the model is installed.

## 6. Audio quality tips

- Use a stable USB audio interface and a clean receive-audio feed.
- Avoid clipping: excessively loud input can distort speech.
- Avoid very low input levels: speech may not cross the configured detection threshold.
- Reduce background noise where possible.
- Radio static, overlapping speakers, accents, fast speech and number strings can reduce accuracy.
- The default audio rate is 16 kHz mono. The selected interface must support the configured rate.

## 7. Privacy and data

Recordings and transcripts are stored on the Raspberry Pi. The application uses local whisper.cpp inference and does not send audio to a cloud transcription service. Access to the Pi, its storage and its dashboard should be limited to authorized personnel.

Ask the administrator how long recordings are retained and how to export or remove them. Do not assume old recordings are automatically deleted in this release.

## 8. Important limitations

- English-only transcription using Whisper Base.en.
- Keyword matches are exact phrase matches against transcript text; they can miss speech or produce false matches.
- The dashboard currently has no user login or role management.
- There is no built-in configuration editor, backup/restore screen or retention cleanup scheduler in this release.
- Do not use this software as the sole basis for emergency response, safety decisions, identity verification or operational command decisions.
- Never connect keyword detection or transcript output to weapons, machinery, dispatch controls or other physical command systems.

## 9. Getting help

Provide your administrator with:
- Approximate time of the problem.
- Dashboard audio and model status.
- The relevant event row and error text.
- USB audio device details, if known.

Do not share sensitive recordings outside your authorized organization.
