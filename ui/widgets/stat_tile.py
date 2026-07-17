"""Compact stat tile: section label + huge value + sub-line + optional dot row."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget


class _Dot(QWidget):
    def __init__(self, on: bool = False, size: int = 8, parent=None):
        super().__init__(parent)
        self.setFixedSize(size + 2, size + 2)
        self._on = on
        self._size = size

    def set_on(self, on: bool) -> None:
        self._on = on
        self.update()

    def paintEvent(self, _e) -> None:
        from PySide6.QtGui import QColor, QPainter
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        c = QColor("#D7191A") if self._on else QColor("#2A2A2A")
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(c)
        p.drawEllipse(1, 1, self._size, self._size)


class StatTile(QFrame):
    """Bento tile: top label, big number, optional dot row, subtitle."""
    def __init__(self, title: str = "STAT", parent=None):
        super().__init__(parent)
        self.setObjectName("CardBright")

        lay = QVBoxLayout(self)
        lay.setContentsMargins(18, 18, 18, 18)
        lay.setSpacing(8)

        self.title_lbl = QLabel(title)
        self.title_lbl.setObjectName("Status")
        lay.addWidget(self.title_lbl)

        self.value_lbl = QLabel("0")
        self.value_lbl.setObjectName("NumBig")
        lay.addWidget(self.value_lbl)

        self._dot_row = QHBoxLayout()
        self._dot_row.setSpacing(4)
        self._dot_row.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self._dots: list[_Dot] = []
        lay.addLayout(self._dot_row)

        self._subtitle = QLabel("")
        self._subtitle.setObjectName("Meta")
        lay.addWidget(self._subtitle)
        lay.addStretch(1)

    def set_value(self, text: str) -> None:
        self.value_lbl.setText(text)

    def set_subtitle(self, text: str) -> None:
        self._subtitle.setText(text)

    def set_dots(self, total: int, on: int) -> None:
        while self._dot_row.count():
            it = self._dot_row.takeAt(0)
            w = it.widget()
            if w:
                w.deleteLater()
        self._dots.clear()
        for i in range(total):
            d = _Dot(i < on)
            self._dot_row.addWidget(d)
            self._dots.append(d)
        self._dot_row.addStretch(1)

    def set_title(self, text: str) -> None:
        self.title_lbl.setText(text)
