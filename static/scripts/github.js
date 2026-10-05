(() => {
  const root = document.querySelector('[data-github-life]');
  if (!root) return;

  const DATA_URL = '../data/github-life.json';
  const number = new Intl.NumberFormat('en-US');
  const dateFormat = new Intl.DateTimeFormat('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
  const monthFormat = new Intl.DateTimeFormat('en-US', { year: 'numeric', month: 'long' });
  const state = { data: null, repository: null, edgeFilter: 'all', commandIndex: 0, commandItems: [] };

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

  function graphPositions(data) {
    const width = 1000;
    const height = 680;
    const families = data.graph.nodes.filter(node => node.type === 'family');
    const positions = new Map();
    families.forEach((family, index) => {
      const angle = -Math.PI / 2 + index / families.length * Math.PI * 2;
      positions.set(family.id, { x: width / 2 + Math.cos(angle) * 310, y: height / 2 + Math.sin(angle) * 220 });
    });
    families.forEach(family => {
      const center = positions.get(family.id);
      const repositories = data.graph.nodes.filter(node => node.type === 'repository' && node.family === family.id);
      repositories.forEach((repo, index) => {
        const angle = (index / Math.max(1, repositories.length)) * Math.PI * 2 + .35;
        const radius = repositories.length > 4 ? 105 : 86;
        positions.set(repo.id, { x: center.x + Math.cos(angle) * radius, y: center.y + Math.sin(angle) * radius });
      });
    });
    const ungrouped = data.graph.nodes.filter(node => node.type === 'repository' && !positions.has(node.id));
    ungrouped.forEach((repo, index) => positions.set(repo.id, { x: 110 + index % 7 * 125, y: 620 - Math.floor(index / 7) * 48 }));
    return positions;
  }

  function inspectorHTML(data, id) {
    const repo = data.repositories.find(item => item.full_name === id);
    if (repo) {
      const connected = data.graph.edges.filter(edge => edge.source === id || edge.target === id);
      return `<p class="repo-inspector__eyebrow">${escapeHTML(repo.curated?.theme || repo.owner)}</p>
        <h3>${escapeHTML(repo.full_name)}</h3>
        <p>${escapeHTML(repo.description || repo.curated?.family_title || 'Public repository metadata did not include a description.')}</p>
        <div class="inspector-facts">
          <div><span>90-day commits</span><strong>${number.format(repo.recent.windows['90'].commits)}</strong></div>
          <div><span>Active days / 30d</span><strong>${number.format(repo.recent.windows['30'].active_days)}</strong></div>
          <div><span>Observed contributors</span><strong>${number.format(repo.contributor_count_observed)}</strong></div>
          <div><span>Releases observed</span><strong>${number.format(repo.release_count_observed)}</strong></div>
          <div><span>Primary language</span><strong>${escapeHTML(repo.primary_language || 'Unclassified')}</strong></div>
          <div><span>License</span><strong>${escapeHTML(repo.license || 'Not returned')}</strong></div>
        </div>
        <div class="inspector-links"><a href="${escapeHTML(repo.url)}">Repository ↗</a>${repo.homepage ? `<a href="${escapeHTML(repo.homepage)}">Documentation ↗</a>` : ''}</div>
        <ul class="inspector-edges">${connected.slice(0, 6).map(edge => `<li><b>${escapeHTML(edge.type.replaceAll('-', ' '))}</b><br>${escapeHTML(edge.label)}</li>`).join('')}</ul>`;
    }
    const family = data.families.find(item => item.id === id);
    if (family) return `<p class="repo-inspector__eyebrow">My project family</p><h3>${escapeHTML(family.title)}</h3><p>${escapeHTML(family.description)}</p><div class="inspector-facts"><div><span>Theme</span><strong>${escapeHTML(family.theme)}</strong></div><div><span>Repositories I connect here</span><strong>${family.repositories.length}</strong></div></div><ul class="inspector-edges">${family.repositories.map(name => `<li><b>${escapeHTML(name)}</b></li>`).join('')}</ul>`;
    return '';
  }

  function selectGraphNode(id) {
    state.repository = id;
    const stage = root.querySelector('[data-project-graph]');
    stage?.querySelectorAll('.graph-node').forEach(node => node.classList.toggle('is-selected', node.dataset.id === id));
    root.querySelector('[data-repo-inspector]').innerHTML = inspectorHTML(state.data, id);
  }

  function renderGraph(data) {
    const svg = root.querySelector('[data-project-graph]');
    const ns = 'http://www.w3.org/2000/svg';
    const positions = graphPositions(data);
    const edgesGroup = document.createElementNS(ns, 'g');
    edgesGroup.setAttribute('aria-hidden', 'true');
    data.graph.edges.forEach(edge => {
      const start = positions.get(edge.source);
      const end = positions.get(edge.target);
      if (!start || !end) return;
      const line = document.createElementNS(ns, 'line');
      line.setAttribute('x1', start.x); line.setAttribute('y1', start.y); line.setAttribute('x2', end.x); line.setAttribute('y2', end.y);
      line.setAttribute('class', 'graph-edge'); line.dataset.type = edge.type; line.dataset.source = edge.source; line.dataset.target = edge.target;
      edgesGroup.append(line);
    });
    const nodesGroup = document.createElementNS(ns, 'g');
    data.graph.nodes.forEach(node => {
      const point = positions.get(node.id);
      if (!point) return;
      const group = document.createElementNS(ns, 'g');
      group.setAttribute('class', 'graph-node'); group.dataset.id = node.id; group.dataset.type = node.type;
      if (node.activity > 0) group.dataset.active = 'true';
      group.setAttribute('transform', `translate(${point.x} ${point.y})`); group.setAttribute('role', 'button'); group.setAttribute('tabindex', '0');
      group.setAttribute('aria-label', `${node.type}: ${node.label}`);
      const circle = document.createElementNS(ns, 'circle');
      circle.setAttribute('r', node.type === 'family' ? '22' : String(7 + Math.min(9, Math.sqrt(node.activity || 0))));
      const label = document.createElementNS(ns, 'text');
      label.setAttribute('text-anchor', 'middle'); label.setAttribute('y', node.type === 'family' ? '38' : '25');
      label.textContent = node.label.length > 22 ? `${node.label.slice(0, 20)}…` : node.label;
      group.append(circle, label); nodesGroup.append(group);
    });
    svg.append(edgesGroup, nodesGroup);
    svg.addEventListener('click', event => { const node = event.target.closest('.graph-node'); if (node) selectGraphNode(node.dataset.id); });
    svg.addEventListener('keydown', event => { const node = event.target.closest('.graph-node'); if (node && ['Enter', ' '].includes(event.key)) { event.preventDefault(); selectGraphNode(node.dataset.id); } });

    root.querySelectorAll('[data-edge-filter]').forEach(button => button.addEventListener('click', () => {
      state.edgeFilter = button.dataset.edgeFilter;
      root.querySelectorAll('[data-edge-filter]').forEach(item => item.setAttribute('aria-pressed', String(item === button)));
      svg.querySelectorAll('.graph-edge').forEach(edge => edge.classList.toggle('is-dimmed', state.edgeFilter !== 'all' && edge.dataset.type !== state.edgeFilter));
      const visible = new Set();
      svg.querySelectorAll(`.graph-edge${state.edgeFilter === 'all' ? '' : `:not(.is-dimmed)`}`).forEach(edge => { visible.add(edge.dataset.source); visible.add(edge.dataset.target); });
      svg.querySelectorAll('.graph-node').forEach(node => node.classList.toggle('is-dimmed', state.edgeFilter !== 'all' && !visible.has(node.dataset.id)));
    }));
    const mobile = root.querySelector('[data-graph-mobile]');
    mobile.innerHTML = data.families.map(family => `<section class="graph-mobile__family"><h3>${escapeHTML(family.title)}</h3><p>${escapeHTML(family.description)}</p>${family.repositories.map(name => `<button type="button" data-mobile-repo="${escapeHTML(name)}">${escapeHTML(name)}</button>`).join('')}</section>`).join('');
    mobile.addEventListener('click', event => {
      const button = event.target.closest('[data-mobile-repo]');
      if (!button) return;
      const repo = data.repositories.find(item => item.full_name === button.dataset.mobileRepo);
      if (repo) window.open(repo.url, '_blank', 'noopener');
    });
    const defaultRepo = data.repositories.find(repo => repo.recent.score > 0 && repo.curated) || data.repositories[0];
    if (defaultRepo) selectGraphNode(defaultRepo.full_name);
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
