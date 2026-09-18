"""
Module: test_pcap_util.py
─────────────────────────
Purpose: Validates synthetic Ethernet II, IPv4, TCP frame construction, RFC 1071 checksum verification,
and standard Libpcap (.pcap) binary file serialization.

Architectural Role:
Acts as the verification suite for `src.core.pcap_util`, ensuring that network traffic recorded by the application
can be exported into valid binary PCAP files inspectable by Wireshark and `tcpdump`.

Responsibilities:
- Verify mathematical correctness of the one's complement Internet Checksum algorithm (RFC 1071).
- Verify standard 24-byte Libpcap global file header generation (magic number, major/minor version, snaplen).
- Validate synthesis of layered network protocol headers (Ethernet II, IPv4 header, TCP header) and payloads.
- Verify packet counting, file writing, and buffer clearing behavior.

Dependencies:
- `struct`
- `pathlib.Path`
- `src.core.pcap_util.PCAPExporter`
- `src.core.pcap_util.compute_internet_checksum`

Expected Collaborators:
- `tmp_path`: Pytest fixture providing clean temporary directory storage.

Educational Note: Binary Frame Construction
Building raw PCAP files in pure Python without external C libraries (like libpcap or scapy) allows students
to directly inspect the exact byte offsets of Ethernet headers (14 bytes), IPv4 headers (20 bytes), and TCP
headers (20 bytes) alongside standard Big-Endian network byte order formatting.
"""

import struct
from pathlib import Path
from src.core.pcap_util import PCAPExporter, compute_internet_checksum


def test_compute_internet_checksum():
    """
    Validates the one's complement Internet Checksum calculation against standard RFC 1071 test vectors.

    Args:
        None.

    Returns:
        None.

    Side Effects:
        Computes 16-bit integer checksum over raw byte sequences.

    Failure Behavior:
        Fails if checksum does not fit in 16 bits or if checksumming header including checksum does not yield 0 or 0xFFFF.
    """
    # RFC 1071 example verification
    data = b"\x45\x00\x00\x3c\x1c\x46\x40\x00\x40\x06\x00\x00\xac\x10\x0a\x63\xac\x10\x0a\x0c"
    chk = compute_internet_checksum(data)
    assert 0 <= chk <= 0xFFFF
    # Recomputing over header with checksum should yield 0 or 0xFFFF
    data_with_chk = data[:10] + struct.pack("!H", chk) + data[12:]
    verify = compute_internet_checksum(data_with_chk)
    assert verify in (0, 0xFFFF)


def test_pcap_exporter_empty(tmp_path: Path):
    """
    Validates export of an empty PCAP buffer and verifies the 24-byte Libpcap global file header structure.

    Args:
        tmp_path: Pytest temporary directory fixture.

    Returns:
        None.

    Side Effects:
        Serializes global header to in-memory bytes.

    Failure Behavior:
        Fails if length is not exactly 24 bytes, or magic number (0xA1B2C3D4) / version (2.4) are invalid.
    """
    exporter = PCAPExporter()
    assert exporter.packet_count == 0
    pcap_bytes = exporter.export_to_bytes()
    # Should contain only 24-byte Libpcap global header
    assert len(pcap_bytes) == 24
    magic, maj, min_v, tz, sig, snaplen, net = struct.unpack("=IHHiIII", pcap_bytes)
    assert magic == 0xA1B2C3D4
    assert maj == 2
    assert min_v == 4
    assert snaplen == 65535
    assert net == 1  # LINKTYPE_ETHERNET


def test_pcap_exporter_packets(tmp_path: Path):
    """
    Validates synthetic frame encapsulation (Ethernet II + IPv4 + TCP) and export into a binary .pcap file.

    Args:
        tmp_path: Pytest temporary directory fixture for writing test capture.

    Returns:
        None.

    Side Effects:
        Writes binary file test.pcap to disk.

    Failure Behavior:
        Fails if file byte count is deficient, ethertype != 0x0800, IP proto != 6, or port numbers mismatch.
    """
    exporter = PCAPExporter(client_ip="192.168.1.100", server_ip="192.168.1.200", client_port=54321, server_port=2121)
    exporter.record_packet("tx", "HELLO|CS4S/2.0")
    exporter.record_packet("rx", "220 HELLO|CS4S/2.0")

    assert exporter.packet_count == 2
    pcap_file = tmp_path / "test.pcap"
    count = exporter.export_to_file(pcap_file)
    assert count == 2
    assert pcap_file.exists()

    data = pcap_file.read_bytes()
    assert len(data) > 24

    # Validate global header
    magic = struct.unpack("=I", data[:4])[0]
    assert magic == 0xA1B2C3D4

    # Validate first packet record header
    sec, usec, incl_len, orig_len = struct.unpack("=IIII", data[24:40])
    assert incl_len == orig_len
    assert incl_len > 0
    frame = data[40 : 40 + incl_len]

    # Ethernet II: 14 bytes (ethertype 0x0800)
    ethertype = struct.unpack("!H", frame[12:14])[0]
    assert ethertype == 0x0800

    # IPv4: 20 bytes (protocol 6 = TCP)
    ip_proto = frame[14 + 9]
    assert ip_proto == 6

    # TCP: 20 bytes (ports 54321 -> 2121)
    src_port, dst_port = struct.unpack("!HH", frame[34:38])
    assert src_port == 54321
    assert dst_port == 2121

    # Payload contains HELLO
    payload = frame[54:]
    assert b"HELLO|CS4S/2.0\n" in payload

    # Test clear
    exporter.clear()
    assert exporter.packet_count == 0
