import pytest
from src.localization.locale_manager import LocaleManager
from src.ui.widgets.ladder_diagram import LadderDiagramWidget


@pytest.fixture
def locale():
    return LocaleManager("src/localization")


def test_ladder_diagram_init(qtbot, locale):
    widget = LadderDiagramWidget(locale=locale, theme_name="mint_light")
    qtbot.addWidget(widget)

    assert not widget.empty_state.isHidden()
    assert widget.scroll.isHidden()
    assert widget.rtt_label.text() != ""


def test_ladder_diagram_add_packets(qtbot, locale):
    widget = LadderDiagramWidget(locale=locale, theme_name="mint_light")
    qtbot.addWidget(widget)

    widget.add_tx("HELLO|CS4S/2.0")
    assert widget.empty_state.isHidden()
    assert not widget.scroll.isHidden()
    assert len(widget.canvas._messages) == 1

    widget.add_rx("220 HELLO|CS4S/2.0")
    assert len(widget.canvas._messages) == 2
    rx_msg = widget.canvas._messages[1]
    assert rx_msg.status_code == 220
    assert rx_msg.delta_ms is not None

    # Error status code
    widget.add_rx("400 BAD_REQUEST|Invalid packet")
    assert widget.canvas._messages[2].status_code == 400

    # PING filtering
    widget.add_tx("PING")
    widget.add_rx("PONG")
    assert len(widget.canvas._messages) == 5

    widget.ping_check.setChecked(True)
    filtered = widget.canvas._filtered_messages()
    assert len(filtered) == 3

    widget.ping_check.setChecked(False)
    assert len(widget.canvas._filtered_messages()) == 5

    # RTT display
    widget.set_rtt(12.5)
    assert "12.5" in widget.rtt_label.text()

    # Clear
    widget.clear()
    assert len(widget.canvas._messages) == 0
    assert not widget.empty_state.isHidden()


def test_ladder_diagram_retranslate(qtbot, locale):
    widget = LadderDiagramWidget(locale=locale, theme_name="mint_light")
    qtbot.addWidget(widget)

    locale.set_locale("es")
    widget.retranslate()
    assert "Cliente" in widget.client_badge.text()
    assert "Servidor" in widget.server_badge.text()

    locale.set_locale("en")
    widget.retranslate()
    assert "Client" in widget.client_badge.text()
    assert "Server" in widget.server_badge.text()
