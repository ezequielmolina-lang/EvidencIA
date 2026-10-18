// Guarda la app para que abra sin conexión; primero la red, si no hay, la copia.
const CACHE = "evidencia-papers-f31d136632";
self.addEventListener("install", (e) => { e.waitUntil(caches.open(CACHE).then((c) => c.addAll(["./", "manifest.webmanifest"]))); self.skipWaiting(); });
self.addEventListener("activate", (e) => { e.waitUntil(caches.keys().then((ks) => Promise.all(ks.filter((k) => k.startsWith("evidencia-papers-") && k !== CACHE).map((k) => caches.delete(k))))); self.clients.claim(); });
self.addEventListener("fetch", (e) => {
  if (e.request.method !== "GET") return;
  e.respondWith(fetch(e.request).then((r) => { if (r.ok && new URL(e.request.url).origin === location.origin) { const copia = r.clone(); caches.open(CACHE).then((c) => c.put(e.request, copia)); } return r; }).catch(() => caches.match(e.request).then((r) => r || caches.match("./"))));
});
