#!/bin/bash
set -e

BASH_ALIASES="$HOME/.bash_aliases"

echo "=== Setting up paperGate aliases ==="
echo ""

# Backup existing .bash_aliases if it exists
if [ -f "$BASH_ALIASES" ]; then
    echo "Backing up existing .bash_aliases to .bash_aliases.bak..."
    cp "$BASH_ALIASES" "${BASH_ALIASES}.bak"
fi

# Create or append to .bash_aliases
echo ""
echo "Adding paperGate aliases to $BASH_ALIASES..."

cat >> "$BASH_ALIASES" << 'EOF'

# paperGate aliases
alias pg='cd ~/paperGate/core && echo "launching paperGate..." && sudo python3 app.py'
alias pg-start='sudo systemctl start papergate papergate-web'
alias pg-stop='sudo systemctl stop papergate papergate-web'
alias pg-restart='sudo systemctl restart papergate papergate-web'
alias pg-enable='sudo systemctl enable papergate papergate-web'
alias pg-disable='sudo systemctl disable papergate papergate-web'
alias pg-status='sudo systemctl status papergate papergate-web'
alias pg-log='journalctl -u papergate -f'
alias pg-web-log='journalctl -u papergate-web -f'
alias pg-logs='journalctl -u papergate -u papergate-web -f'
EOF

# Ensure .bash_aliases is sourced in shell rc files
echo ""
echo "Ensuring .bash_aliases is sourced in shell configuration..."

for RC_FILE in "$HOME/.bashrc" "$HOME/.zshrc"; do
    if [ -f "$RC_FILE" ]; then
        if ! grep -q "source.*\.bash_aliases" "$RC_FILE" 2>/dev/null; then
            echo "" >> "$RC_FILE"
            echo "# Source bash aliases if file exists" >> "$RC_FILE"
            echo "if [ -f ~/.bash_aliases ]; then" >> "$RC_FILE"
            echo "    source ~/.bash_aliases" >> "$RC_FILE"
            echo "fi" >> "$RC_FILE"
            echo "  Added source command to $RC_FILE"
        else
            echo "  $RC_FILE already sources .bash_aliases"
        fi
    fi
done

echo ""
echo "Aliases added successfully!"
echo ""
echo "Available aliases:"
echo "  pg          - Run paperGate core daemon directly (for testing)"
echo "  pg-start    - Start both papergate services"
echo "  pg-stop     - Stop both papergate services"
echo "  pg-restart  - Restart both papergate services"
echo "  pg-enable   - Enable auto-start on boot"
echo "  pg-disable  - Disable auto-start on boot"
echo "  pg-status   - Show status of both services"
echo "  pg-log      - Follow papergate core logs"
echo "  pg-web-log  - Follow papergate web logs"
echo "  pg-logs     - Follow both logs together"
echo ""
echo "Aliases are now available. To use them immediately:"
echo "  source ~/.bash_aliases"
echo ""
echo "Or open a new terminal session."
