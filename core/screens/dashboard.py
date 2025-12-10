import logging
import threading
import os
import time
from datetime import datetime
from io import BytesIO
from PIL import Image
import cairosvg
import settings

from libs.calendar_events import Calendar, get_calendar, update_calendar
from libs.weather import Weather, get_weather, update_weather
from screens import AbstractScreen


class Screen(AbstractScreen):
    calendar: Calendar = get_calendar()
    weather: Weather = get_weather()
    last_minute = -1  # Track last displayed minute

    def _render_calendar_icon(self, size=20):
        """Render the waveshare calendar icon from SVG using embedded approach"""
        icon_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            '..', 'icons', 'calendar_icon.svg'
        )

        try:
            # Read the SVG content
            with open(icon_path, 'r') as f:
                svg_content = f.read()

            # Extract inner content (remove outer <svg> tags)
            import re
            svg_content = re.sub(r'<\?xml[^>]*\?>', '', svg_content)
            svg_match = re.search(r'<svg[^>]*>(.*)</svg>', svg_content, re.DOTALL)
            if svg_match:
                icon_inner = svg_match.group(1)
            else:
                icon_inner = svg_content

            # Create wrapper with white background (like weather icons)
            svg_wrapper = f'''<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink"
     width="{size}" height="{size}" viewBox="0 0 508 508">
    <rect width="508" height="508" fill="white" />
    {icon_inner}
</svg>'''

            # Render SVG wrapper to PNG
            png_data = cairosvg.svg2png(
                bytestring=svg_wrapper.encode('utf-8'),
                output_width=size,
                output_height=size
            )

            img = Image.open(BytesIO(png_data))
            return img.convert('1')
        except Exception as e:
            logging.error(f"Could not render calendar icon: {e}")
            return None

    def reload(self):
        self.blank()
        # Waveshare layout: 800x480 scaled to 264x176 (scale ~0.33x)

        now = datetime.now()

        # === TOP SECTION ===

        # Date baseline alignment: ora font=37, data font=15, differenza=22
        # Se data è a y=25, ora deve essere a y=25-22=3 per allineare baseline

        # Time (left, huge, BOLD) - waveshare uses font-weight:bold
        time_text = now.strftime("%H:%M")
        self.text(time_text, font_size=37, position=(7, 3), font_name=settings.BOLD_FONT)

        # Day (right-aligned, semi-bold) - waveshare uses text-anchor:middle but more to the right
        day_text = now.strftime("%A")
        # Calculate text width to right-align
        from PIL import ImageFont
        day_font = ImageFont.truetype(settings.BOLD_FONT, 17)
        day_bbox = day_font.getbbox(day_text)
        day_width = day_bbox[2] - day_bbox[0]
        day_x = self.image.size[0] - day_width - 5  # 5px margin from right
        self.text(day_text, font_size=17, position=(day_x, 5), font_name=settings.BOLD_FONT)

        # Date (right-aligned)
        date_text = now.strftime("%b %-d, %Y")
        date_font = ImageFont.truetype(settings.FONT, 15)
        date_bbox = date_font.getbbox(date_text)
        date_width = date_bbox[2] - date_bbox[0]
        date_x = self.image.size[0] - date_width - 5  # 5px margin from right
        self.text(date_text, font_size=15, position=(date_x, 25))

        # === BOTTOM SECTION (split at 1/3 width) ===

        # Vertical divider at x=88 (264/3) - waveshare at x=301 (800*0.375)
        divider_x = 88
        self.line((divider_x, 50, divider_x, self.image.size[1]), width=2)

        # === LEFT: Weather (0-88) ===

        # Weather icon (larger, centered in left section, raised)
        icon_size = 50
        icon_x = (divider_x - icon_size) // 2  # Center in left section
        icon_y = 60  # Raised from 75 to 60
        icon_image = self.weather.get_icon_image(size=icon_size)
        if icon_image:
            self.image.paste(icon_image, (icon_x, icon_y))

        # Current temperature below icon (BOLD, larger, centered in left section)
        temp = self.weather.get_temperature()
        temp_text = f"{int(round(temp))}°" if temp != "--" else "--"
        temp_font = ImageFont.truetype(settings.BOLD_FONT, 18)
        temp_bbox = temp_font.getbbox(temp_text)
        temp_width = temp_bbox[2] - temp_bbox[0]
        temp_x = (divider_x - temp_width) // 2  # Center in left section
        temp_y = icon_y + icon_size + 3  # 3px gap below icon
        self.text(temp_text, font_size=18, position=(temp_x, temp_y),
                 font_name=settings.BOLD_FONT)

        # Description below temp (centered in left section, compact)
        desc_text = str(self.weather.get_sky_text())
        if len(desc_text) > 10:
            desc_text = desc_text[:8] + ".."
        desc_font = ImageFont.truetype(settings.FONT, 11)
        desc_bbox = desc_font.getbbox(desc_text)
        desc_width = desc_bbox[2] - desc_bbox[0]
        desc_x = (divider_x - desc_width) // 2  # Center in left section
        desc_y = temp_y + 20  # 20px gap below temperature (reduced spacing)
        self.text(desc_text, font_size=11, position=(desc_x, desc_y))

        # === RIGHT: Calendar (88-264) ===

        # Calendar icon - aligned with event text below
        cal_icon = self._render_calendar_icon(size=18)
        if cal_icon:
            # Align with event_x (divider_x + 10)
            self.image.paste(cal_icon, (divider_x + 10, 55))

        # Calendar events - waveshare: x=330, y starts at 238
        event_x = divider_x + 10
        y_position = 78
        events_to_show = min(3, len(self.calendar.events))

        if events_to_show > 0:
            for i in range(events_to_show):
                event = self.calendar.events[i]
                start = self.calendar.standardize_date(event["start"])
                end = self.calendar.standardize_date(event["end"]) if "end" in event else None

                # Event date with humanized format + time range
                date_text = self.calendar.humanized_datetime(start)

                # Add time range if end time exists and it's not an all-day event
                # All-day events have start and end at 00:00:00
                if end:
                    is_all_day = (start.hour == 0 and start.minute == 0 and
                                  end.hour == 0 and end.minute == 0)
                    if not is_all_day:
                        time_range = f" {start.strftime('%H:%M')}-{end.strftime('%H:%M')}"
                        date_text += time_range

                # Right section is 176px wide, plenty of space
                if len(date_text) > 30:
                    date_text = date_text[:27] + "..."
                self.text(date_text, font_size=8, position=(event_x, y_position))

                # Event title (BOLD) - waveshare uses font-weight:bold for titles
                title_text = str(event['summary'])
                # 176px can fit ~35 chars at font 10 - allow full titles
                if len(title_text) > 35:
                    title_text = title_text[:32] + "..."
                self.text(title_text, font_size=10, position=(event_x, y_position + 11),
                         font_name=settings.BOLD_FONT)

                y_position += 30  # Space between events

                # Stop if we run out of space
                if y_position > 145:
                    break
        else:
            self.text("No events", font_size=9, position=(event_x, 83))

    def handle_btn_press(self, button_number=1):
        thread_lock = threading.Lock()
        thread_lock.acquire()
        if button_number == 0:
            pass
        elif button_number == 1:
            self.blank()
            self.text("Please wait...", font_size=40)
            self.show()
            update_calendar()
            update_weather()
            self.reload()
            self.show()
        elif button_number == 2:
            pass
        elif button_number == 3:
            pass
        else:
            logging.error("Unknown button pressed: KEY{}".format(button_number + 1))
        thread_lock.release()

    def iterate_loop(self):
        """Called periodically by app.py - update display every minute"""
        now = datetime.now()
        current_minute = now.minute

        # If minute has changed, reload the display
        if current_minute != self.last_minute:
            self.last_minute = current_minute
            self.reload()
            self.show()
            logging.debug(f"Dashboard auto-refreshed at {now.strftime('%H:%M')}")
