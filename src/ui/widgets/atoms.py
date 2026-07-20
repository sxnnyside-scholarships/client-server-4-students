"""
Module: atoms.py
────────────────
Purpose: Provides the core, custom-painted atomic widgets (Buttons, Inputs, SpinBoxes)
defined by the MintPy Design System.

These atoms encapsulate micro-animations (scale-on-press, focus glows) that cannot
be achieved purely via QSS, ensuring a high-quality tactile feel.
"""

from PyQt6.QtCore import (
    QPropertyAnimation,
    Qt,
    QVariantAnimation,
    pyqtProperty,
    QSize,
    QRectF,
    QPointF,
    QEvent,
    pyqtSignal,
)
from PyQt6.QtGui import QColor, QPainter, QFocusEvent, QPainterPath, QPen, QFont, QLinearGradient
from PyQt6.QtWidgets import (
    QDoubleSpinBox,
    QGraphicsDropShadowEffect,
    QLabel,
    QLineEdit,
    QPushButton,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QToolButton,
    QCheckBox,
    QStyleOptionToolButton,
    QStyleOptionButton,
    QStyle,
    QStylePainter,
)

from src.ui.icons.icon_provider import get_icon
from src.ui.themes.tokens import icon_color, status_color, surface_colors, mint_gradient


class MintButton(QPushButton):
    """
    A custom-painted push button that scales down to 97% on press to provide
    a tactile micro-response without causing layout shifts.
    """
    def __init__(self, text: str = "", theme_name: str = "mint_light", parent=None):
        super().__init__(text, parent)
        self._theme_name = theme_name
        self._scale = 1.0
        self._hover_blend = 0.0

        self._scale_anim = QPropertyAnimation(self, b"scale_factor")
        self._scale_anim.setDuration(80)
        
        self._hover_anim = QVariantAnimation(self)
        self._hover_anim.setDuration(100)
        self._hover_anim.valueChanged.connect(self._set_hover_blend)

        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.installEventFilter(self)

    @pyqtProperty(float)
    def scale_factor(self):
        return self._scale

    @scale_factor.setter
    def scale_factor(self, value):
        self._scale = value
        self.update()

    def _set_hover_blend(self, value: float):
        self._hover_blend = value
        self.update()

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.Enter:
            self._hover_anim.stop()
            self._hover_anim.setStartValue(self._hover_blend)
            self._hover_anim.setEndValue(1.0)
            self._hover_anim.start()
        elif event.type() == QEvent.Type.Leave:
            self._hover_anim.stop()
            self._hover_anim.setStartValue(self._hover_blend)
            self._hover_anim.setEndValue(0.0)
            self._hover_anim.start()
        return super().eventFilter(obj, event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._scale_anim.stop()
            self._scale_anim.setEndValue(0.97)
            self._scale_anim.start()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._scale_anim.stop()
            self._scale_anim.setEndValue(1.0)
            self._scale_anim.start()
        super().mouseReleaseEvent(event)

    def paintEvent(self, event):
        """
        Uses QStylePainter to draw the exact QSS-defined control, then overlays
        the smooth hover fade and applies the scale transform.
        """
        painter = QStylePainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        opt = QStyleOptionButton()
        self.initStyleOption(opt)

        # Suppress instant QSS hover/pressed states so our animations take over
        opt.state &= ~QStyle.StateFlag.State_MouseOver
        opt.state &= ~QStyle.StateFlag.State_Sunken

        cx = self.width() / 2.0
        cy = self.height() / 2.0

        if self._scale != 1.0:
            painter.translate(cx, cy)
            painter.scale(self._scale, self._scale)
            painter.translate(-cx, -cy)

        # Let QStyle draw the base button (background, border, text, icon from QSS)
        painter.drawControl(QStyle.ControlElement.CE_PushButton, opt)

        # Hover fade: blend a mint-tinted overlay directly on top
        if self._hover_blend > 0:
            if self._theme_name == "mint_dark":
                overlay_color = QColor(100, 255, 200)
            else:
                overlay_color = QColor(0, 150, 100)
                
            overlay_alpha = int(self._hover_blend * 30) # max 30 alpha
            overlay_color.setAlpha(overlay_alpha)
            
            path = QPainterPath()
            path.addRoundedRect(QRectF(self.rect()), 10, 10)
                
            painter.fillPath(path, overlay_color)


class MintModeCard(QToolButton):
    """
    A custom-painted tool button (card) that scales down to 97% on press,
    designed for the Launcher mode selection.
    """
    def __init__(self, theme_name: str = "mint_light", parent=None):
        super().__init__(parent)
        self._theme_name = theme_name
        self._scale = 1.0
        self._hover_blend = 0.0

        self._scale_anim = QPropertyAnimation(self, b"scale_factor")
        self._scale_anim.setDuration(80)
        
        self._hover_anim = QVariantAnimation(self)
        self._hover_anim.setDuration(100)
        self._hover_anim.valueChanged.connect(self._set_hover_blend)
        
        self._icon_size_anim = QPropertyAnimation(self, b"iconSize")
        self._icon_size_anim.setDuration(100)
        
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.installEventFilter(self)

    @pyqtProperty(float)
    def scale_factor(self):
        return self._scale

    @scale_factor.setter
    def scale_factor(self, value):
        self._scale = value
        self.update()
        
    def _set_hover_blend(self, value: float):
        self._hover_blend = value
        self.update()
        
    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.Enter:
            self._hover_anim.stop()
            self._hover_anim.setStartValue(self._hover_blend)
            self._hover_anim.setEndValue(1.0)
            self._hover_anim.start()
            
            self._icon_size_anim.stop()
            self._icon_size_anim.setStartValue(self.iconSize())
            self._icon_size_anim.setEndValue(QSize(34, 34))
            self._icon_size_anim.start()
        elif event.type() == QEvent.Type.Leave:
            self._hover_anim.stop()
            self._hover_anim.setStartValue(self._hover_blend)
            self._hover_anim.setEndValue(0.0)
            self._hover_anim.start()
            
            self._icon_size_anim.stop()
            self._icon_size_anim.setStartValue(self.iconSize())
            self._icon_size_anim.setEndValue(QSize(28, 28))
            self._icon_size_anim.start()
        return super().eventFilter(obj, event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._scale_anim.stop()
            self._scale_anim.setEndValue(0.97)
            self._scale_anim.start()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._scale_anim.stop()
            self._scale_anim.setEndValue(1.0)
            self._scale_anim.start()
        super().mouseReleaseEvent(event)

    def paintEvent(self, event):
        painter = QStylePainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        opt = QStyleOptionToolButton()
        self.initStyleOption(opt)
        
        # Suppress instant QSS hover/pressed states so our animations take over
        opt.state &= ~QStyle.StateFlag.State_MouseOver
        opt.state &= ~QStyle.StateFlag.State_Sunken

        if self._scale != 1.0:
            cx = self.width() / 2.0
            cy = self.height() / 2.0
            painter.translate(cx, cy)
            painter.scale(self._scale, self._scale)
            painter.translate(-cx, -cy)

        # Draw base card
        painter.drawComplexControl(QStyle.ComplexControl.CC_ToolButton, opt)
        
        # Inner mint glow on hover
        if self._hover_blend > 0:
            from src.ui.themes.tokens import RADIUS, accent_color
            
            overlay_color = QColor(accent_color(self._theme_name))
            overlay_alpha = int(self._hover_blend * 20) # Subtle 20 max alpha
            overlay_color.setAlpha(overlay_alpha)
            
            path = QPainterPath()
            path.addRoundedRect(QRectF(self.rect()), RADIUS["md"], RADIUS["md"])
            
            painter.fillPath(path, overlay_color)


class MintTextInput(QLineEdit):
    """
    A text input that adds a soft brand-tinted focus glow and custom-painted border.
    """
    def __init__(self, theme_name: str = "mint_light", parent=None):
        super().__init__(parent)
        self._theme_name = theme_name
        self._is_focused = False

        self._glow = QGraphicsDropShadowEffect(self)
        self._glow.setBlurRadius(12)
        self._glow.setXOffset(0)
        self._glow.setYOffset(0)
        
        self._glow_color = QColor(status_color(self._theme_name, "online"))
        self._glow_color.setAlpha(0)
        self._glow.setColor(self._glow_color)
        
        self.setGraphicsEffect(self._glow)

        self._glow_anim = QVariantAnimation(self)
        self._glow_anim.setDuration(150)
        self._glow_anim.valueChanged.connect(self._update_glow_alpha)

    def _update_glow_alpha(self, alpha: int):
        self._glow_color.setAlpha(alpha)
        self._glow.setColor(self._glow_color)

    def focusInEvent(self, event: QFocusEvent):
        super().focusInEvent(event)
        self._is_focused = True
        self._glow_anim.stop()
        self._glow_anim.setStartValue(self._glow_color.alpha())
        self._glow_anim.setEndValue(80)
        self._glow_anim.start()
        self.update()

    def focusOutEvent(self, event: QFocusEvent):
        super().focusOutEvent(event)
        self._is_focused = False
        self._glow_anim.stop()
        self._glow_anim.setStartValue(self._glow_color.alpha())
        self._glow_anim.setEndValue(0)
        self._glow_anim.start()
        self.update()

    # Note: No paintEvent override. We let QSS render the background and border radius.


class MintDoubleSpinBox(QDoubleSpinBox):
    """
    A double spinbox that adds a soft brand-tinted focus glow and custom-painted border.
    """
    def __init__(self, theme_name: str = "mint_light", parent=None):
        super().__init__(parent)
        self._theme_name = theme_name
        self._is_focused = False

        self._glow = QGraphicsDropShadowEffect(self)
        self._glow.setBlurRadius(12)
        self._glow.setXOffset(0)
        self._glow.setYOffset(0)
        
        self._glow_color = QColor(status_color(self._theme_name, "online"))
        self._glow_color.setAlpha(0)
        self._glow.setColor(self._glow_color)
        
        self.setGraphicsEffect(self._glow)

        self._glow_anim = QVariantAnimation(self)
        self._glow_anim.setDuration(150)
        self._glow_anim.valueChanged.connect(self._update_glow_alpha)

    def _update_glow_alpha(self, alpha: int):
        self._glow_color.setAlpha(alpha)
        self._glow.setColor(self._glow_color)

    def focusInEvent(self, event: QFocusEvent):
        super().focusInEvent(event)
        self._is_focused = True
        self._glow_anim.stop()
        self._glow_anim.setStartValue(self._glow_color.alpha())
        self._glow_anim.setEndValue(80)
        self._glow_anim.start()
        self.update()

    def focusOutEvent(self, event: QFocusEvent):
        super().focusOutEvent(event)
        self._is_focused = False
        self._glow_anim.stop()
        self._glow_anim.setStartValue(self._glow_color.alpha())
        self._glow_anim.setEndValue(0)
        self._glow_anim.start()
        self.update()

    # Note: No paintEvent override. We let QSS render the background and border radius.


class EmptyStateWidget(QWidget):
    """
    Displays an empty state with a centered decorative icon (leaf or grass)
    and a localized message. Used to avoid bare white rectangles in tables/lists.
    """
    def __init__(self, message: str, theme_name: str = "mint_light", icon_name: str = "leaf", parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(16)

        # Muted icon tint
        color = icon_color(theme_name, role="muted")
        
        self.icon_label = QLabel()
        self.icon_label.setPixmap(get_icon(icon_name, color).pixmap(QSize(48, 48)))
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.text_label = QLabel(message)
        self.text_label.setObjectName("subtitleLabel") # Use muted text styling
        self.text_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.text_label.setWordWrap(True)

        layout.addStretch()
        layout.addWidget(self.icon_label)
        layout.addWidget(self.text_label)
        layout.addStretch()

    def set_message(self, message: str):
        self.text_label.setText(message)


class MintCheckbox(QCheckBox):
    """
    A custom-painted checkbox with a gradient fill and scale-in checkmark animation.
    """
    def __init__(self, text: str = "", theme_name: str = "mint_light", parent=None):
        super().__init__(text, parent)
        self._theme_name = theme_name
        self._check_scale = 0.0
        self._check_alpha = 0
        
        self._anim = QVariantAnimation(self)
        self._anim.setDuration(120)
        self._anim.valueChanged.connect(self._update_anim)
        
        self.toggled.connect(self._on_toggled)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        # initialize if checked
        if self.isChecked():
            self._check_scale = 1.0
            self._check_alpha = 255

    def _update_anim(self, val):
        self._check_scale = val
        self._check_alpha = int(val * 255)
        self.update()

    def _on_toggled(self, checked):
        self._anim.stop()
        if checked:
            self._anim.setStartValue(self._check_scale)
            self._anim.setEndValue(1.0)
        else:
            self._anim.setStartValue(self._check_scale)
            self._anim.setEndValue(0.0)
        self._anim.start()

    def sizeHint(self):
        fm = self.fontMetrics()
        w = 18 + 8 + fm.horizontalAdvance(self.text())
        h = max(18, fm.height()) + 8
        return QSize(w, h)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        from src.ui.themes.tokens import PALETTES, RADIUS, mint_gradient
        palette = PALETTES.get(self._theme_name, PALETTES["mint_light"])
        
        box_size = 18
        box_rect = QRectF(0, (self.height() - box_size) / 2.0, box_size, box_size)
        
        # Draw box background
        if self.isChecked() or self._check_scale > 0:
            c1, c2 = mint_gradient(self._theme_name)
            grad = QLinearGradient(box_rect.topLeft(), box_rect.bottomRight())
            grad.setColorAt(0.0, QColor(c1))
            grad.setColorAt(1.0, QColor(c2))
            
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(grad)
            painter.drawRoundedRect(box_rect, RADIUS["xs"], RADIUS["xs"])
        else:
            border_color = QColor(palette["@BORDER@"])
            if self.underMouse():
                border_color = QColor(palette["@BORDER_HOVER@"])
            painter.setPen(QPen(border_color, 1.5))
            painter.setBrush(QColor(palette["@SURFACE@"]))
            painter.drawRoundedRect(box_rect, RADIUS["xs"], RADIUS["xs"])
            
        # Draw checkmark
        if self._check_scale > 0:
            painter.save()
            cx, cy = box_rect.center().x(), box_rect.center().y()
            painter.translate(cx, cy)
            painter.scale(self._check_scale, self._check_scale)
            painter.translate(-cx, -cy)
            
            check_path = QPainterPath()
            check_path.moveTo(box_rect.left() + 4, box_rect.top() + 9)
            check_path.lineTo(box_rect.left() + 8, box_rect.top() + 13)
            check_path.lineTo(box_rect.left() + 14, box_rect.top() + 5)
            
            check_color = QColor(255, 255, 255, self._check_alpha)
            pen = QPen(check_color, 2.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawPath(check_path)
            painter.restore()
            
        # Draw text
        text_rect = QRectF(box_size + 8, 0, self.width() - box_size - 8, self.height())
        painter.setPen(QColor(palette["@TEXT@"]))
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, self.text())


class MintIconButton(QPushButton):
    """
    A compact icon-only button for toolbars.
    """
    def __init__(self, icon_name: str, theme_name: str = "mint_light", parent=None):
        super().__init__(parent)
        self._theme_name = theme_name
        self.setObjectName("iconButton")
        self.setIcon(get_icon(icon_name, icon_color(theme_name, "default")))
        self.setIconSize(QSize(18, 18))
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(34, 34)
        
        self._scale = 1.0
        self._scale_anim = QPropertyAnimation(self, b"scale_factor")
        self._scale_anim.setDuration(80)

    @pyqtProperty(float)
    def scale_factor(self):
        return self._scale

    @scale_factor.setter
    def scale_factor(self, value):
        self._scale = value
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._scale_anim.stop()
            self._scale_anim.setEndValue(0.92)
            self._scale_anim.start()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._scale_anim.stop()
            self._scale_anim.setEndValue(1.0)
            self._scale_anim.start()
        super().mouseReleaseEvent(event)

    def paintEvent(self, event):
        painter = QStylePainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        opt = QStyleOptionButton()
        self.initStyleOption(opt)

        if self._scale != 1.0:
            cx = self.width() / 2.0
            cy = self.height() / 2.0
            painter.translate(cx, cy)
            painter.scale(self._scale, self._scale)
            painter.translate(-cx, -cy)

        painter.drawControl(QStyle.ControlElement.CE_PushButton, opt)


class Breadcrumb(QWidget):
    """
    Parses a path string into clickable segments.
    Emits path_clicked(str) with the resolved path.
    """
    path_clicked = pyqtSignal(str)
    
    def __init__(self, theme_name: str = "mint_light", parent=None):
        super().__init__(parent)
        self._theme_name = theme_name
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(4, 4, 4, 4)
        self._layout.setSpacing(2)
        self.setObjectName("pathLabel") # Re-use the background styling from QSS
        self.set_path("/")
        
    def set_path(self, path: str):
        # clear existing
        while self._layout.count():
            item = self._layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
                
        # Split path
        parts = [p for p in path.split("/") if p]
        
        # Add root
        btn = QToolButton()
        btn.setObjectName("breadcrumbSegment")
        btn.setIcon(get_icon("home", icon_color(self._theme_name, "default")))
        btn.clicked.connect(lambda: self.path_clicked.emit("/"))
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._layout.addWidget(btn)
        
        current_path = ""
        for part in parts:
            current_path += "/" + part
            
            sep = QLabel("/")
            sep.setStyleSheet(f"color: {icon_color(self._theme_name, 'muted')}; font-size: 13px;")
            self._layout.addWidget(sep)
            
            btn = QToolButton()
            btn.setObjectName("breadcrumbSegment")
            btn.setText(part)
            # Default argument hack to capture current loop var in lambda
            btn.clicked.connect(lambda checked, p=current_path: self.path_clicked.emit(p))
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self._layout.addWidget(btn)
            
        self._layout.addStretch()


class MintStepper(QWidget):
    """
    A custom stepper widget bypassing QDoubleSpinBox.
    """
    valueChanged = pyqtSignal(float)

    def __init__(self, theme_name: str = "mint_light", parent=None):
        super().__init__(parent)
        self._theme_name = theme_name
        self._val = 0.0
        self._min = 0.0
        self._max = 100.0
        self._step = 1.0
        self._suffix = ""

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self.minus_btn = MintIconButton("minus", theme_name)
        self.minus_btn.clicked.connect(self._decrement)
        
        self.input_field = MintTextInput(theme_name)
        self.input_field.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.input_field.editingFinished.connect(self._on_edit)
        # Fix width so it doesn't jump around
        self.input_field.setFixedWidth(64)

        self.plus_btn = MintIconButton("plus", theme_name)
        self.plus_btn.clicked.connect(self._increment)

        layout.addWidget(self.minus_btn)
        layout.addWidget(self.input_field)
        layout.addWidget(self.plus_btn)
        
        self._update_display()

    def setRange(self, minimum: float, maximum: float):
        self._min = minimum
        self._max = maximum
        self._update_display()

    def setSingleStep(self, step: float):
        self._step = step

    def setSuffix(self, suffix: str):
        self._suffix = suffix
        self._update_display()

    def value(self) -> float:
        return self._val

    def setValue(self, val: float):
        self._val = max(self._min, min(self._max, val))
        self._update_display()
        self.valueChanged.emit(self._val)

    def _decrement(self):
        self.setValue(self._val - self._step)

    def _increment(self):
        self.setValue(self._val + self._step)

    def _on_edit(self):
        text = self.input_field.text().replace(self._suffix, "").strip()
        try:
            val = float(text)
            self.setValue(val)
        except ValueError:
            self._update_display() # Revert to valid

    def _update_display(self):
        # Format to 1 decimal place if float, else int
        if self._step >= 1.0 and self._val.is_integer():
            text = f"{int(self._val)}{self._suffix}"
        else:
            text = f"{self._val:.1f}{self._suffix}"
        self.input_field.setText(text)


class MintDropdown(QWidget):
    """
    A custom dropdown bypassing QComboBox native styling limitations.
    """
    currentIndexChanged = pyqtSignal(int)

    def __init__(self, theme_name: str = "mint_light", parent=None):
        super().__init__(parent)
        self._theme_name = theme_name
        self._items = []
        self._current_index = -1
        
        self.setObjectName("pathLabel") # Reuses the nice border-radius background
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 6, 8, 6)
        layout.setSpacing(8)

        self.label = QLabel("")
        self.label.setStyleSheet(f"color: {icon_color(theme_name, 'default')}; font-size: 13px;")
        
        self.icon = QLabel()
        self.icon.setPixmap(get_icon("chevron-down", icon_color(theme_name, "muted")).pixmap(QSize(16, 16)))
        
        layout.addWidget(self.label, 1)
        layout.addWidget(self.icon)
        
        self.setMinimumWidth(120)

    def addItem(self, text: str, userData=None):
        self._items.append({"text": text, "data": userData})
        if self._current_index == -1:
            self.setCurrentIndex(0)

    def clear(self):
        self._items.clear()
        self._current_index = -1
        self.label.setText("")

    def findData(self, data) -> int:
        for i, item in enumerate(self._items):
            if item["data"] == data:
                return i
        return -1

    def currentData(self):
        if 0 <= self._current_index < len(self._items):
            return self._items[self._current_index]["data"]
        return None

    def setCurrentIndex(self, index: int):
        if 0 <= index < len(self._items):
            self._current_index = index
            self.label.setText(self._items[index]["text"])
            self.currentIndexChanged.emit(index)

    def blockSignals(self, b: bool):
        return super().blockSignals(b)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._show_popup()
        super().mousePressEvent(event)

    def _show_popup(self):
        if not self._items:
            return
            
        from PyQt6.QtWidgets import QMenu
        menu = QMenu(self)
        from src.ui.themes.tokens import PALETTES
        palette = PALETTES.get(self._theme_name, PALETTES["mint_light"])
        
        menu.setStyleSheet(f"""
            QMenu {{
                background-color: {palette['@SURFACE@']};
                border: 1px solid {palette['@BORDER@']};
                border-radius: 8px;
                padding: 4px;
            }}
            QMenu::item {{
                padding: 6px 24px 6px 12px;
                border-radius: 4px;
                color: {palette['@TEXT@']};
                font-size: 13px;
            }}
            QMenu::item:selected {{
                background-color: {palette['@SURFACE_HOVER@']};
            }}
        """)
        
        # Disable QMenu's native shadow/border if possible, using Qt flags
        menu.setWindowFlags(menu.windowFlags() | Qt.WindowType.FramelessWindowHint | Qt.WindowType.NoDropShadowWindowHint)
        menu.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        actions = []
        for i, item_data in enumerate(self._items):
            act = menu.addAction(item_data["text"])
            act.setData(i)
            actions.append(act)

        # Show below the widget
        pos = self.mapToGlobal(self.rect().bottomLeft())
        # Add a tiny gap
        pos.setY(pos.y() + 4)
        
        action = menu.exec(pos)
        if action:
            self.setCurrentIndex(action.data())
