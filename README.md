# Fly Krew Downloader

Download SoundCloud playlists as a ZIP of MP3 files.

---

## For Friends (Plug & Play)

1. Download the ZIP for your OS from Releases:
   - `FlyKrewDownloader-Windows.exe`
   - `FlyKrewDownloader-macOS.dmg`
2. **Windows:** Run `FlyKrewDownloader-Windows.exe`
   - If SmartScreen warns "Unknown publisher", click *More info* → *Run anyway*
3. **macOS:** Open `FlyKrewDownloader-macOS.dmg`
   - Drag `FlyKrewDownloader.app` to Applications (recommended)
   - If Gatekeeper blocks it, right-click → *Open* → *Open* to confirm
4. Your browser opens automatically — paste a playlist URL and click Download
5. Close the app when you're done

> Note: The app automatically closes after ~15 minutes with no page activity.
> If you come back later and see an error, just re-open the app.

No Python, no installs, nothing else needed.

---

## For Developers

### Setup (any OS)

1. Install Python 3.10+
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Download ffmpeg:
   ```
   python setup_bins.py
   ```
   This auto-detects your OS (Windows/macOS/Linux) and downloads the right binary.
   Alternatively, install ffmpeg via your package manager (`brew install ffmpeg`,
   `apt install ffmpeg`, etc.) and it will be found on PATH.

### Run (dev mode)

```
python launcher.py
```

Or the old way:
```
python -m app.main
```
Then open http://localhost:8000

### Build Standalone Distributable

```
python build.py
```

Produces:
- `dist/FlyKrewDownloader-Windows.exe` — Windows single-file download
- `dist/FlyKrewDownloader-macOS.dmg` — macOS disk image containing `FlyKrewDownloader.app`

> **Note:** You must build on each target OS separately (PyInstaller cannot
> cross-compile). Build on Windows for Windows, on a Mac for macOS.

---

## Limitations

- **Single-user only** — not designed for shared hosting
- Public playlists only (private requires authentication)
- Maximum quality: 128kbps MP3 (SoundCloud's streaming limit)
- Large playlists (100+ tracks) may take several minutes
- Server restart clears all in-progress jobs
