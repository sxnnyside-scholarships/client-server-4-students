"""
Module: engine.py
─────────────────
Purpose: Manages the TCP socket accept loop and client thread lifecycle.

Architectural Role:
This is the foundational network listener for the server. It manages the server's 
main `bind` and `accept` loop, spawning isolated `ClientConnectionHandler` threads 
for every incoming connection.

Responsibilities:
- Bind a TCP socket to a host/port and listen for inbound connections.
- Enforce the `max_connections` limit and IP ban lists before spawning threads.
- Maintain a thread-safe registry of all active clients.
- Provide forced-disconnection capabilities (Lab View Chaos).

Expected Collaborators:
- `src.network.server_backend` (consumes this engine's signals).
- `src.network.server.connection` (instantiated per client).
"""

import logging
import socket
import threading
from typing import Callable

from src.core.protocol import ProtocolHandler
from src.network.security import (
    SecurityEvent,
    SecurityEventCategory,
    SecuritySeverity,
)
from src.network.server.connection import ClientConnectionHandler

logger = logging.getLogger("server.engine")

class ServerNetworkEngine:
    """
    Manages the primary TCP socket accept loop and the lifecycle of client threads.

    Why it exists:
    A server must be able to accept new connections while simultaneously serving 
    existing ones. This engine separates the "accepting" logic from the "handling" logic, 
    ensuring the server never blocks while waiting for a new client.

    Responsibilities:
    - Managing the `socket.accept()` infinite loop.
    - Synchronizing the shutdown sequence across all connected clients.
    - Emitting Qt-compatible callbacks for GUI updates.

    Non-Responsibilities (Anti-Goals):
    - It does NOT route protocol commands (delegated to Dispatcher).
    - It does NOT process incoming bytes (delegated to ConnectionHandler).
    """

    def __init__(self, max_connections: int, dispatcher):
        self.max_connections = max_connections
        self.dispatcher = dispatcher
        self._socket: socket.socket | None = None
        self._running = False
        self._clients: dict[str, tuple[threading.Thread, socket.socket, ProtocolHandler]] = {}
        self._lock = threading.Lock()
        self._shutdown_event = threading.Event()
        
        # Callbacks to notify the Facade/UI
        self.on_log_message: Callable[[str], None] = lambda x: None
        self.on_client_connected: Callable[[str], None] = lambda x: None
        self.on_client_disconnected: Callable[[str], None] = lambda x: None
        self.on_security_alert: Callable[[dict], None] = lambda x: None
        self.on_server_started: Callable[[], None] = lambda: None
        self.on_server_stopped: Callable[[], None] = lambda: None
        self.on_socket_state_changed: Callable[[str, str], None] = lambda addr, state: None
        
        # Testing/chaos properties
        self.simulate_latency = 0.0
        self.simulate_packet_loss = 0.0

    @property
    def is_running(self) -> bool:
        """
        Returns the current running state of the listening socket.

        Args:
            None.

        Returns:
            True if the server is accepting connections.

        Side Effects:
            None.

        Failure Behavior:
            None.
        """
        return self._running

    def get_statistics(self) -> dict:
        """
        Aggregates transmission statistics across all active client connections.

        Args:
            None.

        Returns:
            A dictionary containing 'tx', 'rx', and 'connections' counts.

        Side Effects:
            Acquires the internal thread lock.

        Failure Behavior:
            Returns zeroes if no clients are connected.
        """
        tx, rx, packets = 0, 0, 0
        with self._lock:
            for _, _, proto in self._clients.values():
                if proto:
                    tx += proto.bytes_tx
                    rx += proto.bytes_rx
                    packets += proto.messages_tx + proto.messages_rx
        return {"tx": tx, "rx": rx, "packets": packets, "connections": len(self._clients)}

    def start(self, host: str, port: int):
        """
        Binds the listening socket and spawns the accept loop.

        Args:
            host: The IP address to bind to.
            port: The TCP port to listen on.

        Returns:
            None.

        Side Effects:
            Spawns a daemon thread for `_accept_loop`.
            Emits `on_server_started` callbacks.

        Failure Behavior:
            Fails gracefully (logs error) if the port is already in use.
        """
        if self._running:
            return
        try:
            self._shutdown_event.clear()
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self._socket.settimeout(1.0)
            self._socket.bind((host, port))
            self._socket.listen(5)
            self._running = True

            threading.Thread(target=self._accept_loop, daemon=True).start()

            msg = f"Server started on {host}:{port}"
            self.on_log_message(msg)
            logger.info(msg)
            self.on_server_started()
        except OSError as exc:
            self.on_log_message(f"Failed to start server: {exc}")
            logger.error("Failed to start server: %s", exc)
            self._running = False

    def stop(self):
        """
        Halts the accept loop and disconnects all active clients.

        Args:
            None.

        Returns:
            None.

        Side Effects:
            Sets the shutdown event.
            Closes all sockets iteratively.
            Emits `on_server_stopped`.

        Failure Behavior:
            Ignores sockets that are already closed.
        """
        if not self._running:
            return
        self._running = False
        self._shutdown_event.set()

        if self._socket:
            try:
                self._socket.close()
            except OSError:
                pass

        with self._lock:
            for addr, (t, conn, proto) in self._clients.items():
                try:
                    conn.close()
                except OSError:
                    pass
            self._clients.clear()

        self.on_log_message("Server stopped")
        logger.info("Server stopped")
        self.on_server_stopped()

    def force_disconnect_client(self, addr_str: str):
        """
        Manually severs a connection from the server-side UI.

        Args:
            addr_str: The IP:Port string identifier.

        Returns:
            None.

        Side Effects:
            Closes the targeted socket. The connection handler thread will notice 
            the closure and exit naturally.

        Failure Behavior:
            Silently ignores the request if the client is already gone.
        """
        with self._lock:
            if addr_str in self._clients:
                try:
                    self._clients[addr_str][1].close()
                except OSError:
                    pass
                self.on_log_message(f"[Teacher Mode] Forced disconnect: {addr_str}")

    def _accept_loop(self):
        while self._running:
            try:
                conn, addr = self._socket.accept()
                addr_str = f"{addr[0]}:{addr[1]}"
                ip = addr[0]

                if self.dispatcher.ban_registry.is_banned(ip):
                    logger.warning("Rejected connection from banned IP %s", ip)
                    try:
                        conn.close()
                    except OSError:
                        pass
                    continue

                with self._lock:
                    if len(self._clients) >= self.max_connections:
                        evt = SecurityEvent(
                            category=SecurityEventCategory.CONNECTION_REJECTED.value,
                            severity=SecuritySeverity.WARNING.value,
                            message="Maximum connections exceeded",
                            client_address=addr_str
                        )
                        self.on_security_alert(evt.to_dict())
                        logger.warning("Rejected connection from %s (max_connections=%d)", addr_str, self.max_connections)
                        try:
                            conn.sendall(b"-ERR Maximum connections exceeded\n")
                            conn.close()
                        except OSError:
                            pass
                        continue

                conn.settimeout(30.0)

                proto = ProtocolHandler(conn)
                # Tagged so downstream handlers (e.g. TransferHandler) can
                # report per-connection socket state without needing the
                # engine's full client registry passed around everywhere.
                proto.client_addr = addr_str
                handler = ClientConnectionHandler(
                    engine=self,
                    conn=conn,
                    addr_str=addr_str,
                    proto=proto,
                    dispatcher=self.dispatcher,
                    shutdown_event=self._shutdown_event
                )
                
                t = threading.Thread(
                    target=handler.handle,
                    daemon=True,
                )
                with self._lock:
                    self._clients[addr_str] = (t, conn, proto)
                t.start()

                self.on_log_message(f"Client connected: {addr_str}")
                logger.info("Client connected: %s", addr_str)
                self.on_client_connected(addr_str)

            except socket.timeout:
                continue
            except OSError:
                break

    def remove_client(self, addr_str: str):
        """
        Cleans up a disconnected client from the internal registry.

        Args:
            addr_str: The IP:Port string identifier.

        Returns:
            None.

        Side Effects:
            Mutates the `_clients` dictionary.
            Emits `on_client_disconnected`.

        Failure Behavior:
            None.
        """
        with self._lock:
            self._clients.pop(addr_str, None)
        self.on_log_message(f"Client disconnected: {addr_str}")
        logger.info("Client disconnected: %s", addr_str)
        self.on_client_disconnected(addr_str)
