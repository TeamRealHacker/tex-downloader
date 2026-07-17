"""Queue bar: one row, segmented bar for slots, ghost buttons."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout

from ui.widgets.segmented_bar import SegmentedBar


class QueueBar(QFrame):
    cancel_all = Signal()
    clear_finished = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("Card")
        self._total = 1_000_000
        self._unlimited = True

        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 12, 14, 12)
        lay.setSpacing(8)

        # Title row
        title_row = QHBoxLayout()
        title_row.setSpacing(8)
        self.title_lbl = QLabel("QUEUE  \u00B7  ACTIVE DOWNLOADS")
        self.title_lbl.setObjectName("Section")
        title_row.addWidget(self.title_lbl)
        title_row.addStretch(1)
        self.active_lbl = QLabel("\u221E")
        self.active_lbl.setObjectName("NumMed")
        self.active_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        title_row.addWidget(self.active_lbl)
        lay.addLayout(title_row)

        # One single segmented bar — fills as the queue grows.
        self._bar = SegmentedBar(segments=20, height=6)
        lay.addWidget(self._bar)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        self.btn_clear = QPushButton("CLEAR FINISHED")
        self.btn_clear.setObjectName("Ghost")
        self.btn_clear.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_clear.clicked.connect(self.clear_finished.emit)
        self.btn_cancel = QPushButton("CANCEL ALL")
        self.btn_cancel.setObjectName("Ghost")
        self.btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_cancel.clicked.connect(self.cancel_all.emit)
        btn_row.addStretch(1)
        btn_row.addWidget(self.btn_clear)
        btn_row.addWidget(self.btn_cancel)
        lay.addLayout(btn_row)

        self.set_slots(0)  # 0 = unlimited

    def set_slots(self, n: int) -> None:
        # 0 / negative means unlimited — show ∞.
        self._unlimited = n <= 0
        self._total = 1_000_000 if self._unlimited else max(1, n)
        self._bar.set_fill(0.0)
        self.active_lbl.setText("\u221E" if self._unlimited else "0")

    def update_active(self, active: int, total: int) -> None:
        # Track whether the caller (queue) is unlimited. If the queue just
        # went to unlimited, refresh the label.
        unlimited = total >= 999_999
        if unlimited != self._unlimited:
            self._unlimited = unlimited
        # Don't show a "/N" denominator — the user wants unlimited and
        # the number itself is what matters.
        if self._unlimited:
            self.active_lbl.setText(f"{active}")
        else:
            self.active_lbl.setText(f"{active} / {total}")
        # Bar fills based on active vs total slots.
        if self._unlimited:
            # Capped at 100% — once 8+ are active the bar is full.
            self._bar.set_fill(min(1.0, active / 8.0))
        else:
            self._bar.set_fill(active / max(1, total))
