#!/usr/bin/env python3
"""Validate the generated static site before GitHub Pages deployment."""

from __future__ import annotations

import json
import re
import subprocess
import sys
import urllib.parse
import xml.etree.ElementTree as ET
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"
SQUARESPACE = ("squarespace.com", "squarespace-cdn.com", "static1.squarespace.com")
PRODUCTION_ORIGIN = "https://drtuff.com"
PRODUCTION_HOSTS = {"drtuff.com", "www.drtuff.com"}
FORBIDDEN_DEPLOYMENT_TEXT = ("ttuff.github.io", "/personal_website/", "squarespace-cdn")
STALE_EXTERNAL_REFERENCES = (
    "https://tuff.shinyapps.io/Ecology_Stats_intro_application/",
    "earthdatascience.org/cft",
    "earthdatascience.org/eddi",
    "earthdatascience.org/leri",
)
LEGACY_HTML_MARKERS = (
    "mozallowfullscreen",
    "webkitallowfullscreen",
    "elementtiming=",
    "frameborder=",
    "data-html=",
)
REQUIRED_ROUTES = ("/", "/about", "/research", "/home", "/my-science", "/my-projects", "/my-skills", "/my-cv", "/news", "/contact-me", "/github")


class ReferenceParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.references: list[tuple[str, str]] = []
        self.errors: list[str] = []
        self.ids: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        names = [key.lower() for key, _ in attrs]
        duplicates = sorted(name for name, count in Counter(names).items() if count > 1)
        if duplicates:
            self.errors.append(f"<{tag}> has duplicate attributes: {', '.join(duplicates)}")
        values = {key: value or "" for key, value in attrs}
        if values.get("id"):
            self.ids.append(values["id"])
        if tag == "img" and "alt" not in names:
            self.errors.append("<img> is missing an alt attribute")
        if tag == "div" and "aria-label" in names and not values.get("role"):
            self.errors.append("<div> uses aria-label without an explicit role")
        if tag in {"a", "link"} and values.get("href"):
            if not (tag == "link" and values.get("rel") == "canonical"):
                self.references.append(("href", values["href"]))
        if tag in {"img", "script", "iframe", "source", "video"} and values.get("src"):
            self.references.append(("src", values["src"]))


def local_target(page: Path, reference: str) -> Path | None:
    parsed = urllib.parse.urlsplit(reference)
    if reference.startswith(("//", "mailto:", "tel:", "#", "data:")):
        return None
    if parsed.scheme and parsed.hostname not in PRODUCTION_HOSTS:
        return None
    decoded_path = urllib.parse.unquote(parsed.path)
    if parsed.hostname in PRODUCTION_HOSTS or decoded_path.startswith("/"):
        target = (SITE / decoded_path.lstrip("/")).resolve()
    else:
        target = (page.parent / decoded_path).resolve()
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
    analytics_ids: set[str] = set()
    page_titles: dict[str, Path] = {}
    html_files = sorted(SITE.rglob("*.html"))
    for page in html_files:
        markup = page.read_text(encoding="utf-8")
        parser = ReferenceParser()
        try:
            parser.feed(markup)
            parser.close()
        except Exception as exc:
            failures.append(f"malformed HTML in {page.relative_to(ROOT)}: {exc}")
        for error in parser.errors:
            failures.append(f"invalid HTML in {page.relative_to(ROOT)}: {error}")
        duplicate_ids = sorted(identifier for identifier, count in Counter(parser.ids).items() if count > 1)
        if duplicate_ids:
            failures.append(
                f"duplicate IDs in {page.relative_to(ROOT)}: {', '.join(duplicate_ids)}"
            )
        for attr, reference in parser.references:
            target = local_target(page, reference)
            if target is not None and not target.exists():
                failures.append(
                    f"missing {attr} target in {page.relative_to(ROOT)}: {reference}"
                )
        lower = markup.lower()
        deployment_scan = lower.replace("https://github.com/ttuff/personal_website/", "")
        for hostname in SQUARESPACE:
            if hostname in lower:
                failures.append(f"Squarespace dependency in {page.relative_to(ROOT)}: {hostname}")
        for forbidden in FORBIDDEN_DEPLOYMENT_TEXT:
            if forbidden in deployment_scan:
                failures.append(f"forbidden deployment reference in {page.relative_to(ROOT)}: {forbidden}")
        for stale in STALE_EXTERNAL_REFERENCES:
            if stale.lower() in lower:
                failures.append(f"stale external reference in {page.relative_to(ROOT)}: {stale}")
        for marker in LEGACY_HTML_MARKERS:
            if marker in lower:
                failures.append(f"legacy HTML marker in {page.relative_to(ROOT)}: {marker}")
        if re.search(r"\s/\s+src=", markup, flags=re.I):
            failures.append(f"malformed self-closing tag in {page.relative_to(ROOT)}")
        if re.search(r'href=["\']{2}', markup, flags=re.I):
            failures.append(f"empty href in {page.relative_to(ROOT)}")

        alias_canonicals = {
            "about": f"{PRODUCTION_ORIGIN}/",
            "home": f"{PRODUCTION_ORIGIN}/",
            "research": f"{PRODUCTION_ORIGIN}/my-science",
        }
        if page.parent.name in alias_canonicals:
            canonical = re.search(r'<link\s+rel="canonical"\s+href="([^"]+)"', markup, flags=re.I)
            if not canonical or canonical.group(1) != alias_canonicals[page.parent.name]:
                failures.append(
                    f"incorrect alias canonical in {page.relative_to(ROOT)}; "
                    f"expected {alias_canonicals[page.parent.name]}"
                )
            if '<meta name="robots" content="noindex">' not in lower:
                failures.append(f"redirect alias is indexable: {page.relative_to(ROOT)}")
            if "scripts/analytics.js" in lower:
                failures.append(f"redirect alias would double-count analytics: {page.relative_to(ROOT)}")
        else:
            relative = page.relative_to(SITE)
            route = "/" if relative == Path("index.html") else f"/{relative.parent.as_posix()}"
            expected_url = f"{PRODUCTION_ORIGIN}{route}"
            canonical = re.search(r'<link\s+rel="canonical"\s+href="([^"]+)"', markup, flags=re.I)
            og_url = re.search(r'<meta\s+property="og:url"\s+content="([^"]+)"', markup, flags=re.I)
            if not canonical or canonical.group(1) != expected_url:
                failures.append(f"incorrect canonical URL in {page.relative_to(ROOT)}; expected {expected_url}")
            if not og_url or og_url.group(1) != expected_url:
                failures.append(f"incorrect OpenGraph URL in {page.relative_to(ROOT)}; expected {expected_url}")
            head = markup.split("</head>", 1)[0]
            title_match = re.search(r"<title>(.*?)</title>", head, flags=re.I | re.S)
            description_match = re.search(
                r'<meta\s+name="description"\s+content="([^"]*)">', head, flags=re.I
            )
            if not title_match or not re.sub(r"\s+", " ", title_match.group(1)).strip():
                failures.append(f"missing page title in {page.relative_to(ROOT)}")
            else:
                title = re.sub(r"\s+", " ", title_match.group(1)).strip()
                if title in page_titles:
                    failures.append(
                        f"duplicate page title in {page.relative_to(ROOT)} and "
                        f"{page_titles[title].relative_to(ROOT)}: {title}"
                    )
                page_titles[title] = page
            if not description_match or not description_match.group(1).strip():
                failures.append(f"missing meta description in {page.relative_to(ROOT)}")
            h1_match = re.search(r"<h1\b[^>]*>(.*?)</h1>", markup, flags=re.I | re.S)
            if not h1_match or not re.sub(r"<[^>]+>|\s+", "", h1_match.group(1)):
                failures.append(f"missing meaningful H1 in {page.relative_to(ROOT)}")

            required_social_metadata = (
                'property="og:title"',
                'property="og:description"',
                'property="og:image"',
                'property="og:image:alt"',
                'name="twitter:card"',
                'name="twitter:title"',
                'name="twitter:description"',
                'name="twitter:image"',
                'name="twitter:image:alt"',
                'rel="icon"',
            )
            for marker in required_social_metadata:
                if marker not in head:
                    failures.append(f"missing social/search metadata in {page.relative_to(ROOT)}: {marker}")

            verification_tags = re.findall(
                r'<meta\s+name="google-site-verification"\s+content="([^"]*)">', head, flags=re.I
            )
            if len(verification_tags) > 1 or any(not token.strip() for token in verification_tags):
                failures.append(f"invalid Search Console verification metadata in {page.relative_to(ROOT)}")

            structured_blocks = re.findall(
                r'<script\s+type="application/ld\+json">(.*?)</script>', head, flags=re.I | re.S
            )
            if len(structured_blocks) != 1:
                failures.append(
                    f"expected one JSON-LD block in {page.relative_to(ROOT)}; found {len(structured_blocks)}"
                )
            else:
                try:
                    structured = json.loads(structured_blocks[0])
                    graph = structured.get("@graph", [])
                    types = {entity.get("@type") for entity in graph if isinstance(entity, dict)}
                    expected_page_type = "ProfilePage" if route == "/" else "WebPage"
                    if structured.get("@context") != "https://schema.org" or expected_page_type not in types:
                        failures.append(f"incorrect page JSON-LD in {page.relative_to(ROOT)}")
                    people = [entity for entity in graph if entity.get("@type") == "Person"]
                    if len(people) != 1 or people[0].get("name") != "Ty Tuff":
                        failures.append(f"missing Person JSON-LD in {page.relative_to(ROOT)}")
                    elif route == "/":
                        expected_profiles = {
                            "https://github.com/ttuff",
                            "https://scholar.google.com/citations?user=jxAk620AAAAJ&hl=en",
                            "https://www.researchgate.net/profile/Ty_Tuff",
                        }
                        if set(people[0].get("sameAs", [])) != expected_profiles:
                            failures.append("homepage Person JSON-LD has unverified or missing identity URLs")
                        expected_expertise = {
                            "Environmental data science",
                            "Scientific computing",
                            "Cloud computing",
                            "Open-source software",
                            "Geospatial computing",
                            "Remote sensing",
                            "Large-scale data analysis",
                            "Agentic scientific workflows",
                        }
                        if not expected_expertise <= set(people[0].get("knowsAbout", [])):
                            failures.append("homepage Person JSON-LD is missing verified expertise areas")
                except (json.JSONDecodeError, AttributeError, TypeError) as exc:
                    failures.append(f"invalid JSON-LD in {page.relative_to(ROOT)}: {exc}")

            analytics_tags = re.findall(
                r'<script\s+src="[^"]*scripts/analytics\.js"\s+data-measurement-id="([^"]+)"\s+defer></script>',
                head,
                flags=re.I,
            )
            if len(analytics_tags) != 1:
                failures.append(
                    f"expected exactly one analytics configuration in {page.relative_to(ROOT)}; "
                    f"found {len(analytics_tags)}"
                )
            else:
                measurement_id = analytics_tags[0].upper()
                analytics_ids.add(measurement_id)
                if not re.fullmatch(r"G-[A-Z0-9]+", measurement_id):
                    failures.append(f"invalid GA4 Measurement ID in {page.relative_to(ROOT)}")
            if "googletagmanager.com/gtag/js" in lower or "googletagmanager.com/gtm.js" in lower:
                failures.append(f"page bypasses the centralized analytics loader: {page.relative_to(ROOT)}")

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

    analytics_script = SITE / "scripts" / "analytics.js"
    if not analytics_script.exists():
        failures.append("missing centralized analytics runtime: site/scripts/analytics.js")
    else:
        analytics_source = analytics_script.read_text(encoding="utf-8")
        required_analytics_markers = (
            'const PRODUCTION_HOSTNAME = "drtuff.com"',
            "window.location.hostname !== PRODUCTION_HOSTNAME",
            "send_page_view: false",
            'window.gtag("event", "page_view"',
            'window.gtag("event", "file_download"',
            'window.gtag("event", "outbound_click"',
            '"project_visit"',
            '"project_github_click"',
            "project_name",
            "destination_url",
            "source_page",
            "link_type",
            "allow_google_signals: false",
            "allow_ad_personalization_signals: false",
        )
        for marker in required_analytics_markers:
            if marker not in analytics_source:
                failures.append(f"analytics runtime is missing required behavior: {marker}")
        if analytics_source.count('window.gtag("event", "page_view"') != 1:
            failures.append("analytics runtime must emit exactly one explicit page_view event")
        for private_source in ("window.location.search", "document.referrer", "user_id", "link_text"):
            if private_source in analytics_source:
                failures.append(f"analytics runtime collects a disallowed field: {private_source}")
    if len(analytics_ids) != 1:
        failures.append("canonical pages do not share one GA4 Measurement ID")

    for route in REQUIRED_ROUTES:
        target = SITE / route.lstrip("/")
        if target.is_dir() or route == "/":
            target = target / "index.html"
        if not target.exists():
            failures.append(f"missing required route: {route}")

    cname = SITE / "CNAME"
    if not cname.exists() or cname.read_text(encoding="utf-8").strip() != "drtuff.com":
        failures.append("site/CNAME is missing or does not contain exactly drtuff.com")
    for required_file in (SITE / "sitemap.xml", SITE / "robots.txt", SITE / ".nojekyll"):
        if not required_file.exists():
            failures.append(f"missing deployment file: {required_file.relative_to(ROOT)}")

    github_data = SITE / "data" / "github-life.json"
    if not github_data.exists():
        failures.append("missing generated GitHub-life dataset")
    else:
        try:
            dataset = __import__("json").loads(github_data.read_text(encoding="utf-8"))
            if not dataset.get("repositories") or not dataset.get("contributions", {}).get("days"):
                failures.append("generated GitHub-life dataset has no repositories or calendar data")
            graph = dataset.get("graph", {})
            if dataset.get("meta", {}).get("schema_version", 0) < 2 or not graph.get("summary") or not graph.get("insights"):
                failures.append("generated GitHub-life dataset is missing semantic graph summaries or insights")
            node_ids = {node.get("id") for node in graph.get("nodes", [])}
            edge_ids = [edge.get("id") for edge in graph.get("edges", [])]
            if len(edge_ids) != len(set(edge_ids)) or any(not edge_id for edge_id in edge_ids):
                failures.append("generated GitHub-life graph contains duplicate or missing edge identifiers")
            if any(edge.get("source") not in node_ids or edge.get("target") not in node_ids for edge in graph.get("edges", [])):
                failures.append("generated GitHub-life graph contains an edge with an unknown node")
            portfolio = dataset.get("portfolio", {})
            projects = portfolio.get("projects", [])
            if len(projects) != 5 or not all(project.get("evidence", {}).get("repository_count") for project in projects):
                failures.append("generated GitHub-life dataset is missing the five evidenced portfolio projects")
            for project in projects:
                website = project.get("website", {}).get("url", "")
                github = project.get("github", {}).get("url", "")
                screenshot = project.get("screenshot", {}).get("src", "")
                if not website.startswith("https://") or "drtuff.com" in website:
                    failures.append(f"portfolio project has an invalid external website: {project.get('id')}")
                if not github.startswith("https://github.com/"):
                    failures.append(f"portfolio project has an invalid GitHub URL: {project.get('id')}")
                screenshot_path = SITE / screenshot.lstrip("/")
                if not screenshot.endswith(".webp") or not screenshot_path.exists():
                    failures.append(f"portfolio project has a missing optimized website preview: {project.get('id')}")
                elif screenshot_path.stat().st_size > 150_000:
                    failures.append(f"portfolio website preview exceeds 150 KB: {project.get('id')}")
                for metric in project.get("metrics", []):
                    if not metric.get("value") or not metric.get("label") or not metric.get("source", "").startswith("https://"):
                        failures.append(f"portfolio project has an unsupported metric: {project.get('id')}")
            if github_data.stat().st_size > 500_000:
                failures.append("generated GitHub-life dataset exceeds the 500 KB performance budget")
            serialized = github_data.read_text(encoding="utf-8").lower()
            for stale in STALE_EXTERNAL_REFERENCES[1:]:
                if stale.lower() in serialized:
                    failures.append(f"stale external reference in site/data/github-life.json: {stale}")
        except (ValueError, OSError) as exc:
            failures.append(f"invalid generated GitHub-life dataset: {exc}")

    root_markup = (SITE / "index.html").read_text(encoding="utf-8")
    news_markup = (SITE / "news" / "index.html").read_text(encoding="utf-8")
    if "micrcosm" in root_markup.lower():
        failures.append("homepage contains the misspelling 'micrcosm'")
    if "Ty Tuff, PhD" not in root_markup or "Environmental Data Scientist" not in root_markup:
        failures.append("homepage is missing its primary professional identity")
    if "<h1" not in news_markup.lower() or '<meta name="robots" content="noindex">' not in news_markup.lower():
        failures.append("news page must have an H1 and remain noindex until it has published content")

    projects_source = (SITE / "scripts" / "projects.js").read_text(encoding="utf-8")
    for marker in ("utm_campaign', 'project_gallery'", "data-project-name", "data-project-link-type"):
        if marker not in projects_source:
            failures.append(f"project gallery is missing required referral or analytics behavior: {marker}")
    sitemap_text = (SITE / "sitemap.xml").read_text(encoding="utf-8")
    sitemap_urls = re.findall(r"<loc>([^<]+)</loc>", sitemap_text)
    expected_sitemap_urls = {
        f"{PRODUCTION_ORIGIN}/",
        f"{PRODUCTION_ORIGIN}/my-science",
        f"{PRODUCTION_ORIGIN}/my-projects",
        f"{PRODUCTION_ORIGIN}/my-skills",
        f"{PRODUCTION_ORIGIN}/my-cv",
        f"{PRODUCTION_ORIGIN}/contact-me",
        f"{PRODUCTION_ORIGIN}/github",
    }
    try:
        ET.fromstring(sitemap_text)
    except ET.ParseError as exc:
        failures.append(f"invalid sitemap XML: {exc}")
    if set(sitemap_urls) != expected_sitemap_urls or len(sitemap_urls) != len(set(sitemap_urls)):
        failures.append("sitemap must contain each canonical, indexable production URL exactly once")

    robots_text = (SITE / "robots.txt").read_text(encoding="utf-8")
    expected_robots = f"User-agent: *\nAllow: /\n\nSitemap: {PRODUCTION_ORIGIN}/sitemap.xml\n"
    if robots_text != expected_robots:
        failures.append("robots.txt must allow public crawling and reference the production sitemap")

    build_source = (ROOT / "scripts" / "build_static_site.py").read_text(encoding="utf-8")
    if 'GOOGLE_SITE_VERIFICATION = ""' not in build_source or 'name="google-site-verification"' not in build_source:
        failures.append("build is not ready for optional Search Console HTML-tag verification")

    for path in SITE.rglob("*"):
        if path.is_file() and path.stat().st_size == 0 and path.name != ".nojekyll":
            failures.append(f"empty deployable asset: {path.relative_to(ROOT)}")

    for path in SITE.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in {".html", ".css", ".js", ".xml", ".txt"}:
            continue
        content = path.read_text(encoding="utf-8", errors="replace").lower()
        deployment_scan = content.replace("https://github.com/ttuff/personal_website/", "")
        for forbidden in FORBIDDEN_DEPLOYMENT_TEXT:
            if forbidden in deployment_scan:
                failures.append(f"forbidden deployment reference in {path.relative_to(ROOT)}: {forbidden}")

    if failures:
        print("Validation failed:")
        print("\n".join(f"- {failure}" for failure in failures))
        raise SystemExit(1)
    print(
        f"Validated {len(html_files)} HTML files, {len(REQUIRED_ROUTES)} routes, custom-domain metadata, "
        "and all deployable assets with no missing local references or Squarespace dependencies."
    )


if __name__ == "__main__":
    main()
