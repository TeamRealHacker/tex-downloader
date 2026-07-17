"""Ring/circle stat widget: animated ring with center percentage + label."""
from __future__ import annotations

from PySide6.QtCore import (
    QEasingCurve, QPropertyAnimation, QRectF, QSize, Qt, QTimer, Signal,
)
from PySide6.QtGui import QBrush, QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget


class _Ring(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(QSize(120, 120))
        self._pct = 0.0
        self._target = 0.0
        self._anim = QPropertyAnimation(self, b"pct", self)
        self._anim.setDuration(700)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._accent = QColor("#D7191A")
        self._track = QColor("#2A2A2A")
        self._fg = QColor("#FFFFFF")
        self._caption = ""
        self._unit = "%"

    def get_pct(self) -> float:
        return self._pct

    def set_pct(self, v: float) -> None:
        self._pct = max(0.0, min(1.0, v))
        self.update()

    pct = property(get_pct, set_pct)

    def set_target(self, v: float, anim: bool = True) -> None:
        v = max(0.0, min(1.0, v))
        self._target = v
        if anim:
            self._anim.stop()
            self._anim.setStartValue(self._pct)
            self._anim.setEndValue(v)
            self._anim.start()
        else:
            self._pct = v
            self.update()

    def set_caption(self, text: str) -> None:
        self._caption = text
        self.update()

    def set_unit(self, text: str) -> None:
        self._unit = text
        self.update()

    def paintEvent(self, _e) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        w, h = self.width(), self.height()
        side = min(w, h) - 8
        r = QRectF((w - side) / 2, (h - side) / 2, side, side)
        margin = side * 0.12
        rr = QRectF(r.left() + margin, r.top() + margin,
                    r.width() - margin * 2, r.height() - margin * 2)

        pen_w = max(6.0, side * 0.07)
        # Track
        pen = QPen(self._track)
        pen.setWidthF(pen_w)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        p.drawArc(rr, 0, 360 * 16)
        # Accent
        if self._pct > 0:
            pen.setColor(self._accent)
            p.setPen(pen)
            span = -int(360 * 16 * self._pct)
            p.drawArc(rr, 90 * 16, span)

        # Center text
        pct_text = f"{int(self._pct * 100)}{self._unit}"
        font = QFont(self.font())
        font.setPixelSize(int(side * 0.22))
        font.setBold(True)
        p.setFont(font)
        p.setPen(QPen(self._fg))
        p.drawText(rr, Qt.AlignmentFlag.AlignCenter, pct_text)

        if self._caption:
            cap = QFont(self.font())
            cap.setPixelSize(int(side * 0.10))
            cap.setBold(True)
            p.setFont(cap)
            p.setPen(QPen(self._accent))
            cap_rect = QRectF(rr.left(), rr.bottom() - side * 0.22, rr.width(), side * 0.18)
            p.drawText(cap_rect, Qt.AlignmentFlag.AlignCenter, self._caption)


class RingStat(QFrame):
    """Bento tile: ring with center percentage, title above."""
    def __init__(self, title: str = "STAT", parent=None):
        super().__init__(parent)
        self.setObjectName("CardBright")

        lay = QVBoxLayout(self)
        lay.setContentsMargins(18, 18, 18, 18)
        lay.setSpacing(8)

        self.title_lbl = QLabel(title)
        self.title_lbl.setObjectName("Status")
        lay.addWidget(self.title_lbl)

        ring_row = QVBoxLayout()
        ring_row.setSpacing(4)
        ring_row.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.ring = _Ring()
        ring_row.addWidget(self.ring, 0, Qt.AlignmentFlag.AlignCenter)
        lay.addLayout(ring_row)

        lay.addStretch(1)

        self._subtitle = QLabel("")
        self._subtitle.setObjectName("Meta")
        self._subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(self._subtitle)

    def set_value(self, pct: float, caption: str = "", subtitle: str = "",
                  unit: str = "%", anim: bool = True) -> None:
        self.ring.set_target(pct, anim=anim)
        if caption:
            self.ring.set_caption(caption)
        if unit != "%":
            self.ring.set_unit(unit)
        self._subtitle.setText(subtitle)

    def set_subtitle(self, text: str) -> None:
        self._subtitle.setText(text)

    def set_title(self, text: str) -> None:
        self.title_lbl.setText(text)
