# drtuff.com design inventory

The live Squarespace site was measured in a rendered browser at desktop and mobile widths. The archived `site.css` and `custom.css` under `migration/source/styles/` preserve the exact Squarespace source rules for reference.

## Global system

- Template: Squarespace 7, Bedford-family template (`templateId 55f0aac0e4b0f0a5b7e0b22e`).
- Page background: `#f9f9f9`.
- Body color: `rgba(0, 0, 0, 0.75)`.
- Accent blue: `#51a7f9` (rendered as `rgb(81, 167, 249)`).
- Footer navy: `#132a3f` with a 4px blue top border.
- Body typography: Proxima Nova, 18px, weight 500, 1.6 line height (28.8px).
- H1 typography: Permanent Marker, 60px, weight 400, 1.1 line height (66px).
- H2 typography: Proxima Nova, 40px, weight 700, `-0.02em` tracking, 1.1 line height (44px).
- H3 typography: Proxima Nova, 22px, weight 300, `0.1em` tracking, uppercase, 1.3 line height.
- Standard desktop page padding: 90px. Standard content width at 1280px: 1100px.

The local reproduction embeds recovered local copies of the Permanent Marker and Rock Salt font files. Proxima Nova remains loaded from the live site’s Adobe Typekit kit, with Helvetica/Arial fallbacks. Typekit rejects `127.0.0.1`, so local screenshots use the fallback; the production-domain font load must be confirmed once `drtuff.com` points to GitHub Pages.

## Header and navigation

- Desktop header height: 95px, overlaid on index-page heroes and black on ordinary pages.
- Primary navigation: 16px, weight 600, uppercase, `0.08em` letter spacing.
- Site title: Permanent Marker, 34px.
- Primary navigation order: My Science, My CV, Contact me.
- Mobile breakpoint: 640px.
- Mobile bar: fixed, 52px high, black, 8px vertical / 12px horizontal padding.
- Mobile title: Rock Salt, 20px, `0.15em` letter spacing.
- Mobile menu icon: 36px square plus/close treatment.

## Index pages

- The first index section uses the Squarespace `98vh` fullscreen rule; at 1280×720 the live section is approximately 706px high.
- Desktop image-section content padding: 90px.
- Hero images use full-bleed cover cropping with a centered focal point unless the source specifies otherwise.
- Alternating white/off-white content sections and dark photo or chalkboard sections are part of the original design.
- Buttons are uppercase, outlined, square-cornered, with blue hover treatment.
- Links and headings use blue hover/accent behavior.

## Measured page geometry at 1280px

| Page | Live body height | Main sections |
| --- | ---: | --- |
| Home | 4511px | 6 index sections |
| My Science | 9720px | 7 index sections |
| My Skills | 10837px | 7 index sections |
| My CV | 9942px | 2 index sections |
| News | 1263px | ordinary page; empty blog state |
| Contact Me | 1411px | ordinary page |

Representative Home section heights on the live 390×844 layout were 775, 1583, 787, 740, 692, and 744px. The fixed mobile bar remains visible above the page.

## Media and interaction

- Home uses a full-bleed 2048×1365 portrait/work image, an animated geese GIF, three Vimeo talk embeds, an animated Earth GIF, and social-logo tiles.
- My Science alternates photographic, chalkboard, and white sections and includes Vimeo/YouTube embeds.
- My Skills uses image galleries, slide stills, and a Vimeo background reference.
- Vimeo and YouTube remain intentional third-party embeds; all Squarespace-hosted first-party media is local.
- The contact map is reproduced as a keyless OpenStreetMap embed centered on the original CIRES coordinates. This avoids retaining the Squarespace Google Maps runtime/API key while preserving the original map content and placement.
- Desktop, tablet, and mobile screenshots were captured and inspected through browser automation. `scripts/compare_screenshots.mjs` regenerates matching viewport/full-page captures at 1440×1000, 1280×900, 768×1024, and 390×844 when Playwright is available; `scripts/create_visual_diffs.py` creates side-by-side, overlay, and amplified-difference images when Pillow is available.
