# Bug 报告：`lastBad.endedAt` 写入「检测时刻」而非「真实结束时刻」（2026-10-12）

> **状态：✅ 已修复（v125 起，v125f 定稿）；仅 Isl/Sco/Cen 已部署，其余 7 图待升级**
> 发现场景：前端 tips「天气历史」的「持续时长」与理论值（=变天间隔）系统性不符。
> 数据源：直连 `POST https://data.whiterober.ccwu.cc/api/worldprobe_weather`（Ext / Rag / Los，`slim:0, fresh:1`）。

---

## 一、现象

- 「上次 X（结束于 A 前 · 持续 B）」中的 **B 系统性偏大**；
- 理论：某段坏天气的「持续」应 == 该段到下一段的「变天间隔」（已验证 recent 链 `dur(N) = gap(N+1)` 严丝合缝）；
- 实测偏差：**+33%（Ext）**、**+110%（Rag）**——空闲期越长偏差越大。

## 二、根因（证据链）

**`lastBad.endedAt` = 「某次外部调用检测到坏天气已结束的那一时刻」**，而非坏天气真实结束时刻。

| 图 | 字段 | 值（worldTime 秒） | 对照 |
|----|------|------------------|------|
| Ext | `lastBad.at` | 252330886.3 | = recent seq35.at（开始 ✔） |
| Ext | `lastBad.endedAt` | **252332577.4** | **= 该次响应里 `worldTime` 逐位相等**（=检测时刻） |
| Ext | 真实结束（recent seq36.at） | 252332163.28 | **早 414 秒**（变天后无调用 ⇒ 检测拖到本次查询） |
| Ext | `dur = endedAt−at` | 1691s ≈ 28.2 分钟 | 真实段长 1277s ≈ 21.3 分钟（**+33%**） |
| Rag | `lastBad.endedAt` | 238966930.63 | 真实结束（recent seq29 段末）=238964763.63 → **差 2167s** |
| Rag | `dur` | 4138s ≈ 69 分钟 | 真实 1971s ≈ 33 分钟（**+110%**） |
| Rag | 检测时点 | — | 落后本次查询 1449s ⇒ 检测发生在"查询之外的某次调用"（非自检） |
| Los | `lastBad.endedAt`（补录段） | 223788577.89 | = recent seq2.at **完全一致** ✔（补录值来自日志，正确） |

**关键对照**：
- **recent 链（自检写入）全部正确**：`dur(N)=gap(N+1)`、`endedAt`=下一条 `at`，精度 ≤5 秒；
- **lastBad 链（检测式写入）在"自然结束"场景歪**；仅"日志补录"的段正确；
- Ext 的 `endedAt` 与响应 `worldTime` **逐位相等** ⇒ 该次"结束判定"就是"本次查询"触发的（此前 414 秒无人调用 = 无检测）。

## 三、推断的机制（请求确认）

1. `lastBad` 的「开始/结束检测」**未纳入 `weather_autoscan`（5 秒自检）**——只在"下一次完整 weather 调用"时执行；
2. `endedAt` 写入"检测到结束那一刻的世界时间"，而非"身份发生变化的那一刻"；
3. 空闲期（无人查看）越长，误差越大。

## 四、修复建议

1. **`lastBad` 的开始/结束检测纳入自检路径**（与 recent 同源、同频）；
2. **`endedAt` 口径对齐 recent**：写"检测到身份变化的时刻"（≈ recent 里"下一条的 at"，≤5s 精度）——修复后 `lastBad.dur` 应与 `recent` 对应段完全一致；
3. （可选）增加审计字段：`endedAtSource` / 写入时的 `worldTime`；
4. （可选）自检时与 recent 交叉校验：`endedAt` 应 = "紧随其后的下一条变天的 at"。

## 五、复现方法

1. `POST /api/worldprobe_weather` body `{"server":"Ext","slim":0,"fresh":1}`：
   - 比较 `lastBad.endedAt` 与响应 `worldTime`（相等/接近 ⇒ 本次查询刚写入结束判定）；
   - 比较 `lastBad.endedAt−at` 与 `recent` 对应段的 `endedAt−at`（理论应相等，实测不一致）；
2. 空闲数分钟后再查一次：`lastBad.endedAt` 会"跳"到新的检测时刻 ⇒ 复现；
3. 反例对照：Los 补录段（endedAt 来自日志重建）两链一致 —— 证明"检测式写入"才是歪的。

---

*附：前端侧同期已修复一个独立小瑕疵（「持续」数值误过 `lbWxHistAgo`，被额外叠加 cacheAge+本地流逝虚胖数秒）；本报告的 lastBad 语义问题**前端无法兜底修复**（recent 32 窗口覆盖不了久远坏天气），需插件侧修复。*


---

## 六、修复与交付（2026-10-13 更新）

**状态：✅ 已修复（插件 v125 起；v125f 为当前定稿版）**

### 6.1 修复口径（与本报告建议一致）

| 建议 | 落地情况 |
|---|---|
| ① 结束检测纳入 5 秒自检 | ✅ `TifWxAutoScanTick` 内做 bad begin/end 维护，不再依赖前端调用 `weather` 命令 |
| ② `endedAt` 与 `recent` 同源 | ✅ 结束时刻改取**同源锚点**：`begin_at`（游戏自身过渡戳，与 `recent[].at` 同口径）> 观测窗口中点 `seen_prev + gap/2` > 调用时间 |
| ③ 审计字段 | ✅ 新增 `endedAtSource`：`gameStamp` / `observedWindowMid` / `callTime` / `unknown` |
| ④ 与 `recent` 交叉校验 | ✅ 同一锚点链路，精度 ≤ 5 s（自检周期） |

### 6.2 `endedAtSource` 取值对照（前端据此判断可信度）

| 值 | 含义 | 精度 |
|---|---|---|
| `gameStamp` | 游戏自身的天气过渡戳（**最优**，与 `recent[].at` 逐位同源） | 0 s |
| `observedWindowMid` | 观测窗口 `[上次自检, 本次]` 的中点 | ≤ 半个自检间隔（5 s 量级） |
| `callTime` | 兜底：调用时刻（仅前两者都不可用时出现） | 差 |
| `unknown` | **插件重载 / 服务器重启后**：值从磁盘恢复，但来源标签不持久化 | **值仍正确，仅标签未知** |

### 6.3 实测验收

- **Sco**：`endedAt == lastChange.at`（逐位相等）、`endedAtSource = gameStamp` —— 误差由修复前的 414 s 级降为 **0**
- **Cen**：`lastBad.endedAtSource = observedWindowMid`，`endedAt = 269363008.65`（本次运行期内产生）
- **Isl**：结构与 Sco 一致（`unknown` 系重启后未产生新结束事件所致）

### 6.4 部署状态

- ✅ 已部署：**Isl / Sco / Cen**（v125f，md5 `c32cc933e082c1d79a5b58c539582ee0`）
- ⏳ **Abe / Ast / Ext / Gen / Los / Rag / Val 仍为旧版**（v124m；Gen 为 v124p）⇒ **本 BUG 在这 7 图上仍然存在**
  - 其中 **Ext（偏差 414 s）与 Rag（偏差 2167 s）正是本报告的证据来源**，建议优先升级
- 升级方式：替换各图 `...\ArkApi\Plugins\TransferIdentityFixAPI\TransferIdentityFixAPI.dll` 后重启该地图

### 6.5 前端注意事项

- 「持续时长」请直接用 `endedAt − at`，不要再叠加 cacheAge / 本地流逝（前端此前已修）
- 遇到 `endedAtSource = "unknown"`：数值可用，建议 UI 降级标注，等下一次结束事件后自动恢复正常标签
- `recent[]` 链的 `endedAt` 一直正确（= 下一条的 `at`），无需改动
