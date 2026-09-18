from unittest.mock import MagicMock
from src.localization.locale_manager import LocaleManager
from src.ui.widgets.udp_comparison import UDPComparisonWidget


def test_udp_comparison_widget_render(qtbot):
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
    locale = LocaleManager("src/localization")
    widget = UDPComparisonWidget(locale=locale, theme_name="dark")
    qtbot.addWidget(widget)

    # Mock client
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
    locale = LocaleManager("src/localization")
    widget = UDPComparisonWidget(locale=locale, theme_name="dark")
    qtbot.addWidget(widget)

    locale.set_locale("es")
    widget.retranslate()
    assert "Canal UDP" in widget.title_label.text()

    locale.set_locale("en")
    widget.retranslate()
    assert "UDP" in widget.title_label.text()
