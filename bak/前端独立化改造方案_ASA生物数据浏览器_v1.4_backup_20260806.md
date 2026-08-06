# 前端独立化改造方案 — dino-import.html → ASA 生物数据浏览器

> 版本：v1.4 · 日期：2026-08-06
> 状态：方案（待确认后实施）
> 关联：插件 `TransferIdentityFixAPI` v0.3.0（RCON 13 命令 + tamed/cryo 双 JSON）
> 更新 v1.2：时间窗口改为「**游戏时间最新 30 天**」，基于**世界秒差值**实现，跨服基准偏移天然免疫
> 更新 v1.3：新增 §4.5 畸变（Abe）特殊说明——论证差值方案对畸变依然有效 + 实服验证方法
> 更新 v1.4：生物列表排序规则——按世界秒**从最近到最旧**（fallback 用 downloadedAtMs）

---

## 1. 改造目标

1. **摆脱 Wikily 依赖**：前端不再依赖 Wikily API 导入链路，成为独立自主的生物数据浏览/查询工具。
2. **保留现有 ini 解析能力**：`parseIni()`(L836) → `solveLevels()`(L274) → `calcStatValue()`(L249 ASB) → `ensureSpeciesStats()`(L216) 完整保留。
3. **新增四大能力**：
   - ① 玩家名 URL 参数过滤（禁止显式配置）
   - ② 玩家所在部落（成员即可）**游戏时间最新 30 天**新增生物，全服务器 tamed+cryo 整合
   - ③ 生物归属按容器部落判定 + 部落成员背包计入
   - ④ 跨服某物种整合列表（分服务器、分容器）

---

## 2. 现状盘点（已验证）

### 2.1 数据可用性（`P:\私人共享\ASA\DinoData`，P: = NAS QFTP 映射盘）

| 数据源 | 可用服务器 | 备注 |
|--------|-----------|------|
| `<缩写>_cryo.json` | Abe / Ast / Cen / Ext / Gen / Isl / Los / Rag / Sco / Val（10 台） | 球内 + 宠物台 |
| `<缩写>_tamed.json` | Abe / Ast / Cen / Ext / Isl / Sco（6 台） | 放出的龙；缺 Gen/Los/Rag/Val |

> 前端对缺失服务器必须容错跳过（数据随 Qsync 逐步补齐）。

### 2.2 时间字段（已实服验证）

- **统一字段 `downloadedAtMs`**（tamed / cryo / ArkGetDino）：实测值 `1725981792229` = **Unix 毫秒**（下载进服时间，`DinoDownloadedAtTime`）
  - 语义：龙**最后一次真·下载进这台服务器**的时间；装球 / 放出 / 带球转服 **不更新**
- **无时间 / 无效情况**：空球、v6 旧球、宠物台(stand)、系统单位、**早于 2023-10-25（ASE 脏数据）**
- **世界秒基准**：ARK 存档原始时间（下载/驯服/孵化）为**世界秒 GameTimeSeconds**，各服务器基准独立 → 详见 §4.4 差值方案

### 2.3 ASA 时间系统速查（用户确认口径）

| 项 | 值 |
|----|-----|
| 默认流速 | 游戏时间 = **30 倍**现实时间（1 现实分钟 = 30 游戏分钟） |
| 1 游戏日（24h 游戏时间） | 48 分钟现实（`DayCycleSpeedScale=1.0`） |
| 完整昼夜周期 | `48 ÷ DayCycleSpeedScale` 分钟现实 |
| 畸变（Abe） | 10 天季节循环，昼夜占比动态变化，但**时间系统与其他地图一致** |
| **游戏时间 30 天** | = 30×86400 = **2,592,000 世界秒**（世界秒差值判断，不受流速/倍率影响） |

---

## 3. 总体架构

```
┌─ 数据源（离线 JSON，主路径）─────────────────────┐
│ P:\私人共享\ASA\DinoData\<缩写>_cryo.json       │
│ P:\私人共享\ASA\DinoData\<缩写>_tamed.json       │
│ （Qsync 自动同步，前端 fetch 读取）               │
└──────────────────┬────────────────────────────┘
                   ▼
┌─ 数据层（浏览器内）─────────────────────────────┐
│ 服务器映射表 / tribes 跨服索引 / 容器索引         │
│ 记录归一化（cryo∪tamed 统一结构）                │
│ 世界秒差值引擎（30 游戏天窗口 + 有效性判定）      │
└──────────────────┬────────────────────────────┘
                   ▼
┌─ 应用层 ───────────────────────────────────────┐
│ URL 参数解析（?player=&dino=&days=）            │
│ 玩家→部落解析（跨服 members 匹配）              │
│ 30 天新增引擎 / 容器归属引擎 / 物种整合引擎      │
└──────────────────┬────────────────────────────┘
                   ▼
┌─ UI 层（改造现有 dino-import.html）─────────────┐
│ Tab ① 生物导入（ini，原功能保留）               │
│ Tab ② 数据浏览器（新增）                        │
└────────────────────────────────────────────────┘
```

> RCON 实时查询（DinoMut/ArkGetDino/ArkStatus/ArkTamedDinos）本期**仅作可选扩展**：浏览器无法直连 RCON，需后端代理，留待 Phase 4+。

---

## 4. 数据层设计

### 4.1 服务器映射表（内置常量，与 RCON 文档对齐）

```js
const SERVERS = [
  { abbr:'Isl', name:'孤岛',   cryo:'Isl_cryo.json',  tamed:'Isl_tamed.json' },
  { abbr:'Sco', name:'焦土',   cryo:'Sco_cryo.json',  tamed:'Sco_tamed.json' },
  // ... Cen 中心岛 / Abe 艾伯 / Ext 灭绝 / Ast 仙境 / Rag 拉格纳 / Val 瓦尔盖罗
  //     Los 迷失 / Gen 创世纪2
  // 缺 tamed 的服务器容错跳过
];
```

### 4.2 跨服 tribes 索引

```js
// 遍历所有服务器 cryo JSON 的 tribes 段
const tribeIndex = {
  // key: `${serverAbbr}:${tribeId}`
  'Sco:1589589881': { server:'Sco', tribeId:1589589881, name:'北美狗鱼',
                      ownerName:'板板', members:['板板', ...] }
};
```

### 4.3 记录归一化（cryo ∪ tamed 统一结构）

```js
{
  src: 'cryo' | 'tamed',          // 来源
  server: 'Sco',
  dinoId1, dinoId2, dinoClass,
  name, level, gender, babyAge,
  tribeId,                         // 龙所属部落
  statValues, statPoints, statMutations,  // 12 数组
  downloadedAtMs: 0,               // 下载进服时间（Unix 毫秒，fallback 用）
  worldSeconds: 0,                 // 下载时世界秒（主判断字段，需数据源提供）
  // cryo 独有：
  containerId, containerType, containerName, containerClass, containerTribe,
  // 归属部落（引擎计算后填充）：
  ownerTribeId: null
}
```

> ⚠️ 依赖数据源配合：JSON 顶层需提供 `worldSecondsNow`（文件生成时刻的世界秒），每条记录提供 `worldSeconds`（或由插件直接从 downloadedAtMs 换算输出）。

### 4.4 时间引擎：游戏时间 30 天（世界秒差值）

#### 核心原理：差值比较免疫跨服基准偏移

世界秒与 Unix 满足线性关系 `unixMs = worldSeconds×1000 + offset`，`offset` 每服务器独立（启动时刻+存档值不同）——这就是"对不齐"的根源。

但**差值比较天然抵消偏移**：

```
本服游戏时间经过 = 当前世界秒 − 记录世界秒
                 = (rec.worldSeconds + offset) + (now - rec) − (rec.worldSeconds + offset)
                 = 纯差值，与 offset 无关
```

→ 前端只需做同一服务器内的差值，**无需任何对齐换算**。

#### 判定规则

```
窗口内新增 ⟺  0 ≤ (file.worldSecondsNow − rec.worldSeconds) ≤ 30×86400
```

| 场景 | 处理 |
|------|------|
| 有 `worldSeconds` + `worldSecondsNow` | 差值判断（主路径，精确到游戏时间，不受 DayCycleSpeedScale 影响） |
| 差值 < 0（服务器回档/数据异常） | 视为无效，跳过（防回档误报） |
| 无世界秒（旧数据/字段缺失） | **fallback**：用 `downloadedAtMs`（Unix ms）按现实时间近似——`now − downloadedAtMs ≤ 现实 24h`（默认 30 倍流速下 ≈ 30 游戏天） |
| `downloadedAtMs < 2023-10-25` | ASE 脏数据，无效，显示为空 |
| 空球（dinoId1=0） | 无龙，直接过滤 |
| 系统单位（HelperBot/Train/Oasisaur） | 时间戳无意义，前端留空 |

> 时间常量：`const DAY30_WORLD_SEC = 30*24*3600`（2,592,000）、`const ASA_LAUNCH_MS = Date.UTC(2023,9,25)`

#### 数据源配合需求（写入方案）

| 项 | 要求 |
|----|------|
| JSON 顶层 | 新增 `worldSecondsNow`（生成文件时刻的世界秒） |
| 每条记录 | 新增 `worldSeconds`（该龙下载进服时的世界秒） |
| 实现方 | 插件 / 读档 exe（`ark_save_reader.exe`）读取 `DinoDownloadedAtTime` 原始世界秒直接输出；两者同源即同基准 |

### 4.5 畸变（Abe）特殊说明

> 用户实服观察：畸变「游戏天数」明显多于其他服，担心世界秒差值在畸变上不成立。本节论证与验证。

#### 4.5.1 结论：差值方案对畸变依然有效

ARK 时间模型（用户确认口径 + 官方换算）：

```
1 游戏日 = 86400 世界秒（恒定，与服务器无关）
游戏时间流速 = 30 × DayCycleSpeedScale 倍现实时间
```

- **1 游戏日恒等于 86400 世界秒**（世界秒即游戏时间秒），`DayCycleSpeedScale` 只改变「世界秒 vs 现实秒」的流速，**不改变「世界秒 vs 游戏时间」的比例**
- 因此「游戏时间 30 天 = 2,592,000 世界秒差值」在**任何服务器（含畸变）恒成立**
- 畸变游戏天数多（世界秒绝对值大）→ 只因畸变世界秒推进快（DayCycleSpeedScale 高）或开服早，**基准偏移与推进速率都不影响差值**（差值 = 游戏时间经过量）

#### 4.5.2 畸变季节机制不影响判断

- 畸变有 10 天季节循环，昼夜占比动态变化（白天/夜晚时长轮换）
- 昼夜相位变化只影响「现实时刻对应的游戏钟点」，**不影响世界秒差值**（季节循环仍是游戏时间的一部分，按世界秒自然累计）
- 前提：季节机制不改变「1 游戏日 = 86400 世界秒」的比例（ASA 官方实现下成立）

#### 4.5.3 实服验证方法（数据源输出 worldSecondsNow 后执行）

| 步骤 | 操作 | 预期 |
|------|------|------|
| 1 | 对比各服 `worldSecondsNow` 绝对值 | 畸变应明显更大（推进快/开服早），印证现象 |
| 2 | 现实时间间隔 Δt 后（如 1 现实小时）再采样各服 `worldSecondsNow` | 增量 = Δt×30×DayCycleSpeedScale；各服增量比例应等于其 DayCycleSpeedScale 之比 |
| 3 | 取畸变一条新下载龙，验证差值窗口 | `worldSecondsNow − rec.worldSeconds ≤ 2,592,000` 与实服「30 游戏天内」一致 |

> 若步骤 2/3 验证异常（畸变差值≠游戏时间），才需按 §4.5.4 特殊换算。

#### 4.5.4 备用：按现实时间换算（仅当差值验证异常时启用）

若实服证实畸变世界秒与游戏时间比例异常，前端按各服倍率换算窗口：

```
现实窗口(秒) = 30 游戏天 ÷ (30 × DayCycleSpeedScale)
= 2,592,000 ÷ (30 × DayCycleSpeedScale)
```

需各服务器 `DayCycleSpeedScale` 配置值（前端内置表，畸变单独一项）。**默认不启用**，以世界秒差值为准。

---

## 5. 四大能力详细设计

### 5.1 玩家名 URL 过滤（禁止显式配置）

- URL：`?player=板板`（UTF-8 URL 编码，如 `?player=%E6%9D%BF%E6%9D%BF`）
- 页面加载 `location.search` 解析 → `playerName`；**不写入任何配置文件/常量**
- 解析流程：
  1. 遍历所有服务器 `tribes` 段，收集 `members` 含玩家名的记录
  2. 得到 `{server, tribeId, tribeName}[]`（一玩家可多部落、多服务器，全部纳入）
  3. 若无 URL 参数 → 显示空态引导（提示在地址栏加 `?player=`），不加载数据
- 附加参数（可选）：`dino=`（物种筛选）、`days=`（时间窗，默认 30 游戏天）、`server=`（限定服务器，默认全选）

### 5.2 玩家部落「游戏时间 30 天」新增生物（tamed+cryo 整合）

- **部落范围**：5.1 解析出的全部 `{server, tribeId}` 集合
- **数据**：所有服务器 `cryopod[]` + `dinos[]`
- **判定**：
  - 每条记录 → `ownerTribeId`（见 5.3）∈ 部落集合，且满足 §4.4 时间引擎窗口（世界秒差值 ≤ 2,592,000；fallback 用 downloadedAtMs 现实 24h）
  - cryo 与 tamed **统一口径**，两者取并集展示
- **展示**：按服务器分组 → 每条显示 名称/等级/性别/来源(球内/放出)/容器名/下载进服时间（本地时间）；**组内按世界秒从最近到最旧排序**（fallback 用 `downloadedAtMs` 降序）
- **时间未知**记录：单独"时间未知"折叠区（置底），提示"旧球/宠物台/系统单位无下载时间戳，无法判断"

### 5.3 生物归属判定（容器部落 + 成员背包）

| 记录类型 | 归属部落（ownerTribeId） | 理由 |
|----------|------------------------|------|
| cryo（球内/宠物台） | **`containerTribe`**（容器所在部落） | 用户明确：按容器部落归属——龙可放别部落冰箱（代养） |
| cryo 且 `containerType='player'` | `containerTribe`（=背包玩家部落） | 部落成员背包里的球也算该部落 |
| tamed（放出） | `tribeId`（龙所属部落） | 无容器，按龙本身部落 |

- 展示归属标签：部落名（tribes 索引）+ 容器名（`containerName`）+ 容器类型（`containerType`/`containerClass` 映射中文）

### 5.4 跨服某物种整合列表（分服务器分容器）

- URL：`?player=板板&dino=Direbear_Character_BP_C`
- 流程：
  1. 5.1 解析玩家部落集合
  2. 全服务器 cryo+tamed 中 `dinoClass` 匹配（支持中文名映射：维护 `dinoClass ↔ 中文名` 小表或复用现有 icon_zh_map）
  3. 过滤 `ownerTribeId` ∈ 部落集合
- **分组树**：`服务器 → 容器（cryo 按 containerId+containerName；tamed 归"放出"组）→ 生物列表`
  - 同一容器多生物合并展示（宠物台多宠物共享 containerId 天然聚合）
- **每项**：名称/等级/性别/突变数/属性摘要（血/耐/负重/近战）/容器名/部落；**同容器内按世界秒从最近到最旧排序**（fallback 用 `downloadedAtMs` 降序；时间未知记录置底）

---

## 6. UI 改造设计

### 6.1 页面结构（改造现有 dino-import.html）

```
┌─────────────────────────────────────────┐
│ <h1> 🦖 ASA 生物工具        [导入] [浏览] │ ← Tab 切换
├─────────────────────────────────────────┤
│ Tab① 生物导入（现有功能 100% 保留）       │
│   ├─ 文件列表 / parseIni / solveLevels   │
│   ├─ 突变芯片 / Wikily 导入（原逻辑）     │
│   └─ 注：Wikily 导入按钮保留但标注"可选"  │
├─────────────────────────────────────────┤
│ Tab② 数据浏览器（新增）                  │
│   ├─ 顶部条：玩家名（URL 回填，只读显示） │
│   │          服务器多选 / 时间窗(days)    │
│   ├─ 面板 A：30 天新增生物（分服务器）    │
│   ├─ 面板 B：物种整合列表（分组树）       │
│   │          物种搜索框（中文/类名）      │
│   └─ 状态栏：数据源时间戳/加载状态/统计   │
└─────────────────────────────────────────┘
```

### 6.2 数据加载

- 页面加载后并行 `fetch` 各服务器 JSON（`Promise.all`），带失败容错（缺失服务器跳过并提示）
- 大文件（Ext_cryo 2MB）：加载后建立索引（tribeId→记录、dinoClass→记录、containerId→记录），渲染用懒加载/分页
- 数据源文件时间戳展示（`savedAt`），支持"重新加载"按钮

### 6.3 保留原功能红线

- 不动 `parseIni/solveLevels/calcStatValue/ensureSpeciesStats` 及导入链路核心逻辑
- 仅重构外壳（h1 标题、新增 Tab 容器），确保原 ini 导入流程零回归

---

## 7. 部署与数据读取（关键待确认）

### 7.1 现状
- 页面部署：`P:\wikily-import\dino-import.html`（NAS 映射盘）→ `wiim.whiterober.com/dino-import.html`
- 数据：`P:\私人共享\ASA\DinoData\*.json`（同 NAS，但**不在 wiim web 根内**）
- ⚠️ 本次验证 `wiim.whiterober.com` 返回 401（凭据/访问方式待确认）
- 🔒 RCON 密码属敏感信息（文档 §1.1）：前端**只走离线 JSON**，不接触 RCON 密码；如后续启用 RCON 实时（Phase 5），密码必须由后端代理持有

### 7.2 数据读取方案（三选一）

| 方案 | 做法 | 优劣 |
|------|------|------|
| **A（推荐）** | 把 8+2 个 JSON 同步/复制到 wiim web 根可访问目录（如 `P:\wikily-import\dino-data\`），前端 fetch 相对路径 | 与现有部署一致，最稳；需一次同步脚本（可并入 Qsync 或定时复制） |
| B | NAS web 配置虚拟目录（alias）指向 DinoData | 无需复制，但需改 NAS 配置 |
| C | 页面本地运行（`python -m http.server` 同目录），不依赖 wiim | 仅本机可用，失去 NAS 访问便利 |

> 推荐 A：在 `P:\wikily-import\` 下建 `dino-data\`，由脚本（或 Qsync 规则）把 `*_cryo.json`/`*_tamed.json` 复制过去；前端 `fetch('dino-data/Sco_cryo.json')`。

---

## 8. 风险与待确认清单

- [ ] **wiim web 根与认证**：401 原因（正确凭据/是否需登录态）；web 根是否 `P:\wikily-import`
- [ ] **DinoData 前端可达路径**：选 7.2 的 A/B/C
- [ ] **世界秒数据源配合**：需插件/读档端输出 `worldSecondsNow`（顶层）+ `worldSeconds`（每条记录）；未输出前 fallback 用 `downloadedAtMs` 现实 24h
- [ ] **downloadedAtMs 覆盖**：仅 v7 新格式球带此字段；v6 旧球/宠物台无 → 归"时间未知"
- [ ] tamed 缺 Gen/Los/Rag/Val：是否会有（前端已容错）
- [ ] RCON 实时刷新是否本期需要（ArkTamedDinos 触发 tamed 重写需后端代理，密码不落前端）
- [ ] 中文物种名映射：复用现有 `icon_zh_map.json` 还是新建 `dinoClass↔中文` 小表
- [ ] 属性值/突变展示格式：数组下标 ↔ 中文属性名（RCON 说明 §4）

---

## 9. 实施阶段

| 阶段 | 内容 | 验收 |
|------|------|------|
| **Phase 1** | 数据层：服务器映射/JSON 加载器/tribes 索引/记录归一化/世界秒差值引擎 + URL 玩家解析 | 控制台可列出玩家全部部落（跨服） |
| **Phase 2** | 30 天新增面板（tamed+cryo 整合 + 容器归属 + 世界秒差值） | 玩家游戏时间 30 天新增生物正确分服展示 |
| **Phase 3** | 物种整合列表（分组树：服务器→容器→生物） | 指定物种跨服分容器正确聚合 |
| **Phase 4** | UI 整合（Tab 改造保留 ini 导入）+ 部署（7.2 方案 A）+ 浏览器双端验证 | 原导入零回归 + 浏览模式全功能 |
| **Phase 5（可选）** | RCON 实时刷新（后端代理 ArkTamedDinos/DinoMut，密码服务端持有） | 数据手动刷新闭环 |
