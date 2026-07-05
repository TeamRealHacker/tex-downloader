"""Custom title bar — replaces Windows chrome. Frameless window.

36px tall. Left: brand + drag. Center: state pill. Right: − □ × and a
folder button that opens the user's save directory. Mixed case, no
terminal feel. System sans for body. All icons are hand-rolled SVGs
(see ``ui.icons``) — no emojis, no font glyphs.
"""
from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import QPoint, QPropertyAnimation, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import (
    QFrame, QGraphicsColorizeEffect, QHBoxLayout, QLabel, QSizePolicy, QWidget,
)

from ui import icons


# Default dim color for icon glyphs in the title bar — overridden on hover.
def _palette_color(w: QWidget, fallback: str) -> QColor:
    c = w.palette().color(QPalette.ColorRole.WindowText)
    return c if c.isValid() else QColor(fallback)


class _SvgLabel(QLabel):
    """A QLabel that paints a tinted SVG pixmap.

    The color is read from the ``iconColor`` dynamic property, which the
    parent button sets explicitly in its event handlers (no QSS juggling).
    Falls back to the QPalette WindowText role, then to white.
    """

    def __init__(self, icon_name: str, size: int = 14, parent=None):
        super().__init__(parent)
        self.setObjectName("SvgLabel")
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setFixedSize(size + 4, size + 4)
        self._icon_name = icon_name
        self._size = size
        # Default — the parent button will override this on first refresh.
        self.setProperty("iconColor", "#FFFFFF")

    def set_icon(self, name: str) -> None:
        self._icon_name = name
        self._refresh()

    def set_color(self, color: str) -> None:
        """Explicitly set the icon color (called by the parent button)."""
        self.setProperty("iconColor", color)
        self._refresh()

    def _refresh(self) -> None:
        prop = self.property("iconColor")
        if isinstance(prop, str) and prop:
            color = QColor(prop)
            if color.isValid():
                self.setPixmap(icons.render(self._icon_name, color, self._size))
                return
        c = self.palette().color(QPalette.ColorRole.WindowText)
        if c.isValid():
            self.setPixmap(icons.render(self._icon_name, c, self._size))
        else:
            self.setPixmap(icons.render(self._icon_name, QColor("#FFFFFF"), self._size))

    def changeEvent(self, e) -> None:
        if e.type() == e.Type.PaletteChange:
            self._refresh()
        super().changeEvent(e)

    def showEvent(self, e) -> None:
        self._refresh()
        super().showEvent(e)

    def polish_hook(self) -> None:
        """Re-read the iconColor after style polish completes."""
        self._refresh()


class _WinButton(QFrame):
    """A single window control button (min/max/close) with an SVG glyph."""

    def __init__(self, kind: str, theme: dict | None = None, parent=None):
        super().__init__(parent)
        self.setObjectName("WinBtn")
        self.setProperty("kind", kind)
        self.setFixedSize(QSize(36, 36))
        self._kind = kind
        self._theme = theme or {
            "fg": "#FFFFFF", "fg_dim": "#9A9A9A", "accent": "#D7191A",
            "danger": "#D7191A", "hover": "#181818",
        }

        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        self._glyph = _SvgLabel(kind, size=14, parent=self)
        self._glyph.setObjectName("WinGlyph")
        lay.addWidget(self._glyph, 0, Qt.AlignmentFlag.AlignCenter)
        self._apply_color()

    def set_theme(self, theme: dict) -> None:
        self._theme = theme
        self._apply_color()

    def _apply_color(self) -> None:
        # close button turns white on the red hover bg.
        if self._kind == "close" and self.property("hot") == "closeHover":
            color = "#FFFFFF"
        else:
            color = self._theme["fg"]
        self._glyph.set_color(color)

    def _set_hot(self, value) -> None:
        self.setProperty("hot", value)
        self.style().unpolish(self)
        self.style().polish(self)
        self._apply_color()

    def enterEvent(self, e) -> None:
        self._set_hot("closeHover" if self._kind == "close" else "hover")

    def leaveEvent(self, e) -> None:
        self._set_hot(False)

    def mousePressEvent(self, e) -> None:
        if e.button() != Qt.MouseButton.LeftButton:
            return
        self._set_hot("active")
        win = self.window()
        if self._kind == "min":
            win.showMinimized()
        elif self._kind == "max":
            if win.isMaximized():
                win.showNormal()
            else:
                win.showMaximized()
        elif self._kind == "close":
            win.close()

    def mouseReleaseEvent(self, e) -> None:
        self._set_hot("closeHover" if self._kind == "close" else "hover")


class _FolderButton(QFrame):
    """A square button with a folder SVG — opens the save directory."""

    clicked = Signal()

    def __init__(self, theme: dict | None = None, parent=None):
        super().__init__(parent)
        self.setObjectName("FolderBtn")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(QSize(36, 36))
        self.setProperty("hot", False)
        self._theme = theme or {
            "fg": "#FFFFFF", "fg_dim": "#9A9A9A", "accent": "#D7191A",
        }

        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        self._glyph = _SvgLabel("folder", size=16, parent=self)
        self._glyph.setObjectName("FolderGlyph")
        lay.addWidget(self._glyph, 0, Qt.AlignmentFlag.AlignCenter)
        self._apply_color()

    def set_theme(self, theme: dict) -> None:
        self._theme = theme
        self._apply_color()

    def _apply_color(self) -> None:
        if self.property("hot") == "hover" or self.property("hot") == "active":
            color = self._theme["fg"]
        else:
            color = self._theme["fg_dim"]
        self._glyph.set_color(color)

    def _set_hot(self, value) -> None:
        self.setProperty("hot", value)
        self.style().unpolish(self)
        self.style().polish(self)
        self._apply_color()

    def enterEvent(self, e) -> None:
        self._set_hot("hover")

    def leaveEvent(self, e) -> None:
        self._set_hot(False)

    def mousePressEvent(self, e) -> None:
        if e.button() != Qt.MouseButton.LeftButton:
            return
        self._set_hot("active")
        self.clicked.emit()

    def mouseReleaseEvent(self, e) -> None:
        self._set_hot("hover")


class TitleBar(QFrame):
    """Custom title bar — draggable. Mixed case brand. Min/Max/Close on right.

    Emits ``open_save_folder`` when the user clicks the folder icon.
    """

    open_save_folder = Signal()

    def __init__(self, theme: dict | None = None, parent=None):
        super().__init__(parent)
        self.setObjectName("TitleBar")
        self.setFixedHeight(36)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._theme = theme or {
            "fg": "#FFFFFF", "fg_dim": "#9A9A9A", "accent": "#D7191A",
            "danger": "#D7191A", "hover": "#181818",
        }

        self._drag_pos: QPoint | None = None
        self._drag_win_geom: QPoint | None = None
        self._drag_win_size: tuple[int, int] | None = None

        lay = QHBoxLayout(self)
        lay.setContentsMargins(14, 0, 8, 0)
        lay.setSpacing(0)

        # Drag region + brand
        self._title = QLabel("Tex")
        self._title.setObjectName("TitleBrand")
        lay.addSpacing(6)
        lay.addWidget(self._title, 0, Qt.AlignmentFlag.AlignVCenter)

        # Spacer
        lay.addStretch(1)

        # State pill (center-ish)
        self._pill = QFrame()
        self._pill.setObjectName("StatePill")
        self._pill.setProperty("active", False)
        pill_lay = QHBoxLayout(self._pill)
        pill_lay.setContentsMargins(10, 0, 10, 0)
        pill_lay.setSpacing(6)
        self._pill_dot = QLabel("")
        self._pill_dot.setObjectName("DotSm")
        self._pill_dot.setFixedSize(6, 6)
        self._pill_text = QLabel("Ready")
        self._pill_text.setObjectName("StatePillText")
        self._pill_text.setProperty("active", False)
        pill_lay.addWidget(self._pill_dot)
        pill_lay.addWidget(self._pill_text)
        lay.addWidget(self._pill)

        # Spacer
        lay.addStretch(1)

        # Subtle clock (small, dim)
        self._clock = QLabel("00:00")
        self._clock.setObjectName("TitleClock")
        lay.addWidget(self._clock, 0, Qt.AlignmentFlag.AlignVCenter)
        lay.addSpacing(8)

        # Folder icon — opens the user's save directory.
        self._btn_folder = _FolderButton(theme=self._theme)
        lay.addWidget(self._btn_folder, 0, Qt.AlignmentFlag.AlignVCenter)
        self._btn_folder.clicked.connect(self.open_save_folder.emit)

        # Window controls
        self._btn_min = _WinButton("min", theme=self._theme)
        self._btn_max = _WinButton("max", theme=self._theme)
        self._btn_close = _WinButton("close", theme=self._theme)
        win_row = QHBoxLayout()
        win_row.setContentsMargins(0, 0, 0, 0)
        win_row.setSpacing(0)
        win_row.addWidget(self._btn_min)
        win_row.addWidget(self._btn_max)
        win_row.addWidget(self._btn_close)
        self._win_wrap = QFrame()
        self._win_wrap.setObjectName("WinBar")
        self._win_wrap.setLayout(win_row)
        lay.addWidget(self._win_wrap, 0, Qt.AlignmentFlag.AlignVCenter)

        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._tick)
        self._timer.start()
        self._tick()

    # --- Drag logic ---
    def _drag_widgets(self) -> list[QWidget]:
        """Return children that should NOT initiate a drag (i.e. controls)."""
        return [self._pill, self._btn_min, self._btn_max, self._btn_close, self._win_wrap, self._clock, self._btn_folder]

    def mousePressEvent(self, e) -> None:
        if e.button() != Qt.MouseButton.LeftButton:
            return
        # Don't start drag on controls
        child = self.childAt(e.position().toPoint())
        if child is not None:
            for c in self._drag_widgets():
                if child is c or c.isAncestorOf(child):
                    return
        win = self.window()
        # If maximized, unmaximize and keep cursor x relative
        if win.isMaximized():
            win.showNormal()
            # Approximate: leave window at same x as cursor*scale
            new_x = int(e.globalPosition().x() - win.width() / 2)
            new_y = 0
            win.move(new_x, new_y)
        self._drag_pos = e.globalPosition().toPoint() - win.frameGeometry().topLeft()
        e.accept()

    def mouseMoveEvent(self, e) -> None:
        if self._drag_pos is None or not (e.buttons() & Qt.MouseButton.LeftButton):
            return
        win = self.window()
        win.move(e.globalPosition().toPoint() - self._drag_pos)
        e.accept()

    def mouseReleaseEvent(self, e) -> None:
        self._drag_pos = None
        e.accept()

    def mouseDoubleClickEvent(self, e) -> None:
        if e.button() != Qt.MouseButton.LeftButton:
            return
        win = self.window()
        if win.isMaximized():
            win.showNormal()
        else:
            win.showMaximized()

    def _tick(self) -> None:
        self._clock.setText(datetime.now().strftime("%H:%M"))

    def set_theme(self, theme: dict) -> None:
        self._theme = theme
        self._btn_folder.set_theme(theme)
        self._btn_min.set_theme(theme)
        self._btn_max.set_theme(theme)
        self._btn_close.set_theme(theme)

    # --- State ---
    def set_state(self, state: str) -> None:
        """state: 'ready' | 'fetching' | 'downloading' | 'error' | 'paused'"""
        mapping = {
            "ready":       ("Ready",       False, "DotDim"),
            "fetching":    ("Fetching\u2026",    True,  "DotSm"),
            "downloading": ("Downloading", True,  "DotSm"),
            "error":       ("Error",       True,  "DotSm"),
            "paused":      ("Paused",      False, "DotDim"),
        }
        text, active, dot_obj = mapping.get(state, ("Ready", False, "DotDim"))
        self._pill_text.setText(text)
        self._pill_text.setProperty("active", active)
        self._pill.setProperty("active", active)
        self._pill_dot.setObjectName(dot_obj)
        for w in (self._pill, self._pill_text, self._pill_dot):
            w.style().unpolish(w)
            w.style().polish(w)

        if state in ("downloading", "fetching"):
            eff = self._title.graphicsEffect()
            if not isinstance(eff, QGraphicsColorizeEffect):
                eff = QGraphicsColorizeEffect(self._title)
                self._title.setGraphicsEffect(eff)
            if hasattr(self, '_pulse_anim') and self._pulse_anim is not None:
                self._pulse_anim.stop()
            eff.setColor(QColor("#FFFFFF"))
            a = QPropertyAnimation(eff, b"strength", self._title)
            a.setDuration(1100)
            a.setStartValue(0.0)
            a.setKeyValueAt(0.5, 0.6)
            a.setEndValue(0.0)
            a.setLoopCount(-1)
            a.start()
            self._pulse_anim = a
        else:
            if hasattr(self, '_pulse_anim') and self._pulse_anim is not None:
                self._pulse_anim.stop()
                self._pulse_anim = None
            self._title.setGraphicsEffect(None)
