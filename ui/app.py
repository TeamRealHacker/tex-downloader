"""Tex main window — super minimal, iOS feel.

Layout (frameless):
  TitleBar (custom, 36px, has its own min/max/close)
  Body:    Sidebar (124px) | main stack
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import QEvent, QPoint, Qt, QRect, QSize, QThread, QTimer, Signal
from PySide6.QtGui import QCursor, QDragEnterEvent, QDropEvent, QMouseEvent, QPainter, QColor, QPainterPath, QRegion
from PySide6.QtWidgets import (
    QApplication, QFileDialog, QFrame, QHBoxLayout, QLabel, QMainWindow, QPushButton,
    QScrollArea, QSizeGrip, QStackedWidget, QSystemTrayIcon, QVBoxLayout, QWidget,
)

from core import config, history, metadata, playlist
from core.detector import extract_urls
from core.downloader import DownloadRequest
from core.formats import MP3_QUALITIES, MP4_QUALITIES
from core.queue import DownloadQueue

import ui.anim as anim
import ui.shortcuts as shortcuts
from ui import theme as ui_theme
from ui.tray import TrayIcon
from ui.widgets.empty_state import EmptyState
from ui.widgets.format_picker import FormatPicker
from ui.widgets.icon_button import IconTextButton
from ui.widgets.history_panel import HistoryPanel
from ui.widgets.playlist_panel import PlaylistPanel
from ui.widgets.progress_card import ProgressCard
from ui.widgets.queue_bar import QueueBar
from ui.widgets.settings_panel import SettingsPanel
from ui.widgets.sidebar import Sidebar
from ui.widgets.title_bar import TitleBar
from ui.widgets.url_bar import UrlBar
from ui.widgets.video_card import VideoCard
from ui.widgets.dot_background import DotBackground
from ui.widgets.channel_panel import ChannelPanel
from ui.widgets.editor_panel import EditorPanel


# ---------- Edge resize for frameless window ----------
class _FramelessResizer:
    """Adds native edge-resize to a frameless window on Windows."""

    EDGE = 6
    CURSOR = {
        0: Qt.CursorShape.ArrowCursor,
        1: Qt.CursorShape.SizeHorCursor,    # left
        2: Qt.CursorShape.SizeVerCursor,    # top
        3: Qt.CursorShape.SizeFDiagCursor,  # top+left
        4: Qt.CursorShape.SizeHorCursor,    # right
        5: Qt.CursorShape.SizeBDiagCursor,  # right+top
        6: Qt.CursorShape.SizeBDiagCursor,  # right+bottom
        8: Qt.CursorShape.SizeVerCursor,    # bottom
        9: Qt.CursorShape.SizeFDiagCursor,  # bottom+left
    }

    def __init__(self, win: "TexWindow"):
        self._win = win
        self._edges = 0
        self._resizing = False
        self._start_pos: QPoint | None = None
        self._start_geom: QRect | None = None

    def update_cursor(self, pos: QPoint) -> None:
        if self._resizing:
            return
        edges = self._edges_at(pos)
        if edges == 0:
            self._win.unsetCursor()
        else:
            self._win.setCursor(self.CURSOR[edges])

    def try_start(self, e: QMouseEvent) -> bool:
        if e.button() != Qt.MouseButton.LeftButton:
            return False
        edges = self._edges_at(e.position().toPoint())
        if edges == 0:
            return False
        self._resizing = True
        self._start_pos = e.globalPosition().toPoint()
        self._start_geom = self._win.geometry()
        return True

    def update(self, e: QMouseEvent) -> None:
        if not self._resizing or self._start_pos is None or self._start_geom is None:
            return
        delta = e.globalPosition().toPoint() - self._start_pos
        g = QRect(self._start_geom)
        e0, e1, e2, e3, e4, e5, e6, e7 = (
            bool(self._edges & 1), bool(self._edges & 2),
            bool(self._edges & 4), bool(self._edges & 8),
            bool(self._edges & 16), bool(self._edges & 32),
            bool(self._edges & 64), bool(self._edges & 128),
        )
        # L = bit 1 (left), T = bit 2 (top), R = bit 4 (right), B = bit 8 (bottom)
        left, top, right, bottom = e0, e1, e2, e3
        if left:
            new_w = g.width() - delta.x()
            if new_w < self._win.minimumWidth():
                delta.setX(g.width() - self._win.minimumWidth())
            g.setLeft(g.left() + delta.x())
        if top:
            new_h = g.height() - delta.y()
            if new_h < self._win.minimumHeight():
                delta.setY(g.height() - self._win.minimumHeight())
            g.setTop(g.top() + delta.y())
        if right:
            g.setWidth(max(self._win.minimumWidth(), g.width() + delta.x()))
        if bottom:
            g.setHeight(max(self._win.minimumHeight(), g.height() + delta.y()))
        self._win.setGeometry(g)

    def stop(self) -> None:
        self._resizing = False
        self._start_pos = None
        self._start_geom = None

    def _edges_at(self, pos: QPoint) -> int:
        w, h = self._win.width(), self._win.height()
        e = 0
        if pos.x() <= self.EDGE:
            e |= 1  # left
        if pos.y() <= self.EDGE:
            e |= 2  # top
        if pos.x() >= w - self.EDGE:
            e |= 4  # right
        if pos.y() >= h - self.EDGE:
            e |= 8  # bottom
        return e


# ---------- Workers ----------
class _FetchWorker(QThread):
    ok = Signal(object)
    fail = Signal(str)
    retried_without_cookies = Signal()  # emitted when the worker auto-retried without auth

    def __init__(self, url: str, parent=None):
        super().__init__(parent)
        self.url = url

    def run(self) -> None:
        try:
            self.ok.emit(metadata.fetch(self.url))
        except Exception as e:
            from core.cookies import is_browser_cookie_error
            err = str(e)
            if is_browser_cookie_error(err):
                try:
                    self.retried_without_cookies.emit()
                    self.ok.emit(metadata.fetch(self.url, no_cookies=True))
                    return
                except Exception as e2:
                    self.fail.emit(str(e2))
                    return
            self.fail.emit(err)


class _ChannelWorker(QThread):
    ok = Signal(object)
    fail = Signal(str)

    def __init__(self, url: str, content_type: str, max_count: int, parent=None):
        super().__init__(parent)
        self.url = url
        self.content_type = content_type
        self.max_count = max_count

    def run(self) -> None:
        try:
            from core.channel import fetch_channel
            self.ok.emit(fetch_channel(self.url, self.content_type, self.max_count))
        except Exception as e:
            self.fail.emit(str(e))


# ---------- Main window ----------
class TexWindow(QMainWindow):
    CORNER_RADIUS = 10  # px — rounded corners on all four edges.

    def __init__(self):
        super().__init__()
        self.setObjectName("TexRoot")
        self.setWindowTitle("Tex")

        # Frameless but keep taskbar entry + system menu on Windows.
        # WA_TranslucentBackground lets us paint rounded corners in paintEvent.
        self.setWindowFlags(
            Qt.WindowType.Window
            | Qt.WindowType.FramelessWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        self.setMinimumSize(QSize(820, 540))
        self.resize(980, 660)
        self.setAcceptDrops(True)

        # Resize
        self._resizer = _FramelessResizer(self)

        # State
        self._current_result: metadata.FetchResult | None = None
        self._current_quality = None
        self._fetch_worker: _FetchWorker | None = None
        self._per_video_progress: dict[str, ProgressCard] = {}
        self._done_count = 0
        self._last_click_sound_ms = 0
        self._toast_timer = QTimer(self)
        self._toast_timer.setSingleShot(True)
        self._toast_timer.timeout.connect(self._hide_toast)

        # Queue
        self.queue = DownloadQueue()
        self.queue.added.connect(self._on_added)
        self.queue.started.connect(self._on_started)
        self.queue.progress.connect(self._on_progress)
        self.queue.status_changed.connect(self._on_status)
        self.queue.finished.connect(self._on_finished)
        self.queue.slot_changed.connect(self._on_slots)

        # Sound manager — tray notifications are disabled by user request;
        # all events are signalled via the in-window toast + sound effects.
        from core.sound import SoundManager
        self.sound = SoundManager(enabled=bool(config.get("sounds_enabled", True)))

        # Global click sound — every left-click plays the tick.
        QApplication.instance().installEventFilter(self)

        # Theme palette — extracted BEFORE _build() so every themed widget
        # can pick it up at construction time.
        self._current_theme = config.get("theme", "dark")
        _, self._theme_palette = ui_theme.apply_theme(
            QApplication.instance(), self._current_theme
        )

        self._build()
        shortcuts.install(self)

        # Tray
        self.tray: TrayIcon | None = None
        if config.get("minimize_to_tray", True):
            try:
                self.tray = TrayIcon(self._show, self.shortcut_paste, self._quit)
                self.tray.show()
            except Exception:
                self.tray = None

        # Clipboard
        from core.clipboard import ClipboardWatcher
        self.clip_watcher = ClipboardWatcher(interval_ms=1500, parent=self)
        self.clip_watcher.url_detected.connect(self._on_url_from_clipboard)
        if config.get("watch_clipboard", True):
            self.clip_watcher.start()

        # Theme + initial state
        self.queue.set_max_slots(int(config.get("concurrency", 0)))
        self.titlebar.set_state("ready")
        self.page_settings.refresh_about()
        self.page_settings.set_queue_info(0, int(config.get("concurrency", 0)))
        # Dot background: dark theme only.
        self._dot_bg.setVisible(True)

    # ---------- Mouse events for resize ----------
    def mouseMoveEvent(self, e: QMouseEvent) -> None:
        self._resizer.update(e)
        self._resizer.update_cursor(e.position().toPoint())
        super().mouseMoveEvent(e)

    def mousePressEvent(self, e: QMouseEvent) -> None:
        if self._resizer.try_start(e):
            e.accept()
            return
        super().mousePressEvent(e)

    def mouseReleaseEvent(self, e: QMouseEvent) -> None:
        self._resizer.stop()
        super().mouseReleaseEvent(e)

    # ---------- Global click sound ----------
    def eventFilter(self, obj, ev) -> bool:
        try:
            if ev.type() == QEvent.MouseButtonPress and ev.button() == Qt.MouseButton.LeftButton:
                if not self.sound._enabled:
                    return False
                # Debounce — Qt propagates a single click up the parent chain, so
                # eventFilter fires once per ancestor. ~60ms is well under human click
                # cadence but skips the propagation duplicates.
                from PySide6.QtCore import QDateTime
                now = QDateTime.currentMSecsSinceEpoch()
                if now - self._last_click_sound_ms < 60:
                    return False
                self._last_click_sound_ms = now
                self.sound.play("tick")
        except Exception:
            pass
        return super().eventFilter(obj, ev)

    # ---------- Shortcuts ----------
    def shortcut_paste(self) -> None:
        try:
            from PySide6.QtGui import QGuiApplication
            text = QGuiApplication.clipboard().text() or ""
        except Exception:
            text = ""
        if text:
            self.url_bar.set_text(text)
        else:
            self._show_toast("Clipboard is empty")

    def shortcut_focus_url(self) -> None:
        self.url_bar.input.setFocus()
        self.url_bar.input.selectAll()

    def shortcut_enter(self) -> None:
        if self._current_result and self._current_result.kind == "single" and self._current_quality:
            self._start_single_download()

    def shortcut_escape(self) -> None:
        if self.queue.active_count() > 0:
            self.queue.cancel_all()

    def shortcut_settings(self) -> None:
        self._switch_tab(5)

    def shortcut_history(self) -> None:
        self._switch_tab(4)

    def shortcut_queue(self) -> None:
        self._switch_tab(1)

    def shortcut_download(self) -> None:
        self._switch_tab(0)

    def shortcut_editor(self) -> None:
        self._switch_tab(2)

    # ---------- Build ----------
    def _build(self) -> None:
        central = QWidget()
        central.setObjectName("TexRoot")
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Title bar
        self.titlebar = TitleBar(theme=self._theme_palette)
        self.titlebar.open_save_folder.connect(self._open_save_dir)
        root.addWidget(self.titlebar)

        # Dot-pattern background. Sits at the very back of the root so it
        # covers the full window (behind titlebar, sidebar, and content).
        # Opaque widgets paint on top — dots show through the transparent
        # page chrome.
        self._dot_bg = DotBackground(central, is_dark=(self._current_theme != "light"))
        self._dot_bg.lower()
        self._dot_bg.setGeometry(0, 0, 1, 1)  # placeholder; resizeEvent fixes it

        # Body
        body = QFrame()
        body.setObjectName("TexBody")
        body_lay = QHBoxLayout(body)
        body_lay.setContentsMargins(0, 0, 0, 0)
        body_lay.setSpacing(0)

        self.sidebar = Sidebar(theme=self._theme_palette)
        self.sidebar.nav_changed.connect(self._switch_tab)
        self.sidebar.collapse_changed.connect(self._on_sidebar_collapse)
        body_lay.addWidget(self.sidebar)

        self.main = QFrame()
        self.main.setObjectName("TexPage")
        main_lay = QVBoxLayout(self.main)
        main_lay.setContentsMargins(0, 0, 0, 0)
        main_lay.setSpacing(0)

        self.stack = QStackedWidget()
        main_lay.addWidget(self.stack, 1)

        # Pages
        self.page_dl = self._build_download_page()
        self.stack.addWidget(self.page_dl)
        self.page_queue = self._build_queue_page()
        self.stack.addWidget(self.page_queue)
        # Editor page — trim video segments
        self.page_editor = EditorPanel(theme=self._theme_palette)
        self.page_editor.trim_requested.connect(self._on_trim_download)
        self.stack.addWidget(self.page_editor)
        # Channels page — bulk download from YouTube/TikTok/Instagram channels
        self.page_channels = ChannelPanel(theme=self._theme_palette)
        self.page_channels.fetch_requested.connect(self._on_channel_fetch)
        self.page_channels.download_requested.connect(self._on_channel_download)
        self.stack.addWidget(self.page_channels)
        self.page_history = HistoryPanel()
        self.stack.addWidget(self.page_history)
        self.page_settings = SettingsPanel()
        self.page_settings.changed.connect(self._on_settings_changed)
        self.page_settings.pick_save_dir.connect(self._pick_save_dir)
        # Wrap in scroll area so the panel never gets vertically compressed
        settings_scroll = QScrollArea()
        settings_scroll.setObjectName("ScrollArea")
        settings_scroll.setWidgetResizable(True)
        settings_scroll.setFrameShape(QFrame.Shape.NoFrame)
        settings_scroll.setWidget(self.page_settings)
        self.page_settings_scroll = settings_scroll
        self.stack.addWidget(settings_scroll)

        # Toast
        self.toast = QFrame(self)
        self.toast.setObjectName("Toast")
        self.toast.setVisible(False)
        toast_lay = QHBoxLayout(self.toast)
        toast_lay.setContentsMargins(12, 0, 14, 0)
        toast_lay.setSpacing(8)
        self.toast_dot = QLabel("")
        self.toast_dot.setObjectName("ToastDot")
        self.toast_dot.setFixedSize(6, 6)
        self.toast_lbl = QLabel("")
        self.toast_lbl.setObjectName("ToastText")
        toast_lay.addWidget(self.toast_dot)
        toast_lay.addWidget(self.toast_lbl)
        self.toast.setFixedHeight(28)

        body_lay.addWidget(self.main, 1)
        root.addWidget(body, 1)

        # Size grip in bottom-right corner
        grip_wrap = QFrame(self)
        grip_wrap.setFixedSize(16, 16)
        grip_wrap.move(self.width() - 16, self.height() - 16)
        grip = QSizeGrip(grip_wrap)
        grip.setFixedSize(16, 16)
        self._grip_wrap = grip_wrap

        self._switch_tab(0)

    def resizeEvent(self, e) -> None:
        super().resizeEvent(e)
        self._reposition_toast()
        self._grip_wrap.move(self.width() - 16, self.height() - 16)
        self._resizer.update_cursor(QPoint(self.mapFromGlobal(QCursor.pos())))
        # Dot background fills the whole window — behind titlebar, sidebar, content.
        if hasattr(self, "_dot_bg") and self._dot_bg is not None:
            cw = self.centralWidget()
            if cw is not None:
                self._dot_bg.setGeometry(0, 0, cw.width(), cw.height())
                self._dot_bg.lower()
        # Keep current page sized to the stack
        w = self.stack.currentWidget()
        if w is not None:
            w.resize(self.stack.size())
        # Re-center the queue empty label whenever the page resizes.
        self._position_queue_empty()
        # Keep the rounded-corner mask in sync with the new size.
        self._update_corner_mask()

    def changeEvent(self, e) -> None:
        super().changeEvent(e)
        if e.type() == QEvent.Type.WindowStateChange:
            if self.isMaximized():
                self._grip_wrap.hide()
                # No rounded corners when maximized — clear the mask.
                cw = self.centralWidget()
                if cw is not None:
                    cw.setMask(QRegion())
            else:
                self._grip_wrap.show()
                self._update_corner_mask()

    def _rounded_rect(self) -> QPainterPath:
        """Rounded-rect path covering the full window (for paint + mask)."""
        r = self.CORNER_RADIUS
        p = QPainterPath()
        p.addRoundedRect(0, 0, self.width(), self.height(), r, r)
        return p

    def paintEvent(self, _e) -> None:
        """Draw rounded-corner background.  The central widget is transparent —
        its children (title bar, sidebar, pages) paint on top of this."""
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.setPen(Qt.PenStyle.NoPen)
        # Use the current theme's bg colour.
        bg = QColor(self._theme_palette.get("bg", "#000000"))
        p.setBrush(bg)
        p.drawPath(self._rounded_rect())
        p.end()

    def _update_corner_mask(self) -> None:
        """Clip the central widget to a rounded-rect mask so child widgets
        don't bleed into the corners."""
        cw = self.centralWidget()
        if cw is None or self.isMaximized():
            return
        r = self.CORNER_RADIUS
        path = QPainterPath()
        path.addRoundedRect(0, 0, cw.width(), cw.height(), r, r)
        cw.setMask(QRegion(path.toFillPolygon().toPolygon()))

    # ---------- Page builders ----------
    def _build_download_page(self) -> QWidget:
        page = QWidget()
        page.setObjectName("TexPage")
        v = QVBoxLayout(page)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)

        # URL bar
        url_wrap = QFrame()
        url_wrap.setObjectName("TexPage")
        ul = QVBoxLayout(url_wrap)
        ul.setContentsMargins(16, 14, 16, 0)
        ul.setSpacing(0)
        self.url_bar = UrlBar()
        self.url_bar.fetch_requested.connect(self._on_fetch)
        ul.addWidget(self.url_bar)
        v.addWidget(url_wrap)

        # Scrollable content
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_content = QWidget()
        self.scroll_content.setObjectName("TexPage")
        self.scroll.setWidget(self.scroll_content)
        sl = QVBoxLayout(self.scroll_content)
        sl.setContentsMargins(16, 12, 16, 16)
        sl.setSpacing(12)

        # Empty state
        self.empty_state = EmptyState()
        sl.addWidget(self.empty_state, 1)

        # Content column (full-width, no bento side panel)
        content_col = QVBoxLayout()
        content_col.setSpacing(14)
        content_col.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.video_card = VideoCard()
        content_col.addWidget(self.video_card)

        self.format_picker = FormatPicker()
        self.format_picker.selected.connect(self._on_quality)
        self.format_picker.setVisible(False)
        content_col.addWidget(self.format_picker)

        self.btn_download = QPushButton("\u2B07  Download")
        self.btn_download.setObjectName("Primary")
        self.btn_download.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_download.setFixedHeight(46)
        self.btn_download.setVisible(False)
        self.btn_download.clicked.connect(self._start_single_download)
        content_col.addWidget(self.btn_download)

        # Progress stack
        self.progress_stack = QFrame()
        self.progress_stack.setObjectName("CardFlat")
        ps = QVBoxLayout(self.progress_stack)
        ps.setContentsMargins(0, 0, 0, 0)
        ps.setSpacing(8)
        self.progress_stack.setVisible(False)
        content_col.addWidget(self.progress_stack)

        self.playlist_panel = PlaylistPanel()
        self.playlist_panel.download_selected.connect(self._start_playlist_selected)
        self.playlist_panel.download_all.connect(self._start_playlist_all)
        content_col.addWidget(self.playlist_panel)

        content_wrap = QWidget()
        content_wrap.setLayout(content_col)
        sl.addWidget(content_wrap)

        sl.addStretch(1)
        v.addWidget(self.scroll, 1)
        return page



    def _build_queue_page(self) -> QWidget:
        page = QWidget()
        page.setObjectName("TexPage")
        v = QVBoxLayout(page)
        v.setContentsMargins(20, 18, 20, 18)
        v.setSpacing(12)

        # Top row: title + open-save-folder button
        header_row = QHBoxLayout()
        header_row.setSpacing(8)
        header_row.setContentsMargins(0, 0, 0, 0)
        title = QLabel("Queue")
        title.setObjectName("XL")
        header_row.addWidget(title)
        header_row.addStretch(1)
        self.open_save_btn = IconTextButton("folder", "OPEN SAVE FOLDER",
                                            size=14, height=28,
                                            theme=self._theme_palette)
        self.open_save_btn.setObjectName("Ghost")
        self.open_save_btn.clicked.connect(self._open_save_dir)
        header_row.addWidget(self.open_save_btn)
        v.addLayout(header_row)

        self.queue_bar = QueueBar()
        self.queue_bar.cancel_all.connect(self.queue.cancel_all)
        self.queue_bar.clear_finished.connect(self._on_clear_finished)
        v.addWidget(self.queue_bar)

        # Scrollable card container — wraps the queue_progress frame so the
        # cards keep their full size and the user can scroll through dozens.
        self.queue_scroll = QScrollArea()
        self.queue_scroll.setObjectName("ScrollArea")
        self.queue_scroll.setWidgetResizable(True)
        self.queue_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.queue_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.queue_scroll.setMinimumHeight(220)

        # Inner container — plain QWidget, NOT CardFlat.  Each ProgressCard
        # already has its own Card border; a parent card-style just adds a
        # confusing double-border and hides the scrollbar track.
        self.queue_progress = QWidget()
        self.queue_progress.setStyleSheet("background: transparent;")
        qp = QVBoxLayout(self.queue_progress)
        qp.setContentsMargins(0, 0, 0, 0)
        qp.setSpacing(6)
        self.queue_progress.setVisible(False)
        self.queue_scroll.setWidget(self.queue_progress)

        # Empty state — a label overlaid on top of the scroll area when the
        # queue is empty. Lives as a child of the scroll area so it can be
        # centered over the cards' future position.
        self.queue_empty = QLabel("Nothing in the queue yet.\nPaste a link to start a download.", self.queue_scroll)
        self.queue_empty.setObjectName("EmptyTitle")
        self.queue_empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.queue_empty.setWordWrap(True)
        self.queue_empty.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

        v.addWidget(self.queue_scroll, 1)

        return page

    def _position_queue_empty(self) -> None:
        """Keep the empty label centered inside the scroll area."""
        if not hasattr(self, "queue_empty") or self.queue_empty is None:
            return
        if not self.queue_empty.isVisible():
            return
        sa = self.queue_scroll
        # The empty label is a direct child of the QScrollArea (not the
        # viewport), so position it in the scroll area's own coordinates.
        w = sa.width()
        h = sa.height()
        # Subtract scrollbar width (16px on Windows) to match the viewport.
        sb = sa.verticalScrollBar()
        if sb is not None and sb.isVisible():
            w -= sb.width()
        fm = self.queue_empty.fontMetrics()
        # Two lines of text — give it some breathing room.
        tw = min(w - 40, 400)
        th = fm.height() * 2 + 12
        self.queue_empty.setGeometry((w - tw) // 2, (h - th) // 2, tw, th)

    def _open_save_dir(self) -> None:
        """Open the user's default save directory in Explorer."""
        from core import config
        from pathlib import Path
        path = Path(config.get("save_dir", str(Path.home() / "Downloads" / "Tex")))
        try:
            path.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass
        self._open_path(str(path))

    def _switch_tab(self, idx: int) -> None:
        self.stack.setCurrentIndex(idx)
        self.sidebar.set_active(idx)
        # Force the current page to fill the stack (Qt doesn't auto-stretch QStackedWidget children)
        w = self.stack.currentWidget()
        if w is not None:
            w.resize(self.stack.size())
        if idx == 4:
            self.page_history.refresh()
        if idx == 5:
            self.page_settings.refresh_about()

    def _on_sidebar_collapse(self, _collapsed: bool) -> None:
        # No-op: sidebar handles its own width animation
        pass

    # ---------- Toast ----------
    def _show_toast(self, msg: str, duration_ms: int = 2000) -> None:
        self.toast_lbl.setText(msg)
        self.toast.adjustSize()
        self.toast.setVisible(True)
        self.toast.raise_()
        self._reposition_toast()
        self._toast_timer.start(duration_ms)

    def _reposition_toast(self) -> None:
        if not self.toast.isVisible():
            return
        m = 16
        x = self.width() - self.toast.width() - m
        y = self.height() - self.toast.height() - m - 16
        self.toast.setGeometry(x, y, self.toast.width(), self.toast.height())

    def _hide_toast(self) -> None:
        self.toast.setVisible(False)

    # ---------- Fetch ----------
    def _on_fetch(self, url: str) -> None:
        if not url:
            return
        # Multi-URL paste: split the input on whitespace, extract every URL,
        # and enqueue them all with the currently-selected quality. The
        # downloader fetches its own metadata per item, so no preview step.
        urls = extract_urls(url)
        if len(urls) > 1:
            self._enqueue_bulk(urls)
            return
        # Hot path: if the result is already memoized, skip the worker thread
        # entirely (saves the QThread + queued-signal roundtrip).
        cached = metadata._cache_get(url, False)
        if cached is not None:
            self._set_state("idle")
            self._on_fetch_ok(cached)
            return
        self._set_state("fetching")
        self._show_toast("Fetching\u2026")
        self.sound.play("fetch")
        # Kill any in-flight fetch worker to avoid race conditions.
        if self._fetch_worker is not None:
            try:
                self._fetch_worker.ok.disconnect()
                self._fetch_worker.fail.disconnect()
                self._fetch_worker.retried_without_cookies.disconnect()
            except RuntimeError:
                pass
            if self._fetch_worker.isRunning():
                self._fetch_worker.requestInterruption()
                self._fetch_worker.quit()
                self._fetch_worker.wait(3000)
            self._fetch_worker.deleteLater()
        self._fetch_worker = _FetchWorker(url)
        self._fetch_worker.ok.connect(self._on_fetch_ok)
        self._fetch_worker.fail.connect(self._on_fetch_fail)
        self._fetch_worker.retried_without_cookies.connect(self._on_fetch_retried)
        self._fetch_worker.start()

    def _enqueue_bulk(self, urls: list) -> None:
        """Enqueue a batch of URLs at once — no metadata preview."""
        if not urls:
            return
        # Use the user's currently selected quality; fall back to 720p.
        q = self.format_picker.selected_option() or MP4_QUALITIES[2]
        out_dir = config.ensure_save_subdir("audio" if q.kind == "audio" else "video")
        tpl = config.get("filename_template", "{title} [{quality}].{ext}")
        reqs = [
            DownloadRequest(
                url=u, title="", uploader="", vid_id="",
                quality_key=q.key, out_dir=out_dir, template=tpl,
                audio_only=(q.kind == "audio"),
            )
            for u in urls
        ]
        self.queue.enqueue_many(reqs)
        self.sound.play("queue")
        self._show_toast(f"Queued \u00B7 {len(urls)} item{'s' if len(urls) != 1 else ''}")
        self._switch_tab(1)

    def _on_fetch_retried(self) -> None:
        # Browser cookies failed to decrypt; the worker is silently retrying
        # without auth. Tell the user so they know what happened if it works.
        self._show_toast("Browser cookies failed \u00B7 retried without", 3000)

    def _set_state(self, state: str) -> None:
        self.url_bar.set_loading(state == "fetching")
        self.titlebar.set_state(state if state != "idle" else "ready")

    def _on_fetch_ok(self, result: metadata.FetchResult) -> None:
        self._set_state("idle")
        # Clean up the fetch worker — it's done, free the QThread.
        if self._fetch_worker is not None:
            try:
                self._fetch_worker.ok.disconnect()
                self._fetch_worker.fail.disconnect()
                self._fetch_worker.retried_without_cookies.disconnect()
            except RuntimeError:
                pass
            self._fetch_worker.deleteLater()
            self._fetch_worker = None
        self._current_result = result

        self.video_card.clear()
        self.format_picker.setVisible(False)
        self.btn_download.setVisible(False)
        self.playlist_panel.setVisible(False)
        self.empty_state.setVisible(False)

        if result.kind == "single" and result.video:
            v = result.video
            self.video_card.set_info(v)
            self.format_picker.setVisible(True)
            self.btn_download.setVisible(True)
            self._show_toast(f"Ready \u00B7 {v.title[:50]}")
            self._current_quality = self.format_picker.selected_option()
            # Sizes come from the single metadata call — no probe workers.
            self._apply_format_sizes(v.format_sizes)
        elif result.kind == "playlist" and result.playlist:
            p = result.playlist
            try:
                pp = playlist.parse(self.url_bar.text())
                pre = playlist.precheck_ids(p.entries, pp.current_video_id)
                pre_check_id = pp.current_video_id
            except Exception:
                pre = set()
                pre_check_id = None
            self.playlist_panel.set_playlist(p.title, p.uploader, p.entries, pre)
            msg = f"Ready \u00B7 {p.title[:40] or 'Playlist'}"
            if pre_check_id:
                msg += " \u00B7 current pre-checked"
            self._show_toast(msg)

    def _on_fetch_fail(self, err: str) -> None:
        self._set_state("idle")
        # Clean up the fetch worker on failure too.
        if self._fetch_worker is not None:
            try:
                self._fetch_worker.ok.disconnect()
                self._fetch_worker.fail.disconnect()
                self._fetch_worker.retried_without_cookies.disconnect()
            except RuntimeError:
                pass
            self._fetch_worker.deleteLater()
            self._fetch_worker = None
        self.empty_state.setVisible(True)
        self._show_toast(f"Error \u00B7 {err}", 4000)
        self.sound.play("error")

    def _apply_format_sizes(self, sizes: dict) -> None:
        """Push pre-computed sizes into the format picker.

        Replaces the old 9-worker probe that re-invoked yt-dlp per quality.
        """
        out: dict[str, str] = {}
        for q in MP4_QUALITIES + MP3_QUALITIES:
            sz = sizes.get(q.key) if sizes else None
            out[q.key] = self._human_bytes(sz) if sz else "\u2014"
        self.format_picker.set_size_estimates(out)

    def _human_bytes(self, n: int) -> str:
        if not n:
            return "\u2014"
        x = float(n)
        for unit in ("B", "KB", "MB", "GB", "TB"):
            if abs(x) < 1024:
                return f"{x:.0f} {unit}" if unit == "B" else f"{x:.1f} {unit}"
            x /= 1024
        return f"{x:.1f} PB"

    def _on_quality(self, opt) -> None:
        self._current_quality = opt

    # ---------- Download ----------
    def _start_single_download(self) -> None:
        if not self._current_result or self._current_result.kind != "single":
            return
        v = self._current_result.video
        if not v:
            return
        q = self._current_quality or self.format_picker.selected_option()
        out_dir = config.ensure_save_subdir("audio" if q.kind == "audio" else "video")
        req = DownloadRequest(
            url=v.webpage_url, title=v.title, uploader=v.uploader, vid_id=v.id,
            quality_key=q.key, out_dir=out_dir,
            template=config.get("filename_template", "{title} [{quality}].{ext}"),
            audio_only=(q.kind == "audio"),
        )
        self.queue.enqueue(req)
        self._show_toast(f"Queued \u00B7 {v.title[:50]}")
        self._switch_tab(1)

    def _start_playlist_selected(self) -> None:
        items = self.playlist_panel.selected_entries()
        self._enqueue_playlist(items, label=f"{len(items)} selected")

    def _start_playlist_all(self) -> None:
        items = self.playlist_panel.all_entries()
        self._enqueue_playlist(items, label=f"all {len(items)}")

    def _enqueue_playlist(self, items, label: str) -> None:
        if not items:
            return
        q = self.format_picker.selected_option() or MP4_QUALITIES[2]
        out_dir = config.ensure_save_subdir("audio" if q.kind == "audio" else "video")
        tpl = config.get("filename_template", "{title} [{quality}].{ext}")
        for i, v in enumerate(items, 1):
            # Pre-render the index in the title so we don't put format specs
            # in the yt-dlp output template (those get sanitized into the
            # literal token and leave "{index#02d}" in the filename).
            t = f"{i:02d} - {v.title}" if v.title else f"{i:02d}"
            req = DownloadRequest(
                url=v.webpage_url, title=t, uploader=v.uploader, vid_id=v.id,
                quality_key=q.key, out_dir=out_dir, template=tpl,
                audio_only=(q.kind == "audio"),
            )
            self.queue.enqueue(req)
        self._show_toast(f"Queued \u00B7 {label}")
        self._switch_tab(1)

    # ---------- Queue callbacks ----------
    def _on_added(self, item_id: str) -> None:
        # Subtle per-item sound; the calling site (single / playlist) shows the
        # aggregate toast so the user doesn't get a spam of identical toasts.
        self.sound.play("queue")
        active = self.queue.active_count()
        total = self.queue.slots()
        self.queue_bar.update_active(active, total)
        self.sidebar.set_badge("queue", sum(
            1 for it in self.queue.all_items()
            if it.status in ("active", "paused", "pending")
        ))
        self._set_state("downloading" if active else "idle")

    def _on_started(self, item_id: str) -> None:
        for it in self.queue.all_items():
            if it.item_id == item_id:
                card = ProgressCard(theme=self._theme_palette)
                # Fall back to URL for bulk downloads where title is empty.
                card.set_title(it.req.title or it.req.url)
                self.queue_progress.layout().insertWidget(0, card)
                self.queue_progress.setVisible(True)
                # Hide the empty state overlay now that we have real cards.
                if hasattr(self, "queue_empty") and self.queue_empty is not None:
                    self.queue_empty.setVisible(False)
                self._per_video_progress[item_id] = card
                card.cancel.connect(lambda iid=item_id: self.queue.cancel(iid))
                card.pause_toggle.connect(lambda iid=item_id: self.queue.toggle_pause(iid))
                card.open_folder.connect(self._open_path)
                anim.slide_up_in(card, distance=6, duration_ms=200)
                break
        self.queue_bar.update_active(self.queue.active_count(), self.queue.slots())
        self._set_state("downloading")
        # Scroll the new card into view if the queue is already tall.
        sb = self.queue_scroll.verticalScrollBar()
        if sb is not None and sb.maximum() > 0:
            sb.setValue(0)  # newest card is at the top — show it

    def _on_progress(self, item_id: str, pct: float, speed: float,
                     eta: float, downloaded: int, total: int) -> None:
        card = self._per_video_progress.get(item_id)
        if card:
            card.update_progress(pct, speed, eta, downloaded, total)

    def _on_status(self, item_id: str, status: str) -> None:
        card = self._per_video_progress.get(item_id)
        if card and status in ("active", "paused", "done", "error", "cancelled"):
            card.set_status(status)

    def _on_finished(self, item_id: str, ok: bool, result: str) -> None:
        card = self._per_video_progress.get(item_id)
        for it in self.queue.all_items():
            if it.item_id == item_id:
                if ok:
                    if card:
                        card.set_path(result)
                        card.set_status("done")
                    self._show_toast(f"Done \u00B7 {it.req.title[:50]}")
                    self.sound.play("done")
                    self._done_count += 1
                    if it.req.audio_only:
                        try:
                            from core import tags as _tags
                            _tags.tag_mp3(
                                Path(result), title=it.req.title,
                                artist=it.req.uploader, album="Tex downloads",
                            )
                        except Exception:
                            pass
                    try:
                        size = history.try_get_size(result)
                        history.add(history.HistoryEntry(
                            title=it.req.title, uploader=it.req.uploader, url=it.req.url,
                            quality=it.req.quality_key,
                            kind="audio" if it.req.audio_only else "video",
                            path=result, size=size,
                            finished_at=__import__("time").time(),
                        ))
                    except Exception:
                        pass
                else:
                    if card:
                        if "Cancel" in result:
                            card.set_status("cancelled")
                        else:
                            card.set_status("error")
                            card.file_lbl.setText(f"Error \u00B7 {result}")
                    self._show_toast(f"Error \u00B7 {result[:60]}", 4000)
                    self.sound.play("error")
                break
        active = self.queue.active_count()
        self.queue_bar.update_active(active, self.queue.slots())
        self.sidebar.set_badge("queue", sum(
            1 for it in self.queue.all_items()
            if it.status in ("active", "paused", "pending")
        ))
        if active == 0:
            self._set_state("idle")

    def _on_slots(self, active: int, total: int) -> None:
        self.queue_bar.update_active(active, total)
        if hasattr(self, "page_settings"):
            self.page_settings.set_queue_info(active, total)

    def _on_clear_finished(self) -> None:
        self.queue.clear_finished()
        keep_ids = {it.item_id for it in self.queue.all_items()}
        for iid in list(self._per_video_progress.keys()):
            if iid not in keep_ids:
                card = self._per_video_progress.pop(iid)
                card.cleanup()
                # Disconnect any signals from the card to prevent use-after-free
                try:
                    card.cancel.disconnect()
                    card.pause_toggle.disconnect()
                    card.open_folder.disconnect()
                except RuntimeError:
                    pass
                card.deleteLater()
        if not self._per_video_progress:
            self.queue_progress.setVisible(False)
            if hasattr(self, "queue_empty") and self.queue_empty is not None:
                self.queue_empty.setVisible(True)
                self._position_queue_empty()
        self.sidebar.set_badge("queue", 0)
        self._show_toast("Cleared")

    # ---------- Channel tab ----------
    def _on_channel_fetch(self, url: str, content_type: str, max_count: int) -> None:
        # Kill any in-flight channel worker to avoid race conditions.
        if hasattr(self, '_channel_worker') and self._channel_worker is not None:
            try:
                self._channel_worker.ok.disconnect()
                self._channel_worker.fail.disconnect()
            except RuntimeError:
                pass
            if self._channel_worker.isRunning():
                self._channel_worker.requestInterruption()
                self._channel_worker.quit()
                self._channel_worker.wait(3000)
            self._channel_worker.deleteLater()
        self._channel_worker = _ChannelWorker(url, content_type, max_count)
        self._channel_worker.ok.connect(self._on_channel_ok)
        self._channel_worker.fail.connect(self._on_channel_fail)
        self._channel_worker.start()

    def _on_channel_ok(self, channel) -> None:
        self.page_channels.set_fetching(False)
        self.page_channels.set_channel(channel)
        n = len(channel.entries)
        if n:
            self.sound.play("fetch")
        self._show_toast(f"{channel.title}  \u00B7  {n} item{'s' if n != 1 else ''}")

    def _on_channel_fail(self, err: str) -> None:
        self.page_channels.set_fetching(False)
        self.page_channels.set_status(f"Error  \u00B7  {err}")
        self.sound.play("error")
        self._show_toast(f"Error  \u00B7  {err}", 4000)

    # ---------- Editor trim download ----------
    def _fmt_sec(self, s: float) -> str:
        s = max(0.0, s)
        h, rem = divmod(int(s), 3600)
        m, sec = divmod(rem, 60)
        if h:
            return f"{h}:{m:02d}:{sec:02d}"
        return f"{m}:{sec:02d}"

    def _on_trim_download(self, url: str, start_sec: float, end_sec: float, quality) -> None:
        """Download a trimmed section of a video using yt-dlp's --download-sections."""
        from core.naming import render_path, unique_path
        ext = "mp4"
        out_dir = config.ensure_save_subdir("video")
        tpl = config.get("filename_template", "{title} [{quality}].{ext}")
        trim_label = f"{self._fmt_sec(start_sec)}-{self._fmt_sec(end_sec)}"
        # Use the video title from the editor result if available
        video_title = ""
        if self.page_editor._result and self.page_editor._result.video:
            video_title = self.page_editor._result.video.title
        title = f"{video_title} [Trim {trim_label}]" if video_title else f"[Trim] {trim_label}"
        req = DownloadRequest(
            url=url, title=title, uploader="", vid_id="",
            quality_key=quality.key, out_dir=str(out_dir), template=tpl,
            audio_only=False,
            trim_start=start_sec, trim_end=end_sec,
        )
        self.queue.enqueue(req)
        self.sound.play("queue")
        self._show_toast(f"Queued \u00B7 Trim {self._fmt_sec(start_sec)} \u2192 {self._fmt_sec(end_sec)}")
        self._switch_tab(1)

    def _on_channel_download(self, entries: list) -> None:
        """Enqueue every selected channel entry under a channel-named folder."""
        from core.channel import _channel_dir, ChannelInfo
        from pathlib import Path
        # Build a fake ChannelInfo just to get the dir; cheap.
        ch = ChannelInfo(
            id="", title=self.page_channels._channel_title or "channel",
            uploader="", url="", platform="generic", entries=entries,
        )
        out_dir = _channel_dir(ch)
        try:
            Path(out_dir).mkdir(parents=True, exist_ok=True)
        except Exception:
            pass
        # Use the quality the user picked on the Channels panel itself, not
        # the main page's picker (the two are independent now).
        q = self.page_channels.selected_quality() or MP4_QUALITIES[2]
        tpl = config.get("filename_template", "{title} [{quality}].{ext}")
        reqs = []
        for i, e in enumerate(entries, 1):
            # Pre-render the index in the title — don't put format specs in
            # the yt-dlp output template (the colon in {index:02d} triggers
            # yt-dlp's format-spec parser, which leaves the literal token
            # in the final filename and causes 'Output file not found').
            raw_title = e.get("title", "") or "Untitled"
            t = f"{i:02d} - {raw_title}"
            reqs.append(DownloadRequest(
                url=e.get("webpage_url") or e.get("url", ""),
                title=t,
                uploader=e.get("uploader", ""),
                vid_id=e.get("id", ""),
                quality_key=q.key,
                out_dir=out_dir,
                template=tpl,
                audio_only=(q.kind == "audio"),
            ))
        if reqs:
            self.queue.enqueue_many(reqs)
            self.sound.play("queue")
            self._show_toast(f"Queued  \u00B7  {len(reqs)} from {ch.title[:30]}")
            self._switch_tab(1)  # jump to Queue tab

    def _open_path(self, path: str) -> None:
        try:
            p = Path(path)
            if sys.platform.startswith("win"):
                if p.is_dir():
                    os.startfile(p)
                else:
                    subprocess.Popen(["explorer", "/select," + str(p)])
            elif sys.platform == "darwin":
                subprocess.Popen(["open", "-R", str(p)])
            else:
                subprocess.Popen(["xdg-open", str(p.parent)])
        except Exception as e:
            self._show_toast(f"Open failed \u00B7 {e}", 3000)

    # ---------- Settings ----------
    def _on_settings_changed(self) -> None:
        self.page_settings.apply()
        # Only re-apply the theme when it actually changed — applying QSS to
        # the whole app tree is expensive (200+ widgets, large string).
        new_theme = config.get("theme", "dark")
        if new_theme != self._current_theme:
            self._current_theme = new_theme
            _, self._theme_palette = ui_theme.apply_theme(
                QApplication.instance(), new_theme
            )
            self._dot_bg.set_theme(new_theme != "light")
            # Refresh icons on every themed widget — the SVG icon code
            # reads its color from the palette dict, not from QSS.
            self._propagate_theme()
        self.queue.set_max_slots(int(config.get("concurrency", 0)))
        self.clip_watcher.set_enabled(bool(config.get("watch_clipboard", True)))
        self.queue_bar.set_slots(int(config.get("concurrency", 0)))
        self.sound.set_enabled(bool(config.get("sounds_enabled", True)))
        if self.page_settings._dirty:
            self._show_toast("Saved")
            self.page_settings._dirty = False

    def _pick_save_dir(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Choose save folder", config.get("save_dir"))
        if path:
            self.page_settings.set_save_dir(path)

    def _propagate_theme(self) -> None:
        """Push the current theme palette to every themed widget."""
        p = self._theme_palette
        self.titlebar.set_theme(p)
        self.sidebar.set_theme(p)
        self.page_channels.set_theme(p)
        self.page_editor.set_theme(p)
        for card in self._per_video_progress.values():
            card.set_theme(p)
        self.open_save_btn.set_theme(p)

    # ---------- Drag & drop ----------
    def dragEnterEvent(self, e: QDragEnterEvent) -> None:
        if e.mimeData().hasText():
            urls = extract_urls(e.mimeData().text())
            if urls:
                e.acceptProposedAction()

    def dropEvent(self, e: QDropEvent) -> None:
        urls = extract_urls(e.mimeData().text())
        if urls:
            if len(urls) == 1:
                self.url_bar.set_text(urls[0])
            else:
                # Multi-URL drop — join and let _on_fetch handle bulk enqueue
                joined = " ".join(urls)
                self.url_bar.set_text(joined)
                self._on_fetch(joined)

    # ---------- Clipboard ----------
    def _on_url_from_clipboard(self, url: str) -> None:
        if self.isActiveWindow():
            # Skip if the URL bar already shows this exact URL
            if self.url_bar.text().strip() == url.strip():
                return
            self._show_toast(f"URL detected \u00B7 {url[:40]}")
            self.sound.play("tick")
            self.url_bar.set_text(url)

    # ---------- Tray / close ----------
    def closeEvent(self, e) -> None:
        if self.tray and self.tray.isVisible() and config.get("minimize_to_tray", True):
            e.ignore()
            self.hide()
        else:
            self._quit()

    def _show(self) -> None:
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def _quit(self) -> None:
        if self.tray:
            self.tray.hide()
        # Stop clipboard watcher
        self.clip_watcher.stop()
        # Kill fetch worker if running
        if self._fetch_worker is not None:
            try:
                self._fetch_worker.ok.disconnect()
                self._fetch_worker.fail.disconnect()
                self._fetch_worker.retried_without_cookies.disconnect()
            except RuntimeError:
                pass
            if self._fetch_worker.isRunning():
                self._fetch_worker.requestInterruption()
                self._fetch_worker.quit()
                self._fetch_worker.wait(3000)
            self._fetch_worker.deleteLater()
            self._fetch_worker = None
        # Kill channel worker if running
        if hasattr(self, '_channel_worker') and self._channel_worker is not None:
            try:
                self._channel_worker.ok.disconnect()
                self._channel_worker.fail.disconnect()
            except RuntimeError:
                pass
            if self._channel_worker.isRunning():
                self._channel_worker.requestInterruption()
                self._channel_worker.quit()
                self._channel_worker.wait(3000)
            self._channel_worker.deleteLater()
            self._channel_worker = None
        self.queue.cancel_all()
        # Wait for active downloads to stop — avoid orphaned yt-dlp subprocesses.
        for it in self.queue.all_items():
            if it.worker and it.worker.isRunning():
                it.worker.quit()
                it.worker.wait(2000)
        QApplication.instance().quit()
