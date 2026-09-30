# drtuff.com migration report

## Status

- Pages found: 6
- Pages reproduced: 6, plus the site root and `/about` and `/research` compatibility redirects
- Logical first-party assets recovered: 63
- Assets that could not be recovered: 0
- Public page paths preserved: `/home`, `/my-science`, `/my-skills`, `/my-cv`, `/news`, `/contact-me`
- Raw HTML, sitemap, robots rules, theme CSS, and custom CSS archived: yes
- Remaining Squarespace dependencies in the deployable site: 0
- Production custom domain in source and artifact: `drtuff.com`

## Reproduced content and behavior

- Original headings, paragraphs, lists, CV content, captions, and external links are preserved from the live HTML.
- Original photographs, animated GIFs, chalkboard illustrations, slide images, social marks, footer logo, and favicon are served locally.
- Desktop overlay navigation, mobile fixed navigation, mobile menu, shared footer, index sections, galleries, buttons, responsive grids, hover states, and URL anchors are reproduced.
- Vimeo and YouTube content remains embedded from its original third-party host.
- The empty News page remains empty, matching the live public page.
- My Skills remains available at its existing public URL even though it is not in the primary navigation, matching the live navigation.

## Intentional differences

- Squarespace runtime JavaScript, editing hooks, analytics, image-resize services, and AJAX navigation were removed.
- The live Proxima Nova face remains supplied by the site’s existing Adobe Typekit kit, with a system sans-serif fallback.
- Vimeo background video sections use static local imagery/dark section treatments when autoplay background playback is unavailable; ordinary embedded talks remain playable.
- Squarespace gallery lightboxes are represented as responsive media grids rather than the proprietary Squarespace lightbox runtime.
- The static contact page retains the original direct contact and organization links. Its runtime map is replaced by a keyless OpenStreetMap embed at the same CIRES coordinates. There is no server-side Squarespace form submission dependency.

## Validation and remaining manual work

- `scripts/validate_site.py` rebuilds the static output and checks all nine routes, internal references, local assets, production canonical/OpenGraph URLs, `CNAME`, sitemap, robots rules, and forbidden deployment references.
- GitHub Actions builds and deploys the `site/` directory. The build copies the tracked root `CNAME` into the uploaded Pages artifact, although GitHub ignores artifact `CNAME` files for Actions deployments; the repository Pages custom-domain setting is authoritative.
- Matched live/local browser captures and generated visual comparisons are documented in `migration/fidelity_audit.md`.
- This host still has no GitHub HTTPS or SSH credentials, so an authenticated `git push origin main` and confirmation of the Pages custom-domain setting are required before GitHub can publish this revision.
- DNS has not been changed. Keep Squarespace live until the pushed Pages deployment and custom-domain setting are verified.
