#!/bin/bash
set -e

echo "Installing system packages..."
sudo apt update
sudo apt install -y \
    python3-pip \
    python3-pil \
    python3-numpy \
    python3-gpiozero \
    git \
    fortune-mod \
    wkhtmltopdf

echo "Installing WaveShare e-Paper drivers..."
if [ ! -d ~/e-Paper ]; then
    git clone https://github.com/waveshare/e-Paper ~/e-Paper
fi
cd ~/e-Paper/RaspberryPi_JetsonNano/python
sudo python3 setup.py install

echo "Installing Python dependencies..."
# Get project root - either from parameter or auto-detect
PROJECT_ROOT="${1:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
cd "$PROJECT_ROOT"
sudo pip3 install -r requirements.txt

echo "Dependencies installed successfully"
