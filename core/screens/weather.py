import logging
from PIL import ImageFont
import settings

from libs.weather import Weather, get_weather, update_weather
from screens import AbstractScreen


class Screen(AbstractScreen):

    weather: Weather = get_weather()

    def handle_btn_press(self, button_number: int = 1):
        if button_number == 0:
            pass
        elif button_number == 1:
            update_weather()
            self.reload()
            self.show()
        elif button_number == 2:
            pass
        elif button_number == 3:
            pass
        else:
            logging.error("Unknown button pressed: KEY{}".format(button_number + 1))

    def reload(self):
        self.blank()

        self.draw_titlebar("Weather")

        if self.weather.weather_data:
            # Weather icon (large, left-aligned with fixed margin)
            icon_size = 85
            icon_x = 10  # Fixed left margin
            icon_y = 35
            icon_image = self.weather.get_icon_image(size=icon_size)
            if icon_image:
                self.image.paste(icon_image, (icon_x, icon_y))

            # High/low temperature (BOLD, right-aligned)
            temp_text = str(self.weather.get_temperature_high_low())
            temp_font = ImageFont.truetype(settings.BOLD_FONT, 40)
            temp_bbox = temp_font.getbbox(temp_text)
            temp_width = temp_bbox[2] - temp_bbox[0]
            temp_x = self.image.size[0] - temp_width - 10  # Right-aligned with 10px margin
            temp_y = icon_y + 20  # Vertically aligned with icon center
            self.text(temp_text, font_size=40, position=(temp_x, temp_y),
                     font_name=settings.BOLD_FONT)

            # Weather description (regular, centered below icon+temp)
            desc_text = str(self.weather.get_sky_text())
            desc_font = ImageFont.truetype(settings.FONT, 20)
            desc_bbox = desc_font.getbbox(desc_text)
            desc_width = desc_bbox[2] - desc_bbox[0]
            desc_x = (self.image.size[0] - desc_width) // 2
            desc_y = icon_y + icon_size + 8  # Reduced gap from 15 to 8
            self.text(desc_text, font_size=20, position=(desc_x, desc_y))

            # Location (BOLD, centered below description)
            location_text = str(self.weather.get_location_name())
            location_font = ImageFont.truetype(settings.BOLD_FONT, 18)
            location_bbox = location_font.getbbox(location_text)
            location_width = location_bbox[2] - location_bbox[0]
            location_x = (self.image.size[0] - location_width) // 2
            location_y = desc_y + 24  # Reduced gap from 28 to 24
            self.text(location_text, font_size=18, position=(location_x, location_y),
                     font_name=settings.BOLD_FONT)

        else:
            self.centered_text("No data", 105, 30)
