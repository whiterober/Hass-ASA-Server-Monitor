# HA 操作者指示器实现方案

> 日期：2026-06-09
> 目标：在 Home Assistant 仪表板上显示"谁在操作哪个服务器"

---

## 一、最终效果

| 状态 | 显示内容 |
|------|---------|
| 空闲 | `等待操作` |
| 有人操作 | `陈思梦 已操作 孤岛` |

用户名从 HA 人员实体动态获取，服务器中文名从 AppDaemon 配置实时读取。

---

## 二、架构设计

```
用户点击服务器按钮
        ↓
script.set_selected_server 执行
        ↓
① 设置 input_select.selected_server
② 设置 input_text.current_operator = "陈思梦 已操作 孤岛"
        ↓
③ 自动化触发 → 追加时间戳记录到 var.operation_log
        ↓
④ Lovelace markdown 卡片读取并显示
```

---

## 三、实现细节

### 3.1 存储：`configuration.yaml`

```yaml
input_text:
  current_operator:
    name: "当前操作者"
    initial: ""
    max: 255
    icon: mdi:account-key
```

### 3.2 核心脚本：`scripts.yaml`

```yaml
set_selected_server:
  alias: "设置选中服务器"
  sequence:
    - service: input_select.select_option
      data:
        entity_id: input_select.selected_server
        option: "{{ server_id }}"
    - service: input_text.set_value
      data:
        entity_id: input_text.current_operator
        value: >-
          {% set uid = context.user_id %}
          {% set ns = namespace(name=uid[:8]~'…') %}
          {% for p in states.person %}
            {% if p.attributes.user_id == uid %}
              {% set ns.name = p.attributes.friendly_name %}
            {% endif %}
          {% endfor %}
          {% set themes = state_attr('sensor.asa_server_themes', 'server_themes') or {} %}
          {% set server = themes.get(server_id, {}) %}
          {{ ns.name }} 已操作 {{ server.get('name', server_id) }}
```

**关键点**：

| 技术 | 说明 |
|------|------|
| `context.user_id` | HA 前端触发的服务调用自动携带当前用户 ID |
| `states.person` | 遍历所有 person 实体，按 `attributes.user_id` 匹配 |
| `namespace` | Jinja2 需要 `namespace` 对象才能在循环内修改变量 |
| `state_attr('sensor.asa_server_themes', 'server_themes')` | 从 AppDaemon 配置动态获取服务器 ID→中文名映射 |

### 3.3 用户识别原理

HA 的 person 实体存储了与 HA 用户的关联：

```json
{
  "entity_id": "person.chen_si_meng",
  "state": "home",
  "attributes": {
    "user_id": "498bc277e50647158f11501bea5f55a7",
    "friendly_name": "陈思梦"
  }
}
```

当用户从前端点击按钮时，`context.user_id` 自动填充为 `498bc277e50647158f11501bea5f55a7`，脚本通过遍历 `states.person` 找到匹配的 `friendly_name`。

### 3.4 服务器名映射

从 `sensor.asa_server_themes` 的 `server_themes` 属性动态获取，无需硬编码：

| 缩写 | 中文名 |
|------|--------|
| Isl | 孤岛 |
| Sco | 焦土 |
| Cen | 核心岛 |
| Abe | 畸变 |
| Ext | 灭绝 |
| Ast | 星辰 |
| Rag | 仙境 |
| Val | 瓦尔盖罗 |
| Bob | 俱乐部 |
| Los | 失落地 |

---

## 四、踩坑记录

| 问题 | 原因 | 解决方案 |
|------|------|---------|
| `{{ user }}` 返回空 | 脚本中 `user` 变量未定义 | 改用 `context.user_id` |
| `{% set name = ... %}` 循环内无效 | Jinja2 循环内 `set` 作用域限制 | 改用 `namespace` 对象 |
| `expand('person')` 返回 `[]` | 脚本中不支持此函数 | 改用 `states.person` |
| REST API 测试 `context.user_id` 报错 | API 上下文无此变量 | 仅前端触发时可用，API 测试需硬编码 ID |
| 操作日志 JSON 损坏 | 手动拼接 JSON 导致换行符未转义 | 该用 `JSON.parse`→修改→`JSON.stringify` 流程 |

---

## 五、涉及文件

| 文件 | 变更 |
|------|------|
| `configuration.yaml` | 新增 `input_text.current_operator` |
| `scripts.yaml` | 修改 `set_selected_server`，新增操作者记录步骤 |
| `scripts.yaml` | 修改 `execute_server_action_with_selection`、`kick_player`（同步更新操作者） |
| `configuration.yaml` | 新增自动化：操作者变化时追加到 `var.operation_log` |
| `configuration.yaml` | 新增 `var.operation_log` 存储操作历史 |
| `lovelace` | 服务器面板末尾新增 markdown 卡片显示操作者 |

---

## 六、扩展：支持多用户

当有新用户加入时，只需在 HA **设置→人员** 中创建对应的 person 实体，关联其 HA 用户账号。脚本会自动识别，无需修改代码。

验证方法（HA 开发者工具→模板）：
```jinja2
{% for p in states.person %}
{{ p.attributes.user_id }} → {{ p.attributes.friendly_name }}
{% endfor %}
```
