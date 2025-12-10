import os
import sys
import logging
from io import BytesIO
from PIL import Image
import cairosvg

# Import Met.no provider from waveshare
# Import from weather_providers package
from libs.weather_providers.metno import MetNo

logger = logging.getLogger(__name__)

class MetnoAdapter:
    """Adapter to use Met.no provider from waveshare in paperGate"""

    def __init__(self, latitude, longitude, contact_email="user@example.com"):
        self.latitude = latitude
        self.longitude = longitude

        # Construct User-Agent according to Met.no Terms of Service
        # Format: "AppName/Version (contact@email.com)"
        self.user_agent = f"paperGate/1.0 ({contact_email})"

        # Initialize Met.no provider
        # MetNo(metno_self_id, location_lat, location_long, units)
        self.provider = MetNo(
            metno_self_id=self.user_agent,
            location_lat=latitude,
            location_long=longitude,
            units="celsius"  # Always celsius for paperGate
        )

        self.weather_data = None
        logger.info(f"Met.no adapter initialized with User-Agent: {self.user_agent}")

    def fetch_weather(self):
        """Fetch weather from Met.no API"""
        try:
            # Met.no provider returns dict:
            # {"temperatureMin": "2.0", "temperatureMax": "15.1",
            #  "icon": "mostly_cloudy", "description": "Cloudy"}
            self.weather_data = self.provider.get_weather()
            return True
        except Exception as e:
            logger.error(f"Failed to fetch Met.no weather: {e}")
            return False

    def get_temperature(self):
        """Get current temperature (average of min/max)"""
        if not self.weather_data:
            return None
        # Met.no provides min/max for 6-hour period, return average
        temp_min = float(self.weather_data.get('temperatureMin', 0))
        temp_max = float(self.weather_data.get('temperatureMax', 0))
        return round((temp_min + temp_max) / 2, 1)

    def get_temperature_range(self):
        """Get min/max temperature range"""
        if not self.weather_data:
            return None, None
        return (
            float(self.weather_data.get('temperatureMin', 0)),
            float(self.weather_data.get('temperatureMax', 0))
        )

    def get_description(self):
        """Get weather description"""
        if not self.weather_data:
            return None
        return self.weather_data.get('description', 'Unknown')

    def get_icon_name(self):
        """Get icon name (without .svg extension)"""
        if not self.weather_data:
            return None
        return self.weather_data.get('icon')

    def get_icon_svg_path(self):
        """Get full path to SVG icon file"""
        icon_name = self.get_icon_name()
        if not icon_name:
            return None

        # Icons are in ~/paperGate/icons/
        icons_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            'icons'
        )

        # Add .svg extension if not present
        if not icon_name.endswith('.svg'):
            icon_name = icon_name + '.svg'

        return os.path.join(icons_dir, icon_name)

    def render_icon_to_image(self, size=50):
        """
        Render SVG weather icon to PIL Image for e-paper display

        Uses the same approach as waveshare: create an SVG wrapper that includes
        the icon, then render the complete SVG with CairoSVG.

        Args:
            size: Target size in pixels (default 50)

        Returns:
            PIL Image (1-bit, black/white) or None
        """
        svg_path = self.get_icon_svg_path()
        if not svg_path or not os.path.exists(svg_path):
            logger.error(f"Icon not found: {svg_path}")
            return None

        try:
            # Read the icon SVG content
            with open(svg_path, 'r') as f:
                icon_svg_content = f.read()

            # Extract the inner content (remove <?xml...> and outer <svg> tags if present)
            # We'll embed it directly in our wrapper
            import re
            # Remove XML declaration
            icon_svg_content = re.sub(r'<\?xml[^>]*\?>', '', icon_svg_content)
            # Extract content between <svg> tags or use as-is
            svg_match = re.search(r'<svg[^>]*>(.*)</svg>', icon_svg_content, re.DOTALL)
            if svg_match:
                icon_inner = svg_match.group(1)
            else:
                icon_inner = icon_svg_content

            # Create SVG wrapper with embedded icon content
            # Use viewBox to automatically scale the icon to fit
            svg_wrapper = f'''<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink"
     width="{size}" height="{size}" viewBox="0 0 130 130">
    <rect width="130" height="130" fill="white" />
    {icon_inner}
</svg>'''

            # Render SVG wrapper to PNG in memory
            png_data = cairosvg.svg2png(
                bytestring=svg_wrapper.encode('utf-8'),
                output_width=size,
                output_height=size
            )

            # Convert to PIL Image
            img = Image.open(BytesIO(png_data))

            # Convert to 1-bit for e-paper display
            img = img.convert('1')

            return img

        except Exception as e:
            logger.error(f"Failed to render SVG icon: {e}")
            return None
