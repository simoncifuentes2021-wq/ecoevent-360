const CACHE_NAME = "ecoevent-acopios-v1";
const FORM_PREFIX = "/acopios/";

self.addEventListener("install", event => {
  event.waitUntil(self.skipWaiting());
});

self.addEventListener("activate", event => {
  event.waitUntil((async () => {
    const names = await caches.keys();
    await Promise.all(names.filter(name => name.startsWith("ecoevent-acopios-") && name !== CACHE_NAME).map(name => caches.delete(name)));
    await self.clients.claim();
  })());
});

self.addEventListener("message", event => {
  if (event.data?.type !== "CACHE_FORM_URL" || typeof event.data.url !== "string") return;
  event.waitUntil((async () => {
    const url = new URL(event.data.url);
    if (url.origin !== self.location.origin || !url.pathname.startsWith(FORM_PREFIX)) return;
    const response = await fetch(url.href, { cache: "reload" });
    if (response.ok) {
      const cache = await caches.open(CACHE_NAME);
      const body = await response.clone().text();
      await cache.put(url.href, response.clone());
      const assets = [...new Set(body.match(/\/_next\/static\/[^"'<>\s]+/g) || [])];
      await Promise.all(assets.map(async path => {
        try { const asset = await fetch(new URL(path, self.location.origin)); if (asset.ok) await cache.put(path, asset); } catch { /* A failed optional chunk does not invalidate the cached page. */ }
      }));
      event.ports[0]?.postMessage({ type: "FORM_CACHED" });
    }
  })());
});

self.addEventListener("fetch", event => {
  const request = event.request;
  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return;
  if (url.pathname.startsWith("/_next/static/")) {
    event.respondWith((async () => {
      const cache = await caches.open(CACHE_NAME);
      return (await cache.match(request)) || fetch(request).then(response => {
        if (response.ok) void cache.put(request, response.clone());
        return response;
      });
    })());
    return;
  }
  if (!url.pathname.startsWith(FORM_PREFIX)) return;
  if (request.mode === "navigate") {
    event.respondWith((async () => {
      const cache = await caches.open(CACHE_NAME);
      try {
        const response = await fetch(request);
        if (response.ok) await cache.put(request.url, response.clone());
        return response;
      } catch {
        return (await cache.match(request.url)) || (await cache.match(url.pathname)) || Response.error();
      }
    })());
    return;
  }
});
