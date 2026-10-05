# GitHub life page: investigation and design

## Existing site architecture

The site is a dependency-free static build deployed to GitHub Pages. `scripts/build_static_site.py` transforms six preserved Squarespace page bodies into complete HTML documents, copies shared assets from `static/` and `assets/`, and writes the deployable `site/` directory. `scripts/validate_site.py` rebuilds the site and checks routes, local references, production metadata, the custom domain, and the absence of Squarespace runtime dependencies. `.github/workflows/pages.yml` validates and deploys the generated artifact on pushes to `main`.

The shared visual system uses a `#f9f9f9` paper ground, `#51a7f9` blue accent, `#132a3f` navy, Proxima Nova/body fallbacks, and Permanent Marker headings. Desktop navigation overlays image heroes; mobile switches at 640px to a fixed black bar and disclosure menu. Existing JavaScript is dependency-free and progressively enhances that menu. The new page keeps those global elements, uses the same tokens and type, and adds page-scoped CSS/JavaScript rather than altering the preserved page bodies.

## Public GitHub footprint observed

The investigation was performed on 2026-10-04 against the public `ttuff` account, public repository metadata, public commit search, and public contribution calendars. The account was created on 2016-06-14. GitHub's repository endpoint exposed 51 repositories owned by or associated with the account at investigation time, spanning `ttuff`, `CU-ESIIL`, `earthlab`, `lter`, `Curbcut`, `cu-esiil-edu`, and several collaborator-owned repositories. This is a discovery set, not a claim of ownership.

Public commit search returned 4,868 matches at investigation time and 213 commits in the trailing 90-day window. Those recent commits touched 25 repositories. The highest 90-day counts were `CU-ESIIL/cubedynamics` (81), `earthlab/spectralbridge` (49), and `CU-ESIIL/fire_vase` (23). The same period also showed active work across ESIIL infrastructure, OASIS, research-agent infrastructure, wildfire projects, and five Open Life Science hackathon group repositories.

The public contribution calendar exposed 5,848 contributions on 435 active days from 2016-06-14 through 2026-09-30. This is the public GitHub calendar total, which can include commits, issues, pull requests, and reviews and can omit work GitHub cannot attribute to the account. The strongest observed calendar years were 2025 (2,699) and 2026 through the refresh date (1,644). The longest observed run of consecutive active days was 20 days from 2026-08-24 through 2026-09-12. September 2025 was the highest observed calendar month (718). These values are generated discoveries, not hand-written page copy.

The most active repositories reinforce a connected story rather than a collection of isolated demos:

- CubeDynamics combines a published site, Python code, notebooks, release candidates, and an MIT license.
- SpectralBridge is a cross-sensor calibration tool with multiple contributors, releases, and documentation.
- Fire Vase and spread-vs-growth connect environmental data infrastructure to wildfire and growth questions.
- OASIS links reusable working-group infrastructure with a multi-contributor hackathon template.
- ESIIL's data library, analytics library, documentation, organization site, and working-group guide form a shared infrastructure layer.
- `cft`, `eddi`, and `leri` form an earlier R-centered climate-index lineage.

## Data inventory and provenance

| Data class | Build source | Reliability and use |
| --- | --- | --- |
| Account metadata | REST `GET /users/{username}` | Exact public account fields at refresh time. |
| Repository discovery | REST user repositories, recent commit search, and curated repository names | A public observation set; not guaranteed to include every historical repository. |
| Repository facts | REST repository endpoint | Names, owners, dates, descriptions, default branches, stars, forks, topics, license, homepage, archive/fork state. |
| Languages | REST repository languages endpoint | GitHub Linguist byte counts for the default branch, not developer time or proficiency. |
| Recent activity | REST commit search for commits authored by `ttuff` | Public, author-attributed commits only. Counts can differ from the contribution calendar. |
| Career contribution calendar | GraphQL `contributionsCollection.contributionCalendar`; public calendar HTML is a local fallback | Calendar events GitHub attributes to the account. Missing data are marked unavailable, never converted to zero. |
| Contributors | REST contributors endpoint | Repository contributors according to GitHub; the page calls them observed contributors, not collaborators. Anonymous/bot entries are excluded from the people summary. |
| Releases | REST releases endpoint | Published GitHub releases visible to the build token. |
| Tags | REST tags endpoint | Visible repository tags; a tag is not treated as a release. |
| CI status | REST Actions runs endpoint | Latest visible run on the default branch. Absence can mean no Actions workflow or inaccessible data. |
| Project meaning | `data/github-projects.yml` | Human-edited repository titles/descriptions, families, conceptual categories, research questions, topics, importance, and intellectual relationships. |

## Derived definitions

Recent activity is deliberately not a pure "last push" sort. For repository `r`:

`score(r) = 5 × active_days_30 + 3 × commits_30 + 2 × commits_days_31_to_60 + commits_days_61_to_90 + 6 × releases_90`

The active-day term rewards continuity, the step-down windows reward recency without erasing sustained work, and the release term recognizes shipped milestones. Counts are capped only for display, not calculation. Search results are deduplicated by commit SHA. The page displays the formula in its methodology panel.

An active repository has at least one observed authored commit in the trailing 90 days. "Observed contributors" are non-bot contributor identities returned for the repositories included in the compact dataset. A repeated contributor appears in two or more included repositories. Neither label asserts employment, direct collaboration, or complete contribution history.

Graph edges have one of three explicit evidence types:

1. `curated`: an intellectual or project relationship declared in `data/github-projects.yml`;
2. `family`: repositories assigned to the same curated project family;
3. `shared-contributor`: at least one non-bot GitHub contributor appears in both repositories.

Same-owner and same-language edges are not emitted by themselves because they make the graph dense without proving a useful relationship.

The intellectual map separates two kinds of structure. Conceptual categories (`research-questions`, `methods-software`, `infrastructure`, and `communities`) provide the primary reading of the work. Evidence types (`curated`, `family`, and `shared-contributor`) remain a secondary filter so the interface never implies that an editorial relationship was inferred from GitHub activity. Repositories owned by `ttuff` or an explicitly listed important owner are marked as "mine"; the rest are shown as connected repositories, not as owned work.

Graph metrics are deterministic build products, not claims about importance:

- degree counts distinct adjacent nodes;
- weighted degree sums the normalized weights of adjacent evidence links;
- betweenness is the normalized share of shortest paths that pass through a node in the undirected evidence graph;
- connected components describe reachability in the full graph and in the family-only intellectual map.

The build also emits a small set of reproducible insights: the family with the highest family-level betweenness, the longest observed repository span, the widest observed contributor set, and the widest observed owner set. Each insight stores the exact node and edge identifiers it highlights, so the prose and interaction share the same evidence.

## Proposed compact schema

The generated `data/generated/github-life.json` contains:

- `meta`: schema version, generation time, source URLs/types, refresh mode, and coverage notes;
- `profile` and `summary`: public account facts and defensible top-level counts;
- `contributions`: compact daily calendar cells and yearly totals;
- `repositories`: normalized facts, recent counts, score, small sparklines, languages, releases, contributors, CI, and optional curated family fields;
- `families`: editorial groupings with category, question, topics, and compact evidence summaries;
- `graph`: schema-v2 nodes and deduplicated typed edges, ownership classes, metrics, summary counts, and evidence-linked insights;
- `portfolio`: curated capability stories joined to repository facts, technology evidence, principles, and a compact Connections preview;
- `collaboration`: repeated observed contributors and the repositories connecting them;
- `language_evolution`: repository start/last-push spans grouped by primary language;
- `discoveries`: reproducibly calculated streak, busiest day/month, and concurrent-project facts;
- `limitations`: plain-language qualifications rendered on the page.

Raw API payloads belong in `.cache/github-life/` and are ignored. The browser receives only the compact derived JSON. The Connections and My Projects pages share this file; first-person project narrative remains in the curated source rather than being inferred from API metadata.

`exclude_repositories` in the curated file can remove obvious scratch repositories from the narrative without pretending they were never discovered; discovery counts remain based on the complete observed set.

## Visualization and interaction plan

1. A dark opening field establishes the public time span, public calendar total, discovered repositories, observed owners, and releases, with refresh provenance adjacent to the values.
2. A ranked current-work stream shows score components and 90-day sparklines. It is a list, not a wall of equal cards.
3. A career heatmap uses one row per year, explicit daily cells, keyboard-selectable days, and an adjacent yearly activity trace. Missing periods use a separate unknown treatment; they are not colored as zero.
4. An intellectual map uses stable category columns and curated family anchors on desktop. Family names remain visible; quieter repository labels appear on hover, focus, or selection. Conceptual categories are the primary filters and typed evidence is available as a secondary filter. Selecting a node or generated insight exposes the supporting repositories, people, organizations, owners, dates, and exact links. Mobile receives the same family narrative and evidence as an expandable list instead of a shrunken graph.
5. Repository detail is driven by graph/list selection and foregrounds activity, lifespan, contributors, releases, license, documentation, and CI before stars or forks.
6. Collaboration is shown as people who recur across included repositories and the repository paths connecting them.
7. Language evolution uses repository lifespan lanes based on creation and last-push dates. The label explicitly states that a span is not proof of continuous activity.
8. A native dialog command palette opened by Cmd-K/Ctrl-K searches repositories, owners, years, languages, topics, and project families and scrolls to or selects the result.
9. The final machinery section names each build stage and links to source, generated data, methodology, and the website repository.

All essential detail is available by click/focus rather than hover alone. Immediate neighbors are highlighted while unrelated nodes recede; Escape or the graph background clears the selection. Motion is minimal and disabled under `prefers-reduced-motion`. SVGs are responsive; the graph is replaced rather than miniaturized on narrow screens.

## API limitations

- GitHub has no single REST endpoint for a user's complete cross-organization contribution history. Repository discovery is therefore the union of multiple public sources and curated names.
- Search API results are capped at 1,000 per query. The pipeline uses bounded recent windows; it does not claim lifetime commit totals from search.
- The contribution calendar is GitHub's attribution model, not a raw commit count. Private contributions, commits using unmatched email addresses, non-default-branch commits, and deleted/transferred repositories may be absent or aggregated.
- Repository `pushed_at` can reflect another contributor and is not used as evidence that `ttuff` was active.
- Language bytes describe the current default branch and generated/documentation content can dominate. They do not measure effort.
- GitHub's contributor endpoint can be incomplete for very large histories, can include bots, and does not establish a direct working relationship. The interface uses precise "observed contributor" wording.
- REST release and Actions endpoints report GitHub-native objects only. Packages published elsewhere and external CI systems may be absent.
- GraphQL and higher REST limits require a token during the scheduled build. No token or raw API response is shipped to the browser.

## Performance and automation

The generated JSON is compacted before commit. Calendar data are one small record per day; repository contributor lists and graph nodes are capped after ranking. The page has no runtime GitHub requests and needs no backend. The relationship graph is initialized when it approaches the viewport. The scheduled workflow runs daily, writes only when derived data change, and its generated-data commit triggers the existing Pages workflow. Because the refresh workflow itself does not run on pushes, generated commits cannot recursively trigger another refresh.

## Implementation sequence

1. Add the curated project file, generator, deterministic transformation tests, and compact checked-in dataset.
2. Add a purpose-built `/github/` source page, page-scoped CSS/JavaScript, navigation entry, sitemap route, and validation coverage.
3. Render and inspect desktop/mobile states using the generated data; remove views that do not add evidence.
4. Add the scheduled refresh workflow, documentation, changelog entry, and local preview instructions.
