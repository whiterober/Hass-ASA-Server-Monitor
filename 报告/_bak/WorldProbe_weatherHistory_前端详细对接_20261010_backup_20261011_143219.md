# WorldProbe `weatherHistory` 前端对接详细报告

- 日期：2026-10-10（初版）/ **2026-10-11（fix6 更新）**
- 插件：`TransferIdentityFixAPI`（WorldProbe 子命令族）
- 本次版本：**v122b24**（fix1 / fix2 / fix3 / fix4 / fix5 / fix6 / **fix6b** / **fix6c**，共八轮修订）
- 最新产物：`TransferIdentityFixAPI.dll` **1,921,536 B @ 2026-10-11 13:21:31**，md5 **`ad4744c09f312c7486df8cca8b180a53`**（fix6c；上一版 fix6 为 1,912,320 B md5 `f915d7bbdaf6df25d1c508ae86bce2ee`）
- 部署进度（2026-10-11 14:26）：**Sco / Ext 已升级 fix6c**，其余 8 台（Abe/Ast/Cen/Gen/Isl/Los/Rag/Val）仍为 fix6
- 本文对应字段：`weather` 响应中**新增的顶层键 `weatherHistory`**（fix6 起含 `recent[]` / `recentTotal`）
- 结论：**10/10 图均已上线 `weatherHistory`**；fix6 追加 **`recent[]`（最近 8 次变天）+ 落盘持久化**；插件**不翻译天气 id → 名字**，`#idN` 一律交前端用 `wxSemantics.presetTable` 解析
- ⚠️ **fix6 尚未部署到实服**：10 台现网仍是 fix3（8 台）/ fix4（Isl）/ fix1（Ast）⇒ **换 dll 前响应里没有 `recent[]` / `recentTotal`**，前端务必做**字段存在性判断**

---

## 一、一句话说明

游戏内存里**根本没有**"上次坏天气是什么时候"这种历史字段（Val 249 个属性全扫、Ext/UDS 亦无），
所以插件**自己记**：每次有人调用 `weather` 命令时，插件把"当前天气身份 + 变天时刻"记在内存里，
并在响应里回吐 `weatherHistory`。前端据此就能显示"上次变天 / 上次坏天气距今多久"。

**fix6（2026-10-11）两处增强**：
1. **`recent[]`**：不再只有"最近一次"，而是保留**最近 8 次变天**（各自带替换关系与结束时刻），
   并**落盘**到 `<DinoData>\wx_history.tsv` ⇒ 插件重载 / 服务器重启**不再清空**（配置 `weather_history_persist`，默认开）
2. **仍不做 id→名翻译**：`#idN` 原样输出，名字由前端用 `wxSemantics.presetTable` 解析
   （用户口径：「不翻，给前端翻」）—— 因此 `lastBad` 在 id 类图（Ext / Isl）上仍然恒为 `null`，
   **那两张图的"上次坏天气"改由前端从 `recent[]` 自行计算**（见七.3）

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
  "recentTotal": 9,
  "recent": [
    {
      "seq": 9,
      "id": "#id5",
      "prev": "#id1",
      "at": 252224203.22,
      "atEarliest": null,
      "atSource": "gameStamp",
      "endedAt": null,
      "running": 1,
      "seed": 0
    }
  ],
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
| `lastBad.count` | number | 记录到的坏天气次数（**fix6 起跨插件重载保留**；落盘前为内存态） | 不会 |
| `changes` | number | 记录到的**变天次数**（首次 seed 不计） | 不会 |
| `badCount` | number | 同 `lastBad.count`（顶层便捷字段） | 不会 |
| `seenAt` | number | **本次**调用时刻（= 同响应顶层 `worldTime`） | 不会 |
| `prevSeenAt` | number | **上一次**调用 `weather` 的时刻 | 换 dll / 删 `wx_history.tsv` 后首次调用 |
| `recentTotal` | number | 累计记录到的变天条目数（= 已发放的最大 `seq`；**fix6 起跨重载保留**） | 不会 |
| `recent[]` | array | **最近 8 次**变天条目（新的在后） | **换 fix6 dll 前该键不存在**（务必做存在性判断） |

`recent[]` 每项：

| 字段 | 类型 | 含义 |
|---|---|---|
| `seq` | number | 条目序号（1 起递增，**跨重载保留**） |
| `id` | string | 该次变天后的天气身份（**原样**：名字或 `#idN`，插件不译名） |
| `prev` | string | 它替换掉的那个身份（首次为 `null`） |
| `at` | number | 该天气**开始**时刻（`seed=1` 时为 `null`） |
| `atEarliest` | number | 观测窗口下界（同 `lastChange.atEarliest`） |
| `atSource` | string | `gameStamp`（精确）/ `observedWindow`（区间） |
| `endedAt` | number | 该天气**结束**时刻（= 下一条的 `at`）；仍在进行 ⇒ `null` |
| `running` | 0/1 | 该条目是否**正在进行** |
| `seed` | 0/1 | `1` = 补种条目（从游戏 `PrevWeather` 槽补的，**弱提示**，见三.6） |

---

## 三、时间语义（重要）

1. 所有时间戳都是**绝对 worldTime**，与响应顶层 `worldTime` **同一基准**：`agoSec = worldTime - at`
2. `atSource` 的两种取值含义完全不同，前端**必须先看它**：
   - `gameStamp`：用的是游戏自己的 `BeginWeatherTransitionTime`（绝对时刻）⇒ **精确**
   - `observedWindow`：该图**没有**可用的起始戳（例如 DayWeather 家族持有者的 `BeginWeatherTransitionTime` 是 `-100` 哨兵值），
     于是 `at` = 首次看到新天气的那次调用时刻，`atEarliest` = 上一次调用时刻（当时还是旧天气）
     ⇒ **真实变天时刻落在 `[atEarliest, at]` 区间内**，区间宽度 = 调用间距
3. `seenAt` 与 `prevSeenAt` 让前端**自测轮询间隔**；**fix6 起 `prevSeenAt` 跨插件重载保留**，
   仅两种情况为 `null`：① 该图**首次**被本插件看到；② 删除 `<DinoData>\wx_history.tsv` 后首次调用（即换 dll 后首调）
4. **首次调用只 seed 不计入 `changes`**：插件重载后 `changes=0`、`lastChange.from=null` 是预期行为，不是丢事件
5. `recent[]` 的 `endedAt` = **下一条的 `at`**（即该天气被下一天气替换的时刻）；仍在进行的那条 `endedAt=null` 且 `running=1`
6. `recent[]` 里 `seed=1` 的条目是**补种**（插件首次接触该图时从游戏 `PrevWeather` 槽补的）：`at=null`、`endedAt` = 当前天气的开始时刻。
   **实测 `PrevWeather` 并不等于"刚结束的那一个"**（反例：Ext 12:13 `#id1→#id5`，但 `prevWeatherId` 仍为 **6**，而 6 早在 01:02 就结束了）
   ⇒ `seed=1` 只能当**弱提示**，`seed=0` 才是插件亲见的**权威记录**（前端算"上次坏天气"请优先用 `seed=0`）

---

## 四、各图取值矩阵（2026-10-10 19:31 全服实测）

| 图 | `source` | `idSource` | `current` 实测 | 坏天气判定 |
|---|---|---|---|---|
| Isl（孤岛） | `id`（fix4，**已上线已实测**） | `enum(currWeatherType)` | `#id0` | ❌ 无名字，不可判 |
| Sco / Cen（焦土 / 中心岛） | `name` | `weatherName(sem)` | `PartlyCloudy` | ✅ 按名字 |
| Abe（畸变） | **`none`** | — | `null` | ❌ 该图无天气身份（见六） |
| Ext（灭绝） | `id` | `enum(holder)` | `#id5`（2026-10-11 实测） | ⚠️ **插件不判坏**（fix6 起由前端用 `recent[]` + `presetTable` 自判） |
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
- **fix6 起 id 类图（Ext / Isl）插件依旧不判坏**：`TifWxBadName` 按**名字子串**匹配，而 `#idN` 里没有字母
  ⇒ 结构上不可能命中，`lastBad` 恒为 `null`（**设计性空值**，不是故障）。这两张图的"上次坏天气"请**前端自己算**：
  1. 取 `recent[]` 中 `seed=0` 的条目
  2. 用 `wxSemantics.presetTable.entries` 把 `#idN` 译成名字
  3. 再套你们自己的坏天气名字表，取 `seq` 最大者
- **反例留证（2026-10-11）**：Ext 陨石雨 `#id6`（= `WeatherPreset_EXT_MeteorRain`）于 00:41 开始、01:02 结束（1258 s）；
  插件当时**在线且记录了这两次变化**（服务器日志 `WXHIST` 共 **9 行** = 响应 `changes:9`），但 `badCount` 仍为 **0** —— 因为身份是 `#id6`。
  纠正一个常见误判：这**不是**"插件重启把历史清了"（该实例已连续运行 16 小时未重启）

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
3. **显示"上次坏天气"**：
   - **有名字的图**（Sco / Cen / Rag / Val / Los / Gen / Ast）：直接用 `lastBad.name / at / agoSec / running / endedAt`；`running=1` 表示**正在发生**
   - **id 类图**（Ext / Isl，`source="id"`）：`lastBad` 恒为 `null` ⇒ 请从 **`recent[]`** 自算：
     取 `seed=0` 条目 → 用 `wxSemantics.presetTable.entries` 把 `#idN` 译名 → 套你们自己的坏天气表 → 取 `seq` 最大者
     （这张图也可以用 `wxSemantics.extWeather.prevName`，但它**不可靠**，见三.6）
4. **显示"距上次变天"**：`lastChange.agoSec`（并可用 `atSource` 决定是否显示"约"字：`observedWindow` 是区间值）
5. **不要硬编码"某图一定有名字"**：先读 `idSource`/`source`；`source="none"` ⇒ 该图显示"暂无数据"
6. **注意追踪器是"服务器全局共享"的**：
   - 键为 **每图一个**（按持有者类名），**由任意调用者喂**（插件不区分来源）
   - 因此 `seenAt/prevSeenAt/atEarliest` 反映的是**全服上一次 `weather` 调用**，不一定是"你自己的上一次轮询"
   - 多消费者并发轮询只会让观测窗口**更窄、更精确**，不会互相覆盖出错（每次调用只做 O(1) 更新）
7. **重载语义（fix6 起已变，fix6c 修正落盘位置）**：
   - **落盘位置**：**每台服务器一个文件** `<DinoData>\wx_history_<服标识>.tsv`（如 `wx_history_Sco.tsv`；配置 `weather_history_persist`，默认 `true`）
     —— fix6/fix6b 用的是单文件 `wx_history.tsv`，但 **10 台服务器共用同一个 DinoData 目录**，各服保存时会**互相整文件覆盖**（实测：Sco 的行会被别的图冲掉），**fix6c 改为每服一文件**，并额外“保存时保留其它图的行走”（双保险）
   - **旧文件迁移**：fix6c 首次运行时若新文件不存在，会回退读旧的共享 `wx_history.tsv`，**只取自己图的行**（一次性）
   - 插件重载 / 服务器重启后 `changes`、`badCount`、`lastBad.*`、`recent[]`、`seq` **都会恢复**，**不再归零**
   - 恢复实况看服务器日志（四种之一）：`WXHIST load restored map=… from=… lines=… recent=…`（**真恢复**）/ `WXHIST load … NO LINES for this map`（文件读到了、但没有本图的行）/ `WXHIST load … NOTHING TO READ path=…`（文件不在）/ `WXHIST load … SKIP: dino_data_dir is empty`
   - ⚠️ **判读陷阱（fix6c 及以前）**：那时**匹配 0 行也打 `restored`**（会出现 `recent=0 lastTo=` 这种“假成功”日志，2026-10-11 实测在 7 台上误报）⇒ **fix6d 起 `lines=`/`NO LINES` 才可信**；判“真恢复”看 `recent>=1` 且 `lastTo=<非空识别>`
   - 仍会从零开始的两种情况：① 该图**首次**被本插件看到；② `weather_history_persist=0`（退回旧内存态行为）
   - 仍建议前端自己落库（服务端删档 / 重建目录时该文件会丢）
8. **性能**（fix6 实测复测）：
   - **计算**：每次调用只做一次 map 查找 + 几次数值比较（实测 <10 µs）
   - **体积**：`recent[]` 8 条 ≈ **+1 KB**（slim 总响应 5085 → 约 6.0 KB，+18%）；
     延迟影响**测不出来** —— 拿 `note` 那 1020 B 当量尺（2 图 × 5 次）：
     Rag full 10018 B 平均 1183 ms vs slim 5707 B 平均 1323 ms；Ext full 7403 B / 1144 ms vs slim 5085 B / 1152 ms
     （**slim 反而略慢，纯网络抖动**，最小值 1157 / 1150 ms）⇒ 延迟由 RCON 往返 + 属性扇描主导（≈1.1 s）
   - **磁盘**：仅在**变天**（间隔 1000~2000 s）时写 1 次，且节流 ≥5 s ⇒ 轮询期间**零 I/O**
   - **日志**：仅在变天时写 1 行（`WXHIST change` / `WXHIST bad begin|end`）

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
| **fix6 构建** | `exit=0`、**0 error**；dll **1,912,320 B @ 2026-10-11 12:42:56** md5 `f915d7bbdaf6df25d1c508ae86bce2ee`（比 fix4 的 1,894,912 B 大 17 KB）；日志 `tmp\_wxhist_full.txt` |
| **1 KB 的性能实测** | `tmp\_wx_perf.py`：2 图 × 5 次 full/slim 对比 ⇒ **1 KB 在延迟上测不出来**（见七.8） |
| **Ext 陨石雨案例（根因铁证）** | 服务器日志 `WXHIST` 恰好 **9 行**，与 `changes:9` 一致；轨迹 `19:58 #id1→#id5 … 00:41 #id1→#id6（陨石雨开始）… 01:02 #id6→#id5（结束，1258 s）… 01:32、12:13` ⇒ 插件在线 16 h、亲见陨石雨，`badCount` 仍为 0（身份是 `#id6` 无字母） |
| **实服配置批量写入** | 10 台（Abe/Ast/Cen/Ext/Gen/Isl/Los/Rag/Sco/Val）全部加 `weather_history_persist: true`：每台 **+35 B / +1 行**，三重校验全通（逐行等值、键 24→25 且原键值逐项相等、写后 roundtrip 一致），`os.replace` 原子替换；备份 `bak\wxhist_cfg\` |

### 版本矩阵（部署时点）

| 图 | 版本 |
|---|---|
| Isl | **fix4**（构建戳 `Oct 10 2026 19:38:36`，**已验证**） |
| 其余 8 图（Sco/Cen/Abe/Ext/Rag/Val/Los/Gen） | **fix3**（构建戳 `Oct 10 2026 19:07:43`） |
| Ast | 仍为 **fix1**（`Oct 10 2026 18:37:05`，有人在线未换；fix1 已含 `weatherHistory`，升级后 `idSource` 变为 `fname(weatherSystem)`） |
| 全部 10 图 | **fix6 待部署**（`1,912,320 B @ 2026-10-11 12:42:56` md5 `f915d7bb…`）；**不换 dll 就没有 `recent[]` / `recentTotal`，也没有落盘持久化** |

> 版本差异对前端**无影响**：`weatherHistory` 自 fix1 起即存在；fix2/fix4 只是让更多图**能取到身份**，
> fix3 追加 `prevSeenAt` 与 `atSource` 细化。建议前端做**字段存在性判断**，而不要依赖版本号。

---

## 九、待办 / 后续

| # | 事项 | 状态 |
|---|---|---|
| 1 | Isl 部署 fix4 | **已完成并验证**（2026-10-10 19:47，见八） |
| 2 | **10 图部署 fix6**（`1,912,320 B` md5 `f915d7bb…`）—— `recent[]` / `recentTotal` / 落盘持久化 都靠它 | **待用户部署**（config 已预先改好，对旧 dll 无害） |
| 3 | Ast 仍 fix1，建议随 fix6 一起换（可与其它图同轮，省重启） | 待用户部署 |
| 4 | Abe 的"上次坏天气"是否要用地震信号做（新特性） | 待评估 |
| 5 | Isl 的 `currWeatherType` 数字含义确认（跨图枚举空间） | 待验证 |
| 6 | `PrevWeather` 槽位语义核查（实测不等于"刚结束的那个"，见三.6） | 待验证（影响 `seed=1` 条目的可信度） |
| 7 | 落盘文件 `<DinoData>\wx_history.tsv`（TSV：`M`=图状态 / `R`=最近条目），可用于事后人工核对 | 已实现 |

---

## 十、修订历史（v122b24 八轮）

| 版本 | 内容 |
|---|---|
| fix1 | 新增 `weatherHistory`；`agoSec` 负值钳 0（游戏戳可比同响应 `worldTime` 超前几十毫秒） |
| fix2 | DayWeather 家族身份改取 **WeatherSystem 的 FName**（原用 CloudSystem，实测在 Val 是空壳）；新增 `atSource`/`atEarliest`/`idSource` |
| fix3 | 新增 `prevSeenAt`（上一次调用时刻），`atEarliest` 统一取自调用前快照 |
| fix4 | 新增 `currWeatherType` 数值身份回退（修孤岛 Isl 的 `source=none`） |
| fix5 | `slim=1` 时省略 `weatherHistory.note`（该字段占体积 71%；实测 1439 → 419 B） |
| **fix6** | ①`recent[]` 环形列表（最近 8 次，含 `prev`/`endedAt`/`running`/`seed`）+ `recentTotal`；②首次接触该图时从游戏 `PrevWeather` 槽**补种**（`seed=1`）；③`g_wx_hist` **落盘**到 `<DinoData>\wx_history.tsv`（配置 `weather_history_persist`，默认开），重载不再清空；④上限 8→16 图（旧上限会驱逐活图）；⑤**仍不译名**（`#idN` 原样，交前端） |
| **fix6b** | 落盘恢复**失败重试 3 次** + 三条诊断日志（`restored …` / `NOTHING TO READ path=…` / `SKIP: dino_data_dir is empty`）—— 修“恢复失败与全新图在响应里无法区分”（实测：Sco 重启后 `prevSeenAt` 曾从应有值变回 `null`） |
| **fix6c** | **每服一个文件** `<DinoData>\wx_history_<服标识>.tsv`（10 台共用同一 DinoData 目录，单文件会被互相整文件覆盖）；保存时**保留其它图的行**；旧共享文件**一次性迁移**；日志增 `from=<实际读取路径>`。实测：Sco 恢复成功（`prevSeenAt` 精确回读）、Ext 新文件已生成 |
| **fix6d** | ①加载时统计**匹配行数**：0 行改打 `NO LINES for this map` 并 `return 0`（不再假报 `restored`，顺带最多重试 3 次）；②**恢复成功后置 dirty**，让每服新文件立刻生成（不再依赖旧共享文件）。实测依据：10 台全服上线后有 **7 台**出现“假 restored”日志 |

---

*本报告由插件侧生成，字段语义以插件响应中的 `weatherHistory.note` 为准。*
