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
var VER = 'v20260911-981';
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
      // v978：逐个 add 并容错 —— 链路抖动时任一资源失败不再导致整个 install 失败（SW 无法激活）
      return Promise.all(CORE.map(function (u) { return c.add(u).catch(function () {}); }));
    }).then(function () {
      // v980：仅当核心文档成功入壳才立即接管；否则不 skipWaiting —— 旧 SW 继续用已缓存文档服务，
      //       避免「新壳为空 + 网络失败」时回退成 offline 白屏
      return caches.open(SHELL).then(function (c) { return c.match('/'); });
    }).then(function (hit) {
      if (hit) return self.skipWaiting();
    })
  );
});

self.addEventListener('activate', function (e) {
  e.waitUntil(
    caches.keys().then(function (keys) {
      // v980：旧壳保留最近 2 个（作为 offline 兑底），更旧的才清理；资源缓存与历史缓存一律保留
      var shells = keys.filter(function (k) {
        return k !== SHELL && k.indexOf('dino-import-shell-') === 0;
      }).sort(); // 名字含日期-序号，字典序即时间序
      var drop = shells.slice(0, Math.max(0, shells.length - 2));
      return Promise.all(drop.map(function (k) { return caches.delete(k); }));
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

  // 首页/主文档：v978 缓存优先（秒开）+ 后台更新（stale-while-revalidate）
  // 旧实现 network-first 的两个问题：① 链路中途断流时文档流悬挂 → 整页停在「加载中」、JS 永不执行；
  // ② res.clone() 写缓存会与浏览器流式解析争抢 tee 缓冲 → 可能背压阻塞文档。
  // 现改为：命中当前壳缓存立即返回；后台完整下载 → 校验 → 回写缓存（无 tee 背压）。
  // 「立即刷新」按钮（lbHardReload）会先清掉本文档缓存再 reload，保证一键拿新版。
  if (url.pathname === '/' || url.pathname === '/index.html') {
    e.respondWith(
      caches.open(SHELL).then(function (c) { return c.match(req); }).catch(function () { return null; }).then(function (hit) {
        var netP = fetch(req).then(function (res) {
          if (!res.ok) return res;
          return res.arrayBuffer().then(function (buf) {
            if (!buf || buf.byteLength < 50000) throw new Error('doc too small'); // 断流防护
            var hdr = new Headers(res.headers);
            hdr.delete('content-encoding'); // buf 已是解压后数据，保留此头会让浏览器二次解压失败
            hdr.delete('content-length');
            var mk = function () { return new Response(buf, { status: res.status, statusText: res.statusText, headers: hdr }); };
            caches.open(SHELL).then(function (c2) { return c2.put(req, mk()); }).catch(function () {});
            return mk();
          });
        });
        if (hit) { netP.catch(function () {}); return hit; }   // 命中缓存：立即返回，后台刷新
        return netP.catch(function () {
          // v980：兑底改为**跨全部缓存**查找（新壳为空时回退到旧壳文档）——只查当前壳会导致 offline 白屏
          return caches.match(req).catch(function () { return null; }).then(function (r) {
            return r || caches.match('/').catch(function () { return null; });
          }).then(function (r) {
            return r || new Response('offline', { status: 503, headers: { 'Content-Type': 'text/plain; charset=utf-8' } });
          }).catch(function () { return new Response('offline', { status: 503 }); });
        });
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
