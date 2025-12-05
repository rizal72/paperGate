import logging
import subprocess
import settings

from screens import AbstractScreen


class Screen(AbstractScreen):
    def reload(self):
        try:
            fortune_path = settings.FORTUNE_PATH if settings.FORTUNE_PATH else "fortune"
            child = subprocess.Popen([fortune_path], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            string = child.stdout.read().decode().replace('\n', ' ')
        except OSError:
            logging.error("couldn't run application 'fortune'")
            string = "Couldn't run 'fortune'"
        self.blank()
        self.draw_titlebar("Fortune")
        self.text(string, font_size=14, position=(5, 25))

    def handle_btn_press(self, button_number=1):
        if button_number == 1:
            self.reload()
            self.show()
        elif button_number == 2:
            pass
