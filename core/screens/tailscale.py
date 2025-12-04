import logging
from PIL import Image

import settings
from libs.tailscale import get_tailscale
from screens import AbstractScreen


class Screen(AbstractScreen):
    """
    Tailscale status screen showing connection info, local/Tailscale IPs,
    exit node status, and connected peers
    """
    tailscale = get_tailscale()
    reload_interval = 30  # Refresh every 30 seconds

    def reload(self):
        # Invalidate cache to get fresh data
        self.tailscale.invalidate_cache()

        self.blank()
        self.draw_titlebar("Tailscale")

        # LEFT: Tailscale icon (top-left, 55x55, aligned with peers)
        try:
            icon = Image.open("images/tailscale.png")
            icon = icon.resize((55, 55))
            self.image.paste(icon, (5, 25))
        except FileNotFoundError:
            logging.warning("Tailscale icon not found at images/tailscale.png")

        # RIGHT: Build the status string (larger font: 13pt)
        string = ''

        # Connection status
        if self.tailscale.is_connected:
            string += 'Status:    ✓ Connected\n'
        else:
            string += 'Status:    ✗ Disconnected\n'

        # Local IP
        local_ip = self.tailscale.local_ip
        if local_ip:
            string += f'Local:     {local_ip}\n'
        else:
            string += 'Local:     N/A\n'

        # Tailscale IP
        ts_ip = self.tailscale.tailscale_ip
        if ts_ip:
            string += f'Tailscale: {ts_ip}\n'
        else:
            string += 'Tailscale: N/A\n'

        # Exit node status
        exit_status = self.tailscale.exit_node_status
        if exit_status == "Available":
            string += 'Exit Node: ✓ Available'
        else:  # Disabled
            string += 'Exit Node: - Disabled'

        # Draw the status information (larger font, adjusted for bigger logo)
        self.text(string, font_size=13, font_name=settings.MONOSPACE_FONT, position=(73, 25), wrap=False)

        # Horizontal divider
        self.line((5, 105, self.display.get_size()[0] - 5, 105), width=1)

        # BOTTOM: Peers section
        peers_count = self.tailscale.peers_online
        peers_header = f'Peers:     {peers_count} online'
        self.text(peers_header, font_size=13, font_name=settings.MONOSPACE_FONT, position=(5, 111), wrap=False)

        # Peer list (3 columns, up to 9 peers)
        peer_names = self.tailscale.peer_names
        if peer_names:
            col1_x = 8
            col2_x = 93
            col3_x = 178
            peer_y = 130
            col_height = 10
            peers_per_col = 3

            for idx, peer in enumerate(peer_names):
                col = idx // peers_per_col
                row = idx % peers_per_col

                if col == 0:
                    x = col1_x
                elif col == 1:
                    x = col2_x
                else:
                    x = col3_x

                y = peer_y + row * col_height
                self.text(f'• {peer}', font_size=10, position=(x, y), wrap=False)

    def iterate_loop(self):
        """
        Called every second by main loop
        Handles auto-refresh and ensures display is updated
        """
        super().iterate_loop()  # This handles reload_wait and calls reload()

        # Check if we just reloaded (reload_wait was reset to 0)
        if self.reload_wait == 0 and self.image:
            self.show()  # Update the physical display after reload

    def handle_btn_press(self, button_number=1):
        """
        Handle button presses
        Button 1: Reload screen
        """
        if button_number == 1:
            self.reload()
            self.show()
