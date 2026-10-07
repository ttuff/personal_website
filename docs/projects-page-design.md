# My Projects page: design and data notes

## Purpose

`/my-projects/` is a portfolio hub for the systems I build. It is not a chronological portfolio, a second repository browser, or a set of duplicate SEO landing pages. Five project previews show the range from scientific software and data systems through shared research infrastructure, computational experiments, and emerging agentic systems, then send visitors to each project’s canonical website and repository.

The page stays within the preserved Impact Media Lab system: the original blue, navy, paper, chalkboard textures, marker headings, square outlined calls to action, wide gutters, alternating full-width fields, and asymmetric text/image compositions. It adds no framework or runtime service.

## Content architecture

1. A chalkboard opening states the page's point of view in first person.
2. A single sequence connects scientific questions to reusable infrastructure and enabled science.
3. Five browser-style project previews make the canonical project websites the dominant visual element, paired with a one-sentence technical explanation, evidence-backed metrics, restrained technology labels, and direct website/GitHub actions.
4. Principles and technologies explain how I work without self-scored skill bars.
5. A compact connections preview leads to the full evidence map at `/github/`.
6. A public-evidence section reports repository facts produced by the existing GitHub data pipeline.

## Curated and generated data

`data/github-projects.yml` remains the human-editable source for project selection, first-person narrative, canonical project websites, primary repositories, screenshot metadata, metric sources, technology associations, principles, and representative repositories. `scripts/build_github_life.py` joins that layer to the repository and family facts already collected for the GitHub page. The resulting `portfolio` object in `data/generated/github-life.json` includes the curated gallery fields plus repository links, observed releases and contributors, owners, language evidence, documentation presence, licensing presence, and observed date spans.

The browser performs no GitHub request. Both `/my-projects/` and `/github/` read the same compact generated file, so the narrative layer and the evidence layer cannot silently drift into separate data stores.

## Website preview provenance

The previews are static first-viewport captures of the public canonical project websites, not live iframes. They are delivered as 1200 × 750 WebP files, lazy-loaded below the fold, and framed in HTML/CSS so the browser treatment remains consistent and accessible.

| Local asset | Captured website |
| --- | --- |
| `assets/projects/sites/cubedynamics.webp` | `https://cu-esiil.github.io/cubedynamics/` |
| `assets/projects/sites/spectralbridge.webp` | `https://earthlab.github.io/spectralbridge/` |
| `assets/projects/sites/oasis.webp` | `https://cu-esiil.github.io/home/` |
| `assets/projects/sites/fire-vase.webp` | `https://cu-esiil.github.io/fire_vase/` |
| `assets/projects/sites/fair-care-agents.webp` | `https://cu-esiil.github.io/FAIR-and-CARE-for-AGENTS/` |

Refresh all previews with `python3 scripts/capture_project_previews.py`, or use `--project PROJECT_ID` to update one. The script reads URLs and destination paths from the central project configuration, captures a fixed 1440 × 900 first viewport with local Chrome/Chromium, and converts it to WebP with `cwebp`; it does not introduce a runtime browser dependency into the deployed site.

## Supporting visual provenance

| Local asset | First-party source | Repository license observed by the data build | Treatment |
| --- | --- | --- | --- |
| `assets/projects/cubedynamics-observed.png` | `CU-ESIIL/cubedynamics/docs/assets/generated/visual/observed.png` | MIT | Copied without content changes; PNG optimized. |
| `assets/projects/spectralbridge-overview.webp` | `earthlab/spectralbridge/docs/images/homepage/spectralbridge-technical-overview.png` | GPL-3.0 | Converted to WebP for delivery. |
| `assets/projects/fire-vase-hero.webp` | `CU-ESIIL/fire_vase/docs/assets/figures/hero_vase.png` | MIT | Converted to WebP for the opening composition. |
| `assets/projects/fire-vase-figure-1.webp` | `CU-ESIIL/fire_vase/docs/assets/figures/v2/Figure_1.png` | MIT | Converted to WebP for delivery. |

The older scientific figures remain available as first-party supporting assets but are no longer the primary gallery previews. Their exact sources and observed repository licenses remain documented here.

## Review boundaries

The page deliberately qualifies claims that need care. SpectralBridge says “I helped build”; the agentic section says “I am exploring”; Fire VASE describes the method and question rather than asserting a scientific conclusion. The OASIS role summary is based on the public infrastructure repositories and project documentation, but it is the section most worth checking against the desired first-person account of leadership and operations.

## Accessibility and performance

- Project headings form a continuous hierarchy and each rendered project is a labeled article.
- Website captures have concise alternatives and explicit dimensions; the browser chrome is decorative.
- Technology filtering uses real buttons with `aria-pressed`; dimming is supplementary and every project remains in the document.
- The Connections preview has an SVG title/description on larger screens and a full narrative list on narrow screens.
- The five project previews are compressed WebP files with explicit dimensions and lazy loading. The page adds no third-party JavaScript, contains no fragile iframes, and respects reduced-motion preferences.
