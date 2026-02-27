"""Standalone launcher for Fly Krew Downloader.

Double-click this (or the packaged build) to:
    1. Start the web server
    2. Auto-open the browser
    3. Auto-exit after inactivity (no active downloads)
"""
import sys
import threading
import time
import webbrowser
from datetime import datetime, timedelta

import uvicorn

from app.config import HOST, PORT


INACTIVITY_TIMEOUT = timedelta(minutes=15)
WATCHDOG_POLL_SECONDS = 10


URL = f"http://{HOST}:{PORT}"


def open_browser() -> None:
    """Wait for the server to be ready, then open the default browser."""
    time.sleep(1.5)
    webbrowser.open(URL)


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
    print("=" * 50)
    print("  Fly Krew Downloader")
    print(f"  Running at {URL}")
    print("  Close this window to stop the server.")
    print("=" * 50)
    print()

    # Open browser in background thread
    threading.Thread(target=open_browser, daemon=True).start()

    config = uvicorn.Config(
        "app.main:app",
        host=HOST,
        port=PORT,
        log_level="warning",
    )
    server = uvicorn.Server(config)

    # Auto-exit watchdog
    threading.Thread(target=start_watchdog, args=(server,), daemon=True).start()

    try:
        server.run()
    except KeyboardInterrupt:
        pass

    print("\nServer stopped.")


if __name__ == "__main__":
    main()
