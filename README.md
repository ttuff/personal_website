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
node --test tests/test_analytics.mjs
python3 scripts/validate_site.py
```

`GITHUB_TOKEN` is required for the GraphQL contribution calendar and normal authenticated API limits. The browser never receives the token. Without a token, the generator can use GitHub's public contribution calendar as a local fallback. Edit `data/github-projects.yml` to change human-readable repository metadata, project families, canonical project websites, gallery screenshots, evidence-backed metrics, technology associations, research questions, importance, or curated relationships; see `docs/github-life-design.md` for graph definitions, metric provenance, and limitations and `docs/projects-page-design.md` for the portfolio design, screenshot-refresh command, and asset provenance.

## Deployment

Pushes to `main` run `.github/workflows/pages.yml`, validate the build, and deploy `site/` to GitHub Pages. `.github/workflows/github-life.yml` refreshes the GitHub-life dataset daily, tests and validates it, commits only the compact derived JSON when it changes, and deploys the refreshed artifact directly. The refresh workflow does not run on pushes, so its generated commit cannot trigger a refresh loop. Configure the repository’s Pages source as **GitHub Actions**.

The production URL is `https://drtuff.com/`. The tracked root `CNAME` contains `drtuff.com`, and the build copies it into the deployed `site/` artifact. With a custom GitHub Actions Pages workflow, GitHub’s repository **Settings → Pages → Custom domain** value is authoritative (GitHub ignores artifact `CNAME` files); the retained file is a portable declaration and regression check. Canonical, OpenGraph, Twitter, structured-data, sitemap, and robots URLs are generated for the apex domain.

The compatibility paths `/home`, `/about`, and `/research` redirect to the canonical root/about and science destinations. The empty `/news` route remains available for compatibility but is marked `noindex` and omitted from the sitemap until it has published content. Keep the existing Squarespace DNS records in place until the GitHub Pages workflow has been pushed, the custom domain is registered in the repository Pages settings, and the deployed artifact has been reviewed.

The intended HostGator DNS records are four apex `A` records for GitHub Pages (`185.199.108.153` through `185.199.111.153`) and `CNAME www ttuff.github.io`. DNS is deliberately not managed by this repository.

## Analytics and Search Console

GA4 is configured once in `scripts/build_static_site.py`:

```python
GA_MEASUREMENT_ID = "G-XXXXXXXXXX"
```

In Google Analytics, create or select a GA4 property and a Web data stream for `https://drtuff.com`. Find the ID under **Admin → Data streams → Web → your stream → Measurement ID**, then replace `G-XXXXXXXXXX` above with the real `G-...` value. Measurement IDs are public identifiers, not secrets. Until the placeholder is replaced, analytics remains disabled.

The shared page builder places one `static/scripts/analytics.js` loader in every canonical page head. Redirect-only compatibility pages intentionally omit it so a redirect and its destination cannot produce two page views. The runtime loads `gtag.js` asynchronously only when the browser hostname is exactly `drtuff.com`; localhost, `127.0.0.1`, `ttuff.github.io`, preview servers, and build jobs send nothing. This is a traditional multi-page site, so it sends one explicit `page_view` per page load and does not install client-router tracking.

The runtime also records:

- `file_download` for PDF links, with `file_category` set to `cv` or `other_pdf`;
- `outbound_click` for external links, categorized as `github`, `google_scholar`, `orcid`, `external_project`, or `outbound`;
- `project_visit` for a project-gallery website action;
- `project_github_click` for a project-gallery repository action.

The project events include `project_name`, a query-free `destination_url`, `destination_domain`, `source_page`, and `link_type`. Project-site links also carry non-personal UTM parameters (`utm_source=drtuff.com`, `utm_medium=referral`, `utm_campaign=project_gallery`, and the project id as `utm_content`) so independently configured project analytics can identify traffic from this portfolio. A project action emits its specific event instead of an additional generic outbound event.

Generic outbound event URLs contain only the destination origin. Project events add the public project path but remove query strings and fragments. The integration does not collect form contents, email addresses, personal names, filenames, link text, user IDs, referrers, or advertising signals. GA4 still uses cookies and transfers usage data to Google, so add an appropriate privacy notice and assess whether consent controls are required for the jurisdictions where visitors are located. To avoid measuring the same PDF or outbound interaction through two mechanisms, disable **Outbound clicks** and **File downloads** under the stream's Enhanced Measurement settings; the custom events above remain active.

After deployment, verify the tag with [Google Tag Assistant](https://tagassistant.google.com/) against `https://drtuff.com`, confirm a single `gtag/js` request in the browser Network panel, and use GA4 Realtime to test a page view, an external link, and any PDF link. Local previews are intentionally unsuitable for live-event testing. The deployment validator confirms that each canonical page contains one shared analytics configuration and that aliases contain none; `tests/test_analytics.mjs` covers the hostname guard, single page view, internal/outbound classification, privacy-safe URLs, and PDF events.

No Search Console verification token is currently stored in this repository. Create a Search Console **Domain property** named exactly `drtuff.com`—without `https://`, `www`, a path, or a trailing slash. A Domain property is preferable here because it covers the apex domain, `www`, and all protocols with one verification. In Search Console, choose DNS verification and copy the unique value Google provides. In HostGator's DNS editor, add this record without changing the existing GitHub Pages A or CNAME records:

| DNS field | Value |
| --- | --- |
| Type | `TXT` |
| Name/Host | `@` (or blank if HostGator represents the root that way) |
| Value | `google-site-verification=GOOGLE_PROVIDED_VALUE` |
| TTL | HostGator's default |

`GOOGLE_PROVIDED_VALUE` is a placeholder for the exact value shown by Search Console; do not enter that literal placeholder or invent a token. After the record resolves, click **Verify** and leave the TXT record in DNS so ownership remains verified. Then open **Sitemaps**, enter `sitemap.xml`, and submit `https://drtuff.com/sitemap.xml`.

If DNS access is unavailable, create the narrower URL-prefix property `https://drtuff.com/`, select Google's HTML-tag method, and paste only the tag's `content` value into `GOOGLE_SITE_VERIFICATION` beside the GA4 setting in `scripts/build_static_site.py`. The build will place one verification tag in every canonical page head without changing the visible site. Do not replace an existing valid token.

`sitemap.xml` and `robots.txt` are generated into `site/` by `scripts/build_static_site.py`; both use the canonical `https://drtuff.com` origin. The sitemap includes only the seven canonical, indexable public routes and excludes redirect aliases and the empty, noindex News route. Every canonical page gets a self-referencing HTTPS canonical, Open Graph and Twitter preview metadata, a favicon, and JSON-LD. The homepage is a `ProfilePage` about a `Person`; its GitHub, Google Scholar, and ResearchGate identities come from links already published on the site. Other pages remain simple `WebPage` entities. The aggregate Projects and Connections pages intentionally do not claim `SoftwareSourceCode`, `Dataset`, or `ScholarlyArticle` entities; those types should be added only when stable detail pages have complete authorship, licensing, and canonical metadata.

Run the complete local check with:

```bash
python3 -m unittest discover -s tests -v
node --test tests/test_analytics.mjs
python3 scripts/validate_site.py
```

The checks rebuild the site, parse sitemap XML and JSON-LD, verify robots rules, internal references, unique titles, nonempty descriptions and H1s, canonical and social URLs, favicon assets, redirect/noindex behavior, and the absence of `localhost` or `ttuff.github.io` deployment metadata. After deployment, also inspect representative URLs in Search Console's URL Inspection tool and test the homepage with Google's Rich Results Test.

Once Search Console and GA4 are both collecting data, link them in GA4 under **Admin → Product links → Search Console Links → Link**. Select the verified `drtuff.com` property and the `https://drtuff.com` web stream, review, and submit. This is an account-level Google configuration rather than repository code; the Google account must be a verified Search Console owner and have at least Editor access to the GA4 property.

### Independent project analytics and search

Treat each major project website as its own measurement and search property. The recommended GA4 Standard arrangement is one Analytics account with one GA4 property and one production web stream for each independently published project site. This keeps data ownership, access, retention, Search Console linking, and project growth separate; it also follows Google's normal one-web-stream-per-property guidance. Use consistent event names and UTM conventions across properties, then compare projects in Looker Studio or an exported reporting dataset. Native roll-up properties require Analytics 360.

A single shared portfolio property with one stream per site is lower maintenance and can support cross-domain journeys, but it blends governance and reporting, makes independent Search Console relationships less clean, and is a weaker fit when project sites live under different organizations. Use that alternative only if all sites have the same owner, privacy policy, access group, retention rules, and measurement plan. Do not reuse the personal-site Measurement ID automatically; install each project’s own ID in that project’s repository.

In Search Console, add every independently published project site as its own property and submit that site’s own sitemap. Prefer a Domain property when you control the project’s DNS. For organization-hosted GitHub Pages sites such as `cu-esiil.github.io/project/`, where the project is a path under a shared host and DNS is not yours, use an exact URL-prefix property such as `https://cu-esiil.github.io/cubedynamics/` and verify through a supported site-level method available to that repository. Keep external project URLs out of `drtuff.com/sitemap.xml`; descriptive gallery links establish the relationship without claiming those sites as part of the personal domain.

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
