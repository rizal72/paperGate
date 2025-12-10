import logging
import os
from io import BytesIO
from PIL import Image
import cairosvg
import settings

from libs.calendar_events import Calendar, get_calendar, update_calendar
from screens import AbstractScreen


class Screen(AbstractScreen):
    calendar: Calendar = get_calendar()

    def _render_calendar_icon(self, size=20):
        """Render the calendar icon from SVG"""
        icon_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            '..', 'icons', 'calendar_icon.svg'
        )

        try:
            with open(icon_path, 'r') as f:
                svg_content = f.read()

            import re
            svg_content = re.sub(r'<\?xml[^>]*\?>', '', svg_content)
            svg_match = re.search(r'<svg[^>]*>(.*)</svg>', svg_content, re.DOTALL)
            if svg_match:
                icon_inner = svg_match.group(1)
            else:
                icon_inner = svg_content

            svg_wrapper = f'''<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink"
     width="{size}" height="{size}" viewBox="0 0 508 508">
    <rect width="508" height="508" fill="white" />
    {icon_inner}
</svg>'''

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

        self.draw_titlebar("Calendar")

        if len(self.calendar.events) < 1:
            self.centered_text('No current events', 80, 20)
            return

        # Calendar icon
        cal_icon = self._render_calendar_icon()
        if cal_icon:
            self.image.paste(cal_icon, (10, 35))

        # Event list
        event_x = 10
        y_position = 60
        events_to_show = min(5, len(self.calendar.events))

        for i in range(events_to_show):
            event = self.calendar.events[i]
            start = self.calendar.standardize_date(event["start"])
            end = self.calendar.standardize_date(event["end"]) if "end" in event else None

            # Event date with humanized format + time range
            date_text = self.calendar.humanized_datetime(start)

            # Add time range if end time exists and it's not an all-day event
            if end:
                is_all_day = (start.hour == 0 and start.minute == 0 and
                              end.hour == 0 and end.minute == 0)
                if not is_all_day:
                    time_range = f" {start.strftime('%H:%M')}-{end.strftime('%H:%M')}"
                    date_text += time_range

            # Truncate date/time if too long
            if len(date_text) > 40:
                date_text = date_text[:37] + "..."
            self.text(date_text, font_size=10, position=(event_x, y_position))

            # Event title (BOLD, single line, no wrapping)
            title_text = str(event['summary']).replace('\n', ' ').strip()
            if len(title_text) > 34:
                title_text = title_text[:34] + "..."
            self.text(title_text, font_size=12, position=(event_x, y_position + 12),
                     font_name=settings.BOLD_FONT, wrap=False)

            y_position += 30

            if y_position > 155:
                break

    def handle_btn_press(self, button_number=1):
        if button_number == 0:
            pass
        elif button_number == 1:
            self.reload()
            self.show()
        elif button_number == 2:
            update_calendar()
            self.reload()
            self.show()
        elif button_number == 3:
            pass
        else:
            logging.error("Unknown button pressed: KEY{}".format(button_number + 1))
