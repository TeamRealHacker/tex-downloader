"""Active download hero card: big title, percentage, dot-matrix art, controls."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout

from ui.widgets.dot_matrix import TEX_GLYPH_X, DotMatrix


class ActiveDownloadHero(QFrame):
    """Big hero card shown above progress cards for the most-recent active download."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("CardAccent")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 20, 24, 20)
        outer.setSpacing(10)

        top = QHBoxLayout()
        top.setSpacing(14)
        top.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        # Dot-matrix glyph
        self._art = DotMatrix(TEX_GLYPH_X, pixel=5, gap=2, on_color="#FFFFFF")
        top.addWidget(self._art, 0, Qt.AlignmentFlag.AlignVCenter)

        # State + title
        col = QVBoxLayout()
        col.setSpacing(2)
        self.state_lbl = QLabel("●  DOWNLOADING")
        self.state_lbl.setObjectName("CardAccentText")
        col.addWidget(self.state_lbl)
        self.title_lbl = QLabel("\u2014")
        self.title_lbl.setStyleSheet("color:#000; font-size:18px; font-weight:700;")
        col.addWidget(self.title_lbl)
        top.addLayout(col, 1)

        # Right: percent
        self.pct_lbl = QLabel("0.0%")
        self.pct_lbl.setStyleSheet("color:#000; font-size:32px; font-weight:700;")
        self.pct_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        top.addWidget(self.pct_lbl)

        outer.addLayout(top)

        # Meta row
        self.meta_lbl = QLabel("\u2014")
        self.meta_lbl.setStyleSheet("color:#000; font-size:10px; font-weight:700; letter-spacing:2px;")
        outer.addWidget(self.meta_lbl)

        self.setVisible(False)

    def set_info(self, title: str, meta: str, pct: float = 0.0) -> None:
        self.title_lbl.setText(title[:80])
        self.meta_lbl.setText(meta.upper())
        self.pct_lbl.setText(f"{pct:5.1f}%")
        self.setVisible(True)

    def update_pct(self, pct: float) -> None:
        self.pct_lbl.setText(f"{pct:5.1f}%")
