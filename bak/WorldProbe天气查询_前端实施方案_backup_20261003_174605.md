> 状态：**方案（未实施）** | 生成 2026-10-03 | 依据《WorldProbe 世界 Actor 查询 前端调用文档》（插件 v13，10 图已部署）
> 目标文件：`dino-import.html`（前端，CF Workers Assets 部署）；**后端 `独立后端/dino_backend.py` 零改动**

---

# WorldProbe 天气查询按钮 · 前端实施方案

## 一、需求

1. 依据交接单，在**每张地图的底部功能栏**添加「天气查询」按钮。
2. 该按钮与其面板**完全复用（非复制）火山计时的样式与结构** —— 与火山共用**同一份**外壳与轮询骨架代码，而非复制一份新实现。
3. 范围裁定：**仅 10 图**（Isl / Sco / Cen / Abe / Ext / Ast / Rag / Val / Los / Gen）；**Bob（俱乐部）不加**（插件未部署该图）。

---

## 二、现状证据（已逐项核对，含锚点）

| 项 | 位置 / 结论 |
|---|---|
| 功能条能力表 | `LB_SRV_FUNCS = { Gen: ['volcano'] }` → `dino-import.html` L20376 |
| 功能条按钮定义 | `LB_FUNC_DEF` L20377（`label / color / open / title` 四字段驱动） |
| 功能条渲染 | `lbRenderFuncBar()` L20418 —— **通用驱动**：按钮文案/配色/动作全取自定义表 ⇒ 加按钮只需改表，无需写按钮 HTML |
| 功能条容器 | `#lbFuncBar` → `#lbFuncActions`（L26657-26663；`display:none` 默认，有功能才显示） |
| 火山面板 | `lbVolcanoOpen()` L20764：`.lb-picker-overlay` → `.lb-picker-panel` → `.lb-picker-header`（标题 + ✕）→ 正文 `#lbVolcBody`（`padding:10px 12px; overflow-y:auto`） |
| 火山轮询/重绘 | `lbVolcSync()` 3s 轮询；`lbVolcRender()` 每秒重绘（`LB._volcTimer`）；`lbVolcLogPull()` 台账 15s |
| 火山关闭 | `lbVolcClose()` L20779：清定时器 → 移除 overlay → `lbRenderFuncBar()` |
| 后端路由（**已存在**） | `worldprobe_weather()` → `独立后端/dino_backend.py` L1206；TTL `WP_WEATHER_TTL_MS = 10000`；路由 `path.endswith('worldprobe_weather')` L1970；注释原文「本期仅预置路由，UI 不接」 |
| 插件命令 | `TransferIdentityFix.WorldProbe weather`（交接单 §一；权限 `tif.viewer`） |
| 渲染字段依据 | 交接单 §五：`target / confidence / weatherActorCount / weatherActorClasses / weatherActors / weatherActorDetails / weatherState{family, …}` |
| 强制约束 | ① `weatherState = null`（畸变）**按"无数据"展示，禁止回退解析 `fields`**；② `weatherState` **按 key 存在性判断**，不得假设键齐全；③ 前端不需要 `scan` |
| 前端既有接线（可参照） | 公共设施实时区 v4138：`lbWpQuery()` L18597（POST + 错误处理 + 冷却），`LB_WP_MS = 10000` 全块 CD |

---

## 三、改动清单（仅 `dino-import.html`）

### 3.1 按钮（改表即得，天然零复制）

- `LB_SRV_FUNCS`：10 图各挂 `'weather'`；创世为 `Gen: ['volcano', 'weather']`（两个按钮并排渲染）。
- `LB_FUNC_DEF` 新增一项：

  | key | label | color | open | title |
  |---|---|---|---|---|
  | `weather` | `🌦️ 天气查询` | `#0ea5e9` | `lbWeatherOpen` | 实时天气（插件权威数据） |

### 3.2 抽公共壳（「复用非复制」的落点）

新增四个共享函数，**火山与天气共用同一份代码**：

| 共享函数 | 职责 |
|---|---|
| `lbFuncPanelOpen(key, title)` | 建 overlay + panel + header（标题 + ✕）+ 正文容器；返回正文元素（沿用火山**同一套 class 与内联样式**） |
| `lbFuncPanelClose(key)` | 清定时器 → 移除面板 → `lbRenderFuncBar()` 刷新功能条 |
| `lbFuncPanelPoll(key, fn, ms)` | 轮询骨架（同键只跑一份定时器） |
| `lbFuncPanelTick(key, render)` | 每秒重绘骨架（用于"数据更新于 X 前"类相对时间） |

**火山侧改造（只搬不改）**：`lbVolcanoOpen / lbVolcClose / lbVolcRender / lbVolcPollStart` 保留原函数名，内部改为调用上述共享函数（薄包装）⇒ 对外依赖零破裂、视觉与行为维持现状。

### 3.3 天气三件套（只写"数据 + 内容"）

| 函数 | 内容 |
|---|---|
| `lbWeatherOpen()` | `lbFuncPanelOpen('weather', '🌦️ 天气查询 · ' + 图名)`；开窗立即拉取一次 + 10s 轮询（后端 TTL 10s ⇒ N 客户端只发 1 次 RCON） |
| `lbWeatherSync()` | `POST {LB_API}/api/worldprobe_weather`，body `{ server:<图> }`；失败文案分支见 §3.4 |
| `lbWeatherRender()` | 渲染（见 §3.4） |

### 3.4 渲染设计（对齐交接单）

1. **顶部大字区**：`target` 类名（去 `_C` 后缀）+ `confidence` 徽章（`high` 绿 / `medium` 黄 / `low` 灰）。
2. **中部**：`weatherState` **按 key 存在性**逐行渲染，键名映射中文（雾 / 雨 / 风 / 风向 / 当前天气ID / 下次天气ID / 距切换秒 …）；`family` 两种形态（`uds` / `ext_gen`）分别标注来源族。
3. **`weatherState = null`**：显示「本图天气状态暂不可读（插件未适配该族字段，如畸变）」—— **绝不回退解析 `fields`**。
4. **底部**（沿用火山同款版式）：「数据更新于 X 前」+「数据来自游戏内天气装置（插件权威数据）」。
5. **错误分支**：`unknown server` → 「该服务器暂不支持天气查询」；RCON 超时/无响应 → 「权威数据不可达：…」；**最多重试 2 次即停**（遵守重试上限）。

### 3.5 边界（明确不做）

- 不改后端（路由与 TTL 已就绪）；
- 不动火山计时算法/文案；
- 不动 `LB_WP_*` 公共设施实时区逻辑；
- 不引入 `scan` / `query`；
- 不做交接单 §四"坑 1"未决的「全图总数 / 多点采样」需求；
- Bob 图不显示按钮；非地图页（`LB.tab === 'player'`）不显示（沿用现有 `lbVolcServer()` 判定）。

---

## 四、部署与验证

**部署**：`tmp/_deploy_cf.py`（CF 前端一键部署；递增 `LB_VERSION` + `pwa/sw.js` VER）；后端**无需**重启。

**验证清单（线上 PW 实测）**：

| # | 检查项 | 期望 |
|---|---|---|
| 1 | Gen 功能栏 | 「🌋 火山计时」+「🌦️ 天气查询」两按钮并存 |
| 2 | 火山面板回归 | 排版/文案/倒计时与改造前**完全一致**（抽壳未引入回归） |
| 3 | Rag / Sco 天气面板 | 打开即出 `target` / `confidence` / `weatherState`；重复打开 10s 内命中后端缓存（`cacheAgeMs` 可见） |
| 4 | Abe 天气面板 | `weatherState = null` ⇒ 显示"暂不可读"提示，**不报错、不空白** |
| 5 | 关闭行为 | 关闭后功能条恢复、底部留白正常（`lbBottomFix`） |
| 6 | 非 10 图（Bob）与 `player` 页 | **无**天气按钮 |
| 7 | 构建自检 | 内联 `<script>` `node --check` 3/3 通过、`U+FFFD` = 0、线上版本一致（`版本一致: True`；若报 False 属边缘缓存假象，用 `no-store` 复核） |

---

## 五、风险与对策

| 风险 | 对策 |
|---|---|
| 抽公共壳回归火山面板 | **只搬不改**（DOM 结构 / class / 内联样式原样迁移）；改后**先回测火山**再验天气 |
| 某图仍是旧 dll | 显示「该服务器暂不支持」文案；不自动重试（≤2 次后停） |
| 连点 / 多端并发 | 后端 10s TTL + 同键并发合并；前端仅"面板打开时"轮询（无后台轮询） |
| 字段差异（两族键） | 一律按 key 存在性渲染，缺键不显示、不填默认值 |

---

## 六、实施顺序（获批后执行）

1. 备份 `dino-import.html` → `bak\`；
2. 抽公共壳（火山改薄包装）+ 回测火山；
3. 加 `LB_SRV_FUNCS` / `LB_FUNC_DEF` 条目；
4. 写天气三件套（数据 + 渲染）；
5. 语法校验 → CF 部署 → 线上 PW 按 §四 七项验证；
6. 进度写盘 + 计划文档补记。
