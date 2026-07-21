import pytest
import json
from pathlib import Path

from src.localization.locale_manager import LocaleManager
from src.core.config import ConfigManager
from src.ui.themes.theme_manager import ThemeManager

from src.ui.client_window import ClientWindow
from src.ui.server_window import ServerWindow
from src.network.client_backend import ClientBackend
from src.network.server_backend import ServerBackend


def test_json_key_parity():
    """Asserts that en.json and es.json have identical key trees."""
    base_path = Path("src/localization")
    with open(base_path / "en.json", "r", encoding="utf-8") as f:
        en_data = json.load(f)["en"]
    with open(base_path / "es.json", "r", encoding="utf-8") as f:
        es_data = json.load(f)["es"]

    def flatten(d, prefix=""):
        res = set()
        for k, v in d.items():
            if isinstance(v, dict):
                res.update(flatten(v, prefix + k + "."))
            else:
                res.add(prefix + k)
        return res

    en_keys = flatten(en_data)
    es_keys = flatten(es_data)

    missing_in_es = en_keys - es_keys
    missing_in_en = es_keys - en_keys

    assert not missing_in_es, f"Keys missing in es.json: {missing_in_es}"
    assert not missing_in_en, f"Keys missing in en.json: {missing_in_en}"


def walk_widgets(widget):
    yield widget
    for child in widget.children():
        if child.isWidgetType():
            yield from walk_widgets(child)


def check_no_bracket_keys(window):
    """Asserts no visible widget text starts with `[` indicating a missing key."""
    for w in walk_widgets(window):
        if hasattr(w, "text") and callable(w.text):
            text = w.text()
            if text and text.startswith("[") and text.endswith("]"):
                pytest.fail(f"Found un-namespaced or missing key in UI text: {text} on {w.objectName()}")
        if hasattr(w, "toolTip") and callable(w.toolTip):
            tt = w.toolTip()
            if tt and tt.startswith("[") and tt.endswith("]"):
                pytest.fail(f"Found un-namespaced or missing key in tooltip: {tt} on {w.objectName()}")
        if hasattr(w, "accessibleName") and callable(w.accessibleName):
            an = w.accessibleName()
            if an and an.startswith("[") and an.endswith("]"):
                pytest.fail(f"Found un-namespaced or missing key in accessibleName: {an} on {w.objectName()}")


def test_client_window_localization(qtbot, qapp, mocker, tmp_path):
    config = ConfigManager(tmp_path / "config.json")
    locale = LocaleManager("src/localization")
    themes = ThemeManager("src/ui/themes")
    backend = ClientBackend()

    window = ClientWindow(config, locale, themes, qapp, backend=backend)
    qtbot.addWidget(window)

    locale.set_locale("en")
    window.retranslate()
    check_no_bracket_keys(window)

    locale.set_locale("es")
    window.retranslate()
    check_no_bracket_keys(window)


def test_server_window_localization(qtbot, qapp, mocker, tmp_path):
    config = ConfigManager(tmp_path / "config.json")
    locale = LocaleManager("src/localization")
    themes = ThemeManager("src/ui/themes")

    auth_mock = mocker.MagicMock()
    auth_mock.list_users.return_value = []
    files_mock = mocker.MagicMock()

    runtime_mock = mocker.MagicMock()
    runtime_mock.logs_dir = "/tmp"

    backend = ServerBackend(auth_mock, files_mock)

    window = ServerWindow(
        config, locale, themes, qapp, auth=auth_mock, files=files_mock, backend=backend, runtime=runtime_mock
    )
    qtbot.addWidget(window)

    locale.set_locale("en")
    window.retranslate()
    check_no_bracket_keys(window)

    locale.set_locale("es")
    window.retranslate()
    check_no_bracket_keys(window)
