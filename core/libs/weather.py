import threading
import time
import logging
import os
from PIL import Image
import settings
from libs.metno_adapter import MetnoAdapter

# Get project root for image paths
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
IMAGES_DIR = os.path.join(PROJECT_ROOT, 'images')

WEATHER_LATITUDE = getattr(settings, 'WEATHER_LATITUDE', 45.4642)  # Default: Milan
WEATHER_LONGITUDE = getattr(settings, 'WEATHER_LONGITUDE', 9.1900)
WEATHER_CITY_NAME = getattr(settings, 'WEATHER_CITY_NAME', 'Milano')  # Default: Milano
WEATHER_REFRESH = getattr(settings, 'WEATHER_REFRESH', 900)

logger = logging.getLogger("pitftmanager.libs.weather")


class Weather(threading.Thread):
    """
    This class provides access to the weather info using Met.no provider
    """
    refresh_interval: int = WEATHER_REFRESH
    thread_lock = threading.Lock()

    def __init__(self):
        super().__init__()
        self.name = "Weather"
        self.shutdown = threading.Event()
        
        # Initialize Met.no adapter
        self.metno = MetnoAdapter(WEATHER_LATITUDE, WEATHER_LONGITUDE)
        self.weather_data = None

    def run(self) -> None:
        logger.debug('Weather loop starting...')
        thread_process = threading.Thread(target=self.weather_loop)
        # run thread as a daemon so it gets cleaned up on exit.
        thread_process.daemon = True
        thread_process.start()
        self.shutdown.wait()

    def weather_loop(self):
        while not self.shutdown.is_set():
            self.refresh_interval -= 1
            time.sleep(1)
            if self.refresh_interval < 1:
                try:
                    self.update()
                except Exception as error:
                    logger.warning(f"Weather update error: {error}")
                self.refresh_interval = WEATHER_REFRESH

    def stop(self):
        self.shutdown.set()

    def update(self):
        """
        Update the weather info from Met.no
        :return: None
        """
        self.thread_lock.acquire()
        try:
            success = self.metno.fetch_weather()
            if success:
                self.weather_data = self.metno.weather_data
                logger.debug('Weather updated successfully from Met.no')
            else:
                logger.error('Failed to fetch weather from Met.no')
        finally:
            self.thread_lock.release()

    def get_temperature(self):
        """
        Get the current temperature (average of min/max)
        :return: Float temperature or "--"
        """
        if not self.weather_data:
            return "--"

        temp = self.metno.get_temperature()
        return temp if temp is not None else "--"

    def get_temperature_high_low(self):
        """
        Get high/low temperature range formatted as "high°/low°"
        :return: String like "5°/4°" or "--"
        """
        if not self.weather_data:
            return "--"

        temp_min, temp_max = self.metno.get_temperature_range()
        if temp_min is not None and temp_max is not None:
            return f"{int(round(temp_max))}°/{int(round(temp_min))}°"
        return "--"

    def get_sky_text(self):
        """
        Get the weather description
        :return: String of the weather description
        """
        if not self.weather_data:
            return "--"

        description = self.metno.get_description()
        return description if description else "--"

    def get_location_name(self):
        """
        Get the location name (from settings)
        :return: String of city name
        """
        return WEATHER_CITY_NAME

    def get_icon(self):
        """
        Get the icon name for the current weather
        :return: icon name string
        """
        if not self.weather_data:
            return "-"

        icon = self.metno.get_icon_name()
        return icon if icon else "-"

    def get_icon_image(self, size=50):
        """
        Get the SVG weather icon rendered as PIL Image
        :param size: Size of the icon in pixels (default 50)
        :return: PIL Image or None
        """
        if not self.weather_data:
            return None

        try:
            # Use Met.no adapter to render SVG icon
            img = self.metno.render_icon_to_image(size)
            if img:
                return img
            else:
                logger.warning("Met.no icon render failed, using fallback")
                return self._get_fallback_icon()
        except Exception as e:
            logger.error(f"Could not render SVG icon: {e}")
            return self._get_fallback_icon()

    def _get_fallback_icon(self):
        """
        Fallback to basic PNG icons if SVG rendering fails
        :return: PIL Image or None
        """
        if not self.weather_data:
            return None

        # Get weather description and try to map to PNG icon
        description = self.metno.get_description()
        if not description:
            return None
        
        description_lower = description.lower()

        # Map weather descriptions to icon files (order matters - more specific first)
        icon_map = {
            'thunder': os.path.join(IMAGES_DIR, 'thunderstorm.png'),
            'storm': os.path.join(IMAGES_DIR, 'thunderstorm.png'),
            'drizzle': os.path.join(IMAGES_DIR, 'drizzle.png'),
            'rain': os.path.join(IMAGES_DIR, 'rain.png'),
            'shower': os.path.join(IMAGES_DIR, 'rain.png'),
            'snow': os.path.join(IMAGES_DIR, 'snow.png'),
            'sleet': os.path.join(IMAGES_DIR, 'snow.png'),
            'fog': os.path.join(IMAGES_DIR, 'fog.png'),
            'mist': os.path.join(IMAGES_DIR, 'fog.png'),
            'haze': os.path.join(IMAGES_DIR, 'fog.png'),
            'clear': os.path.join(IMAGES_DIR, 'sun.png'),
            'fair': os.path.join(IMAGES_DIR, 'cloud_sun.png'),
            'partly': os.path.join(IMAGES_DIR, 'cloud_sun.png'),
            'cloudy': os.path.join(IMAGES_DIR, 'cloud.png'),
            'overcast': os.path.join(IMAGES_DIR, 'cloud.png'),
        }

        # Find matching icon
        icon_path = None
        for key, path in icon_map.items():
            if key in description_lower:
                icon_path = path
                break

        # Default to cloud if no match
        if not icon_path:
            icon_path = os.path.join(IMAGES_DIR, 'cloud.png')

        try:
            img = Image.open(icon_path)
            # Convert to 1-bit for e-paper
            return img.convert('1')
        except Exception as e:
            logger.error(f"Could not load weather icon {icon_path}: {e}")
            return None

    def get_moon(self):
        """
        Get the moon phase (not available in Met.no, kept for compatibility)
        :return: emoji str
        """
        # Met.no doesn't provide moon phase
        return "-"


weather: Weather = Weather()


def get_weather():
    """
    Get the main weather object
    :return: Weather
    """
    return weather


def update_weather():
    """
    Force immediate weather update
    :return: None
    """
    weather.refresh_interval = 0


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    print('Weather CLASS instantiated...')
    update_weather()
    time.sleep(2)  # Give it time to fetch
    logger.info(f"Temperature: {weather.get_temperature()}°C")
    logger.info(f"Description: {weather.get_sky_text()}")
