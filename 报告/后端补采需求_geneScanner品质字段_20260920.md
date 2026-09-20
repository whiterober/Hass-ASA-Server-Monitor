# 后端补采需求：基因枪（WeaponGeneScanner）品质与评分字段

> 提出日期：2026-09-20　提出方：dino-import 前端　触发：用户实测「我背包里的基因枪是传说品质的，你的物品卡为啥什么都没表示？评分、类型你都没显示」

## 一、现状（前端实测，有据）

对 `dino-import` 线上数据（`???_cryo.json.gz` → `geneDevices[]`）逐字段核查：

| 项 | 实测结果 |
|---|---|
| `geneDevices[*].scanners[]` 字段全集 | `class, containerClass, containerId, containerOwnerEosId, containerOwnerPid, containerTribe, containerType, containerX, containerY, containerZ, isBlueprint, key, playerName, slots, tribeId, tribeName, type, x, y, z`（**共 19 个**） |
| 品质字段 `qidx` / `quality` | **不存在**（false） |
| 评分字段 `rating` | **不存在**（false） |
| 属性字段 `stats` | **不存在**（false） |
| 物品索引 `itemsByServer` 中含 `GeneScanner` 的条目 | **0 条** |

样本（用户"板板"的传说基因枪）：
```json
{ "key":"9cd8c366b293e64797d882417cf448a4",
  "class":"PrimalItem_WeaponGeneScanner_C_2147171465", "type":"geneScanner", "isBlueprint":0,
  "tribeId":0, "tribeName":"",
  "containerId":"05d120adf120564b972872c5b06c4d5b", "containerType":"player", "containerClass":"PrimalInventory1",
  "containerTribe":1591945641, "containerOwnerPid":288266681, "playerName":"板板",
  "containerX":147147.59, "containerY":-7997.34, "containerZ":13635.44,
  "slots":[{"f52":858697836,"f84":1287728896,"f88":62,"trait":"nocturnal","level":1,"species":"Kangaroo","dinoClass":"Procoptodon_Character_BP"}] }
```

⇒ 结论：**前端无法显示品质色与评分，因为数据里没有这两个字段**。

## 二、请求补采的字段

| 字段 | 说明 | 用途 |
|---|---|---|
| `qidx` | 品质档位（0 普通 / 1 精良 / 2 稀有 / 3 史诗 / 4 传说 / 5 神话），与其它物品同口径 | 卡片顶部**品质色条**（前端 `lbBpStageCol(qidx)`） |
| `rating` | 评分（Float，与物品/恐龙同口径） | 卡片**评分徽章** |
| `stats` | 属性数组（与 `itemsByServer` 的物品同结构） | 卡片属性行（可选，若基因枪无属性可省） |

补充：`slots[]` 里已出现 `f52` / `f84` / `f88` 三个内部字段（疑似品质/等级编码），若其中含品质信息，也请在文档中给出映射关系（或直接换算成 `qidx`）。

## 三、附带请求（可选）

1. 把 `WeaponGeneScanner` 这类**手持基因设备**也纳入 `itemsByServer` 物品索引（当前 0 条）——纳入后前端可自动获得图标/中文/品质/评分，无需再走 `geneDevices` 专通道。
2. 若基因枪本身无评分（游戏内该物品可能没有评分概念），请明确告知 ⇒ 前端将**不显示评分徽章**（而不是显示 0）。

## 四、前端已做的兼容（本次随版本上线）

- 色条：有 `qidx` 用品质色，**无数据时用主题紫**（原先落到默认灰 `#b8b8b8`，看起来像"什么都没有"）
- 类型徽章：复用物品卡的 `lbTypeBadgeHtml`（当前 geneScanner 落入 `other` 兜底；若其图标为空则不显示，不影响布局）
- 评分：**无 `rating` 字段时一律不显示**（不伪造 0 分）
