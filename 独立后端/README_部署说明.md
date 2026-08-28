# dino_backend.py 部署说明（Phase 3 — 独立 RCON 后端）

> 目标：让 `dino.whiterober.ccwu.cc` 页面通过 `data.whiterober.ccwu.cc` 独立工作，脱离 HA/NAS。
> 部署位置：**Win Server 2019 物理服务器**（192.168.199.3，游戏服同机，RCON 走 127.0.0.1）

---

## 1. 文件

| 文件 | 位置 |
|------|------|
| `dino_backend.py` | 物理服务器（建议 `D:\dino_backend\dino_backend.py`） |
| 状态文件目录 | 物理服务器（默认 `D:\ARK Server\DinoData\asa-data\`，后端自动创建/写入） |

> ⚠️ **静态资源（6 个 JSON）已迁到 CF Pages**（icon_zh_map / gene_traits_zh / dino_prefix_zh / dino_colors / icon_anti_color / icons2 平铺在 `dino-import` 项目根目录，随 `index.html` 一起发布），**无需部署到物理服务器**。
>
> 物理服务器上只需后端**自动写入的 2 个状态文件**：`refresh_status.json`、`wild_status.json`（RCON 刷新/搜野生后由 `dino_backend.py` 自动写到 `ASA_DATA` 目录，无需手动放置）。

---

## 2. 部署（物理服务器 Win Server 2019）

### 2.1 前置

1. 确认有 Python 3（无则装：https://www.python.org/downloads/，安装时勾选 Add to PATH）
2. 确认 `D:\ARK Server\DinoData` 存在（游戏插件实时落盘目录）
3. 无需手动放置静态 JSON（6 个静态已在 CF Pages；状态文件由后端自动写入）

### 2.2 启动（前台测试）

```bat
cd /d D:\dino_backend
python dino_backend.py
```

看到输出 `dino_backend listening on :8080` 即成功。

### 2.3 注册为 Windows 服务（开机自启，推荐）

用计划任务（最简单，无需额外工具）：

1. `Win+R` → `taskschd.msc` → 创建任务
2. 常规：名称 `dino_backend`，勾选「不管用户是否登录都要运行」
3. 触发器：`登录时` 或 `启动时`
4. 操作：程序 = `python.exe`，参数 = `D:\dino_backend\dino_backend.py`，起始于 = `D:\dino_backend`

或注册系统服务（需 NSSM）：
```bat
nssm install dino_backend "C:\Python312\python.exe" "D:\dino_backend\dino_backend.py"
nssm set dino_backend AppDirectory D:\dino_backend
nssm start dino_backend
```

---

## 3. 端口转发（工作室路由）

`data.whiterober.ccwu.cc` → CNAME → `work.whiterober.cn`（DDNS）→ 路由器端口转发 → 物理服务器。

在工作室路由器（DDNS 那台）加一条：

| 项 | 值 |
|----|-----|
| 外部端口 | **8080** |
| 内部 IP | 192.168.199.3（物理服务器） |
| 内部端口 | 8080 |
| 协议 | TCP |

> 这样公网 `work.whiterober.cn:8080` → 物理服务器 8080 → dino_backend。
> CF `data.whiterober.ccwu.cc`（橙云）→ 回源 `work.whiterober.cn:8080`。

---

## 4. 验证

浏览器或 curl 测试（先在局域网内直测物理服务器 IP）：

```bat
curl http://192.168.199.3:8080/healthz
:: {"ok": true, "service": "dino-backend", "servers": [...]}

curl http://192.168.199.3:8080/api/themes
:: {"ok": true, "server_themes": {...}}

curl http://192.168.199.3:8080/asa-data/refresh_status.json
:: 返回 JSON（后端自动写入的状态文件）

curl -X POST "http://192.168.199.3:8080/api/refresh_tamed?server=Isl"
:: {"ok": true, "server": "Isl", "triggered": true, ...}   (RCON 成功时)
```

公网验证：`https://data.whiterober.ccwu.cc/healthz`（需端口转发 + CF 生效后）。

---

## 5. 环境变量（可选，默认即可用）

| 变量 | 默认 | 说明 |
|------|------|------|
| `DINO_DATA` | `D:\ARK Server\DinoData` | 数据目录 |
| `ASA_DATA` | `DINO_DATA\asa-data` | 静态资源目录 |
| `RCON_HOST` | `127.0.0.1` | 本机游戏服 |
| `RCON_PASSWORD` | `1219wu1219` | RCON 密码 |
| `PORT` | `8080` | 监听端口 |
| `ALLOW_ORIGIN` | `https://dino.whiterober.ccwu.cc` | CORS 允许来源 |

---

## 6. 前端对接（后端就绪后）

`dino-import-new.html` 已做**双架构兼容**（`LB_ARCH`/`LB_ASA`/`LB_STATUS`/`LB_API`）：
- 静态资源（`LB_ASA`）：新架构走 **CF Pages 同域** `https://dino.whiterober.ccwu.cc`（6 个 JSON 已平铺部署）
- 状态文件（`LB_STATUS`）：新架构走 `https://data.whiterober.ccwu.cc/asa-data`（后端写入 refresh_status/wild_status）
- API（`LB_API`）：新架构走 `https://data.whiterober.ccwu.cc`
- 旧架构（hass 域名）保持 `/local/asa-data/`、`/api/` 完全不变

**⚠️ 但注意**：当前前端新架构的 API 调用路径是 `LB_API + '/api/services/script/...'`（对齐旧 HA 路径）。
独立后端 `dino_backend.py` 用的是新路径 `/api/refresh_tamed` 等。**两者路径不同**，需二选一：

- **方案 B（推荐，前端零改动）**：后端增加旧路径别名路由（`/api/services/script/refresh_tamed`、`/api/webhook/refresh_tamed`、`/api/states/sensor.refresh_tamed_status` 等 → 内部转发到新逻辑）
- **方案 A**：前端双架构新增路径映射——新架构下 `LB.SVC_REFRESH` 等直接指向后端新路径

> 待后端部署验证后，再决定前端路径适配方式（或后端直接兼容旧路径最简单）。

---

## 7. 接口一览

| 方法 | 路径 | 参数 | 说明 |
|------|------|------|------|
| GET | `/healthz` | — | 健康检查 |
| GET | `/api/themes` | — | 服务器主题 |
| GET | `/api/status/:server` | — | 单服状态/端口 |
| POST | `/api/refresh_tamed` | server | 刷新 tamed |
| POST | `/api/search_wild` | server, species | 搜野生 |
| POST | `/api/track_dino` | server, player, dino1, dino2 | 实时追踪 |
| POST | `/api/stop_track_dino` | server, player | 停止追踪 |
| POST | `/api/player_pos` | server, player | 玩家位置 |
| GET | `/asa-data/*` | — | 静态资源 |
| GET | `/dino-data/*` | — | 数据 JSON |

---

## 8. 🔒 双轨隔离规矩（必须遵守，保旧链路零影响）

> 新架构（`dino.whiterober.ccwu.cc`）与旧架构（`hass.whiterober.com`）**双轨并行**，靠三个隔离保证旧链路完全不受影响。

### 8.1 文件隔离（最关键）

| 文件 | 位置 | 版本 |
|------|------|------|
| `dino-import.html`（旧） | HA `/config/www/dino-import.html` | **旧代码，禁止覆盖** |
| `index.html`（新） | CF Pages `dino-import` 项目 | 双兼容新代码 |

> 🔴 **铁律**：**禁止**把新版 `dino-import-new.html` 覆盖上传到 HA `/config/www/dino-import.html`。
> 否则旧链路（hass.whiterober.com）会被新代码接管，可能因新后端未完全就绪而退化。

### 8.2 代码隔离（双兼容自动兜底）

新版前端含 `LB_ARCH` 架构检测：
- **hass 域名** → `LB_ARCH=old` → `LB_ASA='/local/asa-data'`、`LB_API=''` → 路径**精确还原**为旧行为
- **ccwu.cc 域名** → `LB_ARCH=new` → 走 `data.whiterober.ccwu.cc` 新链路

> 即使将来把新版也部署到 HA，在 hass 域名下也会自动走旧路径，行为与旧版一致。

### 8.3 后端隔离（HA 服务全不动）

- HA 的 `scripts.yaml` / `configuration.yaml` / AppDaemon `asa_server_monitor_reliable.py` / webhook / sensor —— **全部不改**
- 新后端 `dino_backend.py` 是独立进程，与 HA 无耦合
- 旧链路（script → 事件 → AppDaemon → RCON）继续独立工作

### 8.4 切换规则

| 操作 | 做法 |
|------|------|
| 保持并行 | 什么都不用做，双轨同时可用 |
| 切到新轨 | 把新版覆盖到 HA www 目录（新代码在 hass 域名自动走旧路径，或直接引导用户用 ccwu.cc 域名） |
| 回滚旧轨 | 用旧版备份恢复 HA www 目录即可 |

> 推荐长期保持双轨：旧轨给老入口（hass），新轨给全国加速入口（ccwu.cc），互不干扰。
