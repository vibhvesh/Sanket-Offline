#!/usr/bin/env bash
set -euo pipefail
[[ $EUID -eq 0 ]] || { echo "Run with sudo."; exit 1; }
[[ "$(dpkg --print-architecture)" == "arm64" ]] || { echo "64-bit ARM OS (arm64) required."; exit 1; }
APP=/opt/sanket-offline; DATA=/var/lib/sanket-offline; CONF=/etc/sanket-offline
REPO=https://raw.githubusercontent.com/vibhvesh/Sanket-Offline/main
echo "[1/8] Installing dependencies"
apt-get update
DEBIAN_FRONTEND=noninteractive apt-get install -y git cmake build-essential python3 python3-venv python3-dev portaudio19-dev libasound2-dev libopenblas-dev curl
echo "[2/8] Building whisper.cpp"
mkdir -p "$APP"
if [[ ! -d "$APP/whisper.cpp/.git" ]]; then git clone --depth 1 https://github.com/ggml-org/whisper.cpp.git "$APP/whisper.cpp"; fi
cmake -S "$APP/whisper.cpp" -B "$APP/whisper.cpp/build" -DWHISPER_BUILD_TESTS=OFF -DWHISPER_BUILD_EXAMPLES=ON -DGGML_OPENBLAS=ON
cmake --build "$APP/whisper.cpp/build" --config Release -j"$(nproc)"
echo "[3/8] Downloading Whisper Base.en"
bash "$APP/whisper.cpp/models/download-ggml-model.sh" base.en-q5_0
echo "[4/8] Downloading Sanket Offline V2"
curl -fsSL "$REPO/app.py" -o "$APP/app.py"
curl -fsSL "$REPO/requirements.txt" -o "$APP/requirements.txt"
mkdir -p "$CONF" "$DATA/recordings"
if [[ ! -f "$CONF/config.yaml" ]]; then curl -fsSL "$REPO/config.yaml" -o "$CONF/config.yaml"; fi
sed -i "s|/opt/sanket-offline/whisper.cpp/models/ggml-base.en-q5_0.bin|$APP/whisper.cpp/models/ggml-base.en-q5_0.bin|; s|/opt/sanket-offline/whisper.cpp/build/bin/whisper-cli|$APP/whisper.cpp/build/bin/whisper-cli|" "$CONF/config.yaml"
echo "[5/8] Installing Python packages"
python3 -m venv "$APP/venv"
"$APP/venv/bin/pip" install --upgrade pip
"$APP/venv/bin/pip" install -r "$APP/requirements.txt"
echo "[6/8] Installing systemd unit"
cat >/etc/systemd/system/sanket-offline.service <<EOF
[Unit]
Description=Sanket Offline V2 local audio transcription prototype
After=network.target sound.target
[Service]
Type=simple
User=root
WorkingDirectory=$APP
Environment=SANKET_CONFIG=$CONF/config.yaml
ExecStart=$APP/venv/bin/uvicorn app:app --host 0.0.0.0 --port 8080
Restart=always
RestartSec=5
[Install]
WantedBy=multi-user.target
EOF
chown -R root:root "$APP" "$CONF" "$DATA"; chmod -R a+rX "$APP"
echo "[7/8] Enabling service"
systemctl daemon-reload; systemctl enable --now sanket-offline
echo "[8/8] Done"
IP="$(hostname -I | awk '{print $1}')"
echo "Dashboard: http://$IP:8080"
echo "Config: $CONF/config.yaml"
echo "Logs: journalctl -u sanket-offline -f"
echo "Keyword actions affect software simulation only; no GPIO relay is driven."
