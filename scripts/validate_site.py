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
PRODUCTION_ORIGIN = "https://drtuff.com"
PRODUCTION_HOSTS = {"drtuff.com", "www.drtuff.com"}
FORBIDDEN_DEPLOYMENT_TEXT = ("ttuff.github.io", "/personal_website/", "squarespace-cdn")
REQUIRED_ROUTES = ("/", "/about", "/research", "/home", "/my-science", "/my-projects", "/my-skills", "/my-cv", "/news", "/contact-me", "/github")


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
        deployment_scan = lower.replace("https://github.com/ttuff/personal_website/", "")
        for hostname in SQUARESPACE:
            if hostname in lower:
                failures.append(f"Squarespace dependency in {page.relative_to(ROOT)}: {hostname}")
        for forbidden in FORBIDDEN_DEPLOYMENT_TEXT:
            if forbidden in deployment_scan:
                failures.append(f"forbidden deployment reference in {page.relative_to(ROOT)}: {forbidden}")

        is_alias = page.parent.name in {"about", "research"}
        if not is_alias:
            relative = page.relative_to(SITE)
            route = "/" if relative == Path("index.html") else f"/{relative.parent.as_posix()}"
            expected_url = f"{PRODUCTION_ORIGIN}{route}"
            canonical = re.search(r'<link\s+rel="canonical"\s+href="([^"]+)"', markup, flags=re.I)
            og_url = re.search(r'<meta\s+property="og:url"\s+content="([^"]+)"', markup, flags=re.I)
            if not canonical or canonical.group(1) != expected_url:
                failures.append(f"incorrect canonical URL in {page.relative_to(ROOT)}; expected {expected_url}")
            if not og_url or og_url.group(1) != expected_url:
                failures.append(f"incorrect OpenGraph URL in {page.relative_to(ROOT)}; expected {expected_url}")

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
            if github_data.stat().st_size > 500_000:
                failures.append("generated GitHub-life dataset exceeds the 500 KB performance budget")
        except (ValueError, OSError) as exc:
            failures.append(f"invalid generated GitHub-life dataset: {exc}")

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
