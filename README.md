# paperGate

Raspberry Pi gateway with e-Paper display for home network monitoring and control.

![System Dashboard](screenshots/system.png)

## Features

- 📟 **E-Paper Display**: WaveShare 2.7" e-Paper HAT showing system stats, weather, calendar, and more
- 🌐 **Web Interface**: Control your display remotely from any browser
- 📰 **RSS Feed Reader**: E-paper optimized news feed viewer (integrated in web interface)
- 🔐 **Tailscale Gateway**: Monitor VPN status and connected peers
- 📊 **System Dashboard**: Visual monitoring with CPU, memory, temperature, disk usage
- 📅 **Calendar Integration**: CalDAV/webcal support for events and tasks
- 🌦️ **Weather**: Current conditions and forecast
- 🎲 **Fortune Cookies**: Random quotes and affirmations

## Quick Start

### Prerequisites

- Raspberry Pi (tested on Pi 4)
- WaveShare 2.7in e-Paper HAT (V2)
- Raspberry Pi OS (Bookworm or later)
- SPI interface enabled (`sudo raspi-config` → Interface Options → SPI)

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/paperGate.git
cd paperGate

# Run installation script
sudo ./scripts/install.sh

# Setup command aliases (optional but recommended)
./scripts/setup-aliases.sh

# Edit configuration
micro core/local_settings.py
micro web/app.cfg

# Start services using aliases
pg-start

# Or without aliases
sudo systemctl start papergate papergate-web

# Enable auto-start on boot
pg-enable  # or: sudo systemctl enable papergate papergate-web
```

Access the web interface at: `http://your-pi-ip:5000`

## Configuration

### Core Settings

Edit `core/local_settings.py`:

```python
# Display driver
DRIVER = "epd2in7b_V2"

# Screens to show (in order)
SCREENS = [
    'system',
    'tailscale',
    'system_dashboard',
    'weather',
    'calendar',
    'webview',  # Shows RSS feed from web interface
]

# Weather
WEATHER_CITY = "Your City"
WEATHER_FORMAT = python_weather.METRIC

# Calendar (webcal or CalDAV)
CALENDAR_URLS = [
    {'type': 'webcal', 'url': 'https://calendar.google.com/...'},
]

# RSS Feed (displayed via webview screen)
WEBVIEW_URL = 'http://localhost:5000/feed'
WEBVIEW_SCALE = 0.8
```

### Web Interface Settings

Edit `web/app.cfg`:

```python
# Authentication (change these!)
AUTH_USERNAME = 'admin'
AUTH_PASSWORD = 'your-secure-password'

# Flask secret key
SECRET_KEY = 'generate-a-random-secret-key'
```

### RSS Feed Sources

Edit the `FEEDS` list in `web/app.py` to customize news sources:

```python
FEEDS = [
    'https://www.ansa.it/sito/ansait_rss.xml',  # ANSA Italia
    'http://feeds.bbci.co.uk/news/rss.xml',     # BBC News
    # Add more feeds here
]
```

## Available Screens

- **system**: Raspberry Pi model, OS, IP, temperature, uptime
- **tailscale**: VPN status, IPs, exit node, connected peers
- **system_dashboard**: Visual CPU/memory/temp/disk dashboard with pie charts
- **weather**: Current weather and forecast
- **calendar**: Upcoming calendar events
- **tasks**: Todo list from CalDAV
- **dashboard**: Combined info view
- **fortune**: Random fortune cookies
- **affirmations**: Positive affirmations
- **webview**: Display webpages (shows RSS feed by default)

## Command Aliases

After running `setup-aliases.sh`, these aliases are available:

```bash
pg          # Run paperGate core daemon directly (for testing)
pg-start    # Start both papergate services
pg-stop     # Stop both papergate services
pg-restart  # Restart both papergate services
pg-enable   # Enable auto-start on boot
pg-disable  # Disable auto-start on boot
pg-status   # Show status of both services
pg-log      # Follow papergate core logs
pg-web-log  # Follow papergate web logs
pg-logs     # Follow both logs together
```

The setup script automatically adds sourcing of `.bash_aliases` to your `.bashrc` or `.zshrc` if not already present.

## CLI Control

Using `core/cli.py` directly:

```bash
cd ~/paperGate/core

# Reload current screen
./cli.py reload

# Switch screens
./cli.py screen weather

# Navigate
./cli.py next
./cli.py previous

# Manage screens (session-only)
./cli.py add_screen fortune
./cli.py remove_screen affirmations
```

## Architecture

```
paperGate/
├── core/           # Main e-paper display daemon
│   ├── app.py      # Core application
│   ├── screens/    # Screen modules
│   └── libs/       # Supporting libraries
├── web/            # Flask web interface (includes RSS feed reader)
│   ├── app.py      # Web app + /feed endpoint
│   └── templates/  # HTML templates
├── images/         # Shared assets (logos, icons)
├── systemd/        # Service definitions (2 services)
└── scripts/        # Installation automation
```

**Communication**: Both CLI and web interface communicate with the core daemon via POSIX message queue (`/epdtext_ipc`).

**Services**:
- `papergate.service` - Core e-paper display daemon
- `papergate-web.service` - Web interface + RSS feed reader (single Flask app on port 5000)

## Troubleshooting

### Display not updating
- Check SPI is enabled: `ls /dev/spi*`
- Check service is running: `pg-status`
- Check logs: `pg-log`

### Web interface not accessible
- Verify service is running: `sudo systemctl status papergate-web`
- Check firewall: `sudo ufw allow 5000`
- Test locally: `curl http://localhost:5000`

### Permission errors on message queue
- Ensure papergate service is running first (creates the queue)
- Check queue permissions: `ls -la /dev/mqueue/epdtext_ipc`

## Creating Custom Screens

See `docs/DEVELOPMENT.md` for detailed screen development guide.

Basic example:

```python
# core/screens/myscreen.py
from screens import AbstractScreen

class Screen(AbstractScreen):
    def reload(self):
        self.blank()
        self.draw_titlebar("My Screen")
        self.text("Hello World", font_size=40, position=(50, 50))
```

Add `'myscreen'` to the `SCREENS` list in `local_settings.py`.

## Documentation

- [Installation Guide](docs/INSTALLATION.md)
- [Configuration Guide](docs/CONFIGURATION.md)
- [Available Screens](docs/SCREENS.md)
- [Development Guide](docs/DEVELOPMENT.md)
- [Troubleshooting](docs/TROUBLESHOOTING.md)

## Contributing

Contributions welcome! Please read [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) first.

## License

MIT License - see [LICENSE](LICENSE)

## Acknowledgments

- Original epdtext project by [tsbarnes](https://github.com/tsbarnes/epdtext)
- WaveShare for e-Paper drivers
- Python community for amazing libraries

## Support

- 📖 [Full Documentation](docs/)
- 🐛 [Issue Tracker](https://github.com/yourusername/paperGate/issues)
- 💬 [Discussions](https://github.com/yourusername/paperGate/discussions)
