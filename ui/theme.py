"""Tex theme — super minimal, iOS feel, dot-matrix font throughout.

Default body 12, headings 16-20, hero 28. Rounded everything.
Mixed case. Sans is the fallback; the dot-matrix/mono is the brand identity.
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QFile, QUrl
from PySide6.QtGui import QFont, QFontDatabase
from PySide6.QtWidgets import QApplication

ASSETS = Path(__file__).resolve().parent.parent / "assets"
MONO_CANDIDATES = [
    ASSETS / "fonts" / "DotGothic16-Regular.ttf",
    ASSETS / "fonts" / "Ndot57.ttf",
    ASSETS / "fonts" / "Ndot55.ttf",
    ASSETS / "fonts" / "LED Dot-Matrix.ttf",
    ASSETS / "fonts" / "DotMatrix.ttf",
    ASSETS / "fonts" / "NothingFont5Mono.ttf",
    ASSETS / "fonts" / "dotmatrix.ttf",
    ASSETS / "fonts" / "JetBrainsMono-Regular.ttf",
    ASSETS / "fonts" / "ShareTechMono-Regular.ttf",
    ASSETS / "fonts" / "VT323-Regular.ttf",
    ASSETS / "fonts" / "PressStart2P-Regular.ttf",
]
MONO_WIN_FALLBACK = "Consolas"
SANS_WIN_FALLBACK = "Segoe UI"


def load_mono_font() -> str:
    app = QApplication.instance()
    if app is None:
        return MONO_WIN_FALLBACK
    for cand in MONO_CANDIDATES:
        if cand.exists():
            fid = QFontDatabase.addApplicationFont(str(cand))
            if fid != -1:
                fams = QFontDatabase.applicationFontFamilies(fid)
                if fams:
                    return fams[0]
    return MONO_WIN_FALLBACK


def _font_mono(family: str, size: int, weight: QFont.Weight = QFont.Weight.Normal,
               letter_spacing: float = 0) -> str:
    ls = f" {letter_spacing}px" if letter_spacing else ""
    return (
        f'font-family: "{family}", "{MONO_WIN_FALLBACK}", monospace;'
        f' font-size: {size}px; font-weight: {int(weight.value)};'
        f' letter-spacing:{ls};'
    )


def _font_sans(size: int, weight: QFont.Weight = QFont.Weight.Normal,
               letter_spacing: float = 0) -> str:
    ls = f" {letter_spacing}px" if letter_spacing else ""
    return (
        f'font-family: "{SANS_WIN_FALLBACK}", "Segoe UI Variable", "Helvetica Neue", sans-serif;'
        f' font-size: {size}px; font-weight: {int(weight.value)};'
        f' letter-spacing:{ls};'
    )


def _dot(color: str, size: int = 8) -> str:
    return (
        f"background-color: {color};"
        f" border-radius: {size // 2}px;"
        f" min-width: {size}px; max-width: {size}px;"
        f" min-height: {size}px; max-height: {size}px;"
    )


def _qss(mono: str, accent: str, accent_dim: str, fg: str, fg_dim: str, fg_faint: str,
         bg: str, panel: str, panel_bright: str, hairline: str, hairline_strong: str,
         hover: str, soft: str, danger: str) -> str:
    return f"""
    /* =========================================================
       Tex · super-minimal · iOS feel · dot-matrix identity
       Body 12, headings 16-20, hero 28.
       ========================================================= */
    QWidget {{
        {_font_mono(mono, 12)}
        color: {fg};
        background-color: transparent;
        selection-background-color: {accent};
        selection-color: #FFFFFF;
        outline: 0;
    }}
    QMainWindow, #TexRoot, #Splash {{
        background-color: transparent;
    }}
    /* Body and pages are transparent — the dot background shows through. */
    #TexBody, #TexPage {{ background: transparent; }}
    QStackedWidget {{ background: transparent; }}
    QScrollArea, QScrollArea > QWidget {{ background: transparent; }}
    #SplashInner {{ background: transparent; }}

    /* ---------- SPLASH ---------- */
    QLabel#SplashDot {{
        {_font_mono(mono, 64, QFont.Weight.Bold, 0)}
        color: {accent};
        background: transparent;
    }}
    QLabel#SplashBrand {{
        {_font_mono(mono, 22, QFont.Weight.Bold, 1)}
        color: {fg};
        background: transparent;
    }}
    QLabel#SplashSub {{
        {_font_mono(mono, 11)}
        color: {fg_faint};
        background: transparent;
    }}

    /* ---------- TYPE ---------- */
    QLabel#XL  {{ {_font_mono(mono, 22, QFont.Weight.Bold, 0)} color: {fg}; }}
    QLabel#L   {{ {_font_mono(mono, 18, QFont.Weight.Bold, 0)} color: {fg}; }}
    QLabel#M   {{ {_font_mono(mono, 15, QFont.Weight.Bold, 0)} color: {fg}; }}
    QLabel#S   {{ {_font_mono(mono, 12)} color: {fg}; }}
    QLabel#XS  {{ {_font_mono(mono, 10)}  color: {fg_dim}; }}

    QLabel#Hero {{
        {_font_mono(mono, 28, QFont.Weight.Bold, 2)} color: {fg};
    }}

    QLabel#Dot, QLabel#DotSm, QLabel#DotLg, QLabel#DotXl {{
        border-radius: 50%;
    }}
    QLabel#Dot {{ {_dot(accent, 8)} }}
    QLabel#DotSm {{ {_dot(accent, 6)} }}
    QLabel#DotLg {{ {_dot(accent, 12)} }}
    QLabel#DotXl {{ {_dot(accent, 16)} }}
    QLabel#DotDim {{ {_dot(fg_faint, 8)} }}
    QLabel#DotWhite {{ {_dot(fg, 8)} }}

    QLabel#Title  {{ {_font_mono(mono, 14, QFont.Weight.Bold, 0)} color: {fg}; }}
    QLabel#TitleLg {{ {_font_mono(mono, 18, QFont.Weight.Bold, 0)} color: {fg}; }}
    QLabel#Meta   {{ {_font_mono(mono, 11)} color: {fg_dim}; }}
    QLabel#MetaDim{{ {_font_mono(mono, 10)}  color: {fg_faint}; }}

    QLabel#Status {{
        {_font_mono(mono, 10, QFont.Weight.Bold, 1)} color: {fg_dim};
    }}
    QLabel#StatusActive {{
        {_font_mono(mono, 10, QFont.Weight.Bold, 1)} color: {accent};
    }}
    QLabel#StatusDim {{
        {_font_mono(mono, 10, QFont.Weight.Bold, 1)} color: {fg_faint};
    }}
    /* Status label that switches between states via a dynamic property.
       Avoids the expensive style().unpolish() / polish() round-trip. */
    QLabel#StatusLbl[pState="active"],
    QLabel#StatusLbl[pState="done"],
    QLabel#StatusLbl[pState="error"] {{
        {_font_mono(mono, 10, QFont.Weight.Bold, 1)} color: {accent};
    }}
    QLabel#StatusLbl[pState="paused"],
    QLabel#StatusLbl[pState="cancelled"] {{
        {_font_mono(mono, 10, QFont.Weight.Bold, 1)} color: {fg_dim};
    }}
    QLabel#SectionBig {{
        {_font_mono(mono, 10, QFont.Weight.Bold, 2)} color: {fg_dim};
    }}
    QLabel#Section {{
        {_font_mono(mono, 10, QFont.Weight.Bold, 2)} color: {fg_faint};
    }}
    QLabel#NumBig  {{ {_font_mono(mono, 24, QFont.Weight.Bold, 1)} color: {fg}; }}
    QLabel#NumMed  {{ {_font_mono(mono, 14, QFont.Weight.Bold, 0)} color: {fg}; }}
    QLabel#BigPct  {{ {_font_mono(mono, 26, QFont.Weight.Bold, 1)} color: {accent}; }}

    /* ---------- TITLE BAR — 36px ---------- */
    QFrame#TitleBar {{
        background-color: transparent;
        border-bottom: 1px solid {hairline};
    }}
    QLabel#TitleBrand {{
        {_font_mono(mono, 14, QFont.Weight.Bold, 1)} color: {fg};
        background: transparent;
    }}
    QLabel#TitleBrandDot {{
        {_font_mono(mono, 18, QFont.Weight.Bold, 0)}
        color: {accent};
        background: transparent;
    }}
    QLabel#TitleClock {{
        {_font_mono(mono, 12, QFont.Weight.Bold, 0)} color: {fg};
        background: transparent;
    }}
    QFrame#StatePill {{
        background: {soft};
        border: 1px solid {hairline_strong};
        border-radius: 10px;
    }}
    QLabel#StatePillText {{
        {_font_mono(mono, 10, QFont.Weight.Bold, 1)}
        color: {fg_dim};
        background: transparent;
    }}
    QFrame#StatePill[active="true"] {{
        border: 1px solid {accent};
    }}
    QLabel#StatePillText[active="true"] {{
        color: {accent};
    }}
    /* Window controls */
    QFrame#WinBtn {{
        background: transparent;
        border: none;
        border-radius: 6px;
    }}
    QFrame#WinBtn[hot="hover"]    {{ background: {hover}; }}
    QFrame#WinBtn[hot="active"]   {{ background: {fg_dim}; }}
    QFrame#WinBtn[hot="closeHover"]{{ background: {danger}; }}
    QLabel#WinGlyph {{
        {_font_mono(mono, 12, QFont.Weight.Bold, 0)} color: {fg};
        background: transparent;
    }}
    QFrame#WinBtn[hot="closeHover"] QLabel#WinGlyph {{ color: #FFFFFF; }}
    QFrame#WinBar {{ background: transparent; border: none; }}

    /* Folder button — sits next to the window controls. */
    QFrame#FolderBtn {{
        background: transparent;
        border: none;
        border-radius: 6px;
    }}
    QFrame#FolderBtn[hot="hover"]  {{ background: {hover}; }}
    QFrame#FolderBtn[hot="active"] {{ background: {fg_dim}; }}
    QLabel#FolderGlyph {{
        {_font_mono(mono, 13, QFont.Weight.Normal, 0)} color: {fg_dim};
        background: transparent;
    }}
    QFrame#FolderBtn[hot="hover"] QLabel#FolderGlyph {{ color: {fg}; }}

    /* ---------- SIDEBAR — narrow, rounded nav ---------- */
    QFrame#Sidebar {{
        background-color: {bg};
        border-right: 1px solid {hairline};
    }}
    QLabel#SideBrand {{
        {_font_mono(mono, 13, QFont.Weight.Bold, 1)} color: {fg};
    }}
    QPushButton#SideNav {{
        {_font_mono(mono, 12, QFont.Weight.Bold, 0)}
        background: transparent;
        color: {fg_dim};
        border: 1px solid transparent;
        text-align: left;
        padding: 9px 14px;
        border-radius: 10px;
    }}
    QPushButton#SideNav:hover {{ color: {fg}; background: {hover}; border-color: {hairline}; }}
    QPushButton#SideNav:checked {{
        color: {accent};
        background: {soft};
        border: 1px solid {accent};
    }}
    /* The icon label inside a nav button — the QLabel is transparent
       and reads its color from the parent QPushButton's palette. */
    QLabel#NavIcon {{
        background: transparent;
    }}
    QPushButton#SideToggle {{
        {_font_mono(mono, 12, QFont.Weight.Bold, 0)}
        background: transparent;
        color: {fg_faint};
        border: 1px solid transparent;
        border-radius: 4px;
        padding: 0px;
    }}
    QPushButton#SideToggle:hover {{
        color: {fg}; background: {hover}; border-color: {hairline};
    }}
    QPushButton#SideToggle:pressed {{
        color: {accent}; border-color: {accent};
    }}
    QLabel#SideBadge {{
        {_font_mono(mono, 9, QFont.Weight.Bold, 0)}
        color: #FFFFFF;
        background: {accent};
        border-radius: 8px;
        min-width: 16px; max-width: 20px;
        min-height: 16px; max-height: 16px;
    }}

    /* ---------- URL BAR ---------- */
    QFrame#UrlBar {{
        background-color: {panel};
        border: 1px solid {hairline};
        border-radius: 6px;
    }}
    QFrame#UrlBar:focus-within {{
        border: 1px solid {accent};
    }}
    QLineEdit#UrlInput {{
        {_font_mono(mono, 13)}
        background: transparent;
        border: none;
        color: {fg};
        padding: 12px 14px;
        selection-background-color: {accent};
    }}
    QLineEdit#UrlInput::placeholder {{ color: {fg_faint}; }}
    QPushButton#FetchBtn {{
        {_font_mono(mono, 11, QFont.Weight.Bold, 1)}
        background: {accent};
        color: #FFFFFF;
        border: none;
        border-radius: 0px 5px 5px 0px;
        padding: 0px 22px;
    }}
    QPushButton#FetchBtn:hover {{ background: {fg}; color: {bg}; }}
    QPushButton#FetchBtn:pressed {{ background: {fg_dim}; }}
    QPushButton#FetchBtn:disabled {{ background: {hairline}; color: {fg_faint}; }}

    /* ---------- BUTTONS ---------- */
    QPushButton {{
        {_font_mono(mono, 11, QFont.Weight.Bold, 1)}
        background: transparent;
        color: {fg};
        border: 1px solid {hairline_strong};
        border-radius: 6px;
        padding: 8px 14px;
    }}
    QPushButton:hover {{ border-color: {fg}; }}
    QPushButton:pressed {{
        background: {accent}; color: #FFFFFF; border-color: {accent};
    }}
    QPushButton:disabled {{
        color: {fg_faint}; border-color: {hairline};
    }}
    QPushButton#Primary {{
        background: {accent};
        color: #FFFFFF;
        border: 1px solid {accent};
        border-radius: 6px;
        padding: 14px 24px;
        {_font_mono(mono, 13, QFont.Weight.Bold, 1)}
    }}
    QPushButton#Primary:hover {{
        background: {fg}; color: {bg}; border-color: {fg};
    }}
    QPushButton#Primary:pressed {{ background: {fg_dim}; color: {bg}; }}
    QPushButton#Primary:disabled {{
        background: {hairline}; color: {fg_faint}; border-color: {hairline};
    }}
    QPushButton#Ghost, QFrame#Ghost {{
        border: 1px solid {hairline}; color: {fg_dim};
        background: transparent;
    }}
    QPushButton#Ghost:hover, QFrame#Ghost:hover,
    QFrame#Ghost[hot="hover"]    {{ color: {fg}; border-color: {fg_dim}; }}
    QPushButton#Ghost:pressed, QFrame#Ghost:pressed,
    QFrame#Ghost[hot="active"]   {{ background: {accent}; color: #FFFFFF; border-color: {accent}; }}
    QPushButton#Icon, QFrame#Icon {{
        border: 1px solid {hairline}; color: {fg};
        background: transparent;
        padding: 0px;
        border-radius: 4px;
    }}
    QPushButton#Icon:hover, QFrame#Icon:hover,
    QFrame#Icon[hot="hover"]    {{ border-color: {fg}; }}
    QPushButton#Icon:pressed, QFrame#Icon:pressed,
    QFrame#Icon[hot="active"]   {{ background: {accent}; color: #FFFFFF; border-color: {accent}; }}
    QLabel#Glyph {{ background: transparent; }}
    QLabel#PrimaryText, QLabel#PrimaryArrow {{ background: transparent; }}

    /* Frame-based primary button (the small "OPEN" on progress cards) */
    QFrame#Primary {{
        background: {accent};
        color: #FFFFFF;
        border: 1px solid {accent};
        border-radius: 4px;
    }}
    QFrame#Primary:hover, QFrame#Primary[hot="hover"]   {{ background: {fg}; border-color: {fg}; color: {bg}; }}
    QFrame#Primary:pressed, QFrame#Primary[hot="active"] {{ background: {fg_dim}; border-color: {fg_dim}; color: {bg}; }}

    /* ---------- RETRO PIXEL BUTTON (the big Fetch button) ---------- */
    QFrame#PixelBtnWrap {{
        background: transparent;
        border: none;
    }}
    QFrame#PixelBtnShadow {{
        background: {accent_dim};
        border: 2px solid {accent_dim};
        border-radius: 8px;
    }}
    QFrame#PixelBtn {{
        background: {accent};
        color: #FFFFFF;
        border: 2px solid #FFFFFF;
        border-radius: 8px;
    }}
    QFrame#PixelBtn[hot="hover"]    {{ background: #E82020; }}
    QFrame#PixelBtn[pressed="true"] {{
        background: #A81415;
        border: 2px solid #FFFFFF;
    }}
    QLabel#PixelText {{
        {_font_mono(mono, 13, QFont.Weight.Bold, 2)}
        color: #FFFFFF;
        background: transparent;
        letter-spacing: 1.5px;
    }}
    QLabel#PixelArrow {{ background: transparent; }}

    /* ---------- CARDS ---------- */
    QFrame#Card {{
        background-color: {panel};
        border: 1px solid {hairline_strong};
        border-radius: 8px;
    }}
    QFrame#CardBright {{
        background-color: {panel_bright};
        border: 1px solid {hairline_strong};
        border-radius: 8px;
    }}
    QFrame#CardInset {{
        background-color: {soft};
        border: 1px solid {hairline};
        border-radius: 6px;
    }}
    QFrame#CardDisabled {{
        background-color: transparent;
        border: 1px dashed {hairline};
        border-radius: 6px;
        opacity: 0.45;
    }}
    QFrame#CardDisabled QPushButton#Chip {{
        color: {fg_faint};
    }}
    QFrame[selected="true"] {{
        background-color: {accent};
        border: 1px solid {accent};
        border-radius: 8px;
    }}
    QFrame[selected="false"] {{
        background-color: {soft};
        border: 1px solid {hairline};
        border-radius: 8px;
    }}
    QFrame#CardFlat {{
        background-color: transparent;
        border: none;
        border-bottom: 1px solid {hairline};
    }}
    QFrame#ThinDivider {{
        background: {hairline};
        max-height: 1px; min-height: 1px;
    }}

    /* ---------- HERO EMPTY ---------- */
    QFrame#HeroEmpty {{
        background-color: transparent;
        border: none;
    }}
    QLabel#HeroTitle {{
        color: {fg};
        {_font_mono(mono, 24, QFont.Weight.Bold, 2)};
    }}
    QLabel#HeroSub {{
        color: {fg_faint};
        {_font_mono(mono, 11)};
    }}
    QLabel#HeroKbd {{
        color: {fg_dim};
        background: {soft};
        border: 1px solid {hairline};
        border-radius: 4px;
        padding: 3px 8px;
        {_font_mono(mono, 10, QFont.Weight.Bold, 0)};
    }}

    /* ---------- FORMAT CHIPS ---------- */
    QPushButton#Chip {{
        {_font_mono(mono, 12, QFont.Weight.Bold, 0)}
        background: transparent;
        color: {fg};
        border: 1px solid {hairline};
        border-radius: 6px;
        padding: 12px 6px;
        min-height: 54px;
        text-align: center;
    }}
    QPushButton#Chip:hover {{ border-color: {fg}; }}
    QPushButton#Chip:pressed {{ background: {accent}; color: #FFFFFF; border-color: {accent}; }}
    QPushButton#Chip:checked {{
        background: {accent}; color: #FFFFFF; border: 1px solid {accent};
    }}
    QPushButton#Chip:disabled {{
        color: {fg_faint}; border-color: {hairline};
    }}
    QPushButton#ChipBtn {{
        background: {soft}; color: {fg_dim}; border: 1px solid {hairline};
        border-radius: 6px; padding: 6px 12px; {_font_mono(mono, 10, QFont.Weight.Normal, 0)}
    }}
    QPushButton#ChipBtn:hover {{ border-color: {fg}; color: {fg}; }}
    QPushButton#ChipBtn:pressed {{ background: {accent}; color: #FFFFFF; border-color: {accent}; }}
    QPushButton#ChipBtn:checked {{
        background: {accent}; color: #FFFFFF; border: 1px solid {accent};
    }}
    QLabel#ChipSize {{
        {_font_mono(mono, 10, QFont.Weight.Bold, 0)} color: {fg_dim};
    }}
    QLabel#ChipSizeChecked {{
        {_font_mono(mono, 10, QFont.Weight.Bold, 0)} color: #FFFFFF;
    }}
    QLabel[selected="true"] {{
        color: #FFFFFF;
    }}
    QLabel[selected="false"] {{
        color: {fg_dim};
    }}

    /* ---------- PROGRESS ---------- */
    QProgressBar#Shimmer {{
        background: {hairline};
        border: none;
        height: 2px;
        text-align: center;
        color: transparent;
    }}
    QProgressBar#Shimmer::chunk {{
        background-color: {accent};
    }}

    /* ---------- INPUTS ---------- */
    QLineEdit, QSpinBox, QComboBox, QPlainTextEdit, QTextEdit {{
        background: {soft};
        border: 1px solid {hairline};
        border-radius: 6px;
        color: {fg};
        padding: 7px 10px;
        {_font_mono(mono, 11)}
    }}
    QLineEdit:hover, QSpinBox:hover, QComboBox:hover, QPlainTextEdit:hover, QTextEdit:hover {{
        border-color: {hairline_strong};
    }}
    QLineEdit:focus, QSpinBox:focus, QComboBox:focus, QPlainTextEdit:focus, QTextEdit:focus {{
        border-color: {accent};
    }}
    QComboBox::drop-down {{ border: none; width: 22px; }}
    QComboBox QAbstractItemView {{
        background: {panel}; color: {fg};
        selection-background-color: {accent};
        selection-color: #FFFFFF;
        border: 1px solid {hairline};
        border-radius: 6px;
        outline: 0;
        padding: 4px;
    }}
    QSpinBox::up-button, QSpinBox::down-button {{ width: 18px; }}

    QCheckBox {{
        {_font_mono(mono, 11)} color: {fg};
        spacing: 10px; padding: 4px 0px;
    }}
    QCheckBox::indicator {{
        width: 14px; height: 14px;
        background: transparent;
        border: 1px solid {hairline_strong};
        border-radius: 3px;
    }}
    QCheckBox::indicator:hover {{ border-color: {fg}; }}
    QCheckBox::indicator:checked {{
        background: {accent}; border: 1px solid {accent};
    }}

    /* ---------- SCROLLBAR — visible but slim ---------- */
    QScrollBar:vertical {{
        background: {bg}; width: 8px;
        border: none; margin: 0px;
    }}
    QScrollBar::handle:vertical {{
        background: {hairline_strong}; min-height: 40px;
        border-radius: 4px;
    }}
    QScrollBar::handle:vertical:hover {{ background: {fg_faint}; }}
    QScrollBar::add-line, QScrollBar::sub-line {{
        height: 0px; background: none; border: none;
    }}
    QScrollBar::add-page, QScrollBar::sub-page {{ background: none; }}
    QScrollBar:horizontal {{
        background: {bg}; height: 8px;
        border: none; margin: 0px;
    }}
    QScrollBar::handle:horizontal {{
        background: {hairline_strong}; min-width: 40px;
        border-radius: 4px;
    }}
    QScrollBar::handle:horizontal:hover {{ background: {fg_faint}; }}

    /* ---------- LISTS ---------- */
    QListView, QListWidget {{
        background: transparent; border: none; outline: 0; padding: 0px;
    }}
    QListView::item, QListWidget::item {{
        padding: 0px; border: none; background: transparent;
    }}
    QListView::item:selected, QListWidget::item:selected {{
        background: transparent; color: {fg};
    }}

    /* ---------- TOOLTIP ---------- */
    QToolTip {{
        {_font_mono(mono, 10)} background: {panel}; color: {fg};
        border: 1px solid {hairline_strong}; border-radius: 4px;
        padding: 5px 7px;
    }}

    /* ---------- TOAST ---------- */
    QFrame#Toast {{
        background: {panel};
        border: 1px solid {accent};
        border-radius: 6px;
    }}
    QLabel#ToastText {{
        {_font_mono(mono, 11, QFont.Weight.Bold, 0)} color: {fg};
    }}
    QLabel#ToastDot {{ {_dot(accent, 6)} }}

    /* ---------- EMPTY ---------- */
    QLabel#Empty {{
        {_font_mono(mono, 12)} color: {fg_faint};
        padding: 60px 20px;
        qproperty-alignment: AlignCenter;
    }}
    QLabel#EmptyTitle {{
        {_font_mono(mono, 13, QFont.Weight.Bold, 1)} color: {fg_dim};
        padding: 0px 20px 14px 20px;
        qproperty-alignment: AlignCenter;
    }}

    /* ---------- DOT MATRIX ART ---------- */
    QLabel#PixelDot {{
        background-color: {accent};
        border-radius: 1px;
    }}
    QLabel#PixelDotOff {{
        background-color: {hairline_strong};
        border-radius: 1px;
    }}
    """


def dark_qss(mono: str) -> str:
    return _qss(
        mono,
        accent="#D7191A",
        accent_dim="#7A0E0F",
        fg="#FFFFFF",
        fg_dim="#A8A8A8",
        fg_faint="#6A6A6A",
        bg="#000000",
        panel="#101010",
        panel_bright="#161616",
        hairline="#1F1F1F",
        hairline_strong="#383838",
        hover="#1A1A1A",
        soft="#0C0C0C",
        danger="#D7191A",
    )


def light_qss(mono: str) -> str:
    return _qss(
        mono,
        accent="#D7191A",
        accent_dim="#A51315",
        fg="#0A0A0A",
        fg_dim="#6A6A6A",
        fg_faint="#B0B0B0",
        bg="#F2F2F2",
        panel="#FFFFFF",
        panel_bright="#F7F7F7",
        hairline="#E2E2E2",
        hairline_strong="#C8C8C8",
        hover="#EAEAEA",
        soft="#F7F7F7",
        danger="#D7191A",
    )


def nord_qss(mono: str) -> str:
    """Nord — cool arctic blue-gray."""
    return _qss(
        mono,
        accent="#88C0D0",          # frost cyan
        accent_dim="#5E81AC",
        fg="#ECEFF4",              # snow storm
        fg_dim="#9AA5B1",
        fg_faint="#4C566A",
        bg="#2E3440",              # polar night
        panel="#3B4252",
        panel_bright="#434C5E",
        hairline="#434C5E",
        hairline_strong="#4C566A",
        hover="#3B4252",
        soft="#3B4252",
        danger="#BF616A",
    )


def solarized_qss(mono: str) -> str:
    """Solarized dark — warm amber on deep teal."""
    return _qss(
        mono,
        accent="#B58900",          # yellow
        accent_dim="#CB4B16",
        fg="#FDF6E3",              # base3
        fg_dim="#93A1A1",
        fg_faint="#586E75",
        bg="#002B36",              # base03
        panel="#073642",           # base02
        panel_bright="#0A4550",
        hairline="#0A4550",
        hairline_strong="#586E75",
        hover="#0A4550",
        soft="#073642",
        danger="#DC322F",
    )


def cyberpunk_qss(mono: str) -> str:
    """Cyberpunk — neon pink on deep purple-black."""
    return _qss(
        mono,
        accent="#FF2A6D",          # hot pink
        accent_dim="#D300C5",
        fg="#F1F1F1",
        fg_dim="#9A9AAE",
        fg_faint="#5A5A7A",
        bg="#0D0221",              # deep purple-black
        panel="#150734",
        panel_bright="#1F0A4A",
        hairline="#241060",
        hairline_strong="#3A1B7A",
        hover="#1F0A4A",
        soft="#150734",
        danger="#FF2A6D",
    )


def forest_qss(mono: str) -> str:
    """Forest — dark green with mint accent."""
    return _qss(
        mono,
        accent="#5EEAD4",          # mint
        accent_dim="#2DD4BF",
        fg="#ECFDF5",
        fg_dim="#9AA8A2",
        fg_faint="#4A5550",
        bg="#0A1410",              # deep forest
        panel="#101E18",
        panel_bright="#162A22",
        hairline="#1F3A30",
        hairline_strong="#2D5A48",
        hover="#162A22",
        soft="#101E18",
        danger="#FB7185",
    )


# Theme registry — value: (display name, qss_fn, palette_dict).
# Each palette is the concrete color set the theme uses, exposed so
# custom-painted widgets (SVG icon buttons, dot backgrounds) can pick
# the right colors without parsing the QSS.
THEMES: dict[str, tuple[str, callable, dict]] = {
    "dark":      ("Tex Dark",   dark_qss, {
        "fg": "#FFFFFF", "fg_dim": "#A8A8A8", "fg_faint": "#6A6A6A",
        "accent": "#D7191A", "accent_dim": "#7A0E0F",
        "bg": "#000000", "panel": "#101010", "panel_bright": "#161616",
        "hairline": "#1F1F1F", "hairline_strong": "#383838",
        "hover": "#1A1A1A", "soft": "#0C0C0C",
        "danger": "#D7191A",
    }),
    "light":     ("Tex Light",  light_qss, {
        "fg": "#1A1A1A", "fg_dim": "#6A6A6A", "fg_faint": "#B0B0B0",
        "accent": "#D7191A", "accent_dim": "#A81415",
        "bg": "#FAFAFA", "panel": "#FFFFFF", "panel_bright": "#FFFFFF",
        "hairline": "#E0E0E0", "hairline_strong": "#C8C8C8",
        "hover": "#EFEFEF", "soft": "#F2F2F2",
        "danger": "#D7191A",
    }),
    "nord":      ("Nord",        nord_qss, {
        "fg": "#ECEFF4", "fg_dim": "#9AA5B1", "fg_faint": "#4C566A",
        "accent": "#88C0D0", "accent_dim": "#5E81AC",
        "bg": "#2E3440", "panel": "#3B4252", "panel_bright": "#434C5E",
        "hairline": "#434C5E", "hairline_strong": "#4C566A",
        "hover": "#434C5E", "soft": "#3B4252",
        "danger": "#BF616A",
    }),
    "solarized": ("Solarized",   solarized_qss, {
        "fg": "#93A1A1", "fg_dim": "#93A1A1", "fg_faint": "#586E75",
        "accent": "#B58900", "accent_dim": "#CB4B16",
        "bg": "#002B36", "panel": "#073642", "panel_bright": "#0A4551",
        "hairline": "#0A4551", "hairline_strong": "#586E75",
        "hover": "#0A4551", "soft": "#073642",
        "danger": "#DC322F",
    }),
    "cyberpunk": ("Cyberpunk",   cyberpunk_qss, {
        "fg": "#F8F8F2", "fg_dim": "#9A9AAE", "fg_faint": "#5A5A7A",
        "accent": "#FF79C6", "accent_dim": "#BD93F9",
        "bg": "#1A0F2E", "panel": "#241635", "panel_bright": "#2E1D44",
        "hairline": "#3A2452", "hairline_strong": "#4A3060",
        "hover": "#2E1D44", "soft": "#241635",
        "danger": "#FF5555",
    }),
    "forest":    ("Forest",      forest_qss, {
        "fg": "#E8F0E8", "fg_dim": "#9AA8A2", "fg_faint": "#4A5550",
        "accent": "#7FB069", "accent_dim": "#5A8043",
        "bg": "#0F1A12", "panel": "#16251A", "panel_bright": "#1F3024",
        "hairline": "#243829", "hairline_strong": "#3A4A3E",
        "hover": "#1F3024", "soft": "#16251A",
        "danger": "#D17B7B",
    }),
}


def get_palette(theme: str = "dark") -> dict:
    """Return the concrete color palette for a theme."""
    entry = THEMES.get(theme)
    if entry is None:
        entry = THEMES["dark"]
    return entry[2]


def apply_theme(app, theme: str = "dark") -> tuple[str, dict]:
    mono = load_mono_font()
    entry = THEMES.get(theme)
    if entry is None:
        entry = THEMES["dark"]
    _, qss_fn, palette = entry
    app.setStyleSheet(qss_fn(mono))
    f = QFont(mono, 11)
    f.setStyleHint(QFont.StyleHint.Monospace)
    app.setFont(f)
    return mono, palette
