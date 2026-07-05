"""Left sidebar — wider (168px) with rounded active state + collapse/expand.

Collapsed: 56px, just SVG icon.
Expanded: icon + label, rounded active bg with red border.
All icons are hand-rolled SVGs (see ``ui.icons``) — no emoji, no glyphs.
"""
from __future__ import annotations

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import (
    QButtonGroup, QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget,
)

from ui import icons


class _NavItem(QPushButton):
    def __init__(self, label: str, key: str, icon_name: str,
                 theme: dict | None = None, parent=None):
        super().__init__(parent)
        self.setObjectName("SideNav")
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.key = key
        self._full_label = label
        self._icon_name = icon_name
        self.setMinimumHeight(36)

        # Theme palette passed in by the parent — we set the icon color
        # explicitly via the iconColor dynamic property, no QSS juggling.
        self._theme = theme or {
            "fg": "#FFFFFF", "fg_dim": "#9A9A9A", "accent": "#D7191A",
        }

        from PySide6.QtWidgets import QHBoxLayout as _HB
        self._lay = _HB(self)
        self._lay.setContentsMargins(0, 0, 0, 0)
        self._lay.setSpacing(8)
        self._icon = QLabel(self)
        self._icon.setObjectName("NavIcon")
        self._icon.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self._icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._icon.setFixedSize(26, 26)
        # Set initial icon color via dynamic property.
        self._icon.setProperty("iconColor", self._theme["fg_dim"])
        self._lay.addSpacing(4)
        self._lay.addWidget(self._icon, 0, Qt.AlignmentFlag.AlignVCenter)

        self._lbl = QLabel(self._full_label, self)
        self._lbl.setObjectName("NavLabel")
        self._lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self._lay.addWidget(self._lbl, 0, Qt.AlignmentFlag.AlignVCenter)
        self._lay.addStretch(1)

        self._refresh_icon()

    def set_theme(self, theme: dict) -> None:
        self._theme = theme
        self._refresh_icon()

    def _refresh_icon(self) -> None:
        # Icon color depends on the button's state:
        # - checked → accent (red, matches the active border)
        # - hover   → fg (bright)
        # - default → fg_dim (subtle)
        if self.isChecked():
            color = self._theme["accent"]
        elif self.underMouse():
            color = self._theme["fg"]
        else:
            color = self._theme["fg_dim"]
        self._icon.setProperty("iconColor", color)
        self._icon.setPixmap(icons.render(self._icon_name, color, 22))

    def _fallback_color(self):
        from PySide6.QtGui import QColor
        return QColor("#FFFFFF")

    def changeEvent(self, e) -> None:
        if e.type() == e.Type.PaletteChange:
            self._refresh_icon()
        super().changeEvent(e)

    def showEvent(self, e) -> None:
        self._refresh_icon()
        super().showEvent(e)

    def set_collapsed(self, collapsed: bool) -> None:
        self._lbl.setVisible(not collapsed)
        self._refresh_icon()

    def enterEvent(self, e) -> None:
        super().enterEvent(e)
        self._refresh_icon()

    def leaveEvent(self, e) -> None:
        super().leaveEvent(e)
        self._refresh_icon()

    def setChecked(self, checked: bool) -> None:
        super().setChecked(checked)
        self._refresh_icon()


class _Badge(QLabel):
    def __init__(self, text: str = "0", parent=None):
        super().__init__(text, parent)
        self.setObjectName("SideBadge")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setFixedHeight(16)
        self.setMinimumWidth(16)
        self.setMaximumWidth(22)


class Sidebar(QFrame):
    nav_changed = Signal(int)
    collapse_changed = Signal(bool)  # True = collapsed

    ICONS = {
        "download": "nav_download",
        "queue":    "nav_queue",
        "channels": "nav_channels",
        "history":  "nav_history",
        "settings": "nav_settings",
    }

    def __init__(self, theme: dict | None = None, parent=None):
        super().__init__(parent)
        self.setObjectName("Sidebar")
        self._collapsed = False
        self.setFixedWidth(168)
        # Default theme palette (overridden by set_theme).
        self._theme = theme or {
            "fg": "#FFFFFF", "fg_dim": "#9A9A9A", "accent": "#D7191A",
        }

        outer = QVBoxLayout(self)
        outer.setContentsMargins(10, 12, 10, 12)
        outer.setSpacing(0)

        # Top row: brand + collapse toggle
        top = QHBoxLayout()
        top.setContentsMargins(8, 0, 4, 0)
        top.setSpacing(4)
        self._brand_dot = QLabel("\u2022")
        self._brand_dot.setObjectName("TitleBrandDot")
        self._brand_dot.setStyleSheet("font-size: 16px;")
        self._brand = QLabel("Tex")
        self._brand.setObjectName("SideBrand")
        top.addWidget(self._brand_dot, 0, Qt.AlignmentFlag.AlignVCenter)
        self._brand_lbl = QLabel("Tex")
        self._brand_lbl.setObjectName("SideBrand")
        top.addWidget(self._brand_lbl, 0, Qt.AlignmentFlag.AlignVCenter)
        top.addStretch(1)

        self._btn_collapse = QPushButton()
        self._btn_collapse.setObjectName("SideToggle")
        self._btn_collapse.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_collapse.setFixedSize(QSize(24, 24))
        self._btn_collapse.setToolTip("Collapse")
        self._btn_collapse.clicked.connect(self._toggle_collapse)
        self._btn_collapse._glyph_lbl = QLabel(self._btn_collapse)
        self._btn_collapse._glyph_lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self._btn_collapse._glyph_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._btn_collapse._glyph_lbl.setFixedSize(24, 24)
        self._btn_collapse._refresh_glyph = self._refresh_collapse_glyph
        self._btn_collapse._refresh_glyph()
        top.addWidget(self._btn_collapse, 0, Qt.AlignmentFlag.AlignVCenter)

        # When collapsed, hide text labels
        self._brand_lbl.setVisible(True)

        outer.addLayout(top)

        outer.addSpacing(18)

        # Nav
        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        self._nav_items: list[_NavItem] = []
        self._nav_badge: dict[str, _Badge] = {}

        nav_defs = [
            ("Download", "download"),
            ("Queue",    "queue"),
            ("Channels", "channels"),
            ("History",  "history"),
            ("Settings", "settings"),
        ]
        for label, key in nav_defs:
            outer.addWidget(self._make_nav_row(label, key))
            outer.addSpacing(2)

        outer.addStretch(1)

    def _make_nav_row(self, label: str, key: str) -> QFrame:
        row = QFrame()
        row.setObjectName("SideRow")
        lay = QHBoxLayout(row)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)

        btn = _NavItem(label, key, self.ICONS.get(key, "nav_download"),
                       theme=self._theme)
        btn.clicked.connect(lambda _=False, k=key: self._on_click(k))
        self._group.addButton(btn)
        self._nav_items.append(btn)

        badge = _Badge("0")
        badge.setVisible(False)
        self._nav_badge[key] = badge

        lay.addWidget(btn, 1)
        lay.addWidget(badge, 0, Qt.AlignmentFlag.AlignVCenter)
        return row

    def set_theme(self, theme: dict) -> None:
        """Update the theme palette used for nav icons."""
        self._theme = theme
        for item in self._nav_items:
            item.set_theme(theme)

    def _on_click(self, key: str) -> None:
        idx = next((i for i, it in enumerate(self._nav_items) if it.key == key), 0)
        self.nav_changed.emit(idx)

    def set_active(self, idx: int) -> None:
        if 0 <= idx < len(self._nav_items):
            self._nav_items[idx].setChecked(True)

    def set_badge(self, key: str, count: int) -> None:
        badge = self._nav_badge.get(key)
        if not badge:
            return
        if count > 0:
            badge.setText(str(min(99, count)))
            badge.setVisible(True)
        else:
            badge.setVisible(False)

    # --- Collapse / expand ---
    def _toggle_collapse(self) -> None:
        self.set_collapsed(not self._collapsed)

    def set_collapsed(self, collapsed: bool) -> None:
        self._collapsed = collapsed
        target = 60 if collapsed else 168
        # Set fixed width immediately — skip QPropertyAnimation because it
        # fights with setFixedWidth and causes visual flicker.
        self.setFixedWidth(target)
        # Update children
        self._brand_lbl.setVisible(not collapsed)
        for item in self._nav_items:
            item.set_collapsed(collapsed)
        # Update badge visibility
        for b in self._nav_badge.values():
            b.setVisible(not collapsed and b.text() not in ("0", ""))
        # Update toggle glyph
        self._btn_collapse._glyph_lbl.setProperty("expanded", not collapsed)
        self._btn_collapse._refresh_glyph()
        self._btn_collapse.setToolTip("Expand" if collapsed else "Collapse")
        self.collapse_changed.emit(collapsed)

    def _refresh_collapse_glyph(self) -> None:
        expanded = self._btn_collapse._glyph_lbl.property("expanded")
        if expanded is None:
            expanded = True
        name = "chevron_left" if expanded else "chevron_right"
        lbl = self._btn_collapse._glyph_lbl
        color = lbl.property("iconColor")
        if not isinstance(color, str) or not color:
            color = lbl.palette().color(QPalette.ColorRole.WindowText)
        if not isinstance(color, QColor) or not color.isValid():
            from PySide6.QtGui import QColor as _QC
            color = _QC("#FFFFFF")
        lbl.setPixmap(icons.render(name, color, 14))

    def is_collapsed(self) -> bool:
        return self._collapsed
