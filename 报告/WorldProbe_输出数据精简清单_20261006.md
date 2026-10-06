# 输出数据「精简清单」（留档）

> 生成时间：2026-10-06　｜　依据：`tmp\_audit_fields_out.txt`（3 次采样 × 每命令）＋ `tmp\_audit_report.md`（严格口径字节占比）
> 采样窗口：**24 秒 × 3 次**（每命令），共 9 条命令：Sco/weather·actor、Abe/weather·actor、Ext/weather·meteor、Rag/actor、Gen/weather·lunar
> 用途：v122 `slim=1` 白名单设计依据；本清单**只列"可精简"**，改留判断见文末「防误删」

---

## 一、两套体积口径（别混用）

| 口径 | 定义 | 用途 |
|---|---|---|
| **严格口径** | 仅按已知「废键名模式」统计（`dump`/`fields`/`*Note`/`unreadable`…） | 得出各命令**废字段字节占比** |
| **区块口径** | 按顶层区块整体体积统计（`dump`/`fields`/`actorProps`/`wxSemantics`…） | 得出**体积大头在哪**（这才是真问题） |

### 严格口径（审计报告）

| 服/命令 | 响应字节 | 废字段字节 | 占比 |
|---|---:|---:|---:|
| Sco_weather | 25,782 | 19,709 | **76.4%** |
| Ext_weather | 16,883 | 1,190 | 7.0% |
| Abe_weather | 30,700 | 1,217 | 4.0% |
| Ext_meteor | 769 | 18 | 2.3% |
| Gen_weather | 93,924 | 1,353 | 1.4% |
| Abe_actor | 10,257 | 61 | 0.6% |
| Gen_lunar | 10,810 | 61 | 0.6% |
| Rag_actor | 10,623 | 61 | 0.6% |
| Sco_actor | 19,373 | 61 | 0.3% |

### 区块口径（真正的大头）

| 服/命令 | 总字节 | 各区块体积（降序） |
|---|---:|---|
| Gen/weather | 104,047 | **dump=83,353** · cloud=5,529 · fields=4,640 · actors=3,805 · wxSystems=2,750 · wxSemantics=1,502 · regionMap=905 · weatherState=665 |
| Abe/weather | 33,677 | **dump=24,116** · fields=4,653 · wxSystems=2,016 · actors=958 · wxSemantics=834 · weatherState=544 · wxSystemsNote=134 |
| Sco/weather | 27,331 | **wxSemantics=15,809** · dump=5,064 · fields=4,975 · weatherState=800 · actors=198 · note=59 |
| Ext/weather | 18,265 | **dump=9,932** · fields=4,795 · wxSemantics=1,302 · weatherState=759 · wxSystems=517 · actors=392 |
| Sco/actor | 20,954 | actorProps=20,699 · actors=198 |
| Gen/lunar | 11,636 | actorProps=11,358 · actors=214 |
| Rag/actor | 11,406 | actorProps=11,144 · actors=205 |
| Abe/actor | 11,013 | actorProps=10,762 · actors=198 |
| Ext/meteor | 333 | actor=113 · note=64（**已是目标形态**） |

---

## 二、分类精简清单

### 🅰️ 调试 / 自检块 —— 体积最大头

| 字段族 | 典型键 | 实测规模 | 处置 |
|---|---|---|---|
| `dump[]` 全量转储 | `dumpCount=80`；`dump[i].{class,objectName,probedProperties,totalMatched,fields[j].{name,size,value,unreadable}}` | Gen 83,353 B（80.1%）/ Abe 24,116（71.6%）/ Ext 9,932（54.4%）/ Sco 5,064 | ⛔ `slim=1` 不输出 |
| `fields[]` 字段表 | `fields[j].{name,size,value,unreadable}` | Sco 4,975 / Ext 4,795 / Abe 4,653 / Gen 4,640 | ⛔ 同上 |
| `wxSemantics.arrayProbe.*` | `stride16[]`/`stride24[]`/`rawSlots[]`/`elementSize`/`num` | Sco `wxSemantics` 整块 15,809 B（57.8%），大半在此 | ⛔ 只留 `presetTable` |
| `wxSemantics.settingsScan[]` / `settingsRaw` | `off`/`arrayNum`/`arrayMax`/`objects[]` | 同上 | ⛔ 运维专用 |
| 固定文案（重复 4–6 份） | `note`/`regionMapNote`/`wxSystemsNote`/`weatherState.weatherNameNote`/`cloud.note`/`wxSemantics.note` | 每个 59–134 B | ⛔ 全删或合并 1 条 |
| 自检标量 | `confidence`/`dumpCount`/`dumpSkip`/`matchedTotal`/`actors[].scalarProps`/`actorProps.{nonZero,readable,engineSkipped,filtered}`/`weatherState.{semFieldsFound,semUnreadable}`/`propSelf.*`/`structProbe`/`structCand`/`payloadProbe.*`/`enumIndices.*`/`unreadable/unreadableEmitted`/`regionMapAgent` | Sco/weather **91 项**、Gen 13、Abe 13、Ext 11 | ⛔ 删除（`engineSkipped/filtered/idx/propsIdx` 实测恒 0） |

### 🅱️ 恒 `null` 占位键 —— 按 family 白名单裁剪

| 服/命令 | 键数 | 典型键 |
|---|---:|---|
| Abe/weather | 52 | `cloud`、`fields[*].value`、`dump[*].fields[*].value`、`wxSemantics.{arrayProbe,defaultWeather,electricalStorm,eventLengths,presetTable,sandstorm,settingsRaw}`、`enumIndices.*`、`extWeather.*`、`payloadProbe.*` |
| Sco/weather | 55 | `electricalStorm.scopeProbe.*.{asArray,asString}`（10 槽×2）、`maskTargets.*`、`cloud` |
| Gen/weather | 40 | `weatherState.{currentWeatherId,nextWeatherId,prevWeatherId}`、`cloud.regions[*].{currentWeatherClass,nextWeatherClass,prevWeather,currentWeather,miniMapType,nextWeather}` |
| Ext/weather | 27 | 同 Abe 家族 + `wxSystems[0].{currentWeather,nextWeather,prevWeather,miniMapType}` |

**规律**：`wxSemantics` 里**非本图家族槽恒定 null**（Abe/Gen 无 `electricalStorm`、非 Ext 图无 `extWeather`、非 Sco 图无 `sandstorm`）
⇒ 按 `weatherState.family`（`uds`/`ab`/`ext_gen`）输出本族，其余整块不输出。

### 🅲 恒 0 / 同槽多口径重复读数

| 服/命令 | 恒 0 键数 | 典型键 |
|---|---:|---|
| Sco/weather | **130** | `weatherState.{lightningIntensity,rainStrength,weatherLerpValue,changeStartTime,inOverrideVolume,prevWeatherId}`、`electricalStorm.region`、`maskTargets.*`（8）、`scopeProbe.*` 的 `asFloat2[0/1]`+`asInt2[0/1]`（每槽 4 个重复口径） |
| Gen/weather | 32 | `cloud.activeIdx`、`cloud.regions[*].{elapsed,timeOfDay,prevWeatherRaw,currentWeatherRaw,nextWeatherRaw,inTransition,miniMapFlags[*].value}`、`weatherState.{inTransition,nextWeatherReplicated,temperatureOffset,transitionEnd,weatherSoundRegionMul}` |
| Ext/weather | 25 | 同族 + `wxSystems[0].{inTransition,miniMapFlags[*].value}` |
| Abe/weather | 23 | `weatherState.{inNight,exposureDawnWeight,exposureNightWeight,nightlightWeight,underWater,inCave,inInterior}`、`regionMapAgent`、`x/y/z` |

- 同一槽被读 **6 种口径**：`hex` / `asFloat2[0,1]` / `asInt2[0,1]` / `asArray` / `asString`
- ⚠️ `regionNameProbe.asString` **雷暴中有值**（实测 `"Center"`）⇒ 只删恒 0 口径（`asFloat2/asInt2/asArray`），**保留有效口径**
- 处置：`slim=1` 时每槽只输出**有意义的 1~2 种口径**

### 🅳 引擎默认常量 / 标识类 —— 一次性取，不轮询

| 子类 | 字段 |
|---|---|
| 温度常量 | `baseSummerTemperature=23`、`baseAutumnTemperature=21`、`baseWinterTemperature=11`、`minValidTemperature=-30`、`maxValidTemperature=60`、`interiorTemperature=22.2`、`HotTemperatureFactor=55`、`ColdTemperatureFactor=-56`、`transitionLength=120` |
| 沙尘/粒子常量 | `Dust Depth`、`Max Dust Coverage`、`Particle Collision Enabled` |
| 身份/类名（每次重复） | `actors[].{class,objectName,level}`、`actorProps.{class,objectName}`、`wxSystems[].{class,objectName,idx}`、`miniMapFlags[].name`、`changeTimerMin/Max` |
| 冗余镜像 | `actors[]` ↔ `actorProps.{class,objectName}`；`wxSystems` ↔ `cloud.regions`（Gen 里 2.75 KB + 5.53 KB 两份）；`wxSemantics.arrayProbe.presetTable` ↔ `wxSemantics.presetTable` |

落在审计 **「CONST 其它」桶**：Sco 157 项 / Gen 140 / Ext 89 / Abe 67。

### 🅴 `actor` 类命令的全量属性转储

| 命令 | `actorProps` 体积 | 属性数 | 前端真正需要 |
|---|---:|---:|---|
| Sco/actor | 20,699 B | 737 | ~9 项（`electricalStorm.region`、`regionNameProbe.asString`、`sandstorm.*`） |
| Gen/lunar | 11,358 B | 224 | **6 项**（`TimeLastEvent`/`Actual`/`Min`/`Max`/`DurationOfEvent`/`CurrentStormRotation`） |
| Rag/actor | 11,144 B | 218 | 8 项（`VolcanoActive`/`Starting`/`Ending`/`WorldVolcanicIntensity`/`TimeNextVolcanoEvent`…） |
| Abe/actor | 10,762 B | 208 | 1 项（`bEarthQuake`，已决定不接） |
| 样板 | **Ext/meteor 333 B** | — | ✅ 已是目标形态 |

**实现要点（已定位）**：`actorProps` 由**单一共享函数** `TifDumpParams()` 产出（`TransferIdentityFixAPI.cpp` ~4900–4953），
`actor` / `allprops` / `dump[i]` 三处共用 ⇒ 加白名单只需**改 1 个函数签名 + 传参**。

### 🅵 前端不用的运维/调试子命令

`wxset` / `callfunc` / `exec` / `types` / `query` / `notes` / `levels` / `scan` 的响应（含 `structProbe`/`structCand`/`propSelf`）—— 保持现状。

---

## 三、精简后目标体积

| 命令 | 现状 | 目标 | 依据 |
|---|---:|---:|---|
| Gen/weather | 104,047 B | ~1.5 KB | 去 `dump` 83.4K + `fields` 4.6K + 镜像 `cloud` |
| Abe/weather | 33,677 B | ~1.5 KB | 去 `dump` 24.1K + `fields` 4.7K + null 52 键 |
| Sco/weather | 27,331 B | **~2.5 KB** | 去 `wxSemantics` 15.8K（留 `presetTable`+`sandstorm`+`electricalStorm` 有效项） |
| Ext/weather | 18,265 B | ~1.5 KB | 去 `dump` 9.9K + `fields` 4.8K |
| actor 类（Sco/Rag/Abe/Gen-lunar） | 10–21 KB | **0.3–1 KB** | 按 `Ext/meteor` 333 B 样板 |
| Ext/meteor | 333 B | 333 B | ✅ 已达标 |
| **4 服 60 s 轮询合计** | **≈143 KB/轮 ≈ 206 MB/天** | **≈6.5 KB/轮 ≈ 9.4 MB/天** | ↓ **≈95%** |

---

## 四、⚠️ 防误删（"恒定"陷阱）

采样窗口仅 24 s × 3 次：**事件型字段未触发时照样「恒定」**——
`sandstorm.active=false`、`bMeteorFXActive=0`、`VolcanoActive=0`、`electricalStorm.region=0`、`weatherState.lightningIntensity=0`
**全部"恒定"但都是核心判据**。⇒「恒定」只能当线索，**删留必须按"该字段是否可能随事件变化"判断**。

**明确不要删**：`worldTime`/`worldTimeSource`、`timeOfDay`/`timeOfDaySolsticeRemapped`（唯一随昼夜变）、
`secondsUntilChange`/`timerNextWeather`/`beginAt`、`presetTable`（id→名称）、`regionNameProbe.asString`、
`sandstorm.*`、`electricalStorm.region`、`bMeteorFXActive`/`phase`/`volumeTrend`、
`VolcanoActive`/`TimeNextVolcanoEvent`、`biometemps.temp`/`actorX/Y/Z`、`globalBase`/`globalWind`。

---

## 五、落地方式（v122）

1. **新增 `slim=1`**（白名单视图）—— `weather` / `actor`；**默认仍 `full=1`**，前端切默认后再翻转；
2. `biometemps` 用 `brief=1`（热力图只需 `idx/name/temp/wind/actorX/Y/Z`）；
3. `zones` 只回 `regionName + 天气字段`（Isl×4 / Cen×6 特殊区域）；
4. 事件到达检测（`bEarthQuake` 0↔1、月球 `TimeLastEvent` 变化）并入。

> 📌 数据来源：`tmp\_audit_fields_out.txt`、`tmp\_audit_report.md`；采样脚本 `tmp\_audit_fields.py`、`tmp\_audit_report.py`（只读）。

---

## 六、v122 落地后的补充（2026-10-06 00:31 构建）

- **实现方式**：所有精简项都挂在**新增参数 `slim=1`** 下（`weather` / `actor`），**默认关闭** ⇒ 不加参数的输出与 v121 **字节级一致**，对现有前端零影响。
- **逐键清单**（前端可直接照它改）：见 `前端事件对接文档_全服_20261006.md` **§9.5.1**（A 段 `weather` 9 项 / B 段 `actor` 规则 / C 段保留键）。
- **`actor` 白名单两种用法**：① `slim=1`（按 `filter=` 关键字套内置表：LunarMeteor / Volcano / Earthquake / Weather）；② `fields=A,B,C`（显式，优先级最高；`+` 代空格）。
- **安全兜底**：`actor ... slim=1` 遇到未列入内置表的 `filter=` 时**不裁剪**，不会返回空属性集。
- **另附**：`热浪` 判定新增派生键 `weatherState.heatWaveActive`（= `currentWeatherId == 4`），口径跨图统一。
- 产物：`TransferIdentityFixAPI.dll` = **1,800,192 B @ 2026-10-06 00:31:02**（待部署）。
