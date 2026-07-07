"""Channel bulk downloader panel.

Layout:
  [ URL input .............................. ] [ Fetch ]
  [ Videos ] [ Shorts ] [ All ]  ·  Count: [   10  ]  ·  Quality: [ 1080p ▾ ]
  ┌────────────────────────────────────────────────┐
  │ ☐ 01  [thumb] Title 1  ·  1:30  ·  uploader    │
  │ ☐ 02  [thumb] Title 2  ·  2:15  ·  uploader    │
  │ ...                                             │
  └────────────────────────────────────────────────┘
  [ SELECT ALL ]                  0 / 0 selected  [ DOWNLOAD ▾ ]
"""
from __future__ import annotations

import re
from pathlib import Path

from PySide6.QtCore import QObject, QSize, Qt, QThread, QTimer, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QFrame, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QScrollArea, QSizePolicy, QSpinBox, QVBoxLayout, QWidget,
)

from core.formats import MP3_QUALITIES, MP4_QUALITIES, QualityOption, find_by_key
from ui.widgets.icon_button import IconTextButton, PixelButton


def _human_dur(seconds: int) -> str:
    if not seconds:
        return "—"
    s = int(seconds)
    if s < 60:
        return f"{s}s"
    m, s = divmod(s, 60)
    if m < 60:
        return f"{m}:{s:02d}"
    h, m = divmod(m, 60)
    return f"{h}:{m:02d}:{s:02d}"


# Public YouTube thumbnail URL. Used as a guaranteed fallback for entries that
# come from ``extract_flat=True`` (where the ``thumbnails`` list sometimes
# contains the channel's avatar rather than the per-video frame).
_YT_THUMB = "https://i.ytimg.com/vi/{id}/hqdefault.jpg"


def _entry_thumb_url(entry: dict) -> str:
    """Best-effort thumbnail URL for a flat entry — YouTube or generic."""
    eid = entry.get("id") or ""
    eurl = (entry.get("url") or entry.get("webpage_url") or "").lower()
    if "youtube.com" in eurl or "youtu.be" in eurl:
        if eid:
            return _YT_THUMB.format(id=eid)
    thumbs = entry.get("thumbnails") or []
    for t in thumbs:
        u = (t.get("url") or "").strip()
        if u and "googleusercontent" not in u:
            return u
    if eid:
        return _YT_THUMB.format(id=eid)
    return ""


class _RowThumb(QThread):
    """Loads a single row's thumbnail (async, cached to disk)."""
    loaded = Signal(str, QPixmap)
    failed = Signal(str)

    def __init__(self, video_id: str, url: str, parent=None):
        super().__init__(parent)
        self.video_id = video_id
        self.url = url

    def run(self) -> None:
        try:
            from core import config
            cache = config.CONFIG_DIR / "thumbs" / f"{self.video_id}.jpg"
            cache.parent.mkdir(parents=True, exist_ok=True)
            if not cache.exists():
                import requests
                try:
                    r = requests.get(
                        self.url, timeout=8,
                        headers={"User-Agent": "Mozilla/5.0"},
                    )
                    if r.status_code == 200 and r.content:
                        cache.write_bytes(r.content)
                except Exception:
                    pass
            if self.isInterruptionRequested():
                return
            pix = QPixmap(str(cache))
            if pix.isNull():
                self.failed.emit(self.video_id)
                return
            pix = pix.scaled(
                QSize(96, 54),
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )
            self.loaded.emit(self.video_id, pix)
        except Exception:
            self.failed.emit(self.video_id)


# Module-level singleton — caps concurrent thumb downloads so a 500-row
# channel doesn't fire 500 HTTP requests at once.
class _ThumbQueue(QObject):
    """Process thumbnail URLs one at a time. Throttled worker queue."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._pending: list[tuple[str, str, "_ChannelRow"]] = []
        self._current_row: "_ChannelRow | None" = None
        self._current_vid: str = ""
        self._active = False

    def reset(self) -> None:
        """Cancel in-flight and clear all pending thumbnail requests."""
        self._pending.clear()
        if self._active and hasattr(self, '_loader') and self._loader:
            self._loader.requestInterruption()
            self._loader.deleteLater()
        self._active = False
        self._current_vid = ""
        self._current_row = None
        self._loader = None

    def request(self, vid_id: str, url: str, row: "_ChannelRow") -> None:
        # Dedupe — if a request for this vid_id is already pending or
        # in-flight, don't queue a second one.
        if self._current_vid == vid_id:
            return
        for v, _, _ in self._pending:
            if v == vid_id:
                return
        self._pending.append((vid_id, url, row))
        self._pump()

    def _pump(self) -> None:
        if self._active or not self._pending:
            return
        vid_id, url, row = self._pending.pop(0)
        self._active = True
        self._current_vid = vid_id
        self._current_row = row
        loader = _RowThumb(vid_id, url, self)
        loader.finished.connect(self._on_done)
        loader.loaded.connect(self._on_loaded)
        loader.failed.connect(self._on_failed)
        self._loader = loader
        loader.start()

    def _on_loaded(self, vid_id: str, pix: QPixmap) -> None:
        if vid_id == self._current_vid and self._current_row is not None:
            self._current_row._on_thumb(vid_id, pix)

    def _on_failed(self, vid_id: str) -> None:
        if vid_id == self._current_vid and self._current_row is not None:
            self._current_row._on_thumb_fail(vid_id)

    def _on_done(self) -> None:
        self._active = False
        self._current_vid = ""
        self._current_row = None
        if self._loader is not None:
            self._loader.deleteLater()
            self._loader = None
        # Process next — defer to next event loop tick so we don't block.
        QTimer.singleShot(0, self._pump)


_THUMB_QUEUE: _ThumbQueue | None = None


def _thumb_queue() -> _ThumbQueue:
    global _THUMB_QUEUE
    if _THUMB_QUEUE is None:
        _THUMB_QUEUE = _ThumbQueue()
    return _THUMB_QUEUE


class _ChannelRow(QFrame):
    toggle = Signal()

    def __init__(self, entry: dict, idx: int, parent=None):
        super().__init__(parent)
        self.setObjectName("CardInset")
        self._entry = entry
        self._video_id = entry.get("id", "") or f"_ch_{idx}"
        self._loader: _RowThumb | None = None
        self._thumb_url = _entry_thumb_url(entry)
        self._thumb_started = False

        lay = QHBoxLayout(self)
        lay.setContentsMargins(10, 8, 10, 8)
        lay.setSpacing(10)

        self.chk = QCheckBox()
        self.chk.setCursor(Qt.CursorShape.PointingHandCursor)
        self.chk.toggled.connect(self.toggle)
        lay.addWidget(self.chk)

        idx_lbl = QLabel(f"{idx:02d}")
        idx_lbl.setObjectName("StatusDim")
        idx_lbl.setFixedWidth(20)
        lay.addWidget(idx_lbl)

        # Thumbnail (96x54, ratio 16:9)
        self.thumb_frame = QFrame()
        self.thumb_frame.setObjectName("ThumbFrame")
        self.thumb_frame.setFixedSize(96, 54)
        tf_lay = QVBoxLayout(self.thumb_frame)
        tf_lay.setContentsMargins(0, 0, 0, 0)
        tf_lay.setSpacing(0)
        self.thumb = QLabel("\u2026")
        self.thumb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.thumb.setStyleSheet("color: #3A3A3A; background: transparent; font-size: 9pt;")
        tf_lay.addWidget(self.thumb)
        lay.addWidget(self.thumb_frame, 0, Qt.AlignmentFlag.AlignVCenter)

        # Title block (vertical: title + meta)
        info = QVBoxLayout()
        info.setContentsMargins(0, 0, 0, 0)
        info.setSpacing(1)

        self.title_lbl = QLabel(entry.get("title", "Untitled"))
        self.title_lbl.setObjectName("Title")
        self.title_lbl.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.title_lbl.setMaximumHeight(22)
        info.addWidget(self.title_lbl)

        uploader = entry.get("uploader", "")
        dur = _human_dur(int(entry.get("duration") or 0))
        meta_parts = []
        if uploader:
            meta_parts.append(uploader)
        meta_parts.append(dur)
        self.meta_lbl = QLabel("  ·  ".join(meta_parts))
        self.meta_lbl.setObjectName("Meta")
        info.addWidget(self.meta_lbl)

        lay.addLayout(info, 1)

    def start_thumb(self) -> None:
        """Begin loading the thumbnail (called once by the panel when the
        row is visible). Idempotent — safe to call multiple times."""
        if self._thumb_started or not self._thumb_url:
            return
        self._thumb_started = True
        _thumb_queue().request(self._video_id, self._thumb_url, self)

    def showEvent(self, e) -> None:
        # Lazy-load when the row becomes visible — keeps page switching
        # instant even on channels with hundreds of videos.
        super().showEvent(e)
        self.start_thumb()

    def _on_thumb(self, vid_id: str, pix: QPixmap) -> None:
        if vid_id == self._video_id:
            self.thumb.setText("")
            self.thumb.setPixmap(pix)

    def _on_thumb_fail(self, vid_id: str) -> None:
        if vid_id == self._video_id:
            self.thumb.setText("NO IMG")

    def is_checked(self) -> bool:
        return self.chk.isChecked()

    def set_checked(self, on: bool) -> None:
        self.chk.setChecked(on)

    @property
    def entry(self) -> dict:
        return self._entry


class ChannelPanel(QFrame):
    fetch_requested = Signal(str, str, int)  # url, content_type, max_count
    download_requested = Signal(list)         # list of entry dicts
    quality_changed = Signal(QualityOption)

    def __init__(self, theme: dict | None = None, parent=None):
        super().__init__(parent)
        self.setObjectName("TexPage")
        self._rows: list[_ChannelRow] = []
        self._channel_title: str = ""
        self._theme = theme or {
            "fg": "#FFFFFF", "fg_dim": "#9A9A9A", "accent": "#D7191A",
        }

        outer = QVBoxLayout(self)
        outer.setContentsMargins(20, 18, 20, 18)
        outer.setSpacing(12)

        # Title
        title = QLabel("Channels")
        title.setObjectName("XL")
        outer.addWidget(title)

        # URL row
        url_row = QHBoxLayout()
        url_row.setSpacing(8)
        self.url_input = QLineEdit()
        self.url_input.setObjectName("UrlInput")
        self.url_input.setPlaceholderText(
            "Paste a channel URL  ·  youtube.com/@name  ·  tiktok.com/@user  ·  instagram.com/user"
        )
        self.url_input.setFixedHeight(40)
        self.url_input.returnPressed.connect(self._on_fetch)
        url_row.addWidget(self.url_input, 1)
        self.fetch_btn = PixelButton("fetch", "FETCH", size=14, height=40,
                                     theme=self._theme)
        self.fetch_btn.setFixedWidth(130)
        self.fetch_btn.clicked.connect(self._on_fetch)
        url_row.addWidget(self.fetch_btn)
        outer.addLayout(url_row)

        # Filter row: content chips + count + quality
        filt_row = QHBoxLayout()
        filt_row.setSpacing(8)
        filt_lbl = QLabel("CONTENT")
        filt_lbl.setObjectName("Section")
        filt_row.addWidget(filt_lbl)

        self.filt_group: dict[str, QPushButton] = {}
        for i, key in enumerate(("videos", "shorts", "all")):
            b = QPushButton(key.upper())
            b.setObjectName("Chip")
            b.setCheckable(True)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setFixedHeight(30)
            if key == "videos":
                b.setChecked(True)
            b.clicked.connect(lambda _=False, k=key: self._on_filter(k))
            filt_row.addWidget(b)
            self.filt_group[key] = b

        filt_row.addSpacing(20)
        count_lbl = QLabel("COUNT")
        count_lbl.setObjectName("Section")
        filt_row.addWidget(count_lbl)

        self.count_spin = QSpinBox()
        self.count_spin.setRange(1, 500)
        self.count_spin.setValue(10)
        self.count_spin.setFixedWidth(70)
        self.count_spin.setFixedHeight(30)
        filt_row.addWidget(self.count_spin)

        filt_row.addSpacing(20)
        qlbl = QLabel("QUALITY")
        qlbl.setObjectName("Section")
        filt_row.addWidget(qlbl)

        # Local quality picker so the channel downloads don't share state
        # with the main page's format picker.
        self.quality_combo = QComboBox()
        self.quality_combo.setObjectName("QualityCombo")
        self.quality_combo.setFixedHeight(30)
        self.quality_combo.setMinimumWidth(160)
        for opt in MP4_QUALITIES + MP3_QUALITIES:
            self.quality_combo.addItem(opt.label, opt.key)
        # Default to 1080p
        for i in range(self.quality_combo.count()):
            if self.quality_combo.itemData(i) == "1080p":
                self.quality_combo.setCurrentIndex(i)
                break
        self.quality_combo.currentIndexChanged.connect(self._on_quality_changed)
        filt_row.addWidget(self.quality_combo)

        filt_row.addStretch(1)
        outer.addLayout(filt_row)

        # Status line
        self.status_lbl = QLabel("Paste a channel URL and press Fetch.")
        self.status_lbl.setObjectName("MetaDim")
        outer.addWidget(self.status_lbl)

        # Video list
        self.list_frame = QFrame()
        self.list_frame.setObjectName("CardFlat")
        list_outer = QVBoxLayout(self.list_frame)
        list_outer.setContentsMargins(0, 0, 0, 0)
        list_outer.setSpacing(1)
        self._list_layout = list_outer

        # Scroll area wrapping the list
        self.scroll = QScrollArea()
        self.scroll.setObjectName("ScrollArea")
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setWidget(self.list_frame)
        self.scroll.setMinimumHeight(260)
        outer.addWidget(self.scroll, 1)

        # Bottom action bar
        action_row = QHBoxLayout()
        action_row.setSpacing(8)
        self.select_all_btn = QPushButton("SELECT ALL")
        self.select_all_btn.setObjectName("Ghost")
        self.select_all_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.select_all_btn.clicked.connect(self._on_select_all)
        self.select_all_btn.setEnabled(False)
        action_row.addWidget(self.select_all_btn)

        action_row.addStretch(1)

        self.count_lbl = QLabel("0 selected")
        self.count_lbl.setObjectName("Meta")
        action_row.addWidget(self.count_lbl)

        self.download_btn = IconTextButton("download", "DOWNLOAD SELECTED",
                                            size=14, height=36, theme=self._theme)
        self.download_btn.clicked.connect(self._on_download)
        self.download_btn.setEnabled(False)
        action_row.addWidget(self.download_btn)

        outer.addLayout(action_row)

        self._current_filter = "videos"
        self._current_quality = self.selected_quality()
        self._pending_entries: list = []
        self._batch_size = 30

    # --- public API ---
    def set_channel(self, channel) -> None:
        """Populate the list from a ChannelInfo — batched so the UI stays
        responsive even for 100+ entries."""
        self._channel_title = channel.title
        self._clear_rows()
        self._pending_entries = list(enumerate(channel.entries, 1))
        self._batch_size = 30
        suffix = " (truncated)" if channel.truncated else ""
        n = len(channel.entries)
        self.status_lbl.setText(
            f"{channel.title}  ·  {channel.uploader}  ·  {n} item{'s' if n != 1 else ''}{suffix}"
        )
        self.select_all_btn.setEnabled(n > 0)
        self.download_btn.setEnabled(n > 0)
        self._update_count()
        self._add_batch()

    def _add_batch(self) -> None:
        """Add up to _batch_size rows, then yield back to the event loop so
        the UI can repaint between batches."""
        if not self._pending_entries:
            return
        batch = self._pending_entries[: self._batch_size]
        self._pending_entries = self._pending_entries[self._batch_size :]
        for i, e in batch:
            row = _ChannelRow(e, i)
            row.toggle.connect(self._update_count)
            self._list_layout.addWidget(row)
            self._rows.append(row)
        if self._pending_entries:
            QTimer.singleShot(0, self._add_batch)

    def set_status(self, msg: str) -> None:
        self.status_lbl.setText(msg)

    def set_fetching(self, fetching: bool) -> None:
        self.fetch_btn.setEnabled(not fetching)
        self.fetch_btn.set_text("… FETCHING" if fetching else "FETCH")
        self.url_input.setReadOnly(fetching)

    def selected_entries(self) -> list:
        return [r.entry for r in self._rows if r.is_checked()]

    def selected_quality(self) -> QualityOption:
        key = self.quality_combo.currentData() or "1080p"
        return find_by_key(key) or MP4_QUALITIES[2]

    # --- internals ---
    def _on_filter(self, key: str) -> None:
        self._current_filter = key
        for k, b in self.filt_group.items():
            b.setChecked(k == key)

    def _on_quality_changed(self, _idx: int) -> None:
        self._current_quality = self.selected_quality()
        self.quality_changed.emit(self._current_quality)

    def set_theme(self, theme: dict) -> None:
        self._theme = theme
        if hasattr(self, "fetch_btn") and hasattr(self.fetch_btn, "set_theme"):
            self.fetch_btn.set_theme(theme)
        if hasattr(self, "download_btn") and hasattr(self.download_btn, "set_theme"):
            self.download_btn.set_theme(theme)

    def _on_fetch(self) -> None:
        url = self.url_input.text().strip()
        if not url:
            return
        self.set_fetching(True)
        self.set_status("Fetching channel…")
        self.fetch_requested.emit(url, self._current_filter, int(self.count_spin.value()))

    def _on_select_all(self) -> None:
        if not self._rows:
            return
        all_on = all(r.is_checked() for r in self._rows)
        for r in self._rows:
            r.set_checked(not all_on)
        self._update_count()

    def _on_download(self) -> None:
        entries = self.selected_entries()
        if entries:
            self.download_requested.emit(entries)

    def _update_count(self) -> None:
        n = sum(1 for r in self._rows if r.is_checked())
        self.count_lbl.setText(f"{n} of {len(self._rows)} selected")
        self.download_btn.setEnabled(n > 0)
        if self._rows:
            all_on = all(r.is_checked() for r in self._rows)
            self.select_all_btn.setText("DESELECT ALL" if all_on else "SELECT ALL")

    def _clear_rows(self) -> None:
        self._pending_entries.clear()
        # Cancel any in-flight thumbnail loads
        _thumb_queue().reset()
        for r in self._rows:
            r.setParent(None)
            r.deleteLater()
        self._rows.clear()
