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

## Deployment

Pushes to `main` run `.github/workflows/pages.yml`, validate the build, and deploy `site/` to GitHub Pages. Configure the repository’s Pages source as **GitHub Actions**.

The expected project URL is `https://ttuff.github.io/personal_website/`.

No `CNAME` is included. Keep the custom domain on Squarespace until the GitHub Pages version has passed visual and functional review.

## Migration records

- `migration/site_inventory.json` — machine-readable page/content inventory
- `migration/site_inventory.md` — human-readable page summary
- `migration/asset_manifest.csv` — recovered asset provenance and file metadata
- `migration/design_inventory.md` — measured live-site design system
- `migration/migration_report.md` — scope, differences, and remaining manual work
- `migration/source/` — preserved raw source material
