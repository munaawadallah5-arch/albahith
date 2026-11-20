// عامل الخدمة لتطبيق «الباحث»: يجعل الموقع قابلًا للتثبيت ويعمل دون إنترنت.
// ملفات الموقع تُطلب من الشبكة أولًا (لتصل الإعلانات الجديدة فورًا)، وعند انقطاع الإنترنت تُعرض آخر نسخة محفوظة.
const CACHE = "albahith-v6";
const CORE = ["./", "index.html", "app.js", "events.js", "logo.svg", "manifest.webmanifest",
  "icons/icon-192.png", "icons/icon-512.png", "icons/maskable-512.png", "icons/apple-touch-icon.png"];

self.addEventListener("install", e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(CORE)).then(() => self.skipWaiting()));
});
self.addEventListener("activate", e => {
  e.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k))))
    .then(() => self.clients.claim()));
});
self.addEventListener("fetch", e => {
  const req = e.request;
  if (req.method !== "GET") return;               // طلبات البحث الذكي (POST) تمر كما هي
  const url = new URL(req.url);
  if (url.origin === location.origin) {
    // cache: "no-cache" يسأل الخادم دائمًا عن أحدث نسخة، بدل نسخة المتصفح المحفوظة (GitHub يجعلها تبقى 10 دقائق)
    e.respondWith(fetch(req, {cache: "no-cache"}).then(res => {
      if (res.ok) { const copy = res.clone(); caches.open(CACHE).then(c => c.put(req, copy)); }
      return res;
    }).catch(() => caches.match(req, {ignoreSearch: true}).then(r => r || caches.match("index.html"))));
  } else if (/fonts\.(googleapis|gstatic)\.com$/.test(url.hostname)) {
    e.respondWith(caches.match(req).then(hit => hit || fetch(req).then(res => {
      const copy = res.clone(); caches.open(CACHE).then(c => c.put(req, copy)); return res;
    })));
  }
});
