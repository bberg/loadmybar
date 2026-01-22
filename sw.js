// Service Worker for LoadMyBar
const CACHE_NAME = 'loadmybar-v1';
const ASSETS = [
  '/',
  '/index.html',
  '/warmup.html',
  '/531.html',
  '/inventory.html',
  '/styles/shared.css',
  '/manifest.json'
];

// Install event - cache assets
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(ASSETS);
    })
  );
  self.skipWaiting();
});

// Activate event - clean old caches
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames
          .filter((name) => name !== CACHE_NAME)
          .map((name) => caches.delete(name))
      );
    })
  );
  self.clients.claim();
});

// Fetch event - serve from cache, fallback to network
self.addEventListener('fetch', (event) => {
  // Only handle same-origin requests
  if (!event.request.url.startsWith(self.location.origin)) {
    return;
  }

  event.respondWith(
    caches.match(event.request).then((response) => {
      // Return cached response or fetch from network
      return response || fetch(event.request).then((fetchResponse) => {
        // Don't cache non-GET requests or analytics
        if (event.request.method !== 'GET' ||
            event.request.url.includes('google')) {
          return fetchResponse;
        }

        // Clone and cache the response
        const responseClone = fetchResponse.clone();
        caches.open(CACHE_NAME).then((cache) => {
          cache.put(event.request, responseClone);
        });

        return fetchResponse;
      });
    }).catch(() => {
      // If both fail, return offline page for navigation requests
      if (event.request.mode === 'navigate') {
        return caches.match('/index.html');
      }
    })
  );
});
