"""
Module: udp_client.py
─────────────────────
Purpose: Educational UDP probe client for measuring connectionless network performance.

Architectural Role:
Provides packet burst generation, latency calculation, and packet loss tracking
over connectionless UDP datagram sockets. Consumed by the UDP Lab View widget.

Responsibilities:
- Transmit datagram bursts of configurable packet counts and payload sizes.
- Track Round-Trip Time (RTT) per datagram.
- Compute packet loss rate, average latency, and effective throughput.
- Deliver structured results for UI rendering.
"""

import socket
import threading
import time
from typing import Callable


class UDPProbeClient:
    """
    Client for transmitting datagram bursts to measure UDP channel characteristics.
    """

    def __init__(self):
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def transmit_burst(
        self,
        host: str,
        port: int,
        count: int = 20,
        packet_size: int = 128,
        delay_ms: float = 10.0,
        progress_cb: Callable[[int, int], None] | None = None,
    ) -> dict:
        """
        Transmits a burst of UDP datagrams, waits for echo acknowledgments,
        and computes performance statistics.

        Args:
            host: Destination IP or hostname.
            port: Destination UDP port.
            count: Number of datagrams to transmit in the burst.
            packet_size: Total payload size per packet in bytes.
            delay_ms: Inter-packet spacing in milliseconds.
            progress_cb: Optional callback(current, total) called during transmission.

        Returns:
            Dictionary containing:
            - total_sent: int
            - total_received: int
            - packets_lost: int
            - loss_rate_pct: float
            - avg_rtt_ms: float
            - min_rtt_ms: float
            - packets: list of dicts {seq, received, rtt_ms}
        """
        if self._cancelled:
            return {
                "total_sent": 0,
                "total_received": 0,
                "packets_lost": 0,
                "loss_rate_pct": 0.0,
                "avg_rtt_ms": 0.0,
                "min_rtt_ms": 0.0,
                "max_rtt_ms": 0.0,
                "throughput_kbps": 0.0,
                "packets": [],
            }

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(0.1)

        sent_timestamps: dict[int, float] = {}
        received_packets: dict[int, float] = {}  # seq -> rtt_ms
        packet_results: list[dict] = []

        start_time = time.perf_counter()

        try:
            # Transmit burst
            for seq in range(count):
                if self._cancelled:
                    break

                # Prepare probe payload
                # Format: PROBE|<seq>|<timestamp>|<padding>
                now = time.perf_counter()
                sent_timestamps[seq] = now
                header = f"PROBE|{seq}|{now:.6f}|"
                pad_len = max(0, packet_size - len(header.encode("utf-8")))
                padding = "X" * pad_len
                payload = (header + padding).encode("utf-8")

                try:
                    sock.sendto(payload, (host, port))
                except OSError:
                    pass

                if progress_cb:
                    progress_cb(seq + 1, count)

                # Try to opportunistically read any ACKs that arrived
                while True:
                    try:
                        data, _ = sock.recvfrom(65535)
                        text = data.decode("utf-8", errors="replace")
                        parts = text.split("|", 3)
                        if parts and parts[0].upper() == "ACK" and len(parts) > 1:
                            rx_seq = int(parts[1])
                            if rx_seq in sent_timestamps and rx_seq not in received_packets:
                                rtt = (time.perf_counter() - sent_timestamps[rx_seq]) * 1000.0
                                received_packets[rx_seq] = rtt
                    except (socket.timeout, ValueError, OSError):
                        break

                if delay_ms > 0:
                    time.sleep(delay_ms / 1000.0)

            # Drain phase: wait for trailing ACKs up to 1.0 second
            sock.settimeout(0.3)
            drain_start = time.perf_counter()
            while (time.perf_counter() - drain_start) < 1.0:
                if len(received_packets) >= count or self._cancelled:
                    break
                try:
                    data, _ = sock.recvfrom(65535)
                    text = data.decode("utf-8", errors="replace")
                    parts = text.split("|", 3)
                    if parts and parts[0].upper() == "ACK" and len(parts) > 1:
                        rx_seq = int(parts[1])
                        if rx_seq in sent_timestamps and rx_seq not in received_packets:
                            rtt = (time.perf_counter() - sent_timestamps[rx_seq]) * 1000.0
                            received_packets[rx_seq] = rtt
                except (socket.timeout, ValueError, OSError):
                    pass

        finally:
            sock.close()

        total_duration = max(0.001, time.perf_counter() - start_time)
        total_sent = len(sent_timestamps)
        total_received = len(received_packets)
        packets_lost = total_sent - total_received
        loss_rate_pct = (packets_lost / total_sent * 100.0) if total_sent > 0 else 0.0

        rtts = list(received_packets.values())
        avg_rtt = (sum(rtts) / len(rtts)) if rtts else 0.0
        min_rtt = min(rtts) if rtts else 0.0
        max_rtt = max(rtts) if rtts else 0.0

        total_bytes_rx = total_received * packet_size
        throughput_kbps = (total_bytes_rx / 1024.0) / total_duration

        for seq in range(total_sent):
            is_rx = seq in received_packets
            packet_results.append(
                {
                    "seq": seq,
                    "received": is_rx,
                    "rtt_ms": round(received_packets[seq], 2) if is_rx else 0.0,
                }
            )

        return {
            "total_sent": total_sent,
            "total_received": total_received,
            "packets_lost": packets_lost,
            "loss_rate_pct": round(loss_rate_pct, 1),
            "avg_rtt_ms": round(avg_rtt, 2),
            "min_rtt_ms": round(min_rtt, 2),
            "max_rtt_ms": round(max_rtt, 2),
            "throughput_kbps": round(throughput_kbps, 2),
            "packets": packet_results,
        }

    def transmit_burst_async(
        self,
        host: str,
        port: int,
        count: int,
        packet_size: int,
        on_completed: Callable[[dict], None],
        delay_ms: float = 10.0,
        progress_cb: Callable[[int, int], None] | None = None,
    ):
        """Spawns a daemon thread to run transmit_burst and invoke on_completed."""

        def _worker():
            results = self.transmit_burst(
                host=host,
                port=port,
                count=count,
                packet_size=packet_size,
                delay_ms=delay_ms,
                progress_cb=progress_cb,
            )
            on_completed(results)

        thread = threading.Thread(target=_worker, daemon=True, name="UDPProbeThread")
        thread.start()
        return thread
