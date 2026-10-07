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
INDEXED_PAGES = ["my-science", "my-skills", "my-cv", "contact-me"]
CUSTOM_PAGES = {
    "github": {
        "title": "GitHub and Open-Source Work — Ty Tuff",
        "description": "Evidence of Ty Tuff’s sustained open-source development across scientific software, environmental data systems, cloud infrastructure, and collaborative research computing.",
    },
    "my-projects": {
        "title": "Projects — Scientific Software and Cloud Infrastructure",
        "description": "Explore the scientific software, cloud and research computing infrastructure, geospatial pipelines, and agentic workflows built and contributed to by Ty Tuff.",
    }
}
PAGE_METADATA_OVERRIDES = {
    "home": {
        "og:title": "Ty Tuff, PhD — Environmental Data Scientist",
        "description": "Environmental data scientist building scientific software, cloud and research computing infrastructure, and open-source methods for complex environmental systems.",
    },
    "my-science": {
        "description": "Learn about Dr. Ty Tuff’s research on relative motion, spatial ecology, evolution, computational methods, and ecological experiments.",
    },
    "my-skills": {
        "description": "Explore Dr. Ty Tuff’s work in environmental data science, spatial modeling, large-scale experiments, data visualization, teaching, and scientific communication.",
    },
    "my-cv": {
        "description": "Read Dr. Ty Tuff’s CV, including education, publications, grants, research and teaching positions, service, outreach, and presentations.",
    },
    "news": {
        "description": "News and updates from Dr. Ty Tuff.",
    },
    "contact-me": {
        "description": "Contact Dr. Ty Tuff to learn more about his environmental data science and ecology work or to develop a new collaboration.",
    },
}
PRODUCTION_ORIGIN = "https://drtuff.com"
GA_MEASUREMENT_ID = "G-XXXXXXXXXX"
GOOGLE_SITE_VERIFICATION = ""
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
        tag = re.sub(r"\s*/>$", ">", match.group(0))
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
        seen_alt = False

        def keep_first_alt(alt_match: re.Match[str]) -> str:
            nonlocal seen_alt
            if seen_alt:
                return ""
            seen_alt = True
            return alt_match.group(0)

        tag = re.sub(r'\salt=(?:"[^"]*"|\'[^\']*\')', keep_first_alt, tag, flags=re.I)
        if not seen_alt:
            tag = tag[:-1] + ' alt="">'
        tag = re.sub(r'\ssrcset=["\'][^"\']*["\']', "", tag, flags=re.I)
        tag = re.sub(r'\ssizes=["\'][^"\']*["\']', "", tag, flags=re.I)
        tag = re.sub(r'\sonload=["\'][^"\']*["\']', "", tag, flags=re.I)
        tag = re.sub(r'\selementtiming=["\'][^"\']*["\']', "", tag, flags=re.I)
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
        opening_tag = re.sub(r'\sdata-html="[^"]+"', "", opening_tag, flags=re.I)
        encoded_iframe = html.unescape(data.group(1)).replace("&amp;", "&")
        attributes = {
            key.lower(): value
            for key, value in re.findall(r'(src|title|width|height)="([^"]*)"', encoded_iframe, flags=re.I)
        }
        iframe = (
            f'<iframe loading="lazy" src="{html.escape(attributes.get("src", ""), quote=True)}" '
            f'width="{html.escape(attributes.get("width", "640"), quote=True)}" '
            f'height="{html.escape(attributes.get("height", "360"), quote=True)}" '
            f'title="{html.escape(attributes.get("title", "Embedded video"), quote=True)}" '
            'allow="fullscreen; picture-in-picture"></iframe>'
        )
        return opening_tag + iframe

    main = re.sub(
        r'<div\b(?=[^>]*class="[^"]*sqs-video-wrapper[^"]*")(?=[^>]*data-html="[^"]+")[^>]*>',
        materialize_video,
        main,
        flags=re.I,
    )

    def clean_video_container(match: re.Match[str]) -> str:
        opening_tag = re.sub(r'\srole=["\']button["\']', "", match.group(0), flags=re.I)
        return re.sub(r'\stabindex=["\'][^"\']*["\']', "", opening_tag, flags=re.I)

    main = re.sub(
        r'<div\b(?=[^>]*class="[^"]*video-lightbox-wrapper[^"]*")[^>]*>',
        clean_video_container,
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
    main = main.replace(
        "https://tuff.shinyapps.io/Ecology_Stats_intro_application/",
        "https://cuecologylab.shinyapps.io/Ecology_Stats_intro_application/",
    )
    main = re.sub(r"\sdata-controller(?:-[\w-]+)?=[\"'][^\"']*[\"']", "", main)
    main = re.sub(r"\sdata-block-(?:css|scripts)=[\"'][^\"']*[\"']", "", main)

    id_counts: dict[str, int] = {}

    def unique_id(match: re.Match[str]) -> str:
        quote, value = match.group(1), match.group(2)
        id_counts[value] = id_counts.get(value, 0) + 1
        suffix = "" if id_counts[value] == 1 else f"-{id_counts[value]}"
        return f" id={quote}{value}{suffix}{quote}"

    main = re.sub(r'\sid=(["\'])([^"\']+)\1', unique_id, main, flags=re.I)
    if slug == "news":
        main = main.replace(
            '<section class="Main-content" data-content-field="main-content">',
            '<section class="Main-content" data-content-field="main-content"><h1>News</h1>',
            1,
        )
    if slug == "root":
        identity = """
  <p class="home-identity__title">Ty Tuff, PhD <span>Environmental Data Scientist</span></p>
  <p class="home-identity__summary">I build scientific software, cloud and research computing infrastructure, and open-source methods for understanding complex environmental systems.</p>
  <p class="home-identity__areas">Scientific computing · Geospatial data · Distributed systems · AI-assisted science</p>
"""
        main = main.replace("</h1>", "</h1>" + identity, 1)
    return main


def navigation(prefix: str) -> str:
    home_href = prefix or "/"
    return f"""
    <div class="mobile-bar">
      <a class="mobile-brand" href="{home_href}">Dr. Tuff</a>
      <button class="mobile-toggle" type="button" aria-expanded="false" aria-controls="mobile-navigation" aria-label="Open navigation menu"><span></span><span></span></button>
    </div>
    <header class="site-header">
      <nav class="primary-nav" aria-label="Primary navigation">
        <a href="{prefix}my-science/">My Science</a>
        <a href="{prefix}my-projects/">My Projects</a>
        <a href="{prefix}github/">GitHub</a>
        <a href="{prefix}my-cv/">My CV</a>
        <a href="{prefix}contact-me/">Contact me</a>
      </nav>
      <a class="site-title" href="{home_href}">Dr. Tuff</a>
      <nav class="social-nav" aria-label="Social links">
        <a class="social-link social-link--github" href="https://github.com/ttuff" aria-label="GitHub"><span aria-hidden="true">GH</span></a>
        <a class="social-link social-link--email" href="mailto:ty.tuff@colorado.edu" aria-label="Email"><span aria-hidden="true">@</span></a>
      </nav>
    </header>
    <nav id="mobile-navigation" class="mobile-navigation" aria-label="Mobile navigation">
      <a href="{prefix}my-science/">My Science</a>
      <a href="{prefix}my-projects/">My Projects</a>
      <a href="{prefix}github/">GitHub</a>
      <a href="{prefix}my-cv/">My CV</a>
      <a href="{prefix}contact-me/">Contact me</a>
    </nav>"""


def footer(prefix: str) -> str:
    home_href = prefix or "/"
    return f"""
    <footer class="site-footer">
      <div class="footer-inner">
        <div class="footer-about">
          <img src="{prefix}assets/images/Ty_logo_WHITE-ea311454.png" alt="Ty Tuff">
          <p>Principal Data Scientist at the NSF’s ESIIL synthesis center for Biology and Computer Science</p>
          <div class="footer-social">
            <a href="https://www.researchgate.net/profile/Ty_Tuff"><img src="{prefix}assets/images/RG-logo-01-9d242ea8.png" alt=""><span>Researchgate</span></a>
            <a href="https://scholar.google.com/citations?user=jxAk620AAAAJ&amp;hl=en"><img src="{prefix}assets/images/GS_logo-01-d709fc22.png" alt=""><span>Google scholar</span></a>
          </div>
        </div>
        <div class="footer-links">
          <h2>Quick Links</h2>
          <a href="{home_href}">Home</a>
          <a href="{prefix}my-science/">My Science</a>
          <a href="{prefix}my-projects/">My Projects</a>
          <a href="{prefix}github/">GitHub</a>
          <a href="{prefix}my-cv/">My CV</a>
          <a href="{prefix}contact-me/">Contact Me</a>
          <nav class="footer-contact-social" aria-label="Contact links"><a href="https://github.com/ttuff" aria-label="GitHub">GH</a><a href="mailto:ty.tuff@colorado.edu" aria-label="Email">@</a></nav>
        </div>
      </div>
      <div class="footer-bottom"><span>© Ty Tuff 2020. All Rights Reserved.</span><span>Site designed &amp; built by <a href="https://www.impactmedialab.com/">Impact Media Lab</a></span></div>
    </footer>"""


def page_document(slug: str, main: str, meta: dict[str, str]) -> str:
    prefix = "../" if slug != "root" else ""
    title = meta.get("og:title") or meta.get("title") or "Dr. Tuff"
    description = re.sub(
        r"\s+",
        " ",
        (meta.get("description") or meta.get("og:description") or "").replace("micrcosm", "microcosm"),
    ).strip()
    if slug == "news" and not description:
        description = "News and updates from Dr. Ty Tuff."
    page_slug = "home" if slug == "root" else slug
    canonical_path = "/" if slug == "root" else f"/{slug}"
    canonical_url = f"{PRODUCTION_ORIGIN}{canonical_path}"
    social_image_url = f"{PRODUCTION_ORIGIN}/{SOCIAL_IMAGE}"
    website_id = f"{PRODUCTION_ORIGIN}/#website"
    person_id = f"{PRODUCTION_ORIGIN}/#person"
    webpage = {
        "@type": "ProfilePage" if slug == "root" else "WebPage",
        "@id": f"{canonical_url}#webpage",
        "name": title,
        "description": description,
        "url": canonical_url,
        "isPartOf": {"@id": website_id},
        "about": {"@id": person_id},
    }
    if slug == "root":
        webpage["mainEntity"] = {"@id": person_id}
    structured_data = json.dumps(
        {
            "@context": "https://schema.org",
            "@graph": [
                {
                    "@type": "WebSite",
                    "@id": website_id,
                    "name": "Dr. Tuff",
                    "url": f"{PRODUCTION_ORIGIN}/",
                },
                {
                    "@type": "Person",
                    "@id": person_id,
                    "name": "Ty Tuff",
                    "url": f"{PRODUCTION_ORIGIN}/",
                    "image": social_image_url,
                    "jobTitle": "Principal Data Scientist",
                    "description": "Environmental data scientist and ecologist who builds scientific software, cloud and research computing infrastructure, and open-source methods for complex environmental systems.",
                    "knowsAbout": [
                        "Environmental data science",
                        "Scientific computing",
                        "Cloud computing",
                        "Research cyberinfrastructure",
                        "Open-source software",
                        "Python",
                        "Geospatial computing",
                        "Remote sensing",
                        "Large-scale data analysis",
                        "Distributed computing",
                        "Agentic scientific workflows",
                        "Technical leadership",
                    ],
                    "worksFor": {
                        "@type": "Organization",
                        "name": "Environmental Data Science Innovation and Inclusion Lab (ESIIL)",
                        "url": "https://esiil.org/",
                    },
                    "sameAs": [
                        "https://github.com/ttuff",
                        "https://scholar.google.com/citations?user=jxAk620AAAAJ&hl=en",
                        "https://www.researchgate.net/profile/Ty_Tuff",
                    ],
                },
                webpage,
            ],
        },
        ensure_ascii=False,
        separators=(",", ":"),
    ).replace("</", "<\\/")
    page_assets = ""
    robots = '  <meta name="robots" content="noindex">\n' if slug == "news" else ""
    search_console = (
        f'  <meta name="google-site-verification" content="{html.escape(GOOGLE_SITE_VERIFICATION, quote=True)}">\n'
        if GOOGLE_SITE_VERIFICATION
        else ""
    )
    analytics = (
        f'  <script src="{prefix}scripts/analytics.js" '
        f'data-measurement-id="{html.escape(GA_MEASUREMENT_ID, quote=True)}" defer></script>\n'
    )
    if slug == "github":
        page_assets = f'  <link rel="stylesheet" href="{prefix}styles/github.css">\n  <link rel="preload" href="{prefix}data/github-life.json" as="fetch" crossorigin="anonymous">\n  <script src="{prefix}scripts/github.js" defer></script>\n'
    elif slug == "my-projects":
        page_assets = f'  <link rel="stylesheet" href="{prefix}styles/projects.css">\n  <link rel="preload" href="{prefix}data/github-life.json" as="fetch" crossorigin="anonymous">\n  <script src="{prefix}scripts/projects.js" defer></script>\n'
    return f"""<!doctype html>
<html lang="en-US">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
{search_console}{analytics}  <title>{html.escape(title)}</title>
  <meta name="description" content="{html.escape(description, quote=True)}">
{robots}  <link rel="canonical" href="{canonical_url}">
  <meta property="og:site_name" content="Dr. Tuff">
  <meta property="og:title" content="{html.escape(title, quote=True)}">
  <meta property="og:type" content="website">
  <meta property="og:url" content="{canonical_url}">
  <meta property="og:description" content="{html.escape(description, quote=True)}">
  <meta property="og:image" content="{social_image_url}">
  <meta property="og:image:alt" content="Portrait of Dr. Ty Tuff">
  <meta property="og:image:width" content="532">
  <meta property="og:image:height" content="569">
  <meta name="twitter:card" content="summary">
  <meta name="twitter:title" content="{html.escape(title, quote=True)}">
  <meta name="twitter:description" content="{html.escape(description, quote=True)}">
  <meta name="twitter:image" content="{social_image_url}">
  <meta name="twitter:image:alt" content="Portrait of Dr. Ty Tuff">
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
        page_meta = {**metadata[slug], **PAGE_METADATA_OVERRIDES.get(slug, {})}
        if slug == "home":
            root_main = rewrite_main(markup, "root", asset_map)
            (DIST / "index.html").write_text(page_document("root", root_main, page_meta), encoding="utf-8")
            continue
        destination = DIST / slug
        destination.mkdir(parents=True, exist_ok=True)
        (destination / "index.html").write_text(page_document(slug, rewritten, page_meta), encoding="utf-8")

    for slug, custom_meta in CUSTOM_PAGES.items():
        main = (ROOT / "pages" / f"{slug}.html").read_text(encoding="utf-8")
        destination = DIST / slug
        destination.mkdir(parents=True, exist_ok=True)
        (destination / "index.html").write_text(page_document(slug, main, custom_meta), encoding="utf-8")

    data_target = DIST / "data"
    data_target.mkdir(exist_ok=True)
    shutil.copy2(ROOT / "data" / "generated" / "github-life.json", data_target / "github-life.json")

    aliases = {
        "home": ("/", f"{PRODUCTION_ORIGIN}/"),
        "about": ("/#h-about-me", f"{PRODUCTION_ORIGIN}/"),
        "research": ("/my-science", f"{PRODUCTION_ORIGIN}/my-science"),
    }
    for alias, (destination, canonical) in aliases.items():
        target = DIST / alias
        target.mkdir(parents=True, exist_ok=True)
        (target / "index.html").write_text(redirect_document(destination, canonical), encoding="utf-8")

    sitemap_paths = ["/", *(f"/{slug}" for slug in INDEXED_PAGES), *(f"/{slug}" for slug in CUSTOM_PAGES)]
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
