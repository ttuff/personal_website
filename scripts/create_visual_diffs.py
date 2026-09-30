#!/usr/bin/env python3
"""Create side-by-side, overlay, and amplified-difference audit images.

Usage:
    python3 scripts/create_visual_diffs.py migration/screenshots/final

Pillow is only needed for this optional visual-audit helper; it is not a site
runtime or build dependency.
"""

from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageChops, ImageEnhance, ImageOps


ROOT = Path(__file__).resolve().parents[1]
PAGES = ("home", "my-science", "my-skills", "my-cv", "news", "contact-me")
VIEWPORTS = ("1440x1000", "1280x900", "768x1024", "390x844")


def padded(image: Image.Image, size: tuple[int, int]) -> Image.Image:
    canvas = Image.new("RGB", size, "white")
    canvas.paste(image.convert("RGB"), (0, 0))
    return canvas


def main() -> None:
    source = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "migration" / "screenshots" / "final"
    if not source.is_absolute():
        source = ROOT / source
    output = source.parent / "comparisons"
    output.mkdir(parents=True, exist_ok=True)
    created = 0

    for page in PAGES:
        for viewport in VIEWPORTS:
            for capture in ("viewport", "full"):
                live_path = source / f"{page}-{viewport}-live-{capture}.png"
                local_path = source / f"{page}-{viewport}-local-{capture}.png"
                if not live_path.exists() or not local_path.exists():
                    continue
                live = Image.open(live_path).convert("RGB")
                local = Image.open(local_path).convert("RGB")
                width = max(live.width, local.width)
                height = max(live.height, local.height)
                live = padded(live, (width, height))
                local = padded(local, (width, height))

                side_by_side = Image.new("RGB", (width * 2, height), "white")
                side_by_side.paste(live, (0, 0))
                side_by_side.paste(local, (width, 0))
                side_by_side.save(output / f"{page}-{viewport}-{capture}-side-by-side.jpg", quality=88)

                Image.blend(live, local, 0.5).save(
                    output / f"{page}-{viewport}-{capture}-overlay.jpg", quality=88
                )
                difference = ImageChops.difference(live, local)
                difference = ImageEnhance.Contrast(ImageOps.autocontrast(difference)).enhance(1.8)
                difference.save(output / f"{page}-{viewport}-{capture}-diff.jpg", quality=90)
                created += 3

    print(f"Created {created} comparison images in {output}")


if __name__ == "__main__":
    main()
