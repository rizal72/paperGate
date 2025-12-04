# Changelog

All notable changes to paperGate will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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

## [Unreleased]

### Planned

- Screenshot display in web interface
- Live preview with auto-refresh
- WebSocket updates for real-time display monitoring
- Screen gallery in web UI
- Feed configuration via web interface
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
