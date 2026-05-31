"""Unit tests for filename parsing/formatting — the bits most likely to regress."""
from pathlib import Path

from app.downloader import TrackInfo, parse_artist_title
from app.zipper import format_track_filename


def _track(index, title, artist, filename):
	return TrackInfo(index=index, title=title, artist=artist, duration=0, file_path=Path(filename))


def test_parse_soundcloud_title_only_uses_uploader():
	artist, title = parse_artist_title({"title": "Late Night Drive", "uploader": "Anyma"})
	assert (artist, title) == ("Anyma", "Late Night Drive")


def test_parse_youtube_artist_title_split_avoids_channel_dup():
	artist, title = parse_artist_title(
		{"title": "Fred again.. - Delilah (Official)", "uploader": "Fred again.. - Topic"}
	)
	assert artist == "Fred again.."
	assert title == "Delilah (Official)"


def test_parse_prefers_explicit_metadata():
	artist, title = parse_artist_title(
		{"title": "whatever", "track": "Strobe", "artist": "deadmau5", "uploader": "channel"}
	)
	assert (artist, title) == ("deadmau5", "Strobe")


def test_format_basic_artist_title():
	assert format_track_filename(_track(1, "Bloom", "ODESZA", "x.mp3")) == "ODESZA - Bloom.mp3"


def test_format_numbered():
	out = format_track_filename(_track(1, "Bloom", "ODESZA", "x.mp3"), number=True)
	assert out == "01 - ODESZA - Bloom.mp3"


def test_format_avoids_artist_duplication():
	# Artist already contained in title -> don't prefix it again.
	out = format_track_filename(_track(1, "ODESZA - Bloom", "ODESZA", "x.mp3"))
	assert out == "ODESZA - Bloom.mp3"


def test_format_falls_back_to_file_stem_not_playlist():
	# No metadata at all: must use the per-track file stem, never a generic name.
	out = format_track_filename(_track(3, "", "", "some-soundcloud-slug.mp3"))
	assert out == "some-soundcloud-slug.mp3"


def test_format_never_empty():
	# Degenerate input still yields a usable, non-empty filename.
	out = format_track_filename(_track(7, "", "", ".mp3"))
	assert out.endswith(".mp3")
	assert out not in (".mp3", "")
