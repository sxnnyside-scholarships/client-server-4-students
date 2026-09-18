"""
Module: pcap_util.py
────────────────────
Purpose: Pure-Python standard Libpcap 2.4 binary generator for educational network traffic analysis.

Architectural Role:
Allows students and instructors to record application-layer protocol exchanges (TX/RX)
and dump them into a standard `.pcap` capture file that can be loaded directly into
Wireshark, tcpdump, or tshark for classroom inspection and packet dissection.

Key Capabilities:
- Standard Libpcap global header (magic 0xa1b2c3d4, v2.4, LINKTYPE_ETHERNET).
- Ethernet II framing (14 bytes) with IPv4 EtherType (0x0800).
- IPv4 header (20 bytes) with authentic 16-bit one's complement checksum calculation.
- TCP header (20 bytes) with dynamic relative sequence and acknowledgement numbers.
- Zero external dependencies: pure Python standard library (`struct`, `time`, `socket`).
"""

from __future__ import annotations

import struct
import time
from pathlib import Path
from typing import NamedTuple


def compute_internet_checksum(data: bytes) -> int:
    """
    Computes the standard 16-bit one's complement Internet checksum (RFC 1071).

    Args:
        data: Byte string over which to compute the checksum.

    Returns:
        16-bit integer checksum.
    """
    if len(data) % 2 != 0:
        data += b"\x00"

    total = 0
    for i in range(0, len(data), 2):
        word = (data[i] << 8) + data[i + 1]
        total += word
        total = (total & 0xFFFF) + (total >> 16)

    return (~total) & 0xFFFF


class CapturedPacket(NamedTuple):
    timestamp: float
    direction: str  # "tx" (client -> server) or "rx" (server -> client)
    packet_str: str


class PCAPExporter:
    """
    In-memory capture buffer and Libpcap file exporter.

    Responsibilities:
    - Recording application-layer protocol messages with accurate timestamps.
    - Synthesizing Ethernet, IPv4, and TCP frames wrapping the CS4S payloads.
    - Exporting RFC-compliant `.pcap` binary streams readable by Wireshark.
    """

    def __init__(
        self,
        client_ip: str = "127.0.0.1",
        server_ip: str = "127.0.0.1",
        client_port: int = 54321,
        server_port: int = 2121,
        max_buffer_size: int = 5000,
    ):
        self.client_ip = client_ip
        self.server_ip = server_ip
        self.client_port = client_port
        self.server_port = server_port
        self.max_buffer_size = max_buffer_size
        self._packets: list[CapturedPacket] = []

    def record_packet(self, direction: str, packet: str, timestamp: float | None = None) -> None:
        """
        Appends a captured protocol packet to the export buffer.

        Args:
            direction: "tx" for outgoing (client -> server) or "rx" for incoming (server -> client).
            packet: The raw protocol text string.
            timestamp: Optional epoch float timestamp. If None, uses `time.time()`.
        """
        ts = timestamp if timestamp is not None else time.time()
        self._packets.append(CapturedPacket(timestamp=ts, direction=direction.lower(), packet_str=packet))
        if len(self._packets) > self.max_buffer_size:
            self._packets.pop(0)

    def clear(self) -> None:
        """Clears all buffered packets."""
        self._packets.clear()

    @property
    def packet_count(self) -> int:
        """Returns the number of buffered packets."""
        return len(self._packets)

    def get_packets(self) -> list[CapturedPacket]:
        """Returns a copy of the buffered packets."""
        return list(self._packets)

    def export_to_bytes(self) -> bytes:
        """
        Encodes all captured packets into a standard Libpcap 2.4 binary byte string.

        Returns:
            bytes containing the global PCAP header followed by all packet frames.
        """
        # 1. Libpcap Global Header (24 bytes)
        # Magic: 0xa1b2c3d4 (microsecond resolution)
        # Version: 2.4
        # Thiszone: 0, Sigfigs: 0
        # Snaplen: 65535
        # LinkType: 1 (LINKTYPE_ETHERNET)
        pcap_buffer = bytearray()
        pcap_buffer.extend(struct.pack("=IHHiIII", 0xA1B2C3D4, 2, 4, 0, 0, 65535, 1))

        # Synthetic MAC addresses
        client_mac = b"\x02\x00\x00\x00\x00\x01"
        server_mac = b"\x02\x00\x00\x00\x00\x02"

        # IP addresses
        try:
            client_ip_bytes = bytes(map(int, self.client_ip.split(".")))
        except Exception:
            client_ip_bytes = b"\x7f\x00\x00\x01"

        try:
            server_ip_bytes = bytes(map(int, self.server_ip.split(".")))
        except Exception:
            server_ip_bytes = b"\x7f\x00\x00\x01"

        client_seq = 1000
        server_seq = 5000
        ident = 1

        for pkt in self._packets:
            # Framing: message payload + newline delimiter as in real wire protocol
            payload_str = pkt.packet_str
            if not payload_str.endswith("\n"):
                payload_str += "\n"
            payload_bytes = payload_str.encode("utf-8", errors="replace")

            is_tx = pkt.direction == "tx"
            src_mac = client_mac if is_tx else server_mac
            dst_mac = server_mac if is_tx else client_mac
            src_ip = client_ip_bytes if is_tx else server_ip_bytes
            dst_ip = server_ip_bytes if is_tx else client_ip_bytes
            src_port = self.client_port if is_tx else self.server_port
            dst_port = self.server_port if is_tx else self.client_port

            current_seq = client_seq if is_tx else server_seq
            current_ack = server_seq if is_tx else client_seq

            # ── Ethernet II Header (14 bytes) ───────────────────────────
            eth_hdr = dst_mac + src_mac + struct.pack("!H", 0x0800)

            # ── TCP Header (20 bytes) ───────────────────────────────────
            # Flags: 0x18 = PSH | ACK
            tcp_hdr = struct.pack(
                "!HHIIBBHHH",
                src_port,
                dst_port,
                current_seq,
                current_ack,
                0x50,  # 5 * 32-bit words = 20 bytes data offset
                0x18,  # PSH, ACK
                65535,  # Window size
                0,  # Checksum (0 indicates offload or optional in raw capture)
                0,  # Urgent pointer
            )

            # ── IPv4 Header (20 bytes) ──────────────────────────────────
            ip_tot_len = 20 + 20 + len(payload_bytes)
            # Pre-build IP header with 0 checksum for calculation
            ip_hdr_pre = struct.pack(
                "!BBHHHBBH4s4s",
                0x45,  # Version 4, IHL 5
                0,  # DSCP / ECN
                ip_tot_len,
                ident & 0xFFFF,
                0x4000,  # Don't fragment flag
                64,  # TTL
                6,  # TCP protocol
                0,  # Checksum placeholder
                src_ip,
                dst_ip,
            )
            ip_checksum = compute_internet_checksum(ip_hdr_pre)
            ip_hdr = struct.pack(
                "!BBHHHBBH4s4s",
                0x45,
                0,
                ip_tot_len,
                ident & 0xFFFF,
                0x4000,
                64,
                6,
                ip_checksum,
                src_ip,
                dst_ip,
            )

            frame = eth_hdr + ip_hdr + tcp_hdr + payload_bytes

            # ── Packet Record Header (16 bytes) ─────────────────────────
            sec = int(pkt.timestamp)
            usec = int((pkt.timestamp - sec) * 1_000_000)
            pkt_hdr = struct.pack("=IIII", sec, usec, len(frame), len(frame))

            pcap_buffer.extend(pkt_hdr)
            pcap_buffer.extend(frame)

            # Advance sequence numbers
            if is_tx:
                client_seq += len(payload_bytes)
            else:
                server_seq += len(payload_bytes)
            ident += 1

        return bytes(pcap_buffer)

    def export_to_file(self, filepath: str | Path) -> int:
        """
        Writes buffered packet frames to a `.pcap` file on disk.

        Args:
            filepath: Destination path for the `.pcap` file.

        Returns:
            The number of packets exported.
        """
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        data = self.export_to_bytes()
        path.write_bytes(data)
        return len(self._packets)
