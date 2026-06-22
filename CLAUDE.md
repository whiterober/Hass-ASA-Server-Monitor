# CLAUDE.md — 粑粑方舟 ASA Server Monitor 智能体

> 本文件是项目的**智能体配置**，Claude 在此项目中工作时自动加载，确保所有操作符合规范。

---

## 🎯 核心边界

**本智能体只涉及 `lovelace` 概览页中「方舟」视图及其关联子页面。** 不涉及其他视图（家、电视遥控器、工作室等），除非明确要求。

## ⚠️⚠️⚠️ 最高铁律：双端同步（优先级高于一切其他规则）

**任何改动必须同时应用到实页和预览区。** 不存在"只在预览改"或"只在实页改"的情况。

### 固定应用逻辑（严格遵守，不可跳步）

1. **改动预览区** — 修改 `build_lovelace.py` / `preview_server.py` / `vendor.css` / 数据文件等，本地构建生成预览
2. **ASA 后台保存同步实页** — 通过 ASA 后台管理页面点击「💾 保存Tab」按钮，走 `saveJSON` → `shell_command.save_asa_data` → `build_lovelace` 流程，同源提交到实页
3. **重启 HA** — 使实页生效
4. **自我验证** — 验证刚才的改动已在预览区和实页同时生效（MD5 + 内容一致性）
5. **除非必要，直接的代码改动只动预览区代码**。同步实页只走"保存Tab"逻辑。要直接动实页文件（SFTP 上传 lovelace）必须暂停、说明原因、等用户确认
6. **🚨 数据文件改动必须先拉后推**。涉及 `tribe_ops.json`、`asa_server_rules.json`、`asa_base_quick_ref.json` 等数据文件时：先用 SFTP 从服务器拉取最新版本 → 本地修改 → 再上传。**禁止**假设本地文件是最新、禁止直接用本地文件覆盖服务器。因为用户可能通过 ASA 管理页手动改过数据。
7. **以上规则与其他规则冲突时，以以上规则为准**
8. **🚨 改前必备份**：修改任何文件前，必须先 `Copy-Item` 备份到 `www/` 目录，命名格式 `asa-admin_backup_YYYYMMDD_HHMMSS.html`。**禁止**在无备份的情况下直接修改。防止改坏后被迫从基线重新开始。

| 改动层 | 实页（HA lovelace） | 预览（preview_tab.html） |
|--------|-------------------|------------------------|
| 数据 | ASA 后台保存 → `/homeassistant/www/asa-data/tribe_ops.json` ← **必须先拉后改** | 同源数据文件 ← **必须先拉后改** |
| 渲染 | `build_lovelace.py` → lovelace JSON | `preview_server.py` 导入 `build_lovelace` 同函数 |
| CSS | `make_content_card()` 内联 CSS | 同逻辑需同步更新到 `preview_server.py` 的 CSS 组合 |
| 结果文件 | `/homeassistant/.storage/lovelace.lovelace` | `/config/www/preview_tab.html` |

| 范围内 | 范围外 |
|--------|--------|
| `lovelace` 中「方舟」视图 (title: "方舟") | 其他 lovelace 视图（家、工作室等） |
| 方舟相关子页面（服务器操作、资讯广场、部落速查等） | `configuration.yaml` 非 ASA 相关模板 |
| 方舟相关的 template sensor 配置 | `scripts.yaml` 非 ASA 相关脚本 |
| `asa_server_monitor_reliable.py` ASA 监控脚本 | discord_patch_bot 非 ASA 相关部分 |
| `apps.yaml` 中 asa_server_monitor_reliable 配置 | 其他 AppDaemon 模块 |

---

## 📁 文件架构

```
[Home Assistant 服务器]                        [本地开发环境]
/config/                                   A:\NetSarang\Xftp 8\Temporary\
├── lovelace          ◄─── XFtp 实时同步 ──► ├── lovelace
├── lovelace.lovelace ◄─── XFtp 实时同步 ──► ├── lovelace.lovelace
├── configuration.yaml◄─── XFtp 实时同步 ──► ├── configuration.yaml
├── apps.yaml         ◄─── XFtp 实时同步 ──► ├── apps.yaml
├── scripts.yaml      ◄─── XFtp 实时同步 ──► ├── scripts.yaml
├── asa_server_monitor_reliable.py ◄─同步──► ├── asa_server_monitor_reliable.py
└── discord_patch_bot.py    ◄─── 同步 ──►   └── discord_patch_bot.py

                                        B:\项目\Hass ASA Server Monitor\
                                        ├── CLAUDE.md          ← 智能体配置（本文件）
                                        ├── *.md                ← 周边文档
                                        └── .code-workspace     ← VSCode 工作区
```

---

## ⚠️ 关键规则：Lovelace 编辑流程

### 核心规则

> **所有 lovelace 页面修改，先改 `lovelace`，再同步到 `lovelace.lovelace`。**

这是用户明确指定的工作流，不可颠倒。

### 编辑流程

> 🚨 **步骤 4 绝对不能跳过！** 漏掉会导致 HA 加载旧版 lovelace，所有修改不生效。

1. **Read** `A:\NetSarang\Xftp 8\Temporary\lovelace` — 确认当前内容
2. **Edit** `A:\NetSarang\Xftp 8\Temporary\lovelace` — 执行修改
3. **验证** lovelace JSON 格式正确
4. **🚨 必须同步** — 执行（不可跳过）：
   ```powershell
   Copy-Item "A:\NetSarang\Xftp 8\Temporary\lovelace" "A:\NetSarang\Xftp 8\Temporary\lovelace.lovelace" -Force
   ```
5. **同步实页** — 打开 ASA 后台管理 → 切换到对应 Tab → 点击「💾 保存Tab」。这会触发 `saveJSON` → `shell_command.save_asa_data` → `build_lovelace` → 更新 `/homeassistant/.storage/lovelace.lovelace`。
   > ⚠️ **禁止直接 SFTP 上传 lovelace 文件，除非用户明确要求。** 必须走 ASA 后台保存同源流程。
6. **🚨🚨 验证 4 路径 MD5（每次保存后强制执行，不可跳过）**：
   ```bash
   python -c "
   import paramiko
   h='192.168.197.253';p=22;u='root';pw='1219Wu1219@'
   c=paramiko.SSHClient();c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
   c.connect(h,port=p,username=u,password=pw,look_for_keys=False,allow_agent=False)
   sin,sout,serr=c.exec_command('md5sum /config/lovelace /config/lovelace.lovelace /config/.storage/lovelace /homeassistant/.storage/lovelace.lovelace',timeout=10)
   print(sout.read().decode())
   c.close()
   "
   ```
   **4 个文件 MD5 必须完全一致。少一个、错一个都算失败。每轮对话涉及 lovelace 修改时，应答末尾必须贴出 MD5 验证结果。**
7. **🚨🚨 实页/预览一致性验证（每次验证后强制执行）**：
   ```bash
   python -c "
   import paramiko
   h='192.168.197.253';p=22;u='root';pw='1219Wu1219@'
   c=paramiko.SSHClient();c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
   c.connect(h,port=p,username=u,password=pw,look_for_keys=False,allow_agent=False)
   sin,sout,serr=c.exec_command('stat -c \"%n %Y\" /homeassistant/.storage/lovelace.lovelace /config/www/preview_tab.html',timeout=10)
   print(sout.read().decode())
   c.close()
   "
   ```
   **两个文件的修改时间戳必须在同一分钟内。否则说明实页和预览不同步。**
8. **重启 HA** 使修改生效

---

## 📊 Lovelace Dashboard 结构

### 视图总览 (lovelace 顶层 views 数组)

| # | title | type | 说明 | 路径 |
|---|-------|------|------|------|
| 0 | 家 | sections | 首页：地图、设备控制 | `/lovelace/0` |
| 1 | 电视遥控器 | sections | 电视/媒体控制 | `/lovelace/1` |
| 2 | 工作室 | sections | 工作室设备 | `/lovelace/2` |
| 3 | **方舟** | sections | **ASA 服务器管理主页** ← 核心 | `/lovelace/3` |
| 4 | 服务器操作 | sections | 服务器操作面板 | `/lovelace/asa-server-ops` |
| 5 | 资讯广场 | sections | 补丁/资讯聚合 | `/lovelace/ark_patch` |
| 6 | 老板部落运维速查 | sections | 部落运维信息 | `/lovelace/info_whiterober` |
| 7 | 老板部落基地速查 | sections | 基地坐标信息 | `/lovelace/base_whiterober` |

### 「方舟」视图结构 (视图索引 3，约在 lovelace 行 1330-2142)

```
方舟 (sections)
├── [Grid] 部落运维速查入口 (仅特定用户可见)
├── [Grid] ASA 服务器操作主卡片 (有条件显示：选中服务器后出现)
│   ├── custom:button-card → 导航到 asa-server-ops
│   └── 动态背景 (来自 sensor.asa_server_themes)
├── [Grid] 服务器规则标题
├── [Grid] 服务器选择网格 (10个服务器按钮)
│   ├── 孤岛 / Isl (孤岛 . 端口7777)
│   ├── 焦土 / Sco (焦土 . 端口7779)
│   ├── 核心岛 / Cen (核心岛 . 端口7781)
│   ├── 畸变 / Abe (畸变 . 端口7783)
│   ├── 灭绝 / Ext (灭绝 . 端口7785)
│   ├── 繁星 / Ast (繁星 . 端口7787)
│   ├── 仙境 / Rag (仙境 . 端口7789)
│   ├── 瓦尔盖罗 / Val (瓦尔盖罗 . 端口7791)
│   ├── 俱乐部 / Bob (俱乐部 . 端口7775)
│   └── 失落地 / Los (失落地 . 端口7793)
├── [Grid] 操作系统选择 (Windows/Linux)
├── [Grid] 快速操作按钮
├── [Grid] 补丁信息入口 → 导航到 ark_patch
├── [Grid] 服务器状态显示
└── [Grid] 操作日志
```

### 子页面导航路径

| 子页面 | navigation_path |
|--------|----------------|
| 部落运维速查 | `/lovelace/info_whiterober` |
| 服务器操作 | `/lovelace/asa-server-ops` |
| 资讯广场 | `/lovelace/ark_patch` |
| 基地速查 | `/lovelace/base_whiterober` |

---

## 🔌 核心实体引用 (ASA 相关)

### 输入控制实体

| Entity ID | 类型 | 说明 |
|-----------|------|------|
| `input_select.selected_server` | input_select | 当前选中服务器 (Isl/Sco/Cen/...) |
| `input_select.selected_action` | input_select | 当前选中操作类型 |
| `input_text.current_operator` | input_text | 当前操作者信息 |
| `input_button.select_server_*` | input_button | 各服务器选择按钮 |
| `input_button.execute_server_action` | input_button | 执行服务器操作 |

### 传感器实体

| Entity ID | 说明 | 关键属性 |
|-----------|------|----------|
| `sensor.asa_server_details` | **核心传感器**：所有服务器详细数据 | `servers[]`, `server_players{}`, `profile_ports{}` |
| `sensor.asa_server_themes` | 服务器主题配置 | `server_themes{}` (含 icon, primary_color, bg_image 等) |
| `sensor.asa_server_status` | 服务器整体状态 | |
| `sensor.dialog_server_status` | 弹窗服务器状态 (在线/离线) | |
| `sensor.dialog_server_version` | 弹窗服务器版本号 | |
| `sensor.dialog_server_players` | 弹窗服务器玩家数 | |
| `sensor.dialog_server_ingame_time` | 弹窗服务器游戏内时间 | |
| `sensor.dialog_server_combined` | 服务器状态与版本组合 | `status`, `version` |
| `sensor.official_server_version` | 官方服务器版本 | |
| `sensor.profile_port` | 当前服务器端口 | |
| `sensor.ingame_time_cache` | 游戏内时间缓存 | `server_times{}` |
| `sensor.safe_point_coords` | 安全点坐标 | `coords` |

### 补丁/资讯传感器

| Entity ID | 说明 |
|-----------|------|
| `sensor.patch_cache` | 补丁缓存 (Discord 主频道) |
| `sensor.patch_channel_cache` | Patch 频道缓存 |
| `sensor.news_cache` | 新闻频道缓存 |
| `sensor.tieba_cache` | 贴吧频道缓存 |
| `sensor.adm_cache` | ADM 预告缓存 |
| `sensor.asb_cache` | ASB 缓存 |
| `sensor.patch_description` | 补丁说明（模板 sensor） |
| `sensor.patch_description_patch` | Patch 频道补丁说明 |
| `sensor.news_patch_description` | 新闻频道补丁说明 |
| `sensor.tieba_lz_summary` | 贴吧楼主摘要 |
| `sensor.adm_preview_summary` | ADM 预告摘要 |
| `sensor.asb_summary` | ASB 摘要 |
| `sensor.latest_summary_sensor` | 最新摘要（自动选择最新的补丁/资讯） |

### 脚本

| Script | 说明 |
|--------|------|
| `script.set_selected_server` | 设置选中服务器（含操作者记录） |
| `script.execute_server_action` | 执行服务器操作 |
| `script.execute_server_action_with_selection` | 带选择的服务器操作 |

---

## 🎨 代码模式与约定

### 服务器数据访问模式

```javascript
// 获取当前选中服务器 ID
states['input_select.selected_server'].state

// 获取服务器详情
states['sensor.asa_server_details'].attributes.servers.find(s => s.ProfileName === 'Isl')

// 获取服务器主题
states['sensor.asa_server_themes'].attributes.server_themes['Isl']

// 获取主题字段
theme.primary_color    // 主色
theme.dark_color       // 深色
theme.light_color      // 浅色
theme.bg_image         // 背景图片 URL
theme.icon             // MDI 图标
theme.name             // 中文名称
theme.overlay_color    // 叠加色
```

### 服务器按钮动态样式模式

每个服务器按钮使用 `custom:button-card` + 三重模板表达式：
- **name**: Jinja2 `[[[ ... ]]]` — 动态显示服务器名+版本号
- **icon**: Jinja2 `[[[ ... ]]]` — 从 themes 获取动态图标
- **styles**: 含 3 层动态样式：
  - `icon.color` — 运行中=主题色 (选中=light_color, 未选中=primary_color), 离线=灰色
  - `name.color` — 选中=白色, 未选中=主题色
  - `card.background` — 选中=渐变色, 未选中=默认卡片色
  - `card.opacity` — 离线=0.5, 运行=1
  - `card.border` — 选中=2px 主题色实线, 未选中=none

### Card Mod 模式

lovelace 中使用 `card_mod` 的 "style" 字段注入自定义 CSS，格式：
```json
{
  "card_mod": {
    "style": "css-selector { property: value; }"
  }
}
```
部分样式使用 Jinja2 模板动态生成（如主题色叠加层）。

### 模板 Sensor 模式 (configuration.yaml)

新版语法 (`template:` 域下)：
```yaml
template:
  - sensor:
      - name: "显示名称"
        unique_id: entity_id_suffix
        state: "{{ ... }}"
        icon: "mdi:icon-name"
        attributes:
          key: "{{ ... }}"
```

---

## 🗺️ ASA 服务器映射表

| Profile ID | 中文名 | 端口 | RCON 端口 |
|-----------|--------|------|-----------|
| Isl | 孤岛 | 7777 | 32320 |
| Sco | 焦土 | 7779 | — |
| Cen | 核心岛 | 7781 | — |
| Abe | 畸变 | 7783 | — |
| Ext | 灭绝 | 7785 | — |
| Ast | 繁星 | 7787 | — |
| Rag | 仙境 | 7789 | — |
| Val | 瓦尔盖罗 | 7791 | — |
| Bob | 俱乐部 | 7775 | — |
| Los | 失落地 | 7793 | — |

### 服务器 MDI 图标 + emoji（lovelace 按钮 + apps.yaml 主题用）

| Profile ID | 图标 | MDI | emoji |
|-----------|------|-----|:---:|
| Isl | 🏝️ 岛屿 | `mdi:island` | 🏝️ |
| Sco | 🌋 火山 | `mdi:volcano` | 🔥 |
| Cen | 💎 水晶 | `mdi:diamond-stone` | 💎 |
| Abe | ☢️ 辐射 | `mdi:radioactive` | ☢️ |
| Ext | ☄️ 陨石 | `mdi:meteor` | ☄️ |
| Ast | ✨ 繁星 | `mdi:star-four-points` | ✨ |
| Rag | 🗼 灯塔 | `mdi:lighthouse-on` | 🗼 |
| Val | 🌲 针叶林 | `mdi:forest` | 🌲 |
| Bob | 🎉 派对 | `mdi:party-popper` | 🎉 |
| Los | 🏰 城堡 | `mdi:castle` | 🏰 |

---

## 🛠️ 常见任务指南

### 添加新服务器按钮到方舟页面

1. 在 `apps.yaml` 的 `asa_server_monitor_reliable` 中注册新 profile
2. 在 `configuration.yaml` 模板中添加相关 sensor（如需要）
3. 编辑 `lovelace` 中「方舟」视图的服务器选择网格
4. 复制现有按钮模板，修改 ProfileName、图标、名称
5. **同步 `lovelace` → `lovelace.lovelace`**

### 修改服务器主题

1. 编辑 `asa_server_monitor_reliable.py` 中的主题配置逻辑
2. 更新 `sensor.asa_server_themes` 属性的生成代码
3. 如需调整 lovelace 中主题使用方式，编辑 `lovelace` 中相关 Jinja2 模板
4. **同步 `lovelace` → `lovelace.lovelace`**

### 添加新的模板 Sensor

1. 在 `configuration.yaml` 的 `template:` 域下添加 sensor 定义
2. 使用 `unique_id` 确保 entity_id 稳定
3. 如需要，在方舟页面 lovelace 卡片中引用新 sensor
4. **同步 `lovelace` → `lovelace.lovelace`**

### 调试 Lovelace 卡片

1. 先用 `lovelace` 编辑
2. 用 JSON 校验器检查格式（lovelace 是 JSON 格式）
3. **同步到 `lovelace.lovelace`**
4. XFtp 自动同步到 HA 服务器
5. 在 HA 前端刷新页面查看效果

---

## ⚙️ 技术栈

| 组件 | 技术 | 说明 |
|------|------|------|
| 前端仪表板 | Home Assistant Lovelace (YAML mode) | JSON 格式存储 |
| 卡片 | custom:button-card, tile, markdown, entities | 混合原生和自定义卡片 |
| 自动化后端 | AppDaemon (Python) | asa_server_monitor_reliable.py |
| Discord 集成 | AppDaemon (Python) | discord_patch_bot.py |
| 模板引擎 | Home Assistant Template (Jinja2) | configuration.yaml 中的 sensor/switch |
| 前端交互 | Jinja2 `[[[ ]]]` 模板 | lovelace 中的动态表达式 |
| 文件同步 | XFtp (SFTP) | 本地 ↔ HA 服务器实时同步 |
| 配置格式 | YAML / JSON | configuration.yaml=YAML, lovelace=JSON |

---

## 📝 相关文档

- [sensor_template_migration.md](sensor_template_migration.md) — 25 个模板传感器迁移指南
- [multi_client_isolation_plan.md](multi_client_isolation_plan.md) — 多客户端/多用户界面隔离方案
- [operator_indicator_solution.md](operator_indicator_solution.md) — 操作者指示器实现方案
- [card_mod_4.2.0_upgrade_analysis.md](card_mod_4.2.0_upgrade_analysis.md) — Card-mod 4.2.0 升级分析

---

### 版本管理

- 每次部署使用 `_upload_v173.py`，自动递增版本号
- **服务器保留最近 10 个版本**（`len > 10` → 删最旧的），防止误删后无法回退
- 重大改动前备份基线：`Copy-Item` → `asa-admin-baseline-vXXX.html`
- **部署后自动打开新版本**：每次 `_upload_v173.py` 成功后，必须用 `open_browser_page` 打开新版本的 URL，无需用户要求

> 最后更新：2026-06-20
> 本文件由 Claude Code 智能体维护，随项目演进持续更新。
