"""Tex icon set — all-filled shapes, no strokes.

Every icon uses only fill="currentColor" with no stroke attributes.
This guarantees reliable rendering at any size in QSvgRenderer — strokes
can disappear or render incorrectly at small pixel sizes. Shapes are
chunky, bold, and optimized for 14-24px renders on both dark and light
backgrounds.
"""
from __future__ import annotations

from PySide6.QtCore import QRectF
from PySide6.QtGui import QColor, QImage, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer


_SVG: dict[str, str] = {

    # ---------- WINDOW CONTROLS ----------
    "min": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'
        '<rect x="5" y="10.5" width="14" height="3" rx="1.5" fill="currentColor"/>'
        '</svg>'
    ),
    "max": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'
        '<rect x="4" y="4" width="16" height="16" rx="2.5" fill="currentColor"/>'
        '<rect x="6" y="6" width="12" height="12" rx="1.5" fill="black"/>'
        '</svg>'
    ),
    "max_restore": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'
        '<rect x="2" y="2" width="12" height="12" rx="2" fill="currentColor"/>'
        '<rect x="4" y="4" width="8" height="8" rx="1" fill="black"/>'
        '<rect x="10" y="10" width="12" height="12" rx="2" fill="currentColor"/>'
        '<rect x="12" y="12" width="8" height="8" rx="1" fill="black"/>'
        '</svg>'
    ),
    "close": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'
        '<rect x="10.5" y="3" width="3" height="18" rx="1.5" fill="currentColor" transform="rotate(45 12 12)"/>'
        '<rect x="10.5" y="3" width="3" height="18" rx="1.5" fill="currentColor" transform="rotate(-45 12 12)"/>'
        '</svg>'
    ),

    # ---------- FOLDER ----------
    "folder": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'
        '<path d="M3 7.5 C3 6.1 4.1 5 5.5 5 H9.5 L12 8 H18.5 C19.9 8 21 9.1 21 10.5 V18 C21 19.4 19.9 20.5 18.5 20.5 H5.5 C4.1 20.5 3 19.4 3 18 Z" fill="currentColor"/>'
        '</svg>'
    ),
    "folder_open": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'
        '<path d="M3 7.5 C3 6.1 4.1 5 5.5 5 H9.5 L12 8 H18.5 C19.9 8 21 9.1 21 10.5 V12 L17 20 H5.5 C4.1 20.5 3 19.4 3 18 Z" fill="currentColor"/>'
        '</svg>'
    ),

    # ---------- PROGRESS CARD ----------
    "pause": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'
        '<rect x="6" y="4" width="4" height="16" rx="1.5" fill="currentColor"/>'
        '<rect x="14" y="4" width="4" height="16" rx="1.5" fill="currentColor"/>'
        '</svg>'
    ),
    "play": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'
        '<path d="M6 3 L6 21 L21 12 Z" fill="currentColor"/>'
        '</svg>'
    ),
    "x": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'
        '<rect x="10.5" y="3" width="3" height="18" rx="1.5" fill="currentColor" transform="rotate(45 12 12)"/>'
        '<rect x="10.5" y="3" width="3" height="18" rx="1.5" fill="currentColor" transform="rotate(-45 12 12)"/>'
        '</svg>'
    ),
    # Box with arrow popping out upper-right corner.
    "open_external": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'
        '<rect x="3" y="3" width="14" height="14" rx="2" fill="currentColor"/>'
        '<rect x="5" y="5" width="10" height="10" rx="1" fill="black"/>'
        '<rect x="5" y="5" width="14" height="3" rx="1" fill="currentColor"/>'
        '<rect x="16" y="5" width="3" height="14" rx="1" fill="currentColor"/>'
        '<rect x="14" y="3" width="5" height="3" rx="1" fill="currentColor"/>'
        '<rect x="16" y="3" width="3" height="5" rx="1" fill="currentColor"/>'
        '</svg>'
    ),

    # ---------- CHANNEL PANEL ----------
    "fetch": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'
        '<rect x="3" y="10" width="12" height="4" rx="2" fill="currentColor"/>'
        '<path d="M13 4 L21 12 L13 20 Z" fill="currentColor"/>'
        '</svg>'
    ),
    "download": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'
        '<rect x="10" y="3" width="4" height="10" rx="2" fill="currentColor"/>'
        '<path d="M5 9 L12 16 L19 9 Z" fill="currentColor"/>'
        '<rect x="3" y="19" width="18" height="3" rx="1.5" fill="currentColor"/>'
        '</svg>'
    ),

    # ---------- SIDEBAR NAV ----------
    "nav_download": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'
        '<rect x="10" y="3" width="4" height="10" rx="2" fill="currentColor"/>'
        '<path d="M5 9 L12 16 L19 9 Z" fill="currentColor"/>'
        '<rect x="3" y="19" width="18" height="3" rx="1.5" fill="currentColor"/>'
        '</svg>'
    ),
    "nav_queue": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'
        '<rect x="3" y="5"  width="18" height="4" rx="2" fill="currentColor"/>'
        '<rect x="3" y="10" width="18" height="4" rx="2" fill="currentColor" opacity="0.7"/>'
        '<rect x="3" y="15" width="18" height="4" rx="2" fill="currentColor" opacity="0.45"/>'
        '</svg>'
    ),
    "nav_channels": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'
        '<rect x="2" y="2" width="9" height="9" rx="2.5" fill="currentColor"/>'
        '<rect x="13" y="2" width="9" height="9" rx="2.5" fill="currentColor" opacity="0.65"/>'
        '<rect x="2" y="13" width="9" height="9" rx="2.5" fill="currentColor" opacity="0.65"/>'
        '<rect x="13" y="13" width="9" height="9" rx="2.5" fill="currentColor"/>'
        '</svg>'
    ),
    # Clock — solid filled circle with two small filled rectangles for hands.
    "nav_history": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'
        '<circle cx="12" cy="12" r="9" fill="currentColor"/>'
        '<rect x="11" y="6" width="2.5" height="7" rx="1.2" fill="black"/>'
        '<rect x="11" y="11" width="6" height="2.5" rx="1.2" fill="black" transform="rotate(-30 14 12)"/>'
        '</svg>'
    ),
    # Gear — solid filled with center hole.
    "nav_settings": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'
        '<circle cx="12" cy="12" r="10" fill="currentColor"/>'
        '<rect x="5" y="10.5" width="14" height="3" rx="1.5" fill="black"/>'
        '<rect x="10.5" y="5" width="3" height="14" rx="1.5" fill="black"/>'
        '<rect x="6" y="6" width="4" height="4" rx="2" fill="currentColor"/>'
        '<rect x="14" y="6" width="4" height="4" rx="2" fill="currentColor"/>'
        '<rect x="6" y="14" width="4" height="4" rx="2" fill="currentColor"/>'
        '<rect x="14" y="14" width="4" height="4" rx="2" fill="currentColor"/>'
        '<circle cx="12" cy="12" r="3.5" fill="black"/>'
        '<circle cx="12" cy="12" r="2" fill="currentColor"/>'
        '</svg>'
    ),

    # ---------- GENERIC ----------
    "check": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'
        '<path d="M3 12 L4.5 10.5 L10 16 L19.5 6.5 L21 8 L10 19 Z" fill="currentColor"/>'
        '</svg>'
    ),
    "search": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'
        '<circle cx="10" cy="10" r="7" fill="currentColor"/>'
        '<circle cx="10" cy="10" r="3.5" fill="black"/>'
        '<rect x="14" y="14" width="7" height="3.5" rx="1.8" fill="currentColor" transform="rotate(-45 17.5 15.75)"/>'
        '</svg>'
    ),
    "trash": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'
        '<rect x="5" y="7" width="14" height="13" rx="2" fill="currentColor"/>'
        '<rect x="3" y="5" width="18" height="3" rx="1.5" fill="currentColor"/>'
        '<rect x="8" y="3" width="8" height="3" rx="1.5" fill="currentColor"/>'
        '<rect x="10" y="10" width="2" height="7" rx="1" fill="black"/>'
        '<rect x="13" y="10" width="2" height="7" rx="1" fill="black"/>'
        '</svg>'
    ),
    "globe": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'
        '<circle cx="12" cy="12" r="9" fill="currentColor"/>'
        '<ellipse cx="12" cy="12" rx="4" ry="9" fill="black"/>'
        '<rect x="3" y="10.5" width="18" height="3" fill="currentColor"/>'
        '</svg>'
    ),
    "infinity": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'
        '<circle cx="8" cy="12" r="5" fill="currentColor"/>'
        '<circle cx="16" cy="12" r="5" fill="currentColor"/>'
        '<circle cx="8" cy="12" r="2.5" fill="black"/>'
        '<circle cx="16" cy="12" r="2.5" fill="black"/>'
        '</svg>'
    ),
    "chevron_left": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'
        '<path d="M14 4 L5 12 L14 20 Z" fill="currentColor"/>'
        '</svg>'
    ),
    "chevron_right": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'
        '<path d="M10 4 L19 12 L10 20 Z" fill="currentColor"/>'
        '</svg>'
    ),
    "chevron_down": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'
        '<path d="M4 9 L12 18 L20 9 Z" fill="currentColor"/>'
        '</svg>'
    ),
    "chevron_up": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'
        '<path d="M4 16 L12 7 L20 16 Z" fill="currentColor"/>'
        '</svg>'
    ),
    "more": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'
        '<circle cx="12" cy="5"  r="2.5" fill="currentColor"/>'
        '<circle cx="12" cy="12" r="2.5" fill="currentColor"/>'
        '<circle cx="12" cy="19" r="2.5" fill="currentColor"/>'
        '</svg>'
    ),
    "dot": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'
        '<circle cx="12" cy="12" r="6" fill="currentColor"/>'
        '</svg>'
    ),
    "spinner": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'
        '<circle cx="12" cy="12" r="9" fill="currentColor" opacity="0.25"/>'
        '<path d="M12 3 A9 9 0 0 1 21 12 L12 12 Z" fill="currentColor"/>'
        '</svg>'
    ),
}


_RENDERERS: dict[str, QSvgRenderer] = {}


def _renderer(name: str) -> QSvgRenderer | None:
    r = _RENDERERS.get(name)
    if r is None:
        svg = _SVG.get(name)
        if not svg:
            return None
        r = QSvgRenderer(svg.encode("utf-8"))
        _RENDERERS[name] = r
    return r


def render(name: str, color: "QColor | str" = "#FFFFFF", size: int = 16,
           opacity: float = 1.0) -> QPixmap:
    """Render an icon to a QPixmap, replacing currentColor with the given color."""
    raw = _SVG.get(name)
    if not raw:
        return QPixmap(size, size)
    if isinstance(color, str):
        color = QColor(color)

    # Use 6-digit hex — QSvgRenderer in PySide6 may not handle 8-digit (#RRGGBBAA).
    tinted = raw.replace("currentColor", color.name(QColor.NameFormat.HexRgb))
    if opacity < 1.0:
        tinted = tinted.replace(
            "<svg",
            f'<svg opacity="{opacity:.3f}"', 1,
        )
    rr = QSvgRenderer(tinted.encode("utf-8"))

    img = QImage(size, size, QImage.Format.Format_ARGB32_Premultiplied)
    img.fill(0)
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    rr.render(p, QRectF(0, 0, size, size))
    p.end()
    return QPixmap.fromImage(img)


def qicon(name: str, color: "QColor | str" = "#FFFFFF", size: int = 16) -> "QIcon":
    from PySide6.QtGui import QIcon
    return QIcon(render(name, color, size))


__all__ = ["render", "qicon"] + list(_SVG.keys())
