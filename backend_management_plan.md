# 服务器规则 / 部落运维速查 / 部落基地速查 — 后台管理方案

> **状态**：计划阶段，待审批
> **选定方案**：方案 B — 外部 Web 编辑器 + HA API
> **数据来源**：`速查表.md`（板服配置速查 = 服务器规则，其余 = 部落运维）
> **创建日期**：2026-06-10

---

## 1. 现状分析

### 1.1 服务器规则（方舟视图内）— 对应「板服配置速查」

- **位置**：方舟视图（lovelace views[3]），`"heading": "服务器规则 ➥"`（约行 1450）
- **当前 lovelace 状态**：仅有标题和分割线，**无任何内容**（数据在 `速查表.md` 中，尚未迁入 HA）
- **实际内容**（来自 `速查表.md`）：

| 子节 | 内容类型 | 结构特征 |
|------|---------|---------|
| 基础倍率设置 | 配置项列表 | emoji + 名称 + 倍率值 + 配置文件 + 配置代码 |
| 附加配置项 | 开关列表 | ✅ + 描述 + 配置文件 + 配置代码 |
| 制造调整项 | 配方覆盖 | 配方名 + 原料清单 + 代码（`<details>` 折叠） |
| 拾取调整项 | 品质调整 | 按地图分类的掉落品质提升项 |

- **数据特点**：文本为主，夹杂 Game.ini 代码块，部分用折叠（`<details>`）隐藏长代码

### 1.2 部落运维速查（`/lovelace/info_whiterober`）

- **位置**：lovelace views[5]，行 3737–4043
- **当前 lovelace 状态**：仅 2 个 tab —「补给速查」「采集速查」
- **实际内容**（来自 `速查表.md`，远超当前 lovelace 范围）：

| # | 速查表名称 | 内容类型 | 是否按服务器分列 | lovelace 现状 |
|---|-----------|---------|:---:|-------------|
| 1 | 经验获取速查 | 参考表格（规则说明） | ✗ | ❌ 未迁入 |
| 2 | 无线传送箱速查 | 按服务器列表 | ✓ | ❌ 未迁入 |
| 3 | 泰克套部署速查 | 按服务器列表 + 图片 | ✓ | ❌ 未迁入 |
| 4 | 畸变发光肩宠速查 | 参考卡片（4 宠对比） | ✗ | ❌ 未迁入 |
| 5 | 铠护犬功能速查 | 命令表 + 装备表 | ✗ | ❌ 未迁入 |
| 6 | 持续消耗速查 | **大型**服务器×物品矩阵表 | ✓ | ✅ 已迁入（作为「补给速查」） |
| 7 | 高效产出速查 | 按产出资源的采集流程表 | 部分 | ✅ 已迁入（作为「采集速查」） |

- **现状问题**：当前 lovelace 只有 2 个 tab，遗漏了 5 个子节；tab 名称「补给速查」也不准确（实际是「持续消耗速查」）

### 1.3 部落基地速查（`/lovelace/base_whiterober`）

- **位置**：lovelace views[7]，行 4044–4351
- **当前 lovelace 状态**：子 tab「英灵殿」「龙舍」，硬编码 HTML 表格
- **当前问题**：**不感知选中服务器** — 无论选哪个服务器都显示同样内容

---

## 2. 核心问题总结

| # | 问题 | 影响 |
|---|------|------|
| 1 | **无后台管理** | 所有内容修改需直接编辑 lovelace JSON 或外部 md 文件 |
| 2 | **内容与代码耦合** | HTML 表格嵌入 JSON 深层，难以查找编辑 |
| 3 | **基地速查无服务器感知** | 不根据 `input_select.selected_server` 切换内容 |
| 4 | **lovelace 内容不完整** | 5/7 的部落运维子节未迁入 HA，仅存在于 `速查表.md` |
| 5 | **图片 URL 冗长** | 补给品/地点截图 URL 单行可达 500+ 字符 |
| 6 | **表格结构无封装** | 每个 `<tr>` 手工编写，无模板/组件 |
| 7 | **服务器规则为空** | 数据在 `速查表.md` 中但从未接入 HA |

---

## 3. 方案 B 总体架构

```
┌──────────────────────────────────────────────────────────────┐
│              管理后台 — asa-admin.html (HA www/)               │
│                                                               │
│  ┌────────────┐  ┌──────────────┐  ┌─────────────────────┐  │
│  │ 服务器规则   │  │ 部落运维编辑器 │  │    部落基地编辑器    │  │
│  │ (板服配置)   │  │ (7+ 子节)     │  │ (服务器维度+Tab切换) │  │
│  └────────────┘  └──────────────┘  └─────────────────────┘  │
│                                                               │
│  认证：HA www/ 同源 WebSocket，复用浏览器登录态               │
└────────────────────────┬──────────────────────────────────────┘
                         │ HA WebSocket API
                         │ 读写 var 实体
                         ▼
┌──────────────────────────────────────────────────────────────┐
│                   HA 数据存储层                                │
│                                                               │
│  var.asa_server_rules             — 服务器规则 JSON            │
│  var.asa_tribe_ops_ref            — 部落运维全部子节 JSON      │
│  var.asa_base_quick_ref           — 部落基地速查 JSON          │
└────────────────────────┬──────────────────────────────────────┘
                         │ Jinja2 模板渲染
                         ▼
┌──────────────────────────────────────────────────────────────┐
│                   HA Lovelace 展示层                           │
│                                                               │
│  Template Sensor → 渲染 JSON 为 HTML（含服务器感知）          │
│  markdown card → 引用 sensor 属性展示                         │
└──────────────────────────────────────────────────────────────┘
```

---

## 4. 数据结构设计

### 4.1 服务器规则（板服配置速查）

**内容来源**：`速查表.md` # 板服配置速查

**结构分析**：四个子节，每节有不同格式。设计为一个包含 section 数组的 JSON。

```json
{
  "sections": [
    {
      "id": "base_rates",
      "title": "基础倍率设置",
      "description": "仿启示录官服",
      "type": "config_list",
      "items": [
        {
          "icon": "🦖",
          "name": "驯服速度",
          "value": "6倍",
          "config_file": "GameUserSettings.ini",
          "config_code": "TamingSpeedMultiplier=6"
        },
        {
          "icon": "🌾",
          "name": "采集倍率",
          "value": "6倍",
          "config_file": "GameUserSettings.ini",
          "config_code": "HarvestAmountMultiplier=6"
        }
      ]
    },
    {
      "id": "extra_config",
      "title": "附加配置项",
      "type": "toggle_list",
      "items": [
        {
          "enabled": true,
          "name": "平台可安装自动炮塔",
          "config_file": "GameUserSettings.ini",
          "config_code": "OverrideStructurePlatformPrevention=True"
        }
      ]
    },
    {
      "id": "crafting_overrides",
      "title": "制造调整项",
      "type": "crafting_list",
      "items": [
        {
          "name": "血精鸡尾酒 HEMOGOBLIN COCKTAIL",
          "ingredients": [
            {"name": "血袋 Blood Pack", "count": 4},
            {"name": "角鼻龙毒脊刺 Cerato Venom Spinel", "count": 3},
            {"name": "麻醉药 Narcotic", "count": 3}
          ],
          "config_file": "Game.ini",
          "config_code": "ConfigOverrideItemCraftingCosts=(...)"
        }
      ]
    },
    {
      "id": "loot_adjustments",
      "title": "拾取调整项",
      "type": "loot_list",
      "items": [
        {
          "map": "畸变",
          "category": "地下宝箱",
          "adjustment": "质量提升",
          "note": "代码详见Beacon的Whiterober工程"
        }
      ]
    }
  ]
}
```

**字段说明**：
- `type` 决定编辑器和渲染器使用哪种模板：
  - `config_list`：emoji + 名称 + 值 + 配置代码（一行一条）
  - `toggle_list`：✅ 开关 + 名称 + 配置代码
  - `crafting_list`：配方名 + 原料子列表 + 可折叠代码块
  - `loot_list`：按地图的掉落品质调整

---

### 4.2 部落运维速查

**内容来源**：`速查表.md` 中除「板服配置速查」外的全部内容

**结构分析**：7 个子节，每节结构不同。设计为一个 tab 数组，每个 tab 有 type 字段区分渲染方式。

```json
{
  "tabs": [
    {
      "id": "xp_share",
      "name": "经验获取速查",
      "description": "经验分配规则",
      "order": 1,
      "type": "reference_table",
      "columns": ["场景", "经验分配规则"],
      "rows": [
        {
          "scenario": "玩家骑目标龙，部落队友杀经验龙",
          "rule": "目标龙获得50%经验，队友100%经验，玩家0%经验"
        }
      ]
    },
    {
      "id": "wireless_transmitter",
      "name": "无线传送箱速查",
      "description": "各服务器传送盘部署位置",
      "order": 2,
      "type": "server_list",
      "servers": [
        {
          "server": "Isl",
          "name": "孤岛",
          "count": "2/4",
          "locations": [
            {"name": "英灵殿", "image_url": null},
            {"name": "2号水洞", "image_url": null}
          ]
        },
        {
          "server": "Sco",
          "name": "焦土",
          "count": "1/4",
          "locations": [
            {"name": "阿紫", "image_url": null}
          ]
        }
      ]
    },
    {
      "id": "tek_suit",
      "name": "泰克套部署速查",
      "description": "各服务器泰克套部署位置",
      "order": 3,
      "type": "server_list",
      "servers": [
        {
          "server": "Isl",
          "name": "孤岛",
          "locations": [
            {"name": "码头", "image_url": "https://cdn.nlark.com/..."}
          ]
        }
      ]
    },
    {
      "id": "glow_pets",
      "name": "畸变发光肩宠速查",
      "description": "四种发光肩宠对比",
      "order": 4,
      "type": "card_grid",
      "columns": 4,
      "cards": [
        {
          "name": "灯泡犬",
          "image_url": "https://cdn.nlark.com/...",
          "feature": "较大容量"
        }
      ]
    },
    {
      "id": "armadoggo",
      "name": "铠护犬功能速查",
      "description": "铠护犬命令与装备",
      "order": 5,
      "type": "mixed_content",
      "content_blocks": [
        {
          "block_type": "text",
          "style": "warning",
          "text": "如果伴随模式下的铠护犬快被杀死，它将挖洞逃走..."
        },
        {
          "block_type": "table",
          "title": "命令表",
          "columns": ["指令", "名称", "说明", "表情"],
          "rows": [
            {
              "command_icon": "https://cdn.nlark.com/...",
              "name": "Sit 坐下",
              "description": "将坐下并待在原位",
              "emote_icon": "https://cdn.nlark.com/...",
              "emote_name": "Bark 汪汪叫"
            }
          ]
        },
        {
          "block_type": "table",
          "title": "装备表",
          "columns": ["装备", "效果"],
          "rows": [
            {
              "equip_icon": "https://cdn.nlark.com/...",
              "name": "随伴的诱饵陷阱",
              "effect": "引诱敌对生物分散注意力，冷却60秒"
            }
          ]
        }
      ]
    },
    {
      "id": "supply_consumption",
      "name": "持续消耗速查",
      "description": "各服务器持续消耗品补给位置",
      "order": 6,
      "type": "server_grid",
      "columns": [
        {"label": "孤岛", "server": "Isl"},
        {"label": "核心岛", "server": "Cen"},
        {"label": "焦土", "server": "Sco"},
        {"label": "畸变", "server": "Abe"},
        {"label": "灭绝", "server": "Ext"}
      ],
      "items": [
        {
          "id": "supply_001",
          "name": "高级步枪子弹",
          "icon_url": "https://cdn.nlark.com/...",
          "category": "常规消耗",
          "locations": {
            "Isl": [
              {"name": "码头", "image_url": "https://cdn.nlark.com/..."},
              {"name": "龙舍", "image_url": "https://cdn.nlark.com/..."}
            ],
            "Sco": [],
            "Abe": [
              {"name": "畸变号", "image_url": "https://cdn.nlark.com/...", "badge": "×2"}
            ]
          }
        }
      ]
    },
    {
      "id": "efficient_farming",
      "name": "高效产出速查",
      "description": "各资源最佳采集流程",
      "order": 7,
      "type": "farming_table",
      "columns": ["产出", "图", "采集点", "流程"],
      "rows": [
        {
          "output_icon": "https://cdn.nlark.com/...",
          "map": "全图",
          "location": "野外",
          "procedure": "1.骑高负重生物 2.带跳蛛|星尾兽|..."
        }
      ]
    }
  ]
}
```

**`type` 渲染策略一览**：

| type | 说明 | 渲染模板 | 编辑器组件 |
|------|------|---------|-----------|
| `reference_table` | 通用参考表格 | `<table>` 键值对照 | 表格行列编辑器 |
| `server_list` | 按服务器分组的列表 | 服务器标题 + 地点列表 | 服务器折叠面板 + 地点列表 |
| `card_grid` | 卡片网格（如肩宠对比） | N 列卡片网格 | 卡片列表编辑器 |
| `mixed_content` | 混合内容（文字+嵌套表格） | 顺序渲染各 block | 内容块管理器 |
| `server_grid` | 服务器×物品矩阵表 | 大型交叉表格 | 二维矩阵编辑器 |
| `farming_table` | 采集流程参考表 | `<table>` 多列 | 表格行列编辑器 |

---

### 4.3 部落基地速查

**设计原则**：根据当前选中的服务器显示不同的基地列表。

```json
{
  "servers": {
    "Isl": {
      "name": "孤岛",
      "tabs": [
        {
          "id": "yingling",
          "name": "英灵殿",
          "description": "综合主基地",
          "locations": [
            {
              "category": "繁育",
              "name": "繁育场",
              "coords": "45.2, 32.8",
              "image_url": "...",
              "features": ["孵蛋器×4", "空调×12"]
            }
          ]
        },
        {
          "id": "longshe",
          "name": "龙舍",
          "description": "生物存储基地",
          "locations": []
        }
      ]
    },
    "Cen": {
      "name": "核心岛",
      "tabs": []
    }
  },
  "default_server": "*",
  "*": {
    "name": "默认",
    "tabs": [
      {
        "id": "placeholder",
        "name": "暂无数据",
        "description": "该服务器暂无基地配置",
        "locations": []
      }
    ]
  }
}
```

**服务器感知渲染流程**（Template Sensor）：
```
1. 读取 input_select.selected_server.state → 如 "Isl"
2. data.servers["Isl"] 存在 → 使用孤岛的 tabs
   不存在 → 使用 data.servers["*"] 的默认 tabs
3. 渲染 tabs 子导航 + 对应地点表格
```

---

## 5. 编辑器功能设计

### 5.1 服务器规则编辑器

**对应内容**：「板服配置速查」的四个子节

```
┌────────────────────────────────────────────────────────────┐
│ 服务器规则编辑器 (板服配置)                                  │
│                                                             │
│ [基础倍率设置] [附加配置项] [制造调整项] [拾取调整项]         │
│ ▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁ │
│                                                             │
│ 当前: 基础倍率设置            [描述: 仿启示录官服        ]   │
│                                                             │
│ ┌─ 配置项列表 ──────────────────────────────────────────┐  │
│ │                                                        │  │
│ │ 1. 🦖 [驯服速度    ] = [6倍  ]                         │  │
│ │    文件: [GameUserSettings.ini  ▾]                     │  │
│ │    代码: [TamingSpeedMultiplier=6              ]       │  │
│ │    [删除]                                              │  │
│ │                                                        │  │
│ │ 2. 🌾 [采集倍率    ] = [6倍  ]                         │  │
│ │    文件: [GameUserSettings.ini  ▾]                     │  │
│ │    代码: [HarvestAmountMultiplier=6            ]       │  │
│ │    [删除]                                              │  │
│ │                                                        │  │
│ │ [+ 添加配置项]                                         │  │
│ └────────────────────────────────────────────────────────┘  │
│                                                             │
│ [保存全部]                                                  │
└────────────────────────────────────────────────────────────┘
```

**配置项表单字段**（按 type 不同）：
- `config_list`：icon emoji 输入、名称、值、配置文件下拉、配置代码
- `toggle_list`：启用开关、名称、配置文件、配置代码
- `crafting_list`：配方名、原料列表（名称+数量）、配置文件、代码（textarea，适合长代码）
- `loot_list`：地图下拉、分类、调整内容、备注

---

### 5.2 部落运维速查编辑器

**对应内容**：7 个子节，不同 type 有不同编辑 UI

整体布局：左侧 tab 列表，右侧根据选中 tab 的 type 切换对应的编辑面板。

```
┌────────────────────────────────────────────────────────────┐
│ 部落运维速查编辑器                                          │
│                                                             │
│ ┌─ Tab 列表 ──────┐  ┌─ 编辑: 持续消耗速查 ───────────────┐ │
│ │                  │  │                                     │ │
│ │ ● 经验获取速查    │  │ 类型: [server_grid ▾]              │ │
│ │   参考表格        │  │ 名称: [持续消耗速查            ]    │ │
│ │                  │  │ 描述: [各服务器持续消耗品补给位置]   │ │
│ │ ● 无线传送箱速查  │  │                                     │ │
│ │   服务器列表      │  │ 表格列:                             │ │
│ │                  │  │ [孤岛(Isl)] [核心岛(Cen)] [焦土(Sco)]│ │
│ │ ● 泰克套部署速查  │  │ [畸变(Abe)] [灭绝(Ext)] [+添加列]   │ │
│ │   服务器列表      │  │                                     │ │
│ │                  │  │ ┌─ 物品列表 ──────────────────────┐ │ │
│ │ ● 畸变发光肩宠    │  │ │                                  │ │ │
│ │   卡片网格        │  │ │ [搜索...]          [+ 添加物品]   │ │ │
│ │                  │  │ │                                  │ │ │
│ │ ● 铠护犬功能速查  │  │ │ 1. 🖼️ 高级步枪子弹               │ │ │
│ │   混合内容        │  │ │    孤岛:码头,龙舍 | 畸变:畸变号×2 │ │ │
│ │                  │  │ │    [编辑] [删除]                  │ │ │
│ │ ● 持续消耗速查 ◀  │  │ │                                  │ │ │
│ │   服务器矩阵      │  │ │ 2. 🖼️ 简易步枪子弹               │ │ │
│ │                  │  │ │    孤岛:码头 | 焦土:中央车站       │ │ │
│ │ ● 高效产出速查    │  │ │    [编辑] [删除]                  │ │ │
│ │   采集流程表      │  │ │                                  │ │ │
│ │                  │  │ └──────────────────────────────────┘ │ │
│ │ [+ 添加Tab]      │  │                                     │ │
│ │                  │  │ [保存]                               │ │
│ └──────────────────┘  └─────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────┘
```

**按 type 的编辑面板**：

| type | 编辑器组件 |
|------|-----------|
| `reference_table` | 列定义 + 行列表编辑器（每行一个键值对） |
| `server_list` | 服务器选择 + 该服务器下的地点编辑器（名称+图片） |
| `card_grid` | 列数设置 + 卡片列表（名称+图片+特性标签） |
| `mixed_content` | 内容块管理器：添加/排序/编辑 block；block 可选 text、table、image 等子类型 |
| `server_grid` | 列管理（服务器绑定）+ 物品列表 + 每个物品的「按服务器-地点」多列编辑面板 |
| `farming_table` | 列定义 + 行列表，每行多列文本 |

---

### 5.3 部落基地速查编辑器

```
┌────────────────────────────────────────────────────────────┐
│ 部落基地速查编辑器                                          │
│                                                             │
│ 编辑服务器: [孤岛 ▾] [核心岛 ▾] ... [默认* ▾]              │
│ ▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁ │
│ 当前: 孤岛                                        [复制自...]│
│                                                             │
│ ┌─ Tab ───────────┐  ┌─ Tab: 英灵殿 ─────────────────────┐ │
│ │ ● 英灵殿         │  │                                    │ │
│ │   综合主基地      │  │ 名称: [英灵殿                ]     │ │
│ │   地点:3         │  │ 描述: [综合主基地            ]     │ │
│ │                  │  │                                    │ │
│ │ ○ 龙舍           │  │ ┌─ 地点列表 ────────────────────┐ │ │
│ │   生物存储基地    │  │ │                                 │ │ │
│ │   地点:2         │  │ │ 1. 分类: [繁育  ▾]              │ │ │
│ │                  │  │ │    名称: [繁育场          ]      │ │ │
│ │ [+ 添加Tab]      │  │ │    坐标: [45.2, 32.8      ]      │ │ │
│ │                  │  │ │    图像: [https://...] [选择]    │ │ │
│ │                  │  │ │    特性: [孵蛋器×4] [空调×12]    │ │ │
│ │                  │  │ │    [删除]                        │ │ │
│ │                  │  │ │                                 │ │ │
│ │                  │  │ │ [+ 添加地点]                     │ │ │
│ │                  │  │ └─────────────────────────────────┘ │ │
│ │                  │  │                          [保存Tab]  │ │
│ └──────────────────┘  └────────────────────────────────────┘ │
│                                                             │
│ [保存孤岛全部]  [保存所有服务器]                             │
└────────────────────────────────────────────────────────────┘
```

---

## 6. 数据流与渲染

### 6.1 整体数据流

```
[编辑器操作] → 构造 JSON → JSON.stringify
    │
    ▼
[HA WebSocket] → var.set_value
    │
    ▼
[var entity 更新] → state 变化
    │
    ▼
[Template Sensor 重新计算]
    ├─ attributes.rendered_rules → 服务器规则 HTML
    ├─ attributes.rendered_tribe_ops → 部落运维 HTML（当前 tab）
    └─ attributes.rendered_base → 基地速查 HTML（服务器感知）
    │
    ▼
[Lovelace markdown card] → 引用对应 sensor 属性
```

### 6.2 部落运维速查 — Tab 切换渲染

在 lovelace 的 `info_whiterober` 视图中：
- 保留 `input_select.info_tribe_tab` 的用法，但选项需要从 2 个扩展到 7 个
- 或者改为**单一 markdown card**，内部用 HTML/CSS/JS 实现 tab 切换（由 Template Sensor 渲染完整的 tab bar + content）
- 推荐后者：Template Sensor 一次渲染全部 tab 的 HTML，前端用 JS 切换显示，避免 7 个 conditional card

### 6.3 服务器规则渲染

Template Sensor 按 sections 顺序渲染，每节根据 `type` 选模板：
- `config_list` → emoji 项列表 + 代码
- `toggle_list` → ✅ 项列表 + 代码
- `crafting_list` → 配方名 + 原料清单 + 折叠代码
- `loot_list` → 按地图的调整列表

---

## 7. HA 实体清单

### var（数据存储）

| Entity ID | Name | Max | 说明 |
|-----------|------|-----|------|
| `input_text.asa_server_rules` | ASA 服务器规则 | 32768 | 板服配置 JSON |
| `input_text.asa_tribe_ops_ref` | ASA 部落运维速查 | 65536 | 7 个子节全部数据 |
| `input_text.asa_base_quick_ref` | ASA 部落基地速查 | 32768 | 按服务器的基地数据 |

> `asa_tribe_ops_ref` 的 max 需要最大，因为包含 7 个子节 + 大量图片 URL。

### Template Sensor（HTML 渲染）

| Entity ID | 输入 | 说明 |
|-----------|------|------|
| `sensor.asa_server_rules_html` | `input_text.asa_server_rules` | 板服配置渲染 |
| `sensor.asa_tribe_ops_html` | `input_text.asa_tribe_ops_ref` | 部落运维渲染（含全 tab HTML） |
| `sensor.asa_base_quick_ref_html` | `input_text.asa_base_quick_ref` | 基地速查渲染（服务器感知） |

### 现有实体需调整

| Entity | 调整 |
|--------|------|
| `input_select.info_tribe_tab` | 选项从 `["补给速查","采集速查"]` 扩展到 7 个（或废弃，改由 Template Sensor 内部 tab 切换） |

---

## 8. 编辑器与 HA 通信

托管在 HA `www/` 目录，同源免跨域。

```
[浏览器已登录 HA] → [打开 /local/asa-admin.html]
    ↓
同源 → WebSocket ws://host/api/websocket
    ↓
1. 连接并认证（复用 HA 登录态）
2. 调用 var.set_value 写入 JSON
```

如需从 HA lovelace 中导航到编辑器，在方舟页面加一个 button-card，`navigate` 到 `/local/asa-admin.html`。

---

## 9. 图片管理

当前图片来源：
- `pic.whiterober.com`（lovelace 现有）
- `cdn.nlark.com`（速查表.md 中的 yuque 图床）

**策略**：
- 编辑器提供图片 URL 输入 + 即时预览
- 提供常用 URL 别名快捷选择（如「码头」「龙舍」等常用截图）
- 长期可选：统一迁移到一个图床，或迁移到 HA `www/images/asa/` 本地

---

## 10. 数据迁移说明

**迁移来源**：
1. lovelace 中已有的「补给速查」和「采集速查」HTML 数据
2. `速查表.md` 中尚未迁入的 5 个子节（经验获取、无线传送箱、泰克套部署、畸变发光肩宠、铠护犬功能）

**迁移方式**：
- 先在编辑器中按 JSON 结构手工录入，验证渲染效果
- lovelace 现有 HTML 数据用脚本辅助提取（Python 解析 `<table>` 标签），自动转换为 JSON 的 `server_grid` 格式
- 速查表.md 中内容手工录入编辑器

**迁移后清理**：
- lovelace `info_whiterober` 中删除硬编码 HTML，改为引用 `sensor.asa_tribe_ops_html`
- lovelace `base_whiterober` 中删除硬编码 HTML，改为引用 `sensor.asa_base_quick_ref_html`
- 方舟视图中的「服务器规则」标题下方添加 markdown card，引用 `sensor.asa_server_rules_html`

---

## 11. 文件清单

| 文件 | 位置 | 说明 |
|------|------|------|
| `asa-admin.html` | HA `www/` | 后台编辑器单页应用 |
| `configuration.yaml` | HA `/config/` | 新增 3 个 input_text + 3 个 template sensor |
| `lovelace` | 本地 `Temporary/` | 替换硬编码 HTML 为 sensor 引用；扩展 tab 数量 |
| `lovelace.lovelace` | 本地 `Temporary/` | 同步 lovelace |

---

> **下一步**：审批数据类型设计（第 4 节，特别是部落运维的 6 种 type）和编辑器交互（第 5 节）。
