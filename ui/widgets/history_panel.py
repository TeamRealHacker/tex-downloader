"""Download history panel with thumbnails + meta."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QListView, QListWidget, QListWidgetItem,
    QPushButton, QVBoxLayout,
)

from core import history

from ui.widgets.dot_matrix import GLYPH_DOWN, GLYPH_MUSIC, DotMatrix


class _Item(QFrame):
    def __init__(self, entry: history.HistoryEntry, parent=None):
        super().__init__(parent)
        self.setObjectName("CardInset")
        self.entry = entry

        lay = QHBoxLayout(self)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(14)

        # Left: kind glyph (dot-matrix arrow / note)
        kind_wrap = QFrame()
        kind_wrap.setFixedWidth(28)
        kw = QVBoxLayout(kind_wrap)
        kw.setContentsMargins(0, 0, 0, 0)
        glyph = DotMatrix(GLYPH_MUSIC if entry.kind == "audio" else GLYPH_DOWN,
                          pixel=2, gap=1, on_color="#D7191A")
        kw.addStretch(1)
        kw.addWidget(glyph, 0, Qt.AlignmentFlag.AlignCenter)
        kw.addStretch(1)
        lay.addWidget(kind_wrap, 0, Qt.AlignmentFlag.AlignVCenter)

        info = QVBoxLayout()
        info.setSpacing(3)

        self.title = QLabel(entry.title[:120])
        self.title.setObjectName("Title")
        self.title.setWordWrap(True)

        meta_text = (
            f"{entry.uploader or 'Unknown'}  \u00B7  "
            f"{entry.quality.upper()}  \u00B7  {self._size_human(entry.size)}"
        )
        self.meta = QLabel(meta_text)
        self.meta.setObjectName("Meta")

        path_lbl = QLabel(str(Path(entry.path).name))
        path_lbl.setObjectName("MetaDim")

        info.addWidget(self.title)
        info.addWidget(self.meta)
        info.addWidget(path_lbl)

        self.btn_open = QPushButton("OPEN  \u2197")
        self.btn_open.setObjectName("Ghost")
        self.btn_open.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_open.clicked.connect(self._open_folder)

        lay.addLayout(info, 1)
        lay.addWidget(self.btn_open, 0, Qt.AlignmentFlag.AlignVCenter)
        self.setToolTip(entry.path)

    def _size_human(self, n: int) -> str:
        if not n:
            return "\u2014"
        x = float(n)
        for unit in ("B", "KB", "MB", "GB", "TB"):
            if abs(x) < 1024:
                return f"{x:.1f} {unit}"
            x /= 1024
        return f"{x:.1f} PB"

    def _open_folder(self) -> None:
        p = Path(self.entry.path)
        if not p.exists():
            return
        try:
            if sys.platform.startswith("win"):
                subprocess.Popen(["explorer", "/select,", str(p)])
            elif sys.platform == "darwin":
                subprocess.Popen(["open", "-R", str(p)])
            else:
                subprocess.Popen(["xdg-open", str(p.parent)])
        except Exception:
            pass


class HistoryPanel(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 14, 16, 16)
        lay.setSpacing(12)

        # Header
        header = QHBoxLayout()
        header.setSpacing(8)
        title = QLabel("HISTORY  \u00B7  LAST  50")
        title.setObjectName("Section")
        header.addWidget(title)
        header.addStretch(1)
        self.count_lbl = QLabel("")
        self.count_lbl.setObjectName("Status")
        header.addWidget(self.count_lbl)
        lay.addLayout(header)

        self.list = QListWidget()
        self.list.setObjectName("HistoryList")
        self.list.setUniformItemSizes(True)
        self.list.setVerticalScrollMode(QListView.ScrollMode.ScrollPerPixel)
        lay.addWidget(self.list, 1)

        self.refresh()

    def refresh(self) -> None:
        self.list.clear()
        items = history.load_all()
        self.count_lbl.setText(f"{len(items)} / 50")
        if not items:
            empty = QLabel("NO DOWNLOADS YET\n\nDOWNLOAD SOMETHING TO SEE IT HERE")
            empty.setObjectName("Empty")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            item = QListWidgetItem(self.list)
            item.setSizeHint(empty.sizeHint())
            self.list.addItem(item)
            self.list.setItemWidget(item, empty)
            return
        for e in items:
            row = _Item(e)
            item = QListWidgetItem(self.list)
            item.setSizeHint(row.sizeHint())
            self.list.addItem(item)
            self.list.setItemWidget(item, row)
