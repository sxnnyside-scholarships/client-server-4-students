"""
Module: test_ladder_diagram.py
──────────────────────────────
Purpose: Validates the Interactive Sequence (Ladder) Diagram widget rendering, message tracking,
delta computation, PING filtering, and dynamic localization updates.

Architectural Role:
Acts as the GUI unit test suite for `LadderDiagramWidget`, validating the pedagogical sequence diagram
canvas that visually contrasts Client and Server lifelines, message arrows, and HTTP/ASCII status codes.

Responsibilities:
- Verify initial empty state presentation and automatic transition upon receiving packet events.
- Validate accurate message ingestion (direction, status code extraction, millisecond delta).
- Test keepalive (PING/PONG) toggle filtering functionality.
- Verify RTT latency readout updates.
- Ensure bidirectional dynamic retranslation between English and Spanish.

Dependencies:
- `pytest`
- `src.localization.locale_manager.LocaleManager`
- `src.ui.widgets.ladder_diagram.LadderDiagramWidget`

Expected Collaborators:
- `qtbot`: Simulates UI lifecycle and event loops.
- `locale`: Provides isolated locale key lookups.

Educational Note: Sequence Diagram Visualizations
Sequence (ladder) diagrams represent the temporal ordering of communication between distinct
network entities. Verifying that status codes, latency deltas, and directional arrows render
accurately ensures students develop a correct mental model of request-response lifecycles.
"""

import pytest
from src.localization.locale_manager import LocaleManager
from src.ui.widgets.ladder_diagram import LadderDiagramWidget


@pytest.fixture
def locale():
    """
    Provides a real LocaleManager instance loaded with repository localization bundles.

    Returns:
        LocaleManager: Initialized with default 'en' locale.
    """
    return LocaleManager("src/localization")


def test_ladder_diagram_init(qtbot, locale):
    """
    Validates the initial empty state of the Ladder Diagram before network traffic arrives.

    Args:
        qtbot: The pytest-qt fixture for simulating GUI events.
        locale: The active LocaleManager fixture.

    Returns:
        None.

    Side Effects:
        Instantiates LadderDiagramWidget and adds it to the qtbot tracking loop.

    Failure Behavior:
        Fails if the empty state placeholder is hidden or the scrollable canvas is initially visible.
    """
    widget = LadderDiagramWidget(locale=locale, theme_name="mint_light")
    qtbot.addWidget(widget)

    assert not widget.empty_state.isHidden()
    assert widget.scroll.isHidden()
    assert widget.rtt_label.text() != ""


def test_ladder_diagram_add_packets(qtbot, locale):
    """
    Validates message ingestion, status code extraction, delta calculation, and PING filtering.

    Args:
        qtbot: The pytest-qt fixture for simulating GUI events.
        locale: The active LocaleManager fixture.

    Returns:
        None.

    Side Effects:
        Appends synthetic TX and RX network packets to the diagram canvas.

    Failure Behavior:
        Fails if message directions, status codes, or filter criteria produce incorrect canvas states.
    """
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
    """
    Validates real-time UI language retranslation across the ladder diagram headers and badges.

    Args:
        qtbot: The pytest-qt fixture for simulating GUI events.
        locale: The active LocaleManager fixture.

    Returns:
        None.

    Side Effects:
        Mutates the active locale between English ('en') and Spanish ('es').

    Failure Behavior:
        Fails if badge strings do not reflect the selected language strings.
    """
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
