# WorldProbe · `badwx` 字段与护栏（v122b21 + v122b22）· 前端通报 · 附四问答复

> 日期：2026-10-10 16:25 ｜ 范围：**仅 Ext（32324）已部署 v122b22**，其余 9 图仍为旧形态
> 起因：前端四问 —— ①非特殊天气为何新建 `learned` 桶 ②`slots[].base` 为何抖动 ③魔数 `7.1595e-9` ④触发点定位

---

## 一、四问答复（均以现场原始内存数据为证）

### ① `learned` 新建 `samples:1 / sinceBad:1 / ageSec:0` —— **不是事件检测**
`badwx` **没有任何事件判定**。`learned` 的桶键 = 驱动值 `GoodWeathersSinceBad`，**每个取值一个桶**，每次调用都学习一次：

| 观测量 | 真实含义 |
|---|---|
| 新桶出现 | **驱动值变了**（本次 `0 → 1`；实测原始值 `GoodWeathersSinceBad hex=01000000` = 1） |
| `samples` | **被观测次数**（每次 `badwx` 调用 +1；**不是事件次数**，实测 6 s 内 2→3） |
| `ageSec:0` | 该桶**刚创建**（首次见到该值） |

⇒ Weather=Overcast（非特殊天气）时出现新桶属**正常**：Overcast 是"好天气"，计数递增。
要"事件时刻"请用 **`firstAt`**，或直接用天气字段（`inTransition` / `currentWeatherId`）。

### ② `slots[].base` 为何抖（`1→0`、`1→7.1595e-9`）—— **游戏在改写那个数组**

同一槽在两个时点的原始 `PossibleWeatherChances`（double 解码）：

| 时刻 | `PossibleWeatherChances`（num=7） |
|---|---|
| 16:06 | `[0, 0, 1, **7.159e-09**, 0, 1, **7.159e-09**]` |
| 16:21 | **`[0, 1, 1, 1, 0, 1, 1]`** ← 自己变回来了 |

⇒ 它是**游戏掷骰过程中反复改写的 scratch 数组**，**不是作者常量**；插件输出与原始数组**逐项一致**（`WeatherChances` 同 `slots[].current` 亦逐项一致）⇒ **不是我方读取漂移**。
**⇒ 前端不要用 `base` 做判据**，只信 `driverPresent` + `factor`。

### ③ 魔数 `7.1595e-9` —— **确实存在于游戏内存**（非插件偏移错）
原始 `PossibleWeatherChances` 的第 4/7 项就是它（`dataHex` 片段 `…00000000f3bf3e3e…`），两个时点**完全一致** ⇒ **确定性残值**。
插件 `current`/`base` 与 raw 数组**逐项一致** ⇒ 排除"读到固定位置残渣"的插件侧问题。
⚠️ 但它会污染比率：`base=7.16e-9` ⇒ `ratio=1.1e8`；若该槽 `current=0` 还会把 `factor` 拖成 **0** ⇒ 已加护栏（见第三节）。

### ④ 触发点定位 —— 你的推算法成立
`learned[新桶].firstAt − learned[旧桶].lastAt = 351.42 游戏秒` ⇒ 正是**驱动值 0→1 跳变那一刻**。
插件侧有对应日志可对照：`WORLDPROBE badwx cls=… sinceBad=… factor=… samples=…`。

---

## 二、v122b21 —— `learned[]` 时间基准（修"age 恒 0 / 反复回跳"）

| 字段 | 语义 | 能否作 age 基准 |
|---|---|---|
| **`firstAt`** | 首次学习到该桶的 `worldTime` | ✅ **稳定，用它** |
| **`ageSec`** | `worldTime − firstAt`（服务端算好） | ✅ 直接用 |
| `lastAt` / **`updatedAt`** | 最后一次观测（活跃桶**恒等于 `worldTime`**） | ❌ **不要用** |
| `samples` | 被观测次数（非事件数） | — |
| `sinceBad` / `factor` | 桶键 / 该点曲线因子 | — |

> `learned[]` 是**内存态**：插件重载/服务器重启即清零 ⇒ 前端需容错（空表、`samples` 很小）。

---

## 三、v122b22 —— `base` 残值护栏

`slots[]` 每项现为 `{i, current, base, ratio, used[, baseSuspect]}`，顶层新增 `ignoredSlots[]` 与 `baseSuspectCount`：

| 字段 | 含义 |
|---|---|
| `used:1/0` | 该槽**是否参与了 `factor`** 计算 |
| `baseSuspect:1` | 该槽的 `base` **不能当分母**（`base < 1e-3` 或 `> 10`，**含 `base=0`**） |
| `ignoredSlots[]` | 被排除的槽下标（如因 `ratio > 10` 等异常） |
| `baseSuspectCount` | 被标记为不可用基准的槽数 |

**效果**：荒唐比值（`1.1e8`）不会再出现；`current=0` + 残值 base 把 `factor` 拖成 0 的路径已堵。
**前端建议**：只用 `driverPresent`（是否支持该机制）与 `factor`（当前曲线系数）；`base` / `ratio` 视为调试信息。

---

## 四、部署后实测（Ext 32324，`build = Oct 10 2026 16:08:48`）

```
baseSuspectCount=2   ignoredSlots=[]   factor=0.8   chanceSum=4.6   driverPresent=1
i=0 current=0   base=0 ratio=None baseSuspect=1 used=0
i=1 current=1   base=1 ratio=1                used=1
i=2 current=1   base=1 ratio=1                used=1
i=3 current=0.8 base=1 ratio=0.8              used=1   ← 真实削减 0.8
i=4 current=0   base=0 ratio=None baseSuspect=1 used=0
i=5 current=1   base=1 ratio=1                used=1
i=6 current=0.8 base=1 ratio=0.8              used=1   ← 同上
learned[0]: {sinceBad:0, factor:0.8, samples:2, firstAt:252157865.65, lastAt:252158054.77, ageSec:189.121}
```

✅ 新字段上线 ／ `factor` 合理 ／ v122b21 字段未回归 ／ 本次样本游戏数组恰好干净（残值未出现）⇒ 无 `ignoredSlots` 条目属正常。

---

## 五、版本判据与容错

| 图 | dll 状态 |
|---|---|
| **Ext（32324）** | ✅ v122b22：**1,877,504 B**，md5 **`0d5eb7e06fc8028b0d2dec38bbfe0c76`**，编译戳 **`Oct 10 2026 16:08:48`** |
| 其余 9 图 | ❌ 未部署 ⇒ **`baseSuspect`/`used`/`ignoredSlots`/`baseSuspectCount` 字段不存在**，`learned[]` 也无 `firstAt`/`ageSec`/`updatedAt` ⇒ 前端做**字段缺失回退** |

---

## 六、可选改进（待确认）

目前 `baseSuspect` **把 `base=0` 也算作"不可用"**（语义 = 不能当分母），因此 `baseSuspectCount` 常为 2。
若前端希望区分「**缺失**」与「**残值异常**」，可拆成两个标记：`baseMissing`（=0 或缺）／`baseSuspect`（过小/过大）。
**该项尚未实施**，需要请在群里说一声。
