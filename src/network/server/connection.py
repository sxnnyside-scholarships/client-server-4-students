"""
Module: connection.py
─────────────────────
Purpose: Manages the lifecycle and read loop for a single client connection.

Architectural Role:
Acts as the isolated execution context for a single connected socket. By running 
in its own daemon thread, it ensures that one slow or malicious client cannot 
block other students from communicating with the server.

Responsibilities:
- Perform the initial server-side `HELLO` protocol handshake.
- Run the infinite read-loop listening for incoming string packets.
- Execute "Teacher Mode" chaos configurations (latency, packet loss).
- Delegate packet processing to the `CommandDispatcher`.

Expected Collaborators:
- `src.network.server.engine` (spawns this handler).
- `src.network.server.dispatcher` (routes the parsed packets).
"""

import logging
import random
import socket
import threading
import time

from src.core.protocol import (
    CAPABILITIES,
    CMD_HELLO,
    CODE_BAD_REQ,
    CODE_GREETING,
    CODE_VERSION_ERR,
    PROTOCOL_VERSION,
    ProtocolHandler,
    STATUS_ERROR,
    STATUS_OK,
)
from src.network.security import SecurityContext

logger = logging.getLogger("server.connection")

class ClientConnectionHandler:
    """
    Stateful execution thread for a connected client.

    Why it exists:
    The server must handle dozens of simultaneous connections. This class encapsulates 
    all the local state (username, security context, protocol handler) required to 
    service a single client concurrently.

    Responsibilities:
    - Managing socket timeouts to drop idle peers.
    - Capturing unhandled exceptions to prevent thread crashes from killing the app.

    Non-Responsibilities (Anti-Goals):
    - It does NOT execute the actual commands (delegated to Dispatcher).
    - It does NOT accept new incoming connections (delegated to Engine).
    """

    def __init__(
        self,
        engine,
        conn: socket.socket,
        addr_str: str,
        proto: ProtocolHandler,
        dispatcher,
        shutdown_event: threading.Event
    ):
        self.engine = engine
        self.conn = conn
        self.addr_str = addr_str
        self.proto = proto
        self.dispatcher = dispatcher
        self.shutdown_event = shutdown_event

    def handle(self):
        """
        The main thread execution loop for this connection.

        Args:
            None.

        Returns:
            None.

        Side Effects:
            Blocks the current thread in an infinite `recv` loop.
            Writes `SecurityContext` data.
            Calls `engine.remove_client` upon termination.

        Failure Behavior:
            If the client sends invalid handshakes, it drops the connection.
            If an unexpected exception bubbles up, it logs the error and gracefully closes the socket.
        """
        sec_ctx = SecurityContext(self.addr_str)
        username: str | None = None
        
        try:
            # Protocol Handshake
            try:
                parts = self.proto.recv_message()
                if not parts or parts[0].upper() != CMD_HELLO:
                    self.proto.send_message(CODE_BAD_REQ, STATUS_ERROR, "Expected HELLO handshake")
                    return
                if len(parts) < 2 or parts[1] != PROTOCOL_VERSION:
                    self.proto.send_message(CODE_VERSION_ERR, STATUS_ERROR, f"Server requires {PROTOCOL_VERSION}")
                    return
                self.proto.send_message(CODE_GREETING, STATUS_OK, PROTOCOL_VERSION, CAPABILITIES)
            except (socket.timeout, ConnectionError):
                return

            while self.engine.is_running and not self.shutdown_event.is_set():
                try:
                    parts = self.proto.recv_message()
                except socket.timeout:
                    self.engine.on_log_message(f"Client idle timeout: {self.addr_str}")
                    break
                except ConnectionError:
                    break
                
                if not parts:
                    break
                    
                # [Teacher Mode] Chaos Interceptor
                if getattr(self.engine, 'simulate_latency', 0.0) > 0:
                    time.sleep(self.engine.simulate_latency)

                if getattr(self.engine, 'simulate_packet_loss', 0.0) > 0:
                    if random.random() < self.engine.simulate_packet_loss:
                        self.engine.on_log_message(f"[Teacher Mode] Dropped packet from {self.addr_str}")
                        continue

                cmd = parts[0].upper()
                
                # Dispatch the command
                should_disconnect, username = self.dispatcher.dispatch(
                    cmd, parts, self.proto, username, sec_ctx, self.engine
                )
                
                if should_disconnect:
                    break

        except Exception as exc:
            logger.error("Error handling %s: %s", self.addr_str, exc)
        finally:
            try:
                self.conn.close()
            except OSError:
                pass
            self.engine.remove_client(self.addr_str)
