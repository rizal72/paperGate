import logging

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

        if self.weather.weather:
            # Use PNG icon instead of emoji
            icon_image = self.weather.get_icon_image()
            if icon_image:
                self.image.paste(icon_image, (15, 38))

            text = str(self.weather.get_temperature()) + '°'
            self.centered_text(text, 40, 60)

            text = str(self.weather.get_sky_text())
            self.centered_text(text, 105, 20)

            # Moon emoji removed - could add moon icon later if needed
            # moon = self.weather.get_moon()
            # self.text(moon, font_size=50, position=(190, 46))

            text = str(self.weather.get_location_name())
            self.centered_text(text, 140, 25)

        else:
            self.centered_text("No data", 105, 30)
