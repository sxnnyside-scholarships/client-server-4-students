"""
Module: test_udp.py
───────────────────
Purpose: Unit validation of UDP probe burst transmissions, simulated channel packet loss, and early client cancellation.

Architectural Role:
Acts as the test suite for `UDPEducatorServer` and `UDPProbeClient`, verifying that datagram-based packet bursts
operate correctly over local UDP sockets and accurately reflect loss rates when simulated drop impairments are applied.

Responsibilities:
- Verify lossless datagram exchange and metrics calculation (RTT, throughput) on clean channels.
- Validate server packet loss simulation (100% loss test ensuring client correctly flags unreceived packets).
- Validate cancellation token mechanics during active burst transmissions.
- Ensure proper thread termination and socket cleanup on server teardown.

Dependencies:
- `time`
- `src.network.client.udp_client.UDPProbeClient`
- `src.network.server.udp_server.UDPEducatorServer`

Expected Collaborators:
- `UDPProbeClient`: Sends timed UDP probes with sequence numbers.
- `UDPEducatorServer`: Echoes probes or simulates packet drops according to educator loss parameters.

Educational Note: Datagram Channel Testing
Unlike TCP stream sockets which guarantee delivery through acknowledgments and sliding window retransmissions,
UDP sockets discard packets silently when drops occur. Testing client burst timeouts verifies that students
can measure packet loss rates accurately without hanging client threads.
"""

import time
from src.network.client.udp_client import UDPProbeClient
from src.network.server.udp_server import UDPEducatorServer


def test_udp_server_and_probe_client_clean_channel():
    """
    Validates end-to-end UDP probe burst transmission across an ideal channel with 0% simulated packet loss.

    Args:
        None.

    Returns:
        None.

    Side Effects:
        Binds a UDP socket server and transmits 10 UDP probe packets from client.

    Failure Behavior:
        Fails if packet loss is non-zero or if average round-trip time is negative.
    """
    logs = []
    port = 34567
    server = UDPEducatorServer(
        host="127.0.0.1",
        port=port,
        get_latency=lambda: 0.0,
        get_packet_loss=lambda: 0.0,
        on_log=logs.append,
    )
    server.start()
    time.sleep(0.1)
    assert server.is_running

    try:
        client = UDPProbeClient()
        results = client.transmit_burst(
            host="127.0.0.1",
            port=port,
            count=10,
            packet_size=128,
            delay_ms=2.0,
        )

        assert results["total_sent"] == 10
        assert results["total_received"] == 10
        assert results["packets_lost"] == 0
        assert results["loss_rate_pct"] == 0.0
        assert results["avg_rtt_ms"] >= 0.0
        assert results["throughput_kbps"] > 0.0
        assert len(results["packets"]) == 10
        for pkt in results["packets"]:
            assert pkt["received"] is True
            assert pkt["rtt_ms"] >= 0.0
    finally:
        server.stop()
        server.join(timeout=1.0)
        assert not server.is_running


def test_udp_server_simulated_packet_loss():
    """
    Validates that UDPProbeClient correctly detects 100% packet loss when the server simulates channel drops.

    Args:
        None.

    Returns:
        None.

    Side Effects:
        Runs UDP server with packet_loss=1.0 and attempts a 5-packet burst.

    Failure Behavior:
        Fails if any packets are marked as received or if loss rate percentage is less than 100%.
    """
    port = 34568
    # 100% loss simulation
    server = UDPEducatorServer(
        host="127.0.0.1",
        port=port,
        get_latency=lambda: 0.0,
        get_packet_loss=lambda: 1.0,
    )
    server.start()
    time.sleep(0.1)

    try:
        client = UDPProbeClient()
        results = client.transmit_burst(
            host="127.0.0.1",
            port=port,
            count=5,
            packet_size=64,
            delay_ms=1.0,
        )

        assert results["total_sent"] == 5
        assert results["total_received"] == 0
        assert results["packets_lost"] == 5
        assert results["loss_rate_pct"] == 100.0
        for pkt in results["packets"]:
            assert pkt["received"] is False
    finally:
        server.stop()
        server.join(timeout=1.0)


def test_udp_client_cancellation():
    """
    Validates that invoking cancel() on UDPProbeClient halts ongoing burst loops immediately.

    Args:
        None.

    Returns:
        None.

    Side Effects:
        Cancels probe client prior to/during transmission.

    Failure Behavior:
        Fails if client proceeds to send the full complement of packets despite cancellation.
    """
    client = UDPProbeClient()
    client.cancel()
    results = client.transmit_burst(
        host="127.0.0.1",
        port=34569,
        count=10,
    )
    # Since cancelled immediately, sent count should be 0 or 1
    assert results["total_sent"] <= 1
