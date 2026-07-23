'use strict';

const ESTRATO_ORDER = ['A1', 'A2', 'A3', 'A4', 'B1', 'B2', 'B3', 'B4', 'C'];
const ESTRATO_COLORS = {
  A1: '#C8962B', A2: '#D6A93E', A3: '#E0BC5C', A4: '#E8CE86',
  B1: '#7E93A6', B2: '#8FA1B0', B3: '#A3B1BC', B4: '#B9C3CB', C: '#C9CDD2',
};

let journals = [];
let conferences = [];
let areas = [];
let chartsRendered = false;

const selectedJournalAreas = new Set();
const selectedConferenceAreas = new Set();
const selectedJournalEstratos = new Set();
const selectedConferenceEstratos = new Set();

const byId = (id) => document.getElementById(id);
const escapeHtml = (value) => String(value ?? '')
  .replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;')
  .replaceAll('"', '&quot;').replaceAll("'", '&#039;');

function normalizeRows(rows) {
  return (rows ?? []).map((row) => ({
    ...row,
    areas: Array.isArray(row.areas) ? row.areas : [],
    areas_str: Array.isArray(row.areas) ? row.areas.join(', ') : '',
  }));
}

function applyFilters(rows, query, selectedAreas, selectedEstratos) {
  const terms = query.toLowerCase().split(',').map((term) => term.trim()).filter(Boolean);

  return rows.filter((row) => {
    const haystack = [row.name, row.sigla, row.issn, row.areas_str].filter(Boolean).join(' ').toLowerCase();
    const matchesQuery = terms.length === 0 || terms.some((term) => haystack.includes(term));
    const matchesArea = selectedAreas.length === 0 || row.areas.some((area) => selectedAreas.includes(area));
    const matchesEstrato = selectedEstratos.length === 0 || selectedEstratos.includes(row.estrato);
    return matchesQuery && matchesArea && matchesEstrato;
  }).sort((a, b) => {
    const rankA = ESTRATO_ORDER.indexOf(a.estrato);
    const rankB = ESTRATO_ORDER.indexOf(b.estrato);
    return (rankA === -1 ? 99 : rankA) - (rankB === -1 ? 99 : rankB);
  });
}

function badge(estrato) {
  if (!estrato) return '';
  const color = ESTRATO_COLORS[estrato] ?? '#C9CDD2';
  return `<span class="badge" style="background:${color}">${escapeHtml(estrato)}</span>`;
}

function createMultiSelect({ rootId, options, selected, placeholder, emptyMessage = 'No options found.', onChange }) {
  const root = byId(rootId);
  if (!root) throw new Error(`Multi-select "${rootId}" was not found.`);

  const trigger = root.querySelector('.multi-select-trigger');
  const valuesContainer = root.querySelector('.multi-select-values');
  const menu = root.querySelector('.multi-select-menu');
  const searchInput = root.querySelector('.multi-select-search');
  const optionsContainer = root.querySelector('.multi-select-options');
  let resizeFrame = null;

  const closeMenu = () => {
    root.classList.remove('open');
    menu.hidden = true;
    trigger.setAttribute('aria-expanded', 'false');
  };

  const tagHtml = (value) => `
    <span class="multi-select-tag">
      <span class="multi-select-tag-label">${escapeHtml(value)}</span>
      <button type="button" class="multi-select-tag-remove" data-remove-value="${escapeHtml(value)}" aria-label="Remove ${escapeHtml(value)}">×</button>
    </span>
  `;

  const bindTagRemoval = () => {
    valuesContainer.querySelectorAll('[data-remove-value]').forEach((button) => {
      button.addEventListener('click', (event) => {
        event.stopPropagation();
        selected.delete(button.dataset.removeValue);
        renderSelectedValues();
        renderOptions();
        onChange();
      });
    });
  };

  const renderSelectedValues = () => {
    const selectedValues = [...selected];

    if (selectedValues.length === 0) {
      valuesContainer.innerHTML = `<span class="multi-select-placeholder">${escapeHtml(placeholder)}</span>`;
      return;
    }

    // Render every tag briefly so their real widths can be measured.
    valuesContainer.innerHTML = selectedValues.map(tagHtml).join('');

    requestAnimationFrame(() => {
      const tags = [...valuesContainer.querySelectorAll('.multi-select-tag')];
      const tagWidths = tags.map((tag) => tag.getBoundingClientRect().width);
      const availableWidth = valuesContainer.clientWidth;
      const gap = 6;

      const summaryProbe = document.createElement('span');
      summaryProbe.className = 'multi-select-summary multi-select-summary-probe';
      summaryProbe.textContent = `+${selectedValues.length}`;
      valuesContainer.appendChild(summaryProbe);
      const summaryWidth = summaryProbe.getBoundingClientRect().width;
      summaryProbe.remove();

      let visibleCount = selectedValues.length;

      for (let count = selectedValues.length; count >= 0; count -= 1) {
        const tagsWidth = tagWidths.slice(0, count).reduce((sum, width) => sum + width, 0);
        const tagsGaps = Math.max(0, count - 1) * gap;
        const hasHidden = count < selectedValues.length;
        const summarySpace = hasHidden ? summaryWidth + (count > 0 ? gap : 0) : 0;

        if (tagsWidth + tagsGaps + summarySpace <= availableWidth) {
          visibleCount = count;
          break;
        }
      }

      const hiddenCount = selectedValues.length - visibleCount;
      valuesContainer.innerHTML = selectedValues.slice(0, visibleCount).map(tagHtml).join('');

      if (hiddenCount > 0) {
        valuesContainer.insertAdjacentHTML(
          'beforeend',
          `<span class="multi-select-summary" title="${hiddenCount} more selected">+${hiddenCount}</span>`,
        );
      }

      bindTagRemoval();
    });
  };

  const renderOptions = () => {
    const query = searchInput ? searchInput.value.trim().toLowerCase() : '';
    const filteredOptions = options.filter((option) => option.toLowerCase().includes(query));

    if (filteredOptions.length === 0) {
      optionsContainer.innerHTML = `<div class="multi-select-empty">${escapeHtml(emptyMessage)}</div>`;
      return;
    }

    optionsContainer.innerHTML = filteredOptions.map((option) => `
      <label class="multi-select-option">
        <input type="checkbox" value="${escapeHtml(option)}" ${selected.has(option) ? 'checked' : ''} />
        <span>${escapeHtml(option)}</span>
      </label>
    `).join('');

    optionsContainer.querySelectorAll('input[type="checkbox"]').forEach((checkbox) => {
      checkbox.addEventListener('change', () => {
        if (checkbox.checked) selected.add(checkbox.value);
        else selected.delete(checkbox.value);
        renderSelectedValues();
        renderOptions();
        onChange();
      });
    });
  };

  const openMenu = () => {
    root.classList.add('open');
    menu.hidden = false;
    trigger.setAttribute('aria-expanded', 'true');
    if (searchInput) {
      searchInput.value = '';
      searchInput.focus();
    }
    renderOptions();
  };

  trigger.addEventListener('click', () => {
    if (menu.hidden) openMenu();
    else closeMenu();
  });

  if (searchInput) searchInput.addEventListener('input', renderOptions);
  menu.addEventListener('click', (event) => event.stopPropagation());

  document.addEventListener('click', (event) => {
    if (!root.contains(event.target)) closeMenu();
  });

  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') closeMenu();
  });

  if ('ResizeObserver' in window) {
    const observer = new ResizeObserver(() => {
      cancelAnimationFrame(resizeFrame);
      resizeFrame = requestAnimationFrame(renderSelectedValues);
    });
    observer.observe(valuesContainer);
  }

  renderSelectedValues();
  renderOptions();
}

function renderJournals() {
  const filtered = applyFilters(
    journals,
    byId('journal-search').value,
    [...selectedJournalAreas],
    [...selectedJournalEstratos],
  );

  byId('journal-caption').textContent = `${filtered.length} of ${journals.length} journals`;
  byId('journal-body').innerHTML = filtered.length ? filtered.map((row) => `
    <tr>
      <td>${escapeHtml(row.name)}</td><td>${escapeHtml(row.issn)}</td>
      <td>${row.percentile == null || row.percentile === '' ? '' : `${escapeHtml(row.percentile)}%`}</td>
      <td>${badge(row.estrato)}</td><td>${escapeHtml(row.areas_str)}</td>
      <td>${row.scopus_url ? `<a href="${escapeHtml(row.scopus_url)}" target="_blank" rel="noopener noreferrer">open ↗</a>` : ''}</td>
    </tr>`).join('') : '<tr><td class="empty" colspan="6">No journals match these filters.</td></tr>';
}

function renderConferences() {
  const filtered = applyFilters(
    conferences,
    byId('conference-search').value,
    [...selectedConferenceAreas],
    [...selectedConferenceEstratos],
  );

  byId('conference-caption').textContent = `${filtered.length} of ${conferences.length} conferences`;
  byId('conference-body').innerHTML = filtered.length ? filtered.map((row) => `
    <tr><td>${escapeHtml(row.sigla)}</td><td>${escapeHtml(row.name)}</td><td>${badge(row.estrato)}</td>
    <td>${escapeHtml(row.areas_str)}</td><td>${escapeHtml(row.submission)}</td><td>${escapeHtml(row.event_date)}</td></tr>`).join('')
    : '<tr><td class="empty" colspan="6">No conferences match these filters.</td></tr>';
}

function distributionData(rows) {
  const counts = Object.fromEntries(ESTRATO_ORDER.map((item) => [item, 0]));
  rows.forEach((row) => { if (row.estrato in counts) counts[row.estrato] += 1; });
  const categories = ESTRATO_ORDER.filter((item) => counts[item] > 0);
  return { categories, values: categories.map((item) => counts[item]) };
}

function areaData(rows) {
  const counts = {};
  rows.forEach((row) => row.areas.forEach((area) => { counts[area] = (counts[area] ?? 0) + 1; }));
  return Object.entries(counts).sort((a, b) => a[1] - b[1]);
}

function plotDistribution(elementId, rows, title) {
  const { categories, values } = distributionData(rows);
  Plotly.newPlot(elementId, [{ x: values, y: categories, type: 'bar', orientation: 'h',
    marker: { color: categories.map((item) => ESTRATO_COLORS[item]) }, text: values, textposition: 'outside',
    hovertemplate: '%{y}: %{x} entries<extra></extra>' }], chartLayout(title, 300), { responsive: true, displayModeBar: false });
}

function plotAreas(elementId, rows, title) {
  const entries = areaData(rows);
  Plotly.newPlot(elementId, [{ x: entries.map(([, count]) => count), y: entries.map(([area]) => area), type: 'bar', orientation: 'h',
    marker: { color: '#D6A93E' }, text: entries.map(([, count]) => count), textposition: 'outside',
    hovertemplate: '%{y}: %{x}<extra></extra>' }], chartLayout(title, 360), { responsive: true, displayModeBar: false });
}

function chartLayout(title, height) {
  return { title: { text: title, font: { family: 'Fraunces', size: 16, color: '#ECEEF1' } }, height,
    margin: { l: 70, r: 35, t: 50, b: 35 }, paper_bgcolor: 'rgba(0,0,0,0)', plot_bgcolor: 'rgba(0,0,0,0)',
    font: { family: 'Inter', color: '#9AA3AD' }, xaxis: { gridcolor: '#2C333D', zeroline: false },
    yaxis: { automargin: true }, showlegend: false };
}

function renderCharts() {
  if (chartsRendered || typeof Plotly === 'undefined') return;
  plotDistribution('journal-distribution', journals, 'Journals by estrato');
  plotDistribution('conference-distribution', conferences, 'Conferences by estrato');
  plotAreas('journal-areas', journals, 'Journals per area');
  plotAreas('conference-areas', conferences, 'Conferences per area');
  chartsRendered = true;
}

function setupTabs() {
  document.querySelectorAll('.tab').forEach((button) => button.addEventListener('click', () => {
    document.querySelectorAll('.tab').forEach((tab) => { tab.classList.remove('active'); tab.setAttribute('aria-selected', 'false'); });
    document.querySelectorAll('.tab-panel').forEach((panel) => { panel.classList.remove('active'); panel.hidden = true; });
    button.classList.add('active');
    button.setAttribute('aria-selected', 'true');
    const panel = byId(button.dataset.tab);
    panel.classList.add('active');
    panel.hidden = false;
    if (button.dataset.tab === 'overview-panel') renderCharts();
  }));
}

async function init() {
  setupTabs();

  try {
    const response = await fetch('./capes_data.json');
    if (!response.ok) throw new Error(`HTTP ${response.status}`);

    const raw = await response.json();
    journals = normalizeRows(raw.revistas);
    conferences = normalizeRows(raw.conferencias);
    areas = Array.isArray(raw.areas) ? raw.areas : [];

    byId('journal-count').textContent = journals.length;
    byId('conference-count').textContent = conferences.length;
    byId('area-count').textContent = areas.length;
    byId('a1-count').textContent = [...journals, ...conferences].filter((row) => row.estrato === 'A1').length;

    createMultiSelect({
      rootId: 'journal-area-filter',
      options: areas,
      selected: selectedJournalAreas,
      placeholder: 'All areas',
      onChange: renderJournals,
    });

    createMultiSelect({
      rootId: 'conference-area-filter',
      options: areas,
      selected: selectedConferenceAreas,
      placeholder: 'All areas',
      onChange: renderConferences,
    });

    createMultiSelect({
      rootId: 'journal-estrato-filter',
      options: ESTRATO_ORDER.filter((estrato) => journals.some((row) => row.estrato === estrato)),
      selected: selectedJournalEstratos,
      placeholder: 'All estratos',
      emptyMessage: 'No estratos found.',
      onChange: renderJournals,
    });

    createMultiSelect({
      rootId: 'conference-estrato-filter',
      options: ESTRATO_ORDER.filter((estrato) => conferences.some((row) => row.estrato === estrato)),
      selected: selectedConferenceEstratos,
      placeholder: 'All estratos',
      emptyMessage: 'No estratos found.',
      onChange: renderConferences,
    });

    byId('journal-search').addEventListener('input', renderJournals);
    byId('conference-search').addEventListener('input', renderConferences);

    renderJournals();
    renderConferences();
    byId('status').remove();
  } catch (error) {
    const status = byId('status');
    status.className = 'status error';
    status.innerHTML = '<strong>Could not load capes_data.json.</strong><br>Place the JSON file in the same folder as index.html, then serve or publish the folder through GitHub Pages.';
    console.error('CAPES data loading failed:', error);
  }
}

document.addEventListener('DOMContentLoaded', init);
