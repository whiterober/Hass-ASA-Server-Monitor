# `weatherHistory` 变更通知（2026-10-11）

- **收件**：前端 / 数据消费方
- **主题**：`weather` 命令的 `weatherHistory` 从「只记最近一次」升级为「**最近 32 次变天 + 跨重启持久化 + 历史补录 + id 类图坏天气识别**」
- **现网版本**：**fix8**（2026-10-11 18:47 构建；`TransferIdentityFixAPI.dll` = `1,926,656 B`，md5 `4cbcfe644a91f233c97041183d13bda1`）
  - ⚠️ **判断某台是否已升级，请看 `/tif ping` 的 `build` 字段**（应为 `Oct 11 2026 18:47:12`）—— 实服 `config.json` 里的 `version` 是旧值，**不可作判据**；也不要只看 dll 文件的体积/时间（SMB 缓存会读到旧值，2026-10-11 实测踩过）
  - 10 台正在陆续重启；**没重启到的图仍按旧上限（8 条）返回**，请按数组长度取数
- **本轮全部改动总表见下方「零」节**
- **兼容性**：**新增字段，无破坏性变更**；旧解析逻辑继续可用（仍建议做字段存在性判断）

---

## 零、本轮全部改动（前端速览，2026-10-11 18:50 定稿）

| # | 改动 | 对前端的影响 | 要不要改代码 |
|---|---|---|---|
| 1 | **fix6**：新增 `recent[]` / `recentTotal` + 跨重启持久化（每台服务器一个内部 tsv） | `weatherHistory` 多出历史列表；`changes` / `badCount` / `lastBad` / `seq` 重启后**不再归零** | 新增字段，可用可不用 |
| 2 | **fix6d**：恢复失败的日志措辞（`NO LINES for this map`） | 无（服务端日志层面） | 否 |
| 3 | **fix7**：`recent[]` 上限 **8 → 32** | **不要再写死 8 条**（旧假设会截断显示）；历史跨度：按当前变天间隔 20~60 min 估算约 **16~32 h**；响应体积 **+3.4 KB/次**（9 图实测均值 7.3 → 10.9 KB，最大约 20 KB），延迟无变化（仍 1.2~1.7 s） | **建议改**：按数组长度 / `recentTotal` 取数 |
| 4 | **历史补录**：把服务器日志中重建的变天历史写进持久化文件 | 重启后 `recent[]` **一次性出现较长历史**（实测：Ext 23 条、Rag 13 条、Sco 8 条、Ast 6 条…）；补录条目的 `atEarliest` 为 `null`、`atSource="observedWindow"`（日志重建，只有起点无区间下界）——**属正常，不是异常** | 否（按既有口径解析即可） |
| 5 | **fix8**：id 类地图的**坏天气识别**（白名单：Ext `#id6` = `WeatherPreset_EXT_MeteorRain`、Isl `#id4` = `HeatWave`，表源=游戏 `WeatherPresetList`） | **Ext / Isl 的 `lastBad` 不再恒为 `null`**，且以后**自维护**：新的陨石雨/热浪开始 → 写 `name`/`at` 且 `badCount+1`；结束 → 写 `endedAt`。`name` 仍是 `#idN`，**id→名仍然由前端 `presetTable` 负责** | **建议改**：可去掉「Ext/Isl `lastBad` 必为 null」的兜底分支 |
| 6 | **save 失败日志**（`WARN WXHIST save …`） | 无 | 否 |
| 7 | **版本号**：插件 `PluginInfo` `0.5 → 0.6`（样例 config `0.5.0 → 0.6.0`） | 实服 `config.json` 的 `version` 字段仍是旧值（实测 `0.3.0`）⇒ **别用它判断版本**，用 `/tif ping` 的 `build` | 否 |

### 前端最小适配清单（5 条）

1. **别写死条数**：`recent[]` 现在最多 **32** 条；请用 `recent.length` 或 `recentTotal` 判断"有没有历史"。
2. **Ext / Isl 的 `lastBad` 可以正常读了**：仍是 `#idN`，用 `presetTable` 译名后套你们的坏天气表；null 兜底可保留，但已不是常态。
3. **补录条目 `atEarliest: null`** 属正常（日志重建的历史没有"上一次轮询"这个下界），不要当异常丢弃。
4. **轮询带宽**：单次响应比之前多约 3.4 KB；若轮询很密（≤2 s），如需"平时只给 8 条、打开面板再取全量"，可以提需求，我加一个 `recentLimit` 参数（默认 8、最大 32）。
5. **字段存在性判断继续保留**：部分服务器可能尚未重启（仍返回旧上限 / 无补录历史）。

---

## 一、新增了什么（响应字段）

```json
"weatherHistory": {
  "key": "BP_RAG_DayWeather_WeatherSystem_C",
  "source": "name",                       // name / id / none
  "idSource": "fname(weatherSystem)",
  "current": "Sandstorm",                 // 名字，或 "#idN"
  "lastChange": { "at": 238861424.55, "atEarliest": null, "atSource": "gameStamp",
                  "agoSec": 441.6, "from": "Rain", "to": "Sandstorm" },
  "lastBad":    { "name": "Sandstorm", "at": 238861424.55, "agoSec": 441.6,
                  "running": 1, "endedAt": null, "count": 3 },
  "changes": 11, "badCount": 3,
  "seenAt": 238861866.21, "prevSeenAt": 238861692.51,

  "recentTotal": 11,                      // ★ 新增：累计条目数（跨重启保留）
  "recent": [                             // ★ 新增：最近 32 次变天（fix7 起），新的在后
    { "seq": 11, "id": "Sandstorm", "prev": "Rain", "at": 238861424.55,
      "atEarliest": null, "atSource": "gameStamp",
      "endedAt": null, "running": 1, "seed": 0 }
  ]
}
```

| 新增字段 | 类型 | 含义 |
|---|---|---|
| `recentTotal` | number | 累计记录到的变天条目数（= 已发放的最大 `seq`）；**跨插件重载 / 服务器重启保留** |
| `recent[]` | array | 最近 **32** 次变天（**fix7 起；此前为 8**），按时间升序（**新的在后**） |
| `recent[].seq` | number | 条目序号（1 起递增，跨重载保留） |
| `recent[].id` | string | 该次变天后的天气身份（**原样**：名字 或 `#idN`，插件**不做** id→名翻译） |
| `recent[].prev` | string | 它替换掉的那个身份（首次为 `null`） |
| `recent[].at` / `atEarliest` / `atSource` | number / number / string | 同 `lastChange` 的三口径（`gameStamp` 精确 / `observedWindow` 区间） |
| `recent[].endedAt` | number | 该天气**结束**时刻（= 下一条的 `at`）；**仍在进行 ⇒ `null`** |
| `recent[].running` | 0/1 | 该条目是否**正在进行** |
| `recent[].seed` | 0/1 | `1` = **补种**条目（插件首次接触该图时从游戏 `PrevWeather` 槽补的，**弱提示**，见五.3） |

---

## 二、语义要点（务必按这个口径解析）

1. **时间基准**：所有时间戳都是**绝对 worldTime**，与响应顶层 `worldTime` 同一基准；`agoSec = worldTime - at`
2. **`atSource` 必须先看**：`gameStamp` = 游戏自身戳（**精确**）；`observedWindow` = 该图无起始戳，真实时刻落在 `[atEarliest, at]` 区间内（宽度 = 调用间距）
3. **`endedAt` 是推断值**：= 下一条条目的 `at`（即"被替换的时刻"），仍在进行的那条为 `null` 且 `running=1`
4. **持久化已生效**：`recent[]` / `changes` / `badCount` / `lastBad` / `seq` 在**插件重载 / 服务器重启后不再归零**
5. **落盘位置（服务端内部）**：每台服务器一个文件 `<DinoData>\wx_history_<服标识>.tsv`（如 `wx_history_Sco.tsv`）——**前端无需关心**，此处仅供排障时对照
6. **共享语义不变**：追踪器是**服务器全局共享**的，由**任意调用者**喂；`seenAt` / `prevSeenAt` 反映**全服上一次** `weather` 调用，不一定是你自己那次

---

## 三、前端需要做的事（只 3 件）

> **[2026-10-11 18:50 更新 · fix8]** Ext / Isl 的 `lastBad` **不再恒为 null**：Ext `#id6`（陨石雨）、Isl `#id4`（热浪）会被插件自己识别并持续维护。下面这段「自己算」的做法仍可作为**兜底 / 交叉校验**。

1. **`lastBad` 在 id 类图（Ext / Isl）上恒为 `null`** —— 这是**设计性空值**（插件按名字子串判坏天气，`#idN` 没有字母）。
   这两张图的"上次坏天气"请**自己算**：
   - 取 `recent[]` 中 **`seed=0`** 的条目（`seed=1` 只是弱提示）
   - 用 `wxSemantics.presetTable.entries` 把 `#idN` **译成名字**
   - 再套你们自己的坏天气名字表，取 `seq` 最大者
2. **字段存在性判断仍要做**：`if (wh.recent)` 再读（兼容将来降级 / 旧节点 / 未升级服务器）
3. **不要用服务端日志判断恢复状态**（见五.4）

---

## 四、各图实测矩阵（2026-10-11 14:30 全服只读实测）

| 图 | `source` | `idSource` | `current` 实测 | `recent[]` | 前端注意 |
|---|---|---|---|---|---|
| Sco | name | `weatherName(sem)` | PartlyCloudy | ✅ | 按名字判坏天气 |
| Cen | name | `weatherName(sem)` | PartlyCloudy | ✅ | 同上 |
| Rag / Val / Gen | name | `fname(weatherSystem)` | ClearSky | ✅ | 同上 |
| Ast | name | `fname(weatherSystem)` | ClearSky | ✅ | 同上 |
| Los | name | `fname(weatherSystem)` | ClearSkyV2 | ✅ | 同上 |
| **Ext** | **id** | `enum(holder)` | `#id1` | ✅ | **用 `recent[]` + `presetTable` 自判**（有 5 条 id→名：1 Cloudy / 2 Overcast / 3 Spooky / 5 ClearSky / 6 MeteorRain） |
| **Isl** | **id** | `enum(currWeatherType)` | `#id0` | ✅ | **无名字来源**（`presetTable=null`）⇒ 只能显示数字身份，无法判坏天气 |
| **Abe** | **none** | — | `null` | ❌ 0 条 | 该图**没有天气身份**（设计性），请按"无数据"处理 |

---

## 五、已知限制（请按"无数据/弱提示"处理）

1. **Abe（畸变）无天气身份** ⇒ `weatherHistory.source=none`、`recent[]` 为空；不是故障
2. **Isl（孤岛）无天气名** ⇒ `#id0` 无法译名，坏天气判定不可用
3. **`seed=1` 只是弱提示**：实测游戏 `PrevWeather` 槽**不等于"刚结束的那一个"**（反例：Ext 12:13 `#id1→#id5`，而 `prevWeatherId` 仍为 6）⇒ 算"上次坏天气"**优先用 `seed=0`** 的真实观测记录
4. **服务端日志措辞问题（临时，不影响字段）**：fix6c 及以前，日志 `WXHIST load restored …` **只要文件读到就会打**，即使没有本图的行（会出现 `recent=0 lastTo=` 空值）⇒ **假成功**。
   - **正确判读**：① 优先看响应字段 `prevSeenAt` 非 `null` ⇒ 确实恢复过；② 看日志则需 `recent>=1` 且 `lastTo=` 有值
   - 修正版 **fix6d 已构建但未部署**（`1,923,072 B` / md5 `e111d09eacf5912b51788ab70cd5fdf0`），将与下次必须重启的改动合批上线

---

## 六、性能与体积（实测，供容量评估）

| 项 | 数值 |
|---|---|
| 服务端计算 | 一次 map 查找 + 几次数值比较（<10 µs） |
| **体积** | `recent[]` 8 条约 **+1 KB**（`slim=1` 总响应 5.09 KB → 约 6.0 KB，+18%） |
| **延迟影响** | **实测不可测**：拿 `note` 的 1020 B 当量尺（2 图 × 5 次）—— Rag full 10018 B 平均 1183 ms vs slim 5707 B 平均 1323 ms；Ext full 7403 B / 1144 ms vs slim 5085 B / 1152 ms（slim 反而略慢，纯抖动；最小值 1157 / 1150 ms） |
| 磁盘 | 仅**变天时**写 1 次，且节流 ≥5 s ⇒ 轮询期间**零 I/O** |
| `slim=1` 口径 | **不裁剪** `recent[]`（保证任何时刻都能算出"上次坏天气"） |

---

## 七、验证证据（已完成的实测）

| 验证项 | 结果 |
|---|---|
| 全服版本 | 10/10 台 = fix6c（dll `1,921,536 B` @13:21:31，md5 `ad4744c09f31…`） |
| 全服字段 | 10/10 台 `weatherHistory` 正常；除 Abe 外均有 `recent[]`（各 1 条） |
| **跨重启恢复（Sco）** | 重启后 `prevSeenAt` = `274235026.33`（与落盘值 `274235026.32820195` **逐位一致**），日志 `WXHIST load restored` |
| **每服文件隔离** | 8 台已生成 `wx_history_<服>.tsv`（Sco 待下次变天；Abe 无需）——修复了"10 台共用同一 DinoData ⇒ 互相整文件覆盖" |
| Ext 补种路径 | 参与但无可补对象（`prevWeatherId == currentWeatherId`）⇒ 不产生 `seed=1` 条目（正确） |

---

## 八、参考文档

- 完整字段说明与前端口径：`WorldProbe_weatherHistory_前端详细对接_20261010.md`（本文是其"变更通知"版摘要）
- 接口权威说明：`接口文档\RCON接口与JSON数据结构说明.md` §3.11（a1）
- 服务端日志（排障用）：`<服务器>\ShooterGame\Binaries\Win64\logs\ArkApi_*.log`，关键字 `WXHIST`

> 有任何字段歧义，先看响应里的 `weatherHistory.note`（`full=1` 时返回）——它是插件侧的字段自述。

---

## 附录 B：历史变天 / 坏天气补录（2026-10-11 15:02 写入，重启后生效）

前端反映的「Ext 上次坏天气为 null」与「历史列表空」已按下面两条一起解决。

### B.1 直接读 JSON 就能拿到的（已写进各图持久化文件）

| 图 | 补入 `recent[]` 条数 | 其中坏天气 | 说明 |
|---|---|---|---|
| Ext | 6 | **2 场陨石雨** | `#id6`（前端映射 `WeatherPreset_EXT_MeteorRain`）：10-11 00:41→01:02、12:37→12:58 |
| Rag | 7 | 3 | ElectricalStorm(10-10 20:12)、Sandstorm(23:04)、Sandstorm(10-11 12:14) |
| Sco | 3 | 1 | Heatwave(10-10 18:53，30 min)；插件原有 2 条保留 |
| Ast | 3 | 0 | Fog/Rain/ClearSky/Rain_Fog 序列 |
| Los | 2 | 1 | Blizzard(10-10 22:30，809 min) |
| Isl | 1 | 0 | `#id0`→`#id2` |
| Cen / Val / Gen | 0 | 0 | 日志窗口内无变天，保持原样 |

同时补了 M 行 `lastBad`：**Ext = `#id6`**（12:37 起，20.4 min，`badCount=2`）、Rag = Sandstorm、Los = Blizzard。

### B.2 前端需要注意的三点

1. **补录条目的 `atEarliest` 为 `null`**（`atSource="observedWindow"`）：这些时间是从服务器日志重建的，没有"上一次轮询还在旧天气"的证据，只有起点 `at`。已有条目的字段不受影响。
2. **`recent[]` 上限：fix7 起为 32 条**（本次补录写入时上限仍为 8，fix7 部署时会同步重写 tsv 把历史行填到 32 条）。更早的历史（如 Rag 的 11 次变天）**不在 JSON 里**，需要全量历史请用 B.3 的静态文件。
3. **Ext 的 `#id6` 是 id 不是名字**：与既有约定一致，请用 `wxSemantics.presetTable` 映射；插件不会把 `#idN` 翻成名字。

### B.3 更早的历史（超出 8 条上限的部分）

- 人读：`b:\项目\ASA Transfer Identity Fix\tmp\_wxhist_retro.txt`
- 机器可读：`b:\项目\ASA Transfer Identity Fix\tmp\_wxhist_retro.json`（`{map: [{kind, logtime, cls, from, to, at, bad_from, bad_to}]}`）

### B.4 生效与回滚

- 生效：**服务器重启后**该图首次天气命令（插件在 `loaded==0` 时读盘一次），此后 JSON 即带补录历史。
- 回滚：`b:\项目\ASA Transfer Identity Fix\bak\wxhist_backfill_20261011_150218\` 下同名文件复制回 `DinoData` 覆盖即可。
- 免责：补录条目是**日志重建**（`src=observed`/`observedWindow`），精度受轮询间隔限制；坏天气的"结束时刻"取下一个已知变天时刻，可能与真实结束有几秒偏差。

---

## 附录 C：fix8（2026-10-11）—— 无名字的地图也能识别坏天气

### C.1 变更点
此前「坏天气」只按**名字子串**判定（`sand/heat/meteor/...`），而 **Ext 与 Isl 两张图根本不暴露天气名**
（Ext 只有 holder 枚举；Isl 的 `currentWeatherId`/`weatherName` 均为 null，只能读天气类型枚举）
⇒ 这两张图的 `lastBad` **在结构上恒为 `null`**，陨石雨/热浪再多也不会被记。

**fix8 起**，插件为这两张图各带一张 **id 白名单**（取自游戏 `WeatherPresetList`）：

| 图 | 坏天气 id | 名称 | 非坏天气 id |
|---|---|---|---|
| **Ext**（`BP_EXT_WeatherSystem_C`） | **`#id6`** | `WeatherPreset_EXT_MeteorRain`（陨石雨） | 1 Cloudy / 2 Overcast / 3 Spooky / 5 ClearSky（0/4 为 base） |
| **Isl**（`UDS_Island_Weather_C`） | **`#id4`** | `HeatWave`（热浪） | 0 ClearSkies / 1 Partly_Cloudy / 2 Rain / 3 Foggy / 5 ColdFront |

判定顺序：**先名字、后 id 白名单**（其它图逻辑一字未改，只在这两张图上"只增不减"）。
另外「两次调用之间发生并结束的坏天气」补救路径（`PrevWeather`）也接了同一张 id 表 —— Ext 的陨石雨
即使整场发生在两次轮询之间，也会被补记一条。

### C.2 对前端的影响
- Ext / Isl 的 `lastBad` **从此自维护**：新陨石雨/热浪开始时会自动写 `name`（`#id6` / `#id4`）、`at`、`badCount+1`，结束时写 `endedAt` —— **不再依赖维护方手工补录**。
- 值的形态不变：仍然是 `#idN`，**`id` → 名字仍由前端 `wxSemantics.presetTable` 负责**（与既有约定一致）。
- 历史补录值（Ext 现为 `#id6` @252235840.794，end 252237550.304，`badCount=3`）会**保留到下一场坏天气**。

### C.3 部署与验证
- 与 fix7 同一个 dll 上线；`/tif ping` 返回的 **`build`** 字段就是构建时间戳，可用来确认新 dll 真的生效。
- 前端无需改动即可受益；若原本对 Ext/Isl 做了"`lastBad` 必为 null"的兜底判断，可以改为正常读取。

---

## 附录 D：下次变天倒计时 与 游戏计数器（2026-10-11 实测，UDS 待验证）

**先纠一个容易误解的点**：`TimerNextWeather`相关字段**只在 BP/ext_gen 族有**（Ext/Ast/Rag/Val/Los/Gen），**UDS 族（Isl/Sco/Cen）完全没有** —— 2026-10-11 实测：Sco/Isl 的 `wxSystems` 是空数组、`activeWxIdx=-1`，88/162 个属性名里找不到 `TimerNextWeather` / `WeatherChangeTimerMin·Max`（也不在 `weatherHistory` 里）。

| 字段 | 位置 | 含义 | 实测（Ext 18:56） |
|---|---|---|---|
| **`secondsUntilChange`** | `weatherState` / `wxSystems[]` | **倒计时秒数（前端直接用这个）** | `1691.19` |
| `nextWeatherAt` / `timerNextWeather` | `weatherState` / `wxSystems[]` | 下次变天的**绝对时刻**（同 `worldTime` 基准） | `252246249.65` |
| `changeIntervalMin` / `changeIntervalMax` | 同上 | 变天间隔**配置区间**（不是计数） | `1000` / `2000` |
| `hasWeatherTimer` / `weatherTimerEnabled` | `weatherState` | `0` ⇒ 倒计时不可信（未初始化模板） | `1` / `1` |
| **`goodWeathersSinceBad`** | `weatherState` | 🔴 **游戏自带计数器**（原始字段 `GoodWeathersSinceBad`，int32）：连续好天气计数，遇坏天气归零 | `0` |

**用法与注意**
1. 要显示"还有多久变天"：读 `secondsUntilChange`；要自己算就 `nextWeatherAt - worldTime`。`hasWeatherTimer=0` 时请显示"—"。
2. 要"变了几次"：**游戏没有总计数器**（193 属性枚举 + 全库检索均无）⇒ 用 `changes` / `recentTotal` / `recent[].length`（插件观测计数）。
3. ⚠️ `goodWeathersSinceBad` **语义待定论**：实测 Ext 当前是好天气却为 `0` ⇒ 不是简单的"连续好天气 +1"；**UDS 图（Isl/Sco/Cen）是否也有该字段尚未验证**。未验证前请当实验性字段用，别拿它做硬逻辑。>
> **三张 UDS 图是否共享一个全局天气？—— 实测：不共享（2026-10-11 19:10）**：各图 `worldTime` 基准不同，先把
> `recent[].at` 换算成"**多久之前**"（`worldTime - at`）再跨图比对（±120 s 窗口）：**Isl vs Sco 0/32、
> Isl vs Cen 0/12、Sco vs Cen 0/24，全部 0 处重合** ⇒ `usingGlobalWeatherState=1` 指的是
> "**地图级全局态 vs 区域覆盖 volume 局部态**"，**不是跨图共享**。⇒ **前端不能"一图变天推其他图"**，
> 三图需各自轮询；要估"还有多久"只能用**本图** `recent[]` 的 `at` 差值。
> **⚠️ 名字表不完整（务必处理）**：实测 Sco 出现 `PartlyCloudy` 与 `PartlyCloudy_Thin`，**两者都不在
> `presetTable`（8 条）里**（表内 0=`Clear_Skies_SE`、2=`Rain_SE`、…，id 1 长期空缺）⇒ `current` /
> `recent[].id` / `lastChange.to` 都可能给出**表外名字**，请**原样透传**（显示原名或做兜底中文），
> **不要判为"未知/异常"或丢弃**。
