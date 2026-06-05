"""Calendar mini-tile: month grid with current day highlighted in red."""
from __future__ import annotations

import calendar
from datetime import date

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QGridLayout, QHBoxLayout, QLabel, QVBoxLayout


_DOW = ["M", "T", "W", "T", "F", "S", "S"]


class CalendarTile(QFrame):
    """Bento tile: month name + mini calendar grid with current day marked."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("CardBright")

        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 18, 20, 20)
        lay.setSpacing(10)

        title_row = QVBoxLayout()
        title_row.setSpacing(2)
        self.lbl_month = QLabel("")
        self.lbl_month.setObjectName("TitleLg")
        title_row.addWidget(self.lbl_month)
        self.lbl_year = QLabel("")
        self.lbl_year.setObjectName("Status")
        title_row.addWidget(self.lbl_year)
        lay.addLayout(title_row)

        # Day-of-week header
        dow_row = QVBoxLayout()
        dow_row.setSpacing(6)
        head = QHBoxLayout()
        head.setSpacing(0)
        for d in _DOW:
            l = QLabel(d)
            l.setObjectName("StatusDim")
            l.setAlignment(Qt.AlignmentFlag.AlignCenter)
            head.addWidget(l, 1)
        dow_row.addLayout(head)
        lay.addLayout(dow_row)

        self.grid = QGridLayout()
        self.grid.setSpacing(2)
        lay.addLayout(self.grid)

        lay.addStretch(1)
        self._refresh(date.today())

    def _refresh(self, today: date) -> None:
        # Clear
        while self.grid.count():
            it = self.grid.takeAt(0)
            w = it.widget()
            if w:
                w.deleteLater()

        self.lbl_month.setText(today.strftime("%B").upper())
        self.lbl_year.setText(str(today.year))

        cal = calendar.Calendar(firstweekday=0)
        weeks = list(cal.monthdayscalendar(today.year, today.month))

        for r, week in enumerate(weeks):
            for c in range(7):
                day = week[c]
                if day == 0:
                    l = QLabel("")
                    l.setFixedHeight(20)
                    self.grid.addWidget(l, r, c)
                    continue
                lbl = QLabel(str(day))
                if day == today.day:
                    lbl.setObjectName("StatusActive")
                    lbl.setStyleSheet(
                        "color:#D7191A; font-weight:700;"
                        "background:transparent;"
                    )
                else:
                    lbl.setObjectName("Meta")
                lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                lbl.setFixedHeight(20)
                self.grid.addWidget(lbl, r, c)
