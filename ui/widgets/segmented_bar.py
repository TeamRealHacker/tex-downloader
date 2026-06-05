"""Segmented progress bar: visual dot-matrix style progress.

Renders N small rectangular segments — filled are red, rest are faint gray.
Uses a single ``QPainter`` call per paint and pre-computes the segment
geometry once per resize.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QWidget


class SegmentedBar(QWidget):
    """A bar made of N square segments — filled segments are red, rest are faint."""

    # Class-level cached colors (avoid re-creating on every paint).
    _ON = QColor("#D7191A")
    _OFF = QColor("#2A2A2A")

    def __init__(self, segments: int = 40, height: int = 8, parent=None):
        super().__init__(parent)
        self._segments = max(1, segments)
        self._fill = 0.0
        self.setFixedHeight(height)

    def set_fill(self, pct: float) -> None:
        self._fill = max(0.0, min(1.0, pct))
        self.update()

    def paintEvent(self, _e) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        w, h = self.width(), self.height()
        gap = 2
        seg_w = max(1, (w - (self._segments - 1) * gap) // self._segments)
        seg_h = h
        on_n = int(self._segments * self._fill)
        if on_n:
            p.fillRect(0, 0, on_n * (seg_w + gap) - gap, seg_h, self._ON)
        if on_n < self._segments:
            p.fillRect(on_n * (seg_w + gap), 0,
                       (self._segments - on_n) * (seg_w + gap) - gap, seg_h, self._OFF)
