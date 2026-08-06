# 最新生物 TAB — 独立实施计划

> 版本：v1.2 · 日期：2026-08-06
> 目标文件：`dino-import-new.html`（部署 `P:\wikily-import\dino-import.html`）
> 关联：方案 `前端独立化改造方案_ASA生物数据浏览器.md` v1.5 · 接口 `RCON接口与JSON数据结构说明.md` v0.3.0
> 状态：计划（待确认后实施）
> 更新 v1.1：明确时间字段口径——tamed 基于驯服+下载时间（下载优先/0 用驯服）；球内/宠物架基于 `packedAtWorldSec`
> 更新 v1.2：后端代理部署确定为 **NAS Docker/Container Station**（读本地 DinoData + 出网 RCON + QNAP 反向代理同域 /api）

---

## 1. 目标

在 `dino-import.html` 新增「最新生物」TAB 页：

1. **地图（服务器）多选**：勾选要刷新的地图，默认全选 10 台
2. **刷新按钮**：触发多服 tamed 刷新，**串行排队**（确认 tamed 已更新再发下一个）+ **进度条**
3. **数据源**：`P:\私人共享\ASA\DinoData`（NAS，与页面同区域，同 ini 定位方式）
4. **结果展示**：游戏内最近 30 天所有生物列表（tamed+cryo 整合），**全字段**，排序**从新到旧**
5. **玩家过滤**：URL `?player=板板` → 仅板板所在部落

---

## 2. 现状基础（已验证）

### 2.1 数据定位（复用现有 ini 模式，L427-429）

现有前端数据定位逻辑：

```js
var DINO_DATA = (window.location.hostname === 'wiim.whiterober.com')
    ? 'https://whiterober:%401219Wu1219%40@wiim.whiterober.com/私人共享/ASA/DinoExports/'
    : '../私人共享/ASA/DinoExports/';
```

→ **wiim.whiterober.com web 根 = NAS 根 `P:\`**，`私人共享/ASA/` 可直接访问（HTTP Basic 认证，`authFetch` 已处理嵌入式凭据）。

**结论**：DinoData 同模式定位即可，**无需复制到 web 根**：

```js
var DINO_JSON = (window.location.hostname === 'wiim.whiterober.com')
    ? 'https://whiterober:%401219Wu1219%40@wiim.whiterober.com/私人共享/ASA/DinoData/'
    : '../私人共享/ASA/DinoData/';
```

### 2.2 数据结构（接口 v0.3.0，实服已验证）

| 文件 | 内容 | 时间字段 |
|------|------|---------|
| `<缩写>_cryo.json` | `tribes{}` + `cryopod[]`（球内+宠物台） | `downloadedAtMs`（球内 Unix）+ `packedAtWorldSec`（收纳世界秒） |
| `<缩写>_tamed.json` | `dinos[]`（放出的龙） | `downloadedAtWorldSec` + `tamedAtWorldSec` |

- 世界秒差值跨服有效（用户确认）：`1 游戏日 = 86400 世界秒`，30 游戏天 = 2,592,000 世界秒
- 世界秒不可换算墙钟；球内 `downloadedAtMs` 是唯一可靠绝对时间

### 2.3 已知缺口

- ⚠️ cryo JSON 顶层**无 `worldSecondsNow`**（窗口差值基准）→ 见 §7 前置
- ⚠️ 触发 tamed 需 RCON，浏览器无法直连 → 需后端代理（§5）

---

## 3. TAB 结构

```
┌─────────────────────────────────────────────┐
│ <h1> 🦖 ASA 生物工具        [导入] [最新生物] │ ← Tab 切换（新增）
├─────────────────────────────────────────────┤
│ Tab① 生物导入（现有功能 100% 保留）           │
├─────────────────────────────────────────────┤
│ Tab② 最新生物（新增）                        │
│   ├─ 顶部工具条                              │
│   │   ├─ 玩家：URL 回填显示（只读）          │
│   │   ├─ 地图多选：□孤岛 □焦土 ... □全选    │
│   │   └─ [🔄 刷新并查看]                    │
│   ├─ 刷新进度条（多服排队进度）              │
│   ├─ 生物列表（30 天窗口，全字段，新→旧）    │
│   └─ 状态栏（数据源时间戳/统计/时间未知数）  │
└─────────────────────────────────────────────┘
```

---

## 4. 数据读取

### 4.1 加载

```js
// 选中服务器集合
async function loadAll(servers) {
  const results = await Promise.all(servers.map(s =>
    Promise.all([
      authFetch(DINO_JSON + s.cryo).then(r => r.json()).catch(() => null),
      authFetch(DINO_JSON + s.tamed).then(r => r.json()).catch(() => null)
    ])
  ));
  // 缺失文件 → 容错跳过并提示
}
```

### 4.2 记录归一化（复用方案 §4.3）

```js
{
  src: 'cryo'|'tamed', server,
  dinoId1, dinoId2, dinoClass, name, level, gender, babyAge, tribeId,
  statValues, statPoints, statMutations,      // 12 数组
  sortWorldSec: 0,   // 时间口径见下表
  srcWorld: '',      // 'tamed'|'downloaded'|'packed'（时间来源标签）
  absMs: 0,          // 仅球内 downloadedAtMs
  containerId, containerType, containerName, containerClass, containerTribe,
  ownerTribeId: null
}
```

**⏱ 时间字段口径（用户确认）**：

| 来源 | `sortWorldSec` 取值 | `srcWorld` | 说明 |
|------|--------------------|-----------|------|
| **tamed（放出龙）** | `downloadedAtWorldSec`（下载时间，**优先**）；为 0 时用 `tamedAtWorldSec`（驯服时间） | `downloaded` / `tamed` | 跨服下载龙=下载时间；本地驯养/繁殖龙（未下载过）下载为哨兵 0 → 用驯服时间 |
| **球内（cryo）** | `packedAtWorldSec`（收球时间） | `packed` | 龙被装入冷冻球的时间 |
| **宠物架（cryo stand）** | `packedAtWorldSec`（上架时间） | `packed` | 宠物架上架时间 |

> 世界秒均不可换算墙钟；`absMs`（球内 `downloadedAtMs`）为唯一可靠绝对时间（显示格式化用）。

### 4.3 部落索引 + 玩家解析

```js
// 遍历各服 cryo.tribes，members 含玩家名 → {server, tribeId, tribeName}
// URL: new URLSearchParams(location.search).get('player')
```

---

## 5. RCON 刷新排队机制（核心）

### 5.1 为什么需要后端代理

浏览器**无法直连 RCON**（TCP + 密码 + 协议）。触发 `TransferIdentityFix.ArkTamedDinos` 必须经后端 HTTP 代理，密码由代理持有（不落前端）。

### 5.2 后端代理接口

| 接口 | 说明 |
|------|------|
| `POST /api/refresh-tamed?server=Sco` | ① RCON `ArkTamedDinos` 触发 ② 记录旧 `savedAt` ③ **轮询** `DinoData/Sco_tamed.json` 直到 `savedAt` 变化（超时 30s）④ 返回 `{ok, server, updated, savedAt, cooldown}` |

代理职责：
- 持有 RCON 密码（`1219wu1219`，仅服务端）
- 连接 `work.whiterober.cn:<port>`（各服端口 32320-32329）
- 轮询判断"已更新"：对比触发前后 `savedAt`（或文件 mtime/大小）
- 20 秒冷却返回 `cooldown`（接口已定义）→ 代理等待冷却后重试一次

### 5.3 前端排队状态机

```
点击刷新
  ↓
[队列] 选中服务器列表（如 [Sco, Isl, Cen, ...]）
  ↓ 逐台串行（for..of）
[触发] POST /api/refresh-tamed?server=Sco
  ↓ ok
[确认更新] 后端已轮询确认 savedAt 变化
  ↓
[完成本台] 进度 = 完成数/总数，进度条 +"正在刷新 Sco (3/8)"
  ↓ 全部完成
[读取+渲染] loadAll → 过滤 → 排序 → 渲染
```

| 状态 | 处理 |
|------|------|
| 触发成功 + 更新确认 | 进入下一台 |
| 触发返回 `cooldown` | 等待 20s 重试一次，仍冷却则标记"跳过(冷却中)" |
| 轮询超时（30s 无更新） | 标记"失败(无更新)"，**继续下一台**（不阻塞） |
| 服务器 RCON 连不上 | 标记失败，继续 |

> 排队原则：**一次只触发一台**，确认 tamed 已更新（`savedAt` 变化）后才发下一台，避免多服并发写文件冲突。

### 5.4 进度条 UI

```
[████████░░░░░░░░] 5/10 · 正在刷新 Sco（焦土）
```
- 每台完成更新一格；失败/跳过用不同颜色标注
- 全部完成后显示"✅ 已刷新 N 台，失败 M 台"

### 5.5 代理部署：NAS Docker/Container Station（用户确认）

> ✅ 已确定：代理跑在 **NAS 的 Docker（QNAP Container Station）**，与前端/数据同 NAS。

**架构**：

```
前端 dino-import.html（wiim.whiterober.com，https）
        │ fetch('/api/refresh-tamed?server=Sco')   ← 同域同 https，无 mixed content
        ▼
QNAP 反向代理 / Application Portal（https）
        │ 转发 /api/* → Docker 容器 HTTP 端口
        ▼
NAS Docker 容器（Node.js / Python 代理服务）
        ├─ 读本地 DinoData（卷挂载）→ 轮询 tamed.json savedAt
        └─ 出网 RCON → work.whiterober.cn:3232x（ArkTamedDinos 触发）
```

**容器设计**：

| 项 | 设计 |
|----|------|
| 镜像 | Node 20-alpine 或 Python 3.12-slim |
| 卷挂载 | NAS 本地 DinoData 目录（如 `/share/私人共享/ASA/DinoData`）→ 容器内 `/data` |
| 环境变量 | `RCON_HOST=work.whiterober.cn`、`RCON_PASSWORD`（仅容器内，不落前端）、各服端口表 |
| 端口 | 容器内监听 8080；**不直接对外暴露**，由 QNAP 反向代理转发 |
| 对外路径 | `https://wiim.whiterober.com/api/refresh-tamed?server=Sco`（QNAP Application Portal / 反向代理将 `/api` 转发到容器 8080） |

**网络要求（实施时验证）**：
- NAS → `work.whiterober.cn:32320-32329` 出网可达（RCON TCP）
- QNAP Container Station 反向代理可用（或 QNAP 自带 Application Portal 规则）

**RCON 密码安全**：密码只存在 NAS 容器环境变量中，前端代码/日志零接触。

> ⚠️ **mixed content 规避（关键）**：前端是 https，若直接 fetch Docker 的 http 端口会被浏览器拦截。必须经 QNAP 反向代理把 `/api/` 挂到 wiim 同域（https），前端用相对路径 `fetch('/api/refresh-tamed?...')`。

---

## 6. 30 天窗口 + 过滤 + 排序

### 6.1 窗口判定（游戏内最近 30 天）

```
窗口内 ⟺  0 ≤ (file.worldSecondsNow − rec.sortWorldSec) ≤ 2,592,000
```

> `sortWorldSec` 按 §4.2 时间口径：tamed=下载时间（0 用驯服时间）；球内/宠物架=`packedAtWorldSec`。

| 场景 | 处理 |
|------|------|
| 有 `worldSecondsNow`（数据源补上后） | 世界秒差值（主路径，跨服有效） |
| 无 `worldSecondsNow` | fallback：仅球内 `absMs` ≤ 现实 24h；tamed/宠物台 → 归"时间未知"（不排除，单独标注） |
| 差值 < 0 | 回档/异常，跳过 |
| `absMs < 2023-10-25` | ASE 脏数据，无效 |
| 空球（dinoId1=0） | 直接过滤 |

### 6.2 玩家过滤

- URL `?player=板板` → 跨服 `tribes.members` 匹配 → 部落集合 `{server, tribeId}`
- 生物 `ownerTribeId`（容器部落 / 龙部落）∈ 部落集合 → 保留
- 无 URL 参数 → 空态引导

### 6.3 排序

- 主：`sortWorldSec` 降序（新→旧）
- fallback：`absMs` 降序
- 时间未知置底

---

## 7. 全字段展示

每条生物卡片/行展示（tamed 与 cryo 字段并集）：

| 分组 | 字段 |
|------|------|
| 基本信息 | 名称、`dinoClass`（+中文映射）、等级、性别、`babyAge`/`isBaby`、来源（球内/宠物台/放出） |
| 归属 | 所属部落（tribes 索引）、容器名、容器类型（中文）、容器部落、`containerClass` |
| 属性（12） | `statValues`/`statPoints`/`statMutations`（health~craftingSpeed 中文） |
| 突变 | `randomMutationsMale/Female`、`ancestors`（世代/名字） |
| 其它 | `colors`、`saddle`、`dinoId1_dinoId2`、`cryoVersion` |
| 时间 | `sortWorldSec`（相对排序显示）+ 来源标签 `srcWorld`（`下载`/`驯服`/`收球`/`上架`）、`absMs`（球内可格式化显示） |

> 复用现有 `icon_zh_map.json`（ZH_MAP）+ 12 stat 中文表（接口 §4）。

---

## 8. 前置依赖与待确认

- [ ] **`worldSecondsNow` 数据源补充**（cryo 顶层）：30 天窗口主路径依赖；缺失时 fallback 仅球内 absMs
- [ ] **NAS 代理部署（§5.5）**：Docker 容器构建 + QNAP 反向代理 `/api` → 容器 8080
- [ ] **NAS 出网 RCON 可达性**：NAS → `work.whiterober.cn:32320-32329`（实施时验证）
- [ ] 容器卷挂载 DinoData 的 NAS 本地路径确认（`/share/私人共享/ASA/DinoData`）
- [ ] RCON 密码仅存容器环境变量（不落前端/日志）
- [ ] tamed 文件同步稳定性（当前仅 Isl 有最新）
- [ ] wiim 认证：现有 `authFetch` 嵌入式凭据模式复用（ini 已工作正常）

---

## 9. 实施步骤

| 阶段 | 内容 | 验收 |
|------|------|------|
| **Step 1** | 后端代理：RCON 触发 + savedAt 轮询确认 + HTTP 接口 | 单服 curl 触发 → tamed.json savedAt 变化 → 返回 ok |
| **Step 2** | 前端数据层：DINO_JSON 定位 + loadAll + 归一化 + 部落索引 + URL 玩家解析 | 控制台列出板板全部部落与生物数 |
| **Step 3** | 刷新排队：多选地图 + 刷新按钮 + 串行排队状态机 + 进度条 | 多服刷新进度正确、tamed 更新确认无误 |
| **Step 4** | 30 天窗口 + 过滤 + 排序 + 全字段渲染 | 板板部落 30 天生物列表新→旧、字段齐全 |
| **Step 5** | UI 整合（Tab 切换）+ 部署 + 浏览器双端验证 | 原导入零回归 + 最新生物全流程可用 |
