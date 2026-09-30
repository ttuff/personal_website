#!/usr/bin/env python3
"""Validate the generated static site before GitHub Pages deployment."""

from __future__ import annotations

import re
import subprocess
import sys
import urllib.parse
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"
SQUARESPACE = ("squarespace.com", "squarespace-cdn.com", "static1.squarespace.com")


class ReferenceParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.references: list[tuple[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {key: value or "" for key, value in attrs}
        if tag in {"a", "link"} and values.get("href"):
            if not (tag == "link" and values.get("rel") == "canonical"):
                self.references.append(("href", values["href"]))
        if tag in {"img", "script", "iframe", "source", "video"} and values.get("src"):
            self.references.append(("src", values["src"]))


def local_target(page: Path, reference: str) -> Path | None:
    parsed = urllib.parse.urlsplit(reference)
    if parsed.scheme or reference.startswith(("//", "mailto:", "tel:", "#", "data:")):
        return None
    target = (page.parent / urllib.parse.unquote(parsed.path)).resolve()
    try:
        target.relative_to(SITE.resolve())
    except ValueError:
        return Path("OUTSIDE_SITE")
    if target.is_dir():
        target = target / "index.html"
    return target


def main() -> None:
    subprocess.run([sys.executable, str(ROOT / "scripts" / "build_static_site.py")], check=True)
    failures: list[str] = []
    html_files = sorted(SITE.rglob("*.html"))
    for page in html_files:
        markup = page.read_text(encoding="utf-8")
        parser = ReferenceParser()
        try:
            parser.feed(markup)
            parser.close()
        except Exception as exc:
            failures.append(f"malformed HTML in {page.relative_to(ROOT)}: {exc}")
        for attr, reference in parser.references:
            target = local_target(page, reference)
            if target is not None and not target.exists():
                failures.append(
                    f"missing {attr} target in {page.relative_to(ROOT)}: {reference}"
                )
        lower = markup.lower()
        for hostname in SQUARESPACE:
            if hostname in lower:
                failures.append(f"Squarespace dependency in {page.relative_to(ROOT)}: {hostname}")

    css_and_js = list(SITE.rglob("*.css")) + list(SITE.rglob("*.js"))
    for path in css_and_js:
        content = path.read_text(encoding="utf-8")
        for hostname in SQUARESPACE:
            if hostname in content.lower():
                failures.append(f"Squarespace dependency in {path.relative_to(ROOT)}: {hostname}")
        for reference in re.findall(r"url\([\"']?([^\"')]+)", content):
            target = local_target(path, reference)
            if target is not None and not target.exists():
                failures.append(f"missing CSS asset in {path.relative_to(ROOT)}: {reference}")

    if failures:
        print("Validation failed:")
        print("\n".join(f"- {failure}" for failure in failures))
        raise SystemExit(1)
    print(f"Validated {len(html_files)} HTML files with no missing local assets, broken internal references, or Squarespace dependencies.")


if __name__ == "__main__":
    main()
