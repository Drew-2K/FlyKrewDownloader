from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import yt_dlp

from app.config import FFMPEG_PATH, SLEEP_BETWEEN_TRACKS


@dataclass
class TrackInfo:
	index: int
	title: str
	artist: str
	duration: int
	file_path: Path


@dataclass
class DownloadResult:
	playlist_title: str
	tracks: list[TrackInfo]
	errors: list[dict]


@dataclass
class PlaylistInfo:
	title: str
	track_count: int
	uploader: str
	url: str


class PlaylistDownloader:
	"""Downloads SoundCloud playlists using yt-dlp."""

	def __init__(self, output_dir: Path, progress_callback: Callable = None):
		"""Initialize the downloader.

		Args:
			output_dir: Directory to save downloaded MP3s
			progress_callback: Optional callback(current_track, total_tracks, track_info)
		"""

		self.output_dir = output_dir
		self.progress_callback = progress_callback
		self._executor = ThreadPoolExecutor(max_workers=1)
		self._cancel_check: Callable[[], bool] | None = None

	def _base_ydl_opts(self) -> dict:
		return {
			"quiet": True,
			"no_warnings": True,
		}

	def _download_ydl_opts(self) -> dict:
		ydl_opts = {
			"format": "bestaudio/best",
			"postprocessors": [
				{
					"key": "FFmpegExtractAudio",
					"preferredcodec": "mp3",
					"preferredquality": "192",
				},
				{
					"key": "FFmpegMetadata",
					"add_metadata": True,
				},
				{
					"key": "EmbedThumbnail",
				},
			],
			"writethumbnail": True,
			"ffmpeg_location": str(FFMPEG_PATH.parent),
			"outtmpl": str(self.output_dir / "%(title)s.%(ext)s"),
			"ignoreerrors": True,
			"quiet": True,
			"no_warnings": True,
		}

		def progress_hook(d):
			if d.get("status") == "finished":
				return
			if d.get("status") == "downloading":
				return

		ydl_opts["progress_hooks"] = [progress_hook]
		return ydl_opts

	def get_playlist_info(self, url: str) -> PlaylistInfo:
		"""Extract playlist metadata without downloading.

		Args:
			url: SoundCloud playlist URL

		Returns:
			PlaylistInfo with title, track count, etc.
		"""

		ydl_opts = self._base_ydl_opts()
		with yt_dlp.YoutubeDL(ydl_opts) as ydl:
			info = ydl.extract_info(url, download=False)

		entries = info.get("entries") or []
		track_count = sum(1 for e in entries if e)

		return PlaylistInfo(
			title=info.get("title") or "",
			track_count=track_count,
			uploader=info.get("uploader") or "",
			url=url,
		)

	async def download_playlist(self, url: str) -> DownloadResult:
		"""Download all tracks from a SoundCloud playlist.

		Args:
			url: SoundCloud playlist URL

		Returns:
			DownloadResult with list of downloaded files and any errors
		"""

		if not FFMPEG_PATH.exists():
			raise FileNotFoundError(
				f"ffmpeg not found. Expected at: {FFMPEG_PATH}\n"
				"Run 'python setup_bins.py' or install ffmpeg and add it to your PATH."
			)

		self.output_dir.mkdir(parents=True, exist_ok=True)
		loop = asyncio.get_running_loop()

		def extract_playlist_sync() -> dict:
			ydl_opts = self._base_ydl_opts()
			with yt_dlp.YoutubeDL(ydl_opts) as ydl:
				return ydl.extract_info(url, download=False)

		playlist_info = await loop.run_in_executor(self._executor, extract_playlist_sync)
		playlist_title = playlist_info.get("title") or ""
		entries = playlist_info.get("entries") or []
		total_tracks = sum(1 for e in entries if e)

		tracks: list[TrackInfo] = []
		errors: list[dict] = []

		cancel_after_current = False

		for fallback_index, entry in enumerate(entries, start=1):
			if self._cancel_check and self._cancel_check():
				break
			if not entry:
				continue

			playlist_index = entry.get("playlist_index") or fallback_index
			title = entry.get("title") or ""
			artist = entry.get("uploader") or entry.get("artist") or ""
			duration = entry.get("duration") or 0

			track_url = entry.get("url") or entry.get("webpage_url")
			if not track_url:
				errors.append(
					{
						"index": playlist_index,
						"title": title,
						"error": "Missing track URL in playlist entry",
					}
				)
				await asyncio.sleep(SLEEP_BETWEEN_TRACKS)
				continue

			if self.progress_callback:
				self.progress_callback(title, total_tracks, None)

			def download_track_sync() -> dict:
				ydl_opts = self._download_ydl_opts()
				with yt_dlp.YoutubeDL(ydl_opts) as ydl:
					return ydl.extract_info(track_url, download=True)

			try:
				track_result = await loop.run_in_executor(self._executor, download_track_sync)
				file_path = None

				requested = track_result.get("requested_downloads")
				if requested and isinstance(requested, list):
					for item in requested:
						candidate = item.get("filepath")
						if candidate:
							file_path = candidate

				if not file_path:
					file_path = track_result.get("filepath") or track_result.get("_filename")

				if not file_path:
					raise RuntimeError("Could not determine downloaded file path")

				mp3_path = Path(file_path)
				if mp3_path.suffix.lower() != ".mp3":
					candidate_mp3 = mp3_path.with_suffix(".mp3")
					if candidate_mp3.exists():
						mp3_path = candidate_mp3

				track_info = TrackInfo(
					index=int(playlist_index),
					title=title or track_result.get("title"),
					artist=artist or track_result.get("uploader"),
					duration=int(duration or track_result.get("duration") or 0),
					file_path=mp3_path,
				)
				tracks.append(track_info)

				if self.progress_callback:
					self.progress_callback(track_info.title, total_tracks, track_info)
			except Exception as e:
				errors.append(
					{
						"index": int(playlist_index),
						"title": title,
						"error": str(e),
					}
				)
			finally:
				if self._cancel_check and self._cancel_check():
					cancel_after_current = True
				await asyncio.sleep(SLEEP_BETWEEN_TRACKS)

			if cancel_after_current:
				break

		return DownloadResult(playlist_title=playlist_title, tracks=tracks, errors=errors)
