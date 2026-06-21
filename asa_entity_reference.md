# ASA 方舟系统实体参考手册

> 涵盖「方舟」视图及关联子页面涉及的所有 Home Assistant 实体。
> 数据来源：`A:\NetSarang\Xftp 8\Temporary\` (XFtp 实时同步自 HA `/config/`)

---

## 一、实体依赖关系图

```
                    ┌──────────────────────────┐
                    │ asa_server_monitor_reliable│  ← AppDaemon Python 脚本
                    │ (apps.yaml 配置)          │
                    └────────────┬─────────────┘
                                 │ 写入
                    ┌────────────▼─────────────┐
                    │ sensor.asa_server_details │  ← 核心数据源
                    │ sensor.asa_server_themes  │
                    │ sensor.ingame_time_cache  │
                    └────────────┬─────────────┘
                                 │ template 引用
              ┌──────────────────┼──────────────────┐
              ▼                  ▼                  ▼
    sensor.dialog_*      sensor.profile_port   sensor.latest_summary
    (弹窗显示用)          sensor.safe_point_coords
              │
              ▼
    ┌─────────────────────┐
    │ input_button.*       │  ← 用户交互入口
    │ input_select.*       │
    │ input_text.*         │
    └─────────┬───────────┘
              │ 触发
    ┌─────────▼───────────┐
    │ script.*             │  ← 自动化执行
    └─────────────────────┘
```

---

## 二、传感器实体完整清单

### 2.1 核心数据传感器

| Entity ID | 类型 | 写入方 | 关键属性 | 读取方 |
|-----------|------|--------|----------|--------|
| `sensor.asa_server_details` | sensor | `asa_server_monitor_reliable.py` | `servers[]` (Status, ServerVersion, ProfileName, OfficialServerVersion), `server_players{}`, `profile_ports{}` | lovelace 方舟视图, dialog_* sensor, scripts |
| `sensor.asa_server_themes` | sensor | `asa_server_monitor_reliable.py` | `server_themes{}` (primary_color, dark_color, light_color, bg_image, icon, name, overlay_color) | lovelace 方舟视图所有按钮 |
| `sensor.ingame_time_cache` | sensor | `asa_server_monitor_reliable.py` | `server_times{}` (server_id → 时间字符串) | `sensor.dialog_server_ingame_time` |
| `sensor.asa_server_status` | sensor | `asa_server_monitor_reliable.py` | 整体状态 | `sensor.dialog_server_status` |
| `sensor.safe_point_coords` | sensor | `asa_server_monitor_reliable.py` | `coords` — 安全点坐标字符串 | lovelace 安全点显示卡片 |

### 2.2 弹窗显示传感器 (template sensor)

| Entity ID | 数据来源 | 逻辑 |
|-----------|----------|------|
| `sensor.dialog_server_status` | `sensor.asa_server_details` → servers → Status | 判断选中服务器在线/离线 |
| `sensor.dialog_server_version` | `sensor.asa_server_details` → servers → ServerVersion | 正则提取版本号 |
| `sensor.dialog_server_players` | `sensor.asa_server_details` → server_players | 读取选中服务器的玩家列表长度 |
| `sensor.dialog_server_ingame_time` | `sensor.ingame_time_cache` → server_times | 读取选中服务器的游戏内时间 |
| `sensor.dialog_server_combined` | `sensor.dialog_server_status` + `sensor.dialog_server_version` | 组合状态+版本号 |
| `sensor.official_server_version` | `sensor.asa_server_details` → servers → OfficialServerVersion | 提取官方版本 |
| `sensor.profile_port` | `sensor.asa_server_details` → profile_ports | 读取选中服务器端口 |

### 2.3 补丁/资讯传感器

| Entity ID | 数据来源 | 写入方 | 说明 |
|-----------|----------|--------|------|
| `sensor.patch_cache` | Discord 主频道 | `discord_patch_bot.py` | 原始缓存 |
| `sensor.patch_channel_cache` | Discord Patch 频道 | `discord_patch_bot.py` | 原始缓存 |
| `sensor.news_cache` | Discord 新闻频道 | `discord_patch_bot.py` | 原始缓存 |
| `sensor.tieba_cache` | Discord 贴吧频道 | `discord_patch_bot.py` | 原始缓存 |
| `sensor.adm_cache` | Discord ADM 频道 | `discord_patch_bot.py` | 原始缓存 |
| `sensor.asb_cache` | Discord ASB 频道 | `discord_patch_bot.py` | 原始缓存 |
| `sensor.patch_description` | `sensor.patch_cache` | template sensor | 格式化显示 |
| `sensor.patch_description_patch` | `sensor.patch_channel_cache` | template sensor | 格式化显示 |
| `sensor.news_patch_description` | `sensor.news_cache` | template sensor | 格式化显示 |
| `sensor.tieba_lz_summary` | `sensor.tieba_cache` | template sensor | 格式化显示 |
| `sensor.adm_preview_summary` | `sensor.adm_cache` | template sensor | 格式化显示 |
| `sensor.asb_summary` | `sensor.asb_cache` | template sensor | 格式化显示 |
| `sensor.latest_summary_sensor` | 6 个缓存 sensor | template sensor | 自动选择最新的 |

### 2.4 版本号提取传感器

| Entity ID | 数据来源 | 正则模式 |
|-----------|----------|----------|
| `sensor.patch_description_version` | `sensor.patch_description` | `(?i)(?:v\|version\|版本)[\\s:：]*([\\d\\.]+)` |
| `sensor.patch_description_patch_version` | `sensor.patch_description_patch` | `\\d+\\.\\d+\\.\\d+\\.\\d+` |
| `sensor.tieba_lz_summary_version` | `sensor.tieba_lz_summary` | `(?i)(?:v\|version\|版本)[\\s:：]*([\\d\\.]+)` |
| `sensor.asb_version` | `sensor.asb_summary` | `\\b\\d+\\.\\d+\\.\\d+(?:\\.\\d+)?\\b` |

---

## 三、输入控制实体

### 3.1 input_select

| Entity ID | 选项 | 默认值 | 用途 |
|-----------|------|--------|------|
| `input_select.selected_server` | Isl, Sco, Cen, Abe, Ext, Ast, Rag, Val, Bob, Los | "" | 全局当前选中服务器 |
| `input_select.selected_action` | 启动/停止/重启/更新/... | — | 待执行的操作类型 |

### 3.2 input_button

| Entity ID | 用途 |
|-----------|------|
| `input_button.select_server_isl` | 选择孤岛 |
| `input_button.select_server_sco` | 选择焦土 |
| `input_button.select_server_cen` | 选择核心岛 |
| `input_button.select_server_abe` | 选择畸变 |
| `input_button.select_server_ext` | 选择灭绝 |
| `input_button.select_server_ast` | 选择星辰 |
| `input_button.select_server_rag` | 选择仙境 |
| `input_button.select_server_val` | 选择瓦尔盖罗 |
| `input_button.select_server_bob` | 选择俱乐部 |
| `input_button.select_server_los` | 选择失落地 |
| `input_button.execute_server_action` | 执行服务器操作 |

### 3.3 input_text

| Entity ID | 用途 |
|-----------|------|
| `input_text.current_operator` | 记录当前操作者信息 |

---

## 四、服务调用链

### 4.1 选择服务器

```
用户点击服务器按钮
    ↓ tap_action: call-service
script.set_selected_server (server_id: "Isl")
    ↓
① input_select.select_option → selected_server = "Isl"
② input_text.set_value → current_operator = "陈思梦 已操作 孤岛"
    ↓
前端响应：
  - sensor.asa_server_details 属性不变
  - lovelace 卡片 Jinja2 模板重新计算
  - 选中按钮高亮 (渐变色背景)
  - 其他按钮恢复默认样式
```

### 4.2 执行服务器操作

```
用户选择操作 → 点击执行
    ↓
script.execute_server_action_with_selection (action: "启动")
    ↓
① input_select.select_option → selected_action
② input_button.press → execute_server_action
    ↓
asa_server_monitor_reliable.py 监听到 input_button 事件
    ↓
调用 ASA API 执行操作
    ↓
更新 sensor.asa_server_details
```

---

## 五、主题配置数据结构

### server_themes 对象结构 (每个服务器一个)

```yaml
Isl:
  name: "孤岛"                    # 中文名
  icon: "mdi:island"             # MDI 图标
  primary_color: "#4CAF50"       # 主色（未选中状态图标色）
  dark_color: "#388E3C"          # 深色（渐变终点）
  light_color: "#81C784"         # 浅色（选中状态图标色、边框色）
  bg_image: "https://..."        # 背景图片 URL
  overlay_color: "rgba(76, 175, 80, 0.7)"  # 叠加色
```

### asa_server_details.servers[] 元素结构

```yaml
- ProfileName: "Isl"
  Status: "Running"              # Running | Stopped | Error
  ServerVersion: "1.0.0.25"      # 当前运行版本
  OfficialServerVersion: "v1.0.0.25"  # 官方最新版本
```

---

## 六、脚本参考

| Script | 字段参数 | 说明 |
|--------|----------|------|
| `script.set_selected_server` | `server_id` (必填) | 设置选中服务器 + 记录操作者 |
| `script.execute_server_action` | 无 | 直接执行 action |
| `script.execute_server_action_with_selection` | `action` | 先选择操作再执行 |

---

## 七、实体命名规则

| 前缀 | 含义 | 示例 |
|------|------|------|
| `sensor.asa_*` | ASA 核心数据 | sensor.asa_server_details |
| `sensor.dialog_*` | 弹窗显示数据 | sensor.dialog_server_status |
| `sensor.*_cache` | 缓存数据 | sensor.patch_cache |
| `sensor.*_summary` | 摘要数据 | sensor.tieba_lz_summary |
| `sensor.*_version` | 版本号 | sensor.asb_version |
| `input_button.select_server_*` | 服务器选择按钮 | input_button.select_server_isl |
| `input_select.selected_*` | 当前选中项 | input_select.selected_server |

---

> 最后更新：2026-06-10
> 数据来源实时同步，如有新增实体请同步更新本文档。
