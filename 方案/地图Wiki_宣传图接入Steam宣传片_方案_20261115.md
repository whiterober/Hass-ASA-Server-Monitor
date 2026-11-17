# 地图 Wiki「地图宣传图」接入 Steam 宣传片 —— 方案（2026-11-15）

> 目标：地图 Wiki「概览」页现有的 **地图宣传图**（静态图）增加**播放地图宣传片**能力，视频源取自 Steam 商店页（官方宣传片）。
> 范围：`app_ui.js` 的 `lbMapWikiPromoHtml()` + 数据文件 + 一次性的 appid 核对。**不改后端接口**。

---

## 1. 现状

| 项 | 现状 |
|---|---|
| 渲染函数 | `app_ui.js` → `lbMapWikiPromoHtml()`（`lbMapWikiBodyHtml(0)` 里置顶调用） |
| 图片来源 | `https://dino.whiterober.ccwu.cc/maps/<id小写>_promo.webp`（来自 `img.whiterober.ccwu.cc/ASA/misc/<Id>_compressed.jpg` 转 WebP q70） |
| 结构 | `.tc-sec > .tc-h('地图宣传图') > 圆角容器 > img[loading=lazy, max-width:560]` |
| 缺图处理 | `onerror` 把整个 `.tc-sec` 移除（不占位、不留空标题） |
| 例外 | `Bob`（俱乐部）无地图，直接返回 `''` |

---

## 2. 数据来源（Steam）

### 2.1 接口

```
GET https://store.steampowered.com/api/appdetails?appids=<appid>&l=schinese
```

返回数组，取 `data[appid].data.movies[]`，每条：

```json
{ "id": 257000,
  "name": "Scorched Earth Trailer",
  "thumbnail": "https://shared.akamai.steamstatic.com/store_item_assets/steam/apps/.../movie.293x165.jpg",
  "webm": { "480": "...webm", "max": "...webm" },
  "mp4":  { "480": "...mp4",  "max": "...mp4" } }
```

- 视频真实地址在 **Steam CDN**（`video.akamai.steamstatic.com` / `shared.akamai.steamstatic.com`），长期有效
- **不要在前端实时请求这个 API**：有区域限流、CORS 不可控，且每次进 wiki 都打 Steam
- 正确做法：**构建期/一次性脚本抓取**，落盘成静态 JSON 随包发布

### 2.2 地图 ↔ appid 映射（**需逐个核对，本方案不预设**）

| 地图 | 服 abbr | 说明 |
|---|---|---|
| 孤岛 The Island | Isl | 基础游戏本体 |
| 焦土 Scorched Earth | Sco | ASA 独立 DLC（有独立商店页与宣传片） |
| 中心岛 The Center | Cen | 免费地图（视频通常在基础游戏页） |
| 畸变 Aberration | Abe | ASA DLC |
| 灭绝 Extinction | Ext | ASA DLC |
| 繁星 Astraeos | Ast | 社区地图（商店页可能有独立宣传片） |
| 仙境 Ragnarok | Rag | 免费地图 |
| 瓦尔盖罗 Valguero | Val | 免费地图 |
| 失落地 Lost Island? | Los | 按项目现有中文名核对实际地图 |
| 创世 Genesis | Gen | ASA DLC（Part 1/2） |
| 俱乐部 Bob | Bob | 无地图，跳过 |

> ⚠️ **实施第一步必须是核对 appid**：用 `appdetails` 逐个试，确认 `movies[]` 非空且视频确实是「这张地图」的宣传片。基础游戏页里混着多张地图的片子，需要按 `movies[].name` 关键字（如 `Aberration`、`Extinction`）筛出对应那条，而不是无脑取 `movies[0]`。

---

## 3. 数据落盘

新增 `map_videos.json`（放项目根目录，随打包进 CF 根或 `maps/`）：

```json
{
  "Isl": { "appid": 2399830, "name": "ARK: Survival Ascended",
           "url": "https://video.akamai.steamstatic.com/store_trailers/.../movie_max.mp4",
           "webm": "https://.../movie_max.webm",
           "poster": "https://shared.akamai.steamstatic.com/.../movie.600x338.jpg",
           "title": "The Island 官方宣传片" },
  "Sco": { ... }
}
```

- 生成脚本：`tmp/_map_videos_gen.py`（一次性；带 UA、失败重试 2 次、逐条打印命中情况）
- 打包：在 `tmp/_sync_repack2.py` 的静态文件复制段追加 `map_videos.json`（与 `cave_entrances.json` 等同级）
- 体积：只有几条 URL 字符串，< 4 KB

---

## 4. 前端改造（`app_ui.js` → `lbMapWikiPromoHtml()`）

### 4.1 结构

```html
<div class="tc-sec" id="lbMwPromo_<id>">
  <div class="tc-h" data-keep="1">地图宣传图</div>
  <div class="lb-mw-media" data-mode="img">
    <img  class="lb-mw-poster" src="..._promo.webp" loading="lazy">
    <video class="lb-mw-video" hidden controls playsinline preload="none"
           poster="<Steam thumbnail>">
      <source src="<mp4 max>" type="video/mp4">
      <source src="<webm max>" type="video/webm">
    </video>
    <button class="lb-mw-play" onclick="lbMwVideoToggle(this)">
      <i class="mdi mdi-play-circle"></i> 播放地图宣传片
    </button>
  </div>
</div>
```

### 4.2 交互

| 动作 | 行为 |
|---|---|
| 默认 | 只显示原宣传图 + 底部「▶ 播放地图宣传片」按钮（按钮只在 `map_videos.json` 有该图时渲染） |
| 点播放 | 图 `hidden`、video `hidden=false`、`video.play()`；按钮文案变「收起」 |
| 点收起 | 暂停 + 复位 `currentTime=0`、video 继续 `hidden`，图回来 |
| 切地图 | 现有逻辑重建整个 body（`lbMapWikiBodyHtml` 每次重渲染）⇒ video 自然销毁，不需要额外状态清理 |

### 4.3 关键实现约束（项目既有教训）

1. **样式只能写一处**：新增 `.lb-mw-*` 样式统一放 `app.css`，不要在内联 style 里各写一份
2. **不要用 `autoplay`**：移动端会被拦；必须用户点击触发 `play()`
3. **`preload="none"`**：视频在视口外/未点击前不占流量（Steam CDN 的 mp4 有 10~40 MB）
4. **`playsinline`**：iOS 必须，否则点播放会全屏劫持
5. **无视频降级**：`map_videos.json` 里没该图 / `url` 为空 ⇒ 连按钮都不渲染，`.tc-sec` 与现状完全一致
6. **视频 404 兜底**：`<video onerror>` ⇒ 切回图片并 toast「宣传片暂不可用（不影响查看）」
7. **`lbResURL` 不要套在视频上**：视频是外链，不参与资源包/`?v=` 版本化，直接写原始 URL
8. **不要用 ✓/✗ 符号**（项目硬规则），需要图标一律 mdi
9. **`Bob` 保持返回 `''`**

### 4.4 代码骨架（示意）

```js
function lbMapWikiPromoHtml(){
  try{
    var id = String(LB_MW.cur || '');
    if (!id || id === 'Bob') return '';
    var uid = 'lbMwPromo_' + id.toLowerCase();
    var src = LB_MAP_BASE + id.toLowerCase() + '_promo' + LB_MAP_EXT;
    var v = (LB_MAP_VIDEOS || {})[id] || null;         // 由 map_videos.json 载入
    var btn = (v && v.url)
      ? '<button class="lb-mw-play lb-tipb" onclick="lbMwVideoToggle(this)">'
        + '<i class="mdi mdi-play-circle"></i> 播放地图宣传片</button>'
      : '';
    var vid = (v && v.url)
      ? '<video class="lb-mw-video" hidden controls playsinline preload="none"'
        + ' poster="' + (v.poster || '') + '"'
        + ' onerror="lbMwVideoFail(this)">'
        + '<source src="' + v.url + '" type="video/mp4">'
        + (v.webm ? '<source src="' + v.webm + '" type="video/webm">' : '')
        + '</video>'
      : '';
    return '<div class="tc-sec" id="' + uid + '">'
      + '<div class="tc-h" data-keep="1">地图宣传图</div>'
      + '<div class="lb-mw-media">' + vid
      + '<img class="lb-mw-poster" src="' + lbResURL(src) + '" data-lbasset="' + src + '"'
      + ' alt="地图宣传图" loading="lazy"'
      + ' onerror="var _p=document.getElementById(\'' + uid + '\');if(_p&&_p.parentNode)_p.parentNode.removeChild(_p)">'
      + btn + '</div></div>';
  }catch(e){ return ''; }
}
```

---

## 5. 风险与注意

| 风险 | 说明 / 应对 |
|---|---|
| **Steam CDN 防盗链** | 目前 mp4/webm 直链允许跨站引用；若将来加了 Referer 白名单 ⇒ 视频失效。应对：`onerror` 自动回退图片，不报错；必要时改为下载转存自家 `img.whiterober.ccwu.cc`（体积 10~40 MB/条，需评估存储） |
| **流量** | 视频走 Steam CDN，不消耗自家流量；但移动端流量是用户的，所以 `preload="none"` 必做 |
| **地区限制** | 国内访问 `akamai.steamstatic.com` 时好时坏；失败即回退图片 |
| **appid 核对成本** | 每张地图都要确认「这条片子确实是这张图」；免费地图（Center / Ragnarok / Valguero / Lost Island）大概率只有基础游戏页的合集片，可能需要**只给部分地图**提供视频 |
| **版本失效** | Steam 换宣传片后旧 URL 仍有效（CDN 保留），不会破图；但内容可能过时，需人工复核 |
| **与 AI 入口的顺序** | 现有顺序：置顶文案 → 宣传图 → AI 入口；新增按钮属于宣传图块内部，不改插入顺序 |

---

## 6. 分阶段实施

| 阶段 | 内容 | 产出 | 谁做 |
|---|---|---|---|
| S1 | 核对 appid：写 `tmp/_steam_appids_probe.py`，逐个 `appdetails` 打印 `data.name` + `movies[].name` | 确认表（哪些图有片、哪条片） | AI 执行，**结果需你确认** |
| S2 | 生成 `map_videos.json`（只含确认过的地图） | 文件 + 打包脚本追加一行 | AI |
| S3 | 前端 `lbMapWikiPromoHtml` 改造 + `.lb-mw-*` 样式 | `app_ui.js` / `app.css` | AI |
| S4 | 部署 + 实测（桌面 + 375 移动端：点击播放、iOS inline、无视频地图无按钮、404 回退） | 实测记录 | AI |
| S5 | 沉淀记忆：`dino-map-promo-video.md` | memory 文件 | AI |

---

## 7. 待你决策

1. **视频放哪几个地图**：全部 10 张都试；还是只给「有独立商店页」的 DLC 地图（Sco / Abe / Ext / Gen / Ast）？
2. **展示形式**：`点按钮播放（默认仍是图）` 还是 `图上方叠加播放按钮，点击直接全屏播放`？
3. **是否需要静音自动循环的「预览态」**（像商店页那样无声自动播放）—— 移动端流量与体验代价较大，默认**不启用**。
4. 若某些地图找不到对应宣传片，是否接受**这些地图不显示按钮**（推荐）。
