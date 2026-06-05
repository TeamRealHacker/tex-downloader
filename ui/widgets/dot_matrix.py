"""Dot-matrix art widget: render a 1-bit pixel art as a grid of dots.

Used to mimic the Nothing OS pixelated glyphs.
"""
from __future__ import annotations

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QFrame, QGridLayout, QLabel, QWidget


# 5x5 mini pixel art "T" (TEX logo monogram). 1 = on, 0 = off.
TEX_GLYPH_T = [
    "11111",
    "00100",
    "00100",
    "00100",
    "00100",
]

# 5x5 mini pixel art "X"
TEX_GLYPH_X = [
    "10001",
    "01010",
    "00100",
    "01010",
    "10001",
]

# 5x5 dot-matrix arrow down
GLYPH_DOWN = [
    "00000",
    "00000",
    "00100",
    "01110",
    "00100",
]

# 5x5 dot-matrix arrow up
GLYPH_UP = [
    "00100",
    "01110",
    "00100",
    "00000",
    "00000",
]

# 5x5 dot-matrix play
GLYPH_PLAY = [
    "00010",
    "00110",
    "01110",
    "00110",
    "00010",
]

# 5x5 dot-matrix music note
GLYPH_MUSIC = [
    "00100",
    "00110",
    "00100",
    "10101",
    "01110",
]

# 5x5 dot-matrix bolt
GLYPH_BOLT = [
    "00100",
    "00110",
    "11110",
    "00110",
    "11100",
]

# 5x5 dot-matrix clipboard
GLYPH_CLIP = [
    "01110",
    "01010",
    "11111",
    "10001",
    "11111",
]

# 5x5 dot-matrix folder
GLYPH_FOLDER = [
    "00000",
    "00110",
    "01111",
    "11111",
    "11111",
]

# 5x5 dot-matrix check
GLYPH_CHECK = [
    "00000",
    "00001",
    "00011",
    "10110",
    "01100",
]

# 5x5 dot-matrix cross
GLYPH_CROSS = [
    "10001",
    "01010",
    "00100",
    "01010",
    "10001",
]

# 5x5 dot-matrix clock (filled)
GLYPH_CLOCK = [
    "01110",
    "11011",
    "11011",
    "11111",
    "01110",
]

# 5x5 dot-matrix download
GLYPH_DOWNLOAD = [
    "00100",
    "00100",
    "10101",
    "01110",
    "00010",
]

# 5x5 dot-matrix gear
GLYPH_GEAR = [
    "00100",
    "10101",
    "11011",
    "10101",
    "00100",
]

# 5x5 dot-matrix link/chain
GLYPH_LINK = [
    "00010",
    "00110",
    "11011",
    "01100",
    "00000",
]

# 5x5 dot-matrix storage/hard-drive
GLYPH_DRIVE = [
    "11111",
    "10001",
    "11111",
    "10101",
    "11111",
]

# 5x5 dot-matrix queue/lines
GLYPH_QUEUE = [
    "00000",
    "11011",
    "00000",
    "11011",
    "00000",
]

# 5x5 dot-matrix settings (sliders)
GLYPH_SLIDERS = [
    "11011",
    "10010",
    "11011",
    "10100",
    "11011",
]


class DotMatrix(QFrame):
    """Render a list of 0/1 strings as a grid of small square pixels."""
    def __init__(self, pattern: list[str], pixel: int = 6, gap: int = 2,
                 on_color: str = "#D7191A", off_color: str = "#2A2A2A",
                 parent=None):
        super().__init__(parent)
        self.setObjectName("DotMatrix")
        self._pattern = pattern
        self._pixel = pixel
        self._gap = gap
        self._on = on_color
        self._off = off_color
        self._build()
        self.setSizePolicy(self.sizePolicy().horizontalPolicy(),
                           self.sizePolicy().verticalPolicy())

    def _build(self) -> None:
        old = self.layout()
        if old is not None:
            while old.count():
                it = old.takeAt(0)
                w = it.widget()
                if w:
                    w.deleteLater()
            QWidget().setLayout(old)
        grid = QGridLayout(self)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(self._gap)
        grid.setVerticalSpacing(self._gap)
        rows = len(self._pattern)
        cols = max(len(r) for r in self._pattern)
        for r, row in enumerate(self._pattern):
            for c, ch in enumerate(row):
                lbl = QLabel("")
                if ch == "1":
                    lbl.setObjectName("PixelDot")
                else:
                    lbl.setObjectName("PixelDotOff")
                lbl.setFixedSize(self._pixel, self._pixel)
                grid.addWidget(lbl, r, c)
        self.setFixedSize(
            cols * self._pixel + (cols - 1) * self._gap,
            rows * self._pixel + (rows - 1) * self._gap,
        )

    def set_on_color(self, color: str) -> None:
        self._on = color
        self._recolor()

    def _recolor(self) -> None:
        grid = self.layout()
        for i in range(grid.count()):
            item = grid.itemAt(i)
            w = item.widget()
            if not w:
                continue
            obj = w.objectName()
            if obj == "PixelDot":
                w.setStyleSheet(f"background:{self._on}; border-radius:1px;")
            else:
                w.setStyleSheet(f"background:{self._off}; border-radius:1px;")

    def sizeHint(self) -> QSize:
        rows = len(self._pattern)
        cols = max(len(r) for r in self._pattern)
        return QSize(
            cols * self._pixel + (cols - 1) * self._gap,
            rows * self._pixel + (rows - 1) * self._gap,
        )
