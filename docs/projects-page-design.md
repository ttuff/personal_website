# My Projects page: design and data notes

## Purpose

`/my-projects/` is a capability-led account of the systems I build. It is not a chronological portfolio or a second repository browser. Five project stories show the range from scientific software and data systems through shared research infrastructure, computational experiments, and emerging agentic systems.

The page stays within the preserved Impact Media Lab system: the original blue, navy, paper, chalkboard textures, marker headings, square outlined calls to action, wide gutters, alternating full-width fields, and asymmetric text/image compositions. It adds no framework or runtime service.

## Content architecture

1. A chalkboard opening states the page's point of view in first person.
2. A single sequence connects scientific questions to reusable infrastructure and enabled science.
3. Five long-form project sections provide the problem, what I built, my role, visual or systems evidence, and direct sources.
4. Principles and technologies explain how I work without self-scored skill bars.
5. A compact connections preview leads to the full evidence map at `/github/`.
6. A public-evidence section reports repository facts produced by the existing GitHub data pipeline.

## Curated and generated data

`data/github-projects.yml` remains the human-editable source for project selection, first-person narrative, roles, technology associations, visual metadata, principles, and representative repositories. `scripts/build_github_life.py` joins that layer to the repository and family facts already collected for the Connections page. The resulting `portfolio` object in `data/generated/github-life.json` includes repository links, observed releases and contributors, owners, language evidence, documentation presence, licensing presence, and observed date spans.

The browser performs no GitHub request. Both `/my-projects/` and `/github/` read the same compact generated file, so the narrative layer and the evidence layer cannot silently drift into separate data stores.

## Visual provenance

| Local asset | First-party source | Repository license observed by the data build | Treatment |
| --- | --- | --- | --- |
| `assets/projects/cubedynamics-observed.png` | `CU-ESIIL/cubedynamics/docs/assets/generated/visual/observed.png` | MIT | Copied without content changes; PNG optimized. |
| `assets/projects/spectralbridge-overview.webp` | `earthlab/spectralbridge/docs/images/homepage/spectralbridge-technical-overview.png` | GPL-3.0 | Converted to WebP for delivery. |
| `assets/projects/fire-vase-hero.webp` | `CU-ESIIL/fire_vase/docs/assets/figures/hero_vase.png` | MIT | Converted to WebP for the opening composition. |
| `assets/projects/fire-vase-figure-1.webp` | `CU-ESIIL/fire_vase/docs/assets/figures/v2/Figure_1.png` | MIT | Converted to WebP for delivery. |

Each evidentiary figure has useful alternative text, a concise caption, and a link back to its exact first-party source. OASIS and the agentic-systems section use HTML/CSS systems diagrams rather than generic decoration. A project-specific OASIS architecture diagram and a mature agentic-workflow output would be worthwhile future assets if the underlying projects publish them.

## Review boundaries

The page deliberately qualifies claims that need care. SpectralBridge says “I helped build”; the agentic section says “I am exploring”; Fire VASE describes the method and question rather than asserting a scientific conclusion. The OASIS role summary is based on the public infrastructure repositories and project documentation, but it is the section most worth checking against the desired first-person account of leadership and operations.

## Accessibility and performance

- Project headings form a continuous hierarchy and each rendered project is a labeled section.
- Figures have alternative text and source captions; code-native diagrams expose an equivalent accessible label.
- Technology filtering uses real buttons with `aria-pressed`; dimming is supplementary and every project remains in the document.
- The Connections preview has an SVG title/description on larger screens and a full narrative list on narrow screens.
- The four raster assets are optimized and lazy-loaded below the opening image. The page adds no third-party JavaScript and respects reduced-motion preferences.
