# WorldProbe · 沙尘暴「80 s vs 215 s」根因：**换算用错了时钟**（附权威顺序表）

> 日期：2026-10-10 17:05 ｜ 图：**Sco（32321，已部署 v122b23）**
> 起因：前端反馈链 —— ①游戏 `WeatherEventLengths` → ②API `lengths` → ③按预设表 index 映射 → ④`÷5.3` 换算 ⇒ 沙尘暴 80 s，与"实际 215 s"矛盾

---

## 一、结论（一句话）

**地图里的 `WeatherEventLengths` 是按 `worldTime` 计的（实测 ≈1.00 游戏秒/现实秒）；而前端用的 `5.3` 是 `dayTime`（昼夜走针）的速度** ⇒ 两者差 **5.3 倍**。
所以 `425 ÷ 5.3 = 80 s` 本身就是一个**维度错误**的产物；正确值是 **≈425 秒 ≈ 7 分钟**。

---

## 二、实测证据：两个时钟速度不同（Sco，3 组采样）

| 时钟 | Δ 采样 | 比率（游戏秒/现实秒） |
|---|---|---|
| **`worldTime`**（天气计时基准：`changeStartTime` / `BeginTime` / `timerNextWeather` 同量级） | 6.21 / 6.12 s<br>12.29 / 12.25 s | **1.015**<br>**1.003** ⇒ **≈ 1.00** |
| `dayTime`（昼夜走针） | 31.4 / 6.12 s<br>62.7 / 12.25 s | **5.13**<br>**5.12** ⇒ **≈ 5.1** |

⇒ 前端那个 `5.3` 来自**昼夜时钟**；但**时长表不属于昼夜时钟**。

---

## 三、权威顺序表（逐项实测，2026-10-10）

用 v122b23 新能力 `follow=WeatherSettings` 读出 8 个设置对象的真实名字与顺序：

```
TransferIdentityFix.WorldProbe actor filter=UDS_SE_Weather props=0 follow=WeatherSettings followTop=8
→ follow: found=1 num=8 stride=24 validProbe=8 items=8
```

| i | 设置对象名（实测） | `WeatherEventLengths[i]`（游戏秒） | **现实时长（÷1.0）** |
|---|---|---|---|
| 0 | `ColdFront_SE` | 800 | **≈13.3 分钟** |
| 1 | `ElectricalStorm` | 425 | **≈7.1 分钟** |
| 2 | `Rain_SE` | 750 | ≈12.5 分钟 |
| 3 | `Foggy_SE` | 650 | ≈10.8 分钟 |
| 4 | `HeatWave_SE` | 700 | ≈11.7 分钟 |
| 5 | `Clear_Skies_SE` | 1200 | **= 20 分钟** |
| **6** | **`Sand_Dust_Storm`** | **425** | **≈7.1 分钟** |
| 7 | `Superheat` | 750 | ≈12.5 分钟 |

✅ **前端的「下标 ↔ 天气名」映射完全正确**（此前只能推断，现已逐项证实）。
✅ **交叉验证**：`Clear_Skies_SE` = 1200 游戏秒 = **20 分钟**，正落在 10-06 长时守护实测的「变天间隔 **14~22 分钟**」区间内；若按 `÷5.3` 则只有 3.8 分钟，与实测完全不符。

---

## 四、为什么不是"游戏表里沙尘暴就是 425"或"沙尘暴口径特殊"

用同一命令把 8 个设置对象**逐个 dump 一层属性**，每个对象只有 **23 个属性**，且**全是效果参数、没有任何时长字段**：

```
Cloud Coverage / CloudSequenceSettings / ColdTemperatureModification / Dust / ElectricalStorm /
Fog / Fog Weather / HotTemperatureModification / JerboaWarningIndex / Material Dust Coverage /
Material Snow Coverage / Material Wetness / MoonColorMultiplier / NativeClass / Rain /
SkylightTemperature / Snow / SourceAngleMultiplier / SunColorTint / Thunder/Lightning /
Wind Intensity / Wind Variation / bOverrideSkylightSettings
```

⇒ 时长**只能来自那张并列的 `WeatherEventLengths`**（与设置对象同索引），沙尘暴就是 425 游戏秒。

---

## 五、前端"实际 215 秒"从哪来

`215 = 1140 ÷ 5.3` —— 说明那个"实际值"也是被**同一个错误比率**加工过的，并非原始读数。
若要拿到**逐次真实时长**，可用 `weather` 的两个字段直接量（同为 `worldTime` 基）：

```
本次已持续(游戏秒) = weatherState.worldTime − weatherState.changeStartTime
```

---

## 六、前端需要改的口径（建议）

1. **换算统一用 `worldTime` 基**：实测 ≈1.00 ⇒ 可直接把"游戏秒"当"现实秒"显示；
   若要更稳，改为**显示游戏秒**（并标注单位），避免再被两种时钟混淆。
2. **不要再用 `dayTime` 的速度（5.1~5.3）去换算时长类字段**（`dayTime` 只用于昼夜/日历显示）。
3. **"到下次变天的间隔" = 表值 + 过渡时长**：Sco 的 `WeatherTransitionLength` 实测 **120**（游戏秒），
   所以 `Clear_Skies_SE` 一轮 ≈ 1200 + 120 = **1320 s = 22 分钟**（与 10-06 实测 22 分钟**精确吻合**）。
4. 沙尘暴按修正口径应显示 **≈7 分钟**（而非 80 s）。

---

## 七、版本与可用命令

- Sco 已部署 **v122b23**：dll **1,880,576 B**，md5 **`ca1abe84726e785a78  → ca1abe84726e785a9781a2e9b1e90a4d`**，编译戳 **`Oct 10 2026 16:44:33`**
- 新增能力（本次用于取权威顺序）：
  `WorldProbe actor filter=<天气类> [propsIdx=N] follow=<指针数组属性> [followTop=N]`
  - 布局自动探测（24 字节结构 `id@0/UObject*@8/hash@16,20` 优先，回退 8 字节纯指针），回包给出 `stride` / `validProbe`
  - 逐元素 dump 一层属性（每元素 ≤120 属性）；不给 `follow=` 时行为完全不变
- 其余 9 图未部署：无 `follow` 能力（不影响既有命令）

---

## 八、仍待补的一项（可选）

「沙尘暴真实时长」目前仍是**按表推算**（7 分钟）。若要**实机验证**，可起一个低频守护（30~60 s 一次），
记录每次 `currWeatherType` 变化时刻与 `worldTime − changeStartTime`，抓到一次真实沙尘暴即可给出**实测值**。
需要的话说一声。
