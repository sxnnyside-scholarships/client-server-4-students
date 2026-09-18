from src.core.config import ConfigManager
from src.localization.locale_manager import LocaleManager
from src.network.client_backend import ClientBackend
from src.ui.client_window import ClientWindow
from src.ui.themes.theme_manager import ThemeManager


def test_client_lab_hub_tabs(qtbot, qapp, tmp_path):
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
    mocker.patch(
        "PyQt6.QtWidgets.QFileDialog.getSaveFileName",
        return_value=(str(out_pcap), "Wireshark Capture (*.pcap)"),
    )
    mocker.patch("PyQt6.QtWidgets.QMessageBox.information")

    window.inspector._on_export_pcap()

    assert out_pcap.exists()
    assert out_pcap.stat().st_size > 24
