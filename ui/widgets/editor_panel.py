"""Editor panel — trim a video by URL with a visual timeline.

Workflow:
1. Paste a URL → fetch metadata (duration, title, thumbnail).
2. A slider / range selector shows the full duration.
3. User drags start/end handles to select the segment.
4. Click "Trim & Download" → downloads with ``--download-sections``.
"""
from __future__ import annotations

import time
from PySide6.QtCore import QThread, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QPushButton, QScrollArea,
    QVBoxLayout, QWidget,
)

from core import config
from core.formats import MP4_QUALITIES, find_by_key


# ─── Slider / Range selector ───────────────────────────────────────────

class _RangeSlider(QWidget):
    """Two-handle range slider with time labels."""
    range_changed = Signal(float, float)  # start_sec, end_sec

    def __init__(self, duration: float = 0.0, parent=None):
        super().__init__(parent)
        self._duration = max(0.0, duration)
        self._start = 0.0
        self._end = duration if duration > 0 else 0.0
        self._dragging = None  # "start" | "end" | None
        self._accent = QColor("#D7191A")
        self._track = QColor("#2A2A2A")
        self._handle_size = 14
        self._track_h = 6
        self.setMinimumHeight(56)
        self.setMaximumHeight(56)

    def set_duration(self, d: float) -> None:
        self._duration = max(0.0, d)
        self._start = 0.0
        self._end = self._duration
        self.update()
        self.range_changed.emit(self._start, self._end)

    def set_range(self, s: float, e: float) -> None:
        self._start = max(0.0, min(s, self._duration))
        self._end = max(0.0, min(e, self._duration))
        self.update()
        self.range_changed.emit(self._start, self._end)

    def values(self) -> tuple[float, float]:
        return self._start, self._end

    def _sec_to_x(self, sec: float) -> float:
        if self._duration <= 0:
            return 0.0
        margin = 30
        w = self.width() - 2 * margin
        return margin + (sec / self._duration) * w

    def _x_to_sec(self, x: float) -> float:
        margin = 30
        w = self.width() - 2 * margin
        if w <= 0:
            return 0.0
        ratio = (x - margin) / w
        ratio = max(0.0, min(1.0, ratio))
        return ratio * self._duration

    def _near_handle(self, x: float) -> str | None:
        sx = self._sec_to_x(self._start)
        ex = self._sec_to_x(self._end)
        threshold = self._handle_size + 4
        if abs(x - sx) <= threshold:
            return "start"
        if abs(x - ex) <= threshold:
            return "end"
        return None

    def mousePressEvent(self, e) -> None:
        if e.button() == Qt.MouseButton.LeftButton:
            self._dragging = self._near_handle(e.position().x())
            if self._dragging is None:
                # Click on the track → jump start handle here
                sec = self._x_to_sec(e.position().x())
                self._start = sec
                self._dragging = "start"
            self.update()

    def mouseMoveEvent(self, e) -> None:
        if self._dragging:
            sec = self._x_to_sec(e.position().x())
            if self._dragging == "start":
                self._start = min(sec, self._end - 0.1) if self._duration > 0 else 0.0
            else:
                self._end = max(sec, self._start + 0.1) if self._duration > 0 else 0.0
            self.update()
            self.range_changed.emit(self._start, self._end)

    def mouseReleaseEvent(self, e) -> None:
        if e.button() == Qt.MouseButton.LeftButton:
            self._dragging = None

    def paintEvent(self, _e) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        margin = 30
        w = self.width() - 2 * margin
        cy = 24

        # Track background
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(self._track)
        p.drawRoundedRect(margin, cy - self._track_h // 2, w, self._track_h, 3, 3)

        # Selected range
        if self._duration > 0:
            sx = self._sec_to_x(self._start)
            ex = self._sec_to_x(self._end)
            sel_w = max(0, ex - sx)
            p.setBrush(self._accent)
            p.drawRoundedRect(int(sx), cy - self._track_h // 2, int(sel_w), self._track_h, 3, 3)

            # Handles
            hs = self._handle_size
            for hx in (sx, ex):
                p.setPen(QPen(self._accent, 2))
                p.setBrush(QColor("#1A1A1A"))
                p.drawRoundedRect(int(hx - hs // 2), cy - hs // 2, hs, hs, 4, 4)

            # Time labels
            p.setPen(QColor("#AAAAAA"))
            p.setFont(p.font())  # use default
            p.drawText(int(sx) - 25, cy + 22, _fmt_time(self._start))
            p.drawText(int(ex) - 25, cy + 22, _fmt_time(self._end))

            # Duration label in center
            mid = (sx + ex) / 2
            p.setPen(QColor("#FFFFFF"))
            dur_text = _fmt_time(self._end - self._start)
            p.drawText(int(mid) - 25, cy - 12, dur_text)
        else:
            p.setPen(QColor("#666666"))
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "No video loaded")

        p.end()


def _fmt_time(s: float) -> str:
    s = max(0.0, s)
    h, rem = divmod(int(s), 3600)
    m, sec = divmod(rem, 60)
    if h:
        return f"{h}:{m:02d}:{sec:02d}"
    return f"{m}:{sec:02d}"


# ─── Fetch worker ──────────────────────────────────────────────────────

class _EditorFetchWorker(QThread):
    ok = Signal(object)
    fail = Signal(str)

    def __init__(self, url: str, parent=None):
        super().__init__(parent)
        self.url = url

    def run(self) -> None:
        try:
            from core.metadata import fetch
            self.ok.emit(fetch(self.url))
        except Exception as e:
            from core.cookies import is_browser_cookie_error
            err = str(e)
            if is_browser_cookie_error(err):
                try:
                    self.ok.emit(fetch(self.url, no_cookies=True))
                    return
                except Exception as e2:
                    self.fail.emit(str(e2))
                    return
            self.fail.emit(err)


# ─── Editor Panel ──────────────────────────────────────────────────────

class EditorPanel(QFrame):
    trim_requested = Signal(str, float, float, object)  # url, start, end, quality

    def __init__(self, theme: dict | None = None, parent=None):
        super().__init__(parent)
        self.setObjectName("TexPage")
        self._theme = theme or {
            "fg": "#FFFFFF", "fg_dim": "#9A9A9A", "accent": "#D7191A",
        }
        self._result = None
        self._quality = MP4_QUALITIES[2]  # default 1080p
        self._worker: _EditorFetchWorker | None = None
        self._thumb_loader: "ThumbLoader | None" = None

        outer = QVBoxLayout(self)
        outer.setContentsMargins(20, 18, 20, 18)
        outer.setSpacing(12)

        # Header
        header = QHBoxLayout()
        header.setSpacing(8)
        title = QLabel("Editor")
        title.setObjectName("XL")
        header.addWidget(title)
        header.addStretch(1)
        outer.addLayout(header)

        # Description
        desc = QLabel("Paste a video URL, select a segment on the timeline, and download only that part.")
        desc.setObjectName("MetaDim")
        desc.setWordWrap(True)
        outer.addWidget(desc)

        # URL input row
        url_row = QHBoxLayout()
        url_row.setSpacing(8)
        self.url_input = _EditorUrlInput()
        self.url_input.fetch_requested.connect(self._on_fetch)
        url_row.addWidget(self.url_input, 1)
        outer.addLayout(url_row)

        # Info card (hidden until fetch)
        self.info_card = QFrame()
        self.info_card.setObjectName("Card")
        ic_lay = QHBoxLayout(self.info_card)
        ic_lay.setContentsMargins(14, 10, 14, 10)
        ic_lay.setSpacing(14)
        self.thumb_lbl = QLabel("—")
        self.thumb_lbl.setFixedSize(168, 94)
        self.thumb_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.thumb_lbl.setObjectName("CardInset")
        ic_lay.addWidget(self.thumb_lbl, 0, Qt.AlignmentFlag.AlignVCenter)
        info_col = QVBoxLayout()
        info_col.setSpacing(2)
        self.ed_title = QLabel("—")
        self.ed_title.setObjectName("TitleLg")
        self.ed_title.setWordWrap(True)
        self.ed_meta = QLabel("")
        self.ed_meta.setObjectName("Meta")
        info_col.addWidget(self.ed_title)
        info_col.addWidget(self.ed_meta)
        info_col.addStretch(1)
        ic_lay.addLayout(info_col, 1)
        self.info_card.setVisible(False)
        outer.addWidget(self.info_card)

        # Timeline card
        self.timeline_card = QFrame()
        self.timeline_card.setObjectName("Card")
        tc_lay = QVBoxLayout(self.timeline_card)
        tc_lay.setContentsMargins(14, 12, 14, 12)
        tc_lay.setSpacing(8)
        tl_header = QHBoxLayout()
        tl_header.setSpacing(8)
        tl_title = QLabel("TIMELINE")
        tl_title.setObjectName("Section")
        tl_header.addWidget(tl_title)
        tl_header.addStretch(1)
        self.range_lbl = QLabel("—")
        self.range_lbl.setObjectName("NumMed")
        tl_header.addWidget(self.range_lbl)
        tc_lay.addLayout(tl_header)
        self.slider = _RangeSlider()
        self.slider.range_changed.connect(self._on_range_changed)
        tc_lay.addWidget(self.slider)
        # Manual time inputs
        time_row = QHBoxLayout()
        time_row.setSpacing(12)
        self.start_input = _TimeEdit("START")
        self.start_input.time_changed.connect(self._on_manual_time)
        time_row.addWidget(self.start_input)
        time_row.addStretch(1)
        self.end_input = _TimeEdit("END")
        self.end_input.time_changed.connect(self._on_manual_time)
        time_row.addWidget(self.end_input)
        tc_lay.addLayout(time_row)
        self.timeline_card.setVisible(False)
        outer.addWidget(self.timeline_card)

        # Quality selector (simple row of ghost buttons)
        self.quality_row = QFrame()
        self.quality_row.setObjectName("Card")
        qr_lay = QHBoxLayout(self.quality_row)
        qr_lay.setContentsMargins(14, 10, 14, 10)
        qr_lay.setSpacing(6)
        ql = QLabel("QUALITY")
        ql.setObjectName("Section")
        qr_lay.addWidget(ql)
        self._q_btns: list[tuple[QPushButton, object]] = []
        for opt in MP4_QUALITIES:
            b = QPushButton(opt.label)
            b.setObjectName("ChipBtn")
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setCheckable(True)
            b.setProperty("qkey", opt.key)
            b.clicked.connect(lambda _=False, o=opt, btn=b: self._on_quality(o, btn))
            qr_lay.addWidget(b)
            self._q_btns.append((b, opt))
        # Default select 1080p
        for b, opt in self._q_btns:
            if opt.key == "1080p":
                b.setChecked(True)
                b.setObjectName("CardBright")
                break
        self.quality_row.setVisible(False)
        outer.addWidget(self.quality_row)

        # Trim button
        self.btn_trim = QPushButton("\u2702  TRIM & DOWNLOAD")
        self.btn_trim.setObjectName("Primary")
        self.btn_trim.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_trim.setFixedHeight(46)
        self.btn_trim.clicked.connect(self._on_trim)
        self.btn_trim.setVisible(False)
        outer.addWidget(self.btn_trim)

        outer.addStretch(1)

        # Status
        self.status_lbl = QLabel("")
        self.status_lbl.setObjectName("Status")
        outer.addWidget(self.status_lbl)

    def set_theme(self, theme: dict) -> None:
        self._theme = theme
        if hasattr(self, "slider"):
            self.slider._accent = QColor(theme.get("accent", "#D7191A"))

    # ── Handlers ──

    def _on_fetch(self, url: str) -> None:
        if not url.strip():
            return
        self.status_lbl.setText("Fetching\u2026")
        self.url_input.set_loading(True)
        self.btn_trim.setVisible(False)
        # Kill previous thumbnail loader
        self._kill_thumb_loader()
        # Kill previous worker
        if self._worker is not None:
            try:
                self._worker.ok.disconnect()
                self._worker.fail.disconnect()
            except RuntimeError:
                pass
            if self._worker.isRunning():
                self._worker.requestInterruption()
                self._worker.quit()
                self._worker.wait(3000)
        self._worker = _EditorFetchWorker(url)
        self._worker.ok.connect(self._on_fetch_ok)
        self._worker.fail.connect(self._on_fetch_fail)
        self._worker.start()

    def _on_fetch_ok(self, result) -> None:
        self.url_input.set_loading(False)
        if self._worker is not None:
            try:
                self._worker.ok.disconnect()
                self._worker.fail.disconnect()
            except RuntimeError:
                pass
            self._worker.deleteLater()
            self._worker = None
        self._result = result
        self.status_lbl.setText("")
        if result.kind == "single" and result.video:
            v = result.video
            self.ed_title.setText(v.title)
            self.ed_meta.setText(f"{v.uploader or 'Unknown'}  \u00B7  {v.duration_str}")
            self.info_card.setVisible(True)
            self.timeline_card.setVisible(True)
            self.quality_row.setVisible(True)
            self.btn_trim.setVisible(True)
            self.slider.set_duration(v.duration)
            self.start_input.set_max(v.duration)
            self.end_input.set_max(v.duration)
            self.end_input.set_time(v.duration)
            self._on_range_changed(0.0, v.duration)
            # Load thumbnail async
            if v.thumbnail:
                self._load_thumb(v.id, v.thumbnail)
        elif result.kind == "playlist":
            self.status_lbl.setText("Playlists are not supported in the Editor. Use the Download tab.")
        else:
            self.status_lbl.setText("Could not load video info.")

    def _on_fetch_fail(self, err: str) -> None:
        self.url_input.set_loading(False)
        if self._worker is not None:
            try:
                self._worker.ok.disconnect()
                self._worker.fail.disconnect()
            except RuntimeError:
                pass
            self._worker.deleteLater()
            self._worker = None
        self.status_lbl.setText(f"Error \u00B7 {err}")
        self.info_card.setVisible(False)
        self.timeline_card.setVisible(False)
        self.quality_row.setVisible(False)
        self.btn_trim.setVisible(False)

    def _on_range_changed(self, s: float, e: float) -> None:
        self.range_lbl.setText(f"{_fmt_time(s)}  \u2192  {_fmt_time(e)}  ({_fmt_time(e - s)})")
        self.start_input.blockSignals(True)
        self.end_input.blockSignals(True)
        self.start_input.set_time(s)
        self.end_input.set_time(e)
        self.start_input.blockSignals(False)
        self.end_input.blockSignals(False)

    def _on_manual_time(self) -> None:
        s = self.start_input.time()
        e = self.end_input.time()
        if s < e:
            self.slider.set_range(s, e)

    def _on_quality(self, opt, btn: QPushButton) -> None:
        self._quality = opt
        for b, _ in self._q_btns:
            b.setChecked(False)
            b.setObjectName("ChipBtn")
            b.style().unpolish(b)
            b.style().polish(b)
        btn.setChecked(True)
        btn.setObjectName("CardBright")
        btn.style().unpolish(btn)
        btn.style().polish(btn)

    def _on_trim(self) -> None:
        if not self._result or self._result.kind != "single" or not self._result.video:
            return
        s, e = self.slider.values()
        if e - s < 1.0:
            self.status_lbl.setText("Select at least 1 second to trim.")
            return
        v = self._result.video
        self.trim_requested.emit(v.webpage_url, s, e, self._quality)
        self.status_lbl.setText(f"Trimming {_fmt_time(s)} \u2192 {_fmt_time(e)} queued.")

    def _load_thumb(self, video_id: str, url: str) -> None:
        # Kill any previous thumb loader first
        self._kill_thumb_loader()
        from ui.widgets.video_card import ThumbLoader
        loader = ThumbLoader(video_id, url, self)
        self._thumb_loader = loader
        def _on_loaded(vid, pix):
            if vid == video_id and self._thumb_loader is loader:
                self.thumb_lbl.setPixmap(
                    pix.scaled(168, 94, Qt.AspectRatioMode.KeepAspectRatio,
                               Qt.TransformationMode.SmoothTransformation)
                )
                self.thumb_lbl.setText("")
        loader.loaded.connect(_on_loaded)
        loader.start()

    def _kill_thumb_loader(self) -> None:
        if self._thumb_loader is not None:
            try:
                self._thumb_loader.loaded.disconnect()
                self._thumb_loader.failed.disconnect()
            except RuntimeError:
                pass
            if self._thumb_loader.isRunning():
                self._thumb_loader.requestInterruption()
                self._thumb_loader.quit()
                self._thumb_loader.wait(2000)
            self._thumb_loader.deleteLater()
            self._thumb_loader = None


class _EditorUrlInput(QFrame):
    fetch_requested = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("UrlBar")
        self.setFixedHeight(44)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        from PySide6.QtWidgets import QLineEdit, QPushButton
        self.input = QLineEdit()
        self.input.setObjectName("UrlInput")
        self.input.setPlaceholderText("Paste video link here\u2026")
        self.input.returnPressed.connect(self._submit)
        lay.addWidget(self.input, 1)
        self.btn = QPushButton("Fetch  \u25B8")
        self.btn.setObjectName("FetchBtn")
        self.btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn.clicked.connect(self._submit)
        self.btn.setFixedWidth(110)
        lay.addWidget(self.btn)

    def _submit(self) -> None:
        t = self.input.text().strip()
        if t:
            self.fetch_requested.emit(t)

    def set_loading(self, on: bool) -> None:
        self.btn.setEnabled(not on)
        self.btn.setText("\u2026" if on else "Fetch  \u25B8")
        self.input.setReadOnly(on)


class _TimeEdit(QFrame):
    time_changed = Signal()

    def __init__(self, label: str, parent=None):
        super().__init__(parent)
        self._max = 0.0
        self._sec = 0.0
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(4)
        lbl = QLabel(label)
        lbl.setObjectName("Status")
        lbl.setFixedWidth(40)
        lay.addWidget(lbl)
        from PySide6.QtWidgets import QLineEdit
        self.input = QLineEdit("0:00")
        self.input.setObjectName("UrlInput")
        self.input.setFixedWidth(70)
        self.input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.input.textEdited.connect(self._parse)
        lay.addWidget(self.input)

    def set_time(self, s: float) -> None:
        self._sec = s
        self.input.setText(_fmt_time(s))

    def set_max(self, m: float) -> None:
        self._max = m

    def time(self) -> float:
        return self._sec

    def _parse(self, text: str) -> None:
        try:
            parts = text.strip().split(":")
            if len(parts) == 3:
                s = int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
            elif len(parts) == 2:
                s = int(parts[0]) * 60 + int(parts[1])
            else:
                s = int(parts[0])
            s = max(0.0, float(s))
            if self._max > 0:
                s = min(s, self._max)
            self._sec = s
            self.time_changed.emit()
        except (ValueError, IndexError):
            pass