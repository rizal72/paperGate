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
            # Calculate centered block of icon + temperature
            icon_size = 70
            gap_between = 8  # Gap between icon and temperature

            # Get current temperature and range separately
            temp_current = self.weather.get_temperature()
            temp_current_text = f"{int(round(temp_current))}°" if temp_current != "--" else "--"

            # Get min/max range with arrows (reduced by 60% total - 30% twice)
            temp_min, temp_max = self.weather.metno.get_temperature_range()
            if temp_min is not None and temp_max is not None:
                temp_range_text = f"(↑{int(round(temp_max))}°↓{int(round(temp_min))}°)"
            else:
                temp_range_text = ""

            # Calculate widths for layout
            temp_current_font = ImageFont.truetype(settings.BOLD_FONT, 32)
            temp_current_bbox = temp_current_font.getbbox(temp_current_text)
            temp_current_width = temp_current_bbox[2] - temp_current_bbox[0]
            temp_current_height = temp_current_bbox[3] - temp_current_bbox[1]

            temp_range_font = ImageFont.truetype(settings.BOLD_FONT, 15)  # 60% smaller total
            temp_range_bbox = temp_range_font.getbbox(temp_range_text)
            temp_range_width = temp_range_bbox[2] - temp_range_bbox[0]
            temp_range_height = temp_range_bbox[3] - temp_range_bbox[1]

            # Calculate total width of icon + gap + current temp + range
            total_width = icon_size + gap_between + temp_current_width + temp_range_width

            # Center the entire block horizontally and vertically
            block_x = (self.image.size[0] - total_width) // 2

            # Calculate vertical centering (between titlebar and description)
            available_height = self.image.size[1] - 30  # Account for titlebar
            block_height = icon_size
            block_y = (available_height - block_height) // 3 + 30 - 10  # Center in upper portion, raised 10px

            # Weather icon (left side of block)
            icon_x = block_x
            icon_y = block_y
            icon_image = self.weather.get_icon_image(size=icon_size)
            if icon_image:
                self.image.paste(icon_image, (icon_x, icon_y))

            # Current temperature (right side of icon, BOLD, large)
            # Align with icon, with slight offset to compensate SVG internal margin
            temp_current_x = icon_x + icon_size + gap_between
            temp_current_y = icon_y + (icon_size - temp_current_height) // 2 - 4  # Raised 4px for SVG margin
            self.text(temp_current_text, font_size=32, position=(temp_current_x, temp_current_y),
                     font_name=settings.BOLD_FONT)

            # Min/max range (right of current temp, BOLD, smaller - 60% reduction total)
            # Aligned to same baseline as current temp
            if temp_range_text:
                temp_range_x = temp_current_x + temp_current_width
                # Baseline alignment: align bottom of bboxes (approximates baseline alignment)
                temp_range_y = temp_current_y + (temp_current_height - temp_range_height)
                self.text(temp_range_text, font_size=15, position=(temp_range_x, temp_range_y),
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
