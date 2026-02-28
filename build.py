"""
Build a standalone distributable using PyInstaller.

Run from the repo root:
    python build.py

Produces:
    Windows: dist/FlyKrewDownloader.exe
    macOS:   dist/FlyKrewDownloader.dmg

Requirements:
    pip install pyinstaller
"""
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).parent
DIST = ROOT / "dist"
BUILD = ROOT / "build"
APP_NAME = "FlyKrewDownloader"
IS_WIN = platform.system() == "Windows"
IS_MAC = platform.system() == "Darwin"
IS_LINUX = platform.system() == "Linux"


def _make_plane_png(png_path: Path, size: int = 1024) -> None:
    """Create a simple plane icon PNG (original artwork) with transparency."""
    from PIL import Image, ImageDraw

    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Background: rounded square (white) for contrast on dark desktops.
    margin = int(size * 0.08)
    radius = int(size * 0.18)
    bg_box = [margin, margin, size - margin, size - margin]
    draw.rounded_rectangle(bg_box, radius=radius, fill=(255, 255, 255, 255))

    # Plane silhouette (stylized): polygon coordinates as fractions of size.
    def p(x: float, y: float) -> tuple[int, int]:
        return (int(x * size), int(y * size))

    plane = [
        p(0.18, 0.56),
        p(0.55, 0.48),
        p(0.62, 0.30),
        p(0.70, 0.30),
        p(0.66, 0.50),
        p(0.82, 0.58),
        p(0.82, 0.63),
        p(0.64, 0.57),
        p(0.58, 0.70),
        p(0.51, 0.70),
        p(0.56, 0.56),
        p(0.18, 0.62),
    ]
    draw.polygon(plane, fill=(20, 20, 20, 255))

    # Small window dot for character.
    w_r = max(2, int(size * 0.018))
    cx, cy = p(0.58, 0.45)
    draw.ellipse([cx - w_r, cy - w_r, cx + w_r, cy + w_r], fill=(255, 255, 255, 255))

    png_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(png_path, format="PNG")


def _make_ico_from_png(png_path: Path, ico_path: Path) -> None:
    from PIL import Image

    img = Image.open(png_path).convert("RGBA")
    sizes = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]
    ico_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(ico_path, format="ICO", sizes=sizes)


def _make_icns_from_png(png_path: Path, icns_path: Path) -> None:
    """Create an .icns using macOS iconutil (must run on macOS)."""
    iconset_dir = icns_path.with_suffix(".iconset")
    if iconset_dir.exists():
        shutil.rmtree(iconset_dir)
    iconset_dir.mkdir(parents=True, exist_ok=True)

    # Generate required iconset sizes
    from PIL import Image

    base = Image.open(png_path).convert("RGBA")

    def save(size: int, name: str) -> None:
        resized = base.resize((size, size), resample=Image.LANCZOS)
        resized.save(iconset_dir / name, format="PNG")

    save(16, "icon_16x16.png")
    save(32, "icon_16x16@2x.png")
    save(32, "icon_32x32.png")
    save(64, "icon_32x32@2x.png")
    save(128, "icon_128x128.png")
    save(256, "icon_128x128@2x.png")
    save(256, "icon_256x256.png")
    save(512, "icon_256x256@2x.png")
    save(512, "icon_512x512.png")
    save(1024, "icon_512x512@2x.png")

    if icns_path.exists():
        icns_path.unlink()

    subprocess.check_call(["iconutil", "-c", "icns", str(iconset_dir), "-o", str(icns_path)])
    shutil.rmtree(iconset_dir, ignore_errors=True)


def ensure_app_icon() -> Path | None:
    """Create and return the correct icon file path for the current OS."""
    try:
        png_path = BUILD / "icon" / "plane.png"
        if not png_path.exists():
            _make_plane_png(png_path, size=1024)

        if IS_WIN:
            ico_path = BUILD / "icon" / "app.ico"
            if not ico_path.exists():
                _make_ico_from_png(png_path, ico_path)
            return ico_path

        if IS_MAC:
            icns_path = BUILD / "icon" / "app.icns"
            if not icns_path.exists():
                _make_icns_from_png(png_path, icns_path)
            return icns_path

        return None
    except Exception as e:
        print(f"WARNING: Could not generate app icon: {e}")
        return None


def find_ffmpeg() -> Path | None:
    """Locate the ffmpeg binary that should be bundled."""
    binary_name = "ffmpeg.exe" if IS_WIN else "ffmpeg"
    bundled = ROOT / "bin" / binary_name
    if bundled.exists():
        return bundled

    system = shutil.which("ffmpeg")
    if system:
        return Path(system)

    return None


def run_pyinstaller() -> None:
    ffmpeg = find_ffmpeg()
    if not ffmpeg:
        print("ERROR: ffmpeg not found.")
        print("Run 'python setup_bins.py' first or install ffmpeg.")
        sys.exit(1)

    # Determine platform-specific ffmpeg dest inside the bundle
    ffmpeg_dest = "bin"  # will be placed at <bundle>/bin/ffmpeg[.exe]

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--clean",
        # Windows ships a single .exe; macOS ships a .app bundle
        ("--onefile" if IS_WIN else "--onedir"),
        "--name", APP_NAME,
        # Bundle static files
        "--add-data", f"{ROOT / 'static'}{os.pathsep}static",
        # Bundle ffmpeg binary
        "--add-data", f"{ffmpeg}{os.pathsep}{ffmpeg_dest}",
        # Hidden imports that PyInstaller may miss
        "--hidden-import", "uvicorn.logging",
        "--hidden-import", "uvicorn.loops",
        "--hidden-import", "uvicorn.loops.auto",
        "--hidden-import", "uvicorn.protocols",
        "--hidden-import", "uvicorn.protocols.http",
        "--hidden-import", "uvicorn.protocols.http.auto",
        "--hidden-import", "uvicorn.protocols.websockets",
        "--hidden-import", "uvicorn.protocols.websockets.auto",
        "--hidden-import", "uvicorn.lifespan",
        "--hidden-import", "uvicorn.lifespan.on",
        "--hidden-import", "uvicorn.lifespan.off",
        "--hidden-import", "app",
        "--hidden-import", "app.main",
        "--hidden-import", "app.config",
        "--hidden-import", "app.downloader",
        "--hidden-import", "app.zipper",
        # Collect all yt-dlp extractors (they're loaded dynamically)
        "--collect-all", "yt_dlp",
    ]

    icon_path = ensure_app_icon()
    if icon_path:
        cmd.extend(["--icon", str(icon_path)])

    # Windowless mode: no terminal window, browser IS the UI.
    # - Windows: --noconsole prevents a console window
    # - macOS: --windowed produces a proper .app bundle runnable via Finder
    if IS_WIN:
        cmd.append("--noconsole")
    elif IS_MAC:
        cmd.append("--windowed")

    # Entry point
    cmd.append(str(ROOT / "launcher.py"))

    print(f"Running PyInstaller ({platform.system()})...")
    print(f"  ffmpeg: {ffmpeg}")
    print(f"  Command: {' '.join(cmd)}\n")

    subprocess.check_call(cmd)


def create_release_asset() -> Path:
    """Create the single-file artifact we upload to GitHub Releases."""
    if IS_WIN:
        exe = DIST / f"{APP_NAME}.exe"
        if not exe.exists():
            print(f"ERROR: {exe} does not exist. Build failed?")
            sys.exit(1)
        # For Windows, the PyInstaller output already is the intended shareable file.
        return exe

    if IS_MAC:
        app = DIST / f"{APP_NAME}.app"
        if not app.exists():
            print(f"ERROR: {app} does not exist. Build failed?")
            sys.exit(1)
        dmg = DIST / f"{APP_NAME}.dmg"
        if dmg.exists():
            dmg.unlink()
        # Create a simple DMG containing the .app bundle (no unzip required)
        subprocess.check_call(
            [
                "hdiutil",
                "create",
                "-volname",
                "Fly Krew Downloader",
                "-srcfolder",
                str(app),
                "-ov",
                "-format",
                "UDZO",
                str(dmg),
            ]
        )
        return dmg

    # Linux (or other): fall back to a ZIP folder like before
    dist_folder = DIST / APP_NAME
    if not dist_folder.exists():
        print(f"ERROR: {dist_folder} does not exist. Build failed?")
        sys.exit(1)
    zip_name = f"{APP_NAME}-Linux.zip"
    zip_path = DIST / zip_name
    if zip_path.exists():
        zip_path.unlink()
    shutil.make_archive(str(zip_path.with_suffix("")), "zip", root_dir=DIST, base_dir=APP_NAME)
    return zip_path


def main() -> None:
    print("=" * 50)
    print(f"  Building {APP_NAME}")
    print(f"  Platform: {platform.system()} {platform.machine()}")
    print("=" * 50)
    print()

    # Clean previous builds
    for d in (BUILD, DIST):
        if d.exists():
            shutil.rmtree(d)

    # Ensure build dirs exist early (for icon generation, etc.)
    BUILD.mkdir(parents=True, exist_ok=True)

    run_pyinstaller()
    asset_path = create_release_asset()

    print()
    print("=" * 50)
    print("  BUILD COMPLETE")
    if IS_WIN:
        print(f"  EXE:    {asset_path.name}")
    elif IS_MAC:
        print(f"  DMG:    {asset_path.name}")
    else:
        print(f"  ZIP:    {asset_path.name}")
    print()
    if IS_MAC:
        print(f"  To test: open dist/{APP_NAME}.app")
    else:
        print(f"  To test: run dist/{APP_NAME}" + (".exe" if IS_WIN else ""))
    print("  To share: upload the single file in dist/ to your friends!")
    print("=" * 50)


if __name__ == "__main__":
    main()
