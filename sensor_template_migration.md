# Home Assistant 模板传感器迁移指南

## 🎯 问题概述

Home Assistant 发出弃用警告：`sensor` 域下旧的 `platform: template` + `sensors:` 语法正被移除，要求将所有旧版模板传感器迁移到 `template:` 域下的新版语法。

**影响范围**: `configuration.yaml` 中 **25 个** 模板传感器需要迁移。

---

## 📋 当前状态分析

### 现有配置结构

| 位置 | 行号 | 内容 |
|------|------|------|
| `template:` | L40-148 | 新版语法，含 1 个 sensor + 5 个 switch |
| `sensor: platform: template` | L172-401 | **旧版语法**，含 25 个模板传感器（待迁移） |

### 旧版语法（需移除）
```yaml
sensor:
  - platform: template
    sensors:
      patch_description:
        friendly_name: "补丁说明"
        value_template: "..."
        icon_template: "mdi:file-document"
```

### 新版语法（目标格式）
```yaml
template:
  - sensor:
      - name: "补丁说明"
        unique_id: patch_description
        state: "..."
        icon: "mdi:file-document"
```

---

## 🔄 字段映射对照表

| 旧版字段 | 新版字段 | 说明 |
|----------|----------|------|
| `friendly_name` | `name` | 显示名称 |
| `value_template` | `state` | 状态值（模板） |
| `icon_template` (静态) | `icon` | 图标（静态字符串） |
| `icon_template` (动态) | `icon` | 图标（模板字符串，兼容） |
| `attribute_templates` | `attributes` | 属性字典 |
| 键名 (如 `patch_description`) | `unique_id` | 保留旧 entity_id |

> **⚠️ 关键**: 使用 `unique_id` 确保迁移后 entity_id 保持不变（如 `sensor.patch_description`），避免破坏 lovelace 卡片、自动化、Python 脚本中的引用。

---

## 📊 待迁移传感器清单 (25个)

### 基础资讯传感器 (1-12)
| # | unique_id | 名称 | 数据来源 |
|---|-----------|------|----------|
| 1 | `patch_description` | 补丁说明 | `sensor.patch_cache` |
| 2 | `patch_description_patch` | Patch频道补丁说明 | `sensor.patch_channel_cache` |
| 3 | `news_patch_description` | 新闻频道补丁说明 | `sensor.news_cache` |
| 4 | `tieba_lz_summary` | 贴吧楼主摘要 | `sensor.tieba_cache` |
| 5 | `adm_preview_summary` | ADM预告摘要 | `sensor.adm_cache` |
| 6 | `asb_summary` | ASB摘要 | `sensor.asb_cache` |
| 7 | `tieba_lz_full` | 贴吧楼主全文 | `sensor.tieba_lz_full` |
| 8 | `adm_preview_full` | ADM预告全文 | 静态值 |
| 9 | `asb_full` | ASB全文 | `sensor.asb_full` |
| 10 | `patch_description_full` | 补丁说明全文 | 静态值 → Python 动态更新 |
| 11 | `patch_channel_patch_info` | Patch频道补丁信息 | 静态值 → Python 动态更新 |
| 12 | `news_patch_channel_info` | 新闻频道补丁信息 | 静态值 → Python 动态更新 |

### 服务器状态传感器 (13-19)
| # | unique_id | 名称 | 说明 |
|---|-----------|------|------|
| 13 | `official_server_version` | 官方服务器版本 | 从 `sensor.asa_server_status` 属性读取 |
| 14 | `dialog_server_status` | 弹窗服务器状态 | 根据选中服务器判断在线/离线 |
| 15 | `dialog_server_version` | 弹窗服务器版本 | 正则提取版本号 |
| 16 | `dialog_server_players` | 弹窗服务器玩家数 | 玩家列表计数 |
| 17 | `patch_description_version` | 补丁说明版本号 | 从补丁说明正则提取 |
| 18 | `patch_description_patch_version` | Patch频道补丁版本号 | 从Patch补丁说明正则提取 |
| 19 | `tieba_lz_summary_version` | 贴吧楼主摘要版本号 | 从贴吧摘要正则提取 |

### 综合与衍生传感器 (20-25)
| # | unique_id | 名称 | 说明 |
|---|-----------|------|------|
| 20 | `asb_version` | ASB版本号 | 正则提取版本号 |
| 21 | `latest_summary_sensor` | 最新摘要 | 按时间排序取最新非空摘要 |
| 22 | `profile_port` | 当前服务器端口 | Python 动态更新 |
| 23 | `safe_point_coords` | 当前地图安全点坐标 | Python 动态更新 + attributes |
| 24 | `dialog_server_ingame_time` | 弹窗服务器游戏内时间 | 从缓存读取 |
| 25 | `dialog_server_combined` | 服务器状态与版本 | 综合传感器 + attributes |

---

## 🛠️ 步骤 1 — 新增模板传感器（新版语法）

将以下 YAML 插入到 `configuration.yaml` 的 `template:` 部分。**建议**：添加为新的 `- sensor:` 列表项（紧接在现有第 48 行 `- switch:` 之前）。

### 完整新版配置

```yaml
template:
  # ========== 现有传感器（保留） ==========
  - sensor:
      - name: "123pan_jump_tile"
        state: "123网盘"
        attributes:
          entity_picture: "https://pp.myapp.com/ma_icon/0/icon_54190090_1753492095/256"

  # ========== 新增：迁移的模板传感器 ==========
  - sensor:
      # --- 1. 补丁说明 ---
      - unique_id: patch_description
        name: "补丁说明"
        icon: mdi:file-document
        state: >
          {{ states('sensor.patch_cache') if states('sensor.patch_cache') != 'unknown' else '暂无补丁说明' }}

      # --- 2. Patch频道补丁说明 ---
      - unique_id: patch_description_patch
        name: "Patch频道补丁说明"
        icon: mdi:file-document
        state: >
          {{ states('sensor.patch_channel_cache') if states('sensor.patch_channel_cache') != 'unknown' else '暂无Patch频道补丁说明' }}

      # --- 3. 新闻频道补丁说明 ---
      - unique_id: news_patch_description
        name: "新闻频道补丁说明"
        icon: mdi:file-document
        state: >
          {{ states('sensor.news_cache') if states('sensor.news_cache') != 'unknown' else '暂无新闻频道补丁说明' }}

      # --- 4. 贴吧楼主摘要 ---
      - unique_id: tieba_lz_summary
        name: "贴吧楼主摘要"
        icon: mdi:forum
        state: >
          {{ states('sensor.tieba_cache') if states('sensor.tieba_cache') != 'unknown' else '暂无贴吧信息' }}

      # --- 5. ADM预告摘要 ---
      - unique_id: adm_preview_summary
        name: "ADM预告摘要"
        icon: mdi:bullhorn
        state: >
          {{ states('sensor.adm_cache') if states('sensor.adm_cache') != 'unknown' else '暂无ADM预告信息' }}

      # --- 6. ASB摘要 ---
      - unique_id: asb_summary
        name: "ASB摘要"
        icon: mdi:information
        state: >
          {{ states('sensor.asb_cache') if states('sensor.asb_cache') != 'unknown' else '暂无ASB信息' }}

      # --- 7. 贴吧楼主全文 ---
      - unique_id: tieba_lz_full
        name: "贴吧楼主全文"
        icon: mdi:forum
        state: >
          {{ states('sensor.tieba_lz_full') if states('sensor.tieba_lz_full') != 'unknown' else '暂无贴吧全文' }}

      # --- 8. ADM预告全文 ---
      - unique_id: adm_preview_full
        name: "ADM预告全文"
        icon: mdi:bullhorn
        state: "暂无ADM预告信息"

      # --- 9. ASB全文 ---
      - unique_id: asb_full
        name: "ASB全文"
        icon: mdi:information
        state: >
          {{ states('sensor.asb_full') if states('sensor.asb_full') != 'unknown' else '暂无ASB全文' }}

      # --- 10. 补丁说明全文 ---
      - unique_id: patch_description_full
        name: "补丁说明全文"
        icon: mdi:file-document
        state: "暂无补丁说明"

      # --- 11. Patch频道补丁信息 ---
      - unique_id: patch_channel_patch_info
        name: "Patch频道补丁信息"
        icon: mdi:file-document
        state: "Patch Channel Info"
        attributes:
          content: "暂无Patch频道补丁信息"

      # --- 12. 新闻频道补丁信息 ---
      - unique_id: news_patch_channel_info
        name: "新闻频道补丁信息"
        icon: mdi:file-document
        state: "暂无新闻频道补丁信息"
        attributes:
          content: "暂无新闻频道补丁信息"

      # --- 13. 官方服务器版本 ---
      - unique_id: official_server_version
        name: "官方服务器版本"
        icon: mdi:tag
        state: >
          {{ state_attr('sensor.asa_server_status', 'official_version') | default('N/A') }}

      # --- 14. 弹窗服务器状态 ---
      - unique_id: dialog_server_status
        name: "弹窗服务器状态"
        icon: >
          {% set server_id = states('input_select.selected_server') %}
          {% set servers = state_attr('sensor.asa_server_details', 'servers') %}
          {% if servers and server_id %}
            {% set matches = servers | selectattr('ProfileName','equalto', server_id) | list %}
            {% set server = matches[0] if matches|length > 0 else None %}
            {% if server and server.Status == 'Running' %}
              mdi:server
            {% else %}
              mdi:server-off
            {% endif %}
          {% else %}
            mdi:help-circle
          {% endif %}
        state: >
          {% set server_id = states('input_select.selected_server') %}
          {% set servers = state_attr('sensor.asa_server_details', 'servers') %}
          {% if servers and server_id %}
            {% set matches = servers | selectattr('ProfileName','equalto', server_id) | list %}
            {% set server = matches[0] if matches|length > 0 else None %}
            {% if server %}
              {% if server.Status == 'Running' %}在线{% else %}离线{% endif %}
            {% else %}未找到
            {% endif %}
          {% else %}请选择服务器
          {% endif %}

      # --- 15. 弹窗服务器版本 ---
      - unique_id: dialog_server_version
        name: "弹窗服务器版本"
        icon: mdi:tag
        state: >
          {% set server_id = states('input_select.selected_server') %}
          {% set servers = state_attr('sensor.asa_server_details', 'servers') %}
          {% if servers and server_id %}
            {% set matches = servers | selectattr('ProfileName','equalto', server_id) | list %}
            {% set server = matches[0] if matches|length > 0 else None %}
            {% if server and server.ServerVersion is defined and server.ServerVersion != 'N/A' %}
              {% set found = server.ServerVersion | regex_findall('(\\d+\\.?\\d*)') %}
              {% set version = found[0] if found | length > 0 else 'N/A' %}
              {{ version }}
            {% else %}N/A
            {% endif %}
          {% else %}请选择服务器
          {% endif %}

      # --- 16. 弹窗服务器玩家数 ---
      - unique_id: dialog_server_players
        name: "弹窗服务器玩家数"
        icon: mdi:account-group
        state: >
          {% set server_id = states('input_select.selected_server') %}
          {% set server_players = state_attr('sensor.asa_server_details', 'server_players') %}
          {% if server_players and server_id in server_players %}
            {{ server_players[server_id] | length }}
          {% else %}0
          {% endif %}

      # --- 17. 补丁说明版本号 ---
      - unique_id: patch_description_version
        name: "补丁说明版本号"
        icon: mdi:tag
        state: >
          {% set value = states('sensor.patch_description') %}
          {% set result = value | regex_findall('(?i)(?:v|version|版本)[\\s:：]*([\\d\\.]+)') %}
          {{ result[0] if result else 'N/A' }}

      # --- 18. Patch频道补丁版本号 ---
      - unique_id: patch_description_patch_version
        name: "Patch频道补丁版本号"
        icon: mdi:tag
        state: >
          {% set value = states('sensor.patch_description_patch') %}
          {% set result = value | regex_findall('\\d+\\.\\d+\\.\\d+\\.\\d+') %}
          {{ result[0] if result else 'N/A' }}

      # --- 19. 贴吧楼主摘要版本号 ---
      - unique_id: tieba_lz_summary_version
        name: "贴吧楼主摘要版本号"
        icon: mdi:tag
        state: >
          {% set value = states('sensor.tieba_lz_summary') %}
          {% set result = value | regex_findall('(?i)(?:v|version|版本)[\\s:：]*([\\d\\.]+)') %}
          {{ result[0] if result else 'N/A' }}

      # --- 20. ASB版本号 ---
      - unique_id: asb_version
        name: "ASB版本号"
        icon: mdi:tag
        state: >
          {% set value = states('sensor.asb_summary') %}
          {% set result = value | regex_findall('\\b\\d+\\.\\d+\\.\\d+(?:\\.\\d+)?\\b') %}
          {{ result[0] if result else 'N/A' }}

      # --- 21. 最新摘要 ---
      - unique_id: latest_summary_sensor
        name: "最新摘要"
        icon: mdi:file-document
        state: >
          {% set entities = [
            states.sensor.patch_cache,
            states.sensor.patch_channel_cache,
            states.sensor.news_cache,
            states.sensor.tieba_cache,
            states.sensor.adm_cache,
            states.sensor.asb_cache
          ] %}
          {% set latest = entities
            | selectattr('attributes.created_at', 'defined')
            | sort(attribute='attributes.created_at', reverse=True)
            | list
            | first %}
          {{ latest.state if latest is not none and latest.state not in ['unknown', 'unavailable', ''] else '暂无摘要' }}

      # --- 22. 当前服务器端口 ---
      - unique_id: profile_port
        name: "当前服务器端口"
        icon: mdi:lan
        state: "{{ states('sensor.profile_port') }}"

      # --- 23. 当前地图安全点坐标 ---
      - unique_id: safe_point_coords
        name: "当前地图安全点坐标"
        icon: mdi:map-marker
        state: "{{ state_attr('sensor.safe_point_coords', 'coords') | default('') }}"
        attributes:
          coords: ""

      # --- 24. 弹窗服务器游戏内时间 ---
      - unique_id: dialog_server_ingame_time
        name: "弹窗服务器游戏内时间"
        icon: mdi:clock
        state: >
          {% set server_id = states('input_select.selected_server') %}
          {% set times = state_attr('sensor.ingame_time_cache', 'server_times') %}
          {% if times and server_id in times %}
            {{ times[server_id] }}
          {% else %}
            N/A
          {% endif %}

      # --- 25. 服务器状态与版本 ---
      - unique_id: dialog_server_combined
        name: "服务器状态与版本"
        icon: >
          {% if is_state('sensor.dialog_server_status', '在线') %}
            mdi:server
          {% else %}
            mdi:server-off
          {% endif %}
        state: >
          {% if is_state('sensor.dialog_server_status', '在线') %}
            {{ states('sensor.dialog_server_version') }}
          {% else %}
            离线 ({{ states('sensor.dialog_server_version') }})
          {% endif %}
        attributes:
          status: "{{ states('sensor.dialog_server_status') }}"
          version: "{{ states('sensor.dialog_server_version') }}"
```

---

## 🗑️ 步骤 2 — 移除旧版 sensor 配置

**删除** `configuration.yaml` 中第 172-401 行的整个旧版 `sensor:` 块：

```yaml
# ❌ 删除以下所有内容（L172 - L401）
sensor:
#  - platform: feedparser          ← 注释也一并移除，或保留后单独注释
#    name: Ark News
#    ...
  - platform: template             ← 旧版语法
    sensors:                       ← 注意：这里是 "sensors"（复数）
      patch_description:
        ...
      ... (共25个传感器)
      dialog_server_combined:
        ...
```

具体删除范围：
```
L172: sensor:
L173: #  - platform: feedparser (注释)
L174-L181: 注释掉的 feedparser 配置
L182:   - platform: template
L183-L401: 所有旧版模板传感器定义
```

---

## 📊 影响分析

### ✅ 不受影响（无需修改）

| 文件 | 原因 |
|------|------|
| `discord_patch_bot.py` | 引用的是 `sensor.patch_cache`、`sensor.patch_channel_cache` 等**缓存实体**，非模板传感器 |
| `asa_server_monitor_reliable.py` | 通过 `self.set_state()` 直接设置实体状态。迁移后 entity_id 不变，`sensor.patch_description_full`、`sensor.asb_full` 等 7 个动态更新传感器继续正常工作 |
| `apps.yaml` | 仅引用缓存实体 (`sensor.patch_cache`, `sensor.patch_channel_cache` 等) |
| `lovelace` (UI) | 21 处引用 `sensor.patch_description`、`sensor.dialog_server_*` 等。因使用 `unique_id` 保留 entity_id，**无需修改 lovelace** |

### ⚠️ 需注意的传感器

以下 7 个传感器被 Python 代码动态更新（`asa_server_monitor_reliable.py`），模板定义仅提供初始值和元数据：

| 传感器 | Python 设置位置 |
|--------|----------------|
| `sensor.patch_description_full` | L1647 |
| `sensor.patch_channel_patch_info` | L1722 |
| `sensor.news_patch_channel_info` | L1783 |
| `sensor.tieba_lz_full` | L1845 |
| `sensor.adm_preview_full` | L1908 |
| `sensor.asb_full` | L1971 |
| `sensor.profile_port` | L139 |
| `sensor.safe_point_coords` | L154 |

---

## ⚡ 步骤 3 — 重启 Home Assistant

迁移完成后，执行以下操作之一：

### 方式 A：仅重载模板实体（推荐，无需重启）
1. 进入 **开发者工具** → **YAML**
2. 点击 **模板实体** 旁边的 **重载**
3. 或使用服务调用：`homeassistant.reload_config_entry` → target: `template`

### 方式 B：完整重启
1. **Settings** → **System** → **Restart** → **Restart Home Assistant**
2. 或执行命令：`ha core restart`

---

## ✅ 验证清单

迁移后请逐一检查：

- [ ] **开发者工具 → 状态**：搜索 `sensor.patch_description`，确认 entity_id 未变
- [ ] 所有 25 个传感器状态显示正常（非 `unknown` / `unavailable`）
- [ ] **Lovelace 仪表盘**：资讯广场卡片正常显示
- [ ] **服务器弹窗**：服务器选择、状态、版本、玩家数显示正常
- [ ] **补丁说明卡片**：补丁版本号提取正常
- [ ] **ASB 卡片**：ASB 信息显示正常
- [ ] **日志** (`Settings → System → Logs`)：无模板渲染错误
- [ ] **Discord Bot** (`discord_patch_bot.py`)：消息推送正常
- [ ] **自动刷新** (`asa_server_monitor_reliable.py`)：服务器状态刷新正常

---

## 🔙 回滚方案

如果迁移后出现问题，可快速回滚：

1. 用旧版 `sensor: platform: template` 替换新版 `template: - sensor:` 配置
2. 重载模板实体或重启 HA
3. entity_id 和历史数据不会丢失（HA 注册表中保留）

---

## 📝 技术说明

### 为什么 entity_id 可能改变
新版模板语法根据 `name` 字段自动生成 entity_id（中文名 → 拼音）。通过显式设置 `unique_id`，HA 会在实体注册表中匹配已有实体，从而**保留旧的 entity_id**（如 `sensor.patch_description` 而不是 `sensor.bu_ding_shuo_ming`）。

### 自引用模板传感器
`profile_port` 和 `safe_point_coords` 的 `state` 模板引用了自身的 `states()` 值。这是特殊模式：Python 代码通过 API 直接设置状态值，模板定义仅提供友好的 `name` 和 `icon`。模板的 `state` 表达式在实体状态已被外部设置时不会覆盖。

---

*文档生成时间: 2026-06-09*
*Home Assistant 配置迁移：旧版 `platform: template` → 新版 `template:` 语法*
