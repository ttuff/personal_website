(() => {
  const root = document.querySelector('[data-projects-page]');
  if (!root) return;

  const escapeHTML = value => String(value ?? '').replace(/[&<>'"]/g, character => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;'
  })[character]);
  const number = new Intl.NumberFormat('en-US');
  const plural = (value, singular, pluralValue = `${singular}s`) => `${number.format(value)} ${value === 1 ? singular : pluralValue}`;
  const externalAttributes = url => /^https?:/.test(url || '') ? ' target="_blank" rel="noreferrer"' : '';

  function links(project) {
    return `<div class="project-links">${project.links.map(link => `<a href="${escapeHTML(link.url)}"${externalAttributes(link.url)}>${escapeHTML(link.label)} <span aria-hidden="true">→</span></a>`).join('')}</div>`;
  }

  function projectVisual(project) {
    if (project.visual) {
      return `<figure class="project-visual">
        <img src="${escapeHTML(project.visual.src)}" alt="${escapeHTML(project.visual.alt)}" loading="lazy" decoding="async">
        <figcaption>${escapeHTML(project.visual.caption)} <a href="${escapeHTML(project.visual.source)}" target="_blank" rel="noreferrer">Source ↗</a></figcaption>
      </figure>`;
    }
    if (project.diagram) {
      return `<div class="system-diagram" role="img" aria-label="${escapeHTML(project.diagram.join(' connects to '))}">
        ${project.diagram.map((label, index) => `<div><span>${String(index + 1).padStart(2, '0')}</span><strong>${escapeHTML(label)}</strong></div>`).join('')}
      </div>`;
    }
    return '';
  }

  function evidenceLine(project) {
    const evidence = project.evidence;
    const parts = [
      plural(evidence.repository_count, 'repository', 'repositories'),
      evidence.release_count ? plural(evidence.release_count, 'observed release') : null,
      evidence.documented_repository_count ? `${evidence.documented_repository_count} with a project site` : null,
      evidence.owner_count > 1 ? `${evidence.owner_count} GitHub owners` : null,
    ].filter(Boolean);
    return parts.join(' · ');
  }

  function renderFeatured(portfolio) {
    const container = root.querySelector('[data-featured-projects]');
    container.innerHTML = portfolio.projects.map((project, index) => `<section id="project-${escapeHTML(project.id)}" class="projects-section project-section project-section--${escapeHTML(project.id)}" aria-labelledby="project-${escapeHTML(project.id)}-title">
      <div class="projects-shell">
        <header class="project-header">
          <p class="projects-kicker">${String(index + 1).padStart(2, '0')} / ${escapeHTML(project.capability)}</p>
          <h2 id="project-${escapeHTML(project.id)}-title">${escapeHTML(project.title)}</h2>
          <p class="project-headline">${escapeHTML(project.headline)}</p>
        </header>
        <div class="project-composition">
          <div class="project-story">
            <div class="project-copy"><span>Problem</span><p>${escapeHTML(project.problem)}</p></div>
            <div class="project-copy"><span>Built</span><p>${escapeHTML(project.built)}</p></div>
            <div class="project-copy project-copy--role"><span>My role</span><ul>${project.role.map(item => `<li>${escapeHTML(item)}</li>`).join('')}</ul></div>
            ${links(project)}
            <p class="project-evidence"><span>Evidence</span>${escapeHTML(evidenceLine(project))}</p>
          </div>
          ${projectVisual(project)}
        </div>
      </div>
    </section>`).join('');
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
