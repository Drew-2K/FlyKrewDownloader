from __future__ import annotations

from io import BytesIO
from pathlib import Path
import re
import zipfile

from app.config import MAX_FILENAME_LENGTH
from app.downloader import TrackInfo


_INVALID_WINDOWS_CHARS = r'<>:"/\\|?*'
_INVALID_WINDOWS_RE = re.compile(f"[{re.escape(_INVALID_WINDOWS_CHARS)}]")


def sanitize_filename(name: str, max_length: int = 200) -> str:
	"""Remove/replace invalid Windows filename characters.

	Replaces: < > : " / \\ | ? *
	Strips leading/trailing spaces and dots.
	Truncates to max_length.
	"""

	cleaned = _INVALID_WINDOWS_RE.sub("_", name)
	cleaned = cleaned.strip(" .")
	if len(cleaned) > max_length:
		cleaned = cleaned[:max_length]
		cleaned = cleaned.strip(" .")
	return cleaned


def format_track_filename(track: TrackInfo) -> str:
	"""Format track as: '01 - Artist - Title.mp3'

	Falls back to '01 - Title.mp3' if artist is empty/unknown.
	"""

	index_str = f"{track.index:02d}"
	artist = (track.artist or "").strip()
	title = (track.title or "").strip()

	if not title:
		title = "Track"

	if not artist or artist.lower() == "unknown":
		base = f"{index_str} - {title}.mp3"
	else:
		base = f"{index_str} - {artist} - {title}.mp3"

	return sanitize_filename(base, max_length=MAX_FILENAME_LENGTH)


def create_playlist_zip(tracks: list[TrackInfo], playlist_title: str, output_path: Path) -> Path:
	"""Create a ZIP file containing all MP3s with numbered filenames.

	Args:
		tracks: List of TrackInfo with file paths
		playlist_title: Used for ZIP filename
		output_path: Directory to save the ZIP

	Returns:
		Path to the created ZIP file
	"""

	output_path.mkdir(parents=True, exist_ok=True)
	zip_name = sanitize_filename(playlist_title or "playlist", max_length=MAX_FILENAME_LENGTH)
	if not zip_name:
		zip_name = "playlist"
	zip_path = output_path / f"{zip_name}.zip"

	total_bytes = 0
	for t in tracks:
		try:
			total_bytes += t.file_path.stat().st_size
		except OSError:
			total_bytes += 0

	in_memory = total_bytes < 100 * 1024 * 1024

	used_names: dict[str, int] = {}

	def unique_zip_name(desired: str) -> str:
		count = used_names.get(desired, 0)
		if count == 0:
			used_names[desired] = 1
			return desired

		used_names[desired] = count + 1
		stem, suffix = Path(desired).stem, Path(desired).suffix
		candidate = f"{stem} ({count + 1}){suffix}"
		candidate = sanitize_filename(candidate, max_length=MAX_FILENAME_LENGTH)
		return candidate

	if in_memory:
		buffer = BytesIO()
		with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as zf:
			for track in tracks:
				arcname = unique_zip_name(format_track_filename(track))
				zf.write(track.file_path, arcname=arcname)

		zip_path.write_bytes(buffer.getvalue())
		return zip_path

	with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
		for track in tracks:
			arcname = unique_zip_name(format_track_filename(track))
			zf.write(track.file_path, arcname=arcname)

	return zip_path
