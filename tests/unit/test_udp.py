import time
from src.network.client.udp_client import UDPProbeClient
from src.network.server.udp_server import UDPEducatorServer


def test_udp_server_and_probe_client_clean_channel():
    logs = []
    # Bind to an ephemeral port (0) or dedicated high port
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
    client = UDPProbeClient()
    client.cancel()
    results = client.transmit_burst(
        host="127.0.0.1",
        port=34569,
        count=10,
    )
    # Since cancelled immediately, sent count should be 0 or 1
    assert results["total_sent"] <= 1
