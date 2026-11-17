'use strict'; // Keep the discovery interface isolated from backend workflow state.
let discoveryCatalog = [], activeCategory = 'all'; // Hold catalog data and the selected category.
let savedTargets; // Restore favorites defensively if stored data is invalid.
try { savedTargets = new Set(JSON.parse(localStorage.getItem('astro-favorites') || '[]')); } catch { savedTargets = new Set(); } // Keep malformed preferences from blocking startup.
const safeText = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); // Escape catalog text before rendering markup.
function artwork(item) { // Render local lunar imagery or an illustrative category motif.
 const category = item.category.toLowerCase(); // Normalize categories for the visual treatment.
 return `<div class="object-art art-${safeText(category.includes('star') ? 'star' : category.includes('galax') ? 'galaxy' : category.includes('nebula') ? 'nebula' : 'planet')}" role="img" aria-label="${safeText(item.name === 'Moon' ? 'NASA lunar reference image' : 'Illustrative celestial motif, not an observation')}">${item.id === 'moon' ? '<img src="/static/moon-reference.png" alt="">' : '<span class="orb"></span>'}</div>`; // Label illustrative artwork honestly.
}
function renderDiscovery() { // Apply category, search, and favorite filters to catalog cards.
 const query = $('catalog-search').value.toLowerCase().trim(); // Read the search query.
 const matches = discoveryCatalog.filter(item => `${item.name} ${item.category} ${item.description}`.toLowerCase().includes(query) && (activeCategory === 'all' || (activeCategory === 'favorites' ? savedTargets.has(item.id) : item.category.toLowerCase().includes(activeCategory === 'galaxy' ? 'galax' : activeCategory)))); // Combine independent filters.
 const card = item => `<article class="celestial-card">${artwork(item)}<div class="card-copy"><div class="card-topline"><span class="eyebrow">${safeText(item.category)}</span><button class="favorite" data-favorite="${safeText(item.id)}" aria-label="Favorite ${safeText(item.name)}" aria-pressed="${savedTargets.has(item.id)}">${savedTargets.has(item.id) ? '♥' : '♡'}</button></div><h3>${safeText(item.name)}</h3><p>${safeText(item.description)}</p><button class="button secondary card-action" data-object="${safeText(item.id)}">Discover object <span aria-hidden="true">↗</span></button></div></article>`; // Generate accessible cards with separate actions.
 $('explore-objects').innerHTML = matches.map(card).join(''); // Update the filtered collection.
 $('home-objects').innerHTML = discoveryCatalog.filter(item => ['moon','jupiter','saturn'].includes(item.id)).map(card).join(''); // Feature familiar beginner targets without inventing visibility.
 $('catalog-count').textContent = `${matches.length} objects`; // Announce the current result count.
 $('catalog-feedback').textContent = matches.length ? '' : 'No objects match yet. Try another category or broaden your search.'; // Explain empty results.
}
function openCelestial(id) { // Show educational details and calculate current visibility on demand.
 const item = discoveryCatalog.find(object => object.id === id); // Resolve the selected local catalog entry.
 if (!item) return; // Ignore a stale selection.
 $('celestial-content').innerHTML = `${artwork(item)}<span class="eyebrow">${safeText(item.category)}</span><h2>${safeText(item.name)}</h2><p>${safeText(item.description)}</p><div class="detail-facts"><div><small>Magnitude</small><b>${safeText(item.magnitude ?? 'Varies')}</b></div><div><small>Distance</small><b>${safeText(item.distance)}</b></div></div><p id="detail-visibility" role="status">Calculating position for your observer settings…</p><button id="observe-object" class="button primary">Observe this target ↗</button><p class="muted">Position is calculated for your site and current time. Equipment movement is simulated.</p>`; // Populate the object detail sheet.
 $('celestial-dialog').showModal(); // Open a keyboard-accessible modal with native focus management.
 $('observe-object').onclick = () => { $('celestial-dialog').close(); showPage('workspace'); $('target').value = id; run(selectTarget)(); }; // Carry the selection into the existing observation workflow.
 post('/astronomy/position', {...site(), target_id:id}).then(position => { if ($('celestial-dialog').open && $('observe-object')?.onclick) $('detail-visibility').textContent = `${position.visible ? 'Above the horizon' : 'Below the horizon'} · altitude ${position.altitude_deg.toFixed(1)}° · azimuth ${position.azimuth_deg.toFixed(1)}°`; }).catch(() => { if ($('detail-visibility')) $('detail-visibility').textContent = 'Position unavailable. Check observer settings and retry from Observe.'; }); // Show real computed status or an actionable error.
}
document.addEventListener('click', event => { // Delegate interactions for dynamically rendered discovery cards.
 const open = event.target.closest('[data-open]'), detail = event.target.closest('[data-object]'), favorite = event.target.closest('[data-favorite]'); // Identify the requested action.
 if (open) { showPage(open.dataset.open); if (open.dataset.open === 'learning') run(loadSkyMap)(); } // Open destinations and draw the sky when requested.
 if (detail) openCelestial(detail.dataset.object); // Open the selected educational detail.
 if (favorite) { const id = favorite.dataset.favorite; savedTargets.has(id) ? savedTargets.delete(id) : savedTargets.add(id); localStorage.setItem('astro-favorites', JSON.stringify([...savedTargets])); renderDiscovery(); $('catalog-feedback').textContent = savedTargets.has(id) ? 'Saved to favorites.' : 'Removed from favorites.'; } // Persist favorites and announce feedback.
});
$('catalog-search').oninput = renderDiscovery; // Filter immediately as the user searches.
document.querySelectorAll('[data-filter]').forEach(button => { button.onclick = () => { activeCategory = button.dataset.filter; document.querySelectorAll('[data-filter]').forEach(filter => { filter.classList.toggle('active', filter === button); filter.setAttribute('aria-pressed', String(filter === button)); }); renderDiscovery(); }; }); // Keep category state accessible.
$('close-detail').onclick = () => $('celestial-dialog').close(); // Restore focus through the native dialog close action.
$('profile-night').onclick = () => $('night').click(); // Reuse the existing persistent red-mode control.
$('reduce-motion').checked = localStorage.getItem('astro-motion') === 'reduced'; // Restore the user's motion preference.
function applyMotion() { document.body.classList.toggle('reduce-motion', $('reduce-motion').checked); localStorage.setItem('astro-motion', $('reduce-motion').checked ? 'reduced' : 'full'); } // Apply and persist reduced motion.
$('reduce-motion').onchange = applyMotion; applyMotion(); // Activate motion preferences on startup.
$('home-date').textContent = new Intl.DateTimeFormat(undefined,{month:'long',day:'numeric',year:'numeric'}).format(new Date()); // Display the current local date.
api('/catalog').then(catalog => { discoveryCatalog = Array.isArray(catalog) ? catalog : catalog.objects ?? []; renderDiscovery(); }).catch(() => { $('catalog-feedback').textContent = 'Catalog unavailable. Reconnect to the local service and reload.'; $('home-objects').textContent = 'Connect to the local service to discover objects.'; }); // Load real catalog content and explain service errors.
showPage('home'); // Start on the discovery dashboard.
