# CLAUDE.md

This file provides guidance to Claude Code when working with code in this repository.

## Project Overview

**paperGate** is a unified Raspberry Pi gateway project with e-Paper display management. It combines three previously separate projects (epdtext, epdtext-web, epdtext-feed) into a single cohesive monorepo for easy deployment and replication.

The system provides:
- E-paper display daemon showing modular screens (weather, calendar, system stats, Tailscale VPN monitoring, etc.)
- Web interface for remote control and monitoring
- Integrated RSS feed reader optimized for e-paper display
- Installation automation for turnkey setup

## Architecture

### Monorepo Structure

```
paperGate/
├── core/               # Main e-paper display daemon (ex-epdtext)
│   ├── app.py         # Main application entry point
│   ├── cli.py         # Command-line IPC client
│   ├── settings.py    # Configuration management
│   ├── screens/       # Screen modules (system, weather, calendar, etc.)
│   ├── libs/          # Supporting libraries (epd, weather, calendar, tailscale)
│   ├── display/       # Runtime screenshots (gitignored, contains personal data)
│   └── local_settings.py.example
├── web/               # Flask web interface (ex-epdtext-web + epdtext-feed integrated)
│   ├── app.py        # Unified Flask app (control panel + /feed endpoint)
│   ├── system.py     # System information utilities
│   ├── templates/
│   │   ├── index.html    # Main control panel
│   │   └── feed.html     # RSS feed reader
│   └── app.cfg.example
├── images/           # Shared assets (logos, weather icons)
├── screenshots/      # Documentation screenshots (for README)
├── systemd/          # Service definitions (2 services total)
│   ├── papergate.service
│   └── papergate-web.service
├── scripts/          # Installation automation
│   ├── install.sh
│   ├── install-deps.sh
│   ├── setup-systemd.sh
│   ├── setup-aliases.sh
│   └── configure-waveshare.sh
└── docs/             # Extended documentation
```

### Key Architectural Decisions

**Monorepo Benefits**:
- Single clone/pull for complete system
- Unified version control
- Shared assets (images, configs)
- Simplified deployment
- Better code reuse

**Service Consolidation**:
- **2 services** instead of 3 (papergate + papergate-web)
- RSS feed reader integrated into web interface at `/feed` endpoint
- Reduced memory footprint and process count
- Shared Flask instance and authentication

**Path Management**:
- All paths relative to project root
- No hardcoded `/home/pi/epdtext` paths
- `core/` and `web/` can reference each other via `../`

**IPC Communication**:
- POSIX message queue at `/epdtext_ipc` (kept for backward compatibility)
- Used by CLI (`core/cli.py`) and web interface (`web/app.py`)
- Core daemon creates and manages the queue

## Core Components

### Core Daemon (core/)

**app.py**: Main application orchestrating:
- Screen rotation and navigation
- Threading for calendar/weather/display updates
- IPC message queue processing
- Hardware button handling

**cli.py**: Command-line IPC client for sending commands to daemon

**settings.py**: Configuration management with fallback defaults from `local_settings.py`

**screens/**: Modular screen system, all inherit from `AbstractScreen`:
- `system`: Pi model, OS, IP, temperature, uptime
- `tailscale`: VPN status, IPs, exit node, peer list
- `system_dashboard`: Visual pie charts for CPU/memory/temp/disk
- `weather`: Current weather and forecast
- `calendar`: Upcoming events from webcal/CalDAV
- `tasks`: Todo list from CalDAV
- `dashboard`: Combined info view
- `fortune`: Random fortune cookies
- `affirmations`: Positive affirmations
- `webview`: Screenshot webpage rendering (shows RSS feed by default)

**libs/**: Supporting libraries:
- `epd.py`: Threaded e-paper driver wrapper
- `weather.py`: Async weather fetching
- `calendar.py`: Webcal/CalDAV integration
- `system.py`: System information utilities
- `tailscale.py`: Tailscale VPN status and peer info

### Web Interface (web/)

**app.py**: Unified Flask application providing:
- Control panel routes (index, next_screen, button presses, etc.)
- Authentication via HTTP Basic Auth
- Dynamic screen management (add/remove screens)
- **Integrated RSS feed reader** at `/feed` endpoint
- System information display
- IPC message queue communication with core daemon

**Key Integration Changes**:
- `FEEDS` list at top of file (RSS sources)
- `/feed` route with feedparser logic
- Path updates: `'../core/screens'` instead of `'../epdtext/screens'`
- Single Flask app on port 5000 (no separate feed service)

**templates/**:
- `index.html`: Main control panel UI
- `feed.html`: RSS feed reader optimized for e-paper (black/white, minimal)

## Configuration

### Core Settings (core/local_settings.py)

```python
DRIVER = "epd2in7b_V2"  # WaveShare e-paper driver
DEBUG = True            # Enable debug logging
TIME = 900              # Auto-refresh interval in seconds

SCREENS = [
    'system',
    'tailscale',
    'system_dashboard',
    'weather',
    'calendar',
    'webview',
]

CALENDAR_URLS = [
    {'type': 'webcal', 'url': 'https://...'},
]

WEATHER_CITY = "Your City"
WEATHER_FORMAT = python_weather.METRIC

# Webview points to integrated feed
WEBVIEW_URL = 'http://localhost:5000/feed'
WEBVIEW_SCALE = 0.8
WEBVIEW_ORIENTATION = 'landscape'

# Logo path uses new structure
LOGO = '/home/pi/paperGate/images/raspberry-pi.png'
```

### Web Settings (web/app.cfg)

```python
AUTH_USERNAME = 'admin'
AUTH_PASSWORD = 'your-secure-password'
SECRET_KEY = 'generate-random-secret'
```

### Feed Sources (web/app.py)

Edit the `FEEDS` list directly in `web/app.py`:

```python
FEEDS = [
    'https://www.ansa.it/sito/ansait_rss.xml',
    # Add more RSS feeds here
]
```

## Common Commands

### Using Aliases (recommended)

After running `./scripts/setup-aliases.sh`:

```bash
pg          # Run paperGate core daemon directly
pg-start    # Start both services
pg-stop     # Stop both services
pg-restart  # Restart both services
pg-enable   # Enable auto-start on boot
pg-disable  # Disable auto-start on boot
pg-status   # Show status of both services
pg-log      # Follow core daemon logs
pg-web-log  # Follow web interface logs
pg-logs     # Follow both logs together
```

### Without Aliases

```bash
# Start services
sudo systemctl start papergate papergate-web

# Enable on boot
sudo systemctl enable papergate papergate-web

# Check status
sudo systemctl status papergate papergate-web

# View logs
journalctl -u papergate -f
journalctl -u papergate-web -f
```

### CLI Control

```bash
cd ~/paperGate/core

./cli.py reload              # Reload current screen
./cli.py screen weather      # Switch to weather screen
./cli.py next                # Next screen
./cli.py previous            # Previous screen
./cli.py add_screen fortune  # Add screen (session-only)
./cli.py remove_screen tasks # Remove screen (session-only)
```

## Installation Process

### Quick Install

```bash
git clone https://github.com/yourusername/paperGate.git
cd paperGate
sudo ./scripts/install.sh
./scripts/setup-aliases.sh
```

### What install.sh Does

1. Checks for Raspberry Pi hardware
2. Installs system dependencies (apt packages)
3. Installs WaveShare e-paper drivers
4. Installs Python packages from requirements.txt
5. Configures SPI interface
6. Creates config files from examples
7. Installs systemd services

### Manual Installation Steps

```bash
# 1. Install dependencies
sudo ./scripts/install-deps.sh

# 2. Configure WaveShare drivers
./scripts/configure-waveshare.sh

# 3. Create config files
cp core/local_settings.py.example core/local_settings.py
cp web/app.cfg.example web/app.cfg

# 4. Edit configs
micro core/local_settings.py
micro web/app.cfg

# 5. Install systemd services
sudo ./scripts/setup-systemd.sh

# 6. Setup aliases (optional)
./scripts/setup-aliases.sh
```

## Development Environment

### Current Setup

- **Development**: Mac with macFUSE mounting Raspberry Pi directory
- **Mounted Path**: `/Users/riccardosallusti/pi4/paperGate`
- **Production**: Raspberry Pi 4 with Tailscale, e-Paper HAT
- **Workflow**: Edit on Mac, test on Pi via SSH

### Important Notes

- Hardware dependencies (gpiozero, waveshare drivers) won't work on Mac
- Changes on Mac immediately reflected on Pi via mount
- Testing must be done on Pi4
- Use `micro` for file editing (not nano)

## Threading Model

- **Main thread**: App.loop() handles IPC messages, calls iterate_loop() on current screen
- **EPD thread**: Checks dirty flag and updates physical display
- **Calendar thread**: Periodically fetches events/tasks
- **Weather thread**: Periodically fetches weather data via asyncio

## IPC Protocol

Commands via POSIX message queue `/epdtext_ipc`:

- `button0`, `button1`, `button2`, `button3` - Simulate button press
- `next`, `previous` - Navigate screens
- `reload` - Reload current screen
- `screen <name>` - Switch to named screen
- `add_screen <name>` - Add screen (session-only)
- `remove_screen <name>` - Remove screen (session-only)

## Creating Custom Screens

1. Create file in `core/screens/` (e.g., `myscreen.py`)
2. Import and inherit from `AbstractScreen`
3. Implement `reload()` method
4. Optionally implement `handle_btn_press()` and `iterate_loop()`
5. Add screen name to `SCREENS` list in `local_settings.py`

Example:

```python
from screens import AbstractScreen

class Screen(AbstractScreen):
    def reload(self):
        self.blank()
        self.draw_titlebar("My Screen")
        self.text("Hello World", font_size=40, position=(50, 50))
```

## Git Workflow

### .gitignore Strategy

The `.gitignore` excludes sensitive personal data:

```gitignore
# Configuration with credentials
core/local_settings.py
web/app.cfg

# Runtime screenshots (contain personal IPs, calendar, etc.)
core/display/*.png
core/display/*.txt
!core/display/.gitkeep
```

The `core/display/` directory is tracked (via .gitkeep) but its contents are ignored.

### Commit Guidelines

- Keep commits focused and atomic
- Update CLAUDE.md for significant architectural changes
- Test on Raspberry Pi before pushing
- Use descriptive commit messages

## Troubleshooting

### Display Issues

- Check SPI enabled: `ls /dev/spi*`
- Check service: `pg-status` or `systemctl status papergate`
- Check logs: `pg-log` or `journalctl -u papergate -f`

### Web Interface Issues

- Check service: `systemctl status papergate-web`
- Test locally: `curl http://localhost:5000`
- Check authentication in `web/app.cfg`
- View logs: `pg-web-log`

### IPC/Permission Issues

- Ensure core daemon running first (creates queue)
- Check queue: `ls -la /dev/mqueue/epdtext_ipc`
- Verify permissions (660, group `pi`)

### Feed Not Showing

- Check FEEDS list in `web/app.py`
- Test feed endpoint: `curl http://localhost:5000/feed`
- Verify WEBVIEW_URL in `core/local_settings.py` points to `http://localhost:5000/feed`
- Check feedparser installation: `pip3 list | grep feedparser`

## Dependencies

See `requirements.txt` for complete list. Key dependencies:

- **Display**: Pillow, gpiozero, waveshare_epd
- **Web**: Flask
- **Weather**: python-weather
- **Calendar**: caldav, icalevents, icalendar
- **Feed**: feedparser
- **IPC**: posix_ipc
- **System**: psutil, distro
- **Webview**: htmlwebshot (requires wkhtmltopdf)

## Migration from Old Projects

If migrating from separate epdtext/epdtext-web/epdtext-feed:

1. **Paths**: All `~/epdtext/` → `~/paperGate/core/`
2. **Services**: `epdtext*` → `papergate*`
3. **Aliases**: Update from `epd-*` to `pg-*`
4. **Feed**: Port 8765 → 5000/feed
5. **Config**: `WEBVIEW_URL` must point to `http://localhost:5000/feed`

## Future Enhancements

Planned features (not yet implemented):

- Screenshot display in web interface (per-screen PNGs)
- Web UI screen gallery
- Live preview with WebSocket updates
- Docker/Docker Compose support
- Plugin system for custom screens
- Feed configuration via web UI
- Backup/restore configuration

## Additional Resources

- [README.md](README.md) - User-facing documentation
- [docs/](docs/) - Extended documentation
- Original epdtext: https://github.com/tsbarnes/epdtext
- WaveShare drivers: https://github.com/waveshare/e-Paper
