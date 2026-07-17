"""URL input bar — thin, hairline, soft radius. No decoration."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QLineEdit, QPushButton


class UrlBar(QFrame):
    fetch_requested = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("UrlBar")
        self.setFixedHeight(48)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # Status dot wrap
        status_wrap = QFrame()
        status_wrap.setFixedWidth(36)
        sw_lay = QHBoxLayout(status_wrap)
        sw_lay.setContentsMargins(0, 0, 0, 0)
        sw_lay.addStretch(1)
        self.status_dot = QLabel("")
        self.status_dot.setObjectName("DotDim")
        self.status_dot.setFixedSize(8, 8)
        sw_lay.addWidget(self.status_dot)
        sw_lay.addStretch(1)
        lay.addWidget(status_wrap)

        # Input
        self.input = QLineEdit()
        self.input.setObjectName("UrlInput")
        self.input.setPlaceholderText("Paste a link \u00B7 or many links at once")
        self.input.returnPressed.connect(self._submit)
        self.input.textChanged.connect(self._on_text_changed)
        lay.addWidget(self.input, 1)

        # Clear
        self.clear_btn = QPushButton("\u00D7")
        self.clear_btn.setObjectName("Icon")
        self.clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clear_btn.setVisible(False)
        self.clear_btn.clicked.connect(self._clear)
        self.clear_btn.setToolTip("Clear")
        self.clear_btn.setFixedSize(32, 32)
        lay.addWidget(self.clear_btn)

        # Fetch button
        self.fetch_btn = QPushButton("Fetch  \u25B8")
        self.fetch_btn.setObjectName("FetchBtn")
        self.fetch_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.fetch_btn.clicked.connect(self._submit)
        self.fetch_btn.setFixedWidth(110)
        lay.addWidget(self.fetch_btn)

        self._dot_status = "idle"
        self._shortcut = QShortcut(QKeySequence("Ctrl+Return"), self)
        self._shortcut.activated.connect(self._submit)

    def _submit(self) -> None:
        text = self.input.text().strip()
        if text:
            self.fetch_requested.emit(text)

    def _clear(self) -> None:
        self.input.clear()
        self.input.setFocus()
        self._set_dot("idle")

    def _on_text_changed(self, t: str) -> None:
        self.clear_btn.setVisible(bool(t))
        if t and self._dot_status == "idle":
            self._set_dot("ready")
        elif not t:
            self._set_dot("idle")

    def _set_dot(self, status: str) -> None:
        self._dot_status = status
        obj_map = {"idle": "DotDim", "loading": "DotSm", "ready": "DotWhite"}
        self.status_dot.setObjectName(obj_map.get(status, "DotDim"))
        self.status_dot.style().unpolish(self.status_dot)
        self.status_dot.style().polish(self.status_dot)

    def set_loading(self, loading: bool) -> None:
        self.fetch_btn.setEnabled(not loading)
        self.fetch_btn.setText("\u2026" if loading else "Fetch  \u25B8")
        self._set_dot("loading" if loading else ("ready" if self.input.text() else "idle"))
        self.input.setReadOnly(loading)

    def set_text(self, text: str) -> None:
        self.input.setText(text)
        # Don't auto-submit — let the user click Fetch or press Enter.

    def text(self) -> str:
        return self.input.text().strip()
