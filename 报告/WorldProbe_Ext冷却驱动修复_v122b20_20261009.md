# WorldProbe · Ext 冷却曲线驱动修复（v122b20）· 前端通报

> 日期：2026-10-09 18:20 ｜ 范围：**仅 Ext（32324）已部署**，其余 9 图仍为旧版
> 起因：前端报「Ext 无冷却曲线驱动（`GoodWeathersSinceBad` 缺失）」

---

## 一、结论（一句话）

`GoodWeathersSinceBad` **一直在**，是插件**把 int32 当 float32 读**导致（读成次正规数 `1.4e-45`，`badwx` 又判成 "missing"）。
v122b20 已修，**Ext 实测生效**：`goodWeathersSinceBad=0`（整数）、`badwx.sinceBad=0`、`driverPresent=1`、`factor=0.8`。

---

## 二、根因（两处，同源）

| 入口 | 旧行为 |
|---|---|
| `badwx` | `TifReadNumByRef` 读到**次正规数直接丢弃** ⇒ `sinceBad=null` + 文案 "GoodWeathersSinceBad missing"（前端看到的就是它） |
| `weather`（slim） | `TifFillWeatherSem` 4 字节槽**没有 int 回退** ⇒ 把 int 当 float 发布 ⇒ `goodWeathersSinceBad = 1.4013e-45` |

属性原始字节实测：`hex=01000000`、`size=4` ⇒ **int32，值就是 1**（采样时显示 0/1 随游戏进程变化）。

---

## 三、修复内容（v122b20）

1. **4 字节槽统一处理**：float32 读数落在次正规区 ⇒ **按 int32 重解释**（不再丢弃/失真）；NaN/Inf 仍拒绝。
   `weather` 与 `badwx` 两条路径口径一致（顺带修掉同类字段，如 `JerboaWarningIndex` 那样的计数/索引）。
2. **`badwx` 新增 `driverPresent`（0/1）**，并把 `reason` 拆成两种，前端可据此区分"该图无此机制"与"我方读取故障"：
   - 无该属性：`this map has no bad-weather cooldown driver: GoodWeathersSinceBad is not present on <class> ...`
   - 有属性但读不出：`GoodWeathersSinceBad exists on <class> but its value could not be read ...`

---

## 四、⚠️ 前端必须知道的口径（全服 10 图实测，2026-10-09）

| 图 | 天气类 | `GoodWeathersSinceBad` | `WeatherChances` | 前端应如何显示 |
|---|---|---|---|---|
| **Ext** | `BP_EXT_WeatherSystem_C` | ✅ **存在（int32）** | 7 槽 | ✅ 显示冷却/驱动：`sinceBad` + `factor` |
| Ast | `BP_AST_DayWeather_WeatherSystem_C` | ❌ **属性不存在** | 7 槽 | ⚠️ 显示"该图无此机制"（**不要报缺失**），只用 `WeatherChances` |
| Rag | `BP_RAG_DayWeather_WeatherSystem_C` | ❌ 不存在 | 6 槽 | 同上 |
| Val | `BP_RAG_DayWeather_WeatherSystem_C` | ❌ 不存在 | 4 槽 | 同上 |
| Los | `BP_LC_DayWeather_WeatherSystem_C` | ❌ 不存在 | 5 槽 | 同上 |
| Gen | `BP_GEN_DayWeather_WeatherSystem_C` | ❌ 不存在 | 1 槽 | 同上 |
| Isl / Sco / Cen | UDS | ❌ 不存在 | ❌ 无（`badwx` 报 "no weather actor exposes WeatherChances"） | 面板隐藏 |
| Abe | ab | ❌ 不存在 | ❌ 无（同上） | 面板隐藏 |

**判据建议**：
1. 用 **`badwx.driverPresent`**（0/1）决定是否显示冷却相关 UI，**别再用 `reason` 是否出现/`sinceBad==null` 判断**；
2. `weatherState.goodWeathersSinceBad` 仅 Ext 有值，且**已是整数**（旧版会是 `1.4e-45` 这类次正规数，可作为"旧 dll"特征）；
3. `factor` 只有在 `driverPresent=1` 时才有意义（Ext：当前 `0.8`）；无驱动时 `factor=null`，其 slot `ratio` 只是**作者设定的权重**，不是曲线削减。

---

## 五、版本与部署状态

- Ext 已部署：`TransferIdentityFixAPI.dll` = 1,875,456 B，**md5 `5fd8557405b0999729b5bcc49b1d9eff`**，编译戳 **`Oct 9 2026 18:13:29`**
- 其余 9 图**尚未部署** ⇒ 那些图上 `driverPresent` 字段**不存在**（前端需容错：字段缺失 = 旧版，按"未知/不支持"处理）
- 本改动只影响**读取与文案**，不改变任何天气行为
