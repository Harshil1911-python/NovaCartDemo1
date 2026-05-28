/* Nova Cart - PWA Service Worker */
const CACHE = 'novacart-v1';
const STATIC = ['/static/css/main.css', '/static/js/main.js', '/static/images/no-image.png'];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(STATIC).catch(() => {})));
  self.skipWaiting();
});

self.addEventListener('activate', e => {
  e.waitUntil(caches.keys().then(keys =>
    Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))
  ));
  self.clients.claim();
});

self.addEventListener('fetch', e => {
  if (e.request.method !== 'GET') return;
  if (e.request.url.includes('/x-admin-9f3k2')) return;
  e.respondWith(
    fetch(e.request).catch(() => caches.match(e.request))
  );
});
