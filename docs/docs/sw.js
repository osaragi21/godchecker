
// Simple cache-first for app shell; network for JSON
const CACHE_NAME = 'godchecker-v1';
const ASSETS = [
  './',
  './index.html',
  './manifest.webmanifest',
  './icons/icon-192.png',
  './icons/icon-512.png'
];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE_NAME).then(c => c.addAll(ASSETS)));
});

self.addEventListener('activate', e => {
  e.waitUntil(self.clients.claim());
});

self.addEventListener('fetch', e => {
  const url = new URL(e.request.url);
  // Do not cache JSON dynamically (let the app fetch fresh)
  if (url.pathname.endsWith('.json')) return;
  e.respondWith(
    caches.match(e.request).then(resp => resp || fetch(e.request))
  );
});
