# Custom-domain preflight

## Production contract

- Canonical origin: `https://drtuff.com`
- GitHub Pages artifact: `site/`
- Source custom-domain file: `CNAME`
- Artifact custom-domain file: `site/CNAME`
- Authoritative GitHub configuration for this Actions deployment: repository **Settings → Pages → Custom domain** must be `drtuff.com`; GitHub ignores artifact `CNAME` files for custom-workflow deployments.
- Canonical `www` behavior: GitHub Pages redirects `www.drtuff.com` to the configured apex domain after both DNS names are configured.
- DNS changes performed during this pass: none

## Root-path and route checks

`scripts/validate_site.py` builds from source and crawls `/`, `/about`, `/research`, `/home`, `/my-science`, `/my-skills`, `/my-cv`, `/news`, and `/contact-me`. Root-relative and page-relative references are resolved against `site/`; every referenced local file must exist.

The `/about` compatibility route redirects to the home-page about section, and `/research` redirects to `/my-science`. Canonical sitemap entries remain limited to the real content routes.

## Production metadata

Every content page emits an apex-domain canonical URL, `og:url`, local apex-domain `og:image`/Twitter image, description, and JSON-LD `WebPage`/`WebSite` data. `robots.txt` points to `https://drtuff.com/sitemap.xml`; all sitemap locations use the apex domain.

## Requested reference classification

The built `site/` output contains **zero** occurrences of `personal_website`, `ttuff.github.io`, `squarespace`, or `squarespace-cdn`.

All source-repository occurrences are classified below. There are no remaining `FIX REQUIRED` occurrences.

| Search term | Classification | Remaining source locations and reason |
| --- | --- | --- |
| `personal_website` | INTENTIONAL | `scripts/validate_site.py` contains it only as a forbidden-string regression check. |
| `ttuff.github.io` | INTENTIONAL | `README.md` records the required `www` DNS CNAME target; `scripts/validate_site.py` contains it as a forbidden-string regression check. |
| `squarespace` | INTENTIONAL | `migration/source/`, `migration/asset_manifest.csv`, and the inventory files are the preserved migration archive/provenance; migration/design/report/changelog/README text describes the source platform; `scripts/archive_live_site.py` archives the live source; `scripts/build_static_site.py` recognizes and removes/replaces source-platform markup and hosts; `scripts/validate_site.py` rejects any deployable dependency. |
| `squarespace-cdn` | INTENTIONAL | This is a subset of archived source/provenance URLs plus the archive/build/validation hostname rules needed to localize and reject them. |

## DNS records to enter later at HostGator

Do not enter these until the committed revision is pushed, the Pages workflow succeeds, and `drtuff.com` is registered as the repository custom domain.

| Type | Host | Value |
| --- | --- | --- |
| A | `@` | `185.199.108.153` |
| A | `@` | `185.199.109.153` |
| A | `@` | `185.199.110.153` |
| A | `@` | `185.199.111.153` |
| CNAME | `www` | `ttuff.github.io` |

GitHub also supports apex IPv6 records (`2606:50c0:8000::153`, `2606:50c0:8001::153`, `2606:50c0:8002::153`, and `2606:50c0:8003::153`), but they are optional unless IPv6 is desired. Remove conflicting legacy apex/`www` records when making the eventual switch; do not remove or change anything before the GitHub Pages deployment is verified.
