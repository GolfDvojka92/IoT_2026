import socket
import threading
import time

# SSDP uses this multicast address and port — these are standard, don't change them
SSDP_MULTICAST_ADDR = "239.255.255.250"
SSDP_PORT           = 1900
SSDP_TTL            = 2       # multicast hops
SSDP_MX             = 3       # max seconds devices may wait before responding to M-SEARCH

class SSDPModule:
    def __init__(self, device_id: str, device_type: str, location: str):
        self.device_id   = device_id    # unique device name
        self.device_type = device_type  # service label
        self.location    = location     # where to reach device (won't be used, needed for the protocol, will hold placeholder string)
        self._running    = False
        self._listener   = None

    # ------------------------------------------------------- #
    #                         NOTIFY                          #
    # ------------------------------------------------------- #

    # Multicasts a NOTIFY message to other devices telling them it's come online
    def advertise(self):
        message = (
            "NOTIFY * HTTP/1.1\r\n"
            f"HOST: {SSDP_MULTICAST_ADDR}:{SSDP_PORT}\r\n"
            "NTS: ssdp:alive\r\n"
            f"NT: {self.device_type}\r\n"
            f"USN: uuid:{self.device_id}::{self.device_type}\r\n"
            f"LOCATION: {self.location}\r\n"
            "CACHE-CONTROL: max-age=1800\r\n"
            "\r\n"
        ).encode("utf-8")

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, SSDP_TTL)
        sock.sendto(message, (SSDP_MULTICAST_ADDR, SSDP_PORT))
        sock.close()
        print(f"[{self.device_id}] SSDP NOTIFY sent (ssdp:alive)")

    # Announces it's going offline
    def send_byebye(self):
        message = (
            "NOTIFY * HTTP/1.1\r\n"
            f"HOST: {SSDP_MULTICAST_ADDR}:{SSDP_PORT}\r\n"
            "NTS: ssdp:byebye\r\n"
            f"NT: {self.device_type}\r\n"
            f"USN: uuid:{self.device_id}::{self.device_type}\r\n"
            "\r\n"
        ).encode("utf-8")

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, SSDP_TTL)
        sock.sendto(message, (SSDP_MULTICAST_ADDR, SSDP_PORT))
        sock.close()
        print(f"[{self.device_id}] SSDP NOTIFY sent (ssdp:byebye)")

    # ------------------------------------------------------- #
    #                       M-SEARCH                          #
    # ------------------------------------------------------- #

    # Broadcasts an M-SEARCH and prints any responses received within MX seconds
    # search_target can be "ssdp:all" or a specific device type string
    def search(self, search_target: str = "ssdp:all"):
        message = (
            "M-SEARCH * HTTP/1.1\r\n"
            f"HOST: {SSDP_MULTICAST_ADDR}:{SSDP_PORT}\r\n"
            "MAN: \"ssdp:discover\"\r\n"
            f"MX: {SSDP_MX}\r\n"
            f"ST: {search_target}\r\n"
            "\r\n"
        ).encode("utf-8")

        # sends M-SEARCH through UDP
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, SSDP_TTL)
        sock.settimeout(SSDP_MX + 1)
        sock.sendto(message, (SSDP_MULTICAST_ADDR, SSDP_PORT))
        print(f"[{self.device_id}] M-SEARCH sent for '{search_target}'")

        discovered = []
        try:
            while True:
                data, addr = sock.recvfrom(4096)
                response   = data.decode("utf-8", errors="ignore")
                print(f"[{self.device_id}] Response from {addr[0]}:\n{response}")
                discovered.append((addr, response))
        except socket.timeout:
            print(f"[{self.device_id}] Search complete — {len(discovered)} device(s) found")
        finally:
            sock.close()

        return discovered

    # ------------------------------------------------------- #
    #                       Listener                          #
    # ------------------------------------------------------- #

    # Starts a background thread that listens for SSDP traffic
    def start_listener(self):
        self._running  = True
        self._listener = threading.Thread(target=self._listen_loop, daemon=True)
        self._listener.start()
        print(f"[{self.device_id}] SSDP listener started")

    def stop_listener(self):
        self._running = False
        print(f"[{self.device_id}] SSDP listener stopped")

    def _listen_loop(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("", SSDP_PORT))

        # Join the SSDP multicast group
        group = socket.inet_aton(SSDP_MULTICAST_ADDR) + socket.inet_aton("0.0.0.0")
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, group)
        sock.settimeout(1.0)

        while self._running:
            try:
                data, addr = sock.recvfrom(4096)
                self._handle_ssdp_message(data.decode("utf-8", errors="ignore"), addr)
            except socket.timeout:
                continue

        sock.close()

    def _handle_ssdp_message(self, message: str, addr: tuple):
        if "M-SEARCH" in message:
            print(f"[{self.device_id}] M-SEARCH from {addr[0]}")
            # TODO: Implement an HTTP 200 OK response
        elif "ssdp:alive" in message:
            print(f"[{self.device_id}] Device came online: {addr[0]}")
        elif "ssdp:byebye" in message:
            print(f"[{self.device_id}] Device went offline: {addr[0]}")
