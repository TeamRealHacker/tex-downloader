"""Dot pattern background — paints a tiled dot grid.

Adapts to the current theme: white dots on dark backgrounds, dark dots
on light backgrounds. Use as a sibling stacked behind the content. It
paints the dot grid in its own ``paintEvent`` and ignores all mouse
events so it never steals focus.
"""
from __future__ import annotations

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QColor, QPainter, QPixmap
from PySide6.QtWidgets import QWidget

TILE = 24
DOT_R = 1
DOT_OFFSET = 2


def _make_dot_tile(color: QColor) -> QPixmap:
    """Build the 24x24 tile once and cache it for fast repeated painting."""
    pm = QPixmap(TILE, TILE)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(color)
    p.drawEllipse(DOT_OFFSET - DOT_R, DOT_OFFSET - DOT_R, DOT_R * 2, DOT_R * 2)
    p.end()
    return pm


class DotBackground(QWidget):
    """A borderless widget that paints a tiled dot grid on its surface.

    Call ``set_theme(is_dark)`` to swap between white (dark bg) and
    dark (light bg) dot colors.
    """

    def __init__(self, parent: QWidget | None = None, is_dark: bool = True,
                 spacing: int = TILE):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self._spacing = spacing
        self._is_dark = is_dark
        self._rebuild_tile()

    def set_theme(self, is_dark: bool) -> None:
        if self._is_dark == is_dark:
            return
        self._is_dark = is_dark
        self._rebuild_tile()
        self.update()

    def _rebuild_tile(self) -> None:
        if self._is_dark:
            # White dots on dark bg — low alpha for subtlety.
            c = QColor(255, 255, 255, 45)
        else:
            # Dark dots on light bg — medium alpha for contrast.
            c = QColor(0, 0, 0, 30)
        self._tile = _make_dot_tile(c)

    def sizeHint(self) -> QSize:
        return QSize(TILE * 20, TILE * 12)

    def paintEvent(self, _e) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.setOpacity(1.0)
        p.drawTiledPixmap(self.rect(), self._tile)
        p.end()
