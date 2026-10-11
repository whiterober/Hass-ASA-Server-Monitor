# WorldProbe `weatherHistory` 前端对接详细报告

- 日期：2026-10-10
- 插件：`TransferIdentityFixAPI`（WorldProbe 子命令族）
- 本次版本：**v122b24**（含 fix1 / fix2 / fix3 / fix4 四轮修订）
- 最新产物：`TransferIdentityFixAPI.dll` **1,894,912 B @ 2026-10-10 19:39:37**，md5 **`0b28dfd8b38fa133dda527d2bef6bc81`**（运行时构建戳 `Oct 10 2026 19:38:36`）
- 本文对应字段：`weather` 响应中**新增的顶层键 `weatherHistory`**
- 结论：**10/10 图均已上线 `weatherHistory`，全部图的 `weatherState` 键数与基线一致（零回归）**

---

## 一、一句话说明

游戏内存里**根本没有**"上次坏天气是什么时候"这种历史字段（Val 249 个属性全扫、Ext/UDS 亦无），
所以插件**自己记**：每次有人调用 `weather` 命令时，插件把"当前天气身份 + 变天时刻"记在内存里，
并在响应里回吐 `weatherHistory`。前端据此就能显示"上次变天 / 上次坏天气距今多久"。

---

## 二、字段结构（响应示例）

```json
"weatherHistory": {
  "key": "BP_RAG_DayWeather_WeatherSystem_C",
  "source": "name",
  "idSource": "fname(weatherSystem)",
  "current": "ClearSky",
  "lastChange": {
    "at": 229806201.43,
    "atEarliest": null,
    "atSource": "observedWindow",
    "agoSec": 47.78,
    "from": null,
    "to": "ClearSky"
  },
  "lastBad": {
    "name": null,
    "at": null,
    "atEarliest": null,
    "atSource": "observedWindow",
    "agoSec": null,
    "running": 0,
    "endedAt": null,
    "count": 0
  },
  "changes": 0,
  "badCount": 0,
  "seenAt": 229806249.20,
  "prevSeenAt": 229806201.43,
  "note": "……（字段自述，含语义要点）"
}
```

### 字段含义

| 字段 | 类型 | 含义 | 何时为 `null` |
|---|---|---|---|
| `key` | string | 追踪器键（该图天气持有者的类名），一图一条 | 不会 |
| `source` | string | 身份来源大类：`name` / `id` / `none` | 不会 |
| `idSource` | string | 身份来自哪个槽位（诊断用）：`weatherName(sem)` / `enum(holder)` / `enum(currWeatherType)` / `fname(weatherSystem)` / `fname(cloudSystem)` | 无身份时为 `""` |
| `current` | string | 当前天气身份：**名字**（如 `ClearSky`）或 **`#idN`**（无名字的图） | 该图无身份（Isl / Abe） |
| `lastChange.at` | number | **当前这个天气是什么时候开始的**（绝对 worldTime） | 从未成功记录 |
| `lastChange.atEarliest` | number | **观测窗口下界** = 上一次调用 `weather` 的时刻；仅当没有游戏戳时才给 | 有游戏戳时 / 首次调用 |
| `lastChange.atSource` | string | `gameStamp`（游戏自身绝对戳，**精确**）或 `observedWindow`（无戳图，用观测区间） | 不会 |
| `lastChange.agoSec` | number | `worldTime - at`（当前天气已持续秒数） | `at` 为 null 时 |
| `lastChange.from` / `to` | string | 上一次变天的**从 / 到**身份 | `from` 在首次 seed 时为 null |
| `lastBad.name` | string | 上一次坏天气的名字 | 从未记录到坏天气 |
| `lastBad.at` | number | 该坏天气**开始**时刻 | 同上 |
| `lastBad.atEarliest` | number | 该坏天气开始的观测窗口下界（无游戏戳图） | 同上 |
| `lastBad.atSource` | string | 同 `lastChange.atSource` | 同上 |
| `lastBad.agoSec` | number | 该坏天气开始距现在秒数 | 同上 |
| `lastBad.running` | 0/1 | 该坏天气**当前是否仍在进行** | 不会 |
| `lastBad.endedAt` | number | 该坏天气**结束**时刻（`running=0` 时有值） | 仍在进行 / 从未 |
| `lastBad.count` | number | 本插件生命周期内记录到的坏天气次数 | 不会 |
| `changes` | number | 记录到的**变天次数**（首次 seed 不计） | 不会 |
| `badCount` | number | 同 `lastBad.count`（顶层便捷字段） | 不会 |
| `seenAt` | number | **本次**调用时刻（= 同响应顶层 `worldTime`） | 不会 |
| `prevSeenAt` | number | **上一次**调用 `weather` 的时刻 | 插件重载后首次调用 |

---

## 三、时间语义（重要）

1. 所有时间戳都是**绝对 worldTime**，与响应顶层 `worldTime` **同一基准**：`agoSec = worldTime - at`
2. `atSource` 的两种取值含义完全不同，前端**必须先看它**：
   - `gameStamp`：用的是游戏自己的 `BeginWeatherTransitionTime`（绝对时刻）⇒ **精确**
   - `observedWindow`：该图**没有**可用的起始戳（例如 DayWeather 家族持有者的 `BeginWeatherTransitionTime` 是 `-100` 哨兵值），
     于是 `at` = 首次看到新天气的那次调用时刻，`atEarliest` = 上一次调用时刻（当时还是旧天气）
     ⇒ **真实变天时刻落在 `[atEarliest, at]` 区间内**，区间宽度 = 调用间距
3. `seenAt` 与 `prevSeenAt` 让前端**自测轮询间隔**；插件重载后首次调用 `prevSeenAt = null`（正常）
4. **首次调用只 seed 不计入 `changes`**：插件重载后 `changes=0`、`lastChange.from=null` 是预期行为，不是丢事件

---

## 四、各图取值矩阵（2026-10-10 19:31 全服实测）

| 图 | `source` | `idSource` | `current` 实测 | 坏天气判定 |
|---|---|---|---|---|
| Isl（孤岛） | `id`（fix4，**已上线已实测**） | `enum(currWeatherType)` | `#id0` | ❌ 无名字，不可判 |
| Sco / Cen（焦土 / 中心岛） | `name` | `weatherName(sem)` | `PartlyCloudy` | ✅ 按名字 |
| Abe（畸变） | **`none`** | — | `null` | ❌ 该图无天气身份（见六） |
| Ext（灭绝） | `id` | `enum(holder)` | `#id1` | ✅ 用 `wxSemantics.presetTable` 译名后判 |
| Ast（异星） | `name`（现 fix1）/ `fname(weatherSystem)`（升级后） | — | `Fog` | ✅ 按名字 |
| Rag / Val / Los / Gen | `name` | `fname(weatherSystem)` | `ClearSky` / `ClearSkyV2` | ✅ 按名字 |

### `#idN` 怎么变成名字（Ext / Isl）

- **Ext**：响应里同时带 `wxSemantics.presetTable.entries`，形如
  `{"i":0,"id":1,"hashIndex":1,"name":"WeatherPreset_EXT_Cloudy"}`
  ⇒ 用 `entries` 建 `id → name` 映射即可（实测 `weatherState.currentWeatherId=1` 与 `current="#id1"` 一致）
- **Isl**：**没有任何名字可用**（`weatherName=null`）⇒ 只能显示数字身份，无法翻译（见六）

---

## 五、"坏天气"判定口径（插件侧）

插件按**名字子串**判定（不区分大小写），命中集合：
`sand / dust / storm / avalanche / meteor / heat / superheat / electr / lightning / thunder /
volcan / tsunami / blizzard / tornado / radiat`

- 该口径**故意放宽**：宁可多记一条，也不漏（前端可再自行过滤）
- **仅在有名字的图上生效**（Ext 经译名、UDS 直接名字、DayWeather 家族 FName）
- 无名字图（Isl）与无身份图（Abe）⇒ `lastBad` 恒为 `null`，属**设计性空值**，请勿当成"没有坏天气"

---

## 六、两个已知限制（请前端按"无数据"处理，不是故障）

1. **Abe（畸变）没有天气身份**
   - 实测：持有者 22 个属性全是生物群系温度/曝光权重（`surfaceTemperature`、`exposure*Weight` …），
     5 个 `BP_AB_WeatherSystem_C` 的 `currentWeather/nextWeather/prevWeather` **全为 null**
   - 即该图**没有"当前天气名"这个概念** ⇒ `weatherHistory.source=none`、`current=null`
   - 若将来需要 Abe 的"上次坏天气"，得换信号源（如 `BP_AB_EarthquakeSystem_C` 地震），属**新特性**，需另行评估

2. **Isl（孤岛）没有天气名**
   - 其持有者 `UDS_Island_Weather_C` 既无 `CurrentWeather` 槽、也无 `weatherName`，该图也没有
     `WeatherSystem`/`CloudSystem` 角色（只有 4 个覆盖体积）
   - fix4 **已上线并实测**（运行时构建戳 `Oct 10 2026 19:38:36`）：Isl 现在
     `source=id`、`idSource=enum(currWeatherType)`、`current=#id0`（与其 `currWeatherType=0` **一致**），
     且 `lastChange` 正常计时（`agoSec` 随 `worldTime` 递增）⇒ 可拿到"上次变天时间"，
     但**无法翻译成名字**，因此坏天气判定不生效
   - 若将来要 Isl 的坏天气，需要先确认 `currWeatherType` 的数字含义（跨图枚举空间**未验证**）

---

## 七、前端接入建议

1. **继续用 `slim=1` 轮询**：`weatherHistory` 在 slim 输出里同样存在，体积不变大
2. **事件检测**：以 `changes` 自增 / `current` 变化为准；**不要**用 `lastChange.at` 变化来判（首次 seed 也会写 at）
3. **显示"上次坏天气"**：直接用 `lastBad.name / at / agoSec / running / endedAt`；`running=1` 表示**正在发生**
4. **显示"距上次变天"**：`lastChange.agoSec`（并可用 `atSource` 决定是否显示"约"字：`observedWindow` 是区间值）
5. **不要硬编码"某图一定有名字"**：先读 `idSource`/`source`；`source="none"` ⇒ 该图显示"暂无数据"
6. **注意追踪器是"服务器全局共享"的**：
   - 键为 **每图一个**（按持有者类名），**由任意调用者喂**（插件不区分来源）
   - 因此 `seenAt/prevSeenAt/atEarliest` 反映的是**全服上一次 `weather` 调用**，不一定是"你自己的上一次轮询"
   - 多消费者并发轮询只会让观测窗口**更窄、更精确**，不会互相覆盖出错（每次调用只做 O(1) 更新）
7. **重载语义**：插件重载 / 服务器重启后，`changes`、`badCount`、`lastBad.*` 归零（内存态）；
   如需长期留痕，请前端自己落库（推荐：把每次 `changes` 自增时的 `to/at` 记进自己的历史表）
8. **性能**：本字段每次调用只做一次 map 查找 + 几次数值比较（实测 <10 µs，`slim` 全响应约 3.5 ms）；
   **仅在变天时**写 1 行插件日志 ⇒ 高频轮询无压力

---

## 八、验证证据（本次上线）

| 验证项 | 结果 |
|---|---|
| 全服扫描 | **10/10 图**均有 `weatherHistory`；**全部图 `weatherState` 键数 = 基线**（Isl 31 / Sco,Cen 38 / Abe 22 / Ext 30 / Ast 25 / Rag,Val,Gen 25 / Los 26） |
| **真实变天实测**（Sco，18:53:45） | `PartlyCloudy → Heatwave`：`changes 0→1`、`lastChange.from/to/at` 正确、`lastBad.name=Heatwave`、`running=1`、`count=1`；插件日志**恰好 2 行**（`WXHIST change` + `WXHIST bad begin`） |
| **`prevSeenAt` 链式严格证明**（Abe） | A1 `worldTime=261122580.1`（首次 `prevSeenAt=null`）→ A2 `prevSeenAt=261122580.1` **完全相同** |
| DayWeather 家族身份路径（Val） | `idSource=fname(weatherSystem)`、`current=ClearSky`、`atSource=observedWindow`，与 `wxSystems[].currentWeather` 交叉一致 |
| Ext 回归 | `badwx` 的 b21/b22 字段全在（`found=1`）；`currentWeatherId=1` 与 `#id1` 一致 |
| **Isl fix4（数值身份）** | 构建戳 `Oct 10 2026 19:38:36`；`source=id`、`idSource=enum(currWeatherType)`、`current=#id0`（与 `currWeatherType=0` 一致）；`keys=31` = 基线；`prevSeenAt(I2)=286891023.58` 与 I1 的 `worldTime` **完全相同** |

### 版本矩阵（部署时点）

| 图 | 版本 |
|---|---|
| Isl | **fix4**（构建戳 `Oct 10 2026 19:38:36`，**已验证**） |
| 其余 8 图（Sco/Cen/Abe/Ext/Rag/Val/Los/Gen） | **fix3**（构建戳 `Oct 10 2026 19:07:43`） |
| Ast | 仍为 **fix1**（`Oct 10 2026 18:37:05`，有人在线未换；fix1 已含 `weatherHistory`，升级后 `idSource` 变为 `fname(weatherSystem)`） |

> 版本差异对前端**无影响**：`weatherHistory` 自 fix1 起即存在；fix2/fix4 只是让更多图**能取到身份**，
> fix3 追加 `prevSeenAt` 与 `atSource` 细化。建议前端做**字段存在性判断**，而不要依赖版本号。

---

## 九、待办 / 后续

| # | 事项 | 状态 |
|---|---|---|
| 1 | Isl 部署 fix4 | **已完成并验证**（2026-10-10 19:47，见八） |
| 2 | Ast 有空时升级到 fix4（用同一 dll md5 `0b28dfd8…`，可与 Isl 同轮，省一次重启） | 待用户部署 |
| 3 | 其他 8 图如需版本统一，后续再全服铺 fix4（同一 dll，行为无差异） | 待用户决定 |
| 4 | Abe 的"上次坏天气"是否要用地震信号做（新特性） | 待评估 |
| 5 | Isl 的 `currWeatherType` 数字含义确认（跨图枚举空间） | 待验证 |

---

## 十、修订历史（v122b24 四轮）

| 版本 | 内容 |
|---|---|
| fix1 | 新增 `weatherHistory`；`agoSec` 负值钳 0（游戏戳可比同响应 `worldTime` 超前几十毫秒） |
| fix2 | DayWeather 家族身份改取 **WeatherSystem 的 FName**（原用 CloudSystem，实测在 Val 是空壳）；新增 `atSource`/`atEarliest`/`idSource` |
| fix3 | 新增 `prevSeenAt`（上一次调用时刻），`atEarliest` 统一取自调用前快照 |
| fix4 | 新增 `currWeatherType` 数值身份回退（修孤岛 Isl 的 `source=none`） |

---

*本报告由插件侧生成，字段语义以插件响应中的 `weatherHistory.note` 为准。*
