"""
Download ffmpeg binary to /bin directory.
Run this once after cloning the repo.

Note: yt-dlp is installed via pip (in requirements.txt), not as a binary.
Supports Windows (x64), macOS (Intel & Apple Silicon), and Linux (x64).
"""
import os
import platform
import stat
import tarfile
import urllib.request
import zipfile
import shutil
from pathlib import Path

BIN_DIR = Path(__file__).parent / "bin"

# ---------- download URLs per platform ----------
_FFMPEG_URLS: dict[str, str] = {
    "Windows-x64": (
        "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/"
        "ffmpeg-master-latest-win64-gpl.zip"
    ),
    "Darwin-x64": (
        "https://evermeet.cx/ffmpeg/getrelease/zip"
    ),
    "Darwin-arm64": (
        "https://evermeet.cx/ffmpeg/getrelease/zip"
    ),
    "Linux-x64": (
        "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/"
        "ffmpeg-master-latest-linux64-gpl.tar.xz"
    ),
}


def _platform_key() -> str:
    system = platform.system()          # Windows | Darwin | Linux
    machine = platform.machine().lower()
    if machine in ("x86_64", "amd64"):
        arch = "x64"
    elif machine in ("arm64", "aarch64"):
        arch = "arm64"
    else:
        arch = machine
    return f"{system}-{arch}"


def _download(url: str, dest: Path) -> None:
    print(f"  Downloading from {url}")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=120) as resp, open(dest, "wb") as f:
        shutil.copyfileobj(resp, f)


def download_ffmpeg() -> None:
    key = _platform_key()
    url = _FFMPEG_URLS.get(key)

    if not url:
        print(f"No automatic ffmpeg download for platform '{key}'.")
        print("Please download ffmpeg manually and place it in the bin/ folder.")
        return

    is_win = platform.system() == "Windows"
    binary_name = "ffmpeg.exe" if is_win else "ffmpeg"
    dest_path = BIN_DIR / binary_name

    if dest_path.exists():
        print(f"{binary_name} already exists in bin/ — skipping download.")
        return

    print(f"Downloading ffmpeg for {key}...")

    if url.endswith(".zip"):
        archive_path = BIN_DIR / "ffmpeg.zip"
        _download(url, archive_path)
        print("Extracting...")
        with zipfile.ZipFile(archive_path, "r") as zf:
            for name in zf.namelist():
                # Windows zip has nested bin/ffmpeg.exe; macOS zip has ffmpeg at root
                basename = name.rsplit("/", 1)[-1]
                if basename == binary_name:
                    with zf.open(name) as src, open(dest_path, "wb") as dst:
                        shutil.copyfileobj(src, dst)
                    break
        archive_path.unlink(missing_ok=True)

    elif url.endswith(".tar.xz"):
        archive_path = BIN_DIR / "ffmpeg.tar.xz"
        _download(url, archive_path)
        print("Extracting...")
        with tarfile.open(archive_path, "r:xz") as tf:
            for member in tf.getmembers():
                if member.name.endswith("/ffmpeg") or member.name == "ffmpeg":
                    member.name = binary_name
                    tf.extract(member, path=BIN_DIR)
                    break
        archive_path.unlink(missing_ok=True)

    else:
        # Direct binary download
        _download(url, dest_path)

    # Make executable on Unix
    if not is_win and dest_path.exists():
        dest_path.chmod(dest_path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    if dest_path.exists():
        print(f"{binary_name} ready!")
    else:
        print("ERROR: ffmpeg binary not found after extraction.")
        print("Please download ffmpeg manually and place it in the bin/ folder.")


if __name__ == "__main__":
    BIN_DIR.mkdir(exist_ok=True)
    download_ffmpeg()
    print("\nSetup complete! Now run: pip install -r requirements.txt")
