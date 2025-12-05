import python_weather
import tzlocal
import sys
import os

# Add parent directory to path to import local_settings from project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from local_settings import DRIVER
except ImportError:
    DRIVER = "epd2in7b"

try:
    from local_settings import DEBUG
except ImportError:
    DEBUG = False

try:
    from local_settings import SAVE_SCREENSHOTS
except ImportError:
    SAVE_SCREENSHOTS = False

try:
    from local_settings import LOGFILE
except ImportError:
    LOGFILE = None

try:
    from local_settings import PAGE_BUTTONS
except ImportError:
    PAGE_BUTTONS = True

try:
    from local_settings import LOGO
except ImportError:
    LOGO = None

try:
    from local_settings import FONT
except ImportError:
    FONT = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'

try:
    from local_settings import BOLD_FONT
except ImportError:
    BOLD_FONT = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'

try:
    from local_settings import MONOSPACE_FONT
except ImportError:
    MONOSPACE_FONT = '/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf'

try:
    from local_settings import TIME
except ImportError:
    TIME = 900

try:
    from local_settings import CALENDAR_URLS
except ImportError:
    CALENDAR_URLS = []

try:
    from local_settings import CALENDAR_REFRESH
except ImportError:
    CALENDAR_REFRESH = 900

try:
    from local_settings import TIMEZONE
except ImportError:
    TIMEZONE = tzlocal.get_localzone().key

try:
    from local_settings import SCREENS
except ImportError:
    SCREENS = [
        'system',
        'fortune',
        'affirmations',
    ]

try:
    from local_settings import AFFIRMATIONS
except ImportError:
    AFFIRMATIONS = [
        "You are enough",
        "You are loved",
        "You are safe",
        "Be yourself",
        "They can't hurt you anymore",
        "You are beautiful",
        "You are strong",
        "You have come a long way"
    ]

try:
    from local_settings import WEATHER_CITY
except ImportError:
    WEATHER_CITY = "Richmond, VA"

try:
    from local_settings import WEATHER_FORMAT
except ImportError:
    WEATHER_FORMAT = python_weather.IMPERIAL

try:
    from local_settings import WEATHER_REFRESH
except ImportError:
    WEATHER_REFRESH = 900

try:
    from local_settings import FORTUNE_PATH
except ImportError:
    FORTUNE_PATH = None

try:
    from local_settings import WEBVIEW_URL
except ImportError:
    WEBVIEW_URL = 'http://localhost:5000'

try:
    from local_settings import WEBVIEW_RELOAD_INTERVAL
except ImportError:
    WEBVIEW_RELOAD_INTERVAL = 300

try:
    from local_settings import WEBVIEW_SCALE
except ImportError:
    WEBVIEW_SCALE = 0.5

try:
    from local_settings import WEBVIEW_ORIENTATION
except ImportError:
    WEBVIEW_ORIENTATION = 'landscape'

try:
    from local_settings import NETWORK_INTERFACE
except ImportError:
    NETWORK_INTERFACE = 'eth0'

# Web Interface Configuration
try:
    from local_settings import SECRET_KEY
except ImportError:
    SECRET_KEY = b'change-me-insecure-default'

try:
    from local_settings import AUTH_USERNAME
except ImportError:
    AUTH_USERNAME = 'admin'

try:
    from local_settings import AUTH_PASSWORD
except ImportError:
    AUTH_PASSWORD = 'changeme'

try:
    from local_settings import FEEDS
except ImportError:
    FEEDS = []
