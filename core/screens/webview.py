import threading
import logging
from PIL import Image, ImageDraw, ImageFont

from screens import AbstractScreen

try:
    from local_settings import WEBVIEW_URL
except ImportError:
    WEBVIEW_URL = "http://tsbarnes.com/"

try:
    from local_settings import WEBVIEW_RELOAD_INTERVAL
except ImportError:
    WEBVIEW_RELOAD_INTERVAL = 300  # 5 minutes default

try:
    from local_settings import WEBVIEW_SCALE
except ImportError:
    WEBVIEW_SCALE = 0.5  # Scale factor for webpage rendering (0.5 = 50%)

try:
    from local_settings import WEBVIEW_ORIENTATION
except ImportError:
    WEBVIEW_ORIENTATION = 'landscape'  # 'landscape' or 'portrait'


class Screen(AbstractScreen):
    """
    This class provides the screen methods needed by epdtext
    """
    webshot = None
    error_message = None
    _initialized = False
    _cached_screenshot = None
    _is_rendering = False
    _render_thread = None
    reload_interval = WEBVIEW_RELOAD_INTERVAL  # Override default reload interval

    def _init_webshot(self):
        """Lazy initialization of WebShot"""
        if self._initialized:
            return

        self._initialized = True
        try:
            from htmlwebshot import WebShot
            # Initialize WebShot without custom config - keep it simple
            self.webshot = WebShot()
        except FileNotFoundError as e:
            self.error_message = "wkhtmltopdf not found.\nInstall with:\nsudo apt install wkhtmltopdf"
        except ImportError as e:
            self.error_message = "htmlwebshot not installed.\nInstall with:\npip3 install htmlwebshot"
        except Exception as e:
            self.error_message = f"WebShot init failed:\n{str(e)}"

    def _render_webpage_async(self):
        """Render webpage in background thread"""
        try:
            logging.info(f"Starting webpage render for {WEBVIEW_URL} (scale: {WEBVIEW_SCALE})")
            size = self.display.get_size()  # Returns (EPD_HEIGHT=264, EPD_WIDTH=176)

            # PIL Images use (width, height) format
            # get_size() returns (264, 176) which PIL interprets as width=264, height=176
            # So the display is 264px wide x 176px tall (landscape orientation)
            pil_width = size[0]   # 264 pixels wide
            pil_height = size[1]  # 176 pixels tall

            # Account for titlebar (20px at top)
            content_height = pil_height - 20  # 176 - 20 = 156 pixels
            content_width = pil_width         # 264 pixels

            # Render webpage based on orientation setting
            # Use typical mobile resolution (iPhone 12/13/14)
            if WEBVIEW_ORIENTATION.lower() == 'portrait':
                base_width = 390   # Portrait: narrow
                base_height = 844  # Portrait: tall
            else:  # landscape (default)
                base_width = 844   # Landscape: wide
                base_height = 390  # Landscape: short

            # Scale up based on WEBVIEW_SCALE for better quality
            render_width = int(base_width / WEBVIEW_SCALE)
            render_height = int(base_height / WEBVIEW_SCALE)

            logging.info(f"Rendering in {WEBVIEW_ORIENTATION} mode: {render_width}x{render_height}")

            # wkhtmltoimage expects (width, height)
            # Try multiple rendering strategies if one fails
            screenshot_path = None

            # Strategy 1: Mobile user agent with error handling
            try:
                logging.debug("Trying mobile rendering with error handling")
                screenshot_path = self.webshot.create_pic(
                    url=WEBVIEW_URL,
                    size=(render_width, render_height),
                    params={
                        '--load-error-handling': 'ignore',
                        '--load-media-error-handling': 'ignore',
                        '--custom-header': 'User-Agent Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1',
                        '--custom-header-propagation': '',
                        '--no-stop-slow-scripts': ''
                    }
                )
            except Exception as e1:
                logging.warning(f"Mobile render failed: {e1}")
                # Strategy 2: Minimal params, no custom headers
                try:
                    logging.debug("Trying minimal rendering (no custom params)")
                    screenshot_path = self.webshot.create_pic(
                        url=WEBVIEW_URL,
                        size=(render_width, render_height)
                    )
                except Exception as e2:
                    # Both strategies failed, re-raise the exception
                    raise Exception(f"All rendering strategies failed. Last error: {e2}")

            screenshot = Image.open(screenshot_path)

            # Resize to fit display maintaining aspect ratio
            # Calculate scale to fit display width
            scale_to_width = content_width / screenshot.width
            new_width = content_width
            new_height = int(screenshot.height * scale_to_width)

            # Resize maintaining 16:9 aspect ratio
            self._cached_screenshot = screenshot.resize((new_width, new_height), Image.LANCZOS)

            logging.info(f"Webpage render completed: {render_width}x{render_height} -> {content_width}x{content_height}")

            # Clear any previous error message on successful render
            self.error_message = None

            # Force immediate display update to show the new screenshot
            self.reload()
            self.show()
        except Exception as e:
            logging.error(f"Error rendering webpage: {e}")
            # Don't overwrite error_message if it's a setup error (wkhtmltopdf not found, etc)
            # Only set it if it's a runtime rendering error
            if not self.error_message or "not found" not in self.error_message.lower():
                # Keep cached screenshot if available, just log the error
                if self._cached_screenshot:
                    logging.warning("Render failed but using cached screenshot")
                else:
                    self.error_message = f"Render failed:\n{str(e)[:50]}"
        finally:
            self._is_rendering = False

    def handle_btn_press(self, button_number: int = 1):
        """
        This method receives the button presses
        """

        # Buttons 0 and 3 are used to switch screens
        if button_number == 1:
            # Force refresh - clear cache and start new render
            if not self._is_rendering:
                self._cached_screenshot = None
                self.reload()
                self.show()
        elif button_number == 2:
            pass

    def reload(self):
        """
        This method should draw the contents of the screen to self.image
        """
        # Initialize WebShot on first reload
        self._init_webshot()

        self.blank()
        self.draw_titlebar("Web View")

        if self.error_message:
            # Show error message if WebShot is not available
            lines = self.error_message.split('\n')
            y_position = 40
            for line in lines:
                self.text(line, font_size=14, position=(10, y_position))
                y_position += 20
        elif self.webshot:
            # WebShot is available
            if self._cached_screenshot:
                # Use cached screenshot
                self.image.paste(self._cached_screenshot, (0, 20))
                # Note: Background refresh is handled by iterate_loop() via reload_interval
            elif self._is_rendering:
                # Currently rendering in background
                self.text("Rendering webpage...", font_size=14, position=(10, 40))
                self.text(f"URL: {WEBVIEW_URL}", font_size=10, position=(10, 60))
                self.text("This may take 1-2 minutes", font_size=12, position=(10, 80))
            else:
                # First load - start background render
                self._is_rendering = True
                self._render_thread = threading.Thread(target=self._render_webpage_async, daemon=True)
                self._render_thread.start()

                self.text("Loading webpage...", font_size=14, position=(10, 40))
                self.text(f"URL: {WEBVIEW_URL}", font_size=10, position=(10, 60))
        else:
            self.text("WebShot not initialized", font_size=14, position=(10, 40))

    def iterate_loop(self):
        """
        This method is optional, and will be run once per cycle
        """
        # Start background refresh when reload_interval expires
        if self.webshot and self._cached_screenshot and not self._is_rendering:
            # Check if it's time for auto-refresh (handled by parent's iterate_loop)
            if self.reload_wait >= self.reload_interval:
                logging.info("Auto-refresh triggered, starting background render")
                self._is_rendering = True
                self.reload_wait = 0  # Reset counter to prevent immediate re-trigger
                self._render_thread = threading.Thread(target=self._render_webpage_async, daemon=True)
                self._render_thread.start()

        # This line is very important, it keeps the auto reload working
        super().iterate_loop()
