"""
Configuration constants.
"""
import platform
import shutil
import sys
from pathlib import Path


def _is_frozen() -> bool:
    """True when running inside a PyInstaller bundle."""
    return getattr(sys, "frozen", False)


def _base_dir() -> Path:
    """Resolve project root, works both in dev and PyInstaller builds."""
    if _is_frozen():
        # PyInstaller sets sys._MEIPASS for one-folder / one-file mode
        return Path(sys._MEIPASS)  # type: ignore[attr-defined]
    return Path(__file__).parent.parent


# Paths
BASE_DIR = _base_dir()
BIN_DIR = BASE_DIR / "bin"
DOWNLOADS_DIR = BASE_DIR / "downloads" if not _is_frozen() else Path(sys.executable).parent / "downloads"
STATIC_DIR = BASE_DIR / "static"


def _resolve_ffmpeg() -> Path:
    """
    Locate the ffmpeg binary in a cross-platform way.

    Priority:
      1. Bundled binary in bin/  (ffmpeg.exe on Windows, ffmpeg on macOS/Linux)
      2. ffmpeg on the system PATH
    """
    is_win = platform.system() == "Windows"
    binary_name = "ffmpeg.exe" if is_win else "ffmpeg"
    bundled = BIN_DIR / binary_name
    if bundled.exists():
        return bundled

    # Fall back to system-installed ffmpeg
    system_ffmpeg = shutil.which("ffmpeg")
    if system_ffmpeg:
        return Path(system_ffmpeg)

    # Return the expected bundled path so error messages are helpful
    return bundled


# ffmpeg path (cross-platform)
FFMPEG_PATH = _resolve_ffmpeg()

# Download settings
SLEEP_BETWEEN_TRACKS = 2  # seconds, to avoid rate limiting
MAX_FILENAME_LENGTH = 200  # safe limit on all platforms

# Server settings
HOST = "127.0.0.1"
PORT = 8000


# ---------------------------------------------------------------------------
# Feature flags — flip any of these to False to instantly hide/disable a
# feature in the UI without touching code. The frontend reads them from
# /api/features on load. This is the easy "kill switch" for anything that
# doesn't earn its keep.
# ---------------------------------------------------------------------------
FEATURES: dict[str, bool] = {
	# Queue several URLs and download them one after another.
	"multi_url_queue": True,
	# Checkbox to prefix filenames with track number ("01 - Artist - Title").
	"number_tracks_toggle": True,
	# Checkbox to turn the background animations on/off.
	"animations_toggle": True,
	# Keep a "Download ZIP again" button after a job completes.
	"redownload_button": True,
}
