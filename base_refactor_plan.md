# 部落基地重构计划

## 目标

ASA 管理页的部落基地编辑器，渲染产出必须和 `/lovelace/base_whiterober_old` **逐字节一致**。所有内嵌 JS 完全保留。

## 数据现状

- 旧视图 `base_whiterober_old` 使用 `raw_html` 类型，单 Tab 396K 字符
- 数据结构：`servers: {Isl: {tabs: [{type:"raw_html", html:"..."}]}}`
- 内嵌：section 切换 JS、SVG 图标、inline CSS、设备表格

## 实施步骤

### 1. 数据建模（从 HTML 提取可变数据）

不拆散 HTML，而是**提取可变字段**为结构化数据，剩余固定结构用模板还原。

```json
{
  "servers": {
    "Isl": {
      "tabs": [{
        "name": "补给速查",
        "type": "base_supply",
        "sections": [{
          "name": "英灵殿",
          "rows": [{
            "device": {"name":"低温仓", "icon_url":"...", "capacity":"72"},
            "storage": [{"icon_url":"...", "name":"Ovis"}],
            "consumables": [{"icon_url":"...", "name":"Kibble"}]
          }]
        }]
      }]
    }
  }
}
```

### 2. HTML 模板

固定结构（CSS class、section 切换 JS）用 Python 字符串模板，可变字段用 `{var}` 替换。

```python
BASE_SUPPLY_TEMPLATE = '''
<div class="section-tab-bar base-title-header">
  {section_tabs}
</div>
{sections_html}
'''

SECTION_TEMPLATE = '''
<div id="section-{section_id}-body" class="accordion-body collapsed">
  <table>...
    {rows_html}
  </table>
</div>
'''
```

**必需保留的 JS 代码**（逐字复制，不改）：
- section tab 切换 onclick handler
- `getRootNode()` Shadow DOM 穿透逻辑

### 3. ASA 管理编辑器

对齐服务器矩阵的交互模式：

```
┌─ 服务器 Tab 栏 ──────────────────────────┐
│ 孤岛  焦土  核心岛  畸变  灭绝            │
├─ 左侧 Tab 列表 ──┬─ 右侧编辑区 ──────────┤
│ 补给速查          │ Section: [英灵殿 ▾]   │
│ 采集速查          │                        │
│                  │ 行 1: 设备 | 存储 | 消耗│
│ + 添加Tab         │ 行 2: 设备 | 存储 | 消耗│
│                  │ + 添加行               │
│                  │ 💾 保存               │
└──────────────────┴───────────────────────┘
```

- 服务器切换：顶部 server-tab
- Tab 切换：左侧列表
- Section 切换：右侧下拉
- 行编辑：设备 / 存储 / 消耗品 三个区域
- 存储和消耗品支持多条（增删）

### 4. 渲染（build_lovelace.py）

```
views[7] = {
  Tab 栏 (horizontal-stack + mod-card)
  + 条件卡片 (匹配 input_select.info_tribe_tab)
    └─ custom:mod-card
      └─ custom:tailwindcss-template-card
        └─ 模板生成的 HTML
}
```

- `card_mod` CSS 和旧视图一致
- `input_select.info_tribe_tab` 复用（Tab 名 = "补给速查"/"采集速查"）

### 5. 预览（preview_server.py）

- 新增 `base_quick_ref` source
- 按服务器 + Tab 生成单页预览

### 6. 数据迁移

从旧视图的 396K raw_html 中**程序化提取**结构化数据，填充到新格式。
此步骤需先完成模板和渲染，再验证产出和旧视图一致。

## 不改的

- 旧视图的所有 JS（section 切换、事件处理）
- CSS class 名和结构
- SVG 图标
- HA 前端兼容的 `getRootNode()` 写法
