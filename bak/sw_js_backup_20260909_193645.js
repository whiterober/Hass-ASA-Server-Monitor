/* PWA Service Worker — dino.whiterober.ccwu.cc
 * 策略：index.html 走 network-first（保证新版本部署后刷新即生效），
 * 其他同源静态资源（图标/manifest）cache-first。
 * 2026-08-29 首次上线
 */
var CACHE = 'dino-import-v20260909-928';
var CORE = ['/', '/manifest.webmanifest', '/icons/icon-192.png', '/icons/icon-512.png'];

self.addEventListener('install', function (e) {
  e.waitUntil(
    caches.open(CACHE).then(function (c) {
      return c.addAll(CORE);
    }).then(function () {
      return self.skipWaiting();
    })
  );
});

self.addEventListener('activate', function (e) {
  e.waitUntil(
    caches.keys().then(function (keys) {
      return Promise.all(keys.filter(function (k) { return k !== CACHE; }).map(function (k) { return caches.delete(k); }));
    }).then(function () {
      return self.clients.claim();
    })
  );
});

self.addEventListener('fetch', function (e) {
  var req = e.request;
  if (req.method !== 'GET') return;
  var url = new URL(req.url);
  if (url.origin !== location.origin) return;

  // 首页/主文档：network-first + 6s 超时回落缓存（2026-09-08：网络抖动/实例异常时防无限 Loading）
  if (url.pathname === '/' || url.pathname === '/index.html') {
    var ac = new AbortController();
    var to = setTimeout(function () { try { ac.abort(); } catch (e2) {} }, 6000);
    e.respondWith(
      fetch(req, { signal: ac.signal }).then(function (res) {
        clearTimeout(to);
        if (res.ok) {
          var copy = res.clone();
          caches.open(CACHE).then(function (c) { c.put(req, copy); });
        }
        return res;
      }).catch(function () {
        clearTimeout(to);
        return caches.match(req).then(function (hit) { return hit || caches.match('/'); });
      })
    );
    return;
  }

  // 其他同源静态：cache-first（sw.js 自身不缓存，浏览器自动更新检查）
  e.respondWith(
    caches.match(req).then(function (hit) {
      if (hit) return hit;
      return fetch(req).then(function (res) {
        if (res.ok) {
          var copy = res.clone();
          caches.open(CACHE).then(function (c) { c.put(req, copy); });
        }
        return res;
      });
    })
  );
});
