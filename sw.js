"use strict";
// Bump VERSION on any deploy that changes cached files — activates the new cache
// and drops the old one on next load.
const VERSION = "v8";
const CACHE = `vslive-${VERSION}`;
const PRECACHE = [
  "./",
  "./index.html",
  "./payload.enc.js",
  "./manifest.webmanifest",
  "./icons/icon-192.png",
  "./icons/icon-512.png",
  "./icons/icon-maskable-512.png"
];

self.addEventListener("install", e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(PRECACHE)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", e => {
  e.waitUntil(
    caches.keys()
      .then(keys => Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

// Navigations: network-first with a short timeout so schedule fixes show up when
// online, but conference Wi-Fi flakiness never blocks the app. Everything else:
// cache-first (static assets).
self.addEventListener("fetch", e => {
  if (e.request.method !== "GET") return;
  // Extensions inject chrome-extension:// requests on desktop; Cache.put rejects
  // non-http(s) schemes, so only handle same-origin requests.
  if (!e.request.url.startsWith(self.location.origin)) return;
  if (e.request.mode === "navigate") {
    e.respondWith(
      Promise.race([
        fetch(e.request).then(r => {
          const copy = r.clone();
          caches.open(CACHE).then(c => c.put("./index.html", copy));
          return r;
        }),
        new Promise((_, rej) => setTimeout(rej, 2500, new Error("timeout")))
      ]).catch(() => caches.match("./index.html"))
    );
    return;
  }
  e.respondWith(
    caches.match(e.request).then(hit => hit || fetch(e.request).then(r => {
      const copy = r.clone();
      caches.open(CACHE).then(c => c.put(e.request, copy));
      return r;
    }))
  );
});
