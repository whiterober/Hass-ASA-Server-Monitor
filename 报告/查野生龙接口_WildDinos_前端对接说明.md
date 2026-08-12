# 查野生龙接口（WildDinos）前端对接说明

> 日期：2026-08-12 ｜ 项目：TransferIdentityFixAPI（纯服务端 ASA API 插件）
> 适用：前端对接"按物种查全图野生龙"能力 ｜ 基于当前实装（全图枚举 + TTL 60s 缓存 + 基因词条）

---

## 1. 概述

服务端插件 **TransferIdentityFixAPI** 提供"按物种查询全图野生龙"能力：

- 通过 **RCON 命令**触发一次"全图野生扫描 + 落盘"，结果写入 JSON 文件；
- **前端只读文件**消费数据（不走 RCON 大 JSON 回包）；
- 野生判定采用**驯服集合反向判定**（枚举全图 actor，排除已驯服集合），覆盖**非活跃/未加载区野生**；
- 每条野生含**基因词条 geneTraits**（词条名 + 层数，与 tamed 结构统一）。

---

## 2. 接口调用

### 2.1 RCON 命令

| 项 | 值 |
|----|----|
| 命令 | `TransferIdentityFix.WildDinos <species>` |
| 参数 | `<species>` = 物种类名（**子串匹配，大小写不敏感**） |
| 权限 | RCON 命令级 `tif.operator` |
| 通道 | 服务器 RCON（各服端口见 §8） |

**返回（成功）**
```json
{ "ok": true, "species": "Rex", "count": 9, "file": "Sco_wild_Rex.json" }
```

**返回（失败/缺参数）**
```json
{ "ok": false, "error": "missing species" }
```

### 2.2 数据文件

- 路径：`<dino_data_dir>/<abbr>_wild_<species>.json`
- `dino_data_dir` 默认 `D:\ARK Server\DinoData`（config `dino_data_dir` 可配）
- 文件名：`<abbr>_wild_<物种>.json`，例：`Sco_wild_Rex.json`
- **前端**通过现有 DinoData 同步机制（如 `P:\私人共享\ASA\DinoData`）拉取该文件

---

## 3. 数据文件结构

顶层：
```json
{
  "savedAt": "1723440000000",
  "species": "Rex",
  "count": 9,
  "dinos": [ ... ]
}
```

| 顶层字段 | 类型 | 说明 |
|---------|------|------|
| `savedAt` | number | 生成时间（**Unix 毫秒**，可用于前端缓存失效判断） |
| `species` | string | 本次查询的物种名（原样） |
| `count` | number | 命中野生数量（`dinos.length`） |
| `dinos` | array | 野生龙记录数组 |

### 3.1 `dinos[]` 每条记录字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | string | `"<id1>_<id2>"` 全局唯一标识 |
| `id1` / `id2` | number | 龙 ID 高/低 32 位 |
| `dinoId1` / `dinoId2` | number | 与 `id1/id2` 相同（兼容别名） |
| `gender` | string | `MALE` / `FEMALE` |
| `colors` | string | 6 色索引逗号串 `"c0,c1,c2,c3,c4,c5"` |
| `dinoClass` | string | 完整类名（如 `Rex_Character_BP_C`） |
| `level` | number | 野生等级 |
| `babyAge` | number | 幼体成长度 0-1（成年为 0） |
| `isBaby` | 0/1 | 是否幼体 |
| `randomMutationsMale` | number | 公系随机突变 |
| `randomMutationsFemale` | number | 母系随机突变 |
| `ancestors` | array | 祖先代（**野生一般空**，保留字段） |
| `saddle` | string | 鞍类名（**野生空**） |
| `statValues` | array[12] | Max 属性值（顺序见 §3.2） |
| `statPoints` | array[12] | 各属性加点 |
| `statMutations` | array[12] | 各属性突变 |
| `imprintingQuality` | number | 驯养度 0-1（**野生 0**） |
| `x` / `y` / `z` | number | UE 世界坐标（需坐标校准转经纬，见 §9） |
| `geneTraits` | array | 基因词条 `[{trait,stacks}]`（见 §3.3） |

### 3.2 stat 12 槽位顺序（`EPrimalCharacterStatusValue`）

| 索引 | 属性 | 索引 | 属性 |
|:---:|------|:---:|------|
| 0 | health | 6 | temperature |
| 1 | stamina | 7 | weight |
| 2 | torpidity | 8 | meleeDamage |
| 3 | oxygen | 9 | movementSpeed |
| 4 | food | 10 | fortitude |
| 5 | water | 11 | craftingSpeed |

### 3.3 `geneTraits` 结构（与 tamed 完全统一）

```json
"geneTraits": [
  { "trait": "Angry",     "stacks": 2 },
  { "trait": "Tenacious", "stacks": 1 }
]
```

- `trait`：基因词条名（词条名）；`stacks`：层数
- 仅在基因系统启用且有词条时非空，否则 `[]`

---

## 4. 完整示例（Sco 实服 Rex）

```json
{
  "savedAt": "1723440000000",
  "species": "Rex",
  "count": 9,
  "dinos": [
    {
      "id": "397174429_187449547",
      "id1": 397174429, "id2": 187449547,
      "dinoId1": 397174429, "dinoId2": 187449547,
      "gender": "MALE",
      "colors": "5,12,3,8,1,22",
      "dinoClass": "Rex_Character_BP_C",
      "level": 285,
      "babyAge": 0,
      "isBaby": 0,
      "randomMutationsMale": 0,
      "randomMutationsFemale": 0,
      "ancestors": [],
      "saddle": "",
      "statValues": [9542, 812, 310, 420, 7150, 3500, 1500, 2140, 421, 130, 36, 110],
      "statPoints": [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
      "statMutations": [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
      "imprintingQuality": 0,
      "x": 41230.5, "y": 98210.1, "z": 3210.8,
      "geneTraits": []
    }
  ]
}
```

---

## 5. 物种匹配规则

- `<species>` 对 `dinoClass` 做**子串匹配**（统一小写化后判断，大小写不敏感）；
- 例：`Rex` → 命中 `Rex_Character_BP_C` / `SnowRex_...` / `AlphaRex_...` 等含 `rex` 的所有变体；
- `Argent` → `Argentavis`；`Dodo` → `Dodo`；
- 无任何命中 → `count: 0`（文件仍生成，`dinos` 为空）。

---

## 6. 缓存机制（重要）

| 项 | 说明 |
|----|------|
| 策略 | **TTL 60s 分组缓存**（key = 物种名） |
| 命中 | 同物种 60s 内重复查询 → **零全图遍历**，直接复用缓存数据（`savedAt` 更新为命中时刻，数据为缓存快照） |
| 未命中 | 首次/超时 → 全图枚举 + 字段提取 → 写缓存 + 落盘 |
| 缓存内容 | 提取后的纯数据（无 actor 指针，**无悬垂/崩溃风险**） |

### 6.1 全图清龙的影响

玩家执行**全图清龙**（`DestroyWildDinos`）后：

- 清龙后 **60s 内**查询同物种 → 命中旧缓存，返回**已被清除的龙**（短暂陈旧）；
- **60s 后**缓存自动过期 → 重新扫描 → 返回新刷新龙，自动恢复；
- 无崩溃、无悬垂、缓存结构不受破坏；
- **前端建议**：全图清龙后如需实时数据，等待 60s 再查询；或接受短暂陈旧（对统计类消费影响小）。

---

## 7. 性能与注意事项

- **单次全图扫描 ~130-160ms**（服务端主线程阻塞）——**不建议高频轮询同一物种**；请利用 60s 缓存窗口，避免频繁触发全图遍历；
- 全图 = PersistentLevel 全部 actor（约 3.5 万+），通过"驯服集合反向判定"区分野生/驯服；
- 大物种（如 Doed 364 只）文件较大——**数据走文件**，不通过 RCON 大 JSON 回包；
- 基因词条仅在基因系统启用（`Hotfix_AreGeneTraitsEnabled`）且有词条时非空；
- 野生特有：`name` 空、无 owner/imprinter/tribe（`ancestors`/`saddle`/`imprintingQuality` 为空/0）；
- 坐标 `x/y/z` 为 UE 世界坐标，前端需用**坐标校准参数**转换（见 §9）。

---

## 8. 服务器标识（abbr）映射

> `abbr = server_id 前 3 字符首字母大写`（config `auto_parse.server_id`）。

| abbr | 地图 | RCON 端口 |
|------|------|:---:|
| Sco | 焦土 ScorchedEarth | 32321 |
| Isl | 孤岛 TheIsland | 32319 |
| Ext | 灭绝 Extinction | — |
| Ast | Astraeos | — |
| Gen | Genesis | — |
| Los | LostColony | — |
| Rag | Ragnarok | — |
| Cen | TheCenter | — |
| Val | Valguero | — |
| Abe | Aberration | — |

文件路径示例：焦土 = `Sco_wild_Rex.json`、孤岛 = `Isl_wild_Rex.json`。

---

## 9. 前端消费建议

1. **取数**：按 `<数据目录>/<abbr>_wild_<species>.json` 拉取文件；
2. **缓存失效**：用顶层 `savedAt`（Unix ms）判断数据新鲜度；配合 60s 服务端缓存，前端无需过度轮询；
3. **关联**：`id`（`"<id1>_<id2>"`）全局唯一，可关联 tamed / cryo / 部落等其它数据；
4. **坐标**：`x/y/z` 为 UE 世界坐标，转经纬需用各图坐标校准参数（参考 `报告/coord_params_all.json` 及各图 `*_coord_calib.json`）；
5. **展示**：`statValues` 为 Max 值（对照 `statPoints` 可算加点分布）；`geneTraits` 直接按 `trait/stacks` 展示词条与层数；
6. **频率**：同一物种两次查询间隔建议 ≥60s（命中缓存，零扫描）；若确需实时，接受服务端 ~130-160ms 的全图扫描代价。

---

*报告基于当前实装（步骤 60-68：全图野生 + 类名缓存 + TTL 60s 分组缓存 + geneTraits）。*
