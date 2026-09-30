# WorldProbe 公共设施全面改造 · 完整实施计划

> 生成：2026-09-30 ｜ 目标项目：dino-import（CF Worker 纯 Assets 架构）
> 依据：《WorldProbe 前端交接单》（插件 v9，dll 1,594,368 B，2026-09-26，10 图已全量部署）
> 修订：v2（2026-09-30）：SupplyCrate/BeaverDam/BeeHive 改**纯实时**；实时区**前置** + 样式对齐静态 + 低可视化 MDI 标记
> 状态：**计划（未实施）** ｜ 涉及文件：`独立后端\dino_backend.py`（真身 `\\SERVER\dino_backend\dino_backend.py`）、`dino-import.html`

---

## 1. 目标与范围

### 1.1 一句话目标

把 dino-import 物品浮窗「公共设施」块，从"**存档扫描的静态清单**"升级为「**静态保留 + WorldProbe 实时查询**」双轨视图：静态设施照旧展示，新增按服务器/类别的实时查询（含坐标、档位、形态、数量）。

### 1.2 保留项（用户点名，绝对不替换）

以下静态设施**继续走现有存档 `isPublic` 数据源**，不因实时改造被移除（静态区**白名单仅此 4 类**）：

| 用户称呼 | 现有类名前缀（LB_PUBFAC_PREFIX） | 说明 |
|---|---|---|
| 城市终端 | `CityTerminal` / `PrimalStructure_CityTerminal` | Ext 任务设施 |
| 神器台座 | `ArtifactCrate` | 神器箱/台座实例 |
| 埋藏藏宝箱 | `TreasureCache_Small` | 寻宝埋藏点 |
| 电力节点 | `PowerNode` / `PrimalStructurePowerNode` | Ext/Gen 电力设施 |

> **v2 修订**：`SupplyCrate`（补给箱）、`BeaverDam`（河狸窝）、`BeeHive`（野生蜂巢）三类**改为纯实时**（WorldProbe）——静态区**不再显示**这三类。
> 实现建议：静态区采用**展示层白名单过滤**（仅显示上表 4 类）；`LB_PUBFAC_PREFIX` 的收集与建筑栏剔除逻辑**保持不变**（避免结构栏回归显示）。

### 1.3 新增能力（WorldProbe 实时轨）

- **11 类**世界物件实时查询（见 §3.1 映射表）
- **坐标**（x/y/z，`hasLoc` 判定 + (0,0,0) 过滤）
- **档位**（osd/cavecrate/elementnode 单词档；beacon `L<NN>` 等级）
- **形态识别**（河狸窝三种 class 形态）
- **数量统计**（每类 matched/returned/truncated 如实展示）

---

## 2. 现状盘点

### 2.1 前端「公共设施」块（v3933~v3982 建设，现状基线）

- **位置**：物品浮窗内 `#lbPubFacHead` + `#lbPubFacGrid`（构建于物品页构建函数内，`dino-import.html` L16201 区；渲染/折叠联动 L16906/L18086 区）
- **数据源**：存档设施数据 `f.isPublic===1` → `lbPubFacAdd(abbr, f)` 织入 `LB._pubFac`（L4450~4467 调用点；L17549+ 实现）
- **口径**：`lbIsPubFacKey()`（L17589+）= 前缀匹配 `LB_PUBFAC_PREFIX`（9 前缀）+ 后缀 `LB_PUBFAC_SUFFIX`（空）+ 排除 `_PlayerOwned`/quest/规则隐藏
- **展示**：每类一行（图标 + 中文 + 英文），tooltip 列出现过的服务器与类名；数量本地缓存 `LB_PUBFAC_LS`
- **局限（本次要解决的）**：无坐标、无实时性、无档位、无"当前世界是否存在"判断

### 2.2 后端 RCON 基础设施（`独立后端\dino_backend.py`，已就绪）

- RCON 链路：`rcon_command()` / `_rcon_str()`（v13 分包截断修复 / KeepAlive 免疫 / 控制字符剥离）；`PORTS` 表（Isl 32320 ~ Gen 32329）；`RCON_HOST=192.168.199.3`
- 路由模式：`do_GET`/`do_POST` 按 path 分支；POST JSON `{server, ...}` → RCON → 直接返回或写状态文件
- 现成先例：`/api/refresh_eggs`、`/api/volcano_state`（**3s TTL 单点缓存**——插件文档 §4 约束"多客户端不得直连狂查"）、`/api/volcano_log`、`/api/inv_probe`
- 命令常量区（L135~141）：`CMD_EGG_PROBE` / `CMD_VOLCANO` / `CMD_INV_PROBE` …（新增即加一行）

### 2.3 WorldProbe（插件 v9，摘要）

`TransferIdentityFix.WorldProbe <types|query|scan|weather>`；11 类字典；`query` 返回 `matched/returned/truncated/actors[{class,difficulty,hasLoc,x,y,z}]`；全命令 **1.1–1.3s**；三大坑（按需加载 / (0,0,0) 幽灵坐标 / scan top≤500）。详见附件交接单。

---

## 3. 映射与差异

### 3.1 类别映射表（静态 ↔ 实时）

| WorldProbe 类别 | 中文标签（前端用） | 现状静态口径 | 行动 |
|---|---|---|---|
| `beacon` | 补给光柱 | ~~SupplyCrate*~~（v2 已转纯实时） | **纯实时**（带 `L<NN>` 档位） |
| `osd` | 轨道空投 | （无） | **实时**（难度档位） |
| `cavecrate` | 洞穴补给箱 | （无） | **实时** |
| `horde` | OSD 部落设施 | （无） | **实时** |
| `artifactcrate` | 神器箱/台座 | ArtifactCrate | 静态保留 + **实时可查**（坐标增强） |
| `elementnode` | 元素节点（矿脉） | （无，勿与 PowerNode 混淆） | **实时**；**PowerNode 电力节点仍静态** |
| `beehive` | 野生蜂巢 | ~~BeeHive~~（v2 已转纯实时） | **纯实时**（PlayerOwned 本就不含） |
| `obelisk` | 方尖碑 | （无） | **实时** |
| `beaverdam` | 河狸窝 | ~~BeaverDam~~（v2 已转纯实时） | **纯实时**（三形态标签） |
| `beaver` | 野生河狸 | （无） | **实时** |
| `weather` | 天气 | （无） | 本期仅后端路由预置，**UI 不接入**（P4 再议） |

> 差异结论（v2）：**仅静态** = `CityTerminal` / `TreasureCache_Small` / `PowerNode`（WorldProbe 无对应）；**双轨** = `ArtifactCrate`（静态 + 实时坐标）；**纯实时** = `SupplyCrate`(beacon) / `BeaverDam` / `BeeHive`；其余为**纯新增**。

### 3.2 双轨展示原则（v2）

- **版式顺序：实时区在前、静态区在后**（用户口径："先显示实时的部分"）
- **样式统一**：实时区条目样式与静态区一致（每类一行：图标 + 中文 + 英文；同款字号/间距/对齐）
- **实时区标记**：加一个**低可视化 MDI 图标**（低透明度/灰调，对齐现有低可视化规范：`opacity≈0.65`、色 `#555`/`#999`、小尺寸）——建议 `mdi-access-point`（实现时定）
- 静态区：标题「公共设施」+ **白名单仅 4 类**（§1.2）
- 两区**互不覆盖**

---

## 4. 架构设计

### 4.1 后端（`独立后端\dino_backend.py`；改真身流程见 §7.3）

**新增常量**：

- `CMD_WORLDPROBE = 'TransferIdentityFix.WorldProbe'`

**新增 3 条路由**（全 POST JSON，响应透传插件 JSON）：

| 路由 | body | RCON 命令 | 缓存策略 |
|---|---|---|---|
| `/api/worldprobe_types` | `{server}` | `WorldProbe types` | 内存 TTL 600s（字典极稳定） |
| `/api/worldprobe_query` | `{server, type, limit}` | `WorldProbe query <type> limit=<N>` | 内存 TTL 5s，键 `server|type|limit`；同键并发合并（单点取数） |
| `/api/worldprobe_weather` | `{server}` | `WorldProbe weather` | 内存 TTL 10s（本期仅预置） |

**约束与实现要点**：

- `limit` 默认 **20**、上限 **100**（RCON 响应约 8KB 上限，参照 InvProbe 注释经验；超限截断由插件 `truncated` 透传）
- 超时 `timeout=8`（对齐 Volcano；单命令 1.1–1.3s，留裕量）
- 失败返回范式对齐现有：`{ok:false, server, error:'rcon: ...'}`
- **并发闸**：同 (server,type) 同时只发 1 条 RCON（其余请求挂在缓存 Promise 上）——对齐 Volcano"后端单点轮询"原则

### 4.2 前端（`dino-import.html`）

**改造点**：物品浮窗「公共设施」块内新增「实时查询」小节——**排在静态列表之前**（实时在前）；实时条目样式与静态一致 + 低可视化 MDI 标记；静态列表仅显示 4 类白名单（§1.2，展示层过滤）

- **服务器选择**：复用块内小选择器（默认 = 当前聚落/主视图选中服；11 服：Isl…Gen）
- **类别 chips**：11 类中文标签（§3.1 表），点击切换查询（单选，默认 `beacon`）
- **查询按钮 + 状态**：查询中禁用（1.1–1.3s/次）；结果时间戳显示
- **结果展示**（每类一块）：
  - 顶行：`matched / returned / truncated` 摘要（如"共 7 · 显示 7"；`truncated=1` 时橙字"N 条未展示，增大 limit"）
  - 列表行：`图标 + 中文名 + 档位徽标 + 坐标 (x, y, z) + 复制按钮`
  - 河狸窝形态标签：含 `DenLogs`→"巢穴"、`BP_` 前缀→"大型坝"、其余→"普通坝"
  - 过滤统计：`(0,0,0)` 幽灵坐标过滤后在列表尾部备注"已过滤 N 条未初始化"
- **提示条（常驻）**："数据为服务器当前可见范围（按需加载，扫不到≠不存在），查询约 1.1–1.3s/类"
- **错误态**：RCON 失败显示"服务器离线或插件未响应"（对齐现有风格）

### 4.3 缓存与并发

- 前端：会话级 LRU `{server|type → {ts, data}}`，TTL 5s；切换类别命中缓存即秒显、后台 5s 后自动不强刷
- 后端：§4.1 表格；**任何情况下前端不得连点批量 11 类**（如做"全查"按钮，必须后端串行队列：一类一查、间隔 ≥1s）

### 4.4 UI 线框（文字版）

```
「公共设施」块（v2：实时在前）
├─ [实时查询（WorldProbe）]  ← 低可视化 MDI 标记（如 ⌖，淡色小图标）
│  ├─ 服务器 [Isl ▾]　类别 [光柱][河狸窝][蜂巢][空投][…]（chips）
│  ├─ [查询]  上次更新 12:30:45
│  ├─ 摘要：共 12 · 显示 12 · truncated=0
│  ├─ 行1: [图标] 补给光柱 Beacon [L25] (123456, -65432, 9876) [复制]
│  └─ 行2: [图标] 河狸窝 Beaver Dam [普通坝] (153521, -223182, -13704) [复制]
│     …（已过滤 2 条未初始化；条目样式同静态：图标+中文+英文）
└─ [静态列表区]（白名单 4 类：城市终端 / 神器台座 / 埋藏藏宝箱 / 电力节点）
   └─ 行: [图标] 城市终端 City Terminal（tooltip 服务器/类名）
```

---

## 5. 坑适配清单（必读，来自附件 + 本项目经验）

| # | 坑 | 对策 |
|---|---|---|
| 1 | 「扫不到」≠「不存在」（按需加载） | UI 常驻提示条；多轮/多点采样属运维动作，前端不承诺"全图总数" |
| 2 | `hasLoc=1` 但坐标 (0,0,0) | 前端**必须过滤** + 尾部备注过滤计数 |
| 3 | `scan` top≤500 | 前端**不使用 scan**（仅 types+query）；运维用字母分片，方案留存 |
| 4 | RCON 8KB 响应上限 | `limit` 默认 20/上限 100；truncated 提示 |
| 5 | 每类查询 1.1–1.3s、RCON 挤占游戏主线程 | 后端 TTL + 单点并发合并；前端防连点；全查须串行队列 |
| 6 | Abe 天气 `weatherState=null` | 不解析 `fields` 原始列表；按"无数据"展示（本期 UI 不接天气，预置路由） |
| 7 | OSD 档位浮动 | 档位原样展示，不做固定假设 |
| 8 | beacon `L<NN>` 颜色因图而异 | 本期**只显等级文本**；颜色映射表为 P4 可选项 |

---

## 6. 分阶段实施

### P0 · 联通性预检（0.5h）

- 在服务器机（或经现有后端临时命令）手工执行 `TransferIdentityFix.WorldProbe types`，确认：`ok:true`、`typeCount=11`
- 抽测 `query beaverdam`（对照附件实测表：Ast 15 / Rag 6 / Val 5 …，允许因世界加载状态偏差）
- **验收**：连续两条命令均 1.1–1.3s 返回且 JSON 可解析

### P1 · 后端路由 + 前端最小可用（2~3h）

- 后端：加 `CMD_WORLDPROBE` + 3 路由 + TTL/并发；`py_compile`；覆盖真身+重启（§7.3）
- 前端：块内加「实时查询」小节（**置于静态区之前**；服务器选择 + 单类别 beacon 查询 + 列表含坐标 + 样式对齐静态 + 低可视化 MDI 标记）
- **验收**：指定服 `query beacon` 返回列表带坐标；连续点击不超发 RCON（后端日志单次）

### P2 · 双轨整合（2~3h）

- 类别 chips 全套 11 类；档位/形态标签；复制坐标；truncated/过滤统计；**静态区白名单过滤（仅 4 类，剔除 SupplyCrate/BeaverDam/BeeHive）**；复测建筑栏无回归
- **验收**：静态列表 = 仅 4 类白名单（内容与改造前该 4 类一致）；建筑栏无公共设施回归；实时区三类（beacon/beaverdam/beehive）逐类可查且样式与静态一致

### P3 · 打磨（1~2h）

- 缓存命中优化、错误态文案、移动端布局（≤768px 行内换行）
- **验收**：清 SW+缓存后全流程复测；文档同步（本计划勾选完成项）

### P4 · 预留（不在本期）

- 天气卡（weather → 底部功能条，参照 Gen 火山模式）；beacon 等级颜色映射表；地图打点（需先确认 `报告\*_coord_calib.json` 坐标体系的复用性）

---

## 7. 验证与部署

### 7.1 后端验证

- 路由存在性判定（铁律）：`POST https://data.whiterober.ccwu.cc/api/worldprobe_types` 不带鉴权 ⇒ **401 login required = 路由存在**；404 = 未重载
- 功能抽查：`types.typeCount==11`；`query` 的 `actors[].class` 与游戏内实物对照（抽 1~2 个点）

### 7.2 前端验证

- 清 SW + caches 后 `?t=` 强刷；静态区对照改造前截图/条目清单；实时区逐类抽查（含 (0,0,0) 过滤场景）

### 7.3 部署流程

- 前端：`python tmp\_deploy_cf.py`（版本递增 vXXXX；打包→wrangler→线上校验）
- 后端：备份真身（`\\SERVER\dino_backend\` 同目录 `.bak_时间戳` + 工作区 `bak/`）→ 工作区镜像覆盖真身 → 校验关键字 + `py_compile` → 在 **服务器机**执行 `restart_dino_backend.bat` → 用户确认重启

### 7.4 回滚

- 前端：CF 控制台回退上一 Version ID（或重新部署旧 `dino-import.html`）
- 后端：用 `.bak_` 快照还原 + 重启

---

## 8. 风险登记

| 风险 | 等级 | 缓解 |
|---|---|---|
| RCON 高频查询挤占游戏主线程 | 中 | TTL 缓存 + 单点合并 + 前端防连点（§4.3） |
| 大响应截断（>8KB） | 低 | limit 上限 + truncated 明示 |
| Abe 天气不可读 | 低 | 本期 UI 不接天气 |
| 静态数据与实时结果不一致（同一物两处显示） | 低 | 双轨标题区分；不合并去重 |
| 后端重启窗口内查询失败 | 低 | 错误态文案；重启用户确认后复测 |

---

## 9. 开放问题（待用户定夺）

1. 「复制坐标」后是否需要附"传送/打点"指令（现有 `track_location` 打点先例可复用）？
2. `limit` 默认值（建议 20）与上限（建议 100）
3. 低可视化 MDI 标记的图标选型（建议 `mdi-access-point`；实现时定）
4. 是否需要"全查"按钮（11 类串行，约 15s；默认不做，仅高级入口）

---

*本计划由 ASA Server Monitor 智能体生成；实施前请以 §6-P0 联通性预检结果为准修订参数。*
