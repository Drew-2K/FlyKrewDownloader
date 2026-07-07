"""Smoke tests for the HTTP API and URL validation."""
import pytest
from fastapi.testclient import TestClient

from app.main import _is_supported_url, app

client = TestClient(app)


@pytest.mark.parametrize(
	"url",
	[
		"https://soundcloud.com/artist/some-track",
		"https://soundcloud.com/artist/sets/my-playlist",
		"https://on.soundcloud.com/abc123",
		"https://youtu.be/abc123",
		"https://www.youtube.com/watch?v=abc123",
		"https://music.youtube.com/watch?v=abc123",
		"https://m.youtube.com/watch?v=abc123",
	],
)
def test_supported_urls(url):
	assert _is_supported_url(url) is True


@pytest.mark.parametrize("url", ["", "notaurl", "https://example.com/song", "ftp://soundcloud.com/x"])
def test_unsupported_urls(url):
	assert _is_supported_url(url) is False


def test_features_endpoint():
	body = client.get("/api/features").json()
	# Every advertised flag must be a boolean the UI can rely on.
	for key in ("multi_url_queue", "number_tracks_toggle", "animations_toggle", "redownload_button"):
		assert isinstance(body[key], bool)


def test_index_served():
	r = client.get("/")
	assert r.status_code == 200
	assert "FLY KREW" in r.text


def test_download_rejects_bad_url():
	r = client.post("/api/download", json={"url": "notaurl"})
	assert r.status_code == 400
