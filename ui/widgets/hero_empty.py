"""Hero empty state: tiny dot, thin headline, kbd row. iOS-style minimal."""
from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget


class _Dot(QWidget):
    """A tiny red dot that softly breathes (alpha pulse only)."""
    def __init__(self, on_color: str = "#D7191A", parent=None):
        super().__init__(parent)
        self._color = QColor(on_color)
        self._alpha = 1.0
        self._going_up = False
        self.setFixedSize(10, 10)

        self._timer = QTimer(self)
        self._timer.setInterval(60)
        self._timer.timeout.connect(self._tick)
        self._timer.start()

    def _tick(self) -> None:
        if self._going_up:
            self._alpha += 0.03
            if self._alpha >= 1.0:
                self._alpha = 1.0
                self._going_up = False
        else:
            self._alpha -= 0.03
            if self._alpha <= 0.4:
                self._alpha = 0.4
                self._going_up = True
        self.update()

    def paintEvent(self, _e) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        c = QColor(self._color)
        c.setAlphaF(self._alpha)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(c)
        p.drawEllipse(0, 0, self.width(), self.height())


class HeroEmpty(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("HeroEmpty")

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(10)
        lay.setAlignment(Qt.AlignmentFlag.AlignCenter)

        wrap = QHBoxLayout()
        wrap.setAlignment(Qt.AlignmentFlag.AlignCenter)
        wrap.setSpacing(8)
        self.dot = _Dot()
        wrap.addWidget(self.dot)
        self.title_lbl = QLabel("Paste a link to begin")
        self.title_lbl.setObjectName("HeroTitle")
        wrap.addWidget(self.title_lbl)
        lay.addLayout(wrap)

        kb = QHBoxLayout()
        kb.setSpacing(6)
        kb.setAlignment(Qt.AlignmentFlag.AlignCenter)

        def kbd(text: str) -> QLabel:
            l = QLabel(text)
            l.setObjectName("HeroKbd")
            return l

        kb.addWidget(kbd("Ctrl V"))
        or_lbl = QLabel("or drop a URL")
        or_lbl.setObjectName("HeroSub")
        kb.addWidget(or_lbl)
        lay.addLayout(kb)

    def setVisible(self, v: bool) -> None:
        super().setVisible(v)
        # Pause the dot timer when hidden so we don't waste CPU cycles.
        if v:
            self.dot._timer.start()
        else:
            self.dot._timer.stop()
