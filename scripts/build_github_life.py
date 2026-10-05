#!/usr/bin/env python3
"""Build the compact, static dataset used by the /github/ page.

GitHub facts come from public REST/GraphQL APIs. Editorial meaning comes from
data/github-projects.yml, which is deliberately JSON-compatible YAML so the
pipeline stays dependency-free.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter, defaultdict, deque
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "data" / "github-projects.yml"
OUTPUT = ROOT / "data" / "generated" / "github-life.json"
CACHE = ROOT / ".cache" / "github-life"
SCHEMA_VERSION = 2
USER_AGENT = "drtuff-github-life/1.0"
GRAPHQL_URL = "https://api.github.com/graphql"
REST_URL = "https://api.github.com"


def utc_now() -> datetime:
    return datetime.now(UTC).replace(microsecond=0)


def iso_date(value: str | None) -> date | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00")).date()


def is_bot(login: str | None) -> bool:
    value = (login or "").lower()
    return value.endswith("[bot]") or value in {"dependabot", "github-actions"}


def contribution_level(value: str | int | None) -> int:
    if isinstance(value, int):
        return max(0, min(4, value))
    return {
        "NONE": 0,
        "FIRST_QUARTILE": 1,
        "SECOND_QUARTILE": 2,
        "THIRD_QUARTILE": 3,
        "FOURTH_QUARTILE": 4,
    }.get(str(value or "").upper(), 0)


def activity_score(commits: Iterable[date], releases: Iterable[date], today: date) -> dict[str, Any]:
    """Return transparent recent-activity components and score."""
    commit_days = list(commits)
    windows = {}
    for size in (30, 60, 90):
        cutoff = today - timedelta(days=size - 1)
        in_window = [value for value in commit_days if cutoff <= value <= today]
        windows[str(size)] = {
            "commits": len(in_window),
            "active_days": len(set(in_window)),
        }
    release_90 = sum(today - timedelta(days=89) <= value <= today for value in releases)
    commits_30 = windows["30"]["commits"]
    commits_31_60 = windows["60"]["commits"] - commits_30
    commits_61_90 = windows["90"]["commits"] - windows["60"]["commits"]
    score = (
        5 * windows["30"]["active_days"]
        + 3 * commits_30
        + 2 * commits_31_60
        + commits_61_90
        + 6 * release_90
    )
    return {"score": score, "windows": windows, "releases_90": release_90}


def weekly_sparkline(commits: Iterable[date], today: date, weeks: int = 13) -> list[int]:
    start = today - timedelta(days=weeks * 7 - 1)
    bins = [0] * weeks
    for value in commits:
        if start <= value <= today:
            bins[min((value - start).days // 7, weeks - 1)] += 1
    return bins


def calendar_discoveries(days: list[dict[str, Any]]) -> dict[str, Any]:
    positive = sorted(
        ((date.fromisoformat(item["date"]), int(item["count"])) for item in days if item["count"] > 0),
        key=lambda item: item[0],
    )
    if not positive:
        return {}
    longest: list[tuple[date, int]] = []
    current: list[tuple[date, int]] = []
    previous: date | None = None
    for item in positive:
        if previous is not None and item[0] == previous + timedelta(days=1):
            current.append(item)
        else:
            current = [item]
        if len(current) > len(longest):
            longest = current.copy()
        previous = item[0]
    months: Counter[str] = Counter()
    for day, count in positive:
        months[day.strftime("%Y-%m")] += count
    busiest_day = max(positive, key=lambda item: item[1])
    busiest_month, busiest_month_count = months.most_common(1)[0]
    return {
        "first_public_contribution": positive[0][0].isoformat(),
        "last_public_contribution": positive[-1][0].isoformat(),
        "longest_active_streak": {
            "days": len(longest),
            "start": longest[0][0].isoformat(),
            "end": longest[-1][0].isoformat(),
            "contributions": sum(count for _, count in longest),
        },
        "busiest_day": {"date": busiest_day[0].isoformat(), "contributions": busiest_day[1]},
        "busiest_month": {"month": busiest_month, "contributions": busiest_month_count},
    }


class ContributionHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.cells: dict[str, dict[str, Any]] = {}
        self.tooltip_for: str | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if tag == "td" and values.get("data-date"):
            self.cells[values.get("id", values["data-date"])] = {
                "date": values["data-date"],
                "count": 0,
                "level": int(values.get("data-level", "0")),
            }
        if tag == "tool-tip" and values.get("for") in self.cells:
            self.tooltip_for = values["for"]

    def handle_data(self, data: str) -> None:
        if not self.tooltip_for:
            return
        match = re.match(r"([\d,]+) contributions?", data.strip())
        if match:
            self.cells[self.tooltip_for]["count"] = int(match.group(1).replace(",", ""))

    def handle_endtag(self, tag: str) -> None:
        if tag == "tool-tip":
            self.tooltip_for = None


@dataclass
class GitHubClient:
    token: str | None
    refresh: bool = False

    def _headers(self, accept: str = "application/vnd.github+json") -> dict[str, str]:
        headers = {"Accept": accept, "User-Agent": USER_AGENT, "X-GitHub-Api-Version": "2022-11-28"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def get(self, path: str, params: dict[str, Any] | None = None, *, accept: str = "application/vnd.github+json") -> Any:
        query = urllib.parse.urlencode(params or {})
        url = f"{REST_URL}{path}" + (f"?{query}" if query else "")
        key = hashlib.sha256(url.encode()).hexdigest()[:20]
        cached = CACHE / f"rest-{key}.json"
        if cached.exists() and not self.refresh:
            return json.loads(cached.read_text(encoding="utf-8"))
        request = urllib.request.Request(url, headers=self._headers(accept))
        try:
            with urllib.request.urlopen(request, timeout=45) as response:
                payload = json.load(response)
        except (urllib.error.URLError, TimeoutError):
            if cached.exists():
                return json.loads(cached.read_text(encoding="utf-8"))
            raise
        CACHE.mkdir(parents=True, exist_ok=True)
        cached.write_text(json.dumps(payload), encoding="utf-8")
        return payload

    def pages(self, path: str, params: dict[str, Any] | None = None, *, max_pages: int = 10, accept: str = "application/vnd.github+json") -> list[Any]:
        values: list[Any] = []
        base = dict(params or {})
        base["per_page"] = 100
        for page in range(1, max_pages + 1):
            base["page"] = page
            payload = self.get(path, base, accept=accept)
            batch = payload.get("items", []) if isinstance(payload, dict) and "items" in payload else payload
            if not isinstance(batch, list):
                break
            values.extend(batch)
            if len(batch) < 100:
                break
        return values

    def graphql(self, query: str, variables: dict[str, Any]) -> dict[str, Any]:
        if not self.token:
            raise RuntimeError("GraphQL requires GITHUB_TOKEN")
        body = json.dumps({"query": query, "variables": variables}).encode()
        key = hashlib.sha256(body).hexdigest()[:20]
        cached = CACHE / f"graphql-{key}.json"
        if cached.exists() and not self.refresh:
            return json.loads(cached.read_text(encoding="utf-8"))
        request = urllib.request.Request(GRAPHQL_URL, data=body, headers=self._headers())
        with urllib.request.urlopen(request, timeout=60) as response:
            payload = json.load(response)
        if payload.get("errors"):
            raise RuntimeError(json.dumps(payload["errors"]))
        CACHE.mkdir(parents=True, exist_ok=True)
        cached.write_text(json.dumps(payload), encoding="utf-8")
        return payload


GRAPHQL_CONTRIBUTIONS = """
query($login:String!, $from:DateTime!, $to:DateTime!) {
  user(login:$login) {
    contributionsCollection(from:$from, to:$to) {
      restrictedContributionsCount
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount contributionLevel } }
      }
      commitContributionsByRepository(maxRepositories:100) {
        repository { nameWithOwner }
        contributions(first:1) { totalCount }
      }
    }
  }
}
"""


def contribution_calendar(client: GitHubClient, username: str, start_year: int, end_year: int, seed_dir: Path | None) -> tuple[list[dict[str, Any]], dict[str, int], dict[str, dict[str, int]], str]:
    days: dict[str, dict[str, Any]] = {}
    yearly: dict[str, int] = {}
    repository_years: dict[str, dict[str, int]] = defaultdict(dict)
    if client.token:
        for year in range(start_year, end_year + 1):
            payload = client.graphql(
                GRAPHQL_CONTRIBUTIONS,
                {"login": username, "from": f"{year}-01-01T00:00:00Z", "to": f"{year}-12-31T23:59:59Z"},
            )["data"]["user"]["contributionsCollection"]
            for week in payload["contributionCalendar"]["weeks"]:
                for item in week["contributionDays"]:
                    level = contribution_level(item["contributionLevel"])
                    days[item["date"]] = {"date": item["date"], "count": item["contributionCount"], "level": level}
            yearly[str(year)] = payload["contributionCalendar"]["totalContributions"]
            for row in payload["commitContributionsByRepository"]:
                repository_years[row["repository"]["nameWithOwner"]][str(year)] = row["contributions"]["totalCount"]
        return sorted(days.values(), key=lambda item: item["date"]), yearly, dict(repository_years), "github-graphql"

    for year in range(start_year, end_year + 1):
        if seed_dir and (seed_dir / f"ttuff-contributions-{year}.html").exists():
            markup = (seed_dir / f"ttuff-contributions-{year}.html").read_text(encoding="utf-8")
        else:
            url = f"https://github.com/users/{username}/contributions?from={year}-01-01&to={year}-12-31"
            request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(request, timeout=45) as response:
                markup = response.read().decode("utf-8", errors="replace")
        parser = ContributionHTMLParser()
        parser.feed(markup)
        for item in parser.cells.values():
            days[item["date"]] = item
        yearly[str(year)] = sum(item["count"] for item in parser.cells.values())
    return sorted(days.values(), key=lambda item: item["date"]), yearly, {}, "github-public-calendar-fallback"


def normalize_repository(raw: dict[str, Any]) -> dict[str, Any]:
    owner = raw.get("owner") or {}
    license_data = raw.get("license") or {}
    return {
        "full_name": raw.get("full_name") or raw.get("nameWithOwner"),
        "name": raw.get("name"),
        "owner": owner.get("login") or (raw.get("full_name") or "/").split("/", 1)[0],
        "owner_type": owner.get("type"),
        "url": raw.get("html_url") or raw.get("url"),
        "description": raw.get("description"),
        "created_at": raw.get("created_at"),
        "pushed_at": raw.get("pushed_at"),
        "updated_at": raw.get("updated_at"),
        "default_branch": raw.get("default_branch"),
        "primary_language": raw.get("language"),
        "topics": raw.get("topics") or [],
        "stars": raw.get("stargazers_count", 0),
        "forks": raw.get("forks_count", 0),
        "license": license_data.get("spdx_id") if isinstance(license_data, dict) else None,
        "homepage": raw.get("homepage"),
        "fork": bool(raw.get("fork")),
        "archived": bool(raw.get("archived")),
    }


def select_repositories(repositories: dict[str, dict[str, Any]], recent_counts: Counter[str], curated_names: set[str], limit: int) -> list[str]:
    def rank(name: str) -> tuple[int, int, str, str]:
        repo = repositories[name]
        return (
            int(name in curated_names),
            recent_counts[name],
            repo.get("pushed_at") or "",
            name.lower(),
        )
    return sorted(repositories, key=rank, reverse=True)[:limit]


def humanize_repository_name(name: str | None) -> str:
    """Return a readable fallback without pretending a repository is a project."""
    value = re.sub(r"[-_]+", " ", name or "").strip()
    return value[:1].upper() + value[1:] if value else "Untitled repository"


def edge_id(edge: dict[str, Any]) -> str:
    source, target = sorted((edge["source"], edge["target"]))
    return f"{edge['type']}:{source}|{target}"


def deduplicate_edges(edges: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Merge repeated evidence without losing its individual labels."""
    merged: dict[tuple[str, str, str], dict[str, Any]] = {}
    for raw in edges:
        source, target = sorted((raw["source"], raw["target"]))
        key = (raw["type"], source, target)
        label = str(raw.get("label") or raw["type"].replace("-", " "))
        if key not in merged:
            merged[key] = {
                **raw,
                "source": raw["source"],
                "target": raw["target"],
                "evidence": [label],
            }
        elif label not in merged[key]["evidence"]:
            merged[key]["evidence"].append(label)
    result = []
    for edge in merged.values():
        evidence = edge["evidence"]
        edge["weight"] = max(int(edge.get("weight", 1)), len(evidence))
        if len(evidence) > 1 and edge["type"] == "shared-contributor":
            names = [label.removeprefix("Observed contributor: ") for label in evidence]
            edge["label"] = f"Observed contributors: {', '.join(names)}"
        edge["id"] = edge_id(edge)
        result.append(edge)
    return sorted(result, key=lambda item: (item["type"], item["id"]))


def graph_metrics(node_ids: Iterable[str], edges: Iterable[dict[str, Any]]) -> dict[str, Any]:
    """Calculate deterministic unweighted structure plus weighted degree."""
    ids = list(dict.fromkeys(node_ids))
    adjacency: dict[str, set[str]] = {node_id: set() for node_id in ids}
    weighted: Counter[str] = Counter()
    for edge in edges:
        source, target = edge["source"], edge["target"]
        if source not in adjacency or target not in adjacency or source == target:
            continue
        adjacency[source].add(target)
        adjacency[target].add(source)
        weight = int(edge.get("weight", 1))
        weighted[source] += weight
        weighted[target] += weight

    components: list[list[str]] = []
    component_for: dict[str, int] = {}
    for start in ids:
        if start in component_for:
            continue
        index = len(components)
        queue = deque([start])
        component_for[start] = index
        component: list[str] = []
        while queue:
            node = queue.popleft()
            component.append(node)
            for neighbor in sorted(adjacency[node]):
                if neighbor not in component_for:
                    component_for[neighbor] = index
                    queue.append(neighbor)
        components.append(component)

    betweenness = dict.fromkeys(ids, 0.0)
    for source in ids:
        stack: list[str] = []
        predecessors: dict[str, list[str]] = {node: [] for node in ids}
        paths = dict.fromkeys(ids, 0.0)
        paths[source] = 1.0
        distance = dict.fromkeys(ids, -1)
        distance[source] = 0
        queue = deque([source])
        while queue:
            node = queue.popleft()
            stack.append(node)
            for neighbor in adjacency[node]:
                if distance[neighbor] < 0:
                    queue.append(neighbor)
                    distance[neighbor] = distance[node] + 1
                if distance[neighbor] == distance[node] + 1:
                    paths[neighbor] += paths[node]
                    predecessors[neighbor].append(node)
        dependency = dict.fromkeys(ids, 0.0)
        while stack:
            node = stack.pop()
            if paths[node]:
                coefficient = (1.0 + dependency[node]) / paths[node]
                for predecessor in predecessors[node]:
                    dependency[predecessor] += paths[predecessor] * coefficient
            if node != source:
                betweenness[node] += dependency[node]
    scale = 1 / ((len(ids) - 1) * (len(ids) - 2)) if len(ids) > 2 else 0
    return {
        "connected_components": len(components),
        "components": components,
        "nodes": {
            node: {
                "degree": len(adjacency[node]),
                "weighted_degree": weighted[node],
                "betweenness": round(betweenness[node] * scale, 4),
                "component": component_for[node],
            }
            for node in ids
        },
    }


def network_insights(families: list[dict[str, Any]], edges: list[dict[str, Any]]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Turn defensible family-level structure into evidence-linked observations."""
    family_ids = {family["id"] for family in families}
    curated_edges = [
        edge for edge in edges
        if edge["type"] == "curated" and edge["source"] in family_ids and edge["target"] in family_ids
    ]
    metrics = graph_metrics(sorted(family_ids), curated_edges)
    family_by_id = {family["id"]: family for family in families}
    insights: list[dict[str, Any]] = []

    def family_nodes(family: dict[str, Any]) -> list[str]:
        return [family["id"], *family["repositories"]]

    def family_edges(family: dict[str, Any]) -> list[str]:
        nodes = set(family_nodes(family))
        return [edge["id"] for edge in edges if edge["source"] in nodes and edge["target"] in nodes]

    if family_ids:
        bridge_id = max(family_ids, key=lambda node: metrics["nodes"][node]["betweenness"])
        bridge_score = metrics["nodes"][bridge_id]["betweenness"]
        if bridge_score > 0:
            incident = [edge for edge in curated_edges if bridge_id in {edge["source"], edge["target"]}]
            neighbors = sorted({edge["target"] if edge["source"] == bridge_id else edge["source"] for edge in incident})
            family = family_by_id[bridge_id]
            insights.append({
                "id": "bridge-family",
                "type": "Bridge project",
                "title": f"{family['title']} bridges my project map",
                "statement": "This family sits on the largest share of shortest paths between otherwise separate project families in the curated map.",
                "evidence": f"{len(incident)} curated family links · betweenness {bridge_score:.2f}",
                "nodes": [bridge_id, *neighbors],
                "edges": [edge["id"] for edge in incident],
            })

        dated = [family for family in families if family.get("evidence", {}).get("active_from") and family.get("evidence", {}).get("active_to")]
        if dated:
            longest = max(
                dated,
                key=lambda family: (
                    date.fromisoformat(family["evidence"]["active_to"]) - date.fromisoformat(family["evidence"]["active_from"]),
                    len(family["repositories"]),
                ),
            )
            start = longest["evidence"]["active_from"][:4]
            end = longest["evidence"]["active_to"][:4]
            if start != end:
                insights.append({
                    "id": "long-running-thread",
                    "type": "Long-running thread",
                    "title": f"{longest['title']} spans {start}–{end}",
                    "statement": "This is the longest time span represented by repository creation and latest-push dates in the current project map.",
                    "evidence": f"{len(longest['repositories'])} repositories · {start}–{end}",
                    "nodes": family_nodes(longest),
                    "edges": family_edges(longest),
                })

        collaborative = max(families, key=lambda family: family.get("evidence", {}).get("contributor_count", 0))
        contributor_count = collaborative.get("evidence", {}).get("contributor_count", 0)
        if contributor_count >= 2:
            insights.append({
                "id": "collaborative-hub",
                "type": "Observed contributor hub",
                "title": f"{collaborative['title']} has the widest contributor evidence",
                "statement": "GitHub returns more distinct non-bot contributors here than for any other family in this compact dataset.",
                "evidence": f"{contributor_count} observed contributors · {len(collaborative['repositories'])} repositories",
                "nodes": family_nodes(collaborative),
                "edges": family_edges(collaborative),
            })

        cross_owner = max(families, key=lambda family: family.get("evidence", {}).get("owner_count", 0))
        owner_count = cross_owner.get("evidence", {}).get("owner_count", 0)
        if owner_count >= 2:
            insights.append({
                "id": "cross-owner-family",
                "type": "Cross-organization thread",
                "title": f"{cross_owner['title']} crosses GitHub homes",
                "statement": "The repositories I group in this family live under the largest number of distinct GitHub owners in the map.",
                "evidence": f"{owner_count} owners · {len(cross_owner['repositories'])} repositories",
                "nodes": family_nodes(cross_owner),
                "edges": family_edges(cross_owner),
            })
    return metrics, insights


def build_dataset(client: GitHubClient, config: dict[str, Any], *, seed_dir: Path | None = None, limit: int = 40) -> dict[str, Any]:
    username = config["profile"]["username"]
    generated = utc_now()
    today = generated.date()

    if seed_dir and (seed_dir / "ttuff-repos.json").exists():
        raw_repositories = json.loads((seed_dir / "ttuff-repos.json").read_text(encoding="utf-8"))
        recent_items = []
        for path in sorted(seed_dir.glob("ttuff-recent-*.json")):
            recent_items.extend(json.loads(path.read_text(encoding="utf-8")).get("items", []))
        featured = json.loads((seed_dir / "ttuff-featured-details.json").read_text(encoding="utf-8")) if (seed_dir / "ttuff-featured-details.json").exists() else {}
    else:
        raw_repositories = client.pages(f"/users/{username}/repos", {"type": "all", "sort": "updated"}, max_pages=10)
        cutoff = (today - timedelta(days=89)).isoformat()
        recent_items = client.pages(
            "/search/commits",
            {"q": f"author:{username} author-date:>={cutoff}", "sort": "author-date", "order": "desc"},
            max_pages=10,
            accept="application/vnd.github.cloak-preview+json",
        )
        featured = {}

    repositories: dict[str, dict[str, Any]] = {}
    for raw in raw_repositories:
        repo = normalize_repository(raw)
        if repo["full_name"]:
            repositories[repo["full_name"]] = repo

    commits_by_repo: dict[str, list[date]] = defaultdict(list)
    seen_shas: set[str] = set()
    for item in recent_items:
        sha = item.get("sha")
        if sha in seen_shas:
            continue
        seen_shas.add(sha)
        raw_repo = item.get("repository") or {}
        full_name = raw_repo.get("full_name")
        author_date = ((item.get("commit") or {}).get("author") or {}).get("date")
        if not full_name or not author_date:
            continue
        commits_by_repo[full_name].append(iso_date(author_date) or today)
        if full_name not in repositories:
            repositories[full_name] = normalize_repository(raw_repo)

    curated_by_repo: dict[str, dict[str, Any]] = {}
    curated_names: set[str] = set()
    repository_metadata = config.get("repository_metadata", {})
    for family in config["families"]:
        for name in family["repositories"]:
            curated_names.add(name)
            curated_by_repo[name] = {
                "family": family["id"],
                "family_title": family["title"],
                "theme": family["theme"],
                "category": family.get("category", "uncategorized"),
                "featured": family.get("featured", False),
            }
            if name not in repositories and not seed_dir:
                try:
                    repositories[name] = normalize_repository(client.get(f"/repos/{name}"))
                except urllib.error.HTTPError:
                    pass

    recent_counts = Counter({name: len(values) for name, values in commits_by_repo.items()})
    excluded = set(config.get("exclude_repositories", []))
    eligible = {name: repo for name, repo in repositories.items() if name not in excluded}
    selected = select_repositories(eligible, recent_counts, curated_names & eligible.keys(), limit)
    normalized: list[dict[str, Any]] = []
    observed_release_count = 0
    contributor_repositories: dict[str, set[str]] = defaultdict(set)
    contributor_avatars: dict[str, str | None] = {}

    for name in selected:
        repo = repositories[name]
        details = featured.get(name, {})
        if details.get("repo"):
            repo.update(normalize_repository(details["repo"]))
        elif not seed_dir and (not repo.get("created_at") or name in commits_by_repo):
            try:
                repo.update(normalize_repository(client.get(f"/repos/{name}")))
            except urllib.error.HTTPError:
                pass

        def supplement(key: str, endpoint: str, fallback: Any) -> Any:
            if key in details:
                return details[key]
            if seed_dir:
                return fallback
            try:
                return client.get(f"/repos/{name}/{endpoint}", {"per_page": 100})
            except (urllib.error.HTTPError, urllib.error.URLError):
                return fallback

        languages = supplement("languages", "languages", {})
        contributors_raw = supplement("contributors", "contributors", [])
        releases_raw = supplement("releases", "releases", [])
        tags_raw = supplement("tags", "tags", [])
        actions_raw = supplement("actions", "actions/runs", {})
        contributors = []
        if isinstance(contributors_raw, list):
            for person in contributors_raw:
                login = person.get("login") or person.get("name")
                if not login or login.lower() == username.lower() or is_bot(login):
                    continue
                contributors.append({"login": login, "url": person.get("html_url"), "contributions": person.get("contributions")})
                contributor_repositories[login].add(name)
                contributor_avatars[login] = person.get("avatar_url")
        releases = []
        if isinstance(releases_raw, list):
            for release in releases_raw:
                releases.append({"tag": release.get("tag_name"), "name": release.get("name"), "published_at": release.get("published_at"), "url": release.get("html_url")})
        observed_release_count += len(releases)
        release_dates = [value for value in (iso_date(item["published_at"]) for item in releases) if value]
        recent = activity_score(commits_by_repo.get(name, []), release_dates, today)
        run = None
        if isinstance(actions_raw, dict) and actions_raw.get("workflow_runs"):
            latest = actions_raw["workflow_runs"][0]
            run = {"status": latest.get("status"), "conclusion": latest.get("conclusion"), "name": latest.get("name"), "url": latest.get("html_url"), "updated_at": latest.get("updated_at")}
        semantic = repository_metadata.get(name, {})
        family_semantic = curated_by_repo.get(name) or {}
        repo.update(
            {
                "languages": languages if isinstance(languages, dict) else {},
                "contributors": contributors[:20],
                "contributor_count_observed": len(contributors),
                "releases": releases[:10],
                "release_count_observed": len(releases),
                "latest_release": releases[0] if releases else None,
                "tag_count_observed": len(tags_raw) if isinstance(tags_raw, list) else 0,
                "ci": run,
                "recent": {**recent, "sparkline": weekly_sparkline(commits_by_repo.get(name, []), today)},
                "curated": family_semantic or None,
                "semantic": {
                    "title": semantic.get("title") or humanize_repository_name(repo.get("name")),
                    "description": semantic.get("description") or repo.get("description") or None,
                    "source": "curated" if semantic else ("github" if repo.get("description") else "fallback"),
                },
            }
        )
        normalized.append(repo)

    calendar, yearly, repository_years, calendar_source = contribution_calendar(client, username, 2016, today.year, seed_dir)
    calendar = [item for item in calendar if item["date"] <= today.isoformat()]
    yearly = {
        year: sum(item["count"] for item in calendar if item["date"].startswith(f"{year}-"))
        for year in yearly
    }
    for repo in normalized:
        repo["contribution_years"] = repository_years.get(repo["full_name"], {})

    repeated = []
    all_people = []
    for login, repo_names in contributor_repositories.items():
        row = {"login": login, "avatar": contributor_avatars.get(login), "repository_count": len(repo_names), "repositories": sorted(repo_names)}
        all_people.append(row)
        if len(repo_names) >= 2:
            repeated.append(row)
    repeated.sort(key=lambda item: (-item["repository_count"], item["login"].lower()))
    all_people.sort(key=lambda item: (-item["repository_count"], item["login"].lower()))

    family_payload = []
    graph_nodes = []
    raw_graph_edges = []
    selected_names = {repo["full_name"] for repo in normalized}
    normalized_by_name = {repo["full_name"]: repo for repo in normalized}
    my_owners = {username, *config.get("profile", {}).get("important_owners", [])}
    for family in config["families"]:
        members = [name for name in family["repositories"] if name in selected_names]
        if not members:
            continue
        member_repositories = [normalized_by_name[name] for name in members]
        contributor_names = sorted({person["login"] for repo in member_repositories for person in repo.get("contributors", [])})
        member_owners = sorted({repo["owner"] for repo in member_repositories if repo.get("owner")})
        member_organizations = sorted({repo["owner"] for repo in member_repositories if repo.get("owner_type") == "Organization"})
        starts = sorted((repo.get("created_at") or "")[:10] for repo in member_repositories if repo.get("created_at"))
        ends = sorted((repo.get("pushed_at") or repo.get("created_at") or "")[:10] for repo in member_repositories if repo.get("pushed_at") or repo.get("created_at"))
        evidence = {
            "repository_count": len(members),
            "contributor_count": len(contributor_names),
            "contributors": contributor_names,
            "organization_count": len(member_organizations),
            "organizations": member_organizations,
            "owner_count": len(member_owners),
            "owners": member_owners,
            "active_from": starts[0] if starts else None,
            "active_to": ends[-1] if ends else None,
        }
        family_payload.append({**family, "repositories": members, "evidence": evidence})
        graph_nodes.append({
            "id": family["id"],
            "type": "family",
            "label": family["title"],
            "description": family["description"],
            "theme": family["theme"],
            "category": family.get("category", "uncategorized"),
            "question": family.get("question"),
            "topics": family.get("topics", []),
        })
        for name in members:
            raw_graph_edges.append({"source": family["id"], "target": name, "type": "family", "label": f"Repository evidence for {family['title']}", "weight": 1})
    for repo in normalized:
        curated = repo.get("curated") or {}
        graph_nodes.append({
            "id": repo["full_name"],
            "type": "repository",
            "label": repo["semantic"]["title"],
            "description": repo["semantic"]["description"],
            "owner": repo["owner"],
            "ownership": "mine" if repo["owner"] in my_owners else "external",
            "family": curated.get("family"),
            "category": curated.get("category", "uncategorized"),
            "activity": repo["recent"]["score"],
        })
    available_families = {family["id"] for family in family_payload}
    for edge in config.get("relationships", []):
        if edge["from"] in available_families and edge["to"] in available_families:
            raw_graph_edges.append({"source": edge["from"], "target": edge["to"], "type": "curated", "label": edge["label"], "weight": 2})
    for person in repeated:
        names = person["repositories"]
        for index, source in enumerate(names):
            for target in names[index + 1 :]:
                raw_graph_edges.append({"source": source, "target": target, "type": "shared-contributor", "label": f"Observed contributor: {person['login']}", "weight": 1})
    graph_edges = deduplicate_edges(raw_graph_edges)
    network_metrics = graph_metrics((node["id"] for node in graph_nodes), graph_edges)
    for node in graph_nodes:
        node["metrics"] = network_metrics["nodes"][node["id"]]
    family_metrics, insights = network_insights(family_payload, graph_edges)

    owners = sorted({repo["owner"] for repo in repositories.values() if repo.get("owner")})
    organizations = sorted(
        {repo["owner"] for repo in repositories.values() if repo.get("owner_type") == "Organization"}
    )
    language_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for repo in normalized:
        language = repo.get("primary_language") or "Unclassified"
        created = (repo.get("created_at") or "")[:10] or None
        pushed = (repo.get("pushed_at") or "")[:10] or created
        if pushed and pushed < created:
            pushed = created
        if created:
            language_groups[language].append({"repository": repo["full_name"], "start": created, "end": pushed})
    language_evolution = [
        {"language": language, "repositories": sorted(rows, key=lambda row: row["start"])}
        for language, rows in sorted(language_groups.items(), key=lambda item: (-len(item[1]), item[0]))
    ]

    discoveries = calendar_discoveries(calendar)
    month_repositories: dict[str, set[str]] = defaultdict(set)
    for name, values in commits_by_repo.items():
        for value in values:
            month_repositories[value.strftime("%Y-%m")].add(name)
    if month_repositories:
        month, names = max(month_repositories.items(), key=lambda item: len(item[1]))
        discoveries["widest_recent_month"] = {"month": month, "repositories": len(names), "names": sorted(names)}

    active_since = discoveries.get("first_public_contribution") or (min((repo["created_at"] for repo in normalized if repo.get("created_at")), default="")[:10] or None)
    total_contributions = sum(int(value) for value in yearly.values())
    graph_repository_names = {node["id"] for node in graph_nodes if node["type"] == "repository"}
    graph_repositories = [normalized_by_name[name] for name in graph_repository_names]
    graph_dates = sorted(
        (repo.get("created_at") or "")[:10]
        for repo in graph_repositories
        if repo.get("created_at")
    )
    graph_end_dates = sorted(
        (repo.get("pushed_at") or repo.get("created_at") or "")[:10]
        for repo in graph_repositories
        if repo.get("pushed_at") or repo.get("created_at")
    )
    graph_organizations = sorted({repo["owner"] for repo in graph_repositories if repo.get("owner_type") == "Organization"})
    return {
        "meta": {
            "schema_version": SCHEMA_VERSION,
            "generated_at": generated.isoformat().replace("+00:00", "Z"),
            "username": username,
            "refresh_mode": "authenticated-graphql-and-rest" if client.token else calendar_source,
            "source_types": ["GitHub REST API", "GitHub GraphQL API" if client.token else "GitHub public contribution calendar", "Curated project metadata"],
            "methodology_url": "/docs/github-life-design.md",
            "source_url": "https://github.com/ttuff/personal_website",
        },
        "profile": {"login": username, "url": f"https://github.com/{username}"},
        "summary": {
            "active_since": active_since,
            "public_calendar_contributions": total_contributions,
            "public_active_days": sum(1 for item in calendar if item["count"] > 0),
            "repositories_discovered": len(repositories),
            "repositories_in_page": len(normalized),
            "owners_observed": len(owners),
            "organizations_observed": len(organizations),
            "organization_names": organizations,
            "releases_observed": observed_release_count,
            "contributors_observed": len(all_people),
            "repeated_contributors_observed": len(repeated),
        },
        "contributions": {"days": calendar, "yearly": yearly, "source": calendar_source},
        "repositories": sorted(normalized, key=lambda repo: (-repo["recent"]["score"], repo["full_name"].lower())),
        "families": family_payload,
        "graph": {
            "nodes": graph_nodes,
            "edges": graph_edges,
            "metrics": {
                "connected_components": network_metrics["connected_components"],
                "family_connected_components": family_metrics["connected_components"],
            },
            "summary": {
                "repositories": len(graph_repository_names),
                "families": len(family_payload),
                "contributors": len({person["login"] for repo in graph_repositories for person in repo.get("contributors", [])}),
                "organizations": len(graph_organizations),
                "active_from": graph_dates[0] if graph_dates else None,
                "active_to": graph_end_dates[-1] if graph_end_dates else None,
            },
            "insights": insights,
        },
        "collaboration": {"contributors": all_people[:40], "repeated": repeated[:20]},
        "language_evolution": language_evolution,
        "discoveries": discoveries,
        "methodology": {
            "activity_score": "5 × active days (30d) + 3 × commits (0–30d) + 2 × commits (31–60d) + commits (61–90d) + 6 × releases (90d)",
            "active_repository": "I call a repository active when GitHub returns at least one public commit authored by me in the trailing 90 days.",
            "observed_contributor": "I use ‘observed contributor’ for a non-bot identity returned by GitHub's contributors endpoint for a repository in this dataset.",
        },
        "limitations": [
            "My repository set combines public repository discovery, recent authored-commit search, and project names I curated; it may not include every repository in my history.",
            "I use GitHub's contribution calendar, which can include commits, issues, pull requests, and reviews; I do not present it as my lifetime commit count.",
            "My recent commit counts include only public commits GitHub attributes to the ttuff author identity, and I bound search results to 90 days.",
            "I use contributor lists to describe GitHub repository contributors, not necessarily my direct collaborators or complete project teams.",
            "I use current default-branch language bytes as context; they do not measure my effort or proficiency.",
            "When CI, release, license, or package data is missing, I treat it as unavailable in the GitHub surface I queried—not as proof that none exists elsewhere.",
        ],
    }


def write_if_changed(path: Path, payload: dict[str, Any]) -> bool:
    content = json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n"
    if path.exists() and path.read_text(encoding="utf-8") == content:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh", action="store_true", help="Ignore cached API responses")
    parser.add_argument("--seed-dir", type=Path, help="Build from previously captured public payloads")
    parser.add_argument("--max-repositories", type=int, default=40)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    dataset = build_dataset(GitHubClient(token=token, refresh=args.refresh), config, seed_dir=args.seed_dir, limit=args.max_repositories)
    changed = write_if_changed(args.output, dataset)
    print(f"{'Updated' if changed else 'Unchanged'} {args.output.relative_to(ROOT)} with {len(dataset['repositories'])} repositories and {len(dataset['contributions']['days'])} calendar days.")


if __name__ == "__main__":
    main()
