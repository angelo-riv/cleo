#!/bin/bash
set -e

echo "=== Quadruped Robot Setup ==="

# System packages
sudo apt update
sudo apt install -y \
  python3-pip \
  python3-dev \
  portaudio19-dev \
  libgpiod2

# Python packages
pip3 install \
  adafruit-circuitpython-pca9685 \
  adafruit-circuitpython-motor \
  adafruit-circuitpython-dht \
  picamera2 \
  opencv-python \
  luma.oled \
  Pillow \
  faster-whisper \
  sounddevice \
  gTTS \
  pygame \
  google-generativeai \
  python-dotenv \
  RPi.GPIO

echo ""
echo "=== Downloading MobileNet SSD model ==="
mkdir -p models

wget -q --show-progress \
  -O models/MobileNetSSD_deploy.prototxt \
  https://raw.githubusercontent.com/chuanqi305/MobileNet-SSD/master/MobileNetSSD_deploy.prototxt

# The caffemodel (~23 MB) must be downloaded separately.
# Run this command manually if the link below fails:
#   wget -O models/MobileNetSSD_deploy.caffemodel "<url>"
wget -q --show-progress \
  -O models/MobileNetSSD_deploy.caffemodel \
  "https://drive.google.com/uc?export=download&id=0B3gersZ2cHIxRm5PMWRoTkdHdHc" \
  || echo "WARNING: caffemodel download failed — download it manually and place it in models/"

echo ""
echo "=== Enabling I2C and Camera ==="
sudo raspi-config nonint do_i2c 0
sudo raspi-config nonint do_camera 0

echo ""
echo "=== Verifying .env file ==="
if [ ! -f .env ]; then
  echo "ERROR: .env file not found."
  echo "Copy .env from the repo and fill in your GEMINI_API_KEY before running."
  exit 1
fi

if grep -q "^GEMINI_API_KEY=$" .env; then
  echo "WARNING: GEMINI_API_KEY is empty in .env — fill it in before running main.py"
fi

echo ""
echo "=== Setup complete ==="
echo "1. Edit .env and add your GEMINI_API_KEY"
echo "2. Run the robot with: python3 main.py"
