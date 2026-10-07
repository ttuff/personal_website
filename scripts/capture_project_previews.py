#!/usr/bin/env python3
"""Refresh optimized first-viewport screenshots for the Projects gallery."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "data" / "github-projects.yml"
CHROME_CANDIDATES = (
    Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
    Path("/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"),
)


def find_chrome(explicit: str | None) -> str:
    if explicit:
        return explicit
    for command in ("google-chrome", "chromium", "chromium-browser", "microsoft-edge"):
        resolved = shutil.which(command)
        if resolved:
            return resolved
    for candidate in CHROME_CANDIDATES:
        if candidate.exists():
            return str(candidate)
    raise SystemExit("Chrome or Chromium was not found; pass --chrome /path/to/browser")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--chrome", help="Chrome/Chromium executable")
    parser.add_argument("--project", action="append", help="Project id to capture; repeat as needed")
    args = parser.parse_args()

    chrome = find_chrome(args.chrome)
    cwebp = shutil.which("cwebp")
    if not cwebp:
        raise SystemExit("cwebp is required to create optimized WebP previews")

    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    selected = set(args.project or [])
    projects = [
        project
        for project in config["portfolio"]["projects"]
        if project.get("website") and project.get("screenshot") and (not selected or project["id"] in selected)
    ]
    missing = selected - {project["id"] for project in projects}
    if missing:
        raise SystemExit(f"Unknown or uncapturable project ids: {', '.join(sorted(missing))}")

    with tempfile.TemporaryDirectory(prefix="project-previews-") as temporary:
        temporary_path = Path(temporary)
        for project in projects:
            png = temporary_path / f"{project['id']}.png"
            target = ROOT / project["screenshot"]["src"].lstrip("/")
            target.parent.mkdir(parents=True, exist_ok=True)
            subprocess.run(
                [
                    chrome,
                    "--headless=new",
                    "--hide-scrollbars",
                    "--disable-gpu",
                    "--force-device-scale-factor=1",
                    "--window-size=1440,900",
                    f"--screenshot={png}",
                    project["website"]["url"],
                ],
                check=True,
            )
            subprocess.run(
                [cwebp, "-quiet", "-q", "78", "-resize", "1200", "750", str(png), "-o", str(target)],
                check=True,
            )
            print(f"Updated {target.relative_to(ROOT)} from {project['website']['url']}")


if __name__ == "__main__":
    main()
