# ASA 刷新代理 — NAS Docker 部署说明

> 服务：`server.py`（Python 标准库，无 pip 依赖）
> 用途：前端「最新生物」Tab 调用 `/api/refresh-tamed?server=XX` → 触发 RCON `ArkTamedDinos` → 轮询确认 `tamed.json` 更新

---

## 1. 文件清单

| 文件 | 说明 |
|------|------|
| `server.py` | 代理服务（HTTP + RCON + 轮询） |
| `Dockerfile` | 容器镜像 |
| `docker-compose.yml` | 编排（含卷挂载与环境变量） |

---

## 2. 部署步骤（QNAP Container Station）

### 2.1 准备目录

把 `最新生物TAB\proxy\` 上传到 NAS 任意目录（如 `/share/docker/asa-refresh-proxy/`）。

### 2.2 确认 NAS 出网 RCON

```bash
# 在 NAS SSH 中测试到 ARK 服务器 RCON 端口（示例 Sco 32321）
nc -zv work.whiterober.cn 32321
# 期望：succeeded
```

### 2.3 确认 DinoData 本地路径

NAS 上 DinoData 实际路径（QNAP 通常 `/share/私人共享/ASA/DinoData`），与 `docker-compose.yml` 的 volumes 一致。可在 NAS SSH 确认：

```bash
ls /share/私人共享/ASA/DinoData
```

### 2.4 构建并启动

```bash
cd /share/docker/asa-refresh-proxy
docker compose up -d --build
# 或 Container Station → 创建应用 → 指向本目录
```

验证：

```bash
curl http://127.0.0.1:8080/healthz
# {"ok": true, "service": "asa-refresh-proxy", ...}
```

---

## 3. QNAP 反向代理（关键：mixed content 规避）

前端是 **https**（`wiim.whiterober.com`），容器是 http——浏览器会拦截跨协议 fetch。
**必须**用 QNAP 反向代理把 `/api` 挂到 wiim 同域（https）：

| 项 | 值 |
|----|-----|
| 来源路径 | `https://wiim.whiterober.com/api` |
| 目标 | `http://127.0.0.1:8080`（容器） |
| 转发 | 保留路径（`/api/refresh-tamed?...`） |

配置入口：QNAP 控制台 → **Application Portal**（或 反向代理 / Web 服务器）→ 添加规则。

完成后验证：

```bash
curl -X POST "https://wiim.whiterober.com/api/refresh-tamed?server=Sco"
# {"ok": true, "server": "Sco", "triggered": true, "updated": true, ...}
```

---

## 4. 环境变量

| 变量 | 默认 | 说明 |
|------|------|------|
| `RCON_HOST` | `work.whiterober.cn` | ARK 服务器地址 |
| `RCON_PASSWORD` | （空） | RCON 密码，**仅容器内**，勿提交/落前端 |
| `DINO_DATA` | `/data` | 容器内数据目录（卷挂载 NAS DinoData） |
| `PORT` | `8080` | 监听端口 |
| `POLL_TIMEOUT` | `30` | 轮询确认 tamed 更新超时（秒） |

---

## 5. 本地测试（非容器）

```bash
# 在本机用真实路径测试（Windows P: 映射）
set DINO_DATA=P:\私人共享\ASA\DinoData
set RCON_PASSWORD=1219wu1219
python server.py
curl -X POST "http://127.0.0.1:8080/api/refresh-tamed?server=Sco"
```

> 本地 mock：前端在非 `wiim.whiterober.com` 域名下不调用代理（`LB.PROXY=false`），点刷新走本地模拟，仅用于 UI 开发验证。
