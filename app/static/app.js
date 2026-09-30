const state = { hotspots: [], alerts: [], sites: [], markerLayer: null, siteLayer: null, satellite: null, map: null, alertFilter: 'all' };

const $ = (id) => document.getElementById(id);
const api = async (path, options = {}) => {
  const response = await fetch(path, options);
  if (!response.ok) throw new Error(await response.text());
  return response.json();
};
const escapeHtml = (value) => String(value ?? '').replace(/[&<>'"]/g, (c) => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));
const relativeTime = (stamp) => {
  const hours = Math.max(0, Math.round((Date.now() - new Date(stamp).getTime()) / 3600000));
  return hours < 1 ? 'just now' : `${hours}h ago`;
};
const severityColor = (severity) => ({ CRITICAL: '#ff5b59', HIGH: '#ff9561', MEDIUM: '#f8c865', LOW: '#55d6bd' }[severity] || '#f8c865');

function initMap() {
  state.map = L.map('map', { zoomControl: true, minZoom: 4, maxZoom: 15 }).setView([22.3, 79.2], 5);
  // Use the public OSM raster tiles as the dependable default. Carto's dark
  // basemap began requiring a token and can otherwise render an API-key
  // watermark over the entire judging demo.
  const dark = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { maxZoom: 19, attribution: '&copy; OpenStreetMap contributors' });
  const labels = L.layerGroup();
  const satellite = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', { maxZoom: 18, attribution: 'Esri World Imagery' });
  dark.addTo(state.map); state.satellite = satellite;
  state.markerLayer = L.layerGroup().addTo(state.map); state.siteLayer = L.layerGroup().addTo(state.map);
  document.querySelector('[data-layer="satellite"]').addEventListener('click', (event) => {
    const button = event.currentTarget;
    button.classList.toggle('active');
    if (button.classList.contains('active')) { satellite.addTo(state.map); }
    else { state.map.removeLayer(satellite); }
  });
  document.querySelector('[data-layer="hotspots"]').addEventListener('click', (event) => { event.currentTarget.classList.toggle('active'); state.markerLayer.eachLayer((layer) => layer.setOpacity(event.currentTarget.classList.contains('active') ? 1 : 0)); });
  document.querySelector('[data-layer="sites"]').addEventListener('click', (event) => { event.currentTarget.classList.toggle('active'); state.siteLayer.eachLayer((layer) => layer.setStyle ? layer.setStyle({ opacity: event.currentTarget.classList.contains('active') ? .9 : 0, fillOpacity: event.currentTarget.classList.contains('active') ? .14 : 0 }) : layer.setOpacity(event.currentTarget.classList.contains('active') ? 1 : 0)); });
  document.querySelector('.map-expand').addEventListener('click', () => { if (state.hotspots.length) state.map.fitBounds(L.latLngBounds(state.hotspots.map((x) => [x.latitude, x.longitude])), { padding: [35, 35] }); });
}

function drawMap() {
  state.markerLayer.clearLayers(); state.siteLayer.clearLayers();
  state.sites.forEach((site) => {
    const circle = L.circle([site.lat, site.lon], { radius: 13500, color: '#65a9dc', weight: 1, opacity: .7, fillColor: '#65a9dc', fillOpacity: .11 });
    circle.bindTooltip(`<strong>${escapeHtml(site.name)}</strong><br>${escapeHtml(site.type)} · ${escapeHtml(site.operator)}`, { direction: 'top', className: 'ember-tooltip' });
    circle.addTo(state.siteLayer);
  });
  state.hotspots.forEach((item) => {
    const color = severityColor(item.severity);
    const outer = L.circleMarker([item.latitude, item.longitude], { radius: 12 + Math.min(8, item.risk_score / 18), color, weight: 1, opacity: .22, fillColor: color, fillOpacity: .1 });
    const marker = L.circleMarker([item.latitude, item.longitude], { radius: 5 + Math.min(4, item.risk_score / 28), color, weight: 2, opacity: .95, fillColor: color, fillOpacity: .86 });
    const popup = `<div class="map-popup"><b>${escapeHtml(item.label)}</b><br><span>${escapeHtml(item.nearest_site)}</span><br><strong>${item.risk_score}/100 risk</strong> · ${item.frp.toFixed(1)} MW</div>`;
    marker.bindPopup(popup); marker.on('click', () => openDetail(item.id)); outer.on('click', () => openDetail(item.id));
    outer.addTo(state.markerLayer); marker.addTo(state.markerLayer);
  });
}

function renderMetrics(overview) {
  const metrics = overview.metrics;
  $('metricAlerts').textContent = metrics.active_alerts;
  $('metricCritical').textContent = metrics.critical_zones;
  $('metricHotspots').textContent = metrics.hotspots_24h;
  $('metricConfidence').textContent = metrics.mean_confidence;
  $('metricFireText').textContent = `${metrics.industrial_fires} industrial fire${metrics.industrial_fires === 1 ? '' : 's'} detected`;
  $('navAlertCount').textContent = metrics.active_alerts;
  $('alertBadge').textContent = metrics.active_alerts;
  $('modeText').textContent = `${overview.mode} MODE`;
  $('lastUpdated').textContent = `LAST SYNC ${relativeTime(overview.last_updated).toUpperCase()}`;
  $('firmsSource').textContent = overview.source_status.firms;
  $('osmSource').textContent = overview.source_status.osm;
  $('insightNumber').textContent = metrics.industrial_fires + metrics.persistent_sources;
  const probability = Math.min(99, Math.round((metrics.industrial_fires / Math.max(1, metrics.hotspots_24h)) * 100));
  $('insightValue').textContent = `${probability}% likelihood`;
  $('insightBar').style.width = `${Math.max(8, probability)}%`;
  $('mapStatus').textContent = overview.mode === 'LIVE' ? 'LIVE FIRMS WINDOW · LAST 48 HOURS' : 'DEMO SENSOR WINDOW · LAST 24 HOURS';
}

function renderAlerts() {
  const filtered = state.alertFilter === 'all' ? state.alerts : state.alerts.filter((x) => x.severity === state.alertFilter);
  $('alertList').innerHTML = filtered.length ? filtered.slice(0, 8).map((item) => `<div class="alert-item" data-id="${escapeHtml(item.hotspot_id)}"><span class="alert-severity ${item.severity}"></span><div><div class="alert-title">${escapeHtml(item.title)}</div><span class="alert-location">${escapeHtml(item.location)}</span><span class="alert-summary">${escapeHtml(item.summary)}</span></div><div><div class="alert-time">${relativeTime(item.timestamp)}</div><div class="alert-score">${item.risk_score}</div></div></div>`).join('') : '<div class="loading-state">No events match this filter.</div>';
  document.querySelectorAll('.alert-item').forEach((el) => el.addEventListener('click', () => openDetail(el.dataset.id)));
}

function renderTimeline(timeline) {
  const max = Math.max(1, ...timeline.map((x) => x.total));
  $('timeline').innerHTML = timeline.length ? timeline.map((point) => `<div class="timeline-bar" title="${escapeHtml(point.time)} · ${point.total} events" style="height:${Math.max(9, 16 + (point.total / max) * 47)}px"></div>`).join('') : '<div class="loading-state">No activity recorded.</div>';
}

function openDetail(id) {
  const item = state.hotspots.find((x) => x.id === id); if (!item) return;
  $('drawerTitle').textContent = item.label.toLowerCase().replace(/\b\w/g, (c) => c.toUpperCase());
  $('drawerBody').innerHTML = `<div class="drawer-body"><div class="dossier-banner"><div><div class="dossier-label">${escapeHtml(item.severity)} PRIORITY</div><div style="font-size:10px;color:#9dafb0;margin-top:4px">${escapeHtml(item.status)} · ${relativeTime(item.acquired_at)}</div></div><div class="dossier-score">${item.risk_score}<small style="font-size:9px;color:#779098">/100</small></div></div><div class="drawer-section"><h3>EVENT GEOMETRY</h3><div class="coord-row"><span>Latitude / longitude</span><strong>${item.latitude.toFixed(4)}, ${item.longitude.toFixed(4)}</strong></div><div class="coord-row"><span>Nearest asset</span><strong>${escapeHtml(item.nearest_site)}</strong></div><div class="coord-row"><span>Asset distance</span><strong>${item.distance_to_site_km.toFixed(1)} km</strong></div></div><div class="drawer-section"><h3>EXPLAINABLE ASSESSMENT</h3>${item.reasoning.map((reason) => `<div class="reason-item">${escapeHtml(reason)}</div>`).join('')}</div><div class="drawer-section"><h3>RISK FACTORS</h3>${item.risk_factors.map((factor) => `<div class="factor-row"><div class="factor-meta"><span>${escapeHtml(factor.name)} <em style="font-style:normal;color:#536c75">· ${escapeHtml(factor.detail)}</em></span><b>${factor.value}%</b></div><div class="factor-track"><i style="width:${factor.value}%"></i></div></div>`).join('')}</div><button class="report-button" id="reportButton">↗ Generate evidence brief</button></div>`;
  $('detailDrawer').classList.add('open'); $('detailDrawer').setAttribute('aria-hidden', 'false');
  $('reportButton').addEventListener('click', () => generateReport(item.id));
  if (state.map) state.map.flyTo([item.latitude, item.longitude], 9, { duration: .7 });
}

async function generateReport(id) {
  try { const report = await api(`/api/report/${encodeURIComponent(id)}`); const blob = new Blob([report.markdown], { type: 'text/markdown' }); const url = URL.createObjectURL(blob); const a = document.createElement('a'); a.href = url; a.download = `emberwatch-${id}.md`; a.click(); URL.revokeObjectURL(url); showToast('Evidence brief downloaded'); } catch { showToast('Could not generate brief'); }
}

function closeDetail() { $('detailDrawer').classList.remove('open'); $('detailDrawer').setAttribute('aria-hidden', 'true'); }
function showToast(message) { const toast = $('toast'); toast.textContent = message; toast.classList.add('show'); setTimeout(() => toast.classList.remove('show'), 3000); }
function setActiveNav(id) {
  document.querySelectorAll('.nav-item').forEach((item) => item.classList.remove('active'));
  $(id).classList.add('active');
}
function scrollToPanel(selector, navId) {
  const panel = document.querySelector(selector);
  if (panel) panel.scrollIntoView({ behavior: 'smooth', block: 'start' });
  if (navId) setActiveNav(navId);
}

async function loadData() {
  try {
    const [overview, hotspots, alerts, sites, timeline] = await Promise.all([api('/api/overview'), api('/api/hotspots'), api('/api/alerts'), api('/api/industrial-sites'), api('/api/timeline')]);
    state.hotspots = hotspots; state.alerts = alerts; state.sites = sites;
    renderMetrics(overview); renderAlerts(); renderTimeline(timeline); drawMap();
  } catch (error) { showToast('API unavailable — start the FastAPI server'); console.error(error); }
}

async function refreshData() {
  const button = $('refreshBtn'); button.disabled = true; button.innerHTML = '<span class="refresh-icon">↻</span> Syncing sources…';
  try { const result = await api('/api/refresh', { method: 'POST' }); showToast(result.message); await loadData(); } catch (error) { showToast('Refresh failed; demo data is still available'); } finally { button.disabled = false; button.innerHTML = '<span class="refresh-icon">↻</span> Refresh intelligence'; }
}
async function runShowcase() {
  const button = $('showcaseBtn'); button.disabled = true; button.innerHTML = '<span>✦</span> Loading scenario…';
  try { await api('/api/demo/reset', { method: 'POST' }); await loadData(); const sites = document.querySelector('[data-layer="sites"]'); if (!sites.classList.contains('active')) sites.click(); setActiveNav('navAlerts'); document.querySelector('.workspace-grid').scrollIntoView({ behavior: 'smooth', block: 'start' }); setTimeout(() => { if (state.alerts[0]) openDetail(state.alerts[0].hotspot_id); showToast('Judge demo loaded — explore the dossier, filters, layers and evidence brief'); }, 700); } catch { showToast('Could not load the showcase scenario'); } finally { button.disabled = false; button.innerHTML = '<span>✦</span> Judge demo'; }
}

document.addEventListener('DOMContentLoaded', () => {
  initMap(); loadData();
  $('refreshBtn').addEventListener('click', refreshData); $('drawerClose').addEventListener('click', closeDetail); $('drawerBackdrop').addEventListener('click', closeDetail);
  $('showcaseBtn').addEventListener('click', runShowcase);
  $('navAlerts').addEventListener('click', () => scrollToPanel('.alerts-panel', 'navAlerts'));
  $('navAtlas').addEventListener('click', () => { scrollToPanel('.map-card', 'navAtlas'); const sites = document.querySelector('[data-layer="sites"]'); if (!sites.classList.contains('active')) sites.click(); });
  $('navReports').addEventListener('click', () => { setActiveNav('navReports'); const first = state.alerts[0]; if (first) openDetail(first.hotspot_id); else showToast('No incident reports available'); });
  $('themeToggle').addEventListener('click', () => { document.body.classList.toggle('light-theme'); localStorage.setItem('emberwatch-theme', document.body.classList.contains('light-theme') ? 'light' : 'dark'); });
  if (localStorage.getItem('emberwatch-theme') === 'light') document.body.classList.add('light-theme');
  document.querySelectorAll('.filter-chip').forEach((button) => button.addEventListener('click', () => { document.querySelectorAll('.filter-chip').forEach((x) => x.classList.remove('active')); button.classList.add('active'); state.alertFilter = button.dataset.filter.toLowerCase(); renderAlerts(); }));
  $('showAllBtn').addEventListener('click', () => { document.querySelector('[data-filter="all"]').click(); document.querySelector('.alerts-panel').scrollIntoView({ behavior: 'smooth' }); });
});
