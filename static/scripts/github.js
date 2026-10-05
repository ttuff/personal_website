(() => {
  const root = document.querySelector('[data-github-life]');
  if (!root) return;

  const DATA_URL = '../data/github-life.json';
  const number = new Intl.NumberFormat('en-US');
  const dateFormat = new Intl.DateTimeFormat('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
  const monthFormat = new Intl.DateTimeFormat('en-US', { year: 'numeric', month: 'long' });
  const state = { data: null, repository: null, selectedNode: null, hoverNode: null, insight: null, edgeFilter: 'all', conceptFilter: 'all', commandIndex: 0, commandItems: [] };

  const escapeHTML = value => String(value ?? '').replace(/[&<>'"]/g, character => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' })[character]);
  const formatDate = value => value ? dateFormat.format(new Date(`${value.slice(0, 10)}T12:00:00Z`)) : 'Unavailable';
  const formatMonth = value => value ? monthFormat.format(new Date(`${value}-01T12:00:00Z`)) : 'Unavailable';
  const yearsBetween = (start, end) => {
    if (!start || !end) return 'Unavailable';
    const days = Math.max(0, (new Date(end) - new Date(start)) / 86400000);
    const years = days / 365.2425;
    return years >= 10 ? `${years.toFixed(1)} years` : `${Math.max(1, Math.round(years))} years`;
  };

  function sparkline(values) {
    const width = 220;
    const height = 42;
    const max = Math.max(1, ...values);
    const points = values.map((value, index) => {
      const x = values.length === 1 ? 0 : index * width / (values.length - 1);
      const y = height - 3 - value / max * (height - 8);
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    }).join(' ');
    return `<svg viewBox="0 0 ${width} ${height}" preserveAspectRatio="none" role="img" aria-label="Weekly commits over 13 weeks: ${values.join(', ')}"><line x1="0" y1="39" x2="220" y2="39"></line><path d="M${points.replaceAll(' ', ' L')}"></path></svg>`;
  }

  function renderSummary(data) {
    const summary = data.summary;
    const latest = data.discoveries.last_public_contribution || data.meta.generated_at.slice(0, 10);
    root.querySelector('[data-summary-value="years"]').textContent = yearsBetween(summary.active_since, latest);
    root.querySelector('[data-summary-note="years"]').textContent = `Since ${formatDate(summary.active_since)}`;
    root.querySelector('[data-summary-value="contributions"]').textContent = number.format(summary.public_calendar_contributions);
    root.querySelector('[data-summary-value="repositories"]').textContent = number.format(summary.repositories_discovered);
    root.querySelector('[data-summary-value="owners"]').textContent = number.format(summary.owners_observed);
    root.querySelector('[data-summary-note="owners"]').textContent = summary.organization_names.join(' · ');
    root.querySelector('[data-summary-value="releases"]').textContent = number.format(summary.releases_observed);
    const refresh = new Date(data.meta.generated_at);
    root.querySelector('[data-refreshed]').textContent = `· refreshed ${dateFormat.format(refresh)}`;
    root.querySelector('[data-refreshed]').dateTime = data.meta.generated_at;
    root.querySelector('[data-machinery-refresh]').textContent = refresh.toLocaleString('en-US', { dateStyle: 'medium', timeStyle: 'short' });
    root.querySelector('[data-refresh-mode]').textContent = data.meta.refresh_mode.replaceAll('-', ' ');
    root.querySelector('[data-activity-formula]').textContent = data.methodology.activity_score;
  }

  function renderCurrent(data) {
    const active = data.repositories.filter(repo => repo.recent.windows['90'].commits > 0).slice(0, 7);
    root.querySelector('[data-current-list]').innerHTML = active.map((repo, index) => {
      const family = repo.curated?.family_title || repo.owner;
      const days = repo.recent.windows['30'].active_days;
      return `<article class="current-row">
        <span class="current-row__rank">${String(index + 1).padStart(2, '0')}</span>
        <div class="current-row__name"><a href="${escapeHTML(repo.url)}"><strong>${escapeHTML(repo.name)}</strong></a><span>${escapeHTML(repo.owner)} · ${escapeHTML(family)}</span></div>
        <div class="current-row__window"><b>${number.format(repo.recent.windows['90'].commits)}</b><span>commits / 90d</span></div>
        <div class="current-row__spark">${sparkline(repo.recent.sparkline)}</div>
        <div class="current-row__score"><strong>${number.format(repo.recent.score)}</strong><span>${days} active day${days === 1 ? '' : 's'} / 30d</span></div>
      </article>`;
    }).join('') || '<p>GitHub returned no public commits authored by me in the trailing 90-day window.</p>';
  }

  function renderCareer(data) {
    const holder = root.querySelector('[data-career-grid]');
    const byYear = new Map();
    data.contributions.days.forEach(day => {
      const year = day.date.slice(0, 4);
      if (!byYear.has(year)) byYear.set(year, new Map());
      byYear.get(year).set(day.date, day);
    });
    [...byYear.keys()].sort().forEach(year => {
      const row = document.createElement('div');
      row.className = 'career-year';
      row.setAttribute('role', 'row');
      const label = document.createElement('span');
      label.className = 'career-year__label';
      label.textContent = `${year} · ${number.format(data.contributions.yearly[year] || 0)}`;
      const cells = document.createElement('div');
      cells.className = 'career-year__cells';
      const first = new Date(`${year}-01-01T12:00:00Z`);
      const end = new Date(`${year}-12-31T12:00:00Z`);
      for (let index = 0; index < first.getUTCDay(); index += 1) {
        const blank = document.createElement('span');
        blank.className = 'career-day career-day--missing';
        blank.setAttribute('aria-hidden', 'true');
        cells.append(blank);
      }
      for (let cursor = first; cursor <= end; cursor = new Date(cursor.getTime() + 86400000)) {
        const key = cursor.toISOString().slice(0, 10);
        const day = byYear.get(year).get(key);
        const button = document.createElement('button');
        button.type = 'button';
        button.className = day ? 'career-day' : 'career-day career-day--missing';
        button.dataset.level = day?.level ?? 0;
        button.dataset.date = key;
        button.dataset.count = day?.count ?? '';
        button.tabIndex = key.endsWith('-01-01') ? 0 : -1;
        button.setAttribute('role', 'gridcell');
        button.setAttribute('aria-selected', 'false');
        button.setAttribute('aria-label', day ? `${day.count} public contributions on ${formatDate(key)}` : `No calendar data for ${formatDate(key)}`);
        if (!day) button.disabled = true;
        cells.append(button);
      }
      row.append(label, cells);
      holder.append(row);
    });
    const selection = root.querySelector('[data-career-selection]');
    holder.addEventListener('click', event => {
      const day = event.target.closest('.career-day:not(:disabled)');
      if (!day) return;
      holder.querySelectorAll('[aria-selected="true"]').forEach(item => item.setAttribute('aria-selected', 'false'));
      day.setAttribute('aria-selected', 'true');
      selection.textContent = `${formatDate(day.dataset.date)} · ${number.format(Number(day.dataset.count))} public GitHub contribution${day.dataset.count === '1' ? '' : 's'}`;
    });
    holder.addEventListener('keydown', event => {
      const day = event.target.closest('.career-day:not(:disabled)');
      if (!day || !['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown'].includes(event.key)) return;
      event.preventDefault();
      const buttons = [...day.parentElement.querySelectorAll('.career-day:not(:disabled)')];
      const delta = { ArrowLeft: -7, ArrowRight: 7, ArrowUp: -1, ArrowDown: 1 }[event.key];
      const next = buttons[Math.max(0, Math.min(buttons.length - 1, buttons.indexOf(day) + delta))];
      if (next) { day.tabIndex = -1; next.tabIndex = 0; next.focus(); }
    });
    const streak = data.discoveries.longest_active_streak;
    root.querySelector('[data-career-discovery]').innerHTML = streak
      ? `<strong>${streak.days} consecutive active days</strong><span>${formatDate(streak.start)}–${formatDate(streak.end)} · ${number.format(streak.contributions)} public contributions</span>`
      : '<span>No continuous public-calendar run was available.</span>';
  }

  const categoryLabels = { 'research-questions': 'Research questions', 'methods-software': 'Methods & software', infrastructure: 'Infrastructure', communities: 'Communities', uncategorized: 'Other public work' };

  function graphPositions(data) {
    const width = 1000;
    const categoryX = { 'research-questions': 145, 'methods-software': 390, infrastructure: 650, communities: 875 };
    const positions = new Map();
    Object.keys(categoryX).forEach(category => {
      const families = data.graph.nodes.filter(node => node.type === 'family' && node.category === category);
      families.forEach((family, index) => {
        const y = families.length === 1 ? 340 : 145 + index * (400 / (families.length - 1));
        positions.set(family.id, { x: categoryX[category], y, category });
      });
    });
    const angles = [-165, -130, -95, -60, -25, 10, 170].map(value => value * Math.PI / 180);
    data.graph.nodes.filter(node => node.type === 'family').forEach(family => {
      const center = positions.get(family.id);
      if (!center) return;
      const repositories = data.graph.nodes.filter(node => node.type === 'repository' && node.family === family.id);
      repositories.forEach((repo, index) => {
        const angle = angles[index % angles.length];
        const ring = 67 + Math.floor(index / angles.length) * 24;
        positions.set(repo.id, { x: center.x + Math.cos(angle) * ring, y: center.y + Math.sin(angle) * ring, category: family.category });
      });
    });
    const ungrouped = data.graph.nodes.filter(node => node.type === 'repository' && !positions.has(node.id));
    ungrouped.forEach((repo, index) => positions.set(repo.id, { x: 70 + index * (width - 140) / Math.max(1, ungrouped.length - 1), y: 690, category: 'uncategorized' }));
    return positions;
  }

  function fact(label, value) {
    return value === null || value === undefined || value === '' ? '' : `<div><span>${escapeHTML(label)}</span><strong>${escapeHTML(value)}</strong></div>`;
  }

  function inspectorHTML(data, id) {
    const repo = data.repositories.find(item => item.full_name === id);
    if (repo) {
      const node = data.graph.nodes.find(item => item.id === id);
      const connected = data.graph.edges.filter(edge => edge.source === id || edge.target === id);
      const family = data.families.find(item => item.id === repo.curated?.family);
      const type = node?.ownership === 'mine' ? 'My repository' : 'Connected repository';
      const evidence = connected.map(edge => {
        const otherId = edge.source === id ? edge.target : edge.source;
        const other = data.graph.nodes.find(item => item.id === otherId);
        return `<li><b>${escapeHTML(edge.type === 'family' ? 'Project membership' : edge.type.replaceAll('-', ' '))}</b><span>${escapeHTML(edge.label)}${other ? ` · ${escapeHTML(other.label)}` : ''}</span></li>`;
      }).join('');
      return `<p class="repo-inspector__eyebrow">${type}</p>
        <h3>${escapeHTML(repo.semantic?.title || repo.name)}</h3>
        <p class="repo-inspector__source">${escapeHTML(repo.full_name)}</p>
        <p>${escapeHTML(repo.semantic?.description || family?.description || 'GitHub does not currently provide a description for this repository.')}</p>
        ${family ? `<div class="inspector-section"><h4>Project story</h4><p>${escapeHTML(family.title)} · ${escapeHTML(family.theme)}</p></div>` : ''}
        <div class="inspector-facts">
          ${fact('90-day commits', number.format(repo.recent.windows['90'].commits))}
          ${fact('Observed contributors', number.format(repo.contributor_count_observed))}
          ${repo.primary_language ? fact('Primary language', repo.primary_language) : ''}
          ${repo.license ? fact('License', repo.license) : ''}
        </div>
        <div class="inspector-links"><a href="${escapeHTML(repo.url)}">GitHub repository ↗</a>${repo.homepage ? `<a href="${escapeHTML(repo.homepage)}">Project site ↗</a>` : ''}${repo.latest_release?.url ? `<a href="${escapeHTML(repo.latest_release.url)}">Latest release ↗</a>` : ''}</div>
        ${evidence ? `<div class="inspector-section"><h4>Why it appears here</h4><ul class="inspector-edges">${evidence}</ul></div>` : ''}`;
    }
    const family = data.families.find(item => item.id === id);
    if (!family) return '';
    const active = family.evidence.active_from && family.evidence.active_to ? `${family.evidence.active_from.slice(0, 4)}–${family.evidence.active_to.slice(0, 4)}` : null;
    const repositories = family.repositories.map(name => data.repositories.find(repoItem => repoItem.full_name === name)).filter(Boolean);
    const repositoryList = repositories.map(repoItem => `<li><div><a href="${escapeHTML(repoItem.url)}">${escapeHTML(repoItem.semantic?.title || repoItem.name)} ↗</a><span>${escapeHTML(repoItem.full_name)}</span></div>${repoItem.homepage ? `<a class="inspector-doc-link" href="${escapeHTML(repoItem.homepage)}">site ↗</a>` : ''}</li>`).join('');
    const links = family.links || [];
    return `<p class="repo-inspector__eyebrow">Project family</p>
      <h3>${escapeHTML(family.title)}</h3>
      <p>${escapeHTML(family.description)}</p>
      ${family.question ? `<div class="inspector-section"><h4>The question</h4><p>${escapeHTML(family.question)}</p></div>` : ''}
      ${family.topics?.length ? `<div class="inspector-section"><h4>What connects this work</h4><p class="inspector-topics">${family.topics.map(escapeHTML).join(' · ')}</p></div>` : ''}
      <div class="inspector-section"><h4>Evidence</h4><div class="inspector-facts">
        ${fact('Repositories', family.evidence.repository_count)}
        ${family.evidence.contributor_count ? fact('Observed contributors', family.evidence.contributor_count) : ''}
        ${family.evidence.organization_count ? fact('Organizations', family.evidence.organization_count) : ''}
        ${active ? fact('Active span', active) : ''}
      </div></div>
      ${links.length ? `<div class="inspector-links">${links.map(link => `<a href="${escapeHTML(link.url)}">${escapeHTML(link.label)} ↗</a>`).join('')}</div>` : ''}
      <details class="inspector-repositories"><summary>Repositories &amp; evidence (${repositories.length})</summary><ul>${repositoryList}</ul></details>`;
  }

  function selectGraphNode(id) {
    state.repository = id;
    state.selectedNode = id;
    state.insight = null;
    root.querySelectorAll('[data-network-insight]').forEach(button => button.setAttribute('aria-pressed', 'false'));
    const html = inspectorHTML(state.data, id);
    root.querySelector('[data-repo-inspector]').innerHTML = html;
    root.querySelector('[data-mobile-inspector]').innerHTML = html;
    applyGraphState();
  }

  function clearGraphSelection() {
    state.repository = null;
    state.selectedNode = null;
    state.hoverNode = null;
    state.insight = null;
    root.querySelectorAll('[data-network-insight]').forEach(button => button.setAttribute('aria-pressed', 'false'));
    applyGraphState();
  }

  function graphNeighborhood(id) {
    const nodes = new Set([id]);
    const edges = new Set();
    state.data.graph.edges.forEach(edge => {
      if (edge.source === id || edge.target === id) {
        nodes.add(edge.source); nodes.add(edge.target); edges.add(edge.id);
      }
    });
    return { nodes, edges };
  }

  function applyGraphState() {
    const svg = root.querySelector('[data-project-graph]');
    if (!svg || !svg.dataset.ready) return;
    const focus = state.insight ? { nodes: new Set(state.insight.nodes), edges: new Set(state.insight.edges) } : (state.hoverNode || state.selectedNode ? graphNeighborhood(state.hoverNode || state.selectedNode) : null);
    const nodeById = new Map(state.data.graph.nodes.map(node => [node.id, node]));
    const conceptMatches = id => state.conceptFilter === 'all' || nodeById.get(id)?.category === state.conceptFilter;
    svg.querySelectorAll('.graph-edge-group').forEach(group => {
      const edgeMatches = state.edgeFilter === 'all' || group.dataset.type === state.edgeFilter;
      const conceptMatch = state.conceptFilter === 'all' || conceptMatches(group.dataset.source) || conceptMatches(group.dataset.target);
      const focusMatch = !focus || focus.edges.has(group.dataset.id);
      group.classList.toggle('is-dimmed', !edgeMatches || !conceptMatch || !focusMatch);
      group.classList.toggle('is-emphasized', Boolean(focus?.edges.has(group.dataset.id)));
    });
    svg.querySelectorAll('.graph-node').forEach(group => {
      const conceptMatch = conceptMatches(group.dataset.id);
      const focusMatch = !focus || focus.nodes.has(group.dataset.id);
      group.classList.toggle('is-dimmed', !conceptMatch || !focusMatch);
      group.classList.toggle('is-emphasized', Boolean(focus?.nodes.has(group.dataset.id)));
      group.classList.toggle('is-selected', group.dataset.id === state.selectedNode);
    });
    root.querySelectorAll('.graph-mobile__family').forEach(section => section.hidden = state.conceptFilter !== 'all' && section.dataset.category !== state.conceptFilter);
  }

  function wrapGraphLabel(text) {
    const words = text.split(/\s+/);
    const lines = [''];
    words.forEach(word => {
      const current = lines.at(-1);
      if (current && `${current} ${word}`.length > 20 && lines.length < 2) lines.push(word);
      else lines[lines.length - 1] = current ? `${current} ${word}` : word;
    });
    return lines;
  }

  function renderGraph(data) {
    const svg = root.querySelector('[data-project-graph]');
    const stage = root.querySelector('[data-graph-stage]');
    const tooltip = root.querySelector('[data-graph-tooltip]');
    const ns = 'http://www.w3.org/2000/svg';
    const positions = graphPositions(data);
    const nodeById = new Map(data.graph.nodes.map(node => [node.id, node]));
    const categoryGroup = document.createElementNS(ns, 'g');
    categoryGroup.setAttribute('class', 'graph-category-labels');
    const categoryX = { 'research-questions': 145, 'methods-software': 390, infrastructure: 650, communities: 875 };
    Object.entries(categoryX).forEach(([category, x]) => {
      const label = document.createElementNS(ns, 'text');
      label.setAttribute('x', x); label.setAttribute('y', 30); label.setAttribute('text-anchor', 'middle'); label.textContent = categoryLabels[category];
      categoryGroup.append(label);
    });
    const edgesGroup = document.createElementNS(ns, 'g');
    edgesGroup.setAttribute('class', 'graph-edges');
    data.graph.edges.forEach(edge => {
      const start = positions.get(edge.source);
      const end = positions.get(edge.target);
      if (!start || !end) return;
      const group = document.createElementNS(ns, 'g');
      group.setAttribute('class', 'graph-edge-group'); group.dataset.id = edge.id; group.dataset.type = edge.type; group.dataset.source = edge.source; group.dataset.target = edge.target;
      group.setAttribute('role', 'button'); group.setAttribute('tabindex', '0'); group.setAttribute('aria-label', `${edge.type.replaceAll('-', ' ')}: ${edge.label}`);
      ['graph-edge graph-edge--hit', 'graph-edge'].forEach(className => {
        const line = document.createElementNS(ns, 'line');
        line.setAttribute('x1', start.x); line.setAttribute('y1', start.y); line.setAttribute('x2', end.x); line.setAttribute('y2', end.y); line.setAttribute('class', className); group.append(line);
      });
      group.addEventListener('mouseenter', event => showGraphTooltip(event, `<strong>${escapeHTML(edge.label)}</strong><span>${escapeHTML(edge.type === 'curated' ? 'Relationship I curated' : edge.type === 'family' ? 'Repository evidence for a project family' : 'Relationship observed through GitHub contributors')}</span>`));
      group.addEventListener('focus', event => showGraphTooltip(event, `<strong>${escapeHTML(edge.label)}</strong><span>${escapeHTML(edge.type.replaceAll('-', ' '))}</span>`));
      group.addEventListener('mouseleave', hideGraphTooltip); group.addEventListener('blur', hideGraphTooltip);
      edgesGroup.append(group);
    });
    const nodesGroup = document.createElementNS(ns, 'g');
    data.graph.nodes.forEach(node => {
      const point = positions.get(node.id);
      if (!point) return;
      const group = document.createElementNS(ns, 'g');
      group.setAttribute('class', 'graph-node'); group.dataset.id = node.id; group.dataset.type = node.type; group.dataset.ownership = node.ownership || ''; group.dataset.category = node.category;
      if (node.activity > 0) group.dataset.active = 'true';
      group.setAttribute('transform', `translate(${point.x} ${point.y})`); group.setAttribute('role', 'button'); group.setAttribute('tabindex', '0');
      group.setAttribute('aria-label', `${node.type === 'family' ? 'Project family' : node.ownership === 'mine' ? 'My repository' : 'Connected repository'}: ${node.label}`);
      const circle = document.createElementNS(ns, 'circle');
      circle.setAttribute('class', 'graph-node__mark'); circle.setAttribute('r', node.type === 'family' ? '27' : String(5 + Math.min(5, Math.sqrt(node.activity || 0) / 2)));
      const hit = document.createElementNS(ns, 'circle'); hit.setAttribute('class', 'graph-node__hit'); hit.setAttribute('r', node.type === 'family' ? '34' : '15');
      const label = document.createElementNS(ns, 'text');
      label.setAttribute('class', `graph-node__label graph-node__label--${node.type}`); label.setAttribute('text-anchor', 'middle');
      if (node.type === 'family') {
        wrapGraphLabel(node.label).forEach((line, index) => { const span = document.createElementNS(ns, 'tspan'); span.setAttribute('x', '0'); span.setAttribute('y', String(46 + index * 13)); span.textContent = line; label.append(span); });
      } else { label.setAttribute('y', '24'); label.textContent = node.label; }
      group.append(circle, hit, label);
      group.addEventListener('mouseenter', event => { state.hoverNode = node.id; applyGraphState(); showGraphTooltip(event, `<strong>${escapeHTML(node.label)}</strong><span>${escapeHTML(node.type === 'family' ? node.description : `${node.ownership === 'mine' ? 'My repository' : 'Connected repository'} · ${node.owner}`)}</span>`); });
      group.addEventListener('focus', event => { state.hoverNode = node.id; applyGraphState(); showGraphTooltip(event, `<strong>${escapeHTML(node.label)}</strong><span>${escapeHTML(node.description || node.owner || '')}</span>`); });
      group.addEventListener('mouseleave', () => { state.hoverNode = null; applyGraphState(); hideGraphTooltip(); });
      group.addEventListener('blur', () => { state.hoverNode = null; applyGraphState(); hideGraphTooltip(); });
      nodesGroup.append(group);
    });
    svg.append(categoryGroup, edgesGroup, nodesGroup);
    svg.dataset.ready = 'true';

    function showGraphTooltip(event, html) {
      tooltip.innerHTML = html; tooltip.hidden = false;
      const stageRect = stage.getBoundingClientRect();
      const targetRect = event.currentTarget.getBoundingClientRect();
      const x = Math.max(12, Math.min(stageRect.width - tooltip.offsetWidth - 12, targetRect.left - stageRect.left + targetRect.width / 2 - tooltip.offsetWidth / 2));
      const preferredY = targetRect.top - stageRect.top - tooltip.offsetHeight - 12;
      const y = preferredY > 8 ? preferredY : targetRect.bottom - stageRect.top + 12;
      tooltip.style.transform = `translate(${x}px, ${Math.min(stageRect.height - tooltip.offsetHeight - 8, y)}px)`;
    }
    function hideGraphTooltip() { tooltip.hidden = true; }

    svg.addEventListener('click', event => {
      const node = event.target.closest('.graph-node');
      if (node) selectGraphNode(node.dataset.id); else if (!event.target.closest('.graph-edge-group')) clearGraphSelection();
    });
    svg.addEventListener('keydown', event => {
      const node = event.target.closest('.graph-node');
      if (node && ['Enter', ' '].includes(event.key)) { event.preventDefault(); selectGraphNode(node.dataset.id); }
    });
    document.addEventListener('keydown', event => { if (event.key === 'Escape' && !root.querySelector('[data-command-palette]').open) clearGraphSelection(); });

    root.querySelectorAll('[data-concept-filter]').forEach(button => button.addEventListener('click', () => {
      state.conceptFilter = button.dataset.conceptFilter;
      root.querySelectorAll('[data-concept-filter]').forEach(item => item.setAttribute('aria-pressed', String(item === button)));
      applyGraphState();
    }));
    root.querySelectorAll('[data-edge-filter]').forEach(button => button.addEventListener('click', () => {
      state.edgeFilter = button.dataset.edgeFilter;
      root.querySelectorAll('[data-edge-filter]').forEach(item => item.setAttribute('aria-pressed', String(item === button)));
      applyGraphState();
    }));

    root.querySelector('[data-graph-summary]').innerHTML = [
      ['Repositories in my map', data.graph.summary.repositories], ['My project families', data.graph.summary.families], ['Contributors GitHub returns', data.graph.summary.contributors], ['Organizations represented', data.graph.summary.organizations], ['My public work span', `${data.graph.summary.active_from?.slice(0, 4) || '—'}–${data.graph.summary.active_to?.slice(0, 4) || '—'}`]
    ].map(([label, value]) => `<div><dt>${escapeHTML(label)}</dt><dd>${escapeHTML(value)}</dd></div>`).join('');

    const mobile = root.querySelector('[data-graph-mobile]');
    mobile.innerHTML = data.families.map(family => `<section class="graph-mobile__family" data-category="${escapeHTML(family.category)}"><button class="graph-mobile__project" type="button" data-mobile-node="${escapeHTML(family.id)}"><span>${escapeHTML(categoryLabels[family.category] || family.theme)}</span><strong>${escapeHTML(family.title)}</strong><small>${escapeHTML(family.description)}</small></button><details><summary>${family.repositories.length} repositories</summary>${family.repositories.map(name => { const repo = data.repositories.find(item => item.full_name === name); return `<button type="button" data-mobile-node="${escapeHTML(name)}">${escapeHTML(repo?.semantic?.title || name)}</button>`; }).join('')}</details></section>`).join('');
    mobile.addEventListener('click', event => { const button = event.target.closest('[data-mobile-node]'); if (button) selectGraphNode(button.dataset.mobileNode); });

    root.querySelector('[data-network-insights]').innerHTML = data.graph.insights.map(insight => `<button type="button" data-network-insight="${escapeHTML(insight.id)}" aria-pressed="false"><span>${escapeHTML(insight.type)}</span><strong>${escapeHTML(insight.title)}</strong><p>${escapeHTML(insight.statement)}</p><small>${escapeHTML(insight.evidence)} · Select to show evidence</small></button>`).join('');
    root.querySelectorAll('[data-network-insight]').forEach(button => button.addEventListener('click', () => {
      const insight = data.graph.insights.find(item => item.id === button.dataset.networkInsight);
      const active = state.insight?.id === insight.id;
      state.insight = active ? null : insight; state.selectedNode = null;
      root.querySelectorAll('[data-network-insight]').forEach(item => item.setAttribute('aria-pressed', String(!active && item === button)));
      if (!active && insight.nodes[0]) {
        const html = inspectorHTML(data, insight.nodes[0]);
        root.querySelector('[data-repo-inspector]').innerHTML = html; root.querySelector('[data-mobile-inspector]').innerHTML = html;
      }
      applyGraphState();
    }));

    const defaultFamily = data.families.find(family => family.id === data.graph.insights[0]?.nodes[0]) || data.families[0];
    if (defaultFamily) {
      const html = inspectorHTML(data, defaultFamily.id);
      root.querySelector('[data-repo-inspector]').innerHTML = html; root.querySelector('[data-mobile-inspector]').innerHTML = html;
    }
    applyGraphState();
  }

  function renderLedger(data) {
    const repositories = data.repositories.filter(repo => repo.curated?.featured || repo.release_count_observed > 0).slice(0, 11);
    root.querySelector('[data-repo-ledger]').innerHTML = repositories.map(repo => {
      const ci = repo.ci?.conclusion || repo.ci?.status || 'unavailable';
      return `<article class="repo-ledger__row">
        <div class="repo-ledger__main"><a href="${escapeHTML(repo.url)}">${escapeHTML(repo.full_name)}</a><p>${escapeHTML(repo.description || repo.curated?.theme || 'Public repository metadata did not include a description.')}</p></div>
        <div class="repo-ledger__fact"><span>Activity</span><strong>${repo.recent.windows['90'].commits} commits / 90d</strong></div>
        <div class="repo-ledger__fact"><span>Observed contributors</span><strong>${number.format(repo.contributor_count_observed)}</strong></div>
        <div class="repo-ledger__fact"><span>Latest release</span><strong>${escapeHTML(repo.latest_release?.tag || 'Not returned')}</strong></div>
        <div class="repo-ledger__fact"><span>License</span><strong>${escapeHTML(repo.license || 'Not returned')}</strong></div>
        <span class="repo-ledger__status" data-status="${escapeHTML(ci)}" aria-label="Latest GitHub Actions status: ${escapeHTML(ci)}"></span>
      </article>`;
    }).join('');
  }

  function renderCollaboration(data) {
    const repeated = data.collaboration.repeated;
    root.querySelector('[data-collaborators]').innerHTML = repeated.length ? repeated.map(person => `<div class="collaborator-row"><span class="collaborator-row__avatar">${person.avatar ? `<img src="${escapeHTML(person.avatar)}" alt="">` : escapeHTML(person.login.slice(0, 2).toUpperCase())}</span><strong>${escapeHTML(person.login)}</strong><span>${person.repository_count} repositories · ${escapeHTML(person.repositories.map(name => name.split('/')[1]).join(' · '))}</span></div>`).join('') : '<p>GitHub returned no repeated non-bot contributor in my current compact repository set.</p>';
    const counts = new Map();
    data.repositories.forEach(repo => counts.set(repo.owner, (counts.get(repo.owner) || 0) + 1));
    root.querySelector('[data-owners]').innerHTML = [...counts].sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0])).map(([owner, count]) => `<div class="owner-row"><strong>${escapeHTML(owner)}</strong><span>${count} repos in page</span></div>`).join('');
  }

  function renderLanguages(data) {
    const allDates = data.language_evolution.flatMap(group => group.repositories.flatMap(repo => [repo.start, repo.end])).filter(Boolean).sort();
    const minYear = Number((allDates[0] || '2016').slice(0, 4));
    const maxYear = Number((allDates.at(-1) || String(new Date().getUTCFullYear())).slice(0, 4));
    const years = Array.from({ length: maxYear - minYear + 1 }, (_, index) => minYear + index);
    const total = new Date(`${maxYear + 1}-01-01T00:00:00Z`) - new Date(`${minYear}-01-01T00:00:00Z`);
    const axis = `<div class="language-axis"><span></span><div class="language-axis__years" style="grid-template-columns:repeat(${years.length},1fr)">${years.map(year => `<span>${year}</span>`).join('')}</div></div>`;
    const rows = data.language_evolution.slice(0, 8).map(group => {
      const spans = group.repositories.map((repo, index) => {
        const start = new Date(`${repo.start}T00:00:00Z`) - new Date(`${minYear}-01-01T00:00:00Z`);
        const end = new Date(`${repo.end || repo.start}T00:00:00Z`) - new Date(`${minYear}-01-01T00:00:00Z`);
        const left = Math.max(0, start / total * 100);
        const width = Math.max(.4, (end - start) / total * 100);
        return `<a class="language-span" href="https://github.com/${escapeHTML(repo.repository)}" style="--start:${left.toFixed(2)}%;--width:${width.toFixed(2)}%;--lane:${index * 9}px" aria-label="${escapeHTML(repo.repository)}, ${formatDate(repo.start)} to ${formatDate(repo.end)}"></a>`;
      }).join('');
      return `<div class="language-row"><div class="language-row__label"><strong>${escapeHTML(group.language)}</strong><span>${group.repositories.length} repos</span></div><div class="language-row__tracks" style="min-height:${Math.max(22, group.repositories.length * 9 + 5)}px">${spans}</div></div>`;
    }).join('');
    root.querySelector('[data-language-timeline]').innerHTML = axis + rows;
  }

  function renderDiscoveries(data) {
    const discoveries = data.discoveries;
    const values = [];
    if (discoveries.longest_active_streak) values.push([`${discoveries.longest_active_streak.days} days without breaking the chain`, `${formatDate(discoveries.longest_active_streak.start)} to ${formatDate(discoveries.longest_active_streak.end)}, with ${number.format(discoveries.longest_active_streak.contributions)} public calendar contributions.`]);
    if (discoveries.busiest_month) values.push([`${number.format(discoveries.busiest_month.contributions)} contributions in one month`, `${formatMonth(discoveries.busiest_month.month)} is my highest visible month in GitHub’s public contribution calendar.`]);
    if (discoveries.widest_recent_month) values.push([`${discoveries.widest_recent_month.repositories} repositories moved in one month`, `In ${formatMonth(discoveries.widest_recent_month.month)}, I committed across ${escapeHTML(discoveries.widest_recent_month.names.slice(0, 5).map(name => name.split('/')[1]).join(', '))}${discoveries.widest_recent_month.names.length > 5 ? ', and more' : ''}.`]);
    if (discoveries.busiest_day) values.push([`${number.format(discoveries.busiest_day.contributions)} contributions on a single day`, `${formatDate(discoveries.busiest_day.date)} is my highest visible public-calendar day.`]);
    root.querySelector('[data-discoveries]').innerHTML = values.map(([title, description], index) => `<article class="discovery-row"><span class="discovery-row__index">0${index + 1}</span><strong>${title}</strong><p>${description}</p></article>`).join('');
  }

  function renderMethod(data) {
    const html = `<h3>Derived measures</h3><p><strong>Recent activity score:</strong> <code>${escapeHTML(data.methodology.activity_score)}</code></p><p><strong>Active repository:</strong> ${escapeHTML(data.methodology.active_repository)}</p><p><strong>Observed contributor:</strong> ${escapeHTML(data.methodology.observed_contributor)}</p><h3>Known limits</h3><ul>${data.limitations.map(item => `<li>${escapeHTML(item)}</li>`).join('')}</ul>`;
    root.querySelector('[data-method-content]').innerHTML = html;
    const dialog = root.querySelector('[data-method-dialog]');
    root.querySelectorAll('[data-open-method]').forEach(button => button.addEventListener('click', () => dialog.showModal()));
    root.querySelector('[data-close-method]').addEventListener('click', () => dialog.close());
    dialog.addEventListener('click', event => { if (event.target === dialog) dialog.close(); });
  }

  function commandIndex(data) {
    const items = [];
    data.repositories.forEach(repo => items.push({ type: 'repository', label: repo.full_name, terms: [repo.owner, repo.primary_language, ...(repo.topics || []), repo.curated?.theme, repo.curated?.family_title].filter(Boolean), action: () => { document.querySelector('#project-graph').scrollIntoView({ behavior: 'smooth' }); selectGraphNode(repo.full_name); } }));
    data.families.forEach(family => items.push({ type: 'project family', label: family.title, terms: [family.theme, family.description], action: () => { document.querySelector('#project-graph').scrollIntoView({ behavior: 'smooth' }); selectGraphNode(family.id); } }));
    data.summary.organization_names.forEach(owner => items.push({ type: 'organization', label: owner, terms: [], action: () => document.querySelector('#collaboration').scrollIntoView({ behavior: 'smooth' }) }));
    data.language_evolution.forEach(group => items.push({ type: 'language', label: group.language, terms: group.repositories.map(repo => repo.repository), action: () => document.querySelector('#languages').scrollIntoView({ behavior: 'smooth' }) }));
    Object.keys(data.contributions.yearly).forEach(year => items.push({ type: 'year', label: `${year} · ${number.format(data.contributions.yearly[year])} contributions`, terms: [year], action: () => document.querySelector('#career').scrollIntoView({ behavior: 'smooth' }) }));
    return items;
  }

  function renderCommandPalette(data) {
    const dialog = root.querySelector('[data-command-palette]');
    const input = root.querySelector('[data-command-input]');
    const results = root.querySelector('[data-command-results]');
    const items = commandIndex(data);
    function update() {
      const query = input.value.trim().toLowerCase();
      state.commandItems = items.filter(item => !query || [item.label, ...item.terms].join(' ').toLowerCase().includes(query)).slice(0, 12);
      state.commandIndex = Math.min(state.commandIndex, Math.max(0, state.commandItems.length - 1));
      results.innerHTML = state.commandItems.length ? state.commandItems.map((item, index) => `<button class="command-result" type="button" role="option" aria-selected="${index === state.commandIndex}" data-command-result="${index}"><span>${escapeHTML(item.type)}</span><strong>${escapeHTML(item.label)}</strong></button>`).join('') : '<p class="command-empty">I couldn’t find a match in my public work.</p>';
    }
    function open() { dialog.showModal(); input.value = ''; state.commandIndex = 0; update(); requestAnimationFrame(() => input.focus()); }
    document.addEventListener('keydown', event => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') { event.preventDefault(); dialog.open ? dialog.close() : open(); return; }
      if (!dialog.open) return;
      if (event.key === 'ArrowDown' || event.key === 'ArrowUp') { event.preventDefault(); state.commandIndex = Math.max(0, Math.min(state.commandItems.length - 1, state.commandIndex + (event.key === 'ArrowDown' ? 1 : -1))); update(); }
      if (event.key === 'Enter' && state.commandItems[state.commandIndex]) { event.preventDefault(); const selected = state.commandItems[state.commandIndex]; dialog.close(); selected.action(); }
    });
    input.addEventListener('input', () => { state.commandIndex = 0; update(); });
    results.addEventListener('click', event => { const button = event.target.closest('[data-command-result]'); if (!button) return; const selected = state.commandItems[Number(button.dataset.commandResult)]; dialog.close(); selected.action(); });
    update();
  }

  fetch(DATA_URL, { cache: 'no-cache' })
    .then(response => { if (!response.ok) throw new Error(`HTTP ${response.status}`); return response.json(); })
    .then(data => {
      state.data = data;
      renderSummary(data);
      renderCurrent(data);
      renderCareer(data);
      const graph = () => renderGraph(data);
      if ('IntersectionObserver' in window) {
        const observer = new IntersectionObserver(entries => { if (entries.some(entry => entry.isIntersecting)) { observer.disconnect(); graph(); } }, { rootMargin: '300px' });
        observer.observe(root.querySelector('#project-graph'));
      } else graph();
      renderLedger(data);
      renderCollaboration(data);
      renderLanguages(data);
      renderDiscoveries(data);
      renderMethod(data);
      renderCommandPalette(data);
    })
    .catch(error => {
      console.error('GitHub life data failed to load', error);
      root.querySelector('[data-load-error]').hidden = false;
    });
})();
