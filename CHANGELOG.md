# Changelog

All notable changes to paperGate will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0] - 2025-12-10

### Added

- **Live screenshot display**: Real-time preview of e-paper display in web interface
  - Auto-refresh every 5 seconds (toggleable)
  - Manual refresh button
  - Loading overlay during screen transitions
  - Smart polling with 2-second delay for e-paper refresh
- **Met.no weather provider**: Professional weather integration with 60+ SVG icons
  - Norwegian Meteorological Institute API (no API key required)
  - 42 weather conditions (vs 18 with python-weather)
  - Day/night icon distinction using astral library
  - SVG icon rendering with CairoSVG
  - Instant temperature + min/max range display
  - Weather cache file for API efficiency
  - User-Agent email configuration for Terms of Service compliance
- **Branding assets**: Professional logo system
  - Full logo and icon variants
  - Favicon for web interface
  - Responsive header with desktop/mobile layouts
- **Screenshot gallery**: Visual documentation in README
- **Calendar enhancements**: Start-end time ranges and all-day event detection

### Changed

- **BREAKING: Configuration unification** - All settings now in single `local_settings.py` in project root
  - Unified core and web settings
  - Centralized imports through `settings.py` module
  - Requires migration from old split configuration files
- **BREAKING: Weather system replacement** - Complete migration from python-weather to Met.no
  - Different configuration parameters (latitude/longitude, city name, email)
  - SVG icons replace PNG icons
  - No more asyncio dependency
- **Screen redesigns**:
  - Calendar screen matches dashboard style with improved spacing
  - Weather screen shows instant temperature with refined layout
  - Dashboard improved spacing, divider, and multi-line weather descriptions
  - Tailscale screen enhanced layout spacing
- **Web interface improvements**:
  - Screenshot display enlarged by 20%
  - Improved loading overlay
  - Better header logo layout for desktop and mobile
  - Enhanced responsive design
- **Project organization**:
  - Webshot moved to `cache/` directory
  - Simplified `.gitignore` cache patterns (now uses `*cache*`)
  - Updated documentation references (nano instead of micro in README)

### Fixed

- Tailscale local IP detection with correct `local_settings.py` path
- WaveShare driver installation using pip3 instead of deprecated setup.py
- Python dict syntax errors in WaveShare installation
- File permissions issues during installation
- install-deps.sh path resolution when called with sudo

### Removed

- `python-weather` dependency (replaced by Met.no)
- `asyncio` dependency for weather (no longer needed with synchronous Met.no)
- CLAUDE.md from version control (kept as local development file only)

### Technical Details

Updated dependencies:
- **Added**: cairosvg (SVG rendering), astral (day/night calculation)
- **Removed**: python-weather, asyncio
- **Weather provider**: Met.no (Norwegian Meteorological Institute)
- **Icons**: 60+ professional SVG weather icons with day/night variants

## [1.0.0] - 2024-12-04

### Added

- **Monorepo architecture**: Unified epdtext, epdtext-web, and epdtext-feed into single paperGate repository
- **Core daemon** (`core/`): E-paper display manager with modular screen system
- **Web interface** (`web/`): Remote control panel with HTTP Basic Auth
- **Integrated RSS feed reader**: Feed reader built into web interface at `/feed` endpoint
- **Installation automation**: Complete setup scripts for turnkey deployment
- **Command aliases**: Convenient `pg-*` aliases for service management
- **Systemd services**: Two services (papergate + papergate-web) with proper dependencies
- **Documentation**: Comprehensive README, CLAUDE.md, and docs/ directory

#### Screens

- `system`: Raspberry Pi system information
- `tailscale`: Tailscale VPN status and peer monitoring
- `system_dashboard`: Visual pie chart dashboard for system metrics
- `weather`: Current weather and forecast
- `calendar`: Calendar events from webcal/CalDAV
- `tasks`: Todo list from CalDAV
- `dashboard`: Combined information view
- `fortune`: Random fortune cookies
- `affirmations`: Positive affirmations
- `webview`: Webpage screenshot rendering (displays RSS feed by default)

#### Features

- IPC communication via POSIX message queue
- Hardware button support (WaveShare e-Paper HAT)
- CLI control via `cli.py`
- Web-based screen management (add/remove screens)
- Threaded weather and calendar updates
- Async webpage rendering for webview screen
- Per-screen configuration and auto-refresh
- Session-only screen management (preserves local_settings.py)

### Changed

- **Service consolidation**: Reduced from 3 services to 2 (integrated feed into web)
- **Path structure**: All paths relative to project root (`~/paperGate/`)
- **Feed endpoint**: RSS reader moved from `:8765` to `:5000/feed`
- **Configuration**: Unified settings with clear separation (core vs web)
- **Logo path**: Updated to use shared `images/` directory

### Technical Details

- Python 3.9+
- Flask web framework
- WaveShare 2.7in e-Paper HAT (V2) support
- Tailscale integration
- CalDAV/webcal calendar support
- Feedparser for RSS feeds
- Async weather fetching with python-weather
- PIL/Pillow for image manipulation
- psutil for system metrics

## [Future Enhancements]

Features planned for future releases:

- WebSocket updates for real-time display monitoring (no polling)
- Screen gallery in web UI
- Feed configuration via web interface (no file editing)
- Docker/Docker Compose support
- Plugin system for custom screens
- Backup/restore configuration functionality
- Multi-language support
- Theme customization for web interface

---

## Legacy Projects (Pre-Monorepo)

### epdtext
Original e-paper display daemon by tsbarnes, forked and extended with:
- Tailscale screen
- System dashboard with pie charts
- Enhanced weather display
- Improved calendar integration

### epdtext-web
Flask web interface for remote control:
- HTTP Basic Auth
- Dynamic screen management
- System information display
- IPC message queue integration

### epdtext-feed
Minimal RSS feed reader optimized for e-paper:
- Black and white design
- Compact layout
- Auto-updating feed display
- Multiple source support

All three projects have been unified into paperGate as of v1.0.0.
