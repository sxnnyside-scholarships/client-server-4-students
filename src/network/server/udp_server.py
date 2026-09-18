"""
Module: udp_server.py
─────────────────────
Purpose: Educational connectionless UDP echo and metrics server.

Architectural Role:
Acts as a companion service to the primary TCP server. Running on an adjacent
port (typically TCP port + 1), it allows students to experiment with UDP datagrams,
observe connectionless packet flow, and benchmark latency and packet loss against
connection-oriented TCP streams.

Responsibilities:
- Listen on a UDP datagram socket.
- Process educational UDP probe requests (`PROBE|<seq>|<timestamp>|<payload>`).
- Simulate latency and packet loss based on educator lab settings.
- Echo datagram acknowledgments (`ACK|<seq>|<timestamp>|<payload>`).
"""

import logging
import random
import socket
import threading
import time
from typing import Callable

logger = logging.getLogger("server.udp")


class UDPEducatorServer(threading.Thread):
    """
    Lightweight UDP datagram server for educational demonstrations.

    Listens for probe packets, applies simulated network degradation (latency and loss),
    and sends echo responses back to the sender address without establishing a connection.
    """

    def __init__(
        self,
        host: str,
        port: int,
        get_latency: Callable[[], float] | None = None,
        get_packet_loss: Callable[[], float] | None = None,
        on_log: Callable[[str], None] | None = None,
    ):
        super().__init__(daemon=True, name="UDPEducatorServer")
        self.host = host
        self.port = port
        self._get_latency = get_latency or (lambda: 0.0)
        self._get_packet_loss = get_packet_loss or (lambda: 0.0)
        self._on_log = on_log or (lambda msg: None)

        self._shutdown_event = threading.Event()
        self._sock: socket.socket | None = None
        self._packets_rx = 0
        self._packets_dropped = 0
        self._packets_echoed = 0

    @property
    def is_running(self) -> bool:
        return not self._shutdown_event.is_set() and self._sock is not None

    def stop(self):
        """Signals the UDP server thread to shut down and closes the socket."""
        self._shutdown_event.set()
        if self._sock:
            try:
                self._sock.close()
            except OSError:
                pass

    def run(self):
        """Main listening loop for UDP datagrams."""
        try:
            self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self._sock.bind((self.host, self.port))
            self._sock.settimeout(0.5)
            self._on_log(f"UDP Companion Server listening on {self.host}:{self.port}")
            logger.info("UDP Companion Server listening on %s:%d", self.host, self.port)
        except OSError as exc:
            self._on_log(f"UDP Server failed to bind to {self.host}:{self.port}: {exc}")
            logger.error("UDP Server bind error: %s", exc)
            return

        while not self._shutdown_event.is_set():
            try:
                data, addr = self._sock.recvfrom(65535)
            except socket.timeout:
                continue
            except OSError:
                break

            self._packets_rx += 1
            addr_str = f"{addr[0]}:{addr[1]}"

            # Parse datagram
            try:
                text = data.decode("utf-8", errors="replace")
            except Exception:
                text = ""

            parts = text.split("|", 3)
            cmd = parts[0].upper() if parts else ""

            # Check simulated packet loss
            loss_rate = self._get_packet_loss()
            if loss_rate > 0.0 and random.random() < loss_rate:
                self._packets_dropped += 1
                self._on_log(f"[UDP Lab] Dropped datagram from {addr_str} (simulated {loss_rate * 100:.0f}% loss)")
                continue

            # Check simulated latency
            latency = self._get_latency()
            if latency > 0.0:
                time.sleep(latency)

            # Echo response for PROBE commands
            if cmd == "PROBE":
                seq = parts[1] if len(parts) > 1 else "0"
                ts = parts[2] if len(parts) > 2 else "0"
                payload = parts[3] if len(parts) > 3 else ""

                reply = f"ACK|{seq}|{ts}|{payload}".encode("utf-8")
                try:
                    self._sock.sendto(reply, addr)
                    self._packets_echoed += 1
                except OSError as exc:
                    logger.debug("Failed to send UDP ACK to %s: %s", addr_str, exc)
            else:
                # Generic echo fallback
                reply = f"ECHO|{text}".encode("utf-8")
                try:
                    self._sock.sendto(reply, addr)
                    self._packets_echoed += 1
                except OSError:
                    pass

        if self._sock:
            try:
                self._sock.close()
            except OSError:
                pass
            self._sock = None
        self._on_log("UDP Companion Server stopped.")
