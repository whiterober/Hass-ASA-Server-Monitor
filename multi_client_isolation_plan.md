# 多客户端/多用户界面隔离方案

> 创建日期：2026-06-09
> 目标：不同客户端、不同用户的操作界面互不同步
> 涉及文件：`lovelace`、`configuration.yaml`、`asa_server_monitor_reliable.py`、`apps.yaml`

---

## 一、问题根因

HA 的 `input_select`、`input_boolean`、`var` 等实体是**全局状态**。用户 A 在电脑上选了"孤岛"服务器，用户 B 在手机上立刻看到同样的变化——所有客户端共享同一个 `input_select.selected_server`。

要实现隔离，需要区分两种状态：

| 状态类型 | 说明 | 共享 or 隔离 |
|---------|------|-------------|
| **读状态**（显示用） | 服务器列表、补丁说明、玩家数等 | 共享（无冲突） |
| **写状态**（操作/选择） | 选服务器、切换选项卡、输入命令等 | 需要隔离 |

---

## 二、识别体系

每个操作需要标记两维信息：

```
操作者 = {用户名} + {客户端标识}
```

| 维度 | 来源 | 示例值 |
|------|------|--------|
| 用户名 | `hass.user.name` | `white` |
| 用户 ID | `hass.user.id` | `abc123...` |
| 浏览器 ID | `browser_mod.browserID` | `a1b2c3d4` |
| 设备类型 | `browser_mod.device` | `Chrome/Windows`、`iOS Safari` |
| IP+端口 | `browser_mod.path` | `192.168.199.11:8124` |

组合后生成唯一操作者 key：

```
white@Chrome-Windows#a1b2c3d4
```

---

## 三、实体分类与隔离策略

### A 类：必须全局（后端依赖，无法完全隔离）

这些实体被 `asa_server_monitor_reliable.py` 直接读取以执行实际操作：

| 实体 | 用途 | 隔离策略 |
|------|------|---------|
| `input_select.selected_server` | 选服务器 | 保持全局，写入时附带操作者信息 |
| `input_select.selected_action` | 选操作 | 保持全局，写入时附带操作者信息 |
| `var.rcon_message` | RCON 命令 | 保持全局，写入时附带操作者信息 |

**隔离方式**：不在状态本身上隔离，而是新增一个**操作锁**实体，确保同一时间只有一个用户/客户端能发起操作。同时仪表板上显示"当前控制者"。

### B 类：可完全隔离（纯 UI 状态，后端不读）

| 实体 | 隔离后存储 |
|------|-----------|
| `input_select.info_square_tab` | `localStorage(item='info_square_tab', user=white)` |
| `input_select.info_tribe_tab` | `localStorage(item='info_tribe_tab', user=white)` |
| `input_select.rcon_quick_commands` | `localStorage(item='rcon_quick', user=white)` |
| `input_boolean.rcon_commands_expanded` | `localStorage(item='rcon_expanded', user=white)` |
| `input_select.player_action_type` | `localStorage(item='player_action', user=white)` |
| `input_select.dialog_server_name` | `localStorage(item='dialog_server', user=white)` |

**隔离方式**：不再使用 HA 全局实体存储这些值，改用 `browser_mod` 的 `localStorage` API，key 中包含用户名，实现每个用户独立状态。

---

## 四、实施步骤

### 阶段 1：安装 browser_mod

1. 通过 HACS → 前端 → 搜索 `browser_mod` → 安装
2. 重启 HA
3. 在任意 lovelace 视图中添加一行验证：
   ```yaml
   - type: markdown
     content: "用户: [[hass.user.name]] | 浏览器: [[browser_mod.browserID]]"
   ```
4. 在不同客户端打开，确认用户名和 browserID 各自不同

### 阶段 2：创建操作者信息实体

在 `configuration.yaml` 中新增两个实体用于追踪当前操作者：

```yaml
input_text:
  current_operator:
    name: "当前操作者"
    initial: ""
    max: 255

timer:
  operator_lock_timeout:
    name: "操作锁超时"
    duration: "00:05:00"   # 5 分钟无操作自动释放锁
```

### 阶段 3：迁移 B 类实体到 localStorage（纯 UI 状态，约 32 处修改）

以 `input_select.info_square_tab` 为例：

**改造前（全局，会同步）**：
```json
{
  "type": "custom:button-card",
  "entity": "input_select.info_square_tab",
  "tap_action": {
    "action": "call-service",
    "service": "input_select.select_option",
    "service_data": {
      "entity_id": "input_select.info_square_tab",
      "option": "ASA PC版本"
    }
  },
  "styles": {
    "background": "[[[ return states['input_select.info_square_tab'].state === 'ASA PC版本' ? '#16a34a' : 'var(--card-background-color)'; ]]]"
  }
}
```

**改造后（localStorage，不同步）**：
```json
{
  "type": "custom:button-card",
  "tap_action": {
    "action": "fire-dom-event",
    "browser_mod": {
      "service": "browser_mod.set_local_storage",
      "data": {
        "key": "info_square_tab_{{{ hass.user.id }}}",
        "value": "ASA PC版本"
      }
    }
  },
  "styles": {
    "background": "[[[ return window.localStorage.getItem('info_square_tab_' + hass.user.id) === 'ASA PC版本' ? '#16a34a' : 'var(--card-background-color)'; ]]]"
  }
}
```

> `key` 中包含 `hass.user.id`，确保不同用户的 tab 选择互不干扰。

涉及修改的 UI 元素清单：

| 原始实体 | lovelace 出现次数 | 替换为 |
|---------|-------------------|--------|
| `input_select.info_square_tab` | ~18 处 | `localStorage('info_square_tab_' + user.id)` |
| `input_select.info_tribe_tab` | ~10 处 | `localStorage('info_tribe_tab_' + user.id)` |
| `input_select.rcon_quick_commands` | ~2 处 | `localStorage('rcon_quick_' + user.id)` |
| `input_boolean.rcon_commands_expanded` | ~2 处 | `localStorage('rcon_expanded_' + user.id)` |
| `input_select.player_action_type` | ~3 处 | `localStorage('player_action_' + user.id)` |

### 阶段 4：A 类实体操作锁 + 控制者显示

`input_select.selected_server` 保持全局，但改造为**带锁操作**：

#### 4a. 操作面板添加控制者标记

在服务器选择区域上方新增：

```json
{
  "type": "markdown",
  "content": "> 操作者：[[hass.user.name]]@[[browser_mod.device]]
> 当前控制：[[ states('input_text.current_operator') or '无人' ]]",
  "card_mod": {
    "style": "ha-card { font-size: 12px; opacity: 0.7; }"
  }
}
```

#### 4b. 服务器按钮改造：点击时声明操作者

```json
{
  "type": "custom:button-card",
  "entity": "input_select.selected_server",
  "tap_action": {
    "action": "fire-dom-event",
    "browser_mod": {
      "service": "browser_mod.sequence",
      "data": {
        "sequence": [
          {
            "service": "input_text.set_value",
            "data": {
              "entity_id": "input_text.current_operator",
              "value": "{{ hass.user.name }}@{{ browser_mod.device }}"
            }
          },
          {
            "service": "input_select.select_option",
            "data": {
              "entity_id": "input_select.selected_server",
              "option": "Isl"
            }
          }
        ]
      }
    }
  }
}
```

#### 4c. 后端读取操作者

在 `asa_server_monitor_reliable.py` 中，每次执行操作前：

1. 读取 `input_text.current_operator`，记录是谁触发的操作
2. 操作完成后，将操作者信息写入通知/日志
3. 如果 `operator_lock_timeout` 超时，清空 `current_operator`

### 阶段 5：跨用户结果通知

当用户 A 执行了操作（如重启服务器），用户 B 的界面上要能看到结果。由于读取状态的实体（如 `sensor.dialog_server_status`）仍然是全局的，所有客户端自动看到更新。

需要额外处理的是**通知归属**——在通知卡片上标注操作者：

```json
{
  "type": "markdown",
  "content": "{% set op = states('input_text.current_operator') %}
{% if op and op != '' %}
> 🔧 {{ op }} 正在操作 {{ states('input_select.selected_server') }}
{% else %}
> 空闲，可以操作
{% endif %}"
}
```

---

## 五、文件变更清单

| 文件 | 变更类型 | 说明 |
|------|---------|------|
| 通过 HACS 安装 | 新增 | `browser_mod` |
| `configuration.yaml` | 新增 | `input_text.current_operator`、`timer.operator_lock_timeout` |
| `lovelace` | 修改 | ~32 处 B 类实体 → localStorage；~5 处 A 类实体加锁 |
| `apps.yaml` | 不变 | — |
| `asa_server_monitor_reliable.py` | 小幅修改 | 读取/写入 `current_operator`；操作日志标注操作者 |

---

## 六、最终效果

| 场景 | 改造前 | 改造后 |
|------|-------|--------|
| 用户 white 在电脑选"孤岛" | 用户 A 手机也显示"孤岛" | 手机保持自己选中的服务器 |
| white 在电脑切到"方舟新闻" tab | 手机也自动切到"方舟新闻" | 手机保持"ASB版本" tab |
| white 输入 RCON 命令 | 手机同步看到输入内容 | 手机看到独立的输入框 |
| 两个用户同时操作不同服务器 | 后端混乱 | 操作锁机制：先到先得，后来者看到锁定提示 |
| 操作结果（服务器启动/停止） | 都看到 | 都看到结果 + 标注操作者用户名 |

---

## 七、风险与注意事项

1. **localStorage 跨设备不共享**：电脑和手机是独立 localStorage，天然隔离——这正是我们需要的
2. **清除浏览器数据会丢失 UI 状态**：localStorage 被清除后，tab 选择等回退到默认值，不影响功能
3. **操作锁死锁**：如果用户关闭浏览器前未释放锁，`timer.operator_lock_timeout`（5 分钟）自动释放
4. **后端全局实体的竞态**：`input_select.selected_server` 仍全局，但加上操作锁后，同一时间只有一个用户在控制
