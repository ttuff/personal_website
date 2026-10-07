from __future__ import annotations

import importlib.util
import json
import sys
import unittest
from datetime import date, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("github_life", ROOT / "scripts" / "build_github_life.py")
assert SPEC and SPEC.loader
github_life = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = github_life
SPEC.loader.exec_module(github_life)


class ActivityScoreTests(unittest.TestCase):
    def test_score_rewards_active_days_and_declining_recency_windows(self) -> None:
        today = date(2026, 10, 4)
        commits = [today, today, today - timedelta(days=10), today - timedelta(days=45), today - timedelta(days=75)]
        releases = [today - timedelta(days=2)]
        result = github_life.activity_score(commits, releases, today)
        self.assertEqual(result["windows"]["30"], {"commits": 3, "active_days": 2})
        self.assertEqual(result["score"], 10 + 9 + 2 + 1 + 6)

    def test_sparkline_retains_exact_commit_total(self) -> None:
        today = date(2026, 10, 4)
        commits = [today - timedelta(days=value) for value in (0, 1, 7, 20, 89)]
        self.assertEqual(sum(github_life.weekly_sparkline(commits, today)), len(commits))


class CalendarTests(unittest.TestCase):
    def test_graphql_contribution_levels_map_to_heatmap_intensity(self) -> None:
        self.assertEqual(github_life.contribution_level("NONE"), 0)
        self.assertEqual(github_life.contribution_level("THIRD_QUARTILE"), 3)
        self.assertEqual(github_life.contribution_level("FOURTH_QUARTILE"), 4)

    def test_discoveries_find_consecutive_streak_not_sparse_span(self) -> None:
        days = [
            {"date": "2026-01-01", "count": 2},
            {"date": "2026-01-02", "count": 1},
            {"date": "2026-01-03", "count": 4},
            {"date": "2026-01-05", "count": 10},
        ]
        result = github_life.calendar_discoveries(days)
        self.assertEqual(result["longest_active_streak"]["days"], 3)
        self.assertEqual(result["busiest_day"]["date"], "2026-01-05")


class GraphTests(unittest.TestCase):
    def test_duplicate_edges_merge_without_losing_evidence(self) -> None:
        edges = github_life.deduplicate_edges([
            {"source": "a", "target": "b", "type": "shared-contributor", "label": "Observed contributor: one", "weight": 1},
            {"source": "b", "target": "a", "type": "shared-contributor", "label": "Observed contributor: two", "weight": 1},
        ])
        self.assertEqual(len(edges), 1)
        self.assertEqual(edges[0]["weight"], 2)
        self.assertEqual(len(edges[0]["evidence"]), 2)
        self.assertIn("one", edges[0]["label"])
        self.assertIn("two", edges[0]["label"])

    def test_graph_metrics_identify_bridge_and_components(self) -> None:
        edges = [
            {"source": "a", "target": "b", "weight": 1},
            {"source": "b", "target": "c", "weight": 2},
        ]
        metrics = github_life.graph_metrics(["a", "b", "c", "isolated"], edges)
        self.assertEqual(metrics["connected_components"], 2)
        self.assertEqual(metrics["nodes"]["b"]["degree"], 2)
        self.assertEqual(metrics["nodes"]["b"]["weighted_degree"], 3)
        self.assertGreater(metrics["nodes"]["b"]["betweenness"], metrics["nodes"]["a"]["betweenness"])

    def test_fallback_repository_title_handles_missing_metadata(self) -> None:
        self.assertEqual(github_life.humanize_repository_name("fire_vase"), "Fire vase")
        self.assertEqual(github_life.humanize_repository_name(None), "Untitled repository")


class GeneratedDatasetTests(unittest.TestCase):
    def test_checked_in_dataset_is_compact_and_has_evidenced_edges(self) -> None:
        path = ROOT / "data" / "generated" / "github-life.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        self.assertLess(path.stat().st_size, 500_000)
        self.assertGreater(len(payload["repositories"]), 10)
        self.assertTrue(payload["contributions"]["days"])
        self.assertEqual(payload["meta"]["schema_version"], 2)
        allowed = {"curated", "family", "shared-contributor"}
        self.assertTrue(all(edge["type"] in allowed and edge["label"] for edge in payload["graph"]["edges"]))
        self.assertTrue(all(repo["url"].startswith("https://github.com/") for repo in payload["repositories"] if repo.get("url")))
        self.assertFalse(any("earthdatascience.org" in (repo.get("homepage") or "") for repo in payload["repositories"]))

    def test_curated_homepage_overrides_replace_stale_github_metadata(self) -> None:
        config = json.loads((ROOT / "data" / "github-projects.yml").read_text(encoding="utf-8"))
        metadata = config["repository_metadata"]
        self.assertEqual(metadata["earthlab/cft"]["homepage"], "https://earthlab.github.io/cft/")
        self.assertEqual(metadata["earthlab/eddi"]["homepage"], "https://earthlab.github.io/eddi/")
        self.assertEqual(metadata["earthlab/leri"]["homepage"], "https://earthlab.github.io/leri/")

    def test_graph_has_unique_nodes_edges_and_valid_family_membership(self) -> None:
        payload = json.loads((ROOT / "data" / "generated" / "github-life.json").read_text(encoding="utf-8"))
        nodes = payload["graph"]["nodes"]
        edges = payload["graph"]["edges"]
        node_ids = {node["id"] for node in nodes}
        edge_ids = {edge["id"] for edge in edges}
        self.assertEqual(len(node_ids), len(nodes))
        self.assertEqual(len(edge_ids), len(edges))
        self.assertTrue(all(edge["source"] in node_ids and edge["target"] in node_ids for edge in edges))
        for family in payload["families"]:
            membership = [edge for edge in edges if edge["type"] == "family" and family["id"] in {edge["source"], edge["target"]}]
            self.assertEqual(len(membership), len(family["repositories"]))

    def test_semantic_fallbacks_and_insight_evidence_are_complete(self) -> None:
        payload = json.loads((ROOT / "data" / "generated" / "github-life.json").read_text(encoding="utf-8"))
        node_ids = {node["id"] for node in payload["graph"]["nodes"]}
        edge_ids = {edge["id"] for edge in payload["graph"]["edges"]}
        self.assertTrue(all(repo["semantic"]["title"] for repo in payload["repositories"]))
        self.assertTrue(all(node.get("ownership") in {"mine", "external"} for node in payload["graph"]["nodes"] if node["type"] == "repository"))
        self.assertTrue(payload["graph"]["insights"])
        for insight in payload["graph"]["insights"]:
            self.assertTrue(insight["statement"] and insight["evidence"])
            self.assertTrue(set(insight["nodes"]) <= node_ids)
            self.assertTrue(set(insight["edges"]) <= edge_ids)

    def test_portfolio_joins_curated_projects_to_repository_evidence(self) -> None:
        payload = json.loads((ROOT / "data" / "generated" / "github-life.json").read_text(encoding="utf-8"))
        portfolio = payload["portfolio"]
        projects = portfolio["projects"]
        repository_names = {repo["full_name"] for repo in payload["repositories"]}
        self.assertEqual(
            {project["id"] for project in projects},
            {"cubedynamics", "spectralbridge", "oasis", "fire-vase", "agentic-systems"},
        )
        for project in projects:
            self.assertEqual(project["evidence"]["repository_count"], len(project["repositories"]))
            self.assertTrue({repo["full_name"] for repo in project["repositories"]} <= repository_names)
            self.assertTrue(project["summary"])
            self.assertTrue(project["website"]["url"].startswith("https://"))
            self.assertNotIn("drtuff.com", project["website"]["url"])
            self.assertTrue(project["github"]["url"].startswith("https://github.com/"))
            screenshot = ROOT / project["screenshot"]["src"].lstrip("/")
            self.assertEqual(screenshot.suffix, ".webp")
            self.assertTrue(screenshot.exists())
            self.assertLess(screenshot.stat().st_size, 150_000)
            self.assertEqual(
                project["evidence"]["release_count"],
                sum(repo["release_count_observed"] for repo in project["repositories"]),
            )
            for metric in project.get("metrics", []):
                self.assertTrue(metric["value"] and metric["label"])
                self.assertTrue(metric["source"].startswith("https://"))
            if project.get("visual"):
                asset = ROOT / project["visual"]["src"].lstrip("/")
                self.assertTrue(asset.exists(), f"Missing portfolio visual: {asset}")
                self.assertTrue(project["visual"]["alt"])
        used_technologies = {technology for project in projects for technology in project["technologies"]}
        published_technologies = {
            technology
            for technologies in portfolio["technology_groups"].values()
            for technology in technologies
        }
        self.assertTrue(published_technologies)
        self.assertTrue(published_technologies <= used_technologies)


if __name__ == "__main__":
    unittest.main()
