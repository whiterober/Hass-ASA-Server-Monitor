> ⚠️ **本文件已并入** `前端事件对接文档_全服_20261006.md` **§12**（前端只看那一个文件）；此处留档。

# 全服天气事件与概率总表（11 端口 / 10 服在线）

> 生成时间：2026-10-06（**v2 修正版**：权重严格按 `asArray.num` 切片）
> 数据来源：本机对实服 RCON 的真实响应（原始 JSON：`tmp\_v122_raw\*.json`）
> 插件版本：**v122b2**（**全服 10 服已上线并实测通过**，编译戳 `Oct  6 2026 01:50:26` / dll 1,808,896 B @ 01:50:57）—— 2026-10-06 02:2x 重启后逐服复验：版本普查 10/10、`actor slim` / `weather slim` / `zones` / `biometemps` / `heatWaveActive` 均正常（详见主文档 §9 / §12.5）
> 🔴 **权重随 `GoodWeathersSinceBad` 经曲线 `C_EXT_BadWeatherWegiht` 动态变化** ⇒ 每次按当前 `WeatherChances` 归一化，勿写死；动态系数改用 `WorldProbe badwx`（派生法，实测 Ext factor **0.8**；无曲线驱动的图 v122b2 起 `factor:null`，此时只看 `probsPct[]`）
> 口径：**概率 = 该槽权重 ÷ 同组正权重之和**；UDS 家族**必须分昼夜**，ext_gen 家族用当前 `WeatherChances`（本身已是动态值）

## 0. 可预测性总表（先看这张）

| 服 | 端口 | 家族 | 天气概率表 | **下一天气能提前知道吗** | 事件型内容 | **事件能否精确预测** |
|---|---:|---|---|:---:|---|---|
| **Bob** | 32319 | — | ❌ **端口无响应** | — | — | — |
| **Isl** | 32320 | UDS | ✅ 5 槽日/夜 | ❌ 只能给概率 | 区域天气 `Weather_Override_Volume_C` | ⚠️ 走 `WorldProbe zones`（区域名+天气） |
| **Sco** | 32321 | UDS | ✅ 8 槽日/夜 | ❌ 只能给概率 | 雷暴/沙尘暴/热浪/极热 | ✅ **秒级判据**（无预兆） |
| **Cen** | 32322 | UDS | ✅ 5 槽日/夜 | ❌ 只能给概率 | 区域天气 ×6 | ⚠️ 走 `WorldProbe zones` |
| **Abe** | 32323 | ab | ❌ **无权重表** | ❌ 不可 | **地震** | ❌ **不可预测**（无计时/概率字段） |
| **Ext** | 32324 | ext_gen | ✅ 7 槽（5 种有效） | ❌ `nextWeather` 占位 | **陨石雨** | ✅ **提前 40~80 s** |
| **Ast** | 32325 | ext_gen | ✅ 7 槽 | ❌ 同上 | — | ⚠️ 秒级判据 |
| **Rag** | 32326 | ext_gen | ✅ 6 槽 | ❌ 同上 | **火山喷发** | ✅ **精确 ETA**（秒级） |
| **Val** | 32327 | ext_gen | ✅ 4 槽 | ❌ 同上 | — | ⚠️ 秒级判据 |
| **Los** | 32328 | ext_gen | ✅ 5 槽 | ❌ 同上 | — | ⚠️ 秒级判据 |
| **Gen** | 32329 | ext_gen | ✅ **每小地图各一张**（1/2/7 槽） | ❌ 同上 | **月球流星雨** | ✅ **实测误差 +0.225 s** |

- 🔴 **全部图共性**：**「下一天气是谁」都拿不到** —— 各家族 `nextWeather` / `NextWeatherReplicated` 均为占位值；能给的是**概率**（权重归一化）。
- 🔴 **Abe 是唯一完全不可预测的事件图**；**Isl / Cen 的「特殊区域天气」必须走 `WorldProbe zones`**，不能用主天气表推断。

## 1. 逐服天气概率（真实权重 + 归一化概率）

### Isl（32320）—— 家族 `uds`，名称表 `WeatherPresetList`（6 条）

| i | 天气（名称表） | 白天 权重 → 概率 | 夜晚 权重 → 概率 | 单次时长 |
|---:|---|---:|---:|---:|
| 0 | ColdFront（id 5） | `0` → **0.0%** | `0.2` → **20.0%** | 300 s |
| 1 | Partly_Cloudy（id 1） | `0.1` → **10.0%** | `0` → **0.0%** | 300 s |
| 2 | Rain（id 2） | `0.3` → **30.0%** | `0` → **0.0%** | 300 s |
| 3 | Foggy（id 3） | `0.3` → **30.0%** | `0.4` → **40.0%** | 300 s |
| 4 | HeatWave（id 4） | `0.3` → **30.0%** | `0.4` → **40.0%** | 300 s |

- 原始权重：`Day = [0.0, 0.1, 0.3, 0.3, 0.3]`；`Night = [0.2, 0.0, 0.0, 0.4, 0.4]`；`Lengths = [300.0, 300.0, 300.0, 300.0, 300.0]`
- 🔴 **必须分昼夜**；`i` = 预设表顺序下标（非天气 id）
- 备注：`dataHex` 固定返回 128 B（16 槽），**有效槽数 = `asArray.num`**，其后为相邻数组内存（已按 num 切片剔除）

### Sco（32321）—— 家族 `uds`，名称表 `WeatherPresetList`（8 条）

| i | 天气（名称表） | 白天 权重 → 概率 | 夜晚 权重 → 概率 | 单次时长 |
|---:|---|---:|---:|---:|
| 0 | ColdFront_SE（id 5） | `0` → **0.0%** | `0.5` → **29.4%** | 800 s |
| 1 | ElectricalStorm（id 7） | `0.1` → **4.5%** | `0.2` → **11.8%** | 425 s |
| 2 | Rain_SE（id 2） | `0.35` → **15.9%** | `0.1` → **5.9%** | 750 s |
| 3 | Foggy_SE（id 3） | `0.15` → **6.8%** | `0.2` → **11.8%** | 650 s |
| 4 | HeatWave_SE（id 4） | `0.7` → **31.8%** | `0` → **0.0%** | 700 s |
| 5 | Clear_Skies_SE（id 0） | `0.5` → **22.7%** | `0.5` → **29.4%** | 1200 s |
| 6 | Sand_Dust_Storm（id 6） | `0.25` → **11.4%** | `0.2` → **11.8%** | 425 s |
| 7 | Superheat（id 8） | `0.15` → **6.8%** | `0` → **0.0%** | 750 s |

- 原始权重：`Day = [0.0, 0.1, 0.35, 0.15, 0.7, 0.5, 0.25, 0.15]`；`Night = [0.5, 0.2, 0.1, 0.2, 0.0, 0.5, 0.2, 0.0]`；`Lengths = [800.0, 425.0, 750.0, 650.0, 700.0, 1200.0, 425.0, 750.0]`
- 🔴 **必须分昼夜**；`i` = 预设表顺序下标（非天气 id）
- 备注：`dataHex` 固定返回 128 B（16 槽），**有效槽数 = `asArray.num`**，其后为相邻数组内存（已按 num 切片剔除）

### Cen（32322）—— 家族 `uds`，名称表 `WeatherPresetList`（6 条）

| i | 天气（名称表） | 白天 权重 → 概率 | 夜晚 权重 → 概率 | 单次时长 |
|---:|---|---:|---:|---:|
| 0 | ColdFront_TheCenter（id 5） | `0.25` → **12.5%** | `0.25` → **12.5%** | 550 s |
| 1 | Rain_TheCenter（id 2） | `0.25` → **12.5%** | `0.25` → **12.5%** | 550 s |
| 2 | Foggy_TheCenter（id 3） | `0.25` → **12.5%** | `0.5` → **25.0%** | 550 s |
| 3 | HeatWave_TheCenter（id 4） | `0.25` → **12.5%** | `0` → **0.0%** | 550 s |
| 4 | Clear_Skies_TheCenter（id 0） | `1` → **50.0%** | `1` → **50.0%** | 800 s |

- 原始权重：`Day = [0.25, 0.25, 0.25, 0.25, 1.0]`；`Night = [0.25, 0.25, 0.5, 0.0, 1.0]`；`Lengths = [550.0, 550.0, 550.0, 550.0, 800.0]`
- 🔴 **必须分昼夜**；`i` = 预设表顺序下标（非天气 id）
- 备注：`dataHex` 固定返回 128 B（16 槽），**有效槽数 = `asArray.num`**，其后为相邻数组内存（已按 num 切片剔除）

### Abe（32323）—— 家族 `ab`，名称表 `WeatherPresetList`（0 条）

- ❌ **无权重表**：`WeatherWeights_Day/Night` 与 `WeatherChances` 全为 `null`（Abe 家族未接名称/权重槽）
- ⇒ Abe 天气**只有 id 可读**（`currentWeather` = null）⇒ **无概率可算**；地震见 §2.4

### Ext（32324）—— 家族 `ext_gen`，名称表 `WeatherPresetList`（5 条）

| 槽位 | 天气名（按 id 对齐） | 权重 | 概率 | 基准权重 |
|---:|---|---:|---:|---:|
| 0 | — | `0` | **0.0%** | `0` |
| 1 | WeatherPreset_EXT_Cloudy | `1` | **21.7%** | `1` |
| 2 | WeatherPreset_EXT_Overcast | `1` | **21.7%** | `1` |
| 3 | WeatherPreset_EXT_Spooky | `0.8` | **17.4%** | `1` |
| 4 | — | `0` | **0.0%** | `0` |
| 5 | WeatherPreset_EXT_ClearSky | `1` | **21.7%** | `1` |
| 6 | WeatherPreset_EXT_MeteorRain | `0.8` | **17.4%** | `1` |

- 权重原始：`[0.0, 1.0, 1.0, 0.8, 0.0, 1.0, 0.8]`（槽数 `num=7`）
- 名称表：id 1=WeatherPreset_EXT_Cloudy；id 2=WeatherPreset_EXT_Overcast；id 3=WeatherPreset_EXT_Spooky；id 5=WeatherPreset_EXT_ClearSky；id 6=WeatherPreset_EXT_MeteorRain
- ✅ **陨石雨 = id 6**；预兆 40~80 s（`transMin/Max`）；实测：音量 0.03→0.50(+13 s)→0.97(+31 s)→ **`fxActive=1`(+44 s)**
- 🔴 权重随 `GoodWeathersSinceBad` 经曲线 `C_EXT_BadWeatherWegiht` 动态变化 ⇒ **每次按当前 `WeatherChances` 归一化，勿写死**（曲线点无需硬读：v122b 起用 `WorldProbe badwx` 派生法给出 `factor` + `learned[]`，实测 Ext **0.8**）

### Ast（32325）—— 家族 `ext_gen`，名称表 `WeatherPresetList`（7 条）

| 槽位 | 天气名（按预设表顺序对齐） | 权重 | 概率 | 基准权重 |
|---:|---|---:|---:|---:|
| 0 | DA_WeatherPreset_AST_ClearSky | `1` | **34.5%** | `0` |
| 1 | DA_WeatherPreset_AST_Fog | `0.6` | **20.7%** | `1` |
| 2 | DA_WeatherPreset_AST_Rain | `0.4` | **13.8%** | `1` |
| 3 | DA_WeatherPreset_AST_Heatwave | `0.6` | **20.7%** | `1` |
| 4 | WeatherPreset_AST_Sandstorm | `0.1` | **3.4%** | `0` |
| 5 | DA_WeatherPreset_AST_ClearSky_Fog | `0.1` | **3.4%** | `1` |
| 6 | DA_WeatherPreset_AST_Rain_Fog | `0.1` | **3.4%** | `1` |

- 权重原始：`[1.0, 0.6, 0.4, 0.6, 0.1, 0.1, 0.1]`（槽数 `num=7`）
- 名称表：id 13549692=DA_WeatherPreset_AST_ClearSky；id 5353682=DA_WeatherPreset_AST_Fog；id 9248846=DA_WeatherPreset_AST_Rain；id 10526457=DA_WeatherPreset_AST_Heatwave；id 13537236=WeatherPreset_AST_Sandstorm；id 13830887=DA_WeatherPreset_AST_ClearSky_Fog；id 13831035=DA_WeatherPreset_AST_Rain_Fog

### Rag（32326）—— 家族 `ext_gen`，名称表 `WeatherPresetList`（6 条）

| 槽位 | 天气名（按预设表顺序对齐） | 权重 | 概率 | 基准权重 |
|---:|---|---:|---:|---:|
| 0 | WeatherPreset_RAG_ClearSky | `1` | **48.8%** | `0` |
| 1 | WeatherPreset_RAG_Fog | `0.2` | **9.8%** | `1` |
| 2 | WeatherPreset_RAG_Rain | `0.35` | **17.1%** | `1` |
| 3 | WeatherPreset_RAG_Sandstorm | `0.15` | **7.3%** | `1` |
| 4 | WeatherPreset_RAG_ElectricalStorm | `0.2` | **9.8%** | `0` |
| 5 | WeatherPreset_RAG_Superheat | `0.15` | **7.3%** | `1` |

- 权重原始：`[1.0, 0.2, 0.35, 0.15, 0.2, 0.15]`（槽数 `num=6`）
- 名称表：id 13504264=WeatherPreset_RAG_ClearSky；id 5353331=WeatherPreset_RAG_Fog；id 9248384=WeatherPreset_RAG_Rain；id 13493531=WeatherPreset_RAG_Sandstorm；id 6877403=WeatherPreset_RAG_ElectricalStorm；id 3959118=WeatherPreset_RAG_Superheat

### Val（32327）—— 家族 `ext_gen`，名称表 `WeatherPresetList`（4 条）

| 槽位 | 天气名（按预设表顺序对齐） | 权重 | 概率 | 基准权重 |
|---:|---|---:|---:|---:|
| 0 | WeatherPreset_VAL_ClearSky | `1` | **64.5%** | `0` |
| 1 | WeatherPreset_VAL_Fog | `0.2` | **12.9%** | `1` |
| 2 | WeatherPreset_VAL_Rain | `0.2` | **12.9%** | `1` |
| 3 | WeatherPreset_VAL_ElectricalStorm | `0.15` | **9.7%** | `1` |

- 权重原始：`[1.0, 0.2, 0.2, 0.15]`（槽数 `num=4`）
- 名称表：id 13568744=WeatherPreset_VAL_ClearSky；id 5352204=WeatherPreset_VAL_Fog；id 9247411=WeatherPreset_VAL_Rain；id 6876294=WeatherPreset_VAL_ElectricalStorm

### Los（32328）—— 家族 `ext_gen`，名称表 `WeatherPresetList`（5 条）

| 槽位 | 天气名（按预设表顺序对齐） | 权重 | 概率 | 基准权重 |
|---:|---|---:|---:|---:|
| 0 | WeatherPreset_LC_ClearSkyV2 | `1` | **41.7%** | `0` |
| 1 | WeatherPreset_LC_ClearSkyV3 | `1` | **41.7%** | `1` |
| 2 | WeatherPreset_LC_SnowFluery | `0.2` | **8.3%** | `1` |
| 3 | WeatherPreset_LC_Blizzard | `0.2` | **8.3%** | `1` |
| 4 | WeatherPreset_LC_ClearSky | `0` | **0.0%** | `0` |

- 权重原始：`[1.0, 1.0, 0.2, 0.2, 0.0]`（槽数 `num=5`）
- 名称表：id 13517021=WeatherPreset_LC_ClearSkyV2；id 14576822=WeatherPreset_LC_ClearSkyV3；id 13912101=WeatherPreset_LC_SnowFluery；id 13742185=WeatherPreset_LC_Blizzard；id 15605184=WeatherPreset_LC_ClearSky

### Gen（32329）—— 家族 `ext_gen`，名称表 `WeatherPresetList`（7 条）

- 🔴 **五小地图各自独立**（`DayWeather_WeatherSystem` 多实例；`propsIdx` 顺序可能随加载变化）

| `propsIdx` | 槽数 | 权重数组 | 归一化概率 |
|---:|---:|---|---|
| 0 | 1 | `1` | 100.0% |
| 1 | 2 | `1` · `1` | 50.0% · 50.0% |
| 2 | 7 | `1` · `0.2` · `0.2` · `0.2` · `0.1` · `0.1` · `0.1` | 52.6% · 10.5% · 10.5% · 10.5% · 5.3% · 5.3% · 5.3% |
| 3 | 2 | `1` · `1` | 50.0% · 50.0% |
| 4 | 2 | `1` · `1` | 50.0% · 50.0% |
| 5 | 2 | `1` · `1` | 50.0% · 50.0% |

- 只有**海洋图**含 7 种天气；其余图预设表仅 `*_ClearSky`（天气由序列/蓝图驱动，**不适用概率预测**）
- 前端取法：`WorldProbe weather full=1 limit=6 actors=1 slim=1` → `wxSystems[].miniMapType / currentWeather / secondsUntilChange`

## 2. 事件型内容

### 2.1 Gen 月球流星雨（`LunarMeteorController_C`，全世界 1 个）

| 项 | 实测值 |
|---|---|
| `TimeLastEvent` | `207611509.06` |
| `ActualTimeBetweenEvents` | `799.527` |
| `MinTimeBetweenEvents` | `300` |
| `MaxTimeBetweenEvents` | `800` |
| `DurationOfEvent` | `240` |
| `ParticleIntensity` | `20` |
| `CurrentStormRotation` | `57.9191` |
| `WarmUpLength` | `60` |

- 间隔 **300~800 s 均匀随机**（均值 550 s）；持续 **240 s** ⇒ 时间占比 ≈ **44%**；预热 60 s
- 公式 `ETA = TimeLastEvent + ActualTimeBetweenEvents − worldClock`；实测误差 **+0.225 s**（2026-10-06）
- 🔴 无玩家在 Gen 时定时器不推进（空服限制，已实测）

### 2.2 Rag 火山（`BP_VolcanoManager_C`）

| 项 | 实测值 |
|---|---|
| `VolcanoActive` | `0` |
| `VolcanoStarting` | `0` |
| `VolcanoEnding` | `0` |
| `WorldVolcanicIntensity` | `0` |
| `LocalVolcanicIntensity` | `0` |
| `TimeNextVolcanoEvent` | `0` |
| `TimeVolcanoEventStarted` | `0` |
| `TimeVolcanoEventEnds` | `0` |
| `VolcanoEventLength` | `120` |
| `LavaEnabled` | `0` |
| `ActorsInLava` | `0` |

- 间隔 `VolcanoIntervalMinMax = [5000, 15000]` s；持续 120 s ⇒ 占比 ≈ **1.2%**
- `TimeNextVolcanoEvent = 0` ⇒ **未排期**（前端显示「空闲期·未排期」）；正常流程在事件结束后自动排期

### 2.3 Ext 陨石雨

- 天气 **id 6**（`WeatherPreset_EXT_MeteorRain`）；预兆 40~80 s；前端用 `WorldProbe meteor`（**770 B**），按 `phase ∈ {incoming, active}` 弹窗

### 2.4 Abe 地震

- ❌ **不可预测**（208 属性无双筛计时/概率字段，无独立调度器）⇒ 前端只显示规律文案，不接字段

### 2.5 Isl / Cen 特殊区域天气

- 实测 Isl 有 `Weather_Override_Volume_C`，**Cen 有 6 个** ⇒ 走 `WorldProbe zones fresh=1`（实测覆盖 Isl×4 / Cen×6，返回区域名 + 该区域天气）

## 3. 前端取数命令与实测体积（v122 `slim=1`）

| 目的 | 命令（前缀 `TransferIdentityFix.`） | 实测体积 |
|---|---|---:|
| 某图天气语义 | `WorldProbe weather full=1 limit=1 slim=1` | Isl 2.5K／Sco 12.5K／Cen 11.6K／Abe 3.7K／Ext 3.0K／Ast 3.7K／Rag 3.6K／Val 3.4K／Los 3.4K／Gen 6.2K（**对比 full：52~93% 降幅**） |
| Gen 六图 | `WorldProbe weather full=1 limit=6 actors=1 slim=1` | 6.2 KB |
| UDS 权重（日/夜） | `actor filter=UDS_<地图>_Weather props=1 probe=WeatherWeights_Day,WeatherWeights_Night,WeatherEventLengths top=1` | ~21 KB（未 slim） |
| ext_gen 权重 | `actor filter=WeatherSystem props=1 propsIdx=0 probe=WeatherChances,PossibleWeatherChances top=1` | ~16 KB |
| Gen 五图权重 | `actor filter=DayWeather_WeatherSystem props=1 propsIdx=0..5 probe=WeatherPresetList,WeatherChances top=1` | ~18 KB |
| 陨石雨 | `WorldProbe meteor` | **0.77 KB** |
| 月球 / 火山 / 地震 | `actor filter=<LunarMeteorController / VolcanoManager / Earthquake> props=1 propsIdx=0 top=1`（加 `slim=1` 走白名单） | 10.8K / 10.6K / 10.3K → 白名单 <1 KB |
| 区域天气（Isl/Cen） | `WorldProbe zones fresh=1` | 视区域数 |

## 4. ⚠️ v122 部署状态与 hotfix

- **全服**：`weather slim=1` ✅ 正常（10/10 服实测降幅 52~93%）；`weatherState.heatWaveActive` ✅ 在 Sco/Cen/Ext 出现（其余图 `currentWeatherId` 本身为 null ⇒ 按设计不输出）
- 🔴 **`actor slim=1` / `fields=` 在 `00:30:33` 构建里未生效**（该分支只解析前 4 个 token，参数被丢弃；实测 `VolcanoManager` full=slim=10,623 B）
- ✅ **已修复**：`01:00:29` 构建改为扫描完整参数串（`slim=1` / `fields=` 位置不再受限）⇒ **待重新投放该 dll 后 `actor slim` 才生效**

