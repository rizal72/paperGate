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
│   │   ├── weather_providers/  # Weather provider modules (Met.no, OpenWeatherMap, etc.)
│   │   ├── calendar_events.py  # Webcal/CalDAV integration (renamed from calendar.py)
│   │   ├── weather.py          # Weather management with Met.no
│   │   ├── metno_adapter.py    # Adapter for Met.no provider
│   │   └── weather_utility.py  # HTTP caching for weather APIs
│   ├── display/       # Runtime screenshots (gitignored, contains personal data)
│   └── local_settings.py.example
├── web/               # Flask web interface (ex-epdtext-web + epdtext-feed integrated)
│   ├── app.py        # Unified Flask app (control panel + /feed endpoint)
│   ├── system.py     # System information utilities
│   ├── templates/
│   │   ├── index.html    # Main control panel
│   │   └── feed.html     # RSS feed reader
│   └── static/       # Web assets (CSS, logos, favicon)
├── icons/            # Weather SVG icons (60+ from waveshare + calendar icon)
├── cache/            # Runtime temporary files (gitignored)
│   └── webshot.png   # Webview screen webpage screenshot
├── images/           # Shared assets (logos, fallback weather PNGs)
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
- `weather.py`: Weather management using Met.no provider
- `metno_adapter.py`: Adapter bridging Met.no provider with paperGate's Weather class
- `weather_providers/`: Modular weather provider system (Met.no, OpenWeatherMap, AccuWeather, etc.)
- `weather_utility.py`: HTTP caching utilities for weather API calls
- `calendar_events.py`: Webcal/CalDAV integration (renamed from `calendar.py` to avoid stdlib conflict)
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

### Live Screenshot Display

**Feature**: Real-time preview of the physical e-paper display in the web interface.

**How It Works**:

1. **Screenshot Generation** (`core/screens/__init__.py`):
   - Every screen's `show()` method saves a screenshot to `core/display/{screen_name}.png`
   - Screenshots saved immediately after rendering, before physical display update
   - Examples: `system.png`, `weather.png`, `tailscale.png`, etc.

2. **Screen Tracking** (`core/app.py`):
   - `_save_current_screen_name()` method saves current screen to `core/display/current_screen.txt`
   - Called on screen changes (next/previous/switch) and at daemon startup
   - Provides web interface with name of currently displayed screen

3. **Web Endpoints** (`web/app.py`):
   - `/display_screenshot/<screen_name>`: Serves screenshot PNG with no-cache headers
   - `/current_screen_name`: Returns JSON with current screen name
   - Input validation prevents path traversal attacks

4. **Frontend** (`web/templates/index.html`):
   - "Current Display" card shows live screenshot preview
   - Loading overlay with spinner during screen transitions
   - Smart polling: waits for screen name change + 2 second delay for e-paper refresh
   - Auto-refresh every 5 seconds (toggle on/off)
   - Manual refresh button with SVG icon
   - Intercepts navigation clicks and form submissions to show loading state

**Technical Details**:
- Screenshots are gitignored (contain personal data like IPs, calendar events)
- No-cache headers prevent browser from showing stale images
- Loading delay accounts for e-paper physical refresh time (~2-3 seconds)
- `forceRefresh` parameter bypasses `isLoading` check for immediate updates
- Form interception uses `preventDefault()` and `fetch()` to avoid page reloads

**User Experience**:
- Click Next/Previous/Switch → Loading overlay appears
- Poll for screen name change → Wait 2 seconds → Load new screenshot
- Loading disappears only when new image is fully loaded in browser
- Provides immediate visual feedback when controlling display remotely

## Weather System

**Major Update (Dec 2025)**: Complete weather system replacement from python_weather to Met.no provider with professional SVG icons.

### Met.no Weather Provider

**Why Met.no**:
- Norwegian Meteorological Institute - reliable, free, no API key required
- 42 weather conditions (vs 18 with python_weather) - better granularity
- 60+ professional SVG weather icons with day/night distinction
- Clean JSON API with 6-hour forecast data
- Used by waveshare-epaper-display project (proven reliable)

**Architecture**:
```
Weather class → MetnoAdapter → Met.no Provider → API
                      ↓
              SVG Icon Rendering (CairoSVG)
                      ↓
              PIL Image (1-bit for e-paper)
```

**Key Components**:
- `libs/weather.py`: Main Weather class (threading, data management)
- `libs/metno_adapter.py`: Bridge between Met.no provider and paperGate API
- `libs/weather_providers/metno.py`: Met.no API implementation from waveshare
- `libs/weather_providers/base_provider.py`: Base class for all weather providers
- `libs/weather_utility.py`: HTTP caching and utilities

**SVG Icon Rendering**:
- 60+ SVG icons in `icons/` directory (clear_sky_day.svg, rain_heavy.svg, etc.)
- SVG embedding technique: wrap icon content in SVG with white background
- CairoSVG renders SVG → PNG in memory
- Convert to 1-bit PIL Image for e-paper display
- Fallback to basic PNG icons if SVG rendering fails

**Temperature Data**:
- **Instant temperature**: Current real-time temperature from `air_temperature` field
- **Min/max range**: 6-hour forecast period temperatures
- All three values exposed through MetnoAdapter methods

**Configuration** (see Settings section below):
- `WEATHER_LATITUDE`: Location latitude (e.g., 45.4642 for Milan)
- `WEATHER_LONGITUDE`: Location longitude (e.g., 9.1900 for Milan)
- `WEATHER_CITY_NAME`: City name for display (e.g., "Milano")
- `WEATHER_CONTACT_EMAIL`: Contact email (required by Met.no Terms of Service)
- `WEATHER_REFRESH`: Update interval in seconds (default: 900 = 15 min)

**Day/Night Icon Logic**:
- Built into Met.no provider using astral library
- Calculates sunrise/sunset times based on coordinates
- Returns different icons: `clear_sky_day.svg` vs `clearnight.svg`

**User-Agent Compliance**:
- Met.no Terms of Service require User-Agent with app name and contact email
- Format: `"paperGate/1.0 (email@example.com)"`
- MetnoAdapter constructs this automatically from `WEATHER_CONTACT_EMAIL` setting
- Used only if Met.no needs to contact about API usage issues

**Screen Layouts**:

*Dashboard Screen* (Dec 2025 refinements):
- **Top section**: Time (37px bold left), Day/Date (17px/15px right, 8px margin)
- **Vertical divider**: x=88, stops 8px from bottom for visual separation
- **Left section (weather, 0-88px)**:
  - Icon 50px centered, raised to y=60
  - Current temp 18px bold, 3px below icon
  - Description 11px: multi-line word wrap, 2px line spacing, max 2 lines
  - All elements centered in left section
- **Right section (calendar, 88-264px)**:
  - Calendar icon 18px at (98, 55)
  - Up to 3 events: date 8px, title 10px bold, 30px spacing
  - Character limits: date 30 chars, title 35 chars
- Auto-refresh every minute (iterate_loop)

*Weather Screen* (Dec 2025 redesign):
- **Icon + Temperature block** (centered horizontally, raised 10px):
  - Icon 70px on left
  - Gap 8px between icon and text
  - Current temp 32px bold + range 15px bold with arrows: "6° (↑9°↓7°)"
  - Baseline aligned, 4px offset to compensate SVG margin
  - No space between arrows and values
- **Description** 20px regular, centered below
- **Location** 18px bold, centered at bottom
- Compact spacing optimized for 264x176 display

**Migration Notes**:
- Removed python_weather and asyncio dependencies
- calendar.py renamed to calendar_events.py (avoid stdlib conflict)
- No breaking API changes - Weather class maintains same public interface
- SVG icons auto-scale for any size (default: 50px dashboard, 85px weather screen)

## Calendar Events

**Update (Dec 2025)**: Enhanced calendar events with start-end times and all-day event detection.

**Module Rename**:
- `libs/calendar.py` → `libs/calendar_events.py`
- Reason: Avoid conflict with Python standard library `calendar` module
- All imports updated throughout codebase

**Event Data Structure**:
```python
{
    'start': datetime,     # Event start time
    'end': datetime,       # Event end time (added Dec 2025)
    'summary': str         # Event title
}
```

**Time Display**:
- Events with times: "Dec 12 18:30-20:15" or "Today 18:30-20:15"
- All-day events: "Dec 12" or "Today" (no time shown)
- All-day detection: Both start and end at 00:00:00

**Dashboard Screen**:
- Shows up to 3 upcoming events
- Date/time line (8px): Humanized date + time range
- Title line (10px bold): Event summary
- Calendar icon (18px) aligned with event list
- Character limits: date 30 chars, title 35 chars (with "..." truncation)

**Event Sources**:
- Webcal: Uses icalevents library, extracts `event.start` and `event.end`
- CalDAV: Uses caldav library, extracts `dtstart.value` and `dtend.value`
- Both standardized through `standardize_date()` method

**Auto-Refresh**:
- Dashboard screen refreshes every minute via `iterate_loop()`
- Calendar data refreshes every `CALENDAR_REFRESH` seconds (configurable)
- Thread-safe updates with `thread_lock`

## Network Resilience

**Update (Feb 2026)**: Robust network handling for power recovery scenarios.

### Problem

When power is restored, the Raspberry Pi boots faster than the router, causing network-dependent operations (calendar/weather fetch) to fail at startup. The app would hang on "Loading calendars..." until manual restart.

### Solution

**Three-layer protection**:

1. **Wait-for-network at startup** (`core/app.py`):
   - `_wait_for_network()` method called before calendar/weather initialization
   - Tests TCP connectivity to Google DNS (8.8.8.8:53) and Cloudflare (1.1.1.1:53)
   - Maximum 3 minutes timeout (configurable)
   - Shows "Waiting network... (Xs)" on e-paper display during wait
   - Returns True when connectivity confirmed, proceeds with app startup

2. **Wait-for-DNS at startup** (`core/app.py`):
   - `_wait_for_dns()` method called after network connectivity confirmed
   - Tests actual DNS resolution to real domains: calendar.google.com, outlook.office365.com, google.com, cloudflare.com
   - Uses `socket.gethostbyname()` to verify DNS resolver is working
   - Maximum 60 seconds timeout (configurable)
   - Shows "Waiting DNS... (Xs)" on e-paper display during wait
   - Returns True when DNS resolution confirmed, then loads calendars
   - Critical fix: Prevents "Temporary failure in name resolution" errors when router is slow to provide DNS service

3. **Exponential backoff retry** (`core/libs/calendar_events.py`):
   - `@retry_with_backoff()` decorator for network operations
   - Retries on: ConnectionError, TimeoutError, SSLError, NewConnectionError, ServerNotFoundError
   - Exponential backoff: 1s → 2s → 4s → 8s → 16s (max 60s)
   - Maximum 5 retry attempts per operation
   - Applies to: webcal fetch, CalDAV connection, calendar events fetch, todos fetch
   - Graceful degradation: continues with partial data if some sources fail

### Configuration

```python
# Retry settings (calendar_events.py)
MAX_RETRY_ATTEMPTS = 5
INITIAL_RETRY_DELAY = 1  # seconds
MAX_RETRY_DELAY = 60  # seconds

# Network wait settings (app.py)
def _wait_for_network(self, timeout=180):  # 3 minutes default
def _wait_for_dns(self, timeout=60):  # 1 minute default
```

### Systemd Integration

**papergate.service** updated with `network-online.target`:
```ini
[Unit]
After=network.target network-online.target
Wants=network-online.target
```

Note: On Raspbian with dhcpcd, `network-online.target` alone is insufficient. The application-level `_wait_for_network()` provides reliable connectivity verification.

### Benefits

- **No manual intervention**: App starts successfully even when router is slow to boot
- **Resilient operation**: Recovers from temporary network glitches during runtime
- **Clear feedback**: Display shows waiting status during network initialization
- **Graceful degradation**: Continues with available data if some calendars fail permanently

## Calendar Screen

**Redesign (Dec 2025)**: Complete redesign to match dashboard style and improve consistency.

**Layout**:
- **Calendar icon**: 20px SVG at (10, 35)
- **Event list** starting at y=60:
  - Date/time: 10px regular, humanized format + time range
  - Title: 12px bold, **single line only** with `wrap=False`
  - Spacing: 30px between events
  - Max 5 events visible

**Text Truncation**:
- Date/time: 40 characters max (37 + "...")
- Title: 34 characters max (static truncation to prevent wrapping)
- Important: Must use `wrap=False` in `self.text()` call to prevent automatic line wrapping

**Design Principles**:
- Matches dashboard calendar section format
- Consistent font sizes and spacing
- Clean 10px left margin
- All-day event detection (no time shown if start/end at 00:00:00)

**Key Implementation Detail**:
The `AbstractScreen.text()` method has `wrap=True` by default and uses `textwrap.fill()` for automatic wrapping. To keep titles on a single line, always pass `wrap=False` explicitly.

## Configuration

**IMPORTANT:** All configuration is now unified in a single file: `local_settings.py` (in project root)
This includes display settings, web interface authentication, RSS feeds, and all other options.

**Architecture:** `core/settings.py` acts as a centralized wrapper that imports from `local_settings.py` and provides defaults for all configuration variables. All code (core, libs, screens, web) imports through `settings` module, never directly from `local_settings`.

### Settings (local_settings.py)

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

# Weather configuration - Met.no provider (Norwegian Meteorological Institute)
WEATHER_LATITUDE = 45.4642    # Milan, Italy
WEATHER_LONGITUDE = 9.1900
WEATHER_CITY_NAME = "Milano"
WEATHER_CONTACT_EMAIL = "your.email@example.com"  # Required by Met.no Terms of Service
WEATHER_REFRESH = 900          # Refresh interval in seconds (default: 15 min)

# Webview points to integrated feed
WEBVIEW_URL = 'http://localhost:5000/feed'
WEBVIEW_SCALE = 0.8
WEBVIEW_ORIENTATION = 'landscape'

# Logo path uses new structure
LOGO = '/home/pi/paperGate/images/raspberry-pi.png'
```

### Web Interface Settings (also in local_settings.py)

All web configuration is now unified in `local_settings.py`:

```python
# Web Interface Authentication (IMPORTANT: Change these!)
AUTH_USERNAME = 'admin'
AUTH_PASSWORD = 'your-secure-password'

# Flask secret key (generate with: python3 -c 'import os; print(os.urandom(16))')
SECRET_KEY = b'your-secret-key-here'

# RSS Feed Sources
FEEDS = [
    'https://www.ansa.it/sito/ansait_rss.xml',  # ANSA Italia
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

# 3. Create config file
cp local_settings.py.example local_settings.py

# 4. Edit config (all settings in one file)
micro local_settings.py

# 5. Install systemd services
sudo ./scripts/setup-systemd.sh

# 6. Setup aliases (optional)
./scripts/setup-aliases.sh
```

## Development Environment

### Important Notes

- Hardware dependencies (gpiozero, waveshare drivers) won't work on Mac/Windows
- Testing must be done on Pi4 hardware
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

## Screen Details

### Webview Screen

The webview screen displays webpage screenshots on the e-paper display using wkhtmltoimage.

**Features:**
- Asynchronous rendering in background thread (non-blocking)
- Screenshot caching to avoid re-rendering on every screen change
- Screenshots saved to `cache/webshot.png` (gitignored)
- Configurable auto-refresh interval (default: 5 minutes)
- Manual refresh via KEY1 button
- Loading/rendering status messages
- Multiple rendering strategies with fallback

**Configuration** (add to `local_settings.py`):
```python
WEBVIEW_URL = "http://localhost:5000/feed"  # URL to render
WEBVIEW_RELOAD_INTERVAL = 300  # Seconds between auto-refreshes (default: 300 = 5 minutes)
WEBVIEW_SCALE = 0.8  # Scale factor for webpage (default: 0.5)
WEBVIEW_ORIENTATION = 'landscape'  # 'landscape' or 'portrait' (default: 'landscape')
```

**Note on WEBVIEW_SCALE:**
- `0.5`: Captures webpage at 2x size, scales to 50% - shows more content
- `1.0`: Captures at display size (no scaling) - less content, larger text
- `0.25`: Captures at 4x size, scales to 25% - entire page, smaller text

**Note on WEBVIEW_ORIENTATION:**
- `'landscape'` (default): Renders as 844x390 viewport (wide) - good for news sites
- `'portrait'`: Renders as 390x844 viewport (tall) - good for mobile-first sites

**Dependencies:**
```bash
sudo apt install wkhtmltopdf
sudo pip3 install htmlwebshot
```

**Behavior:**
- First load: Shows "Loading webpage..." message while rendering (~1-2 minutes)
- Subsequent loads: Shows cached screenshot immediately, refreshes in background
- KEY1: Force refresh (clears cache and starts new render)
- Auto-refresh: Re-renders every `WEBVIEW_RELOAD_INTERVAL` seconds
- Screenshots saved to `cache/webshot.png` for reuse

**Common Use:** By default configured to show integrated RSS feed reader at `http://localhost:5000/feed`

### Tailscale Screen

The Tailscale screen displays VPN connection status, network information, and connected peers.

**Update (Dec 2025)**: Improved peers list layout for better readability.

**Layout:**
- **Top section**: Tailscale icon (55x55) and status information
  - Connection status (Connected/Disconnected)
  - Local IP address
  - Tailscale IP address
  - Exit node status (Available/Disabled)
- **Horizontal divider**: y=95
- **Peers section**: "Peers: X online" header at y=101
  - **2-column layout** at 50% width each (col1_x=8, col2_x=140)
  - 132px spacing between columns for better readability
  - Up to 5 peers per column (10 total visible)
  - Overflow handling: Shows first 9 peers + "• +N more..." if >10 peers total

**Peer List Features:**
- Two columns with equal width distribution
- Improved spacing compared to previous 3-column layout
- Automatic overflow indication prevents visual clipping
- Starting position y=120 (raised 10px from original 130px)
- 10px vertical spacing between peers

**Example overflow:**
- With 15 total peers: Shows 9 named peers + "• +6 more..."
- Prevents overlap and maintains clean layout

**Auto-refresh**: Every 30 seconds via `reload_interval`

## Git Workflow

### .gitignore Strategy

The `.gitignore` excludes sensitive personal data:

```gitignore
# Configuration with credentials
local_settings.py

# Runtime screenshots (contain personal IPs, calendar, etc.)
core/display/*.png
core/display/*.txt
!core/display/.gitkeep

# Cache files and directories (simplified Dec 2025)
*cache*
!cache/.gitkeep
```

**Key patterns**:
- `*cache*`: Catches all cache files/directories anywhere in project (weather cache, webshots, etc.)
- `core/display/` directory is tracked (via .gitkeep) but contents are ignored
- Simplified from multiple cache-specific entries to single generic pattern

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
- Check authentication settings in `local_settings.py` (AUTH_USERNAME, AUTH_PASSWORD)
- View logs: `pg-web-log`

### IPC/Permission Issues

- Ensure core daemon running first (creates queue)
- Check queue: `ls -la /dev/mqueue/epdtext_ipc`
- Verify permissions (660, group `pi`)

### Feed Not Showing

- Check FEEDS list in `web/app.py`
- Test feed endpoint: `curl http://localhost:5000/feed`
- Verify WEBVIEW_URL in `local_settings.py` points to `http://localhost:5000/feed`
- Check feedparser installation: `pip3 list | grep feedparser`

## Dependencies

See `requirements.txt` for complete list. Key dependencies:

- **Display**: Pillow, gpiozero, waveshare_epd
- **Web**: Flask
- **Weather**: cairosvg (SVG rendering), astral (day/night calculation), requests (HTTP API calls)
- **Calendar**: caldav, icalevents, icalendar, humanize, pytz
- **Feed**: feedparser
- **IPC**: posix_ipc
- **System**: psutil, distro
- **Webview**: htmlwebshot (requires wkhtmltopdf)

**Removed Dependencies** (Dec 2025):
- python-weather: Replaced by Met.no provider
- asyncio: No longer needed with synchronous Met.no implementation

## Migration from Old Projects

If migrating from separate epdtext/epdtext-web/epdtext-feed:

1. **Paths**: All `~/epdtext/` → `~/paperGate/core/`
2. **Services**: `epdtext*` → `papergate*`
3. **Aliases**: Update from `epd-*` to `pg-*`
4. **Feed**: Port 8765 → 5000/feed
5. **Config**: `WEBVIEW_URL` must point to `http://localhost:5000/feed`

## Future Enhancements

Planned features (not yet implemented):

- Web UI screen gallery (show all available screens)
- Live preview with WebSocket updates (instead of polling)
- Docker/Docker Compose support
- Plugin system for custom screens
- Feed configuration via web UI (instead of editing app.py)
- Backup/restore configuration
- Mobile app (React Native or PWA)

## Additional Resources

- [README.md](README.md) - User-facing documentation
- [docs/](docs/) - Extended documentation
- Original epdtext: https://github.com/tsbarnes/epdtext
- WaveShare drivers: https://github.com/waveshare/e-Paper

## Project Promotion Strategy

### Target Channels

**Reddit (High Priority):**
- r/raspberry_pi (~500k) - Main Raspberry Pi community
- r/selfhosted (~500k) - Self-hosting and home server enthusiasts
- r/homeassistant (~400k) - Home automation community
- r/linux (~1.5M) - General Linux community
- r/eink (~20k) - E-paper display niche
- r/tailscale (~10k) - Tailscale integration users

**Reddit Best Practices:**
- Post timing: Tuesday-Thursday morning (8-10 AM EST)
- Include dashboard screenshot + brief feature description
- Title format: "paperGate: Raspberry Pi gateway with e-Paper display for home monitoring (Tailscale, Weather, Calendar, Web UI)"
- Link to GitHub + video demo if possible

**Hacker News:**
- Format: "Show HN: paperGate – Raspberry Pi e-Paper Display Gateway"
- HN appreciates: detailed documentation, clean code, demo screenshots
- Link directly to README or landing page

**GitHub Optimization:**
- Topics to add: raspberry-pi, epaper, e-ink, home-automation, tailscale, weather, python, flask, waveshare
- Ensure repo has clear description and topics
- Add GitHub Social Preview image (1280x640px with logo + screenshots)

**Specialized Forums/Blogs:**
- Raspberry Pi Forums - https://forums.raspberrypi.com/ (Projects section)
- Hackaday.io - Hardware project platform with photo/video
- Hackster.io - Project showcase with tutorials

**Social Media:**
- Twitter/X thread with physical display photos, feature demos, repo link
- Hashtags: #RaspberryPi #EPaper #HomeAutomation #SelfHosted #Tailscale
- Mastodon: fosstodon.org, hachyderm.io

**Newsletters/Aggregators:**
- Hacker Newsletter (if featured on HN front page)
- Console.dev (developer tools newsletter)
- Pi Weekly (Raspberry Pi dedicated newsletter)

**Communities/Discord:**
- Raspberry Pi Discord
- Self-Hosted Discord
- Homelab Discord

### Pre-Launch Checklist

**Completed:**
- High-quality screenshots with demo data
- Clear and detailed README
- Complete installation guide
- MIT License

**To Do:**
- GitHub Social Preview image (1280x640px with logo + screenshot grid)
- CHANGELOG or Release notes
- Enable GitHub Issues/Discussions for community engagement
- Contributing guide (optional but appreciated)
- Video demo (optional but highly effective)

### Rollout Strategy

**Phase 1 (Week 1):**
1. Create GitHub Social Preview image
2. Add topics to repository
3. Post on r/raspberry_pi (most receptive audience)
4. Post on r/eink (dedicated niche)

**Phase 2 (Week 2):**
1. If positive feedback, post on r/selfhosted
2. Show HN submission
3. Twitter/X thread with physical setup photos

**Phase 3 (Ongoing):**
1. Specialized forums (Raspberry Pi Forums, Hackaday)
2. Respond to questions and feedback
3. Consider YouTube video demo

### Key Selling Points

1. **Met.no weather integration** - 60+ professional SVG icons, no API key required
2. **Tailscale integration** - Trending topic, highly appreciated by community
3. **Monorepo architecture** - Easy to clone and deploy
4. **Modern web interface** - Responsive and feature-rich
5. **Demo screenshots** - Anonymized data shows attention to detail
6. **Comprehensive documentation** - Including CLAUDE.md for developers
7. **Multiple screen types** - Dashboard, system stats, weather, calendar, Tailscale monitoring
8. **Professional SVG icons** - 42 weather conditions with day/night distinction
9. **Easy installation** - One-line script with automated setup
10. **Active development** - Recent commits, well-maintained

### Content Templates

**Reddit Post Example:**
- Title: paperGate: Raspberry Pi gateway with e-Paper display for home monitoring
- Body: Feature list, tech stack, GitHub link, screenshots
- Include: Dashboard photo, key features, tech details
- Call to action: Happy to answer questions

**Show HN Example:**
- Title: Show HN: paperGate – Raspberry Pi e-Paper Display Gateway
- Body: Project description, motivation, key features, GitHub link
- Emphasize: Monorepo, no API key, web interface, documentation
- Tone: Collaborative, asking for feedback

### Post-Launch Activities

- Monitor and respond to comments/questions promptly
- Update README with featured badges if picked up
- Create Issues for feature requests from community
- Consider creating Discussions section for Q&A
- Track analytics (GitHub stars, clones, traffic)
- Document feedback and iterate on improvements


## Release v2.0.0 Preparation (2024-12-10)

### Completed Pre-Launch Tasks

**CHANGELOG & Release:**
- ✅ CHANGELOG.md updated with v2.0.0 release notes
- ✅ Git tag v2.0.0 created and pushed to GitHub
- ✅ Merged develop → main for stable release

**GitHub Optimization:**
- ✅ GitHub Social Preview image created (1280x640px)
  - Location: 
  - Logo centered at top (papergate-icon.svg)
  - 4 screenshots in horizontal layout: dashboard, system_dashboard, system, tailscale
  - Official brand colors: #6b7280 (gray), #94a3b8 (slate), #f5a5a5 (red)
  - Features line: Weather • Calendar • System Dashboard • Tailscale • Live Web Interface
- ✅ Social preview uploaded to GitHub Settings
- ✅ Repository topics added via gh CLI:
  - raspberry-pi, epaper, e-ink, home-automation, tailscale, weather, python, flask, waveshare

**Screenshot Enhancement:**
- ✅ All 6 screenshots enhanced with soft shadow effect
  - Gaussian blur (4px radius) with slate (#94a3b8) color
  - 2px offset for subtle depth
  - 12px margins on all sides to prevent cropping
  - Professional, modern appearance matching brand design

**Developer Tools:**
- ✅ GitHub CLI (gh) installed on pi4 for automation
- ✅ Authenticated as rizal72 for repository management

**Python Scripts Created:**
- : Generates GitHub social preview with logo and screenshots
- : Applies soft shadow effect to documentation screenshots

### Ready for Launch

The repository is now fully optimized for community promotion with:
- Professional visual identity (logo, colors, shadows)
- Complete documentation (README, CHANGELOG, CLAUDE.md)
- GitHub discoverability (topics, social preview)
- v2.0.0 stable release with significant features

**Next Steps:**
1. Post on r/raspberry_pi with social preview card
2. Post on r/eink for niche community
3. Enable GitHub Issues/Discussions for community engagement
4. Monitor feedback and respond to questions

**Phase 1 Timing:**
- Best posting time: Tuesday-Thursday, 8-10 AM EST
- Include social preview image in Reddit post
- Link directly to GitHub repository


## Release v2.0.0 Preparation (2024-12-10)

### Completed Pre-Launch Tasks

**CHANGELOG & Release:**
- ✅ CHANGELOG.md updated with v2.0.0 release notes
- ✅ Git tag v2.0.0 created and pushed to GitHub
- ✅ Merged develop → main for stable release

**GitHub Optimization:**
- ✅ GitHub Social Preview image created (1280x640px)
  - Location: branding/social-preview.png
  - Logo centered at top (papergate-icon.svg)
  - 4 screenshots in horizontal layout: dashboard, system_dashboard, system, tailscale
  - Official brand colors: #6b7280 (gray), #94a3b8 (slate), #f5a5a5 (red)
  - Features line: "Weather • Calendar • System Dashboard • Tailscale • Live Web Interface"
- ✅ Social preview uploaded to GitHub Settings
- ✅ Repository topics added via gh CLI:
  - raspberry-pi, epaper, e-ink, home-automation, tailscale, weather, python, flask, waveshare

**Screenshot Enhancement:**
- ✅ All 6 screenshots enhanced with soft shadow effect
  - Gaussian blur (4px radius) with slate (#94a3b8) color
  - 2px offset for subtle depth
  - 12px margins on all sides to prevent cropping
  - Professional, modern appearance matching brand design

**Developer Tools:**
- ✅ GitHub CLI (gh) installed on pi4 for automation
- ✅ Authenticated as rizal72 for repository management

**Python Scripts Created:**
- create_social_preview.py: Generates GitHub social preview with logo and screenshots
- add_shadow_to_screenshots.py: Applies soft shadow effect to documentation screenshots

### Ready for Launch

The repository is now fully optimized for community promotion with:
- Professional visual identity (logo, colors, shadows)
- Complete documentation (README, CHANGELOG, CLAUDE.md)
- GitHub discoverability (topics, social preview)
- v2.0.0 stable release with significant features

**Next Steps:**
1. Post on r/raspberry_pi with social preview card
2. Post on r/eink for niche community
3. Enable GitHub Issues/Discussions for community engagement
4. Monitor feedback and respond to questions

**Phase 1 Timing:**
- Best posting time: Tuesday-Thursday, 8-10 AM EST
- Include social preview image in Reddit post
- Link directly to GitHub repository
