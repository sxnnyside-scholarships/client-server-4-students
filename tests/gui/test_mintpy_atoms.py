import pytest
from PyQt6.QtCore import Qt, QEvent
from PyQt6.QtGui import QFocusEvent
from PyQt6.QtWidgets import QApplication

from src.ui.widgets.atoms import (
    MintButton,
    MintDoubleSpinBox,
    MintModeCard,
    MintTextInput,
    EmptyStateWidget,
)

def test_mint_button_instantiation(qtbot):
    btn = MintButton("Test", "mint_light")
    qtbot.addWidget(btn)
    assert btn.text() == "Test"
    assert btn._scale == 1.0

def test_mint_button_scale_animation(qtbot):
    btn = MintButton("Test", "mint_light")
    qtbot.addWidget(btn)
    
    # Simulate a mouse press
    qtbot.mousePress(btn, Qt.MouseButton.LeftButton)
    # The scale animation should be targeting 0.97
    assert btn._scale_anim.endValue() == 0.97
    
    # Simulate release
    qtbot.mouseRelease(btn, Qt.MouseButton.LeftButton)
    assert btn._scale_anim.endValue() == 1.0

def test_mint_text_input_glow(qtbot):
    inp = MintTextInput("mint_light")
    qtbot.addWidget(inp)
    
    # Simulate a focus in event
    inp.focusInEvent(QFocusEvent(QEvent.Type.FocusIn))
    assert inp._glow_anim.endValue() == 80
    
    # Simulate a focus out event
    inp.focusOutEvent(QFocusEvent(QEvent.Type.FocusOut))
    assert inp._glow_anim.endValue() == 0

def test_mint_spinbox_glow(qtbot):
    spin = MintDoubleSpinBox("mint_dark")
    qtbot.addWidget(spin)
    
    spin.focusInEvent(QFocusEvent(QEvent.Type.FocusIn))
    assert spin._glow_anim.endValue() == 80
    
    spin.focusOutEvent(QFocusEvent(QEvent.Type.FocusOut))
    assert spin._glow_anim.endValue() == 0

def test_empty_state_widget(qtbot):
    empty = EmptyStateWidget("Nothing here.", "mint_light", "leaf")
    qtbot.addWidget(empty)
    assert empty.text_label.text() == "Nothing here."
    
    empty.set_message("Still empty.")
    assert empty.text_label.text() == "Still empty."
