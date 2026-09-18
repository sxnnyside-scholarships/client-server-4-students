"""
Module: test_lab_hub.py
───────────────────────
Purpose: Validates the Client Lab Hub tab navigation, cross-component telemetry distribution,
and Wireshark PCAP export integration.

Architectural Role:
Acts as the automated integration test suite verifying that telemetry signals emitted by the
network backend (`packet_tx`, `packet_rx`) are routed to the Inspector, Ladder Diagram,
and Guided Missions components without coupling or loss.

Responsibilities:
- Verify switching between File Manager view and Lab Hub view.
- Ensure all five Lab tabs (Inspector, Sequence Diagram, Challenges, Code Generator, UDP Lab)
  are instantiated, switchable, and retain state.
- Validate telemetry event propagation across all subscriber widgets.
- Test user-facing PCAP file export flow via simulated file dialogs.

Dependencies:
- `PyQt6.QtWidgets`
- `src.core.config.ConfigManager`
- `src.localization.locale_manager.LocaleManager`
- `src.network.client_backend.ClientBackend`
- `src.ui.client_window.ClientWindow`
- `src.ui.themes.theme_manager.ThemeManager`
- `pytest-qt`, `pytest-mock`

Expected Collaborators:
- `qtbot`: Simulates UI lifecycle and event loops.
- `mocker`: Mocks system file dialogs and alert boxes.

Educational Note: Lab Hub Composition
The Lab Hub demonstrates a modular tabbed pedagogical interface where multiple specialized
visualizers consume identical low-level network telemetry streams concurrently without
interfering with core socket operations.
"""

from PyQt6.QtWidgets import QFileDialog, QMessageBox
from src.core.config import ConfigManager
from src.localization.locale_manager import LocaleManager
from src.network.client_backend import ClientBackend
from src.ui.client_window import ClientWindow
from src.ui.themes.theme_manager import ThemeManager


def test_client_lab_hub_tabs(qtbot, qapp, tmp_path):
    """
    Validates switching between primary client views and navigating through all 5 Lab Hub tabs.

    Args:
        qtbot: The pytest-qt fixture for simulating GUI events.
        qapp: The active QApplication instance.
        tmp_path: Temporary filesystem path fixture for isolated configuration storage.

    Returns:
        None.

    Side Effects:
        Instantiates ClientWindow and simulates tab navigation clicks.

    Failure Behavior:
        Fails if any lab tab widget is missing or if index navigation fails to activate the proper pane.
    """
    config = ConfigManager(tmp_path / "config.json")
    locale = LocaleManager("src/localization")
    themes = ThemeManager("src/ui/themes")
    backend = ClientBackend()

    window = ClientWindow(config, locale, themes, qapp, backend=backend)
    qtbot.addWidget(window)

    # Initially in files view
    assert window.stack.currentWidget() == window.files_page

    # Switch to Lab View
    window._on_mode_changed("lab")
    assert window.stack.currentWidget() == window.lab_page

    # Verify all 5 tabs exist in lab_stack
    assert window.lab_stack.count() == 5
    assert window.lab_stack.widget(0) == window.inspector
    assert window.lab_stack.widget(1) == window.ladder
    assert window.lab_stack.widget(2) == window.missions_widget
    assert window.lab_stack.widget(3) == window.python_code
    assert window.lab_stack.widget(4) == window.udp_comparison

    # Click Ladder tab
    window.tab_ladder_btn.click()
    assert window.lab_stack.currentIndex() == 1

    # Click Missions tab
    window.tab_missions_btn.click()
    assert window.lab_stack.currentIndex() == 2

    # Click Python Code tab
    window.tab_code_btn.click()
    assert window.lab_stack.currentIndex() == 3

    # Click UDP tab
    window.tab_udp_btn.click()
    assert window.lab_stack.currentIndex() == 4

    # Click Inspector tab
    window.tab_inspector_btn.click()
    assert window.lab_stack.currentIndex() == 0


def test_client_lab_telemetry_broadcast(qtbot, qapp, tmp_path):
    """
    Validates that client network telemetry signals are correctly delivered to all subscriber tabs.

    Args:
        qtbot: The pytest-qt fixture for simulating GUI events.
        qapp: The active QApplication instance.
        tmp_path: Temporary directory fixture for isolated configuration.

    Returns:
        None.

    Side Effects:
        Fires `packet_tx` and `packet_rx` signals through the mock backend instance.

    Failure Behavior:
        Fails if the Inspector, Ladder diagram, or Missions manager fail to record received frames.
    """
    config = ConfigManager(tmp_path / "config.json")
    locale = LocaleManager("src/localization")
    themes = ThemeManager("src/ui/themes")
    backend = ClientBackend()

    window = ClientWindow(config, locale, themes, qapp, backend=backend)
    qtbot.addWidget(window)

    # Emit telemetry packets
    backend.packet_tx.emit("HELLO|CS4S/2.0")
    backend.packet_rx.emit("220 HELLO|CS4S/2.0")

    # Verify inspector captured packets
    assert len(window.inspector._log_entries) == 2
    assert window.inspector.pcap_exporter.packet_count == 2

    # Verify ladder diagram captured packets
    assert len(window.ladder.canvas._messages) == 2

    # Verify missions manager validated Handshake mission
    m1 = window.missions_mgr.get_mission("m1_handshake")
    assert m1 is not None
    assert m1.is_completed is True


def test_client_lab_pcap_export(qtbot, qapp, tmp_path, mocker):
    """
    Validates PCAP packet capture export from the Protocol Inspector into a standard .pcap capture file.

    Args:
        qtbot: The pytest-qt fixture for simulating GUI events.
        qapp: The active QApplication instance.
        tmp_path: Temporary directory fixture for capture file destination.
        mocker: The pytest-mock fixture for mocking file dialogs.

    Returns:
        None.

    Side Effects:
        Writes a standard binary libpcap file to the filesystem.

    Failure Behavior:
        Fails if the resulting file does not exist or lacks standard PCAP global header bytes (> 24 bytes).
    """
    config = ConfigManager(tmp_path / "config.json")
    locale = LocaleManager("src/localization")
    themes = ThemeManager("src/ui/themes")
    backend = ClientBackend()

    window = ClientWindow(config, locale, themes, qapp, backend=backend)
    qtbot.addWidget(window)

    # Record packet
    backend.packet_tx.emit("HELLO|CS4S/2.0")
    backend.packet_rx.emit("220 HELLO|CS4S/2.0")

    # Mock QFileDialog to return a temp path
    out_pcap = tmp_path / "test_session.pcap"
    mocker.patch.object(
        QFileDialog,
        "getSaveFileName",
        return_value=(str(out_pcap), "Wireshark Capture (*.pcap)"),
    )
    mocker.patch.object(QMessageBox, "information")

    window.inspector._on_export_pcap()

    assert out_pcap.exists()
    assert out_pcap.stat().st_size > 24
