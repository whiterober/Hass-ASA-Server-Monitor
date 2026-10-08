# 前端事件对接文档（**全服 11 端口**）— Isl / Sco / Cen / Abe / Ext / Ast / Rag / Val / Los / Gen（Bob 未纳管）

> 生成时间：2026-10-05 18:35　｜　**最近更新：2026-10-06 23:35（新增 §26：v122b6 —— 前端反馈 4 缺口修复说明）**
> 数据来源：**本机对全服实服 RCON 的真实响应**（原始 JSON 存于 `tmp\_events_raw\*.json`、`tmp\_v122_raw\*.json`、`tmp\_heat_raw\*.json`）
> 插件版本：**v121**（`TransferIdentityFixAPI.dll` = 1,797,632 B @ 2026-10-05 23:38:38；编译戳 `Oct  5 2026 23:38:11`）
> ✅ **全服 10 服已投放 v122b**（编译戳 `Oct  6 2026 01:22:47`；dll = 1,808,896 B @ 2026-10-06 01:23:19）—— 2026-10-06 01:4x **全量回归实测通过**：`actor slim=1` ✅ / `badwx` ✅ / `weather slim=1` ✅ / `heatWaveActive` ✅ / `meteor` ✅ / `biometemps` ✅ / `zones` ✅；
> 🆕 **全服 10 服已升级 v122b2**（编译戳 `Oct  6 2026 01:50:26`；dll = 1,808,896 B @ 01:50:57）—— 2026-10-06 02:2x 重启后**逐服实测 10/10 通过**：`fields=` 单独用 ✅ / `badwx` 5 服 `factor:null` ✅ / `actor slim` ✅ / `weather slim` ✅ / `heatWaveActive` ✅ / `biometemps` ✅ / `zones` ✅；修复内容：① `fields=` 可**单独使用**（v122b 必须与 `slim=1` 同用）；② 无曲线驱动的图 `badwx.factor` 由误导性最小值改为 `null` + `reason`
> 🆕 **v122b6 已构建（尚未部署）**（dll = 1,831,424 B @ 2026-10-06 23:21:14；md5 `1b6ffda3329fe2fbb1ea841251c71a59`）—— 修复前端反馈的 4 个缺口：① `transitionBegin/End`/`nextWeatherAt` 6 位截断 ② Isl 缺过渡字段（统一改用 `transitionProgress`）③ Gen 五实例缺进度（`wxSystems[].live` / `transitionProgress`）④ `Lerp to New Settings` 未进 HTTP；**附加 `weatherName`**。**部署判据：`weather` 响应头出现 `"schema":"wx-122b6"`**。详见 **§26**
> ⏱️ 生效方式：**覆盖 dll 即生效（AsaApi 5 s 自动重载）**；各服于 2026-10-06 02:04~02:25 陆续重启完成，全服就绪耗时 1,209 s（版本普查 10/10 命中新编译戳）
> 📌 **本文件为唯一真源（单文件，不再分册）**；结构自检：`python TransferIdentityFixAPI\scripts\doc_check.py`
> 修订：撤销 2026-10-05 23:49 的分册结构；**保留**速查表（§10）/ 版本变更日志（§9.0）/ 总览「前端动作」列 / Abe「只显示规律」结论

## 0. 总览（先看这张表）

| 服 | 端口 | 事件 | 读取命令 | 关键字段 | 判据 | **前端动作** |
|---|---:|---|---|---|---|---|
| **Sco** | 32321 | 雷暴 / 沙尘暴 / 热浪 | `WorldProbe weather full=1 limit=1` | `weatherState.currentWeatherId`；`wxSemantics.sandstorm.active`；`electricalStorm.regionNameProbe.asString` | 雷暴 `==7`（秒级）；沙尘暴 `active==true`；热浪 `==4`；区域名须走 `scopeProbe` | ✅ **直接展示**（一条命令含三项 + 世界钟；⚠️ `lightningIntensity` 在 UDS 恒 0，不可用） |
| **Abe** | 32323 | 地震 | ⛔ **无需读取** | — | — | ⛔ **不做数据对接** —— 只显示说明性规律文案，见 §0.1 |
| **Ext** | 32324 | 陨石雨 | ⭐ `WorldProbe meteor`（v117+，一条给全） | `phase` / `inMeteorShower` / `warn` / `volumeTrend` / `volume` / `secondsUntilChange` | `phase ∈ {incoming, active}` ⇒ 进行中（含 40~80 s 预兆）；`leaving`/`none` ⇒ 不弹 | ✅ **直接展示**（按 `phase` 四态驱动；`warn` 单独用会有假预警，见 §3.7.1） |
| **Rag** | 32326 | 火山 | `WorldProbe actor filter=VolcanoManager props=1 propsIdx=0` | `VolcanoActive` / `VolcanoStarting` / `VolcanoEnding` / `WorldVolcanicIntensity` / `TimeNextVolcanoEvent` | `Active=1` ⇒ 喷发中；`Intensity≥0.75` ⇒ 岩浆活跃；`Tnext>0` ⇒ 可算 ETA | ⚙️ **需合成**：`ETA = TimeNextVolcanoEvent − worldClock`（v121 起同响应自洽；v120 用 `weather.worldTime`）；`Tnext=0` ⇒ 显示「空闲期·未排期」 |
| **Gen** | 32329 | 五图天气 + 月球流星雨 | 天气：`WorldProbe weather full=1 limit=6 actors=1`；流星雨：`WorldProbe actor filter=LunarMeteorController props=1 propsIdx=0 top=1` | 天气：`wxSystems[].miniMapType` / `currentWeather` / `secondsUntilChange`；流星雨：`TimeLastEvent` / `ActualTimeBetweenEvents` / `Min·MaxTimeBetweenEvents` / `DurationOfEvent` | 按 **`miniMapType`** 匹配（`null` = 月球；⚠️ **勿写死下标**）；`secondsUntilChange=1000` 且 `beginAt<0` ⇒ 该图**未运行**；流星雨 `ETA = Last + Actual − worldClock` | ⚙️ **混合**：五图倒计时**直接展示**；流星雨 ETA 需合成（**有玩家时 2026-10-06 已实测有效**；空服不推进） |

### 0.1 ⛔ Abe 地震：**前端只显示规律，不做数据对接**（2026-10-05 用户确认）

| 项 | 结论 |
|---|---|
| 能否预测（倒计时 / 概率） | ❌ **不能** —— 该 actor **208 个属性全量双筛**，无 `Next*` / `*Interval*` / `*Chance*` / `*Probab*` / `*Weight*` 任何计时或概率字段 |
| `bEarthQuake` 能干什么 | 只表示"**此刻是否正在地震**"；空服/无玩家时事件也不推进 ⇒ 参考价值低 |
| 有独立调度器吗 | ❌ Abe 上 `Event` / `Hazard` / `Disaster` 扫描 **0 命中**（推断由 GameMode / 蓝图序列触发） |
| **前端怎么做** | ✅ **只显示说明性规律文案，不轮询、不接任何字段** |
| 建议文案（可直接用） | 「**地震为随机事件，服务器不定期发生；发生时屏幕剧烈抖动，洞穴内可能落石，请注意躲避。**」 |
| 备选简版 | 「地震：随机发生，无法预测」 |

- 🔴 因此 `bEarthQuake` **不建议上屏**，仅作**运维/调试**用途。细节见 [`前端对接_Abe.md`](前端对接_Abe.md) §2.5。
- 🔜 "事件到达即通知"属 **v122 backlog**，当前不做。

### 0.2 通用约定

- host `work.whiterober.cn`，命令前缀 `TransferIdentityFix.`，**每条命令必须用独立进程/连接**（同进程连发 RCON 必死锁）。
- **世界钟**（唯一推荐口径）：取 **`weather` 响应里的 `worldTime`**（永远秒级）。
  v121 起任意分支的 `worldTime` 都是秒级且带 `worldTimeSource`；v120 及更早只有 `weather`/`zones`/`biometemps` 可靠。详见 [`通用字段口径 §4.5.3`](前端对接_通用字段口径.md)。
- 性能：`actor`/`weather` 全量扫描约 **1.2~1.5 s**；建议轮询间隔 ≥ 60 s（占用 < 2%）。
- **v122 起可加 `slim=1` 瘦身**（去掉 `dump[]`/`fields[]` 等布局调试块 + `actor` 只回白名单字段）⇒ 体积降约 95%，**默认关闭**。见 §9.5。
- 📄 **全服天气概率与「能不能预测」总表**：见独立文档 `天气事件与概率总表_20261006.md`（10 服全覆盖 + 可预测性总表）。

## 1. Sco（32321）—— 雷暴 / 天气

### 1.1 命令

```
TransferIdentityFix.WorldProbe weather full=1 limit=1
TransferIdentityFix.WorldProbe actor filter=UDS_SE_Weather props=1 propsIdx=0
```

（`actor` 子命令**只解析 4 个 token**：`filter=` / `props=1` / `propsIdx=N` / `probe=`；`+` 代表空格，单次 `probe` 上限 **12** 个名字；
不带空格的属性名可直接写，如 `probe=SandstormSweepSequenceNS`）

- ✅ **雷暴 / 沙尘暴 / 热浪的判据全部在 `weather full=1` 的响应里**（`weatherState` + `wxSemantics`）⇒ **一条命令就够**；
  `probe=` 只用于**探索**（读 `scopeProbe` 里的区域名 / FString 槽）。
- 🚫 **不要写 `probe=Current+Lightning+Intensity`**（§1.1 旧示例）：该属性在 Sco（UDS 家族）上**不存在**，只会拿到 `null`（见 §1.10）。
- 🔴 **区域名读法**：`wxSemantics.electricalStorm.regionNameProbe.asString` —— **必须走 `scopeProbe`**，
  顶层 `probe=ElectricalStormRegionName` 读不出（返回 `null` + `type:"unreadable"`）。

### 1.2 Sco 天气 id → 名称（实测 `wxSemantics.arrayProbe.presetTable`，2026-10-05）

| 天气 id | 预设名 |
|---:|---|
| 0 | `Clear_Skies_SE` |
| 2 | `Rain_SE` |
| 3 | `Foggy_SE` |
| 4 | `HeatWave_SE`（热浪） |
| 5 | `ColdFront_SE` |
| 6 | `Sand_Dust_Storm` |
| **7** | **`ElectricalStorm`** ← 雷暴 |
| 8 | `Superheat`（焚风） |

- 🔴 **`i`（数组下标）≠ `id`**：`presetTable[]` 是按 `i` 顺序存的，必须用 `id` 字段做映射（例：`i=1` 的 `id=7`）
- id **1** 未出现在表内（表内 8 条 / 枚举 0..8 共 9 值）⇒ id 1 名称未知，前端遇到请显示 `id=1 (未知)`

### 1.3 前端关心的 JSON 键（`weatherState`）

| JSON 键 | 来源属性 | 含义 |
|---|---|---|
| `currentWeatherId` / `nextWeatherId` / `prevWeatherId` | `CloudNewWeather` / `NextWeather` / `CloudPreviousWeather` | 天气枚举 id（**不是**数组下标） |
| ⚠️ `lightningIntensity` | `Current Lightning Intensity` | ❌ **UDS（Sco）上不存在该属性**（`probe` 返回 null、`fields[]` 里也没有）⇒ **不可用作雷暴判据**，见 §1.10 |
| ⚠️ `lightningMaxIntensity` | `Maximum Lightning Flash Light Intensity` | ❌ 同上（属 Abe / 其它家族字段，Sco 端**不要依赖**） |
| `transitionLength` / `inTransition` / `transitionElapsed` | `WeatherTransitionLength`(=120) / `bInWeatherTransition` / `WeatherTransitionTimeElapsed` | 天气切换进度 |
| `windStrength` / `fogStrength` / `rainStrength` / `rainVolume` / `windVolume` / `windDirection` | `Wind Intensity`/`BlowingFogMPC`/`Rain`/`Rain Volume`/`Wind Volume`/`Wind Direction` | 环境强度 |
| `baseSummerTemperature` 等 | `Base Summer/Autumn/Winter Temperature` | 季节温度 |

### 1.4 雷暴专门字段（`wxSemantics.electricalStorm`，2026-10-05 18:34 实测）

| 键 | 槽大小 | 实测（无雷暴时） | 说明 |
|---|---:|---|---|
| `electricalStorm.region` | 4 B int32 | `0` | **0 = 无雷暴区域**；非 0 ⇒ 雷暴生效 |
| `electricalStorm.debug` | 1 B | `false` | `bDebugElectricalStorm` |
| `electricalStorm.regionNameProbe` | 16 B | 雷暴中 `asString="Center"` | **区域名字符串槽**（FString，`num`=字符数含结尾 0）；无雷暴时全 0 |
| `electricalStorm.scopeProbe."Current Lightning Location"` | 24 B | 全 0（`asVec3=[0,0,0]`） | **当前闪电落点（FVector）** |
| `electricalStorm.scopeProbe."Custom Lightning Location"` | 24 B | 全 0 | 自定义闪电位置 |
| `electricalStorm.scopeProbe."Custom Lightning Target"` | 24 B | 全 0 | 自定义闪电目标 |
| `electricalStorm.scopeProbe."Current Lightning Target Offset"` | 24 B | 全 0 | 落点偏移 |
| `electricalStorm.scopeProbe.PendingLightningFlashesLoc` | 16 B | 全 0（TArray 头） | **待闪电队列**（num>0 ⇒ 有闪电活动中） |
| `electricalStorm.scopeProbe."DLWE Relevant Projection Boxes"` | 16 B | 全 0（TArray 头） | 相关投影框 |

**雷暴判据（🔴 2026-10-05 21:2x 修正版）**：
`weatherState.currentWeatherId == 7`（**秒级生效，首选**）**或** `electricalStorm.region != 0`（滞后约 9 分钟，仅作补充）

> ❌ 旧判据已废：`scopeProbe."Current Lightning Location"` 与 `PendingLightningFlashesLoc.num` 经雷暴期间实测**恒为 0**
> （UDS 不写这些原版字段），不能用作判据。详见 §1.10。

### 1.5 Sco 的第二个事件：沙尘暴（`wxSemantics.sandstorm`）

> 🔴 **2026-10-07 01:0x 勘误（实服抓到真实沙尘暴后修订）**：本节所述的 `dust` / `Material Dust Coverage` / `sweepSequence` / `active` 判据在 Sco 上**恒为 0，即使沙墙清晰可见**（该图无 DLWE 系统）。**请改用 §27 的判据**（天气 id=6 / `weatherName="Sandstorm"`）。

> ✅ **完整字段表 / 判据 / `scopeProbe` 读法坑已统一到 §1.12**（本小节只留索引，避免两处维护）。
> 一句话：同一条 `weather full=1` 命令里读 `wxSemantics.sandstorm.active`（`true` ⇒ 沙尘暴进行中），
> 持续 `durationSec = 480 s`，起止时间与 `weather.worldTime` 同轴，可算进度/剩余。

### 1.6 🔴 两个实测坑（务必记住）

1. **`scan` 找不到"风暴"**：`scan filter=Storm` → **0 命中**、`scan filter=Electrical` → **0 命中**；
   图上与天气相关的 Actor 只有 `UDS_SE_Weather_C`（1 个）。⇒ **雷暴/沙尘暴不是独立 Actor**，
   必须读天气 Actor 的字段，不要试图 `scan` 找风暴实体。
   （对比：`scan filter=Lightning` 命中 4 个 `Wyvern_Character_BP_Lightning_C` —— 那是闪电飞龙生物，跟雷暴无关）
2. **Sco 的插件版本偏旧**：本轮 `probe=Current+Lightning+Intensity` 返回 `null`，且响应键名里
   **`+` 未被还原成空格**（`probes.Current+Lightning+Intensity`）⇒ Sco 上的 dll **早于 v103**（`+` 代空格是 v103 才修）。
   - 影响：Sco 上**无法用 `probe=` 读带空格的属性名**（如 `ElectricalStormRegionName` 可以，因为它无空格）
   - 处置建议：把最新 dll（v106/v107）也投放到 Sco，即可获得 `presetTableSource` 等新键与 `+` 支持
   - 另注：`UDS_SE_Weather_C` 上**不存在** `Current Lightning Intensity` / `Maximum Lightning Flash Light Intensity`
     属性（`probe` 返回 `null`、`fields[]` 中也没有）⇒ 这两个名字属 Abe/其它家族，Sco 端**不要依赖**
   - 🆕 **更正（2026-10-05 19:30）**：Sco 本轮已升到 **v111**（`+` 代空格 = v103+、`presetTable` = v106+、`structFields` = v108+），
     上述「版本偏旧」的**现象不再适用**；Sco 的带空格 `probe=` 与 `presetTableSource` **待前端实测确认**。

### 1.7 展示建议
`天气名（id 查表）` + `雷暴：进行中/无`（见 §1.4 判据）+ `沙尘暴：进行中/无`（`sandstorm.active`，可加进度 `sandstorm.progress`，
见 §1.12）+ `热浪：进行中/无`（`currentWeatherId == 4`，见 §1.13）
+ 距离下次变天秒数（`nextWeatherAt - worldTime`，Sco 用 `WeatherChangeTimerMin/Max` 与 `TimerNextWeather`）。

### 1.8 雷暴观测记录（2026-10-05 18:39~19:28，44 轮 / 48 分钟）

| 项 | 结果 |
|---|---|
| 采样 | 每 60 s 一次 `WorldProbe weather full=1 limit=1`，读 `electricalStorm` / `sandstorm` |
| `electricalStorm.region` | **全程 0**（44/44 轮） |
| `scopeProbe."Current Lightning Location"` | 全程 `[0,0,0]` |
| `scopeProbe.PendingLightningFlashesLoc` | 全程全 0（TArray 头 num=0） |
| `sandstorm.active` / `progress` | 全程 `false` / `0.0` |

- 结论：窗口内 **Sco 未进入雷暴、也未进入沙尘暴**；判据链（§1.4）已就绪，缺的是事件本身 —— 属低概率天气事件，48 分钟未命中属正常。
- 窗口内 4 段 RCON 超时（18:44–18:56 / 19:02–19:03 / 19:10–19:12 / 19:18–19:20）**对应插件 dll 热替换重启**，非服务故障；
  前端轮询遇同类超时可按「服务器重启中」处理（退避重试即可）。

### 1.9 🟢 天气可强制切换（v112+ 函数调用，2026-10-05 21:25 用户目视确认）

```
TransferIdentityFix.WorldProbe callfunc fn=MC_ChangeWeather p.New+Weather+Type=7 p.Transition+Length=30 p.Reset+Particle+Emitters=1 apply=1
```

| 参数 | 类型 | 说明 |
|---|---|---|
| `New Weather Type` | int8 | 天气 id（见 §1.2） |
| `Transition Length` | double | 过渡秒数（实测引擎会改写为 60，属正常） |
| `Reset Particle Emitters` | int8 | 1 = 清掉上一天气的残留粒子（**v116 起才支持第 3 个参数**；v115 只能传 2 个） |

- `apply=1` 才真正执行；省略 = 预演（dry-run，只回参数表与目标地址）
- **目视确认结果**：`7` = 雷暴（天空闪电/电离效果）、`2` = 雨（雨丝 + 地面湿）、`0` = 停止（闪电电离消失）
- 🔴 只写字段（`wxset`）**基本无效**：7 个槽位实测仅 `CloudNewWeather` 能间接影响 `currentWeatherId`（属"半有效"）
  ⇒ **强制切天气必须走 `callfunc`**，不要指望字段写入。

**id → 视觉对照（目视确认）**：`0` 晴 · `2` 雨 · `7` 雷暴；`1/3/4/5/6/8` 尚未做目视标定。

### 1.10 判据有效性重估（2026-10-05 21:26，**雷暴进行中**实测）

| 字段 | 可用性 | 实测证据 |
|---|---|---|
| `weatherState.currentWeatherId` | ✅ **秒级** | 发 `callfunc(7)` 后 3 秒内即 `7.0` |
| `electricalStorm.region` | ⚠️ **滞后约 9 分钟** | 20:58 切雷暴 → 21:08 才变 `3` |
| `electricalStorm.regionNameProbe.asString` | ✅ **可读（本次新解出）** | 雷暴中 = `"Center"`（FString：`num`=7 / `max`=8） |
| `scopeProbe."Current Lightning Location"` | ❌ 恒 0 | 雷暴中 10 次采样全 0，且数 30 秒前后逐字节相同 |
| `scopeProbe.PendingLightningFlashesLoc` | ❌ 恒 0 | 同上 |
| `PendingLightningFlashes*` / `Current Lightning Intensity` / `Lightning Flash Timer` / `Clouds Flashing` | ❌ 恒 0 | UDS **不写**这些原版字段 |
| `ElectricalStormRegionName`（用 `props` 读） | ❌ 读不出 | 返回 `null` + `"type":"unreadable"` —— FString 必须走 `scopeProbe` 版本 |

🔴 **读法坑**：`region` 必须按 **int32** 读；按 float 读会得到 `4.2039e-45`（= int `3` 的浮点读法）。

### 1.11 范围边界结论（2026-10-05 21:26，雷暴进行中实测）

- **UDS 雷暴没有"几何边界"数据**：`All Weather Mask Brushes` / `All Weather Mask Projection Boxes` /
  `DLWE Relevant Projection Boxes` / `DLWE Relevant Weather Mask Brushes` / `DLWE_Brush_Locations_Buffer` /
  `Mask Buffer Target` / `DLWE_RenderTarget_Center` 在**雷暴中全为 0**，且 10 次采样（≈30 秒）**逐字节完全一致**
  ⇒ 不是"没抓到"，而是 mod **不使用**这些字段。
- **"哪个区"能说清楚**（双口径）：`electricalStorm.region`（数字，滞后）+ `regionNameProbe.asString`（名字，直读）。
  实测雷暴中读到区域名 `"Center"`，与用户当时站位（地图 50/50 中心区）**强吻合** ✅
- **前端建议**：报「**区域名**」而非「区域数字」—— 数字是内部枚举且会滞后，名字可直接上屏，如「雷暴区域：Center」。
- ✅ **验收口径（2026-10-05 用户确认）**：「范围名字能读即可」—— 几何边界**不追了**；
  旧天气残留粒子效果**已由目视确认消失**，v116 的第 3 参数（`Reset Particle Emitters`）仅作备选，**不再列入待办**。

---


### 1.12 🌪️ 沙尘暴 —— 现状与判据（2026-10-05 23:30 实测，v120b）

> 🔴 **2026-10-07 01:0x 勘误**：本节所列 `active` 判据（基于 dust 字段）**已证伪**，Sco 全程 0。见 **§27**。

**一句话判据**：`wxSemantics.sandstorm.active == true` ⇒ 沙尘暴进行中（同一条 `weather` 命令即可拿到，无需额外请求）。

**现状（实测，无沙尘暴时）**：`active=false` / `progress=0.0` / `startTime=finishTime=0` / `frame=frameLast=0`

| 键 | 实测 | 说明 |
|---|---|---|
| **`sandstorm.active`** | `false` | **事件开关（唯一判据）** |
| `sandstorm.enabled` | `true` | 该图是否启用该事件（Sco = 启用） |
| `sandstorm.durationSec` | `480` | 单次持续 **480 s** |
| `sandstorm.startTime` / `finishTime` | `0` / `0` | 起止世界时间（**与 `weather.worldTime` 同轴**）⇒ 可算进度/剩余 |
| `sandstorm.progress` | `0.0` | 0~1 进度（进行中才有意义） |
| `sandstorm.frame` / `frameLast` / `frameInterval` | `0 / 0 / 1` | 扫掠帧号 / 上一帧 / 帧间隔（沙墙逐帧推进） |
| `sandstorm.direction` | `"north-south"` | 扫掠方向（**字符串，可直接上屏**） |
| `sandstorm.westEast` / `backwards` | `false` / `false` | 方向布尔（与 `direction` 一致） |

- 🔴 **读法坑（必须走 `scopeProbe`）**：`SandstormSweepSequence*` / `CurrentSandstormSweepSequence` **不能**用顶层
  `probe=` 读（返回 `size=null`）；它们在 **`wxSemantics.electricalStorm.scopeProbe`** 里：

| 槽（`scopeProbe.*`） | size | 实测 |
|---|---:|---|
| `SandstormSweepSequenceNS` | 16 | TArray 头：**`num=225` / `max=234`** ⇒ 南北路线 225 个采样点 |
| `SandstormSweepSequenceWE` | 16 | TArray 头：**`num=225` / `max=234`** ⇒ 东西路线同 |
| `CurrentSandstormSweepSequence` | 16 | 全 0（未进行时无当前序列） |
| `SweepFrontierCurve` | 8 | 对象 `CurveLinearColor` / **`C_SE_SandStormSweep_Frontier`**（沙墙前沿曲线） |
| `SandstormSweepDirectionCurve` | 8 | 对象 `CurveLinearColor`（方向曲线） |

- ✅ **沙尘暴不是独立 Actor**：`scan filter=Sand` / `Dust` / `Storm` ⇒ **0 命中**；全世界只有 **1 个 `UDS_SE_Weather_C`**（400 个属性）。
- **展示建议**：`沙尘暴：进行中（进度 xx%）` + `方向：north-south`；（直接用上方 `direction` 字符串上屏即可）。

### 1.13 🔥 热浪（`HeatWave_SE`，id=4）／焚风（`Superheat`，id=8）—— 现状与判据（2026-10-05 23:31 受控实测）

- 🟥 **术语更正（2026-10-07）**：**热浪 = `HeatWave_SE`（id 4）**、**焚风 = `Superheat`（id 8）**，
  二者是**两个不同天气**；本节受控实测的对象是**热浪（id 4）**，焚风机制相同、判据同为 `weatherState.currentWeatherId`，
  强制命令把 `Type=4` 换成 `Type=8` 即可。译名口径与前端一致（`HeatWave`=热浪 / `Superheat`=焚风，前端 v4364 已改）。
- 🔴 **热浪没有专门语义槽**：`wxSemantics` 里只有 **`electricalStorm` / `sandstorm`** 两个事件槽，
  **不存在** `heatWave` / `foehn` / `superheat` 键；`scan filter=Heat` / `Heatwave` / `Foehn` / `Superheat` ⇒ **全部 0 命中**
  ⇒ **既不是独立 Actor，也没有专属状态字段**。
- ✅ **唯一判据 = `weatherState.currentWeatherId == 4`**（`HeatWave_SE`＝热浪；**焚风则为 `== 8`**，见 §1.2 表）；**秒级生效**
  （受控测试中发出 `callfunc` 后首次采样即为 `4.0`）。
- **受控测试**（空服，`MC_ChangeWeather(4)` → 约 60 s → 复位 `0`；命令见 §1.9）：

```
TransferIdentityFix.WorldProbe callfunc fn=MC_ChangeWeather p.New+Weather+Type=4 p.Transition+Length=30 p.Reset+Particle+Emitters=1 apply=1
```

- ✅ **`callfunc` 回包自带 `verify[]` 自检块**（可直接用于确认切换是否生效）：
  `CurrWeatherType before 0 → after 4`；另 `candidates` 唯一 ⇒ `MC_ChangeWeather` 的 **`fnIdx=18`**
  （`flags=3a18f040` / `numParms=0` / `parmsSize=1`；参数表：`New Weather Type`@0 int8、`Transition Length`@8 double、`Reset Particle Emitters`@16 int8）
  ⚠️ **`verify[]` 只对 UDS 家族（Sco 等）有效**；**Ext 的 `verify[]` 实测全为 `null`**（见 §3.7.2）

| 采样点 | `currentWeatherId` | `windStrength` | `windDirection` | `interiorTemperature` | `sandstorm.active` |
|---|---:|---:|---:|---:|---|
| 基线（切换前） | `0.0` | `3.0` | `90.0` | `22.2` | `false` |
| HW1 | `4.0` | `3.0` | `90.0` | `22.2` | `false` |
| HW2 | `4.0` | `3.0` | `90.0` | `22.2` | `false` |
| HW3 | `4.0` | `3.0` | `90.0` | `22.2` | `false` |
| HW4 | `4.0` | `3.0` | `90.0` | `22.2` | `false` |
| HW5 | `4.0` | `3.0` | `90.0` | `22.2` | `false` |
| HW6 | `4.0` | `3.0` | `90.0` | `22.2` | `false` |
| 复位后 | `0.0` | `3.0` | `90.0` | `22.2` | `false` |

- ⇒ **结论：热浪期间 `windStrength` / `windDirection` / `interiorTemperature` 读数与晴天完全一致（不变）**
  ⇒ 前端**只能靠 `currentWeatherId` 判定**（热浪 `4` / 焚风 `8`）；热浪与焚风的风、热效果均由**客户端表现层**驱动，**服务端无字段可读**。
- **背景可读量**（仅供参考，不是判据）：`baseSummerTemperature=23` / `baseAutumnTemperature=21` / `baseWinterTemperature=11`、
  `maxValidTemperature=60` / `minValidTemperature=-30`、`HotTemperatureFactor=55`、`ColdTemperatureFactor=-56`。
- **概率参考**（见「🎯 Sco（UDS_SE_Weather）日/夜权重表」）：白天 **31.8%**（8 种天气中最高）/ 夜晚 **0%**
  ⇒ **热浪只可能在白天出现**；结合 §1.9 可用 `callfunc` 强制验证。
- **展示建议**：`热浪：进行中/无`（`currentWeatherId == 4`）；不要试图用风速/温度变化做判据（实测无变化）。

## 2. Abe（32323）—— 地震

### 2.1 命令

```
TransferIdentityFix.WorldProbe actor filter=Earthquake props=1 propsIdx=0 top=1
```

实测命中：`BP_AB_EarthquakeSystem_C_UAID_C87F54AA07514BFF01_1480239655`（全图 **1** 个）

### 2.2 事件字段（全量 actorProps，实测 18:31）

| 属性 | 实测值 | 说明 |
|---|---:|---|
| **`bEarthQuake`** | `0` | **唯一事件开关**（0/1） |
| `NS_DirtFall_Quake_CPU_A` / `_B` / `NS_DirtFall_quake_A` / `_B` | `0` | 尘土下落特效开关 |
| `Timeline_Shake_*`（2 个） | `0` | 屏幕/相机抖动时间线 |
| `Ceiling Height` | — | 洞顶高度（与该事件无关，勿混用） |

### 2.3 Abe 天气（非事件，供背景展示）

- `weather full=1` → `semSource = "BP_AB_WeatherAgent_C"`，`weatherState.family = "ab"`，4 个 `wxSystems[]`
- ⚠️ **Abe 的 `currentWeather` 目前为 `null`**（该家族未接名称解码；只有 id 可读）
- `wxSemantics.electricalStorm = null`（雷暴是 Sco 专属，Abe 无此字段）

### 2.4 展示建议
`地震：进行中/平静`（`bEarthQuake`），可附尘土特效开关数与抖动时间线数量作为强度暗示。

---

#### 🌎 Abe 地震：**当前不可预测（缺计时/概率字段）**（2026-10-05 23:24 实测）

**对象**：`BP_AB_EarthquakeSystem_C`（`scan filter=Earthquake` → `distinct=1`，全世界仅 1 个；`filter=Quake` / `Hazard` = 0）

| 字段 | 实测 | 说明 |
|---|---:|---|
| `bEarthQuake` | `0` | **地震进行中标志**（当前无地震） |
| `UnstasisLastInRangeTime` | `260720201.53` | 解除静止时间（非事件排期） |
| `Timeline` / `Timeline_0` | `null` | 时间轴组件（未实例化/空） |
| `Timeline_0_Shake_*` / `Timeline_Shake_*` | `0` | 相机抖动曲线引用（全 0） |
| `NS_DirtFall_Quake_*` | `0` | 落尘 Niagara 系统引用（全 0） |

- ⇒ **该 actor 上没有任何"下次时间 / 间隔 / 概率 / 权重"字段**（`Min*` / `Max*` / `Chance` / `Next*Quake` 全部不存在）；
- ⇒ **现状：只能读"此刻是否正在地震"（`bEarthQuake`），无法给出倒计时或概率**。
- 🔎 **推断**：地震是由 **AShooterGameMode / 天气系统的 hazard 调度**或**蓝图序列**触发（非本 actor 自排期）；
  插件已挂 `AHazardTrigger.Activate/Deactivate` 钩子（`HOOK_OK` 可见），可作为后续"事件到达即通知"的抓手。
- 🔍 **本次全量双筛证据**（该 actor 共 **208** 个属性）：非零项仅 `ClientReplicationSendNowThreshold=2`、
  `UnstasisLastInRangeTime=260720201.53` 与一批 bitfield（`bAutoStasis=132` / `bStasised=64` …）；
  扩大扫描 `EarthquakeSystem` / `AB_Earth` ⇒ 均只命中 **1** 个；`Event` / `Hazard` / `Disaster` ⇒ **0**
  ⇒ **Abe 上不存在独立的地震调度器 actor**，进一步支持上述推断。
- 🔜 **v122 候选**（v121 已用于修正 `worldTime` 精度，见 §9）：① 抓 `bEarthQuake 0→1` 翻转的**实时通知**（不需要预测，事件到达即报）；
  ② 用 `AHazardTrigger` 钩子记录历史时刻 ⇒ 多次采样后**统计间隔分布**（经验概率）；
  ③ 若需"提前预警"，需在蓝图侧找到 hazard 调度器（属官方蓝图范畴，**不建议改**）。

### 2.5 ⛔ **前端接入建议（2026-10-05 用户确认）：只显示规律，不做数据对接**

| 项 | 结论 |
|---|---|
| 能否**预测**（倒计时 / 概率） | ❌ **不能** —— 该 actor 共 **208** 个属性全量双筛，**无** `Next*` / `*Interval*` / `*Chance*` / `*Probab*` / `*Weight*` 任何计时或概率字段 |
| `bEarthQuake` 能做什么 | 只表示"**此刻是否正在地震**"（0/1），**不能**推出下一次；且空服/无玩家时事件本身也不推进 ⇒ 参考价值低 |
| 是否存在独立调度器 | ❌ Abe 上 `Event` / `Hazard` / `Disaster` 扫描 **0 命中**；推断由 GameMode / 蓝图序列触发 |
| **前端怎么做** | ✅ **只显示说明性规律文案，不接任何数据字段**（不轮询、不展示"地震中/平静"、不展示强度） |
| 建议文案（可直接用） | 「**地震为随机事件，服务器不定期发生；发生时屏幕剧烈抖动，洞穴内可能落石，请注意躲避。**」 |
| 备选文案（更简） | 「地震：随机发生，无法预测」 |

- 🔴 因此 §2.2 的 `bEarthQuake` **不建议上屏**，仅可作为**运维/调试**用途（例如排查异常时人工查看）。
- 🔜 若将来仍要"事件到达即通知"，属 **v122 backlog**（抓 `bEarthQuake 0↔1` 翻转或 `AHazardTrigger` 钩子），**当前不做**。
- 🆕 **同口径适用：Gen 雪崩**（`HazardTrigger_Avalanche_C`，Gen 全图 **51** 个触发卷）—— **同样只显示规律文案、不做数据对接**；插件层已按地震同一作法加入 `actor` 内置白名单（v122b4），细节见 **§15**。

#### 2.5.1 🔬 地震机制详解（2026-10-06 v122b4 实测补充）

**对象**：`BP_AB_EarthquakeSystem_C`（`scan filter=Earthquake`，全图 **1** 个，**常驻 actor**；本轮全量 **208 属性，不可读 0 项**）

| 层 | 实测字段 | 当前值 | 说明 |
|---|---|---|---|
| 状态开关 | `bEarthQuake` | 0 | **唯一对外状态**（0 = 平静 / 1 = 地震中） |
| 表现·相机 | `Timeline` · `Timeline_0` · `Timeline_0_Shake_1C76B8…` · `Timeline_0__Direction_1C76B8…` · `Timeline_Shake_9C4E2F…` · `Timeline__Direction_9C4E2F…` | 0 | **蓝图 Timeline 驱动**：两条时间线各带 **Shake（抖动）+ Direction（方向）** 轨 ⇒ 地震 = **有方向的剧烈相机抖动** |
| 表现·落石尘土 | `NS_DirtFall_Quake_CPU_A` · `NS_DirtFall_Quake_CPU_B` · `NS_DirtFall_quake_A` · `NS_DirtFall_quake_B` | 0 | **4 个 Niagara 落石/尘土特效**（正对应"洞穴内落石"） |
| 表现·音效 | `LastPostProcessVolumeSound` | 0 | 后处理 / 音效计时 |
| 常驻性 | `UnstasisLastInRangeTime` | 260729369.28 | 最近一次离开隐状态时间（证明是**常驻 actor**，非临时生成） |
| **计时/概率** | 全量双筛 `Next*` / `*Interval*` / `*Chance*` / `*Probab*` / `*Weight*` | — | ❌ **一个都没有**（208 属性再次确认 ⇒ 不可预测） |

**可见征兆（据此写前端文案）**：

1. **有方向的剧烈相机抖动**（`Timeline_*_Shake*` + `Timeline_*__Direction*`）
2. **落石与尘土特效**（4 个 `NS_DirtFall_*`）—— 洞穴 / 洞顶最明显
3. 配套后处理与音效（`LastPostProcessVolumeSound`）

**触发来源**：**不在本 actor 内** ⇒ 由 `AShooterGameMode` / 蓝图层 hazard 序列触发（**推断**，非实测；Abe 上不存在独立调度器 actor）。

## 3. Ext（32324）—— 陨石雨（**本次新解出的映射表**）

### 3.1 命令

```
TransferIdentityFix.WorldProbe weather full=1 limit=1
TransferIdentityFix.WorldProbe actor filter=WeatherSystem props=1 propsIdx=0
```

### 3.2 天气 id → 名称（v106 由插件直接输出，2026-10-05 验收 PASS）

| 天气 id | 预设名 |
|---:|---|
| 1 | `WeatherPreset_EXT_Cloudy` |
| 2 | `WeatherPreset_EXT_Overcast` |
| 3 | `WeatherPreset_EXT_Spooky` |
| 5 | `WeatherPreset_EXT_ClearSky` |
| **6** | **`WeatherPreset_EXT_MeteorRain`** ← 陨石雨 |

（表内 5 条；id **0**（Base 默认天气）与 **4** 不在表内）

### 3.3 前端直接用（v106 新键）

| JSON 键 | 示例值 | 说明 |
|---|---|---|
| `wxSemantics.presetTableSource` | `"WeatherPresetList"` | **v106 判别串**（有它 = 插件已带映射） |
| `wxSemantics.presetTable.num/max/elementSize` | `5 / 5 / 24` | 表规模（元素 24 字节） |
| `wxSemantics.presetTable.entries[i].{id,hashIndex,name}` | `{"id":6,"hashIndex":6,"name":"WeatherPreset_EXT_MeteorRain"}` | 完整映射；`hashIndex` 供自检（= `id % 31`） |
| `wxSemantics.extWeather.currentId / currentName` | `1 / "WeatherPreset_EXT_Cloudy"` | **当前天气**（名称直接可用） |
| `wxSemantics.extWeather.nextId / nextName` | `1 / "WeatherPreset_EXT_Cloudy"` | 下一个天气 |
| `wxSemantics.extWeather.prevId / prevName` | `1 / "WeatherPreset_EXT_Cloudy"` | 上一个天气 |

### 3.4 陨石事件开关（`actor filter=WeatherSystem` 的全属性）

| 属性 | 语义 |
|---|---|
| **`bMeteorFXActive`** | 陨石特效激活（0/1）—— 最直接的事件开关 |
| `MeteorVolume` / `FinalMeteorVolume` | 陨石音量（当前 / 最终） |
| `MeteorMPC` | 陨石材质参数集 |
| `GlobalMeteorRainSound` | 全局陨石雨音效开关 |
| `MeteorRain` | **指向生成器实例** `BP_Meteor_Spawner_C_UAID_50EBF67F7F17A82F02_1940668705`（常驻，不等于事件正在发生） |

> 🔴 **关键判读**：Ext 陨石是**天气预设 + 常驻生成器**，**不是** Hazard。判定"正在陨石"应看
> `extWeather.*Name == WeatherPreset_EXT_MeteorRain`（id 6）**或** `bMeteorFXActive=1`；
> **不要**用 `MeteorRain` 槽非空来判（它一直在）。

### 3.5 展示建议
`当前天气：Cloudy` + `陨石雨：进行中/无` + `距离变天 xx 秒`（`weatherState.nextWeatherAt - worldTime`）。

### 3.6 `CurrentWeatherStates`（240 字节 = 蓝图结构体 `S_EXT_WeatherState`，**30 个字段已全部解出**）

命令：`actor filter=EXT_WeatherSystem props=1 propsIdx=0 probe=CurrentWeatherStates`

> ⚠️ 需 **v107+** 才会返回完整 240 字节（v106 及更早 hex 只给 64 字节 + `"truncated":1`）
> 判别：`hex` 长度 480 字符（240 字节）= v107；128 字符（64 字节）+ `truncated` = 旧版

实测逐偏移（2026-10-05 18:37）：

| 偏移 | 内容 | 偏移 | 内容 |
|---|---|---|---|
| +0 / +8 / +16 | 3 个对象指针 `P1 P2 P3` | +24 / +32 / +40 | **同 3 个指针再现** |
| +48 / +56 / +64 | `6.0 / 2.0 / 4.0`（double） | +72 / +80 / +88 | **`6.0 / 2.0 / 4.0` 再现** |
| +96 / +104 / +112 | `Q1 Q1 Q2`（指针，成对） | +120 / +128 / +136 | `Q2 Q3 Q3`（指针，成对） |
| +144 / +152 | `10.0 / -100.0` | +160 ~ +184 | `0.0` |
| +192 / +200 / +208 / +216 | `0.0625 / 0.0625 / 0.1 / 0.1` | +224 / +232 | `0.0` |

- 结构：**240 = 5 组 × 48 字节**（每组 6 个 8 字节槽）；指针"成对重复"⇒ 疑似 current/next 两份状态（**未验证**）
- 🔴 **结构语义**：整块 = 「当前一份 + `_Prev` 上一份」**成对状态**（云图/云剖面/序列/播放器/Actor 引用 + 过渡时长/变天时间 + MPC 参数 + 温度偏移）

**v111 实测解出的 30 个子字段**（`structFields[]`，字段名已剥 `_Index_GUID` 后缀；值取自 19:21 快照）：

| 偏移 | 字段 | 值 | 说明 |
|---:|---|---|---|
| +0/+8/+16 | `HighAltCloudMap` / `MidAltCloudMap` / `LowAltCloudMap` | 对象指针 | 高/中/低**云图** |
| +24/+32/+40 | 三者 `_Prev` | 与当前同指针 | 本次未切换 |
| +48 | `HighAltCloudProfile` | **6** | 高空云层剖面号 |
| +56 | `MidAltCloudProfile` | **2** | 中空云层剖面号 |
| +64 | `LowAltCloudProfile` | **4** | 低空云层剖面号 |
| +72/+80/+88 | 三者 `_Prev` | 6 / 2 / 4 | 同当前 |
| +96 / +104 | `WeatherSequence` / `_Prev` | 对象指针 | 天气序列 |
| +112 / +120 | `WeatherSeqPlayer` / `_Prev` | 对象指针 | 序列播放器 |
| +128 / +136 | `WeatherSeqActor` / `_Prev` | 对象指针 | 序列 Actor |
| +144 | `WeatherTransitionDuration` | **10** | 天气过渡时长（秒） |
| +152 | `WeatherChangedTime` | **-100** | 上次变天时间（-100 = 未初始化） |
| **+160 / +168** | **`MPCMeteors` / `_Prev`** | **0 / 0** | **陨石材质参数（陨石事件可直接看这里）** |
| +176 / +184 | `MPCLightning` / `_Prev` | 0 | 闪电材质参数 |
| +192 / +200 | `MPCBlowingFog` / `_Prev` | 0.0625 | 雾气强度 |
| +208 / +216 | `MPCWindStrength` / `_Prev` | 0.1 | 风力强度 |
| +224 / +232 | `Temperature_Offset` / `_Prev` | 0 | 温度偏移 |

- ✅ **插件输出**（v111+）：`structKind`（`ScriptStruct` = 原生结构体 / `UserDefinedStruct` = 蓝图结构体）、
  `structType`（结构体名）、`structFieldCount`、`structFields[{name,offset,size,value,hex?}]`；
  失败时输出 `structFields:null` 并附 `structProbe` 自检信息
- ⚠️ **BP 字段名带 `_Index_GUID` 后缀**，前端展示前请剥掉（如 `MPCMeteors_94_01E7D4E1...` → `MPCMeteors`）
- 前端建议：陨石判定可用 `CurrentWeatherStates.MPCMeteors`、`WeatherTransitionDuration`、`WeatherChangedTime`
  作为补充；主判据仍是 §3.3/§3.4 的 `extWeather.*Name` 与 `bMeteorFXActive`

---

### 3.7 🎯 Ext 陨石雨：id=6 + **预兆字段** + 秒级预警（2026-10-05 21:38 实测）

**陨石雨是天气 id 6**（`wxSemantics.presetTable`，共 5 项）：
`id1 WeatherPreset_EXT_Cloudy` · `id2 …_Overcast` · `id3 …_Spooky` · `id5 …_ClearSky` · **`id6 …_MeteorRain`**

**预兆字段（"到点 → 40~80 秒过渡 → 陨石落地"，不是瞬间跳出来）** —— 均在 `BP_EXT_WeatherSystem_C` 上：

| 字段 | 实测 | 含义 |
|---|---|---|
| `bMeteorFXActive` | `0` | **陨石特效开关**（预兆核心） |
| `MeteorVolume` / `FinalMeteorVolume` | `0` / `0` | 当前/目标音量（**渐入的听觉预兆**） |
| `GlobalMeteorRainSound` | `0` | 全局陨石雨音效 |
| `MeteorMPC` | `0` | 材质参数集合（天空/粒子） |
| `MeteorRain` | → `BP_Meteor_Spawner_C` | 陨石雨直接挂**生成器对象**（用 `probe=MeteorRain` 可读） |
| `bInWeatherTransition` | `0` | **过渡中标志**（=1 即进入预兆窗口） |
| `WeatherTransitionTimeMin/Max` | `40` / `80` | 官方过渡窗口 **40~80 秒** |
| `NextWeatherReplicated` | `0` | 下一天气**未提前复制/未提前可读** |

- ⚠️ `MeteorRain` / `WeatherChances` / `PossibleWeatherChances` / `BadWeatherWeightCurve` 用 `props=1` 显示 `unreadable`，
  **必须用 `probe=` 读**（写法：`actor filter=EXT_WeatherSystem props=1 probe=MeteorRain`）。
- **秒级预警口径**：轮询 `weather full=1`（或 `probe=bMeteorFXActive`）——
  `bMeteorFXActive==1` **或** `bInWeatherTransition==1` （配合 `MeteorVolume>0`）即"预兆中"，
  提前量 = 过渡时长（`WeatherTransitionTimeMin`~`Max`，40~80 秒）。
- 其他：`Meteor_Shield_Dome_C` x2 / `Meteor_Shield_City_C` x1 为陨石护盾建筑；`BP_Meteor_Spawner_C` 有 200 个属性但**无倒计时字段**（被动生成器）。


#### 3.7.1 前端调用示例（**v117+**，实测 2026-10-05 21:49）

```
TransferIdentityFix.WorldProbe meteor          # 每 1~2 秒调一次
```

典型响应（无陨石时，**v121 形态**）：
```json
{"ok":true,"sub":"meteor",
 "worldTime":251767300.55,"worldTimeSource":"gamedouble",
 "supported":1,
 "meteorWeatherId":6,"meteorWeatherName":"WeatherPreset_EXT_MeteorRain",
 "currentWeatherId":1,"nextWeatherId":1,"inMeteorShower":0,
 "fxActive":0,"inTransition":0,"nextWeatherReplicated":0,
 "warn":0,"warnReason":"none","phase":"none","volumeTrend":"flat",
 "volume":0.0,"finalVolume":0.0,
 "transMin":40.0,"transMax":80.0,"timerNextWeather":251764209.147,
 "changeMin":1000.0,"changeMax":2000.0,"secondsUntilChange":1793.406}
```
> ⚠️ v117 的响应**没有** `worldTime` / `worldTimeSource`；v118+ 才有 `phase` / `volumeTrend`（四态驱动，见 §3.7.1 第 1 条）。

**前端判读**：

1. **主判据用 `inMeteorShower == 1`（不要只凭 `warn==1`）**：它在过渡开始的**瞬间**就为真
   （`currentWeatherId` 立刻变 6），天然包含 **40~80 秒预兆提前量**；`warnReason` 仅作文案补充。
   🔴 **实测坑**：切回晴天时音量仍在衰减 + `inTransition=1` ⇒ 会出现 `warn=1` 但 `inMeteorShower=0` 的**假预警**，
   此时应**不弹窗**（详见 RCON 文档 §3.11(f) 的三态对照表）。
   ✅ **v118 起直接按 `phase` 驱动（已实测四态）**：`incoming` → 弹（预兆，提前 40~80 s）；
   `active`（`fxActive=1`）→ 弹；`leaving` → **不弹**（`warn` 已收敛为 0）；`none` → 不弹。
   `volumeTrend`（`rising`/`falling`/`flat`）可用于进度条或音效渐入动画。
2. **提前量 = 过渡窗口**（`transMin`~`transMax`，40~80 秒），**不是** `secondsUntilChange`（那是"下次随便什么天气"的时间）。
3. `supported==0`（非 Ext 图）→ 隐藏该面板，不要报错。
4. ⚠️ `transElapsed` 是**绝对时间戳**，别当"已耗时秒数"显示。
5. 性能：响应 702 B、实测 1.19~1.22 s/次（含客户端脚本启动开销），1~2 秒轮询无压力。


#### 3.7.2 运维：如何强制触发陨石雨（**仅测试用**，`fnIdx=2` 必须带）

```
TransferIdentityFix.WorldProbe callfunc filter=EXT_WeatherSystem fn=WeatherChange fnIdx=2 \
    p.Weather=6 p.TransitionTime=40 apply=1     # 切陨石雨
TransferIdentityFix.WorldProbe callfunc filter=EXT_WeatherSystem fn=WeatherChange fnIdx=2 \
    p.Weather=1 p.TransitionTime=40 apply=1     # 收尾切回阴天
```

实测时间线（`TransitionTime=40`，2026-10-05 21:55，用户目视确认"天变暗 / 雷声 / 陨石"）：

| 时刻 | `volume` | `inTransition` | `fxActive` | `warn` |
|---|---|---|---|---|
| +0 s | 0.031 | 1 | 0 | 1 |
| +13 s | 0.499 | 1 | 0 | 1 |
| +31 s | 0.966 | 1 | 0 | 1 |
| **+44 s** | **1.0** | **0** | **1** | 1 |

⇒ 前端据此理解预兆形状：**音量线性渐入 → 过渡结束瞬间 `fxActive` 翻 1（陨石落地）**。
⚠️ 另有两个"看着像但实测无效"的入口（`SetCurrentWeatherState` / `ForceSetCurrentNextWeathers`），详见 RCON 文档 §3.11(g)。


### 3.8 Ext 天气概率（**可选展示**，2026-10-05 22:40 实测解出）

```
TransferIdentityFix.WorldProbe actor filter=EXT_WeatherSystem props=1 probe=WeatherChances,PossibleWeatherChances top=1
```

| 天气 | **当前概率**（`WeatherChances` 归一化） | 基准权重（`PossibleWeatherChances`） |
|---|---:|---:|
| 阴天 `Cloudy` | **21.7%** | 1.0 |
| 阴郁 `Overcast` | **21.7%** | 1.0 |
| 诡异 `Spooky` | **17.4%** | 1.0 |
| 晴 `ClearSky` | **21.7%** | 1.0 |
| **陨石雨 `MeteorRain`** | **17.4%** | 1.0 |

- 下标 = 天气 id（0..6；id 0 / 4 未定义、权重恒 0）
- 🔴 **权重会变**（坏天气由 `BadWeatherWeightCurve` 下调）⇒ **请实时按 `WeatherChances` 归一化算概率**，不要写死 17.4%
- 展示建议：「陨石雨 约 17%（按当前权重）」；可用基准表（各 20%）做对照解释"为什么现在不是 20%"


#### 🔍 Ext 概率「完整性」补全（2026-10-05 23:07 实测，v120b）

| 槽 | `size` | 实测值 | 结论 |
|---|---:|---|---|
| `WeatherChances` | 16 | `[0, 1, 1, 0.8, 0, 1, 0.8]`（num=7） | ✅ **权威权重**（下面的百分比即由此归一化） |
| `PossibleWeatherChances` | 16 | `[0, 1, 1, 1, 0, 1, 1]`（num=7） | 基准表（5 天气各 20%，仅作对照） |
| `RegionWeights` | 32 | **全 0**（32 B 零填充） | ❌ **未使用** ⇒ Ext **无**区域差异概率 |
| `CaveWeights` | 32 | **全 0** | ❌ **未使用** ⇒ 洞穴与地表同概率 |
| `BadWeatherWeightCurve` | 8 | **对象引用** → `CurveFloat` / `C_EXT_BadWeatherWegiht` | ⚠️ **曲线对象**（非数组），动态修正坏天气权重 |

- 🔴 **驱动变量已定位**：`EXT_WeatherSystem.GoodWeathersSinceBad`（实测 `0`）——
  即"距上次坏天气已经过的好天气数"，正是 `C_EXT_BadWeatherWegiht` 曲线的输入。
  ⇒ **实时概率 = `WeatherChances` 归一化 × 曲线(GoodWeathersSinceBad)**；曲线数值**尚未解出**（待 v121 读 `FRichCurve::Keys`）。
- ✅ **Ext 变天倒计时（可直接做）**：`TimerNextWeather` 是**绝对世界时间**（实测 `251767202.8`），
  变天区间 `WeatherChangeTimerMin/Max = 1000 / 2000` 秒 ⇒ `距下次变天 = TimerNextWeather − worldTime(weather 分支)`。
- 运行时状态字段：`CurrentWeather = 1`（Cloudy）/ `NextWeather = 1` / `PrevWeather = 1` /
  `bEnableWeatherTimer = 1` / `bHasWeatherTimer = 1` / `bInWeatherTransition = 0` / `WeatherTransitionTimeElapsed = 251765998.88`。

#### 🎯 Sco（UDS_SE_Weather）日/夜权重表 —— **已完整解出**（2026-10-05 22:59 实测，v120 + `dataHex`）

命令：`WorldProbe actor filter=UDS_SE_Weather props=1 probe=WeatherWeights_Day,WeatherWeights_Night,WeatherEventLengths,WeatherSettings,DefaultWeather top=1`

**下标 = `arrayProbe.presetTable` 的顺序 `i`（0..7）——不是天气 id**（8 槽数组而 id 为 {0,2,3,4,5,6,7,8} 不连续，故只能是顺序下标；实测昼夜分布也完全符合直觉）

| `i` | 天气（presetTable） | **白天权重**（归一化） | **夜晚权重**（归一化） | 时长 |
|---:|---|---:|---:|---:|
| 0 | `ColdFront_SE` 寒潮 | 0（**0%**） | 0.5（**29.4%**） | 800 s |
| 1 | **`ElectricalStorm` 雷暴** | 0.1（**4.5%**） | 0.2（**11.8%**） | 425 s |
| 2 | `Rain_SE` 雨 | 0.35（**15.9%**） | 0.1（**5.9%**） | 750 s |
| 3 | `Foggy_SE` 雾 | 0.15（**6.8%**） | 0.2（**11.8%**） | 650 s |
| 4 | `HeatWave_SE` 热浪 | 0.7（**31.8%**） | 0（**0%**） | 700 s |
| 5 | `Clear_Skies_SE` 晴 | 0.5（**22.7%**） | 0.5（**29.4%**） | 1200 s |
| 6 | **`Sand_Dust_Storm` 沙尘暴** | 0.25（**11.4%**） | 0.2（**11.8%**） | 425 s |
| 7 | `Superheat` 焚风 | 0.15（**6.8%**） | 0（**0%**） | 750 s |

- 原始值：`WeatherWeights_Day = [0, 0.1, 0.35, 0.15, 0.7, 0.5, 0.25, 0.15]`；
  `WeatherWeights_Night = [0.5, 0.2, 0.1, 0.2, 0, 0.5, 0.2, 0]`；
  `WeatherEventLengths = [800, 425, 750, 650, 700, 1200, 425, 750]`（秒）
- ✅ **结果自洽**：白天热浪最高（31.8%）/ 夜晚 0；夜晚寒潮最高（29.4%）/ 白天 0；夜晚无热浪与焚风
- 🔴 前端展示要点：**必须按白天/夜晚分别取权重**；`WeatherSettings` 是 80 B 原始块（byte 视图，非数值表，可忽略）
- 对齐来源：`wxSemantics.arrayProbe.presetTable`（`presetTable` 本身为 `null`，**必须读 `arrayProbe` 里的那份**）

### 3.9 Gen（32329）+ UDS 家族（Sco / Isl / Cen）概率（**需 v119+**）

#### 3.9.1 Gen 五图概率 —— ✅ **已完整解出**（2026-10-05 23:08，v120b，`BP_GEN_DayWeather_WeatherSystem_C` ×5）

- **结构**：每个小地图一套独立天气系统（`matched=5`），各自持有 **`WeatherPresetList`**（该图自己的预设表，对象数组）
  + **`WeatherChances`**（该图自己的权重，`num` 随图而变）。
- **`presetTableSource = "WeatherPresetList"`**（Ext 用 `WeatherPresetList` 之外还有别的；Gen 就靠它命名）。
- **`PresetTable` 示例（海洋图，7 条）**：`WeatherPreset_GEN_Ocean_ClearSky` / `_Rain` / `_ElectricalStorm` /
  `_Heatwave` / `_ClearSky_Fog` / `_Rain_Fog` / `_ElectricalStorm_Fog`。

| `propsIdx` | 小地图 | 预设表（`WeatherPresetList`） | `WeatherChances` | **解出概率** |
|---:|---|---|---|---|
| 0 | `arctic` 雪山 | `WeatherPreset_GEN_Arctic_ClearSky` | `[1]`（num=1） | **晴 100%** |
| 1 | `bog` 沼泽 | `WeatherPreset_GEN_Bog_ClearSky` | `[1, 1]`（num=2） | 晴 50% / 50%（2 槽） |
| **2** | **`ocean` 海洋** | **7 条 `GEN_Ocean_*`** | **`[1, 0.2, 0.2, 0.2, 0.1, 0.1, 0.1]`** | **晴 52.6% / 雨 10.5% / 雷暴 10.5% / 热浪 10.5% / 晴雾 5.3% / 雨雾 5.3% / 雷暴雾 5.3%** |
| 3 | `volcanic` 火山 | `WeatherPreset_GEN_Volcanic_ClearSky` | `[1, 1]` | 晴 50% / 50%（2 槽） |
| 4 | `lunar` 月球 | `WeatherPreset_GEN_Lunar_ClearSky` | `[1, 1]` | 晴 50% / 50%（2 槽） |
| 5 | （第 6 个系统） | `WeatherPreset_GEN_Lunar_ClearSky` | `[1, 1]` | 同上 |

- ✅ **`PossibleWeatherChances` 在五图恒为 `[0,1,1,1,0,1,1]`**（num=7，基准 20%×5），**不是**真实权重；
  **真实权重看各图自己的 `WeatherChances`**（`num` 会变：1 / 2 / 7）。
- 🔴 **重要**：**只有海洋图有多样天气概率**；雪山 / 沼泽 / 火山 / 月球的预设表**只有 1 个 `ClearSky`**
  ⇒ 这些图上的 `Storm` 等天气**不是权重抽签产生**（实测 arctic 当前 `Storm`，而其预设表只有 ClearSky），
  由序列事件 / 蓝图驱动 ⇒ **不可用权重预测**，前端请对这几图只做"当前天气"展示。
- 五图识别：`wxSystems` idx **12..16** = `arctic / bog / ocean / volcanic / null(月球)`（实测 23:08）。
- 命令：`WorldProbe actor filter=DayWeather_WeatherSystem props=1 propsIdx=<0..4> probe=WeatherPresetList,WeatherPresetListNight,WeatherChances,PossibleWeatherChances top=1`

#### 3.9.2 UDS 家族（Sco / Isl / Cen）—— ✅ **Sco 已解出**，Isl / Cen 待同法执行

- UDS 用的槽名与 Ext **不同**：`WeatherWeights_Day` / `WeatherWeights_Night`（**日/夜两套**，各 `num=8`）+
  `WeatherEventLengths`（时长表）、`WeatherSettings`（80 B 原始块）；Ext 的 `WeatherChances` 等槽在这些图上**不存在**。
- ✅ **Sco 已完整解出**（v120 + `dataHex`，2026-10-05 22:59）⇒ 见上方「🎯 Sco（UDS_SE_Weather）日/夜权重表」
  （删除了早期 v116 时期「只能看到前 4 个 double」的过期结论）。
- 🔜 **Isl / Cen** 同属 UDS 家族，部署 v119+ 后按同一命令即可解出（命令见上方 Sco 小节）。
- 🔴 前端注意：**展示概率时必须区分白天/夜晚**（UDS 两套权重）。

## 4. Rag（32326）—— 火山

### 4.1 命令

```
TransferIdentityFix.WorldProbe actor filter=VolcanoManager props=1 propsIdx=0
TransferIdentityFix.WorldProbe actor filter=VolcanoManager props=1 propsIdx=0 probe=VolcanoIntervalMinMax,VolcanoEventLength
```

实测命中：`BP_VolcanoManager_C_UAID_581122A0FE147E6E02_1747848833`（1 个）

### 4.2 事件字段（实测 18:31）

| 属性 | 实测值 | 说明 |
|---|---:|---|
| **`VolcanoActive`** | `0` | **喷发中（0/1）** |
| `VolcanoStarting` | `0` | 正在开始 |
| `VolcanoEnding` | `0` | 正在结束 |
| `TimeNextVolcanoEvent` | `0` | 下次事件时间戳（0 = 未排程） |
| `TimeVolcanoEventStarted` / `TimeVolcanoEventEnds` | — | 本次起止时间 |
| `VolcanoEventLength` | `120` | 单次持续 **120 秒**（**double 真值**，勿读 `asFloat2`） |
| `WorldVolcanicIntensity` | `0` | 全局火山强度（0~1） |
| `LocalVolcanicIntensity` | `0` | 局部强度 |
| `WorldVolcanicIntensityToConsiderLavaActive` | `0.75` | ≥ 此值 ⇒ 岩浆激活 |
| `WorldVolcanicIntensityToLaunchProj` | `0.9` | ≥ 此值 ⇒ 发射抛射物 |
| `ActorsInLava` | `0` | 落入岩浆的 Actor 数 |
| `LavaEnabled` | `0` | 岩浆启用 |

### 4.3 🔴 必读坑：`VolcanoIntervalMinMax`

- 该槽 8 字节，**必须用 `probe=` 读**：`asFloat2 = [5000.0, 15000.0]`（秒）⇒ 事件间隔 **5000~15000 秒**
- 若直接看 `actorProps.props[].value`，会得到 `1.67e+31` 这类**垃圾值**（8 字节槽按 double 解）

### 4.4 展示建议
`火山：平静/喷发中` + `强度 xx%` + `距离下次事件 mm:ss`（由 `TimeNextVolcanoEvent - worldTime` 换算）。

---

### 4.5 🎯 Rag 火山管理器字段表（`BP_VolcanoManager_C`，2026-10-05 21:38 实测）

`scan filter=Volcano` → **`BP_VolcanoManager_C` x1**（207 属性）；`actor filter=VolcanoManager props=1 probe=…`

| 字段 | 实测 | 含义 |
|---|---|---|
| `VolcanoIntervalMinMax` | `[5000.0, 15000.0]` | 事件间隔 5000~15000 秒（**必须 `probe=` 读**） |
| `TimeNextVolcanoEvent` | **8 字节全 0** | ⚠️ **当前未排期 ⇒ 给不出倒计时**（非读法问题） |
| `TimeVolcanoEventStarted` / `Ends` | `0` / `0` | 起止时间 |
| `VolcanoEventLength` | `120` | 单次持续 120 秒 |
| `VolcanoActive` / `VolcanoStarting` / `VolcanoEnding` | `0` / `0` / `0` | 事件状态 |
| `WorldVolcanicIntensity` / `LocalVolcanicIntensity` | `0` / `0` | 强度（0~1） |
| `WorldVolcanicIntensityToConsiderLavaActive` | `0.75` | ≥0.75 ⇒ 视为岩浆活跃 |
| `WorldVolcanicIntensityToLaunchProj` | `0.9` | ≥0.9 ⇒ 抛射弹幕 |
| `LavaEnabled` / `ActorsInLava` | `0` / `0` | 岩浆开关 / 岩浆中 Actor 数 |
| `tmp_VolcanoTransitionSpeed` | `0.05` | 强度过渡速度 |

- 🔴 **坑**：`TimeNextVolcanoEvent` 为真 0 时表示**尚未排期**，前端不要显示成"已过时间"；需持续采样观察它何时被写入。

#### 4.5.1 火山倒计时可行性（2026-10-05 22:13 **实测确认可行**）

- **判据**：`距下次喷发 = TimeNextVolcanoEvent − worldTime`
  （`TimeNextVolcanoEvent` 是**绝对世界时间**的 8 字节 double；它**不是**倒计时秒数）
- **排期公式（实测两次，完全吻合）**：`worldTime + rand(VolcanoIntervalMinMax)`，即 **`worldTime + rand(5000, 15000)` 秒**
  - 实测 ①：`238402000 + 7734.5 = 238409734.47` ✓
  - 实测 ②（调用 `SetNextVolcanoTime` 重抽）：`238402000 + 12562.8 = 238414562.76` ✓
- **何时会被排期**：一次事件结束之后（或手动触发）—— 所以**休眠期读到 `0` 是正常的**（尚未排期）
- 🚫 **【已作废 · 2026-10-05 22:19 的"复制属性会停旧值"结论】**
  该解释已被 **v121 根因分析推翻**：实测并非"停旧值"，而是 **`actor` 分支的 `worldTime` 用 6 位有效数字输出**
  （`238403998.03` 被印成 `238404000`），看起来像冻结。**同一时刻 `weather.worldTime` 一直是秒级连续推进的**。
  ⇒ 前端**不要**再做"连续两次 `worldTime` 是否变化"的可用性探测；直接用 **`weather.worldTime`**（v120 及更早）
  或 v121 之后的**任意分支 `worldTime`** 即可。**详见 §4.5.3 与 §9**。
- **强制触发/排期函数（v118+，`callfunc`，全部零参数）**：

| 函数 | 实测效果 |
|---|---|
| **`StartVolcanoEvent`** | ✅ **真正开始喷发**（实测）：`VolcanoActive=1` / `VolcanoStarting=1`；`TimeVolcanoEventStarted/Ends` 被写入且 **Ends−Started = 120 s = `VolcanoEventLength`**；`WorldVolcanicIntensity` 在约 25 秒内从 0 爬到 **1.0** |
| `ForceEndVolcano` | `VolcanoEnding=1` 并**重新排期**（实测后续 `Tnext = worldTime + 5427.7`） |
| `ForceStartVolcano` | 把 `TimeNextVolcanoEvent` 写成**「即将到期」**的时间（实测两次：`worldTime − 379` 与 `worldTime + 133`）⇒ 作用是**让下一次事件立刻到期**（需 tick 消费）；**不直接开喷**（`VolcanoActive` 保持 0） |
| `SetNextVolcanoTime` | **重新抽签排期**（+12562.8 s，落在 5000~15000 区间） |
| **`EndVolcanoEvent`** | ✅ **完整结束事件**（实测）：`VolcanoStarting` 由 1 归 0、`VolcanoEnding=1`、`WorldVolcanicIntensity` 按 `tmp_VolcanoTransitionSpeed`(0.05/s) 衰减到 0（1.0→0 约 20 s），随后 `VolcanoActive=0`（对比：`ForceEndVolcano` 停得更彻底且会**立刻重排**下一次事件） |

调用示例：
```
TransferIdentityFix.WorldProbe callfunc filter=VolcanoManager fn=SetNextVolcanoTime fnIdx=0 apply=1
```


#### 4.5.2 自然流程也会自动排期（2026-10-05 22:29 实测）

- `EndVolcanoEvent` 让事件干净结束后，**`TimeNextVolcanoEvent` 被自动写入** `238413080.76`
  ≈ 基准 **+10080 秒（约 2.8 小时）**，**落在 `[5000, 15000]` 区间内** ✓
  ⇒ 「距下次喷发」这条预测**在自然流程下同样成立**（不依赖手动 `SetNextVolcanoTime`）。

#### 4.5.3 🔴 时间基准精度（**v121 已统一各分支**；v120 及更早须用 `weather.worldTime`）

**背景**：v120 之前插件读 `worldTime` 走 `UWorld::TimeSeconds`（旧值/复制值，**1000 秒一跳**，实测
`238401000 → 238402000 → 238403000`），ETA 误差可达 ±1000 秒。

**根因已在 v121 定位并修复（2026-10-05 23:38 构建）**：

| 响应分支 | v120b 实测 `worldTime` | 输出路径 |
|---|---|---|
| `weather` / `zones` / `biometemps` | ✅ `273764105.56`（秒级） | 走 `TifJsonNum`（大值转**定点 2 位小数**） |
| `actor` / `scan` / `types` / `meteor` | ❌ `2.73764e+08`（= 273764000） | **直接 `<<` 进流 ⇒ 继承 ostream 默认 6 位有效数字** |

- 🔴 **真实根因**：时钟取值本身**没问题**（v120 已用 GameState 双精度值），
  是**部分子命令把 `world_ts` 直接流进 `ostringstream`**，按默认 **6 位有效数字**输出；
  在 ~2.7e8 量级下步长正好 **1000 s** ⇒ 看上去像"整千量化/冻结"（**不是**取值问题）。
- ✅ **v121 修复**：新增 `TifJsonNumStr()` / `TifWsJson()`，**9 个分支统一**走 `TifJsonNum` 口径；
  并让 **8 类直出分支**补上 `worldTimeSource`（v120 只有 `actor` / `meteor` 有）；
  `weather` / `zones` / `biometemps` / `levels` 分支走的是 `TifJsonNum`，**本身一直是秒级、且仍不带该字段**。
- ⇒ **v121 起**：`worldTime` 在任何分支都是**秒级可信**；前端仍建议统一取 `weather.worldTime`（同源、字段最全）。
- ⇒ **v120 及更早**：`actor` / `scan` / `types` / `meteor` 的 `worldTime` 只有 6 位有效数字（±500 s），
  **不可用于倒计时**；世界钟必须取 `weather.worldTime`。详见下方 v121 根因小节。

#### 4.5.4 Ext `dataHex` 生效状态 —— ✅ **已确认生效（2026-10-05 23:07）**

- 早期（22:40）Ext `probe=WeatherChances` **未回 `dataHex`**，当时 Ext 仍在 v118；**升到 v119+ 后已正常**
  （v120b 实测：`WeatherChances` / `PossibleWeatherChances` 均带 `dataHex`（128 B）+ `dataBytes`，见 §3.8）。
- 判别：**`probe=` 结果里出现 `asArray.dataHex`** = v119+；没有 = v118 及更早。
- 部署确认法：`DinoMutPing` 的 `build` 字段应为 **`Oct  5 2026 22:19` 之后**（v121 = `Oct  5 2026 23:38:38`）。

#### 4.5.5 ✅ v120 秒级时钟（2026-10-05 22:48 构建）与实测结论

- v120 把 WorldProbe 的世界时钟改为 **GameState 双精度值**（`ReplicatedWorldTimeSecondsDouble`，
  与蓝图 `GetServerWorldTimeSeconds` 同源）；旧的 `UWorld::TimeSeconds`（1000 秒一跳）仅兜底。
- 响应新增 **`worldTimeSource`**：`gamedouble`（精确）/ `worldtimesec`（兜底）/ `none` / `error`。
- **实测（五服 v120，2026-10-05 23:03）**：`weather` 类分支达到秒级精度 ✓；`actor` 类分支未生效 ✗
  （详见 4.5.3）⇒ **前端取钟口径见 4.5.3**。
- 产物：`TransferIdentityFixAPI.dll` = 1,795,072 B @ **2026-10-05 22:48:10**
  （二进制校验含 `gamedouble` / `worldTimeSource`）。

#### 4.5.6 🎯 火山倒计时「秒级」端到端验证 —— **通过**（2026-10-05 23:04 实测）

| 步骤 | 实测结果 |
|---|---|
| ① 重启后读 `TimeNextVolcanoEvent` | `0` ⇒ **服务器刚开机时火山未排期**（不是读法错误） |
| ② `VolcanoIntervalMinMax`（`probe=` 读） | `[5000.0, 15000.0]` ✓ |
| ③ `callfunc ... fn=SetNextVolcanoTime fnIdx=0 apply=1` | `Tnext` 被写入 `238415256.29` |
| ④ 同刻 `weather.worldTime` | `238403998.03` |
| ⑤ **ETA = Tnext − weather.worldTime** | **`11258.26` 秒（187.64 分）**，**落在 `[5000,15000]`** ✓ |
| ⑥ 连续采样（每 10 s） | ETA **按 1:1 秒级递减**（10 s 掉 10 s）✓ |

- ⇒ **结论**：Rag 火山倒计时**成立且可精确到秒**，但**前提是两条**：
  (a) 世界钟必须取 `weather.worldTime`（见 4.5.3）；
  (b) `TimeNextVolcanoEvent > 0`（**服务器重启后需等一次事件结束、或手动排期，才会被写入**）。
- **前端建议**：`Tnext <= 0` ⇒ 显示「空闲期·未排期」而非负数倒计时。

#### 4.5.7 强度阈值 / 控制三件套 / 未解悬念（从文末归位，2026-10-05 22:2x 实测）

- **强度阈值**：`WorldVolcanicIntensity ≥ 0.75` ⇒ 视为岩浆活跃（`WorldVolcanicIntensityToConsiderLavaActive`）；
  `≥ 0.9` ⇒ 抛射弹幕（`WorldVolcanicIntensityToLaunchProj`）。实测 `StartVolcanoEvent` 后强度 ~25 s 爬满到 1.0。
- **控制三件套（v118+，全部零参数 `callfunc`）**：
  - 开始喷发：`fn=StartVolcanoEvent fnIdx=0 apply=1`
  - 停止喷发并重排：`fn=ForceEndVolcano fnIdx=0 apply=1`
  - 重新抽签排期：`fn=SetNextVolcanoTime fnIdx=0 apply=1`

- 🔴 **未解悬念（2026-10-05 22:26~22:28 实测）**：即使 `WorldVolcanicIntensity = 1.0`、且玩家声称就在火山口，
  `LocalVolcanicIntensity` / `LavaEnabled` / `ActorsInLava` **仍恒为 0**，服务器上 `Projectile` 类 Actor **数量为 0**（一发弹幕都没射过）。
  - 对比坐标：`BP_VolcanoManager_C` 实测在 `x=165026, y=-351442`；三个在线 `PlayerPawnTest_Male_C` 分别在
    `(377717,-405363)` / `(-282318,103168)` / `(353798,-486081)` —— **没有一个在管理器附近**（最近 219,420 单位）；
    而 `Rag_LavaSpline_C`（岩浆河 22 个）集中在 `(77867,-225103)` 一带，与"管理器"也相距 15 万单位。
  - ⇒ 待查：**"本地强度/岩浆/弹幕"的参考点到底是哪个对象**（管理器？岩浆河？区域体积？），或该支路需要**正常流程**（原生事件）才被激活。
  - **前端建议**：目前只报 `WorldVolcanicIntensity`（全局）+ `VolcanoActive`；**不要**承诺"弹幕/岩浆"字段的可用性。

#### 🎯 v120 世界钟实测（五服全量，2026-10-05 23:07）—— **v121 已修复**

| 服 | 端口 | build | `weather.worldTime`（秒级） | `actor` 分支 v120b 输出 | 原因 |
|---|---:|---|---|---|---|
| Sco | 32321 | `Oct  5 2026 22:47:44` | `273762076.95 → 273762096.54` | `2.73764e+08` | 6 位有效数字 |
| Abe | 32323 | 同上 | 秒级 | `2.60721e+08` | 同上 |
| Ext | 32324 | 同上 | 秒级 | `2.51766e+08` | 同上 |
| Rag | 32326 | 同上 | `238403961.43 → 238403974.42` | `2.38404e+08` | 同上 |
| Gen | 32329 | 同上 | 秒级 | `2.07607e+08` | 同上 |

- ⇒ **五服全部 v120b**；`actor` 分支的"整千值"= **6 位有效数字格式化的产物**（同源同一个 `world_ts` 变量），
  **v121 已把所有分支统一到 `TifJsonNum` 口径** ⇒ 该现象消失。

#### 🔧 v121 根因定位与修复（2026-10-05 23:38 构建，**已推翻早前"整千量化"判断**）

- **现象**：`actor` / `scan` / `types` / `meteor` 分支的 `worldTime` 恒为 1000 的整数倍
  （Sco `273762000.0`、Rag `238404000.0`），而 `weather` 分支正常推进 ⇒ 早前误判为"整千量化/冻结"。
- **真实根因（实测确立）**：同一条命令族里 `worldTime` **共用一个 `world_ts` 变量**，
  但两条输出路径不同 ——
  - `weather` / `zones` / `biometemps`：`TifJsonNum()`（**大值 ≥1e6 转定点 2 位小数**）⇒ 完整精度；
  - `actor` / `scan` / `types` / `meteor`（含 `wxset` / `callfunc` / `wave` 等共 **9 处**）：
    `oss << world_ts` **直出** ⇒ 继承 ostream 默认 **6 位有效数字**，`273764105.56` 被写成 `2.73764e+08`。
  - 交叉验证：`2.73764e+08` 与真钟 `273764105.56` 的差恰为 105 s（< 半个 1000 s 步长），
    且 23:08→23:24（真实 1017 s）该值从 `2.07607e+08` 走到 `2.07608e+08` ⇒ **确实是同一个钟，只是印错精度**。
- **v121 修复**：新增 `TifJsonNumStr(double)`（`TifJsonNum` 的字符串版，可直接嵌进 `<<` 链、不改调用方格式标志）
  与 `TifWsJson(double, const char*)`（一次性输出 `,"worldTime":<秒级>,"worldTimeSource":"<源>"`）；
  9 处直出全部替换 ⇒ **所有分支的 `worldTime` 秒级可信**；其中 8 类直出分支同时补上 `worldTimeSource`
  （`weather` 类分支走 `TifJsonNum`，本就秒级、不带该字段）。**2026-10-05 23:52 五服实服验证通过**（见 §9.3）。
- **产物**：`TransferIdentityFixAPI.dll` = **1,797,632 B @ 2026-10-05 23:38:38**（v120b 为 1,795,072 B，+2,560 B）。
- **影响面**：Rag 火山 ETA、Abe/Gen 任何用 `actor` 分支钟算的倒计时；前端「取 `weather.worldTime`」的建议
  在 v121 起**不再是强制规避项**（但仍是推荐口径）。

## 5. Gen（32329）—— 五小地图天气 + 月球流星雨

### 5.1 命令

```
TransferIdentityFix.WorldProbe weather full=1 limit=3 actors=1
TransferIdentityFix.WorldProbe weather full=1 idx=2 allprops=1        # 只看海图（示例）
TransferIdentityFix.WorldProbe wave                                    # 海图深水大浪（水体参数）
```

### 5.2 五图识别（实测 18:31）

| `wxSystems[i]` | `miniMapType` | 小地图 | 实测 `currentWeather` |
|---:|---|---|---|
| 0 | `arctic` | 雪山 | `Storm` |
| 1 | `bog` | 沼泽 | `Rain` |
| 2 | `ocean` | 海洋 | `Rain` |
| 3 | `volcanic` | 火山 | `ClearSky` |
| 4 | `null` | **月球**（无标志位，只能靠 `null`/Level 名判定） | `ClearSky` |

- ✅ **权威标识 = `miniMapType`**（v85 起）；`cloud.regions[i]` 是同序镜像（更省流量的取法）
- ⚠️ **`wxSystems[i]` 的下标 `i` 会随地图加载顺序变化**（本表是 18:31 的 0..4；23:08 复测为 12..16，见 §5.5 / §3.9.1）
  ⇒ 前端**必须按 `miniMapType` 匹配**，**不要写死下标**（`null` = 月球）
- 🔴 `bIsArctic` / `bIsBog` / `bIsOcean` / `bIsVolcanic` 是**身份标识（恒定）**，**绝不能**当事件开关
- 每份 `wxSystems[i]` 自带 `currentWeather` / `nextWeather` / `timerNextWeather` / `timeOfDay`

### 5.3 月球流星雨

- 对应 **月球小地图**（`miniMapType=null`）的天气序列；生成器为 `LunarMeteorController_C`（Ext 陨石的等价物：`BP_Meteor_Spawner_C`）
- 判定：该小地图 `currentWeather`/`nextWeather` 落在流星雨序列上（名称由该图自己的预设表决定）

### 5.4 海图"深水区大浪"（不是天气事件）

`wave` 命令实测四组水体（`bakedOceanState / waveHeight / waveSteepness / bakedOceanSpeed / waterLevel / oceanTile`）：

| 组 | waveHeight | waveSteepness | waterLevel | 结论 |
|---:|---:|---:|---:|---|
| 1 | **47.25** | **7** | **-285199** | 深水区大浪 |
| 2 | 2 | 10 | 87 | 浅水 |
| 3 | 0.3 | 0.5 | 84 | 浅水 |
| 4 | 10 | 0 | 0 | 中水 |

- ⚠️ 气旋（`Buff_CycloneBox_C` / `Buff_UnderwaterCyclone_C`）是**另一套机制**，别与大浪混用

---

### 5.5 🎯 Gen 五图天气倒计时（2026-10-05 21:31 实测）

命令：`TransferIdentityFix.WorldProbe weather full=1 limit=6 actors=1` → 读 `wxSystems[i]`

| 小地图 | `miniMapType` | 当前天气 | `secondsUntilChange` |
|---|---|---|---:|
| 雪山 | `arctic` | Storm | ⚠️ `1000`（**该图未运行**） |
| 沼泽 | `bog` | Rain | 1403 秒（23.4 分） |
| 海洋 | `ocean` | ClearSky（prev=Rain） | 354 秒（5.9 分） |
| 火山 | `volcanic` | ClearSky（**prev=`Eruption`**） | 1824 秒（30.4 分） |
| 月球 | `null` | ClearSky | 2007 秒（33.5 分） |

- ✅ **首选 `secondsUntilChange`**（插件已算好的剩余秒数）；`timerNextWeather` 是**绝对世界时间**，前端别自己减。
- 🔴 **坑：未运行的图给假倒计时** —— `beginAt < 0`（实测 `-100`）即「**未运行**」，此时 `timerNextWeather` 是相对默认值（`1000`）；
  正常运行的图 `beginAt` 是绝对世界时间。
- 每图变天区间 `changeTimerMin/Max = 1500/2500` 秒（25~41.7 分）；`activeWxIdx` = 正在计时的系统下标。
- 火山小地图的天气序列含 `Eruption`（**与 Rag 的 `BP_VolcanoManager_C` 不是同一套机制**）。
- 权重/名字槽 `weightsDay` / `weightsNight` / `eventLengths` / `settingsScan` / `arrayProbe` / `defaultWeather` **全为 null**。


#### 🌙 Gen 月球流星雨：**可预测（字段齐全）**；**有玩家时正常推进**（2026-10-06 00:09 实测）

**控制器**：`LunarMeteorController_C`（`scan filter=LunarMeteor` → `distinct=1`，全世界仅 1 个）

| 字段 | 实测值 | 含义 |
|---|---:|---|
| `Active` | `1`（空服）/ `0`（实活全程） | ⚠️ **语义未定论**：空服采样为 `1`、有玩家时（含刚触发瞬间）全程为 `0` ⇒ **前端勿用此字段判断事件是否正在进行** |
| `TimeLastEvent` | `207609342.14` | **上次事件开始时间（绝对世界时间）**，事件触发时更新 |
| `ActualTimeBetweenEvents` | `474.825` | **实际间隔**（每次事件后重抽） |
| `MinTimeBetweenEvents` / `MaxTimeBetweenEvents` | `300` / `800` | 间隔**区间** ⇒ 在 300~800 s 间**均匀随机** |
| `DurationOfEvent` | `240` | 单次持续 **240 s** |
| `ParticleIntensity` | `20` | 粒子强度 |
| `CurrentStormRotation` | `-7.83929` | 风暴旋转角（空服采样时为 `-48.425`） |
| `CometSpawnBoxExtent` / `LunarPSOffset` | `20000` / `-250000` | 生成盒尺寸 / 月球粒子偏移 |
| `BackgroundMeteorEmitter` | `0` | 背景流星发射器（未激活） |
| `ClientTick` / `ServerTick` / `WarmUpLength` | `1` / `1` / `60` | 客户端·服务端 tick 开关（**均开**）/ 事件**预热 60 s** |
| `VectorDot1` / `Vector to check against` | `0.75` / `1` | 方向判定参数 |

- **预测公式**：`下次事件 ≈ TimeLastEvent + ActualTimeBetweenEvents`（实测 `207606947.85 + 658.516 = 207607606.37`）
- **概率口径（可直接展示）**：事件间隔**均匀分布于 [300, 800] s**（均值 550 s），单次持续 **240 s**
  ⇒ **流星雨时间占比 ≈ 240 / 550 ≈ 44%**；`ActualTimeBetweenEvents` 每次事件后重抽。
- ✅ **有玩家时定时器正常工作（2026-10-06 00:09 实测，详见下方 §5.5.1）**：`TimeLastEvent` **会推进**、
  `ActualTimeBetweenEvents` 每次重抽（实测 `474.825`）、ETA 按真钟 **1:1 递减**、第 14 轮抓到真实触发。
  ⇒ 前端公式 `ETA = TimeLastEvent + ActualTimeBetweenEvents − worldClock` **可直接用**。
- 🔴 **注意（空服限制）**：**无玩家在 Gen 时定时器不推进**（实测 23:24:57→23:25:14 真钟越过预测时刻，
  ETA 由 `-44.8 s` 漂到 `-62.1 s`，`TimeLastEvent` 始终未更新）⇒ 空服取不到真实事件时刻，
  上线后若发现 ETA 长时间为负，**先确认玩家是否在 Gen**。
- 另：月球小地图的**天气**（`wxSystems` idx=16）与流星雨**是两套机制** —— 该图天气预设表只有 `ClearSky`，
  流星雨由本控制器独立驱动（与天气权重无关）。
- 命令：`WorldProbe actor filter=LunarMeteorController props=1 propsIdx=0 top=1`

### 5.5.1 ✅ 月球流星雨「实活」实测（2026-10-06 00:09，有玩家在 Gen）

**结论：定时器与预测公式均在真实运行状态下有效** —— 空服时观察到的"不推进"**不是公式问题**。

| 验证点 | 实测 |
|---|---|
| 定时器是否推进 | ✅ `TimeLastEvent` 由空服采样时的 `207606947.85` 推进到 `207609342.14`（+2394 s） |
| 间隔是否重抽 | ✅ `ActualTimeBetweenEvents` = **474.825**（落在 `[300, 800]` ✓） |
| 预测公式 | ✅ **分段 1:1 递减**（ETA 到点归零后按新间隔重算，故不可拿全程首末值比较）：触发前 12 轮 `185.5 → 7.1`（真实 180 s / Δ-178.4）；触发后 `696.0 → 607.0`（真实 90 s / Δ-89.0）<br>ℹ️ 采样脚本自带「结论判定」打印的 `❌` 系**脚本逻辑缺陷**（只比较首末 ETA、跨过了触发点重置），**非事实判定** |
| 事件触发 | ✅ **抓到触发**：第 14 轮 `TimeLastEvent` 跳到 `207609817.19`（`★ 新事件 +475.05`） |
| **预测精度** | ✅ 预测 `207609342.14 + 474.825 = 207609816.965` vs 实际 `207609817.19` ⇒ **误差 +0.225 s** |
| 控制器状态 | ✅ 与空服采样时不同：`CurrentStormRotation` `-48.4 → 13.3623` ⇒ 控制器在真实运行 |

（采样轮次：20 轮 / 约 228 秒；下表每 4 轮抽 1 行 + 触发轮）

| 轮 | 时刻 | 世界钟 | `TimeLastEvent`(+`Actual`) | ETA(s) | `Active` | `ParticleIntensity` | `CurrentStormRotation` | 触发 |
|---:|---|---|---|---:|---:|---:|---:|---|
| 1 | 00:09:30 | `207609631.48` | `207609342.14`(+`474.825`) | 185.5 | `0` | `20` | `-7.83929` |  |
| 5 | 00:10:30 | `207609691.07` | `207609342.14`(+`474.825`) | 125.9 | `0` | `20` | `-7.83929` |  |
| 9 | 00:11:30 | `207609750.39` | `207609342.14`(+`474.825`) | 66.6 | `0` | `20` | `-7.83929` |  |
| 13 | 00:12:30 | `207609809.87` | `207609342.14`(+`474.825`) | 7.1 | `0` | `20` | `-7.83929` |  |
| 14 | 00:12:45 | `207609824.70` | `207609817.19`(+`703.485`) | 696.0 | `0` | `20` | `13.3623` | ★ 新事件 +475.05 |
| 17 | 00:13:30 | `207609869.29` | `207609817.19`(+`703.485`) | 651.4 | `0` | `20` | `13.3623` |  |

> ⚠️ **顺带纠正一个口径**：本次前置检查显示 **5 张子图全部 `beginAt=-100`**、月球 `secondsUntilChange=1000`：
> 按「`beginAt<0` + `sec=1000` ⇒ 该图**未运行**」的旧说法应判为未运行 —— 但流星雨定时器**确实在推进**。
> ⇒ 这两个字段只反映**天气切换**调度状态，**不能用来判断子图是否已加载 / 玩家是否在场**；要判断玩家在不在该图，用 `/tif status` 或玩家位置类字段。

### 5.6 【概率口径】下次天气/下个事件能不能预测（跨服通用，2026-10-05 实测定论）

| 服 | 权重/概率表 | 下一天气可提前得知？ |
|---|---|---|
| **Ext** | ✅ **可读**：`WeatherChances` / `PossibleWeatherChances` 为 **double 数组**（`0.0 / 1.0 / 1.0 / …`，num=7）；`BadWeatherWeightCurve` → `CurveFloat C_EXT_BadWeatherWegiht`（原版笔误） | ❌ `nextWeatherId` 与当前相同（占位）、`NextWeatherReplicated=0` |
| **Gen** | ✅ **可读（2026-10-05 23:08 解出）**：**每图各自的** `WeatherChances`（`num` 随图变：arctic 1 / bog·volcanic·lunar 2 / ocean 7）+ `WeatherPresetList` 直接给名字；海洋图 `[1,0.2,0.2,0.2,0.1,0.1,0.1]` ⇒ **晴 52.6% / 雨·雷暴·热浪 10.5%×3 / 三种雾 5.3%×3**；其余四图预设表仅 `*_ClearSky` ⇒ **天气非权重抽签、不可用概率预测** | ❌ `nextWeather` 5/5 图与当前相同 |
| 🌙 **Gen 月球流星雨** | ✅ `LunarMeteorController_C`：间隔 **Min/Max=300/800 s 均匀随机** + `DurationOfEvent=240 s` ⇒ 占比 ≈ 44% | ✅ `TimeLastEvent + ActualTimeBetweenEvents`（**有玩家时已实测有效**；空服不推进，见 §5.5.1） |
| Sco | ✅ **可读**：`WeatherWeights_Day` / `WeatherWeights_Night`（各 `num=8`）+ `WeatherEventLengths`（白天热浪 31.8% 最高 / 夜晚寒潮 29.4% 最高，见「🎯 Sco（UDS_SE_Weather）日/夜权重表」） | ⚠️ `nextWeather` 与当前相同（占位）⇒ 只能给概率，给不出「下一个是谁」 |
| Rag | ❌ **不适用**（火山是独立管理器，非天气权重体系） | ✅ 但**能算倒计时**：`TimeNextVolcanoEvent − worldTime`（见 §4.5） |

**结论与建议（前端/后端分工）**：

1. **时间维度**：确定值，直接展示 —— Gen 每图 `secondsUntilChange`；Ext `secondsUntilChange`；Rag 待 `TimeNextVolcanoEvent` 排期后可算。
2. **内容维度**：Ext / Sco / Gen(海洋图) 的概率表**均已可读**（把数组下标与 `presetTable` / `WeatherPresetList` 顺序对齐即可给出「各天气占比」）；
   仅 **Gen 的非海洋四图**（预设表只有 `ClearSky`）与 **Abe 地震** 无权重可算 ⇒ 前者只能报「当前天气」，后者需服务端记历史。
3. **谁算更好 → 插件侧（服务端）算**：① 这些字段只有服务端可读；② 统计要**持续采样**，前端轮询会丢样本、刷新即丢历史；
   ③ 前端只负责展示结果，避免拉全表与跨设备口径不一致。
4. **事件型天气（陨石雨/沙尘暴/火山）：走"秒级预警"而非"概率预测"** —— 预兆字段（§3.7）能给出 40~80 秒提前量。

## 6. 通用字段口径（前端必读）

| 主题 | 口径 |
|---|---|
| **8 字节槽** | 可能是 `double` / `FVector2D` / `int64` 枚举。`probe=` 会同时给 `asInt2` / `asFloat2` / `f64` 与 `hex`；**不能只信 `asFloat2`**（`VolcanoEventLength` 真值 120 是 double） |
| **`unreadable` / `unreadableEmitted`** | 属性存在但读不出数值（多为容器/对象引用）。v104 起会**连名字一起输出**（`{"name":X,"value":null,"type":"unreadable"}`） |
| **`truncated` / `container`** | v105 起，宽槽（>64 字节）会输出 `size` + 前 64 字节 hex，并对容器做 **h0/h24** 双候选元素扫描 |
| **v106 判别串** | `wxSemantics.presetTableSource`（= 插件已直接给出 id→名称映射） |
| **v107 判别** | 宽槽（>64 字节）`hex` 长度 **480 字符**（240 字节）= v107+；128 字符（64 字节）+ `truncated` = v106 及更早 |
| **v111 判别 / 结构体** | 响应出现 `structKind` / `structFields` = v111+；结构体属性的子字段可直接读（见 §8） |
| **`weatherState.family`** | `uds`（Sco/Isl/Cen） / `ab`（Abe） / `ext_gen`（Ext + Gen）—— 各家族字段名不同，按 key 取用而非按属性名 |
| **世界时间** | ⚠️ **v120 及更早**：必须取 `weather` 响应里的 `worldTime`（秒级）；`actor` / `scan` / `types` / `meteor` 分支只有 **6 位有效数字**（±500 s，不可用于倒计时）。**v121 起**（dll `1,797,632 B @ 2026-10-05 23:38:38`）所有分支均已秒级，见 §4.5.3 |
| **`worldTimeSource`** | v121 起 **`actor`/`scan`/`types`/`meteor`/`wave`/`query`/`callfunc`/`wxset` 8 类分支都有**（`gamedouble` 精确 / `worldtimesec` 兜底 / `none` 未就绪 / `error`）；`weather` / `zones` / `biometemps` / `levels` **仍不带**（本就秒级）；v120 仅 `actor` / `meteor` 有 |
| **性能** | `actor`/`weather` 全量扫描约 **1.2~1.5 s**；建议轮询间隔 ≥ 60 s（占用 < 2%） |
| **RCON 调用** | 每条命令独立连接/进程；同一进程连发会**死锁** |

---

## 7. 采样证据（可复核）

| 文件 | 内容 |
|---|---|
| `tmp\_events_raw\Sco_32321_weather.json` | Sco 天气全响应（含 `settingsScan` / `arrayProbe.presetTable` / `fields[]`） |
| `tmp\_events_raw\Abe_32323_quake.json` | Abe 地震系统全属性（`bEarthQuake` 等 47 项） |
| `tmp\_events_raw\Abe_32323_weather.json` | Abe 天气（`semSource=BP_AB_WeatherAgent_C`，4 个 wxSystems） |
| `tmp\_events_raw\Ext_32324_weather.json` | Ext 天气（`presetTable` / `extWeather`，v106 输出） |
| `tmp\_events_raw\Rag_32326_volcano.json` | Rag 火山管理器全属性 |
| `tmp\_events_raw\Gen_32329_weather.json` | Gen 五图天气 + cloud.regions |
| `tmp\_events_gather_out.txt` / `_events_extract_out.txt` | 上面的字段抽取汇总（本地解析，无 RCON） |

> ⚠️ `tmp\` 为临时目录，**这些快照可能已被清理**；缺失时用每节顶部给出的命令重跑一遍即可复现（命令均为只读）。

---

## 8. 结构体子字段解码（v108~v111 新能力）

> 背景：以前宽槽（如 `CurrentWeatherStates` 240 字节）只能当**黑盒 hex** 交给前端；
> **v111 起插件直接给出结构体名 + 每个子字段的名称/偏移/大小/值**，前端可按下标取值，不必自己拆字节。

### 8.1 怎么触发

任何 `props=1` 类命令（`actor` / `weather`）在遇到**结构体属性**时**自动附带**，无需额外参数：
命中时给 `structKind` / `structType` / `structFieldCount` / `structFields[]`；未命中给 `structFields:null` + `structProbe`（自检信息）。

### 8.2 响应键口径

| 键 | 含义 | 取值示例 |
|---|---|---|
| `propSelf.{cls,elem,structOff,innerOff}` | 属性自身自检（类指针 / 元素名 / Struct 字段偏移 / Inner 偏移） | `d03f446cf77f0000` / `null` / `112` / `120` |
| `structKind` | 结构体种类 | `ScriptStruct`（原生）/ `UserDefinedStruct`（**蓝图结构体**）/ `Class`（**不是结构体**）/ `null` |
| `structType` | 结构体名 | `S_EXT_WeatherState` |
| `structFieldCount` | 子字段数 | `30` |
| `structFields[i].{name,offset,size,value}` | 子字段（非数值字段附 `hex`） | `{"name":"MPCMeteors","offset":160,"size":8,"value":0}` |

🔴 **前端判读要点**：

1. 只有 `structKind` 为 `ScriptStruct` / `UserDefinedStruct` 才能读 `structFields[]`；
   为 `Class` / `null` = **该属性本就不是结构体**（对象引用 / 容器 / Map）⇒ 请走原 `unreadable` / 容器路线，**不要视为解码失败**。
2. **蓝图结构体字段名带 `_Index_GUID` 后缀**（如 `MPCMeteors_94_01E7D4E1...`），展示前按第一个 `_数字_` 之前的主名截断即可。
3. 只解码**一层**；子字段若仍是结构体，该槽只给 `hex`（本次无嵌套用例，前端可能遇到需容错）。

### 8.3 实测样本（2026-10-05，v111）

| Actor / 属性 | 槽大小 | `structKind` / `structType` | 字段数 | 结论 |
|---|---:|---|---:|---|
| Ext `EXT_WeatherSystem.CurrentWeatherStates` | 240 | `UserDefinedStruct` / `S_EXT_WeatherState` | **30** | ✅ 全解（字段表见 §3.6） |
| Sco `UDS_SE_Weather_C.CurrSequenceSettings` / `PrevSequenceSettings` | 40 | `UserDefinedStruct` / `S_SE_CloudMapSequence` | **3** | ✅ 含 `FrameInterval=10` |
| Ext `EXT_WeatherSystem.PrimaryActorTick` | 64 | `ScriptStruct` / `ActorTickFunction` | 1 | ✅ 原生结构体同样可解 |
| Sco `UDS_SE_Weather_C.Obscured Lightning Niagara System` | — | `Class` | — | ✅ **正常拒绝**（对象/类引用属性） |
| Sco `UDS_SE_Weather_C.WeatherSettings` | 80 | `null` | — | ✅ **正常拒绝**（非结构体，疑 Map，走 `settingsScan` 路线） |

### 8.4 排查用（前端可忽略）

解码失败时响应含 `structProbe{addrs,fieldNames,propHead}` 与 `structCand`（候选结构体指针），
为插件侧自检信息；需要排查时把整段回贴给插件维护方即可。

---

## 9. 🆕 v121 → v122b2 接口变更摘要（前端必读；**线上 10 服 = v122b2 `01:50:26`，已全服实测通过**）

### 9.0 版本变更日志（历史汇总）

| 版本 | dll 体积 / 时间 | 变更点 | 影响 |
|---|---|---|---|
| v111 | 1,745,408 B @ 10-05 19:16 | `presetTable` 映射 / `structFields` 结构体解码 | 概率命名、结构体直读 |
| v117 | — | 新增 `meteor` 子命令 | Ext 陨石一条命令给全 |
| v118 | — | `phase` / `volumeTrend`；`warn` 收敛 | Ext 四态驱动、消除假预警 |
| v119 | 1,794,560 B @ 22:20 | `probe=` 增加 `asArray.dataHex` / `dataBytes` | Ext/Sco/Gen 概率表解出 |
| v120 / v120b | 1,795,072 B @ 22:48 | 世界钟改 **GameState 双精度** + `worldTimeSource` | 秒级时钟 |
| **v121** | **1,797,632 B @ 23:38:38**（编译戳 `23:38:11`） | **`worldTime` 输出精度统一（9 处直出）+ 8 类分支补 `worldTimeSource`** | **各分支时钟均秒级可信**（v120 及更早仅 `weather` 类分支可靠）✅ 五服已上线验证 |
| **v122** | **1,800,192 B @ 10-06 00:31** | **新增 `slim=1` 白名单视图（`weather` / `actor`）+ `weatherState.heatWaveActive` 派生键** | 体积可降约 95%；**默认关闭 ⇒ 不加 `slim=1` 与 v121 完全一致**（无破坏性） |
| **v122-hotfix** | **1,800,192 B @ 10-06 01:00:29** | **`actor` 分支改为扫描完整参数串** ⇒ `slim=1` / `fields=` 放在任意位置都生效 | 🔴 `00:30:33` 构建里 **`actor slim` 不生效**（该分支只解析前 4 个 token，实测 `VolcanoManager` full=slim=10,623 B）；`weather slim` 一直正常。**用 `actor slim` 前请确认 build = `Oct  6 2026 01:00:29`** |
| **v122b** | **1,808,896 B @ 10-06 01:23:19**（编译戳 `Oct  6 2026 01:22:47`，含 hotfix） | **新增 `WorldProbe badwx` 子命令**：把「坏天气权重因子」用**派生法**给出（`WeatherChances[i] / PossibleWeatherChances[i]`），并把 `(GoodWeathersSinceBad → factor)` 样本累积成 `learned[]` 学习表 | ✅ **不读任何曲线内存**（`FRichCurve` 布局不在公开头文件 ⇒ 猜偏移=已封禁的失败模式）⇒ 无崩溃/读错风险；首次调用 `learned[]` 为空，随时间自动补全曲线形状。**本次 dll 一并含 hotfix，`actor slim` 从此版本起生效**（10 服回归实测已确认 ✅）。遗留两点见下行 |
| **v122b2** | **1,808,896 B @ 10-06 01:50:57**（编译戳 `Oct  6 2026 01:50:26`） | ① **`fields=` 单独即可裁剪**（去掉 `slim &&` 前置条件）；② **无曲线驱动的图 `badwx.factor` 返回 `null`** + 新增 `reason` 说明，且该情形不再累积 `learned[]` | ✅ **2026-10-06 02:2x 全服 10/10 实测通过**：Gen `fields=` 单独用 = 720 B / 2 项；Ast/Rag/Val/Los/Gen `factor:null` + `reason` 5/5；Ext 仍 `0.8`；`actor slim` 与 `weather slim` 回归无变化 |


### 9.1 变更点（仅 2 项，无破坏性）

| # | 变更 | v120b 行为 | v121 行为 | 前端是否需要改 |
|---|---|---|---|---|
| 1 | `worldTime` 输出精度 | `actor` / `scan` / `types` / `meteor` / `wave` / `query` / `wxset` / `callfunc` 分支用 **6 位有效数字**（`2.73764e+08`） | **统一定点 2 位小数**（`273764105.56`） | ✅ **不需要**（现在任意分支都可算倒计时） |
| 2 | `worldTimeSource` | 仅 `actor` / `meteor` 有 | **`actor` / `scan` / `types` / `meteor` / `wave` / `query` / `callfunc` / `wxset` 共 8 类分支都有**；`weather` / `zones` / `biometemps` / `levels` **仍不带**（其 `worldTime` 本来就秒级） | ✅ 可选：用它统一判断时钟来源 |

- **无字段删除、无键改名、无行为破坏** ⇒ 前端可**无感升级**，不需同步改版。

### 9.2 兼容矩阵（前端可同时兼容两版）

| 需求 | v120b 及更早 | v121 |
|---|---|---|
| 秒级世界钟 | 只能取 `weather.worldTime`（`actor` 分支 ±500 s） | 任意分支均可 |
| `worldTimeSource` | 仅 `actor` / `meteor` | 8 类直出分支都有（`weather` 类分支仍不带，无需判别） |
| 火山倒计时 | 用 `weather.worldTime` 与 `TimeNextVolcanoEvent` 相减（跨两条响应） | 可用任一条响应内自洽相减 |
| 陨石 `phase` / `volumeTrend` | v118+ 已有 ✓ | ✓ |

**推荐写法（两版通用）**：世界钟取 **`weather` 响应里的 `worldTime`**（永远是秒级）；
响应里如果有 `worldTimeSource` 则仅作日志/自检用。

### 9.3 部署状态（**历史：五服阶段**）—— ✅ **2026-10-05 23:52 五服已全部上线 v121 并实测验证通过**

> 本节为 v121 时段的原始验证记录（保留原文）。**当前全服状态**见 §12.5 与顶部修订行。

| 服 | 端口 | 实测 `build` | `actor` 分支 `worldTime` | `worldTimeSource` | 双钟偏差 |
|---|---:|---|---|---|---|
| Sco | 32321 | `Oct  5 2026 23:38:11` | `273764769.57` | `gamedouble` | 1.50 s |
| Abe | 32323 | 同上 | `260723027.90` | `gamedouble` | 1.42 s |
| Ext | 32324 | 同上 | `251768041.83` | `gamedouble` | — |
| Rag | 32326 | 同上 | `238406517.81` | `gamedouble` | 1.69 s |
| Gen | 32329 | 同上 | `207608624.78` | `gamedouble` | — |

- ✅ **验证结论**：五服 `build` 均为 v121；`actor` / `scan` 分支世界钟 **均为完整秒级**（不再是 `2.73764e+08`）；
  `|actor − weather|` ≈ **1.4~1.7 s**（正好等于两次 RCON 调用的间隔）⇒ **两处钟口径一致**。
- 🎯 **版本判别（前端/脚本可用）**：`DinoMutPing.build` → v121 = `Oct  5 2026 23:38:11`；
  v120b = `Oct  5 2026 22:47:44`。dll 体积：v121 = **1,797,632 B**（v120b = 1,795,072 B）。
- 📌 **历史（最小部署集参考）**：若将来只升部分服，优先级是 **Rag（必）> Ext / Gen（推荐）> Sco / Abe（可缓）**；
  未升级的服**接口字段完全一致**，仅需按 §9.2 取钟即可。

### 9.4 尚未实现（v122 backlog，前端请勿依赖）

① `FloatCurve` 键值读取（解 `C_EXT_BadWeatherWegiht` ⇒ Ext 实时概率的动态修正因子）；
② `weatherState` 派生 `heatWaveActive`（= `currentWeatherId == 4`）；
③ 事件到达检测（Abe `bEarthQuake` 0↔1、Gen 月球 `TimeLastEvent` 变化）。

### 9.5 🆕 v122 —— `slim=1` 白名单视图 + `weatherState.heatWaveActive`（2026-10-06 00:31 构建，**待部署**）

> dll：`TransferIdentityFixAPI.dll` = **1,808,896 B**（v122b `01:22:47` / v122b2 `01:50:26`；v122 = 1,800,192 B；v121 = 1,797,632 B）；编译戳以 `DinoMutPing.build` 为准。

**变更 1：`slim=1`（新增参数，默认关闭 ⇒ 不加即与 v121 输出完全一致）**

| 命令 | `slim=1` 去掉的内容 | 保留 |
|---|---|---|
| `weather ... slim=1` | `dump[]`（Gen 83 KB / Abe 24 KB / Ext 10 KB）、`fields[]`（4.6~5.0 KB）、`wxSemantics.settingsRaw`、`wxSemantics.settingsScan[]`、`wxSemantics.arrayProbe.rawSlots` / `stride8·16·24·32`、`wxSemantics.payloadProbe`、`cloud`（与 `wxSystems` 互为镜像）、`weatherActorDetails[]` | `weatherState`（含新增 `heatWaveActive`）、`wxSystems[]`、`wxSemantics.presetTable` / `sandstorm` / `electricalStorm` / `extWeather` / `enumIndices`、`regionMap`、`actors[]` |
| `actor ... props=1 slim=1` | 白名单之外的全部属性 | 白名单字段（`actorProps.props` 只含白名单项） |
| `actor ... props=1 fields=A,B,C` | 同上（显式白名单，优先级最高） | 指定字段（`+` 代空格）；⚠️ **v122b 及更早：`fields=` 必须与 `slim=1` 同用**，否则不裁剪（实测 Gen `fields=TimeLastEvent,ActualTimeBetweenEvents` 返回全量 224 项 / 10,810 B）；**v122b2（`01:50:26`）起可单独用** |

- `slim=1` **不带 `fields=`** 时按 `filter=` 关键字套内置白名单：

| `filter=` 关键字 | 内置白名单字段 |
|---|---|
| `LunarMeteor` | `TimeLastEvent` · `ActualTimeBetweenEvents` · `MinTimeBetweenEvents` · `MaxTimeBetweenEvents` · `DurationOfEvent` · `CurrentStormRotation` · `ParticleIntensity` · `BackgroundMeteorEmitter` |
| `Volcano` | `VolcanoActive` · `VolcanoStarting` · `VolcanoEnding` · `WorldVolcanicIntensity` · `LocalVolcanicIntensity` · `TimeNextVolcanoEvent` · `TimeVolcanoEventStarted` · `TimeVolcanoEventEnds` · `VolcanoEventLength` · `LavaEnabled` · `ActorsInLava` |
| `Earthquake` | `bEarthQuake` |
| **`Avalanche`（🆕 v122b4）** | `ActivationChance` · `CurrentActivationChance` · `ActivationIncrement` · `MinTimeBetweenActivations` · `MinWarningInterval` · `MaxWarningInterval` · `WarningTimer` · `Bounds` · `SlideSpeed` · `ProjectileTimer` · `LastActivationTime` |
| `Weather` | `bMeteorFXActive` · `MeteorVolume` · `FinalMeteorVolume` · `bInWeatherTransition` · `TimerNextWeather` · `CurrentWeather` · `NextWeather` · `PrevWeather` · `WeatherTransitionTimeElapsed` · `WeatherTransitionTimeMin` · `WeatherTransitionTimeMax` · `WeatherChances` · `GoodWeathersSinceBad` |
| 其它 | **不裁剪**（保持全量输出，避免误得空集） |

- ⚠️ **安全兜底**：`slim=1` 遇到未列入内置表的 `filter=` 时**等价于不裁剪**，不会返回空属性集。
- ⚠️ **`fields=` 显式白名单的四个坑**（前端务必知）：① 字段名须与属性名**逐字一致**（拼错 ⇒ 该项不出现，且**不会**回退全量）；② **v122b 及更早：`fields=` 必须与 `slim=1` 同用**，否则静默返回全量；③ **v122b2 `01:50:26` 起**：坑 ② 已修（可单独用）；④ **若该图没有目标 actor**（如 Isl / Sco 无 `LunarMeteorController` / `WeatherSystem`）⇒ 返回 `matched:0` / `actors:[]`，**这是正常情况、不是错误**（实测 151 B）。✅ **跨版本安全写法：统一写 `... props=1 slim=1 fields=A,B`（两版行为一致）**。
- 📊 **实测体积（2026-10-06 01:4x，v122b `01:22:47` 全服回归）**：`weather slim=1` 降幅 **51.1%~93.6%**（Sco 25,529→12,482 / 51.1%，Isl 31,182→2,522 / 91.9%，Cen 50,243→11,561 / 77.0%，Gen 90,129→5,732 / 93.6%，Ext 16,529→2,963 / 82.1%）；`actor props=1 slim=1` 降幅 **90.3%~93.8%**（Rag `VolcanoManager` 10,623→**1,033** B / 11 项，Gen `LunarMeteorController` 10,810→**981** B / 8 项，Abe `Earthquake` 10,257→**631** B / 1 项，Ext `WeatherSystem` 12,049→**1,159** B / 13 项 —— **字段全部落在内置白名单内，无越界**）；`slim=1 fields=TimeLastEvent,ActualTimeBetweenEvents` = **720 B / 恰好 2 项**。

#### 9.5.0 ⚠️ 部署注意（历史记录：v122-hotfix → **已由 v122b 修复并经全服回归确认**）

- 🔴 **`00:30:33` 构建的 `actor ... slim=1` / `fields=` 无效**（`actor` 分支当时只解析前 4 个 token，第 5 个之后的参数被丢弃）—— 实测证据：`actor filter=VolcanoManager props=1 propsIdx=0 top=1 slim=1` 与不加 `slim` **同为 10,623 B**，属性未裁剪。
- ✅ **`weather ... slim=1` 不受影响**（该分支一直扫描完整参数串）：10/10 服实测降幅 **52%~93%**（Isl 91.9%／Sco 52.1%／Cen 77.0%／Abe 87.6%／Ext 82.1%／Ast 89.8%／Rag 90.2%／Val 90.6%／Los 89.2%／Gen 93.2%）。
- ✅ **修复版 `01:00:29`**：改为扫描完整参数串，`slim=1` / `fields=` 位置不再受限（最多仍受 6 token 上限影响，但参数顺序自由）。
- 📌 **行动项（已完成）**：前端若要用 `actor ... slim=1`，先 `DinoMutPing` 确认 `build = Oct  6 2026 01:22:47`（v122b 起已全部生效）。
- ✅ **2026-10-06 01:4x 全服回归（v122b `01:22:47`）**：`actor slim=1` 在 Rag / Gen / Abe / Ext 四图**全部生效**且字段全在白名单内 ⇒ `00:30:33` 缺陷已闭环。
- 🆕 **v122b 遗留的两点（v122b2 `01:50:26` 已修）**：① `fields=` **单独使用**时不裁剪（须与 `slim=1` 同用；同用时正常，实测 720 B / 2 项）⇒ v122b2 起单独可用；② 无曲线驱动的图 `badwx.factor` 报最小值（Ast 实测 0.1，误导）⇒ v122b2 起返回 `null` + `reason`。
- ✅ **两点已于 2026-10-06 02:2x 全服实测闭环**（重启后逐服验证）：① Gen `fields=` 单独用 = **720 B / 2 项**（Isl / Sco 返回 `matched:0`，因该图无此 actor，属正常）；② Ast / Rag / Val / Los / Gen **5/5 均返回 `factor:null` + `reason`**，Ext 仍为正确的 `0.8`。

#### 9.5.1 精简掉的字段清单（**逐键同步给前端**）

> 用途：前端据此确认「切到 `slim=1` 后哪些键会消失」。**未列出的键一律保留。**

**A. `weather ... slim=1` 会消失的键**

| # | 消失的键（JSON 路径） | 含义 | 替代做法 |
|---:|---|---|---|
| 1 | `dumpSkip` · `dumpCount` · `dump[]` | 全部天气 actor 的原始属性转储（`dump[i].{class,probedProperties,totalMatched,fields[]}`） | 需要单个 actor 时用 `allprops=N` |
| 2 | `fields[]` | 天气 actor 字段表（`{name,size,value,unreadable}`） | 定点解码用 `probe=` |
| 3 | `weatherActorDetails[]` | 每个天气类名 + 实例数 | `weatherActorClasses` / `weatherActors[]` **保留** |
| 4 | `wxSemantics.settingsRaw` | 80 B 原始 hex 块 | 无 |
| 5 | `wxSemantics.settingsScan[]` | 指针扫描结果（`off` / `arrayNum` / `arrayMax` / `objects[]`） | `wxSemantics.presetTable` **保留** |
| 6 | `wxSemantics.arrayProbe.rawSlots[]` | 原始 8 字节槽 hex | 无 |
| 7 | `wxSemantics.arrayProbe.stride8[] · stride16[] · stride24[] · stride32[]` | 四种步长重扫的候选对象 | 正解在 `arrayProbe.presetTable[]` **保留** |
| 8 | `wxSemantics.payloadProbe{ ElectricalStormRegionName · SandstormSweepSequenceNS · SandstormSweepSequenceWE · CurrentSandstormSweepSequence · SweepFrontierCurve }` | 5 个不可读槽的原始载荷探针 | 有效值走 `scopeProbe` / `probe=` |
| 9 | **`cloud`（整块）**：`cloud.count` · `cloud.regions[]` · `cloud.localtime[]` · `cloud.activeIdx` | 与 `wxSystems[]` **互为镜像** | **`wxSystems[]` 保留**（前端本就按 `miniMapType` 读） |

**B. `actor ... props=1 slim=1` 会消失的键**

| 情况 | 行为 |
|---|---|
| 给了 `fields=A,B,C` | 只消失 `actorProps.props[]` 中**不在 A,B,C 里**的条目 |
| 只给 `slim=1` | 按 `filter=` 关键字套内置白名单（见 9.5 表），其余条目消失 |
| `filter=` 不含任何内置关键字 | **不裁剪**（原样输出，安全兜底） |
| 其它键 | **全部保留**：`ok` / `sub` / `filter` / `worldTime` / `worldTimeSource` / `matched` / `returned` / `actors[]` / `propsIdx` / `matchedTotal` / `actorProps.{class,objectName,propsTotal,nonZero,readable,unreadable,engineSkipped,filtered}`（被裁掉的属性计入 `engineSkipped`） |

**C. `weather` 在 slim 下**一定保留**的键**

`ok` · `sub` · `target` · `confidence` · `worldTime` · `worldTimeSource` · `semSource` · `hasLoc` · `x/y/z` · `full` · `weatherActorCount` · `activeWxIdx` · `regionMap` · `regionMapAgent` · `actors[]` · `weatherActorClasses` · `weatherActors[]` · `probedProperties` · `matched` · `note` · `wxSystemsNote` · **`weatherState.*`（含新增 `heatWaveActive`）** · **`wxSystems[]`（完整）** · `wxSemantics.{defaultWeather, weightsDay, weightsNight, eventLengths, presetTableSource, presetTable, arrayProbe.{num, elementSize, presetTable}, electricalStorm, sandstorm, extWeather, enumIndices}`

**变更 2：`weatherState.heatWaveActive`（派生键，统一口径）**

- `1` = 热浪生效（= `currentWeatherId == 4`）；`0` = 否。
- 仅当 `currentWeatherId` 可读时输出（Abe 无天气 id ⇒ 不出现该键）。
- 口径：UDS `HeatWave_SE` 与 GEN `WeatherPreset_GEN_Ocean_Heatwave` **同为 id 4** ⇒ 前端可跨图统一判定。

**变更 3：未做项（明确记录）**

- `FloatCurve` 键值读取（Ext `C_EXT_BadWeatherWegiht`）⇒ 归 **v122b**（需先做内存布局探测）。
- 事件到达检测 ⇒ **不做**（RCON 只能拉不能推；前端 1~3 s 轮询 `meteor`，响应仅 333 B）。

## 10. 速查表（命令 → 字段 → 判据）—— **单一真源**

| 目的 | 命令（前缀 `TransferIdentityFix.`） | 关键字段 | 判据 / 口径 | 详见 |
|---|---|---|---|---|
| Sco 天气 + 三事件 | `WorldProbe weather full=1 limit=1` | `weatherState.currentWeatherId`；`wxSemantics.sandstorm.active`；`electricalStorm.regionNameProbe.asString` | 雷暴 `==7`；沙尘暴 `active==true`；热浪 `==4`；区域名走 `scopeProbe` | §1.4 / §1.12 / §1.13 |
| Sco 概率（日/夜） | `WorldProbe actor filter=UDS_SE_Weather props=1 probe=WeatherWeights_Day,WeatherWeights_Night,WeatherEventLengths top=1` | `asArray.dataHex`（v119+） | 下标 = `arrayProbe.presetTable` 顺序；**必须分昼夜** | Sco §1.x 权重表 |
| Sco 强制切天气（测试） | `callfunc fn=MC_ChangeWeather p.New+Weather+Type=<id> p.Transition+Length=30 p.Reset+Particle+Emitters=1 apply=1` | 回包 `verify[]` | `fnIdx=18`；不带 `apply=1` = 预演 | Sco §1.9 / §1.13 |
| Ext 陨石（推荐） | `WorldProbe meteor` | `phase` / `inMeteorShower` / `warn` / `volumeTrend` / `volume` / `secondsUntilChange` | `phase ∈ {incoming, active}` ⇒ 弹；`leaving`/`none` ⇒ 不弹 | §3.7.1 |
| Ext 强制触发（测试） | `callfunc filter=EXT_WeatherSystem fn=WeatherChange fnIdx=2 p.Weather=6 p.TransitionTime=40 apply=1` | — | **`fnIdx=2` 必须带**；停止用 `p.Weather=1` | §3.7.2 |
| Ext 概率 | `WorldProbe actor filter=EXT_WeatherSystem props=1 probe=WeatherChances,PossibleWeatherChances top=1` | `asArray.dataHex` | 下标 = 天气 id（0/4 未定义）；归一化 = 概率 | §3.8 |
| Rag 火山状态 | `WorldProbe actor filter=VolcanoManager props=1 propsIdx=0` | `VolcanoActive` / `Starting` / `Ending` / `WorldVolcanicIntensity` / `TimeNextVolcanoEvent` | `Active=1` 喷发中；`Intensity≥0.75` 岩浆 | §4.2 / §4.5 |
| Rag 火山倒计时 | 同上（配世界钟） | `TimeNextVolcanoEvent` | `ETA = Tnext − worldClock`；`Tnext=0` ⇒ 未排期 | §4.5.1 / §4.5.6 |
| Rag 控制三键 | `callfunc filter=VolcanoManager fn={StartVolcanoEvent\|ForceEndVolcano\|SetNextVolcanoTime} fnIdx=0 apply=1` | — | 全部零参数 | 附录 §4.5.7 |
| Gen 五图天气 | `WorldProbe weather full=1 limit=6 actors=1` | `wxSystems[].miniMapType` / `currentWeather` / `secondsUntilChange` | 按 `miniMapType` 匹配；`1000`+`beginAt<0` = 未运行 | §5.2 / §5.5 |
| Gen 月球流星雨 | `WorldProbe actor filter=LunarMeteorController props=1 propsIdx=0 top=1` | `TimeLastEvent` / `ActualTimeBetweenEvents` / `Min·MaxTimeBetweenEvents` / `DurationOfEvent` | `ETA = Last + Actual − worldClock`；⚠️ **空服不推进**（有玩家时已实测有效） | §5.5 / §5.5.1 |
| Gen 概率 | `actor filter=DayWeather_WeatherSystem props=1 propsIdx=<0..4> probe=WeatherPresetList,WeatherChances,PossibleWeatherChances top=1` | `asArray.objects` / `asArray.dataHex` | 只有**海洋图**有多样概率 | §3.9.1 |
| Abe 地震 | **不接** | — | ⛔ 只显示规律文案 | §0.1 / Abe §2.5 |
| 任意 actor 探针 | `WorldProbe actor filter=<类名子串> props=1 propsIdx=N top=K` | `actorProps.props[]` | **参数按 token 顺序解析**（`filter=` / `props=1` / `propsIdx=N` / `probe=` / `top=N` / `slim=1` / `fields=A,B`）；`+` = 空格 | 通用 §6 |
| **瘦身轮询（v122，推荐）** | 任意 `weather` / `actor` 命令**追加 `slim=1`**（`actor` 可再加 `fields=A,B,C`） | 同原命令 | 体积 ↓≈95%；**默认关闭** ⇒ 不加即 v121 原样 | §9.5 |
| **全服概率 / 可预测性** | 见 **§12**（10 服逐服权重+概率、可预测性总表、事件提前量） | — | 概率 = 权重归一化；「下一天气是谁」全图都拿不到 | §12 |
| 生物群落温度**热力图** | `WorldProbe biometemps brief=1 count=512`（`skip=` 分页） | `biomes[].{idx,name,temp,wind,actorX,actorY,actorZ}` + 头 `globalBase/globalWind` | `temp` 已是**绝对温度**；坐标=体积锚点；刷新 ≥ 5 min | §11.1 |
| **特殊区域天气**（Isl/Cen） | `WorldProbe zones fresh=1` | `zones[].{weather.typeIndex,temperature.offset,wind,bounds.worldX/Y/Z+radius,meta}` | **Isl×4 / Cen×6**，其余图 `count=0`（正常）；球形区域可直接画 | §11.2 |
| 宽槽 / 数组 / 结构体 | 同上 + `probe=A,B,C`（**≤12 个**） | `asArray.dataHex`（v119+）/ `structFields[]`（v111+） | 大数走定点 2 位小数；蓝图字段名带 `_Index_GUID` 后缀需剪掉 | 通用 §6 / §8 |
| 读世界钟 | **`weather.worldTime`**（推荐） | `worldTime` / `worldTimeSource` | v120 及更早 `actor` 分支只有 6 位有效数字（±500 s） | 通用 §4.5.3 |
| CurveFloat 键值（Ext 实时概率） | 🔜 **v122 计划**（未实现） | — | 用于解 `C_EXT_BadWeatherWegiht` | §9.4 |

## 11. 🗺️ 两块地图图层数据（2026-10-06 全服实测）

### 11.1 生物群落温度**热力图**（`WorldProbe biometemps`）

```
TransferIdentityFix.WorldProbe biometemps brief=1 count=512
TransferIdentityFix.WorldProbe biometemps brief=1 filter=Volcano      # 单区点名
```

**语义**：每条 = 一个 `ABiomeZoneVolume`（生物群落体积）；`temp` 是**绝对温度**（已代入 `globalBase` 与群落公式），`actorX/Y/Z` 是**体积锚点坐标**（前端画点/热力图定位用）。

| 键 | 含义 | 上屏建议 |
|---|---|---|
| `biomes[].idx` | level 内 actor 下标（稳定键） | 图层要素 ID |
| `biomes[].name` | 群落名（部分资产自带 `??????` ⇒ 插件回退 `<unnamed#N>`） | 标签 |
| **`biomes[].temp`** | **绝对温度（°C）** —— 热力图上色主字段 | 颜色映射（冷蓝 / 热红） |
| `biomes[].wind` | 该群落风强度 | 副信息 |
| **`biomes[].actorX / actorY / actorZ`** | 体积锚点世界坐标 | 点位/标签定位 |
| `biomes[].priority` · `absMin/absMax` · `preMul/preExp/preAdd` · `above*/below*` · `finMul/finExp/finAdd` | 该群落的温度调参（**解释"为何这块更冷/更热"**） | 悬浮说明（`brief=1` 不返回） |
| 响应头 `globalBase` / `globalWind` / `day` / `dayTime` / `worldSec` / `worldTime` | 公式输入 + 世界钟 | 图例「基准温度」 |
| 响应头 `count` / `seen` / `failed` | 本次条数 / 全图命中总数 / 读取失败数 | 分页与健康度 |

**全服群落区实测数量（2026-10-06，`brief=1 count=64`）**

| 服 | Isl | Sco | Cen | Abe | Ext | Ast | Rag | Val | Los | Gen |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 总区数 | **9** | **390** | **130** | **47** | **171** | **10** | **457** | **83** | **174** | **530** |
| 64 条体积 | 1.2 KB | 7.5 KB | 7.2 KB | 5.3 KB | 7.0 KB | 1.4 KB | 7.5 KB | 7.3 KB | 7.5 KB | 7.5 KB |

- 🔴 **必须分页/放大上限**：默认 `count=64`、**上限 512**；Sco(390)、Rag(457)、**Gen(530)** 超限 ⇒ Gen 用 `skip=512 count=512` 补一次（或 `filter=<区名>` 精确取）。
- 🔴 **刷新频率建议 ≥ 5 分钟**（温度随昼夜/天气缓慢变化）：全量 `brief=1 count=512` 约 **60 KB**（按 64 条 7.5 KB 线性估算）⇒ **不要放进秒级轮询**。
- ✅ `brief=1` = 热力图专用视图（只回 `idx/name/temp/wind/actorX/Y/Z`），体积约为全量 1/4。
- ⚠️ `biometemps` **暂不支持 `slim=1`**（它自身即精简视图；全量才带调参）。

**实测样例（极端温度印证数据有效）**

| 服 | 群落样例（name = temp / wind） |
|---|---|
| Isl | `<unnamed#521>` = **45.0** ／ `<unnamed#1120>` = **-20.0** ／ `Lava Cave` = 42.0 ／ `Cave` = 13.0 |
| Sco | `Northern High Desert` = **70.0**（最热）／ `Central Dunes` = 67.8 ／ `Northern Mountains` = 61.4（风 350）／ `Northern West Oasis` = 30.0 |
| Abe | `The Fallen Nexus` = 28.0 ／ `Mushroom Forest` = 24.0 ／ `The Spine` = 10.0 |
| Los | `Crater Hot-Springs` = 18.0 ／ `The Frozen Eye` = **-10.0** ／ `The Aberrant Spread` = 5.0 |
| Gen | `The Freshwater Hollow` / `Windowpoint` = **26.4** ／ `Window's Grasp` = 20.4 |

### 11.2 Isl / Cen **特殊区域天气**（`WorldProbe zones`）

```
TransferIdentityFix.WorldProbe zones fresh=1      # 首次/换图后重建全图扫描
TransferIdentityFix.WorldProbe zones              # 缓存读取（天气字段每次仍重读）
```

**实测覆盖（2026-10-06 全服）**：**Isl ×4 区**、**Cen ×6 区**；其余 8 图 `count=0`（无覆盖体积）。

| 字段 | 含义 | 上屏建议 |
|---|---|---|
| `zones[].class` | `Weather_Override_Volume_C` | — |
| **`zones[].weather.typeIndex`** | **该区域强制的天气 id**（`0` 多为默认/无覆盖） | 用本图 `wxSemantics.presetTable` 转名称后显示 |
| `zones[].weather.transitioning` / `transitionTimeRemaining` | 是否过渡中 / 剩余秒 | 过渡动画 |
| `zones[].temperature.offset` | 区域温度偏移 | 副信息 |
| `zones[].wind.direction` / `wind.apply` | 风向（度）/ 是否应用 | 风向箭头 |
| `zones[].meta.{priority, volumeAlpha, transitionWidth, scaledTransitionWidth, mode, started, globalRainInfluenceOnClouds}` | 生效范围/过渡宽度/优先级 | 悬浮说明 |
| **`zones[].bounds.{worldX, worldY, worldZ, radius}`** | **球心世界坐标 + 半径** | **直接画圆/球**（`radius` 取自 `Total Sphere Bounds`） |
| `zones[].bounds.{x,y,z,actorX,actorY,actorZ,centerField,radiusField}` | 本地点 + actor 锚点 + 取值字段名（自检） | 调试 |
| 响应头 `count` / `cached` / `scanAge` / `live` / `note` | 区域数 / 是否缓存 / 扫描年龄 | 刷新策略判断 |

- 🔴 **不要用主天气表推区域天气**：区域体积是**独立**一套（主表=整图基准；覆盖体积=局部例外）。
- 🔴 `Sco` 的 `zones` 实测 `count=0` 属**正常**（该图无覆盖体积），不要当报错。
- 体积参考：Isl **13.7 KB** / Cen **20.4 KB**；建议 `fresh=1` 仅在启动/换图后调用一次。

## 12. 全服天气事件与概率 + 可预测性总表（前端单文件版）

> 本节由独立文档 `天气事件与概率总表_20261006.md` **并入**（该文件保留为留档快照）；前端只需看本文件。

> 生成时间：2026-10-06（**v2 修正版**：权重严格按 `asArray.num` 切片）
> 数据来源：本机对实服 RCON 的真实响应（原始 JSON：`tmp\_v122_raw\*.json`）
> 插件版本：**v122**（全服已投放，`build = Oct  6 2026 00:30:33`；`actor slim` 修复版为 `01:00:29`，详见 §4）
> 口径：**概率 = 该槽权重 ÷ 同组正权重之和**；UDS 家族**必须分昼夜**，ext_gen 家族用当前 `WeatherChances`（本身已是动态值）

#### 12.1 可预测性总表（先看这张）

| 服 | 端口 | 家族 | 天气概率表 | **下一天气能提前知道吗** | 事件型内容 | **事件能否精确预测** |
|---|---:|---|---|:---:|---|---|
| **Bob** | 32319 | — | ❌ **端口无响应** | — | — | — |
| **Isl** | 32320 | UDS | ✅ 5 槽日/夜 | ❌ 只能给概率 | 区域天气 `Weather_Override_Volume_C` | ⚠️ 走 `WorldProbe zones`（区域名+天气） |
| **Sco** | 32321 | UDS | ✅ 8 槽日/夜 | ❌ 只能给概率 | 雷暴/沙尘暴/热浪/焚风 | ✅ **秒级判据**（无预兆） |
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

#### 12.2 逐服天气概率（真实权重 + 归一化概率）

#### Isl（32320）—— 家族 `uds`，名称表 `WeatherPresetList`（6 条）

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

#### Sco（32321）—— 家族 `uds`，名称表 `WeatherPresetList`（8 条）

| i | 天气（名称表） | 白天 权重 → 概率 | 夜晚 权重 → 概率 | 单次时长 |
|---:|---|---:|---:|---:|
| 0 | ColdFront_SE（id 5） | `0` → **0.0%** | `0.5` → **29.4%** | 800 s |
| 1 | ElectricalStorm（id 7） | `0.1` → **4.5%** | `0.2` → **11.8%** | 425 s |
| 2 | Rain_SE（id 2） | `0.35` → **15.9%** | `0.1` → **5.9%** | 750 s |
| 3 | Foggy_SE（id 3） | `0.15` → **6.8%** | `0.2` → **11.8%** | 650 s |
| 4 | HeatWave_SE（id 4） | `0.7` → **31.8%** | `0` → **0.0%** | 700 s |
| 5 | Clear_Skies_SE（id 0） | `0.5` → **22.7%** | `0.5` → **29.4%** | 1200 s |
| 6 | Sand_Dust_Storm（id 6） | `0.25` → **11.4%** | `0.2` → **11.8%** | 425 s |
| 7 | Superheat（id 8，焚风） | `0.15` → **6.8%** | `0` → **0.0%** | 750 s |

- 原始权重：`Day = [0.0, 0.1, 0.35, 0.15, 0.7, 0.5, 0.25, 0.15]`；`Night = [0.5, 0.2, 0.1, 0.2, 0.0, 0.5, 0.2, 0.0]`；`Lengths = [800.0, 425.0, 750.0, 650.0, 700.0, 1200.0, 425.0, 750.0]`
- 🔴 **必须分昼夜**；`i` = 预设表顺序下标（非天气 id）
- 备注：`dataHex` 固定返回 128 B（16 槽），**有效槽数 = `asArray.num`**，其后为相邻数组内存（已按 num 切片剔除）

#### Cen（32322）—— 家族 `uds`，名称表 `WeatherPresetList`（6 条）

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

#### Abe（32323）—— 家族 `ab`，名称表 `WeatherPresetList`（0 条）

- ❌ **无权重表**：`WeatherWeights_Day/Night` 与 `WeatherChances` 全为 `null`（Abe 家族未接名称/权重槽）
- ⇒ Abe 天气**只有 id 可读**（`currentWeather` = null）⇒ **无概率可算**；地震见 §2.4

#### Ext（32324）—— 家族 `ext_gen`，名称表 `WeatherPresetList`（5 条）

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
- 🔴 权重随 `GoodWeathersSinceBad` 经曲线 `C_EXT_BadWeatherWegiht` 动态变化 ⇒ **每次按当前 `WeatherChances` 归一化，勿写死**（曲线点待 v122b）

#### Ast（32325）—— 家族 `ext_gen`，名称表 `WeatherPresetList`（7 条）

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

#### Rag（32326）—— 家族 `ext_gen`，名称表 `WeatherPresetList`（6 条）

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

#### Val（32327）—— 家族 `ext_gen`，名称表 `WeatherPresetList`（4 条）

| 槽位 | 天气名（按预设表顺序对齐） | 权重 | 概率 | 基准权重 |
|---:|---|---:|---:|---:|
| 0 | WeatherPreset_VAL_ClearSky | `1` | **64.5%** | `0` |
| 1 | WeatherPreset_VAL_Fog | `0.2` | **12.9%** | `1` |
| 2 | WeatherPreset_VAL_Rain | `0.2` | **12.9%** | `1` |
| 3 | WeatherPreset_VAL_ElectricalStorm | `0.15` | **9.7%** | `1` |

- 权重原始：`[1.0, 0.2, 0.2, 0.15]`（槽数 `num=4`）
- 名称表：id 13568744=WeatherPreset_VAL_ClearSky；id 5352204=WeatherPreset_VAL_Fog；id 9247411=WeatherPreset_VAL_Rain；id 6876294=WeatherPreset_VAL_ElectricalStorm

#### Los（32328）—— 家族 `ext_gen`，名称表 `WeatherPresetList`（5 条）

| 槽位 | 天气名（按预设表顺序对齐） | 权重 | 概率 | 基准权重 |
|---:|---|---:|---:|---:|
| 0 | WeatherPreset_LC_ClearSkyV2 | `1` | **41.7%** | `0` |
| 1 | WeatherPreset_LC_ClearSkyV3 | `1` | **41.7%** | `1` |
| 2 | WeatherPreset_LC_SnowFluery | `0.2` | **8.3%** | `1` |
| 3 | WeatherPreset_LC_Blizzard | `0.2` | **8.3%** | `1` |
| 4 | WeatherPreset_LC_ClearSky | `0` | **0.0%** | `0` |

- 权重原始：`[1.0, 1.0, 0.2, 0.2, 0.0]`（槽数 `num=5`）
- 名称表：id 13517021=WeatherPreset_LC_ClearSkyV2；id 14576822=WeatherPreset_LC_ClearSkyV3；id 13912101=WeatherPreset_LC_SnowFluery；id 13742185=WeatherPreset_LC_Blizzard；id 15605184=WeatherPreset_LC_ClearSky

#### Gen（32329）—— 家族 `ext_gen`，名称表 `WeatherPresetList`（7 条）

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

#### 12.3 事件型内容

#### 2.1 Gen 月球流星雨（`LunarMeteorController_C`，全世界 1 个）

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

#### 2.2 Rag 火山（`BP_VolcanoManager_C`）

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

#### 2.3 Ext 陨石雨

- 天气 **id 6**（`WeatherPreset_EXT_MeteorRain`）；预兆 40~80 s；前端用 `WorldProbe meteor`（**770 B**），按 `phase ∈ {incoming, active}` 弹窗

#### 2.4 Abe 地震

- ❌ **不可预测**（208 属性无双筛计时/概率字段，无独立调度器）⇒ 前端只显示规律文案，不接字段

#### 2.5 Isl / Cen 特殊区域天气

- 实测 Isl 有 `Weather_Override_Volume_C`，**Cen 有 6 个** ⇒ 走 `WorldProbe zones fresh=1`（实测覆盖 Isl×4 / Cen×6，返回区域名 + 该区域天气）

#### 12.4 取数命令与实测体积

| 目的 | 命令（前缀 `TransferIdentityFix.`） | 实测体积 |
|---|---|---:|
| 某图天气语义 | `WorldProbe weather full=1 limit=1 slim=1` | Isl 2.5K／Sco 12.5K／Cen 11.6K／Abe 3.7K／Ext 3.0K／Ast 3.7K／Rag 3.6K／Val 3.4K／Los 3.4K／Gen 6.2K（**对比 full：52~93% 降幅**） |
| Gen 六图 | `WorldProbe weather full=1 limit=6 actors=1 slim=1` | 6.2 KB |
| UDS 权重（日/夜） | `actor filter=UDS_<地图>_Weather props=1 probe=WeatherWeights_Day,WeatherWeights_Night,WeatherEventLengths top=1` | ~21 KB（未 slim） |
| ext_gen 权重 | `actor filter=WeatherSystem props=1 propsIdx=0 probe=WeatherChances,PossibleWeatherChances top=1` | ~16 KB |
| Gen 五图权重 | `actor filter=DayWeather_WeatherSystem props=1 propsIdx=0..5 probe=WeatherPresetList,WeatherChances top=1` | ~18 KB |
| 陨石雨 | `WorldProbe meteor` | **0.77 KB** |
| 月球 / 火山 / 地震 | `actor filter=<LunarMeteorController / VolcanoManager / Earthquake> props=1 propsIdx=0 top=1`（加 `slim=1` 走白名单） | 实测 10.8K→**981 B** / 10.6K→**1,033 B** / 10.3K→**631 B**（−90.3~93.8%） |
| 区域天气（Isl/Cen） | `WorldProbe zones fresh=1` | 视区域数 |

#### 12.5 部署状态与 hotfix

- **全服**：`weather slim=1` ✅ 正常（10/10 服实测降幅 52~93%）；`weatherState.heatWaveActive` ✅ 在 Sco/Cen/Ext 出现（其余图 `currentWeatherId` 本身为 null ⇒ 按设计不输出）
- 🔴 **（历史，已闭环）`actor slim=1` / `fields=` 在 `00:30:33` 构建里未生效**（该分支只解析前 4 个 token，参数被丢弃；实测 `VolcanoManager` full=slim=10,623 B）
- ✅ **已修复并经全服回归确认（v122b `01:22:47`，2026-10-06 01:4x）**：改扫完整参数串 ⇒ `slim=1` / `fields=` 位置自由；四图实测降幅 **90.3%~93.8%**，字段全在白名单内。
- 🆕 **v122b 遗留两点（v122b2 `01:50:26` 修）**：`fields=` 单独用不裁剪（须配 `slim=1`）；无驱动图 `badwx.factor` = 误导最小值（Ast 0.1）。
- ✅ **全服升级与实测（2026-10-06 02:2x，重启后）**：版本普查 **10/10 = v122b2 `01:50:26`**；`fields=` 单独用（Gen 720 B / 2 项）✅；`badwx` 5/5 `factor:null` + `reason`、Ext `0.8` ✅；`actor slim` 回归 **Rag 1,033 / Gen 981 / Abe 631 / Ext 1,159 B**（与 v122b 一致）；`weather slim` 回归 **Sco 12,527 / Isl 2,517 / Cen 11,593 / Ext 2,963 / Gen 6,130 B**；`zones` **Isl 4 区 / Cen 6 区**、`biometemps` Gen/Sco 各 8 区 ✅。
- ✅ **热浪派生键抢测（2026-10-06 01:49）**：Sco 当时正处热浪 —— `weatherState.currentWeatherId = 4.0` 且 `heatWaveActive = 1`；**02:2x 复测 Sco `currentWeatherId = 2.0` ⇒ `heatWaveActive = 0`**（热浪已结束）⇒ 派生口径与 id 两次都完全一致，前端可放心用 `heatWaveActive` 判热浪（Cen / Ext 实测为 0；Isl / Gen `currentWeatherId` 为 null ⇒ 按设计不输出该键）。

### 12.6 🆕 坏天气权重因子（`WorldProbe badwx`，v122b）

```
TransferIdentityFix.WorldProbe badwx                        # 默认 filter=WeatherSystem
TransferIdentityFix.WorldProbe badwx filter=EXT_WeatherSystem
```

**它解决什么**：Ext / Ast / Rag / Val / Los / Gen 的坏天气（陨石雨等）权重会随「距上次坏天气连续过了几个好天」**动态下调**。此前只能看到**当前权重**，说不清"为什么是 17.4% 而不是 20%"。

**做法（关键）**：**不读曲线资产的内存**。曲线对象（Ext 为 `CurveFloat C_EXT_BadWeatherWegiht`，官方拼写如此）的 `FRichCurve` 键布局不在公开头文件、且逐引擎版本不同 —— 猜偏移正是本项目已封禁的失败模式。改成**派生**：

$$	ext{factor} = rac{	ext{WeatherChances}[i]}{	ext{PossibleWeatherChances}[i]}$$

`PossibleWeatherChances` 是**作者基准**（实测各图皆为 `[0,1,1,1,0,1,1]`），所以这个比值**就是曲线此刻施加的系数**（实测 Ext = **0.8**，即坏天气权重被压到 80%）。

| 键 | 含义 |
|---|---|
| `found` / `class` / `objectName` | 命中的天气 actor（无 `WeatherChances` ⇒ `found:0` + `reason`） |
| `sinceBad` | 曲线驱动量 `GoodWeathersSinceBad`（当前采样值；缺失为 `null`） |
| `slots[]` | 逐槽 `{i, current, base, ratio}`（`base=0` ⇒ `ratio:null`，不瞎算） |
| **`factor`** | 当前曲线系数（= 各槽 ratio 的最小值；无削减 ⇒ `1.0`）；🆕 **v122b `01:22:47` 及更早：无曲线驱动的图也报最小值（Ast 实测 0.1，误导）；v122b2 `01:50:26` 起该情形返回 `null` + `reason`** |
| `chanceSum` / `probsPct[]` | 当前权重和 / **归一化后的实时概率（已含因子，可直接上屏）** |
| **`learned[]`** | `{sinceBad, factor, samples, lastAt}` —— **随时间累积**的曲线采样表 ⇒ 曲线形状会自己浮现，可用于预测「再过 N 个好天，陨石雨概率会变成多少」 |
| `note` | 口径自述（派生方式） |

- ✅ **可保证的**：① 不访问未知内存（无崩溃/读错风险）；② `base` 缺失或为 0 时该槽返回 `null` 而非假数；③ 找不到属性时明确 `found:0` + 原因，绝不返回错的概率。
- ⚠️ **需要时间的**：`learned[]` 首次调用为空，只有服务器跑过若干次「好天→坏天」循环后才逐步填满（每个 `sinceBad` 值攒 `samples` 次）。在此之前，**当前 `factor` 与 `probsPct[]` 始终是精确的**（纯算术，来自两个实时数组）。
- 📉 体积很小（约 1 KB 量级）⇒ 可低频轮询（建议 ≥ 5 min，与热力图一致）。

**实测（2026-10-06 01:4x，v122b `01:22:47`）**

| 图 | 命中类 | `sinceBad` | `factor` | `probsPct[]`（7 槽） | `learned` |
|---|---|---|---|---|---|
| Ext | `BP_EXT_WeatherSystem_C` | `0` | **0.8** ✅（曲线存在，权重被压到 80%） | 0.0 / 21.7 / 21.7 / 17.4 / 0.0 / 21.7 / 17.4 | 1 条样本（响应 ≈ 885 B） |
| Ast | `BP_AST_DayWeather_WeatherSystem_C` | `null` | **`null`**（v122b2 起）+ `reason` | 34.5 / 20.7 / 13.8 / 20.7 / 3.4 / 3.4 / 3.4 | 0（无驱动则不学习，符合设计） |

**v122b2 实测复验（2026-10-06 02:2x，重启后）**：Ast / Rag / Val / Los / Gen **5/5 均返回 `factor:null` + `reason`**（响应 948~1,006 B）；Ext 仍为 **`0.8`**（885 B）。⛔ **v122b 及更早**：同一命令在这 5 服会返回固定的误导值（0 ~ 0.1）。

**逐服枚举：`badwx` 到底能用在哪些图（2026-10-06 01:58，10/10 服实测）**

| 服 | `found` | 命中类 | `sinceBad` | `factor` | 受影响（缺陷 2） |
|---|:---:|---|---|:---:|:---:|
| Isl | `0` | —（该图无 `WeatherChances` 属性） | — | — | — 命令不适用 |
| Sco | `0` | —（同上） | — | — | — 命令不适用 |
| Cen | `0` | —（同上） | — | — | — 命令不适用 |
| Abe | `0` | —（同上） | — | — | — 命令不适用 |
| **Ext** | `1` | `BP_EXT_WeatherSystem_C` | `0` | **0.8** | ✅ 否（有曲线驱动，值正确） |
| **Ast** | `1` | `BP_AST_DayWeather_WeatherSystem_C` | `null` | 0.1 ⚠️ | ⚠️ **是** |
| **Rag** | `1` | `BP_RAG_DayWeather_WeatherSystem_C` | `null` | 0 ⚠️ | ⚠️ **是** |
| **Val** | `1` | `BP_RAG_DayWeather_WeatherSystem_C`（**Val 复用 Rag 蓝图类**） | `null` | 0 ⚠️ | ⚠️ **是** |
| **Los** | `1` | `BP_LC_DayWeather_WeatherSystem_C` | `null` | 0 ⚠️ | ⚠️ **是** |
| **Gen** | `1` | `BP_GEN_DayWeather_WeatherSystem_C` | `null` | 0 ⚠️ | ⚠️ **是** |

- 🔴 **重点：无驱动图上的伪 `factor` 会"漂移"** —— 本轮实测 Rag / Val / Los / Gen = **`0`**，Ast = `0.1`（v122b 及更早）。`factor:0` 若被上屏，含义会变成"坏天气权重被压到 **0%**"（看起来像"坏天气被禁用"），**比 0.1 更误导**；而同一响应里的 `probsPct[]` 始终精确（Ast 实测 34.5 / 20.7 / 13.8 / 20.7 / 3.4 / 3.4 / 3.4）。
- ✅ **前端判据（跨版本安全）**：`sinceBad` 为 `null` ⇒ **不要读 `factor`**，直接用 `probsPct[]`（该数组始终精确，纯算术来自两个实时数组）。
- ✅ **前端屏蔽写法（任意版本都安全）**：`const f = (data.sinceBad === null) ? null : data.factor;` —— 这样即使线上仍是 v122b，5 服也不会显示假数字。
- 📌 **`badwx` 可用范围一句话**：**6/10 服有该属性**（Ext / Ast / Rag / Val / Los / Gen），其中**只有 Ext 的 `factor` 有意义**；Isl / Sco / Cen / Abe 返回 `found:0`（改用 `weather` + `probsPct` 那条线取概率）。


---

## 13. 🆕 机制分析（三问：Rag 沙尘暴 / Gen 雪崩 / Ext 王泰坦）

> 独立文件：`接口文档\机制分析_三问_Rag沙尘暴_Gen雪崩_Ext王泰坦_20261006.md`（前端副本：`WorldProbe_机制分析_三问_20261006.md`）

- **Rag 沙尘暴**：6 预设**全局掷骰**（沙尘暴 = 预设索引 **3**，实测实时概率 **7.32%** = 0.15 ÷ 2.05，每 `1500~2500 s` 掷一次、过渡 40~80 s）；**效果只在沙尘暴触发卷（沙漠）内生效** —— `BP_RAG_WeatherEffects_C` 的 `SandstormAmount` / `SandstormDebries` / **`bInSandstormTrigger`**（区域闸门）；无独立 Actor（`scan filter=Sand/Storm` = 0 命中）
- **Gen 雪崩**：**`HazardTrigger_Avalanche_C` × 51**（只布置在雪原）—— 进入触发卷即按 `CurrentActivationChance`（起始 **25%**，每次失败 **+5%**）掷骰，命中后先播 **10~15 s 预警**，再生成滑体（`SlideSpeed 750`、`Bounds 8000`），两次间隔 **≥180 s**；**Rag 无任何 hazard/雪崩触发器**（`scan filter=Hazard|Avalanche|Snow` 全 0）
- **Ext 王泰坦**：**两条通道**（首版漏了第二条，已更正）—— ① **荒地世界BOSS刷怪区** `NPCZoneManagerBlueprint_Land_WorldBoss_C`（实测仅 **Ext / Ast 各 1 个**；`bEnabled=1`、`MinTimeBetweenSpawns=4200 s`、`DespawnBossAfterTime=900 s`、玩家需在 `6000 uu` 内、`LastSpawnTime` 距实测时约 15 h）；② **禁区竞技场召唤** `BossArenaManager_FZ_C` + `TributeTerminal_FZ_C`（`SummonCooldown=21600 s`）。当下 **0 个 Titan 实例**（只有两面形态旗 `Flag_SM_KingTitan_C` / `...Mecha_C`；`bBossSpawned=0`）


---

## 14. 🆕 Rag 沙尘暴接入（v122b3 新增命令 `WorldProbe sandstorm`）

> ✅ **部署状态（2026-10-06 13:11 实服实测）**：**Rag 已覆盖并通过验证** —— `DinoMutPing.build == Oct  6 2026 12:58:34`、盘面 dll `1,821,696 B @ 12:59:09`、`sandstorm` 响应 **2,006 B**，实测明细见 **§14.5**。
> ⚠️ **其余图尚未覆盖**（Isl / Sco / Cen / Abe / Ext / Ast / Val / Los / Gen）⇒ 在那些图调用 `sandstorm` 前，请先确认该图 `build` 也是 `Oct  6 2026 12:58:34`（旧版不认该子命令，只会回“未知子命令”）。
> **dll**：`TransferIdentityFixAPI.dll` = **1,821,696 B @ 2026-10-06 12:59:09**（编译戳 **`Oct  6 2026 12:58:34`**）
> 📌 **与 §15 是同一个 dll**：v122b3（沙尘暴命令）与 v122b4（雪崩白名单）已合成一个文件，**一次覆盖两项同时生效**（自动重载 5 s，无需重启）。
> **只读命令**，默认无参数；响应约 **1~2 KB**，可 30~60 s 轮询（与热力图同频）。

```
TransferIdentityFix.WorldProbe sandstorm
```

### 14.1 为什么是三层结构（机制决定，不是设计偏好）

Rag 的沙尘暴**不是独立 Actor**，也不是 Scorched Earth 那种"尘墙扫图"（`scan filter=Sand` / `Storm` = 0 命中；`wxSemantics.sandstorm` 在 Rag 为 `null`）。真实机制是：

1. **掷骰层** `BP_RAG_DayWeather_WeatherSystem_C`：6 个预设里抽一个，沙尘暴 = **索引 3**（`WeatherPreset_RAG_Sandstorm`）
2. **区域层** `BP_RAG_DayWeather_Agent_C`：4 个区域权重（`SeqWeight_Region0..3`）+ 区域昼夜实例（`RegionTOD_Region0..3`）
3. **效果层** `BP_RAG_WeatherEffects_C`：**`bInSandstormTrigger`**（区域闸门）+ `SandstormAmount`（强度）

⇒ 所以"沙尘暴只在沙漠"= **全局抽中了沙尘暴 + 效果层只在触发卷（沙漠）内生效**，而不是"沙漠区域自己有一套天气"。

### 14.2 响应字段

| 键 | 含义 | 备注 |
|---|---|---|
| `supported` | 1 = 本图有沙尘暴机制（找到掷骰层或效果层） | 其它图可能为 0 |
| `layers.roll/region/effect` | 三层各自的 `found` + `class` | 某层缺失 ⇒ `found:0`、`class:null`（**不是错误**） |
| `presetTable.entries[]` | `{i, id, name}` —— 6 个预设（idx3 = Sandstorm） | 从 `WeatherPresetList` 实读 |
| `sandstormPreset` | `{index, name}` | 沙尘暴预设下标（Rag 实测 **3**） |
| `weights.sandstormPct` | **沙尘暴实时概率（%）** | = `WeatherChances[3] ÷ Σ正值`（Rag 实测 **7.317**） |
| `weights.chanceSum` / `probsPct[]` / `slots[]` | 权重和 / 全部预设的归一化概率 / 逐槽 `{i,current,base,ratio}` | `base=0` ⇒ `ratio:null`（不瞎算） |
| `timer` | `changeMin/changeMax`（换天气间隔 s）、`nextAt`、**`secondsUntilChange`**、`inTransition`、`transitionDuration` | Rag 实测 1500~2500 s、过渡 40~80 s |
| `region.seqWeights[4]` | 4 个区域的序列权重 | Rag 实测 `[1,0,0,0]` |
| `region.todRegions[]` | `{region, hasActor, objectName}` | `hasActor=0` ⇒ 该区域无 TOD 实例（Rag 为 Region0/3 有、1/2 无） |
| `effect.sandstormAmount` / `sandstormDebries` | 沙尘暴强度 / 碎屑特效量 | >0 表示"正在刮" |
| **`effect.inSandstormTrigger`** | **是否处于沙尘暴触发卷内（区域闸门）** | 1 = 该位置真的在刮 |
| `effect.weatherOffInCave` / `snowAmount` / `rainAmount` | 洞穴关天气 / 雪 / 雨量 | 对照用 |
| `effect.sweepWeight` / `sweepSeqActor` / `sweepSeqPlayer` | 沙墙扫过序列 | 指针不可读时为 `null`（不猜） |
| **`active`** | **派生总开关**：`inSandstormTrigger=1` 或 `sandstormAmount>0` | 前端可直接用它判"正在沙尘暴" |
| `note` | 口径自述 | 便于排查 |

### 14.3 前端用法建议

| 需求 | 取法 |
|---|---|
| 展示"沙尘暴概率" | `weights.sandstormPct`（%），或 `weights.probsPct[3]` |
| 展示"下次换天气倒计时" | `timer.secondsUntilChange` |
| 展示"正在沙尘暴" | **`active === 1`**（区域相关；跨图安全） |
| 判断机制可用性 | `supported === 1`；某层 `found:0` 时**不要报警** |
| 未命中字段 | 一律 `null`（该图没有该属性），按 `null` 处理即可 |

- ⚠️ **Rag 的 id → 名称映射**：本命令的 `presetTable` 给出名称；`weatherState.currentWeatherId` 在 Rag **不可读**（`null`），所以**不要**用 id 判断当前天气，改用 `timer` + `active`。
- ⚠️ 该命令对**其它图**也会应答：没有对应类的图会返回 `supported:0` + 三层 `found:0`（例如 Isl / Sco），不会报错。

### 14.4 适用图范围（2026-10-06 全服实测，决定"哪些服要覆盖"）

| 图 | `WeatherEffects` | `DayWeather_*` | `sandstorm` 命令可用性 |
|---|---|---|---|
| Isl · Sco · Cen · Abe | ❌ 0 命中 | ❌ 0 命中 | ❌ `supported:0`（本图无此机制） |
| Ext | ❌ 0 命中 | ⚠️ 仅 `BP_EXT_DayWeatherAgent_C` | ⚠️ 仅 **region 层**可能命中（Ext 天气类名为 `BP_EXT_WeatherSystem_C`，不含 `DayWeather_WeatherSystem`） |
| **Rag** | ✅ `BP_RAG_WeatherEffects_C` | ✅ 全家桶（Agent / TOD×2 / Cloud / WeatherSystem） | ✅ **完整**：预设 idx3 = `WeatherPreset_RAG_Sandstorm` |
| **Val** | ✅ `BP_RAG_WeatherEffects_C` | ✅ 全家桶（**复用 RAG 类体系**） | ✅ 完整（同 Rag 类体系） |
| **Los** | ✅ `BP_LC_WeatherEffects_C` | ✅ 全家桶 | ✅ 完整 |
| **Ast** | ✅ `BP_AST_WeatherEffects_C` | ✅ 全家桶 | ✅ 完整 |
| **Gen** | ✅ `BP_GEN1_WeatherEffects_C` | ✅ 5 个 `WeatherSystem` | ✅ 可应答（但其预设表仅 `*_ClearSky` / `Lunar_MeteorShower` ⇒ **无 Sandstorm 预设**，`sandstormPreset.index` 为 -1） |

- 📌 **部署结论**：功能上**只有 Rag / Val / Los / Ast / Gen 有沙尘暴三层**；**Sco 不需要**（其沙尘暴是 Scorched-Earth 的"尘墙"机制，已由既有 `weather` → `wxSemantics.sandstorm` 提供，v122b2 即有）。若要保持全服版本一致，可一并覆盖其它图。
- ⚠️ `Ext` 的天气类体系（`BP_EXT_WeatherSystem_C`）不属 `DayWeather_*`，故 `sandstorm` 命令在 Ext 只可能命中 region 层 —— 需要 Ext 沙尘暴请继续用 `weather` 的 `wxSemantics`。


---

### 14.5 ✅ Rag 实服实测结果（2026-10-06 13:11，v122b4 已覆盖）

| 项 | 实测 |
|---|---|
| 盘面 dll | `1,821,696 B @ 2026-10-06 12:59:09` |
| `DinoMutPing.build` | **`Oct  6 2026 12:58:34`** ✅ |
| 响应体积 | **2,006 B** |
| `supported` | `1` |
| 三层 | roll `BP_RAG_DayWeather_WeatherSystem_C` ✅ · region `BP_RAG_DayWeather_Agent_C` ✅ · effect `BP_RAG_WeatherEffects_C` ✅（均 `found:1`） |
| `sandstormPreset` | `{"index": 3, "name": "WeatherPreset_RAG_Sandstorm"}` ✅ |
| `weights` | `chanceSum=2.05` · **`sandstormPct=7.31707`** · `probsPct=[48.7805, 9.7561, 17.0732, 7.31707, 9.7561, 7.31707]` |
| `timer` | `changeMin/Max=1500/2500` · `nextAt=238452130.04` · **`secondsUntilChange=1893.39`** · `inTransition=0` |
| `region` | `seqWeights=[1,0,0,0]`；`todRegions` Region0/3 `hasActor=1`、Region1/2 `hasActor=0` |
| `effect` | `sandstormAmount` · `sandstormDebries` · `inSandstormTrigger` · `weatherOffInCave` · `snowAmount` · `rainAmount` = **0**；`sweepWeight`/`sweepSeqActor`/`sweepSeqPlayer` = **null**（指针不可读 ⇒ 按 null 处理，**未猜值**） |
| `active` | `0`（当前无沙尘暴） |

**⚠️ 两个必知的坑（本次实测发现）**

1. **`slots[].base` / `ratio` 在服务器重启后短时间内可能是未初始化读数**
   - 12:19（重启后约 2 分钟）：`base` 与 `current` **完全相同**（0.2 / 0.35 / 0.15 …）
   - 13:11（稳定后）：`base = [0,1,1,1,0,1]`（作者基准），`ratio` 随之变为 0.2 / 0.35 / 0.15 / 0.15
   - ✅ **但 `current` 两次完全一致** ⇒ **`sandstormPct` / `probsPct[]` 两次都准确**；**前端只用这两个**，不要依赖 `base` / `ratio` 的绝对值
2. **`timer.transitionDuration` 不是“本次过渡长度”**：本次读 **10**，上一次读 **54.01**，而 `WeatherTransitionTimeMin/Max` 恒为 **40~80** ⇒ 该字段疑为残留/中间量；判过渡时长请用 **`WeatherTransitionTimeMin/Max`**（`weather` 响应的 `weatherState` 里也有）

**回归**：`weather slim=1`（3,550 B）、`badwx`（998 B / 7 slots）均正常。

---

## 15. 🆕 Gen 雪崩（**与 Abe 地震同口径处理**，v122b4）

> **插件版本**：`TransferIdentityFixAPI.dll` = **1,821,696 B @ 2026-10-06 12:59:09**（编译戳 **`Oct  6 2026 12:58:34`**）—— 与 §14 沙尘暴命令**同一个 dll**
> ⚠️ **部署状态：Gen 尚未覆盖**（本轮仅 **Rag** 已覆盖，见 §14 顶部；Rag 实测见 §14.5）；本节描述的 `Avalanche` 白名单在旧版（v122b2）上**不存在**（旧版会返回该 actor 的全量属性）。
> **处理原则**：与 Abe 地震完全一致 —— 插件层用**通用 `actor` 命令 + 内置白名单**暴露、**不新增专用子命令**；前端层**只显示说明性规律文案、不做数据对接**。

### 15.1 插件层（已实现）：`actor` 内置白名单新增 `Avalanche`

```
TransferIdentityFix.WorldProbe actor filter=HazardTrigger_Avalanche props=1 propsIdx=0 top=1 slim=1
```

| 白名单字段 | 实测值（Gen，2026-10-06） | 含义 |
|---|---:|---|
| `ActivationChance` / `CurrentActivationChance` | 0.25 / 0.25 | 进入触发卷时的**基础触发概率 25%** |
| `ActivationIncrement` | 0.05 | **每次未触发后概率 +5%**（保底递增） |
| `MinTimeBetweenActivations` | 180 s | 两次雪崩最小间隔 |
| `MinWarningInterval` / `MaxWarningInterval` | 10 / 15 s | 预警提示间隔窗口 |
| `WarningTimer` | 1.51 | 当前预警计时 |
| `Bounds` | 8000 | 触发盒尺寸（uu） |
| `SlideSpeed` | 750 | 雪崩滑体速度 |
| `ProjectileTimer` | 2 | 雪崩投射物计时 |
| `LastActivationTime` | 0 | 该触发点上次激活时刻（0 = 本次未激活） |

- 与地震的差别仅在**字段数量**（地震仅 1 个 0/1 标志；雪崩这一族有完整掷骰参数），**作法完全一致**：同一 `actor` 命令 + `slim=1` 白名单，`filter=` 里含 `Avalanche` 即命中。
- ⚠️ **不带 `slim=1`** 时仍返回该 actor 的全量属性（约 400 项 / 十余 KB）；前端不需要就**不要加** `slim=1`（避免误得空集的口径冲突）。

### 15.2 前端层（⛔ 同 Abe 地震：只显示规律，不做数据对接）

| 项 | 结论 |
|---|---|
| 触发对象 | **`HazardTrigger_Avalanche_C` × 51**（`scan filter=Avalanche`，仅 Gen；**Rag 0 命中**） |
| 同族（不接入） | `HazardTrigger_Slide_C` ×73（滑坡/碎石滑落）、`Buff_Hazard_BubbleBox_C` ×71、`Volcanic_Eruption_Hazard_C` ×1 |
| 能否**预测** | ❌ **不能** —— 雪崩**不是全局天气排期**，而是"**玩家进入触发卷才掷骰**"的位置相关事件（`TheMinimumPlayerDistanceFromSpawnPoint` 类参数控制），服务端读不到"下一个玩家会在哪踩进去" |
| 能做什么 | 只能给出**静态参数**（概率 25% 起、每次 +5%、冷却 180 s、预警 10~15 s）与**事件到达通知**（插件已挂钩 `AHazardTrigger::Activate/Deactivate`，见 §4.5 火山事件日志） |
| **前端怎么做** | ✅ **只显示说明性规律文案，不轮询、不上屏"雪崩中/概率"** |
| 建议文案（可直接用） | 「**雪崩为区域随机事件：仅发生在雪山区域，走进雪崩区时有概率触发；触发前会有约 10~15 秒预警，请立即离开积雪坡面。**」 |
| 备选文案（更简） | 「雪崩：雪山区域随机触发，听到预警请立刻撤离」 |

- 🔴 与地震同理：`LastActivationTime` 只说明"某个触发卷上一次何时激活"，**推不出下一次**，不建议上屏。
- 🔜 若将来要做"事件到达即通知"，与地震共用同一条 backlog（`AHazardTrigger` 钩子 → 事件推送），**当前不做**。


### 15.3 🔬 触发地形 · 具体概率 · 征兆（v122b4 实测补充）

**① 触发地形（"特定地形"具体指哪里）**

- 51 个 `HazardTrigger_Avalanche_C` **全部布置在 Gen 的雪原（Arctic 子图）**；`Rag` / `Ext` / `Ast` / `Val` / `Los` / `Isl` / `Sco` / `Cen` / `Abe` 实测 **0 命中** ⇒ 只有 Gen 有雪崩
- 触发卷尺寸 `Bounds = 8000`（uu）⇒ 属**局部地形陷阱**，不是全图天气（对照：Rag 沙尘暴是全局天气，见 §14）
- 同族但**不**接入：`HazardTrigger_Slide_C`（73，滑坡/碎石滑落）、`Buff_Hazard_BubbleBox_C`（71）、`Volcanic_Eruption_Hazard_C`（1）

**② 具体概率（保底递增模型，字段实测）**

| 项 | 字段 | 实测值 |
|---|---|---|
| 基础触发概率 | `ActivationChance` / `CurrentActivationChance` | **0.25（25%）** |
| 失败递增 | `ActivationIncrement` | **+0.05（每次未触发 +5%）** |
| ⇒ 逐次概率 | — | 第 1 次 25%、第 2 次 30%、第 3 次 35% … **最多 15 次未命中即 100%**（0.25 + 15×0.05 = 1.0） |
| 两次间隔冷却 | `MinTimeBetweenActivations` | **180 s（3 分钟）** |
| 独立性 | `LastActivationTime` | 51 个触发卷**各自独立计数**（逐卷一个时间戳） |

**③ 征兆（触发前留出反应时间）**

| 征兆字段 | 实测 | 含义 |
|---|---:|---|
| `WarningTimer` | 1.51 | 当前预警计时（预警已进行 1.51 s） |
| `MinWarningInterval` / `MaxWarningInterval` | 10 / 15 s | **预警窗口 10~15 s** ⇒ 从预警起约 10~15 s 后滑体落地 |
| `WarningEmitter` | `unreadable` | 预警特效发射器（指针不可读 ⇒ 只报字段存在性） |
| `SlideFX` / `SlideSound` / `SlideFXUpdateInterval` | 0 / 0 / 0.5 s | 滑体特效与音效（0.5 s 刷新） |
| `SlideSpeed` | **750** | 滑体速度（uu/s）——**跑得比它快就能脱离** |
| `ProjectileTimer` | 2 | 滑体投射物计时 |

**④ 前端文案建议（把地形 + 概率 + 征兆都写进去）**

> 「**雪崩是雪山区域的地形随机事件**：走进积雪坡面 / 谷地时约 **25%** 触发；同一处反复经过概率逐次 **+5%**（最多 15 次必触发），两次之间至少间隔 **3 分钟**。**触发前有约 10~15 秒预警**（画面与音效提示），听到预警请立刻离开坡面 —— 滑体速度约 **750 单位/秒**，直线跑离通常可躲开。」

---

## 16. 🆕 Gen 巨浪机制详解（Ocean 子图波浪，`WorldProbe wave`）

> 实测 2026-10-06 13:0x（Gen 32329）；**`wave` 是 v118 起既有命令**，本条**不需要新 dll**（v122b2 即可实测）

### 16.1 它是什么：Ocean 子图的「海况」，不是独立天气

- Gen 的 5 个 DayWeather 系统用 **`miniMapType`** 区分子图：`arctic` / `bog` / **`ocean`** / `volcanic` / `null`（月球）——**勿按下标写死**（与 §0 总览 Gen 行口径一致）
- **巨浪 = `ocean` 子图的海况**：由 **`BP_Waterline_Ocean_Gen_4_ASA_C`**（水体参数，注意类名里的 `Gen_4` = Ocean 子图）+ `BP_GEN_DayWeather_WeatherSystem_C` 的 **`WaveState`** 共同决定
- 实测命中系统：`weather.bIsOcean = 1`（确证是 ocean 系统）、**`WaveState = 0.35`**，且该值与 `waterline.groups[0].bakedOceanState = 0.35` **完全一致** ⇒ **`WaveState` 就是主海洋水体的当前海况（0~1）**

### 16.2 命令与响应（实测原值）

```
TransferIdentityFix.WorldProbe wave
```

| 键 | 实测值 | 含义 |
|---|---|---|
| **`verdict`** | **`calm`** | **插件派生的海况结论 —— 前端可直接上屏** |
| `weather.WaveState` | **0.35** | 海况数值（0 = 平静 … 1 = 满态） |
| `weather.CurrentWeather` / `NextWeather` / `PrevWeather` | `ClearSky` / `ClearSky` / `ClearSky_Fog` | **ocean 子图天气名可读**（Gen 里少数可读天气名的子图，见 §3.9.1） |
| `weather.TimerNextWeather` | 207655703.06 | 下次换天气（世界秒）；`worldTime` = 207654375.44 ⇒ **≈1,327.6 s 后** |
| `weather.bInWeatherTransition` | 0 | 未在过渡中 |
| `weatherSystemCount` / `weatherIdx` | 5 / 2 | 命中第 3 个系统（0 基下标 2） |
| `waterline.class` / `enableOcean` | `BP_Waterline_Ocean_Gen_4_ASA_C` / 1 | 水体对象（`Gen_4` = Ocean）、海洋已启用 |

### 16.3 水体 4 组参数（`waterline.groups[]`，实测原值）

| group | `bakedOceanState` | `waveHeight` | `waveSteepness` | `bakedOceanSpeed` | `waterLevel` | `oceanTile` |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | **0.35** | 47.25 | 7 | 1.5 | **-285199** | **60000** |
| 2 | 1 | 2 | 10 | 10 | 87 | 2500 |
| 3 | 0.25 | 0.3 | 0.5 | 25 | 84 | 500 |
| 4 | 0.25 | 10 | 0 | 25 | 0 | 5000 |

- 🔎 **推断（未逐项验证，如实标注）**：group1（`waterLevel=-285199` 深海基准 + `oceanTile=60000` 最大瓦片）⇒ **主海洋主体**；group2（`oceanTile=2500`，state 已达 **1** 满态）⇒ 近海 / 浅海；group3 / group4（`oceanTile=500 / 5000`）⇒ 内陆湖泊与河道水体。
- ⚠️ `bakedOceanState` 是**该组的烘焙状态**，**不等于浪高**：group1 在 state 0.35 时 `waveHeight=47.25` 是**参数上限值**，实际浪高按海况插值。

### 16.4 前端用法

| 需求 | 取法 |
|---|---|
| 显示"海况 / 巨浪"结论 | **`verdict`**（如 `calm`）；数值可辅以 `weather.WaveState` |
| 显示"下次海况变化倒计时" | `TimerNextWeather − worldTime`（秒） |
| 判断是否位于 Ocean 子图 | `weather.bIsOcean === 1` 或 `wxSystems[].miniMapType === "ocean"` |
| 进阶（浪高参数/多水体） | `waterline.groups[]`：按 `oceanTile` 最大者视为主海洋 |


---

## 17. 🆕 Rag ElectricalStorm 是否区域性？（**否**）与 Sco 对照（**是**）

> 实测 2026-10-06 13:45（Rag 32326 / Sco 32321）；用于前端决定"雷暴要不要按区域显示"

### 17.1 Rag：雷暴 = 普通**全局天气预设**（无区域闸门）

| 检查项 | 实测结果 |
|---|---|
| 预设表 | `presetTable` 6 项，**idx 4 = `WeatherPreset_RAG_ElectricalStorm`**（与 ClearSky / Fog / Rain / Sandstorm / Superheat 并列） |
| 当前概率 | 权重 0.2 ÷ `chanceSum 2.05` ⇒ **9.76%**（`probsPct[4]`，`badwx` / `sandstorm` 命令均可取） |
| **区域绑定字段** | `wxSemantics.electricalStorm` = **`null`** ⇒ Rag 天气 actor 上**不存在** `ElectricalStormRegion`（没有"绑到哪个区域"的字段） |
| 效果层 `BP_RAG_WeatherEffects_C`（203 属性） | 仅有 `RainAmount` · `SnowAmount` · `SandstormAmount` · `SandstormDebries` · `bInSandstormTrigger` · `bWeatherOffInCave` ⇒ **无任何电/雷字段**（连 `bInElectricalStormTrigger` 式闸门都没有） |
| 独立雷暴 Actor / 掩膜 | `scan filter=Electrical` / `Storm` / `Mask` ⇒ **全部 0 命中**（`filter=Lightning` 只命中 14 只闪电飞龙，是生物） |
| 唯一与区域相关的可读字段 | Agent `SeqWeight_Region0..3 = [1,0,0,0]` —— 管的是**昼夜序列权重**，**不是**雷暴范围 |

⇒ **Rag 的雷暴由全局掷骰选中后整图按同一预设生效，不做区域过滤**；前端**不要**按区域开关显示。
⚠️ 边界说明：以上能证明"**不存在区域机制**"（无字段、无掩膜、无闸门）；"蓝图内部是否硬编码范围"无法从实例数据反证，但效果层完全无雷参数，基本可排除。

### 17.2 Sco（Scorched Earth）：雷暴 = **掩膜驱动 + 区域绑定**（对照）

| 项 | 实测 |
|---|---|
| **区域绑定** | `wxSemantics.electricalStorm = {"region": 2, "debug": false, "regionNameProbe": …"asString": "**NW**"}` ⇒ **绑定区域 2（"NW" 西北区）** |
| 掩膜系统（DLWE） | `All Weather Mask Brushes` · `DLWE Relevant Weather Mask Brushes` · `DLWE Relevant Projection Boxes` · `DLWE_MaskTarget` · `DLWE Brush Size Buffer` · `DLWE Brush Strength Buffer` · `DLWE_Brush_Locations_Buffer` · `Current DLWE Mode=2` · `Enable Obscured Lightning=1` |
| 闪电参数 | `Lightning Bolt Length=60000` · `Lightning Flash Interval (Min/Max)=0.1/0.3` · `Lightning Flash Length=1.5` · `Lightning Flash Light Shaft Intensity=1.2` · `Lightning Flash Max Angle from Forward=100` · `Lightning Flash Maximum Distance=26972501` |
| 预设表 | 8 槽，含 `ElectricalStorm`（id 7）——与 SE 沙尘暴（尘墙扫过）同属"掩膜驱动"体系 |

⇒ **SE 的雷暴（与 SE 沙尘暴同理）只在绑定区域内表现**；这类图才需要按区域处理。

### 17.3 前端口径（速查）

| 图 | 雷暴怎么处理 |
|---|---|
| **Rag** | 当**全局天气**处理：展示"雷暴概率 9.76%"即可，**不做区域过滤**（无区域字段） |
| **Sco / SE 系** | 雷暴**只在绑定区域（实测 region 2 = "NW"）出现** ⇒ 若要精确展示，需按区域判断（`weather` 响应 `wxSemantics.electricalStorm.region` / `regionNameProbe`） |


### 17.4 Val 的雷暴也是**全图**的（2026-10-06 13:48 实测）

| Val 检查项 | 实测 |
|---|---|
| 预设表（**Val 自有命名**，非 Rag 的） | 4 项：`WeatherPreset_VAL_ClearSky` · `WeatherPreset_VAL_Fog` · `WeatherPreset_VAL_Rain` · **`WeatherPreset_VAL_ElectricalStorm`（idx 3）** |
| **区域绑定字段** | `wxSemantics.electricalStorm` = **`null`** ⇒ 与 Rag 相同，**没有** `ElectricalStormRegion` |
| 独立雷暴 Actor / 掩膜 | `scan filter=Electrical` / `Storm` / `Lightning` / `Mask` / `DLWE` ⇒ **全部 0 命中** |
| 效果层 `BP_RAG_WeatherEffects_C`（203 属性，与 Rag 同类） | 仅 `RainAmount=0.5` · `SnowAmount=0.5` · `SandstormAmount` · `SandstormDebries` · `bInSandstormTrigger=0` · `bWeatherOffInCave=1` ⇒ **无任何电/雷字段** |

⇒ **Val 与 Rag 同机制：雷暴由全局掷骰选中、整图生效，不做区域过滤。**

**6 图对照（同批实测，`electricalStorm` 全为 `null`，仅 Sco 例外）**

| 图 | 预设表 | 有雷暴预设 | ES 绑定 | 前端怎么显示 |
|---|---|:---:|---|---|
| **Rag** | 6 项（idx4 = `WeatherPreset_RAG_ElectricalStorm`） | ✅ | `null` | **全局**（不看区域） |
| **Val** | 4 项（idx3 = `WeatherPreset_VAL_ElectricalStorm`） | ✅ | `null` | **全局** |
| **Los** | 5 项（ClearSkyV2 / V3 / SnowFluery / Blizzard / ClearSky） | ❌ | `null` | **无雷暴**（该图是暴风雪） |
| **Ast** | 7 项（含 `WeatherPreset_AST_Sandstorm`） | ❌ | `null` | **无雷暴**（有沙尘暴） |
| **Gen** | 7 项（**Ocean 子图**：含 `WeatherPreset_GEN_Ocean_ElectricalStorm` / `..._ElectricalStorm_Fog`） | ✅ | `null` | 按**子图**（`miniMapType = ocean`） |
| **Sco（SE）** | 8 项（含 `ElectricalStorm`，id 7） | ✅ | **`region=2` = "NW"** | 按**区域**（详见 §17.2） |

> 💡 命名注意：**Val 的预设表是自己的 `VAL_*` 名字**（不是 Rag 的 `RAG_*`）——Val 只是**复用了 Rag 的天气蓝图类**，实例数据是 Val 专属的。

---

## 18. 🆕 Los 的三条 ClearSky 实测（**并不等价：其中一条权重为 0**）

> 实测 2026-10-06 13:49（Los 32328，`WorldProbe badwx`）；对象 `BP_LC_DayWeather_WeatherSystem_C`，`chanceSum = 2.4`

| 槽 i | 预设名 | 资产 id | 当前权重 | **实际概率** |
|---:|---|---:|---:|---:|
| 0 | `WeatherPreset_LC_ClearSkyV2` | 13497063 | 1 | **41.67%** |
| 1 | `WeatherPreset_LC_ClearSkyV3` | 14560421 | 1 | **41.67%** |
| 2 | `WeatherPreset_LC_SnowFluery` | 13895676 | 0.2 | 8.33% |
| 3 | `WeatherPreset_LC_Blizzard` | 13725760 | 0.2 | 8.33% |
| 4 | `WeatherPreset_LC_ClearSky` | 15588821 | **0** | **0%（不参与抽签）** |

- ✅ **真正生效的是 `V2` 与 `V3`**（各 41.67%）；**普通 `LC_ClearSky` 权重为 0**，只是留在预设表里（历史/占位），**不会被抽中**
- ⚠️ **`V2` 与 `V3` 的具体差异不可读**：三者同为 `BP_WeatherPreset_Base_C` 实例，服务端只能读到 **名字 + 资产 id + 当前权重**；预设内部参数（雾 / 云 / 光照 / 持续时间）**不可读**，且 Los 的 `weightsDay` / `weightsNight` / `eventLengths` / `defaultWeather` 实测**全为 `null`**（整个 DayWeather 家族同理，Rag / Val / Ast 相同）⇒ 名字里的 `V2` / `V3` 属**作者版本标记**，**不能当作"三种不同的晴天"**展示（要区分只能靠游戏内观察）
- 📌 **前端口径**：显示「晴（V2/V3 合计 **83.3%**）· 雪絮 8.3% · 暴风雪 8.3%」；若逐槽展示，请把权重 0 的 `LC_ClearSky` 标为"未启用"


---

## 19. 🆕 Gen 漩涡（水下漩涡 / 旋风盒）机制

> 实测 2026-10-06 14:12（Gen 32329）；**没有专用命令**，用通用 `actor` 读属性即可

### 19.1 载体：不是独立 Actor，而是「环境 Buff + 触发盒」

`scan filter=Whirl` / `Vortex` / `Maelstrom` / `Tornado` / `Current` ⇒ **全部 0 命中**（Gen 里没有名为"漩涡"的 actor）。真实载体：

| 类 | 数量 | 作用 |
|---|---:|---|
| **`Buff_UnderwaterCyclone_C`** | 1 | **水下漩涡本体**（海洋中的漩涡） |
| **`Buff_CycloneBox_C`** | **28** | **漩涡/旋风触发盒**（在这些盒内生成） |
| `Gen_AreaBuff_Ocean_C` | 1 | 海洋**区域** buff（见 §19.5） |
| `Gen_AreaBuff_Lunar_C` | 1989 | 月球区域 buff（量最大，非本节主题） |

### 19.2 核心参数（`Buff_UnderwaterCyclone_C` 与 `Buff_CycloneBox_C` **完全一致** ⇒ 同一套机制）

| 字段 | 实测 | 含义 |
|---|---:|---|
| **`CycloneInterval`** | **360 s（6 分钟）** | 两次漩涡之间的间隔 |
| **`CycloneDuration`** | **90 s** | 单次漩涡持续时长 |
| `CycloneSpeedMin` / `CycloneSpeedMax` | **140 / 300** | 卷动速度区间 |
| `CameraShakeOuterRadius` / `CameraShakeScaleMultiplier` | 1000 / 1 | 被卷入时的相机抖动半径与倍率 |
| `CycloneInBox` / `CurrentNumCycloneInBox` / `CyclonesInBox` | 0 / 0 / 0 | **此刻盒内是否有漩涡**（实时状态） |
| `MaxNumCycloneInBox` | `null` | 单盒漩涡数量上限 **不可读**（如实标注，不猜） |
| `ShallowEmitterDontSpawnOutOfViewCheckRadius` | 500 | 浅水发射器距离校验 |
| `DeactivateAfterTime` | -1 | 不自动失效（由 Duration 控制） |

### 19.3 🔥 实锤：该参数就是真实时长（运行记录）

`Buff_UnderwaterCyclone_C` 上留有：

- `LastTimeSpawn = 207658246.45`
- `LastTimeDeactivate = 207658337.04`
- ⇒ **上次漩涡实际持续 90.59 s**，与 `CycloneDuration = 90` **吻合** ✅

⇒ 说明这套字段是**真实生效**的，不是蓝图里没用的默认值。

### 19.4 对玩家的影响

- 被卷入后由漩涡**施加位移/卷动**（`CycloneSpeed 140~300`）+ **相机抖动**（半径 1000）
- `Submerged*` / `Unsubmerged*` 的 `MaxSpeed` / `MaxAcceleration` / `RotationRate` 修正**当前均为 0** ⇒ **不改基础速度**，位移来自漩涡本身
- 盒内会施加对应 buff（`Buff_CycloneBox_C`）；水下为 `Buff_UnderwaterCyclone_C`

### 19.5 顺带解出：Gen 海洋区域 buff（`Gen_AreaBuff_Ocean_C`）

| 字段 | 实测 | 含义 |
|---|---:|---|
| `CharacterMultiplier_SubmergedOxygenDecreaseSpeed` | **0.1** | **水下氧气消耗 ×0.1**（可潜更久） |
| `SubmergedMaxSpeedModifier` | **3** | 水下最大速度 ×3 |
| `UnsubmergedMaxSpeedModifier` | 1 | 水面不变 |
| `StamRegenSpeed` | **3** | 体力恢复 ×3 |

### 19.6 前端口径

| 需求 | 做法 |
|---|---|
| 显示"此刻是否有漩涡" | `WorldProbe actor filter=Buff_CycloneBox props=1 propsIdx=0 top=1 fields=CycloneInBox,CurrentNumCycloneInBox,CycloneInterval,CycloneDuration,CycloneSpeedMin,CycloneSpeedMax` → `CycloneInBox > 0` 即正在刮 |
| **预测下一次** | ❌ **做不到**：没有任何"下次时刻/倒计时"字段；只能按 `CycloneInterval = 360 s` 的规律做粗略估计，或现场观测 |
| 显示"强度" | `CycloneSpeedMin/Max = 140/300`（静态参数，可直接作为文案） |
| 定位在哪片区域 | ⚠️ 盒子的位置**不可读**（`Box1` 为 unreadable）；只能确认"全图共 28 个盒 + 1 个水下漩涡" |


## 20. 🆕 天气区域（`zones`）数据时效 + `settings`/`state` 字段口径（2026-10-06 实测，**前端必读**）

> 一句话：**同一个区里有两份同名属性 —— `settings` 是「预设常量」，`state` 是「实时插值态」**。把「（实时）」标在 `settings` 上就是错的；后端还有 60 s 整包缓存。

### 20.1 链路三层与时效

| 层 | 位置 | 时效 | 说明 |
|---|---|---|---|
| 插件 `zones` | `TransferIdentityFixAPI.cpp`（`zones` 子命令） | **actor 名单**静态缓存 ≤900 s；**属性值每次调用重读** | `fresh=1` / 换图（`world_ts` 回退）/ 指针失效 / 超 900 s 触发重扫（日志 `WORLDPROBE zones rescanned`）；属性值走 `TifCollectProps`，**无值缓存** |
| 后端 `worldprobe_zones` | `dino_backend.py` | **整包 60 s TTL**（`WP_ZONES_TTL_MS = 60000`）+ 同键并发合并 | 响应带 `cacheAgeMs` / `serverNowMs`；`fresh:1` 跳过缓存 |
| 前端 `lbWxZonesSync()` | — | 60 s 轮询 | 想显示真实时值 → 见 20.5 |

### 20.2 `settings` vs `state`（最容易踩的坑）

- `settings`：该区的**天气预设定义**对象（`Snow_TC` / `Snow_Light_TC` / `Snow_Heavy_TC` …）→ **固定常量**，不随时间变。
- `state`：该区的**实时天气状态**对象（`UDS_Weather_Settings_C_<id>`）→ **会变**，且过渡期是**插值小数值**。
- 两者**属性同名**：`Cloud Coverage` / `Material Snow Coverage` / `Snow` / `ColdTemperatureModification` / `HotTemperatureModification` / `SkylightTemperature` / `Wind Intensity` / `Fog` / `ElectricalStorm` …

### 20.3 实测证据（Cen 32322）

**（a）三次采样（17:27 / 17:42 / 17:43）**

| 区 | 预设（`settings` objectName） | 云量 | 雪覆盖 | 雪量 `Snow` | 风强 |
|---|---|---|---|---:|---:|---:|
| 0 | `Snow_TC` | 3.8 | 1 | 0.1 | 4 |
| 1 | `Snow_Light_TC` | 3.8 | 0.5 | 0.05 | 2 |
| 2 | `Snow_Light_TC` | 3.8 | 0.5 | 0.05 | 2 |

- `settings` 三次完全一致 ⇒ **常量**
- `state` 变化：zone0 `Snow` 0.1 → 0.05 → 0.05；zone1 `Snow` 0.05 → 0.01 → 0.01；`ColdTemperatureModification` 0 → 1 → 1（多区同步）

**（b）连续采样（12 轮 × 15 s，17:45:54 起）—— 抓到插值小数**

| 轮次 | 时间 | zone0 `state.Snow` | zone1/2 `state.Snow` | 全区 `state.ColdTemperatureModification` |
|---|---:|---:|---:|---:|
| 1 | 17:45:55 | **0.0999628** | **0.0499706** | **0.000694156** |
| 2 | 17:46:12 | 0.1 | 0.05 | 0 |
| 3 | 17:46:28 | 0.1 | 0.05 | 0（无变化） |

⇒ **`state` 是实时插值态**：数值逐帧逼近 `settings` 预设值。UI 上的「冷温修正 0.0651834」这类**多位小数就是插值中间值**（同族实测还有 `0.000694156`）。

**（c）稳态对照（Isl 32320）**：4 个区三次采样全等；637 s 长窗 diff（641 字段）**仅 `scanAge` / `worldTime` 变** ⇒ 稳态时 `state` 与 `settings` 也完全一致（那一轮 `state` 的 `Snow` / `ColdTemperatureModification` 全 0），**不能据此判断「数据是静态的」**。

### 20.4 前端字段口径（照这个取，不会错）

| UI 字段 | 取值路径 | 性质 | 建议文案 |
|---|---|---|---|
| 云量 | `zones[i].settings.props["Cloud Coverage"]` | 预设常量 | 「云量（区域预设）」 |
| 雪覆盖 | `zones[i].settings.props["Material Snow Coverage"]` | 预设常量 | 「雪覆盖（区域预设）」 |
| 雪量 | **`zones[i].state.props["Snow"]`** | 实时（插值） | 「雪量（实时）」 |
| 冷温修正 | **`zones[i].state.props["ColdTemperatureModification"]`** | 实时（插值） | 「冷温修正（实时）」 |
| 「此刻是否在下雪」 | `settings["Material Snow Coverage"] > 0`（该区会下雪）且 `state["Snow"] > 0`（此刻在下） | 组合判据 | — |

> ⚠️ `settings.Snow` 与 `state.Snow` 同名不同义：前者＝预设目标值，后者＝此刻实际值。

### 20.5 实时卡片必须传 `fresh:1`

- 后端整包 60 s TTL 会把 `state` 的实时插值**冻结最多 60 s**（`cacheAgeMs` 可直接读出）。
- 前端「（实时）」卡片 → `POST /api/worldprobe_zones`，body `{"server":"Cen","fresh":1}`；插件侧无需改动（属性值本就每次重读）。
- 若 60 s 轮询 × `fresh:1` 有压力，可只对实时卡片用 `fresh:1`，其余沿用缓存。

### 20.6 复核命令

```
# 直连插件（绕开后端缓存）
TransferIdentityFix.WorldProbe zones            # 生效名单缓存，属性值实时
TransferIdentityFix.WorldProbe zones fresh=1    # 强制重扫名单
# 后端
POST /api/worldprobe_zones   {"server":"Cen","fresh":1}
```


## 21. 🆕 「风向」口径核查（2026-10-06 实测：**区域风向是每区固定常量，不是实时值**）

> 用户反馈「区域的风向从来没观察到变化」—— **属实**。穷举了所有可读来源，风向在这套 mod 里就是**作者写死的常量**。

### 21.1 结论

| # | 结论 |
|---|---|
| 1 | `zones[i].wind.direction` = **区域体积的作者常量**（Isl 4 区、Cen 6 区**全部 = 180**），不随时间变 |
| 2 | `zones[i].wind.apply` 才是决定「本区是否强制使用该风向」的开关（Isl `1/0/0/1`、Cen `0/0/0/1/0/1`），同样是常量 |
| 3 | 天气预设 `UDS_Weather_Settings_C`（23 项）**不含「Wind Direction」**（只有 `Wind Intensity` / `Wind Variation`）⇒ 风向**不随天气类型切换而变** |
| 4 | 全局 `weather.weatherState.windDirection` = **每图固定值**（Isl `180` / Sco `90` / Cen `90`；Abe 无此字段） |
| 5 | `biometemps` 只有风强（`globalWind=3`、`biomes[].wind=0`），**没有风向** |
| 6 | 风源 actor `WindDirectionalSource`（Isl ×1）的 193 个 actor 级属性里**没有** Direction/Speed/Strength（在组件上，见 21.4） |

### 21.2 实测证据

| 来源 | 字段 | 实测值 | 是否变化 |
|---|---|---|---|
| 区域体积 | `zones[i].wind.direction` | Isl ×4 = `180`；Cen ×6 = `180` | ❌ |
| 区域体积 | `zones[i].wind.apply` | Isl `1,0,0,1`；Cen `0,0,0,1,0,1` | ❌ |
| 全局天气 | `weatherState.windDirection` | Isl `180` / Sco `90` / Cen `90` | ❌（6 轮 × 20 s） |
| 全局天气 | `weatherState.windStrength` / `windVolume` | `3` / `1` | ❌ |
| biome | `biometemps.globalWind` / `biomes[].wind` | `3` / `0` | ❌（3 轮） |
| 风源 actor | `WindDirectionalSource` 193 属性 | 无风向类字段 | ❌（2 轮全等） |

**观测窗口**：Isl 18:41:36~18:43:29（6 轮 × 20 s，值恒 `180`）；Cen 17:27 / 17:42 / 17:43（6 区恒 `180`）；另含区域 `allprops` 一轮 ⇒ 跨 ≈1.3 小时完全一致。

### 21.3 前端口径（照这个写，不要再标「实时」）

| 场景 | 用哪个字段 | 建议文案 |
|---|---|---|
| 区域卡片里的「风向」 | `zones[i].wind.direction` | **「区域固定风向（180°）」**，或直接显示为「本区风向设置」 |
| 提示该区是否真的强制风向 | `zones[i].wind.apply` | 「本区强制风向：是（1）/ 否（0）」 |
| 若想显示"当前风向" | `weather.weatherState.windDirection` | **「地图固定风向」**（Isl 180 / Sco 90 / Cen 90），并注明是地图级常量 |
| 风强（这个才是会动的） | `weatherState.windStrength` / `zones[i].state["Wind Intensity"]` | 可标「实时」（随天气状态插值） |

⚠️ **不要**对 `wind.direction` / `wind.apply` 标「实时」——它们不会变；风向相关的**实时量只有风强**。

### 21.4 未解部分：风源组件（若将来要「真·实时风向」）

- Isl 上存在 **`WindDirectionalSource`** ×1（`WindDirectionalSource_0`，位置 `46590, 50010, -19660`，PersistentLevel）
- `probe=Component` 已能解析其组件：**`class = WindDirectionalSourceComponent` / `objectName = WindDirectionalSourceComponent0`**（8 字节指针，`hex=7081671b21020000`）
- 该组件的属性（`RelativeRotation`（FRotator）/ `Speed` / `Strength` / `Radius` / gust 等）**当前命令无法 dump**：
  `actor` 子命令只遍历关卡 Actor，组件不是 Actor；
- 若要读它，需要插件新增能力 **`probeProps=<ProbeName>`**（把 `probe=` 已解析到的对象按 `TifCollectProps` 全量输出，走 v108+ 结构体解码读 `RelativeRotation.Pitch/Yaw/Roll`）；
  加此能力后即可判定"UE 风源 actor 的风向是否随时间旋转"。
- 现状：**前端不需要它**（区域卡片的固定风向结论已由 21.1~21.3 覆盖）。

### 21.6 「风」三件套最终定论（**风量 / 风强 / 风向 —— 全是固定值**）

| 项 | 字段（取值路径） | 实测值 | 性质 |
|---|---|---|---|
| **风量** | `weather.weatherState.windVolume`（源头 = 全局天气 actor 的 `Wind Volume`） | **恒 `1`**（Isl/Sco/Cen 三图一致） | **固定**（地图级常量；**不在**区域预设 23 项里） |
| **风强**（区域预设） | `zones[i].settings.props["Wind Intensity"]` | Cen `4/2/2/8/4/8`、Isl `8/2/4/8` | **固定**（每区预设值） |
| **风强**（区域实时对象） | `zones[i].state.props["Wind Intensity"]` | 逐区**恒等于预设** | **固定**（实测**不参与**过渡插值） |
| **风强**（全局） | `weather.weatherState.windStrength` | `3`（Isl/Sco/Cen 一致） | 固定 |
| 风变幅 | `Wind Variation`（区域预设/实时） | `0` | 关闭 |
| **风向**（区域） | `zones[i].wind.direction` / `wind.apply` | `180` / Isl `1,0,0,1`、Cen `0,0,0,1,0,1` | **固定基准值** |
| **风向**（全局） | `weatherState.windDirection` / `Current Wind Direction` | Isl `180` / Sco `90` / Cen `90` | **固定基准值** |

**决定性实测（Cen 32322，19:43:38，当时正处于天气过渡）**：

| 区 | `state["Wind Intensity"]` | 预设值 | `state.Snow` | 预设 Snow |
|---|---:|---:|---:|---:|
| z0 | **4** | 4 | 0.05 | 0.1 |
| z1 | **2** | 2 | 0.01 | 0.05 |
| z2 | **2** | 2 | 0.01 | 0.05 |
| z3 | **8** | 8 | 0.3 | 4 |
| z4 | **4** | 4 | 0.05 | 0.1 |
| z5 | **8** | 8 | 0.3 | 4 |

⇒ 雪量当时**正在插值**（明显偏离预设，如 `0.3` vs `4`），而风强**逐区严丝合缝等于预设** ⇒
**风强不参与插值**，可当固定值使用。

**🔥 风向「会不会变」的开关（新增发现）**：

| 图 | 天气 actor 类 | `Current/Cached Wind Direction` | `Enable Wind Direction Variation` | `Maximum Wind Direction Variation` |
|---|---|---|---|---|
| **Isl** | `UDS_Island_Weather_C` | 180 | **1（开）** | **500** |
| Sco | `UDS_SE_Weather_C` | 90 | 0（关） | 0 |
| Cen | `UDS_TheCenter_Weather_C` | 90 | 0（关） | 0 |

- Sco / Cen 风向恒定 = **作者把「风向变化」关了**（`0 / 0`），不是数据接错。
- Isl 的变化功能**是开着的**（上限 500），但变化载体是 **风源 actor 的组件旋转**
  （`WindDirectionalSourceComponent`，当前命令读不到）；可读的 `Current Wind Direction` 在采样窗口内恒 `180`。
- 天气 actor 上另有 `Old Wind Intensity = -1`（"新旧风强"过渡槽），但区域实时风强实测不变化。

**前端口径（这条最重要）**：
- 区域卡片里的**风量 / 风强 / 风向**全部按**固定值**展示，**不要标「实时」**。
- 本区块（区域天气）里**真正实时**的只有：`state["Snow"]`（雪量）与 `state["ColdTemperatureModification"]`（冷温修正），
  以及云/覆盖类的 `state` 参数。

### 21.5 复核命令

```
TransferIdentityFix.WorldProbe zone s                     # 区域列表（wind.direction / wind.apply）
TransferIdentityFix.WorldProbe weather                    # weatherState.windDirection / windStrength
TransferIdentityFix.WorldProbe biometemps brief=1 count=3 # globalWind / biomes[].wind
TransferIdentityFix.WorldProbe scan filter=Wind limit=25  # 找到 WindDirectionalSource
TransferIdentityFix.WorldProbe actor filter=WindDirectionalSource props=1 probe=Component
```


## 22. 🆕 Sco（UDS 家族）沙尘暴接口 —— `sandstorm` 新增 UDS 分支（v122b5，2026-10-06 已实服验证）

### 22.1 两套沙尘暴，字段完全不同

| 家族 | 地图 | 沙尘暴数据在哪 | `sandstorm` 输出形态 |
|---|---|---|---|
| **Rag 家族**（DayWeather） | Rag | `DayWeather_WeatherSystem`（预设表）+ `DayWeather_Agent`（区域权重）+ `WeatherEffects`（`SandstormAmount` / 触发体） | 预设概率 `sandstormPct` + 区域权重 + 特效值 |
| **UDS 家族** | **Sco / Isl / Cen / Abe…** | **地图天气 actor `UDS_<Map>_Weather_C` 上的 `Dust` / `Material Dust Coverage` 系列** | **本版新增：`family:"uds"` + `dust` / `visual` / `weather`** |

> ⚠️ v122b3/v122b4 的沙尘暴代理在 Sco 上**永远返回 `supported:0`**（Sco 根本没有 DayWeather 那三层）。
> **v122b5 起**插件自动分流：找不到 Rag 三层 → 自动切到 UDS 家族。

### 22.2 请求

```
TransferIdentityFix.WorldProbe sandstorm        # 无需参数，Rag / UDS 自动分流
```

### 22.3 响应结构（UDS 家族，Sco 实测原样）

```json
{"ok":true,"sub":"sandstorm","family":"uds","supported":1,
 "source":{"class":"UDS_SE_Weather_C",
           "objectName":"UDS_SE_Weather_C_UAID_047C1657966A80D401_1851991591","props":737},
 "dust":{"dust":0,"intendedDust":0,"materialDustCoverage":0,
         "oldDust":-1,"oldMaterialDustCoverage":-1,"sweepSequence":0,
         "systemSpawning":0,"enableDustParticles":0,"forming":0,"clearing":0,"edDusty":0},
 "visual":{"particleAlpha":0.6,"particleScale":1,"dustDepth":7,"fogIntensity":5.5,
           "fogMaxPct":8,"ppwfIntensity":2.5,"maxParticleSpawnRate":300,
           "maxDustCoverage":0.5,"dynamicTrails":0},
 "weather":{"currentId":0,"prevId":0,"nextId":null,"waitingForNewWeather":0,
            "lerpValue":1,"transitionLength":0},
 "active":0}
```

### 22.4 字段表

| 键 | 原始属性名 | 含义 |
|---|---|---|
| `dust.dust` | `Dust` | 当前沙尘量 |
| `dust.intendedDust` | `Intended Dust` | 目标沙尘量（过渡终点） |
| `dust.materialDustCoverage` | `Material Dust Coverage` | **材质沙尘覆盖**（沙墙视觉强度的主判据） |
| `dust.oldDust` / `dust.oldMaterialDustCoverage` | `Old Dust` / `Old Material Dust Coverage` | 过渡起点；`-1` = 无过渡（同 `Old Wind Intensity` 模式，**未独立验证**） |
| `dust.sweepSequence` | `CurrentSandstormSweepSequence` | 沙暴扫掠动画序列（0 = 未播放） |
| `dust.systemSpawning` | `Dust System Spawning` | 沙尘粒子系统是否在生成 |
| `dust.enableDustParticles` | `Enable Dust Particles` | 地图级沙尘粒子开关（Sco 恒 0，**含义未验证**） |
| `dust.forming` / `dust.clearing` | `Dust/Sand Forming` / `Dust/Sand Clearing` | 起沙 / 落沙标志 |
| `dust.edDusty` | `ED_Dusty` | 蓝图"沙尘"状态位 |
| `visual.*` | `Dust Particle Alpha/Scale`、`Dust Depth`、`Fog Particle Intensity (Dust)`、`Max Fog Particle Percentage (Dust)`、`PPWF Intensity from Dust`、`Max Dust Particle Spawn Rate`、`Max Dust Coverage`、`Apply Dynamic Trails to Dust` | 视觉/粒子参数（静态配置） |
| `weather.currentId` | `CloudNewWeather` | 当前天气 id |
| `weather.prevId` | `CloudPreviousWeather` | 上一次天气 id（**Sco：id 6 = `Sand_Dust_Storm`**，映射见 `weather` 命令 presetTable） |
| `weather.nextId` | `NextWeather` | **UDS 家族没有该属性 ⇒ 恒 `null`**（按设计） |
| `weather.waitingForNewWeather` | `bWaitForNewWeatherToLoad` | 是否在等新天气资源加载 |
| `weather.lerpValue` | `WeatherLerpValue` | 天气过渡进度（1 = 已收敛） |
| `weather.transitionLength` | `WeatherTransitionLength` | 过渡时长 |

### 22.5 前端判据

| 想判断 | 用法 |
|---|---|
| **是否正在刮沙尘暴** | 顶层 `active == 1`（= `materialDustCoverage > 0` 或 `dust > 0` 或 `sweepSequence > 0` 或 `forming != 0`） |
| 刚刮过 / 即将刮 | `weather.prevId` / `weather.currentId`（Sco：`6` = `Sand_Dust_Storm`）；UDS 家族**拿不到 `nextId`** |
| 是否在过渡 | `dust.oldMaterialDustCoverage != -1`（-1 = 无过渡） |
| 沙墙视觉强度参考 | `dust.materialDustCoverage` 对比 `visual.maxDustCoverage`（Sco = 0.5） |

### 22.6 实服验证（2026-10-06 20:39，v122b5）

| 服 | build | `sandstorm` 响应 | 判读 |
|---|---|---|---|
| **Sco**(32321) | **`Oct  6 2026 20:31:01`** | **1,140 B**，`family:"uds"`、`supported:1` | ✅ 新分支生效（旧构建时为 114 B `unknown subcommand`） |
| Isl(32320) | `01:50:26` | 114 B 不支持 | 旧构建，待铺 |
| Cen(32322) | `01:50:26` | 114 B 不支持 | 旧构建，待铺 |
| **Rag**(32326) | `12:58:34` | **2,030 B**，`supported:1`、`preset="WeatherPreset_RAG_Sandstorm"`、`pct=7.31707` | ✅ 行为**完全未变**（零回归） |

Sco 实测补充：当日 20:25 时 `prevId = 6`（刚刮过 `Sand_Dust_Storm`），20:39 已归 `0`（晴）；`dust` 全 0、`active = 0`。

### 22.7 注意事项

- **`active = 1`（正在刮）路径尚未实测**：Sco 当前未在刮沙尘暴，等真实沙暴发生时再核对一次判据。
- `enableDustParticles = 0`（Sco 实测恒 0）：疑为地图级沙尘粒子总开关，**与沙暴可视化的关系未验证**，不要用它当判据。
- 覆盖范围：只有 **Sco（v122b5）** 与 **Rag（v122b3b4）** 是可用版本；其余 8 服仍 `01:50:26`（连 `sandstorm` 命令都没有）。


## 23. 🆕 强制天气命令 `WorldProbe wxset`（写路径）—— 重点：**Sco 沙尘暴如何强制触发**

> ⚠️ **这是全服写操作**（会改变所有在线玩家看到的天气）。默认 **dry-run**，只有显式传 `apply=1` 才真正落笔。

### 23.1 语法（**最多 4 个参数**，第 5 个起被丢弃）

```
TransferIdentityFix.WorldProbe wxset prop=<属性名> [num=N | value=<对象名> | hex=HH..] [filter=X] [propsIdx=N] [apply=1]
```

| 参数 | 说明 |
|---|---|
| `prop=<名>`（必填） | 目标属性名；**名字里有空格用 `+` 代替**，如 `prop=Manual+Weather+State` |
| `num=N` | 按槽位宽度写数值（槽宽 ≥8 → double；≥4 → int；**否则按 1 字节**） |
| `value=<对象名>` | 写对象指针槽（**实测无效**，见 23.4，不建议用） |
| `hex=HH..` | 直接写原始字节（长度必须等于槽宽×2） |
| `filter=X` | 类名子串匹配，**默认 `SE_Weather`**（Sco 直接命中；**Isl/Cen 必须显式指定**，否则 `matched:0`） |
| `propsIdx=N` | 同类多个 actor 时选第 N 个（越界钳到首位） |
| `apply=1`（或 `go=1`） | **真正写入**；不带则只预演 |

### 23.2 回包字段

| 键 | 含义 |
|---|---|
| `matched` / `actor{class,objectName}` | 命中数量与目标 actor |
| `prop` / `offset` / `size` | 属性名、所在偏移、**槽宽（字节）** |
| `applied` | 1 = 已写入；0 = dry-run |
| `beforeHex` / `beforeObject` | 写前原始字节 / 若为对象指针则给出对象名 |
| `afterHex` / `afterObject` | 写后回读（dry-run 时与 before 相同） |
| `verify[5]` | 五个状态位的前后值：`CurrWeatherType`、`CloudNewWeather`、`ED_CurrentWeather`、`Current Weather Override Volume`、`Currently in a Weather Override Volume` |
| `target{objectName,class,resolvedHex,foundIn,stride}` | 用 `value=<对象名>` 时的解析结果 |
| `error` | 失败原因（`no actor matched filter` / `property not found on this actor` / `property size unsupported` / `no value given`） |

**dry-run 实测样例（Sco，2026-10-06 20:50，未写入）**

```json
{"ok":true,"sub":"wxset","filter":"SE_Weather","matched":1,
 "actor":{"class":"UDS_SE_Weather_C","objectName":"UDS_SE_Weather_C_UAID_047C1657966A80D401_1851991591"},
 "prop":"CloudNewWeather","offset":6561,"size":1,"applied":0,
 "beforeHex":"08","afterHex":"08",
 "verify":[{"name":"CurrWeatherType","before":8,"after":8},
           {"name":"CloudNewWeather","before":8,"after":8},
           {"name":"ED_CurrentWeather","before":12,"after":12},
           {"name":"Current Weather Override Volume","before":0,"after":0},
           {"name":"Currently in a Weather Override Volume","before":0,"after":0}],
 "error":null}
```

> 说明：`CloudNewWeather` 在 Sco 上只有 **1 字节**（`size:1`，偏移 6561），当前值 `08` = 8。
> **Isl** 用默认 filter 会 `matched:0` → 必须 `filter=Island_Weather`；**Cen** 用 `filter=TheCenter_Weather`；
> 其它图先用 `WorldProbe scan filter=Weather` 查类名再填。

### 23.3 🔥 Sco 沙尘暴强制（四步法）

```
1) 预演（只读，确认能命中、看原值）
TransferIdentityFix.WorldProbe wxset prop=CloudNewWeather num=6

2) 真写（全服生效）
TransferIdentityFix.WorldProbe wxset prop=CloudNewWeather num=6 apply=1

3) 立刻用沙尘暴接口核对「是否真的起沙」（v122b5+，目前只有 Sco 有）
TransferIdentityFix.WorldProbe sandstorm      → 看 dust.materialDustCoverage / dust.dust / active

4) 结束 / 回滚（写回晴天）
TransferIdentityFix.WorldProbe wxset prop=CloudNewWeather num=0 apply=1
```

**Sco 天气 id 表**（`weather` 命令 presetTable 实测映射，2026-10-05）

| 下标 i | id | 名称 |
|---:|---:|---|
| 0 | 5 | `ColdFront_SE`（寒潮） |
| 1 | 7 | `ElectricalStorm`（电风暴） |
| 2 | 2 | `Rain_SE`（雨） |
| 3 | 3 | `Foggy_SE`（雾） |
| 4 | 4 | `HeatWave_SE`（热浪） |
| 5 | 0 | `Clear_Skies_SE`（晴） |
| **6** | **6** | **`Sand_Dust_Storm`（沙尘暴 / 沙墙）** |
| 7 | 8 | `Superheat`（焚风） |

### 23.4 ⚠️ 实测边界（务必转达前端，别当成"一定成功"）

**已证无效的写法（2026-10-05 Sco 实测，全部回读一致但天气不变）**：

| 属性槽 | 尝试值 | 结果 |
|---|---|---|
| `Manual Weather State`（8 字节对象指针 → `UDS_Weather_Settings_C_4`） | 指向 ElectricalStorm | ❌ 无变化（指针写入成功、天气不动） |
| `Local Weather State` / `Global Weather State` | 同上 | ❌ 无变化 |
| `ED_CurrentWeather` | 7 | ❌ 无变化 |
| `CurrWeatherType` | 7 | ❌ 无变化 |
| `Current Weather Override Volume` | 1 | ❌ 无变化 |

**唯一"半有效"的写法**：`CloudNewWeather = <id>`
- ✅ `weather` 的 `currentWeatherId` **会立刻变成该 id**（保持数分钟稳定）
- ⚠️ 但**不保证真实效果启动**：当时写 `7`（ElectricalStorm）时 `region` / `Current Lightning Location` / `PendingLightningFlashesLoc` / `lightningIntensity` **全为 0** ⇒ 只改了"请求/显示用的天气 id"，电风暴并未真的开始。
- ⇒ **对沙尘暴**：沙墙的视觉由天气设置里的 `Dust` / `Material Dust Coverage` 驱动，理论上 id 切到 6 后这些值会开始插值上涨，**但必须用步骤 3 的 `sandstorm` 复核**——「id 变了 ≠ 沙墙起来了」。

### 23.5 调用纪律（前端/调用方）

1. **先 dry-run 再 apply**，并把 `beforeHex`（或 `weather` 的 `currentWeatherId`）记下来当回滚值。
2. 一次只写**一个**槽位；不要连续轰炸。
3. 建议**人少时段**执行，测试结束立即回滚（写回原 id）。
4. **不要**写对象指针槽（实测无效，且可能留下脏状态）。
5. 版本要求：`wxset` 自 **v112** 起就有（**旧构建 `01:50:26` 也可用**）；
   而"复核是否起沙"的 `sandstorm`（UDS 分支）需要 **v122b5**，**目前仅 Sco 已部署**（Rag 为 v122b3b4，只有 Rag 家族沙尘暴分支）。


### 23.6 各图 `filter=` 取值表（2026-10-06 20:56 全服实测类名）

| 图 | 天气类（实测数量） | 建议 `filter=` | 备注 |
|---|---|---|---|
| **Sco** | `UDS_SE_Weather_C` ×1 | `SE_Weather`（**默认值，可省略**） | ✅ 唯一**实测可写**：`CloudNewWeather` |
| Isl | `UDS_Island_Weather_C` ×1（另有 `Weather_Override_Volume_C` ×4） | `Island_Weather` | 别用 `Weather`（会命中覆盖体积） |
| Cen | `UDS_TheCenter_Weather_C` ×1（另有 `Weather_Override_Volume_C` ×6） | `TheCenter_Weather` | 同上 |
| Abe | `BP_AB_WeatherAgent_C` ×1、`BP_AB_WeatherSystem_C` ×4 | `AB_WeatherAgent` | 未实测 |
| Ext | `BP_EXT_DayWeatherAgent_C` ×1、`BP_EXT_WeatherSystem_C` ×1 | `EXT_DayWeatherAgent` | 未实测 |
| Ast | `BP_AST_DayWeather_WeatherSystem_C` / `_Agent_C` / `_WeatherEffects_C` / `_CloudSystem_C` / `_RegionTimeOfDay_C`（各 1） | `AST_DayWeather_WeatherSystem` | 未实测 |
| Rag | `BP_RAG_DayWeather_WeatherSystem_C` / `_Agent_C`、`BP_RAG_WeatherEffects_C`、`BP_DayWeather_CloudSystem_C`、`BP_RAG_DayWeather_RegionTimeOfDay_C` ×2 | `RAG_DayWeather_WeatherSystem` | 未实测 |
| Val | 复用整套 `BP_RAG_*`（同 Rag） | `RAG_DayWeather_WeatherSystem` | 未实测 |
| Los | `BP_LC_DayWeather_WeatherSystem_C` / `_Agent_C`、`BP_LC_WeatherEffects_C`、`_CloudSystem_C`、`_RegionTimeOfDay_C`（各 1） | `LC_DayWeather_WeatherSystem` | 未实测 |
| Gen | `BP_GEN_DayWeather_WeatherSystem_C` **×5**、`_CloudSystem_C` ×5、`_RegionTimeOfDay_C` ×5、`BP_GEN_DayWeather_Agent_C` ×1、`BP_GEN1_WeatherEffects_C` ×1 | `GEN_DayWeather_WeatherSystem` | ⚠️ 5 份 = 5 张小地图，选实例需 `propsIdx`（见下方限制 1） |

核查命令：`TransferIdentityFix.WorldProbe scan filter=Weather limit=25`

**⚠️ 三条硬限制（务必转达调用方）**

1. **参数上限 4 个**：`wxset` 只解析前 4 个 token ⇒ `prop=` + `num=` + `filter=` + `apply=1` 正好用满；
   **再加 `propsIdx=` 就会把 `apply=1` 挤掉**（结果仍是"预演"，看起来像没生效）。Gen 想"选小地图 + 真写"目前做不到。
2. **`filter` 只匹配类名**（不像 `actor` 子命令也匹配实例名）⇒ 无法用实例名挑选 Gen 的 5 份 WeatherSystem。
3. **DayWeather 家族（Abe/Ext/Ast/Rag/Val/Los/Gen）的天气 id 极可能是 `FName`（8 字节）**：
   `num=` 会按 8 字节 double 写入 ⇒ **不要用 `num=`**；只能自定义 `hex=`（FName 比较索引），**未验证、不建议**。
   ⇒ 目前**唯一实测可写**的仍是 **Sco 的 `CloudNewWeather`（1 字节 id）**，其余图请先 dry-run 观察 `size`/`error` 再决定。


### 23.7 🔴 本轮追加实测（2026-10-06 21:03~21:05）：**Sco 天气无法从服务端强制触发**

**背景**：前端真实执行了 `wxset prop=CloudNewWeather num=6 apply=1`（写入成功，`currentId` 一度变为 6）。

**实测 1：只写 id → 过渡不启动**
`dust` / `materialDustCoverage` / `intendedDust` / `sweepSequence` / `systemSpawning` / `forming` **全 0**；
`weatherLerpValue = 0`、`changeStartTime = 0`、`active = 0` ⇒ **沙墙不出现**（不是在过渡，是**过渡没开始**）。

**实测 2：两根"推进过渡"杠杆（写入成功 → 观察 → 已回滚，实服无遗留）**

| 杠杆 | 属性（offset / size） | 写入 | 观察 30 s | 回滚 |
|---|---|---|---|---|
| ② | `bWaitForNewWeatherToLoad`（6576 / 1） | `01 → 00` ✅ | `waitingForNewWeather` 确实变 0 ✅，但 `dust` 全 0、`lerp=0`、`active=0` ❌ | `00 → 01` ✅ |
| ③ | `WeatherChangeStartTime`（6848 / 8） | `0.0 → 273839679.42` ✅ | 同样 `dust` 全 0、`lerp=0`、`active=0` ❌ | 写回 `0000000000000000` ✅ |

**实测 3：写入的 id 不持久**
`CloudNewWeather` 被 mod 自行改写：20:59 时 = 6（我们的写值）→ 21:08 已变回 8（Superheat）；
`ED_CurrentWeather` 全程保持 12 未变。

**结论（务必转达）**
- 连同此前失败的 6 个槽位，**共 8 条槽位实测无效 + 1 条半有效**（`CloudNewWeather`）⇒
  **Sco 的天气切换无法从服务端强制触发，没有可用的"一键刮沙尘暴"方法。**
- 前端应当：
  1. 用 `weather` / `sandstorm` **如实展示**当前天气与沙暴状态（**不要**把 `currentId` 当"正在刮"的判据——它会被 mod 改写）；
  2. 需要看到沙墙**只能等自然天气**（后台已挂低频守护，一旦自然刮起会抓全量快照用于确证驱动字段）。
- 若前端仍要提供"强制"按钮，必须在 UI 上注明**仅改请求 id、不保证生效**。


## 24. 🆕 UDS 天气的**实时判据**（2026-10-06 实测定稿：抓全 5 次真实变天）

> 来源：Sco 低频守护 21:24~22:51（88 个采样点）实录 —— 期间天气在 **`PartlyCloudy`（晴）↔ `Heatwave`（热浪）** 之间切换 5 次，**未出现沙尘暴**。

### 24.1 判据速查（前端照这个写）

| 想知道 | 用什么字段 | 实测 |
|---|---|---|
| **当前天气名** | **`CurrSequenceSettings.asString`**（结构体 `S_SE_CloudMapSequence` 的 `WeatherFolderName`） | `PartlyCloudy` / `Heatwave` |
| **是否正在变天** | `Current Weather State Changed == 1`（过渡期），或 `Current Local Weather Change Speed != 0` | 过渡完成后回 `0` |
| **过渡进度（0→1）** | **`Lerp to New Settings`** | `0 → 0.0294 → 0.722658 → 1` |
| 目标/当前天气 id | `CloudNewWeather`（= `weather` 的 `currentWeatherId`）、`CurrWeatherType` | `0`(晴) ↔ `4`(热浪) |
| 上一轮天气 id | `CloudPreviousWeather` | 与 `CloudNewWeather` 镜像 |
| ~~`WeatherLerpValue`~~ | ❌ **不是进度**：变天当刻跳 `1`、切换完成归 `0` | 已更正 |
| 变天间隔 | **无字段可读**（`NextWeather`/`TimerNextWeather` 在 UDS 上不存在）⇒ 用观测统计 | **约 11~22 分钟**（5 次实测） |

### 24.2 实测定稿时间线（Sco，21:24~22:51）

| 时间 | 观测到的变化 |
|---|---|
| 21:47:50 | 变天启动：`WeatherLerpValue 0→1`、`bWaitForNewWeatherToLoad 1→0`、`BeginTime` 跳变、`OldLerpToNewSettings 0→1` |
| 21:58:40 | 切到 **Heatwave**：`CloudNewWeather 0→4`、`CurrWeatherType 0→4`、`asString PartlyCloudy→Heatwave`、`Current Weather State Changed 0→1`、`Lerp to New Settings 0→0.0294` |
| 21:59:40 | 过渡中：`Lerp to New Settings → 0.722658`、`Current Local Weather Change Speed 0.0202→0.0621` |
| 22:00:40 | 过渡完成：`Lerp to New Settings → 1`、`Current Weather State Changed → 0`、`Change Speed → 0` |
| 22:14:40 | 回到 **PartlyCloudy**（`CloudNewWeather 4→0`） |
| 22:36:40 / 22:50:40 | 又一次 `0→4→0` |

⇒ 期间天气**相当活跃**（间隔 11~22 分钟），"晴天很久"只是错觉/恰好没抽到别的天气。

### 24.3 沙尘暴判据仍缺现场（重要）

- 本窗口 `Dust` / `Material Dust Coverage` / `CurrentSandstormSweepSequence` / `Dust System Spawning` /
  `Dust/Sand Forming` / `ED_Dusty` **全程 = 0**（88 点）；
- ⇒ **晴/热浪切换完全不碰 dust 系字段** ⇒ dust 系只在沙尘暴时才取值（这一点反过来支持它作为沙暴判据）；
- **沙尘暴现场仍待捕捉**（守护继续运行，抓到即落全量快照）。

### 24.4 前端建议

| 场景 | 做法 |
|---|---|
| 天气卡片 | 显示 `CurrSequenceSettings.asString` 对应中文名 + 变天中显示 `Lerp to New Settings` 百分比 |
| 「变天中」徽标 | `Current Weather State Changed == 1` 时点亮 |
| 沙暴卡片 | 仅 `materialDustCoverage > 0`（或 `Dust > 0`）时显示，否则隐藏 |
| 变天节奏文案 | **不要**承诺"下次变天时刻"（无字段）；可写「该图约 15 分钟一轮天气」这类经验描述 |


## 25. 🆕 跨服「天气判据」对照表（10 图实测，含"距下次变天"算法）

> 回答「只有 UDS 才有进度么？」—— **不是**。三个家族各有各的字段，**DayWeather/EXT 家族最全**（还能预告下次变天）。

### 25.1 对照表（2026-10-06 23:06 实测）

| 图 | 家族 | 天气 actor 类 | 「过渡中」 | 「进度」 | **「下次变天时刻」** | 间隔配置 |
|---|---|---|---|---|---|---|
| Isl / Sco / Cen | **UDS** | `UDS_Island_Weather_C` / `UDS_SE_Weather_C` / `UDS_TheCenter_Weather_C` | `Current Weather State Changed` | **`Lerp to New Settings`（0→1）** | ❌ **无** | ❌ 无（观测 ≈11~22 min） |
| **Ext** | EXT | `BP_EXT_WeatherSystem_C` | `bInWeatherTransition` | `WeatherTransitionTimeElapsed` + `Begin/EndWeatherTransitionTime` | ✅ **`TimerNextWeather`** | `WeatherChangeTimerMin/Max` = **1000/2000 s** |
| **Ast** | DayWeather | `BP_AST_DayWeather_WeatherSystem_C` | 同上 | 同上 | ✅ | **1500/2500 s** |
| **Rag / Val** | DayWeather | `BP_RAG_DayWeather_WeatherSystem_C` | 同上 | 同上 | ✅ | **1500/2500 s** |
| **Los** | DayWeather | `BP_LC_DayWeather_WeatherSystem_C` | 同上 | 同上 | ✅ | **1500/2500 s** |
| **Gen** | DayWeather | `BP_GEN_DayWeather_WeatherSystem_C`（×5） | 同上 | 同上 | ✅（`weather` 会挑活跃实例） | **1500/2500 s** |
| **Abe** | AB | `BP_AB_WeatherAgent_C`（291 属性） / `BP_AB_WeatherSystem_C`（195 属性） | ❌ **候选名 0 命中** | ❌ | ❌ | ❌ |

**Abe 特别说明**：其天气 actor **没有任何** transition / timer / next-weather 字段；
它是「生物群系 + 温度」驱动体系（`SurfaceWeather`、`FertileChamberWeather`、`BioLumChamberWeather`、
`ElementChamberWeather`、`Seq_SurfaceTemperature`、`Seq_ExposureDayWeight` …），**无法给出变天进度或下次时刻**。

### 25.2 「距下次变天」算法（DayWeather / EXT 家族）

```
剩余秒数 = TimerNextWeather − worldTime      # worldTime 取同一次响应的顶层字段
过渡进度 = (worldTime − BeginWeatherTransitionTime) / (EndWeatherTransitionTime − BeginWeatherTransitionTime)
```

实测样例（23:06:59）：

| 图 | worldTime | `nextWeatherAt` | 距下次变天 |
|---|---|---|---|
| Ext | 251848507.63 | 251850000.0 | **≈ 24.9 分钟** |
| Gen | 207690657.33 | 207692000.0 | **≈ 22.4 分钟** |
| Rag | 238485828.14 | 238486000.0 | **≈ 2.9 分钟** |
| Ast | 246168150.64 | 246168000.0 | **已过期 −150.6 s**（`bInWeatherTransition=0`，尚未起过渡） |

### 25.3 ⚠️ 精度陷阱（务必转达）

- `weather` 命令返回的 `nextWeatherAt` **被截断到 6 位有效数字**：
  Ext 直读 `TimerNextWeather = 251850005.51` → `weather` 返回 **251850000.0**（差 **5.5 s**）；
- ⇒ 需要精确剩余时间时，请 **`fields=TimerNextWeather,BeginWeatherTransitionTime,WeatherTransitionTimeElapsed` 直读**。

### 25.4 前端读取配方（按家族选）

| 家族 | 推荐读取 |
|---|---|
| **UDS**（Sco/Isl/Cen） | `WorldProbe sandstorm`（沙暴）+ `fields=Lerp+to+New+Settings,Current+Weather+State+Changed,Current+Local+Weather+Change+Speed`（天气）+ `probe=CurrSequenceSettings`（天气名） |
| **DayWeather/EXT**（Rag/Ext/Ast/Val/Los/Gen） | `fields=TimerNextWeather,WeatherChangeTimerMin,WeatherChangeTimerMax,bInWeatherTransition,WeatherTransitionTimeElapsed,BeginWeatherTransitionTime,EndWeatherTransitionTime`（可算**距下次变天**与进度） |
| **Abe** | 只能取温度/区域类字段（`Seq_*Temperature` 等），**不要承诺变天进度/倒计时** |

---

## 26. 🆕 v122b6 —— 前端反馈 4 个缺口的处理说明（2026-10-06 23:35，**已构建，待部署**）

> **一句话结论**：4 条里 **2 条是插件代码缺失（①④）**、**2 条是游戏数据本身如此（②③）** —— **与"有没有部署新版 dll"无关**：①④ 旧 dll / 新 dll 都缺，必须改代码重编译；②③ 任何 dll 都补不出来（那张图的天气对象天生没有那些属性）。
> **当前状态**：v122b6 **已构建打包**（`TransferIdentityFixAPI.dll` = **1,831,424 B** @ 2026-10-06 23:21:14，md5 `1b6ffda3329fe2fbb1ea841251c71a59`），**尚未投放实服**。
> **🔑 部署判据（前端请照此判断新旧）**：部署后 `WorldProbe weather` 的响应**头部会出现 `"schema":"wx-122b6"`**；没有这个键 ⇒ 该服仍是旧构建。建议前端把它当**可选增强开关**（新字段缺失时不要报错，走旧逻辑即可）。

### 26.1 逐条对照（缺什么 → 为什么 → 现在给什么 → 前端怎么用）

| # | 前端反馈 | 归因（已核源码 + 实服实测） | v122b6 之后 | 前端怎么用 |
|---|---|---|---|---|
| **①** | `transitionBegin` / `transitionEnd` 被 6 位截断 | **插件代码 bug**：语义字段发射走了 `oss << double`（C++ 流默认 **6 位有效数字**），修好的 `TifJsonNum` 没覆盖到这段 | `transitionBegin` / `transitionEnd` / `nextWeatherAt` / `secondsUntilChange` 全部**逐秒精度**（示例：`251850005.51`，旧版会输出 `251850000`） | 若你为"末位恒为 0"写过取整/去抖补偿，**可以删掉**；新版可直接显示到秒 |
| **②** | Isl 缺 `changeStartTime` 等 UDS 字段 | **数据本身**：`UDS_Island_Weather_C` **确实没有** `WeatherChangeStartTime` / `WeatherLerpValue` / `WeatherTransitionLength` / `CloudNewWeather` / `CloudPreviousWeather` / `CurrSequenceSettings`（连命名变体都已逐一排除，`fields=` 指名直读取证） | 新增 **`transitionProgress`**（= `Lerp to New Settings`，0..1 过渡混合度）、`oldTransitionProgress`、`staticLerpValue`、`weatherStateChanged`、`localChangeSpeed`、`currWeatherType`、`prevWeatherType` | **统一改用 `transitionProgress` 画过渡进度**（Sco / Cen / Isl 三张 UDS 图都有）；`weatherStateChanged` 可做"刚变过天"的一次性提示；**不要再依赖 `changeStartTime`**（Ext/Gen 才有） |
| **③** | Gen 非活跃小图缺过渡进度数值 | **数据本身**：Gen 有 5 份 `WeatherSystem`，**只有活跃那份**有真实计时器，其余是未初始化模板（`TimerNextWeather=1000`、`BeginWeatherTransitionTime=-100`） | `wxSystems[]` 每项新增 **`live`**（`1` = 在走表；判据 `TimerNextWeather ≥ 1e5`）与 **`transitionProgress`**（优选 `Lerp to New Settings`，否则按 `Elapsed/(End-Begin)` 合成） | 5 图卡片：**只用 `live=1` 的那项**显示倒计时/进度（与原有 `activeWxIdx` 等价，但逐项自带、无需再算）；`live=0` 的项显示「—」 |
| **④** | `Lerp to New Settings` 未编入 HTTP | **插件语义键表未收录**（**不是后端丢字段**：后端 `worldprobe_weather` 原样透传插件对象，字段没进 HTTP 是因为插件根本没输出） | 已收录，映射为 `transitionProgress`（同 ②） | 见 ② |
| **附** | （前端未提，顺手补）当前天气**名字** | UDS 图把当前天气名藏在 `CurrSequenceSettings` 结构体的**首成员 FString** 里（其布局与 `TArray` 头相同：ptr/num/max，这也是它之前只以 `asString` 出现在探针里的原因） | 新增 **`weatherName`**（如 `PartlyCloudy` / `Heatwave`）；EXT/GEN 图该键为 `null` | UDS 图（Sco / Isl / Cen）可直接把 `weatherName` 当**当前天气名称**上屏；EXT/GEN 图继续用 `wxSystems[].currentWeather`（FName） |

### 26.2 ⚠️ 为什么 `WeatherLerpValue` 不能当过渡进度（重要，别踩）

- `WeatherLerpValue` 是**瞬时量**：**变天瞬间跳到 1，之后回落 0**（实服连续采样证实）——用它当进度会误判。
- 真正的 0..1 进度是 **`Lerp to New Settings`** ⇒ 对外键名 **`transitionProgress`**。
- EXT/GEN 家族没有 `Lerp to New Settings`，它们的进度由 `WeatherTransitionTimeElapsed / (EndWeatherTransitionTime − BeginWeatherTransitionTime)` 合成 —— v122b6 已在 `wxSystems[].transitionProgress` 里替前端算好，前端直接取。

### 26.3 兼容矩阵（前端最小改动版：缺失即回退，不报错）

| 字段 | 旧 dll（v122b2 ~ v122b5） | v122b6 | 建议写法 |
|---|---|---|---|
| `schema`（响应头） | 无 | `"wx-122b6"` | `const isNew = o.schema === "wx-122b6"`（仅作可选分支开关） |
| `weatherState.transitionProgress` | 无（UDS 图拿不到任何过渡字段） | UDS 图有数值；EXT/GEN 为 `null` | `const p = ws.transitionProgress ?? null;` 非 `null` 才画进度条 |
| `weatherState.weatherName` | 无 | UDS 图为字符串；EXT/GEN 为 `null` | `const nm = ws.weatherName ?? 由 id 映射表兜底` |
| `weatherState.transitionBegin` / `transitionEnd` / `nextWeatherAt` | **存在但被截断**（6 位有效数字） | 逐秒精度 | 旧版适合"分钟级"文案，新版可显示到秒；两者都是数值，无需类型分支 |
| `wxSystems[].live` | 无 | `0` / `1` | 挑活跃实例：`live === 1`；字段缺失时回退 `activeWxIdx` |
| `wxSystems[].transitionProgress` | 无 | 数值或 `null` | 同 ② |

### 26.4 部署范围与验证步骤

- **一次构建覆盖全服**（本次改动无按图差异）；建议顺序：**Sco（32321）先验** → 通过后其余 9 图（含 Bob 之外的 10 端口全部同一份 dll）。
- 验证（`TransferIdentityFix.WorldProbe weather`，逐服看三点）：
  1. 响应头 **`"schema":"wx-122b6"`**（无 ⇒ 旧构建）；
  2. `weatherState.transitionProgress` 与 `weatherState.weatherName` 非 `null`（Sco / Isl / Cen）；
  3. `transitionBegin` 或 `nextWeatherAt` 的**末位不再是 0000**。
- 本文档 **§9.4「尚未实现（v122 backlog）」中的 ① 时间戳精度、④ 语义键缺失两项，随 v122b6 关闭**；②③ 属"游戏数据本身如此"，不作为插件 backlog。

### 26.5 本次源码改动位置（运维/复核用）

| 改动 | 位置 |
|---|---|
| 精度：语义字段发射 `oss << sit->second` → `TifJsonNum(...)` | `weatherState` 构建循环 |
| `secondsUntilChange` 精度 | 同循环之后 |
| 7 个 UDS 语义键入表 + 映射 | `kTifWeatherSemKeys` / `kTifWxPropMap` |
| `CurrSequenceSettings` 结构体首 FString → `weatherName` | 新函数 `TifReadSeqWeatherName()` + `dump_props` 特例 |
| `wxSystems[].live` / `transitionProgress` | `wxSystems` 循环 |
| 响应头 `schema` | `weather` 响应头部 |

---

## 27. 🌪️ Sco 沙尘暴判据修正（2026-10-07 01:0x，**实服抓到真实沙尘暴后的定论**）

> **背景**：2026-10-07 **01:09:41** Sco 真的切入沙尘暴（用户在游戏内**肉眼看到沙墙**），这是本项目第一次抓到"可见沙墙 + 逐分钟全字段采样"的完整窗口，因此得出了确定结论。

### 27.1 🔴 定论一：`dust` 系列字段**不是** Sco 沙墙的判据（恒 0）

实测（沙尘暴期间，多次采样）：

```
active=0
dust=0  intendedDust=0  materialDustCoverage=0  sweepSequence=0
systemSpawning=0  enableDustParticles=0  forming=0  clearing=0  edDusty=0
```

**逐分钟全字段 diff**（15 个快照 01:00:47→01:14:47，逐字段对比）证明：沙尘暴切换那一刻（01:09:47）**只有以下 16 项变化**，其中**没有任何一项**属于 dust / 材质 / sweep：

| 变化字段 | 值 |
|---|---|
| `CloudNewWeather` | `0 → 6`（id 6 = `Sand_Dust_Storm`） |
| `CurrWeatherType` | `0 → 6` |
| `CloudPreviousWeather` | `3 → 0` |
| `PrevWeatherType` | `3 → 0` |
| **`WeatherTransitionLength`** | `120 → 20`（**沙尘暴特征值**） |
| `Lerp to New Settings` | `1 → 0.958292`（过渡混合度） |
| `Current Local Weather Change Speed` | `0 → 0.029052` |
| `Current Weather State Changed` | `0 → 1` |
| `CurrWeatherVariation` | `0 → null` |
| `Cache Period` / `PrevFrameInterval` | `1.1 → 1.09709` / `15 → 10` |
| `CurrSequenceSettings.asString` | `PartlyCloudy → **Sandstorm**` |
| `CurrSequenceSettings.WeatherFolderName` | FString 长度 13 → 10（"PartlyCloudy"→"Sandstorm"，逐字节吻合） |
| `CurrSequenceSettings.Variations` | → `8044f147400100000300000003000000`（3 个 variation） |
| `Cache Alpha` / `Cache Current Timer` | 每帧抖动（无关） |

### 27.2 定论二：沙墙的真实载体（全图 actor 扫描，v122b2+）

| actor | 类 | 说明 |
|---|---|---|
| **`Matinee_SandStorm`** | `ShooterMatineeActor` | **沙尘暴演出**（Matinee）；`PlayRate=0.0117`、`InterpPosition=0` |
| **`Matinee_ElectricStorm`** | `ShooterMatineeActor` | 雷暴演出（同位置，隔壁） |
| `ElectricalStormPointCenter` + 四角 `…SouthWest/SouthEast/NorthWest/NorthEast` | `Note` | 雷暴 5 个区域锚点（全图） |
| `PS_SandDust_low_SM_*`（≥15 个实例） | `NiagaraActor` | 低空沙尘粒子 |
| `PS_EnvCaveAmbDust*`、`PS_cave_DustCloud_falling` | `NiagaraActor` | 洞穴环境灰尘粒子 |

- `DLWE` / `WeatherEffect` / `Particle` / `CloudSystem` / `RegionTimeOfDay` 在 Sco **全部 0 命中**。
- 结合 `Enable Dynamic Landscape Weather Effects = 0` ⇒ **Sco 根本没启用「动态地表土尘」系统**，所以那套 `Dust` 字段永远 0，而沙墙照样演。
- ⚠️ `ShooterMatineeActor` 的 bool 属性（`bIsPlaying` 等）**读取值不可信**（实测 `bActorEnableCollision=36`、`bAllowTickBeforeBeginPlay=128` 之类，均非 0/1 ⇒ bool 位域读取不可靠），**暂不能作为判据**。

### 27.3 ✅ 前端应该用的判据（现成可用）

| 判据 | 取值 | 可用性 |
|---|---|---|
| **`weatherState.currentWeatherId`** / `currWeatherType` | **`6` ⇒ 沙尘暴**；`7` ⇒ 雷暴；`4` ⇒ 热浪；`0` ⇒ 晴天；`2` 雨；`3` 雾；`5` 寒潮；`8` Superheat | ✅ 推荐主判据 |
| **`weatherState.weatherName`** | `"Sandstorm"`（沙尘暴）/`"PartlyCloudy"`/`"Heatwave"`/`"Fog"` | ✅ **v122b6 起提供**（人读名，最稳） |
| `weatherState.transitionLength` | **`20`** ⇒ 沙尘暴（其他天气多为 `120`） | ✅ 辅助校验 |
| `weatherState.transitionProgress` | 0..1（v122b6 起提供，来源 `Lerp to New Settings`） | ✅ 过渡进度条 |
| `weatherState.currentWeatherId==6` 期间的持续时间 | 沙尘暴时长 | ✅ 由前端自己起止计时 |
| ❌ `wxSemantics.sandstorm.active` | 在 Sco 恒 0 | **废弃**（等 v122b7 改为按天气 id 判定） |
| ❌ `dust` / `materialDustCoverage` / `sweepSequence` | 在 Sco 恒 0 | **废弃** |

> 📌 **一句话**：Sco 的沙尘暴 = 「**当前天气 id 6（或名字 Sandstorm）+ 过渡长度 20**」，与"土尘覆盖度"无关。

### 27.4 前端最小改动（伪码）

```js
const ws = resp.weatherState || {};
const isSandstorm = (ws.currentWeatherId === 6) || (ws.weatherName === "Sandstorm");
const isElectricalStorm = (ws.currentWeatherId === 7) || (ws.weatherName === "ElectricalStorm");
// 过渡中：ws.transitionProgress (0..1，v122b6)，非 null 才画进度条
// 沙尘暴时长：自己记录 isSandstorm 的起止（服务端不提供时长字段）
```

### 27.5 待办（v122b7 建议）

1. `sandstorm` 子命令的 `active` 判据改为 **`CurrWeatherType==6 || CloudNewWeather==6 || asString=="Sandstorm"`**，并输出 `activeSource`（说明依据）；
2. `dust{}` 块保留但**显式标注** `"note":"constant 0 on UDS maps - not the driver"`，避免前端再误用；
3. 新增 `matinee{}`：`Matinee_SandStorm` / `Matinee_ElectricStorm` 是否存在 + `PlayRate` / `InterpPosition`（并标注 bool 不可信）；
4. 等一次"沙尘暴前后"的 `PlayRate`/`InterpPosition` 对比，判定能否作为"正在演"的信号（当前两次采样均为 `0.0117` / `0`，尚未见变化）。

### 27.6 采样证据

- 原始 JSON：`tmp\_dust_live_20261007_011220.json`、`tmp\_dust_trace_raw\*.json`、`tmp\_sandwall_raw\*.json`
- 逐分钟快照：`tmp\_wxwatch\V3SNAP_20261007_01*.json`（15 个参与 diff）
- 分析输出：`tmp\_dust_diff_out.txt`（全字段 diff）、`tmp\_sandwall_out.txt`（actor 扫描）、`tmp\_sandwall_parse_out.txt`（Matinee/Niagara 属性）

---

## 28. ⚡ 雷暴"范围"能抓到什么（2026-10-07，v122b8）

> **一句话**：**能抓"在哪一块"（区域名 + 区域锚点坐标），抓不到"盖住多大"（掩膜几何不可读）。**

### 28.1 实测能力对照

| 想抓的东西 | 能不能 | 依据 |
|---|---|---|
| 雷暴是否进行中 | ✅ **能**（主判据） | `weatherState.currentWeatherId == 7`（秒级） |
| 雷暴在哪个区域 | ✅ **能** | `electricalStorm.region`（int，非 0 生效）+ `electricalStorm.regionName`（**v122b8 起**，短名如 `Center` / `NW`）；判据 `regionNameProbe.asString` 自 v93 起可读但会残留 |
| 区域**锚点坐标** | ✅ **能**（**v122b8 起**） | `electricalStorm.regionPoints[]`（5 个 `ElectricalStormPoint*` Note actor 的世界坐标）；`regionPoint` = 当前 region 对应的那个锚点 |
| 雷暴**几何边界**（多边形 / 半径） | ❌ **不能** | `Weather Mask Target in Use/Size/Half Size/Brush Target` 在**无雷暴与雷暴中两种状态都**为 `0`/`null`（实测两份原始样本比对）；闪电落点槽位恒 0（§1.4 已证） |

### 28.2 区域锚点实测坐标（Sco 32321，`ElectricalStormPoint*`）

| actor | x | y | z |
|---|---:|---:|---:|
| `ElectricalStormPointCenter` | 1,960 | 1,510 | -13,420 |
| `ElectricalStormPointSouthWest` | -193,670 | 132,810 | -13,420 |
| `ElectricalStormPointSouthEast` | 142,920 | 132,810 | -13,420 |
| `ElectricalStormPointNorthWest` | -178,330 | -166,100 | -13,420 |
| `ElectricalStormPointNorthEast` | 174,570 | -169,940 | -13,420 |

> 另有 2 个演出 actor：`Matinee_ElectricStorm`、`Matinee_SandStorm`（`ShooterMatineeActor`，同址）。**注意**：§1.6 里"`scan filter=Electrical` → 0 命中"的旧结论**不适用于 `actor` 命令** —— `actor filter=Electrical` 能扫到这 7 个（Note/Matinee），因为它们不是"天气 actor"而是舞台标记。

### 28.3 短名 ↔ 长名映射（v122b8 已内置）

| `regionName`（探针短名） | 锚点后缀（长名） |
|---|---|
| `Center` | `ElectricalStormPointCenter` |
| `NW` | `ElectricalStormPointNorthWest` |
| `NE` | `ElectricalStormPointNorthEast` |
| `SW` | `ElectricalStormPointSouthWest` |
| `SE` | `ElectricalStormPointSouthEast` |

**实测样本（雷暴中抓取）**：`tmp\_es1_sco_full.json` → `"region":2`，名字槽 hex `50ecd04e160200000300000008000000`
⇒ FString `num=3`、数据 `4e00 5700` = `'N','W'` ⇒ **`regionName="NW"` ⇒ 雷暴在西北角**。

### 28.4 前端用法（v122b8 起）

```js
const es = resp.wxSemantics?.electricalStorm;
const active = (resp.weatherState?.currentWeatherId === 7);
if (active && es) {
  // 在哪块：名字 + 该块锚点坐标（可直接在地图上打点/画圈）
  showRegion(es.regionName, es.regionPoint);      // regionPoint:{objectName,x,y,z} 或 null
  // 全部 5 块坐标（可预先画分区）：es.regionPoints[]
}
```

### 28.5 ⚠️ 两个必须知道的坑

1. **`regionName` 会残留**：雷暴结束后 `region` 回到 0，但名字槽仍保留上一场的名字（实测 `region=0` 而 `regionName` 仍为 `Center`）。⇒ **不能**用它当"是否进行中"的判据，只能当"这次/上次在哪儿"的提示。
2. **`region` 滞后约 9 分钟**（§1.4 已记）⇒ 时间敏感场景一律以 `currentWeatherId == 7` 为准。

### 28.6 生效判据

- `sandstorm` 子命令：`"schema":"sandstorm-122b7"`（v122b7 起）
- `weather` 子命令：`"schema":"wx-122b6"`（v122b6 起）+ **出现 `wxSemantics.electricalStorm.regionPoints` 即 v122b8**
- 证据文件：`tmp\_es1_sco_full.json`（雷暴中 region=2/NW）、`tmp\_events_raw\Sco_32321_weather.json`（无雷暴 region=0/名字全 0）

### 28.7 🔄 雷暴与沙尘暴的对齐（v122b9，2026-10-07）

| 对齐项 | 沙尘暴（v122b7 起） | 雷暴（v122b9 起） |
|---|---|---|
| **显式判据 + 来源** | `sandstorm.active` / `activeSource` / `sandIds` | **`electricalStorm.active`**（1 = 进行中）/ **`activeSource`**（`currWeatherType` = 主判据 `CurrWeatherType == 7`；`region` = 滞后约 9 分钟的补充；`none`）/ **`stormIds`** |
| **无效字段显式标注** | `dustNonZero` + `dustNote`（dust 恒 0 非驱动源） | `geometryNote`（`Weather Mask Target *` 两态皆 0/null，无几何可读） |
| **载体上报** | `matinee[]`（`Matinee_SandStorm` / `Matinee_ElectricStorm`，含 `playRate` / `interpPosition`） | **`matinee[]`（同结构，v122b9 起）** |
| **位置 / 范围** | ❌ 不提供（沙墙为全图演出） | ✅ `regionPoints[]`（5 锚点）/ `regionPoint` / `regionName` / `regionNameFull` |
| **部署判据** | `sandstorm` 子命令：`"schema":"sandstorm-122b7"` | **`weather` 子命令：`"schema":"wx-122b9"` + `schemaFeatures[]`** |
| **天气名** | `weatherName = "Sandstorm"`（实测） | ⏳ 待真雷暴实测（同一 `CurrSequenceSettings` 槽位，预期给雷暴名） |
| **时长 / 进度** | 前端自行计时（服务端不提供时长） | 同（口径一致） |

- `weather` 的 `schemaFeatures` 当前为 `["weatherName","transitionProgress","regionPoints","stormActive"]`
  ⇒ **前端按"能力"判断比按版本号判断更稳**：以后新增字段只需往数组里加名字，前端判断逻辑不必再改。
- ⚠️ **唯一的已知未对齐点**：雷暴进入 `active` 时 `weatherName` 的实际字符串（需真雷暴期间采一次确认）。

### 28.8 🧪 2026-10-07 强制切换实测（雷暴 / 沙尘暴 / 恢复）+ v122b10 修正

**强制切换命令（实测有效，`apply=1` 才执行）**

```
TransferIdentityFix.WorldProbe callfunc fn=MC_ChangeWeather p.New+Weather+Type=7 p.Transition+Length=30 p.Reset+Particle+Emitters=1 apply=1
```

| 时刻 | 动作 | 实测结果 |
|---|---|---|
| 01:39:31 | `apply=1` 切**雷暴(7)** | `ok:true` |
| 01:39:46 | 采样 | `currentWeatherId=7` / `currWeatherType=7` / `transitionLength=30`（**引擎本次未改写为 60**）⇒ **15 秒内生效** |
| 01:40:23 | `apply=1` 切**沙尘暴(6)** | `ok:true` |
| 01:40:43 | 采样 | `currWeatherType=6`、**`sandstorm.active=1` / `activeSource="currWeatherType"`**、`dustNonZero=0` ⇒ **✅ 沙尘暴判据修正实测通过** |
| 01:40:49 | 手动恢复晴天(0) | `ok:true` |
| 01:41:01 | 复核 | `currWeatherType=0`、`CloudPreviousWeather=6`（上一场确为沙尘暴） |
| 01:41:19 | 脚本自带恢复(0) | `ok:true`（幂等，无副作用） |

**结论**
1. ✅ **沙尘暴判据可用**：`sandstorm.active`（+`activeSource`）在真实沙尘暴期间正确为 `1`，且 `dust` 仍恒 0 ⇒ 前端**不要**再用 dust 判。
2. ✅ 强制切换（`callfunc`）可用于**按需制造事件**做验证；沙尘暴/雷暴/晴天三态切换均成功，恢复干净。
3. 🔴 **本次顺带查出 2 个读取 bug（已由 v122b10 修复，待部署）**：
   - `electricalStorm.active` **恒 0**：用 **int32** 读了 **1 字节**的 `CurrWeatherType`（同族 `CloudNewWeather`/`CloudPreviousWeather` 在 dump 里 size=1 为证）⇒ 改为按真实元素大小读（`TifReadNumByRef`）。
   - `weatherName` / `regionName` **恒 null**：`TifReadSeqWeatherName()` 把 FString 的**结尾 NUL 当成非法控制符直接 return false**，而 `num` 计数**包含**该 NUL ⇒ 每次必失败；同一时刻通用 payload probe 却能读到 `"Center"`（hex `num=7`）为反证 ⇒ 改为遇 NUL `break`。
4. **v122b10 部署判据**：`electricalStorm` 块出现新键 **`activeJudge`**（说明两条判据），且雷暴期间 `active=1 / activeSource="currWeatherType"`、`weatherName` 与 `regionName` 非 null。

> 📌 前端判据终版（两场风暴统一）：**沙尘暴 = `currentWeatherId==6` 或 `weatherName=="Sandstorm"`；雷暴 = `currentWeatherId==7`**；
> `sandstorm.active` / `electricalStorm.active` 由插件统一给出，可直接用。

### 28.9 🧭 "沙墙到哪里了" —— **不可读**（2026-10-07 沙尘暴进行中专项实测，定论）

> **结论**：服务端**拿不到**沙墙的位置/推进；能确定的只有"**在刮 / 不在刮**"。这是游戏设计如此（沙墙是客户端 Matinee + Niagara 视觉，服务器不需要知道它的位置），不是抓取姿势问题。

**采样条件**：`callfunc` 强制切沙尘暴(6) 生效后（`sandstorm.active=1`、`currWeatherType=6`）逐 15 秒采样。

| 候选字段（绕过 400 属性上限，用 `fields=` 指名直读） | 沙尘暴进行中实测 | 说明 |
|---|---|---|
| `bSandstormSweepActive` | **0** | "扫掠进行中"标志未置位 |
| `bSandstormSweepBackwards` / `bSandstormSweepWestEast` | **0** / **0** | 扫掠方向标志同样未置位 |
| `CurrentSandstormSweepSequence` | **0** | 无扫掠序列 |
| `SandstormSweepSequenceNS` / `…WE` | **null** | 曲线引用槽为空（未赋值） |
| `SweepFrontierCurve`（沙墙前沿曲线） | **null** | 同上 |
| `SandstormSweepDirectionCurve` | **null** | 同上 |
| `Matinee_SandStorm.InterpPosition` | **0**（不推进） | 演出位置；服务端 `MatineeData=null`（无时间线数据可换算位移） |
| `Matinee_SandStorm.PlayRate` | `0.0117`（恒定） | 静态配置值，非进度 |
| `PS_SandDust_low_SM_*`（Niagara） | 194 个属性中**无** `User.*`/覆盖度/位置参数 | 粒子参数在组件上，服务端不可读 |
| 掩膜几何 `Weather Mask Target *` | 两态皆 `0`/`null` | 见 §28.7 |

> ⚠️ **本节同时纠正一个取材坑**：`actor <filter> props=1` 的 **400 条上限把属性名的 S–Z 段整段挡住**
> （Sco 天气 actor 共 **737** 个属性，dump 只到 `Rain_Particles` 为止）——`Sandstorm*` / `Sweep*` 全在被挡区段。
> **凡是要读 `Sandstorm*` / `Sweep*` / `Weather*` / `Wind*` 等后半段属性，必须用 `fields=` 指名直读**（可绕过上限）。

**前端口径（终版）**
- ✅ 能显示：**是否在刮**（`sandstorm.active` / `currentWeatherId == 6`）、**天气名**（`weatherName`）、**过渡进度**（`transitionProgress`）、**雷暴所在区域**（`electricalStorm.regionName` + `regionPoints`）。
- ❌ 不能显示：沙墙**位置**、**推进百分比**、**覆盖范围**、**强度**。若产品需要"沙墙到哪了"，只能靠玩家目视/直播反馈，或者由**客户端侧**（MOD/截图分析）解决，服务端无解。

### 28.10 ✅ 雷暴"范围"实测通过（v122b10，2026-10-07 01:52）

**采样条件**：`callfunc` 强制切雷暴(7)，`apply` 后 **60 秒**采样（脚本每 30 s 一轮）。

| 字段 | 实测值 | 判定 |
|---|---|---|
| `weatherState.weatherName` | **`"ElectricalStorm"`** | ✅ 雷暴期名字正确（此前恒 null，v122b10 的 FString 修复生效） |
| `weatherState.currentWeatherId` / `currWeatherType` | `7.0` / `7.0` | ✅ 秒级 |
| `electricalStorm.active` / `activeSource` | **`1`** / **`"currWeatherType"`** | ✅ v122b10 的 1 字节读法修复生效 |
| `electricalStorm.regionName` | **`"Center"`** | ✅ 区域短名可读 |
| `electricalStorm.regionPoint` | **`{"objectName":"ElectricalStormPointCenter","x":1960,"y":1510,"z":-13420}`** | ✅ **区域名 ↔ 锚点坐标匹配成功**（前端可直接在地图打点） |
| `electricalStorm.regionNameProbe.asString`（探针路径对照） | `"Center"`（hex `num=7`，wchar `43 65 6e 74 65 72`） | ✅ 双路径一致，互相印证 |
| `electricalStorm.region`（数字） | **`0`**（风暴 60 秒时仍未更新） | ⚠️ **滞后**（§1.10 记 ~9 分钟）⇒ **不要**用数字做判据 |

**结论（前端口径 · 终版）**

| 想显示 | 用什么 |
|---|---|
| 是否雷暴 | `weatherState.currentWeatherId == 7`（秒级）或 `weatherName == "ElectricalStorm"`；插件另给 `electricalStorm.active` |
| 雷暴在**哪一块** | `electricalStorm.regionName`（`Center` / `NW` / `NE` / `SW` / `SE`） |
| 那一块的**坐标** | `electricalStorm.regionPoint`（当前区域的锚点）；全量 5 个锚点见 `regionPoints[]` |
| 雷暴**多大一片** | ❌ 不可读（掩膜几何两态皆 0/null，见 §28.9） |
| 沙尘暴同理 | `currentWeatherId == 6` 或 `weatherName == "Sandstorm"`；沙墙范围不可读 |

> 📌 至此两场风暴的"范围"能力均已定论：**雷暴 = 区域名 + 锚点坐标（可用）；沙尘暴 = 无位置（全图演出）；两者几何边界均不可读。**

---

## 29. 📣 前端总通告：从"沙尘暴长期监测"到现在的全部改动与结论（2026-10-06 ~ 10-07）

> **本节目的是让前端不用翻前面几十节**：一次看清这轮改了什么、现在能用什么、什么永远拿不到、怎么兼容旧版。

### 29.1 这轮做了什么（版本时间线）

| 版本 | 内容（前端相关） | 线上状态 |
|---|---|---|
| **v122b2** | 基线：`fields=` 可单独使用；无曲线驱动的图 `badwx.factor` 改为 `null` + `reason` | 其余 **9 图** |
| **v122b3/b4** | Rag 沙尘暴：新增 `WorldProbe sandstorm`（三层结构：roll / region / effect） | Rag |
| **v122b5** | Sco/UDS 家族沙尘暴回退分支（当时用 `dust` 字段做判据 —— **后已证伪**） | Sco 旧版 |
| **v122b6** | 前端反馈 4 缺口的代码修复：① **6 位截断 → 逐秒精度**；④ 语义键补 7 项（`transitionProgress`/`weatherStateChanged`/`localChangeSpeed`/`currWeatherType`…）；③ `wxSystems[].live` + 逐实例 `transitionProgress`；附 **`weatherName`**；`weather` 加 `"schema":"wx-122b6"` | Sco 已含 |
| **v122b7** | **沙尘暴判据改正**：`sandstorm.active` 改为按**天气 id/名称**判定，新增 `activeSource` / `sandIds` / `dustNonZero` / `dustNote` / `matinee[]`，`"schema":"sandstorm-122b7"` | Sco 已含 |
| **v122b8** | **雷暴区域**：`electricalStorm.regionPoints[]`（5 个锚点坐标）+ `regionName` / `regionNameFull` / `regionPoint` + `geometryNote` | Sco 已含 |
| **v122b9** | **雷暴与沙尘暴对齐**：`electricalStorm.active` / `activeSource` / `stormIds` / `matinee[]`；`weather` schema 升 **`wx-122b9`** + **`schemaFeatures[]`** | Sco 已含 |
| **v122b10** | 修 **2 个读取 bug**：① FString 结尾 NUL 导致 `weatherName`/`regionName` 恒 `null`；② 1 字节槽误按 int32 读导致 `electricalStorm.active` 恒 0。新增 `activeJudge`（部署判据） | **Sco 已部署并实测通过** |

### 29.2 现在能显示什么（终版字段表 · 照这个写即可）

| 想显示 | 字段 | 取值 |
|---|---|---|
| **沙尘暴进行中** | `weatherState.currentWeatherId == 6` 或 `weatherState.weatherName == "Sandstorm"` | 秒级；插件另给 `wxSemantics.sandstorm.active = 1`（`activeSource = "currWeatherType"`） |
| **雷暴进行中** | `weatherState.currentWeatherId == 7` 或 `weatherState.weatherName == "ElectricalStorm"` | 秒级；插件另给 `wxSemantics.electricalStorm.active = 1` |
| **雷暴在哪一块** | `wxSemantics.electricalStorm.regionName` | `Center` / `NW` / `NE` / `SW` / `SE` |
| **那块的位置** | `wxSemantics.electricalStorm.regionPoint` | `{objectName,x,y,z}`（当前区域锚点；无雷暴时为 `null`） |
| **全部 5 块锚点** | `wxSemantics.electricalStorm.regionPoints[]` | 5 条 `{objectName,x,y,z}`（可预先画分区） |
| **变天过渡进度** | `weatherState.transitionProgress`（0..1）、`transitionLength`、`weatherStateChanged` | v122b6 起 |
| **天气名** | `weatherState.weatherName` | `"Sandstorm"` / `"ElectricalStorm"` / `"PartlyCloudy"` / `"Heatwave"` / `"Fog"` … |
| **世界钟** | `worldTime`（逐秒精度，v122b6 起不再 6 位截断） | 任意分支同口径 |
| **能力自检** | `weather.schemaFeatures[]` | 现含 `weatherName` / `transitionProgress` / `regionPoints` / `stormActive` |
| **风暴载体** | `sandstorm.matinee[]` / `electricalStorm.matinee[]` | `Matinee_SandStorm`(playRate 0.0117) / `Matinee_ElectricStorm`(0.01) |

### 29.3 🔴 明确"拿不到"的清单（请勿再提需求，已实测多次）

| 项 | 结论 | 证据 |
|---|---|---|
| **沙墙位置 / 推进百分比 / 覆盖范围 / 强度** | ❌ 服务端无任何可读字段 | sweep 组（`bSandstormSweepActive` / `CurrentSandstormSweepSequence` / `SandstormSweepSequenceNS·WE` / `SweepFrontierCurve` / `SandstormSweepDirectionCurve`）**风暴进行中全为 0/null**；`dust` 全 0（该图无 DLWE）；`Matinee.InterpPosition` 恒 0 且 `MatineeData=null`；Niagara 无参数 |
| **雷暴几何边界（多大一片）** | ❌ 掩膜几何两态皆 0/null | `Weather Mask Target in Use/Size/Half Size/Brush Target` |
| `electricalStorm.region`（**数字**） | ⚠️ **滞后约 9 分钟**，仅作参考 | 强制雷暴 60 秒时仍为 0 |
| `regionName` 的**残留**特性 | ⚠️ 风暴结束后仍保留上次区域名 | 只应在 `active == 1` 时使用 |

### 29.4 兼容与回退（**按能力判断，别按版本号**）

- 建议判据：`const has = (resp.schemaFeatures || []).includes("regionPoints")` ⇒ 有则用新块，无则走旧逻辑（不报错）。
- **无破坏性变更**：所有新键都是**新增**；唯一语义变化是 `sandstorm.active` —— 旧版恒 0（判据错误），**v122b7 起才正确**，所以别把旧版的 0 当作"没沙尘暴"的证据。
- 部署状态（2026-10-07 01:5x）：**Sco = v122b10**（`electricalStorm.activeJudge` 存在即新版）；**其余 9 图 = v122b2**（无上述新字段，请按能力回退）。

### 29.5 采样证据（可复核，均在项目 `tmp/`）

| 证据 | 文件 |
|---|---|
| 沙尘暴前后**全字段 diff**（切换仅 16 项变化，无一项属 dust/材质/sweep） | `tmp\_dust_diff_out.txt` |
| 第 1 次真实沙尘暴（自然发生，用户目视确认沙墙）逐分钟记录 | `tmp\_wxwatch\V3SNAP_20261007_01*.json` |
| sweep 组专项（风暴中全 0/null；并暴露 400 属性上限坑） | `tmp\_sweep2_out.txt` |
| 强制切换时间线（雷暴/沙尘暴/晴天，含判据验证） | `tmp\_forcewx_out.txt` |
| 雷暴区域专项（`regionName="Center"` + `regionPoint` 匹配成功） | `tmp\_stormreg_out.txt` |
| 版本判定（`activeJudge` / `weatherName` 修复生效） | `tmp\_ver_check_out.txt` |

### 29.6 附：强制切换天气工具（仅供联调自测）

```
TransferIdentityFix.WorldProbe callfunc fn=MC_ChangeWeather p.New+Weather+Type=<id> p.Transition+Length=30 p.Reset+Particle+Emitters=1 apply=1
```
`id`：`0` 晴 · `2` 雨 · `3` 雾 · `4` 热浪 · `6` 沙尘暴 · `7` 雷暴（目视标定过的是 0/2/7/6）。省略 `apply=1` 为预演。
> ⚠️ 会**直接改变实服天气**（对在线玩家可见），联调用完请切回 `0`。

---

## 30. ⚡ v122b11 —— WorldProbe 只读子命令「响应 TTL 缓存」（照抄火山插件机制）

> **一句话**：八个只读子命令现在带**短 TTL 缓存**，引擎重复查询不再每次都重扫世界；后端 TTL 可以安全降到 **3 s**，前端秒级轮询由此成立。

### 30.1 覆盖范围

| 命令 | 缓存 |
|---|---|
| `weather` · `sandstorm` · `badwx` · `meteor` · `biometemps` · `wave` · `actor` · `zones` | ✅ 响应 TTL |
| `wxset` · `exec` · `callfunc` · `funcs` | ❌ **写入/调试类，永不缓存** |
| `volcano`（独立命令） | ✅ 早已有（本次即照抄它） |

### 30.2 机制（与火山一致）

- **键**：**完整命令行参数字符串**（`weather` 与 `weather slim=1` 是两条独立缓存，绝不串数据）；表上限 32 条，超出淘汰最早项。
- **TTL 命中** ⇒ 直接把上次的响应体回给调用方，**不扫描 actor、不读任何字段**（毫秒级）；响应里 `cache.cached=1`、`cache.ageMs` 给出陈旧毫秒数。
- **TTL 未命中** ⇒ 正常执行一次并把响应体存入缓存（`cache.cached=0`、`misses+1`）。
- **绕过**：命令行里出现 `fresh` 或 `rescan` 即完全绕过缓存（`zones` 的 `rescan=1` 也会重建它自带的静态列表）。
- **配置**：`probe_cache_seconds`（默认 **1**，v122b13 起由 3 降到 1；`0` = 关闭整个机制，上限 60）、`probe_rescan_seconds`（默认 **30**，10~600；v122b13 起同时作为「指针级缓存」的重扫节流）。
- **部署判据**：任意上述命令的响应里出现 **`cache`** 块即 v122b11 已生效。

### 30.3 响应新增字段

```json
"cache": { "cached": 1, "ageMs": 1234, "workUs": 18, "bypass": 0,
           "lastMissUs": 41250, "savedEstUs": 1237500,
           "cacheSeconds": 3, "rescanSeconds": 30, "sub": "weather",
           "key": "weather", "hits": 42, "misses": 15, "bypasses": 2, "bodies": 6 }
```

> v122b12 起多了 5 个字段（`workUs` / `bypass` / `lastMissUs` / `savedEstUs` / `key`）
> 和 `bypasses` 计数，含义见 §30.7。

### 30.4 前端约定（重要）

1. **常规轮询不要传 `fresh=1`** —— 吃到缓存是设计预期（最多陈旧 `cacheSeconds` 秒）。
2. **需要"绝对实时"时**（例如要捕捉变天瞬间、故障排查）才传 `fresh=1`。
3. 用 `cache.cached` 判断本次是否命中；用 `cache.ageMs` 判断数据新旧，**不要**因为 `cached=1` 就以为坏了。
4. 判据字段（`currentWeatherId` / `weatherName` / `active` / `regionName` / `regionPoints` …）语义**完全不变**，只是可能落后 ≤ `cacheSeconds` 秒。

### 30.5 后端可以做什么

- 本插件侧已能承受秒级轮询：`WP_ZONES_TTL_MS`（当前 60 s）**可以降到 3 s**（后端侧改动属独立任务）。
- 若后端仍想"每次都要最新"，可在后端请求里加 `fresh=1`，但那样会放弃插件的缓存收益。

### 30.6 待补（下一步）

- **指针级缓存**：TTL 到期时当前版本仍会重新枚举 actor；下一步把「已定位的 actor 指针集 + 属性偏移表」按 `rescan_seconds` 节流复用（火山 `VolcanoEnsure` 的完整做法），使 TTL 到期也只需毫秒级字段读取。
- 验证脚本已就绪：`tmp\_vfy122b11.py`（八命令连发三次对比耗时与 `cache.cached`、`fresh=1` 绕过检查、关键字段回归），**部署后运行**。


### 30.7 v122b12 补充：计时口径 + `fresh` 也回报 + meteor 修复

#### 为什么要有 `workUs`（重要，前端/后端都别再按耗时判断缓存）
- 实测：**同进程复用连接**连发 8 个命令，命中与未命中的耗时**几乎一样**，都在 **1.1~1.5 s**。
- 结论：这段耗时是 **RCON 往返地板**（建连 + 认证 + 服务端按回合处理），**与插件做了多少活无关**；
  调用侧（不管 python 还是后端 HTTP）**不可能**用耗时看出缓存有没有生效。
- 因此 v122b12 让**插件自己计时**并回报进 `cache{}`：

| 字段 | 含义 |
|------|------|
| `workUs` | **本次插件内部实际耗时（µs）**。未命中=完整世界扫描成本（通常几万 µs），命中=拷贝已存响应体（几百 µs） |
| `lastMissUs` | 最近一次完整扫描的耗时（µs），可当作「省下了多少」的参照 |
| `savedEstUs` | 命中累计估算节省（每次命中按 `lastMissUs` 计），仅供观感参考 |
| `bypass` | 本次是否是 `fresh=1`/`rescan=1` 强制重扫（1=是） |
| `bypasses` | 累计强制重扫次数（不计入 `misses`） |
| `key` | 归一化后的缓存键（`fresh`/`rescan`/`rescan=1` 已从键里剥掉） |

#### `fresh=1` / `rescan=1` 现在的行为（v122b12 变更）
1. 以前：**完全透传**内部响应，**不带 `cache` 块** → 调用方看不出状态。
2. 现在：照常返回 `cache{...}`，标 `bypass:1` + 该次全扫描的 `workUs`。
3. **刷新会写进归一化键**：`weather fresh=1` 之后紧接着的普通 `weather` 调用**直接命中刚刷新的数据**
   （键里剥掉 `fresh`/`rescan` 家族；其余参数 `slim=1`/`brief=1`/`fields=...` 仍保留在键里，不同参数不会串数据）。
   > ⚠️ 该条在 v122b12 首版**有缺陷**：只剥了裸写 `fresh`/`rescan`，**`fresh=1` 这种带值写法漏剥**，
   > 实测（2026-10-07 Sco）`weather fresh=1` 之后紧跟的 `weather` 仍 `cached=0`。
   > **v122b12d 已修正**（改成前缀匹配，`fresh*` / `rescan*` 全部剥离）。

#### meteor 修复（v122b12）
- **旧行为**：在**非 Extinction 图**（如 Sco）调 `meteor`，返回的 JSON **没有闭合的 `}`**（长度 169），
  调用方任何严格 `JSON.parse` 都会失败。自 v117 就存在——因为该命令只在灭绝图用，一直没暴露。
- **新行为**：非 Ext 图返回**完整 JSON**：`{"ok":true,"sub":"meteor","supported":0,
  "error":"no WeatherSystem actor exposes bMeteorFXActive (Ext-only field)", ...}`。
- 前端若之前对 meteor 做过容错/跳过，可改为按 `supported` 字段正常判断。

#### 部署判据
- 响应 `cache{}` 里出现 **`workUs`** ⇒ v122b12 已生效。
- 非 Ext 图 `meteor` 能被 `JSON.parse` 解析 ⇒ 修复已生效。
- 调 `weather fresh=1` 时 `cache.key` 回报为 **`"weather"`**（不带 `fresh=1`）⇒ v122b12d 已生效。

#### 实测收益（2026-10-07 Sco，插件自报 `workUs`）
| 命令 | 未命中（全扫描） | 命中（走缓存） |
|------|-----------------|---------------|
| `weather` | 255,534 µs（255 ms） | 6 µs |
| `sandstorm` | 92,456 µs | 2 µs |
| `wave` | 78,522 µs | 2 µs |
| `zones` | 43,919 µs | 1 µs |
| `meteor` | 42,574 µs | 2 µs |
| `badwx` | 41,259 µs | 1 µs |
| `biometemps` | 32,873 µs | 8 µs |

> 调用侧看到的 1.1~1.5 s 与上表无关（那是 RCON 往返地板）。一次 `weather` 全扫描省下约 **255 ms 的游戏线程时间**。


### 30.8 v122b13 指针级缓存（TTL 到期不再遍历全图）

#### 为什么
实测各只读命令的**插件内部耗时**（`cache.workUs`）与应答大小无关：

| 命令 | 应答字节 | v122b12 未命中耗时 |
|------|---------|-------------------|
| `wave` | 277 B | 78 ms |
| `zones` | 404 B | 44 ms |
| `meteor` | 169 B | 42 ms |
| `badwx` | 279 B | 41 ms |
| `biometemps` | 7.8 KB | 33 ms |
| `weather`（full） | 28.9 KB | 255 ms |

几百字节的应答也要 40~80 ms ⇒ 成本几乎全在**「遍历全图找目标对象」**，而不是拼 JSON。

#### 改了什么（只缓存地址，不缓存数值）
1. **类属性表缓存**：属性「名字 → 偏移/大小」只取决于 UClass（同类实例完全一致），
   现在按类建表一次并共用（UDS_*_Weather_C 有 737 项属性）。换图（世界指针变化）即整表清空。
2. **actor 索引缓存**：全图遍历改为一次性建「actor 指针 + 类名」索引，
   重建条件＝换图 / 表空 / 超过 `probe_rescan_seconds`（默认 30 s）。8 个只读命令共用它。
3. **`biometemps` 生物群系体积列表缓存**：`idx` 语义保持不变（仍是原 level 数组下标）。
4. **默认响应 TTL 3 s → 1 s**：TTL 到期不再触发全图遍历，所以「更实时」和「更省」同时成立。

#### 时效性说明（重要）
- 这两层缓存**只保存"对象在哪、字段在第几字节"**，每次应答的数值都是**当场从内存读取**。
- 因此**指针级缓存不会让数据变旧**；唯一可能看旧值的仍是第 ① 层响应 TTL（现在默认 1 s）。
- 「目标对象换人」（换图、实例重建）由三处兜底：世界指针变化即失效；用前按类名比对，
  不符立即重扫（不受 30 s 节流限制）；`fresh=1` / `rescan=1` 仍强制重扫。

#### `cache{}` 新增字段

| 字段 | 含义 |
|------|------|
| `ptrActors` | actor 索引里的对象数（该图全量 actor 规模） |
| `ptrBuilds` | 索引重建次数（正常应长期停在 1~2；每 `rescanSeconds` 才 +1） |
| `ptrHits` | 索引复用次数（每次调用 +1） |
| `ptrAgeSec` | 索引年龄（秒），≥ `rescanSeconds` 时下次调用会重建 |
| `clsBuilds` | 类属性表构建次数（远小于调用次数即正常） |
| `clsHits` | 类属性表复用次数 |

#### 部署判据
- `cache{}` 里出现 `ptrActors` / `ptrBuilds` / `clsBuilds` ⇒ v122b13 已生效。
- 连续调用同一个命令时 `workUs` 从「几万 µs」降到「几百~几千 µs」，且 `ptrBuilds` 仍为 1。


### 30.9 v122b14 / v122b15 三项优化（含两处**接口行为变化**，前端需知）

#### 背景：实测证明瓶颈是「全量遍历」，不是拼 JSON
| 时段 | 发现 |
|------|------|
| v122b13 后 | `weather` 仍 205 ms、`sandstorm` 仍 48 ms，而 `badwx/wave/meteor` 已降到 µs 级 |
| 定位 | 3 处**漏网的全量遍历**：`sandstorm.matinee[]`、`weather.ElectricalStormPoint`、`weather.electricalStorm.matinee[]` |

其中 `ElectricalStormPoint` 那处最贵：它对**全部 93,690 个 actor** 逐个调 `TifObjName`（FName→UTF8，≈1.8 µs/次）≈ **170 ms**，
而它其实只认类名为 `Note` 的注释对象（用 `actor ... byname=1` 实测确认）。

#### 做了什么
1. **候选列表记忆化**：新增 `TifWpSelect`，把「按类名筛出的候选指针」按 scope 缓存，
   随 actor 索引代次失效 ⇒ 同一过滤条件只在索引重建时扫一次。
   （v122b15 又把上面 3 处遍历也改成用它，雷暴锚点用类名 `Note` 预筛、马蒂尼用 `Matinee` 预筛，
   **名字判定逻辑保留，结果不变**。）
2. **`slim=1` 直接跳过 `dump_props`**：`fields[]` 在 slim 下本来就不发，
   所以那 738 项属性遍历/193 项深解码纯属白做。代价：slim 下 `probedProperties` / `matched` **恒为 0**（不再是真实计数）。
3. **`actor` 的对象名兜底改为 `byname=1` 显式开启**（默认关闭）：
   旧版对每个类名不匹配的 actor 都做一次 `TifObjName`（93,690 次 ≈ 172 ms）。

> ⚠️ **接口行为变化（两条，请前端确认）**
> - **`actor`**：若原来依赖「用对象名（如 `UAID_...` 后缀）当 filter」来选实例，
>   现在必须显式加 **`byname=1`**（不加则只按类名匹配）。仅按类名过滤的调用**不受影响**。
> - **`weather slim=1`**：`probedProperties` / `matched` 两个**诊断计数**恒为 0；
>   判据字段（`weatherState` / `wxSemantics` / `electricalStorm.regionPoints` / `matinee[]` …）**完全不变**。

#### 最终实测（Sco，插件自报 `workUs`，单位 µs）
| 命令 | v122b12 | v122b13 | v122b14 | **v122b15** | 总降幅 |
|------|--------:|--------:|--------:|------------:|------:|
| `weather slim=1` | 255,534 | 220,000 | 205,929 | **3,561 ~ 3,923** | **98.6%** |
| `weather full count=1` | — | — | 209,000 | **8,256 ~ 8,993** | 96% |
| `sandstorm` | 92,456 | 55,400 | 47,792 | **2,157 ~ 2,316** | **97.7%** |
| `wave` | 78,522 | 8,000 | 869 | **780 ~ 874** | 98.9% |
| `badwx` | 41,259 | 2,865 | 69 | **101 ~ 140** | 99.7% |
| `meteor` | 42,574 | 4,300 | 573 | **584 ~ 717** | 98.7% |
| `biometemps` | 32,873 | 2,100 | 1,987 | **1,867 ~ 2,339** | 94% |
| `zones` | 43,919 | 900 | 858 | **427 ~ 777** | 99% |
| `actor`（类名） | 172,000 | 172,000 | 1,997 | **1,968 ~ 2,088** | 98.8% |
| `actor ... byname=1` | — | — | 207,070 | 170,990 | （显式开启，仍慢，符合预期） |

- 说明：每次索引重建（世界变化 / 每 `probe_rescan_seconds`＝30 s）后的**第一次**调用会多花约 60 ms 建索引，
  之后 30 s 内全是上面表里的快值。默认响应 TTL 1 s，所以正常轮询几乎不会踩到重建点。
- **内容回归**：与优化前样本逐键对比 —— `weather slim=1` / `sandstorm` 键集**新增 0、丢失 0**；
  雷暴锚点 5 个（同名同序）、`matinee` 2 个（`Matinee_SandStorm` / `Matinee_ElectricStorm`）、
  `scopeProbe` 20 项、`dust` 11 键 / `weather` 9 键 —— **全部一致**。


### 30.10 陈旧性实证（2026-10-07，Sco，v122b15）

#### 一、逐字段对拍：缓存路径 vs 无缓存路径
方法：同一命令先按常规调（各层缓存全生效），紧接着加 `fresh=1`（绕过响应 TTL + 强制重新定位对象），
两边 JSON 去掉 `cache` / `worldTime` 后**逐字段比对**（脚本 `tmp\_staleness_check.py`）。

| 命令 | 结果 |
|------|------|
| `weather slim=1` / `sandstorm` / `badwx` / `meteor` / `wave` / `actor` | **完全一致 ✓** |
| `biometemps` | 仅温度差 ≈0.006 ℃（两次相隔 1.1 s，**世界真的在变**；两次都未命中 TTL，说明是现读值） |
| `zones` | 仅差它自己的诊断字段（`cached` / `scanAge`）；`zones[]` 数据一致 |

#### 二、TTL 命中体 vs 现场重建体（更硬的证据）
1 s 的响应 TTL 在"每次新建连接"的调用方式下永远命中不了（建连+认证约 1.2 s），
因此给项目客户端加了**同连接连发**（`rcon_client.send_rcon_burst_sync`，原单发路径未改动），
在一条连接上连发 `命令 → 命令 → 命令 fresh=1`（脚本 `tmp\_ttl_hit_test.py`）：

| 命令 | #1 重建 | #2 TTL 命中 | #3 fresh 重建 | #2 vs #3 逐字段 |
|------|--------:|------------:|--------------:|-----------------|
| `weather slim=1` | 53,691 µs | cached=1 ageMs=**627** workUs=**8** | 13,629 µs | **完全一致 ✓** |
| `sandstorm` | 11,924 µs | cached=1 ageMs=**567** workUs=**2** | 11,553 µs | **完全一致 ✓** |
| `zones` | 588 µs | cached=1 ageMs=**539** workUs=**2** | 48,690 µs | **完全一致 ✓** |
| `biometemps` | 31,907 µs | cached=1 ageMs=**695** workUs=**4** | 1,947 µs | 仅温度差 0.005~0.009 ℃（昼夜曲线真实变化） |

⇒ TTL 命中返回的就是"几百 ms 前那个真值"，**不是被冻结的旧值**；而各层指针缓存（类属性表 /
actor 索引 / 候选列表 / 体积表）**不参与数值**，只决定"去哪里读"，所以数值永远现读。

#### 三、唯一需要说明的理论窗口：**对象身份**，不是数值
所有缓存都不含数值，唯一的滞后是"**选中哪个对象**"这个决定，窗口 = `probe_rescan_seconds`（默认 30 s）。
触发条件很窄：地图里**同类的另一个实例**变成了"应该被选中的那个"，而旧实例仍存活且类名相同。

- 现实中最可能命中的只有 **GEN**：它有 5 套迷你地图天气对象，`weather` 会挑"正在计时的那一个"。
- Sco / Isl / Cen / Ext / Abe 等图**只有一个天气对象**，不存在"选哪个"的歧义（Sco 实测 `weatherActorCount=1`）。
- 三层兜底：
  1. **换图**（世界指针变化）→ 缓存立即整体失效；
  2. 对象销毁/内存被回收复用 → 类名比对失配 → **立即重扫**（不受 30 s 节流限制）；
  3. `fresh=1` / `rescan=1` → 立即重新定位 + 重建应答体。
- 若想更严：把 `probe_rescan_seconds` 从 30 调到 **10**（下限 10；代价＝每 10 s 一次约 60 ms 的索引重建）。

#### 四、结论
- **数值陈旧：不存在**（除响应 TTL 本身，且默认已从 3 s 降到 **1 s**，比优化前更实时）。
- **身份陈旧：存在理论窗口 ≤ `probe_rescan_seconds`（30 s）**，仅"同图多实例且选中条件随运行状态变化"时可能发生；
  当前只有 GEN 属于这种情况，且可用 `fresh=1` 立即消除。


### 30.11 v122b16 全服安全兜底 + 全服部署注意

#### 一、为什么要加兜底（避免"某张图悄悄少数据"）
v122b15 把雷暴锚点（`ElectricalStormPoint*`）的扫描从"对全部 actor 逐个比对象名"改成
"先按类名 `Note` 预筛、再比对象名" —— 这个 `Note` 是在 **Sco 实测**的。
若某张图的锚点类名不是 `Note`，那它 `wxSemantics.electricalStorm.regionPoints` 会**变空**（静默回归）。

#### 二、v122b16 做法：预筛 + 兜底（结果集按索引代次记忆化）
1. 先用类名 `Note` 预筛 → 比对象名含 `ElectricalStormPoint`；
2. **若一个都没找到** ⇒ 回退为"全量比对象名"（即原行为）；
3. 解析出的锚点列表按 actor 索引代次缓存 ⇒ 兜底全扫**每 `probe_rescan_seconds` 最多一次**，
   且只在真正需要它的图上发生（Sco 走快路径）。

⇒ 无论各图锚点类名是什么，`regionPoints` 都不会丢；已无需逐图核对类名。

> 同批另一处（`matinee[]`）**本来就带类名条件**（原代码即 `class 含 "Matinee"` + `对象名含 "Storm"`），
> v122b15 只是把"遍历方式"换成读缓存，**条件未变**，无回归风险。

#### 三、🔴 全服部署注意（实测发现）
1. **只推 dll，不要推 `package` 里的 `config.json`**。
   实测各图 `config.json` 都是**各自维护**的（`borrowable_classes` 项数与内容都不同，
   例如 Sco 有 `Beam`＝小天花板 / `Shipyard` / `Garage` 的本地命名，打包里是 12 项另一套类名）。
   覆盖会导致各图"可借结构清单"被换掉。
2. **`probe_cache_seconds` / `probe_rescan_seconds` 当前所有图都未写** ⇒ 走代码默认
   （响应 TTL **1 s**、重扫节流 **30 s**）。若想把"对象身份窗口"压到 10 s，
   需在**各图 config.json 手动加** `"probe_rescan_seconds": 10`（下限 10；代价＝每 10 s 一次约 60 ms 索引重建）。
3. **必须重启服务器**才会加载新 dll（AsaApi 不支持热重载）；
   验证方法＝看 `ArkApi_<PID>_<日期>.log` 的**最新文件名时间戳晚于 dll 构建时间**。
4. Bob 服务器**未安装该插件**（无插件目录，RCON 返回 `Server received, But no response!!`）；
   其余图在本次普查时**服务器未运行**（RCON 连接超时），因此除 Sco 外无法远程验证 —— 
   但 §30.11 一/二的兜底已把"逐图类名差异"这一唯一风险消除。


### 30.12 本轮改动通告（给前端的单独文件）

本轮（v122b12 → v122b16）的**面向使用方**说明已单独成文，便于直接转发：

- 插件项目：`接口文档\前端事件对接文档_全服_20261006.md`（本文件，§30.9 ~ §30.11 为技术细节）
- 前端项目：`报告\WorldProbe_本轮改动通告_20261007_v122b16.md`（**唯一通告来源**，含 2 处必须配合的行为变化、
  新增可选字段、已修 bug、建议后端优化项、性能/回归数据、部署状态与判据、需要前端回复确认的 3 个问题）

> 本文件与通告文件内容若出现冲突，以通告文件为准（通告面向使用方、更新更及时）。


### 30.13 v122b14 的 `slim` 回归与 v122b17 修复（含排查教训）

#### 一、问题（v122b14 ~ v122b16 期间存在）
- **`weather slim=1` 下 `weatherState` 变空**：
  - Sco：`weatherState = null`（整个语义块丢失，实测 `slim=1` 为空、不带 slim 为 38 键 / `semFieldsFound=31`）
  - Ext：仅 7 键、`semFieldsFound=1`、`family` 被误判为 `uds`（不带 slim 为 30 键 / 22 / `ext_gen`）
- 前端因此看到"插件未给全局天气名 / 条件不满足跳卡"。

#### 二、根因
`weatherState` 的全部数据（`sem_val` / `sem_sz` / `sem_bad` / `sem_wxname`）
是在 **`dump_props` 这个 738 项属性遍历函数内部顺带填充**的（源码注释原文：*"Semantically interesting
ones are always recorded (regardless of the filter) so weatherState stays populated"*）。
v122b14 为省下那次遍历的 200 ms，在 `slim=1` 下**整个跳过**了 `dump_props`
⇒ 语义数据失去来源。Ext 之所以还剩 1 个字段：`sem_val` 为空时会触发"换一个候选对象再 dump 一次"的兜底，
在 DayWeatherAgent 上捡到 1 个语义键，并把 `family` 判成 `uds`。

#### 三、v122b17 修复
`slim=1` 时改由新增的 `TifFillWeatherSem()` **从已缓存的类属性表**直接收集这些键
（`TifWeatherSemInteresting` 精确名单 + `CurrSequenceSettings` → 天气名），
按宽度取值规则与 `dump_props` **逐条一致**（8 字节非次正规 double / 4 字节 float（`DayNumber` 按 int）/
1 字节 byte），只是不再遍历全部属性 ⇒ `weatherState` 恢复且仍为**亚毫秒级**。

#### 四、排查教训（本项目的检查纪律）
1. **基线必须取在"改动之前"**：本次 v122b16 的"内容零回归"结论之所以漏掉这个回归，
   是因为对照样本 `_regress_weather.json` 采集于 **b14 之后**（两边都同样为空，diff 自然一致）。
   ⇒ 以后对拍一律使用 **改动前** 的存档（例：Sco 的 `tmp\_test_sco_raw\weather-slim_1_130039.json` 是 v122b11 时代样本）。
2. **改"跳过计算"前必须查副作用**：`dump_props` 表面只产出 `fields[]`，实际还填 `sem_val` 四个容器；
   凡是要跳过某段计算，先 grep 该函数体内对**外部变量**的写入。
3. 只读诊断字段（`probedProperties`/`matched`）与判据字段（`weatherState`）必须分开评估影响面。


### 30.14 v122b17 上线结果与前端确认事项（单独简报）

- 前端项目：`报告\WorldProbe_v122b17_上线结果与确认事项_20261007.md`（**本次上线结果 + 前端需确认的 3 件事**）
- 要点：v122b17 除 Val 外已全图生效；`weatherState` 恢复（Sco 38 键且与 v122b11 老样本键集一致）；
  前端 v4410 兜底保留、v4411 规则 b17 后除 Val 外不再触发；
  诊断计数 `semFieldsFound/semUnreadable` 各差 1（因 `CurrSequenceSettings` 计入 `sem_val`），下次构建对齐。
- 版本判据：dll `1,870,336 B / 2026-10-07 14:59:47`，md5 `b8252d25274e4940af22fc324cfd2b97`。


### 30.15 天气触发间隔：实测 + 权重推算（Sco，2026-10-06/07 长时守护）

> 问题：Sco 的「沙尘暴 / 雷暴 / 焚风」大概多久来一次？UDS 家族**没有** `TimerNextWeather`
> （读不到"下次变天时刻"字段），所以只能给**统计口径的"大概间隔"**，不能做倒计时。

**一、实测（60 s 采样；两轮守护 21:24~22:51 与 21:24~23:27，夜间接力至次日）**

| 观测项 | 实测值 |
|---|---|
| 任意天气切换间隔 | **14 / 22 / 14 / 22 / 14 分钟**（5 个间隔，均值 ≈ 17 分钟） |
| 窗口内抽到的天气 | 只有 `ClearSkies ↔ Heatwave`（晴 ↔ 热浪）；沙尘暴 0 次、雷暴 0 次、焚风 0 次 |
| 沙尘暴（自然发生） | 21:24 之前刚结束一次（守护起点 `CloudPreviousWeather=6`）→ **次日 01:09:41** 再起（`CloudNewWeather` / `CurrWeatherType 0→6`）⇒ **实测间隔 ≈ 3 小时 45 分**（自然样本仅 1 次） |
| 雷暴 / 焚风（自然发生） | 两个窗口内**均未抽到** ⇒ 无自然样本，只能推算 |

**二、权重推算（口径：每次变天独立抽签）**

- 平均单次天气时长 = Σ(概率 × 时长)：**白天 ≈ 13.0 分钟 / 夜晚 ≈ 13.5 分钟**（由 §1.x 权重表 + `WeatherEventLengths` 算得）
- 预计间隔 = 平均单次时长 ÷ 该天气概率：

| 天气 | 白天概率 | 夜晚概率 | 预计间隔（白天） | 预计间隔（夜晚） |
|---|---:|---:|---:|---:|
| 沙尘暴 `Sand_Dust_Storm`(6) | 11.4% | 11.8% | ≈ **1.9 小时** | ≈ **1.9 小时** |
| 雷暴 `ElectricalStorm`(7) | 4.5% | 11.8% | ≈ **4.8 小时** | ≈ **1.9 小时**（夜里明显更容易） |
| 焚风 `Superheat`(8) | 6.8% | **0%** | ≈ **3.2 小时** | **不出**（夜间权重 0） |
| （参考）热浪 `HeatWave_SE`(4) | 31.8% | **0%** | ≈ **41 分钟** | 不出 |
| （参考）三者任一出现 | 22.7% | 23.6% | ≈ **1 小时**就有一次 | ≈ 1 小时就有一次 |

**三、给前端的口径提醒**

1. 只适合显示「大概多久一次 / 概率量级」，**不要做倒计时**（UDS 家族无"下次变天"字段）。
2. 实测 3h45m 与推算 1.9h 的差距属正常：抽签服从几何分布、**方差很大**，且沙尘暴自然样本仅 1~2 次。
3. 概率**必须分昼夜**取表（见 §30.16）；热浪 / 焚风夜间权重为 0 ⇒ 夜里不会出现。


### 30.16 昼夜判定（选 Day / Night 权重表用）—— 全服字段对照

**一、全服实测（2026-10-07，`weather slim=1` × 10 图）**

| 图 | 天气家族 | 天气回复顶层 `worldTime` | `weatherState` 里的昼夜字段 |
|---|---|---|---|
| Isl / **Sco** / Cen | uds | ✅ 有 | ❌ **无**（`timeOfDay` / `dayNumber` 都缺） |
| Val | **实际 ext_gen**（当前**误报 `uds`**） | ✅ 有 | ✅ `timeOfDay`（⚠️ 其 `weatherState` 仅 7 键 = 尚未部署 v122b17；且 `family` 是**启发式推断** —— 缺 `CurrentWeather` / `TimerNextWeather` / `WindStrengthMPC` 时会**回落成 `uds`**（源码 `TransferIdentityFixAPI.cpp` L9052）⇒ 部署 v122b17 后应自动修正） |
| Abe | ab | ✅ 有 | ✅ `dayNumber` + `timeOfDay` + `timeOfDaySolsticeRemapped` |
| Ext / Ast / Rag / Los / Gen | ext_gen | ✅ 有 | ✅ `timeOfDay` |

**二、通用昼夜源（全服 10 图实测均可用，与天气家族无关）**

命令：`TransferIdentityFix.WorldProbe biometemps brief=1`
返回顶层：`day`（`DayNumber`）/ `dayTime`（`DayTime`）/ `worldSec`（`ReplicatedWorldTimeSecondsDouble`）/ `worldTime`。

⇒ **前端沿用现有昼夜状态选表即可**；UDS 三图 `weatherState` 缺 `timeOfDay` **不构成阻塞**（昼夜另有通用源）。
（补充实测：Sco 天气 actor 上直接 `probe=TimeOfDay,DayNumber` 均为 `null`；`Nighttime Factor = -5.6` 是恒定曲线倍率，
**不可当昼夜值用**；光照系 `SunlightBlendWeightNormalized` / `Seq_SunLightWeight` 等在天气 actor 上同为 `null`。）

**三、选表口径（与 §1.x 一致）**

- `WeatherWeights_Day` / `WeatherWeights_Night` 各 **8 槽**，**下标 `i` = `arrayProbe.presetTable` 顺序，不是天气 id**；
- 概率 = 该槽权重 ÷ **同组正权重之和**；ext_gen 家族改用其动态 `WeatherChances`；
- 取数命令：`TransferIdentityFix.WorldProbe actor filter=UDS_<图>_Weather props=1 probe=WeatherWeights_Day,WeatherWeights_Night,WeatherEventLengths top=1`。

**四、概率「套数」分家族（回答「非 UDS 是不是只有一套概率」）**

| 家族 | 图 | 概率来源 | 套数 | 是否要选昼夜 |
|---|---|---|---|---|
| **uds** | Isl / Sco / Cen（Val 修复前误报此族） | `WeatherWeights_Day` / `WeatherWeights_Night` | **2 套（静态配置）** | ✅ 必须按昼夜选表 |
| **ext_gen** | Ext / Ast / Rag / Los / Gen（Val 实测后应归此族） | `WeatherChances` | **1 套（游戏实时算好的当前值，已含昼夜影响）** | ❌ 不用 —— 它没有昼夜维度 |
| **ab** | Abe | `WeatherWeights_Day/Night` 与 `WeatherChances` 均 `null` | **0 套（不可读）** | —（需另挖槽名） |

⇒ 一句话口径：**UDS = 静态两套（要选昼夜）；ext_gen = 单套实时值（不用选）；Abe = 无**。

> ⚠️ 上述「ext_gen 单套实时值」与「Abe 零可读」沿用此前实测口径（§1.12 / §12）。
> 2026-10-07 当日复核未完成（终端两次不可用，绝对路径与子进程包装均无法识别解释器），
> `WeatherChances` 的**当前取值**与 Abe 的槽名均**待补一次现场复测**。
