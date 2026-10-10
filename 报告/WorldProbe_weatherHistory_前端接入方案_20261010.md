# WorldProbe `weatherHistory` 前端接入方案

- 日期：2026-10-10 ｜ 状态：**待用户评审**
- 依据：`WorldProbe_weatherHistory_前端详细对接_20261010.md`（插件 v122b24，10/10 图已上线）
- 前端基线：v4538（badwx 护栏 + firstAt/ageSec 已接入）

---

## 一、背景与目标

游戏内存无天气历史 → 插件自己记（每次 `weather` 调用快照"当前天气 + 变天时刻"），响应回吐 `weatherHistory`。

**前端接入目标（三项）**：

| # | 目标 | 价值 |
|---|---|---|
| A | 期望徽章数据源增强 | "距上次发生"从间接推导（badwx 桶年龄）升级为真值直读（lastBad），并让非 Ext 图首次拥有期望数据 |
| B | 「上次变天 / 上次坏天气」展示 | 10 图新能力（此前仅 Ext 有数据体系） |
| C | badwx 校验能力（调试） | "变天误判"类疑问从此可自证（确定性检测 vs 桶机制对照） |

**总原则**：weatherHistory（事件事实）与 badwx（压制曲线/概率）**各司其职、不可互替**；所有展示对插件重载归零容错。

---

## 二、数据流与接入点

```
/api/worldprobe_weather (slim=1) → LB._wx.data.weatherHistory   ← 无需新请求（现有轮询已含）
```

| 项 | 说明 |
|---|---|
| 数据位置 | `LB._wx.data.weatherHistory`（属"当前 tab 图"；切图即变） |
| 轮询频率 | 现有面板 poll（2~3s/图）即喂数据；**精度=调用频率**（没人看的图窗口拉大） |
| 时间基准 | 全部绝对 worldTime；**显示成现实秒 = agoSec ÷ 走针 + cacheAge 补时 + 本地流逝**（与 v4538 同款） |
| 工具函数 | 新增 `lbWxHist()`（取当前图 history）+ `lbWxHistBadIs(name)`（lastBad 名称匹配） |

---

## 三、方案 A：期望徽章增强

### A1. 年龄来源优先级（目标天气 T）

```
1. weatherHistory.lastBad 匹配 T（名字子串）且 agoSec 有效  → 真值（首选）
2. badwx.learned.ageSec（现状，保持不变）                   → 回退（仅 Ext 有）
3. 两者皆无                                                 → 不显示（现状）
```

### A2. 名称匹配表（避免跨类误配）

| 目标天气 | 匹配词（插件坏天气集合内） | 陷阱说明 |
|---|---|---|
| 陨石雨 MeteorRain | `meteor` | — |
| 沙尘暴 Sandstorm / Sand_Dust_Storm | `sand` / `dust` | **不可用 `storm`**（与电风暴冲突） |
| 暴风雪 Blizzard | `blizzard` | — |
| 雷暴 ElectricalStorm | `electr` / `lightning` / `thunder` | **不可用 `storm`**（与沙尘暴冲突） |

### A3. 「正在发生」态（新）

`lastBad.running === 1` 且匹配 T → 期望徽章显示「**正在发生**」态（替代档词）。

- 文案待定（见七·待确认 #1）：`正在发生` / `进行中`
- 颜色建议：`#f97316`（橙，与"刚翻篇"灰区分）

### A4. 非 Ext 图的首次可用

9 图无 badwx `learned` → 之前期望徽章**算不出**（静默不显示）；接入后 lastBad 匹配即有值：

| 图 | 天气 | 期望徽章现状 | 接入后 |
|---|---|---|---|
| Ext | 陨石雨 | 有（learned） | 真值优先 |
| Los | 暴风雪 | 无（learnt 缺失） | **首开**（lastBad 匹配时） |
| Val | 雷暴 | 无 | **首开** |
| Sco/Ast 等 | 沙尘暴（视调用点） | 无 | **首开** |

> 注：`_gapR/_occR`（平均变天/发生间隔）链不变；仅 `_ageR` 来源升级。

---

## 四、方案 B：「上次变天 / 上次坏天气」展示

### B1. 显示规则（含坑位规避）

| 数据 | 显示条件 | 文案草案 |
|---|---|---|
| 上次变天 | **仅 `changes >= 1`**（seed 态不显示，防误导） | `上次变天 4分钟前`（`atSource=observedWindow` → `上次变天 约4分钟前`） |
| 上次坏天气 | `lastBad.name` 有值 | `上次坏天气 Heatwave · 1小时32分前`；`running=1` → `坏天气进行中：Heatwave` |
| 无记录 | `source=none`（Abe）/ `lastBad=null`（重载后） | `暂无记录`（不显示为错误） |
| Isl | `current="#idN"` | 仅时间（无名字）：`上次变天 约X前`；坏天气不支持 |

### B2. 显示位置候选（待定，见七·#2）

1. 陨石监控卡（Ext）底部行扩展（现有"数据来自游戏内实时事件"附近）
2. 天气浮窗基准温度卡附加行（所有图统一）
3. 徽章 tips 内追加一节（低入侵，先做这个最稳）
4. 服务器操作/主面板天气行

### B3. 文案格式

- 时间人性化：复用 `lbProbCycleTxt()`（秒/分钟/小时）
- 「约」字：`atSource === 'observedWindow'` 时加（区间值）

---

## 五、方案 C：badwx 校验能力（调试）

新增 `lbWxHistVerify()`（**不进 UI**，控制台/诊断调用）：

```
输出：learned.ageSec÷走针（桶年龄） vs lastChange.agoSec（真变天） vs lastBad（真坏天气）
判据：
- learned 说"刚有事件"但 weatherHistory 无对应坏天气 → 桶变化属正常学习（非事件）
- changes 自增且 to 与某天气吻合 → 真实变天（可作压制起点证据）
```

用途：下次"误判嫌疑"出现时，一条命令秒出结论（免去多轮取证）。

---

## 六、坑位规避清单（强制）

| # | 坑 | 规避 |
|---|---|---|
| 1 | 插件重载归零（Sco 今日实锤） | 所有显示容错"暂无记录"；不当故障 |
| 2 | seed 态 `lastChange.at` 是"插件首次看到"时刻 | **`changes=0` 不显示"上次变天"** |
| 3 | `lastBad` 仅"最近一次任意坏天气"、不分种类 | 名称匹配才用；不匹配回退 learned；即"上次陨石雨"≠"上次坏天气" |
| 4 | 观测窗口（observedWindow）是区间 | 显示加"约" |
| 5 | 精度=调用频率（没人看的图窗口拉大） | 显示可加数据年龄（`seenAt` 距今）标注；至少在文档说明 |
| 6 | Isl（#idN）/ Abe（none） | `source` 判断，显示"暂无数据"，不报错 |
| 7 | 走针换算 | agoSec÷走针 + cacheAge 补时 + 本地流逝（同 v4538 口径） |

---

## 七、待确认点（用户拍板）

| # | 事项 | 选项 |
|---|---|---|
| 1 | 「正在发生」文案/颜色 | `正在发生`(橙) / `进行中`(橙) / 不用该态 |
| 2 | 展示位置 | ①tips 内追加（最快）② 基准温度卡附加行 ③ 陨石卡底部 ④ 先不做 UI |
| 3 | 「上次变天」是否全图展示 | 全图 / 仅 ext_gen / 仅 Ext |
| 4 | 实施节奏 | 一次性（A+B+C） / 先 A+C 后 B |

---

## 八、实施规划（草案）

| 版本 | 内容 | 风险 |
|---|---|---|
| v4539 | 工具函数（lbWxHist/lbWxHistBadIs/lbWxHistVerify）+ 方案 A 期望增强 | 低（有回退） |
| v4540 | 方案 B 展示（按 #2 定案位置）+ 文案 | 低（新增行） |
| 部署 | `_deploy_cf.py` 一键；验证：Ext（seed 态显示"暂无记录"）/ Sco（已 changes=1 可验） | — |

---

## 九、附：实测快照（2026-10-10 20:15）

- **Ext**：`changes:0 / from:null`（seed 态）→ 方案 B1 规则下显示"暂无变天记录"；`lastBad` 空
- **Sco**：`changes:1`、`PartlyCloudy→Fog`、窗口 `[274171793.79, 274172471.41]`（可验证"约X前"文案）；`lastBad` 因 19:07 插件重载清零
- `seenAt/prevSeenAt`：≈4 现实秒间隔（本页面轮询在喂）
