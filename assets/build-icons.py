#!/usr/bin/env python3
"""
Source build for public/favicon.svg, public/favicon.ico and public/apple-touch-icon.png.

Not served: wrangler only publishes ./public, so this stays private to the repo.

Regenerate after editing:

    python3 assets/build-icons.py

Requires Pillow (`pip install Pillow`).

--- Why the numbers below are what they are -------------------------------

ARTWORK. The mark is the turtle-graphics cursor from the site header, copied
verbatim from the .brand-mark SVG in public/index.html: same four points,
same 1.6 stroke with round joins, same rounded tile. The constants below are
the only definition of it here -- the SVG text and the PNG rasterizer are
both generated from them, so the vector and the bitmaps cannot drift apart.
If the header mark changes, change MARK_POINTS here and re-run.

COLOR. The header draws a green arrowhead on the pale --brand-tint tile,
which works at 34 CSS px next to the wordmark. A favicon is 16 px against
browser chrome that is white in light mode and near-black in dark mode, and
#e2f7e6 disappears into the light one. So the tile takes the solid --brand
green and the arrowhead is knocked out in white: same silhouette, same two
brand colors, legible on either chrome. The same inversion is what makes the
iOS home-screen icon read as a tile rather than as a pale smudge.

SCALE. The stroked mark is 20.6 x 23.6 in the 40-unit tile, centered at
(20, 18.5) -- the round join puts half of the 1.6 stroke outside every
vertex. The header leaves generous air around it because it sits in a header
row next to the wordmark; an icon has to carry a whole tile alone, so
FAVICON_SCALE grows the mark to 74% of the tile height. APPLE_SCALE stops at
62%: iOS applies its own squircle mask, so the artwork stays inside roughly
the middle 80%.

CORNERS. favicon.svg keeps the header's rx=11 tile. apple-touch-icon.png is
deliberately square and full-bleed -- iOS rounds it itself, and pre-rounded
corners would leave transparent notches inside its mask.

RASTERIZING. Pillow has no vector renderer, so draw_icon() reproduces the
SVG by hand: the fill is the polygon, and the stroke is one butt-capped line
per edge plus a disc at each vertex, which is what stroke-linejoin="round"
means. It is drawn at SUPERSAMPLE x the target and reduced with LANCZOS, so
the 16 px icon gets real supersampling instead of a hinted rasterization.
assets/check-icons.py verifies the output against a browser's own rendering
of favicon.svg; run it if you touch anything in here.
"""

import sys
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
PUBLIC = ROOT / "public"

# --- The header mark, in its own 40x40 tile ------------------------------
MARK_POINTS = ((20, 7.5), (29.5, 29.5), (20, 24.5), (10.5, 29.5))
MARK_STROKE = 1.6
MARK_CENTER = (20, 18.5)   # center of the stroked bounding box, see SCALE note
TILE = 40
TILE_RADIUS = 11           # rx on the header's tile

BRAND = "#1fae5a"          # --brand
MARK = "#ffffff"

FAVICON_SCALE = 1.25       # -> 74% of tile height
APPLE_SCALE = 1.05         # -> 62%, inside the iOS mask's safe area

ICO_SIZES = (16, 32, 48)
APPLE_PX = 180
SUPERSAMPLE = 16


def placed_points(scale: float) -> list[tuple[float, float]]:
    """The mark's points, scaled about its own center, still in tile units."""
    cx, cy = MARK_CENTER
    half = TILE / 2
    return [(half + (x - cx) * scale, half + (y - cy) * scale)
            for x, y in MARK_POINTS]


def icon_svg(radius: float, scale: float) -> str:
    cx, cy = MARK_CENTER
    d = " ".join(f"{'ML'[i > 0]}{x:g} {y:g}" for i, (x, y) in enumerate(MARK_POINTS)) + " Z"
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {TILE} {TILE}">\n'
        f'  <rect width="{TILE}" height="{TILE}" rx="{radius:g}" fill="{BRAND}"/>\n'
        "  <!-- turtle-graphics cursor: an arrowhead pointing along its heading -->\n"
        f'  <g transform="translate({TILE / 2:g} {TILE / 2:g}) scale({scale:g}) '
        f'translate({-cx:g} {-cy:g})">\n'
        f'    <path d="{d}" fill="{MARK}" stroke="{MARK}" '
        f'stroke-width="{MARK_STROKE:g}" stroke-linejoin="round"/>\n'
        "  </g>\n"
        "</svg>\n"
    )


def draw_icon(size: int, radius: float, scale: float) -> Image.Image:
    """Rasterize the same icon icon_svg() describes, supersampled to `size` px."""
    n = size * SUPERSAMPLE
    unit = n / TILE
    img = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle((0, 0, n - 1, n - 1), radius=radius * unit, fill=BRAND)

    pts = [(x * unit, y * unit) for x, y in placed_points(scale)]
    stroke = MARK_STROKE * scale * unit
    draw.polygon(pts, fill=MARK)
    for i, (x, y) in enumerate(pts):
        draw.line((x, y, *pts[(i + 1) % len(pts)]), fill=MARK, width=round(stroke))
        r = stroke / 2                                   # the round join
        draw.ellipse((x - r, y - r, x + r, y + r), fill=MARK)

    return img.resize((size, size), Image.LANCZOS)


def main() -> int:
    if not PUBLIC.is_dir():
        sys.exit(f"missing: {PUBLIC}")

    svg_path = PUBLIC / "favicon.svg"
    svg_path.write_text(icon_svg(TILE_RADIUS, FAVICON_SCALE))

    ico_path = PUBLIC / "favicon.ico"
    frames = [draw_icon(px, TILE_RADIUS, FAVICON_SCALE) for px in ICO_SIZES]
    frames[-1].save(ico_path, "ICO", sizes=[(px, px) for px in ICO_SIZES],
                    append_images=frames[:-1])

    apple_path = PUBLIC / "apple-touch-icon.png"
    apple = draw_icon(APPLE_PX, 0, APPLE_SCALE)
    # iOS ignores the alpha channel; flatten so it can never composite black.
    Image.alpha_composite(Image.new("RGBA", apple.size, BRAND), apple) \
        .convert("RGB").save(apple_path, "PNG", optimize=True)

    for path in (svg_path, ico_path, apple_path):
        print(f"{path.name:22} {path.stat().st_size / 1024:5.1f} KB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
