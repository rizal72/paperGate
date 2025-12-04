#!/bin/bash
set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "Installing systemd service files..."
sudo cp "$PROJECT_ROOT/systemd/papergate.service" /etc/systemd/system/
sudo cp "$PROJECT_ROOT/systemd/papergate-web.service" /etc/systemd/system/

echo "Reloading systemd daemon..."
sudo systemctl daemon-reload

echo "Systemd services installed successfully"
echo ""
echo "To start services:"
echo "  sudo systemctl start papergate papergate-web"
echo ""
echo "To enable on boot:"
echo "  sudo systemctl enable papergate papergate-web"
