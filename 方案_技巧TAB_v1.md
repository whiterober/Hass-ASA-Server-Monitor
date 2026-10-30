# 「技巧」TAB 方案（v5739 预研）

> 提出人：用户（2026-10-31）
> 原话：「在两个 wiki 浮窗加一个 TAB：技巧：复用项目内 AI 模块，从 dododex 获取玩家分享的各种技巧并翻译；
> 顺便将现有的各个 TAB 文案集中优化再分配；在没人执行过 AI 时，直接复用 AI 模块样式（但是不显示提示词输入框）」
> 状态：**仅方案，未动手**

---

## 1. 目标与范围

| 项 | 内容 |
|---|---|
| 新增 TAB | 「💡 技巧」加在现有 8 个 TAB 之后（生物浮窗） |
| 覆盖浮窗 | `#lbWikiOverlay`（生物）、`#lbWikiItemOverlay`（物品）—— 两者数据源不同，见 §3.4 |
| 数据来源 | dododex.com 用户提交 tips（**已实测可抓**，见 §2） |
| 翻译方式 | 复用项目内 AI 模块（DeepSeek），按需翻译 + 本地缓存 |
| 附带工作 | 现有 8 个 TAB 的说明文案集中到一张常量表，重新分配措辞 |
| 空态要求 | 从未生成过 AI 时，直接复用 `.lb-hf-aibox` 外框样式，但**不渲染 textarea** |

---

## 2. 数据源可行性 —— 已实测（2026-10-31）

```text
GET https://www.dododex.com/tips/rex
→ HTTP 200 · 43,214 bytes · 单页 20 条 tip
→ 分页 /tips/rex/2
→ 分类页 /tips/rex/taming-ko | utility | encountering | funny | opinion | stories | name-ideas
```

**未被 Cloudflare 拦截**（普通 UA 直取即成功，与 ark.wiki.gg 的 403 完全不同）。

### 2.1 单条 tip 的真实 HTML 结构（原文摘录）

```html
<div class="lightbox marginBottom row aifs tip" data-tipid="440968">
  <div class="rowItem">
    <div class="marginBottom lh2 small">
      <span class="pill"><i class="fas fa-fire"></i> 1 point</span> &nbsp;
      <a class="pill noDec" href="/tips/rex/taming-ko">🥚 Taming &amp; KO</a> &nbsp;
      <a class="light noDec" href="/tips/rex/440968/slug...">
        <time datetime="2026-10-28T04:43:21+00:00">2 days ago</time></a> &nbsp;
      <span class="lightPill">✨ NEW</span> &nbsp;
      <a href="/report-tip?tipId=440968" ...>Report</a>
    </div>
    <div class="tipText lh"><p>正文…</p></div>
  </div>
</div>
```

### 2.2 可提取字段

| 字段 | 来源 | 用途 |
|---|---|---|
| `id` | `div.tip[data-tipid]` | 去重键 / 跳转原文 |
| `points` | 首个 `span.pill` 文本里的数字 | **排序主键**（高赞=高价值） |
| `cat` / `catEmoji` | `a.pill[href^="/tips/<slug>/"]` 的末段 + 文本 | 分类徽章 / 过滤 |
| `date` | `time[datetime]` | 显示「2 天前」 |
| `text` | `div.tipText` 内 `<p>` 拼接 | 翻译源 |

### 2.3 额外的宝藏：dododex 自家 AI 摘要

页面顶部还有一段：

```html
<div class="lightbox pad lh marginTop2" style="border-left:4px solid var(--lavlight)">
  <div class="bold ..."><i class="bxf bx-sparkles"></i> Dododex users say:</div>
  <div>The Rex is best tamed by luring it into a sturdy trap or ...</div>
</div>
```

这是 dododex 用全部 tips 汇总出的**一段连贯玩法摘要**（霸王龙版约 120 词），
比逐条 tip 更适合放在「技巧」TAB 顶部当**开篇总述**。

---

## 3. 后端设计（`独立后端/dino_backend.py`）

### 3.1 新增函数

```python
def _dodo_slug(key):
    """项目物种键/类名 → dododex slug
       优先 WIKI_EN_MAP[key]（wiki 英文名，如 Rex_Character_BP_C → rex）
       兜底：类名去掉 _Character_BP_C 后转小写连字符"""

def _dodo_fetch_tips(slug, pages=2, timeout=20):
    """抓 /tips/<slug> + /tips/<slug>/2，解析成 items[]"""

def _dodo_parse(html):
    """正则解析 items + summary"""

def _dodo_get(key, start=True):
    """带缓存 + 后台线程的取数入口（沿用 _wiki_get 的 worker 模式）"""
```

### 3.2 解析正则（按 §2.1 真实结构写，勿凭记忆改）

```python
_TIP_RE = re.compile(
    r'<div class="lightbox marginBottom row aifs tip" data-tipid="(\d+)">'
    r'.*?<span class="pill">.*?</i>\s*([\d,]+)\s*point'
    r'.*?<a class="pill noDec" href="/tips/[^/"]+/([a-z\-]+)">([^<]+)</a>'
    r'.*?<time datetime="([^"]+)"'
    r'.*?<div class="tipText lh">(.*?)</div>',
    re.S)

_SUM_RE = re.compile(
    r'Dododex users say:</div>\s*<div>(.*?)</div>', re.S)
```

> ⚠️ 落地时先 dump 一份真实 HTML 跑正则，验证 `hits == 20` 再写业务逻辑
> （历史教训：凭猜测写参数名 ⇒ 0 命中白忙，见 general.instructions「MediaWiki 抓取规范」）。

### 3.3 过滤与排序规则

```python
KEEP_CAT = ('taming-ko', 'utility', 'encountering')   # 丢弃 funny / opinion / stories / name-ideas
MIN_POINTS = 100      # 低赞多是「我朋友笑了」这类废话
MIN_LEN = 60          # 过短无信息量
TOP_N = 15            # 单物种最多 15 条
```

排序：`points` 降序 → 同分按 `date` 降序。

### 3.4 接口

```http
GET /api/dino/tips?cls=Rex_Character_BP_C
→ 200 {"ok":true,"slug":"rex","ts":1761...,
        "summary":"The Rex is best tamed by ...",
        "items":[{"id":"212611","points":2329,"cat":"taming-ko","catZh":"驯服·击晕",
                  "date":"2021-07-07","text":"after you have it down..."}]}
```

```http
GET /api/dino/tips/zh?cls=Rex_Character_BP_C      # 已翻译缓存命中时直接返回中文
POST /api/dino/tips/zh  {"cls":..., "items":[...]}  # 前端翻译完回写（可选，见 §4.4 方案 B）
```

### 3.5 缓存与限流

| 项 | 值 | 理由 |
|---|---|---|
| 磁盘缓存 | `/config/www/asa-data/wiki/_tips_<slug>.json` | 沿用 `_wiki_cache_path` 同套 |
| TTL | **30 天** | tips 增长慢，30 天足够新 |
| 抓取并发 | **串行**，单物种一次 | dododex 别惹（记忆里有「禁止并发抓外站」教训） |
| 失败退避 | 失败后 6 小时内不再重试 | 防止死循环打人家站 |
| 页数 | 最多 2 页（40 条原始） | 足够筛出 15 条 |

### 3.6 `_WIKI_PARSE_VER`

**必须递增**（当前 307 → 308）。历史教训：改了抓取/解析逻辑不递增 ⇒ 老缓存不失效，表现成「代码没生效」。

---

## 4. 前端设计（`dino-import.html`）

### 4.1 TAB 注册

```js
// L49492 现状
var LB_WIKI_TABS = ['概览','驯服','繁殖','采集','收割','技能','经验','生成指令'];
// 改为
var LB_WIKI_TABS = ['概览','驯服','繁殖','采集','收割','技能','经验','生成指令','技巧'];

// L53609 分发链追加（注意：新 TAB 索引 = 8，原 if 链是硬编码数字，别插错位）
if (_T === 8) { renderTips(); return; }
```

> 物品浮窗（`#lbWikiItemOverlay`）走另一套渲染，需要单独加（见 §4.6）。

### 4.2 三种状态

| 状态 | 显示 |
|---|---|
| **未生成过**（首次打开） | `.lb-hf-aibox` 外框 + `.lb-hf-aihint` 一行说明 + 一个 `.lb-hf-aibtn.primary`「🪄 抓取并翻译」—— **无 textarea、无模型/token 行** |
| **抓取完成未翻译** | 条目列表（英文原文）+ 底部「🪄 翻译全部（N 条）」 |
| **已翻译（缓存命中）** | 中文正文 + 分类/赞数/日期徽章 + 每条「原文」折叠 |

空态结构（严格复用 AI 模块类名，不新建皮肤）：

```html
<div class="lb-hf-aibox" id="lbTipsBox">
  <div class="lb-hf-aihint">还没有「技巧」数据 —— 从 dododex 抓取玩家分享的驯服/使用技巧（约 15 条，自动翻译成中文）。</div>
  <div class="lb-hf-airow">
    <span class="lb-hf-ai-fill"></span>
    <button class="lb-hf-aibtn primary" onclick="lbTipsGen()">🪄 抓取并翻译</button>
  </div>
</div>
```

**不渲染 `<textarea class="lb-hf-aiinput">`** —— 满足用户「不显示提示词输入框」的口径。

### 4.3 条目卡片样式（新类，作用域限定）

```css
#lbWikiOverlay .tc-tipc{padding:9px 11px;border-radius:9px;background:#7c3aed0e;border:1px solid #7c3aed2e;margin-top:8px}
#lbWikiOverlay .tc-tipc-h{display:flex;align-items:center;gap:6px;flex-wrap:wrap;font-size:11px;color:#8b8b9a}
#lbWikiOverlay .tc-tipc-tag{padding:1px 7px;border-radius:5px;background:#7c3aed26;color:#c4b5fd;font-weight:600}
#lbWikiOverlay .tc-tipc-pt{color:#f59e0b;font-weight:700}
#lbWikiOverlay .tc-tipc-b{font-size:12.5px;color:#cbd5e1;line-height:1.85;margin-top:6px}
```

> 放 `make_ic_css()` 之外（不在 info_card 体系），但须遵守「作用域限定 `#lbWikiOverlay`」。
> 遵守「界面禁止 ✓/✗」：分类徽章用 emoji（dododex 自带），赞数用 `⭐` 或 `mdi`。

### 4.4 翻译链（复用现有 AI 模块）

```js
// 复用已有函数，不新建配置体系
var cfg = lbAiCfgGet();                    // token / model
lbAiNormModel(cfg.model)                   // 模型归一
fetch(LB_AI_BASE + '/chat/completions', ...)  // 与 lbBbNotesAiGen 同源

// 批量策略：一次 5 条，JSON 进出，减少往返
// prompt: "把下面 5 条 ARK 玩家技巧翻译成简体中文，保留原意与语气，输出 JSON 数组"
// 失败降级：单条失败 → 保留英文 + 标记「未翻译」
```

**缓存**：`localStorage['lb_tips_<slug>'] = {ver, ts, summaryZh, items:[{...zh}]}`，
TTL 客户端 30 天，与后端一致。

**岔路（需你定）**：
- **方案 A（纯前端翻译）**：用户点按钮才翻，token 由用户自己的 AI 配置出。零后端成本，但每人翻一遍。
- **方案 B（后端预翻译 + 回写）**：第一个用户翻完回写后端，之后所有人直接读中文。省 token，但要加 POST 路由 + 写入权限校验。
- **方案 C（后端定时批量预翻译）**：后台 worker 抓完就翻，用户永远秒开。最省心，但后端要持有 AI token。

> 建议 **A → 后续升级 B**：先跑通体验，再考虑共享缓存。

### 4.5 现有 8 个 TAB 文案集中优化（`LB_WIKI_TXT`）

现状问题：
- 说明文案分散在 8 个 `renderXxx()` 里，长短语并存（有的 `tc-note` 一句 60 字，有的 `tc-hint` 三字）
- 同一概念重复表述：驯服 tab 讲「基础 ÷ 倍率」，繁殖 tab 再讲一遍
- `.tc-note` 已在 v5738 删掉 1 处，但采集/收割/经验/生成指令还有 5 处同款

重组方案：抽一张常量表

```js
var LB_WIKI_TXT = {
  ov:     { h: '概览',   intro: '…', note: '…' },
  tame:   { h: '驯服',   intro: '…', note: '…', tips: '…' },   // ← tips 来自 dododex taming-ko
  breed:  { h: '繁殖',   intro: '…', note: '…', tips: '…' },   // ← dododex breeding 相关
  gather: { h: '采集',   intro: '…', note: '…', tips: '…' },   // ← dododex utility
  harvest:{ h: '收割',   intro: '…', note: '…' },
  abil:   { h: '技能',   intro: '…' },
  exp:    { h: '经验',   intro: '…', note: '…' },
  spawn:  { h: '生成指令', intro: '…', note: '…' },
  tips:   { h: '技巧',   intro: '…', empty: '…' }
};
```

**重新分配原则**：

| 内容类型 | 归到哪个 TAB | 不放在哪 |
|---|---|---|
| 物种定位 / 一句话玩法 / 与原版差异 | 概览 | 其余全不放 |
| 击晕手法、麻醉、饲料、喂食节奏 | 驯服（并入 dododex `taming-ko`） | 技巧 |
| 交配 / 孵化 / 留痕 / 变异 | 繁殖（并入 dododex 繁殖类 tip） | 技巧 |
| 采集加成 / 工具挂钩 / 产量倍率 | 采集（+ dododex `utility`） | 技巧 |
| 宰杀产出 / 战利品 | 收割 | 技巧 |
| 技能说明 / 冷却 / 按键 | 技能 | 技巧 |
| 经验公式 / 值不值得练 | 经验 | 技巧 |
| 生成指令参数 | 生成指令 | 技巧 |
| **没有明确归属的零散心得、冷知识、骚操作** | **技巧** | — |

**统一措辞风格**（三条硬规矩）：
1. 说明行不超过 **1 行**（≈40 汉字），超了就折叠或删
2. 同类信息统一用 `.tc-hint`（灰小字）或 `.tc-note`（黄虚线框），**不许同一 TAB 内两种混用**
3. 数字一律 `tcNum()` / 时长一律 `tcDur()`，禁止裸字符串

### 4.6 物品浮窗（`#lbWikiItemOverlay`）

dododex **没有物品 tips**。三个选项：

| 选项 | 说明 | 成本 |
|---|---|---|
| **甲** | 物品浮窗不加「技巧」TAB（只在生物浮窗加） | 0 |
| **乙** | 加 TAB，但内容来自项目自有「物品笔记」AI（`lbBbNotesAi*` 那套）复用 | 中 |
| **丙** | 加 TAB，内容 = 该物品在 dododex 对应生物下的相关 tip 关键词匹配 | 高、命中率低 |

> 建议 **甲**，先做生物浮窗。物品侧价值不明显，且已有「物品 Wiki」自己那套内容。

---

## 5. 工作量估算

| 阶段 | 内容 | 预估 | 交付物 |
|---|---|---|---|
| **P0** | 后端：slug 映射 + 抓取 + 解析 + 过滤 + 缓存 + 路由；`_pv` → 308 | 约 200 行 / 1 轮 | `dino_backend.py`（需你重启后端） |
| **P1** | 前端：TAB 注册 + 三态渲染 + 空态复用 AI 样式 + 条目卡片 CSS | 约 250 行 / 1 轮 | `dino-import.html` v5739 |
| **P2** | 翻译链接入（方案 A）+ localStorage 缓存 + 失败降级 | 约 120 行 / 1 轮 | v5740 |
| **P3** | `LB_WIKI_TXT` 常量表 + 8 个 render 函数改为读表 + 措辞统一 | 约 300 行 / 1-2 轮 | v5741 |
| **P4** | 实测：霸王龙 / 阿根廷巨鹰 / 一个新生物（数据缺的）三档验证 | 0.5 轮 | 验证 JSON |

**总估**：4-6 轮部署，不含你重启后端的时间。

---

## 6. 风险与坑（提前记下）

| 风险 | 应对 |
|---|---|
| dododex 改版 → 正则全灭 | 正则单独成常量；解析失败时返回 `ok:false, reason:'parse'`，前端显示「暂无技巧」而不是报错；连续 3 次失败自动关站 24h |
| slug 映射不到（新生物 dododex 还没收录） | 返回空态，不编造；显示「dododex 暂未收录该物种的技巧」 |
| 低质量 tip 泛滥（"我朋友笑了"） | `MIN_POINTS` / `MIN_LEN` / 分类白名单三重过滤 |
| AI token 未配置 | 抓取按钮旁提示「需先在 ⚙ 配置 AI Token」，不阻塞抓取（可先看英文原文） |
| 首屏变慢 | tips **懒加载**（点开「技巧」TAB 才请求），不参与 wiki 首包 |
| PWA 缓存旧壳 | `sw.js` 的 `VER` 随每次部署递增（既有流程） |

---

## 7. 需要你拍板的 3 个岔路

1. **翻译在哪做** → §4.4 方案 A（纯前端，用户自己 token）/ B（后端共享缓存）/ C（后端定时预翻译）
2. **物品浮窗要不要也加** → §4.6 甲（只加生物）/ 乙 / 丙
3. **dododex 自家 AI 摘要要不要用** → §2.3 那段 `Dododex users say:` 放「技巧」TAB 顶部当总述（建议要，免费且质量不错）

---

## 8. 小白版一句话

dododex 这个站我实测能直接抓（不像 wiki 那样被墙），一个物种一次能拿 20 条玩家技巧，
按点赞数排前排的就是干货；抓到后让项目里已有的 AI 翻成中文缓到本地。
技术上是「后端加一个抓取接口 + 前端加第 9 个标签页」，难点不在抓，在于**得挑出有用的、别让废话刷屏**。


---

## 9. 用户拍板结果（2026-10-31，v5739 起生效）

| 岔路 | 用户决定 | 落地状态 |
|---|---|---|
| TAB 位置 | 「技巧」排在「生成」**之前** | ✅ v5739 已实现（生物浮窗索引 7=技巧、8=生成） |
| 「生成指令」命名 | 改名「**生成**」，**两个浮窗都改** | ✅ v5739 已实现（`LB_WIKI_TABS` / `LB_WI_TABS` / tooltip×3 / 物品内区块标题） |
| 物品浮窗要不要加「技巧」 | **不加**（dododex 无物品 tips） | ✅ v5739 物品浮窗只改名，未加 TAB |
| 翻译在哪做 | **后端共享缓存**（第一个人翻完回写，之后所有人读中文） | ⏳ 待实现，见 §9.1 |
| dododex 自家 AI 摘要 | 未定 | ⏳ 建议随 P0 一起抓，前端先不展示 |
| 本轮范围 | 只改 TAB 结构 + 改名，技巧先占位 | ✅ v5739 |

### 9.1 「后端共享缓存」方案落地要点（替代原 §4.4 方案 A）

原 §4.4 的三选一已定为 **方案 B（后端共享缓存）**，实现要点：

```text
① 后端抓取后写入两处：
   - wiki/_tips_<slug>.json        原始英文（30 天 TTL）
   - wiki/_tips_<slug>_zh.json     中文译文（永久，除非原文变更）

② 翻译触发：
   - GET /api/dino/tips?cls=xxx  → 读英文缓存
   - GET /api/dino/tips/zh?cls=xxx → 有中文直接返回；无中文返回 {"needZh":true,"items":[英文]}
   - POST /api/dino/tips/zh  {"cls":..., "zh":[{"id":..., "text":"..."}]}
       · 前端翻完回写
       · 后端做 base64 长度/条数上限校验（防滥用）
       · 写入前按 id 合并，已存在的中文条目**不覆盖**（多客户端并发安全）

③ 成本控制：
   - 单物种上限 15 条、单条 ≤ 1200 字
   - 已有中文的条目不重复翻译（按 tip id 比对）
   - 后端保留一个 `_tips_zh_tokens` 计数日志，便于事后核算

④ 前端：
   - 命中中文 → 直接渲染，零 token
   - 未命中 → 复用 lbAiCfgGet() 的 token，一次 5 条批量翻，翻完 POST 回写
   - localStorage 仅做「本次会话已请求」的轻量防抖，**不再做长期缓存**（长期缓存由后端承担）
```

> ⚠️ 注意：`POST` 会往 `/config/www/asa-data/` 写文件，须遵守项目铁律「**禁止服务器端 Python 写 JSON 数据文件**」
> —— 但该铁律针对的是被 HA 进程/缓存还原的 `server_rules.json` 等文件；
> wiki 缓存目录（`wiki/`）本来就由 `_wiki_save()` 写入，属既有机制，可复用 `_wiki_save()` 而非新写。

### 9.2 本轮（v5739）已交付

| 文件 | 改动 |
|---|---|
| `dino-import.html` | `LB_WIKI_TABS` 8→9（技巧/生成）；分发链 `7→renderTips`、`8→renderSpawn`；新增 `renderTips()` 占位（复用 `.lb-hf-aibox`，无 textarea）；`LB_WI_TABS` 末项改「生成」；物品内 `SEC('生成指令')→SEC('生成')`；tooltip×3 同步 |
| `pwa/sw.js` | `VER` → `v20261030-5739` |

**占位态实测要点**：点「技巧」TAB 只出现一个虚线框 + 一行说明 + 「待接入」，**无输入框、无模型/token 行** —— 严格符合用户「复用 AI 模块样式但不显示提示词输入框」的口径。
