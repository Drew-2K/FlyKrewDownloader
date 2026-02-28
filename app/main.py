from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
import re
import shutil
import urllib.request
import uuid
from typing import Literal

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.config import DOWNLOADS_DIR, FFMPEG_PATH, HOST, PORT, STATIC_DIR
from app.downloader import PlaylistDownloader
from app.zipper import create_playlist_zip


SOUNDCLOUD_PLAYLIST_PATTERN = r"https?://soundcloud\.com/[\w-]+/sets/[\w-]+"
SOUNDCLOUD_SHORTLINK_PATTERN = r"https?://on\.soundcloud\.com/[\w-]+"


def _resolve_soundcloud_url(url: str) -> str:
	if not url:
		return url
	if not re.match(SOUNDCLOUD_SHORTLINK_PATTERN, url):
		return url

	request = urllib.request.Request(
		url,
		headers={
			"User-Agent": "Mozilla/5.0",
			"Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
		},
	)
	with urllib.request.urlopen(request, timeout=15) as response:
		return response.geturl()


class DownloadRequest(BaseModel):
	url: str


class DownloadResponse(BaseModel):
	job_id: str
	playlist_title: str
	track_count: int


class JobStatus(BaseModel):
	job_id: str
	status: Literal["pending", "downloading", "zipping", "complete", "cancelled", "error"]
	playlist_title: str | None
	total_tracks: int
	completed_tracks: int
	completed_tracks_info: list[str]
	current_track: str | None
	errors: list[dict]
	zip_ready: bool


@dataclass
class Job:
	id: str
	url: str
	status: str = "pending"
	playlist_title: str | None = None
	total_tracks: int = 0
	completed_tracks: int = 0
	completed_tracks_info: list = field(default_factory=list)
	current_track: str | None = None
	errors: list = field(default_factory=list)
	zip_path: Path | None = None
	created_at: datetime = field(default_factory=datetime.now)
	cancel_requested: bool = False


jobs: dict[str, Job] = {}


# Updated whenever the user interacts with the app (downloads, status polls, heartbeat, etc.).
LAST_ACTIVITY: datetime = datetime.now()


def touch_activity() -> None:
	global LAST_ACTIVITY
	LAST_ACTIVITY = datetime.now()


def get_last_activity() -> datetime:
	return LAST_ACTIVITY


def has_active_jobs() -> bool:
	# Consider these as "active" work.
	active = {"pending", "downloading", "zipping"}
	return any(j.status in active for j in jobs.values())


app = FastAPI()


@app.get("/api/ping")
async def ping():
	"""Heartbeat endpoint used by the UI to keep the app alive while open."""
	touch_activity()
	return {"ok": True}


@app.on_event("startup")
def cleanup_stale_downloads():
	if DOWNLOADS_DIR.exists():
		shutil.rmtree(DOWNLOADS_DIR)
	DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)


async def cleanup_old_jobs():
	while True:
		await asyncio.sleep(600)
		cutoff = datetime.now() - timedelta(hours=1)
		for job_id, job in list(jobs.items()):
			if job.created_at < cutoff:
				shutil.rmtree(DOWNLOADS_DIR / job_id, ignore_errors=True)
				del jobs[job_id]


@app.on_event("startup")
async def start_cleanup_task():
	asyncio.create_task(cleanup_old_jobs())


app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
async def index():
	return FileResponse(STATIC_DIR / "index.html")


def _job_status_model(job: Job) -> JobStatus:
	zip_ready = bool(job.zip_path and job.zip_path.exists())
	return JobStatus(
		job_id=job.id,
		status=job.status,  # type: ignore
		playlist_title=job.playlist_title,
		total_tracks=job.total_tracks,
		completed_tracks=job.completed_tracks,
		completed_tracks_info=list(job.completed_tracks_info),
		current_track=job.current_track,
		errors=list(job.errors),
		zip_ready=zip_ready,
	)


@app.post("/api/download", response_model=DownloadResponse)
async def start_download(request: DownloadRequest, background_tasks: BackgroundTasks):
	url = (request.url or "").strip()

	if not (re.match(SOUNDCLOUD_PLAYLIST_PATTERN, url) or re.match(SOUNDCLOUD_SHORTLINK_PATTERN, url)):
		raise HTTPException(status_code=400, detail="Invalid SoundCloud playlist URL")

	if not FFMPEG_PATH.exists():
		raise HTTPException(
			status_code=500,
			detail="ffmpeg not found. Run 'python setup_bins.py' or install ffmpeg to your PATH.",
		)

	loop = asyncio.get_running_loop()
	try:
		url = await loop.run_in_executor(None, _resolve_soundcloud_url, url)
	except Exception:
		raise HTTPException(status_code=400, detail="Invalid SoundCloud playlist URL")

	if not re.match(SOUNDCLOUD_PLAYLIST_PATTERN, url or ""):
		raise HTTPException(status_code=400, detail="Invalid SoundCloud playlist URL")

	job_id = str(uuid.uuid4())
	touch_activity()
	job = Job(id=job_id, url=url)
	jobs[job_id] = job

	job_dir = DOWNLOADS_DIR / job_id
	job_dir.mkdir(parents=True, exist_ok=True)

	downloader = PlaylistDownloader(job_dir)

	try:
		info = await loop.run_in_executor(None, downloader.get_playlist_info, url)
	except Exception as e:
		msg = str(e)
		if "private" in msg.lower():
			raise HTTPException(status_code=404, detail="Playlist is private")
		raise HTTPException(status_code=404, detail="Playlist not found")

	job.playlist_title = info.title
	job.total_tracks = info.track_count

	background_tasks.add_task(process_download, job_id)

	return DownloadResponse(job_id=job_id, playlist_title=info.title, track_count=info.track_count)


async def process_download(job_id: str):
	job = jobs.get(job_id)
	if not job:
		return

	job_dir = DOWNLOADS_DIR / job_id
	job_dir.mkdir(parents=True, exist_ok=True)

	def progress_callback(current_track, total_tracks, track_info):
		touch_activity()
		job.current_track = current_track
		job.total_tracks = total_tracks
		if track_info is not None:
			job.completed_tracks += 1
			job.completed_tracks_info.append(track_info.title)

	downloader = PlaylistDownloader(job_dir, progress_callback=progress_callback)
	downloader._cancel_check = lambda: bool(job.cancel_requested)

	try:
		job.status = "downloading"
		result = await downloader.download_playlist(job.url)
		job.playlist_title = result.playlist_title or job.playlist_title
		job.errors = result.errors

		job.status = "zipping"
		touch_activity()
		job.current_track = None
		zip_path = create_playlist_zip(result.tracks, job.playlist_title or "playlist", job_dir)
		job.zip_path = zip_path
		touch_activity()

		if job.cancel_requested:
			job.status = "cancelled"
		else:
			job.status = "complete"
	except Exception as e:
		job.status = "error"
		job.errors.append({"index": 0, "title": "", "error": str(e)})


@app.get("/api/status/{job_id}", response_model=JobStatus)
async def get_status(job_id: str):
	job = jobs.get(job_id)
	if not job:
		raise HTTPException(status_code=404, detail="Job not found")
	return _job_status_model(job)


@app.get("/api/result/{job_id}")
async def get_result(job_id: str):
	job = jobs.get(job_id)
	if not job:
		raise HTTPException(status_code=404, detail="Job not found")
	if not job.zip_path or not job.zip_path.exists():
		raise HTTPException(status_code=404, detail="ZIP not ready")

	return FileResponse(
		path=job.zip_path,
		media_type="application/zip",
		filename=job.zip_path.name,
	)


@app.delete("/api/job/{job_id}")
async def cancel_job(job_id: str):
	job = jobs.get(job_id)
	if not job:
		raise HTTPException(status_code=404, detail="Job not found")

	job.cancel_requested = True
	return {"job_id": job_id, "status": "cancel_requested"}


if __name__ == "__main__":
	import uvicorn

	uvicorn.run("app.main:app", host=HOST, port=PORT)
