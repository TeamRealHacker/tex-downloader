"""Build a single-file .exe using PyInstaller."""
import os
import sys
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))


def main() -> int:
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--noconsole",
        "--onefile",
        "--name", "TEX",
        "--add-data", f"assets{os.pathsep}assets",
        "--icon", os.path.join("assets", "icon.ico") if os.path.exists(os.path.join(HERE, "assets", "icon.ico")) else "NONE",
        "main.py",
    ]
    cmd = [c for c in cmd if c != "NONE"]
    print(">>", " ".join(cmd))
    return subprocess.call(cmd, cwd=HERE)


if __name__ == "__main__":
    sys.exit(main())
