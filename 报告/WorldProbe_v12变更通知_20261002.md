# WorldProbe v12 变更通知（2026-10-02）

> **面向对象**：前端开发
> **背景**：前端反馈「海底 / 沙漠宝箱落在补给箱类、且没有品质信息」
> **对应产物**：`TransferIdentityFixAPI.dll` = **1,596,928 B**（2026-10-02 15:04:06）
> **权威文档**：`ASA Transfer Identity Fix\docs\WorldProbe_前端交接单.md`（v12 版）
> **注意**：插件版本号仍为 `0.5.0`（未升号），请以 **dll 体积 / 部署时间**区分新旧。

---

## 一、根因（这次为什么改）

「海底箱 / 沙漠箱」其实是**同一个类**：**`SupplyCrate_OceanInstant_C`**，10 张图共 **32 个**（Isl 2 / Cen 6 / Ast 4 / **Rag 17** / Val 3）。

它先前被算进 `beacon`（补给箱 / 光柱），原因有两个：

1. 类名以 `SupplyCrate_` 开头 → 命中 `beacon` 的匹配模式
2. 又不含 `beacon` 的任何排除词

但它**根本不是光柱**：它不是从天上掉下来的，而是**固定点位**的藏宝箱。Wiki 权威对照（`Beacon IDs` 实体表）：

| 游戏内名称 | Entity ID | 地图 |
|---|---|---|
| **Deep Sea Loot Crate** | `SupplyCrate_OceanInstant_C` | The Island 等 |
| **Desert Loot Crate** | `SupplyCrate_OceanInstant_High_C` | Ragnarok |
| **Treasure Chest** | `SupplyCrate_Chest_Treasure_JacksonL_C` | Ragnarok（全图仅 1 个） |

> ⚠️ 同一族在两个地图上**类名混用**（Ragnarok 实机报的也是不带 `_High_` 的那个），所以新类别的显示名同时覆盖两种叫法。

至于「没有品质信息」：这类箱的**类名里既没有档位词、也没有等级数字**，解析函数返回空串 → 前端落到 unknown。

---

## 二、变更清单

### ① 新增类别 `seacrate`（类别数 13 → **14**）

| key | label | 匹配规则 |
|---|---|---|
| `seacrate` | **`Deep Sea / Desert Loot Crate`** | `SupplyCrate_OceanInstant` / `SupplyCrate_Chest_Treasure` |

**它们不再出现在 `beacon` 里**，请核对 `beacon` 的 `matched` 变化（下表为**预期值**，部署后请实测比对）：

| 地图 | 端口 | `beacon` 原值 | 预期新值 | 差额来源 |
|---|---|---:|---:|---|
| Isl | 32320 | 27 | **25** | −2（OceanInstant 2） |
| Sco | 32321 | 22 | **22** | 无 |
| Cen | 32322 | 33 | **27** | −6 |
| Abe | 32323 | 7 | **7** | 无 |
| Ext | 32324 | 0 | **0** | 无 |
| Ast | 32325 | 71 | **67** | −4 |
| Rag | 32326 | 30 | **12** | −17（OceanInstant）+ −1（JacksonL） |
| Val | 32327 | 21 | **18** | −3 |
| Los | 32328 | 2 | **2** | 无（`LostLootChest_T1/T2` 名字不含 `Cave`，仍归 beacon） |
| Gen | 32329 | 21 | **21** | 无 |

#### ⚠️ `seacrate` 内部含**两类不同的箱子**，且档位完全相同 —— 区分必须看 `class`

| `class` | 中文名 | 出现地图 | 数量 | `type` | `difficulty` |
|---|---|---|---|---|---|
| `SupplyCrate_OceanInstant_C` | 深海 / 沙漠战利品箱 | Isl / Cen / Ast / **Rag** / Val | 10 图共 32（Rag 16~17） | `seacrate` | `deepsea` |
| **`SupplyCreate_OceanInstant_High_C`**（Rag / Ast）<br>**`SupplyCreate_OceanInstant_High_SE_C`**（Sco） | **沙漠战利品箱**<br>（Desert Loot Crate） | **Rag / Ast / Sco** | Rag 2、Ast 3、**Sco 0~4**（刷新浮动） | `seacrate` | `deepsea` |
| `SupplyCrate_Chest_Treasure_JacksonL_C` | **Ragnarok 宝藏箱** | **仅 Rag** | **全图 1 个** | `seacrate` | `deepsea` |

**⇒ 两者 `type` 与 `difficulty` 完全相同**，若只按这两者上色**会长得一模一样**。要分开展示（不同图标 / 文案），**必须用 `class` 字符串判断**：

```js
const isTreasure = a.class.includes('Chest_Treasure');  // Rag 宝藏箱（全图 1 个）
const isDeepSea  = a.class.includes('OceanInstant');    // 深海 / 沙漠箱
```

> 📌 另：Rag 还有一个**专属洞穴箱** `SupplyCrate_Cave_QualityTier4_Ragnarok_C`（`Cave_QualityTier4_C` 同理），它归 **`cavecrate`**、档位 `legendary`，**不是** `seacrate`，**无需特殊处理**。
> 📌 Rag 宝藏箱是**固定点位**（Viking Bay 沉没海盗船内，约 22.1 / 33.2），可能因被开掉 / 未刷新而**暂时查不到** —— 属正常，箱子一出现就会进 `seacrate`。

#### 🔴 v14 修正：沙漠箱为什么一个都没有（dll = **1,598,464 B** / 2026-10-02 16:42:52）

实测 `scan filter=OceanInstant` 查到：**沙漠箱真实类名是 `Supp**lyCreate**_OceanInstant_High_C`** —— 是 **`Create`** 而不是 `Crate`！

| 地图 | `SupplyCrate_OceanInstant_C`（深海箱） | `SupplyCreate_OceanInstant_High_C`（沙漠箱） |
|---|---|---|
| **Rag** | 16 | **2** |
| **Ast** | 3 | **3** |
| Cen / Isl / Val | 5 / 2 / 3 | 0 |

> ⚠️ **`Create` 是游戏自己的拼写**（Wiki 原样照抄，不是笔误），**不可“改正”** 为 `Crate`。

**双重失效（与之前 Los 洞穴箱一模一样的“两头落空”）**：
1. `seacrate` 模式写的是 `SupplyCrate_OceanInstant`（Crate）→ 与 `Create` 差一个字母 → **匹配失败**；
2. `beacon` 的排除词是宽子串 `OceanInstant` → **又能匹配到它** → 被排除。
⇒ **这 5 个箱（Rag 2 + Ast 3）此前不属于任何类别**，前端自然一个都查不到。

**v14 修正**：`seacrate` 模式补上 `SupplyCreate_OceanInstant`。
**部署 v14 后预期**：**Rag 的 `seacrate` 由 16 → 18**，**Astraeos 由 3 → 6**。

### ② 新档位值 `deepsea`（⚠️ 本次唯一必须前端配合的点）

`seacrate` 的 `difficulty` **恒为 `deepsea`**。

- 请加**一条颜色映射**，整类共用一个颜色即可；
- 不加映射会落进 unknown（热力色）。

> 为什么不给 `L80`？游戏数据里这批箱确实是 80 级门槛，但**门槛不体现在类名上**，写死 `L80` 属于臆造；故用独立标识。

### ③ 65 个洞穴箱补上档位（此前恒为空串）

| 类名族 | 返回档位 |
|---|---|
| `SupplyCrate_IceCaveTier<1..3>_C` | `easy` / `medium` / `hard` |
| `SupplyCrate_SwampCaveTier<1..3>_C` | `easy` / `medium` / `hard` |
| `SupplyCrate_UnderwaterCaveTier<1..3>_C` | `easy` / `medium` / `hard` |

分布：Isl 16 / Cen 3 / Ast 20 / Rag 17 / Val 9。编号与 `QualityTier<N>` 同口径（1=蓝、2=黄、3=红）。

### ④ ⚠️ `cavecrate` 现在会出现 `L<NN>` 值

畸变（Abe）与 Valguero 的洞穴箱类名是 **`SupplyCrate_Cave_Aberration_Level<NN>_C`** → `difficulty` = `L10` / `L25` / `L35` / `L50` / `L65` / `L80`。

> 前端若只判断 `easy/medium/hard`，**需要补分支**；可与光柱（beacon）共用同一套「等级 → 颜色」表。

**因此 `cavecrate` 会同时出现两种口径**，这是已确认的现实，不是数据错误。

### ⑤ 顺带修掉的两个 bug（部署后才显现）

1. **`cavecrate` 的 `LootChest_Cave` 模式此前从未生效**（模式数被硬编码为 4，而实际有 5 个）→ 部署后 Los 的 `query cavecrate` 应从 **0 → 8**；
2. **上一版（v11）的 `beacon` `T<N>` 档位也未部署** → Gen / Los 的 `difficulty` 从空串变为 `T1` / `T2` / `T3`。

---

## 三、前端自查项

- **`typeCount` 请读数组长度**（现为 **14**），不要硬编码；
- 完整字典请调 `TransferIdentityFix.WorldProbe types probe`；
- 若发现「海底箱 / 沙漠箱」仍出现在 `beacon` 且 `difficulty` 为空 → **说明该地图还是旧 dll**。

---

## 四、单图验收清单（建议先在 Isl 验证）

| # | 命令 | 预期结果 |
|---|---|---|
| 1 | `TransferIdentityFix.DinoMutPing` | `ok:true`（正常响应即 dll 已加载） |
| 2 | `TransferIdentityFix.WorldProbe query seacrate limit=20` | `matched = 2`，全部 `difficulty = "deepsea"` |
| 3 | `TransferIdentityFix.WorldProbe query beacon limit=60` | `matched = 25`，`difficultyCounts` 中 **无 `unknown`** |
| 4 | `TransferIdentityFix.WorldProbe query cavecrate limit=60` | `matched = 28`，`difficultyCounts` ≈ `{easy:9, medium:11, hard:8}`，**无 `unknown`** |
| 5 | `TransferIdentityFix.WorldProbe types probe` | `types` 数组长度 = **14**，含 `seacrate`（`matched = 2`） |

> 验证 3 的「无 unknown」与验证 4 的「无 unknown」是本次最直观的两个通过信号。

---

## 五、v13 补充（2026-10-02 15:29）—— dll 更新为 1,597,952 B

### 唯一变化：`DinoMutPing` 新增 `build` 字段

| | 响应 |
|---|---|
| 旧（v12） | `{"ok":true,"plugin":"TransferIdentityFixAPI","version":"0.5.0"}` |
| 新（v13） | `{"ok":true,"plugin":"TransferIdentityFixAPI","version":"0.5.0","build":"Oct  2 2026 15:29:18"}` |

- `build` = **编译时间指纹**，在**编译期**烤进 dll，**不受实服 `config.json` 影响**
- **为什么加**：`version` 读的是实服 `config.json`，而多台实服的 config 仍是旧文件 → 无论实际部署哪一版 dll，都恒报 `0.3.0`，**无法据它判断实服在跑哪一版**
- ✅ **`query` / `types` / `weather` 的输出与 v12 完全一致** → 若前端不调用 `DinoMutPing`，则**无需任何改动**

### 部署核对提示

- 部署后调 `/tif ping`，看 `build` 是否为本次时间 → **确认新 dll 已真正生效**；
- 若响应里**没有 `build` 字段** → 说明该服还是 v12 或更早的 dll。


---

## 六、v15 补充（2026-10-02 21:29）—— dll = **1,612,288 B**

> 部署核对：`TransferIdentityFix.DinoMutPing` → `"build":"Oct  2 2026 21:28:47"`
> （`build` 是**编译期**指纹；**没有该字段**说明该服还是 v13 之前的 dll）

本次打包含 **3 项变更**，其中 **① 是前端需要配合的点**。

### ① 🔴 `actors[]` 新增 `noteId` / `noteIdProp` —— 探险者笔记「**精准逐点隐藏**」已打通

**仅 `query explorerchest`** 的条目会多出这两个字段（**其他类别不带**，取值前需判类型）：

```json
{"class":"ExplorerChest_Li_C","difficulty":"","hasLoc":1,
 "x":121476,"y":112079,"z":2505.48,
 "noteId":379,"noteIdProp":"ExplorerNoteIndex"}
```

| 字段 | 类型 | 说明 |
|---|---|---|
| `noteId` | int | 该箱子对应的**笔记编号**（`-1` = 未识别，此时看 `noteIdProp` 是否为空） |
| `noteIdProp` | string | 取值来源的**属性名**（溯源用；实测恒为 `ExplorerNoteIndex`） |

#### 语义：与 `_notes.json.gz` 的 `unlockedIds[]` **同一索引空间**，可直接比对（零换算）

三条实测证据（Abe 32323，2026-10-02 21:36）：

1. **索引空间对齐**：Abe 玩家位图 `max index = 1266`，箱子 `max noteId = 1265` → **越界数 = 0**
2. **作者段连续、不重叠**（位图按作者分段的典型特征，见下表）
3. **量级**：值落在位图容量内（43×32 = 1376），**不是**百万级「资产 ID」

#### 实测：作者段 → `noteId` 区间（Abe，`matched = 179`）

| `class` | 作者 | n | `noteId` 区间 |
|---|---|---:|---|
| `..._Li_C` | Mei-Yin Li | 30 | 357..386 |
| `..._DinoDossiers_C` | Helena Walker | 46 | 387..1255 |
| `..._Rockwell_C` | Rockwell | 30 | 417..446 |
| `..._Rusty_C` | Rusty（含 Skye 1） | 6 | 447..472 |
| `..._Emilia_C` | Emilia Müller | 5 | 452..456 |
| `..._Boris_C` | Boris | 5 | 457..461 |
| `..._Trent_C` | Trent | 5 | 462..466 |
| `..._Dmika_C` | Imamu | 5 | 467..471 |
| `..._Dianna_C` | Diana Altaras | 20 | 473..492 |
| `..._SheWhoWaits_C` | The One Who Waits | 5 | 510..522 |
| `..._Glitch_C` | HLN-A | 11 | 695..866 |
| `..._Santiago_Gen2Chronicles_C` | Santiago | 1 | 867..867 |
| `..._BobsTallTales_C` | Bob | 10 | 1256..1265 |

#### 前端用法（≈2 行，即 Phase 2）

```js
const unlocked = new Set(
  (LB._notes?.[abbr]?.players || []).find(p => p.eos === LB.playerEos)?.unlockedIds || []);
// 渲染 explorerchest 点位时：unlocked.has(a.noteId) → 跳过该点
```

> ✅ 与 Phase 1（人物组级）**可叠加**，也可**只用逐点**（更准，建议直接切逐点）。
> 切换按钮机制不变：过滤仍在**渲染层**、`LB._facPosC` 保持**全量** ⇒ **零网络重渲染**。

#### ⚠️ 三条注意

1. **`noteId` 不唯一**：实测 `863×2`、`866×3`，**全部集中在 `ExplorerChest_Glitch_C`（HLN-A Discoveries）**，且这 5 个箱子**坐标各不相同**。
   ⇒ 属「同一 note 在关卡部署了多个箱子实例」的**游戏设计** ⇒ 按 ID 过滤会**一起隐藏**（行为正确）；若要做「地点列表去重」需前端自行处理。
2. **非 `explorerchest` 类别没有 `noteId` 字段** ⇒ 取值前判 `a.noteId != null`。
3. `explorerchest` 条目里**没有** `noteId` ⇒ 该服**仍是 v14 或更早**的 dll。

### ② 顺带：新增两个类别（类别数 14 → **15**）

| key | label | 匹配模式 |
|---|---|---|
| `outpost` | `Outpost (Lost Colony)` | `MissionType_LC_Outpost` / `Mission_Outpost` / `StructureBP_Mission_Outpost` |
| `teleporter` | `City Teleporter` | `MapTeleporter` |

> 仍是**读 `types` 数组长度**判断类别数，不要硬编码（源码实测当前 = 15 条）。

### ③ 验收清单（建议在 Abe 或 Isl）

| # | 命令 | 预期 |
|---|---|---|
| 1 | `TransferIdentityFix.DinoMutPing` | `build` = `Oct  2 2026 21:28:47` |
| 2 | `TransferIdentityFix.WorldProbe query explorerchest limit=50` | 每条含 `noteId`；`noteIdProp` 恒为 `ExplorerNoteIndex` |
| 3 | 同上 `limit=2000`（Abe） | `matched = 179`、`returned = 179`、**无** `noteId < 0` |
| 4 | `TransferIdentityFix.WorldProbe types probe` | `types` 长度 = **15**，含 `outpost` / `teleporter` |
| 5 | （Los）`query teleporter limit=50` | `matched` ≈ **6**（`MapTeleporter_C`） |
