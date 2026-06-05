"""Quote / fun-fact card: quote on top, attribution underneath.

Rotates through a list of curated Nothing-OS style lines.
"""
from __future__ import annotations

import random

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout

from ui.widgets.dot_matrix import TEX_GLYPH_X, DotMatrix


_QUOTES: list[tuple[str, str]] = [
    ("A watched pot never boils. A watched download never finishes.",
     "INTERNET PROVERB"),
    ("4K or it didn't happen.", "FUN FACT"),
    ("Rats laugh when tickled; humans can't hear it.", "FUN FACT"),
    ("There are more possible chess games than atoms in the observable universe.",
     "FUN FACT"),
    ("If you judge people, you have no time to love them.", "MOTHER TERESA"),
    ("The first computer bug was an actual moth, taped to a log in 1947.",
     "FUN FACT"),
    ("Octopuses have three hearts and blue blood.", "FUN FACT"),
    ("Stay hungry, stay foolish.", "STEVE JOBS"),
    ("Honey never spoils. Archaeologists have eaten 3,000-year-old honey.",
     "FUN FACT"),
    ("Bananas are berries. Strawberries are not.", "FUN FACT"),
    ("The quieter you become, the more you can hear.", "RAM DASS"),
    ("There is no patch for human stupidity.", "UNKNOWN"),
    ("A smooth sea never made a skilled sailor.", "FRANKLIN D. ROOSEVELT"),
    ("Done is better than perfect.", "SHERYL SANDBERG"),
    ("Whatever you do, do it with all your might.", "CICERO"),
]


class QuoteTile(QFrame):
    """Bento tile showing a rotating fun fact / quote."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("CardBright")

        lay = QVBoxLayout(self)
        lay.setContentsMargins(22, 22, 22, 22)
        lay.setSpacing(14)

        # Top row: dot-matrix glyph + label
        top = QVBoxLayout()
        top.setSpacing(10)
        self.glyph = DotMatrix(TEX_GLYPH_X, pixel=4, gap=2, on_color="#D7191A")
        self.lbl_section = QLabel("FUN FACTS")
        self.lbl_section.setObjectName("Status")
        top.addWidget(self.glyph)
        top.addWidget(self.lbl_section)
        lay.addLayout(top)

        # Quote body
        self.lbl_quote = QLabel("")
        self.lbl_quote.setObjectName("Title")
        self.lbl_quote.setWordWrap(True)
        lay.addWidget(self.lbl_quote)

        # Attribution
        self.lbl_attr = QLabel("")
        self.lbl_attr.setObjectName("StatusActive")
        lay.addWidget(self.lbl_attr)

        lay.addStretch(1)

        self._last_idx = -1
        self.set_quote_index(0)
        self._timer = QTimer(self)
        self._timer.setInterval(9000)
        self._timer.timeout.connect(self.next_quote)
        self._timer.start()

    def set_quote_index(self, idx: int) -> None:
        if not _QUOTES:
            return
        idx = idx % len(_QUOTES)
        self._last_idx = idx
        q, a = _QUOTES[idx]
        self.lbl_quote.setText(f"\u201C{q}\u201D")
        self.lbl_attr.setText(f"\u2014  {a}")

    def next_quote(self) -> None:
        if len(_QUOTES) <= 1:
            return
        nxt = self._last_idx
        while nxt == self._last_idx:
            nxt = random.randrange(len(_QUOTES))
        self.set_quote_index(nxt)
