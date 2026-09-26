# 📋 前端 PID/EOSID 部落归属改造计划

> 日期：2026-08-11
> 目标：前端从「角色名判定归属」彻底改为「pid 判定归属、eosId 关联真人」。

> 🔴 **核心铁律（用户强制）**：**判定逻辑只允许用 `pid` / `eosId`**；`name` / `characterName` **只用于显示，绝不允许用于判定**。
> - 唯一例外：**登录定位**（从 hass 登录名找「我是谁」）允许用 `name` 匹配 `players.name` **一次**（仅初始化引导，定位到 eosId 后即切换为 pid/eosId 判定）
> - pid/eosId 仅内部判定与过滤，任何界面显示一律使用 `name` / `characterName`，绝不直接显示 pid/eosId

> 🔴 **报错铁律（用户强制）**：**不要兜底，数据不符合新结构一律报错**。
> - 依赖 pid/eosId/players 新结构的地方，若数据缺失/不符合 → **直接报错提示**（页面可见错误信息），**禁止静默回退到旧名字匹配**
> - 包括：rec 缺 `containerOwnerPid`、players 段缺失、`_schemaVer` 不符、显示反查不到角色等
> - 目的：让数据/结构问题**立刻暴露**，而不是悄悄降级掩盖

---

## 一、后端数据现状（已验证，2026-08-11）

### cryo 文件（`{serverId, arkPath, elapsedMs, stats, players, tribes, cryopod}`）
| 字段 | 结构 | 说明 |
|------|------|------|
| `players` | `[{pid, eosId, name, characterName}]`（list） | pid=角色唯一，eosId=玩家唯一，name=游戏平台账号名，characterName=游戏角色名 |
| `tribes` | `{tid: {name, ownerName, ownerPid, ownerEosId, members:[{name,pid,eosId}]}}` | 部落长/成员均带 pid |
| `cryopod` | 每条含 `containerOwnerPid` / `containerOwnerEosId` | 玩家背包球 |

### ✅ 已验证关键映射（2026-08-11）
| 维度 | 值 | 说明 |
|------|-----|------|
| hass 账号名（`auth/current_user`） | `whiter.rober` | 前端 `lbInitPlayer` 取到的值 |
| `players.name`（同人） | `whiter.rober` | **与 hass 账号名完全一致** → 可用登录名匹配 |
| `players.characterName` | `板板` | 游戏角色名，已填充（49/49） |
| `players.pid` | `288266681` | 角色唯一（Isl/Abe 跨服相同） |
| `players.eosId` | `00025a2b...` | 玩家唯一（跨服相同） |
| 部落 `ownerName` | `板板` | 部落显示名 = characterName |

> ⚠️ **字段语义澄清（重要，2026-08-11 实测）**：
> - `players.name` = **平台账号名**（如 Asdcent / whiter.rober）
> - `players.characterName` = **角色名**（如 满穗 / 板板）
> - `tribes.members[].name` / `tribes.ownerName` = **角色名**（与 players.characterName 对应，如 满穗）
> - `cryopod.playerName` = 角色名（如 满穗）
> → 前端显示：tribes/背包的 `name` 直接显示（已是角色名）；`players` 段角色显示用 `characterName`（回退 `name`）
> → 匹配：hass 登录名匹配 `players.name`（平台账号名）；角色名匹配 `players.characterName`

> ✅ **例证（2026-08-11 实测）**：
> - 满穗 → pid=421583285、name=`Asdcent`（平台账号）、char=`满穗`、eos=00023a7f...
> - 板板 → pid=288266681、name=`whiter.rober`、char=`板板`、eos=00025a2b...
> - 基纽特战队（tid=1912594779）：ownerName=歌星星(pid 580027822)，members 含 `{name:"满穗", pid:421583285, eosId:"00023a7f..."}`、`{name:"嘎巴丸", pid:233391766}`、`{name:"人类", pid:880859190}` 等 → **部落 members.name 存角色名**
> - characterName **重拉后已全部填充（49/49）**，此前为 0

> ⚠️ **pid 跨服一致性**：whiter.rober 在 Isl 和 Abe 的 pid 相同（288266681）→ **pid 全服统一**，角色切换 UI 无需按 `server+pid` 组合，全局 pid 判定即可。

> ⚠️ **服务器覆盖**：仅 Isl/Sco/Abe 有 players 段（其余返回 404，新 exe 未跑）；前端需容忍部分服务器无 players。

> ⚠️ **多角色现状实测**（2026-08-11）：Isl/Sco/Abe 三服合并后，同 eos 多 pid 数量 = 0，同 pid 跨 eos = 0；name 重复 4 例均为同一 eos+pid 跨服重复（非多角色）。设计仍按多角色就绪。

### tamed 文件（`{savedAt, count, dinos}`）
- **无 `players` 段**；dinos 只有 `tribeId`（放出生物按部落归属即可，不需要 pid）

### 关键点
- `players` 段只在 **cryo 文件** 中 → 前端跨服务器加载时需**合并各服务器 cryo 的 players**
- 角色 pid / eosId 均为**全服统一**（跨服务器一致）→ 按 eosId 合并，同一 eosId 下可挂多个角色 pid
- 前端当前 IndexedDB 缓存是旧结构，**需清缓存或加缓存版本号**避免旧数据先渲染

---

## 二、改造目标（3 项需求）

1. **HA 用户名 ↔ players.name 对应**：登录账号名 → 匹配 `players[].name` → 得 eosId
2. **页面可选 eos 旗下角色**：一个 eos 下多个角色（pid 内部判定，显示 `characterName`）
3. **按 pid 显示生物**：玩家背包 `containerOwnerPid === 选中角色 pid`；部落 `members[].pid` 含选中 pid

---

## 三、改造分 5 块

### ① 数据归一化（`lbLoad` / `addCryoRec`）
- **`addCryoRec`**：rec 增加透传 `containerOwnerPid`、`containerOwnerEosId`（当前代码只透传 `playerName`，新字段从原始 `p` 透传）——玩家背包归属判定的数据基础
- **`lbLoad` 汇总 players**：新增 `playersByEos = {}`，遍历各服务器 cryo 的 `players`，按 `eosId` 合并：
  ```js
  playersByEos[eosId] = { eosId, name, roles: { [pid]: characterName } }
  ```
  （同一 eosId 下多个 pid 角色合并；role 的 characterName 为空时回退 name）

> ⚠️ **同 eos 多角色设计（已覆盖）**：`roles` 是 pid→characterName 字典，天然支持「一个 eos 下多个角色」。
> 当前后端数据实测每个 eos 仅 1 个 pid（multiCount=0），但身份模型按多角色设计：
> - `LB.playerRoles` = `[{pid, characterName}]` 角色数组
> - 角色切换 UI 列出全部角色（显示 characterName），切换时改 `LB.curPid`
> - 归属判定均按当前 `LB.curPid`：背包 `containerOwnerPid===LB.curPid`、部落 `members[].pid` 含 `LB.curPid`
> - 一旦后端出现同 eos 多角色，前端结构不变，下拉自然多选项
- 结果写入 `data.players`；`lbCacheSet` / `lbCacheGet` 兼容新增字段（`data.players` 随缓存存取）
- **缓存版本落地**（具体实现）：
  - `lbLoad` 输出 `out._schemaVer = 2`（新结构版本号）
  - `lbCacheGet` 读取后校验：`data._schemaVer !== 2` 或 `!data.players` 或 rec 无 `containerOwnerPid` → 判旧缓存失效，丢弃并重拉
  - `lbView` 的内存缓存命中（`LB._cache`）同样校验 `_schemaVer`
  - **重拉后仍无 players / rec 仍缺 pid → 报错**（页面提示后端数据未更新），不做降级
- 🔴 **players 段完全缺失**（所有服务器 cryo 都无 players）→ 报错「后端数据未更新（缺 players 段）」

### ② 身份模型（核心）
> 🔴 **判定只用 pid/eosId**：以下状态全部基于 pid/eosId，不存 name/characterName 作为判定依据
- 新增状态：
  - `LB.playerEos` — 当前 eosId（玩家唯一）
  - `LB.playerRoles` — 该 eos 下角色列表 `[{pid}]`（**只存 pid**，characterName 仅渲染下拉时查表）
  - `LB.curPid` — 当前选中角色 pid（**内部唯一判定依据**）
- **角色解析链**：
  ```
  HA 登录名(LB.autoPlayer) → 匹配 playersByEos[].name（唯一允许用 name 的一次）→ 得 eosId
  → 该 eos 下所有角色 pid → 默认选中第一个（characterName 非空优先，仅用于排序/默认，不用于判定）
  ```
- **启动解析函数**：新增 `lbResolveIdentity()`（在 `lbInitPlayer` 拿到 autoPlayer 后调用）：
  - 数据就绪后，用 `LB.autoPlayer` 匹配 `playersByEos[].name` → 设 `LB.playerEos`、`LB.playerRoles`、`LB.curPid`
  - **匹配失败（登录名在 players 中找不到）→ 报错**（提示账号未关联游戏角色），不做游客降级
- **游客/未登录模式**：`LB._needLogin` 时按现有游客逻辑浏览（未登录本就不判定归属）；登录后但 `curPid` 无法解析 → 报错
- **URL 参数**：`?player=` 改为支持 `?pid=`（直接指定角色 pid）；未指定则走登录名匹配；改造后不再用 URL 传角色名
- **角色持久化**：`LB.curPid` 写入 `localStorage`（如 `lbCurPid`），下次启动直接恢复；无记录则默认选中第一个
- **角色切换后重渲染**：`lbSetCurPid(pid)` → 保存持久化 → `lbRenderView()` + `lbRenderBreedResult()` + 刷新 `lbBuildClassMap()`（物种浮窗计数）
- `lbPlayer()` 保留返回**当前角色 characterName**（仅供展示/兼容旧逻辑渲染，**不作判定**）；
  新增 `lbCurPid()` 返回 `LB.curPid`（供归属判定）
- **角色切换 UI**：筛选栏新增角色下拉（显示 `characterName`，pid 仅内部），
  切换后重渲染列表 + 繁育结果

### ③ 归属判定（全部改为 pid/eosId）
> 🔴 **只用 pid/eosId 判定**；name/characterName 不参与任何判断
| 场景 | 旧（名字） | 新（pid/eosId） |
|------|-----------|----------|
| 玩家背包 | `playerName === player` | `containerOwnerPid === LB.curPid` |
| 部落成员 | `members.indexOf(名字)` | `members[].pid` 含 `LB.curPid` |
| 部落长 | `ownerName === 名字` | `ownerPid === LB.curPid` |
| 同 eos 多角色 | — | `LB.playerEos` 分组，角色间按 pid 区分 |
| 数据缺失 | — | **报错**（rec 缺 pid / players 缺失 / 结构不符 → 页面报错，不静默回退） |

> 🔴 **数据结构变化隐患（必须处理）**：后端改造后 `tribes.members` 由 `[名字]` 变为 `[{name,pid,eosId}]` 对象数组！
> 前端以下代码会**对对象数组失效**，实施时必须同步改：
> - `lbPlayerTribes`（1770）：`t.members.indexOf(player)` → 需改为遍历 `t.members` 检查 `.pid === LB.curPid`
> - `lbOwnerName`（3243/3251）：`ts.members[0]` 直接返回 → 对象数组需取 `.name`
> - `lbOwnerName`（3243）：`if(ts.members && ts.members.length) return ts.members[0]` → `return ts.members[0].name`（或遍历）

### ③b 玩家背包归属路径（完整链路，2026-08-11 梳理）
> 玩家背包（`containerType==='player'`，PrimalInventory1）从前端实际代码梳理的 5 段链路：

| 环节 | 现状（名字判定） | 改造后（pid 判定） |
|------|----------------|-------------------|
| **① 数据透传** | `addCryoRec` 只存 `playerName:p.playerName` | 增加 `containerOwnerPid:p.containerOwnerPid`、`containerOwnerEosId:p.containerOwnerEosId`（rec 新字段） |
| **② 归属过滤** | `lbIsPlayerRec`：`containerType==='player'` → `playerName === player` | → `containerOwnerPid === LB.curPid`（rec 缺 pid → **报错**，不回退） |
| **③ 独立分组** | `lbRenderView`：`containerType==='player'` → `playerCarried[]` | 不变（分组依据 containerType），过滤已由②完成 |
| **④ Tab 计数** | 「玩家携带」Tab：`pcCnt=playerCarried.length` | 不变（playerCarried 已是过滤后集合） |
| **⑤ 显示** | `lbOwnerName`：`playerName` 直接显示 | 从 players 反查 `pid → characterName`（反查不到 → **报错**，不回退） |

> 关键：玩家背包 rec 的 `containerOwnerPid` 是**背包持有角色**的 pid；
> `lbIsMyRec`/`lbIsPlayerRec` 均需同步改（列表过滤 + 繁育归属共用同一判定）。

### ③c 全部调用点清单（实施改动清单，2026-08-11 全量 grep 梳理）
| 行号 | 函数 | 现状 | 改造 |
|------|------|------|------|
| 1512 | `lbPlayer()` | 返回名字（autoPlayer/游客/URL player） | 改造：返回当前角色 characterName（仅显示）；新增 `lbCurPid()` 返回 pid（判定） |
| 1764 | `lbPlayerTribes()` | `members.indexOf(player)` 名字匹配 | 遍历 `members[].pid === curPid` 构建部落集合 |
| 1777 | `lbIsPlayerRec()` | 背包 `playerName===player` | 背包 `containerOwnerPid===curPid` |
| 2321/2368/2372 | `lbView()` 列表过滤 | 名字 | pid |
| 2667 | 刷新后重渲染 | `lbPlayer()` 名字 | `lbCurPid()`/角色名 |
| 2772/2773/2776 | `lbBuildClassMap()` 物种浮窗计数 | 名字 | pid（**计划遗漏点，必须改**） |
| 3229 | `lbIsMyRec()` 繁育归属 | 名字 | pid |
| 3236/3243/3251 | `lbOwnerName()` 显示 | `members[0]` 对象数组 bug | 取 `.name`；玩家名反查 characterName |
| 3287/3288/3295 | `lbRenderBreedResult()` 繁育结果 | 名字 | pid |
| 3405/3408 | `extTag()` 显示 | 名字 | pid 判定 + characterName 显示 |
| 3413 | `extTag()` 皇冠 | `t.ownerName` | `t.ownerPid === LB.curPid` 判定 |
| 3420 | 繁育分组标题 | `lbPlayer()` 名字 | 显示当前角色 characterName |
| 2296 | `lbContainerLabel()` | player→「背包」 | 不变（无判定） |

### ④ 显示层（pid/eosId 一律不外露；name/characterName 仅此处使用）
- 玩家名：从 `players` 反查 `pid → characterName`——**反查不到 → 报错**（提示数据不一致），不做 name/playerName 回退
- 部落长：显示 `ownerName`（已是角色名，不显示 pid）
- extTag 皇冠：`ownerPid === LB.curPid` 判定，显示 `ownerName`
- **全局约束**：任何 `innerHTML`/`textContent` 不得出现 pid/eosId 原始值；
  调试工具（调试信息弹窗）如需展示，只显示 name/characterName

### ⑤ 旧数据兼容 & 报错策略（不做兜底）
- 🔴 **rec 缺 `containerOwnerPid`** → **报错**（页面提示数据异常），不做名字回退
- 🔴 **players 段缺失** → **报错**（提示后端数据未更新），不做旧字段回退
- 🔴 **显示反查不到角色**（pid 在 players 中无对应）→ **报错**（提示数据不一致）
- 🔴 **旧缓存**（`_schemaVer!==2`）→ 失效重拉；重拉后仍无新结构 → **报错**
- tamed 无 players → 部落归属不变（只按 tribeId + members pid）；tamed 无玩家背包（全是 released，无 containerType==='player'）
- 跨服务器：**pid 全服统一**（已验证 whiter.rober 在 Isl/Abe 同为 288266681）→ 直接用 `LB.curPid` 全局判定，无需 server+pid 组合
  - 玩家背包：`containerOwnerPid === LB.curPid`（同 pid 即同人）
  - 同一 eos 多角色（多 pid）时：角色切换即切换 `LB.curPid`
- **players 合并去重**：同一 eos 跨服合并时 `name`/`characterName` 取非空优先；`roles` 按 pid 字典自动去重

---

## 四、验证方案
1. **数据层**：加载后检查 `data.players` 结构、rec 含 `containerOwnerPid`、`data._schemaVer===2`
2. **归属**：板板（HA 用户名）→ 匹配 eos → 角色列表显示 characterName → 列表只显示该角色背包 + 所属部落生物
3. **切换角色**：选另一个角色 → 生物列表随之变化（重名角色不再互相串）；`localStorage.lbCurPid` 持久化生效
4. **显示审计**：grep 页面 HTML 输出，确认无 pid/eosId 数字泄漏（仅 name/characterName）；**重点**：`tribes.members` 对象数组不再出现 `[object Object]`
5. **旧缓存**：清 IndexedDB 后首次加载正常；旧缓存（无 `_schemaVer===2`）自动失效重拉
6. **游客模式**：未登录时按游客视角浏览，不报错；**登录后解析失败 → 报错**
7. **物种浮窗**：`lbBuildClassMap` 计数按 pid 过滤正确
8. **繁育**：`lbRenderBreedResult` 我的/外部分组按 pid 正确划分，分组标题显示角色 characterName
9. **报错场景**：
   - 模拟 rec 缺 `containerOwnerPid` → 页面报错（非静默）
   - 模拟 players 段缺失 → 页面报错
   - 模拟显示反查不到角色 → 页面报错
   - 所有报错提示包含可读原因（非原始 pid/eosId 泄漏）

---

## 五、涉及文件
| 文件 | 操作 |
|------|------|
| `b:\项目\Hass ASA Server Monitor\dino-import-new.html` | 唯一改动文件 |
| `.copilot\进度\007_开发_最新生物TAB数据链路.md` | 进度记录 |
| `bak\dino-import-new_backup_*.html` | 改前备份 |

---

## 六、决策（已确认）
- [x] 角色切换 UI：筛选栏角色下拉（显示 characterName）
- [x] 默认选中角色：characterName 非空优先
- [x] 跨服判定：pid 全服统一，全局 `LB.curPid` 判定（已验证）
- [x] 显示铁律：pid/eosId 不外露，一律 name/characterName

## 六b、实施步骤顺序（保证一次过）
按依赖顺序实施，每步验证后再进下一步：
1. **数据层**（①）：`addCryoRec` 透传 pid/eosId → `lbLoad` 合并 `playersByEos` → `data.players` + `_schemaVer=2` → 缓存版本校验（`lbCacheGet`/`lbView`）
2. **身份模型**（②）：新增 `LB.playerEos/playerRoles/curPid` → `lbResolveIdentity()` → `lbCurPid()` → 角色持久化 `localStorage.lbCurPid` → URL `?pid=` 支持
3. **归属判定核心**（③）：`lbPlayerTribes`（members 遍历 pid）→ `lbIsPlayerRec`/`lbIsMyRec`（背包 pid）→ `lbBuildClassMap`（计数）
4. **显示层**（④）：`lbOwnerName`（members[0].name 修复 + 玩家名反查）→ `extTag`（皇冠 pid 判定）→ `lbPlayer()` 返回 characterName → 繁育分组标题
5. **角色切换 UI**（②续）：筛选栏角色下拉 → `lbSetCurPid()` 重渲染（列表+繁育+物种浮窗计数）
6. **语法校验 + 部署 + 浏览器全量验证**（四、验证方案 1-8 项）

> 若第 1 步数据层验证失败（players 字段缺失/缓存未刷新），先解决数据再继续，不往下堆代码。

## 七、待用户确认
- [ ] 开始实施改造（备份 → 按六b 步骤 → 语法校验 → 部署 → 浏览器验证）
