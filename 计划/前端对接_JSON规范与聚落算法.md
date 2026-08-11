# 前端对接规范：JSON 输出与坐标聚落算法

> 用途：给前端对接数据。本文档描述 TransferIdentityFixAPI 体系下各 JSON 文件的**输出字段规范**与**坐标聚落算法规范**。
> 日期：2026-08-11 ｜ 数据流：`exe/dll 生成 json → 聚类脚本 → settlements.json → HTML`

---

## 1. 概述与数据流

```
┌─────────────┐   ┌─────────────┐
│ dll（实服） │   │ exe（离线）  │
│ tamed.json  │   │ cryo.json   │
└──────┬──────┘   └──────┬──────┘
       │                 │
       ▼                 ▼
┌──────────────────────────────┐
│ gen_settlements_v3.py 聚类    │  → settlements.json
└──────────────┬───────────────┘
               ▼
┌──────────────────────────────┐
│ gen_settlement_html_v2.py    │  → 部落聚落 HTML（前端参考实现）
└──────────────────────────────┘
```

- **`*_tamed.json`**：实服插件（dll）在线枚举**放出生物**，含世界坐标 + owner + 印痕者。
- **`*_cryo.json`**：离线 exe 解析存档**球内生物**，含球所在容器坐标 + 印痕者 + 玩家/部落表。
- **`settlements.json`**：聚类脚本产物，把生物归到「聚落」，供前端分组展示。

---

## 2. 数据文件总览

| 文件 | 生成端 | 内容 | 关键字段 |
|------|--------|------|----------|
| `<abbr>_tamed.json` | dll（实服） | 放出生物 | `x/y/z`、`ownerPid/ownerName`、`imprinterName/imprinterEosId`、`tribeId` |
| `<abbr>_cryo.json` | exe（离线） | 球内生物 | `containerX/Y/Z`、`imprinterName/imprinterEosId`、`containerId/Type`、`players`、`tribes` |
| `<abbr>_settlements.json` | 聚类脚本 | 聚落归属 | `settlements`、`pods[]`、`tamed[]`、`scattered` |

---

## 3. `*_cryo.json` 字段规范（exe 输出）

顶层：`{ serverId, arkPath, elapsedMs, stats, players[], tribes{}, cryopod[] }`

### 3.1 `players[]`（玩家数据）
```json
{ "pid": 880859190, "eosId": "0002a034b2f14582a2e953741073bcb8",
  "name": "蒜头", "characterName": "人类" }
```
| 字段 | 类型 | 说明 |
|------|------|------|
| `pid` | int64 | 角色唯一 ID（**判定口径**）|
| `eosId` | string | 玩家唯一 EOSID（32hex，账户级）|
| `name` | string | 账户名（PlayerName）|
| `characterName` | string | 角色名（PlayerCharacterName）|

> 边界：某玩家在**本服无角色数据**时不在此段（如跨服板板在 Isl 缺失）。

### 3.2 `tribes{}`（部落表）
```json
"1912594779": { "name": "基纽特战队", "ownerName": "歌星星", "ownerPid": 233391766,
  "ownerEosId": "", "members": [ { "name": "嘎巴丸", "pid": 233391766, "eosId": "" } ] }
```
| 字段 | 说明 |
|------|------|
| `ownerPid` | 部落长角色 pid（判定）|
| `members[]` | `{name, pid, eosId}`，重名角色以 pid 区分 |

### 3.3 `cryopod[]`（球内生物）—— 坐标 + 印痕者关键字段
```json
{
  "dinoId1": 5740778, "dinoId2": 437319863, "name": "小蜜", "level": 1,
  "tribeId": 1589589881,
  "containerId": "6f49b802...", "containerType": "display",
  "containerName": "", "containerTribe": 1589589881,
  "containerX": -318380.0, "containerY": -169503.0, "containerZ": -10486.0,
  "imprinterName": "板板", "imprinterEosId": "00025a2b9cf14195...",
  "downloadedAtMs": 1786438781236, "packedAtWorldSec": 233033901.336
}
```
| 字段 | 类型 | 说明 |
|------|------|------|
| `containerX/Y/Z` | double | **球所在容器（冰箱/展示台/背包建筑）的世界坐标**；无坐标 = `0` |
| `containerType` | string | `fridge`/`display`/`stand`/`player`/`other`/`hospital` |
| `containerId` | string(32hex) | 容器 inventory uuid |
| `imprinterName` | string | 印痕者（繁育者）角色名；无印痕 = `""` |
| `imprinterEosId` | string | 印痕者 EOSID（32hex）；无 = `""` |

> **坐标说明**：球是物品对象不在 `ActorTransforms`，坐标取自其所在容器建筑（见 §5）。

---

## 4. `*_tamed.json` 字段规范（dll 输出）

顶层：`{ savedAt, count, dinos[] }`

```json
{
  "id": "387355_125397295", "dinoId1": 387355, "dinoId2": 125397295,
  "name": "粉鯊1", "level": 216, "gender": "FEMALE", "tribeId": 1912594779,
  "x": -310126.1, "y": -162985.0, "z": -13994.3,
  "ownerPid": 0, "ownerName": "",
  "imprinterName": "嘎巴丸", "imprinterEosId": "00023cf443714568b5e273e50d6e152b",
  "imprintingQuality": 1.0000,
  "downloadedAtWorldSec": 217115924.462, "tamedAtWorldSec": 0.000
}
```
| 字段 | 类型 | 说明 |
|------|------|------|
| `x/y/z` | double | **放出生物世界坐标**（ActorLocation）|
| `ownerPid` | int64 | 拥有者/驯服者 pid（`OwningPlayerID`）；**多成员部落共享龙 = 0** |
| `ownerName` | string | 拥有者角色名 |
| `imprinterName` | string | 印痕者角色名；无 = `""` |
| `imprinterEosId` | string | 印痕者 EOSID；无 = `""` |

> **owner 与 imprinter 区别**：owner=驯服/拥有者（单人部落有值）；imprinter=繁育印记者（能区分部落内成员，可跨部落）。

---

## 5. 坐标数据源（ActorTransforms）

- 存档 `custom` 表 `ActorTransforms` 存**所有放置对象的世界坐标**。
- 布局：**72B/条** = `key(16B guid)` + `x double @+16` + `y double @+24` + `z double @+32` + 旋转/缩放（其余字节）。
- 容器坐标链路：球 `containerId`(inventory uuid) → `inventory_host` 映射 → **建筑宿主 key**（如 `CryoFridge_C_<id>`）→ ActorTransforms 查坐标。

---

## 6. 坐标聚落算法（gen_settlements_v3.py）

### 6.1 聚类流程
```
1. 按容器聚合：containerId → {x, y, type, tribeId, 球数}
2. 排除 player 背包容器 + 无坐标容器
3. 按 tribeId 分组（同一部落的容器才可能聚成同一聚落）
4. 组内 DBSCAN（eps=6000，按容器坐标）
5. 输出 settlements + 每条生物 settlementId/distance + 离散
```

### 6.2 参数
| 参数 | 值 | 说明 |
|------|-----|------|
| `eps` | **6000** | 聚落距离阈值（单位）；一个基地跨度 ~5500 需 6000 |
| 分组 | 按 `tribeId` | 部落 → 聚落层级 |
| 聚类对象 | **容器** | 非球（同一容器多球坐标相同，无意义）|

### 6.3 离散规则
- 未落入任何聚落的**容器** → 归独立特殊聚落 `scattered`（「离散」）

---

## 7. `settlements.json` 输出规范（聚类结果）

```json
{
  "eps": 6000,
  "settlements": {
    "S1": { "id": "S1", "tribeId": 1912594779, "tribeName": "基纽特战队",
            "center": {"x": -320015.9, "y": -169097.0},
            "radius": 2387.1, "containers": 67, "pods": 6371 }
  },
  "scattered": { "id": "scattered", "name": "离散", "containers": 0, "pods": 0 },
  "pods": [ { "dinoId": "5740778_437319863", "name": "小蜜", "tribeId": 1589589881,
              "containerType": "display", "settlementId": "S1", "distance": 123.4 } ],
  "tamed": [ { "dinoId": "387355_125397295", "name": "粉鯊1", "ownerPid": 0,
               "ownerName": "", "settlementId": "S3", "distance": 456.7 } ]
}
```
| 字段 | 说明 |
|------|------|
| `settlements.{id}` | 聚落：中心坐标、半径、容器数、球数 |
| `settlementId` | 每条生物归属的聚落 ID；`scattered`=离散 |
| `distance` | 生物到聚落中心的距离 |

---

## 8. 聚落成员规则（gen_settlement_html_v2.py）

### 8.1 印痕者 → pid 反查（resolve_imprinter）
```
imprinterName 匹配 players.characterName（角色级）
  + imprinterEosId 匹配 players.eosId（账户级）  → 综合定位 pid
重名角色（"人类"×3）用 EOS 区分；小号（同 EOS 多角色）用角色名区分
```

### 8.2 仅限本部落（count_imprinter）
- 印痕者反查到 pid → 必须 ∈ 该聚落所属部落的 `members[].pid` 才计入冠名
- 未反查到 pid（如跨服板板在 Isl players 缺失）→ 若印痕者名 ∈ 该部落 `members[].name` 则计入（名字兜底）
- **跨部落印痕者排除**（如嘎巴丸在北境游骑兵聚落）

### 8.3 聚落成员判定（top_owners，即冠名规则）
> **冠名（top_owners）规则 = 判定是否为本聚落成员的规则**：经 §8.1 反查 + §8.2 本部落过滤后的印痕者，按数量排序取前 3 名，即该聚落的**成员（管理者）**，聚落名即成员名组合。
- 取印痕者数量**前 3 名** → 作为聚落成员
- 数量 < 第一名 **5%** 的，若绝对数量也 **< 50 条** → 不算成员（去掉明显过少的）
- **绝对数量 ≥ 50 条的不受 5% 比例约束**（占比低但留痕龙够多仍算成员，如 275 条的人类）
- 聚落名 = 成员名组合（如「嘎巴丸、人类」）；**无成员回退 S 编号**

---

## 9. 边界与限制

| 项 | 说明 |
|----|------|
| ownerPid 多成员部落 = 0 | 共享龙无个人拥有者 → 区分成员靠印痕者 |
| 印痕者覆盖 ~78% | 仅有印痕（繁育）的龙有 imprinter |
| 印痕者无 pid 字段 | SDK/DinoData 只存名+EOSID → pid 全在分析端反查 |
| 跨服角色数据边界 | 某服 players 段可能缺某玩家（如板板在 Isl 缺失）→ 用成员名兜底 |
| eps 全局参数 | 不同服基地规模不同，eps=6000 为当前定值（Sco 基地跨度 ~5500）|

---

## 10. 相关脚本

| 脚本 | 作用 |
|------|------|
| `ark_save_reader.exe` | 离线读存档 → `*_cryo.json` |
| dll `TransferIdentityFix.ArkTamedDinos` | 实服 → `*_tamed.json` |
| `gen_settlements_v3.py` | 聚类 → `settlements.json` |
| `gen_settlement_html_v2.py` | 聚落 HTML（冠名/折叠/离散，前端参考实现）|
