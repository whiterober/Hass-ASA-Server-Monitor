# 前端独立化改造方案 — dino-import.html → ASA 生物数据浏览器

> 版本：v1.5 · 日期：2026-08-06
> 状态：方案（待确认后实施）
> 关联：插件 `TransferIdentityFixAPI` v0.3.0（RCON 13 命令 + tamed/cryo 双 JSON）
> 更新 v1.2：时间窗口改为「**游戏时间最新 30 天**」，基于**世界秒差值**实现，跨服基准偏移天然免疫
> 更新 v1.3：新增 §4.5 畸变（Abe）特殊说明
> 更新 v1.4：生物列表排序规则——按世界秒**从最近到最旧**
> 更新 v1.5：对齐接口文档 v0.3.0 时间戳定稿——四字段模型（`downloadedAtMs`/`packedAtWorldSec`/`downloadedAtWorldSec`/`tamedAtWorldSec`），世界秒差值**跨服有效**（用户确认），不可换算墙钟（实服验证）

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
| `<缩写>_tamed.json` | 动态（实服验证时仅 Isl 有最新，其余同步波动中） | 放出的龙 |

> 前端对缺失服务器必须容错跳过（数据随 Qsync 逐步补齐，tamed 文件为插件触发/周期性重写）。

### 2.2 时间字段（接口 v0.3.0 定稿，实服已验证）

**四字段模型**（不再统一单一字段）：

| 字段 | 所在数据 | 语义 | 是否可靠绝对时间 |
|------|---------|------|:---:|
| `downloadedAtMs` | **仅 cryo 球内**（v7 新格式球） | 下载进服时间（Unix 毫秒，custom data `[02][timestamp]`） | ✅ 唯一可靠（跨服可比、可格式化） |
| `packedAtWorldSec` | cryo 球内 + 宠物台 | 原服收球/上架时间（原始世界秒） | ❌ 世界秒，仅排序/同服差值 |
| `downloadedAtWorldSec` | tamed 放出龙 / ArkGetDino | 下载进服时间（原始世界秒） | ❌ 世界秒 |
| `tamedAtWorldSec` | tamed 放出龙 / ArkGetDino | 驯服/繁殖时间（原始世界秒，本地龙有值） | ❌ 世界秒 |

**关键定稿（实服验证）**：
- **世界秒不可换算墙钟**：各服世界时钟流速不同、基准因存档继承而异（本服从 ASE 继承，换算 epoch 从 2017-2020 都有）→ 世界秒**只做差值/排序**，不转 Unix、不格式化显示
- **世界秒差值跨服有效**（用户确认）：`1 游戏日 = 86400 世界秒`恒定，差值 = 游戏时间经过量，跨服基准差异在减法中抵消 → 可用于「游戏时间 30 天」窗口判断
- **球内/宠物台读不到驯服时间**（实服验证：Sco+Ext 1987 球 6 宠物台全部 tamed=0）→ 只有 tamed 放出龙有 `tamedAtWorldSec`
- **本地龙 vs 下载龙（tamed）**：下载龙 `downloadedAtWorldSec` 有值（`tamedAtWorldSec`=0）；本地驯养龙 `downloadedAtWorldSec`=0、`tamedAtWorldSec` 有值 → 前端优先 `downloadedAtWorldSec`，为 0 用 `tamedAtWorldSec`
- **ASE 脏数据阈值** `2023-10-25` 仅适用 `downloadedAtMs`（Unix 秒）；世界秒数值量级小（~2e8），不适用该阈值，直接差值/排序

### 2.3 ASA 时间系统速查（用户确认口径）

| 项 | 值 |
|----|-----|
| 默认流速 | 游戏时间 = **30 倍**现实时间（1 现实分钟 = 30 游戏分钟） |
| 1 游戏日（24h 游戏时间） | 48 分钟现实（`DayCycleSpeedScale=1.0`） |
| 完整昼夜周期 | `48 ÷ DayCycleSpeedScale` 分钟现实 |
| 畸变（Abe） | 10 天季节循环，昼夜占比动态变化，但**时间系统与其他地图一致** |
| **游戏时间 30 天** | = 30×86400 = **2,592,000 世界秒**（世界秒差值判断，跨服有效） |

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
│ 记录归一化（cryo∪tamed 统一结构，四字段时间）     │
│ 世界秒差值引擎（30 游戏天窗口，跨服有效）         │
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
  // 时间（归一化，各源取值规则见下）：
  sortWorldSec: 0,                 // 世界秒：排序 + 同服差值窗口（主字段）
  absMs: 0,                        // 可靠绝对时间：仅 cryo 球内 downloadedAtMs（Unix ms）
  srcWorld: '',                    // 世界秒来源: 'packed'|'downloaded'|'tamed'
  // cryo 独有：
  containerId, containerType, containerName, containerClass, containerTribe,
  // 归属部落（引擎计算后填充）：
  ownerTribeId: null
}
```

**各源归一化规则**：

| 来源 | `sortWorldSec` | `absMs` | `srcWorld` |
|------|---------------|---------|-----------|
| cryo 球内 | `packedAtWorldSec`（收球时间） | `downloadedAtMs` | `packed` |
| cryo 宠物台 | `packedAtWorldSec`（上架时间） | 0 | `packed` |
| tamed 放出 | `downloadedAtWorldSec \|\| tamedAtWorldSec`（下载优先，0 用驯服） | 0 | `downloaded`/`tamed` |

> ⚠️ 数据源缺口：cryo JSON 顶层**当前无 `worldSecondsNow`**（窗口差值需要"当前世界秒"），见 §4.4 数据源配合。

### 4.4 时间引擎：游戏时间 30 天（世界秒差值，跨服有效）

#### 核心原理：差值比较 = 游戏时间经过量（用户确认跨服有效）

- `1 游戏日 = 86400 世界秒` 恒定（世界秒即游戏时间秒），与服务器无关
- **同服差值** = 游戏时间经过量；跨服基准差异在减法中抵消 → 语义跨服一致
- 世界秒**不可换算墙钟**（实服验证 epoch 2017-2020 混乱）→ 前端**不做任何 Unix 换算**，只做差值

#### 判定规则

```
窗口内新增 ⟺  0 ≤ (file.worldSecondsNow − rec.sortWorldSec) ≤ 30×86400
```

| 场景 | 处理 |
|------|------|
| 有 `worldSecondsNow` + `sortWorldSec` | 差值判断（主路径，精确到游戏时间，跨服有效） |
| 差值 < 0（服务器回档/数据异常） | 视为无效，跳过（防回档误报） |
| 无 `worldSecondsNow`（数据源缺口） | **fallback**：仅 cryo 球内用 `absMs`（downloadedAtMs Unix）按现实时间近似——`now − absMs ≤ 现实 24h`（默认 30 倍流速 ≈ 30 游戏天）；tamed/宠物台无 absMs → 仅排序+标注 |
| `absMs < 2023-10-25` | ASE 脏数据，无效，显示为空 |
| 空球（dinoId1=0） | 无龙，直接过滤 |
| 系统单位（HelperBot/Train/Oasisaur） | 时间无意义，前端留空 |

> 时间常量：`const DAY30_WORLD_SEC = 30*24*3600`（2,592,000）、`const ASA_LAUNCH_MS = Date.UTC(2023,9,25)`

#### 数据源配合需求（写入方案）

| 项 | 要求 | 现状 |
|----|------|------|
| JSON 顶层 `worldSecondsNow`（文件生成时刻世界秒） | **必须**（窗口差值基准） | ❌ 当前缺失，需插件/读档端补充 |
| cryo 每条 `packedAtWorldSec` | 已输出 ✅ | |
| cryo 球内 `downloadedAtMs` | 已输出 ✅（仅 v7 球） | |
| tamed 每条 `downloadedAtWorldSec` / `tamedAtWorldSec` | 已输出 ✅ | |

### 4.5 畸变（Abe）特殊说明

> 用户实服观察：畸变「游戏天数」明显多于其他服。v1.5 基于接口定稿更新。

#### 4.5.1 结论：差值方案对畸变依然有效（跨服）

- `1 游戏日 = 86400 世界秒`恒定 → 「游戏时间 30 天 = 2,592,000 世界秒差值」在**任何服务器（含畸变）恒成立**（用户确认跨服有效）
- 畸变游戏天数多 = 世界秒绝对值大（推进快/开服早），**差值不受影响**
- 接口实服验证补充：世界秒**不可换算墙钟**（epoch 2017-2020）——但这是"转 Unix"不可靠，**不影响差值判断**

#### 4.5.2 畸变季节机制不影响判断

- 10 天季节循环只改变昼夜占比，不改变世界秒差值语义（季节仍是游戏时间的一部分）
- 前提：季节机制不改变「1 游戏日 = 86400 世界秒」比例（ASA 官方实现下成立）

#### 4.5.3 实服验证方法（数据源输出 worldSecondsNow 后执行）

| 步骤 | 操作 | 预期 |
|------|------|------|
| 1 | 对比各服 `worldSecondsNow` 绝对值 | 畸变应明显更大（推进快/开服早），印证现象 |
| 2 | 现实间隔 Δt 后采样各服 `worldSecondsNow` | 增量比例应等于各服世界秒流速之比；**同服内差值仍是游戏时间** |
| 3 | 取畸变一条新收球龙验证 | `worldSecondsNow − packedAtWorldSec ≤ 2,592,000` 与实服「30 游戏天内」一致 |

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
  - 每条记录 → `ownerTribeId`（见 5.3）∈ 部落集合，且满足 §4.4 时间引擎窗口
  - 主路径：同服世界秒差值（`worldSecondsNow − sortWorldSec ≤ 2,592,000`）
  - Fallback（无 `worldSecondsNow`）：仅球内 `absMs` ≤ 现实 24h；tamed/宠物台无 absMs → 归"时间未知"
  - cryo 与 tamed **统一口径**，两者取并集展示
- **展示**：按服务器分组 → 每条显示 名称/等级/性别/来源(球内/放出)/容器名/世界秒时间（相对排序）；**组内按世界秒从最近到最旧排序**
- **时间未知**记录：单独"时间未知"折叠区（置底），提示"无世界秒且无可靠绝对时间的旧数据"

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
- **每项**：名称/等级/性别/突变数/属性摘要（血/耐/负重/近战）/容器名/部落；**同容器内按世界秒（sortWorldSec）从最近到最旧排序**（fallback `absMs` 降序；时间未知记录置底）

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
- [ ] **`worldSecondsNow` 数据源缺口**：cryo 顶层当前无此字段（窗口差值基准），需插件/读档端补充；缺失时 fallback 仅球内 absMs 现实 24h
- [ ] **tamed 文件同步波动**：实服验证时仅 Isl 有最新 tamed，其余待 Qsync/触发重写
- [ ] **downloadedAtMs 覆盖**：仅 v7 新格式球带此字段（可靠绝对时间）；v6 旧球/宠物台只有世界秒 → 无 worldSecondsNow 时归"时间未知"
- [ ] 世界秒跨服有效性：用户已确认差值跨服有效；待 `worldSecondsNow` 输出后按 §4.5.3 实服验证
- [ ] 中文物种名映射：复用现有 `icon_zh_map.json` 还是新建 `dinoClass↔中文` 小表
- [ ] 属性值/突变展示格式：数组下标 ↔ 中文属性名（RCON 说明 §4）

---

## 9. 实施阶段

| 阶段 | 内容 | 验收 |
|------|------|------|
| **Phase 1** | 数据层：服务器映射/JSON 加载器/tribes 索引/记录归一化（四字段时间）/世界秒差值引擎 + URL 玩家解析 | 控制台可列出玩家全部部落（跨服） |
| **Phase 2** | 30 天新增面板（tamed+cryo 整合 + 容器归属 + 世界秒差值；fallback absMs） | 玩家游戏时间 30 天新增生物正确分服展示 |
| **Phase 3** | 物种整合列表（分组树：服务器→容器→生物） | 指定物种跨服分容器正确聚合 |
| **Phase 4** | UI 整合（Tab 改造保留 ini 导入）+ 部署（7.2 方案 A）+ 浏览器双端验证 | 原导入零回归 + 浏览模式全功能 |
| **Phase 5（可选）** | RCON 实时刷新（后端代理 ArkTamedDinos/DinoMut，密码服务端持有） | 数据手动刷新闭环 |
