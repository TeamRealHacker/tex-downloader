<p align="center">
  <img src="assets/logo.svg" width="128" alt="Tex logo">
</p>

<h1 align="center">Tex</h1>

<p align="center">
  <b>Super minimal, super fast video / audio downloader</b><br>
  Python + PySide6 &middot; iOS-inspired &middot; Dark &amp; Light themes
</p>

<p align="center">
  <img src="https://img.shields.io/badge/version-0.3.0-red" alt="version">
  <img src="https://img.shields.io/badge/python-3.10+-blue" alt="python">
  <img src="https://img.shields.io/badge/license-MIT-green" alt="license">
</p>

---

## Features

### Download
- **Paste &amp; go** &mdash; Ctrl+V a URL, pick quality, click Download. Done.
- **Multi-URL paste** &mdash; paste 10 links at once, they all queue up automatically.
- **Multi-platform** &mdash; YouTube, TikTok, Instagram, Twitter/X, and 1000+ more sites via yt-dlp.
- **Quality picker** &mdash; MP4 (4K &rarr; 360p) and MP3 (320 / 192 / 128 kbps) with file size preview.
- **ID3 tagging** &mdash; MP3s get title, artist, album art automatically.
- **Filename templates** &mdash; `{title} [{quality}].{ext}` and more.

### Editor (NEW in v0.3.0)
- **Visual timeline** &mdash; paste any video URL, drag start/end handles to select a segment.
- **Manual time input** &mdash; type exact START / END times, synced with the slider.
- **Trim &amp; Download** &mdash; downloads only the selected portion using yt-dlp's `--download-sections`.

### Channels
- **Channel bulk download** &mdash; paste a YouTube channel URL, fetch up to 200 videos, pick which to download.

### Queue
- **Concurrent queue** &mdash; unlimited downloads with pause, cancel, clear.
- **Live progress** &mdash; per-item speed, ETA, and percentage.

### Settings &amp; Customization
- **6 themes** &mdash; Dark, Light, Nord, Solarized, Cyberpunk, Forest. Live-togglable.
- **Browser cookies auto-extracted** &mdash; Chrome, Edge, Firefox, Brave, Opera, Vivaldi. Age-restricted content works out of the box. No manual `cookies.txt`.
- **Sound effects** &mdash; tick, fetch, queue, done, error. Toggleable.

### UX
- **System tray** &mdash; minimize to tray, paste URL from tray menu.
- **Clipboard auto-detect** &mdash; copies a URL, Tex picks it up.
- **Drag &amp; drop** &mdash; drop URLs onto the window.
- **Edge resize** &mdash; drag any edge of the frameless window to resize.
- **Collapsible sidebar** &mdash; 168px expanded, 56px collapsed.

---

## Screenshots

| Download | Queue | Editor |
|:--------:|:-----:|:------:|
| ![Download](https://files.catbox.moe/z6190l.png) | ![Queue](https://files.catbox.moe/gvruke.png) | _Coming soon_ |

| Channels | History | Settings |
|:--------:|:-------:|:--------:|
| ![Channels](https://files.catbox.moe/otfy93.png) | ![History](https://files.catbox.moe/spk7ac.png) | ![Settings](https://files.catbox.moe/ph5k04.png) |

---

## Quick start (from source)

```bash
pip install PySide6 yt-dlp imageio-ffmpeg
python main.py
```

On first launch Tex prompts for a save folder, then creates `Video/` and `Audio/` subfolders inside it.

---

## Download portable build

Head to **[Releases](https://github.com/TeamRealHacker/tex-downloader/releases)** and download `TEX-Portable.zip`.

Unzip it anywhere &mdash; it's fully portable. No installer, no registry, no AppData. Config, history, and thumbnails are stored in a `TexData/` folder next to the EXE. Copy the whole folder to a USB stick and it just works.

The ZIP includes `ffmpeg.exe` bundled, so video merging and trimming work out of the box.

### What's inside the ZIP

```
TEX/
├── TEX.exe          ← main app
├── icon.ico         ← window / taskbar / tray icon
├── ffmpeg.exe       ← video merging & trimming
├── assets/          ← sounds, fonts
└── _internal/       ← Python runtime, DLLs, dependencies
```

---

## Build from source

```bash
pip install pyinstaller PySide6 yt-dlp imageio-ffmpeg mutagen requests Pillow
python build.py
```

Output: `dist/TEX/` folder + `dist/TEX-Portable.zip`

The default build mode is **one-directory** (all DLLs alongside the EXE) for maximum stability. If you need a single-file EXE, run `python build.py --onefile` instead.

---

## Keyboard shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+V` | Paste URL |
| `Ctrl+L` | Focus URL bar |
| `Enter` | Fetch metadata |
| `Esc` | Cancel all downloads |
| `Ctrl+,` | Settings |
| `Ctrl+H` | History |
| `Ctrl+J` | Queue |
| `Ctrl+1` | Download tab |
| `Ctrl+2` | Queue tab |
| `Ctrl+3` | Editor tab |
| `Ctrl+4` | Channels tab |
| `Ctrl+5` | History tab |
| `Ctrl+6` | Settings tab |

---

## Filename template tokens

`{title}` &middot; `{channel}` &middot; `{quality}` &middot; `{id}` &middot; `{date}` &middot; `{ext}`

Example: `{channel} - {title} [{quality}].{ext}` &rarr; `jawed - Me at the zoo [1080p].mp4`

---

## Architecture

```
tex-downloader/
├── main.py                    # entry point: splash → window
├── build.py                   # PyInstaller wrapper (one-dir + zip)
├── assets/
│   ├── logo.svg               # app logo (pixel T)
│   ├── icon.ico               # multi-size Windows icon
│   ├── icon.png               # 256px fallback
│   ├── fonts/                 # dot-matrix TTFs
│   └── sounds/                # UI WAV effects
├── core/
│   ├── config.py              # portable-aware config (TexData/ or ~/.tex/)
│   ├── detector.py            # URL → platform
│   ├── metadata.py            # yt-dlp wrapper, ffmpeg discovery
│   ├── formats.py             # quality ladder (MP4 + MP3)
│   ├── downloader.py          # QThread + progress + pause/cancel + trim
│   ├── queue.py               # N-slot FIFO with unlimited mode
│   ├── naming.py              # filename templates
│   ├── tags.py                # ID3 + cover art
│   ├── history.py             # last 50
│   ├── cookies.py             # browser auto-detection for yt-dlp
│   ├── clipboard.py           # URL watcher
│   ├── sound.py               # SoundManager (QSoundEffect)
│   └── channel.py             # bulk channel fetcher
├── ui/
│   ├── app.py                 # TexWindow — frameless, edge-resize
│   ├── theme.py               # QSS — 6 themes, token-based
│   ├── icons.py               # hand-rolled SVG icons
│   ├── anim.py                # animation helpers
│   ├── shortcuts.py           # global QShortcut installer
│   ├── tray.py                # system tray
│   └── widgets/
│       ├── title_bar.py       # custom title bar
│       ├── sidebar.py         # collapsible nav (Download / Queue / Editor / Channels / History / Settings)
│       ├── splash.py          # frameless splash + 3-dot loader
│       ├── url_bar.py         # URL input with status dot
│       ├── editor_panel.py    # visual timeline trim & download
│       ├── channel_panel.py   # bulk channel downloader
│       ├── format_picker.py   # quality chips
│       ├── progress_card.py   # per-item progress
│       ├── history_panel.py   # download history list
│       ├── settings_panel.py  # all preferences
│       ├── video_card.py      # thumbnail + metadata card
│       ├── playlist_panel.py  # playlist view
│       ├── queue_bar.py       # queue status bar
│       ├── dot_matrix.py      # pixel-art glyph library
│       └── icon_button.py     # SVG icon button classes
└── .github/
    └── workflows/
        └── release.yml        # tag v* → auto-build ZIP → GitHub Release
```

---

## UI tokens

All QSS colors are driven by tokens in `ui/theme.py`. Edit `_qss(...)` to retheme.

Key tokens: `accent` (`#D7191A`), `fg`, `fg_dim`, `bg`, `panel`, `hairline`, `hover`, `soft`, `danger`.

---

## Privacy

Tex never sends your URLs or downloads to any third party. All data lives in `TexData/` (portable) or `~/.tex/` (installed) on your local machine.

---

## License

MIT