#!/bin/bash
set -e

echo "=== Configuring WaveShare e-Paper Display ==="
echo ""

# Check if SPI is enabled
if ! grep -q "^dtparam=spi=on" /boot/config.txt 2>/dev/null; then
    echo "SPI interface not enabled. Enabling SPI..."
    echo "dtparam=spi=on" | sudo tee -a /boot/config.txt
    echo "SPI enabled. A reboot will be required."
    NEEDS_REBOOT=1
else
    echo "SPI interface already enabled."
fi

# Check if WaveShare drivers are installed
if python3 -c "import waveshare_epd" 2>/dev/null; then
    echo "WaveShare e-Paper drivers already installed."
else
    echo "WaveShare drivers not found. They will be installed by install-deps.sh"
fi

echo ""
if [ "$NEEDS_REBOOT" = "1" ]; then
    echo "Configuration complete. Please reboot your Raspberry Pi for SPI to take effect."
    echo "After reboot, run the installation script again."
else
    echo "Configuration complete. No reboot required."
fi
