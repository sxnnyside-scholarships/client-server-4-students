"""
Module: graph.py
────────────────
Purpose: Renders a live topological map of the server and its connected clients.

Architectural Role:
Acts as a pure data visualizer for the Server's Lab View mode. It isolates the
complex `QGraphicsScene` mathematics from the standard `server_window.py` layout logic.

Responsibilities:
- Draw the central Server node and dynamically position Client nodes in an orbit.
- Animate/Recalculate positions as clients connect and disconnect.

Expected Collaborators:
- `src.ui.server_window` (instantiates and updates this widget).
"""

import math

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QBrush, QColor, QPen, QPainter
from PyQt6.QtWidgets import (
    QGraphicsEllipseItem,
    QGraphicsLineItem,
    QGraphicsScene,
    QGraphicsTextItem,
    QGraphicsView,
    QVBoxLayout,
    QWidget,
)


from src.ui.themes.tokens import status_color, PALETTES


class ConnectionGraphWidget(QWidget):
    """
    Renders a live topological map of the server and its clients.

    Why it exists:
    A core goal of CS4S is visualizing abstract networking concepts. This widget
    proves to students that multiple clients are concurrently communicating with
    the central server without locking it up.

    Responsibilities:
    - Managing a `QGraphicsScene` and its item lifecycle (adding/removing shapes).
    - Trigonometric recalculation of node orbits.

    Non-Responsibilities (Anti-Goals):
    - It does NOT track the *state* of the connections, it simply draws what it is told to draw.
    """

    def __init__(self, theme_name: str = "mint_light"):
        super().__init__()
        self._theme_name = theme_name
        self._build_ui()
        self.clients = {}  # addr -> (node_item, line_item, text_item)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.scene = QGraphicsScene()
        self.scene.setSceneRect(-200, -200, 400, 400)

        self.view = QGraphicsView(self.scene)
        self.view.setRenderHint(QPainter.RenderHint.Antialiasing)
        # Disable scrollbars for a clean look
        self.view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.view.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        # Transparent background for the view
        self.view.setStyleSheet("background: transparent; border: none;")

        layout.addWidget(self.view)

        # Draw central server node
        self.server_node = QGraphicsEllipseItem(-20, -20, 40, 40)

        server_color = QColor(status_color(self._theme_name, "online"))
        self.server_node.setBrush(QBrush(server_color))

        # Determine appropriate border color (e.g. TEXT tone)
        palette = PALETTES.get(self._theme_name, PALETTES["mint_light"])
        border_color = QColor(palette["@BORDER@"])
        text_color = QColor(palette["@TEXT@"])

        self.server_node.setPen(QPen(border_color, 2))
        self.scene.addItem(self.server_node)

        label = QGraphicsTextItem("SERVER")
        label.setDefaultTextColor(text_color)
        label.setPos(-25, -45)
        self.scene.addItem(label)

    def add_client(self, addr: str):
        """
        Draws a new client node in orbit around the server.

        Args:
            addr: The string IP/Port identifier of the connecting client.

        Returns:
            None.

        Side Effects:
            Instantiates new `QGraphicsItem` objects and adds them to the scene.
            Triggers a recalculation of all existing node positions.

        Failure Behavior:
            If the address already exists in the graph, it is silently ignored.
        """
        if addr in self.clients:
            return

        # Determine position based on number of clients
        count = len(self.clients)
        angle = (count * (360 / max(1, count + 1))) * (math.pi / 180)
        radius = 120

        cx = radius * math.cos(angle)
        cy = radius * math.sin(angle)

        palette = PALETTES.get(self._theme_name, PALETTES["mint_light"])
        border_color = QColor(palette["@BORDER@"])
        text_color = QColor(palette["@TEXT@"])
        client_color = QColor(status_color(self._theme_name, "connecting"))

        # Draw connecting line
        line = QGraphicsLineItem(0, 0, cx, cy)
        line.setPen(QPen(border_color, 1, Qt.PenStyle.DashLine))
        self.scene.addItem(line)

        # Draw client node
        node = QGraphicsEllipseItem(cx - 15, cy - 15, 30, 30)
        node.setBrush(QBrush(client_color))
        node.setPen(QPen(border_color, 2))
        self.scene.addItem(node)

        # Draw label
        text = QGraphicsTextItem(addr.split(":")[1] if ":" in addr else addr)
        text.setDefaultTextColor(text_color)
        text.setPos(cx - 20, cy + 15)
        self.scene.addItem(text)

        self.clients[addr] = (node, line, text)
        self._recalculate_positions()

    def remove_client(self, addr: str):
        """
        Removes a client node and its connection line from the scene.

        Args:
            addr: The string IP/Port identifier of the disconnecting client.

        Returns:
            None.

        Side Effects:
            Removes `QGraphicsItem` objects from the scene memory.
            Triggers a recalculation of the remaining node orbits.

        Failure Behavior:
            If the address is not found in the graph, it is silently ignored.
        """
        if addr in self.clients:
            node, line, text = self.clients.pop(addr)
            self.scene.removeItem(node)
            self.scene.removeItem(line)
            self.scene.removeItem(text)
            self._recalculate_positions()

    def _recalculate_positions(self):
        """
        Re-distributes all client nodes evenly in a circular orbit around the center.

        Args:
            None.

        Returns:
            None.

        Side Effects:
            Mutates the X/Y coordinate positions of existing `QGraphicsItem` instances.

        Failure Behavior:
            None. Safely exits if there are zero clients.
        """
        if not self.clients:
            return

        angle_step = 360 / len(self.clients)
        radius = 120

        for i, (_addr, items) in enumerate(self.clients.items()):
            node, line, text = items
            angle = (i * angle_step) * (math.pi / 180)

            cx = radius * math.cos(angle)
            cy = radius * math.sin(angle)

            line.setLine(0, 0, cx, cy)
            node.setRect(cx - 15, cy - 15, 30, 30)
            text.setPos(cx - 20, cy + 15)
