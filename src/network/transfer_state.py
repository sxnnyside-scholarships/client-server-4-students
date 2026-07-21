"""
Module: transfer_state.py
─────────────────────────
Purpose: Defines the lifecycle states of a network file transfer.

Architectural Role:
Acts as a pure data structure (Enum). It is the shared vocabulary used by the
`ClientTransferEngine`, `ServerTransferEngine`, and the GUI components to track
the lifecycle of an active file operation.

Responsibilities:
- Define the `TransferState` enumeration.

Expected Collaborators:
- `src.network.client.transfers.ClientTransferEngine`
- `src.network.server.handlers.transfer.TransferHandler`
"""

from enum import Enum


class TransferState(Enum):
    """
    Represents the operational phases of an upload or download stream.

    Why it exists:
    Because large files take time to transfer, the GUI needs a way to show users
    what is happening. Exposing state explicitly allows the UI to render progress
    bars accurately without polling the network thread.

    Responsibilities:
    - Mapping internal threading states to semantic UI states.

    Non-Responsibilities (Anti-Goals):
    - It does NOT dictate the sequence of the protocol (that's the `ProtocolHandler`'s job).
    """

    QUEUED = "Queued"
    """Transfer requested, waiting for worker thread allocation."""

    STARTING = "Starting"
    """Worker assigned, protocol header negotiated."""

    RUNNING = "Running"
    """Acknowledged by peer, actively streaming chunks to/from disk."""

    CANCELLING = "Cancelling"
    """Cancellation event intercepted; draining or padding bytes to preserve socket."""

    CANCELLED = "Cancelled"
    """Stream manually aborted and socket safely recovered."""

    COMPLETED = "Completed"
    """Entire payload successfully streamed and verified."""

    FAILED = "Failed"
    """Aborted due to network error, timeout, or disk constraint."""
