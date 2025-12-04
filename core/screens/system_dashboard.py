#!/usr/bin/env python3
"""
System Dashboard Screen with Pie Charts
Shows CPU, Memory, Temperature, and Disk usage with pie charts on the left
and system info text on the right
"""

from screens import AbstractScreen
import psutil
import socket
import settings

class Screen(AbstractScreen):
    def __init__(self):
        super().__init__()
        self.reload_interval = 30  # Refresh every 30 seconds
        self._cached_data = None
        self._is_loading = False

    def get_cpu_percent(self):
        """Get CPU usage percentage"""
        return psutil.cpu_percent(interval=0.1)

    def get_memory_percent(self):
        """Get memory usage percentage"""
        mem = psutil.virtual_memory()
        return mem.percent

    def get_cpu_temp(self):
        """Get CPU temperature"""
        try:
            temps = psutil.sensors_temperatures()
            if 'cpu_thermal' in temps:
                return temps['cpu_thermal'][0].current
            elif 'coretemp' in temps:
                return temps['coretemp'][0].current
        except:
            pass
        return None

    def get_disk_percent(self):
        """Get disk usage percentage for root partition"""
        disk = psutil.disk_usage('/')
        return disk.percent

    def get_model(self):
        """Get Raspberry Pi model"""
        try:
            with open('/sys/firmware/devicetree/base/model', 'r') as f:
                model = f.read().strip('\x00')
                # Simplify model name
                if 'Raspberry Pi 4' in model:
                    return 'RPi 4B'
                elif 'Raspberry Pi 3' in model:
                    return 'RPi 3B'
                else:
                    return 'RPi'
        except:
            return 'Unknown'

    def get_os_info(self):
        """Get OS information"""
        try:
            import distro
            return f"{distro.name()} {distro.version()}"
        except:
            try:
                with open('/etc/os-release', 'r') as f:
                    for line in f:
                        if line.startswith('PRETTY_NAME='):
                            return line.split('=')[1].strip().strip('"')
            except:
                pass
        return 'Linux'

    def get_network_interface(self):
        """Get active network interface"""
        try:
            from local_settings import NETWORK_INTERFACE
            # Check if interface exists
            if NETWORK_INTERFACE in psutil.net_if_addrs():
                return NETWORK_INTERFACE
        except:
            pass

        # Auto-detect
        interfaces = psutil.net_if_addrs()
        for iface in ['eth0', 'wlan0', 'en0']:
            if iface in interfaces:
                return iface
        return 'unknown'

    def get_ip_address(self):
        """Get local IP address"""
        iface = self.get_network_interface()
        try:
            addrs = psutil.net_if_addrs()
            if iface in addrs:
                for addr in addrs[iface]:
                    if addr.family == socket.AF_INET:
                        return addr.address
        except:
            pass
        return 'N/A'

    def get_uptime(self):
        """Get system uptime"""
        try:
            import datetime
            uptime_seconds = psutil.boot_time()
            uptime_delta = datetime.datetime.now() - datetime.datetime.fromtimestamp(uptime_seconds)

            days = uptime_delta.days
            hours = uptime_delta.seconds // 3600
            minutes = (uptime_delta.seconds % 3600) // 60

            if days > 0:
                return f"{days}d {hours}h {minutes}m"
            elif hours > 0:
                return f"{hours}h {minutes}m"
            else:
                return f"{minutes}m"
        except:
            return "N/A"

    def draw_pie_chart(self, cx, cy, size, percentage, label, value_text):
        """Draw a single pie chart with label and value"""
        from PIL import ImageDraw, ImageFont

        # Calculate bbox
        bbox = [cx - size//2, cy - size//2, cx + size//2, cy + size//2]

        # Create draw object
        draw = ImageDraw.Draw(self.image)

        # Draw filled portion (black)
        if percentage > 0:
            angle = int((percentage / 100) * 360)
            draw.pieslice(bbox, start=-90, end=-90 + angle, fill=0, outline=0)

        # Draw outer ring
        draw.ellipse(bbox, outline=0, width=2)

        # Label below pie
        try:
            font_label = ImageFont.truetype(settings.FONT, 9)
        except:
            font_label = ImageFont.load_default()
        label_bbox = draw.textbbox((0, 0), label, font=font_label)
        label_width = label_bbox[2] - label_bbox[0]
        self.text(label, font_size=9, position=(cx - label_width // 2, cy + size // 2 + 3))

        # Value below label
        try:
            font_value = ImageFont.truetype(settings.FONT, 11)
        except:
            font_value = ImageFont.load_default()
        value_bbox = draw.textbbox((0, 0), value_text, font=font_value)
        value_width = value_bbox[2] - value_bbox[0]
        self.text(value_text, font_size=11, position=(cx - value_width // 2, cy + size // 2 + 13))

    def _collect_data(self):
        """Collect all system data - can be slow"""
        return {
            'cpu': self.get_cpu_percent(),
            'mem': self.get_memory_percent(),
            'temp': self.get_cpu_temp(),
            'disk': self.get_disk_percent(),
            'model': self.get_model(),
            'os': self.get_os_info(),
            'iface': self.get_network_interface(),
            'ip': self.get_ip_address(),
            'uptime': self.get_uptime(),
            'tailscale': self._get_tailscale_status()
        }

    def _get_tailscale_status(self):
        """Get Tailscale status"""
        try:
            from libs.tailscale import Tailscale
            ts = Tailscale()
            if ts.is_connected:  # Property, not method
                return "✓ Online"
        except:
            pass
        return "✗ Offline"

    def reload(self):
        self.blank()
        self.draw_titlebar("System Dashboard")

        # Use cached data if available, otherwise show loading
        if self._cached_data is None:
            # First load - show loading message centered
            self.centered_text("Loading system data...", font_size=14, y=80)
            self.show()
            # Collect data for first time
            self._cached_data = self._collect_data()
            # Redraw with actual data
            self.blank()
            self.draw_titlebar("System Dashboard")

        # Get metrics from cache
        cpu_percent = self._cached_data['cpu']
        mem_percent = self._cached_data['mem']
        temp = self._cached_data['temp']
        disk_percent = self._cached_data['disk']

        # LEFT SIDE: Pie charts (2x2 grid)
        pie_size = 35
        left_width = 105
        padding = 12
        start_y = 30

        metrics = [
            {"name": "CPU", "value": cpu_percent, "unit": "%"},
            {"name": "MEM", "value": mem_percent, "unit": "%"},
            {"name": "TEMP", "value": temp, "unit": "°C", "max": 85},
            {"name": "DISK", "value": disk_percent, "unit": "%"},
        ]

        for idx, metric in enumerate(metrics):
            row = idx // 2
            col = idx % 2

            # Calculate position
            x_offset = padding + col * 50
            y_offset = start_y + row * 70

            # Pie chart center
            cx = x_offset + pie_size // 2
            cy = y_offset + pie_size // 2

            # Calculate percentage
            if "max" in metric:
                if metric["value"] is not None:
                    percentage = (metric["value"] / metric["max"]) * 100
                    value_text = f"{int(metric['value'])}{metric['unit']}"
                else:
                    percentage = 0
                    value_text = "N/A"
            else:
                percentage = metric["value"]
                value_text = f"{int(metric['value'])}{metric['unit']}"

            # Draw pie chart
            self.draw_pie_chart(cx, cy, pie_size, percentage, metric["name"], value_text)

        # Vertical divider line
        self.line((left_width, 20, left_width, self.display.get_size()[1] - 5), width=1)

        # RIGHT SIDE: System info text
        right_x = left_width + 12
        text_y = 31
        line_height = 13

        # Get system info from cache
        model = self._cached_data['model']
        os_info = self._cached_data['os']
        # Truncate long OS names
        if len(os_info) > 20:
            os_info = os_info[:17] + "..."
        iface = self._cached_data['iface']
        ip = self._cached_data['ip']
        uptime = self._cached_data['uptime']
        tailscale_status = self._cached_data['tailscale']

        info_lines = [
            ("System Info", 12, False),  # Increased from 11
            ("─────────────────", 10, False),  # Increased from 9
            (f"Model: {model}", 11, False),  # Increased from 10
            (f"OS: {os_info}", 11, False),  # Increased from 10
            ("", 11, False),
            (f"Network: {iface}", 11, False),  # Increased from 10
            (f"IP: {ip}", 11, False),  # Increased from 10
            (f"Tailscale: {tailscale_status}", 11, False),  # Increased from 10
            ("", 11, False),
            (f"Uptime: {uptime}", 11, False),  # Increased from 10
        ]

        for line_text, font_size, bold in info_lines:
            if line_text == "":
                text_y += line_height
                continue
            self.text(line_text, font_size=font_size, position=(right_x, text_y))
            text_y += line_height

    def iterate_loop(self):
        """Update cache in background during auto-refresh"""
        if self.reload_wait >= self.reload_interval:
            # Update cache before reload
            self._cached_data = self._collect_data()
        super().iterate_loop()

    def handle_btn_press(self, button_number):
        """Handle button press - refresh on KEY1"""
        if button_number == 0:  # KEY1
            # Update cache and reload
            self._cached_data = self._collect_data()
            self.reload()
            self.show()
