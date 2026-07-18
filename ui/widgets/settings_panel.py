"""Settings panel — iOS list-row feel, mixed case, with About section.

Each row: [fixed-width title]  [stretch]  [control].
Right-side controls are at their natural size (with max widths).
"""
from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QFrame, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QSizePolicy, QSpinBox, QVBoxLayout, QWidget,
)

from core import config

APP_VERSION = "0.3.1"


def _section_label(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setObjectName("SectionBig")
    return lbl


def _title(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setObjectName("S")
    return lbl


def _caption(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setObjectName("MetaDim")
    lbl.setWordWrap(True)
    return lbl


def _hairline() -> QFrame:
    d = QFrame()
    d.setObjectName("ThinDivider")
    d.setFixedHeight(1)
    return d


def _row(left_text: str, right: QWidget) -> QWidget:
    """iOS-style row: fixed-width title, stretch, right widget at natural size."""
    row = QWidget()
    row.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    lay = QHBoxLayout(row)
    lay.setContentsMargins(0, 12, 0, 12)
    lay.setSpacing(16)
    title = _title(left_text)
    title.setFixedWidth(200)
    lay.addWidget(title, 0, Qt.AlignmentFlag.AlignVCenter)
    lay.addStretch(1)
    lay.addWidget(right, 0, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight)
    return row


def _row_multi(left_text: str, *right_widgets: QWidget) -> QWidget:
    """Row with multiple right-side widgets (e.g. path + button)."""
    row = QWidget()
    row.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    lay = QHBoxLayout(row)
    lay.setContentsMargins(0, 12, 0, 12)
    lay.setSpacing(16)
    title = _title(left_text)
    title.setFixedWidth(200)
    lay.addWidget(title, 0, Qt.AlignmentFlag.AlignVCenter)
    lay.addStretch(1)
    inner = QWidget()
    inner.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
    il = QHBoxLayout(inner)
    il.setContentsMargins(0, 0, 0, 0)
    il.setSpacing(8)
    for w in right_widgets:
        il.addWidget(w, 0, Qt.AlignmentFlag.AlignVCenter)
    lay.addWidget(inner, 0, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight)
    return row


def _row_stack(left_text: str, *children: QWidget) -> QWidget:
    """Multi-line row: title on top, controls below."""
    row = QWidget()
    row.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    outer = QVBoxLayout(row)
    outer.setContentsMargins(0, 12, 0, 12)
    outer.setSpacing(6)
    if left_text:
        outer.addWidget(_title(left_text))
    for c in children:
        outer.addWidget(c)
    return row


def _kval(key: str, value: str) -> tuple[QWidget, QLabel]:
    k = _title(key)
    k.setFixedWidth(160)
    v = QLabel(value)
    v.setObjectName("S")
    v.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
    v.setWordWrap(True)
    v.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
    row = QWidget()
    row.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    lay = QHBoxLayout(row)
    lay.setContentsMargins(0, 10, 0, 10)
    lay.setSpacing(16)
    lay.addWidget(k, 0, Qt.AlignmentFlag.AlignVCenter)
    lay.addStretch(1)
    lay.addWidget(v, 0, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight)
    return row, v


class SettingsPanel(QFrame):
    changed = Signal()
    pick_save_dir = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("Card")
        self.setMinimumWidth(520)
        # Inside a QScrollArea; let it grow vertically to its natural size
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self._dirty = False

        outer = QVBoxLayout(self)
        outer.setContentsMargins(28, 24, 28, 24)
        outer.setSpacing(0)

        # Title
        title = QLabel("Settings")
        title.setObjectName("XL")
        title_row = QWidget()
        tl = QHBoxLayout(title_row)
        tl.setContentsMargins(0, 0, 0, 14)
        tl.addWidget(title)
        outer.addWidget(title_row)
        outer.addWidget(_hairline())

        cfg = config.load()

        # --- GENERAL ---
        outer.addWidget(_section_label("GENERAL"))
        outer.addWidget(_hairline())

        # Save folder
        self.save_dir_lbl = QLabel(cfg["save_dir"])
        self.save_dir_lbl.setObjectName("S")
        self.save_dir_lbl.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.save_dir_lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.save_dir_lbl.setMaximumWidth(240)
        self.save_dir_lbl.setMinimumWidth(80)
        self.btn_pick_dir = QPushButton("Choose")
        self.btn_pick_dir.setObjectName("Ghost")
        self.btn_pick_dir.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_pick_dir.setMaximumWidth(90)
        self.btn_pick_dir.clicked.connect(self.pick_save_dir.emit)
        outer.addWidget(_row_multi("Save folder", self.save_dir_lbl, self.btn_pick_dir))
        outer.addWidget(_hairline())

        # Theme
        from ui import theme as _ui_theme
        self.theme_combo = QComboBox()
        for theme_id, (label, _fn, _palette) in _ui_theme.THEMES.items():
            self.theme_combo.addItem(label, theme_id)
        # Select the current theme by id.
        current_id = cfg.get("theme", "dark")
        for i in range(self.theme_combo.count()):
            if self.theme_combo.itemData(i) == current_id:
                self.theme_combo.setCurrentIndex(i)
                break
        self.theme_combo.setMinimumWidth(140)
        self.theme_combo.setMaximumWidth(160)
        self.theme_combo.currentIndexChanged.connect(self._on_theme_changed)
        outer.addWidget(_row("Theme", self.theme_combo))
        outer.addWidget(_hairline())

        # Minimize to tray
        self.tray_chk = QCheckBox("Minimize to tray")
        self.tray_chk.setChecked(bool(cfg.get("minimize_to_tray", True)))
        self.tray_chk.stateChanged.connect(self._on_change)
        outer.addWidget(_row("Minimize to tray", self.tray_chk))
        outer.addWidget(_hairline())

        # Auto-detect
        self.clip_chk = QCheckBox("Auto-detect URLs from clipboard")
        self.clip_chk.setChecked(bool(cfg.get("watch_clipboard", True)))
        self.clip_chk.stateChanged.connect(self._on_change)
        outer.addWidget(_row("Auto-detect URLs from clipboard", self.clip_chk))
        outer.addWidget(_hairline())

        # --- FEEDBACK ---
        outer.addSpacing(8)
        outer.addWidget(_section_label("FEEDBACK"))
        outer.addWidget(_hairline())

        self.sound_chk = QCheckBox("Sound effects")
        self.sound_chk.setChecked(bool(cfg.get("sounds_enabled", True)))
        self.sound_chk.stateChanged.connect(self._on_change)
        outer.addWidget(_row("Sound effects", self.sound_chk))
        outer.addWidget(_hairline())

        # --- DOWNLOAD ---
        outer.addSpacing(8)
        outer.addWidget(_section_label("DOWNLOAD"))
        outer.addWidget(_hairline())

        self.conc_spin = QSpinBox()
        self.conc_spin.setRange(1, 16)
        # 0 means unlimited. Default to unlimited for the user-facing model.
        cur_conc = int(cfg.get("concurrency", 0))
        self.conc_spin.setValue(cur_conc if cur_conc > 0 else 8)
        self.conc_spin.setMinimumWidth(80)
        self.conc_spin.setMaximumWidth(100)
        self.conc_spin.valueChanged.connect(self._on_change)
        self.conc_unlimited_chk = QCheckBox("Unlimited parallel slots")
        # Checked when stored value is 0 / unset.
        # Block signals during init to prevent premature config save.
        self.conc_unlimited_chk.blockSignals(True)
        self.conc_unlimited_chk.setChecked(cur_conc <= 0)
        self.conc_unlimited_chk.blockSignals(False)
        self.conc_unlimited_chk.stateChanged.connect(self._on_conc_unlimited_toggle)
        # Spinbox is meaningless when unlimited is on — dim it.
        self.conc_spin.setEnabled(cur_conc > 0)
        outer.addWidget(_row("Parallel slots", self.conc_spin))
        outer.addWidget(self.conc_unlimited_chk)
        outer.addWidget(_hairline())

        self.speed_combo = QComboBox()
        self.speed_combo.addItems(["Unlimited", "10 MB/s", "5 MB/s", "2 MB/s", "1 MB/s"])
        bps = int(cfg.get("speed_limit_bps", 0) or 0)
        mapping = {0: "Unlimited", 10 * 1024 * 1024: "10 MB/s",
                   5 * 1024 * 1024: "5 MB/s", 2 * 1024 * 1024: "2 MB/s",
                   1 * 1024 * 1024: "1 MB/s"}
        self.speed_combo.setCurrentText(mapping.get(bps, "Unlimited"))
        self.speed_combo.setMinimumWidth(120)
        self.speed_combo.setMaximumWidth(140)
        self.speed_combo.currentTextChanged.connect(self._on_change)
        outer.addWidget(_row("Speed limit", self.speed_combo))
        outer.addWidget(_hairline())

        self.retries_spin = QSpinBox()
        self.retries_spin.setRange(0, 10)
        self.retries_spin.setValue(int(cfg.get("retries", 3)))
        self.retries_spin.setMinimumWidth(80)
        self.retries_spin.setMaximumWidth(100)
        self.retries_spin.valueChanged.connect(self._on_change)
        outer.addWidget(_row("Retries", self.retries_spin))
        outer.addWidget(_hairline())

        # Filename template
        self.tpl_edit = QLineEdit(cfg.get("filename_template", "{title} [{quality}].{ext}"))
        self.tpl_edit.textChanged.connect(self._on_change)
        outer.addWidget(_row_stack(
            "Filename template",
            self.tpl_edit,
            _caption("Tokens: {title}  ·  {channel}  ·  {quality}  ·  {id}  ·  {date}  ·  {ext}"),
        ))
        outer.addWidget(_hairline())

        # --- AUTH ---
        outer.addSpacing(8)
        outer.addWidget(_section_label("AUTHENTICATION"))
        outer.addWidget(_hairline())

        # Auto-detect browser for cookies; user can override or turn off entirely.
        from core.cookies import available_browsers, detect_browser
        installed = available_browsers()
        installed_keys = {b[0] for b in installed}
        current = (cfg.get("cookies_from_browser", "auto") or "auto").strip().lower()

        self.browser_combo = QComboBox()
        self.browser_combo.setMinimumWidth(140)
        self.browser_combo.setMaximumWidth(160)
        # First entry: Auto (use whichever browser is installed; detect on the fly).
        self.browser_combo.addItem("Auto", "auto")
        if not installed or current not in ("auto",):
            # When nothing is installed, force the default to "none" so we don't
            # silently fail every download.
            if not installed and current in ("auto",):
                current = "none"
        for key, label, _paths in installed:
            self.browser_combo.addItem(f"{label}  (detected)", key)
        # Always offer None and the common browsers as fallbacks.
        for key, label in [("none", "None"),
                           ("chrome", "Chrome"),
                           ("firefox", "Firefox"),
                           ("edge", "Microsoft Edge"),
                           ("brave", "Brave"),
                           ("opera", "Opera"),
                           ("vivaldi", "Vivaldi"),
                           ("safari", "Safari")]:
            if key in installed_keys or key == "none":
                continue
            self.browser_combo.addItem(label, key)
        # Pick the current value
        idx = self.browser_combo.findData(current)
        if idx < 0:
            idx = 0
        self.browser_combo.setCurrentIndex(idx)
        self.browser_combo.currentTextChanged.connect(self._on_change)
        outer.addWidget(_row("Use cookies from", self.browser_combo))
        outer.addWidget(_caption(
            "Auto uses your installed browser's cookies for age-restricted / private content. "
            "Choose a specific browser or None to override."
        ))
        outer.addWidget(_hairline())

        # --- ABOUT ---
        outer.addSpacing(8)
        outer.addWidget(_section_label("ABOUT"))
        outer.addWidget(_hairline())

        about_pairs = [
            ("App version",       "—"),
            ("Python",            "—"),
            ("yt-dlp",            "—"),
            ("FFmpeg",            "—"),
            ("Default save dir",  "—"),
            ("Active queue",      "—"),
        ]
        self._about_labels: dict[str, QLabel] = {}
        for key, val in about_pairs:
            row, v = _kval(key, val)
            self._about_labels[key] = v
            outer.addWidget(row)
            outer.addWidget(_hairline())

        outer.addStretch(1)
        self.status_lbl = QLabel("")
        self.status_lbl.setObjectName("Status")
        outer.addWidget(self.status_lbl)

        self.refresh_about()

    def _on_theme_changed(self, _idx: int) -> None:
        # Update the config key to the theme id (not the display label).
        self._pending_theme_id = self.theme_combo.currentData()
        self._on_change()

    def _on_change(self, *_a) -> None:
        # Debounce — spinbox arrow keys, text edits, and combo changes can
        # fire dozens of signals per second. The expensive side (theme re-apply,
        # config save, ffmpeg probe) only needs to run once per user gesture.
        if not hasattr(self, "_change_timer"):
            from PySide6.QtCore import QTimer
            self._change_timer = QTimer(self)
            self._change_timer.setSingleShot(True)
            self._change_timer.setInterval(250)
            self._change_timer.timeout.connect(self._emit_changed)
        self._change_timer.start()

    def _on_conc_unlimited_toggle(self, *_a) -> None:
        # Disable the spinbox when unlimited is on — the value is meaningless
        # in that case and we store 0 to mean "unlimited".
        self.conc_spin.setEnabled(not self.conc_unlimited_chk.isChecked())
        self._on_change()

    def _emit_changed(self) -> None:
        self._dirty = True
        self.changed.emit()

    def set_save_dir(self, path: str) -> None:
        self.save_dir_lbl.setText(path)
        # Save dir changed — refresh About so the new path shows (static
        # fields are still cached so no subprocess re-run).
        self.refresh_about()
        self._on_change()

    def show_status(self, msg: str) -> None:
        self.status_lbl.setText(msg)

    def set_queue_info(self, active: int, total: int) -> None:
        v = self._about_labels.get("Active queue")
        if v:
            v.setText(f"{active} of {total} in flight")

    def refresh_about(self) -> None:
        # ffmpeg version probe is expensive (subprocess). Only run it once.
        if not hasattr(self, "_about_static") or not self._about_static:
            from core.metadata import ffmpeg_location
            try:
                import yt_dlp
                ytdlp_ver = getattr(yt_dlp, "version", None) or "unknown"
            except Exception:
                ytdlp_ver = "unknown"

            ffm = ffmpeg_location()
            if ffm and Path(ffm).exists():
                ver = "—"
                try:
                    import subprocess
                    out = subprocess.run(
                        [ffm, "-version"], capture_output=True, text=True, timeout=3,
                    )
                    first = (out.stdout or "").splitlines()[0] if out.stdout else ""
                    toks = first.split()
                    if len(toks) >= 3 and toks[0] == "ffmpeg":
                        ver = toks[2]
                except Exception:
                    pass
                ff_text = f"{Path(ffm).name}  ·  {ver}"
            else:
                ff_text = "not found"
            self._about_static = {
                "App version": APP_VERSION,
                "Python":      f"{sys.version.split()[0]}",
                "yt-dlp":      str(ytdlp_ver),
                "FFmpeg":      ff_text,
            }
        # Dynamic parts (save dir) refresh on every call.
        cfg = config.load()
        values = dict(self._about_static)
        values["Default save dir"] = cfg.get("save_dir", "—")
        for k, v in values.items():
            label = self._about_labels.get(k)
            if label:
                label.setText(v)

    def apply(self) -> None:
        cfg = config.load()
        cfg["save_dir"] = self.save_dir_lbl.text()
        cfg["theme"] = getattr(self, "_pending_theme_id", None) or self.theme_combo.currentData() or "dark"
        # 0 (or negative) means unlimited — store the actual spin value but
        # interpret it as 0 when the unlimited checkbox is on.
        if self.conc_unlimited_chk.isChecked():
            cfg["concurrency"] = 0
        else:
            cfg["concurrency"] = self.conc_spin.value()

        sm = {"Unlimited": 0, "10 MB/s": 10 * 1024 * 1024,
              "5 MB/s": 5 * 1024 * 1024, "2 MB/s": 2 * 1024 * 1024,
              "1 MB/s": 1 * 1024 * 1024}
        cfg["speed_limit_bps"] = sm.get(self.speed_combo.currentText(), 0)
        cfg["cookies_from_browser"] = self.browser_combo.currentData() or "auto"
        cfg["filename_template"] = self.tpl_edit.text() or "{title} [{quality}].{ext}"
        cfg["watch_clipboard"] = self.clip_chk.isChecked()
        cfg["minimize_to_tray"] = self.tray_chk.isChecked()
        cfg["sounds_enabled"] = self.sound_chk.isChecked()
        cfg["retries"] = self.retries_spin.value()
        config.save(cfg)
