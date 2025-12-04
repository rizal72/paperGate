import threading
import time
import python_weather
import asyncio
import xml
import logging
from PIL import Image


try:
    from local_settings import WEATHER_FORMAT
except ImportError:
    WEATHER_FORMAT = python_weather.IMPERIAL

try:
    from local_settings import WEATHER_CITY
except ImportError:
    WEATHER_CITY = "Richmond, VA"

try:
    from local_settings import WEATHER_REFRESH
except ImportError:
    WEATHER_REFRESH = 900


logger = logging.getLogger("pitftmanager.libs.weather")


class Weather(threading.Thread):
    """
    This class provides access to the weather info
    """
    weather = None
    refresh_interval: int = WEATHER_REFRESH
    # loop = asyncio.get_event_loop()
    
    # loop = asyncio.new_event_loop()
    # asyncio.set_event_loop(loop)
    thread_lock = threading.Lock()

    def __init__(self):
        super().__init__()
        self.name = "Weather"
        self.shutdown = threading.Event()

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
                    # self.loop.run_until_complete(self.update())
                    asyncio.run(self.update())
                except xml.parsers.expat.ExpatError as error:
                    logger.warning(error)
                self.refresh_interval = WEATHER_REFRESH

    def stop(self):
        self.shutdown.set()

    async def update(self):
        """
        Update the weather info
        :return: None
        add locale=python_weather.Locale.ITALIAN if needed
        """
        self.thread_lock.acquire()
        client = python_weather.Client(unit=WEATHER_FORMAT)
        self.weather = await client.get(WEATHER_CITY)
        await client.close()
        self.thread_lock.release()

        # async with python_weather.Client(unit=WEATHER_FORMAT) as client:
        #     self.weather = await client.get(WEATHER_CITY)
        
        logger.debug('weather update CALLED!')

    def get_temperature(self):
        """
        Get the temperature
        :return: String of the temperature
        """
        if not self.weather:
            return "--"

        temp = self.weather.current.temperature
        return temp

    def get_sky_text(self):
        """
        Get the sky text
        :return: String of the sky text
        """
        if not self.weather:
            return "--"

        description = self.weather.current.description
        # print('description = ', description)
        return description

    def get_location_name(self):
        """
        Get the location name
        :return: String of the location name
        """
        if not self.weather:
            return "--"

        location = self.weather.nearest_area.name
        # print('location = ', location)
        return location

    def get_icon(self):
        """
        Get the icon for the current weather
        :return: emoji str
        """
        if not self.weather:
            return "-"

        kind = self.weather.current.kind
        icon = kind.emoji
        # icon = '🌧'
        # print('kind = ', kind)
        # print('icon = ', icon)
        return icon

    def get_icon_image(self, size=50):
        """
        Get the icon image for the current weather by converting emoji to PNG
        :param size: Size of the icon in pixels (default 50)
        :return: PIL Image or None
        """
        if not self.weather:
            return None

        try:
            from pilmoji import Pilmoji
            from PIL import ImageDraw, ImageFont

            # Get the emoji
            emoji = self.get_icon()
            if not emoji or emoji == "-":
                return None

            # Create a blank image for the emoji
            img = Image.new('1', (size, size), 1)  # 1-bit image, white background

            # Use Pilmoji to render the emoji
            with Pilmoji(img) as pilmoji:
                # Try to render the emoji centered
                # Pilmoji needs a font for text context
                try:
                    font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', size)
                except:
                    font = ImageFont.load_default()

                # Draw the emoji
                pilmoji.text((0, 0), emoji, font=font, fill=0)  # 0 = black

            return img

        except Exception as e:
            logger.error(f"Could not render emoji icon: {e}")
            # Fallback to PNG icons if emoji rendering fails
            return self._get_fallback_icon()

    def _get_fallback_icon(self):
        """
        Fallback to basic PNG icons if emoji rendering fails
        :return: PIL Image or None
        """
        if not self.weather:
            return None

        kind = self.weather.current.kind
        kind_name = str(kind).lower()

        # Map weather kinds to icon files (order matters - more specific first)
        icon_map = {
            'thunderstorm': 'images/thunderstorm.png',
            'thunder': 'images/thunderstorm.png',
            'storm': 'images/thunderstorm.png',
            'drizzle': 'images/drizzle.png',
            'rain': 'images/rain.png',
            'rainy': 'images/rain.png',
            'shower': 'images/rain.png',
            'snow': 'images/snow.png',
            'snowy': 'images/snow.png',
            'sleet': 'images/snow.png',
            'fog': 'images/fog.png',
            'foggy': 'images/fog.png',
            'mist': 'images/fog.png',
            'haze': 'images/fog.png',
            'sunny': 'images/sun.png',
            'clear': 'images/sun.png',
            'partly_cloudy': 'images/cloud_sun.png',
            'partly': 'images/cloud_sun.png',
            'cloudy': 'images/cloud.png',
            'overcast': 'images/cloud.png',
        }

        # Find matching icon
        icon_path = None
        for key, path in icon_map.items():
            if key in kind_name:
                icon_path = path
                break

        # Default to cloud if no match
        if not icon_path:
            icon_path = 'images/cloud.png'

        try:
            return Image.open(icon_path)
        except Exception as e:
            logger.error(f"Could not load weather icon {icon_path}: {e}")
            return None

    def get_moon(self):
        """
        Get the moon phase for the current weather
        :return: emoji str
        """
        if not self.weather:
            return "-"

        for forecast in self.weather.forecasts:
            moon = forecast.astronomy.moon_phase.emoji
            break
        return moon


weather: Weather = Weather()


def get_weather():
    """
    Get the main weather object
    :return: Weather
    """
    # update_weather()
    return weather


def update_weather():
    """
    Update the weather info
    :return: None
    """
    # loop = asyncio.get_event_loop()
    # loop.run_until_complete(weather.update())
    
    # asyncio.run(weather.update())
    weather.refresh_interval = 0


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    print('Weather CLASS instantiated...')
    update_weather()
    logger.info(weather.weather.current.description)
