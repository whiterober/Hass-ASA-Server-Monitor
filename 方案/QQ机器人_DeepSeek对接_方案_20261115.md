# QQ 机器人 × DeepSeek 对接「粑粑服搞事系统」方案分析

> 日期：2026-11-15
> 状态：📋 分析报告（未改任何代码、未部署）
> 硬约束：① 能力上限 = **管理者（level 2）**，主宰者（level 3）专属能力一律不开放 ② **机器人禁止部署在本机**

---

## 0. 结论摘要（TL;DR）

| 项 | 结论 |
|---|---|
| 可行性 | **高**。后端已是纯 HTTP API（约 92 个路由）且经 CF Tunnel 公网可达，机器人无需接触内网/本机 |
| 推荐接入方式 | **QQ 官方机器人开放平台 + Webhook 回调** → 托管在 **Cloudflare Workers**（零服务器、零本机依赖） |
| 推荐不采用 | OneBot/NapCat 协议（需长驻进程，且属非官方协议，有封号风险） |
| 权限落地 | 机器人使用**独立账号**（`accounts.json` 中 `role: "admin2"`），token 存 Workers Secret；`level 3` 接口在后端已硬编码拒绝，天然隔离 |
| 最大风险 | ① 自然语言误触发破坏性动作（`destroy` / `fullbackup` / `update`）② `rcon` 动作可下发任意控制台命令 ③ QQ 侧身份冒用 |
| 必须做 | **破坏性动作二次确认**（机器人回「确认码」，用户回复确认才执行）+ `rcon` 命令白名单 + 全量审计 |
| 主要待决策 | QQ 接入形态（群机器人 / 频道机器人 / 私聊）、是否允许 `rcon`、是否允许 `update`（更新服务器端） |

---

## 1. 需求拆解

| # | 需求原文 | 拆解为 |
|---|---|---|
| 1 | 做 QQ 机器人对接 DeepSeek | 需要一个**常驻接收 QQ 消息**的入口 + **LLM 意图解析**（DeepSeek function calling）+ **工具执行层**（调后端 API） |
| 2 | 调用本项目所有能力 | 后端全部 HTTP 接口（只读 + 写），**除 level 3** |
| 3 | 获取信息 | 生物/物品/wiki/地图 wiki/新闻/服务器状态/存档/任务进度/归档台账/天气/配置规则 等 |
| 4 | 执行命令 | `srvctl` 9 种动作（start/stop/kill/update/saveworld/savekill/fullbackup/destroy/rcon）、回档流程、模组部署、任务中止等 |
| 5 | 不允许本机部署 | 机器人**不能**跑在这台物理服务器上；也不能反向依赖本机常驻进程 |

---

## 2. 现状盘点（后端能力与鉴权）

### 2.1 鉴权模型（`dino_backend.py`）

| 等级 | 判定 | 说明 |
|---|---|---|
| **3** | 硬编码 `username == 'whiterober'` | 系统拥有者 / 主宰者 —— **本次不开放** |
| **2** | `accounts.json[用户].role == 'admin2'` | 二级管理员 —— 机器人账号取这一档 |
| 1 | 其余已登记账号 | 普通玩家 |
| 0 | 无 | 未登录 |

Token 机制（`_srvctl_make_token` / `_srvctl_check_token`）：

```
raw = base64url("{username}|{exp}")
sig = HMAC-SHA256(secret, "{username}|{exp}|sha256(pwd)[:10]")
token = raw + "." + sig
```

- `secret` 来自环境变量 `SRVCTL_SECRET` 或后端同目录 `srvctl_secret.txt`
- **改密码即吊销旧 token**（`pwdtag` 参与签名）—— 很适合机器人账号
- 统一守卫 `_srvctl_guard(handler, qs, need_token)`：写接口强制 token，且要求 `level >= 2`

### 2.2 能力分组（按权限等级）

| 等级 | 代表接口 | 机器人可用 |
|---|---|---|
| **公开只读** | `/api/status/<地图>`、`/api/mapwiki/*`、`/api/dino/tips`、`/api/dino/wikitext`、`/api/item/tips`、`/api/news/*`、`/api/bb_notes`、`/dino-data/*`、`/asa-data/*` | ✅ |
| **level 1** | `/api/plugins/borrow-list` | ✅ |
| **level 2**（需 token） | `/api/srvctl/action`、`/api/srvctl/rcon`、`/api/srvctl/startq`、`/api/srvctl/observe`、`/api/srvctl/arkcheck`、`/api/tasks/*`、`/api/update/*`、`/api/mods/*`、`/api/arkbackup/*`、`/api/cfg_rules/refresh`、`/api/zh/*`、`/api/pkg/clear` | ✅（受策略限制） |
| **level 3** | `/api/plugins/config`、`/api/plugins/config/locks`、`/api/plugins/config/reload`、`/api/admin/restart`、`/api/restart/enable`、`/api/restart/quiet/skip` | ❌ 禁止 |

### 2.3 可执行动作白名单（`SRVCTL_ACTIONS`）

```python
('start','stop','kill','update','saveworld','savekill','fullbackup','destroy','rcon')
```

补充机制（已实现，机器人直接受益）：
- `savekill` = 后端原子编排「存档 → 校验 → 终止」，比 `kill` 更安全
- `destroy` / `fullbackup` 走**异步 job**，有进度接口
- `kill` / `savekill` 有**全局串行闸**（同一时刻只放行一台，间隔 ≥5s）
- 回档期间该服**禁止任何外部动作**（后端已在入口拦截）

### 2.4 公网可达性

后端已通过 Cloudflare Tunnel 暴露为 `https://data.whiterober.ccwu.cc` ⇒ **机器人（无论在哪个云）都能直连**，无需本机做任何反向代理或端口映射。这是"不允许本机部署"能成立的关键前提。

> ⚠️ 调后端必须**带浏览器 UA**，否则被 Cloudflare Bot 拦成 403（`error code: 1010`）。

---

## 3. QQ 侧接入方案对比

| 方案 | 实现方式 | 是否需本机 | 需长驻进程 | 合规性 | 部署成本 | 结论 |
|---|---|---|---|---|---|---|
| **A. QQ 官方机器人开放平台（Webhook）** | `q.qq.com` 创建机器人 → 配置 HTTPS 回调 URL → 平台把消息 POST 过来 | ❌ 不需要 | ❌ 不需要（无状态函数） | ✅ 官方 | **CF Workers 免费额度足够** | ✅ **推荐** |
| B. QQ 官方机器人（WebSocket） | 机器人主动连平台网关 | ❌ 不需要 | ✅ **需要常驻进程** | ✅ 官方 | 云服务器（含 24h 常驻） | ⚠️ 次选 |
| C. OneBot v11（NapCat / Lagrange） | 模拟 QQ 客户端协议 | ❌ 不需要 | ✅ 需要常驻进程 | ❌ 非官方，封号风险 | 云服务器 + QQ 小号 | ❌ 不推荐 |
| D. 第三方 Bot SaaS 托管 | 交给平台托管 | ❌ | ❌ | 取决于平台 | 月费 | ⚠️ 需评估数据外泄 |

### 3.1 为什么推荐 A（Webhook + Workers）

```
QQ 用户 @机器人 发消息
        ↓  (QQ 开放平台回调)
Cloudflare Workers  /qq/webhook
        ↓
① 验签（Ed25519 / Bot Token）
② 去重 + 频控 + 身份映射（QQ openid → 允许的操作者）
③ 拼上下文 → 调 DeepSeek（带 tools schema）
        ↓  DeepSeek 返回 tool_calls
④ 工具执行层 → fetch https://data.whiterober.ccwu.cc/api/...
        ↓
⑤ 结果摘要 → 回推 QQ（被动回复 or 主动消息）
```

- **零常驻**：Workers 是请求驱动，天然满足"不允许本机部署"
- **会话状态**：多轮对话上下文放 **Durable Object**（每个 QQ 会话一个 DO）或 KV（TTL 30 分钟）
- **免费额度**：Workers 10 万请求/天、KV 10 万读/天、DO 亦有免费额度 —— 对私服群量级完全够

> QQ 官方平台限制需提前确认：① 个人开发者可创建的机器人类型 ② 群聊需「群主/管理员添加」③ 被动回复有 5 分钟窗口 ④ 主动消息有条数限制 ⑤ 富媒体/卡片消息格式限制

---

## 4. DeepSeek 工具调用设计

### 4.1 工具分层（关键设计）

把后端能力包成 **3 层工具**，而不是把 92 个接口直接丢给模型（会撑爆上下文且极易误调用）：

| 层 | 工具示例 | 是否需要确认 | 说明 |
|---|---|---|---|
| **L1 只读查询**（约 14 个） | `server_status`、`dino_info`、`item_info`、`map_wiki`、`news_latest`、`backup_list`、`task_progress`、`cfg_rules`、`weather`、`bb_notes` | ❌ 直接执行 | 无副作用，可直接给模型自由调用 |
| **L2 可控写操作**（3 个） | `server_action`（只允许 `saveworld`/`savekill`/`start`/`stop`）、`abort_task`、`backup_precheck` | ⚠️ 单次确认 | 先回执「将对 X 服执行 savekill，回复 `确认 A3F2`」 |
| **L3 高危动作**（默认关闭） | `server_action` 中的 `destroy`/`fullbackup`/`update`、`rcon` | 🚫 **默认禁用**，需白名单命令 | 建议一期完全不开 |

### 4.2 Function Calling 骨架

```jsonc
{
  "name": "server_action",
  "description": "对方舟服务器执行运维动作。破坏性动作必须先取得用户明确确认。",
  "parameters": {
    "type": "object",
    "properties": {
      "action":   { "type": "string", "enum": ["start","stop","saveworld","savekill"] },
      "servers":  { "type": "array", "items": { "type": "string",
                    "enum": ["Isl","Sco","Cen","Abe","Ext","Ast","Rag","Val","Bob","Los","Gen"] } },
      "reason":   { "type": "string", "description": "操作原因，写入审计日志" }
    },
    "required": ["action","servers","reason"]
  }
}
```

### 4.3 意图解析兜底

- **槽位缺失**（"重启一下"没说是哪台）→ 机器人先反问，不猜
- **多意图**（"把畸变存个档然后重启"）→ 拆成两次工具调用，**每步确认**
- **歧义守护**：模型返回的 `action`/`servers` 必须在白名单内，**由代码二次校验**（不信模型输出）
- **禁止模型直接拼 URL**：所有请求由固定函数构造，杜绝 SSRF / 越权路径

---

## 5. 权限与安全设计

### 5.1 身份与账号

| 项 | 设计 |
|---|---|
| 机器人后端账号 | 新建 `accounts.json` 条目，`role: "admin2"`，密码随机 32 位（**仅机器人侧持有**） |
| Token | 机器人启动时用 `username|exp` 换 token（或预生成长期 token 存 Workers Secret），**绝不回传 QQ 用户** |
| QQ 用户 → 后端身份 | 维护「QQ openid → 允许的操作人」白名单；非白名单用户**只能用 L1 只读** |
| 主宰者隔离 | level 3 接口后端已硬编码（`username == 'whiterober'`）⇒ 机器人账号**物理上够不着** |

### 5.2 破坏性动作四道闸

1. **工具白名单**：模型只能点名白名单内的 action（`destroy`/`rcon` 一期不暴露）
2. **代码二次校验**：执行前校验 `action ∈ 允许集`、`servers ⊆ 已知列表`、`level(机器人账号) >= 2`
3. **人工确认码**：生成 4 位随机码，用户必须在 **60 秒内**回复 `确认 XXXX` 才执行（存 DO/KV）
4. **串行与幂等**：同一服 60 秒内同一动作只执行一次（防刷/防重复 @）

### 5.3 审计与可观测

- 后端已有 `srvctl.log` / `admin.log`，机器人再记一份：`时间 | QQ openid | 昵称 | 工具 | 参数 | 结果 | traceId`
- 每次操作回复里带 `traceId`，出问题可按号对账
- 每日汇总「机器人今天做了哪些写操作」推给服主

### 5.4 其他风控

| 风险 | 对策 |
|---|---|
| 提示词注入（用户在群里让模型"忽略上面的指令"） | 系统提示固定 + 工具参数代码校验 + 写操作永远要人确认 |
| QQ 侧伪造回调 | 验签（平台签名）+ 校验 `appid`，非法直接 401 |
| 刷接口打爆后端 | Workers 侧按 openid 限流（如 20 次/分钟）+ 后端自身 RCON 串行队列 |
| 敏感信息外泄（端口/RCON 密码/存档路径） | 只读工具**裁剪字段**，不返回 `profile_ports`、`rcon_password`、文件系统路径 |
| 后端被公网扫描 | 现有 Cloudflare + Tunnel 已隐藏源站；机器人只是又一个普通客户端 |

---

## 6. 托管架构（满足"不允许本机"）

```
┌──────────────┐   Webhook    ┌───────────────────────────┐
│ QQ 开放平台   │ ───────────▶ │ Cloudflare Workers        │
└──────────────┘              │  /qq/webhook              │
        ▲                     │  ├─ 验签/限流/去重          │
        │ 被动回复/主动消息      │  ├─ Durable Object 会话     │
        └─────────────────────│  ├─ DeepSeek API (tools)   │
                              │  └─ 工具执行层              │
                              └──────────┬────────────────┘
                                         │ HTTPS + 浏览器 UA
                                         ▼
                          https://data.whiterober.ccwu.cc
                          （CF Tunnel → 物理服务器 dino_backend.py）
```

- **Workers**：免费额度 10 万 req/天，本场景（私服群）远不会打满
- **Durable Object**：每个 QQ 会话一个，存多轮上下文 + 待确认动作 + 30 分钟 TTL
- **KV**：存「QQ openid → 后端账号」映射、动作确认码
- **Secrets**：`DEEPSEEK_API_KEY`、`BOT_APPID`、`BOT_SECRET`、`DINO_SRVCTL_TOKEN`
- 本机**零新增进程、零端口开放**

备选（若不接受 CF）：阿里云函数计算 / 腾讯云 SCF + API 网关，同样是无状态托管，但需自行处理回调 URL 与证书。

---

## 7. 成本估算（口径：AI 动手时间 + 外部等待）

| 项 | 说明 | 量级 |
|---|---|---|
| DeepSeek API | 按 token 计费，一次问答约 2k~6k 输入（工具 schema+上下文）+ 数百输出 | 每天 200 条对话 ≈ 几毛钱（以官网价为准） |
| Cloudflare Workers | 免费额度 10 万 req/天 | 0 元 |
| QQ 官方机器人 | 平台免费（部分能力需审核） | 0 元 |
| **我动手写代码** | 工具层 + 意图层 + 确认流 + 审计 ≈ 1200~1800 行 TS/JS | **约 2~3 小时**动手，分 3 轮交付 |
| 外部等待 | QQ 机器人审核（1~3 工作日）、CF 部署（分钟级） | 主要瓶颈在平台审核 |

> 不用"人日"估算：实际是 AI 写码时间 + 平台审核等待。

---

## 8. 分阶段实施计划

| 阶段 | 内容 | 产出 | 风险 |
|---|---|---|---|
| **P0 只读问答** | Workers + 验签 + DeepSeek + 3 个只读工具（服务器状态 / 生物查询 / 最新补丁） | 群里能问「畸变现在几个人」「霸王龙怎么驯」 | 无副作用，可放心跑 |
| **P1 全量只读** | 补齐 14 个只读工具（wiki/物品/回档列表/任务进度/配置规则/天气/笔记） | 日常答疑全自动 | 需字段裁剪防泄密 |
| **P2 写操作 + 确认** | `saveworld`/`savekill`/`start`/`stop` + 确认码 + 审计 + QQ 身份白名单 | 群里能喊「把核心岛存档重启」 | 需四道闸齐全才可开 |
| **P3 高危/多轮** | `update`/`destroy`/`fullbackup`（可选）、多轮上下文、日报推送 | 运维全托管 | 建议长期只对 1~2 个 openid 开放 |

---

## 9. 待决策问题（需要你拍板）

1. **QQ 接入形态**：群机器人（群里 @ 触发）/ 频道机器人 / 私聊单聊？（三者平台权限与消息限制不同）
2. **谁来用**：只有你 + 指定管理员，还是群里所有人可只读查询？
3. **是否开放 `update`（更新服务器端游戏版本）**：这条会触发整队重启，风险最高
4. **是否开放 `rcon`**：如果开，需要定命令白名单（例如只允许 `ListPlayers`/`GetServerInfo`/`Broadcast`）
5. **确认方式**：回复 4 位确认码（推荐，零 UI 依赖）/ 还是只允许私聊操作（群里不给破坏性动作）
6. **是否接受 Cloudflare Workers** 作为唯一托管（若公司/个人有云服务器，也可换成云函数）
7. **是否要日报/告警推送**（每天 20:00 推服务器状态、存档成功/失败、任务进度）

---

## 10. 风险登记

| 风险 | 等级 | 缓解 |
|---|---|---|
| 自然语言误触发 `stop`/`kill` | 高 | 破坏性动作永不自动执行，必须确认码 + 代码白名单 |
| 机器人账号权限过宽（admin2 可 `destroy`） | 高 | 工具层不暴露 → 即使模型点名也执行不了 |
| QQ 开放平台审核被拒 | 中 | 先做 P0 用测试机器人验证；被拒则退到「云函数 + OneBot」备选 |
| DeepSeek 幻觉编造服务器数据 | 中 | 所有事实必须来自工具返回，系统提示禁止自行编造；回答里带数据时间戳 |
| 提示词注入 | 中 | 工具参数代码校验 + 写操作人工确认 |
| 成本超预期（群内刷屏） | 低 | openid 级限流 + 单日配额 |
| 平台消息限制（被动回复 5 分钟窗口） | 低 | 长任务改为「先回执，完成后主动消息」 |

---

## 11. 与现有项目档案的关系

- 后端能力与权限判定：`独立后端/dino_backend.py`（`_role_level` / `_srvctl_guard` / `SRVCTL_ACTIONS`）
- 前端调用样例（可作为工具层参数参考）：`app_core.js` 的 `lbSrvCtl*` 系列
- 部署与缓存铁律：`tmp/_deploy_cf.py`、`tmp/_headers`
- 后端重启授权：`POST /api/admin/restart` 属 **level 3** ⇒ 机器人**不可用**（符合本次要求）

---

（报告结束；未产生任何代码改动或部署动作）
