# 实时追踪野生龙接口（TrackDino）前端对接说明

> 日期：2026-08-25 ｜ 项目：TransferIdentityFixAPI（纯服务端 ASA API 插件）
> 适用：前端对接"实时追踪某条龙并在地图上显示追踪标记"能力 ｜ 基于当前实装（0.5s 定位刷新 + TeamPing Track 标记）
> 配合：野生龙枚举用 `查野生龙接口_WildDinos_前端对接说明.md`（先查 id → 再追踪）

---

## 1. 概述

服务端插件 **TransferIdentityFixAPI** 提供"**把某条龙实时追踪到指定玩家的小地图**"能力：

- 通过 **RCON 命令**指定 **目标玩家** + **龙的 ID**（`<id1>_<id2>`）；
- 插件在服务器端每 **0.5 秒**定位该龙，向玩家发送一次 `Client_AddTeamPing`（`ETeamPingType::Track`）追踪标记；
- 标记会**跟随龙移动**（活体绑定），玩家打开地图即可看到该龙当前实时位置；
- 前端可**随时切换追踪目标**（再次调用 TrackDino 传新 id）；用 **StopTrackDino** 清除标记。
- **追踪输入 id 建议先由 `TransferIdentityFix.WildDinos <species>` 查询野生龙清单取得**，再交给 TrackDino 追踪。

---

## 2. 接口调用

### 2.1 开始追踪：`TransferIdentityFix.TrackDino`

| 项 | 值 |
|----|----|
| 命令 | `TransferIdentityFix.TrackDino <player> <dino1> <dino2>` |
| 参数 | `<player>` = 目标玩家（**EOSID / 玩家名 / PID 均可**）；`<dino1> <dino2>` = 龙的 ID 高/低 32 位 |
| 权限 | RCON 命令级 `tif.operator` |
| 通道 | 服务器 RCON（各服端口见 WildDinos 文档 §8） |

**返回（成功）**
```json
{ "ok": true, "player": "<玩家标识>", "dino": "<id1>_<id2>", "found": 1 }
```
- `found=1`：该龙**当前在服务器世界内**（已找到并开始追踪）
- `found=0`：该龙**当前未找到**（未加载/未生成/已死亡）——任务仍会挂起，之后每 0.5s 尝试定位，**一旦出现自动开始追踪**

**返回（失败）**
```json
{ "ok": false, "error": "missing args (player dino1 dino2)" }   // 参数不全
{ "ok": false, "error": "invalid dino id" }                       // dino1/dino2 非数字或为 0
{ "ok": false, "error": "player not found" }                      // 玩家不在线/未找到
```

### 2.2 停止追踪 / 清除标记：`TransferIdentityFix.StopTrackDino`

| 项 | 值 |
|----|----|
| 命令 | `TransferIdentityFix.StopTrackDino <player>` |
| 参数 | `<player>` = 目标玩家（同 TrackDino） |
| 权限 | RCON 命令级 `tif.operator` |

**返回（成功）**
```json
{ "ok": true, "player": "<玩家标识>", "stopped": 1 }
```

---

### 2.3 查询玩家位置：`TransferIdentityFix.PlayerPos`

| 项 | 值 |
|----|----|
| 命令 | `TransferIdentityFix.PlayerPos <player>` |
| 参数 | `<player>` = 目标玩家（**EOSID 必传**，玩家名实测不命中） |
| 权限 | RCON 命令级 `tif.operator` |
| 返回（成功） | `{"ok":true,"player":"<EOSID>","found":true,"x":<feet X>,"y":<feet Y>,"z":<feet Z>}` |
| 返回（玩家无位置） | `{"ok":true,"player":"<EOSID>","found":false,"error":"no player position"}` |
| 返回（失败） | `{"ok":false,"error":"player not found"}` |

> 实测（2026-08-25，Sco 32321）：`whiter.rober` 用玩家名传参返回 `player not found`；用 EOSID `00025a2b9cf14195b9714edd4ee38ac5` 返回 `x=-120777 y=33602 z=790.55`。坐标单位为 UE feet（英尺），与死亡包坐标同源。

---
## 3. 标记清理机制（重要）

追踪标记的清理有 **4 条路径**，前端无需额外处理，但需了解：

| 触发 | 行为 |
|------|------|
| **调用 `StopTrackDino <player>`** | 立即清除该玩家的追踪任务，并发送一条**同槽位过期 Track 标记**（`SendExpiredTrackPing`），客户端收到后**移除地图上的标记** |
| **被追踪龙死亡**（`bIsDead`） | 定位时发现已死 → 自动停止刷新，并发送过期标记**清除地图标记**（不会追尸） |
| **玩家离线 / 不可见** | 定位失败（找不到玩家 Controller）→ 任务保留但不发送标记；玩家重连后恢复 |
| **前端切换目标** | 再次调用 `TrackDino` 传新 id → **覆盖**原任务（旧标记同槽位被新标记替换，无需先 Stop） |

> 前端规范：追踪结束后应主动调用 `StopTrackDino <player>`，确保标记被客户端清除，避免残留。

---

## 4. 数据流与依赖

```
前端 (Hass AppDaemon / 前端页)
   │  RCON
   ▼
TransferIdentityFix.WildDinos <species>   →  读 <abbr>_wild_<species>.json 拿龙 id（含 id1/id2、level、class 等）
   │
   ▼
TransferIdentityFix.TrackDino <player> <id1> <id2>   →  开始实时追踪（0.5s 刷新）
   │
   ▼
客户端玩家小地图显示 Track 标记（跟随龙移动）
   │
   ▼
TransferIdentityFix.StopTrackDino <player>          →  停止并清除标记
```

- **推荐流程**：`WildDinos` 拿清单 → 前端选择目标 → `TrackDino` 开始追踪 → 追踪结束 `StopTrackDino` 清理。
- **切换目标**：直接再 `TrackDino` 新 id（自动覆盖），无需先 Stop。

---

## 5. 参数说明

### 5.1 `<player>`（目标玩家）
`FindControllerForTarget` 依次匹配（任一命中即可）：
1. **EOSID**：`Utf8Encode(GetEOSIDFromController)` 精确匹配
2. **数字 PID**：`LinkedPlayerID` 精确匹配
3. **玩家名 / 角色名**：字符匹配

> 前端建议优先传 **EOSID**（稳定不变），避免重名/改名影响。

### 5.2 `<dino1> <dino2>`（龙的 ID）
- 全局唯一：`<id1>_<id2>`（高/低 32 位），与 WildDinos 数据文件每条记录的 `id` / `id1` / `id2` 一致
- **取数来源**：`WildDinos` 返回的 `dinos[].id1` + `dinos[].id2`（或解析 `id` 字符串 `"id1_id2"`）
- 也适用于**已驯服龙**（传其 id 同样可追踪，追踪逻辑不区分野生/驯服）

---

## 6. 注意事项

1. **追踪标记只有目标玩家在线时才可见**——标记发送到玩家 Controller；玩家离线期间任务保留，重连后自动恢复。
2. **刷新频率**：服务器每 **0.5 秒**定位一次并发送一个 Track 标记（`ProcessDinoTrackTasks`）；若龙在未加载区（stasis），标记不刷新但任务不失效，龙激活后自动恢复。
3. **`found=0` 不代表失败**：任务仍挂起，龙出现后自动开始追踪（可用于"预追踪"）。
4. **同一玩家同时只追一条**：再次 TrackDino 会覆盖旧目标（前端切换目标即如此）。
5. **标记类型**：`ETeamPingType::Track`（与手动地图标记同体系），玩家地图/小地图可见，第三方不可见。
6. **权限**：命令级 `tif.operator`（RCON 通道），与 WildDinos 同权限体系。
7. **前端建议**：追踪结束后务必 `StopTrackDino`；长时间不追踪可清空任务避免服务器无谓定位。

---

## 7. 日志关键字

| 日志 | 含义 |
|------|------|
| `TRACK_DINO player=... dino=... found=0/1` | 开始/切换追踪（含是否找到） |
| `TRACK_PING player=... dino=...` | 每 0.5s 刷新定位成功 |
| `TRACK_PING no_root player=...` | 定位到龙但取不到位置（跳过本次） |
| `TRACK_PING dino_missing player=...` | 龙已不在世界（死亡/消失），自动清除标记 |
| `TRACK_CLEAR_PING player=... dino=...` | 已发送过期标记（清除地图标记） |
| `STOP_TRACK_DINO player=...` | 停止追踪 |

---
## 8. 后端配合：HA script + AppDaemon 事件处理链路（完整实施版 · 2026-08-25 实测）

> ⚠️ **重要**：`TrackDino` / `StopTrackDino` / `PlayerPos` 是**服务端 RCON 命令**，前端页面**无法直接发 RCON**。前端要触发追踪/查位置，必须先由后端（HA 侧）新增「**前端 → HA script → AppDaemon 事件 → RCON → sensor 回读**」链路（与现有 `refresh_tamed` / `search_wild_dinos` 完全同构）。本节为**完整实施版**（含可直接粘贴的代码；前端拿到 script/webhook 地址后即可接入）。

### 8.0 实测结论（2026-08-25 实服 Sco 32321 验证）

- `TransferIdentityFix.PlayerPos <EOSID>` **已生效**，返回真实坐标：`{"ok":true,"found":true,"x":-120777,"y":33602,"z":790.55}`
- **`<player>` 必须传 EOSID**：用玩家名（如 `whiter.rober`）实测返回 `{"ok":false,"error":"player not found"}`（`FindControllerForTarget` 的名字匹配走**角色名**，与 `ListPlayers` 显示的平台名不一致）
- 孤岛 32319 未部署新 dll 时插件无响应（`Server received, But no response!!`）

### 8.1 参考模板：现有 refresh_tamed 链路（成熟链路，直接照抄）

```
前端(有 token)   POST /api/services/script/refresh_tamed   body: {"server":"Sco"}
前端(无 token)   POST /api/webhook/refresh_tamed?server=Sco   （手机 App 免认证）
      ▼
HA script.refresh_tamed  →  发事件 refresh_tamed_request
      ▼
AppDaemon listen_event("refresh_tamed_request")  →  send_rcon_command_sync(host, port, password, cmd)
      ▼
sensor.refresh_tamed_status  ←  前端轮询 state(ok/cooldown/error) + attributes(server/ok/cooldown/result/ts)
```

对应 AppDaemon 侧实现（`asa_server_monitor_reliable.py`）：
- `self.listen_event(self.refresh_tamed_event, "refresh_tamed_request")`（initialize 注册）
- 回调内 `send_rcon_command_sync(self.rcon_host, port, self.rcon_password, "TransferIdentityFix.ArkTamedDinos")` → `json.loads` 解析 → `set_state("sensor.refresh_tamed_status", ...)`
- 端口取自配置 `rcon_ports[server]`

### 8.2 `scripts.yaml` — 追加 3 个 script（照现有 refresh_tamed 格式）

| script | 参数 | 发事件 | 对应 RCON 命令 |
|--------|------|--------|----------------|
| `script.track_dino` | `server` `player` `dino1` `dino2` | `track_dino_request` | `TransferIdentityFix.TrackDino <player> <dino1> <dino2>` |
| `script.stop_track_dino` | `server` `player` | `stop_track_dino_request` | `TransferIdentityFix.StopTrackDino <player>` |
| `script.player_pos` | `server` `player` | `player_pos_request` | `TransferIdentityFix.PlayerPos <player>` |

```yaml
# ===== TrackDino 实时追踪 + 玩家位置（2026-08-25 新增） =====
track_dino:
  alias: 追踪野生龙
  fields:
    server:
      description: 服务器缩写（如 Sco）
      example: Sco
    player:
      description: 目标玩家 EOSID
      example: "00025a2b9cf14195b9714edd4ee38ac5"
    dino1:
      description: 龙 ID 高 32 位
      example: "123"
    dino2:
      description: 龙 ID 低 32 位
      example: "456"
  sequence:
    - event: track_dino_request
      event_data:
        server: "{{ server }}"
        player: "{{ player }}"
        dino1: "{{ dino1 }}"
        dino2: "{{ dino2 }}"

stop_track_dino:
  alias: 停止追踪野生龙
  fields:
    server:
      description: 服务器缩写（如 Sco）
      example: Sco
    player:
      description: 目标玩家 EOSID
      example: "00025a2b9cf14195b9714edd4ee38ac5"
  sequence:
    - event: stop_track_dino_request
      event_data:
        server: "{{ server }}"
        player: "{{ player }}"

player_pos:
  alias: 查询玩家位置
  fields:
    server:
      description: 服务器缩写（如 Sco）
      example: Sco
    player:
      description: 目标玩家 EOSID
      example: "00025a2b9cf14195b9714edd4ee38ac5"
  sequence:
    - event: player_pos_request
      event_data:
        server: "{{ server }}"
        player: "{{ player }}"
```

### 8.3 `automations.yaml` — 追加 3 个 webhook 自动化（无 token 手机场景用）

> ⚠️ 本地同步版 `automations.yaml` 未见现有 webhook 段（现有 `/api/webhook/refresh_tamed` 可能在 HA UI/.storage 内创建）。下面给出标准格式，按现有 webhook 同样的方式添加即可。

```yaml
- id: 'track_dino_webhook'
  alias: TrackDino Webhook
  triggers:
    - trigger: webhook
      webhook_id: track_dino
  actions:
    - action: event.fire
      event_type: track_dino_request
      event_data:
        server: "{{ trigger.query.server }}"
        player: "{{ trigger.query.player }}"
        dino1: "{{ trigger.query.dino1 }}"
        dino2: "{{ trigger.query.dino2 }}"
  mode: restart

- id: 'stop_track_dino_webhook'
  alias: StopTrackDino Webhook
  triggers:
    - trigger: webhook
      webhook_id: stop_track_dino
  actions:
    - action: event.fire
      event_type: stop_track_dino_request
      event_data:
        server: "{{ trigger.query.server }}"
        player: "{{ trigger.query.player }}"
  mode: restart

- id: 'player_pos_webhook'
  alias: PlayerPos Webhook
  triggers:
    - trigger: webhook
      webhook_id: player_pos
  actions:
    - action: event.fire
      event_type: player_pos_request
      event_data:
        server: "{{ trigger.query.server }}"
        player: "{{ trigger.query.player }}"
  mode: restart
```

### 8.4 `asa_server_monitor_reliable.py` — AppDaemon 追加

**initialize 中（`refresh_tamed_request` 那行附近）加 3 行监听：**

```python
self.listen_event(self.track_dino_event, "track_dino_request")
self.listen_event(self.stop_track_dino_event, "stop_track_dino_request")
self.listen_event(self.player_pos_event, "player_pos_request")
```

**追加 3 个回调**（照 `refresh_tamed_event` 同构写法）：

```python
def track_dino_event(self, event_name, data, kwargs):
    """实时追踪：前端 → script.track_dino → 事件 → RCON TrackDino → sensor 回读"""
    status_entity = "sensor.track_dino_status"
    server = (data or {}).get("server", "").strip()
    player = (data or {}).get("player", "").strip()
    dino1 = (data or {}).get("dino1", "").strip()
    dino2 = (data or {}).get("dino2", "").strip()
    if not (server and player and dino1 and dino2):
        self.set_state(status_entity, state="error",
                       attributes={"ok": False, "error": "missing args"})
        return
    port = self.rcon_ports.get(server)
    if not port:
        self.set_state(status_entity, state="error",
                       attributes={"server": server, "ok": False, "error": "no rcon port"})
        return
    try:
        success, result = send_rcon_command_sync(
            self.rcon_host, port, self.rcon_password,
            "TransferIdentityFix.TrackDino %s %s %s" % (player, dino1, dino2))
        ok = False; found = None; err = None
        if success and result:
            try:
                j = json.loads(result)
                ok = bool(j.get("ok")); found = j.get("found"); err = j.get("error")
            except Exception:
                ok = True
        self.set_state(status_entity, state="ok" if ok else "error",
                       attributes={"server": server, "player": player,
                                   "dino": "%s_%s" % (dino1, dino2),
                                   "ok": ok, "found": found, "error": err,
                                   "result": str(result)[:200],
                                   "ts": str(datetime.now())})
        self.log("[track_dino] %s %s ok=%s found=%s" % (server, player, ok, found))
    except Exception as e:
        self.set_state(status_entity, state="error",
                       attributes={"server": server, "ok": False, "error": str(e)})
        self.log("[track_dino] %s error: %s" % (server, e), level="ERROR")

def stop_track_dino_event(self, event_name, data, kwargs):
    """停止追踪：RCON StopTrackDino → sensor 回读"""
    status_entity = "sensor.stop_track_dino_status"
    server = (data or {}).get("server", "").strip()
    player = (data or {}).get("player", "").strip()
    if not (server and player):
        self.set_state(status_entity, state="error",
                       attributes={"ok": False, "error": "missing args"})
        return
    port = self.rcon_ports.get(server)
    if not port:
        self.set_state(status_entity, state="error",
                       attributes={"server": server, "ok": False, "error": "no rcon port"})
        return
    try:
        success, result = send_rcon_command_sync(
            self.rcon_host, port, self.rcon_password,
            "TransferIdentityFix.StopTrackDino %s" % player)
        ok = False
        if success and result:
            try:
                j = json.loads(result)
                ok = bool(j.get("ok"))
            except Exception:
                ok = True
        self.set_state(status_entity, state="ok" if ok else "error",
                       attributes={"server": server, "player": player,
                                   "ok": ok, "result": str(result)[:200],
                                   "ts": str(datetime.now())})
        self.log("[stop_track_dino] %s %s ok=%s" % (server, player, ok))
    except Exception as e:
        self.set_state(status_entity, state="error",
                       attributes={"server": server, "ok": False, "error": str(e)})
        self.log("[stop_track_dino] %s error: %s" % (server, e), level="ERROR")

def player_pos_event(self, event_name, data, kwargs):
    """玩家位置：RCON PlayerPos → sensor 回读（x/y/z）"""
    status_entity = "sensor.player_pos_status"
    server = (data or {}).get("server", "").strip()
    player = (data or {}).get("player", "").strip()
    if not (server and player):
        self.set_state(status_entity, state="error",
                       attributes={"ok": False, "error": "missing args"})
        return
    port = self.rcon_ports.get(server)
    if not port:
        self.set_state(status_entity, state="error",
                       attributes={"server": server, "ok": False, "error": "no rcon port"})
        return
    try:
        success, result = send_rcon_command_sync(
            self.rcon_host, port, self.rcon_password,
            "TransferIdentityFix.PlayerPos %s" % player)
        ok = False; x = y = z = None; found = False; err = None
        if success and result:
            try:
                j = json.loads(result)
                ok = bool(j.get("ok")); found = bool(j.get("found"))
                x = j.get("x"); y = j.get("y"); z = j.get("z"); err = j.get("error")
            except Exception:
                ok = True
        self.set_state(status_entity, state="ok" if ok else "error",
                       attributes={"server": server, "player": player,
                                   "ok": ok, "found": found,
                                   "x": x, "y": y, "z": z, "error": err,
                                   "result": str(result)[:200],
                                   "ts": str(datetime.now())})
        self.log("[player_pos] %s %s ok=%s found=%s x=%s y=%s z=%s" % (server, player, ok, found, x, y, z))
    except Exception as e:
        self.set_state(status_entity, state="error",
                       attributes={"server": server, "ok": False, "error": str(e)})
        self.log("[player_pos] %s error: %s" % (server, e), level="ERROR")
```

### 8.5 前端调用方式（后端加好后）

| 功能 | 有 token | 无 token（webhook） | 结果回读 |
|------|----------|---------------------|----------|
| 开始追踪 | `POST /api/services/script/track_dino` body `{server,player,dino1,dino2}` | `POST /api/webhook/track_dino?server=Sco&player=<EOSID>&dino1=..&dino2=..` | 轮询 `sensor.track_dino_status`（attributes 含 `found`） |
| 停止追踪 | `POST /api/services/script/stop_track_dino` | `POST /api/webhook/stop_track_dino?server=Sco&player=<EOSID>` | 轮询 `sensor.stop_track_dino_status` |
| 玩家位置 | `POST /api/services/script/player_pos` | `POST /api/webhook/player_pos?server=Sco&player=<EOSID>` | 轮询 `sensor.player_pos_status`（attributes 含 `x/y/z/found`） |

**要点**：
- `player` 一律传 **EOSID**（玩家名不命中）
- `dino1/dino2` 来自 `WildDinos` 返回的 `id1/id2`
- 建议前端触发后轮询对应 sensor 判断成功（与 `refresh_tamed` 读 `sensor.refresh_tamed_status` 同模式）
- 追踪结束主动调 `script.stop_track_dino` 清标记

### 8.6 后端改动清单与生效

1. **HA scripts**：新增 `script.track_dino`、`script.stop_track_dino`、`script.player_pos`（§8.2 YAML），均只发事件
2. **HA webhooks（可选）**：无 token 场景新增 `/api/webhook/track_dino`、`/api/webhook/stop_track_dino`、`/api/webhook/player_pos`（§8.3 自动化）
3. **AppDaemon**（`asa_server_monitor_reliable.py`）：
   - `initialize` 注册 3 个 `listen_event`
   - 新增 3 个回调（§8.4），复用 `send_rcon_command_sync` + `rcon_ports`
   - **重启 AppDaemon 生效**（`ha apps restart a0d7b954_appdaemon`）
4. **前端**：改调 3 个 script（或 webhook）+ 轮询 3 个 sensor，无需直接碰 RCON

### 8.7 前后端分工小结（与 WildDinos 配合）

| 能力 | 现有/新增 | 链路 |
|------|-----------|------|
| 野生龙清单查询 | 已有 | 前端 → `script.search_wild_dinos` → 事件 → AppDaemon → RCON `WildDinos` → 读 `<abbr>_wild_*.json` |
| 实时追踪（本次） | **新增** | 前端 → `script.track_dino` → 事件 → AppDaemon → RCON `TrackDino` → `sensor.track_dino_status` 回读 |
| 停止追踪（本次） | **新增** | 前端 → `script.stop_track_dino` → 事件 → AppDaemon → RCON `StopTrackDino` → `sensor.stop_track_dino_status` 回读 |
| 玩家位置（本次） | **新增** | 前端 → `script.player_pos` → 事件 → AppDaemon → RCON `PlayerPos` → `sensor.player_pos_status` 回读 |

**前端推荐流程**：`WildDinos` 拿清单选龙 → `script.track_dino` 开始追踪 → 玩家看小地图 → 结束 `script.stop_track_dino` 清理标记；需要确认玩家位置时 `script.player_pos`。
