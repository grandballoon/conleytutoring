#!/usr/bin/env python3
"""
Check that the hand-rolled rasterizer in build-icons.py still agrees with a
real SVG renderer.

    python3 assets/check-icons.py

Pillow cannot render SVG, so build-icons.py draws the mark with polygons and
discs. That is only safe as long as it matches what a browser does with
public/favicon.svg, which is what actually ships to modern browsers. This
renders the served SVG in headless Chrome at 512 px and compares it against
draw_icon() at the same size. Run it after touching the geometry.

Requires Pillow and Google Chrome.
"""

import importlib.util
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from PIL import Image, ImageChops

ROOT = Path(__file__).resolve().parent.parent
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
SIZE = 512
MEAN_TOLERANCE = 1.0    # out of 255; edge antialiasing alone lands near 0.4


def load_builder():
    spec = importlib.util.spec_from_file_location(
        "build_icons", Path(__file__).with_name("build-icons.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def chrome_render(svg: Path, size: int, workdir: Path) -> Image.Image:
    shutil.copy(svg, workdir / "icon.svg")
    (workdir / "icon.html").write_text(
        "<!DOCTYPE html><meta charset=utf-8>"
        "<style>html,body{margin:0;padding:0;background:transparent}"
        f"img{{display:block;width:{size}px;height:{size}px}}</style>"
        '<img src="icon.svg">'
    )
    shot = workdir / "icon.png"
    proc = subprocess.Popen(
        [CHROME, "--headless", "--disable-gpu", "--hide-scrollbars",
         "--no-first-run", "--disable-background-networking",
         "--disable-component-update", "--force-device-scale-factor=1",
         "--default-background-color=00000000", f"--window-size={size},{size}",
         f"--user-data-dir={workdir / 'chrome'}", f"--screenshot={shot}",
         str(workdir / "icon.html")],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    # Chrome does not always exit after writing the screenshot (its updater
    # can keep the process alive), so wait on the file rather than on the
    # process, then stop it.
    try:
        deadline = time.time() + 60
        while time.time() < deadline:
            if shot.exists() and shot.stat().st_size > 0:
                time.sleep(0.3)     # let the write finish
                break
            time.sleep(0.2)
        else:
            sys.exit("chrome produced no screenshot")
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()

    with Image.open(shot) as raw:
        return raw.convert("RGBA")


def main() -> int:
    builder = load_builder()
    svg = ROOT / "public" / "favicon.svg"
    if not svg.exists():
        sys.exit(f"missing {svg}; run build-icons.py first")

    workdir = Path(tempfile.mkdtemp(prefix="check-icons-"))
    try:
        reference = chrome_render(svg, SIZE, workdir)
    finally:
        shutil.rmtree(workdir, ignore_errors=True)

    ours = builder.draw_icon(SIZE, builder.TILE_RADIUS, builder.FAVICON_SCALE)
    diff = ImageChops.difference(reference, ours).convert("L")
    hist = diff.histogram()
    pixels = SIZE * SIZE
    mean = sum(i * c for i, c in enumerate(hist)) / pixels
    edgey = sum(c for i, c in enumerate(hist) if i > 32) * 100 / pixels

    print(f"mean abs diff {mean:.3f}/255 (tolerance {MEAN_TOLERANCE}), "
          f"{edgey:.2f}% of pixels differ by more than 32")
    if mean > MEAN_TOLERANCE:
        sys.exit("rasterizer has drifted from favicon.svg")
    print("ok: the PNGs match a browser's rendering of favicon.svg")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
