"""Bottom dock: thin, 40px. Brand + queue + ffmpeg only."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout

from ui.widgets.dot_matrix import TEX_GLYPH_X, DotMatrix
from ui.widgets.settings_panel import APP_VERSION


class _Item(QFrame):
    def __init__(self, label: str, parent=None):
        super().__init__(parent)
        self.setObjectName("DockItem")

        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)
        lay.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        col = QVBoxLayout()
        col.setSpacing(0)
        self._label = QLabel(label)
        self._label.setObjectName("DockLabel")
        col.addWidget(self._label)
        self._value = QLabel("\u2014")
        self._value.setObjectName("DockValue")
        col.addWidget(self._value)
        lay.addLayout(col)

    def set_value(self, text: str, accent: bool = False) -> None:
        self._value.setText(text)
        self._value.setObjectName("DockValueAccent" if accent else "DockValue")
        self._value.style().unpolish(self._value)
        self._value.style().polish(self._value)


class Dock(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("Dock")
        self.setFixedHeight(40)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(20, 0, 20, 0)
        lay.setSpacing(28)
        lay.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        # Brand
        brand = QHBoxLayout()
        brand.setSpacing(8)
        brand.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        art = DotMatrix(TEX_GLYPH_X, pixel=2, gap=1, on_color="#D7191A")
        brand.addWidget(art, 0, Qt.AlignmentFlag.AlignVCenter)
        ver = QLabel(f"TEX  v{APP_VERSION}")
        ver.setObjectName("DockLabel")
        brand.addWidget(ver)
        lay.addLayout(brand)

        # Hairline separator
        sep = QFrame()
        sep.setObjectName("ThinDivider")
        sep.setFixedWidth(1)
        sep.setFixedHeight(18)
        lay.addWidget(sep, 0, Qt.AlignmentFlag.AlignVCenter)

        # Queue
        self.item_queue = _Item("QUEUE")
        lay.addWidget(self.item_queue)

        lay.addStretch(1)

        # FFmpeg
        self.item_ff = _Item("FFMPEG")
        lay.addWidget(self.item_ff)

    def set_queue(self, active: int, total: int) -> None:
        self.item_queue.set_value(f"{active} / {total}", accent=(active > 0))

    def set_ffmpeg(self, path: str | None) -> None:
        if path:
            self.item_ff.set_value(Path(path).name)
        else:
            self.item_ff.set_value("MISSING")
