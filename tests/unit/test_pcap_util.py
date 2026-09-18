import struct
from pathlib import Path
from src.core.pcap_util import PCAPExporter, compute_internet_checksum


def test_compute_internet_checksum():
    # RFC 1071 example verification
    data = b"\x45\x00\x00\x3c\x1c\x46\x40\x00\x40\x06\x00\x00\xac\x10\x0a\x63\xac\x10\x0a\x0c"
    chk = compute_internet_checksum(data)
    assert 0 <= chk <= 0xFFFF
    # Recomputing over header with checksum should yield 0 or 0xFFFF
    data_with_chk = data[:10] + struct.pack("!H", chk) + data[12:]
    verify = compute_internet_checksum(data_with_chk)
    assert verify in (0, 0xFFFF)


def test_pcap_exporter_empty(tmp_path: Path):
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
