"""Filename template engine. Tokens: {title} {channel} {date} {quality} {id} {ext}"""
from __future__ import annotations

import datetime as dt
import re
from pathlib import Path

from .metadata import safe_filename

_TOKEN_RE = re.compile(r"\{([a-zA-Z_]+)\}")


def render(
    template: str,
    *,
    title: str,
    channel: str = "",
    quality: str = "",
    vid_id: str = "",
    date: str = "",
    ext: str = "mp4",
) -> str:
    today = dt.date.today().isoformat()
    mapping = {
        "title": safe_filename(title) or "untitled",
        "channel": safe_filename(channel) or "unknown",
        "quality": quality or "",
        "id": vid_id or "",
        "date": date or today,
        "ext": ext or "mp4",
    }
    out = _TOKEN_RE.sub(lambda m: mapping.get(m.group(1), m.group(0)), template)

    # Strip path separators and traversal sequences from the literal parts
    # of the template (user could set "../{title}.{ext}" which would write
    # outside the intended directory).
    out = out.replace("\\", "/")
    # Remove any leading or embedded ../  or ..\  traversal
    while "../" in out:
        out = out.replace("../", "")
    while "./" in out:
        out = out.replace("./", "")
    # Strip leading /  (absolute path injection)
    out = out.lstrip("/")

    if "{ext}" not in template:
        out = f"{out}.{ext}"
    else:
        out = out.strip()
    return out


def render_path(
    template: str,
    base_dir: Path,
    *,
    title: str,
    channel: str = "",
    quality: str = "",
    vid_id: str = "",
    date: str = "",
    ext: str = "mp4",
) -> Path:
    fname = render(
        template,
        title=title, channel=channel, quality=quality,
        vid_id=vid_id, date=date, ext=ext,
    )
    return base_dir / fname


def unique_path(path: Path) -> Path:
    """If path exists, append (1), (2) … before the extension."""
    if not path.exists():
        return path
    stem, suffix = path.stem, path.suffix
    i = 1
    while True:
        candidate = path.with_name(f"{stem} ({i}){suffix}")
        if not candidate.exists():
            return candidate
        i += 1
