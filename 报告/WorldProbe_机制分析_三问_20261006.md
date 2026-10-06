# 机制分析：Rag 沙尘暴 · Gen 雪崩 · Ext 王泰坦（全服实服实测）

> 生成时间：2026-10-06 12:2x　｜　插件版本：**v122b2**（编译戳 `Oct  6 2026 01:50:26`）
> 数据来源：**本机对实服 RCON 的真实响应**（Rag 32326 / Gen 32329 / Ext 32324）；原始 JSON 存于 `tmp\_q3_*_weather.json`、`tmp\_q5_ext_*.json`
> ⚠️ 全部结论均有实测证据；不可读（指针/不透明数组）的项在文中显式标注 `unreadable`，不猜值。

---

## 1. Rag 沙尘暴（体感"仅沙漠区域"）

### 1.1 载体：**不是独立 Actor**

| 类 | 实例数 | 职责 |
|---|---:|---|
| `BP_RAG_DayWeather_WeatherSystem_C` | 1 | **掷骰 + 计时**（决定"这次是什么天气"） |
| `BP_RAG_DayWeather_Agent_C` | 1 | **区域权重**（决定"哪里生效"） |
| `BP_RAG_DayWeather_RegionTimeOfDay_C` | 2 | 区域昼夜（`RegionTOD_Region0` / `Region3` 有实例，`Region1/2` 为 null） |
| `BP_DayWeather_CloudSystem_C` | 1 | 云层 |
| `BP_RAG_WeatherEffects_C` | 1 | **实际天气效果（含沙尘暴）** |

- `scan filter=Sand` / `Storm` / `Weather` ⇒ **沙尘暴没有专属 actor**（同为 SE 沙尘暴结论：`Sand/Dust/Storm` 全 0 命中）。

### 1.2 全局掷骰（决定"是不是沙尘暴"）

- **预设表**（`WeatherPresetList`，索引即内部 id）：

| idx | 预设 | 当前权重 |
|---:|---|---:|
| 0 | `WeatherPreset_RAG_ClearSky` | 1（base 为 0 ⇒ 兜底项） |
| 1 | `WeatherPreset_RAG_Fog` | 0.20 |
| 2 | `WeatherPreset_RAG_Rain` | 0.35 |
| **3** | **`WeatherPreset_RAG_Sandstorm`** | **0.15** |
| 4 | `WeatherPreset_RAG_ElectricalStorm` | 0.20 |
| 5 | `WeatherPreset_RAG_Superheat` | 0.15 |

- **计时**：`WeatherChangeTimerMin/Max = 1500 / 2500 s`（每 25~42 min 掷一次）、`WeatherTransitionTimeMin/Max = 40 / 80 s`（过渡）、当前 `TransitionDuration = 54.01 s`、`TimerNextWeather = 238449024.9`（`secondsUntilChange` 可直接倒计时）。
- **实时概率**：`chanceSum = 2.05` ⇒ `probsPct = [48.78, 9.76, 17.07, **7.32**, 9.76, 7.32]`
  ⇒ **Rag 沙尘暴当前单次掷骰概率 = 7.32%**（= 0.15 ÷ 2.05）。
- `GoodWeathersSinceBad` 在 Rag **不可读** ⇒ 无曲线驱动 ⇒ `badwx.factor` 为 `null`（v122b2 行为，已验证）。
- ⚠️ `WeatherChances` / `PossibleWeatherChances` / `CurrentWeather` 等**直读为 `unreadable`**（TArray/指针），必须走 `WorldProbe badwx` 的派生路径。
- 📌 **实测观察（2026-10-06，13:11 复测）**：`PossibleWeatherChances`（即 `slots[].base`）**读数随服务器状态变化** —— 重启后约 2 分钟时为“与 `current` 相同”，稳定后为作者基准 **`[0,1,1,1,0,1]`**；而 `WeatherChances`（`current`）两次**完全一致** ⇒ 概率计算（`sandstormPct` / `probsPct`）不受影响；**前端勿依赖 `base` / `ratio`**。
- 📌 **新增命令**：`WorldProbe sandstorm`（v122b3）一次给出三层 + `sandstormPct` + `active`；Rag 已于 2026-10-06 13:11 实测通过（详见主文档 §14.5）。
- 📌 **Rag 的雷暴（`ElectricalStorm`，预设 idx4，概率 9.76%）不是区域性的**（`electricalStorm` 语义块为 `null`、效果层无雷参数、无掩膜 actor）；**对照 Sco/SE 的雷暴是区域性**（`ElectricalStormRegion=2` = "NW" + 整套 DLWE 掩膜）—— 详见主文档 **§17**。

### 1.3 区域闸门（决定"哪些区域真的看到沙尘暴"）

| 对象 | 关键字段 | 当前值 | 作用 |
|---|---|---:|---|
| `BP_RAG_WeatherEffects_C` | `SandstormAmount` | 0 | 沙尘暴强度 |
| | `SandstormDebries` | 0 | 碎屑特效量 |
| | **`bInSandstormTrigger`** | **0** | **是否位于沙尘暴触发卷内**（区域闸门的核心开关） |
| | `bWeatherOffInCave` | 0 | 洞穴内关闭天气 |
| | `SandSweepSequence` / `SandSweepSeqActor` / `SandSweepSeqPlayer` / `SandSweepWeight` | 部分 `unreadable` | 沙墙**扫过**地图的序列/权重 |
| | `bInSnowBiome` / `SnowRegionWeight` | — | 雪原侧同类机制（对照） |
| `BP_RAG_DayWeather_Agent_C` | `RegionWeights`（4 槽，size 32） | 0（不可读） | 每区域权重 |
| | `SeqWeight_Region0..3` | **Region0=1**，其余 0 | 当前生效区域序列权重 |
| | `RegionTOD_Region0..3` | 0/3 有实例，1/2 为 null | 区域昼夜实例（`regionMapNote`：mini-map 索引 → RegionTimeOfDay） |
| `WeatherSystem` | `WeatherSoundRegionMul` | 0 | 区域音效倍率 |

**⇒ 机制结论**：Rag 沙尘暴是**「全局掷骰决定天气类型 + 区域触发卷/权重决定生效范围」**的两段式：天气系统会把 `Sandstorm` 当作一次全局天气选出（7.32%），但**沙尘暴的视觉与伤害只在沙尘暴触发卷（沙漠区域）内生效**——卷外玩家看不到（`bInSandstormTrigger=0`、`SandstormAmount=0`），所以体感是"沙尘暴只在沙漠"。

### 1.4 前端可直接用

| 需求 | 命令 | 字段 |
|---|---|---|
| 沙尘暴概率 | `WorldProbe badwx`（Rag） | `probsPct[3]`（当前 7.32%） |
| 下次换天气倒计时 | `WorldProbe weather full=1 limit=1 slim=1` | `weatherState.secondsUntilChange` / `nextWeatherAt` |
| 是否正在沙尘暴（含区域） | `WorldProbe actor filter=RAG_WeatherEffects props=1 propsIdx=0 fields=SandstormAmount,SandstormDebries,bInSandstormTrigger` | `SandstormAmount>0`（全局在刮）、`bInSandstormTrigger=1`（该玩家/卷内在刮） |
| **一键取全（v122b3 推荐）** | `WorldProbe sandstorm` | `active`（是否正在沙尘暴）、`weights.sandstormPct`（概率）、`timer.secondsUntilChange`（倒计时）、`region.seqWeights`（区域） |

---

## 2. Gen 雪崩（**只在 Gen 雪原**；Rag 没有雪崩）

### 2.1 触发器：`HazardTrigger_Avalanche_C` × **51**

`Gen scan filter=Hazard` 实测：

| 类 | 数量 | 说明 |
|---|---:|---|
| `HazardTrigger_Slide_C` | 73 | 滑坡/碎石滑落（与雪崩同属 `AHazardTrigger` 家族） |
| `Buff_Hazard_BubbleBox_C` | 71 | 危害气泡框 Buff |
| **`HazardTrigger_Avalanche_C`** | **51** | **雪崩触发卷** |
| `Hazards_Volcanic_WP_C` | 1 | 火山危害路径点 |
| `Volcanic_Eruption_Hazard_C` | 1 | 火山喷发危害（插件已挂钩其激活/停用） |

> 插件侧：`AHazardTrigger::Activate / Deactivate` 已挂钩（`SafeSetHook` 保护），雪崩、滑坡、火山喷发共用同一对入口 ⇒ 事件级无轮询、可精确记录开始/结束（日志 `VOLCANO_EVENT`，含 `cls` 与实际危害类名）。

### 2.2 判定模型（`actor filter=HazardTrigger_Avalanche props=1 propsIdx=0`，实测值）

| 字段 | 实测 | 含义 |
|---|---:|---|
| `ActivationChance` / `CurrentActivationChance` | 0.25 | 进入触发卷时**基础触发概率 25%** |
| `ActivationIncrement` | 0.05 | **每次未触发后概率 +5%**（保底递增，迟早会崩） |
| `MinTimeBetweenActivations` | 180 s | 两次雪崩最小间隔 |
| `MinWarningInterval` / `MaxWarningInterval` | 10 / 15 s | 预警提示间隔窗口（先响警告再崩） |
| `WarningTimer` | 1.51 | 当前预警计时 |
| `Bounds` | 8000 | 触发盒尺寸（uu） |
| `SlideSpeed` | 750 | 雪崩滑体速度（uu/s） |
| `ProjectileTimer` | 2 | 雪崩投射物计时 |
| `SlideFXUpdateInterval` | 0.5 | 滑体特效刷新间隔 |
| `LastActivationTime` | 0 | 本点**从未触发**过 |
| `SlidePositions` / `TriggerBox` / `SlideComponents` / `WarningEmitter` / `SlideFX` / `SlideSound` | `unreadable` | 指针/不透明数组（不猜） |

**⇒ 机制结论（三步）**：玩家进入触发卷 → 按 `CurrentActivationChance`（起始 25%，每次失败 +5%）掷骰 → 命中则先播 10~15 s 预警、再生成滑体（`SlideSpeed 750`）造成雪崩；两次之间至少间隔 180 s。

### 2.3 「只在雪原」的成因 + Rag 对照

- 51 个触发卷**只布置在 Gen 的雪原生物群系**（低温区），其它群系没有触发卷 ⇒ 永远不会发生雪崩。
- **Rag 无雪崩**：`Rag scan filter=Hazard` / `filter=Avalanche` / `filter=Snow` ⇒ **全部 0 命中**。Rag 的低温区只是生物群系温度（`Ice Queen Nest -5.32℃`、`SnowCherub Lake -7.32℃`），**没有任何 hazard 触发器**。
  ⇒ ⚠️ 修正提问中的括注：**"雪崩仅在 Rag 雪山区域"不成立**，实测雪崩触发器 100% 在 **Gen**。

### 2.4 前端可用

- 雪崩是**位置相关**的（进入卷才可能触发）⇒ 服务端只给"事件"：每次 `Activate` 的**发生时刻（世界秒）+ 危害类名**。
- 可稳定获取的静态参数：51 个触发点、25%/次 + 5%/次递增、180 s 冷却、10~15 s 预警、`Bounds 8000`。
- 🆕 **v122b4 已按「Abe 地震」同口径处理**：`actor` 内置白名单新增 `Avalanche`（11 个字段），
  命令 `WorldProbe actor filter=HazardTrigger_Avalanche props=1 propsIdx=0 top=1 slim=1`；
  **前端同样只显示规律文案、不做数据对接**（与地震一致：无法预测 + 位置相关 + 空服不推进）——详见主文档 §15。

---

## 3. Ext 王泰坦：**两条通道**（荒地 WorldBoss 刷怪区 + 禁区竞技场召唤）

> 🆕 **2026-10-06 12:5x 更正**：首版只查了 `BossArenaManager`（竞技场）与 `filter=Titan`，**漏了 `filter=WorldBoss`** —— 实测 Ext **确实存在独立的「世界 BOSS 刷怪区」**，详见 §3.5。

### 3.1 当下世界状态：**只有 2 面形态旗，没有任何 Titan 实例**

1. `Ext scan filter=Titan` ⇒ 全图仅 **`Flag_SM_KingTitan_C` ×1** 与 **`Flag_SM_KingTitanMecha_C` ×1**（两面**场标旗**，代表王泰坦 / 机械王泰坦两种形态），**不存在任何 Titan 角色实例**。
2. `Ext scan filter=King` / `filter=KingTitan` / `filter=Mecha` ⇒ 同样只命中这两面旗。
3. `Ext scan filter=Boss` ⇒ 4 个 `BossArenaManager_*_C` + **1 个 `NPCZoneManagerBlueprint_Land_WorldBoss_C`**（← **荒地刷新通道**，见 §3.5）。

⇒ 当下世界**没有 Titan 角色实例**（两只 BOSS 都不在场）；但**不等于**“没有野生刷新通道” —— 更正见 §3.5。

### 3.2 真实机制：4 组「竞技场管理器 + 贡品终端」

`Ext scan filter=Arena` ⇒ 4 个 `BossArenaManager_*_C`；`scan filter=Terminal` ⇒ 4 个 `TributeTerminal_*_C`，一一对应：

| 竞技场管理器 | 对应 BOSS | 贡品终端 |
|---|---|---|
| `BossArenaManager_Desert_C` | 沙漠泰坦 | `TributeTerminal_Desert_C` |
| `BossArenaManager_Forest_C` | 森林泰坦 | `TributeTerminal_Forest_C` |
| `BossArenaManager_Snow_C` | 冰泰坦 | `TributeTerminal_Snow_C` |
| **`BossArenaManager_FZ_C`** | **王泰坦**（`FZ` = Forbidden Zone 禁区） | `TributeTerminal_FZ_C` |

### 3.3 运行时状态字段（`actor filter=BossArenaManager_FZ props=1 propsIdx=0`，253 属性）

| 字段 | 实测值 | 含义 |
|---|---:|---|
| `bArenaActive` | 0 | 竞技场未激活 |
| `bBossSpawned` | 0 | 无 BOSS 已生成 |
| `BossDespawned` / `BossPhase2` | 0 / 0 | 未进二阶段 |
| `TheBoss` | 0 | BOSS 实例指针（空） |
| **`SummonCooldown`** | **21600 s（6 小时）** | 召唤/重复召唤冷却 |
| `LastArenaActivatedTime` | 0 | **该服从未激活过** |
| `LastBossArenaActiveTime` | 0 | 同上 |
| `TimeToResetWhenNoActivePlayers` | 10 s | 无活跃玩家后重置 |
| `TeleportToHomeTime` | 60 s | 结算后传送回程 |
| `LootContainerSpawnDelay` | 3.5 s | 掉落容器延迟 |
| `ZeroDifficultyBossLevel` / `FourDifficultyBossLevel` | 1 / 100 | 难度等级表 |
| `FiveDifficultyHealthAndDamageAddition` | 3 | 难度 5 的加成 |
| `BossClass` / `BossSpawnPos` / `BossClassDifficultyMap` / `BossTeleporterType` / `TitanInfoVolume` / `LootContainerSpawnPositions` | `unreadable` | 类指针 / 位置数组（不透明） |

- 关联对象：`BP_Obelisk_C_Corrupted_C`（腐蚀方尖碑 ×1）、`BP_Obelisk_A/B/C_C`；`scan filter=Corrupt` ⇒ 腐蚀生物 2,672+ 只（Dilo 931 / Ptero 609 / Raptor 281 / Stego 235 / Rex 224 …），说明该图"野生"的是**腐蚀生物群**，不是泰坦。

### 3.4 前端可用

| 需求 | 命令 | 字段 |
|---|---|---|
| 王泰坦是否在场 | `actor filter=BossArenaManager_FZ props=1` | `bBossSpawned` / `bArenaActive` / `TheBoss != 0` |
| 竞技场是否在战斗中 | 同上 | `BossPhase2`、`TimeToResetWhenNoActivePlayers` |
| 召唤冷却剩余 | 同上 | `SummonCooldown` − (now − `LastArenaActivatedTime`) |

### 3.5 🆕 更正：**确实存在「世界 BOSS 刷怪区」（荒地刷新版）**

> 首版漏查 `filter=WorldBoss`；用户指出后重查，**证据成立**。

**① 关键证据：全图唯一含 `WorldBoss` 的类**

```
Ext WorldProbe scan filter=WorldBoss        -> NPCZoneManagerBlueprint_Land_WorldBoss_C  (1)
Ext WorldProbe scan filter=Zone             -> NPCZoneManager 991 / NPCZoneVolume 1034 /
                                               NPCZoneSpawnVolume 1109 / BiomeZoneVolume 245 /
                                               NPCZoneManagerBlueprint_Land_C 17 / _Water_C 12 /
                                               NPCZoneManager_ToD_C 8 /
                                               >>> NPCZoneManagerBlueprint_Land_WorldBoss_C 1 <<<
```

⇒ 这是独立于竞技场的**野外刷怪区管理器**（与 17 个普通 `_Land_` 区并列，专管世界 BOSS）。

**② 该刷怪区调参（实例实测，330 属性）**

| 字段 | 实测值 | 含义 |
|---|---:|---|
| `bEnabled` | 1 | 刷怪区已启用 |
| **`MinTimeBetweenSpawns`** | **4200 s（70 min）** | 两次生成最小间隔 |
| **`DespawnBossAfterTime`** | **900 s** | BOSS 生成后 900 s 自动消失 |
| `MinDamageToReceiveBossLoot` | 100 | 需造成 ≥100 伤害才能拾取 BOSS 战利品 |
| `MaxDistanceFromBossToReceiveLoot` | -1 | 拾取距离不限 |
| **`TheMinimumPlayerDistanceFromSpawnPoint`** | **6000** | 玩家需在刷怪点 6000 uu 内才触发 |
| `TheMinimumStructureDistanceFromSpawnPoint` | 6000 | 建筑距刷怪点最小距离 |
| `TheMinimumTamedDinoDistanceFromSpawnPoint` | 4000 | 已驯服恐龙距刷怪点最小距离 |
| `CloseStructureDistanceFromSpawnPoint` | 1000 | 过近则关闭 |
| `TheIncreaseNPCInterval` / `TheDecreaseNPCInterval` | 45 / 20 | 刷怪量提升 / 回落间隔 |
| `TheMaximumWorldTimeForFullIncrease` | 120 | 满额提升所需时间 |
| `LastSpawnTime` / `LastIncreaseNPCTime` | 251754156.88 | 上次生成 / 增量时间（本轮实测距当前约 15 h） |
| `LastManuallySpawnedTime` | -100000 | **从未手动生成** |
| `ManualSpawningNPCLerpToMaxRandomBaseLevel` | 0.45 | 手动生成等级插值 |
| `MinimumManualSpawnInterval` | -1 | 手动生成无间隔限制 |

**③ 与通用刷怪区的差别在哪（重要）**

- WorldBoss 实例的 330 个属性与通用 `NPCZoneManagerBlueprint_Land_C` **逐项相同**（142 个非零值完全一致）
  ⇒ “刷的是哪只 BOSS”**不在实例数据里**，而在**蓝图默认值（CDO）与它管辖的 `NPCZoneSpawnVolume`** 里 ⇒ 实例侧**读不出 BOSS 类名**。
- 竞技场侧同样取不到：`BossArenaManager_FZ.BossClass = 0`（payload 探测 `probe=BossClass` 已解出 `structKind:"Class"`，内容为 0）、`BossClassDifficultyMap`/`BossSpawnPos`/`BossTeleporterType` 均 `unreadable`。
- 服务端日志（`Saved\Logs\ShooterGame.log` + `Win32\logs\ArkApi_*.log`）里 Titan/WorldBoss 字样**只有本插件自己的探针日志**，无历史生成记录可查。

**④ 判定与捕捉方案**

- ✅ **结论（修正后）**：Ext 王泰坦存在**两条通道** —— ①**荒地 WorldBoss 刷怪区**（`NPCZoneManagerBlueprint_Land_WorldBoss_C`，70 min 间隔 / 需玩家 6000 uu 内 / 生成后 900 s 消失）；②**禁区竞技场召唤**（`BossArenaManager_FZ_C` + `TributeTerminal_FZ_C`，冷却 21600 s）。当前两条通道都**未在场**（`bBossSpawned=0`、无 Titan 实例）。
- 🔍 **确证“刷的就是王泰坦”的方法**（待捕捉）：轮询 `NPCZoneManagerBlueprint_Land_WorldBoss` 的 `LastSpawnTime`（间隔 4200 s、需玩家在 6000 uu 内），一旦变化**立即** `scan filter=Titan|KingTitan` + `scan top=60` 抓现场类名；或让玩家在荒地蹲守。

---

## 4. 三问一句话总结

| 问题 | 实测答案 |
|---|---|
| **Rag 沙尘暴** | 全局掷骰的 6 种天气之一（**实时概率 7.32%**，每 25~42 min 掷一次）；**效果只在沙尘暴触发卷（沙漠）内生效**（`bInSandstormTrigger` / `SandstormAmount`）⇒ 所以"只在沙漠区域" |
| **Gen 雪崩** | **51 个 `HazardTrigger_Avalanche_C` 触发卷**（只在雪原）：进入即按 **25%/次 + 5% 保底递增**掷骰，命中先预警 10~15 s 再生成 `SlideSpeed 750` 的滑体，间隔 ≥180 s；**Rag 没有任何雪崩/危害触发器**（提问括注有误） |
| **Ext 王泰坦** | **两条通道**：①**荒地世界BOSS刷怪区** = `NPCZoneManagerBlueprint_Land_WorldBoss_C`（全图唯一含 `WorldBoss` 的类，`bEnabled=1`、`MinTimeBetweenSpawns=4200 s`、`DespawnBossAfterTime=900 s`、需玩家在 `6000 uu` 内）；②**禁区竞技场召唤** = `BossArenaManager_FZ_C` + `TributeTerminal_FZ_C`（`SummonCooldown=21600 s`）。当下 0 个 Titan 实例（`bBossSpawned=0`）⇒ 首版“不是野生刷新”说法已更正 |

## 5. 未决 / 不可读项（明确标注，不猜）

- Rag：`WeatherChances`、`CurrentWeather`、`WeatherSeqActors/Players`、`CurrentWeatherStates` 直读 `unreadable` ⇒ 概率只能走 `badwx` 派生；`WeatherPresetList` 的 6 项索引已确认（顺序即 id）。
- Rag `zones` **无数据**（`zones` 仅 Isl / Cen 支持）；Rag `biometemps` 可给 30+ 生物群系温度，但采样中未见名为 "Desert" 的卷（沙漠区域疑为 `unnamed#117 temp=37.68` 一类未命名卷）⇒ 未确证，不作结论。
- Gen/Ext：`SlidePositions`、`TriggerBox`、`BossClass`、`BossSpawnPos`、`BossClassDifficultyMap`、`BossTeleporterType`、`TitanInfoVolume` 均 `unreadable`（指针/不透明数组），故**无法**给出"雪崩点/竞技场坐标列表"。
- 🆕 **Ext 荒地 WorldBoss 刷怪区“刷的是哪只 BOSS”尚无法直读**：其实例属性与普通 `NPCZoneManagerBlueprint_Land_C` 完全一致，刷怪清单在蓝图 CDO / 附属 `NPCZoneSpawnVolume` 里；需靠 `LastSpawnTime` 变动时抓现行类名（方案见 §3.5④）。
- 🆕 **全服对照（10 图 `filter=WorldBoss` 实测）**：**Ext 1 个**、**Ast 1 个**（同类名 `NPCZoneManagerBlueprint_Land_WorldBoss_C`），Isl / Sco / Cen / Abe / Rag / Val / Los / Gen **均 0 命中** ⇒ 世界 BOSS 刷怪区只在 Ext 与 Ast 存在（两者均为 ext_gen 体系图）。
