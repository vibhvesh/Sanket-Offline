# Safety scope

Sanket Offline is an offline receive-audio recording and transcription demonstrator.

- Audio input is receive-only.
- Keyword matching creates timestamped informational events.
- The dashboard relay indication is simulated; no GPIO relay driver or physical relay actuation is implemented.
- Do not use transcript text or keyword detections as authentication, authorization, or a safety decision.
- Speech and numeric codes can be replayed or misrecognized and are not secure authentication.
- Do not connect this application to weapons, emergency dispatch controls, vehicles, industrial machinery, or safety-critical/operational command systems.
- Test with harmless audio and a receive-only setup.

Speech recognition can omit, substitute, or hallucinate words, especially with radio noise, clipping, overlapping speakers, accents, and weak signals. Operators must verify transcripts.
