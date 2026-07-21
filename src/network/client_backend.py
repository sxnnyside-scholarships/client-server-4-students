"""
Module: client_backend.py
─────────────────────────
Purpose: Networking engine for the client side.

Architectural Role:
Acts as a Facade connecting the core networking engines (`engine.py`, `operations.py`,
`transfers.py`) to the PyQt6 event loop. It translates pure Python callbacks into
thread-safe Qt signals that the UI can observe.

Responsibilities:
- Instantiate the core `ClientConnectionEngine`.
- Wire engine callback hooks to `pyqtSignal` emissions.
- Provide a unified API surface for the `ClientWindow` to trigger network actions.

Expected Collaborators:
- `src.ui.client_window` (consumes this class).
- `src.network.client.engine`, `src.network.client.operations`, `src.network.client.transfers`
"""

from PyQt6.QtCore import QObject, pyqtSignal

from src.network.client.engine import ClientConnectionEngine
from src.network.client.operations import ClientOperations
from src.network.client.transfers import ClientTransferEngine


class ClientBackend(QObject):
    """
    Threaded TCP client with Qt signal integration.

    Why it exists:
    Qt GUI widgets cannot be updated from background network threads without crashing.
    This class bridges the gap by converting network thread events into Qt Signals,
    which safely cross the thread boundary into the main UI thread.

    Responsibilities:
    - Managing the lifecycle of `ClientConnectionEngine`.
    - Exposing safe asynchronous methods for file operations and transfers.

    Non-Responsibilities (Anti-Goals):
    - It does NOT implement protocol framing (delegated to `ProtocolHandler`).
    - It does NOT perform raw socket I/O (delegated to `engine.py`).
    """

    # Signals → UI
    connected = pyqtSignal()
    disconnected = pyqtSignal()
    auth_success = pyqtSignal()
    auth_failed = pyqtSignal(str)
    file_list_received = pyqtSignal(list)
    upload_complete = pyqtSignal(str)
    download_complete = pyqtSignal(str)
    directory_created = pyqtSignal()
    error_occurred = pyqtSignal(str, str)
    connection_recovering = pyqtSignal(int, int)
    status_message = pyqtSignal(str)
    transfer_progress = pyqtSignal(int)
    transfer_progress_detailed = pyqtSignal(dict)
    transfer_state_changed = pyqtSignal(str, str)
    capabilities_discovered = pyqtSignal(list)
    action_completed = pyqtSignal(str)
    rtt_measured = pyqtSignal(float)

    # Educational Signals
    packet_tx = pyqtSignal(str)
    packet_rx = pyqtSignal(str)

    def __init__(self, config=None):
        super().__init__()

        # Build core engines
        self.engine = ClientConnectionEngine()

        if config is not None:
            self.engine.enable_tls = config.get_nested("client", "enable_tls", default=False)

        self.operations = ClientOperations(self.engine)
        self.transfers = ClientTransferEngine(self.engine)

        # Wire Engine -> PyQt Signals
        self.engine.on_connected = self.connected.emit
        self.engine.on_disconnected = self.disconnected.emit
        self.engine.on_auth_success = self.auth_success.emit
        self.engine.on_auth_failed = self.auth_failed.emit
        self.engine.on_error_occurred = self.error_occurred.emit
        self.engine.on_connection_recovering = self.connection_recovering.emit
        self.engine.on_status_message = self.status_message.emit
        self.engine.on_capabilities_discovered = self.capabilities_discovered.emit
        self.engine.on_packet_tx = self.packet_tx.emit
        self.engine.on_packet_rx = self.packet_rx.emit

        # Wire Operations -> PyQt Signals
        self.operations.on_file_list_received = self.file_list_received.emit
        self.operations.on_directory_created = self.directory_created.emit
        self.operations.on_action_completed = self.action_completed.emit
        self.operations.on_rtt_measured = self.rtt_measured.emit

        # Wire Transfers -> PyQt Signals
        self.transfers.on_transfer_state_changed = self.transfer_state_changed.emit
        self.transfers.on_error_occurred = self.error_occurred.emit
        self.transfers.on_transfer_progress = self.transfer_progress.emit
        self.transfers.on_transfer_progress_detailed = self.transfer_progress_detailed.emit
        self.transfers.on_upload_complete = self.upload_complete.emit
        self.transfers.on_download_complete = self.download_complete.emit

    @property
    def is_connected(self) -> bool:
        """
        Returns the current connection state of the client engine.

        Args:
            None.

        Returns:
            True if the underlying socket is connected and authenticated.

        Side Effects:
            None.

        Failure Behavior:
            None.
        """
        return self.engine.is_connected

    def get_statistics(self) -> dict:
        """
        Retrieves real-time byte transmission statistics from the underlying protocol handler.

        Args:
            None.

        Returns:
            A dictionary containing 'tx' (bytes transmitted) and 'rx' (bytes received).

        Side Effects:
            None.

        Failure Behavior:
            Returns `{"tx": 0, "rx": 0}` if the connection has not been established yet.
        """
        if self.engine.proto:
            return {"tx": self.engine.proto.bytes_tx, "rx": self.engine.proto.bytes_rx}
        return {"tx": 0, "rx": 0}

    # ── Connection Management ──

    def connect_to_server(self, host: str, port: int, user: str, pwd: str):
        """
        Initiates a background connection and authentication sequence.

        Args:
            host: The server IP or hostname.
            port: The TCP port (usually 2121).
            user: The account username.
            pwd: The plaintext password.

        Returns:
            None. (Asynchronous operation).

        Side Effects:
            Spawns background network threads.
            Emits `connected`, `auth_success`, or `auth_failed` signals upon completion.

        Failure Behavior:
            Emits `error_occurred` if the socket cannot be opened.
        """
        self.engine.connect(host, port, user, pwd)

    def disconnect(self):
        """
        Gracefully terminates the network connection.

        Args:
            None.

        Returns:
            None.

        Side Effects:
            Closes the underlying socket and terminates background threads.
            Emits the `disconnected` signal.

        Failure Behavior:
            Safely ignores repeated calls if already disconnected.
        """
        self.engine.disconnect()

    # ── Operations ──

    def list_files(self, path: str = ""):
        """
        Requests a directory listing from the remote server.

        Args:
            path: The relative remote path (empty string for root).

        Returns:
            None. (Asynchronous operation).

        Side Effects:
            Emits `file_list_received` when the server responds.

        Failure Behavior:
            Emits `error_occurred` if the connection drops.
        """
        self.operations.list_files(path)

    def create_directory(self, dirname: str):
        """
        Requests the server to create a new folder.

        Args:
            dirname: The path/name of the new directory.

        Returns:
            None. (Asynchronous operation).

        Side Effects:
            Emits `directory_created` on success.

        Failure Behavior:
            Emits `error_occurred` if the folder already exists or permission is denied.
        """
        self.operations.create_directory(dirname)

    def delete_file(self, filename: str):
        """
        Requests the server to delete a remote file or directory.

        Args:
            filename: The relative path to delete.

        Returns:
            None.

        Side Effects:
            Emits `action_completed` on success.

        Failure Behavior:
            Emits `error_occurred` on failure.
        """
        from src.core.protocol import CMD_DELETE

        self.operations.do_action(CMD_DELETE, filename)

    def rename_file(self, old_name: str, new_name: str):
        """
        Requests the server to rename a file or directory.

        Args:
            old_name: The current path.
            new_name: The desired new path.

        Returns:
            None.

        Side Effects:
            Emits `action_completed` on success.

        Failure Behavior:
            Emits `error_occurred` on failure.
        """
        from src.core.protocol import CMD_RENAME

        self.operations.do_action(CMD_RENAME, old_name, new_name)

    def move_file(self, filename: str, dest_dir: str):
        """
        Requests the server to move a file into a different directory.

        Args:
            filename: The path of the file to move.
            dest_dir: The target destination directory.

        Returns:
            None.

        Side Effects:
            Emits `action_completed` on success.

        Failure Behavior:
            Emits `error_occurred` on failure.
        """
        from src.core.protocol import CMD_MOVE

        self.operations.do_action(CMD_MOVE, filename, dest_dir)

    def measure_rtt(self):
        """
        Requests a round-trip latency measurement from the server.

        Args:
            None.

        Returns:
            None. (Asynchronous operation).

        Side Effects:
            Emits `rtt_measured` with the elapsed milliseconds once the
            server's PONG response arrives.

        Failure Behavior:
            Silently does nothing if the probe fails (no error surfaced,
            since a missed latency sample isn't user-actionable).
        """
        self.operations.ping()

    def send_raw(self, raw_cmd: str):
        """
        Injects a raw, unvalidated protocol string directly into the socket stream.

        Args:
            raw_cmd: The string command (e.g., "HELLO|CS4S").

        Returns:
            None.

        Side Effects:
            Writes to the underlying TCP socket.

        Failure Behavior:
            May corrupt the protocol state machine if used improperly.
        """
        self.operations.send_raw(raw_cmd)

    # ── Transfers ──

    def upload_file(self, local_path: str, remote_name: str):
        """
        Initiates a binary file upload to the server.

        Args:
            local_path: Absolute path to the file on the user's local disk.
            remote_name: The destination relative path on the server.

        Returns:
            None. (Asynchronous operation).

        Side Effects:
            Reads aggressively from the local disk.
            Emits `transfer_progress` iteratively. Emits `upload_complete` upon finish.

        Failure Behavior:
            Emits `error_occurred` if the local file is unreadable or the socket drops.
        """
        self.transfers.upload_file(local_path, remote_name)

    def download_file(self, remote_name: str, local_path: str):
        """
        Initiates a binary file download from the server.

        Args:
            remote_name: The relative path of the file on the server.
            local_path: Absolute path where the file should be saved on the local disk.

        Returns:
            None. (Asynchronous operation).

        Side Effects:
            Writes aggressively to the local disk.
            Emits `transfer_progress` iteratively. Emits `download_complete` upon finish.

        Failure Behavior:
            Emits `error_occurred` if the local disk is un-writable or the socket drops.
        """
        self.transfers.download_file(remote_name, local_path)

    def cancel_transfer(self, remote_name: str):
        """
        Aborts an ongoing file transfer.

        Args:
            remote_name: The identifier of the active transfer.

        Returns:
            None.

        Side Effects:
            Closes the data stream. Leaves a partial/corrupted file on the receiving end.

        Failure Behavior:
            None.
        """
        self.transfers.cancel_transfer(remote_name)
