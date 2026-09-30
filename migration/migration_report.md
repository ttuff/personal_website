# drtuff.com migration report

## Status

- Pages found: 6
- Pages reproduced: 6, plus the site root
- Logical first-party assets recovered: 63
- Assets that could not be recovered: 0
- Public page paths preserved: `/home`, `/my-science`, `/my-skills`, `/my-cv`, `/news`, `/contact-me`
- Raw HTML, sitemap, robots rules, theme CSS, and custom CSS archived: yes
- Remaining Squarespace dependencies in the deployable site: 0

## Reproduced content and behavior

- Original headings, paragraphs, lists, CV content, captions, and external links are preserved from the live HTML.
- Original photographs, animated GIFs, chalkboard illustrations, slide images, social marks, footer logo, and favicon are served locally.
- Desktop overlay navigation, mobile fixed navigation, mobile menu, shared footer, index sections, galleries, buttons, responsive grids, hover states, and URL anchors are reproduced.
- Vimeo and YouTube content remains embedded from its original third-party host.
- The empty News page remains empty, matching the live public page.
- My Skills remains available at its existing public URL even though it is not in the primary navigation, matching the live navigation.

## Intentional differences

- Squarespace runtime JavaScript, editing hooks, analytics, image-resize services, and AJAX navigation were removed.
- The live Proxima Nova face is supplied by Adobe Typekit. The replacement uses a system sans-serif stack rather than create a new external font dependency.
- Vimeo background video sections use static local imagery/dark section treatments when autoplay background playback is unavailable; ordinary embedded talks remain playable.
- Squarespace gallery lightboxes are represented as responsive media grids rather than the proprietary Squarespace lightbox runtime.
- The static contact page retains the original direct contact and organization links. There is no server-side Squarespace form submission dependency.

## Validation and remaining manual work

- `scripts/validate_site.py` rebuilds the static output and checks internal references, local assets, HTML parsing, and forbidden Squarespace dependencies.
- GitHub Actions builds and deploys the `site/` directory to GitHub Pages.
- The migration is committed locally. This host has no GitHub HTTPS or SSH credentials, so an authenticated `git push origin main` is still required before Pages can publish.
- Before moving DNS, inspect the GitHub Pages URL at 1440, 1024, 768, and 390px and compare against the live site. The optional screenshot script captures both versions.
- Do not add a `CNAME` file or change DNS until visual and functional review is accepted.
