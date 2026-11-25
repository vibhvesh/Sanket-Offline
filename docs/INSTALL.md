# Installation and operation

Requirements: Raspberry Pi 5, 64-bit Raspberry Pi OS or Ubuntu, active cooling, reliable PSU, and a USB audio interface. Pi 5 has no conventional analog microphone input.

Run the one-line installer in the repository README. It installs system packages, compiles whisper.cpp, downloads `ggml-base.en-q5_0.bin`, creates the Python environment and enables systemd.

Find the Pi address with `hostname -I`. Open `http://PI-IP:8080` or `http://sanket-offline.local:8080` when mDNS is available.

List audio devices:
```bash
source /opt/sanket-offline/venv/bin/activate
python -c "import sounddevice as s; print(s.query_devices())"
```
Set the numeric input device in `/etc/sanket-offline/config.yaml`, then run `sudo systemctl restart sanket-offline`.

Service commands:
```bash
sudo systemctl status sanket-offline
sudo journalctl -u sanket-offline -f
sudo systemctl restart sanket-offline
```
After installation, transcription is performed locally by whisper.cpp. No audio is sent to a cloud service.
