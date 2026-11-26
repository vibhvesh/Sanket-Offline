# Safety and prototype boundary

Sanket Offline V2 is an offline audio transcription and keyword-event prototype.

- Audio is captured from a receive-side 3.5 mm source through a suitable USB audio interface.
- Transcription and phrase matching are informational and may be wrong.
- ON/OFF/TOGGLE rules change software-simulated channel states only.
- No GPIO output or physical relay board is driven in this repository version.
- Do not treat recognized phrases as authentication, authorization or proof of speaker identity.
- Do not connect this prototype to weapons, safety-critical equipment or operational command-and-control.
- Keep the unauthenticated dashboard restricted to a trusted private network.
- Check audio electrical levels and isolation before connecting any source to the USB audio interface.
