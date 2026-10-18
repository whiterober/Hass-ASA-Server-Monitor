# 花盆（Plant Pot）植物资产字段 前端对接说明

> 面向：前端 / 后端（`独立后端`）
> 日期：2026-10-18 ｜ 数据来源：ArkSaveReader（exe）解析存档
> 插件 dll：**零改动**

---

## 1. 一句话

`item` 数据（`<图>_item.json.gz`）中每个物品新增 **`plantAsset`** 字段：
- **空盆** ⇒ `""`
- **满盆** ⇒ 植物资产短名（如 `PaloVerde_2_settings`）

前端据此判断空/满，并按资产名展示植物类型。

> 🔴 **旧数据（还没重跑解析的 `*_item.json.gz`）里没有这个 key**，读出来是 `undefined` 而不是 `""`。
> 前端务必按 **§2.1 三态写法**处理，否则会把空盆误判成满盆（详见 §2.2 / §2.3）。

---

## 2. 字段定义

| 字段 | 类型 | 说明 |
|---|---|---|
| `plantAsset` | string | 花盆内植物资产短名；`""` = 空盆；**非花盆物品恒为 `""`** |

### 2.1 ✅ 正确判据（三态，兼容旧数据）

```js
// 推荐：三态判断，兼容「还没重跑解析」的旧数据
const potState = (item) => {
  if (typeof item.plantAsset !== "string") return "unknown"; // 旧数据：字段不存在
  return item.plantAsset === "" ? "empty" : "filled";
};

// 只要布尔值时：
const isFilled = (item) => typeof item.plantAsset === "string" && item.plantAsset !== "";
const isEmpty  = (item) => typeof item.plantAsset === "string" && item.plantAsset === "";
```

### 2.2 ⛔ 错误写法（旧数据会误判）

```js
// ❌ 旧数据里没有 plantAsset 这个 key，读出来是 undefined，不是 ""
item.plantAsset === ""      // undefined === ""  →  false
// 后果：旧数据里的【空盆】会被判成【满盆】
```

> ⚠️ 只有 `PrimalItemStructure_PlantPot_C` 类才会有非空 `plantAsset`。
> 其它物品（含 `PrimalItemStructure_*` 的其它结构）恒为空串，可直接忽略。

---

## 2.3 旧数据兼容说明

| 场景 | 是否兼容 | 说明 |
|---|---|---|
| **新 exe 读旧 `.ark` 存档** | ✅ 完全兼容 | 只新增字段，不动既有解析路径；已用 9-20 旧存档实测 4 张图均正常，`quantity`/`stats`/`customName` 无回归 |
| **新 exe 覆盖旧 exe** | ✅ 兼容 | 配置/输出文件格式向后兼容，同目录 `gene_map.json` 无需改动 |
| **旧 `*_item.json.gz`（无 `plantAsset`）** | ⚠️ 字段缺失 | 旧 exe 本来就没导出这个信息，**无法判断空满**（不是代码 bug）。必须重跑解析才有数据；在此之前请按 §2.1 返回 `unknown`，不要默认当成空盆或满盆 |
| **前端读旧数据** | ⚠️ 需按 §2.1 写 | 用 `=== ""` 硬判会把旧数据判错（见 §2.2）|

---

## 3. JSON 示例

### 满盆（在绿洲龙背包里）

```json
{
  "type": "item",
  "kind": "structure",
  "class": "PrimalItemStructure_PlantPot_C_2145577158",
  "key": "7ce70a5aec0c224786da347f8f485988",
  "quantity": 0,
  "durability": 0,
  "rated": 0,
  "qidx": -1,
  "stats": [],
  "customClass": "",
  "customName": "",
  "plantAsset": "PaloVerde_2_settings",
  "containerClass": "DinoTamedInventoryComponent_Oasisaur_C_2146798869",
  "containerType": "other",
  "containerTribeName": "北美狗鱼"
}
```

### 空盆

```json
{
  "class": "PrimalItemStructure_PlantPot_C_2145880713",
  "plantAsset": "",
  "containerClass": "PrimalInventoryBP_StorageBox_Large_C1",
  "containerTribeName": "大表哥"
}
```

---

## 4. ⚠️ 关于「尺寸」：游戏没有尺寸分级

查证结论（wiki + 补丁记录 + 实测）：

- 官方 Oasisaur 页面唯一相关描述：*"the amount of food restored being **larger for larger plants**"*
  ⇒ **不存在 Small / Medium / Large 这种枚举档位**
- Patch 51.3：*"Fixed an issue where it would **not scale correctly**"*
  ⇒ 官方内部管的是 **scale（缩放）**，不是尺寸 ID
- 世界内**放置后**的花盆才有缩放字段（物品态不保存）：
  `CurrentFoliageScale`=1.0、`FoliageSizeLimit`=0.2~1.0、步进 0.05 ⇒ 玩家可用 +/- 调 17 档

**所以：**

$$\text{实际显示大小} = \text{资产固有大小} \times \text{CurrentFoliageScale}$$

⇒ `plantAsset` 给的是**植物种类/变体**，尺寸信息蕴含在资产名里（如 `LumaD` vs `LumaD_02`）。
若前端要显示"大/中/小"，需要一个**资产 → 档位**的映射表，目前**尚未定稿**（待实测/人工分类后补充）。

---

## 5. 已知的 20 种植物资产（本地 23 个存档扫描结果）

| # | plantAsset | 类型 | 来源地图目录 | 出现次数 |
|---|---|---|---|---:|
| 1 | `PaloVerde_2_settings` | 树 | ScorchedEarth / HighDesert | 48 |
| 2 | `SM_FanPalm_settings` | 棕榈 | ScorchedEarth / Oasis | 11 |
| 3 | `SM_FernB_settings` | 蕨 | Aberration / BioLumChamber | 10 |
| 4 | `DatePalm_B_settings` | 棕榈 | ScorchedEarth / Oasis | 10 |
| 5 | `SM_Element_TreeA_Yellow_settings` | 树 | Aberration / ElementChamber | 8 |
| 6 | `LumaD_settings` | 树 | Aberration / BioLumChamber | 8 |
| 7 | `BigPalm_SM_settings` | 棕榈 | PrimalEarth / Jungle | 7 |
| 8 | `LumaA_02_settings` | 叶簇 | Aberration / BioLumChamber | 5 |
| 9 | `Poisonous_Plant_settings` | 灌木 | Aberration / ElementChamber | 4 |
| 10 | `Biolum_Poisonous_Plant_settings` | 灌木 | Aberration / ElementChamber | 4 |
| 11 | `LumaA_settings` | 叶簇 | Aberration / BioLumChamber | 4 |
| 12 | `WhitePine_B_FoliageType` | 松 | Astraeos(Mod) / LostColony | 3 |
| 13 | `WhitePine_D_FoliageType` | 松 | Astraeos(Mod) / LostColony | 3 |
| 14 | `SeaWeed07_settings` | 海草 | PrimalEarth / UnderWater | 3 |
| 15 | `Katsura_1_EXT_03_settings` | 树 | Extinction / Ruins / City | 2 |
| 16 | `LumaD_02_settings` | 树 | Aberration / BioLumChamber | 2 |
| 17 | `BiolumGrassBuds_settings` | 海草 | PrimalEarth / UnderWater | 2 |
| 18 | `Pinyonpine_settings` | 松 | ScorchedEarth / Canyons | 2 |
| 19 | `MLarge_Bush_SM_Red_settings` | 灌木 | Astraeos(Mod) / TheIsland | 1 |
| 20 | `Coral_Big3_settings` | 珊瑚 | PrimalEarth / UnderWater / Corals | 1 |

> 出现次数为跨存档累计（部分存档是同一张图的副本），**不代表实际盆数**。

### 同种变体组（很可能是大小/形态差异）

| 组 | 成员 |
|---|---|
| 荧光树 | `LumaD_settings` / `LumaD_02_settings` |
| 荧光叶簇 | `LumaA_settings` / `LumaA_02_settings` |
| 白松 | `WhitePine_B_FoliageType` / `WhitePine_D_FoliageType` |
| 帕洛佛得 | `PaloVerde_2_settings`（另有基名 PaloVerde） |
| 枣椰 | `DatePalm_B_settings`（另有基名 DatePalm） |

> 另有 **Astraeos 模组资产**（`/Game/Mods/Astraeos/...`），说明模组植被也可进盆 —— 前端不要假设只出现原版资产。

---

## 6. 全服实况（2026-10-18 线上实测）

新 exe 部署后 10 张图全部重跑完成，`plantAsset` 已可用：

| 图 | 花盆总数 | 满 | 空 | 资产种类 |
|---|---:|---:|---:|---:|
| ScorchedEarth (Sco) | 46 | 8 | 38 | 1 |
| Extinction (Ext) | 20 | 19 | 1 | 9 |
| TheIsland (Isl) | 18 | 4 | 14 | 2 |
| Astraeos (Ast) | 11 | 4 | 7 | 4 |
| Abe / Cen / Gen / Los / Rag / Val | 0 | 0 | 0 | — |
| **合计** | **95** | **35** | **60** | **15** |

> 线上 15 种资产实际分布：`PaloVerde_2_settings`(8) / `SM_Element_TreeA_Yellow_settings`(4) / `LumaD_settings`(4) /
> `DatePalm_B_settings`(3) / `LumaA_02_settings`(2) / `Poisonous_Plant_settings`(2) / `Biolum_Poisonous_Plant_settings`(2) /
> `LumaA_settings`(2) / `SM_FernB_settings`(2) / `WhitePine_B_FoliageType`(1) / `WhitePine_D_FoliageType`(1) /
> `SM_FanPalm_settings`(1) / `Katsura_1_EXT_03_settings`(1) / `LumaD_02_settings`(1) / `BiolumGrassBuds_settings`(1)

---

## 7. 展示建议

| 元素 | 建议 |
|---|---|
| 图标 | 空盆 / 满盆两套（游戏内本来就有 Filled 图标变体）；`unknown` 用第三套或置灰 |
| 状态文字 | `filled` ⇒ 显示资产中文名；`empty` ⇒ 「空盆」；`unknown` ⇒ 「—」或「数据待更新」 |
| 兜底 | 遇到未知资产名，直接显示原始短名，勿显示空白 |
| 分组 | 可按 `containerClass` 区分背包 / 箱子 / 恐龙背包 |
| 排序 | 满盆优先（Oasisaur 喂食用）|

---

## 8. ✅ 生效状态

**2026-10-18 已完成全服部署与重跑**：服务器 10 张图的 `<图>_item.json.gz` 全部带 `plantAsset`，无异常。

- exe md5：`40562b562825cf22a6c3fb799d0002bb`（1,556,992 B）
- 部署位置：`\\SERVER\ARK Server\DinoData\ark_save_reader.exe`
- 本地发布包：`TransferIdentityFixAPI\package\TransferIdentityFixAPI\ark_save_reader.exe`（同 md5）
- 自检方法：任取一个 `*_item.json.gz`，搜索 `PlantPot`，能看到 `"plantAsset":"..."` 或 `"plantAsset":""` 即正常
- 若某图后续出现解析回退（旧 exe 覆盖），该图会重新变成无 `plantAsset` ⇒ 前端按 §2.1 返回 `unknown`

---

## 9. 一句话总结

**`plantAsset` 一出，空满即可判、植物种类即可显示**（旧数据请按 §2.1 返回 `unknown`）；尺寸没有官方分级，需要的话得另建「资产 → 档位」表。
