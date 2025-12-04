#!/bin/bash
set -e

echo "=== paperGate Installation ==="
echo ""

# Check if running on Raspberry Pi
if ! grep -q "Raspberry Pi" /proc/cpuinfo 2>/dev/null; then
    echo "Warning: This script is designed for Raspberry Pi"
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Get project root
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

echo "Project root: $PROJECT_ROOT"
echo ""

# Install dependencies
echo "Step 1/4: Installing system dependencies..."
sudo ./scripts/install-deps.sh

# Configure WaveShare drivers
echo "Step 2/4: Setting up e-Paper display drivers..."
./scripts/configure-waveshare.sh

# Setup configuration files
echo "Step 3/4: Creating configuration files..."
if [ ! -f core/local_settings.py ]; then
    cp core/local_settings.py.example core/local_settings.py
    echo "Created core/local_settings.py - Please edit it with your settings"
fi

if [ ! -f web/app.cfg ]; then
    cp web/app.cfg.example web/app.cfg
    echo "Created web/app.cfg - Please edit it with your auth credentials"
fi

# Setup systemd services
echo "Step 4/4: Setting up systemd services..."
sudo ./scripts/setup-systemd.sh

echo ""
echo "=== Installation Complete! ==="
echo ""
echo "Next steps:"
echo "1. Edit core/local_settings.py with your configuration"
echo "2. Edit web/app.cfg with authentication credentials"
echo "3. Start services: sudo systemctl start papergate papergate-web"
echo "4. Enable on boot: sudo systemctl enable papergate papergate-web"
echo ""
echo "Access web interface at: http://$(hostname -I | awk '{print $1}'):5000"
echo "Access RSS feed reader at: http://$(hostname -I | awk '{print $1}'):5000/feed"
