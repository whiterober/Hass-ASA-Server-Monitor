# WorldProbe · 前端配合清单（2026-10-10）· 本轮插件改动对前端的影响与待办

> 背景：2026-10-10 插件连发 v122b19~b23（`callfunc` 指针参数 / 4 字节 int 读取修复 / `badwx` 时间基准与护栏 /
> `actor follow=` 新能力），现已 **10/10 图全量部署**（含 Isl，17:56 核对通过）。
> 本文汇总**前端需要配合改动的地方**，按优先级排列。

---

## 一、🔴 高优先：天气时长换算口径（修正"沙尘暴 80 s"）

**结论**：`WeatherEventLengths` 按 **`worldTime`** 计（实测 **≈1.00 游戏秒/现实秒**）；
前端的 **`÷5.3` 用的是 `dayTime`（昼夜走针）速度**（实测 ≈5.1）⇒ **差 5.3 倍**。

| 天气（下标=设置对象顺序，实测） | 表值（游戏秒） | **应显示（修正后）** |
|---|---|---|
| `ColdFront_SE` (0) | 800 | ≈13.3 分钟 |
| `ElectricalStorm` (1) | 425 | ≈7.1 分钟 |
| `Rain_SE` (2) | 750 | ≈12.5 分钟 |
| `Foggy_SE` (3) | 650 | ≈10.8 分钟 |
| `HeatWave_SE` (4) | 700 | ≈11.7 分钟 |
| `Clear_Skies_SE` (5) | 1200 | **20 分钟** |
| **`Sand_Dust_Storm` (6)** | **425** | **≈7.1 分钟** |
| `Superheat` (7) | 750 | ≈12.5 分钟 |

**前端待办**
1. 时长换算统一走 `worldTime` 基（可近似"游戏秒 = 现实秒"），**禁用 `dayTime` 速度（5.1~5.3）**
2. "到下次变天的间隔" = **表值 + 过渡时长**（Sco `WeatherTransitionLength` 实测 **120 s**）；
   例：`Clear_Skies_SE` ⇒ 1200+120 = **1320 s = 22 分钟**（与实测 22 分钟精确吻合）
3. 若需"本次天气已持续多久"，直接用 **`weatherState.worldTime − weatherState.changeStartTime`**（同为 worldTime 基）
4. **下标 ↔ 天气名映射经实测确认无误**（8 项设置对象名已逐项读出），无需改动

---

## 二、🟠 中优先：`badwx` 字段接入（仅 ext_gen 6 图适用）

**适用图**：Ext / Ast / Rag / Val / Los / Gen（`found=1`）；**UDS 4 图（Isl/Sco/Cen/Abe）`found=0` ⇒ 面板隐藏**

| 字段 | 用法 |
|---|---|
| **`firstAt`** | 该曲线点**首次学习时刻**（稳定）→ **用它当时间基准** |
| **`ageSec`** | `worldTime − firstAt`（服务端算好）→ 直接显示"已学习时长" |
| `lastAt` / `updatedAt` | 最后观测（活跃桶恒等于 `worldTime`）→ **不要用它算 age**（否则 age 恒 0、来回跳） |
| `samples` | **被观测次数**（每次调用 +1，**不是事件次数**）⇒ 只作"可信度"参考 |
| `driverPresent` | 0/1 —— **是否具备曲线驱动**；**只用它 + `factor` 决定 UI** |
| `factor` | 当前曲线系数；仅在 `driverPresent==1` 时有意义（**仅 Ext** 目前为 1） |
| `slots[].used` / `baseSuspect` / `ignoredSlots[]` / `baseSuspectCount` | `base` 可用性标记；**`base` 与 `ratio` 只当调试信息，不要做判据** |
| `reason` | 两种文案：① "has no bad-weather cooldown driver"（该图无此机制）② "exists … could not be read"（读取故障） |

**前端待办**：改用 `firstAt`/`ageSec` 显示时长；改用 `driverPresent` 决定面板显隐；`learned[]` 视为**内存态**（插件重载即清零）⇒ 空表/少样本要容错。

---

## 三、🟠 中优先：`electricalStorm` 口径（承接上一份通报）

1. 路径是顶层 **`wxSemantics.electricalStorm`**（不是 `weatherState` 内）
2. **仅 Sco（+Abe 有锚点但家族不同）** 具备区域点；**Val / Isl / Cen / Ext / Ast / Rag / Los / Gen 均为 `null`** ⇒ **隐藏面板，不要报"缺失"**
3. 判"是否在刮"用 `weatherState.currentWeatherId` 对照 `wxSemantics.presetTable`：
   - Sco 雷暴 = **7**；Val 电风暴 = **6877769**（`WeatherPreset_VAL_ElectricalStorm`）

---

## 四、🟡 低优先：`weatherState` 键数基线（用于自检 / 告警阈值）

| 图 | 键数基线 | 图 | 键数基线 |
|---|---|---|---|
| Isl | 31 ✓（已部署） | Ast / Rag / **Val** / Gen | **25** |
| Sco / Cen | 38 | Los | 26 |
| Abe | 22 | Ext | 30 |

⚠️ **Val 已从 7 键恢复为 25 键**（旧版残留问题已随本次部署修好）——若前端有"键数 < N 判异常"的逻辑，请用上表更新阈值。

---

## 五、部署状态与版本判据

- ✅ **已部署（10/10 图）**：Isl / Sco / Cen / Abe / Ext / Ast / Rag / Val / Los / Gen
  版本戳 **`Oct 10 2026 16:44:33`**；dll = **1,880,576 B**，md5 **`ca1abe84726e785a9781a2e9b1e90a4d`**
- ✅ 全图已核对：`weatherState` 键数逐图与基线一致（Isl 31 / Sco·Cen 38 / Abe 22 / Ext 30 / Ast·Rag·Val·Gen 25 / Los 26）
  ⇒ 新字段（`driverPresent` / `firstAt` / `ageSec` / `baseSuspectCount` 等）在适用图上均已可用，**无需再写“旧版缺失”分支**
- 部署方式：**只替换 dll，不覆盖各图 `config.json`**

---

## 六、新增能力（前端如需可用；我方运维用）

```
WorldProbe actor filter=<天气类> [propsIdx=N] follow=<指针数组属性> [followTop=N]
```
- 作用：把指针数组的**每个元素**的属性 dump 出来（本次用它读出 8 个 `UDS_Weather_Settings_C` 的真实顺序与字段）
- 布局自动探测（24 字节结构优先 / 8 字节纯指针回退），回包给出 `stride` 与 `validProbe`
- 不给 `follow=` 时，行为与旧版完全一致

---

## 七、待办汇总（前端）

| # | 事项 | 优先级 |
|---|---|---|
| 1 | 时长换算改 `worldTime` 基（≈1.0），间隔 = 表值 + 过渡 120 s | 🔴 高 |
| 2 | `badwx`：用 `firstAt`/`ageSec`/`driverPresent`，弃用 `lastAt` 作 age 基准 | 🟠 中 |
| 3 | `electricalStorm`：仅 Sco 显示区域点，其余隐藏 | 🟠 中 |
| 4 | `weatherState` 键数阈值按第四节更新（含 Val 25） | 🟡 低 |
| 5 | ~~Isl 未部署 ⇒ 字段缺失回退~~ **已解除**（10/10 全量部署完成） | ✅ 已完成 |

---

## 八、前端反馈：`weatherHistory.note` 体积优化建议（2026-10-10 晚追加）

**背景**：v4539 前端已全量接入 `weatherHistory`（期望增强 / 展示层 / 校验），并做了性能实测。

| 项 | 实测 |
|---|---|
| `weather` 响应（slim=1）总大小 | **5479 B** |
| `weatherHistory` 序列化 | **1439 B**（占响应 26%） |
| └ 其中 `note` 字段 | **1020 B（占该字段 71%）** |
| 实体数据（除 note） | ≈419 B |
| 前端解析 + 渲染开销 | 微秒级（500 次调用仅 0.1~0.2 ms，不可测量级） |

**建议**：`slim=1` 时省略 `note`（如首调携带一次、后续省略；full 模式保留亦可）。
- 收益：该字段体积 1439→419 B（**-71%**）；当前图每 3 s 轮询 ≈ 省 1 KB/3 s（未压缩；gzip 后约 -0.3 KB/次）
- 前端对 `note` **零依赖**（字段语义已固化进本文档及 v4539 代码注释）

**期望回应**：是否采纳 + 目标版本号。

---

## 九、前端反馈：`lastBad` 分类记录建议（2026-10-10 晚追加 #2）

**背景**：期望徽章需要"上次【特定天气】发生"的时间。现 `lastBad` 仅记"**最近一次任意坏天气**"：
最近坏天气 ≠ 目标天气时无法推断（例：陨石雨期望 vs 最近坏天气=热浪 → 前端只能显示"无记录"）。

**动机实例**（2026-10-10 实测）：Ext 变天 Cloudy→ClearSky（非坏天气）后，前端 v4539 曾用 `badwx` 桶年龄回退而**假报「刚翻篇」**（26 秒=桶年龄）；v4540 已删该回退（无真值即不显示期望徽章）。

**建议**（任选其一，均保留现有 `lastBad` 字段兼容不动）：
- `lastBadByName: { "MeteorRain": {at, agoSec, running, endedAt}, "Heatwave": {...}, ... }`（推荐，结构最简、查询直接）
- 或 `recentBad[]`：最近 N 次坏天气列表（建议 N=10，滚动覆盖）

**收益**：期望徽章（陨石雨/沙尘暴/暴风雪/雷暴）全图即刻可用真值；不再依赖 badwx 桶近似。

**期望回应**：是否采纳 + 目标版本号。
