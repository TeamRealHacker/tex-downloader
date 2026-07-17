"""Progress card: compact 3-row layout (status+title, dotty bar, stats+buttons)."""
from __future__ import annotations

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QPalette
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QPushButton, QSizePolicy, QVBoxLayout,
)

from ui import icons
from ui.widgets.dot_matrix import TEX_GLYPH_X, DotMatrix  # noqa: F401
from ui.widgets.icon_button import IconButton
from ui.widgets.segmented_bar import SegmentedBar


def _human_bytes(n: float) -> str:
    if not n:
        return "—"
    n = float(n)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(n) < 1024.0:
            if unit == "B":
                return f"{int(n)} {unit}"
            return f"{n:.1f} {unit}"
        n /= 1024.0
    return f"{n:.1f} PB"


def _human_speed(bps: float) -> str:
    if not bps:
        return "—"
    return f"{_human_bytes(bps)}/s"


def _human_eta(seconds: float) -> str:
    if not seconds or seconds < 0:
        return "—"
    s = int(seconds)
    if s < 60:
        return f"{s}s"
    m, s = divmod(s, 60)
    if m < 60:
        return f"{m}m {s}s"
    h, m = divmod(m, 60)
    return f"{h}h {m}m"


class ProgressCard(QFrame):
    cancel = Signal()
    pause_toggle = Signal()
    open_folder = Signal(str)

    # Class-level — avoids recreating the dict on every state change.
    _STATE_TEXT = {
        "active": "DOWNLOADING",
        "paused": "PAUSED",
        "done": "DONE",
        "error": "ERROR",
        "cancelled": "CANCELLED",
    }

    def __init__(self, theme: dict | None = None, parent=None):
        super().__init__(parent)
        self.setObjectName("Card")
        self._path: str = ""
        self._finished = False
        self._theme = theme or {
            "fg": "#FFFFFF", "fg_dim": "#9A9A9A", "accent": "#D7191A",
        }

        # Tight padding — the card is supposed to be ~75px tall total.
        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 9, 12, 9)
        lay.setSpacing(5)

        # ---- Row 1: status · title · percent · buttons ----
        r1 = QHBoxLayout()
        r1.setSpacing(10)
        r1.setContentsMargins(0, 0, 0, 0)

        self.status_lbl = QLabel("DOWNLOADING")
        self.status_lbl.setObjectName("StatusLbl")
        self.status_lbl.setProperty("pState", "active")
        # 96px is enough for "DOWNLOADING" (12 chars) at 10pt mono.
        self.status_lbl.setFixedWidth(96)
        r1.addWidget(self.status_lbl)

        self.file_lbl = QLabel("")
        self.file_lbl.setObjectName("Title")
        self.file_lbl.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        # Elide on the right so very long titles don't push the percent off.
        self.file_lbl.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        r1.addWidget(self.file_lbl, 1)

        self.percent_lbl = QLabel("0.0%")
        self.percent_lbl.setObjectName("NumMed")
        self.percent_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.percent_lbl.setFixedWidth(60)
        r1.addWidget(self.percent_lbl)

        # Compact icon buttons — hand-rolled SVGs, no emoji.
        self.btn_pause = IconButton("pause", size=11, width=28, height=24,
                                    theme=self._theme)
        self.btn_pause.clicked.connect(self.pause_toggle.emit)
        r1.addWidget(self.btn_pause)

        self.btn_cancel = IconButton("x", size=12, width=28, height=24,
                                     theme=self._theme)
        self.btn_cancel.clicked.connect(self.cancel.emit)
        r1.addWidget(self.btn_cancel)

        # "OPEN" primary button — an icon + label, all SVG.
        self.btn_open = _OpenButton()
        self.btn_open.setVisible(False)
        self.btn_open.clicked.connect(self._emit_open)
        r1.addWidget(self.btn_open)

        lay.addLayout(r1)

        # ---- Row 2: dotty segmented bar (30 segments, grows one-by-one) ----
        self.bar = SegmentedBar(segments=30, height=6)
        lay.addWidget(self.bar)

        # ---- Row 3: stats line ----
        self.stats_lbl = QLabel("\u2014  \u00B7  \u2014  \u00B7  \u2014")
        self.stats_lbl.setObjectName("Status")
        lay.addWidget(self.stats_lbl)

        self.setVisible(False)

        # Smoothly animate the bar fill toward the target pct.
        self._bar_target = 0.0
        self._bar_current = 0.0
        self._bar_timer = QTimer(self)
        self._bar_timer.setInterval(45)  # ~22fps — smooth, low CPU
        self._bar_timer.timeout.connect(self._tick_bar)

    # --- public API ---
    def set_title(self, title: str) -> None:
        # Use Qt's elide so long titles get "…" on the right when the row is
        # narrow. The tooltip keeps the full text available on hover.
        fm = self.file_lbl.fontMetrics()
        # Use the label's actual width (or a sensible default if not yet laid out).
        # maximumWidth() returns QWIDGETSIZE_MAX when not explicitly set, which
        # means elision would never trigger for long video titles.
        avail = self.file_lbl.width() if self.file_lbl.width() > 50 else 600
        elided = fm.elidedText(title, Qt.TextElideMode.ElideRight, avail - 10)
        self.file_lbl.setText(elided)
        self.file_lbl.setToolTip(title)
        self._finished = False
        self.setVisible(True)
        self.btn_open.setVisible(False)
        self.btn_pause.setVisible(True)
        self.btn_cancel.setVisible(True)
        self._set_state("active")

    def _set_state(self, state: str) -> None:
        self.status_lbl.setText(self._STATE_TEXT.get(state, "DOWNLOADING"))
        # Dynamic property triggers QSS re-evaluation without the expensive
        # style().unpolish() / polish() round-trip.
        self.status_lbl.setProperty("pState", state)
        self.status_lbl.update()
        if state == "active":
            self.btn_pause.set_icon("pause")
        elif state == "paused":
            self.btn_pause.set_icon("play")
        elif state == "done":
            self.btn_pause.setVisible(False)
            self.btn_cancel.setVisible(False)
            self.btn_open.setVisible(True)
            # Fill the bar on completion.
            self._bar_target = 1.0
            if not self._bar_timer.isActive():
                self._bar_timer.start()
        elif state in ("error", "cancelled"):
            self.btn_pause.setVisible(False)
            self.btn_cancel.setVisible(False)

    def set_status(self, status: str) -> None:
        if status in ("active", "paused", "done", "error", "cancelled"):
            self._set_state(status)

    def update_progress(self, pct: float, speed: float, eta: float,
                        downloaded: int, total: int) -> None:
        self._bar_target = max(0.0, min(1.0, pct / 100.0))
        if not self._bar_timer.isActive():
            self._bar_timer.start()
        # Right-aligned, monospace — always 6 chars wide so the layout
        # never reflows as the percentage changes.
        self.percent_lbl.setText(f"{pct:5.1f}%")
        speed_s = _human_speed(speed)
        eta_s = _human_eta(eta)
        if total:
            size_s = f"{_human_bytes(downloaded)} / {_human_bytes(total)}"
        else:
            size_s = _human_bytes(downloaded)
        self.stats_lbl.setText(f"{speed_s}  \u00B7  ETA {eta_s}  \u00B7  {size_s}")

    def set_path(self, path: str) -> None:
        self._path = path

    def set_theme(self, theme: dict) -> None:
        self._theme = theme
        if hasattr(self, "btn_pause") and hasattr(self.btn_pause, "set_theme"):
            self.btn_pause.set_theme(theme)
        if hasattr(self, "btn_cancel") and hasattr(self.btn_cancel, "set_theme"):
            self.btn_cancel.set_theme(theme)

    def _emit_open(self) -> None:
        if self._path:
            self.open_folder.emit(self._path)

    def _tick_bar(self) -> None:
        diff = self._bar_target - self._bar_current
        if abs(diff) < 0.005:
            self._bar_current = self._bar_target
            self.bar.set_fill(self._bar_current)
            self._bar_timer.stop()
            return
        # Ease the bar toward the target — 12% of the gap per tick.
        self._bar_current += diff * 0.12
        self.bar.set_fill(self._bar_current)

    def cleanup(self) -> None:
        """Stop the animation timer before deletion to prevent use-after-free."""
        if self._bar_timer.isActive():
            self._bar_timer.stop()


class _OpenButton(QFrame):
    """A small 'OPEN' primary action button with an SVG arrow icon."""

    clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("Primary")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(24)
        self.setProperty("hot", False)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(10, 0, 8, 0)
        lay.setSpacing(6)

        from PySide6.QtWidgets import QLabel
        self._text = QLabel("OPEN")
        self._text.setObjectName("PrimaryText")
        self._text.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        lay.addWidget(self._text, 0, Qt.AlignmentFlag.AlignVCenter)

        self._arrow = QLabel(self)
        self._arrow.setObjectName("PrimaryArrow")
        self._arrow.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self._arrow.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._arrow.setFixedSize(14, 14)
        lay.addWidget(self._arrow, 0, Qt.AlignmentFlag.AlignVCenter)

        self._refresh_arrow()

    def _refresh_arrow(self) -> None:
        # White on the red Primary button.
        self._arrow.setProperty("iconColor", "#FFFFFF")
        self._arrow.setPixmap(icons.render("open_external", "#FFFFFF", 12))

    def changeEvent(self, e) -> None:
        if e.type() == e.Type.PaletteChange:
            self._refresh_arrow()
        super().changeEvent(e)

    def showEvent(self, e) -> None:
        self._refresh_arrow()
        super().showEvent(e)

    def _set_hot(self, v) -> None:
        self.setProperty("hot", v)
        self.style().unpolish(self)
        self.style().polish(self)

    def enterEvent(self, e) -> None:
        self._set_hot("hover")

    def leaveEvent(self, e) -> None:
        self._set_hot(False)

    def mousePressEvent(self, e) -> None:
        if e.button() == Qt.MouseButton.LeftButton:
            self._set_hot("active")
            e.accept()

    def mouseReleaseEvent(self, e) -> None:
        if e.button() == Qt.MouseButton.LeftButton:
            self._set_hot("hover")
            if self.rect().contains(e.position().toPoint()):
                self.clicked.emit()
            e.accept()
