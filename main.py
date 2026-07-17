"""Tex entry point — shows splash, then window."""
from __future__ import annotations

import os
import sys
from pathlib import Path

from PySide6.QtCore import QEventLoop, QTimer, Qt
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QApplication

from core import config
from core.metadata import ffmpeg_location
from ui import theme as ui_theme
from ui.widgets.splash import Splash


def make_app_icon() -> QIcon:
    # Portable bundle: use the real icon from the exe directory.
    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).resolve().parent
        ico = exe_dir / "icon.ico"
        png = exe_dir / "icon.png"
        if ico.exists():
            return QIcon(str(ico))
        if png.exists():
            pm = QPixmap(str(png))
            if not pm.isNull():
                return QIcon(pm)
    # Dev / fallback: code-generated icon.
    pm = QPixmap(256, 256)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    p.setBrush(QColor("#000000"))
    p.setPen(Qt.PenStyle.NoPen)
    p.drawRect(0, 0, 256, 256)
    p.setBrush(QColor("#D7191A"))
    p.drawEllipse(56, 56, 144, 144)
    p.setPen(QPen(QColor("#FFFFFF"), 6))
    p.drawArc(96, 96, 64, 64, 30 * 16, 270 * 16)
    p.end()
    return QIcon(pm)


def ensure_ffmpeg_first_run() -> None:
    # Portable: look for ffmpeg next to the EXE first.
    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).resolve().parent
        for name in ("ffmpeg.exe", "ffmpeg", "ffmpeg/bin/ffmpeg.exe"):
            candidate = exe_dir / name
            if candidate.exists():
                import core.metadata as _meta
                _meta._FFMPEG_LOCATION = str(candidate)
                return
    ffm = ffmpeg_location()
    if ffm and Path(ffm).exists():
        return
    try:
        import imageio_ffmpeg  # type: ignore
        ffm = imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        ffm = None
    if not ffm:
        print("[TEX] ffmpeg not found. Some downloads may fail.", file=sys.stderr)


def ensure_save_dir() -> None:
    cfg = config.load()
    p = Path(cfg["save_dir"])
    p.mkdir(parents=True, exist_ok=True)
    subdirs = cfg.get("subdirs")
    video_name = "Video"
    audio_name = "Audio"
    if isinstance(subdirs, dict):
        video_name = subdirs.get("video", "Video")
        audio_name = subdirs.get("audio", "Audio")
    (p / video_name).mkdir(parents=True, exist_ok=True)
    (p / audio_name).mkdir(parents=True, exist_ok=True)


def first_run_pick_save_dir() -> None:
    cfg = config.load()
    if cfg.get("save_dir") and Path(cfg["save_dir"]).exists():
        return
    from PySide6.QtWidgets import QFileDialog
    # Portable: default to a "Downloads" folder next to the EXE.
    if getattr(sys, "frozen", False):
        default_dir = str(Path(sys.executable).resolve().parent / "Downloads")
    else:
        default_dir = str(Path.home() / "Downloads")
    path = QFileDialog.getExistingDirectory(
        None, "Tex \u00B7 choose download folder", default_dir,
    )
    if path:
        cfg["save_dir"] = path
        config.save(cfg)
    else:
        # Portable fallback: Downloads next to EXE; installed fallback: ~/Downloads/Tex
        if getattr(sys, "frozen", False):
            fallback = str(Path(sys.executable).resolve().parent / "Downloads")
        else:
            fallback = str(Path.home() / "Downloads" / "Tex")
        cfg["save_dir"] = fallback
        config.save(cfg)


def _wait(ms: int) -> None:
    """Run the event loop for ms milliseconds (used by the splash)."""
    loop = QEventLoop()
    QTimer.singleShot(ms, loop.quit)
    loop.exec()


def main() -> int:
    QApplication.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    app.setApplicationName("Tex")
    app.setOrganizationName("Tex")
    app.setApplicationDisplayName("Tex")
    app.setWindowIcon(make_app_icon())
    app.setQuitOnLastWindowClosed(False)

    # Theme must be set before window is shown
    ui_theme.apply_theme(app, config.get("theme", "dark"))

    # Show splash
    splash = Splash()
    splash.set_status("Starting up\u2026")
    splash.resize(420, 320)
    splash.show()
    app.processEvents()
    _wait(450)

    # First-run setup
    splash.set_status("Checking ffmpeg\u2026")
    app.processEvents()
    ensure_ffmpeg_first_run()
    _wait(220)

    splash.set_status("Preparing folders\u2026")
    app.processEvents()
    ensure_save_dir()
    first_run_pick_save_dir()
    ensure_save_dir()
    _wait(220)

    # Build window
    splash.set_status("Ready\u2026")
    app.processEvents()
    from ui.app import TexWindow
    win = TexWindow()
    win.show()
    app.processEvents()
    _wait(180)

    splash.dismiss()
    _wait(220)

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())