"""Top bar: ● Tex (inline) · state pill · clock. 40px."""
from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QSizePolicy


class TopBar(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("TopBar")
        self.setFixedHeight(40)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(20, 0, 20, 0)
        lay.setSpacing(12)

        # Brand: red dot + Tex
        self._brand_dot = QLabel("\u2022")
        self._brand_dot.setStyleSheet(
            f"color: #D7191A; font-size: 16px; font-weight: 700;"
            f" background: transparent; padding: 0px 4px 0px 0px;"
        )
        self._title = QLabel("Tex")
        self._title.setObjectName("TopBrand")
        lay.addWidget(self._brand_dot, 0, Qt.AlignmentFlag.AlignVCenter)
        lay.addWidget(self._title, 0, Qt.AlignmentFlag.AlignVCenter)

        lay.addStretch(1)

        # State pill
        self._pill = QFrame()
        self._pill.setObjectName("StatePill")
        self._pill.setProperty("active", False)
        pill_lay = QHBoxLayout(self._pill)
        pill_lay.setContentsMargins(10, 0, 12, 0)
        pill_lay.setSpacing(6)
        self._pill_dot = QLabel("")
        self._pill_dot.setObjectName("DotSm")
        self._pill_dot.setFixedSize(6, 6)
        self._pill_text = QLabel("READY")
        self._pill_text.setObjectName("StatePillText")
        self._pill_text.setProperty("active", False)
        pill_lay.addWidget(self._pill_dot)
        pill_lay.addWidget(self._pill_text)
        lay.addWidget(self._pill)

        # Clock
        self._clock = QLabel("00:00")
        self._clock.setObjectName("TopClock")
        self._clock.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        lay.addWidget(self._clock)

        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._tick)
        self._timer.start()
        self._tick()

    def _tick(self) -> None:
        self._clock.setText(datetime.now().strftime("%H:%M"))

    def set_state(self, state: str) -> None:
        """state: 'ready' | 'fetching' | 'downloading' | 'error' | 'paused'"""
        mapping = {
            "ready":       ("READY",       False, "DotDim"),
            "fetching":    ("FETCHING",    True,  "DotSm"),
            "downloading": ("DOWNLOADING", True,  "DotSm"),
            "error":       ("ERROR",       True,  "DotSm"),
            "paused":      ("PAUSED",      False, "DotDim"),
        }
        text, active, dot_obj = mapping.get(state, ("READY", False, "DotDim"))
        self._pill_text.setText(text)
        self._pill_text.setProperty("active", active)
        self._pill.setProperty("active", active)
        self._pill_dot.setObjectName(dot_obj)
        for w in (self._pill, self._pill_text, self._pill_dot):
            w.style().unpolish(w)
            w.style().polish(w)
        # Pulse brand dot
        if state in ("downloading", "fetching"):
            from PySide6.QtGui import QColor
            from PySide6.QtCore import QPropertyAnimation
            from PySide6.QtWidgets import QGraphicsColorizeEffect
            eff = self._brand_dot.graphicsEffect()
            if not isinstance(eff, QGraphicsColorizeEffect):
                eff = QGraphicsColorizeEffect(self._brand_dot)
                self._brand_dot.setGraphicsEffect(eff)
            eff.setColor(QColor("#FFFFFF"))
            a = QPropertyAnimation(eff, b"strength", self._brand_dot)
            a.setDuration(1100)
            a.setStartValue(0.0)
            a.setKeyValueAt(0.5, 0.6)
            a.setEndValue(0.0)
            a.setLoopCount(-1)
            a.start()
        else:
            self._brand_dot.setGraphicsEffect(None)
            self._brand_dot.setStyleSheet(
                f"color: #D7191A; font-size: 16px; font-weight: 700;"
                f" background: transparent; padding: 0px 4px 0px 0px;"
            )
