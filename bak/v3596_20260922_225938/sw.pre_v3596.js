/* PWA Service Worker — dino.whiterober.ccwu.cc
 * v976 双缓存改造（2026-09-11）
 * ---------------------------------------------------------------
 * 问题：原实现 activate 只保留「当前版本缓存」，而缓存名随每次部署变化
 *       → 每部署一次就清空图标/地图缓存（5000+ 张）→ 用户端全量重下，「资源加载中」极慢
 * 修法：把「页面壳」与「静态资源」拆成两个缓存
 *   · dino-import-shell-<VER>：index.html 等文档，随版本变（network-first，部署即生效）
 *   · dino-import-assets     ：图标/地图/json 等，**跨版本永久复用**（cache-first，超 1200 条淘汰最旧）
 *   并保留历史单缓存（dino-import-v*）不删，让已下载资源继续命中
 * 策略：index.html 走 network-first（保证新版本刷新即生效），其他同源静态 cache-first。
 */
var VER = 'v20260922-3595'; // v1145：随前端版本递增，强制移动端（PWA/Safari）拿到新壳并丢弃旧 shell 缓存
//   背景：手机/iPad 曾长期停留在旧版前端（跑旧的逐台加载逻辑 ⇒ 卡在「存档已落盘」达 10 分钟）；
//   index.html 虽为 network-first，但弱网/离线时仍回退旧缓存 ⇒ 每次部署同步递增本版本号可确保换壳生效。
var SHELL = 'dino-import-shell-' + VER;
var ASSETS = 'dino-import-assets';
var ASSETS_MAX = 1200; // v20260912-1029：600→1200（实测预取需 717 张，600 上限导致缓存震荡：每写一张即淘汰一张）
var CORE = ['/', '/manifest.webmanifest', '/icons/icon-192.png', '/icons/icon-512.png'];
// v984：网络与缓存都不可用时的「自动重试页」（避免用户看到 'offline' 白屏字样）
var RETRY_HTML = '<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>正在重试…</title></head><body style="background:#0f0f13;color:#ddd;font-family:system-ui,sans-serif;display:flex;align-items:center;justify-content:center;height:100vh;margin:0"><div style="text-align:center"><div style="font-size:15px;margin-bottom:10px">网络暂时不可用，正在自动重试…</div><div id="t" style="font-size:12px;color:#888">3 秒后重试</div></div><script>var n=3;setInterval(function(){n--;var e=document.getElementById("t");if(e)e.textContent=n>0?(n+" 秒后重试"):"正在重试…";if(n<=0)location.reload();},1000);</script></body></html>';

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
      // v982：每个 add 加 10s 超时 —— 否则网络挂起会让 install 永不完成 → 新 SW 永不接管 → 修复到不了用户端
      return Promise.all(CORE.map(function (u) {
        var ac = new AbortController();
        var to = setTimeout(function () { try { ac.abort(); } catch (e2) {} }, 10000);
        return c.add(new Request(u, { signal: ac.signal })).catch(function () {}).then(function () { clearTimeout(to); });
      }));
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
    caches.open(SHELL).then(function (c) { return c.match('/'); }).then(function (hasDoc) {
      // v984：仅当「当前壳已有 '/' 文档」（预缓存成功）时才清理旧壳；
      //       否则旧壳是唯一兑底，一律不动（清掉后网络一失败就是白屏）
      if (!hasDoc) return null;
      return caches.keys().then(function (keys) {
        var shells = keys.filter(function (k) {
          return k !== SHELL && k.indexOf('dino-import-shell-') === 0;
        }).sort(); // 名字含日期-序号，字典序即时间序
        var drop = shells.slice(0, Math.max(0, shells.length - 2));
        return Promise.all(drop.map(function (k) { return caches.delete(k); }));
      });
    }).then(function () {
      return self.clients.claim();
    })
  );
});

self.addEventListener('fetch', function (e) {
  var req = e.request;
  if (req.method !== 'GET') return;
  // v1175（用户定策 B，2026-09-15）：**导航请求不再由 SW 接管** —— 浏览器直连 Cloudflare Assets。
  //   原实现要 res.arrayBuffer() 整份读完才 respondWith，且 delete('content-encoding')
  //   ⇒ 首字节 = 最后一字节，且 1.17MB 明文（实测 TTFB 12,735ms / HTML 1,170,501 B 未压缩）。
  //   代价（已确认接受）：断网或服务器不可用时页面打不开（旧壳回退链失效）；资源/分片缓存策略不变。
  if (req.mode === 'navigate') return;
  var url = new URL(req.url);
  if (url.origin !== location.origin) return;

  // 首页/主文档：v978 缓存优先（秒开）+ 后台更新（stale-while-revalidate）
  // 旧实现 network-first 的两个问题：① 链路中途断流时文档流悬挂 → 整页停在「加载中」、JS 永不执行；
  // ② res.clone() 写缓存会与浏览器流式解析争抢 tee 缓冲 → 可能背压阻塞文档。
  // 现改为：命中当前壳缓存立即返回；后台完整下载 → 校验 → 回写缓存（无 tee 背压）。
  // 「立即刷新」按钮（lbHardReload）会先清掉本文档缓存再 reload，保证一键拿新版。
  // 首页/主文档：v985 回到 network-first（总是先取网络 → 部署即生效），失败再回退缓存。
  // 保留的加固：12s 超时（防链路挂起导致整页卡死）、完整读取后写缓存（无 tee 背压）、
  //              put 全程 catch、跨缓存兑底（含旧壳）、最终兑底为「自动重试页」而非 offline 文本。
  if (url.pathname === '/' || url.pathname === '/index.html') {
    var ac = new AbortController();
    // v987：12s → 30s（实测链路忙时 HTML 下载可超 12s，超时回退旧缓存会把整页退回旧代码）
    var to = setTimeout(function () { try { ac.abort(); } catch (e2) {} }, 30000);
    e.respondWith(
      fetch(req, { signal: ac.signal }).then(function (res) {
        clearTimeout(to);
        if (!res.ok) return res;
        return res.arrayBuffer().then(function (buf) {
          if (!buf || buf.byteLength < 50000) throw new Error('doc too small'); // 断流防护
          var hdr = new Headers(res.headers);
          hdr.delete('content-encoding'); // buf 已是解压后数据，保留此头会让浏览器二次解压失败
          hdr.delete('content-length');
          var mk = function () { return new Response(buf, { status: res.status, statusText: res.statusText, headers: hdr }); };
          caches.open(SHELL).then(function (c2) { return c2.put(new Request('/'), mk()).catch(function () {}); }).catch(function () {});
          return mk();
        });
      }).catch(function () {
        clearTimeout(to);
        // v987：兑底文档必须取「最新」副本 —— caches.match() 按缓存创建顺序命中最旧的那个
        //       （实测因此把页面退回到 v976 旧代码）；改为：当前壳 → 其余壳按名字倒序 → 最后才全缓存
        return caches.keys().then(function (keys) {
          var shells = keys.filter(function (k) { return k.indexOf('dino-import-shell-') === 0; }).sort().reverse();
          var order = [SHELL].concat(shells.filter(function (k) { return k !== SHELL; }));
          return order.reduce(function (p, k) {
            return p.then(function (found) {
              if (found) return found;
              return caches.open(k).then(function (c) { return c.match('/'); }).catch(function () { return null; });
            });
          }, Promise.resolve(null));
        }).then(function (doc) {
          if (doc) return doc;
          return caches.match('/').catch(function () { return null; });
        }).then(function (doc2) {
          return doc2 || new Response(RETRY_HTML, { status: 503, headers: { 'Content-Type': 'text/html; charset=utf-8' } });
        }).catch(function () {
          return new Response(RETRY_HTML, { status: 503, headers: { 'Content-Type': 'text/html; charset=utf-8' } });
        });
      })
    );
    return;
  }

  // 其他同源静态：cache-first（caches.match 跨全部 cache 查找 → 自动复用历史/资源缓存）
  e.respondWith(
    caches.match(req).then(function (hit) {
      if (hit) return hit;
      // v982：put 全程 catch —— 流被链路抖动中断时 put 会抛 NetworkError，不能成为未处理拒绝
      // v985：10s → 20s（实测链路延迟上限 13.4s，10s 会把慢资源误判为失败）
      var ac = new AbortController();
      var to = setTimeout(function () { try { ac.abort(); } catch (e2) {} }, 20000);
      return fetch(req, { signal: ac.signal }).then(function (res) {
        clearTimeout(to);
        if (res.ok) {
          var copy = res.clone();
          caches.open(ASSETS).then(function (c) {
            return c.put(req, copy).then(trimAssets).catch(function () {});
          }).catch(function () {});
        }
        return res;
      }).catch(function () {
        clearTimeout(to);
        return new Response('', { status: 504 });
      });
    })
  );
});
