// ///////////////////////////////////////////////////////////////////////////
// ////////////////////////// Lock-E Service Worker //////////////////////////
// ///////////////////////////////////////////////////////////////////////////

// Change the version every time CSS/JS files are modified so users get the new ones
const CACHE_NAME = "lock-e-v2";
const OFFLINE_URL = "/offline.html";

// Files saved when the worker is installed
const PRECACHE = [
  OFFLINE_URL,
  "/CSS/index.css",
  "/CSS/locker.css",
  "/JS/index.js",
  "/JS/locker.js",
  "/icons/icon-192.png",
  "/icons/icon-512.png",
  "/icons/logo.svg",
];

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(CACHE_NAME).then((cache) => cache.addAll(PRECACHE)));
  self.skipWaiting();
});

// Deletes the caches of the old versions
self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k))),
    ),
  );
  self.clients.claim();
});

self.addEventListener("fetch", (e) => {
  const req = e.request;
  if (req.method !== "GET") return;

  const url = new URL(req.url);

  // Pages : always asked to the server (they depend on the logged-in user),
  // the offline page is displayed if there is no connection
  if (req.mode === "navigate") {
    e.respondWith(fetch(req).catch(() => caches.match(OFFLINE_URL)));
    return;
  }

  // Static files (CSS, JS, icons, Leaflet) : answered from the cache and updated in the background
  const isStatic =
    (url.origin === location.origin && /^\/(CSS|JS|icons)\//.test(url.pathname)) ||
    url.hostname === "cdnjs.cloudflare.com";

  if (isStatic) {
    e.respondWith(
      caches.open(CACHE_NAME).then(async (cache) => {
        const cached = await cache.match(req);
        const network = fetch(req)
          .then((res) => {
            if (res.ok) cache.put(req, res.clone());
            return res;
          })
          .catch(() => cached);
        return cached || network;
      }),
    );
  }

  // Everything else (API, reservations, map tiles...) goes directly to the network
});
