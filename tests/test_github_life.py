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


class GeneratedDatasetTests(unittest.TestCase):
    def test_checked_in_dataset_is_compact_and_has_evidenced_edges(self) -> None:
        path = ROOT / "data" / "generated" / "github-life.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        self.assertLess(path.stat().st_size, 500_000)
        self.assertGreater(len(payload["repositories"]), 10)
        self.assertTrue(payload["contributions"]["days"])
        allowed = {"curated", "family", "shared-contributor"}
        self.assertTrue(all(edge["type"] in allowed and edge["label"] for edge in payload["graph"]["edges"]))
        self.assertTrue(all(repo["url"].startswith("https://github.com/") for repo in payload["repositories"] if repo.get("url")))


if __name__ == "__main__":
    unittest.main()
