"""Build a portable .exe using PyInstaller.

Produces a single-file executable with:
  - Custom icon (assets/icon.ico)
  - All assets bundled
  - yt-dlp and dependencies included
  - Portable config (next to EXE in TexData/)

Usage:
    python build.py           # standard build
    python build.py --dir     # one-directory build (faster, easier to debug)
"""
import os
import sys
import shutil
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))


def _find_icon() -> str:
    for name in ("assets/icon.ico", "assets/icon.png"):
        p = os.path.join(HERE, name)
        if os.path.exists(p):
            return p
    return "NONE"


def main() -> int:
    icon = _find_icon()
    one_dir = "--dir" in sys.argv

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--noconsole",
    ]

    if one_dir:
        cmd.append("--onedir")
        cmd.extend(["--name", "TEX"])
    else:
        cmd.append("--onefile")
        cmd.extend(["--name", "TEX"])

    # Icon
    if icon != "NONE":
        cmd.extend(["--icon", icon])

    # Assets (sounds, fonts, etc.)
    cmd.extend(["--add-data", f"assets{os.pathsep}assets"])

    # Hidden imports that PyInstaller misses
    hidden = [
        "yt_dlp",
        "imageio_ffmpeg",
        "mutagen",
        "requests",
        "PIL",
        "PySide6.QtMultimedia",
    ]
    for h in hidden:
        cmd.extend(["--hidden-import", h])

    cmd.append("main.py")

    cmd = [c for c in cmd if c != "NONE"]
    print(">>", " ".join(cmd))

    ret = subprocess.call(cmd, cwd=HERE)

    if ret == 0 and not one_dir:
        # Copy icon next to the EXE for tray icon usage
        dist_dir = os.path.join(HERE, "dist")
        if os.path.isdir(dist_dir):
            if icon != "NONE" and icon.endswith(".ico"):
                shutil.copy2(icon, os.path.join(dist_dir, "icon.ico"))
            elif icon != "NONE" and icon.endswith(".png"):
                shutil.copy2(icon, os.path.join(dist_dir, "icon.png"))
            print("\nPortable build ready in dist/")
            print("Copy dist/TEX.exe anywhere — config lives in TexData/ next to it.")

    return ret


if __name__ == "__main__":
    sys.exit(main())