"""Format picker: VIDEO (MP4) and AUDIO (MP3). Two clean rows of chips."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QButtonGroup, QFrame, QGridLayout, QHBoxLayout, QLabel, QPushButton, QVBoxLayout,
)

from core.formats import MP3_QUALITIES, MP4_QUALITIES, QualityOption


class FormatChip(QFrame):
    clicked = Signal()

    def __init__(self, opt: QualityOption, parent=None):
        super().__init__(parent)
        self.setObjectName("CardInset")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.opt = opt
        self._selected = False
        self._size_text = ""
        self._available = True  # False when the format isn't available for this video

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        self._btn = QPushButton(opt.label)
        self._btn.setObjectName("Chip")
        self._btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn.setCheckable(True)
        self._btn.clicked.connect(self.clicked.emit)
        lay.addWidget(self._btn)

        self.size_lbl = QLabel("\u2014")
        self.size_lbl.setObjectName("ChipSize")
        self.size_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.size_lbl.setFixedHeight(20)
        self.size_lbl.setStyleSheet("background: transparent; padding: 0px 0px 4px 0px;")
        lay.addWidget(self.size_lbl)

    def set_size(self, text: str) -> None:
        """Set the human-readable size estimate. ``"-"`` (em-dash) means
        the format is unavailable for this video — disable the chip."""
        self._size_text = text
        self.size_lbl.setText(text.upper())
        # "—" / "N/A" / "" all count as unavailable.
        unavailable = (not text) or text.strip() in ("\u2014", "-", "N/A", "n/a", "")
        self.set_available(not unavailable)

    def set_available(self, on: bool) -> None:
        self._available = bool(on)
        # Disabled chips: gray out, no hover, no click feedback.
        self._btn.setEnabled(bool(on))
        self.setObjectName("CardDisabled" if not on else "CardInset")
        cursor = Qt.CursorShape.PointingHandCursor if on else Qt.CursorShape.ForbiddenCursor
        self.setCursor(cursor)
        self._btn.setCursor(cursor)
        self.update()
        self.size_lbl.update()

    def is_available(self) -> bool:
        return self._available

    def set_selected(self, sel: bool) -> None:
        self._selected = sel
        self._btn.setChecked(sel)
        # setObjectName alone re-evaluates the QSS — no unpolish/polish dance needed.
        self.setObjectName("CardBright" if sel else "CardInset")
        self.size_lbl.setObjectName("ChipSizeChecked" if sel else "ChipSize")
        self.update()
        self.size_lbl.update()

    def is_selected(self) -> bool:
        return self._selected

    def set_loading(self, on: bool) -> None:
        self.size_lbl.setText("\u2026" if on else "\u2014")


class FormatPicker(QFrame):
    selected = Signal(QualityOption)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("Card")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(14, 12, 14, 14)
        outer.setSpacing(10)

        # Video
        vid_lbl = QLabel("VIDEO  \u00B7  MP4")
        vid_lbl.setObjectName("Section")
        outer.addWidget(vid_lbl)

        self._video_grid = QGridLayout()
        self._video_grid.setSpacing(6)
        outer.addLayout(self._video_grid)

        # Divider
        div = QFrame()
        div.setObjectName("ThinDivider")
        div.setFixedHeight(1)
        outer.addWidget(div)

        # Audio
        aud_lbl = QLabel("AUDIO  \u00B7  MP3")
        aud_lbl.setObjectName("Section")
        outer.addWidget(aud_lbl)

        self._audio_grid = QGridLayout()
        self._audio_grid.setSpacing(6)
        outer.addLayout(self._audio_grid)

        self._chips: dict[str, FormatChip] = {}
        self._selected_key: str = "1080p"
        self._group = QButtonGroup(self)
        self._group.setExclusive(True)

        for i, opt in enumerate(MP4_QUALITIES):
            chip = FormatChip(opt)
            chip.clicked.connect(lambda _=False, o=opt: self._emit(o))
            self._group.addButton(chip._btn)
            self._chips[opt.key] = chip
            self._video_grid.addWidget(chip, 0, i)
            chip.setMinimumWidth(96)

        for i, opt in enumerate(MP3_QUALITIES):
            chip = FormatChip(opt)
            chip.clicked.connect(lambda _=False, o=opt: self._emit(o))
            self._group.addButton(chip._btn)
            self._chips[opt.key] = chip
            self._audio_grid.addWidget(chip, 0, i)
            chip.setMinimumWidth(96)

        self._chips[self._selected_key].set_selected(True)

    def _emit(self, opt: QualityOption) -> None:
        for key, chip in self._chips.items():
            selected = chip.opt.key == opt.key
            chip.set_selected(selected)
            # Keep QButtonGroup in sync so checkable button state is consistent
            if selected:
                self._group.blockSignals(True)
                chip._btn.setChecked(True)
                self._group.blockSignals(False)
        self._selected_key = opt.key
        self.selected.emit(opt)

    def selected_option(self) -> QualityOption:
        for opt in MP4_QUALITIES + MP3_QUALITIES:
            if opt.key == self._selected_key:
                return opt
        return MP4_QUALITIES[2]

    def set_size_estimates(self, sizes: dict[str, str]) -> None:
        for key, txt in sizes.items():
            chip = self._chips.get(key)
            if chip:
                chip.set_size(txt)

    def set_loading_sizes(self, loading: bool) -> None:
        for chip in self._chips.values():
            chip.set_loading(loading)
