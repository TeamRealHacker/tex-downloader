"""Clipboard watcher: emit signal when a URL is detected."""
from __future__ import annotations

import re
from typing import Callable

from PySide6.QtCore import QObject, QTimer, Signal

from .detector import extract_urls

_URL_RE = re.compile(r"https?://[^\s<>\"']+")


class ClipboardWatcher(QObject):
    url_detected = Signal(str)

    def __init__(self, interval_ms: int = 1200, parent=None):
        super().__init__(parent)
        self._last = ""
        self._timer = QTimer(self)
        self._timer.setInterval(interval_ms)
        self._timer.timeout.connect(self._tick)
        self._enabled = True

    def start(self) -> None:
        self._timer.start()

    def stop(self) -> None:
        self._timer.stop()

    def set_enabled(self, on: bool) -> None:
        self._enabled = on

    def _tick(self) -> None:
        if not self._enabled:
            return
        try:
            from PySide6.QtGui import QGuiApplication
            cb = QGuiApplication.clipboard()
            text = cb.text()
        except Exception:
            return
        if not text or text == self._last:
            return
        self._last = text
        urls = extract_urls(text)
        if urls:
            self.url_detected.emit(urls[0])
