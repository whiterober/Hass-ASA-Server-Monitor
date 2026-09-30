<!-- 来源：ASA Transfer Identity Fix 项目  |  生成 2026-09-26  |  对应插件 dll v9 (1,594,368 B / mtime 2026-09-26 17:25:35)  |  项目内权威版：ASA Transfer Identity Fix\docs\WorldProbe_前端交接单.md -->

# WorldProbe 前端交接单

> 版本：v9（dll = 1,594,368 B / mtime 2026-09-26 17:25:35）
> 状态：**已全量部署到 10 张图**（Abe / Ast / Cen / Ext / Gen / Isl / Los / Rag / Sco / Val）
> RCON 命令前缀：`TransferIdentityFix.WorldProbe <子命令>`

---

## 一、命令总览

| 子命令 | 用途 | 权限 |
|---|---|---|
| `types` | 列出全部**类别字典**（11 类）及匹配规则 | `tif.viewer` |
| `query <type> [limit=N]` | 按类别查实例，**返回坐标** | `tif.viewer` |
| `scan [filter=X] [top=N]` | 类名普查（诊断用，前端一般不需要） | `tif.viewer` |
| `weather` | 天气状态（含 `weatherState`） | `tif.viewer` |

---

## 二、类别字典（**共 11 类**）

| # | key | label | 匹配规则 | 排除 |
|---|---|---|---|---|
| 1 | `osd` | Orbital Supply Drop | `SupplyCrate_Base_Horde` | — |
| 2 | `cavecrate` | Cave Supply Crate | `SupplyCrate_Cave` | — |
| 3 | `horde` | OSD Horde Infrastructure | `HordeCrateManager` / `Horde_Spline_Path` / `HordeSpawnNetwork` | `ElementNode`, `SupplyCrate` |
| 4 | `artifactcrate` | Artifact Crate | `ArtifactCrate` | — |
| 5 | `elementnode` | Element Node | `ElementNode` / `ElementVein` | — |
| 6 | `beacon` | Supply Crate (Beacon) | `SupplyCrate` | `SpawningVolume`, `Horde`, `Cave`, **`DamLogs`**, **`DenLogs`** |
| 7 | `beehive` | Wild Bee Hive | `BeeHive` | `PlayerOwned` |
| 8 | `obelisk` | Obelisk | `BP_Obelisk` | — |
| 9 | `beaverdam` | Beaver Dam | **`BeaverDam` / `DamLogs` / `DenLogs`** | — |
| 10 | `beaver` | Wild Beaver | `Beaver_Character_BP` | — |
| 11 | `weather` | Weather | （专用逻辑，`patterns` 为空属正常） | — |

> ⚠️ **`resource` 类别已于 2026-09-26 删除**（双图 18 万 actor 普查零命中，资源点不是独立 actor）。
> `query resource` 会返回 `unknown type`。

---

## 三、`query <type>` 响应结构

```json
{
  "ok": true, "sub": "query", "type": "beaverdam",
  "worldTime": 250990000.0, "levelCount": 2566,
  "matched": 7, "returned": 7, "truncated": 0, "limit": 20,
  "difficultyCounts": {},
  "sampleClasses": ["BP_BeaverDam_C", "BeaverDam_C"],
  "actors": [
    {"class": "BeaverDam_C", "difficulty": "", "hasLoc": 1,
     "x": -643914, "y": -139148, "z": -9865.9}
  ]
}
```

| 字段 | 说明 |
|---|---|
| `matched` | 该类别在**当前已加载世界**中的实例总数 |
| `returned` | 本次实际返回条数（受 `limit` 限制） |
| `truncated` | `1` = 还有更多未返回，需增大 `limit` 或分页 |
| `difficulty` | 档位（仅部分类别有：`osd`/`cavecrate`/`elementnode` 走 `easy/medium/hard/legendary/corrupt`；`beacon` 走 **`L<NN>`** 玩家等级） |
| `hasLoc` | `1` = 坐标有效 |
| `class` | **完整类名** ✅ |

### 档位格式说明（`difficulty`）

| 类别 | 格式 | 示例 |
|---|---|---|
| `osd` / `cavecrate` / `elementnode` | 单词 | `easy` / `medium` / `hard` / `legendary` / `corrupt` |
| **`beacon`** | **`L<NN>`** 玩家等级 | `L03` / `L15` / `L25` / `L35` / `L45` |
| `beaverdam` / `beaver` / `beehive` / `obelisk` / `artifactcrate` / `horde` | 空字符串 | `""` |

> ⚠️ **光柱（beacon）的等级→颜色映射因图而异**（Wiki：孤岛蓝=25 / 焦土蓝=30 / 畸变蓝=35），前端需**按地图**套表。
> ⚠️ **OSD 档位会浮动**（同一点位先后出现过 `_Hard_C` / `_Easy_C` / `_Legendary_C` / `_Medium_C`）—— 不要假设固定。

---

### 河狸窝的**三种形态**与区分方法

`query beaverdam` 会把三种形态**一并返回**，用**每条实例的 `actors[].class`** 区分：

| `class` 值 | 含义 | 已实测出现 |
|---|---|---|
| `BeaverDam_C` | 普通坝 | **Ext ×3 / Ast / Isl ×1** |
| **`BP_BeaverDam_C`** | **大型坝** | **Ast** |
| `SupplyCrateBaseBP_Instantaneous_DenLogs_Child2_C` | **巢穴 / lodge** | **Rag ×6 / Val ×5** |

> 2026-09-26 全服实测：河狸窝**共 30 个**（Ast 15 / Rag 6 / Val 5 / Ext 3 / Isl 1）；Abe / Sco / Cen / Los / Gen **当前 0 个**。

**推荐判据（按 `class` 字符串）**：
- 含 `DenLogs` → **巢穴**
- 含 `BP_` 前缀 → **大型坝**
- 否则 → 普通坝

> ⚠️ **不要用 `difficulty` 判断类型** —— 河狸窝该字段**恒为空字符串**（`difficulty` 只对 `osd` / `cavecrate` / `elementnode` 的档位、以及 `beacon` 的 `L<NN>` 有意义）。
> ⚠️ **`sampleClasses` 只能判断"这张图存在哪些形态"**（它是整体去重列表、**不带坐标**）；要定位到具体某一个是哪种，必须用 `actors[].class`。
> 💡 因为 `beaverdam` 类别用的是**子串匹配**（`BeaverDam` / `DamLogs` / `DenLogs`），未来若出现新变体（如 `XXX_BeaverDam_C`）会被**自动收录**，前端按 `class` 原样展示即可，无需改码。

---

## 四、⚠️ 三个**必须**注意的坑

### 坑 1（最重要）：**「扫不到」≠「不存在」** —— 按需加载

> `scan` / `query` 只能看到 **当前已加载 / 已生成**的 actor。
> 玩家未涉足的区域，物件可能**根本不在列表里**。

**实证**：2026-09-26 查 The Island 河狸窝时，两轮穷举（833 类全量清单 + 10 关键词）**全部零命中**；
用户飞到现场后**立刻重扫**就命中了 `BeaverDam_C` ×1（坐标 `153521, -223182, -13704`）。

**因此**：
- ❌ 不要用"查不到"推断"该图没有"
- ❌ 不要拿**一次** `scan` 的数量当"全图总数"
- ✅ 需要全图统计时，必须**多点/多次采样**（或先让人跑图触发加载）
- ✅ 界面上建议加提示："数据为服务器当前可见范围"

### 坑 2：坐标为 `(0,0,0)` 的条目是**未初始化**对象

`hasLoc` 可能为 `1` 但坐标是 `(0,0,0)`（实测 Isl 的 29 只河狸里有 4-5 条如此）。
**前端必须过滤**，否则地图上会出现"原点幽灵"。

### 坑 3：`scan` 的 `top` 上限 **500**

`scan` 无分页参数；大图（Isl = **832** 类）一次拿不全。
**前端不需要 `scan`**（用 `types` + `query` 即可）。运维要全量清单时需**字母分片**：
`for ch in a..z: scan filter=<ch> top=500` → 合并去重。

---

## 五、`weather` 响应（跨图差异大）

### 响应关键字段

| 字段 | 说明 |
|---|---|
| `target` | 实际选中的天气 Actor 类名 |
| `confidence` | `high` = 读到语义字段；`medium` = 仅找到天气 actor；`low` = 回退到 GameState |
| `weatherActorCount` / `weatherActorClasses` | 实例数 / **去重后**类数 |
| `weatherActors` | **去重后**的类名数组（⚠️ v6 之前是含重复的原始列表） |
| `weatherActorDetails` | `[{class, count}]` 明细 |
| `weatherState` | 结构化天气值（**键因图而异**，见下），无数据时为 `null` |

### `weatherState` 的两种形态（用 `family` 区分）

| `family` | 适用图 | 典型键 |
|---|---|---|
| **`uds`** | Isl / Sco / Cen / Abe / Ast / Val / Los（原版系） | `fogStrength` / `rainStrength` / `windStrength` / `windDirection` / `currentWeatherId`(来自 `CloudNewWeather`) / `weatherSpeed` / `baseSummerTemperature` … |
| **`ext_gen`** | Ext / Gen / Rag / Ast | `currentWeatherId` / `nextWeatherId` / `secondsUntilChange` / `changeIntervalMin` / `inTransition` / `fogStrength` / `windStrength` … |

> ⚠️ **`weatherState` 只输出实际找到的键**（v6 之前是固定 23 键、缺失填 -1/0）。前端请**按 key 存在性判断**，不要假设键齐全。
> ⚠️ `currentWeatherId` 是**原始枚举索引**，游戏不给名称映射（`WeatherPresetList` 是 80 字节结构体读不出）。Gen 上该字段不可读时返回 **`null`**，`semUnreadable` 给出不可读字段数。

### 已实测的天气 Actor 类名（供参考，勿硬编码）

| 图 | 天气 Actor |
|---|---|
| Ext | `BP_EXT_WeatherSystem_C` + `BP_EXT_DayWeatherAgent_C` |
| **Abe** | **`BP_AB_WeatherSystem_C`** ⚠️ 见下方"待适配" |
| Gen | `BP_GEN_DayWeather_WeatherSystem_C`（另有 CloudSystem / RegionTimeOfDay / Agent 等 5 类） |
| Rag | `BP_RAG_DayWeather_WeatherSystem_C` |
| **Val** | **`BP_RAG_DayWeather_WeatherSystem_C`** ← 与 Rag **同名**（Valguero 直接复用 Ragnarok 的天气蓝图） |
| **Ast** | **`BP_AST_DayWeather_WeatherSystem_C`** |
| **Los** | **`BP_LC_DayWeather_WeatherSystem_C`**（`LC` = LostColony） |
| Isl | `UDS_Island_Weather_C` + `Weather_Override_Volume_C` ×4 |
| Sco | `UDS_SE_Weather_C` |
| Cen | `UDS_TheCenter_Weather_C` + `Weather_Override_Volume_C` ×6 |

> 规律（已 8 图验证）：
> - **原版图** = `UDS_<地图>_Weather_C`（Isl / Sco / Cen）
> - **官方重制/DLC 图** = `BP_<前缀>_DayWeather_*`（Gen / Rag / **Val** / Ast / Los）
> - **例外**：Ext = `BP_EXT_WeatherSystem_C`、Abe = `BP_AB_WeatherSystem_C`（无 `DayWeather` 段）

### ⚠️ Abe（畸变）当前**未适配**

`target` 能正确选中 `BP_AB_WeatherSystem_C`，但 **`weatherState` 返回 `null`**（`confidence = medium`、`family` 缺失）。
原因：Aberration 的天气属性名**不在插件当前白名单内**（第 7 种字段族）。
**前端处理建议**：`weatherState` 为 `null` 时按"无数据"展示，**不要回退去解析 `fields`**（那是原始属性列表，含大量噪声）。

> 规律：**官方重制/DLC 图 = `BP_<前缀>_DayWeather_*`；原版图 = `UDS_<地图>_Weather_C`**（已 5 次验证）

---

## 六、`types` 响应

```json
{"ok": true, "sub": "types", "probe": 0, "worldTime": 250990000.0,
 "levelCount": 2566, "totalActors": 0,
 "types": [{"type": "osd", "label": "Orbital Supply Drop", "actorBased": true,
            "patterns": ["SupplyCrate_Base_Horde"],
            "difficultyTiers": ["easy","medium","hard","legendary"]}, ...]}
```

> ⚠️ **`typeCount` 已从 9 变为 11**（新增 `beaverdam`、`beaver`）。前端请**读取数组长度**，勿硬编码 9。

---

## 七、验收记录（2026-09-26 **全服 10 图**）

| 图 | 端口 | `typeCount` | 天气 target | conf | family | 河狸窝 |
|---|---|---:|---|:---:|---|:---:|
| Isl | 32320 | 11 ✅ | `UDS_Island_Weather_C` | high | uds | 1 |
| Sco | 32321 | 11 ✅ | `UDS_SE_Weather_C` | high | uds | 0 |
| Cen | 32322 | 11 ✅ | `UDS_TheCenter_Weather_C` | high | uds | 0 |
| **Abe** | 32323 | 11 ✅ | `BP_AB_WeatherSystem_C` | ⚠️ medium | ⚠️ — | 0 |
| Ext | 32324 | 11 ✅ | `BP_EXT_WeatherSystem_C` | high | ext_gen | 3 |
| Ast | 32325 | 11 ✅ | `BP_AST_DayWeather_WeatherSystem_C` | high | ext_gen | **15** |
| Rag | 32326 | 11 ✅ | `BP_RAG_DayWeather_WeatherSystem_C` | high | ext_gen | 6 |
| Val | 32327 | 11 ✅ | `BP_RAG_DayWeather_WeatherSystem_C` | high | ext_gen | 5 |
| Los | 32328 | 11 ✅ | `BP_LC_DayWeather_WeatherSystem_C` | high | ext_gen | 0 |
| Gen | 32329 | 11 ✅ | `BP_GEN_DayWeather_WeatherSystem_C` | high | ext_gen | 0 |

- 全部命令响应 **1.1–1.3 秒**
- 插件版本 **v9**（dll 1,594,368 B），10 图已统一部署
- `typeCount = 11` **10/10 通过**

### 河狸窝的**三种**已实测类名（全部被 `query beaverdam` 覆盖）

| 形态 | 类名 | 图 |
|---|---|---|
| 坝 | `BeaverDam_C` | Ext ×3 / Ast / Isl ×1 |
| **大型坝** | **`BP_BeaverDam_C`** | **Ast** |
| 巢穴 / lodge | `SupplyCrateBaseBP_Instantaneous_DenLogs_Child2_C` | **Rag ×6 / Val ×5** |

---

## 八、待前端确认

1. 是否需要「全图总数」？→ 需要则要设计**多点采样**策略（受坑 1 限制）
2. 光柱 `L<NN>` 的**等级→颜色**映射表由前端按图维护（Wiki 已知：Isl 蓝=25 / Sco 蓝=30 / Abe 蓝=35）
3. `weatherState` 的 `family` 分支 UI 是否需要区分展示
