# Verification Checklist (Run After Each Module)

This file lists the exact verification commands to run after each module is implemented, plus end-to-end checks once all modules are complete.

> Notes
> - Run commands from the repo root: `FlyKrewDownloader/`
> - Some checks require internet access (SoundCloud).
> - Some checks require `bin/ffmpeg.exe` (download/conversion).

---

## Global Prereqs (Once)

1. Install dependencies

   ```
   python -m pip install -r requirements.txt
   ```

2. Download ffmpeg (Windows)

   ```
   python setup_bins.py
   ```

3. Verify ffmpeg file exists

   ```
   python -c "from app.config import FFMPEG_PATH; import os; print(FFMPEG_PATH); print(os.path.exists(FFMPEG_PATH))"
   ```

   Expected: prints the ffmpeg path, then `True`.

---

## Module 1: `app/config.py`

Command:

```
python -c "from app.config import BASE_DIR, BIN_DIR, DOWNLOADS_DIR, STATIC_DIR, FFMPEG_PATH, HOST, PORT; print(BASE_DIR); print(BIN_DIR); print(DOWNLOADS_DIR); print(STATIC_DIR); print(FFMPEG_PATH); print(f'{HOST}:{PORT}')"
```

Expected:
- Paths print without errors.
- Host/port prints `127.0.0.1:8000`.

---

## Module 2: `app/downloader.py`

### Import + type sanity

Command:

```
python -c "from app.downloader import PlaylistDownloader, TrackInfo, DownloadResult, PlaylistInfo; print('ok')"
```

Expected: prints `ok`.

### Playlist metadata extraction (requires internet)

Command (replace URL with a real *public* SoundCloud playlist URL):

```
python -c "from app.downloader import PlaylistDownloader; from pathlib import Path; d=PlaylistDownloader(Path('downloads/_verify')); info=d.get_playlist_info('https://soundcloud.com/user/sets/playlist-name'); print(info.title); print(info.track_count); print(info.uploader); print(info.url)"
```

Expected:
- Prints non-empty `title`.
- `track_count` is an integer > 0.
- `uploader` is non-empty.
- `url` matches the input URL.

### Playlist download (requires internet + ffmpeg)

Command (replace URL with a real *public* playlist URL, ideally 3-5 tracks):

```
python -c "import asyncio; from app.downloader import PlaylistDownloader; from pathlib import Path; async def main():
    d=PlaylistDownloader(Path('downloads/_verify'))
    r=await d.download_playlist('https://soundcloud.com/user/sets/playlist-name')
    print(r.playlist_title)
    print(len(r.tracks))
    print(len(r.errors))
    for t in r.tracks: print(t.index, t.artist, t.title, t.duration, t.file_path)
asyncio.run(main())"
```

Expected:
- Creates MP3 files in `downloads/_verify`.
- `len(tracks) + len(errors) <= track_count`.
- Each `TrackInfo.file_path` exists on disk.

---

## Module 3: `app/zipper.py`

### Import

```
python -c "from app.zipper import create_playlist_zip, sanitize_filename, format_track_filename; print('ok')"
```

Expected: prints `ok`.

### Filename sanitization

```
python -c "from app.zipper import sanitize_filename; s=' Track <Test> ' + chr(34) + 'Quotes' + chr(34) + ' | Pipe. '; print(sanitize_filename(s))"
```

Expected:
- No invalid Windows filename characters remain: `< > : \" / \\ | ? *`.
- No leading/trailing spaces or dots.

### ZIP creation (requires some existing MP3s)

Prereq: download a small playlist first (Module 2 download check) to produce MP3s.

Command:

```
python -c "from pathlib import Path; from app.zipper import create_playlist_zip; from app.downloader import TrackInfo; 
tracks=[]
base=Path('downloads/_verify')
for i,p in enumerate(sorted(base.glob('*.mp3')), start=1):
    tracks.append(TrackInfo(index=i, title=p.stem, artist='', duration=0, file_path=p))
zip_path=create_playlist_zip(tracks, 'verify-playlist', Path('downloads/_verify'))
print(zip_path); print(zip_path.exists())"
```

Expected:
- ZIP file path prints.
- ZIP exists on disk.

---

## Module 4: `app/main.py` (API only; UI later)

### Start server

```
python -m app.main
```

Expected:
- Server listens on `http://127.0.0.1:8000`.

### Manual API smoke checks (once endpoints exist)

1. `GET /` in browser: `http://127.0.0.1:8000/`
2. `POST /api/download` with JSON body: `{ "url": "<playlist url>" }`
3. Poll `GET /api/status/{job_id}` until complete/error
4. Download ZIP: `GET /api/result/{job_id}`
5. Cancel: `DELETE /api/job/{job_id}`

Expected:
- Job progresses through statuses: pending -> downloading -> zipping -> complete (or error).
- ZIP download returns a file.

---

## End-to-End (After All Modules + UI)

1. Start server:

   ```
   python -m app.main
   ```

2. Open in browser:

   - `http://127.0.0.1:8000`

3. Paste a public playlist URL and click Download.

Expected:
- Progress UI updates every ~2 seconds.
- Completed tracks appear in completed list.
- Failed tracks (if any) appear in failed list with errors.
- Download button appears when job completes (and downloads the ZIP).
