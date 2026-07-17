"""Playlist panel: list with index, title, duration; ALL/NONE/INVERT; DOWNLOAD SELECTED/ALL."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox, QFrame, QHBoxLayout, QLabel, QListView, QListWidget, QListWidgetItem,
    QPushButton, QVBoxLayout,
)

from core.metadata import VideoInfo


class _Row(QFrame):
    def __init__(self, info: VideoInfo, index: int, parent=None):
        super().__init__(parent)
        self.setObjectName("CardInset")
        self.info = info
        self.index = index

        lay = QHBoxLayout(self)
        lay.setContentsMargins(14, 10, 14, 10)
        lay.setSpacing(14)

        self.checkbox = QCheckBox()
        self.checkbox.setCursor(Qt.CursorShape.PointingHandCursor)
        self.checkbox.stateChanged.connect(self._on_check)

        self.idx_lbl = QLabel(f"{index:02d}")
        self.idx_lbl.setObjectName("Status")
        self.idx_lbl.setFixedWidth(26)

        text_col = QVBoxLayout()
        text_col.setSpacing(2)
        self.title = QLabel(info.title[:90])
        self.title.setObjectName("Title")
        self.title.setWordWrap(True)
        self.meta = QLabel(f"{info.uploader or 'Unknown'}  ·  {info.duration_str}")
        self.meta.setObjectName("Meta")
        text_col.addWidget(self.title)
        text_col.addWidget(self.meta)

        lay.addWidget(self.checkbox)
        lay.addWidget(self.idx_lbl)
        lay.addLayout(text_col, 1)
        self.setToolTip(f"{info.title}\n{info.uploader}\n{info.duration_str}")

    def _on_check(self) -> None:
        # Visual feedback
        self.setObjectName("Card" if self.checkbox.isChecked() else "CardInset")
        self.style().unpolish(self)
        self.style().polish(self)

    def isChecked(self) -> bool:
        return self.checkbox.isChecked()

    def setChecked(self, v: bool) -> None:
        self.checkbox.setChecked(v)


class PlaylistPanel(QFrame):
    selection_changed = Signal()
    download_selected = Signal()
    download_all = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("Card")
        self._rows: list[_Row] = []

        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 14, 16, 16)
        lay.setSpacing(12)

        # Header
        header = QHBoxLayout()
        header.setSpacing(8)
        self.title_lbl = QLabel("PLAYLIST")
        self.title_lbl.setObjectName("Section")
        header.addWidget(self.title_lbl)
        header.addStretch(1)
        self.count_lbl = QLabel("0 / 0")
        self.count_lbl.setObjectName("Status")
        header.addWidget(self.count_lbl)
        lay.addLayout(header)

        self.subtitle_lbl = QLabel("")
        self.subtitle_lbl.setObjectName("Meta")
        self.subtitle_lbl.setWordWrap(True)
        lay.addWidget(self.subtitle_lbl)

        # Empty state (hidden when entries exist)
        self._empty_lbl = QLabel("This playlist is empty or private.")
        self._empty_lbl.setObjectName("Meta")
        self._empty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_lbl.setWordWrap(True)
        self._empty_lbl.setVisible(False)
        lay.addWidget(self._empty_lbl)

        # Buttons row
        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)
        self.btn_all = QPushButton("ALL")
        self.btn_none = QPushButton("NONE")
        self.btn_inv = QPushButton("INVERT")
        for b in (self.btn_all, self.btn_none, self.btn_inv):
            b.setObjectName("Ghost")
            b.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_all.clicked.connect(self.select_all)
        self.btn_none.clicked.connect(self.select_none)
        self.btn_inv.clicked.connect(self.invert)
        btn_row.addWidget(self.btn_all)
        btn_row.addWidget(self.btn_none)
        btn_row.addWidget(self.btn_inv)
        btn_row.addStretch(1)
        lay.addLayout(btn_row)

        # List
        self.list = QListWidget()
        self.list.setObjectName("PlaylistList")
        self.list.setUniformItemSizes(True)
        self.list.setVerticalScrollMode(QListView.ScrollMode.ScrollPerPixel)
        lay.addWidget(self.list, 1)

        # Bottom buttons
        bottom = QHBoxLayout()
        bottom.setSpacing(8)
        self.btn_dl_selected = QPushButton("↓  DOWNLOAD SELECTED")
        self.btn_dl_selected.setObjectName("Primary")
        self.btn_dl_selected.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_dl_selected.clicked.connect(self.download_selected.emit)

        self.btn_dl_all = QPushButton("↓↓  DOWNLOAD ALL")
        self.btn_dl_all.setObjectName("Ghost")
        self.btn_dl_all.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_dl_all.clicked.connect(self.download_all.emit)

        bottom.addWidget(self.btn_dl_selected, 1)
        bottom.addWidget(self.btn_dl_all, 0)
        lay.addLayout(bottom)

        self.setVisible(False)

    def set_playlist(self, title: str, uploader: str,
                     entries: list[VideoInfo],
                     precheck_ids: set[str]) -> None:
        from PySide6.QtCore import QTimer
        # Clean up old row widgets
        for r in self._rows:
            r.setParent(None)
            r.deleteLater()
        self._rows.clear()
        self.list.clear()

        self.title_lbl.setText("PLAYLIST  ·  " + (title[:60] or "UNTITLED"))
        n = len(entries)
        self.subtitle_lbl.setText(
            f"{uploader or 'Unknown'}  ·  {n} video{'s' if n != 1 else ''}"
        )

        for i, info in enumerate(entries, 1):
            row = _Row(info, i)
            if info.id in precheck_ids:
                row.setChecked(True)
            row.checkbox.stateChanged.connect(self._on_change)
            self._rows.append(row)

            item = QListWidgetItem(self.list)
            item.setSizeHint(row.sizeHint())
            self.list.addItem(item)
            self.list.setItemWidget(item, row)

        self.setVisible(True)
        # Show empty state when no entries
        if n == 0:
            self._empty_lbl.setVisible(True)
            self.btn_dl_selected.setEnabled(False)
            self.btn_dl_all.setEnabled(False)
        else:
            self._empty_lbl.setVisible(False)
        self._refresh_count()

        # Stagger animation
        from ui.anim import slide_up_stagger
        QTimer.singleShot(20, lambda: slide_up_stagger(self._rows, delay_ms=18, distance=6))

    def _on_change(self) -> None:
        self._refresh_count()
        self.selection_changed.emit()

    def _refresh_count(self) -> None:
        n_total = len(self._rows)
        n_checked = sum(1 for r in self._rows if r.isChecked())
        self.count_lbl.setText(f"{n_checked} / {n_total}")
        self.btn_dl_selected.setEnabled(n_checked > 0)
        self.btn_dl_all.setEnabled(n_total > 0)

    def select_all(self) -> None:
        for r in self._rows:
            r.setChecked(True)

    def select_none(self) -> None:
        for r in self._rows:
            r.setChecked(False)

    def invert(self) -> None:
        for r in self._rows:
            r.setChecked(not r.isChecked())

    def selected_entries(self) -> list[VideoInfo]:
        return [r.info for r in self._rows if r.isChecked()]

    def all_entries(self) -> list[VideoInfo]:
        return [r.info for r in self._rows]
