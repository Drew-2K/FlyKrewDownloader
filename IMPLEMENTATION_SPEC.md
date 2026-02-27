# SoundCloud Playlist to MP3 ZIP Downloader

## Overview

A local Python web application that takes a SoundCloud playlist URL via a browser interface, downloads all tracks as numbered MP3s, and serves a ZIP file for download.

**Core approach:** Use yt-dlp (the most reliable SoundCloud extraction tool) as a Python library, with FastAPI serving a simple web UI. Bundle ffmpeg for zero-dependency distribution to end users.

---

## Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Language | Python 3.10+ | Best yt-dlp integration, mature ecosystem |
| SoundCloud access | yt-dlp library | Most reliable, actively maintained, handles client_id rotation automatically |
| Web framework | FastAPI | Modern async, simple, good for future API expansion |
| ffmpeg | Bundled in `/bin` | Friends get zero-setup experience |
| Authentication | None (public playlists only) | Simpler; private support can be added later via cookies |
| Rate limiting | 2-second sleep between tracks | Conservative; avoids SoundCloud blocks |
| File naming | `{index:02d} - {artist} - {title}.mp3` | Preserves playlist order |

---

## Project Structure

```
FlyKrewDownloader/
├── app/
│   ├── __init__.py          # Empty, marks as package
│   ├── main.py              # FastAPI application entry point
│   ├── downloader.py        # yt-dlp wrapper logic
│   ├── zipper.py            # ZIP creation utilities
│   └── config.py            # Configuration constants
├── static/
│   ├── index.html           # Web UI
│   └── style.css            # Minimal styling
├── bin/                     # Bundled binaries (gitignored, user downloads)
│   └── ffmpeg.exe           # Only ffmpeg; yt-dlp installed via pip
├── downloads/               # Temp folder for tracks (gitignored)
├── requirements.txt
├── setup_bins.py            # Script to download ffmpeg/yt-dlp binaries
├── .gitignore
├── README.md
└── IMPLEMENTATION_SPEC.md   # This file
```

---

## Dependencies

### Python Packages (`requirements.txt`)

```
fastapi>=0.100.0
uvicorn[standard]>=0.23.0
yt-dlp>=2024.01.01
python-multipart>=0.0.6
```

### External Binaries (to be placed in `/bin`)

| Binary | Source | Purpose |
|--------|--------|---------|
| `ffmpeg.exe` | https://github.com/BtbN/FFmpeg-Builds/releases (Windows GPL build) | Audio conversion to MP3 |

> **Note:** yt-dlp is installed via pip (in requirements.txt), NOT as a bundled binary. This gives us direct Python library access for progress callbacks and cancellation support.

---

## Module Specifications

### 1. `app/config.py`

Configuration constants for the application.

```python
"""
Configuration constants.
"""
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).parent.parent
BIN_DIR = BASE_DIR / "bin"
DOWNLOADS_DIR = BASE_DIR / "downloads"
STATIC_DIR = BASE_DIR / "static"

# ffmpeg path (bundled)
FFMPEG_PATH = BIN_DIR / "ffmpeg.exe"

# Download settings
SLEEP_BETWEEN_TRACKS = 2  # seconds, to avoid rate limiting
MAX_FILENAME_LENGTH = 200  # Windows safe limit

# Server settings
HOST = "127.0.0.1"
PORT = 8000
```

---

### 2. `app/downloader.py`

Wrapper around yt-dlp for downloading SoundCloud playlists.

#### Public Interface

```python
class PlaylistDownloader:
    """Downloads SoundCloud playlists using yt-dlp."""
    
    def __init__(self, output_dir: Path, progress_callback: Callable = None):
        """
        Args:
            output_dir: Directory to save downloaded MP3s
            progress_callback: Optional callback(current_track, total_tracks, track_info)
        """
        pass
    
    async def download_playlist(self, url: str) -> DownloadResult:
        """
        Download all tracks from a SoundCloud playlist.
        
        Args:
            url: SoundCloud playlist URL
            
        Returns:
            DownloadResult with list of downloaded files and any errors
        """
        pass
    
    def get_playlist_info(self, url: str) -> PlaylistInfo:
        """
        Extract playlist metadata without downloading.
        
        Args:
            url: SoundCloud playlist URL
            
        Returns:
            PlaylistInfo with title, track count, etc.
        """
        pass


@dataclass
class TrackInfo:
    index: int           # 1-based position in playlist
    title: str
    artist: str
    duration: int        # seconds
    file_path: Path      # Path to downloaded MP3
    

@dataclass
class DownloadResult:
    playlist_title: str
    tracks: list[TrackInfo]      # Successfully downloaded
    errors: list[dict]           # Failed tracks: {"index": int, "title": str, "error": str}
    

@dataclass
class PlaylistInfo:
    title: str
    track_count: int
    uploader: str
    url: str
```

#### Implementation Notes

- Use yt-dlp as a Python library, not subprocess:
  ```python
  import yt_dlp
  
  ydl_opts = {
      'format': 'bestaudio/best',
      'postprocessors': [{
          'key': 'FFmpegExtractAudio',
          'preferredcodec': 'mp3',
          'preferredquality': '192',
      }],
      'ffmpeg_location': str(FFMPEG_PATH.parent),
      'outtmpl': str(output_dir / '%(title)s.%(ext)s'),
      'ignoreerrors': True,  # Continue on failed tracks
      'quiet': True,
      'no_warnings': True,
  }
  ```

- Implement progress hooks:
  ```python
  def progress_hook(d):
      if d['status'] == 'finished':
          # Track download complete
          pass
      elif d['status'] == 'downloading':
          # Update progress
          pass
  ```

- Add sleep between tracks:
  ```python
  import asyncio
  await asyncio.sleep(SLEEP_BETWEEN_TRACKS)
  ```

- Run yt-dlp in thread pool to avoid blocking:
  ```python
  import asyncio
  from concurrent.futures import ThreadPoolExecutor
  
  executor = ThreadPoolExecutor(max_workers=1)
  await asyncio.get_event_loop().run_in_executor(executor, sync_download_func)
  ```

---

### 3. `app/zipper.py`

ZIP creation with proper file naming.

#### Public Interface

```python
def create_playlist_zip(
    tracks: list[TrackInfo],
    playlist_title: str,
    output_path: Path
) -> Path:
    """
    Create a ZIP file containing all MP3s with numbered filenames.
    
    Args:
        tracks: List of TrackInfo with file paths
        playlist_title: Used for ZIP filename
        output_path: Directory to save the ZIP
        
    Returns:
        Path to the created ZIP file
    """
    pass


def sanitize_filename(name: str, max_length: int = 200) -> str:
    """
    Remove/replace invalid Windows filename characters.
    
    Replaces: < > : " / \ | ? *
    Strips leading/trailing spaces and dots.
    Truncates to max_length.
    """
    pass


def format_track_filename(track: TrackInfo) -> str:
    """
    Format track as: '01 - Artist - Title.mp3'
    
    Falls back to '01 - Title.mp3' if artist is empty/unknown.
    """
    pass
```

#### Implementation Notes

- Use Python's built-in `zipfile` module
- Create ZIP in memory if playlist is small (<100MB), otherwise use temp file
- Handle duplicate filenames by appending counter: `01 - Track (2).mp3`

**Track numbering uses original playlist position:**
- Source of truth: `playlist_index` from yt-dlp metadata
- Failed tracks leave gaps in numbering (intentional)
- Example: If track 2 fails → ZIP contains `01 - ..., 03 - ..., 04 - ...`
- This ensures consistency if user re-downloads after a track becomes available

---

### 4. `app/main.py`

FastAPI application with job management.

#### API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | Serve `index.html` |
| `GET` | `/static/{path}` | Serve static files |
| `POST` | `/api/download` | Start download job |
| `GET` | `/api/status/{job_id}` | Get job progress |
| `GET` | `/api/result/{job_id}` | Download ZIP file |
| `DELETE` | `/api/job/{job_id}` | Cancel/cleanup job |

#### Request/Response Models

```python
# POST /api/download
class DownloadRequest(BaseModel):
    url: str  # SoundCloud playlist URL

class DownloadResponse(BaseModel):
    job_id: str
    playlist_title: str
    track_count: int


# GET /api/status/{job_id}
class JobStatus(BaseModel):
    job_id: str
    status: Literal["pending", "downloading", "zipping", "complete", "cancelled", "error"]
    playlist_title: str | None
    total_tracks: int
    completed_tracks: int
    current_track: str | None  # Title of track being downloaded
    errors: list[dict]  # Failed tracks
    zip_ready: bool


# GET /api/result/{job_id}
# Returns: FileResponse with ZIP file
```

#### Job Management

```python
from dataclasses import dataclass, field
from datetime import datetime
import uuid

@dataclass
class Job:
    id: str
    url: str
    status: str = "pending"  # pending | downloading | zipping | complete | cancelled | error
    playlist_title: str | None = None
    total_tracks: int = 0
    completed_tracks: int = 0
    current_track: str | None = None
    errors: list = field(default_factory=list)
    zip_path: Path | None = None
    created_at: datetime = field(default_factory=datetime.now)
    cancel_requested: bool = False  # Set to True to stop after current track
    
# In-memory job storage (dict)
jobs: dict[str, Job] = {}
```

#### Implementation Notes

- Use `BackgroundTasks` for download jobs:
  ```python
  from fastapi import BackgroundTasks
  
  @app.post("/api/download")
  async def start_download(request: DownloadRequest, background_tasks: BackgroundTasks):
      job_id = str(uuid.uuid4())
      jobs[job_id] = Job(id=job_id, url=request.url)
      background_tasks.add_task(process_download, job_id)
      return {"job_id": job_id}
  ```

- Create unique temp directory per job:
  ```python
  job_dir = DOWNLOADS_DIR / job_id
  job_dir.mkdir(parents=True, exist_ok=True)
  ```

- Cleanup old jobs (files + memory) after 1 hour or on explicit delete

- Validate URL is a SoundCloud playlist:
  ```python
  import re
  SOUNDCLOUD_PLAYLIST_PATTERN = r'https?://soundcloud\.com/[\w-]+/sets/[\w-]+'
  ```

    **Shortlink support:** Also accept SoundCloud shortlinks (`https://on.soundcloud.com/...`) by resolving the redirect to its final URL, then validating that the resolved URL matches `SOUNDCLOUD_PLAYLIST_PATTERN`.

- **Cancellation handling** in download loop:
  ```python
  # In process_download background task:
  for track in playlist_entries:
      if job.cancel_requested:
          job.status = "cancelled"
          break  # Exit loop, current track already finished
      download_single_track(track)
      job.completed_tracks += 1
      await asyncio.sleep(SLEEP_BETWEEN_TRACKS)
  ```

- **Startup cleanup** - clear stale downloads on server start:
  ```python
  @app.on_event("startup")
  def cleanup_stale_downloads():
      if DOWNLOADS_DIR.exists():
          shutil.rmtree(DOWNLOADS_DIR)
      DOWNLOADS_DIR.mkdir(exist_ok=True)
  ```

- **Background cleanup task** - delete jobs older than 1 hour:
  ```python
  async def cleanup_old_jobs():
      while True:
          await asyncio.sleep(600)  # Every 10 minutes
          cutoff = datetime.now() - timedelta(hours=1)
          for job_id, job in list(jobs.items()):
              if job.created_at < cutoff:
                  shutil.rmtree(DOWNLOADS_DIR / job_id, ignore_errors=True)
                  del jobs[job_id]
  ```

---

### 5. `static/index.html`

Single-page web UI.

#### Features

1. **URL Input**
   - Text input for SoundCloud playlist URL
   - "Download" button
    - URL validation (client-side regex check)
      - Accept both full playlist URLs (`soundcloud.com/<user>/sets/<playlist>`) and SoundCloud shortlinks (`on.soundcloud.com/...`).
      - For shortlinks, the server resolves the redirect before starting the job.

2. **Progress Display**
   - Shows after job starts
   - Progress bar: `████████░░ 8/10 tracks`
   - Current track name
   - List of completed tracks with checkmarks
   - List of failed tracks with errors

3. **Download Button**
   - Appears when job completes
   - Links to `/api/result/{job_id}`
   - Shows ZIP filename and size

4. **Error Handling**
   - Display friendly errors for invalid URLs
   - Show partial success (some tracks failed)
   - Retry button on complete failure

#### JavaScript Logic

```javascript
// Poll for status every 2 seconds while downloading
async function pollStatus(jobId) {
    const response = await fetch(`/api/status/${jobId}`);
    const status = await response.json();
    
    updateProgressUI(status);
    
    if (status.status === 'complete' || status.status === 'error') {
        clearInterval(pollInterval);
        if (status.zip_ready) {
            showDownloadButton(jobId);
        }
    }
}

// Start download
async function startDownload() {
    const url = document.getElementById('url-input').value;
    const response = await fetch('/api/download', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({url})
    });
    const {job_id} = await response.json();
    pollInterval = setInterval(() => pollStatus(job_id), 2000);
}
```

---

### 6. `static/style.css`

Minimal, clean styling.

#### Design Guidelines

- Dark theme (easy on eyes, matches SoundCloud aesthetic)
- Centered card layout, max-width 600px
- Orange accent color (#ff5500 - SoundCloud's brand color)
- System font stack for fast loading
- Mobile-responsive

---

### 7. `setup_bins.py`

Script to download ffmpeg binary (yt-dlp is installed via pip).

```python
"""
Download ffmpeg binary to /bin directory.
Run this once after cloning the repo.

Note: yt-dlp is installed via pip (in requirements.txt), not as a binary.
"""
import urllib.request
import zipfile
import shutil
from pathlib import Path

BIN_DIR = Path(__file__).parent / "bin"

FFMPEG_URL = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"

def download_ffmpeg():
    """Download and extract ffmpeg.exe."""
    print("Downloading ffmpeg...")
    zip_path = BIN_DIR / "ffmpeg.zip"
    urllib.request.urlretrieve(FFMPEG_URL, zip_path)
    
    print("Extracting ffmpeg.exe...")
    with zipfile.ZipFile(zip_path, 'r') as zf:
        # Find ffmpeg.exe inside the archive (it's in a subfolder)
        for name in zf.namelist():
            if name.endswith('bin/ffmpeg.exe'):
                # Extract to bin/ with flat structure
                with zf.open(name) as src, open(BIN_DIR / 'ffmpeg.exe', 'wb') as dst:
                    shutil.copyfileobj(src, dst)
                break
    
    zip_path.unlink()  # Clean up zip
    print("ffmpeg.exe ready!")

if __name__ == "__main__":
    BIN_DIR.mkdir(exist_ok=True)
    download_ffmpeg()
    print("\nSetup complete! Now run: pip install -r requirements.txt")
```

---

### 8. `.gitignore`

```gitignore
# Binaries (user downloads separately)
bin/*.exe

# Downloaded files
downloads/

# Python
__pycache__/
*.pyc
*.pyo
.venv/
venv/
env/

# IDE
.vscode/
.idea/

# OS
.DS_Store
Thumbs.db
```

---

### 9. `README.md`

```markdown
# SoundCloud Playlist to MP3

Download SoundCloud playlists as a ZIP of MP3 files.

## Setup

1. Install Python 3.10+
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Download ffmpeg:
   ```
   python setup_bins.py
   ```
   Or manually place `ffmpeg.exe` in the `bin/` folder.

## Usage

1. Start the server:
   ```
   python -m app.main
   ```
2. Open http://localhost:8000
3. Paste a SoundCloud playlist URL
4. Click Download and wait
5. Save the ZIP file

## Limitations

- **Single-user only** - not designed for shared hosting
- Public playlists only (private requires authentication)
- Maximum quality: 128kbps MP3 (SoundCloud's streaming limit)
- Large playlists (100+ tracks) may take several minutes
- Server restart clears all in-progress jobs
```

---

## Execution Flow

```
User pastes URL → Click Download
         │
         ▼
    POST /api/download
         │
         ▼
    Validate URL (regex)
         │
         ▼
    Create Job (uuid)
    Start Background Task
         │
         ▼
    Return job_id to UI
         │
         ▼
    ┌─────────────────────────────────────┐
    │     Background: process_download    │
    │                                     │
    │  1. Extract playlist info (yt-dlp)  │
    │  2. Update job: total_tracks        │
    │  3. For each track:                 │
    │     - Download as MP3               │
    │     - Update job: current_track     │
    │     - Sleep 2 seconds               │
    │  4. Create ZIP with numbered files  │
    │  5. Update job: status=complete     │
    └─────────────────────────────────────┘
         │
         ▼
    UI polls GET /api/status/{job_id}
    Updates progress bar, track list
         │
         ▼
    Job complete → Show download button
         │
         ▼
    GET /api/result/{job_id}
         │
         ▼
    Browser downloads ZIP file
```

---

## Error Handling

| Error | Handling |
|-------|----------|
| Invalid URL | Return 400, show error in UI |
| Playlist not found | Return 404, show error in UI |
| Private playlist | yt-dlp returns error, show "Playlist is private" |
| Track unavailable | Log error, continue with other tracks, include in final report |
| Rate limited | yt-dlp handles internally; if persistent, track fails and we continue |
| ffmpeg not found | Return 500, show "Setup incomplete" error |
| Disk full | Catch IOError, cleanup partial files, mark job as error |
| Job cancelled | Stop after current track, create ZIP with completed tracks, status="cancelled" |

**Retry policy:** None at our application level. yt-dlp has internal retry logic for transient network errors. If a track ultimately fails, we record the error and move on. No exponential backoff at our layer.

---

## Testing Checklist

### Manual Tests

- [ ] Small playlist (3-5 tracks) downloads successfully
- [ ] ZIP contains correctly numbered MP3s
- [ ] Progress updates appear in real-time
- [ ] Failed tracks show in error list
- [ ] Download button works after completion
- [ ] Unicode characters in track titles handled
- [ ] Very long track titles truncated properly

### Edge Cases

- [ ] Playlist with 1 track
- [ ] Playlist with deleted/unavailable track in middle
- [ ] Playlist with 50+ tracks (rate limit test)
- [ ] Track title with special characters: `Track <Test> "Quotes" | Pipe`
- [ ] Two tracks with identical names
- [ ] Empty playlist (should error gracefully)

### URLs for Testing

```
# Public playlist (replace with actual test URLs)
https://soundcloud.com/user/sets/playlist-name

# Various sizes to test
- Small: 3-5 tracks
- Medium: 15-25 tracks  
- Large: 50+ tracks
```

---

## V1 Scope & Limitations

**V1 is a single-user local tool.** Multi-user hosting is explicitly out of scope.

### What V1 IS
- One person running it on their own machine
- One download at a time (UI enforced)
- Ephemeral job storage (server restart = jobs cleared)
- Localhost only (`127.0.0.1:8000`)

### What V1 is NOT
- A hosted service for multiple users
- Concurrent job isolation (two jobs might conflict)
- Persistent job history (no database)
- Secure against malicious input (URL validation only)

### In-Memory Limitations (Accepted)
- Jobs lost on server restart ✓
- No pagination for job list ✓
- Memory grows with active jobs (minimal - just metadata) ✓

### Hosting Scenarios

| Scenario | V1 Support |
|----------|------------|
| `localhost:8000` on your machine | ✅ Supported |
| LAN access from another device | ⚠️ Untested (bind to `0.0.0.0` manually) |
| Public internet hosting | ❌ Not supported (no auth, no user isolation) |
| Docker/container | ❌ Not supported |
| Multiple simultaneous users | ❌ Not supported |

### Cancellation Semantics
- **Supported:** Stop downloading after the current track finishes
- **Not supported:** Force-kill mid-track (risks file corruption)
- **Result:** Cancelled jobs produce a partial ZIP with all completed tracks

### Progress Counter Semantics
- `total_tracks`: Set once when playlist info is extracted
- `completed_tracks`: Increments only after MP3 file is written to disk
- `errors`: Failed tracks added immediately after failure
- **Invariant:** `completed_tracks + len(errors) ≤ total_tracks`

### Disk Cleanup Lifecycle
| Trigger | Action |
|---------|--------|
| Server startup | Delete ALL contents of `/downloads` |
| Job older than 1 hour | Auto-delete job folder + remove from memory |
| `DELETE /api/job/{id}` | Immediate deletion |
| ZIP downloaded | Stays available for 1 hour (allows re-download) |

---

## Future Enhancements (Out of Scope for V1)

1. **Private playlist support** - Add cookie extraction flow
2. **CLI mode** - Add argparse for command-line usage
3. **PyInstaller packaging** - Single .exe distribution (required for V2)
4. **Concurrent downloads** - Multiple tracks simultaneously (careful with rate limits)
5. **Album art embedding** - Include cover in MP3 metadata
6. **Format options** - FLAC, WAV, etc. (though SoundCloud source is lossy)
7. **Single track support** - Not just playlists
8. **Docker packaging** - For easy deployment
9. **Multi-user hosting** - Auth, user isolation, persistent storage

---

## V2 Planning: Plug-and-Play Distribution

> **Purpose:** Document V2 requirements so V1 architecture supports them. No V2 features implemented in V1.

### Target Users

| User | Platform | Technical Skill | Requirement |
|------|----------|-----------------|-------------|
| You | Windows | Developer | V1 is sufficient |
| Friend A | Windows | Non-coder | Download → Double-click → Works |
| Friend B | macOS (newer MacBook) | Non-coder | Download → Double-click → Works |

### V2 Hard Requirements

**Non-negotiable for friends:**
- ❌ No Python installation
- ❌ No terminal/command line
- ❌ No `pip install`
- ❌ No manual ffmpeg download
- ❌ No configuration or setup steps
- ✅ Download one file → Double-click → Browser opens → Use it

### What Gets Bundled (Users Install NOTHING)

PyInstaller creates a single executable containing:

| Component | Bundled? | Notes |
|-----------|----------|-------|
| Python 3.10+ interpreter | ✅ Yes | Embedded in exe |
| FastAPI + uvicorn | ✅ Yes | Bundled as Python packages |
| yt-dlp library | ✅ Yes | Bundled as Python package |
| ffmpeg binary | ✅ Yes | Included via `--add-binary` |
| Static files (HTML/CSS) | ✅ Yes | Included via `--add-data` |

**Result:** One ~90MB file. Nothing else needed.

### Chosen Approach: PyInstaller Single-File Executable

| Platform | Output | Size | User Experience |
|----------|--------|------|-----------------|
| Windows | `FlyKrewDownloader.exe` | ~90MB | Double-click → browser opens |
| macOS | `FlyKrewDownloader.app` | ~90MB | Double-click → browser opens |

**Why PyInstaller:**
- Bundles entire Python interpreter (users don't need Python)
- Handles all pip dependencies automatically
- Can embed ffmpeg binary
- Produces native executables for each platform
- Mature, well-documented, widely used

### V2 Architecture

```
User double-clicks FlyKrewDownloader.exe
         │
         ▼
    PyInstaller extracts to temp folder:
    ├── python310.dll (Python interpreter)
    ├── library.zip (all Python packages)
    ├── bin/ffmpeg.exe
    └── static/ (HTML, CSS)
         │
         ▼
    app/main.py runs (using bundled Python)
         │
         ▼
    Server starts on localhost:8000
         │
         ▼
    Auto-open default browser
         │
         ▼
    User sees web UI, uses normally
         │
         ▼
    User closes browser tab when done
    (exe keeps running until closed)
```

### What V1 Must Do to Enable V2

These V1 decisions directly support plug-and-play packaging:

| V1 Decision | Why It Helps V2 |
|-------------|-----------------|
| yt-dlp as pip library (not subprocess) | PyInstaller bundles it automatically |
| Relative paths (`Path(__file__).parent`) | Works inside packaged app |
| No external config files | Nothing for users to edit |
| FastAPI + uvicorn | Standard packages, bundle cleanly |
| Single `/bin` folder for ffmpeg | Easy to bundle alongside exe |
| No database | No additional files to manage |

### V1 → V2 Changes Required

| Component | V1 (Your dev machine) | V2 (Friends' machines) | Effort |
|-----------|----------------------|------------------------|--------|
| Python runtime | You installed it | Bundled in exe | Auto |
| pip dependencies | You ran `pip install` | Bundled in exe | Auto |
| ffmpeg | You ran `setup_bins.py` | Bundled in exe | Medium |
| ffmpeg path | Hardcoded `.exe` | Platform-aware | Low |
| App launch | `python -m app.main` | Double-click exe | Auto |
| Browser open | You open manually | Auto-open on startup | Low |
| Downloads folder | Project folder | User's Downloads | Low |

### Platform-Specific Details

#### Windows (`FlyKrewDownloader.exe`)

```
Build command:
pyinstaller --onefile --windowed --add-binary "bin/ffmpeg.exe;bin" --add-data "static;static" app/main.py
```

- `--onefile`: Single exe (extracts to temp on run)
- `--windowed`: No console window
- `--add-binary`: Include ffmpeg.exe
- Startup time: 3-5 seconds (extraction)
- Works on Windows 10/11

#### macOS (`FlyKrewDownloader.app`)

```
Build command:
pyinstaller --onefile --windowed --add-binary "bin/ffmpeg:bin" --add-data "static:static" app/main.py
```

- Different path separator (`:` not `;`)
- Bundle macOS ffmpeg binary (from evermeet.cx or Homebrew)
- **Gatekeeper warning on first run:**
  - macOS blocks unsigned apps by default
  - User must: Right-click → Open → "Open Anyway"
  - Document this clearly with screenshots
  - Alternative: Pay $99/year for Apple Developer account to sign it

### config.py Changes for V2

```python
"""
Configuration constants - V2 cross-platform version.
"""
import platform
import sys
from pathlib import Path

# Detect if running as PyInstaller bundle
if getattr(sys, 'frozen', False):
    # Running as compiled exe - PyInstaller sets this
    BASE_DIR = Path(sys._MEIPASS)  # Temp extraction folder
else:
    # Running as script (V1 dev mode)
    BASE_DIR = Path(__file__).parent.parent

BIN_DIR = BASE_DIR / "bin"
STATIC_DIR = BASE_DIR / "static"

# Downloads go to user's Downloads folder (not app folder)
# This way files persist after app closes and users can find them
DOWNLOADS_DIR = Path.home() / "Downloads" / "FlyKrewDownloader"

# Platform-aware ffmpeg path
if platform.system() == "Windows":
    FFMPEG_PATH = BIN_DIR / "ffmpeg.exe"
else:  # macOS, Linux
    FFMPEG_PATH = BIN_DIR / "ffmpeg"

# Download settings
SLEEP_BETWEEN_TRACKS = 2
MAX_FILENAME_LENGTH = 200

# Server settings
HOST = "127.0.0.1"
PORT = 8000
```

### main.py Changes for V2

```python
import webbrowser
import threading

@app.on_event("startup")
def on_startup():
    """Run on server start."""
    # Cleanup old downloads
    cleanup_stale_downloads()
    
    # Auto-open browser (slight delay to ensure server is ready)
    def open_browser():
        import time
        time.sleep(1)
        webbrowser.open(f"http://{HOST}:{PORT}")
    
    threading.Thread(target=open_browser, daemon=True).start()
```

### PyInstaller Spec File (V2)

```python
# FlyKrewDownloader.spec
block_cipher = None

a = Analysis(
    ['app/main.py'],
    pathex=[],
    binaries=[
        ('bin/ffmpeg.exe', 'bin'),  # Windows
        # ('bin/ffmpeg', 'bin'),    # macOS - separate spec file
    ],
    datas=[
        ('static', 'static'),
    ],
    hiddenimports=[
        'uvicorn.logging',
        'uvicorn.protocols.http',
        'uvicorn.protocols.http.auto',
        'uvicorn.protocols.websockets',
        'uvicorn.protocols.websockets.auto',
        'uvicorn.lifespan',
        'uvicorn.lifespan.on',
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='FlyKrewDownloader',
    debug=False,
    strip=False,
    upx=True,
    console=False,  # No console window
    icon='static/icon.ico',  # Add app icon
)
```

### V2 Distribution

**GitHub Releases structure:**
```
Release v2.0.0
├── FlyKrewDownloader-Windows.exe     (direct download, ~90MB)
├── FlyKrewDownloader-macOS.zip       (contains .app bundle, ~90MB)
└── README.txt
```

**README.txt for friends:**
```
═══════════════════════════════════════════════════════
   SoundCloud Playlist Downloader
═══════════════════════════════════════════════════════

WINDOWS:
  1. Download FlyKrewDownloader-Windows.exe
  2. Double-click to run
  3. Your browser opens automatically
  4. Paste a SoundCloud playlist URL
  5. Click Download and wait
  6. Find your ZIP in: Downloads > FlyKrewDownloader

macOS:
  1. Download FlyKrewDownloader-macOS.zip
  2. Unzip it (double-click)
  3. Right-click the app → Open → "Open Anyway"
     (This is normal for apps not from the App Store)
  4. Your browser opens automatically
  5. Paste a SoundCloud playlist URL
  6. Click Download and wait
  7. Find your ZIP in: Downloads > FlyKrewDownloader

TO CLOSE:
  - Windows: Right-click the tray icon or close the terminal
  - macOS: Cmd+Q or close from Dock
```

### V2 Roadmap

| Phase | Tasks | Time |
|-------|-------|------|
| **2a** | Platform-aware config.py (frozen detection, ffmpeg path) | 1-2 hours |
| **2b** | Auto-open browser on startup | 30 min |
| **2c** | Move downloads to user's Downloads folder | 30 min |
| **2d** | PyInstaller Windows build + testing | 3-4 hours |
| **2e** | Get macOS ffmpeg binary, test on friend's MacBook | 2-3 hours |
| **2f** | PyInstaller macOS build + Gatekeeper testing | 3-4 hours |
| **2g** | Create GitHub release with both builds | 1 hour |
| **2h** | Write friend-friendly README | 30 min |

**Total: ~1-2 weekends**

### V1 Decisions That Are V1-Only

| Decision | V1 Reason | V2 Change |
|----------|-----------|-----------|
| `ffmpeg.exe` hardcoded | Windows-only dev | Platform detection |
| Downloads in project folder | Dev convenience | User's Downloads folder |
| Manual `python -m app.main` | Developer workflow | Double-click exe |
| Manual browser open | Developer knows URL | Auto-open |
| No Gatekeeper docs | Windows only | Add macOS instructions |
| No app icon | Not user-facing | Add icon for recognition |

### V1 Decisions That Carry Forward (No Change Needed)

| Decision | Why It's Already V2-Ready |
|----------|---------------------------|
| yt-dlp as pip library | Bundles automatically |
| FastAPI + uvicorn | Standard, bundles cleanly |
| In-memory job storage | Still fine for single user |
| 2-second rate limiting | Universal requirement |
| ZIP output format | Works everywhere |
| Localhost-only server | Security, unchanged |
| `/api/` route structure | Clean, no changes needed |

### Known V2 Limitations

| Limitation | Mitigation |
|------------|------------|
| ~90MB download size | Acceptable for desktop app |
| 3-5 second startup (PyInstaller extraction) | Show splash or "Starting..." message |
| macOS Gatekeeper warning | Clear documentation with screenshots |
| Can't auto-update yt-dlp | Users re-download new version if SoundCloud breaks |
| No crash reporting | Add simple error logging to file |

---

## Implementation Order

1. **Phase 1: Core (MVP)**
   - [ ] `config.py` - Constants
   - [ ] `downloader.py` - yt-dlp wrapper
   - [ ] `zipper.py` - ZIP creation
   - [ ] `main.py` - FastAPI app (endpoints only, no UI)
   - [ ] Test with curl/Postman

2. **Phase 2: UI**
   - [ ] `index.html` - Basic form
   - [ ] `style.css` - Styling
   - [ ] JavaScript polling logic
   - [ ] End-to-end test in browser

3. **Phase 3: Polish**
   - [ ] `setup_bins.py` - Binary downloader
   - [ ] Error handling improvements
   - [ ] README documentation
   - [ ] `.gitignore`

---

## Contact

Technical owner: [Your Name]
Created: February 2026

---

## Post V1 Build Edits

This section tracks small, post-implementation adjustments made after the initial V1 spec was written.
Use it as a lightweight changelog so new tweaks don’t require rewriting earlier sections.

### Edits (February 2026)

1. **Accept SoundCloud shortlinks**
    - **Why:** Users commonly paste `https://on.soundcloud.com/...` links.
    - **UI:** Client-side URL validation accepts `on.soundcloud.com/...` and `soundcloud.com/<user>/sets/<playlist>`.
    - **API:** `POST /api/download` resolves `on.soundcloud.com/...` redirects to the final URL before validating it as a playlist URL.

2. **Cancel button in UI**
    - **Why:** Allows stopping long playlist downloads without closing the server.
    - **UI:** Provides a Cancel action during download.
    - **API:** Uses `DELETE /api/job/{job_id}` to request cancellation (stop after current track, then produce partial ZIP).

3. **Auto-download ZIP when ready**
    - **Why:** Removes one extra click at the end.
    - **UI:** When status reaches `complete` or `cancelled` and `zip_ready=true`, the browser download starts automatically and a success message is shown.
4. **Rebrand UI**
   - **Why:** Custom branding and visual flair.
   - **UI:** Title changed to "FLY KREW DOWNLOADER" (all caps), subtitle changed to "Rip it baby 🪩".
   - **UI:** Download button styled with transparent background, animated rainbow gradient border, and glowing effect.
   - **UI:** Changed from dark theme to light Apple-inspired aesthetic: opaque white card background (95% opacity) with rainbow gradient only on the edges.
   - **UI:** Header text centered with divider line below it.
   - **UI:** All text and UI elements adapted for light background: dark gray text (#1d1d1f), muted gray (#6e6e73), light backgrounds on inputs and sections.

5. **Enhanced download completion UX**
   - **Why:** More engaging and informative completion state.
   - **UI:** Success message shows centered checkmark icon (60px, white with rainbow edges) and text "LETS GET GROOVY BABY 🕺".
   - **UI:** Removed file size display from success area.
   - **UI:** Completed tracks list shows actual track titles instead of "Track 1, Track 2, etc."
   - **UI:** Failed column hidden by default (with proper IDs and hidden class); only appears when errors exist. Completed column centers when failed is hidden.
   - **UI:** Current track section automatically hides when status is zipping/complete/cancelled to avoid showing stale or confusing values.
   - **API:** Added `completed_tracks_info: list[str]` to Job dataclass and JobStatus response to track completed track titles.
   - **API:** Clear `current_track` when entering zipping phase.

6. **Fix: Completed tracks showing as "playlist"**
   - **Issue:** After implementing track titles in completed list, all tracks displayed as "✓ playlist" instead of actual track names. The `completed_tracks_info` array was populated with "playlist" entries.
   - **Root cause:** In `app/downloader.py`, the `TrackInfo` creation was using `track_result.get("title") or title`, but `track_result.get("title")` returned "playlist" for individual track downloads within playlists.
   - **Fix:** Reversed the priority to `title or track_result.get("title")` to prefer the original entry title from the playlist metadata.
   - **UI Fix:** Restructured HTML to move track-lists section outside the progress section, making it independent so it can be shown alongside either progress or success sections.
   - **UI Fix:** Updated visibility logic in `updateProgressUI()` to explicitly show track-lists when complete.

7. **Visual refinements**
   - **Why:** Fine-tune aesthetics and improve visual hierarchy.
   - **UI:** Reduced checkmark icon from 60px to 32px for better proportions.
   - **UI:** Changed page background from light grey/white gradient to darker grey gradient (`#2d3436` to `#1e272e`) while maintaining blur effect.
   - **UI:** White card on dark gradient creates better contrast and focus.
8. **Playful background animations**
   - **Why:** Make the DJ-focused tool more engaging and fun to use. Optimized for desktop with lighter experience on mobile.
   - **UI:** Animated "GROOVY" text with rainbow gradient, jiggle, and scale effect (0.6s infinite loop).
   - **UI:** Flying planes (  ) that cross screen horizontally or diagonally, dropping musical notes ( ) that fall and spin. Spawn every 10-20s (5-10s during active downloads).
   - **UI:** Glowing color orbs with 5 gradient variants that fade in, pulse/scale, and fade out over 3.6s. Spawn every 8-15s. Heavily blurred for soft glow.
   - **UI:** Cursor trail of musical notes (  ) that drift upward while fading. Throttled to 100ms for performance. Desktop only.
   - **UI:** Starfield particles - 50 tiny dots (30 on mobile) drifting slowly across background for subtle depth, like dust in club lights.
   - **UI:** Card pulse during downloads - subtle scale (1.0  1.02) and glow intensification on 0.8s loop when status is downloading/zipping. Removes when complete.
   - **Performance:** All animations GPU-accelerated via CSS transforms. Elements auto-remove after completion. Mobile: reduced frequency, smaller sizes, disabled cursor trail.
