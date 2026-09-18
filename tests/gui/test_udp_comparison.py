"""
Module: test_udp_comparison.py
──────────────────────────────
Purpose: Validates the Educational UDP Lab widget, datagram burst transmission triggers, visual matrix
rendering, metric card calculations, and dynamic localization.

Architectural Role:
Acts as the test suite for `UDPComparisonWidget`, which demonstrates connectionless, unreliable datagram
transmissions and visually contrasts UDP packet loss and jitter against reliable stream-oriented TCP.

Responsibilities:
- Verify that initial widget rendering configures burst count, datagram payload size, and target parameters.
- Validate asynchronous burst initiation, button locking state during transmission, and result rendering.
- Verify packet chip matrix rendering (green for received, red for dropped) and aggregated loss percentage.
- Verify dynamic localization updates across titles and metric cards.

Dependencies:
- `unittest.mock.MagicMock`
- `src.localization.locale_manager.LocaleManager`
- `src.ui.widgets.udp_comparison.UDPComparisonWidget`

Expected Collaborators:
- `qtbot`: Simulates UI lifecycle and event loops.
- `locale`: Provides localized strings for lab text and metrics.

Educational Note: Visualizing Packet Loss
Connectionless protocols like UDP do not perform retransmissions or acknowledgments at layer 4. By rendering
individual packet chips in real-time, students visually perceive burst drops caused by network congestion or
impairment without relying solely on abstract statistics.
"""

from unittest.mock import MagicMock
from src.localization.locale_manager import LocaleManager
from src.ui.widgets.udp_comparison import UDPComparisonWidget


def test_udp_comparison_widget_render(qtbot):
    """
    Validates initial rendering of the UDP Comparison Widget and parameter update methods.

    Args:
        qtbot: The pytest-qt fixture for simulating GUI events.

    Returns:
        None.

    Side Effects:
        Instantiates UDPComparisonWidget and registers it with the qtbot event loop.

    Failure Behavior:
        Fails if controls (comboboxes, title label, burst button) fail to initialize or update.
    """
    locale = LocaleManager("src/localization")
    widget = UDPComparisonWidget(locale=locale, theme_name="dark", host="127.0.0.1", udp_port=2122)
    qtbot.addWidget(widget)

    assert widget.title_label.text() != ""
    assert widget.count_combo.count() == 4
    assert widget.size_combo.count() == 4
    assert widget.burst_btn.isEnabled()

    widget.set_target("192.168.1.50", 9999)
    assert widget.host == "192.168.1.50"
    assert widget.udp_port == 9999


def test_udp_comparison_burst_results(qtbot):
    """
    Validates the execution flow of a UDP probe burst, button state toggling, and metric card updates.

    Args:
        qtbot: The pytest-qt fixture for simulating GUI events.

    Returns:
        None.

    Side Effects:
        Emits synthetic burst summary metrics via `burst_finished` signal.

    Failure Behavior:
        Fails if packet chips are not created in the matrix layout or if loss/latency values are inaccurate.
    """
    locale = LocaleManager("src/localization")
    widget = UDPComparisonWidget(locale=locale, theme_name="dark")
    qtbot.addWidget(widget)

    sample_results = {
        "total_sent": 10,
        "total_received": 8,
        "packets_lost": 2,
        "loss_rate_pct": 20.0,
        "avg_rtt_ms": 4.5,
        "min_rtt_ms": 2.1,
        "max_rtt_ms": 7.8,
        "throughput_kbps": 128.5,
        "packets": [{"seq": i, "received": (i < 8), "rtt_ms": 4.5 if i < 8 else 0.0} for i in range(10)],
    }

    widget._probe_client.transmit_burst_async = MagicMock()
    widget.burst_btn.click()
    assert widget._is_transmitting is True
    assert not widget.burst_btn.isEnabled()

    # Trigger results
    widget.burst_finished.emit(sample_results)
    assert widget._is_transmitting is False
    assert widget.burst_btn.isEnabled()

    # Check that 10 chips were rendered in matrix grid
    assert widget.matrix_grid.count() == 10
    assert "20.0" in widget.status_label.text()
    assert "20.0%" in widget.udp_metrics_loss.text()
    assert "4.50 ms" in widget.udp_metrics_latency.text()


def test_udp_comparison_retranslate(qtbot):
    """
    Validates on-the-fly language switching across widget title and metric labels.

    Args:
        qtbot: The pytest-qt fixture for simulating GUI events.

    Returns:
        None.

    Side Effects:
        Switches the active locale between Spanish and English.

    Failure Behavior:
        Fails if the title label fails to reflect the selected language strings.
    """
    locale = LocaleManager("src/localization")
    widget = UDPComparisonWidget(locale=locale, theme_name="dark")
    qtbot.addWidget(widget)

    locale.set_locale("es")
    widget.retranslate()
    assert "Canal UDP" in widget.title_label.text()

    locale.set_locale("en")
    widget.retranslate()
    assert "UDP" in widget.title_label.text()
