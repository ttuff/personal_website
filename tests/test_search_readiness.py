from __future__ import annotations

import html
import json
import re
import subprocess
import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"
ORIGIN = "https://drtuff.com"
INDEXABLE_ROUTES = (
    "/",
    "/my-science",
    "/my-projects",
    "/my-skills",
    "/my-cv",
    "/contact-me",
    "/github",
)


def route_file(route: str) -> Path:
    return SITE / "index.html" if route == "/" else SITE / route.lstrip("/") / "index.html"


class SearchReadinessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        subprocess.run([sys.executable, str(ROOT / "scripts" / "build_static_site.py")], check=True)

    def test_indexable_pages_have_unique_search_metadata(self) -> None:
        titles: set[str] = set()
        for route in INDEXABLE_ROUTES:
            markup = route_file(route).read_text(encoding="utf-8")
            expected_url = f"{ORIGIN}{route}"
            title = re.search(r"<title>(.*?)</title>", markup, flags=re.I | re.S)
            description = re.search(
                r'<meta name="description" content="([^"]+)">', markup, flags=re.I
            )
            canonical = re.search(r'<link rel="canonical" href="([^"]+)">', markup, flags=re.I)
            h1 = re.search(r"<h1\b[^>]*>(.*?)</h1>", markup, flags=re.I | re.S)

            self.assertIsNotNone(title, route)
            self.assertIsNotNone(description, route)
            self.assertEqual(canonical.group(1), expected_url, route)
            self.assertIsNotNone(h1, route)
            self.assertTrue(re.sub(r"<[^>]+>|\s+", "", h1.group(1)), route)
            normalized_title = html.unescape(re.sub(r"\s+", " ", title.group(1)).strip())
            self.assertNotIn(normalized_title, titles)
            titles.add(normalized_title)
            self.assertNotIn("localhost", markup)
            self.assertNotIn("ttuff.github.io", markup)

    def test_sitemap_contains_only_canonical_public_urls(self) -> None:
        sitemap = (SITE / "sitemap.xml").read_text(encoding="utf-8")
        root = ET.fromstring(sitemap)
        namespace = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        urls = [element.text for element in root.findall("s:url/s:loc", namespace)]
        expected = [f"{ORIGIN}{route}" for route in INDEXABLE_ROUTES]
        self.assertCountEqual(urls, expected)
        self.assertEqual(len(urls), len(set(urls)))

    def test_robots_allows_crawling_and_advertises_sitemap(self) -> None:
        self.assertEqual(
            (SITE / "robots.txt").read_text(encoding="utf-8"),
            f"User-agent: *\nAllow: /\n\nSitemap: {ORIGIN}/sitemap.xml\n",
        )

    def test_homepage_has_verified_person_structured_data(self) -> None:
        markup = (SITE / "index.html").read_text(encoding="utf-8")
        block = re.search(
            r'<script type="application/ld\+json">(.*?)</script>', markup, flags=re.I | re.S
        )
        self.assertIsNotNone(block)
        structured = json.loads(block.group(1))
        graph = structured["@graph"]
        profile_page = next(entity for entity in graph if entity["@type"] == "ProfilePage")
        person = next(entity for entity in graph if entity["@type"] == "Person")
        self.assertEqual(profile_page["mainEntity"]["@id"], person["@id"])
        self.assertEqual(person["name"], "Ty Tuff")
        self.assertEqual(
            set(person["sameAs"]),
            {
                "https://github.com/ttuff",
                "https://scholar.google.com/citations?user=jxAk620AAAAJ&hl=en",
                "https://www.researchgate.net/profile/Ty_Tuff",
            },
        )

    def test_aliases_and_empty_news_page_are_not_indexable(self) -> None:
        expected_canonicals = {
            "about": f"{ORIGIN}/",
            "home": f"{ORIGIN}/",
            "research": f"{ORIGIN}/my-science",
        }
        for route, expected_canonical in expected_canonicals.items():
            markup = (SITE / route / "index.html").read_text(encoding="utf-8")
            self.assertIn('<meta name="robots" content="noindex">', markup)
            self.assertIn(f'<link rel="canonical" href="{expected_canonical}">', markup)
        news = (SITE / "news" / "index.html").read_text(encoding="utf-8")
        self.assertIn('<meta name="robots" content="noindex">', news)

    def test_custom_domain_and_social_previews_are_deployable(self) -> None:
        self.assertEqual((SITE / "CNAME").read_text(encoding="utf-8").strip(), "drtuff.com")
        for route in INDEXABLE_ROUTES:
            markup = route_file(route).read_text(encoding="utf-8")
            self.assertIn('property="og:image:alt"', markup, route)
            self.assertIn('name="twitter:image:alt"', markup, route)
            self.assertRegex(markup, r'<link rel="icon" href="[^"]+">')


if __name__ == "__main__":
    unittest.main()
