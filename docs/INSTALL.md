# V2 Installation and bring-up

Requirements: Raspberry Pi 5, 64-bit Raspberry Pi OS or Ubuntu ARM64, active cooling, reliable power and a USB audio interface.

1. Connect the 3.5 mm audio source to a suitable USB audio interface. Check source output level and use appropriate attenuation/isolation if needed; not every 3.5 mm output is microphone-level.
2. Connect the USB interface to the Pi.
3. Run the one-line installer in the repository README.
4. Find the Pi address with `hostname -I`; open `http://PI-IP:8080`.
5. Confirm Audio says `connected` and Whisper says `READY`.

List audio devices:

```bash
/opt/sanket-offline/venv/bin/python -c "import sounddevice as s; print(s.query_devices())"
arecord -l
```

Set `audio.device` in `/etc/sanket-offline/config.yaml` to the PortAudio input index and restart:

```bash
sudo systemctl restart sanket-offline
sudo journalctl -u sanket-offline -f
```

The VAD implementation expects 16 kHz mono PCM16 audio in 20 ms frames. Clip policy is 1-second pre-roll and 2 seconds of silence before ending a clip. Whisper Base.en is installed locally during setup.

Check model files:

```bash
ls -lh /opt/sanket-offline/whisper.cpp/build/bin/whisper-cli
ls -lh /opt/sanket-offline/whisper.cpp/models/ggml-base.en-q5_0.bin
```
