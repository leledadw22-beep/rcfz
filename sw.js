// RC Flight Zone service worker — makes the app installable + work offline.
// Same-origin requests: network-first (fresh data when online, cached fallback offline).
// Cross-origin (YouTube/TikTok thumbnails): left to the browser, never cached here.
const CACHE = 'rcfz-v1';
const SHELL = ['.', 'index.html', 'manifest.webmanifest', 'icon-192.png', 'icon-512.png', 'data/videos.js'];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(SHELL)).catch(() => {}).then(() => self.skipWaiting()));
});

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys().then(keys => Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', e => {
  const url = new URL(e.request.url);
  if (e.request.method !== 'GET' || url.origin !== location.origin) return; // pass through cross-origin
  e.respondWith(
    fetch(e.request)
      .then(r => { const copy = r.clone(); caches.open(CACHE).then(c => c.put(e.request, copy)); return r; })
      .catch(() => caches.match(e.request).then(m => m || caches.match('index.html')))
  );
});
