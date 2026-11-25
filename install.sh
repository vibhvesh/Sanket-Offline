#!/usr/bin/env bash
set -euo pipefail
if [[ $EUID -ne 0 ]]; then echo "Run with sudo."; exit 1; fi
ARCH="$(dpkg --print-architecture)"
if [[ "$ARCH" != "arm64" ]]; then echo "64-bit OS required (arm64 detected: $ARCH)."; exit 1; fi
APP=/opt/sanket-offline
DATA=/var/lib/sanket-offline
CFG=/etc/sanket-offline
echo "[1/7] Installing system packages"
apt-get update
DEBIAN_FRONTEND=noninteractive apt-get install -y git cmake build-essential python3 python3-venv python3-dev portaudio19-dev libasound2-dev libopenblas-dev curl
echo "[2/7] Fetching whisper.cpp"
if [[ ! -d "$APP/whisper.cpp/.git" ]]; then mkdir -p "$APP"; git clone --depth 1 https://github.com/ggml-org/whisper.cpp.git "$APP/whisper.cpp"; fi
cmake -S "$APP/whisper.cpp" -B "$APP/whisper.cpp/build" -DWHISPER_BUILD_TESTS=OFF -DWHISPER_BUILD_EXAMPLES=ON -DGGML_OPENBLAS=ON
cmake --build "$APP/whisper.cpp/build" --config Release -j"$(nproc)"
echo "[3/7] Downloading local English model"
bash "$APP/whisper.cpp/models/download-ggml-model.sh" base.en-q5_0
echo "[4/7] Installing application"
mkdir -p "$APP" "$DATA/recordings" "$CFG"
curl -fsSL https://raw.githubusercontent.com/vibhvesh/Sanket-Offline/main/app.py -o "$APP/app.py"
curl -fsSL https://raw.githubusercontent.com/vibhvesh/Sanket-Offline/main/requirements.txt -o "$APP/requirements.txt"
if [[ ! -f "$CFG/config.yaml" ]]; then curl -fsSL https://raw.githubusercontent.com/vibhvesh/Sanket-Offline/main/config.yaml -o "$CFG/config.yaml"; fi
sed -i "s|/opt/sanket-offline/whisper.cpp/models/ggml-base.en-q5_0.bin|$APP/whisper.cpp/models/ggml-base.en-q5_0.bin|; s|/opt/sanket-offline/whisper.cpp/build/bin/whisper-cli|$APP/whisper.cpp/build/bin/whisper-cli|" "$CFG/config.yaml"
python3 -m venv "$APP/venv"
"$APP/venv/bin/pip" install --upgrade pip
"$APP/venv/bin/pip" install -r "$APP/requirements.txt"
chown -R root:root "$APP"; chmod -R a+rX "$APP"; chown -R root:root "$CFG"; chmod 755 "$DATA" "$DATA/recordings"
echo "[5/7] Creating systemd service"
cat >/etc/systemd/system/sanket-offline.service <<EOF
[Unit]
Description=Sanket Offline Audio Transcription
After=network.target sound.target
[Service]
Type=simple
User=root
WorkingDirectory=$APP
Environment=SANKET_CONFIG=$CFG/config.yaml
ExecStart=$APP/venv/bin/uvicorn app:app --host 0.0.0.0 --port 8080
Restart=always
RestartSec=5
[Install]
WantedBy=multi-user.target
EOF
echo "[6/7] Enabling service"
systemctl daemon-reload
systemctl enable --now sanket-offline
echo "[7/7] Complete"
IP="$(hostname -I | awk '{print $1}')"
echo "Dashboard: http://$IP:8080"
echo "Logs: journalctl -u sanket-offline -f"
echo "Config: $CFG/config.yaml"
