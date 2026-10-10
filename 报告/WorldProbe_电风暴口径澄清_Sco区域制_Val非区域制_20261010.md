# WorldProbe · 电风暴（electricalStorm）口径澄清：**Sco 是区域制，Val 不是**

> 日期：2026-10-10 ｜ 起因：前端报「Val 的 `electricalStorm` 为 null（`hasESfull:false`）」，并提到 wiki 称 Val 雷暴是区域性质
> 结论一句话：**wiki 那句"区域性质"说的是 Scorched Earth（我们的 Sco），不是 Valguero**；Val 只是**有电风暴这个天气**，实现上**不是区域制**，服务端**读不到任何区域几何**。

---

## 一、Wiki 原文（逐字）

来源：ARK Wiki「Environmental / Weather → Electrical Storm」

> "Electrical storms, **only found on Scorched Earth**, deactivate electronics (such as cryopods) and prevent some advanced weapons from firing. …
> **Unlike nearly every other weather event, electrical storms do not directly affect the entire map, but instead hover over a random area** (which is still fairly large) and repeatedly bombard it with lightning."

而 Valguero 页面 *Unique Environmental Features* 只列：彩虹、极光、流星、雪漠寒风、深渊、水体尸体、畸变生态、蘑菇、辐射区、恐爪龙巢、飞龙沟、野生母蜘蛛；其 *Environmental Events* 仅标 **Rainbow: Within Valguero** —— **没有电风暴条目**。

⇒ 即"区域悬停劈雷"是 **Scorched Earth** 的特性（**Sco 就是 Scorched Earth**，故实测完全吻合）。

---

## 二、实测对照（2026-10-10）

| 检查项 | **Sco**（=Scorched Earth） | **Val**（Valguero） |
|---|---|---|
| `wxSemantics.electricalStorm` | **满配对象** | **`null`** |
| `regionPoints` | **5 个锚点**（SW/SE/NW/NE_15/Center，含 x/y/z） | 无 |
| `regionName` / `regionPoint` / `active` | `'NW'` / 当前点 / `active=1` | 无 |
| `stormIds` / `maskTargets` / `matinee` / `wxKeyScan` | ✅ 均有 | 无 |
| 天气 actor 上的门控属性<br>`ElectricalStormRegion` / `bDebugElectricalStorm` / `ElectricalStormRegionName` | **存在** | **三个全部不存在**（⇒ 插件输出 null 的直接原因） |
| 地图上的 `ElectricalStormPoint*` 锚点 | **5 个**（Note 类） | **0 个** |
| 电风暴天气预设 | ✅ 雷暴 = 天气 id **7** | ✅ **`WeatherPreset_VAL_ElectricalStorm`，id = 6877769** |
| 区域实例 | — | CloudSystem **1**、WeatherSystem **1**、RegionTimeOfDay **2**（`Region2/3` 为 null） |
| 区域权重 | — | Agent `SeqWeight_Region0..3 = [1,0,0,0]`；`RegionWeights` 32B 全 0 |

**全服锚点分布**（`WorldProbe actor filter=ElectricalStormPoint byname=1`）：

| 图 | Sco | Abe | 其余 8 图（Isl/Cen/Ext/Ast/Rag/Val/Los/Gen） |
|---|---|---|---|
| 锚点数 | **5** | **5** | **0** |

---

## 三、根因（两层，都是"地图层面"，不是采集故障）

1. **插件门控**：`wxSemantics.electricalStorm` 仅当天气 actor 上读到 `ElectricalStormRegion` **或** `bDebugElectricalStorm` 时输出对象，否则 `null`（`TransferIdentityFixAPI.cpp` L8919-8923）。**Val 的天气 actor 是 `BP_RAG_DayWeather_WeatherSystem_C`（复用 Rag 蓝图），这三个属性都不存在** ⇒ 必然 `null`。
2. **数据本身不存在**：即便放开该门，**Val 地图上没有任何 `ElectricalStormPoint*` 锚点**，也没有天气遮罩/区域体（`filter=Mask` = 0；`filter=Override` 只有 `LocalSkyLightOverride`）⇒ **无几何可画**。

---

## 四、前端口径建议

1. **Sco**：维持现状（v4461 口径）——5 个候选点常驻、当前点激活时发光圈；判据 `wxSemantics.electricalStorm.active`。
2. **Val 及其余 8 图**：`wxSemantics.electricalStorm` 为 `null` ⇒ **面板隐藏**（不要报"缺失/故障"）。
   判"**是否在刮电风暴**"请改用：`weatherState.currentWeatherId` 对照 `wxSemantics.presetTable` ——
   - Val：电风暴 = **6877769**（`WeatherPreset_VAL_ElectricalStorm`）
   - Sco：雷暴 = **7**
3. **区域范围/点位**：**仅 Sco（与 Abe 有锚点，但 Abe 家族不同、无 UDS 属性）** 可得；Val **不可得**（无锚点、无区域体，仅 2 个占位 RegionTOD）。
4. 若希望接口更明确，可让我们加一版（v122b21）：把 `electricalStorm` 改为显式
   `{"supported":false,"reason":"…","anchors":0,"presetId":6877769}`，或另加 `electricalStormSupport{regionProps:0/1,anchors:N,presetId:…}`
   ⇒ 前端据此直接决定"隐藏面板"，无需再用 null 猜。**该项尚未实施，等确认。**

---

## 五、待前端确认

- 你看到的"wiki 说 Val 雷暴是区域性质的"——请给**具体链接/段落**；我这边抓到的 wiki 描述把"区域悬停"归给 **Scorched Earth**，Valguero 页面未提电风暴。若你看的是**中文 wiki**或**其它来源**，发我链接，我做逐字核对并同步修正本文档。
