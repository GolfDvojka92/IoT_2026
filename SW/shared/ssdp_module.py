import socket
import threading
import time

# SSDP  configuration constants
SSDP_MULTICAST_ADDR     = "239.255.255.250"
SSDP_PORT               = 1900
SSDP_TTL                = 2     # multicast hops
SSDP_MX                 = 3     # max seconds devices may wait before responding to M-SEARCH
SSDP_MAX_AGE            = 120   # max seconds before device is labeled UNAVAILABLE by the controller
SSDP_ADVERTISE_INTERVAL = 10    # device advertise interval in seconds

class SSDPModule:
    def __init__(self, device_id: str, device_type: str, location: str):
        self.device_id   = device_id    # unique device name
        self.device_type = device_type  # service label
        self.location    = location     # where to reach device (won't be used, needed for the protocol, will hold placeholder string)
        self._running    = False        
        self._listener   = None
        self._advertiser = None

    """
        Broadcasts an SSDP NOTIFY message announcing that this device is online.
        Other devices listening on the multicast group can detect it.
    """
    def advertise(self): 
        message = (
            "NOTIFY * HTTP/1.1\r\n"
            f"HOST: {SSDP_MULTICAST_ADDR}:{SSDP_PORT}\r\n"
            "NTS: ssdp:alive\r\n"
            f"NT: {self.device_type}\r\n"
            f"USN: uuid:{self.device_id}::{self.device_type}\r\n"
            f"LOCATION: {self.location}\r\n"
            f"CACHE-CONTROL: max-age={SSDP_MAX_AGE}\r\n"
            "\r\n"
        ).encode("utf-8")

        # Create UDP multicast socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, SSDP_TTL)
       
        # Send advertisement
        sock.sendto(message, (SSDP_MULTICAST_ADDR, SSDP_PORT))
        sock.close()

        print(f"[{self.device_id}] SSDP NOTIFY sent (ssdp:alive)")

    """
        Broadcasts an SSDP NOTIFY message announcing that this device is leaving.
    """
    def send_byebye(self):
        message = (
            "NOTIFY * HTTP/1.1\r\n"
            f"HOST: {SSDP_MULTICAST_ADDR}:{SSDP_PORT}\r\n"
            "NTS: ssdp:byebye\r\n"
            f"NT: {self.device_type}\r\n"
            f"USN: uuid:{self.device_id}::{self.device_type}\r\n"
            "\r\n"
        ).encode("utf-8")

        # Create UDP multicast socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, SSDP_TTL)
        
        # Send departure notification
        sock.sendto(message, (SSDP_MULTICAST_ADDR, SSDP_PORT))
        sock.close()

        print(f"[{self.device_id}] SSDP NOTIFY sent (ssdp:byebye)")

    """
        Sends an SSDP M-SEARCH request to discover devices.

        Args:
            search_target:
                - "ssdp:all" to find all devices
                - Specific device/service type to filter results

        Returns:
            List of discovered device responses.
    """
    def search(self, search_target: str = "ssdp:all"):
        message = (
            "M-SEARCH * HTTP/1.1\r\n"
            f"HOST: {SSDP_MULTICAST_ADDR}:{SSDP_PORT}\r\n"
            "MAN: \"ssdp:discover\"\r\n"
            f"MX: {SSDP_MX}\r\n"
            f"ST: {search_target}\r\n"
            "\r\n"
        ).encode("utf-8")

        # Create UDP multicast socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, SSDP_TTL)
        sock.settimeout(SSDP_MX + 1)

        # Send search request
        sock.sendto(message, (SSDP_MULTICAST_ADDR, SSDP_PORT))
        
        print(f"[{self.device_id}] M-SEARCH sent for '{search_target}'")

        discovered = []
        try:
            while True:
                data, addr = sock.recvfrom(4096)
                response   = data.decode("utf-8", errors="ignore")
                print(f"[{self.device_id}] Response from {addr[0]}")
                discovered.append((addr, response))
        
        except socket.timeout:
            print(f"[{self.device_id}] Search complete — {len(discovered)} device(s) found")
        
        finally:
            sock.close()

        return discovered

    """
        Starts the SSDP listener thread for receiving SSDP traffic.
    """
    def start_listener(self):
        self._running  = True
        self._listener = threading.Thread(target=self._listen_loop, daemon=True)
        self._listener.start()
        print(f"[{self.device_id}] SSDP listener started")

    """
        Starts the recurring advertiser thread.
        Periodically broadcasts ssdp:alive notifications.
    """
    def start_advertiser(self):
        self._advertiser = threading.Thread(target=self._advertise_loop, daemon=True)
        self._advertiser.start()
        print(f"[{self.device_id}] SSDP advertiser started")

    """
        Stops listener and advertiser threads.
    """
    def stop_bg_threads(self):
        self._running = False
        print(f"[{self.device_id}] SSDP listener stopped")
        print(f"[{self.device_id}] SSDP advertiser stopped")

    """
        Continuously sends periodic SSDP advertisements while running.
    """
    def _advertise_loop(self):
        while self._running:
            self.advertise()
            time.sleep(SSDP_ADVERTISE_INTERVAL)

    """
        Main listener loop:
        - Joins SSDP multicast group
        - Receives SSDP traffic
        - Processes messages
    """
    def _listen_loop(self):
        # Create UDP socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("", SSDP_PORT))

        # Join the SSDP multicast group
        group = socket.inet_aton(SSDP_MULTICAST_ADDR) + socket.inet_aton("0.0.0.0")
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, group)
        
        # Timeout allows periodic checking of self._running
        sock.settimeout(1.0)

        while self._running:
            try:
                data, addr = sock.recvfrom(4096)
                self._handle_ssdp_message(data.decode("utf-8", errors="ignore"), addr)
            
            except socket.timeout:
                continue

        sock.close()

    """
        Handles incoming SSDP messages:
        - M-SEARCH requests
        - ssdp:alive notifications
        - ssdp:byebye notifications
    """
    def _handle_ssdp_message(self, message: str, addr: tuple):
        if "M-SEARCH" in message:
            search_target = self._parse_header(message, "ST")

            # Respond if the search is for everyone, or specifically for our device type
            if search_target in ("ssdp:all", self.device_type):
                self._send_ok_response(addr)
    """
        Sends HTTP 200 OK response directly to a device that sent M-SEARCH.
    """
    def _send_ok_response(self, addr: tuple):
        response = (
            "HTTP/1.1 200 OK\r\n"
            f"ST: {self.device_type}\r\n"
            f"USN: uuid:{self.device_id}::{self.device_type}\r\n"
            f"LOCATION: {self.location}\r\n"
            "CACHE-CONTROL: max-age=1800\r\n"
            "EXT:\r\n"               # required by the SSDP spec, indicates MAN was understood
            f"DATE: {time.strftime('%a, %d %b %Y %H:%M:%S GMT', time.gmtime())}\r\n"
            "SERVER: Python/SSDP BabyMonitor/1.0\r\n"
            "\r\n"
        ).encode("utf-8")

        # Unicast — a fresh UDP socket aimed directly at the requester's IP and port
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.sendto(response, addr)
        sock.close()
        print(f"[{self.device_id}] Sent HTTP 200 OK to {addr[0]}")

    """
        Extracts a specific HTTP-style header value from an SSDP message.

        Args:
            message: Raw SSDP message
            header: Header name to search for

        Returns:
            Header value if found, otherwise empty string
    """
    def _parse_header(self, message: str, header: str) -> str:
        for line in message.splitlines():
            if line.upper().startswith(header.upper() + ":"):
                return line.split(":", 1)[1].strip()
        return ""
