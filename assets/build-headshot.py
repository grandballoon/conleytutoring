#!/usr/bin/env python3
"""
Source build for public/headshot.webp and public/headshot.jpg (the About-card avatar).

Not served: wrangler only publishes ./public, so this and headshot-source.jpg
stay private to the repo.

Regenerate after editing:

    python3 assets/build-headshot.py

Requires Pillow and cwebp (`pip install Pillow`, `brew install webp`).

--- Why the numbers below are what they are -------------------------------

CROP. The avatar used to be a 1200x1600 portrait positioned by CSS with
`background-size: 100%; background-position: 50% 30%` inside a square box.
That means the browser scaled the image to the box width W, giving a rendered
height of (4/3)W, and offset it vertically by 0.30 * (W - (4/3)W) = -0.1W.
So the visible band ran from 0.1W to 1.1W of a (4/3)W-tall image -- i.e. from
7.5% to 82.5% of the source height, or pixels y=120..1320. Exactly 1200 tall.

Baking that 1200x1200 square in means the browser downloads no pixels it will
never paint, and it renders identically to the old CSS crop. To re-frame the
photo, change CROP_TOP here and re-run; don't reintroduce a CSS pan, or the
served file goes back to carrying invisible rows.

SIZE. The avatar's widest rendered size is ~355 CSS px (the .8fr column of a
1080px `--maxw` grid, less the card's 1.75rem padding and 1px border). The
`max-width` on `.avatar` in index.html holds the single-column layout to the
same ceiling, so 700px is a true 2x everywhere. Raising one without the other
wastes bytes or softens the image.

QUALITY. q74 is visually transparent against the original at 1:1 -- which is
already 2x the size this is ever painted at. The photo has a busy Brooklyn
street background, so it costs more bits than a studio headshot would; that,
not the quality setting, is why this lands nearer 70 KB than 50 KB.
"""

import os
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "assets" / "headshot-source.jpg"
PUBLIC = ROOT / "public"

CROP_TOP = 120      # see CROP note above
CROP_SIZE = 1200
OUTPUT_PX = 700     # 2x the ~355 CSS px ceiling
QUALITY = 74


def circle_flatten(img: Image.Image) -> Image.Image:
    """Replace the corners outside the border-radius circle with a blurred copy.

    `.avatar` is clipped to a circle, so ~21% of a square image is never
    painted. Encoding that region as blurred rather than as sharp foliage
    costs far fewer bits and cannot change what a visitor sees. The blur is
    used instead of a flat fill because a hard edge at the circle boundary is
    itself expensive to encode.
    """
    n = img.width
    mask = Image.new("L", (n, n), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, n - 1, n - 1), fill=255)
    out = img.filter(ImageFilter.GaussianBlur(n // 12))
    out.paste(img, (0, 0), mask)
    return out


def main() -> int:
    if not SOURCE.exists():
        sys.exit(f"missing source: {SOURCE}")

    src = Image.open(SOURCE).convert("RGB")
    square = src.crop((0, CROP_TOP, CROP_SIZE, CROP_TOP + CROP_SIZE))
    avatar = circle_flatten(square.resize((OUTPUT_PX, OUTPUT_PX), Image.LANCZOS))

    jpg = PUBLIC / "headshot.jpg"
    avatar.save(jpg, "JPEG", quality=QUALITY, optimize=True,
                progressive=True, subsampling="4:2:0")

    # cwebp reads a lossless intermediate so it is not re-encoding JPEG noise.
    webp = PUBLIC / "headshot.webp"
    tmp = PUBLIC / "_headshot-tmp.png"
    avatar.save(tmp)
    try:
        subprocess.run(
            ["cwebp", "-quiet", "-q", str(QUALITY), "-m", "6", "-sharp_yuv",
             str(tmp), "-o", str(webp)],
            check=True,
        )
    finally:
        tmp.unlink(missing_ok=True)

    before = SOURCE.stat().st_size
    for path in (webp, jpg):
        size = path.stat().st_size
        print(f"{path.name:16} {size / 1024:6.1f} KB  "
              f"({100 - size * 100 / before:.1f}% under the {before / 1024:.0f} KB source)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
