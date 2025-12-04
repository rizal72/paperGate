import json
import logging
import socket
import subprocess
import sys
import os
import psutil

# Add parent directory to path for standalone execution
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Lazy load NETWORK_INTERFACE to avoid circular imports
_NETWORK_INTERFACE = None

def get_network_interface():
    global _NETWORK_INTERFACE
    if _NETWORK_INTERFACE is None:
        try:
            # Read local_settings.py as text to avoid circular imports
            local_settings_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "local_settings.py")
            if os.path.exists(local_settings_path):
                with open(local_settings_path, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith('NETWORK_INTERFACE'):
                            # Parse: NETWORK_INTERFACE='eth0' or NETWORK_INTERFACE="eth0"
                            if '=' in line:
                                value = line.split('=', 1)[1].strip()
                                # Remove quotes
                                value = value.strip('\'"')
                                _NETWORK_INTERFACE = value
                                break
            if _NETWORK_INTERFACE is None:
                _NETWORK_INTERFACE = 'wlan0'
        except Exception as e:
            logger.debug(f"Could not load NETWORK_INTERFACE from local_settings: {e}")
            _NETWORK_INTERFACE = 'wlan0'
    return _NETWORK_INTERFACE


logger = logging.getLogger('epdtext.libs.tailscale')


class Tailscale:
    """
    This class provides access to Tailscale information
    """

    def __init__(self):
        self._status_cache = None
        self._cache_valid = False

    def _get_status(self):
        """
        Get Tailscale status from tailscale CLI
        Returns parsed JSON or None if error
        """
        if self._cache_valid and self._status_cache:
            return self._status_cache

        try:
            result = subprocess.run(
                ['tailscale', 'status', '--json'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                self._status_cache = json.loads(result.stdout)
                self._cache_valid = True
                return self._status_cache
            else:
                logger.error(f"tailscale status failed: {result.stderr}")
                return None
        except subprocess.TimeoutExpired:
            logger.error("tailscale status timed out")
            return None
        except FileNotFoundError:
            logger.error("tailscale command not found")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse tailscale status JSON: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error getting tailscale status: {e}")
            return None

    def invalidate_cache(self):
        """
        Invalidate the status cache to force refresh on next access
        """
        self._cache_valid = False

    @property
    def is_connected(self):
        """
        Check if Tailscale is connected
        """
        status = self._get_status()
        if not status:
            return False

        backend_state = status.get('BackendState', '')
        return backend_state == 'Running'

    @property
    def tailscale_ip(self):
        """
        Get the Tailscale IPv4 address
        """
        status = self._get_status()
        if not status:
            return None

        ips = status.get('TailscaleIPs', [])
        # Return the first IPv4 address (non-IPv6)
        for ip in ips:
            if ':' not in ip:  # Simple check for IPv4
                return ip
        return None

    @property
    def local_ip(self):
        """
        Get the local network IPv4 address
        """
        try:
            network_interface = get_network_interface()
            for interface_name, interface_addresses in psutil.net_if_addrs().items():
                for address in interface_addresses:
                    if interface_name == network_interface and address.family == socket.AF_INET:
                        return address.address
            return None
        except Exception as e:
            logger.error(f"Error getting local IP: {e}")
            return None

    @property
    def hostname(self):
        """
        Get the Tailscale hostname
        """
        status = self._get_status()
        if not status:
            return None

        self_info = status.get('Self', {})
        return self_info.get('HostName', None)

    @property
    def is_exit_node_enabled(self):
        """
        Check if this node is advertising as an exit node
        """
        status = self._get_status()
        if not status:
            return False

        self_info = status.get('Self', {})
        # Check if AdvertiseRoutes contains the default routes
        advertised_routes = self_info.get('AllowedIPs', [])

        # Exit node advertises 0.0.0.0/0 and/or ::/0
        has_ipv4_default = '0.0.0.0/0' in advertised_routes
        has_ipv6_default = '::/0' in advertised_routes

        return has_ipv4_default or has_ipv6_default

    @property
    def exit_node_status(self):
        """
        Get exit node status as a string
        Returns: "Available" or "Disabled"
        Note: Tailscale API does not expose which peers are using this node as exit node
        """
        if self.is_exit_node_enabled:
            return "Available"
        else:
            return "Disabled"

    @property
    def peers_online(self):
        """
        Count number of online peers
        """
        status = self._get_status()
        if not status:
            return 0

        peer_status = status.get('Peer', {})
        online_count = 0

        for peer_id, peer_data in peer_status.items():
            # Check if peer is online (has recent activity)
            if peer_data.get('Online', False):
                online_count += 1

        return online_count

    @property
    def peer_names(self):
        """
        Get list of online peer hostnames
        Returns: List of peer hostnames (up to 9)
        """
        status = self._get_status()
        if not status:
            return []

        peer_status = status.get('Peer', {})
        peer_list = []

        for peer_id, peer_data in peer_status.items():
            # Check if peer is online
            if peer_data.get('Online', False):
                hostname = peer_data.get('HostName', 'unknown')
                peer_list.append(hostname)

        # Sort alphabetically and limit to 9
        peer_list.sort()
        return peer_list[:9]

    @property
    def backend_state(self):
        """
        Get the backend state string
        """
        status = self._get_status()
        if not status:
            return "Unknown"

        return status.get('BackendState', 'Unknown')


# Singleton instance
tailscale = Tailscale()


def get_tailscale():
    """
    Get the singleton Tailscale instance
    """
    return tailscale


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    ts = get_tailscale()

    print(f"Connected: {ts.is_connected}")
    print(f"Backend State: {ts.backend_state}")
    print(f"Local IP: {ts.local_ip}")
    print(f"Tailscale IP: {ts.tailscale_ip}")
    print(f"Hostname: {ts.hostname}")
    print(f"Exit Node Enabled: {ts.is_exit_node_enabled}")
    print(f"Exit Node Status: {ts.exit_node_status}")
    print(f"Peers Online: {ts.peers_online}")
