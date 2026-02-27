"""
Build a standalone distributable using PyInstaller.

Run from the repo root:
    python build.py

Produces:
    dist/FlyKrewDownloader/          <- folder with the exe + all deps
    dist/FlyKrewDownloader.zip       <- ready-to-share archive

Requirements:
    pip install pyinstaller
"""
import os
import platform
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path


ROOT = Path(__file__).parent
DIST = ROOT / "dist"
BUILD = ROOT / "build"
APP_NAME = "FlyKrewDownloader"
IS_WIN = platform.system() == "Windows"
IS_MAC = platform.system() == "Darwin"


def find_ffmpeg() -> Path | None:
    """Locate the ffmpeg binary that should be bundled."""
    binary_name = "ffmpeg.exe" if IS_WIN else "ffmpeg"
    bundled = ROOT / "bin" / binary_name
    if bundled.exists():
        return bundled

    system = shutil.which("ffmpeg")
    if system:
        return Path(system)

    return None


def run_pyinstaller() -> None:
    ffmpeg = find_ffmpeg()
    if not ffmpeg:
        print("ERROR: ffmpeg not found.")
        print("Run 'python setup_bins.py' first or install ffmpeg.")
        sys.exit(1)

    # Determine platform-specific ffmpeg dest inside the bundle
    ffmpeg_dest = "bin"  # will be placed at <bundle>/bin/ffmpeg[.exe]

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--clean",
        # One-folder mode (faster startup, more reliable than one-file)
        "--onedir",
        "--name", APP_NAME,
        # Bundle static files
        "--add-data", f"{ROOT / 'static'}{os.pathsep}static",
        # Bundle ffmpeg binary
        "--add-data", f"{ffmpeg}{os.pathsep}{ffmpeg_dest}",
        # Hidden imports that PyInstaller may miss
        "--hidden-import", "uvicorn.logging",
        "--hidden-import", "uvicorn.loops",
        "--hidden-import", "uvicorn.loops.auto",
        "--hidden-import", "uvicorn.protocols",
        "--hidden-import", "uvicorn.protocols.http",
        "--hidden-import", "uvicorn.protocols.http.auto",
        "--hidden-import", "uvicorn.protocols.websockets",
        "--hidden-import", "uvicorn.protocols.websockets.auto",
        "--hidden-import", "uvicorn.lifespan",
        "--hidden-import", "uvicorn.lifespan.on",
        "--hidden-import", "uvicorn.lifespan.off",
        "--hidden-import", "app",
        "--hidden-import", "app.main",
        "--hidden-import", "app.config",
        "--hidden-import", "app.downloader",
        "--hidden-import", "app.zipper",
        # Collect all yt-dlp extractors (they're loaded dynamically)
        "--collect-all", "yt_dlp",
    ]

    # Console mode: user sees the server window (intentional — they need to
    # know the app is running and can close it to stop).
    # On macOS we could do --windowed but console is clearer for now.
    if IS_WIN:
        cmd.append("--console")

    # Entry point
    cmd.append(str(ROOT / "launcher.py"))

    print(f"Running PyInstaller ({platform.system()})...")
    print(f"  ffmpeg: {ffmpeg}")
    print(f"  Command: {' '.join(cmd)}\n")

    subprocess.check_call(cmd)


def create_zip() -> Path:
    """Zip the dist folder for easy sharing."""
    dist_folder = DIST / APP_NAME
    if not dist_folder.exists():
        print(f"ERROR: {dist_folder} does not exist. Build failed?")
        sys.exit(1)

    suffix = "Windows" if IS_WIN else ("macOS" if IS_MAC else "Linux")
    zip_name = f"{APP_NAME}-{suffix}.zip"
    zip_path = DIST / zip_name

    print(f"\nCreating {zip_name}...")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for file in dist_folder.rglob("*"):
            arcname = f"{APP_NAME}/{file.relative_to(dist_folder)}"
            zf.write(file, arcname)

    size_mb = zip_path.stat().st_size / (1024 * 1024)
    print(f"  -> {zip_path}  ({size_mb:.1f} MB)")
    return zip_path


def main() -> None:
    print("=" * 50)
    print(f"  Building {APP_NAME}")
    print(f"  Platform: {platform.system()} {platform.machine()}")
    print("=" * 50)
    print()

    # Clean previous builds
    for d in (BUILD, DIST):
        if d.exists():
            shutil.rmtree(d)

    run_pyinstaller()
    zip_path = create_zip()

    print()
    print("=" * 50)
    print("  BUILD COMPLETE")
    print(f"  Folder: dist/{APP_NAME}/")
    print(f"  ZIP:    {zip_path.name}")
    print()
    print("  To test: run dist/FlyKrewDownloader/FlyKrewDownloader" + (".exe" if IS_WIN else ""))
    print("  To share: send the ZIP file to your friends!")
    print("=" * 50)


if __name__ == "__main__":
    main()
