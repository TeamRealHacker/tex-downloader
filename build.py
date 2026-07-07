"""Build a portable folder using PyInstaller.

Produces a one-directory build (TEX/) containing TEX.exe + all DLLs and
dependencies side-by-side.  This is more stable than a single-file EXE
because the OS loads DLLs individually instead of unpacking a ~150 MB
archive to a temp folder every launch.

Usage:
    python build.py            # one-directory build + zip
    python build.py --onefile  # legacy single-EXE (less stable)
"""
import os
import sys
import shutil
import subprocess
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
DIST_DIR = os.path.join(HERE, "dist")
BUILD_DIR = os.path.join(HERE, "build")


def _find_icon() -> str:
    """Return the best icon file available, or 'NONE'."""
    for name in ("assets/icon.ico", "assets/icon.png"):
        p = os.path.join(HERE, name)
        if os.path.exists(p):
            return p
    return "NONE"


def _pyinstaller_args(onefile: bool) -> list[str]:
    """Build the PyInstaller command line."""
    icon = _find_icon()

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--noconsole",
    ]

    if onefile:
        cmd.append("--onefile")
    else:
        cmd.append("--onedir")

    cmd.extend(["--name", "TEX"])

    # Icon
    if icon != "NONE":
        cmd.extend(["--icon", icon])

    # Assets (sounds, fonts, etc.)
    cmd.extend(["--add-data", f"assets{os.pathsep}assets"])

    # Hidden imports that PyInstaller misses
    hidden = [
        "yt_dlp",
        "yt_dlp.extractor",
        "imageio_ffmpeg",
        "mutagen",
        "mutagen.mp4",
        "mutagen.id3",
        "requests",
        "PIL",
        "PIL.Image",
        "PIL.ImageQt",
        "PySide6.QtMultimedia",
        "PySide6.QtMultimediaWidgets",
        "PySide6.QtCore",
        "PySide6.QtGui",
        "PySide6.QtWidgets",
        "PySide6.QtNetwork",
        "json",
        "urllib.parse",
    ]
    for h in hidden:
        cmd.extend(["--hidden-import", h])

    cmd.append("main.py")

    # Filter out the placeholder
    cmd = [c for c in cmd if c != "NONE"]
    return cmd


def _zip_folder(folder: str, out_zip: str) -> None:
    """Zip a folder's contents (not the folder itself) into *out_zip*."""
    with zipfile.ZipFile(out_zip, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, _dirs, files in os.walk(folder):
            for f in files:
                full = os.path.join(root, f)
                arcname = os.path.relpath(full, folder)
                zf.write(full, arcname)


def main() -> int:
    onefile = "--onefile" in sys.argv

    cmd = _pyinstaller_args(onefile)
    print(">>", " ".join(cmd))

    ret = subprocess.call(cmd, cwd=HERE)
    if ret != 0:
        return ret

    icon = _find_icon()

    if onefile:
        # Legacy single-EXE: copy icon next to it
        if os.path.isdir(DIST_DIR) and icon != "NONE":
            ext = ".ico" if icon.endswith(".ico") else ".png"
            shutil.copy2(icon, os.path.join(DIST_DIR, f"icon{ext}"))
        print("\nSingle-EXE build ready in dist/TEX.exe")
    else:
        # One-directory build: copy icon + create zip
        tex_dir = os.path.join(DIST_DIR, "TEX")
        if os.path.isdir(tex_dir) and icon != "NONE":
            ext = ".ico" if icon.endswith(".ico") else ".png"
            shutil.copy2(icon, os.path.join(tex_dir, f"icon{ext}"))

        # Create portable zip
        zip_path = os.path.join(DIST_DIR, "TEX-Portable.zip")
        if os.path.exists(zip_path):
            os.remove(zip_path)
        _zip_folder(tex_dir, zip_path)
        zip_mb = os.path.getsize(zip_path) / (1024 * 1024)
        print(f"\nPortable build ready in dist/TEX/")
        print(f"Zipped: dist/TEX-Portable.zip ({zip_mb:.1f} MB)")
        print("Copy the entire TEX/ folder anywhere — config lives in TexData/ next to TEX.exe.")

    return 0


if __name__ == "__main__":
    sys.exit(main())