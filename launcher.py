"""
Standalone launcher for Fly Krew Downloader.

Double-click this (or the PyInstaller exe) to:
  1. Start the web server
  2. Auto-open the browser
  3. Keep running until the window is closed
"""
import sys
import threading
import time
import webbrowser

import uvicorn

from app.config import HOST, PORT


URL = f"http://{HOST}:{PORT}"


def open_browser() -> None:
    """Wait for the server to be ready, then open the default browser."""
    time.sleep(1.5)
    webbrowser.open(URL)


def main() -> None:
    print("=" * 50)
    print("  Fly Krew Downloader")
    print(f"  Running at {URL}")
    print("  Close this window to stop the server.")
    print("=" * 50)
    print()

    # Open browser in background thread
    threading.Thread(target=open_browser, daemon=True).start()

    try:
        uvicorn.run(
            "app.main:app",
            host=HOST,
            port=PORT,
            log_level="warning",
        )
    except KeyboardInterrupt:
        pass

    print("\nServer stopped.")


if __name__ == "__main__":
    main()
