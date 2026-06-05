"""Keyboard shortcuts."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QShortcut


def install(window) -> None:
    """Install global shortcuts on a window."""
    sc_paste = QShortcut(QKeySequence("Ctrl+V"), window)
    sc_paste.setContext(Qt.ShortcutContext.ApplicationShortcut)
    sc_paste.activated.connect(window.shortcut_paste)

    sc_focus = QShortcut(QKeySequence("Ctrl+L"), window)
    sc_focus.setContext(Qt.ShortcutContext.ApplicationShortcut)
    sc_focus.activated.connect(window.shortcut_focus_url)

    sc_enter = QShortcut(QKeySequence("Return"), window)
    sc_enter.setContext(Qt.ShortcutContext.ApplicationShortcut)
    sc_enter.activated.connect(window.shortcut_enter)

    sc_esc = QShortcut(QKeySequence("Escape"), window)
    sc_esc.setContext(Qt.ShortcutContext.ApplicationShortcut)
    sc_esc.activated.connect(window.shortcut_escape)

    sc_settings = QShortcut(QKeySequence("Ctrl+,"), window)
    sc_settings.setContext(Qt.ShortcutContext.ApplicationShortcut)
    sc_settings.activated.connect(window.shortcut_settings)

    sc_history = QShortcut(QKeySequence("Ctrl+H"), window)
    sc_history.setContext(Qt.ShortcutContext.ApplicationShortcut)
    sc_history.activated.connect(window.shortcut_history)

    sc_queue = QShortcut(QKeySequence("Ctrl+J"), window)
    sc_queue.setContext(Qt.ShortcutContext.ApplicationShortcut)
    sc_queue.activated.connect(window.shortcut_queue)

    sc_dl = QShortcut(QKeySequence("Ctrl+1"), window)
    sc_dl.setContext(Qt.ShortcutContext.ApplicationShortcut)
    sc_dl.activated.connect(window.shortcut_download)

    sc_dl2 = QShortcut(QKeySequence("Ctrl+2"), window)
    sc_dl2.setContext(Qt.ShortcutContext.ApplicationShortcut)
    sc_dl2.activated.connect(window.shortcut_queue)

    sc_dl3 = QShortcut(QKeySequence("Ctrl+3"), window)
    sc_dl3.setContext(Qt.ShortcutContext.ApplicationShortcut)
    sc_dl3.activated.connect(window.shortcut_history)

    sc_dl4 = QShortcut(QKeySequence("Ctrl+4"), window)
    sc_dl4.setContext(Qt.ShortcutContext.ApplicationShortcut)
    sc_dl4.activated.connect(window.shortcut_settings)
