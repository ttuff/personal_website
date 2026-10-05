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
CUSTOM_PAGES = {
    "github": {
        "title": "I Build in Public — Ty Tuff on GitHub",
        "description": "Explore the public GitHub work I’ve built, maintained, and contributed to, including my collaborations, project relationships, and evolving technical practice.",
    },
    "my-projects": {
        "title": "My Projects — Scientific Software and Research Infrastructure",
        "description": "Explore the scientific software, environmental data systems, research infrastructure, computational experiments, and agentic systems I build.",
    }
}
PRODUCTION_ORIGIN = "https://drtuff.com"
SOCIAL_IMAGE = "assets/images/10353027_10153056621894937_558955528339896458_n-fd9f57fd.jpg"
TYPEKIT_URL = "https://use.typekit.net/ik/Plzv6nh1Zm7kt6TtAz-0cecuDBs31OE5yPK8WPSNthGfe7jffFHN4UJLFRbh52jhWDmK52qDFDIojDJu5eJXZAIUF2qDFAFq5sTEHKoqSKuXpPuXiAZcO1FUiABkZWF3jAF8OcFzdPUqSKuXpPuXiAZcO1FUiABkZWF3jAF8OcFzdPUqS1suZcj0jhNlOeUzjhBC-eNDifUaiaS0ZYJliYqliYmcZKoDSWmyScmDSeBRZPoRdhXCiaiaOcskiYmcZKoRdhXK2YgkdayTdAIldcNhjPJ4Z1mXiW4yOWgXH6qJtKGbMg62JMJ7fbKzMsMMeMb6MKGHfO2IMsMMeM96MKG4fHXgIMMjgKMfH6qJK3IbMg6YJMJ7fbRRHyMMeMX6MKGHfOYIMsMMeMv6MKG4fJ3gIMMjIPMfH6qJ6m9bMs6YJMHbMjO6zNXB.js"


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
        "/github": prefix + "github/",
        "/my-projects": prefix + "my-projects/",
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

    # Replace Squarespace's map runtime with a plain, keyless map embed.
    def materialize_map(match: re.Match[str]) -> str:
        opening_tag = match.group(0)
        context_match = re.search(r'data-context="([^"]+)"', opening_tag, flags=re.I)
        if not context_match:
            return opening_tag
        try:
            context = json.loads(html.unescape(context_match.group(1)))
            location = context["location"]
            lat = location["mapLat"]
            lng = location["mapLng"]
            title = location.get("addressTitle", "Map")
        except (KeyError, TypeError, ValueError, json.JSONDecodeError):
            return opening_tag
        bbox = f"{lng - 0.01},{lat - 0.005},{lng + 0.01},{lat + 0.005}"
        query = urllib.parse.urlencode({"bbox": bbox, "layer": "mapnik", "marker": f"{lat},{lng}"})
        iframe = (
            f'<iframe class="static-map-embed" title="{html.escape(title, quote=True)} map" '
            f'src="https://www.openstreetmap.org/export/embed.html?{query}" loading="lazy" '
            'referrerpolicy="no-referrer-when-downgrade"></iframe>'
        )
        return opening_tag + iframe

    main = re.sub(
        r'<div\b(?=[^>]*data-context="[^"]*&quot;mapLat&quot;)[^>]*>',
        materialize_map,
        main,
        flags=re.I,
    )

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
        <a href="{prefix}my-projects/">My Projects</a>
        <a href="{prefix}github/">Connections</a>
        <a href="{prefix}my-cv/">My CV</a>
        <a href="{prefix}contact-me/">Contact me</a>
      </nav>
      <a class="site-title" href="{prefix}">Dr. Tuff</a>
      <nav class="social-nav" aria-label="Social links">
        <a class="social-link social-link--github" href="https://github.com/ttuff" aria-label="GitHub"><span aria-hidden="true">GH</span></a>
        <a class="social-link social-link--email" href="mailto:ty.tuff@colorado.edu" aria-label="Email"><span aria-hidden="true">@</span></a>
      </nav>
    </header>
    <nav id="mobile-navigation" class="mobile-navigation" aria-label="Mobile navigation">
      <a href="{prefix}my-science/">My Science</a>
      <a href="{prefix}my-projects/">My Projects</a>
      <a href="{prefix}github/">Connections</a>
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
          <div class="footer-social">
            <a href="https://www.researchgate.net/profile/Ty_Tuff"><img src="{prefix}assets/images/RG-logo-01-9d242ea8.png" alt=""><span>Researchgate</span></a>
            <a href="https://scholar.google.com/citations?user=jxAk620AAAAJ&amp;hl=en"><img src="{prefix}assets/images/GS_logo-01-d709fc22.png" alt=""><span>Google scholar</span></a>
          </div>
        </div>
        <div class="footer-links">
          <h2>Quick Links</h2>
          <a href="{prefix}">Home</a>
          <a href="{prefix}my-science/">My Science</a>
          <a href="{prefix}my-projects/">My Projects</a>
          <a href="{prefix}github/">Connections</a>
          <a href="{prefix}my-cv/">My CV</a>
          <a href="{prefix}contact-me/">Contact Me</a>
          <div class="footer-contact-social" aria-label="Contact links"><a href="https://github.com/ttuff" aria-label="GitHub">GH</a><a href="mailto:ty.tuff@colorado.edu" aria-label="Email">@</a></div>
        </div>
      </div>
      <div class="footer-bottom"><span>© Ty Tuff 2020. All Rights Reserved.</span><span>Site designed &amp; built by <a href="https://www.impactmedialab.com/">Impact Media Lab</a></span></div>
    </footer>"""


def page_document(slug: str, main: str, meta: dict[str, str]) -> str:
    prefix = "../" if slug != "root" else ""
    title = meta.get("og:title") or meta.get("title") or "Dr. Tuff"
    description = meta.get("description") or meta.get("og:description") or ""
    page_slug = "home" if slug == "root" else slug
    canonical_path = "/" if slug == "root" else f"/{slug}"
    canonical_url = f"{PRODUCTION_ORIGIN}{canonical_path}"
    social_image_url = f"{PRODUCTION_ORIGIN}/{SOCIAL_IMAGE}"
    structured_data = json.dumps(
        {
            "@context": "https://schema.org",
            "@type": "WebPage",
            "name": title,
            "description": description.strip(),
            "url": canonical_url,
            "isPartOf": {"@type": "WebSite", "name": "Dr. Tuff", "url": f"{PRODUCTION_ORIGIN}/"},
        },
        ensure_ascii=False,
        separators=(",", ":"),
    ).replace("</", "<\\/")
    page_assets = ""
    if slug == "github":
        page_assets = f'  <link rel="stylesheet" href="{prefix}styles/github.css">\n  <link rel="preload" href="{prefix}data/github-life.json" as="fetch" crossorigin="anonymous">\n  <script src="{prefix}scripts/github.js" defer></script>\n'
    elif slug == "my-projects":
        page_assets = f'  <link rel="stylesheet" href="{prefix}styles/projects.css">\n  <link rel="preload" href="{prefix}data/github-life.json" as="fetch" crossorigin="anonymous">\n  <script src="{prefix}scripts/projects.js" defer></script>\n'
    return f"""<!doctype html>
<html lang="en-US">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)}</title>
  <meta name="description" content="{html.escape(description, quote=True)}">
  <link rel="canonical" href="{canonical_url}">
  <meta property="og:site_name" content="Dr. Tuff">
  <meta property="og:title" content="{html.escape(title, quote=True)}">
  <meta property="og:type" content="website">
  <meta property="og:url" content="{canonical_url}">
  <meta property="og:description" content="{html.escape(description, quote=True)}">
  <meta property="og:image" content="{social_image_url}">
  <meta property="og:image:width" content="532">
  <meta property="og:image:height" content="569">
  <meta name="twitter:card" content="summary">
  <meta name="twitter:title" content="{html.escape(title, quote=True)}">
  <meta name="twitter:description" content="{html.escape(description, quote=True)}">
  <meta name="twitter:image" content="{social_image_url}">
  <link rel="icon" href="{prefix}assets/icons/favicon-e92ccdd0.ico">
  <link rel="stylesheet" href="{prefix}styles/site.css">
{page_assets}
  <script src="{TYPEKIT_URL}"></script>
  <script>try{{Typekit.load();}}catch(error){{document.documentElement.classList.add('typekit-unavailable');}}</script>
  <script src="{prefix}scripts/site.js" defer></script>
  <script type="application/ld+json">{structured_data}</script>
</head>
<body class="page-{page_slug}">
{navigation(prefix)}
{main}
{footer(prefix)}
</body>
</html>
"""


def redirect_document(destination: str, canonical: str) -> str:
    escaped_destination = html.escape(destination, quote=True)
    escaped_canonical = html.escape(canonical, quote=True)
    return f"""<!doctype html>
<html lang="en-US">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="robots" content="noindex">
  <meta http-equiv="refresh" content="0; url={escaped_destination}">
  <link rel="canonical" href="{escaped_canonical}">
  <title>Redirecting — Dr. Tuff</title>
</head>
<body><p>Redirecting to <a href="{escaped_destination}">{escaped_destination}</a>.</p></body>
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
        if slug == "my-science":
            science_projects_link = """
    <section class="Index-page science-projects-link" aria-labelledby="science-projects-title">
      <div class="Index-page-content">
        <div class="science-projects-link__inner">
          <p class="science-projects-link__kicker">Questions into systems</p>
          <h2 id="science-projects-title">See what I build from the science.</h2>
          <p>My projects turn environmental questions into computational methods, software, data systems, and shared research infrastructure.</p>
          <a class="sqs-block-button-element" href="../my-projects/">Explore my projects</a>
        </div>
      </div>
    </section>
"""
            rewritten = rewritten.replace('<nav class="Index-nav">', science_projects_link + '    <nav class="Index-nav">', 1)
        destination = DIST / slug
        destination.mkdir(parents=True, exist_ok=True)
        (destination / "index.html").write_text(page_document(slug, rewritten, metadata[slug]), encoding="utf-8")
        if slug == "home":
            root_main = rewrite_main(markup, "root", asset_map)
            (DIST / "index.html").write_text(page_document("root", root_main, metadata[slug]), encoding="utf-8")

    for slug, custom_meta in CUSTOM_PAGES.items():
        main = (ROOT / "pages" / f"{slug}.html").read_text(encoding="utf-8")
        destination = DIST / slug
        destination.mkdir(parents=True, exist_ok=True)
        (destination / "index.html").write_text(page_document(slug, main, custom_meta), encoding="utf-8")

    data_target = DIST / "data"
    data_target.mkdir(exist_ok=True)
    shutil.copy2(ROOT / "data" / "generated" / "github-life.json", data_target / "github-life.json")

    aliases = {
        "about": ("/#h-about-me", f"{PRODUCTION_ORIGIN}/"),
        "research": ("/my-science", f"{PRODUCTION_ORIGIN}/my-science"),
    }
    for alias, (destination, canonical) in aliases.items():
        target = DIST / alias
        target.mkdir(parents=True, exist_ok=True)
        (target / "index.html").write_text(redirect_document(destination, canonical), encoding="utf-8")

    sitemap_paths = ["/", *(f"/{slug}" for slug in PAGES), *(f"/{slug}" for slug in CUSTOM_PAGES)]
    sitemap = "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n<urlset xmlns=\"http://www.sitemaps.org/schemas/sitemap/0.9\">\n"
    sitemap += "".join(f"  <url><loc>{PRODUCTION_ORIGIN}{path}</loc></url>\n" for path in sitemap_paths)
    sitemap += "</urlset>\n"
    (DIST / "sitemap.xml").write_text(sitemap, encoding="utf-8")
    (DIST / "robots.txt").write_text(
        f"User-agent: *\nAllow: /\n\nSitemap: {PRODUCTION_ORIGIN}/sitemap.xml\n",
        encoding="utf-8",
    )
    shutil.copy2(ROOT / "CNAME", DIST / "CNAME")

    (DIST / ".nojekyll").write_text("", encoding="utf-8")


if __name__ == "__main__":
    main()
