import asyncio
import importlib
import logging
import signal
import time
import sys
import os

import posix_ipc

import settings
from libs import epd
from libs.calendar import Calendar, get_calendar
from libs.epd import EPD, get_epd
from libs.weather import Weather, get_weather, update_weather
from settings import TIME, SCREENS, DEBUG, LOGFILE


class App:
    logger = logging.getLogger("epdtext.app")
    current_screen_index: int = 0
    screen_modules: list = []
    screens: list = []
    calendar: Calendar = get_calendar()
    weather: Weather = get_weather()
    epd: EPD = get_epd()
    async_loop: asyncio.AbstractEventLoop = asyncio.new_event_loop()
    loop_time: int = 0

    def current_screen(self):
        return self.screens[self.current_screen_index]

    def current_screen_module(self):
        return self.screen_modules[self.current_screen_index]

    def previous_screen(self):
        if self.current_screen_index > 0:
            self.current_screen_index -= 1
        else:
            self.current_screen_index = len(self.screens) - 1
        self.logger.debug("Current screen: {0}".format(self.current_screen().__module__))
        self.current_screen().reload()
        self.current_screen().show()

    def next_screen(self):
        self.current_screen_index += 1
        if self.current_screen_index >= len(self.screens):
            self.current_screen_index = 0
        self.logger.debug("Current screen: {0}".format(self.current_screen().__module__))
        self.current_screen().reload()
        self.current_screen().show()

    def handle_btn0_press(self):
        if settings.PAGE_BUTTONS:
            self.previous_screen()
        else:
            self.logger.debug("Screen '{0}' handling button 0".format(self.current_screen().__module__))
            self.current_screen().handle_btn_press(button_number=0)

    def handle_btn1_press(self):
        self.logger.debug("Screen '{0}' handling button 1".format(self.current_screen().__module__))
        self.current_screen().handle_btn_press(button_number=1)

    def handle_btn2_press(self):
        self.logger.debug("Screen '{0}' handling button 2".format(self.current_screen().__module__))
        self.current_screen().handle_btn_press(button_number=2)

    def handle_btn3_press(self):
        if settings.PAGE_BUTTONS:
            self.next_screen()
        else:
            self.logger.debug("Screen '{0}' handling button 3".format(self.current_screen().__module__))
            self.current_screen().handle_btn_press(button_number=3)

    def add_screen(self, screen_name):
        try:
            screen_module = importlib.import_module("screens." + screen_name)
        except ImportError as error:
            # Try loading without 'screens.' prefix before giving up
            self.logger.debug(f"Failed to import 'screens.{screen_name}', trying '{screen_name}'")
            try:
                screen_module = importlib.import_module(screen_name)
            except ImportError:
                screen_module = None
        if screen_module:
            try:
                new_screen = screen_module.Screen()
                self.screens.append(new_screen)
                self.screen_modules.append(screen_module)
                self.logger.info(f"Successfully added screen '{screen_name}'")
            except AttributeError:
                self.logger.error("Screen '{0}' has no Screen class".format(screen_name))
            except Exception as e:
                self.logger.error(f"Failed to initialize screen '{screen_name}': {e}")
        else:
            self.logger.error("Failed to load screen module: {}".format(screen_name))

    def find_screen_index_by_name(self, screen_name):
        for index in range(0, len(self.screens)):
            name = self.screens[index].__module__
            if name == screen_name or name.split('.')[-1] == screen_name:
                return index
        # Return -1 without logging - let the caller decide if this is an error
        return -1

    def get_screen_by_name(self, screen_name):
        index = self.find_screen_index_by_name(screen_name)
        if index >= 0:
            return self.screens[index]
        else:
            self.logger.debug("Screen '{0}' not found".format(screen_name))
            return None

    def get_screen_module_by_name(self, screen_name):
        index = self.find_screen_index_by_name(screen_name)
        if index >= 0:
            return self.screen_modules[index]
        else:
            self.logger.debug("Screen '{0}' not found".format(screen_name))
            return None

    def _show_loading(self, message):
        """
        Show a loading message on the display during initialization
        """
        from PIL import Image, ImageDraw, ImageFont

        # Create a simple loading screen
        img = Image.new('1', self.epd.get_size(), 255)  # White background
        draw = ImageDraw.Draw(img)

        try:
            font = ImageFont.truetype(settings.FONT, 20)
        except:
            font = ImageFont.load_default()

        # Center the text
        bbox = draw.textbbox((0, 0), message, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        x = (self.epd.get_size()[0] - text_width) // 2
        y = (self.epd.get_size()[1] - text_height) // 2

        draw.text((x, y), message, font=font, fill=0)  # Black text

        # Show on display
        self.epd.show(img)

    def __init__(self):
        if DEBUG:
            logging.basicConfig(level=logging.DEBUG, filename=LOGFILE)
            self.logger.info("Debug messages enabled")
        else:
            logging.basicConfig(filename=LOGFILE)

        self.logger.info("Starting epdtext...")
        self.logger.info("Timezone selected: {}".format(settings.TIMEZONE))

        signal.signal(signal.SIGINT, self.shutdown)
        signal.signal(signal.SIGTERM, self.shutdown)

        self.epd.start()

        # Show loading message
        self._show_loading("Initializing...")

        self.mq = posix_ipc.MessageQueue("/epdtext_ipc", flags=posix_ipc.O_CREAT)
        self.mq.block = False

        self._show_loading("Loading calendar...")
        self.calendar.get_latest_events()

        self._show_loading("Loading weather...")
        asyncio.run(self.weather.update())

        self.calendar.start()
        self.weather.start()

        btns = epd.get_buttons()
        btns[0].when_pressed = self.handle_btn0_press
        btns[1].when_pressed = self.handle_btn1_press
        btns[2].when_pressed = self.handle_btn2_press
        btns[3].when_pressed = self.handle_btn3_press

        self._show_loading("Loading screens...")
        for module in SCREENS:
            self.add_screen(module)

    def shutdown(self, *args):
        self.logger.info("epdtext shutting down gracefully...")
        self.epd.clear()
        while len(self.screens) > 0:
            del self.screens[0]

        time.sleep(5)

        self.epd.stop()
        self.calendar.stop()
        self.weather.stop()

        self.epd.join()
        self.calendar.join()
        self.weather.join()

        exit(0)

    def process_message(self):
        try:
            message = self.mq.receive(timeout=10)
        except posix_ipc.BusyError:
            message = None

        if message:
            parts = message[0].decode().split()

            command = parts[0]
            self.logger.debug("Received IPC command: " + command)
            if command == "button0":
                self.handle_btn0_press()
            elif command == "button3":
                self.handle_btn3_press()
            elif command == "button1":
                self.handle_btn1_press()
            elif command == "button2":
                self.handle_btn2_press()
            elif command == "previous":
                self.previous_screen()
            elif command == "next":
                self.next_screen()
            elif command == "reload":
                self.current_screen().reload()
                self.current_screen().show()
            elif command == "screen":
                self.logger.debug("Attempting switch to screen '{0}'".format(parts[1]))
                self.current_screen_index = self.find_screen_index_by_name(parts[1])
                if self.current_screen_index < 0:
                    self.logger.error("Couldn't find screen '{0}'".format(parts[1]))
                    self.current_screen_index = 0
                self.current_screen().reload()
                self.current_screen().show()
            elif command == "remove_screen":
                self.logger.debug("Attempting to remove screen '{0}'".format(parts[1]))
                screen_to_remove = self.get_screen_by_name(parts[1])
                module_to_remove = self.get_screen_module_by_name(parts[1])

                if screen_to_remove and module_to_remove:
                    if self.current_screen_index == self.find_screen_index_by_name(parts[1]):
                        self.current_screen_index = 0
                        self.current_screen().reload()
                    self.screens.remove(screen_to_remove)
                    self.screen_modules.remove(module_to_remove)
                    self.logger.info(f"Successfully removed screen '{parts[1]}'")
                else:
                    self.logger.error(f"Cannot remove screen '{parts[1]}': not found")
            elif command == "add_screen":
                self.logger.debug("Attempting to add screen '{0}'".format(parts[1]))
                if self.get_screen_by_name(parts[1]):
                    self.logger.error("Screen '{0}' already added".format(parts[1]))
                else:
                    self.add_screen(parts[1])

            else:
                self.logger.error("Command '{0}' not recognized".format(command))

    def loop(self):
        while True:
            self.process_message()

            time.sleep(1)

            # self.weather.refresh_interval -= 1
            # if self.weather.refresh_interval < 1:
            #     # asyncio.get_event_loop().run_until_complete(self.weather.update())
            #     update_weather()
            #     self.current_screen().reload()
            #     self.current_screen().show()
            #     self.weather.refresh_interval = settings.WEATHER_REFRESH

            self.current_screen().iterate_loop()

            if self.loop_time >= TIME:
                self.loop_time = 0

            self.loop_time += 1

            if self.loop_time == 1:
                self.current_screen().show()


if __name__ == '__main__':
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))

    app = App()
    app.loop()
