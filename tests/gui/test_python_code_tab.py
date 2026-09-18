"""
Module: test_python_code_tab.py
───────────────────────────────
Purpose: Validates the interactive Python Code Generator widget, snippet templates, dynamic parameter
interpolation, clipboard copying, and language localization.

Architectural Role:
Acts as the test suite for `PythonCodeWidget`, which bridges the visual GUI laboratory with programmatic
Python socket scripting by generating self-contained code snippets matching GUI operations.

Responsibilities:
- Verify that standard protocol operations (Handshake, Auth, List, Download, Upload, TLS, Complete Script)
  are populated in the operation dropdown selector.
- Ensure that host, port, username, and TLS flags update template code dynamically.
- Validate clipboard copy actions and transient UI button feedback.
- Verify full interface retranslation between English and Spanish.

Dependencies:
- `pytest`
- `src.localization.locale_manager.LocaleManager`
- `src.ui.widgets.python_code_tab.PythonCodeWidget`

Expected Collaborators:
- `qtbot`: Simulates UI lifecycle and clipboard events.
- `locale`: Provides localized strings for code descriptions and button labels.

Educational Note: Programmatic Code Generation
The Python code tab enables students to immediately inspect how graphical actions (such as logging in
or uploading a file) translate into raw BSD socket API calls in standard Python, eliminating the
abstraction gap between GUI interaction and networking implementation.
"""

import pytest
from src.localization.locale_manager import LocaleManager
from src.ui.widgets.python_code_tab import PythonCodeWidget


@pytest.fixture
def locale():
    """
    Provides a real LocaleManager instance loaded with repository localization bundles.

    Returns:
        LocaleManager: Initialized with default 'en' locale.
    """
    return LocaleManager("src/localization")


def test_python_code_widget_init(qtbot, locale):
    """
    Validates initial instantiation and dynamic parameter injection into Python snippet templates.

    Args:
        qtbot: The pytest-qt fixture for simulating GUI events.
        locale: The active LocaleManager fixture.

    Returns:
        None.

    Side Effects:
        Instantiates PythonCodeWidget with specific host, port, and credentials.

    Failure Behavior:
        Fails if initial connection parameters are not correctly substituted into the displayed code.
    """
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
    """
    Validates selecting different networking operations and verifying their respective Python snippets.

    Args:
        qtbot: The pytest-qt fixture for simulating GUI events.
        locale: The active LocaleManager fixture.

    Returns:
        None.

    Side Effects:
        Changes dropdown selection index to trigger snippet regeneration.

    Failure Behavior:
        Fails if the resulting Python snippet does not contain the required protocol commands or libraries.
    """
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
    """
    Validates updating connection parameters at runtime and regenerating the code view.

    Args:
        qtbot: The pytest-qt fixture for simulating GUI events.
        locale: The active LocaleManager fixture.

    Returns:
        None.

    Side Effects:
        Invokes set_connection_params on the widget.

    Failure Behavior:
        Fails if updated host and port parameters are not reflected in the code viewer text.
    """
    widget = PythonCodeWidget(locale=locale, theme_name="mint_light")
    qtbot.addWidget(widget)

    widget.set_connection_params(host="10.0.0.1", port=4500, username="bob", tls_enabled=False)
    code = widget.code_viewer.toPlainText()
    assert 'HOST = "10.0.0.1"' in code
    assert "PORT = 4500" in code


def test_python_code_widget_clipboard(qtbot, locale):
    """
    Validates copying generated code to the system clipboard and updating button feedback.

    Args:
        qtbot: The pytest-qt fixture for simulating GUI events.
        locale: The active LocaleManager fixture.

    Returns:
        None.

    Side Effects:
        Sets text on the application clipboard and updates button text.

    Failure Behavior:
        Fails if the button text is not updated to the localized 'Copied!' indicator.
    """
    widget = PythonCodeWidget(locale=locale, theme_name="mint_light")
    qtbot.addWidget(widget)

    widget._copy_to_clipboard()
    assert widget.copy_btn.text() == widget._t("python_code.copied")


def test_python_code_widget_retranslate(qtbot, locale):
    """
    Validates dynamic UI language switching across dropdown options and button labels.

    Args:
        qtbot: The pytest-qt fixture for simulating GUI events.
        locale: The active LocaleManager fixture.

    Returns:
        None.

    Side Effects:
        Mutates the active locale between English ('en') and Spanish ('es').

    Failure Behavior:
        Fails if button text or explanatory notes do not update to the target language.
    """
    widget = PythonCodeWidget(locale=locale, theme_name="mint_light")
    qtbot.addWidget(widget)

    locale.set_locale("es")
    widget.retranslate()
    assert "Copiar" in widget.copy_btn.text()

    locale.set_locale("en")
    widget.retranslate()
    assert "Copy" in widget.copy_btn.text()
