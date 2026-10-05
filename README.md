# drtuff.com

Static reconstruction of [drtuff.com](https://www.drtuff.com), migrated from Squarespace for deployment on GitHub Pages.

The live Squarespace site remains the source of truth until DNS is moved. Its public HTML, sitemap, robots rules, CSS, page inventory, design measurements, and original-resolution first-party assets are preserved under `migration/` and `assets/`.

## Build and validate

```bash
python3 scripts/validate_site.py
```

The build is written to `site/`. Preview it locally with:

```bash
python3 -m http.server 8000 --directory site
```

Then open `http://127.0.0.1:8000`.

The capability-led project narrative is available at `http://127.0.0.1:8000/my-projects/`, and the data-driven Connections narrative is at `http://127.0.0.1:8000/github/`. They share a checked-in compact dataset generated from public GitHub data and a small editorial layer; the curated first-person project stories remain in `data/github-projects.yml`.

```bash
GITHUB_TOKEN=... python3 scripts/build_github_life.py --refresh
python3 -m unittest discover -s tests -v
python3 scripts/validate_site.py
```

`GITHUB_TOKEN` is required for the GraphQL contribution calendar and normal authenticated API limits. The browser never receives the token. Without a token, the generator can use GitHub's public contribution calendar as a local fallback. Edit `data/github-projects.yml` to change human-readable repository metadata, project families, capability stories, technology associations, research questions, importance, or curated relationships; see `docs/github-life-design.md` for graph definitions, metric provenance, and limitations and `docs/projects-page-design.md` for the portfolio design and asset provenance.

## Deployment

Pushes to `main` run `.github/workflows/pages.yml`, validate the build, and deploy `site/` to GitHub Pages. `.github/workflows/github-life.yml` refreshes the GitHub-life dataset daily, tests and validates it, commits only the compact derived JSON when it changes, and deploys the refreshed artifact directly. The refresh workflow does not run on pushes, so its generated commit cannot trigger a refresh loop. Configure the repository’s Pages source as **GitHub Actions**.

The production URL is `https://drtuff.com/`. The tracked root `CNAME` contains `drtuff.com`, and the build copies it into the deployed `site/` artifact. With a custom GitHub Actions Pages workflow, GitHub’s repository **Settings → Pages → Custom domain** value is authoritative (GitHub ignores artifact `CNAME` files); the retained file is a portable declaration and regression check. Canonical, OpenGraph, Twitter, structured-data, sitemap, and robots URLs are generated for the apex domain.

The compatibility paths `/about` and `/research` redirect to the canonical home/about and science destinations. Keep the existing Squarespace DNS records in place until the GitHub Pages workflow has been pushed, the custom domain is registered in the repository Pages settings, and the deployed artifact has been reviewed.

The intended HostGator DNS records are four apex `A` records for GitHub Pages (`185.199.108.153` through `185.199.111.153`) and `CNAME www ttuff.github.io`. DNS is deliberately not managed by this repository.

## Migration records

- `migration/site_inventory.json` — machine-readable page/content inventory
- `migration/site_inventory.md` — human-readable page summary
- `migration/asset_manifest.csv` — recovered asset provenance and file metadata
- `migration/design_inventory.md` — measured live-site design system
- `migration/fidelity_audit.md` — matched-viewport live/local comparison results
- `migration/migration_report.md` — scope, differences, and remaining manual work
- `migration/source/` — preserved raw source material
- `docs/github-life-design.md` — GitHub-life architecture, provenance, derived metrics, and API limitations
- `docs/projects-page-design.md` — project-page design, data boundaries, review notes, and visual provenance
- `data/github-projects.yml` — human-editable project families, capability stories, and relationships
- `data/generated/github-life.json` — compact generated dataset consumed by `/github/` and `/my-projects/`
