"""QThread-based downloader with progress, pause/resume, cancel."""
from __future__ import annotations

import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yt_dlp
from PySide6.QtCore import QMutex, QMutexLocker, QThread, Signal

from . import config
from .cookies import detect_browser
from .formats import MP3_QUALITIES, MP4_QUALITIES, QualityOption, find_by_key
from .metadata import ffmpeg_location
from .naming import render_path, unique_path


def _safe_int(val: Any, default: int = 0) -> int:
    """Convert *val* to int without raising on bad input."""
    try:
        return int(val)
    except (TypeError, ValueError):
        return default


@dataclass
class DownloadRequest:
    url: str
    title: str
    uploader: str
    vid_id: str
    quality_key: str
    out_dir: str
    template: str
    audio_only: bool
    cookies_file: str = ""
    no_cookies: bool = False  # skips cookies entirely; set after a browser-cookie failure


class DownloaderWorker(QThread):
    progress = Signal(str, float, float, float, int, int)  # tag, percent, speed, eta, downloaded, total
    status = Signal(str, str)  # tag, message
    finished = Signal(str, bool, str)  # tag, success, message

    def __init__(self, tag: str, req: DownloadRequest, parent=None):
        super().__init__(parent)
        self.tag = tag
        self.req = req
        self._cancel = False
        self._pause = False
        self._mutex = QMutex()

    def cancel(self) -> None:
        with QMutexLocker(self._mutex):
            self._cancel = True
            self._pause = False

    def toggle_pause(self) -> None:
        with QMutexLocker(self._mutex):
            self._pause = not self._pause

    def _is_cancelled(self) -> bool:
        with QMutexLocker(self._mutex):
            return self._cancel

    def _is_paused(self) -> bool:
        with QMutexLocker(self._mutex):
            return self._pause

    def run(self) -> None:
        try:
            self._run_unsafe()
        except Exception as e:  # noqa: BLE001
            # If the failure was a browser-cookie extraction issue (DPAPI decrypt,
            # locked database, missing keyring, etc.) AND we haven't already
            # retried without cookies, do that now. Most non-age-restricted
            # content still works without auth.
            err = str(e)
            if (not self.req.no_cookies) and not self.req.cookies_file:
                from .cookies import is_browser_cookie_error
                if is_browser_cookie_error(err):
                    self.status.emit(self.tag, "RETRY without browser cookies")
                    self.req.no_cookies = True
                    try:
                        self._run_unsafe()
                        return
                    except Exception as e2:  # noqa: BLE001
                        self.status.emit(self.tag, f"ERROR: {e2}")
                        self.finished.emit(self.tag, False, str(e2))
                        return
            self.status.emit(self.tag, f"ERROR: {e}")
            self.finished.emit(self.tag, False, err)

    def _run_unsafe(self) -> None:
        req = self.req
        quality: QualityOption | None = find_by_key(req.quality_key)
        if quality is None:
            self.finished.emit(self.tag, False, "Unknown quality")
            return

        out_dir = Path(req.out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

        ext = "mp3" if quality.kind == "audio" else "mp4"
        target = render_path(
            req.template,
            out_dir,
            title=req.title, channel=req.uploader,
            quality=quality.key, vid_id=req.vid_id, ext=ext,
        )
        target = unique_path(target)

        outtmpl = str(target.with_suffix("")) + ".%(ext)s"

        opts: dict[str, Any] = {
            "quiet": True,
            "no_warnings": True,
            "no_color": True,
            "noprogress": True,
            "outtmpl": outtmpl,
            "noplaylist": True,
            "retries": _safe_int(config.get("retries"), 3),
            "fragment_retries": _safe_int(config.get("retries"), 3),
            "concurrent_fragment_downloads": 4,
            "windowsfilenames": True,
            "trim_file_name": 200,
        }
        ffm = ffmpeg_location()
        if ffm:
            opts["ffmpeg_location"] = ffm
        # Cookies: explicit file overrides the browser setting.
        # ``no_cookies`` short-circuits both (set by the auto-retry path).
        if not req.no_cookies:
            if req.cookies_file:
                opts["cookiefile"] = req.cookies_file
            else:
                browser = (config.get("cookies_from_browser", "auto") or "auto").strip().lower()
                if browser and browser not in ("none", "off", "no", "false", "0"):
                    if browser in ("auto", "default"):
                        browser = detect_browser() or ""
                    if browser:
                        opts["cookiesfrombrowser"] = (browser, None, None, None)
        if config.get("speed_limit_bps"):
            opts["ratelimit"] = _safe_int(config.get("speed_limit_bps"), 0)

        # Format / post-processors
        if quality.kind == "audio":
            opts["format"] = "bestaudio/best"
            opts["postprocessors"] = [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": str((quality.extra or {}).get("preferredquality", "192")),
            }]
            opts["postprocessor_args"] = ["-id3v2_version", "3"]
            opts["writethumbnail"] = False
        else:
            opts["format"] = quality.format_str
            # Only force mp4 merge for YouTube — other platforms (Twitter,
            # Instagram) may only serve webm and forcing mp4 causes errors.
            from .detector import detect
            if detect(req.url) in ("youtube", "youtube_playlist"):
                opts["merge_output_format"] = "mp4"

        # Progress hook — throttled
        last_emit = [0.0]
        paused_at = [0.0]

        def _hook(d: dict[str, Any]) -> None:
            if self._is_cancelled():
                raise yt_dlp.utils.DownloadError("Cancelled by user")

            # Pause handling: sleep loop while paused
            while self._is_paused() and not self._is_cancelled():
                if paused_at[0] == 0.0:
                    paused_at[0] = time.time()
                    self.status.emit(self.tag, "PAUSED")
                time.sleep(0.2)
            if paused_at[0] != 0.0:
                paused_at[0] = 0.0
                self.status.emit(self.tag, "DOWNLOADING")

            now = time.time()
            if d.get("status") == "downloading":
                total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
                downloaded = d.get("downloaded_bytes") or 0
                pct = (downloaded / total * 100.0) if total else 0.0
                speed = d.get("speed") or 0.0
                eta = d.get("eta") or 0.0
                if now - last_emit[0] > 0.25:
                    last_emit[0] = now
                    self.progress.emit(
                        self.tag, float(pct), float(speed), float(eta),
                        int(downloaded), int(total),
                    )
            elif d.get("status") == "finished":
                # Preserve actual downloaded/total values — the queue card uses
                # these to show the final size (e.g. "45.2 MB / 45.2 MB").
                fin_dl = d.get("downloaded_bytes") or downloaded or 0
                fin_tot = d.get("total_bytes") or total or 0
                self.progress.emit(
                    self.tag, 100.0, 0.0, 0.0,
                    int(fin_dl), int(fin_tot),
                )
                self.status.emit(self.tag, "FINALIZING")

        opts["progress_hooks"] = [_hook]

        # Silent logger
        class _SilentLogger:
            def debug(self, *_a, **_k): pass
            def info(self, *_a, **_k): pass
            def warning(self, *_a, **_k): pass
            def error(self, *_a, **_k): pass

        opts["logger"] = _SilentLogger()

        with yt_dlp.YoutubeDL(opts) as ydl:
            self.status.emit(self.tag, "FETCHING")
            ydl.download([req.url])

        # Compute final file path
        if quality.kind == "audio":
            final = target.with_suffix(".mp3")
        else:
            final = target.with_suffix(".mp4")
            if not final.exists():
                # ffmpeg merge may write a different ext — scan siblings
                # using stem matching (NOT glob — [] in filenames are
                # metacharacters and break glob patterns).
                stem = target.stem.lower()
                for f in out_dir.iterdir():
                    if f.stem.lower() == stem:
                        final = f
                        break

        if not final.exists():
            self.finished.emit(self.tag, False, "Output file not found.")
            return

        self.finished.emit(self.tag, True, str(final))
