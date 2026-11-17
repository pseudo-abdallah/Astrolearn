'use strict';

const byId = id => document.getElementById(id);
const radians = degrees => degrees * Math.PI / 180;
const degrees = angle => angle * 180 / Math.PI;
const wrap = angle => ((angle % 360) + 360) % 360;
const imageTypes = new Set(['image/png', 'image/jpeg', 'image/webp']);
const images = [];
let targets = [];
let filter = 'visible';
let selected = null;
let favorites = new Set();

try {
  const saved = JSON.parse(localStorage.getItem('astrolearn-user-favorites') || '[]');
  if (Array.isArray(saved)) favorites = new Set(saved);
  document.body.classList.toggle('night', localStorage.getItem('astrolearn-user-night') === 'true');
} catch { /* Local storage may be disabled. */ }

function remember(key, value) {
  try { localStorage.setItem(key, JSON.stringify(value)); } catch { /* Keep in-session settings. */ }
}

// Approximate horizontal coordinates using local sidereal time and fixed catalog RA/Dec.
function skyPosition(target, latitude, longitude, instant) {
  const daysSinceJ2000 = instant.getTime() / 86400000 + 2440587.5 - 2451545;
  const sidereal = 280.46061837 + 360.98564736629 * daysSinceJ2000 + longitude;
  const hour = radians(wrap(sidereal - target.ra_deg));
  const dec = radians(target.dec_deg);
  const lat = radians(latitude);
  const east = -Math.cos(dec) * Math.sin(hour);
  const north = Math.sin(dec) * Math.cos(lat) - Math.cos(dec) * Math.cos(hour) * Math.sin(lat);
  const up = Math.sin(dec) * Math.sin(lat) + Math.cos(dec) * Math.cos(hour) * Math.cos(lat);
  return {
    ...target,
    altitude: degrees(Math.atan2(up, Math.hypot(east, north))),
    azimuth: wrap(degrees(Math.atan2(east, north))),
  };
}

function updateSky() {
  const latitude = Number(byId('latitude').value);
  const longitude = Number(byId('longitude').value);
  const instant = byId('when').value ? new Date(byId('when').value) : new Date();
  if (!Number.isFinite(instant.getTime())) return;
  targets = catalog.map(target => skyPosition(target, latitude, longitude, instant))
    .sort((a, b) => b.altitude - a.altitude);
  byId('site-label').textContent = latitude === 29.3759 && longitude === 47.9774
    ? 'Kuwait City' : [latitude, longitude].map(value => value.toFixed(2) + '°').join(', ');
  byId('sky-time').textContent = new Intl.DateTimeFormat(undefined, {
    month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit', timeZoneName: 'short',
  }).format(instant);
  renderTargets();
  renderDetail();
  drawAtlas();
}

function describePosition(target) {
  const visibility = target.altitude >= 0 ? 'Above horizon' : 'Below horizon';
  return visibility + ' · Alt ' + target.altitude.toFixed(1) + '° · Az ' + target.azimuth.toFixed(1) + '°';
}

function renderTargets() {
  const query = byId('search').value.trim().toLowerCase();
  const category = byId('category').value.toLowerCase();
  const matches = targets.filter(target =>
    (filter !== 'visible' || target.altitude >= 0) &&
    (filter !== 'saved' || favorites.has(target.id)) &&
    (!category || target.category.toLowerCase() === category) &&
    (target.name + ' ' + target.id).toLowerCase().includes(query));
  byId('results-count').textContent = matches.length
    ? matches.length + (matches.length === 1 ? ' target' : ' targets') + ' · highest first'
    : 'No matching targets.';
  const list = byId('target-list');
  list.replaceChildren();
  for (const target of matches) {
    const row = document.createElement('li');
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'target-row';
    button.setAttribute('aria-pressed', String(target.id === selected));
    const label = document.createElement('span');
    const title = document.createElement('strong');
    const meta = document.createElement('small');
    const altitude = document.createElement('span');
    title.textContent = target.name + (favorites.has(target.id) ? ' ★' : '');
    meta.textContent = target.category;
    altitude.className = target.altitude >= 0 ? 'above' : 'below';
    altitude.textContent = target.altitude.toFixed(0) + '°';
    altitude.setAttribute('aria-label', describePosition(target));
    label.append(title, meta);
    button.append(label, altitude);
    button.onclick = () => {
      selected = target.id;
      renderTargets();
      renderDetail();
      drawAtlas();
      byId('detail-title').focus();
    };
    row.append(button);
    list.append(row);
  }
}

function renderDetail() {
  const target = targets.find(item => item.id === selected);
  byId('target-detail').hidden = !target;
  if (!target) return;
  byId('detail-title').textContent = target.name;
  byId('detail-description').textContent = target.description;
  byId('detail-position').textContent = describePosition(target);
  byId('favorite').setAttribute('aria-pressed', String(favorites.has(target.id)));
  byId('favorite').textContent = favorites.has(target.id) ? '★ Favorited' : '☆ Favorite';
}

function drawAtlas() {
  const context = byId('sky').getContext('2d');
  context.clearRect(0, 0, 500, 500);
  const night = document.body.classList.contains('night');
  context.strokeStyle = night ? '#713d49' : '#344661';
  context.fillStyle = night ? '#edb4bc' : '#adbed6';
  context.font = '15px system-ui';
  context.textAlign = 'center';
  for (const radius of [68, 136, 204]) {
    context.beginPath();
    context.arc(250, 250, radius, 0, Math.PI * 2);
    context.stroke();
  }
  context.beginPath();
  context.moveTo(46, 250);
  context.lineTo(454, 250);
  context.moveTo(250, 46);
  context.lineTo(250, 454);
  context.stroke();
  for (const [letter, x, y] of [['N', 250, 34], ['S', 250, 478], ['E', 26, 255], ['W', 474, 255]]) {
    context.fillText(letter, x, y);
  }
  for (const target of targets.filter(item => item.altitude >= 0)) {
    const radius = (90 - target.altitude) * 204 / 90;
    const x = 250 - radius * Math.sin(radians(target.azimuth));
    const y = 250 - radius * Math.cos(radians(target.azimuth));
    const active = target.id === selected;
    context.fillStyle = night ? '#f5a0ad' : active ? '#b7e8ff' : '#dceaff';
    context.beginPath();
    context.arc(x, y, active ? 6 : 3, 0, Math.PI * 2);
    context.fill();
    if (active) context.fillText(target.name, Math.max(72, Math.min(428, x)), y - 12);
  }
}

function showView(name) {
  for (const section of document.querySelectorAll('main > section')) section.hidden = section.id !== name;
  for (const button of document.querySelectorAll('[data-view]')) {
    if (button.dataset.view === name) button.setAttribute('aria-current', 'page');
    else button.removeAttribute('aria-current');
  }
  byId(name + '-heading').focus();
}

function showImage(image) {
  byId('preview').src = image.url;
  byId('preview').alt = 'Uploaded sky image: ' + image.name;
  byId('image-caption').textContent = image.name;
  showView('observe');
}

function addImage(image) {
  images.unshift(image);
  const button = document.createElement('button');
  const thumbnail = document.createElement('img');
  const name = document.createElement('span');
  thumbnail.src = image.url;
  thumbnail.alt = '';
  name.textContent = image.name;
  button.type = 'button';
  button.append(thumbnail, name);
  button.onclick = () => showImage(image);
  byId('gallery').prepend(button);
  byId('image-status').textContent = images.length + (images.length === 1 ? ' image' : ' images') + ' in this session.';
  showImage(image);
}

for (const button of document.querySelectorAll('[data-view]')) button.onclick = () => showView(button.dataset.view);
for (const button of document.querySelectorAll('[data-filter]')) {
  button.onclick = () => {
    filter = button.dataset.filter;
    for (const option of document.querySelectorAll('[data-filter]')) option.setAttribute('aria-pressed', String(option === button));
    renderTargets();
  };
}
byId('search').oninput = renderTargets;
byId('category').onchange = renderTargets;
byId('settings-toggle').onclick = () => {
  const form = byId('observer');
  form.hidden = !form.hidden;
  byId('settings-toggle').setAttribute('aria-expanded', String(!form.hidden));
  if (!form.hidden) byId('latitude').focus();
};
byId('observer').onsubmit = event => { event.preventDefault(); updateSky(); };
byId('favorite').onclick = () => {
  if (!selected) return;
  if (favorites.has(selected)) favorites.delete(selected);
  else favorites.add(selected);
  remember('astrolearn-user-favorites', [...favorites]);
  renderTargets();
  renderDetail();
};
byId('set-target').onclick = () => {
  const reference = targets.find(item => item.id === selected);
  byId('observe-target').textContent = reference.name;
  byId('observe-facts').textContent = reference.description;
  showView('observe');
};
byId('back-explore').onclick = () => showView('explore');
byId('night').setAttribute('aria-pressed', String(document.body.classList.contains('night')));
byId('night').onclick = () => {
  const enabled = document.body.classList.toggle('night');
  byId('night').setAttribute('aria-pressed', String(enabled));
  remember('astrolearn-user-night', enabled);
  drawAtlas();
};
for (const button of document.querySelectorAll('.upload')) button.onclick = () => byId('image-file').click();
byId('image-file').onchange = () => {
  const file = byId('image-file').files[0];
  byId('image-file').value = '';
  if (!file) return;
  const status = byId('upload-status');
  if (!imageTypes.has(file.type) || file.size > 20 * 1024 * 1024) {
    status.textContent = 'Choose a PNG, JPEG or WebP image up to 20 MB.';
    return;
  }
  const url = URL.createObjectURL(file);
  const check = new Image();
  check.onload = () => { status.textContent = ''; addImage({name: file.name, url}); };
  check.onerror = () => { URL.revokeObjectURL(url); status.textContent = 'This file could not be displayed as an image.'; };
  check.src = url;
};
byId('image-status').textContent = 'No images added yet.';
updateSky();

