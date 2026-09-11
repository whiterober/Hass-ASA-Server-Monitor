/* PWA Service Worker — dino.whiterober.ccwu.cc
 * v976 双缓存改造（2026-09-11）
 * ---------------------------------------------------------------
 * 问题：原实现 activate 只保留「当前版本缓存」，而缓存名随每次部署变化
 *       → 每部署一次就清空图标/地图缓存（5000+ 张）→ 用户端全量重下，「资源加载中」极慢
 * 修法：把「页面壳」与「静态资源」拆成两个缓存
 *   · dino-import-shell-<VER>：index.html 等文档，随版本变（network-first，部署即生效）
 *   · dino-import-assets     ：图标/地图/json 等，**跨版本永久复用**（cache-first，超 600 条淘汰最旧）
 *   并保留历史单缓存（dino-import-v*）不删，让已下载资源继续命中
 * 策略：index.html 走 network-first（保证新版本刷新即生效），其他同源静态 cache-first。
 */
var VER = 'v20260911-977';
var SHELL = 'dino-import-shell-' + VER;
var ASSETS = 'dino-import-assets';
var ASSETS_MAX = 600;
var CORE = ['/', '/manifest.webmanifest', '/icons/icon-192.png', '/icons/icon-512.png'];

// 资源缓存超量淘汰（按插入顺序删最旧；异步不阻塞响应）
function trimAssets() {
  return caches.open(ASSETS).then(function (c) {
    return c.keys().then(function (keys) {
      if (keys.length <= ASSETS_MAX) return;
      var over = keys.length - ASSETS_MAX;
      return Promise.all(keys.slice(0, over).map(function (k) { return c.delete(k); }));
    });
  }).catch(function () {});
}

self.addEventListener('install', function (e) {
  e.waitUntil(
    caches.open(SHELL).then(function (c) {
      return c.addAll(CORE);
    }).then(function () {
      return self.skipWaiting();
    })
  );
});

self.addEventListener('activate', function (e) {
  e.waitUntil(
    caches.keys().then(function (keys) {
      return Promise.all(keys.filter(function (k) {
        if (k === ASSETS) return false;                          // 资源缓存：永久保留
        if (k === SHELL) return false;                           // 当前壳：保留
        if (k.indexOf('dino-import-shell-') === 0) return true;   // 旧壳：清理
        return false;                                            // 历史 dino-import-v*：保留（已下载资源继续命中）
      }).map(function (k) {
        return caches.delete(k);
      }));
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
          caches.open(SHELL).then(function (c) { c.put(req, copy); });
        }
        return res;
      }).catch(function () {
        clearTimeout(to);
        return caches.match(req).then(function (hit) { return hit || caches.match('/'); });
      })
    );
    return;
  }

  // 其他同源静态：cache-first（caches.match 跨全部 cache 查找 → 自动复用历史/资源缓存）
  e.respondWith(
    caches.match(req).then(function (hit) {
      if (hit) return hit;
      return fetch(req).then(function (res) {
        if (res.ok) {
          var copy = res.clone();
          caches.open(ASSETS).then(function (c) {
            return c.put(req, copy).then(trimAssets);
          });
        }
        return res;
      });
    })
  );
});
