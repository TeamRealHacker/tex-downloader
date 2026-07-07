"""Video info card: thumbnail + title + meta. Thin, hairline only."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSize, Qt, QThread, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QSizePolicy, QVBoxLayout

from core import config
from core.metadata import VideoInfo


_THUMB_SESSION: "requests.Session | None" = None


def _session() -> "requests.Session":
    """Reuse a single Session for keepalive across thumbnail downloads."""
    global _THUMB_SESSION
    if _THUMB_SESSION is None:
        import requests
        _THUMB_SESSION = requests.Session()
        _THUMB_SESSION.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        })
    return _THUMB_SESSION


class ThumbLoader(QThread):
    loaded = Signal(str, QPixmap)
    failed = Signal(str)

    def __init__(self, video_id: str, url: str, parent=None):
        super().__init__(parent)
        self.video_id = video_id
        self.url = url

    def run(self) -> None:
        cache = config.CONFIG_DIR / "thumbs" / f"{self.video_id}.jpg"
        try:
            cache.parent.mkdir(parents=True, exist_ok=True)
            if not cache.exists():
                try:
                    r = _session().get(self.url, timeout=8)
                    if r.status_code == 200 and r.content:
                        cache.write_bytes(r.content)
                except Exception:
                    pass
            if self.isInterruptionRequested():
                return
            pix = QPixmap(str(cache))
            if not pix.isNull():
                pix = pix.scaled(
                    QSize(320, 180),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                self.loaded.emit(self.video_id, pix)
            else:
                self.failed.emit(self.video_id)
        except Exception:
            self.failed.emit(self.video_id)


class VideoCard(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("Card")
        self._current_id: str | None = None
        self._loader: ThumbLoader | None = None

        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(12)

        # Thumb
        self.thumb_frame = QFrame()
        self.thumb_frame.setObjectName("CardInset")
        self.thumb_frame.setFixedSize(168, 94)
        tf_lay = QVBoxLayout(self.thumb_frame)
        tf_lay.setContentsMargins(0, 0, 0, 0)
        tf_lay.setSpacing(0)
        self.thumb = QLabel("LOADING\u2026")
        self.thumb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.thumb.setStyleSheet("color: #4A4A4A; background: transparent;")
        tf_lay.addWidget(self.thumb)

        # Info
        info = QVBoxLayout()
        info.setSpacing(2)
        info.setContentsMargins(0, 0, 0, 0)

        self.platform_lbl = QLabel("")
        self.platform_lbl.setObjectName("StatusActive")
        info.addWidget(self.platform_lbl)

        self.title_lbl = QLabel("\u2014")
        self.title_lbl.setObjectName("TitleLg")
        self.title_lbl.setWordWrap(True)
        self.title_lbl.setMaximumHeight(48)

        self.meta_lbl = QLabel("")
        self.meta_lbl.setObjectName("Meta")
        self.meta_lbl.setWordWrap(True)

        info.addWidget(self.title_lbl)
        info.addWidget(self.meta_lbl)
        info.addStretch(1)

        lay.addWidget(self.thumb_frame, 0, Qt.AlignmentFlag.AlignVCenter)
        lay.addLayout(info, 1)
        self.setVisible(False)

    def set_info(self, info: VideoInfo) -> None:
        self._current_id = info.id
        self.platform_lbl.setText(info.platform.upper().replace('_', ' '))
        self.title_lbl.setText(info.title)
        dur = info.duration_str
        ch = info.uploader or "Unknown channel"
        self.meta_lbl.setText(f"{ch}  \u00B7  {dur}")
        self.setVisible(True)

        self.thumb.setText("LOADING\u2026")
        if self._loader and self._loader.isRunning():
            try:
                self._loader.loaded.disconnect()
                self._loader.failed.disconnect()
            except RuntimeError:
                pass
            self._loader.requestInterruption()
            self._loader.deleteLater()
        if info.thumbnail:
            self._loader = ThumbLoader(info.id, info.thumbnail)
            self._loader.loaded.connect(self._on_thumb)
            self._loader.failed.connect(self._on_thumb_fail)
            self._loader.start()
        else:
            self.thumb.setText("NO IMAGE")
            self._loader = None

    def _on_thumb(self, vid_id: str, pix: QPixmap) -> None:
        if vid_id == self._current_id:
            self.thumb.setText("")
            self.thumb.setPixmap(pix)

    def _on_thumb_fail(self, vid_id: str) -> None:
        if vid_id == self._current_id:
            self.thumb.setText("NO THUMB")

    def clear(self) -> None:
        self._current_id = None
        self.thumb.clear()
        self.thumb.setText("NO IMAGE")
        self.title_lbl.setText("\u2014")
        self.meta_lbl.setText("")
        self.platform_lbl.setText("")
        self.setVisible(False)
