"""Test setup: stub yt_dlp when it isn't installed.

The unit tests only exercise pure helpers (naming, URL validation, endpoints)
and never actually call yt_dlp, but app.downloader imports it at module load.
Stubbing keeps the test deps light and lets the suite run anywhere.
"""
import sys
import types

if "yt_dlp" not in sys.modules:
	try:
		import yt_dlp  # noqa: F401
	except ImportError:
		sys.modules["yt_dlp"] = types.ModuleType("yt_dlp")
