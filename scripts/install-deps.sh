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
# Determine actual user's home directory (handles sudo correctly)
USER_HOME=$(getent passwd ${SUDO_USER:-$USER} | cut -d: -f6)
EPAPER_DIR="$USER_HOME/e-Paper"

if [ ! -d "$EPAPER_DIR" ]; then
    # Clone as the actual user, not root
    if [ -n "$SUDO_USER" ]; then
        sudo -u $SUDO_USER git clone https://github.com/waveshare/e-Paper "$EPAPER_DIR"
    else
        git clone https://github.com/waveshare/e-Paper "$EPAPER_DIR"
    fi
fi
cd "$EPAPER_DIR/RaspberryPi_JetsonNano/python"
sudo python3 setup.py install

echo "Installing Python dependencies..."
# Get project root - either from parameter or auto-detect
PROJECT_ROOT="${1:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
cd "$PROJECT_ROOT"
sudo pip3 install -r requirements.txt

echo "Dependencies installed successfully"
