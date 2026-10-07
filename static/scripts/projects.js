(() => {
  const root = document.querySelector('[data-projects-page]');
  if (!root) return;

  const escapeHTML = value => String(value ?? '').replace(/[&<>'"]/g, character => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;'
  })[character]);
  const number = new Intl.NumberFormat('en-US');
  const externalAttributes = url => /^https?:/.test(url || '') ? ' target="_blank" rel="noreferrer"' : '';

  function projectEventAttributes(project, linkType) {
    return ` data-project-name="${escapeHTML(project.title)}" data-project-link-type="${escapeHTML(linkType)}"`;
  }

  function projectMetrics(project) {
    if (project.metrics?.length) return project.metrics.slice(0, 2);
    const metrics = [];
    if (project.evidence.release_count) {
      metrics.push({value: number.format(project.evidence.release_count), label: 'observed releases'});
    }
    if (project.evidence.contributor_count) {
      metrics.push({value: number.format(project.evidence.contributor_count), label: 'observed contributors'});
    }
    if (metrics.length < 2 && project.evidence.repository_count) {
      metrics.push({value: number.format(project.evidence.repository_count), label: 'linked repositories'});
    }
    return metrics.slice(0, 2);
  }

  function projectWebsiteHref(project, url) {
    const tracked = new URL(url);
    tracked.searchParams.set('utm_source', 'drtuff.com');
    tracked.searchParams.set('utm_medium', 'referral');
    tracked.searchParams.set('utm_campaign', 'project_gallery');
    tracked.searchParams.set('utm_content', project.id);
    return tracked.toString();
  }

  function projectCard(project, index) {
    const website = project.website || project.links?.find(link => !link.url.includes('github.com'));
    const github = project.github || project.links?.find(link => link.url.includes('github.com'));
    const metrics = projectMetrics(project);
    const tags = project.technologies.slice(0, 6);
    const domain = website ? new URL(website.url).hostname : '';
    const websiteHref = website ? projectWebsiteHref(project, website.url) : '';
    return `<article id="project-${escapeHTML(project.id)}" class="project-gallery__item" aria-labelledby="project-${escapeHTML(project.id)}-title">
      ${website && project.screenshot ? `<a class="project-browser" href="${escapeHTML(websiteHref)}"${externalAttributes(websiteHref)}${projectEventAttributes(project, 'website')} aria-label="Visit the ${escapeHTML(project.title)} project website">
        <span class="project-browser__bar" aria-hidden="true"><i></i><i></i><i></i><span>${escapeHTML(domain)}</span></span>
        <img src="${escapeHTML(project.screenshot.src)}" alt="${escapeHTML(project.screenshot.alt)}" width="1200" height="750" loading="lazy" decoding="async">
      </a>` : ''}
      <div class="project-gallery__copy">
        <p class="projects-kicker">${String(index + 1).padStart(2, '0')} / ${escapeHTML(project.capability)}</p>
        <h3 id="project-${escapeHTML(project.id)}-title">${escapeHTML(project.title)}</h3>
        <p class="project-gallery__headline">${escapeHTML(project.headline)}</p>
        <p class="project-gallery__summary">${escapeHTML(project.summary || project.built)}</p>
        ${metrics.length ? `<dl class="project-gallery__metrics">${metrics.map(metric => `<div><dt>${escapeHTML(metric.label)}</dt><dd>${escapeHTML(metric.value)}</dd></div>`).join('')}</dl>` : ''}
        <ul class="project-gallery__technologies" aria-label="Technologies used by ${escapeHTML(project.title)}">${tags.map(technology => `<li>${escapeHTML(technology)}</li>`).join('')}</ul>
        <div class="project-gallery__actions">
          ${website ? `<a class="projects-button" href="${escapeHTML(websiteHref)}"${externalAttributes(websiteHref)}${projectEventAttributes(project, 'website')}>Visit ${escapeHTML(project.title)}</a>` : ''}
          ${github ? `<a class="projects-text-link" href="${escapeHTML(github.url)}"${externalAttributes(github.url)}${projectEventAttributes(project, 'github')}>View code on GitHub <span aria-hidden="true">↗</span></a>` : ''}
        </div>
      </div>
    </article>`;
  }

  function renderFeatured(portfolio) {
    const container = root.querySelector('[data-featured-projects]');
    container.innerHTML = `<section class="projects-section projects-gallery" aria-labelledby="project-gallery-title">
      <div class="projects-shell">
        <div class="projects-heading">
          <div><p class="projects-kicker">The project ecosystem</p><h2 id="project-gallery-title">Project websites, not replicas.</h2></div>
          <p>Each preview opens the project’s own canonical website. This page gives the technical throughline; the project sites hold the full documentation, evidence, and scientific context.</p>
        </div>
        <div class="project-gallery__list">${portfolio.projects.map(projectCard).join('')}</div>
      </div>
    </section>`;
  }

  function renderPrinciples(portfolio) {
    root.querySelector('[data-principles]').innerHTML = portfolio.principles.map((principle, index) => `<li>
      <span>${String(index + 1).padStart(2, '0')}</span>
      <strong>${escapeHTML(principle.title)}</strong>
      <p>${escapeHTML(principle.text)}</p>
    </li>`).join('');
  }

  function renderTechnologies(portfolio) {
    const selector = root.querySelector('[data-technology-selector]');
    const projectList = root.querySelector('[data-technology-projects]');
    selector.innerHTML = `<button type="button" class="is-active" data-technology="all" aria-pressed="true">All project evidence</button>` + Object.entries(portfolio.technology_groups).map(([group, technologies]) => `<section><h3>${escapeHTML(group)}</h3>${technologies.map(technology => `<button type="button" data-technology="${escapeHTML(technology)}" aria-pressed="false">${escapeHTML(technology)}</button>`).join('')}</section>`).join('');
    projectList.innerHTML = portfolio.projects.map(project => `<article data-project-technologies="${escapeHTML(project.technologies.join('|'))}">
      <span>${escapeHTML(project.capability)}</span>
      <strong>${escapeHTML(project.title)}</strong>
      <p>${escapeHTML(project.technologies.join(' · '))}</p>
      <a href="#project-${escapeHTML(project.id)}" aria-label="Read the ${escapeHTML(project.title)} project evidence">View evidence <span aria-hidden="true">↑</span></a>
    </article>`).join('');

    selector.addEventListener('click', event => {
      const button = event.target.closest('[data-technology]');
      if (!button) return;
      const selected = button.dataset.technology;
      selector.querySelectorAll('[data-technology]').forEach(item => {
        const active = item === button;
        item.classList.toggle('is-active', active);
        item.setAttribute('aria-pressed', String(active));
      });
      projectList.querySelectorAll('article').forEach(article => {
        const technologies = article.dataset.projectTechnologies.split('|');
        article.classList.toggle('is-muted', selected !== 'all' && !technologies.includes(selected));
        article.classList.toggle('is-match', selected !== 'all' && technologies.includes(selected));
      });
    });
  }

  function wrapLabel(label) {
    const words = label.split(' ');
    if (words.length < 3) return [label];
    const middle = Math.ceil(words.length / 2);
    return [words.slice(0, middle).join(' '), words.slice(middle).join(' ')];
  }

  function renderConnections(data) {
    const ids = new Set(data.portfolio.connections_preview);
    const nodes = data.families.filter(family => ids.has(family.id));
    const positions = {
      'climate-indices': [115, 105], 'fire-growth-form': [130, 230], 'ecological-sampling': [115, 355],
      'cube-dynamics': [365, 125], 'spectral-bridge': [380, 305],
      'agentic-infrastructure': [635, 105], 'esiil-infrastructure': [650, 280],
      oasis: [865, 180], 'open-life-science-hackathon': [865, 345]
    };
    const edges = data.graph.edges.filter(edge => edge.type === 'curated' && ids.has(edge.source) && ids.has(edge.target));
    const svgEdges = edges.map(edge => {
      const source = positions[edge.source], target = positions[edge.target];
      if (!source || !target) return '';
      return `<line x1="${source[0]}" y1="${source[1]}" x2="${target[0]}" y2="${target[1]}"><title>${escapeHTML(edge.label)}</title></line>`;
    }).join('');
    const svgNodes = nodes.map(node => {
      const position = positions[node.id];
      if (!position) return '';
      const lines = wrapLabel(node.title);
      return `<a href="../github/#project-graph" aria-label="${escapeHTML(node.title)} — open the full connections map">
        <circle cx="${position[0]}" cy="${position[1]}" r="9"></circle>
        <text x="${position[0]}" y="${position[1] + 29}" text-anchor="middle">${lines.map((line, index) => `<tspan x="${position[0]}" dy="${index ? 15 : 0}">${escapeHTML(line)}</tspan>`).join('')}</text>
      </a>`;
    }).join('');
    const mobile = nodes.map(node => `<li><span>${escapeHTML(node.category.replaceAll('-', ' '))}</span><strong>${escapeHTML(node.title)}</strong><small>${escapeHTML(node.description)}</small></li>`).join('');
    root.querySelector('[data-connections-preview]').innerHTML = `<svg viewBox="0 0 980 430" role="img" aria-labelledby="connections-svg-title connections-svg-desc">
      <title id="connections-svg-title">A preview of how my project families connect</title>
      <desc id="connections-svg-desc">Nine project families connected by eight relationships that I curate. The full evidence map is available on the Connections page.</desc>
      <g class="connections-preview__edges">${svgEdges}</g>
      <g class="connections-preview__nodes">${svgNodes}</g>
    </svg><ol class="connections-preview__mobile">${mobile}</ol>`;
  }

  function renderPublic(data) {
    const summary = data.summary;
    const values = [
      ['Repositories in my public map', summary.repositories_in_page],
      ['Observed releases', summary.releases_observed],
      ['Contributors GitHub returns', summary.contributors_observed],
      ['Organizations represented', data.graph.summary.organizations]
    ];
    root.querySelector('[data-public-summary]').innerHTML = values.map(([label, value]) => `<div><dt>${escapeHTML(label)}</dt><dd>${number.format(value)}</dd></div>`).join('');
    const repoByName = new Map(data.repositories.map(repo => [repo.full_name, repo]));
    root.querySelector('[data-representative-repositories]').innerHTML = data.portfolio.representative_repositories.map(name => repoByName.get(name)).filter(Boolean).map(repo => {
      const details = [repo.latest_release ? `release ${repo.latest_release.tag}` : null, repo.homepage ? 'project site' : null].filter(Boolean).join(' · ');
      return `<article>
        <div><span>${escapeHTML(repo.curated?.family_title || repo.owner)}</span><strong>${escapeHTML(repo.semantic.title)}</strong><small>${escapeHTML(details || 'public repository')}</small></div>
        <div class="representative-repositories__links"><a href="${escapeHTML(repo.url)}" target="_blank" rel="noreferrer">Code ↗</a>${repo.homepage ? `<a href="${escapeHTML(repo.homepage)}" target="_blank" rel="noreferrer">Project ↗</a>` : ''}</div>
      </article>`;
    }).join('');
    const generated = new Date(data.meta.generated_at);
    root.querySelector('[data-public-refresh]').textContent = `GitHub evidence refreshed ${generated.toLocaleDateString('en-US', {month: 'short', day: 'numeric', year: 'numeric'})}.`;
  }

  async function initialize() {
    try {
      const response = await fetch('../data/github-life.json');
      if (!response.ok) throw new Error(`Project data returned ${response.status}`);
      const data = await response.json();
      if (!data.portfolio?.projects?.length) throw new Error('Portfolio data is missing');
      renderFeatured(data.portfolio);
      renderPrinciples(data.portfolio);
      renderTechnologies(data.portfolio);
      renderConnections(data);
      renderPublic(data);
      if (window.location.hash) {
        window.requestAnimationFrame(() => {
          const target = document.querySelector(window.location.hash);
          if (target) target.scrollIntoView();
        });
      }
    } catch (error) {
      root.querySelector('[data-featured-projects]').innerHTML = '';
      const message = root.querySelector('[data-projects-error]');
      message.hidden = false;
      console.error(error);
    }
  }

  initialize();
})();
