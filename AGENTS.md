# paperGate Agent Instructions

This file provides guidelines for agentic coding assistants working with paperGate codebase.

## Project Context

paperGate is a Raspberry Pi e-paper display gateway with weather, calendar, system monitoring, and Tailscale VPN status. It's a Python-based monorepo (core/ for daemon, web/ for Flask UI) running on Raspberry Pi 4.

## Development Commands

### Installation & Setup
```bash
# Quick install (on Raspberry Pi)
sudo ./scripts/install.sh
./scripts/setup-aliases.sh

# Manual setup
sudo ./scripts/install-deps.sh
cp local_settings.py.example local_settings.py
sudo ./scripts/setup-systemd.sh
```

### Service Management
```bash
# Using aliases (recommended)
pg-start        # Start both services
pg-stop         # Stop both services
pg-restart      # Restart both services
pg-status       # Show status
pg-log          # Follow core daemon logs
pg-web-log      # Follow web interface logs

# Direct systemd commands
sudo systemctl start papergate papergate-web
sudo systemctl status papergate papergate-web
journalctl -u papergate -f
```

### Running & Testing
```bash
# Core daemon (directly)
cd core && python3 app.py

# Web interface
cd web && python3 app.py

# CLI control (when daemon running)
cd core && ./cli.py next
./cli.py screen weather
./cli.py reload
```

### Python Dependencies
```bash
# Install dependencies
pip3 install -r requirements.txt

# List installed packages
pip3 list | grep -E "(flask|gpiozero|waveshare)"
```

## Code Style Guidelines

### Python Conventions

**Imports:**
- Use absolute imports for project modules: `from libs.calendar_events import Calendar`
- Use relative imports only within same package
- Group imports: standard library, third-party, local modules
- Order: `import sys` → `import flask` → `import settings`

**Type Hints:**
- Use type hints for function signatures (not strictly enforced)
- Return types recommended: `def reload(self) -> None:`
- Complex types: `from collections.abc import Generator`

**Naming:**
- Classes: PascalCase (`class AbstractScreen`)
- Functions/Methods: snake_case (`def reload(self)`)
- Constants: UPPER_SNAKE_CASE (`MAX_RETRY_ATTEMPTS = 5`)
- Private methods: single underscore (`def _render_icon(self)`)
- Module-level loggers: `logger = logging.getLogger('module.name')`

**Formatting:**
- 4 spaces indentation (no tabs)
- Max line length: ~100-120 characters (not strict)
- Docstrings: Use Google style or simple description
- Comments: Use `#` for single-line, minimal inline comments

**Error Handling:**
- Always use try/except for I/O operations (file access, network)
- Log errors instead of print: `logger.error(f"Failed: {e}")`
- Use specific exceptions: `except FileNotFoundError as e:`
- Graceful degradation for non-critical features (e.g., screenshot saving)
- Network operations: Use `@retry_with_backoff` decorator for resilience

**Logging:**
- Use `logging` module, never `print()`
- Configure logger per module: `logger = logging.getLogger('pitftmanager.libs.calendar')`
- Levels: `logger.debug()` for verbose, `logger.error()` for failures
- Debug logs only when `settings.DEBUG` is True

**Threading:**
- Main thread: Event loop, IPC message processing
- Background threads: Calendar fetch, weather fetch, display updates
- Use `threading.Lock()` for shared state
- Check thread safety when accessing shared resources

## Screen Development

### Creating Screens

1. Inherit from `AbstractScreen` in `core/screens/myscreen.py`
2. Implement required `reload()` method
3. Optional: `handle_btn_press(button_number)` for button interaction
4. Optional: `iterate_loop()` for periodic updates (called every second)
5. Add to `SCREENS` list in `local_settings.py`

**Example Screen:**
```python
import logging
from screens import AbstractScreen

class Screen(AbstractScreen):
    reload_interval = 60  # Seconds between auto-reloads
    logger = logging.getLogger('screens.myscreen')

    def reload(self):
        self.blank()
        self.text("Hello World", font_size=40, position=(50, 50))
```

### Screen API

**Core Methods:**
- `self.blank()`: Clear screen (creates new 1-bit image)
- `self.text()`: Draw text with word wrapping (default: `wrap=True`)
- `self.centered_text()`: Center text horizontally
- `self.line()`: Draw lines (useful for dividers)
- `self.draw_titlebar()`: Draw horizontal title bar
- `self.show()`: Render to physical display + save screenshot

**Text Wrapping:**
- Default: `self.text()` wraps automatically (`wrap=True`)
- Single line: Pass `wrap=False` explicitly
- Character limits: Truncate with `"..."` to prevent overflow

**Screenshot Generation:**
- Automatic in `show()` method (saves to `core/display/{screen_name}.png`)
- Gitignored (contains personal data)
- Used by web interface for live preview

## Configuration

**All settings in `local_settings.py` (project root)**
- Never hardcode paths or credentials
- Use `settings` module wrapper: `import settings`
- `core/settings.py` provides defaults if missing in `local_settings.py`

**Key Settings:**
- `DRIVER`: e-paper driver model (`epd2in7b_V2`)
- `SCREENS`: List of active screen modules
- `CALENDAR_URLS`: Webcal/CalDAV calendar sources
- `WEATHER_LATITUDE/LONGITUDE`: Location for weather
- `DEBUG`: Enable verbose logging
- `SAVE_SCREENSHOTS`: Save debug screenshots with UUID

## Web Interface

**Routes in `web/app.py`:**
- `/`: Main control panel (HTML template)
- `/feed`: RSS feed reader (integrated, no separate service)
- `/display_screenshot/<screen_name>`: Serve screen screenshots
- `/current_screen_name`: Return JSON with current screen
- POST endpoints: `/next_screen`, `/previous_screen`, `/switch_screen`

**Authentication:**
- HTTP Basic Auth via `AUTH_USERNAME` / `AUTH_PASSWORD`
- Flask `SECRET_KEY` for session management

## Important Notes

**Hardware Dependencies:**
- Code runs on Raspberry Pi 4 (not Mac/Windows dev machines)
- Hardware libraries (gpiozero, waveshare_epd) only work on Pi
- Test on Pi: `ssh pi@pi4 'cd ~/paperGate && ...'`

**Path Management:**
- All paths relative to project root
- Use `os.path.join()` for cross-platform paths
- Reference across directories: `../core/screens` from web/

**IPC Communication:**
- POSIX message queue at `/dev/mqueue/epdtext_ipc`
- Commands: `next`, `previous`, `reload`, `screen <name>`
- Used by CLI (`core/cli.py`) and web interface

**Network Resilience:**
- Wait for network at startup (`_wait_for_network()`)
- Wait for DNS resolution (`_wait_for_dns()`)
- Exponential backoff retry for calendar/weather fetches
- Graceful degradation when network unavailable

## Common Patterns

**Retry Logic (for network operations):**
```python
from functools import wraps
import time

def retry_with_backoff(max_attempts=5, initial_delay=1, max_delay=60):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except (ConnectionError, TimeoutError) as e:
                    if attempt == max_attempts - 1:
                        raise
                    time.sleep(min(initial_delay * (2 ** attempt), max_delay))
        return wrapper
    return decorator
```

**Thread-Safe Updates:**
```python
import threading

class MyClass:
    def __init__(self):
        self.data = None
        self.lock = threading.Lock()

    def update_data(self, new_data):
        with self.lock:
            self.data = new_data
```

**SVG Icon Rendering:**
```python
import cairosvg
from PIL import Image
from io import BytesIO

def render_svg_icon(svg_path, size=50):
    with open(svg_path, 'r') as f:
        svg_content = f.read()
    png_data = cairosvg.svg2png(bytestring=svg_content.encode('utf-8'),
                                output_width=size, output_height=size)
    return Image.open(BytesIO(png_data)).convert('1')
```

## Testing Notes

**No automated test suite configured.**
- Manual testing required on Raspberry Pi hardware
- Test all screens after changes
- Verify web interface functionality
- Check systemd service status: `pg-status`

**Manual Testing Checklist:**
1. Core daemon starts without errors: `pg-log`
2. Screens cycle correctly: `./cli.py next`
3. Calendar/weather data loads: Check logs for network errors
4. Web interface accessible: `curl http://localhost:5000`
5. Screenshot preview works in web UI
6. Button presses handled (if hardware buttons connected)

## Dependencies

**Key Python packages:**
- `Pillow`: Image manipulation (1-bit for e-paper)
- `gpiozero`: Hardware button handling
- `waveshare_epd`: E-paper display driver
- `Flask`: Web interface
- `feedparser`: RSS feed parsing
- `caldav`, `icalevents`: Calendar integration
- `cairosvg`, `astral`: SVG weather icons, day/night calc
- `requests`, `aiohttp`: HTTP clients (weather APIs)
- `posix_ipc`: IPC message queue
- `psutil`, `distro`: System monitoring

**System dependencies (apt):**
- `python3-dev`: Python development headers
- `libi2c-dev`, `libgpiod-dev`: I2C/GPIO libraries
- `wkhtmltopdf`: Webview screenshot rendering
