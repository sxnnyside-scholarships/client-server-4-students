import pytest
from src.localization.locale_manager import LocaleManager
from src.ui.widgets.python_code_tab import PythonCodeWidget


@pytest.fixture
def locale():
    return LocaleManager("src/localization")


def test_python_code_widget_init(qtbot, locale):
    widget = PythonCodeWidget(
        locale=locale,
        theme_name="mint_light",
        host="192.168.1.50",
        port=8080,
        username="alice",
        tls_enabled=True,
    )
    qtbot.addWidget(widget)

    assert widget.op_combo.count() == 9
    code = widget.code_viewer.toPlainText()
    assert 'HOST = "192.168.1.50"' in code
    assert "PORT = 8080" in code
    assert widget.notes_body.text() != ""


def test_python_code_widget_switch_ops(qtbot, locale):
    widget = PythonCodeWidget(locale=locale, theme_name="mint_light")
    qtbot.addWidget(widget)

    # Switch to Auth
    widget.op_combo.setCurrentIndex(1)
    code = widget.code_viewer.toPlainText()
    assert "AUTH|" in code

    # Switch to TLS
    widget.op_combo.setCurrentIndex(7)
    code = widget.code_viewer.toPlainText()
    assert "import ssl" in code
    assert "wrap_socket" in code

    # Switch to Full script
    widget.op_combo.setCurrentIndex(8)
    code = widget.code_viewer.toPlainText()
    assert "def run_client():" in code


def test_python_code_widget_update_params(qtbot, locale):
    widget = PythonCodeWidget(locale=locale, theme_name="mint_light")
    qtbot.addWidget(widget)

    widget.set_connection_params(host="10.0.0.1", port=4500, username="bob", tls_enabled=False)
    code = widget.code_viewer.toPlainText()
    assert 'HOST = "10.0.0.1"' in code
    assert "PORT = 4500" in code


def test_python_code_widget_clipboard(qtbot, locale):
    widget = PythonCodeWidget(locale=locale, theme_name="mint_light")
    qtbot.addWidget(widget)

    widget._copy_to_clipboard()
    assert widget.copy_btn.text() == widget._t("python_code.copied")


def test_python_code_widget_retranslate(qtbot, locale):
    widget = PythonCodeWidget(locale=locale, theme_name="mint_light")
    qtbot.addWidget(widget)

    locale.set_locale("es")
    widget.retranslate()
    assert "Copiar" in widget.copy_btn.text()

    locale.set_locale("en")
    widget.retranslate()
    assert "Copy" in widget.copy_btn.text()
