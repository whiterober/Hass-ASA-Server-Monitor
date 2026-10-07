# WorldProbe `weather` 命令性能优化建议（指针缓存）

> 来源：dino-import 天气面板"秒级刷新"需求评估 · 2026-10-07 · 基于实服实测数据
> 交付对象：插件（TransferIdentityFix / WorldProbe）开发者

## 1. 背景

dino-import 前端（粑粑服搞事系统）希望把「游戏内切换天气 → 网页可见」延迟从当前的 ~76 秒压到秒级，以便玩家完整看到变天扫描进度。评估中发现瓶颈全部在 `weather` 命令本身。

## 2. 实测数据（Sco 焦土，RCON 直连 192.168.199.3:32321）

| 命令 | 耗时（端到端 RCON） | 响应大小 |
|---|---|---|
| `WorldProbe weather full=1 limit=1 slim=0` | **4.32 / 6.31 / 6.31 / 6.29 / 6.29 / 6.31 / 6.43 s**（7 次采样） | 28 KB |
| `WorldProbe weather full=0 slim=0` | **6.29 / 6.30 s** | 30 KB |
| `WorldProbe weather full=0 slim=1` | **6.31 / 6.30 s** | 14.7 KB |
| `WorldProbe weather full=1 slim=1` | **6.29 s** | 14.7 KB |
| `WorldProbe types`（同插件） | **0.053 s** | 3.6 KB |
| `TransferIdentityFix.Volcano`（对照：火山插件） | **0.004 / 0.035 / 0.030 s** | 81 B |

**关键观察：**

1. `weather` 的任何参数组合耗时几乎一样（≈6.3s），**与输出数据量完全无关**（14.7 KB 与 30 KB 同速）⇒ 瓶颈不是序列化/传输，而是**采集过程本身的固定成本**（每次调用实时重扫世界对象）。
2. 同一 RCON 通道上，`types` 与 `Volcano` 都是**毫秒级** ⇒ 通道、网络、RCON 服务均无问题。
3. 火山插件**已有指针缓存机制**（`cache.cached` / `scans` / `rescanSeconds=120s` / `cacheSeconds=1s`），所以 3 秒级轮询在生产上毫无压力。

## 3. 现状负载（为什么当前只能 60s 一次）

后端 `dino_backend.py` 当前 `WP_WEATHER_TTL_MS = 60000`：

- 单次采集 ≈6s ⇒ 每分钟 1 次采集 ≈ **游戏线程 10% 占用**（可接受）
- 若 TTL 降到 10s：每分钟 6 次 ⇒ **≈60% 占用**（明显卡顿 —— 这正是 2026-10-06 把 TTL 从 10s 升到 60s 的原因）
- 若 TTL 降到 3s（秒级目标）：**采集（6s）追不上周期（3s），队列永久堆积 ⇒ 不可行**

## 4. 优化建议（参考 Volcano 插件的成熟机制）

### 4.1 指针缓存（首要）

- 首次调用时扫描定位天气相关对象（GameState / weather actor 等），**保存指针**
- 后续调用直接读缓存指针（校验有效性；失效或跨地图切换时重扫）
- 重扫限流：参照 Volcano 的 `rescanSeconds=120s`（全量扫描最低间隔）

### 4.2 短窗复用

- 参照 Volcano 的 `cacheSeconds=1~3s`：同窗口内的重复调用直接复用同一份结果
- 目标：连续调用第 2 次起 P95 **< 100ms**

### 4.3 可选：轻量模式

- 新增如 `weather lite`（或参数 `light=1`）：只返回前端契约键（当前天气名/id、过渡进度、沙暴状态等），不带 28KB 全量字段
- 供高频轮询使用；完整模式保持现状供详细面板使用

## 5. 验收标准

1. 连续 10 次 `weather` 调用（间隔 1s）：**第 2 次起 P95 < 100ms**（首次允许 = 现有全扫耗时）
2. 数据正确性：缓存窗口内返回的 `currentWeatherId / weatherName / transitionProgress / regionPoints` 与实时读取一致（关键字段不得过期超过 cacheSeconds）
3. 与现有 schema（`wx-122b9`）字段兼容，前端零改动接入

## 6. 收益

优化落地后：

- 后端 TTL 可安全降至 **3s**、前端轮询 **3s** ⇒「切换 → 可见」延迟 **≤6s**（当前 ~76s）
- 游戏线程占用仍 **<15%**（远低于当前 60s 方案的等效成本上限）
- 雷暴/沙尘暴/过渡扫描动画均可实时完整呈现
