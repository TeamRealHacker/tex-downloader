"""Reusable icon-only button — paints an SVG glyph, follows QSS `color`.

A small square button that renders a hand-rolled SVG via ``ui.icons``. The
icon's color is driven by the QSS ``color`` property (re-read on every
palette change), so hover/active QSS rules naturally re-tint the icon.
"""
from __future__ import annotations

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QFrame, QHBoxLayout

from ui import icons


class IconButton(QFrame):
    """A square 28x24 (default) icon button.

    Emits ``clicked`` on left-mouse release. The icon's color follows
    QSS — it reads ``palette().color(WindowText)`` on every paint.
    """

    clicked = Signal()

    def __init__(self, icon_name: str, size: int = 14,
                 width: int = 28, height: int = 24,
                 theme: dict | None = None, parent=None):
        super().__init__(parent)
        self.setObjectName("Icon")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(QSize(width, height))
        self._icon_name = icon_name
        self._icon_size = size
        self._theme = theme or {
            "fg": "#FFFFFF", "fg_dim": "#9A9A9A", "accent": "#D7191A",
        }

        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        from PySide6.QtWidgets import QLabel
        self._glyph = QLabel(self)
        self._glyph.setObjectName("Glyph")
        self._glyph.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self._glyph.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._glyph.setFixedSize(width, height)
        self._glyph.setProperty("iconColor", self._theme["fg"])
        lay.addWidget(self._glyph, 0, Qt.AlignmentFlag.AlignCenter)
        # NOTE: No eventFilter installed — _refresh_glyph() is called from
        # changeEvent, showEvent, enterEvent, leaveEvent, mousePressEvent,
        # mouseReleaseEvent.  A Paint eventFilter caused ~1200 SVG re-parses
        # per second when hovering over buttons (now cached in icons.render).
        # Initial render
        self._refresh_glyph()

    def set_theme(self, theme: dict) -> None:
        self._theme = theme
        self._refresh_glyph()

    def set_icon(self, name: str) -> None:
        self._icon_name = name
        self._refresh_glyph()

    def _refresh_glyph(self) -> None:
        # Color: hot="active" → white (on accent bg), otherwise theme fg.
        if self.property("hot") == "active":
            color = "#FFFFFF"
        else:
            color = self._theme["fg"]
        self._glyph.setProperty("iconColor", color)
        self._glyph.setPixmap(icons.render(self._icon_name, color, self._icon_size))

    def changeEvent(self, e) -> None:
        if e.type() == e.Type.PaletteChange:
            self._refresh_glyph()
        super().changeEvent(e)

    def showEvent(self, e) -> None:
        self._refresh_glyph()
        super().showEvent(e)

    def mousePressEvent(self, e) -> None:
        if e.button() == Qt.MouseButton.LeftButton:
            self.setProperty("hot", "active")
            self.style().unpolish(self)
            self.style().polish(self)
            self._refresh_glyph()
            e.accept()

    def mouseReleaseEvent(self, e) -> None:
        if e.button() == Qt.MouseButton.LeftButton:
            self.setProperty("hot", "hover")
            self.style().unpolish(self)
            self.style().polish(self)
            self._refresh_glyph()
            if self.rect().contains(e.position().toPoint()):
                self.clicked.emit()
            e.accept()

    def enterEvent(self, e) -> None:
        self.setProperty("hot", "hover")
        self.style().unpolish(self)
        self.style().polish(self)
        self._refresh_glyph()

    def leaveEvent(self, e) -> None:
        self.setProperty("hot", False)
        self.style().unpolish(self)
        self.style().polish(self)
        self._refresh_glyph()


class PixelButton(QFrame):
    """A retro-pixelated primary button with a hard 3D shadow.

    Two stacked children: a dark "shadow" frame offset 3px down-right,
    and a bright "face" frame on top. On press, the face moves down 3px
    to cover the shadow — gives a satisfying 8-bit click feel. Bold
    uppercase text + an SVG icon, all rendered in white on the red face.
    """

    clicked = Signal()

    def __init__(self, icon_name: str, text: str, size: int = 16,
                 height: int = 44, theme: dict | None = None, parent=None):
        super().__init__(parent)
        self.setObjectName("PixelBtnWrap")
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFixedHeight(height + 4)  # +4 for shadow room
        self._icon_name = icon_name
        self._icon_size = size
        self._height = height
        self._pressed = False
        self._theme = theme or {
            "fg": "#FFFFFF", "fg_dim": "#9A9A9A", "accent": "#D7191A",
            "accent_dim": "#7A0E0F",
        }

        # The hard shadow frame — sits behind the face, offset down-right.
        self._shadow = QFrame(self)
        self._shadow.setObjectName("PixelBtnShadow")
        self._shadow.setFixedHeight(height)
        self._shadow.move(3, 3)

        # The actual button face — moves down 3px on press.
        self._face = QFrame(self)
        self._face.setObjectName("PixelBtn")
        self._face.setCursor(Qt.CursorShape.PointingHandCursor)
        self._face.setFixedHeight(height)
        self._face.move(0, 0)
        self.setFixedHeight(height + 3)

        from PySide6.QtWidgets import QLabel
        lay = QHBoxLayout(self._face)
        lay.setContentsMargins(18, 0, 16, 0)
        lay.setSpacing(10)

        self._text = QLabel(text)
        self._text.setObjectName("PixelText")
        self._text.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        lay.addWidget(self._text, 0, Qt.AlignmentFlag.AlignVCenter)

        self._arrow = QLabel(self._face)
        self._arrow.setObjectName("PixelArrow")
        self._arrow.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self._arrow.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._arrow.setFixedSize(size + 4, height)
        lay.addWidget(self._arrow, 0, Qt.AlignmentFlag.AlignVCenter)

        self._refresh_arrow()

        # Resize the shadow/face to match the wrapper width.
        self.resizeEvent = self._on_resize  # type: ignore[assignment]

    def _on_resize(self, e) -> None:
        w = self.width() - 3
        self._shadow.setFixedSize(w, self._height)
        self._face.setFixedSize(w, self._height)
        # Re-apply pressed offset (resize can move them).
        self._face.move(0, 3 if self._pressed else 0)
        self._shadow.move(3, 3)

    def setFixedWidth(self, w):  # type: ignore[override]
        super().setFixedWidth(w + 3)
        self._on_resize(None)

    def set_text(self, text: str) -> None:
        self._text.setText(text)

    def set_icon(self, name: str) -> None:
        self._icon_name = name
        self._refresh_arrow()

    def _refresh_arrow(self) -> None:
        # Always white — sits on the red button face.
        self._arrow.setProperty("iconColor", "#FFFFFF")
        self._arrow.setPixmap(icons.render(self._icon_name, "#FFFFFF", self._icon_size))

    def showEvent(self, e) -> None:
        self._refresh_arrow()
        super().showEvent(e)

    # Hover/press state — both the wrapper and the face track these.
    def _set_hot(self, v) -> None:
        self._face.setProperty("hot", v)
        self._face.style().unpolish(self._face)
        self._face.style().polish(self._face)

    def _set_pressed(self, on: bool) -> None:
        self._pressed = on
        self._face.setProperty("pressed", on)
        self._face.style().unpolish(self._face)
        self._face.style().polish(self._face)
        self._face.move(0, 3 if on else 0)

    # Forward mouse events to the face — easier hit detection.
    def mousePressEvent(self, e) -> None:
        if e.button() == Qt.MouseButton.LeftButton:
            self._set_hot(False)
            self._set_pressed(True)
            e.accept()

    def mouseReleaseEvent(self, e) -> None:
        if e.button() == Qt.MouseButton.LeftButton:
            inside = self._face.rect().contains(
                self._face.mapFromParent(e.position().toPoint())
            )
            self._set_pressed(False)
            self._set_hot("hover")
            if inside:
                self.clicked.emit()
            e.accept()

    def enterEvent(self, e) -> None:
        if not self._pressed:
            self._set_hot("hover")

    def leaveEvent(self, e) -> None:
        self._set_hot(False)


class IconTextButton(QFrame):
    """A primary-style button: small SVG icon + label, no emoji.

    The icon color follows QSS — re-reads ``palette().color(WindowText)``
    on every palette change so hover/active re-tints the icon naturally.
    """

    clicked = Signal()

    def __init__(self, icon_name: str, text: str, size: int = 14,
                 height: int = 40, theme: dict | None = None, parent=None):
        super().__init__(parent)
        self.setObjectName("Primary")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(height)
        self.setProperty("hot", False)
        self._icon_name = icon_name
        self._icon_size = size
        self._theme = theme or {
            "fg": "#FFFFFF", "fg_dim": "#9A9A9A", "accent": "#D7191A",
        }

        from PySide6.QtWidgets import QLabel
        lay = QHBoxLayout(self)
        lay.setContentsMargins(14, 0, 12, 0)
        lay.setSpacing(8)

        self._text = QLabel(text)
        self._text.setObjectName("PrimaryText")
        self._text.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        lay.addWidget(self._text, 0, Qt.AlignmentFlag.AlignVCenter)

        self._arrow = QLabel(self)
        self._arrow.setObjectName("PrimaryArrow")
        self._arrow.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self._arrow.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._arrow.setFixedSize(size + 2, height)
        self._arrow.setProperty("iconColor", self._theme["fg"])
        lay.addWidget(self._arrow, 0, Qt.AlignmentFlag.AlignVCenter)

        self._refresh_arrow()

    def set_theme(self, theme: dict) -> None:
        self._theme = theme
        self._refresh_arrow()

    def set_text(self, text: str) -> None:
        self._text.setText(text)

    def set_icon(self, name: str) -> None:
        self._icon_name = name
        self._refresh_arrow()

    def _refresh_arrow(self) -> None:
        color = self._theme["fg"]
        self._arrow.setProperty("iconColor", color)
        self._arrow.setPixmap(icons.render(self._icon_name, color, self._icon_size))

    def changeEvent(self, e) -> None:
        if e.type() == e.Type.PaletteChange:
            self._refresh_arrow()
        super().changeEvent(e)

    def showEvent(self, e) -> None:
        self._refresh_arrow()
        super().showEvent(e)

    def _set_hot(self, v) -> None:
        self.setProperty("hot", v)
        self.style().unpolish(self)
        self.style().polish(self)
        self._refresh_arrow()

    def enterEvent(self, e) -> None:
        self._set_hot("hover")

    def leaveEvent(self, e) -> None:
        self._set_hot(False)

    def mousePressEvent(self, e) -> None:
        if e.button() == Qt.MouseButton.LeftButton:
            self._set_hot("active")
            e.accept()

    def mouseReleaseEvent(self, e) -> None:
        if e.button() == Qt.MouseButton.LeftButton:
            self._set_hot("hover")
            if self.rect().contains(e.position().toPoint()):
                self.clicked.emit()
            e.accept()
