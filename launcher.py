"""Standalone launcher for Fly Krew Downloader.

Double-click this (or the packaged build) to:
    1. Start the web server
    2. Auto-open the browser
    3. Auto-exit after inactivity (no active downloads)
"""
import os
import sys
import threading
import time
import urllib.request
import webbrowser
from datetime import datetime, timedelta

import uvicorn

from app.config import HOST, PORT


INACTIVITY_TIMEOUT = timedelta(minutes=15)
WATCHDOG_POLL_SECONDS = 10


URL = f"http://{HOST}:{PORT}"


def _ensure_std_streams() -> None:
    """Ensure stdout/stderr are usable in PyInstaller --noconsole builds.

    In windowed/no-console mode on Windows, sys.stdout/sys.stderr can be None,
    which breaks libraries that probe TTY capabilities (e.g. isatty()).
    """

    def ensure(stream_name: str) -> None:
        stream = getattr(sys, stream_name)
        if stream is None:
            setattr(sys, stream_name, open(os.devnull, "w", encoding="utf-8", errors="ignore"))
            return
        if not hasattr(stream, "isatty"):
            setattr(sys, stream_name, open(os.devnull, "w", encoding="utf-8", errors="ignore"))

    ensure("stdout")
    ensure("stderr")


def open_browser() -> None:
    """Wait for the server to be ready, then open the default browser."""
    # Poll for readiness so we don't open a dead tab on slow startup.
    deadline = time.time() + 20
    while time.time() < deadline:
        if _ping_server(timeout=1.0):
            break
        time.sleep(0.25)
    webbrowser.open(URL)


def _ping_server(timeout: float = 1.0) -> bool:
    try:
        with urllib.request.urlopen(f"{URL}/api/ping", timeout=timeout) as resp:
            status = getattr(resp, "status", 200)
            return 200 <= int(status) < 300
    except Exception:
        return False


def _show_startup_error(title: str, message: str) -> None:
    """Show a user-visible error in no-console builds."""
    # Prefer a native Windows message box (no extra deps).
    if sys.platform.startswith("win"):
        try:
            import ctypes

            ctypes.windll.user32.MessageBoxW(None, message, title, 0x10)  # MB_ICONERROR
            return
        except Exception:
            pass

    # Fallback: best-effort stderr (may be hidden in windowed builds).
    try:
        sys.stderr.write(f"{title}: {message}\n")
        sys.stderr.flush()
    except Exception:
        pass


def start_watchdog(server: uvicorn.Server) -> None:
    """Stop the server after a period of no download activity and no active jobs."""
    # Import here so the module state is shared with the running app in-process.
    from app import main as app_main

    while not server.should_exit:
        try:
            now = datetime.now()
            last = app_main.get_last_activity()
            active = app_main.has_active_jobs()
            if (not active) and (now - last) > INACTIVITY_TIMEOUT:
                server.should_exit = True
                return
        except Exception:
            # Don't crash the app if watchdog has trouble.
            pass
        time.sleep(WATCHDOG_POLL_SECONDS)


def main() -> None:
    _ensure_std_streams()

    # If an instance is already running, just open the UI and exit.
    if _ping_server(timeout=0.8):
        webbrowser.open(URL)
        return

    print("=" * 50)
    print("  Fly Krew Downloader")
    print(f"  Running at {URL}")
    print("  Close this window to stop the server.")
    print("=" * 50)
    print()

    config = uvicorn.Config(
        "app.main:app",
        host=HOST,
        port=PORT,
        log_level="warning",
        use_colors=False,
    )
    server = uvicorn.Server(config)

    # Open browser in background thread (after we know we're attempting startup)
    threading.Thread(target=open_browser, daemon=True).start()

    # Auto-exit watchdog
    threading.Thread(target=start_watchdog, args=(server,), daemon=True).start()

    try:
        server.run()
    except OSError as e:
        # Common case: previous instance is still running and owns the port.
        winerror = getattr(e, "winerror", None)
        msg = str(e).lower()
        if winerror == 10048 or "address already in use" in msg or "only one usage" in msg:
            if _ping_server(timeout=0.8):
                webbrowser.open(URL)
                return
            _show_startup_error(
                "Fly Krew Downloader already running",
                "FlyKrewDownloader is already using port 8000. Close it in Task Manager and try again.",
            )
            return
        _show_startup_error("Fly Krew Downloader failed to start", str(e))
        return
    except KeyboardInterrupt:
        pass

    print("\nServer stopped.")


if __name__ == "__main__":
    main()
