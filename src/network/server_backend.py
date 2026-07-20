"""
Module: server_backend.py
─────────────────────────
Purpose: Networking engine for the server side.

Architectural Role:
Acts as a Facade connecting the core server networking engines (`engine.py`, `dispatcher.py`) 
to the PyQt6 event loop. It translates pure Python callbacks into thread-safe Qt signals 
that the UI can observe.

Responsibilities:
- Register all command handlers (`AuthCommandHandler`, `FileOpsHandler`, `TransferHandler`) 
  with the `CommandDispatcher`.
- Instantiate the `ServerNetworkEngine`.
- Wire engine callback hooks to `pyqtSignal` emissions.
- Expose Lab View / Chaos mode configurations (latency, packet loss) to the UI.

Expected Collaborators:
- `src.ui.server_window` (consumes this class).
- `src.network.server.engine`, `src.network.server.dispatcher`, `src.network.server.handlers`
"""

from PyQt6.QtCore import QObject, pyqtSignal

from src.core.protocol import (
    CMD_AUTH,
    CMD_DELETE,
    CMD_DOWNLOAD,
    CMD_LIST,
    CMD_MKDIR,
    CMD_MOVE,
    CMD_RENAME,
    CMD_UPLOAD,
)
from src.network.server.dispatcher import CommandDispatcher
from src.network.server.engine import ServerNetworkEngine
from src.network.server.handlers.auth import AuthCommandHandler
from src.network.server.handlers.file_ops import FileOpsHandler
from src.network.server.handlers.transfer import TransferHandler
from src.storage.auth import AuthManager
from src.storage.file_manager import FileManager


class ServerBackend(QObject):
    """
    Threaded TCP server with Qt signal integration.

    Why it exists:
    Qt GUI widgets cannot be updated from background network threads without crashing. 
    This class bridges the gap by converting network thread events into Qt Signals, 
    which safely cross the thread boundary into the main UI thread.

    Responsibilities:
    - Managing the lifecycle of `ServerNetworkEngine`.
    - Assembling the handler pipelines and injecting `AuthManager` and `FileManager` dependencies.

    Non-Responsibilities (Anti-Goals):
    - It does NOT implement protocol framing (delegated to `ProtocolHandler`).
    - It does NOT perform raw socket I/O (delegated to `engine.py`).
    """

    # Signals → UI
    log_message = pyqtSignal(str)
    client_connected = pyqtSignal(str)
    client_disconnected = pyqtSignal(str)
    security_alert = pyqtSignal(dict)
    server_started = pyqtSignal()
    server_stopped = pyqtSignal()
    socket_state_changed = pyqtSignal(str, str)

    def __init__(self, auth: AuthManager, files: FileManager, config=None):
        super().__init__()
        self.auth = auth
        self.files = files
        max_connections = 5
        if config is not None:
            max_connections = config.get_nested("server", "max_connections", default=5)
        
        # Build the command dispatcher
        self.dispatcher = CommandDispatcher()
        
        # Handlers
        auth_handler = AuthCommandHandler(auth)
        file_handler = FileOpsHandler(files)
        transfer_handler = TransferHandler(files)
        
        # Register routes
        self.dispatcher.register(CMD_AUTH, auth_handler.handle, requires_auth=False)
        self.dispatcher.register(CMD_LIST, file_handler.cmd_list)
        self.dispatcher.register(CMD_MKDIR, file_handler.cmd_mkdir)
        self.dispatcher.register(CMD_DELETE, file_handler.cmd_delete)
        self.dispatcher.register(CMD_RENAME, file_handler.cmd_rename)
        self.dispatcher.register(CMD_MOVE, file_handler.cmd_move)
        self.dispatcher.register(CMD_UPLOAD, transfer_handler.cmd_upload)
        self.dispatcher.register(CMD_DOWNLOAD, transfer_handler.cmd_download)

        # Build the networking engine
        self.engine = ServerNetworkEngine(max_connections=max_connections, dispatcher=self.dispatcher)
        
        # Wire engine callbacks to Qt Signals
        self.engine.on_log_message = self.log_message.emit
        self.engine.on_client_connected = self.client_connected.emit
        self.engine.on_client_disconnected = self.client_disconnected.emit
        self.engine.on_security_alert = self.security_alert.emit
        self.engine.on_server_started = self.server_started.emit
        self.engine.on_server_stopped = self.server_stopped.emit
        self.engine.on_socket_state_changed = self.socket_state_changed.emit

    @property
    def is_running(self) -> bool:
        """
        Returns the current running state of the server.

        Args:
            None.

        Returns:
            True if the server is actively listening for connections.

        Side Effects:
            None.

        Failure Behavior:
            None.
        """
        return self.engine.is_running

    def get_statistics(self) -> dict:
        """
        Retrieves real-time byte transmission statistics.

        Args:
            None.

        Returns:
            A dictionary containing 'tx' (bytes transmitted) and 'rx' (bytes received).

        Side Effects:
            None.

        Failure Behavior:
            None.
        """
        return self.engine.get_statistics()

    # ── Teacher Mode Chaos Settings ──
    @property
    def max_connections(self):
        return self.engine.max_connections

    @max_connections.setter
    def max_connections(self, value):
        self.engine.max_connections = value

    @property
    def simulate_latency(self):
        return self.engine.simulate_latency

    @simulate_latency.setter
    def simulate_latency(self, value):
        self.engine.simulate_latency = value

    @property
    def simulate_packet_loss(self):
        return self.engine.simulate_packet_loss

    @simulate_packet_loss.setter
    def simulate_packet_loss(self, value):
        self.engine.simulate_packet_loss = value

    def start(self, host: str, port: int):
        """
        Starts the TCP listening socket on a background thread.

        Args:
            host: The IP address to bind to.
            port: The TCP port to listen on.

        Returns:
            None. (Asynchronous operation).

        Side Effects:
            Spawns the main listener thread.
            Emits `server_started`.

        Failure Behavior:
            Fails if the port is already in use.
        """
        self.engine.start(host, port)

    def stop(self):
        """
        Stops the TCP server and disconnects all clients.

        Args:
            None.

        Returns:
            None.

        Side Effects:
            Kills all background worker threads.
            Emits `server_stopped`.

        Failure Behavior:
            Safely ignores repeated calls if already stopped.
        """
        self.engine.stop()

    def force_disconnect_client(self, addr_str: str):
        """
        Disconnects a specific client aggressively.

        Args:
            addr_str: The IP:Port string identifier of the client.

        Returns:
            None.

        Side Effects:
            Closes the target's TCP socket.

        Failure Behavior:
            Silently ignores the request if the client is already disconnected.
        """
        self.engine.force_disconnect_client(addr_str)
