# drtuff.com fidelity audit

## Method

All six live Squarespace routes and their local static equivalents were captured in the same browser at 1440×1000, 1280×900, 768×1024, and 390×844. Each run waited for page load and fonts, traversed the page to trigger lazy media, returned to the top, and recorded viewport/full-page screenshots plus DOM geometry and asset-load state.

The ignored audit artifacts are under `migration/screenshots/final/`. Generated side-by-side, 50% overlays, and amplified image differences are under `migration/screenshots/comparisons/`. They can be regenerated with `scripts/compare_screenshots.mjs` and `scripts/create_visual_diffs.py`.

## Final page-height comparison

Values are live/local CSS pixels. The percentage is local drift from live; it is a geometry signal, not a perceptual image score.

| Page | 1440×1000 | 1280×900 | 768×1024 | 390×844 |
| --- | ---: | ---: | ---: | ---: |
| Home | 4819 / 5054 (+4.9%) | 4687 / 4891 (+4.4%) | 5264 / 5353 (+1.7%) | 6477 / 6474 (0.0%) |
| My Science | 9356 / 9978 (+6.6%) | 9895 / 10345 (+4.5%) | 12309 / 12082 (-1.8%) | 18975 / 18976 (0.0%) |
| My Skills | 10798 / 11770 (+9.0%) | 11013 / 12069 (+9.6%) | 13416 / 13936 (+3.9%) | 14168 / 14556 (+2.7%) |
| My CV | 9491 / 9525 (+0.4%) | 10008 / 10060 (+0.5%) | 13147 / 13348 (+1.5%) | 18226 / 18226 (0.0%) |
| News | 1284 / 1284 (0.0%) | 1263 / 1284 (+1.7%) | 1143 / 1284 (+12.3%) | 1424 / 1305 (-8.4%) |
| Contact Me | 1403 / 1453 (+3.6%) | 1411 / 1482 (+5.0%) | 1592 / 1629 (+2.3%) | 2250 / 2251 (0.0%) |

## Shared fixes applied

- Restored the original desktop header order: brand, primary navigation, then social links.
- Restored the full Squarespace grid width, single gutter layer, nested-column ratios, floated media, aspect-ratio image positioning, slideshow sizing, two-column galleries, and hidden index navigation.
- Restored Proxima Nova through the existing Adobe Typekit kit and retained local Permanent Marker/Rock Salt files with safe fallbacks.
- Restored footer logo/social assets, quick links, contact links, desktop height, and mobile stacking.
- Restored the missing contact map with a keyless embed at the original coordinates.
- Matched the original 640px mobile breakpoint, fixed mobile bar/menu, section geometry, and page-specific long-form layout.

## Page findings

- **Home:** Hero crop, headline lines, mobile bar, content order, talks, Earth CTA, social section, and footer are preserved. Desktop residual drift comes from fallback font metrics and static Vimeo/gallery presentation.
- **My Science:** Section order, chalkboard/photo alternation, project cards, images, videos, and mobile long-form geometry are preserved. Desktop totals remain within 7%.
- **My Skills:** Content and all 29 first-party images load. Proprietary Squarespace slideshow/lightbox behavior is represented by a deterministic first-slide view plus thumbnails and a responsive two-column gallery; this is the largest remaining desktop geometry difference.
- **My CV:** Desktop and mobile geometry are within 2%; content, headings, and imagery are preserved.
- **News:** The intentionally empty state is preserved. Its unusual live whitespace is matched on desktop; tablet/mobile whitespace remains the largest proportional difference on this otherwise empty page.
- **Contact Me:** Contact content, organization links, social links, two-column desktop layout, mobile stack, map location, and footer are preserved. The map provider differs intentionally because the Squarespace Google Maps runtime/API key was removed.

## Functional and asset checks

- Desktop and mobile primary navigation routes resolve locally.
- The mobile menu opens, exposes all three links, closes, and updates `aria-expanded`/labels.
- Every local image in the final capture matrix loaded successfully; lazy-only live Squarespace images occasionally reported unloaded when off-screen.
- Local favicon, CSS, JavaScript, fonts, images, GIFs, map iframe, and Vimeo/YouTube embeds have valid generated references.
- No deployable HTML, CSS, or JavaScript depends on Squarespace or its CDN.

## Intentional residuals

- The static build does not reproduce Squarespace editing/runtime code, AJAX navigation, analytics, gallery lightboxes, or background-video autoplay.
- Typekit rejects the localhost hostname, so local captures use the declared fallback. Production typography should be checked once the kit loads on `drtuff.com`.
- The contact map uses OpenStreetMap rather than the removed Squarespace Google Maps integration.
