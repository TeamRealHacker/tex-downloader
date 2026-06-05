"""Splash / loading screen — centered dot + brand. Auto-dismiss."""
from __future__ import annotations

from PySide6.QtCore import QPropertyAnimation, QSize, Qt, QTimer
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QApplication, QFrame, QLabel, QVBoxLayout, QWidget


class _LoaderDot(QFrame):
    """Three pulsing dots — minimal."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("SplashLoader")
        self.setFixedSize(48, 16)
        self._phase = 0
        self._timer = QTimer(self)
        self._timer.setInterval(180)
        self._timer.timeout.connect(self._tick)
        self._timer.start()

    def _tick(self) -> None:
        self._phase = (self._phase + 1) % 3
        self.update()

    def paintEvent(self, e) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        for i in range(3):
            x = i * 16 + 4
            if i == self._phase:
                p.setBrush(QColor("#D7191A"))
            else:
                p.setBrush(QColor("#3A3A3A"))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(x, 4, 8, 8)


class Splash(QWidget):
    """Frameless splash that fills the screen with a centered brand."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.SplashScreen
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setObjectName("Splash")

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        lay.setAlignment(Qt.AlignmentFlag.AlignCenter)

        inner = QFrame()
        inner.setObjectName("SplashInner")
        il = QVBoxLayout(inner)
        il.setContentsMargins(0, 0, 0, 0)
        il.setSpacing(20)
        il.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Big red dot
        self._dot = QLabel("\u2022")
        self._dot.setObjectName("SplashDot")
        self._dot.setAlignment(Qt.AlignmentFlag.AlignCenter)
        il.addWidget(self._dot, 0, Qt.AlignmentFlag.AlignHCenter)

        # Brand
        self._brand = QLabel("Tex")
        self._brand.setObjectName("SplashBrand")
        self._brand.setAlignment(Qt.AlignmentFlag.AlignCenter)
        il.addWidget(self._brand, 0, Qt.AlignmentFlag.AlignHCenter)

        # Subtitle
        self._sub = QLabel("Loading\u2026")
        self._sub.setObjectName("SplashSub")
        self._sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        il.addWidget(self._sub, 0, Qt.AlignmentFlag.AlignHCenter)

        # Loader dots
        self._loader = _LoaderDot()
        il.addSpacing(4)
        il.addWidget(self._loader, 0, Qt.AlignmentFlag.AlignHCenter)

        lay.addWidget(inner, 0, Qt.AlignmentFlag.AlignCenter)

        # Fade in
        self.setWindowOpacity(0.0)
        self._fade_in = QPropertyAnimation(self, b"windowOpacity", self)
        self._fade_in.setDuration(220)
        self._fade_in.setStartValue(0.0)
        self._fade_in.setEndValue(1.0)

    def show(self) -> None:  # type: ignore[override]
        super().show()
        self._fade_in.start()

    def dismiss(self) -> None:
        """Fade out and close."""
        fade_out = QPropertyAnimation(self, b"windowOpacity", self)
        fade_out.setDuration(200)
        fade_out.setStartValue(self.windowOpacity())
        fade_out.setEndValue(0.0)
        fade_out.finished.connect(self.close)
        fade_out.start()
        self._fade_out = fade_out

    def set_status(self, text: str) -> None:
        self._sub.setText(text)
