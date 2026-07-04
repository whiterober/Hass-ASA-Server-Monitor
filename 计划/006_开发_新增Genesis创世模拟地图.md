# 新增 Genesis（创世模拟）地图 + bg_image CDN 迁移

## 基础信息
- 创建时间：2026-07-04
- 任务类型：开发
- 服务器 ID：`Gen`
- 中文名：创世模拟
- 图标：🧬 `mdi:dna`
- 端口：7795 / RCON：32329
- 主题色：科技蓝 #3F51B5（Indigo，避免与灭绝青色撞色）
- 按钮位置：方舟视图第三行 Los 按钮后第一个占位符
- 🆕 bg_image 全量迁移：11 个地图封面从 HA 本地 `/api/image/serve/` → CDN `https://img.whiterober.ccwu.cc/ASA/misc/Xxx_compressed.jpg`

---

## 涉及文件

| # | 文件 | 改动 |
|---|------|------|
| 1 | `apps.yaml` | 新增 Gen 配置 + 全量替换 11 个 bg_image URL |
| 2 | 智能体指令（ASA Server Monitor 模式） | 新增服务器映射 + 图标表 |
| 3 | `lovelace`（本地 + 实页 4 路径） | 新增 1 个按钮替换占位符 |
| 4 | `configuration.yaml` | 按需添加 template sensor |

---

## 步骤 1：apps.yaml — 新增 Gen 配置

在 `asa_server_monitor_reliable` 配置下，各段末尾追加：

### profile_names
```yaml
    - "Gen"
```

### profile_map
```yaml
    "Gen": "创世模拟"
```

### profile_ports
```yaml
    "Gen": 7795
```

### rcon_ports
```yaml
    "Gen": 32329
```

### safe_points
```yaml
    "Gen": { x: 0.0, y: 0.0, z: 0.0 }   # ⚠️ 待确认实际坐标
```

### server_themes（Gen 新增）
```yaml
    "Gen":
      name: "创世模拟"
      icon: "mdi:dna"
      emoji: "🧬"
      primary_color: "#3F51B5"
      light_color: "#7986CB"
      dark_color: "#303F9F"
      bg_image: "url('https://img.whiterober.ccwu.cc/ASA/misc/Gen_compressed.jpg')"
      overlay_color: "rgba(63, 81, 181, 0.7)"
```

### 🆕 bg_image 全量 CDN 迁移（11 个地图）

所有服务器 `server_themes` 的 `bg_image` 统一替换：

| ID | 旧 URL（示意） | 新 URL |
|----|---------------|--------|
| Isl | `/api/image/serve/5bb40c2d.../original` | `https://img.whiterober.ccwu.cc/ASA/misc/Isl_compressed.jpg` |
| Sco | `/api/image/serve/d1a891ac.../original` | `https://img.whiterober.ccwu.cc/ASA/misc/Sco_compressed.jpg` |
| Cen | `/api/image/serve/cddd157b.../original` | `https://img.whiterober.ccwu.cc/ASA/misc/Cen_compressed.jpg` |
| Abe | `/api/image/serve/cd69a890.../original` | `https://img.whiterober.ccwu.cc/ASA/misc/Abe_compressed.jpg` |
| Ext | `/api/image/serve/c0fbe9bc.../original` | `https://img.whiterober.ccwu.cc/ASA/misc/Ext_compressed.jpg` |
| Ast | `/api/image/serve/e65bafd6.../original` | `https://img.whiterober.ccwu.cc/ASA/misc/Ast_compressed.jpg` |
| Rag | `/api/image/serve/59594e89.../original` | `https://img.whiterober.ccwu.cc/ASA/misc/Rag_compressed.jpg` |
| Val | `/api/image/serve/7946ff3f.../original` | `https://img.whiterober.ccwu.cc/ASA/misc/Val_compressed.jpg` |
| Bob | `/api/image/serve/2827072b.../original` | `https://img.whiterober.ccwu.cc/ASA/misc/Bob_compressed.jpg` |
| Los | `/api/image/serve/84c38141.../original` | `https://img.whiterober.ccwu.cc/ASA/misc/Los_compressed.jpg` |
| Gen | —（新增） | `https://img.whiterober.ccwu.cc/ASA/misc/Gen_compressed.jpg` |

> 统一格式：`url('https://img.whiterober.ccwu.cc/ASA/misc/{地图缩写}_compressed.jpg')`

---

## 步骤 2：智能体指令 — 新增映射表

### 服务器映射表追加

| ID | 中文名 | 端口 | RCON |
|----|--------|------|------|
| Gen | 创世模拟 | 7795 | 32329 |

### MDI 图标 + emoji 表追加

| ID | 图标 | MDI | emoji |
|----|------|-----|:---:|
| Gen | 🧬 创世模拟 | `mdi:dna` | 🧬 |

---

## 步骤 3：lovelace — 新增服务器按钮

**位置**：`views[3]`（方舟）→ 服务器选择网格 → 第三行 Los 按钮后第一个占位符

**当前第三行**：
```
Los 按钮 → [占位符] → [占位符] → Bob 按钮
```

**改为**：
```
Los 按钮 → Gen 按钮 → [占位符] → Bob 按钮
```

### 按钮模板（参照现有 button-card 结构）

```json
{
  "type": "custom:button-card",
  "entity": "input_button.select_server_gen",
  "name": "[[[ return states['sensor.asa_server_themes'].attributes.server_themes['Gen'].name ]]]",
  "icon": "[[[ return states['sensor.asa_server_themes'].attributes.server_themes['Gen'].icon ]]]",
  "tap_action": {
    "action": "call-service",
    "service": "script.set_selected_server",
    "service_data": { "server_id": "Gen" }
  },
  "styles": {
    "card": {},
    "icon": {},
    "name": {}
  }
}
```

> 5 层动态样式（icon.color / name.color / card.background / card.opacity / card.border）参照现有按钮的 Jinja2 模板。

---

## 步骤 4：双端同步（标准流程）

1. 编辑本地 `lovelace` → JSON 校验
2. `Copy-Item lovelace → lovelace.lovelace -Force`
3. ASA 后台 → 「💾 保存Tab」→ 触发实页同步
4. MD5 四路径验证
5. 重启 HA

---

## 步骤 5：configuration.yaml（按需）

如 Genesis 需要独立 `input_button.select_server_gen` 和模板 sensor：

```yaml
input_button:
  select_server_gen:
    name: "选择创世模拟服务器"
```

---

## 待确认事项

- [ ] Genesis 安全点坐标（`safe_points` x/y/z）
- [x] ~~Genesis 背景图片~~ — 已改为 CDN 直链
- [ ] CDN 图片是否已全部上传到位
- [x] ~~RCON 端口~~ — 已写入 apps.yaml

---

## ✅ 实施记录（2026-07-04）

| 步骤 | 状态 | 备注 |
|------|------|------|
| apps.yaml | ✅ | 备份 `bak/apps_backup_20260704_173037.yaml`，上传 OK |
| 智能体指令 | ⚠️ | VS Code 内部配置，需手动更新 |
| lovelace 按钮 | ✅ | 3 路径 MD5 一致 `d79b048ac...` |
| HA 重启 | ✅ | 已触发，等待 Web 就绪 |

---

## 布局影响

- 第三行：`Los | 空 | 空 | Bob` → `Los | Gen | 空 | Bob`
- 10 按钮 → 11 按钮
- 网格仍为 4 列，无需调整布局
