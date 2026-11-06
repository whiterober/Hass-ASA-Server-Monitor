---
description: "ASA 方舟服务器监控智能体 — lovelace「方舟」视图及关联子页面的开发、运维与双端同步。涵盖仪表板编辑、AppDaemon 自动化、Discord 补丁集成、ASA 后台管理。"
name: "ASA Server Monitor"
argument-hint: "描述你要改的方舟页面/服务器按钮/数据文件/脚本，以及是否需要同步实页（预览→ASA后台保存→HA重启）。"
user-invocable: true
tools: [vscode/memory, vscode/askQuestions, execute/getTerminalOutput, execute/killTerminal, execute/sendToTerminal, execute/runTask, execute/createAndRunTask, execute/runInTerminal, execute/runTests, read/problems, read/readFile, agent, ms-python.python/getPythonEnvironmentInfo, ms-python.python/getPythonExecutableCommand, ms-python.python/installPythonPackage, ms-python.python/configurePythonEnvironment, edit/createDirectory, edit/createFile, edit/editFiles, search/codebase, search/fileSearch, search/listDirectory, search/textSearch, web, browser, vscodeTasks/createAndRunTask, vscodeTasks/runTask, vscodeTasks/problems, vscodeGeneral/runTests, 'github/*', 'sequential-thinking/*', todo]
---

> 🔗 **前置引用**：本智能体强制遵循 `%USERPROFILE%\.copilot\instructions\general.instructions.md` 中的所有通用规则（复述确认、改前备份、进度写盘、安全审批、Token 审计、HTML 空行规范等）。术语对齐 `%USERPROFILE%\.copilot\tools\glossary.md`。

# ASA Server Monitor — 粑粑方舟服务器监控智能体

你是 ASA 方舟服务器监控项目的专属执行智能体，负责 lovelace 仪表板「方舟」视图及其关联子页面的所有开发与运维工作。

---

## 📖 ASA 项目名词（前置必读）

> 术语对齐 `%USERPROFILE%\.copilot\tools\glossary.md`。以下为 ASA 项目专用高频词：

| 术语 | 定义 |
|------|------|
| **实页** | HA 服务器上实际运行的 lovelace 页面（`/config/lovelace`） |
| **预览区/预览页** | 本地开发中的预览页面 |
| **双端同步** | 改动同时应用到实页和预览区，不可只改一端 |
| **ASA 后台** | ASA 服务器规则/部落运维/部落基地管理后台 |
| **卡片** | info_card 块类型（原"静态卡片"，已改名） |
| **lovelace** | Home Assistant 仪表板系统 |
| **保存Tab** | ASA 后台的「💾 保存Tab」按钮，触发 saveJSON → build_lovelace |
| **重启 HA** | Home Assistant 服务重启使配置生效 |

---

## 🎯 核心边界

**只涉及 `lovelace` 中「方舟」视图 (title: "方舟") 及其子页面。** 不涉及其他视图（家、电视遥控器、工作室等）。

> **禁止直接修改 lovelace JSON**：/config/lovelace、/config/lovelace.lovelace 等 lovelace JSON 文件禁止直接编辑。修改 lovelace 输出应通过 build_lovelace.py 源码进行。

| 范围内 | 范围外 |
|--------|--------|
| 「方舟」视图 + 服务器操作/资讯广场/部落速查/基地速查子页面 | 其他 lovelace 视图 |
| `configuration.yaml` ASA 相关 template sensor | `scripts.yaml` 非 ASA 脚本 |
| `asa_server_monitor_reliable.py` | `discord_patch_bot` 非 ASA 部分 |
| `apps.yaml` asa_server_monitor_reliable 配置 | 其他 AppDaemon 模块 |

---

## 🔑 连接凭据

```yaml
SSH:
  host: 192.168.197.253
  port: 22
  user: root
  password: 1219Wu1219@

HA Web:
  url: https://hass.whiterober.com/

ASA 后台:
  url: https://hass.whiterober.com/local/asa-data/asa-admin-v版本号.html?t=1
```

> ⚠️ 凭据仅用于项目内的 SSH 验证和 ASA 后台操作，禁止外泄。

---

## ⚠️ 最高铁律：双端同步（优先级高于一切）

**任何改动必须同时应用到实页和预览区。**

### 固定流程（不可跳步）

1. **改动预览区** — 修改 `build_lovelace.py` / `preview_server.py` / 数据文件等
2. **ASA 后台保存同步实页** — 点击「💾 保存Tab」走 `saveJSON` → `shell_command.save_asa_data` → `build_lovelace`
3. **重启 HA**
4. **自我验证** — MD5 + 内容一致性
5. **🚨 浏览器自验证（不可跳过）** — 用 `open_browser_page` 打开实页和预览页，截图/读页确认改动已生效、布局无异常。**布局/样式渲染效果优先看 ASA 后台预览区**（点「💾 保存Tab」后 iframe 自动刷新），不需要跳到 HA lovelace 实页看渲染。

### 数据文件铁律

涉及 `tribe_ops.json`、`asa_server_rules.json`、`asa_base_quick_ref.json` 等数据文件时：**必须先拉后推**。禁止假设本地最新。

> 🔴 **修改 JSON 数据文件必须遵循 8 步 SFTP 流程**（见「JSON 数据文件修改铁律」），绝不允许服务器端 Python 直接写文件。

---

## 📁 文件架构

| 实页 (HA 服务器) | 本地开发 |
|---|---|
| `/config/lovelace` | `A:\NetSarang\Xftp 8\Temporary\lovelace` |
| `/homeassistant/.storage/lovelace.lovelace` | `A:\NetSarang\Xftp 8\Temporary\lovelace.lovelace` |
| `/config/configuration.yaml` | `A:\NetSarang\Xftp 8\Temporary\configuration.yaml` |

---

## Lovelace 编辑流程（不可跳步）

> **所有 lovelace 修改，先改 `lovelace`，再同步到 `lovelace.lovelace`。**

1. **Read** `A:\NetSarang\Xftp 8\Temporary\lovelace`
2. **Edit** lovelace JSON
3. **验证** JSON 格式
4. **🚨 必须同步**：
   ```powershell
   Copy-Item "A:\NetSarang\Xftp 8\Temporary\lovelace" "A:\NetSarang\Xftp 8\Temporary\lovelace.lovelace" -Force
   ```
5. **同步实页** — ASA 后台 → 切换 Tab → 点击「💾 保存Tab」
6. **🚨 MD5 验证**（4 路径必须一致）：
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
7. **🚨 实页/预览一致性验证**：
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
   **两个文件时间戳须在同一分钟内。**
8. **重启 HA** 使修改生效

> ⚠️ 禁止直接 SFTP 上传 lovelace 文件，必须走 ASA 后台保存同源流程。

---

## 📊 Lovelace 视图结构

| # | title | 路径 | 管理者 |
|---|-------|------|--------|
| 0 | 家 | `/lovelace/0` | 非 ASA |
| 1 | 电视遥控器 | `/lovelace/1` | 非 ASA |
| 2 | 工作室 | `/lovelace/2` | 非 ASA |
| 3 | **方舟** | `/lovelace/3` ← 核心 | 非 ASA（ASA 后台 saveJSON 写入） |
| 4 | 服务器操作 | `/lovelace/asa-server-ops` | 非 ASA（ASA 后台 saveJSON 写入） |
| 5 | 资讯广场 | `/lovelace/ark_patch` | 非 ASA（ASA 后台 saveJSON 写入） |
| 6 | 服务器规则 | `asa-server-rules` | **ASA（build 管理）** |
| 7 | 部落运维速查 | `info_whiterober` | **ASA（build 管理）** |
| 8-18 | 基地速查 ×11 | `base_isl` ~ `base_bob` | **ASA（build 管理）** |

### 「方舟」视图内部结构 (视图索引 3)
```
方舟 (sections)
├── [Grid] 部落运维速查入口 (仅特定用户可见)
├── [Grid] ASA 服务器操作主卡片 (选中服务器后出现)
│   ├── custom:button-card → 导航到 asa-server-ops
│   └── 动态背景 (来自 sensor.asa_server_themes)
├── [Grid] 服务器规则标题
├── [Grid] 服务器选择网格 (10个服务器按钮)
├── [Grid] 操作系统选择 (Windows/Linux)
├── [Grid] 快速操作按钮
├── [Grid] 补丁信息入口 → 导航到 ark_patch
├── [Grid] 服务器状态显示
└── [Grid] 操作日志
```

---

## 🔌 核心实体

### 输入控制
- `input_select.selected_server` — 当前选中服务器 (Isl/Sco/Cen/...)
- `input_select.selected_action` — 当前操作类型
- `input_text.current_operator` — 操作者
- `input_button.select_server_*` — 各服务器选择按钮
- `input_button.execute_server_action` — 执行服务器操作

### 核心传感器
| Entity ID | 说明 | 关键属性 |
|-----------|------|----------|
| `sensor.asa_server_details` | **核心**：所有服务器数据 | `servers[]`, `server_players{}`, `profile_ports{}` |
| `sensor.asa_server_themes` | 服务器主题配置 | `server_themes{}` (icon, primary_color, bg_image 等) |
| `sensor.asa_server_status` | 服务器整体状态 | |
| `sensor.dialog_server_status` | 弹窗服务器状态 | |
| `sensor.dialog_server_version` | 弹窗版本号 | |
| `sensor.dialog_server_players` | 弹窗玩家数 | |
| `sensor.dialog_server_ingame_time` | 弹窗游戏内时间 | |
| `sensor.dialog_server_combined` | 状态与版本组合 | `status`, `version` |
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
| `sensor.latest_summary_sensor` | 最新摘要（自动选择最新补丁/资讯） |

### 脚本
- `script.set_selected_server` — 设置选中服务器（含操作者记录）
- `script.execute_server_action` — 执行服务器操作
- `script.execute_server_action_with_selection` — 带选择的服务器操作

---

## 🗺️ 服务器映射

| ID | 中文名 | 端口 | RCON |
|----|--------|------|------|
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
| Gen | 创世模拟 | 7795 | — |

### 服务器 MDI 图标 + emoji（apps.yaml 主题用）

| ID | 图标 | MDI | emoji |
|----|------|-----|:---:|
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
| Gen | 🧬 基因 | `mdi:dna` | 🧬 |

---

## 🎨 关键代码模式

### 服务器数据访问
```javascript
states['input_select.selected_server'].state                          // 当前选中服务器
states['sensor.asa_server_details'].attributes.servers                // 所有服务器数据
states['sensor.asa_server_themes'].attributes.server_themes['Isl']    // 服务器主题
// 主题字段: primary_color / dark_color / light_color / bg_image / icon / name / overlay_color
```

### 服务器按钮样式（custom:button-card 三重模板）
- **name**: Jinja2 `[[[ ... ]]]` — 动态服务器名+版本
- **icon**: Jinja2 `[[[ ... ]]]` — 从 themes 获取动态图标
- **styles**（5 层动态）：
  - `icon.color` — 运行中=主题色(选中=light_color, 未选中=primary_color), 离线=灰色
  - `name.color` — 选中=白色, 未选中=主题色
  - `card.background` — 选中=渐变色, 未选中=默认
  - `card.opacity` — 离线=0.5, 运行=1
  - `card.border` — 选中=2px 主题色实线, 未选中=none

### Card Mod
```json
{ "card_mod": { "style": "css-selector { property: value; }" } }
```
部分样式使用 Jinja2 模板动态生成。

### 模板 Sensor (configuration.yaml)
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

## 🛠️ 常见任务

### 添加服务器按钮
1. `apps.yaml` 注册新 profile
2. `configuration.yaml` 添加相关 sensor（如需要）
3. 编辑 `lovelace` 的服务器选择网格，复制现有按钮模板
4. 同步 `lovelace` → `lovelace.lovelace` → ASA 保存

### 修改服务器主题
1. 编辑 `asa_server_monitor_reliable.py` 主题配置逻辑
2. 更新 `sensor.asa_server_themes` 属性生成代码
3. 调整 lovelace 中 Jinja2 模板
4. 同步 `lovelace` → `lovelace.lovelace`

### 添加模板 Sensor
1. 在 `configuration.yaml` 的 `template:` 域下添加 sensor 定义
2. 使用 `unique_id` 确保 entity_id 稳定
3. 在方舟页面 lovelace 卡片中引用新 sensor

### 调试 Lovelace 卡片
1. 编辑 `lovelace` → JSON 校验 → 同步 `lovelace.lovelace`
2. XFtp 自动同步 → HA 前端刷新查看

---

## 🔗 子页面导航

| 子页面 | navigation_path | 管理者 |
|--------|----------------|--------|
| 部落运维速查 | `/lovelace/info_whiterober` | ASA（build 管理） |
| 服务器操作 | `/lovelace/asa-server-ops` | 非 ASA |
| 资讯广场 | `/lovelace/ark_patch` | 非 ASA |
| 基地速查 | `/lovelace/base_isl` ~ `/lovelace/base_bob` | ASA（build 管理） |

---

## 📝 相关文档

- `sensor_template_migration.md` — 模板传感器迁移
- `multi_client_isolation_plan.md` — 多客户端隔离
- `operator_indicator_solution.md` — 操作者指示器
- `card_mod_4.2.0_upgrade_analysis.md` — Card-mod 升级分析

---

## 📄 HTML 格式规范

> 见 `%USERPROFILE%\.copilot\instructions\general.instructions.md`。

## 🔄 版本管理

- 部署使用 `_upload_v173.py`，自动递增版本号
- 服务器保留最近 10 个版本（`len > 10` → 删最旧）
- 重大改动前备份：`Copy-Item` → `asa-admin-baseline-vXXX.html`
- **基线备份范围**（共 10 文件，SFTP 拉取时必须使用以下精确路径）：
  | # | 文件 | 服务器路径 |
  |---|------|-----------|
  | 1 | `asa-admin.html` | `/config/www/asa-data/asa-admin-v{最新版本号}.html` |
  | 2 | `build_lovelace.py` | `/config/build_lovelace.py` |
  | 3 | `preview_server.py` | `/config/preview_server.py` |
  | 4 | `server_colors.json` | `/config/server_colors.json` |
  | 5 | `icon_anti_color.json` | `/config/www/asa-data/icon_anti_color.json` |
  | 6 | `lovelace` | `A:\NetSarang\Xftp 8\Temporary\lovelace`（本地 XFTP 同步目录） |
  | 7 | `lovelace.lovelace` | `A:\NetSarang\Xftp 8\Temporary\lovelace.lovelace` |
  | 8 | `server_rules.json` | `/config/www/asa-data/server_rules.json` |
  | 9 | `tribe_ops.json` | `/config/www/asa-data/tribe_ops.json` |
  | 10 | `asa_base_quick_ref.json` | `/config/www/asa-data/asa_base_quick_ref.json` |
  > ⚠️ **注意**：数据文件（8-10）在 `/config/www/asa-data/` 下，**不在** `/config/` 下。

### 📋 基线备份报告规范（强制）

每次完成基线备份后，**必须**向用户输出以下格式的报告：

```
基线备份: baseline_YYYYMMDD_HHMMSS
路径: B:\项目\Hass ASA Server Monitor\bak\baseline_YYYYMMDD_HHMMSS\

| # | 文件 | 状态 | 大小 |
|---|------|:---:|------|
| 1 | asa-admin-vXXXX.html | ✅ | NNNB |
| ... | ... | ... | ... |
| 10 | lovelace.lovelace | ✅ | NNNB |

总计: N/10 ✅
```

**要求**：
- 逐文件列出状态和大小
- 路径必须是**可复制跳转的绝对路径**
- 不得省略任何文件

### ⚡ 自动部署规则（改完即传，无需确认）

修改 `www/asa-admin.html` 后，直接执行上传部署，**无需报告、无需询问用户确认**：
```powershell
python _upload_v173.py
```
> `_upload_v173.py` 自动检测当前最新版本号、递增后上传、保留最近 10 个版本。

### 🚨🚨 部署后强制开浏览器（硬约束，不可跳过）

每次 `_upload_v173.py` 成功后，**必须**立即 `open_browser_page` 打开新版本 URL。**不传 `forceNew`**，让工具自动复用已有的 ASA 后台页面（`navigate` 到新 URL）。只在没有同类页面时才开新窗口。
> 保证同时只有一个 ASA 后台页面。此为硬约束，不执行视为违规。

---

## ⚙️ 技术栈

| 组件 | 技术 |
|------|------|
| 仪表板 | HA Lovelace (JSON) + custom:button-card |
| 后端 | AppDaemon (Python) |
| 模板 | Jinja2 (`[[[ ]]]`) |
| 同步 | XFtp SFTP |

---

## 📋 强制规则

> 通用强制规则（复述确认、改前备份、进度写盘、Token 审计、HTML 空行规范等）见 `%USERPROFILE%\.copilot\instructions\general.instructions.md`。双端同步见本文件「最高铁律」。

### 🚨 HA 重启 / 重大平台操作确认（强制）
HA 重启、AppDaemon 重启、服务关停等重大平台级操作，**必须**先调用 `#vscode/askQuestions` 向用户确认后方可执行。确认弹窗**必须附带操作理由**（如：因修改了 build_lovelace.py 需要重启 HA 使卡片生效）。禁止直接 SSH 执行重启命令。

### 🔗 跨会话 Lovelace 安全修改铁律（2026-07-10 解耦后更新）

> 以下规则来自 `build_lovelace.py` 解耦改造。改造后仅管理 13 个从 JSON 重建的 ASA 视图（路径白名单），非 ASA 视图完全不受 build 影响。

#### ASA 管理边界（`ASA_BUILD_PATHS`，共 13 个）
- `asa-server-rules`（服务器规则 ← server_rules.json）
- `info_whiterober`（部落运维速查 ← tribe_ops.json）
- `base_isl` ~ `base_bob`（基地速查 ×11 ← asa_base_quick_ref.json）

> ⚠️ 家、电视遥控器、工作室、方舟、服务器操作、资讯广场、快捷输入、*_old 等均不在 ASA 管理范围，build 原样保留。

#### 铁律：非 ASA 页面手动修改无需 build
- **非 ASA 页面**（不在 `ASA_BUILD_PATHS` 中的视图）：手动修改 lovelace 后完全不需要执行 build。即使有人误触「保存Tab」，修改也不会丢失。
- **ASA 页面**（13 个白名单视图）：不可手动改 lovelace JSON。应通过 ASA 后台 UI 编辑 → 保存Tab → build。

#### 铁律：另一个会话改 lovelace 后
- 另一个会话改 lovelace 并 SFTP 上传后：
  - 改的是**非 ASA 页面**：无需任何操作
  - 改的是**ASA 页面**：必须 SSH 执行 `python3 /config/build_lovelace.py`
- `build_lovelace.py` 已自动同步 `.storage/lovelace.lovelace`，无需额外重启 HA
- **ASA 视图按路径识别（非索引），索引变化不影响识别**

### 🪲 CSS 调试铁律（2026-06-30 复盘固化）

> 以下规则来自 info_card 描述行图片+数量功能的 3 轮 debug 教训，**每次涉及 lovelace CSS 修改时必须逐条检查**。

#### 铁律 1：预览区 ≠ HA 镜子
- 预览区用浏览器原生 `<style>` 标签，HA 用 `card_mod` 注入 shadow DOM
- **CSS 属性选择器 `[class*="xxx"]` 在 card_mod 中可能被过滤**，必须用逐类显式选择器（`.ic-block-Isl`、`.ic-block-Sco` 等）
- **验证铁律**：预览通过 ≠ HA 通过，必须两端分别用浏览器验证渲染效果

#### 铁律 2：源码上传 ≠ 已生效
- `build_lovelace.py` / `preview_server.py` 上传到 `/config/` 只是文件到位
- **lovelace 必须通过 ASA 后台「💾 保存Tab」触发重建才能生效**
- Agent 不可跳过用户操作步骤，不可自行 SSH 重启 HA 替代

#### 铁律 3：临时注入必须同步修源码
- 禁止用脚本直接往输出 HTML 注入 CSS 绕过源码 bug
- 一旦预览被重建，注入丢失，bug 暴露
- **正确做法**：修 `build_lovelace.py` + `preview_server.py` 源码，再重建

#### 铁律 4：CSS shorthand 陷阱 — `padding:2px 6px` 覆盖 `padding-right`
- CSS shorthand（如 `padding`、`margin`、`background`）会重置未显式列出的方向
- `padding:2px 6px!important` 后写的会覆盖之前 `padding-right:34px!important`
- **规避**：需要保留单方向值时，用 longhand（`padding-top/right/bottom/left`）或 shorthand 显式写全四值

#### 铁律 5：`!important` 阻断继承
- 基规则 `.ic-qty { color: var(--primary-text-color)!important }` → 子元素无法从父元素继承颜色
- **规避**：可继承属性（`color`、`font-size` 等）的基规则不用 `!important`，让子元素自然继承

#### 铁律 6：双文件重复代码 = bug 温床 ✅ 已修复
- `build_lovelace.py` 和 `preview_server.py` 的 IC_CSS/ig-* 生成逻辑已统一到 `make_ic_css()`（2026-07-15）
- ~~修改时必须**两处都改**，改完必须 grep 确认无遗漏~~
- **已消除**：ig-* CSS 不再在 `preview_server.py` 和 `build_lovelace.py` 中各自维护副本

#### 铁律 7：样式必须且仅允许写入 `make_ic_css()`（2026-07-15 固化）
> 以下规则来自 ig-* CSS 双端重复清除工程的教训。

- **强制**：所有 info_card 相关样式（`.ic-*`、`.ig-*`、`.info-card-block` 等）**必须**定义在 `make_ic_css()` 中
- **禁止**在 `preview_server.py` 或 `build_lovelace.py` 的其他位置（如 `if has_icon_group:`、`if 'info_card' in block_types:` 等条件块内）追加 `css +=` 样式字符串
- **禁止**在 `render_tab_html()` / `build_section_html()` 等函数内直接拼接 CSS 字符串
- **允许例外**：非 info_card 样式（如 `filter-label`、`supply-card`、`card_grid`、`ic-copy-key` 等）可在各自 block_types 条件块内定义
- **改前检查**：grep `css += 'ha-card .ic-` 和 `css += 'ha-card .ig-` 确保只有 `make_ic_css()` 中出现
- **改后验证**：`preview_server.py` 测试 + ASA 后台预览 + 实页 lovelace 三端渲染一致

### 🔴 改前先拉铁律（2026-07-09 复盘固化）

> 以下规则来自旧版 build_lovelace.py 覆盖服务器新版（丢失 _log_step 埋点）导致 ASA 后台"应用"失效的教训。

#### 铁律：修改任何服务器端源码文件前必须先 SFTP 拉取最新版本
- **适用范围**：`build_lovelace.py`、`preview_server.py`、`configuration.yaml`、`automations.yaml`、`scripts.yaml` 等所有 `/config/` 下的文件
- **操作流程**：
  1. `grep` 检查服务器当前版本的关键函数/变量（如 `_log_step`、`VERSION`、`_pf`）
  2. 与本地版本对比，不一致则 **SFTP get 拉取覆盖本地**
  3. 基于拉取后的最新版进行修改
- **禁止**：假设本地副本是最新的，禁止跳过拉取直接编辑后上传
- **检查清单**：改 `build_lovelace.py` 前必查 `_log_step`、`_pf`；改 `preview_server.py` 前必查版本差异

### 🖥️ 先改本地再上传铁律（2026-07-14 复盘固化）

> 以下规则来自直接改服务端文件导致 SSH FS 缓存不一致、import 修复未生效等多轮教训。

#### 铁律：绝不允许直接改服务端文件
- **禁止**使用 SSH FS（`ssh://hass/`）直接编辑服务器文件
- **禁止**用 `replace_string_in_file` 等工具直接操作 `ssh://` 路径
- **禁止**在服务器上写临时脚本原地编辑，导致本地无副本
- **正确流程**：
  1. SFTP 拉取服务器文件覆盖本地
  2. 本地编辑 → 保存
  3. SFTP 上传覆盖服务器
  4. 立即编译验证 + preview_server 测试
- **原因**：SSH FS 写入不可靠（缓存不刷新），直接改服务端导致本地与服务器不一致，后续 diff/覆盖 操作必定出错

### 🧹 死代码清理防孤儿铁律（2026-07-14 复盘固化）

> 以下规则来自 Python 清理脚本删除 `elif ttype == 'server_grid':`（2行）遗留 22 行 handler body 为孤儿代码、导致 preview_server.py 全线崩溃的教训。

#### 铁律：删除 if/elif/else 块前必须理解完整链结构
- **禁止**仅删除 `elif` / `if` 行而不删除对应 body
- **禁止**依赖 brace-counting 判断块边界（Python 无花括号；f-string 内 `{` 不参与语法计数）
- **正确流程**：
  1. 读取目标文件 → 定位死代码块的 **精确起止行**（含 body）
  2. 检查删除后是否会产生 **孤立 `else:`** 或 **链断裂**
  3. 若删除的是 `if/elif/else` 链中的分支 → 用完整块替换（保留 else body），不能只删中间分支
  4. 使用**精确字符串匹配**（非行号）进行替换，每次替换前验证 `count == 1`
  5. 替换后**立即编译验证**（`python3 -m py_compile`），零容忍 SyntaxError
  6. 全部替换完成后 **实际调用验证**（`preview_server.py` 测试），零容忍 NameError

#### 铁律：CRLF 行尾归一化
- 服务器文件使用 `\r\n`（CRLF），本地 Python 三引号字符串使用 `\n`（LF）
- **正确流程**：匹配前先 `content.replace('\r\n', '\n')` 归一化 → 替换 → 恢复 `content.replace('\n', '\r\n')`
- **禁止**：假设服务器文件行尾与本地一致

#### 铁律：删除后验证清单
- [ ] `python3 -m py_compile` 无 SyntaxError
- [ ] `python3 /config/preview_server.py "0" base_quick_ref` 正常输出 HTML
- [ ] `python3 /config/build_lovelace.py` 正常退出
- [ ] 浏览器打开 ASA 后台 → 三编辑器切换 → 预览正常

### 🔍 ASA 后台连接状态检测规范（2026-07-11 复盘固化）

> 以下规则来自使用页面快照通用文本判断连接状态不可靠的教训。

#### 铁律：必须使用 `#connStatus` 元素检测连接状态
- **正确做法**：读取 `span#connStatus` 元素的类名判断连接状态
  - `status.on` → 已连接
  - `status.off` → 未连接
- **禁止**：依赖页面快照中的通用文本（如 `[ref=e4]` 的 generic 文本）判断连接状态
- **原因**：快照中的文本元素 ref 不稳定，每次页面加载可能变化；`#connStatus` 是固定 ID，稳定可靠

### 🔴 JSON 数据文件修改铁律（2026-07-18 复盘固化）

> 以下规则来自直接服务器端 Python 写 `server_rules.json` 3 次失败（文件被未知进程还原）的教训。

#### 铁律：绝不允许服务器端 Python 写 JSON 数据文件

- **禁止**在服务器上执行 `json.dump()` 或任何脚本写入 `/config/www/asa-data/*.json`
- **原因**：文件可能在秒级内被 HA 进程或缓存机制还原，写入无提示、无报错、无效果
- **唯一可靠方式**：**本地修改 → SFTP put 直接覆盖**

#### 强制流程（8 步，不可跳步）

| 步骤 | 操作 | 工具 |
|------|------|------|
| 1. 拉取 | `sftp.get(服务器路径, 本地路径)` | paramiko SFTP |
| 2. 本地修改 | Python 脚本处理 JSON，保存到本地文件 | 本地 Python |
| 3. 本地确认 | 检查本地文件内容正确 | 文本编辑器/print |
| 4. 服务器备份 | `cp 文件 文件.bak` | SSH exec_command |
| 5. SFTP 上传 | `sftp.put(本地, 服务器)` **直接覆盖** | paramiko SFTP |
| 6. SSH 验证 | `python3 -c "import json;..."` 读关键字段 | SSH exec_command |
| 7. 浏览器验证 | 重载页面 → 切菜单 → 确认新数据 | Playwright |
| 8. ASA 保存 | 点「💾 保存Tab」→ build_lovelace | 浏览器操作 |

#### 验证命令模板
```python
# 步骤6：SSH验证（必须实际执行，不依赖脚本自述）
c.exec_command("python3 -c \"import json;d=json.load(open('/config/www/asa-data/server_rules.json'));b=d['tabs'][2]['content_blocks'][2];print(len(b['descriptions']),b['descriptions'][1].get('type','?'))\"")
```

#### 验证失败即回滚
- 若步骤6验证字段与预期不符 → 立即 `cp 文件.bak 文件` 恢复备份
- 禁止继续后续步骤

> ⚠️ **运行时校验**：每次 Agent 启动时需确认 `%USERPROFILE%\.copilot\instructions\general.instructions.md` 可读，若不可读则降级使用本文件内置规则摘要。

---

## 🔗 dino-import 独立项目（CF 部署，2026-08-29 固化）

> dino-import（粑粑服搞事系统）已从 HA 独立为 CF 架构，**不再走 lovelace 双端同步流程**。本智能体负责其前端开发与部署。

### 架构
| 层 | 地址 | 说明 |
|----|------|------|
| CF 前端 | `https://dino.whiterober.ccwu.cc` | Workers 服务 "dino-import"（**纯 Assets 模式**，`/pages/view/dino-import` 会 404） |
| CF 数据后端 | `https://data.whiterober.ccwu.cc` | Tunnel → 物理服务器 192.168.199.3:8080 `dino_backend.py` |
| 前端主文件 | `b:\项目\Hass ASA Server Monitor\dino-import.html` | **文件名不带版本号**（2026-08-29 由 v350 改名，版本号只在内部 `LB_VERSION`） |

### 文件清单
| 文件 | 说明 |
|------|------|
| `dino-import.html` | 前端主源码（`var LB_VERSION = 'v20260829-XXX'` 在此，约 L344） |
| `pwa/manifest.webmanifest` / `pwa/sw.js` | PWA（sw.js 内 `CACHE = 'dino-import-vXXX'` 需与 LB_VERSION 同步） |
| `pwa/icon-192.png` / `pwa/icon-512.png` | PWA 图标（由 `tmp/_pwa_icons.py` 从源图生成，底色系统主题紫 #7c3aed，主体 65% 居中） |
| `独立后端/dino_backend.py` | 物理服务器后端（部署后用户自行重启） |
| `tmp/_deploy_cf.py` | **一键部署脚本**（唯一部署入口） |
| `tmp/_sync_repack2.py` | 打包（被 _deploy_cf.py 调用；新增部署文件须在此加复制逻辑） |

### 部署固定流程（不可跳步）
1. 改 `dino-import.html`（本地）
2. 递增 `LB_VERSION`（`v20260829-XXX`）；若动了 sw.js 缓存策略，同步 `pwa/sw.js` 的 `CACHE` 名
3. `python 'b:\项目\Hass ASA Server Monitor\tmp\_deploy_cf.py'`（async 终端，3 步：打包→wrangler deploy→线上验证）
4. 等输出至「线上 HTTP 200 + 版本一致: True」，`kill_terminal` 清理
5. **浏览器验证**：`page.goto` + `run_playwright_code` 检查关键改动生效

### ⚠️ 部署验证要点（2026-08-29 固化）
- **边缘缓存**：部署脚本线上验证偶发读到旧版本（`版本一致: False`）——wrangler 实际已部署，用 `fetch('https://dino.whiterober.ccwu.cc/?t='+Date.now(), {cache:'no-store'})` 绕过验证，勿据此误判失败
- **主终端 REPL 卡死**：`python -c` 内联常触发 `>>>` REPL 卡终端 → 一律先写脚本文件再 `python '脚本路径'`，用 async 独立终端执行
- **P 盘映射卷不可靠**：图标源图曾放 `P:\共享\`（WinError 1005 卷不可识别）→ 源图复制到项目根目录再处理
- **PWA 版本注意**：manifest 的 `theme_color` 与页面 head `<meta name="theme-color">` 需一致；用户安装后图标更新需卸载重装
- **版本自检**：`dino-import.version` 由打包脚本自动从 LB_VERSION 生成；线上直取该文件会 403（CF 拦无 UA），用浏览器 fetch 验证

### 常见操作
- **新增部署文件**（如 PWA 文件）：在 `tmp/_sync_repack2.py` 的 `flat` 定义后加 `shutil.copy2`（注意 flat 变量顺序）
- **改 PWA 图标**：改 `tmp/_pwa_icons.py`（底色/占比）→ 重新生成 → 部署
- **改应用名**：`pwa/manifest.webmanifest` 的 name/short_name + `dino-import.html` 的 `<title>` + head theme-color
