#!/usr/bin/env python3
"""Build the dependency-free static reproduction from the preserved archive."""

from __future__ import annotations

import csv
import html
import json
import re
import shutil
import urllib.parse
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "migration" / "source" / "pages"
DIST = ROOT / "site"
PAGES = ["home", "my-science", "my-skills", "my-cv", "news", "contact-me"]


def normalize_remote(url: str) -> str:
    value = html.unescape(url).replace("\\/", "/")
    if value.startswith("//"):
        value = "https:" + value
    parsed = urllib.parse.urlsplit(value)
    if parsed.hostname in {"images.squarespace-cdn.com", "static1.squarespace.com"}:
        return urllib.parse.urlunsplit(("https", parsed.netloc, parsed.path, "", ""))
    return value


def load_asset_map() -> dict[str, str]:
    mapping: dict[str, str] = {}
    with (ROOT / "migration" / "asset_manifest.csv").open(encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if not row["local_path"]:
                continue
            mapping[normalize_remote(row["original_url"])] = row["local_path"]
    return mapping


def relative_target(slug: str, target: str) -> str:
    prefix = "../" if slug != "root" else ""
    routes = {
        "/": prefix,
        "/home": prefix + "home/",
        "/my-science": prefix + "my-science/",
        "/my-skills": prefix + "my-skills/",
        "/my-cv": prefix + "my-cv/",
        "/news": prefix + "news/",
        "/contact-me": prefix + "contact-me/",
    }
    for route in sorted(routes, key=len, reverse=True):
        if target == route or target.startswith(route + "#"):
            return routes[route] + target[len(route) :]
    return target


def rewrite_main(markup: str, slug: str, asset_map: dict[str, str]) -> str:
    match = re.search(r"<main\b[^>]*>.*?</main>", markup, flags=re.I | re.S)
    if not match:
        raise RuntimeError(f"No main element found for {slug}")
    main = match.group(0)
    main = re.sub(r"<script\b.*?</script>", "", main, flags=re.I | re.S)
    main = re.sub(r"<style\b.*?</style>", "", main, flags=re.I | re.S)
    main = re.sub(r"<noscript\b.*?</noscript>", "", main, flags=re.I | re.S)
    main = re.sub(r"<use\b[^>]*>\s*</use>|<use\b[^>]*/?>", "", main, flags=re.I)

    # Materialize lazy images before removing Squarespace runtime attributes.
    def materialize_img(match: re.Match[str]) -> str:
        tag = match.group(0)
        remote_match = re.search(r'(?:data-image|data-src|src)=["\']([^"\']+)', tag, flags=re.I)
        if remote_match:
            remote = normalize_remote(remote_match.group(1))
            local = asset_map.get(remote)
            if local:
                prefix = "../" if slug != "root" else ""
                src = prefix + local
                if re.search(r'\ssrc=["\']', tag, flags=re.I):
                    tag = re.sub(r'\ssrc=["\'][^"\']*["\']', f' src="{src}"', tag, count=1, flags=re.I)
                else:
                    tag = tag[:-1] + f' src="{src}">'
        tag = re.sub(r'\ssrcset=["\'][^"\']*["\']', "", tag, flags=re.I)
        tag = re.sub(r'\ssizes=["\'][^"\']*["\']', "", tag, flags=re.I)
        tag = re.sub(r'\sonload=["\'][^"\']*["\']', "", tag, flags=re.I)
        return tag

    main = re.sub(r"<img\b[^>]*>", materialize_img, main, flags=re.I)

    # Convert Squarespace's encoded video configuration into ordinary embeds.
    def materialize_video(match: re.Match[str]) -> str:
        opening_tag = match.group(0)
        data = re.search(r'data-html="([^"]+)"', opening_tag, flags=re.I)
        if not data:
            return opening_tag
        iframe = html.unescape(data.group(1)).replace("&amp;", "&")
        iframe = re.sub(r"<iframe\b", '<iframe loading="lazy"', iframe, count=1, flags=re.I)
        return opening_tag + iframe

    main = re.sub(
        r'<div\b(?=[^>]*class="[^"]*sqs-video-wrapper[^"]*")(?=[^>]*data-html="[^"]+")[^>]*>',
        materialize_video,
        main,
        flags=re.I,
    )

    prefix = "../" if slug != "root" else ""

    def remote_replacer(match: re.Match[str]) -> str:
        original = match.group(0)
        normalized = normalize_remote(original)
        local = asset_map.get(normalized)
        return prefix + local if local else original

    main = re.sub(r"https?://(?:images\.squarespace-cdn\.com|static1\.squarespace\.com)[^\"'<>\s]+", remote_replacer, main)

    def href_replacer(match: re.Match[str]) -> str:
        quote, target = match.group(1), html.unescape(match.group(2))
        if target.startswith("https://www.drtuff.com"):
            target = target.removeprefix("https://www.drtuff.com") or "/"
        target = relative_target(slug, target)
        return f"href={quote}{target}{quote}"

    main = re.sub(r'href=(["\'])([^"\']+)\1', href_replacer, main, flags=re.I)
    main = re.sub(r"\sdata-controller(?:-[\w-]+)?=[\"'][^\"']*[\"']", "", main)
    main = re.sub(r"\sdata-block-(?:css|scripts)=[\"'][^\"']*[\"']", "", main)
    return main


def navigation(prefix: str) -> str:
    return f"""
    <div class="mobile-bar">
      <a class="mobile-brand" href="{prefix}">Dr. Tuff</a>
      <button class="mobile-toggle" type="button" aria-expanded="false" aria-controls="mobile-navigation" aria-label="Open navigation menu"><span></span><span></span></button>
    </div>
    <header class="site-header">
      <nav class="primary-nav" aria-label="Primary navigation">
        <a href="{prefix}my-science/">My Science</a>
        <a href="{prefix}my-cv/">My CV</a>
        <a href="{prefix}contact-me/">Contact me</a>
      </nav>
      <a class="site-title" href="{prefix}">Dr. Tuff</a>
      <nav class="social-nav" aria-label="Social links">
        <a href="https://github.com/ttuff" aria-label="GitHub">GH</a>
        <a href="mailto:ty.tuff@colorado.edu" aria-label="Email">@</a>
      </nav>
    </header>
    <nav id="mobile-navigation" class="mobile-navigation" aria-label="Mobile navigation">
      <a href="{prefix}my-science/">My Science</a>
      <a href="{prefix}my-cv/">My CV</a>
      <a href="{prefix}contact-me/">Contact me</a>
    </nav>"""


def footer(prefix: str) -> str:
    return f"""
    <footer class="site-footer">
      <div class="footer-inner">
        <div class="footer-about">
          <img src="{prefix}assets/images/Ty_logo_WHITE-ea311454.png" alt="Ty Tuff">
          <p>Principle Data Scientist at the NSF’s ESIIL synthesis center for Biology and Computer Science</p>
          <p class="footer-social"><a href="https://www.researchgate.net/profile/Ty_Tuff">Researchgate</a> · <a href="https://scholar.google.com/citations?user=jxAk620AAAAJ&amp;hl=en">Google scholar</a></p>
        </div>
        <div class="footer-links">
          <h2>Quick Links</h2>
          <a href="{prefix}">Home</a>
          <a href="{prefix}my-science/">My Science</a>
          <a href="{prefix}my-cv/">My CV</a>
          <a href="{prefix}contact-me/">Contact Me</a>
        </div>
      </div>
      <div class="footer-bottom"><span>© Ty Tuff 2020. All Rights Reserved.</span><span>Site designed &amp; built by <a href="https://www.impactmedialab.com/">Impact Media Lab</a></span></div>
    </footer>"""


def page_document(slug: str, main: str, meta: dict[str, str]) -> str:
    prefix = "../" if slug != "root" else ""
    title = meta.get("og:title") or meta.get("title") or "Dr. Tuff"
    description = meta.get("description") or meta.get("og:description") or ""
    canonical_slug = "home" if slug == "root" else slug
    return f"""<!doctype html>
<html lang="en-US">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)}</title>
  <meta name="description" content="{html.escape(description, quote=True)}">
  <link rel="canonical" href="https://www.drtuff.com/{canonical_slug}">
  <link rel="icon" href="{prefix}assets/icons/favicon-e92ccdd0.ico">
  <link rel="stylesheet" href="{prefix}styles/site.css">
  <script src="{prefix}scripts/site.js" defer></script>
</head>
<body class="page-{canonical_slug}">
{navigation(prefix)}
{main}
{footer(prefix)}
</body>
</html>
"""


def main() -> None:
    asset_map = load_asset_map()
    inventory = json.loads((ROOT / "migration" / "site_inventory.json").read_text(encoding="utf-8"))
    metadata = {page["slug"]: page["metadata"] for page in inventory["pages"]}
    DIST.mkdir(exist_ok=True)
    for directory in ["assets", "styles", "scripts"]:
        target = DIST / directory
        if target.exists():
            shutil.rmtree(target)
    shutil.copytree(ROOT / "assets", DIST / "assets")
    shutil.copytree(ROOT / "static" / "styles", DIST / "styles")
    shutil.copytree(ROOT / "static" / "scripts", DIST / "scripts")

    for slug in PAGES:
        markup = (SOURCE / f"{slug}.html").read_text(encoding="utf-8", errors="replace")
        rewritten = rewrite_main(markup, slug, asset_map)
        destination = DIST / slug
        destination.mkdir(parents=True, exist_ok=True)
        (destination / "index.html").write_text(page_document(slug, rewritten, metadata[slug]), encoding="utf-8")
        if slug == "home":
            root_main = rewrite_main(markup, "root", asset_map)
            (DIST / "index.html").write_text(page_document("root", root_main, metadata[slug]), encoding="utf-8")

    (DIST / ".nojekyll").write_text("", encoding="utf-8")


if __name__ == "__main__":
    main()
