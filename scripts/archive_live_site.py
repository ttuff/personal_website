#!/usr/bin/env python3
"""Archive and inventory the public drtuff.com Squarespace site.

The script works from the raw HTML saved in migration/source/pages. With
--download it also retrieves one original/high-resolution copy of each
first-party asset referenced by those pages and the sitemap.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
import mimetypes
import re
import subprocess
import urllib.parse
import urllib.request
from collections import defaultdict
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "migration" / "source"
PAGES = SOURCE / "pages"
ASSETS = ROOT / "assets"
PAGE_ORDER = ["home", "my-science", "my-skills", "my-cv", "news", "contact-me"]
PUBLIC_URLS = {slug: f"https://www.drtuff.com/{slug}" for slug in PAGE_ORDER}
PUBLIC_URLS["home"] = "https://www.drtuff.com/home"

FIRST_PARTY_HOSTS = {
    "images.squarespace-cdn.com",
    "static1.squarespace.com",
    "file.squarespace-cdn.com",
}

DOC_EXTENSIONS = {".pdf", ".doc", ".docx", ".rtf", ".txt", ".zip"}
MEDIA_EXTENSIONS = {".mp4", ".webm", ".mov", ".mp3", ".m4a", ".wav"}
ICON_EXTENSIONS = {".ico", ".svg"}


def clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(value)).strip()


def normalize_url(value: str, base: str) -> str:
    value = html.unescape(value.strip()).replace("\\/", "/")
    if value.startswith("//"):
        value = "https:" + value
    value = urllib.parse.urljoin(base, value)
    parsed = urllib.parse.urlsplit(value)
    if parsed.hostname in {"images.squarespace-cdn.com", "static1.squarespace.com"}:
        # Queryless URLs return the original asset instead of a Squarespace resize.
        value = urllib.parse.urlunsplit(("https", parsed.netloc, parsed.path, "", ""))
    return value


class PageParser(HTMLParser):
    def __init__(self, base_url: str) -> None:
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self.title = ""
        self._title_parts: list[str] = []
        self.meta: dict[str, str] = {}
        self.headings: list[dict[str, str]] = []
        self.links: list[dict[str, str]] = []
        self.images: list[dict[str, str]] = []
        self.embeds: list[dict[str, str]] = []
        self.sections: list[dict[str, str]] = []
        self.text_blocks: list[dict[str, str]] = []
        self._stack: list[tuple[str, dict[str, str]]] = []
        self._capture: list[tuple[str, list[str], dict[str, str]]] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs_list: list[tuple[str, str | None]]) -> None:
        attrs = {k: v or "" for k, v in attrs_list}
        self._stack.append((tag, attrs))
        if tag in {"script", "style", "svg", "noscript", "template"}:
            self._skip_depth += 1
        if tag == "title":
            self._capture.append((tag, [], attrs))
        elif tag in {"h1", "h2", "h3", "h4", "h5", "h6", "p", "li", "figcaption"}:
            self._capture.append((tag, [], attrs))
        elif tag == "a":
            self._capture.append((tag, [], attrs))
        if tag == "meta":
            key = attrs.get("name") or attrs.get("property") or attrs.get("itemprop")
            if key and attrs.get("content"):
                self.meta[key] = attrs["content"]
        if tag == "section":
            self.sections.append(
                {
                    "id": attrs.get("id", ""),
                    "classes": attrs.get("class", ""),
                    "collection_id": attrs.get("data-collection-id", ""),
                }
            )
        if tag == "img":
            raw = attrs.get("data-image") or attrs.get("data-src") or attrs.get("src")
            if raw and not raw.startswith("data:"):
                self.images.append(
                    {
                        "url": normalize_url(raw, self.base_url),
                        "alt": attrs.get("alt", ""),
                        "title": attrs.get("title", ""),
                        "dimensions": attrs.get("data-image-dimensions", "")
                        or "x".join(filter(None, [attrs.get("width", ""), attrs.get("height", "")])),
                        "classes": attrs.get("class", ""),
                    }
                )
        for attr in ("data-config-url", "src"):
            raw = attrs.get(attr, "")
            if tag in {"iframe", "video", "source"} or attr == "data-config-url":
                if raw and ("vimeo" in raw or "youtube" in raw or tag in {"video", "source"}):
                    self.embeds.append({"type": tag, "url": normalize_url(raw, self.base_url)})

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        for _, parts, _ in self._capture:
            parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "svg", "noscript", "template"} and self._skip_depth:
            self._skip_depth -= 1
        if self._capture and self._capture[-1][0] == tag:
            captured_tag, parts, attrs = self._capture.pop()
            text = clean_text("".join(parts))
            if captured_tag == "title":
                self.title = text
            elif captured_tag.startswith("h") and captured_tag[1:].isdigit() and text:
                self.headings.append({"level": captured_tag, "text": text})
            elif captured_tag in {"p", "li", "figcaption"} and text:
                self.text_blocks.append({"type": captured_tag, "text": text})
            elif captured_tag == "a":
                href = attrs.get("href", "")
                if href:
                    self.links.append({"text": text, "url": normalize_url(href, self.base_url)})
        if self._stack:
            self._stack.pop()


def extract_raw_urls(markup: str, base_url: str) -> set[str]:
    candidates = set(re.findall(r"https?:\\?/\\?/[^\"'<>\s]+|//[^\"'<>\s]+", markup))
    urls: set[str] = set()
    for candidate in candidates:
        candidate = candidate.rstrip(")],;\\").replace("&quot;", "")
        try:
            urls.add(normalize_url(candidate, base_url))
        except ValueError:
            continue
    return urls


def asset_destination(url: str, content_type: str = "") -> Path:
    parsed = urllib.parse.urlsplit(url)
    raw_name = urllib.parse.unquote(Path(parsed.path).name) or "asset"
    raw_name = re.sub(r"[^A-Za-z0-9._-]+", "-", raw_name).strip("-.") or "asset"
    suffix = Path(raw_name).suffix.lower()
    if not suffix:
        guessed = mimetypes.guess_extension(content_type.split(";", 1)[0].strip()) or ""
        suffix = ".jpg" if guessed == ".jpe" else guessed
        raw_name += suffix
    if suffix in DOC_EXTENSIONS:
        directory = ASSETS / "documents"
    elif suffix in MEDIA_EXTENSIONS:
        directory = ASSETS / "media"
    elif suffix in ICON_EXTENSIONS or "favicon" in raw_name.lower():
        directory = ASSETS / "icons"
    elif suffix in {".woff", ".woff2", ".ttf", ".otf"}:
        directory = ASSETS / "fonts"
    else:
        directory = ASSETS / "images"
    digest = hashlib.sha1(url.encode("utf-8")).hexdigest()[:8]
    return directory / f"{Path(raw_name).stem}-{digest}{suffix}"


def image_dimensions(path: Path) -> str:
    if path.suffix.lower() not in {".jpg", ".jpeg", ".png", ".gif", ".webp", ".tif", ".tiff", ".ico"}:
        return ""
    try:
        result = subprocess.run(
            ["sips", "-g", "pixelWidth", "-g", "pixelHeight", str(path)],
            check=True,
            capture_output=True,
            text=True,
        )
        width = re.search(r"pixelWidth: (\d+)", result.stdout)
        height = re.search(r"pixelHeight: (\d+)", result.stdout)
        return f"{width.group(1)}x{height.group(1)}" if width and height else ""
    except (subprocess.CalledProcessError, FileNotFoundError):
        return ""


def download_asset(url: str) -> tuple[Path | None, str, str]:
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 drtuff.com migration archive"})
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            content_type = response.headers.get_content_type()
            data = response.read()
    except Exception as exc:  # Preserve failures in the manifest instead of dropping them.
        return None, "", str(exc)
    destination = asset_destination(url, content_type)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(data)
    return destination, content_type, ""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--download", action="store_true", help="download first-party assets")
    args = parser.parse_args()

    inventory: dict[str, object] = {
        "source": "https://www.drtuff.com",
        "captured_from": "Squarespace public HTML and sitemap",
        "navigation": [
            {"position": 1, "label": "My Science", "url": "/my-science"},
            {"position": 2, "label": "My CV", "url": "/my-cv"},
            {"position": 3, "label": "Contact me", "url": "/contact-me"},
        ],
        "pages": [],
    }
    asset_sources: dict[str, set[str]] = defaultdict(set)
    asset_notes: dict[str, set[str]] = defaultdict(set)

    for position, slug in enumerate(PAGE_ORDER, start=1):
        page_path = PAGES / f"{slug}.html"
        markup = page_path.read_text(encoding="utf-8", errors="replace")
        page_url = PUBLIC_URLS[slug]
        parsed = PageParser(page_url)
        parsed.feed(markup)
        page = {
            "url": page_url,
            "slug": slug,
            "title": parsed.title,
            "navigation_position": position if slug in {"my-science", "my-cv", "contact-me"} else None,
            "page_hierarchy": ["site", slug],
            "headings": parsed.headings,
            "textual_content": parsed.text_blocks,
            "images": parsed.images,
            "image_captions": [x for x in parsed.text_blocks if x["type"] == "figcaption"],
            "links": parsed.links,
            "downloadable_files": [
                link for link in parsed.links if Path(urllib.parse.urlsplit(link["url"]).path).suffix.lower() in DOC_EXTENSIONS
            ],
            "galleries": [section for section in parsed.sections if "gallery" in section["classes"].lower()],
            "embedded_content": parsed.embeds,
            "layout_structure": parsed.sections,
            "relevant_css_classes": sorted(
                {token for section in parsed.sections for token in section["classes"].split()}
            ),
            "metadata": parsed.meta,
            "archived_html": str(page_path.relative_to(ROOT)),
        }
        inventory["pages"].append(page)

        for image in parsed.images:
            url = image["url"]
            if urllib.parse.urlsplit(url).hostname in FIRST_PARTY_HOSTS:
                asset_sources[url].add(page_url)
                if image.get("alt"):
                    asset_notes[url].add(f"alt: {image['alt']}")
                if image.get("dimensions"):
                    asset_notes[url].add(f"declared: {image['dimensions']}")
        for url in extract_raw_urls(markup, page_url):
            parsed_url = urllib.parse.urlsplit(url)
            suffix = Path(parsed_url.path).suffix.lower()
            if parsed_url.hostname in FIRST_PARTY_HOSTS and parsed_url.path not in {"", "/"} and (
                parsed_url.hostname == "images.squarespace-cdn.com"
                or suffix in DOC_EXTENSIONS | MEDIA_EXTENSIONS | ICON_EXTENSIONS | {".woff", ".woff2", ".ttf", ".otf"}
            ):
                asset_sources[url].add(page_url)

    sitemap_markup = (SOURCE / "sitemap.xml").read_text(encoding="utf-8", errors="replace")
    for raw in re.findall(r"<image:loc>(.*?)</image:loc>", sitemap_markup):
        url = normalize_url(raw, "https://www.drtuff.com")
        asset_sources[url].add("sitemap.xml")

    (ROOT / "migration" / "site_inventory.json").write_text(
        json.dumps(inventory, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    md = [
        "# drtuff.com site inventory",
        "",
        "Source of truth: `https://www.drtuff.com` (Squarespace). Raw captures are preserved under `migration/source/`.",
        "",
        "## Navigation",
        "",
        "1. My Science (`/my-science`)",
        "2. My CV (`/my-cv`)",
        "3. Contact me (`/contact-me`)",
        "",
        "The public sitemap also exposes `/home`, `/my-skills`, and `/news`; the site root resolves to the Home index.",
        "",
        "## Pages",
        "",
    ]
    for page in inventory["pages"]:
        md.extend(
            [
                f"### {page['slug']}",
                "",
                f"- URL: {page['url']}",
                f"- Title: {page['title']}",
                f"- Sections: {len(page['layout_structure'])}",
                f"- Images: {len(page['images'])}",
                f"- Links: {len(page['links'])}",
                f"- Embeds: {len(page['embedded_content'])}",
                f"- Archived HTML: `{page['archived_html']}`",
                "- Headings:",
            ]
        )
        for heading in page["headings"]:
            md.append(f"  - {heading['level']}: {heading['text']}")
        md.append("")
    md.extend(
        [
            "## Notes",
            "",
            "- Page-level text, links, images, metadata, sections, and embed URLs are recorded in `site_inventory.json`.",
            "- Vimeo and YouTube media remain third-party embeds; their URLs are inventoried rather than downloaded.",
            "- The archived HTML retains Squarespace implementation classes for forensic comparison only.",
            "",
        ]
    )
    (ROOT / "migration" / "site_inventory.md").write_text("\n".join(md), encoding="utf-8")

    manifest_rows = []
    for url in sorted(asset_sources):
        local_path = None
        media_type = ""
        error = "not downloaded (run with --download)"
        if args.download:
            local_path, media_type, error = download_asset(url)
        dimensions = image_dimensions(local_path) if local_path else ""
        manifest_rows.append(
            {
                "local_path": str(local_path.relative_to(ROOT)) if local_path else "",
                "original_url": url,
                "source_page": " | ".join(sorted(asset_sources[url])),
                "original_filename": urllib.parse.unquote(Path(urllib.parse.urlsplit(url).path).name),
                "media_type": media_type or mimetypes.guess_type(url)[0] or "",
                "dimensions": dimensions,
                "file_size": local_path.stat().st_size if local_path else "",
                "notes": "; ".join(sorted(asset_notes[url]) + ([f"download error: {error}"] if error else [])),
            }
        )
    with (ROOT / "migration" / "asset_manifest.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "local_path",
                "original_url",
                "source_page",
                "original_filename",
                "media_type",
                "dimensions",
                "file_size",
                "notes",
            ],
        )
        writer.writeheader()
        writer.writerows(manifest_rows)


if __name__ == "__main__":
    main()
