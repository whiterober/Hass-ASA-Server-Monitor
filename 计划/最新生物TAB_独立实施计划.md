# 最新生物 TAB — 独立实施计划

> 版本：v1.3 · 日期：2026-08-06
> 目标文件：`dino-import-new.html`（**页面内嵌 hass**：部署到 HA `/config/www/`，`hass.whiterober.com/local/`）
> 关联：方案 `前端独立化改造方案_ASA生物数据浏览器.md` v1.5 · 接口 `RCON接口与JSON数据结构说明.md` v0.3.0
> 状态：计划（待确认后实施）
> 更新 v1.1：明确时间字段口径——tamed 基于驯服+下载时间（下载优先/0 用驯服）；球内/宠物架基于 `packedAtWorldSec`
> 更新 v1.2：~~后端代理部署确定为 NAS Docker~~（v1.3 已替换）
> 更新 v1.3：**改用 AppDaemon 直接调用 RCON**（复用 HA 现有 `send_rcon_command_sync`）+ **页面内嵌 hass**（全网可访问、与 HA 同源调端点）+ **NAS CORS 放行 hass 域**（数据跨域读取）

---

## 1. 目标

在 `dino-import.html` 新增「最新生物」TAB 页：

1. **地图（服务器）多选**：勾选要刷新的地图，默认全选 10 台
2. **刷新按钮**：触发多服 tamed 刷新，**串行排队**（确认 tamed 已更新再发下一个）+ **进度条**
3. **数据源**：NAS `P:\私人共享\ASA\DinoData`（页面跨域读取，NAS CORS 放行 hass 域）
4. **结果展示**：游戏内最近 30 天所有生物列表（tamed+cryo 整合），**全字段**，排序**从新到旧**
5. **玩家过滤**：URL `?player=板板` → 仅板板所在部落

---

## 2. 现状基础（已验证）

### 2.1 数据定位

- 数据在 NAS：`P:\私人共享\ASA\DinoData`（Web 可达需 **NAS Basic 认证** + 用户 Edge 已登录 NAS 会话可访问）
- 页面内嵌 hass 后，前端 fetch `https://wiim.whiterober.com/私人共享/ASA/DinoData/<缩写>_cryo.json` 为**跨域**请求 → 需 **NAS 配置 CORS 放行 `https://hass.whiterober.com`**（用户已确认此方案）
- 跨域 + Basic 认证：`authFetch` 内嵌凭据 URL 模式（现有 DINO_DATA 已用）

### 2.2 数据结构（接口 v0.3.0，实服已验证）

| 文件 | 内容 | 时间字段 |
|------|------|---------|
| `<缩写>_cryo.json` | `tribes{}` + `cryopod[]`（球内+宠物台） | `downloadedAtMs`（球内 Unix）+ `packedAtWorldSec`（收纳世界秒） |
| `<缩写>_tamed.json` | `dinos[]`（放出的龙） | `downloadedAtWorldSec` + `tamedAtWorldSec` |

- 世界秒差值跨服有效（用户确认）：`1 游戏日 = 86400 世界秒`，30 游戏天 = 2,592,000 世界秒
- 世界秒不可换算墙钟；球内 `downloadedAtMs` 是唯一可靠绝对时间

### 2.3 已知缺口

- ⚠️ cryo JSON 顶层**无 `worldSecondsNow`**（窗口差值基准）→ 缺失时 fallback 球内 absMs
- ⚠️ 浏览器**无法直连 RCON** → 由 HA AppDaemon 现有 RCON 能力中转（§5）

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

### 4.1 加载（跨域 + Basic）

```js
var DINO_JSON = 'https://whiterober:%401219Wu1219%40@wiim.whiterober.com/私人共享/ASA/DinoData/';
// 页面内嵌 hass 后为跨域请求；NAS 需返回 CORS 头放行 hass 域
async function loadAll(servers) {
  const results = await Promise.all(servers.map(s =>
    Promise.all([
      authFetch(DINO_JSON + s.cryo).then(r => r.json()).catch(() => null),
      authFetch(DINO_JSON + s.tamed).then(r => r.json()).catch(() => null)
    ])
  ));
}
```

### 4.2 记录归一化（时间口径 v1.1）

```js
{
  src: 'cryo'|'tamed', server,
  dinoId1, dinoId2, dinoClass, name, level, gender, babyAge, tribeId,
  statValues, statPoints, statMutations,      // 12 数组
  sortWorldSec: 0,   // tamed=downloadedAtWorldSec||tamedAtWorldSec；cryo=packedAtWorldSec
  srcWorld: '',      // 'downloaded'|'tamed'|'packed'
  absMs: 0,          // 仅球内 downloadedAtMs
  containerId, containerType, containerName, containerClass, containerTribe,
  ownerTribeId: null  // cryo=containerTribe；tamed=tribeId
}
```

### 4.3 部落索引 + 玩家解析

```js
// 遍历各服 cryo.tribes，members 含玩家名 → {server, tribeId, tribeName}
// URL: new URLSearchParams(location.search).get('player')
```

---

## 5. 刷新触发：AppDaemon RCON（v1.3 核心）

### 5.1 为什么走 AppDaemon

浏览器**无法直连 RCON**（TCP + 密码 + 协议）。HA 的 AppDaemon `asa_server_monitor_reliable.py` **已实现完整 RCON**：
- `send_rcon_command_sync(host, port, password, command)`（L12）
- 配置：`rcon_host` / `rcon_password` / `rcon_ports`（apps.yaml）
- 已用于 `GetInGameTime` 等

→ 直接复用，**无需 NAS Docker**（v1.2 方案废弃）。

### 5.2 AppDaemon 端：新增 HTTP 端点

在 `asa_server_monitor_reliable.py`（或新 app）用 AppDaemon HTTP API 注册端点：

| 端点 | 行为 | 返回 |
|------|------|------|
| `POST /api/asa/refresh-tamed?server=Sco` | 复用 `send_rcon_command_sync` 执行 `TransferIdentityFix.ArkTamedDinos` | `{ok, server, cooldown, error}` |

- 服务器端口从 `rcon_ports` 映射取（Isl 32320 ~ Gen 32329）
- 冷却（接口返回 `cooldown:true`）→ 等待 20s 重试一次
- **只做触发**，不做轮询（轮询由前端做，见 5.3）

### 5.3 前端排队状态机（触发后前端自轮询确认）

```
点击刷新
  ↓
[队列] 选中服务器列表（如 [Sco, Isl, Cen, ...]）
  ↓ 逐台串行（for..of）
[触发] POST https://hass.whiterober.com/api/asa/refresh-tamed?server=Sco
  ↓ ok（同源，页面已带 HA 认证）
[确认更新] 前端 fetch DINO_JSON + abbr + '_tamed.json' 轮询 savedAt 变化（间隔 1s，超时 30s）
  ↓
[完成本台] 进度 = 完成数/总数，进度条 +"正在刷新 Sco (3/8)"
  ↓ 全部完成
[读取+渲染] loadAll → 过滤 → 排序 → 渲染
```

| 状态 | 处理 |
|------|------|
| 触发成功 + 前端确认 savedAt 变化 | 进入下一台 |
| 触发返回 `cooldown` | 等待 20s 重试一次，仍冷却则标记"跳过(冷却中)" |
| 前端轮询超时（30s 无更新） | 标记"失败(无更新)"，**继续下一台** |
| AppDaemon 端点不可达 | 标记失败，继续 |

> 排队原则：**一次只触发一台**，前端确认 tamed 已更新（`savedAt` 变化）后才发下一台。

### 5.4 进度条 UI

```
[████████░░░░░░░░] 5/10 · 正在刷新 Sco（焦土）
```
- 每台完成更新一格；失败/跳过用不同颜色标注
- 全部完成后显示"✅ 已刷新 N 台，失败 M 台"

### 5.5 部署与认证（页面内嵌 hass）

**部署**：页面放 HA `/config/www/dino-import.html` → `https://hass.whiterober.com/local/dino-import.html?player=板板`（全网可访问）

**认证链**：
| 环节 | 认证 |
|------|------|
| 页面访问 | HA 认证（登录态；`/local/` 静态目录按 HA 配置） |
| 刷新端点 | **同源**（hass）→ 页面带 HA 登录态即可；AppDaemon 端点需与 HA 认证打通（实施时定：HA 代理 or AppDaemon API key） |
| 数据读取 | 跨域 NAS → `authFetch` 内嵌 Basic 凭据 + **NAS CORS 放行 hass 域** |

**NAS CORS 配置**（用户已确认）：NAS web（wiim）为 DinoData 请求返回：
```
Access-Control-Allow-Origin: https://hass.whiterober.com
Access-Control-Allow-Credentials: true
```

> ⚠️ token 安全：AppDaemon API key 若需前端携带，**禁止写死在前端 HTML**；优先走 HA 登录态同源认证（页面内嵌 hass 即为此目的）。

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

- [ ] **AppDaemon 端点**：在 `asa_server_monitor_reliable.py` 新增 HTTP 端点（复用 send_rcon_command_sync）；AppDaemon API 认证打通（HA 代理 or API key）
- [ ] **页面部署到 HA**：`dino-import.html` → `/config/www/`（`/local/` 访问）；原 wiim 部署可保留或弃用
- [ ] **NAS CORS**：NAS web 为 `wiim.whiterober.com/私人共享/...` 返回 `Access-Control-Allow-Origin: https://hass.whiterober.com`
- [ ] **`worldSecondsNow` 数据源补充**（cryo 顶层）：30 天窗口主路径依赖；缺失时 fallback 仅球内 absMs
- [ ] 前端 `DINO_JSON` 与刷新端点地址更新（页面内嵌 hass 后）
- [ ] tamed 文件同步稳定性（当前仅 Isl 有最新）
- [ ] HA `/local/` 访问权限（匿名 or 登录态）确认

---

## 9. 实施步骤

| 阶段 | 内容 | 验收 |
|------|------|------|
| **Step 1** | AppDaemon 端点：新增 HTTP 端点触发 RCON `ArkTamedDinos` + 认证打通 | curl POST → 返回 {ok}，ARK 侧 tamed 重写触发 |
| **Step 2** | 前端改造：DINO_JSON 指向跨域 NAS + 刷新改调 hass 端点 + 触发后前端自轮询 savedAt | 多服刷新进度正确、tamed 更新确认无误 |
| **Step 3** | NAS CORS 配置放行 hass 域 | 页面跨域 fetch DinoData 成功 |
| **Step 4** | 页面部署到 HA `/config/www/` + 浏览器验证（数据/刷新/渲染） | 原导入零回归 + 最新生物全流程可用 |
| **Step 5** | （数据源补 `worldSecondsNow` 后）30 天窗口主路径精确化 + 实服验证 | 30 天窗口跨服准确 |
