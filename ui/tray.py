"""System tray with red dot."""
from __future__ import annotations

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QAction, QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QMenu, QSystemTrayIcon


def _red_dot_icon() -> QIcon:
    pm = QPixmap(64, 64)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    p.setBrush(QColor("#D7191A"))
    p.setPen(Qt.PenStyle.NoPen)
    p.drawEllipse(8, 8, 48, 48)
    p.end()
    return QIcon(pm)


class TrayIcon(QSystemTrayIcon):
    def __init__(self, on_show, on_paste, on_quit, parent=None):
        super().__init__(parent)
        self.setIcon(_red_dot_icon())
        self.setToolTip("TEX")
        self.on_show = on_show
        self.on_paste = on_paste
        self.on_quit = on_quit

        menu = QMenu()
        a_show = QAction("Open Tex", menu)
        a_show.triggered.connect(self.on_show)
        a_paste = QAction("Paste URL", menu)
        a_paste.triggered.connect(self.on_paste)
        a_quit = QAction("Quit", menu)
        a_quit.triggered.connect(self.on_quit)
        menu.addAction(a_show)
        menu.addAction(a_paste)
        menu.addSeparator()
        menu.addAction(a_quit)
        self.setContextMenu(menu)
        self.activated.connect(self._on_activated)

    def _on_activated(self, reason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.on_show()

    def notify(self, title: str, body: str,
               icon=QSystemTrayIcon.MessageIcon.Information,
               timeout_ms: int = 4000) -> None:
        """Show a system notification balloon / toast. No-op if unsupported."""
        if QSystemTrayIcon.supportsMessages():
            try:
                self.showMessage(title, body, icon, int(timeout_ms))
            except Exception:
                pass
