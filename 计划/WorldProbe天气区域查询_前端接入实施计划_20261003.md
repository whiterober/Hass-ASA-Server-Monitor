# WorldProbe 天气区域查询（zones）· 前端接入实施计划

> 生成：2026-10-03 ｜ 目标项目：dino-import（CF Worker 纯 Assets 架构）
> 依据：《WorldProbe 天气区域查询（zones）· 完整交接单》→ `报告\WorldProbe天气区域查询_前端调用文档_20261003.md`（插件 dll `1,631,744 B @22:14:58`）
> 状态：**计划待实施**（本文档只描述方案；本轮未改代码、未部署）
> 涉及文件：`独立后端\dino_backend.py`（真身 `\\SERVER\dino_backend\dino_backend.py`）、`dino-import.html`、`pwa\sw.js`

---

## 1. 目标与范围

### 1.1 一句话目标

在 dino-import 天气浮窗内新增「**区域实时（插件权威）**」分组：展示 `WorldProbe zones` 返回的**每个天气覆盖区域**（`Weather_Override_Volume`）的天气与气温。只有 **Isl（4 区）/ Cen（6 区）** 会出现该分组，其余 8 图自动隐藏。

### 1.2 范围内 / 范围外

| 范围内 | 范围外 |
|---|---|
| 后端 1 条新路由 `worldprobe_zones`（TTL 60s） | 插件侧（已完成，不改） |
| 前端数据层 + 渲染层 + 开关窗生命周期 | 静态区域参考表（保留现状，不删） |
| 线上验收与版本递增、备份 | 「玩家所在区域判定」/ 区域边界坐标（用户已裁定不做） |

### 1.3 前置依赖

- 插件 `TransferIdentityFix.WorldProbe zones` 已全服铺开（交接单 §8 / §14 ✅）
- Cen 6 区明细需插件 6,800 预算 dll 换装后复验（交接单 §12-1）→ **不阻塞前端实施**

---

## 2. 对接单契约摘要（前端只用三类字段）

### 2.1 顶层

| 字段 | 前端用途 |
|---|---|
| `ok` / `sub` | 成功标志 / 固定 `zones` |
| `count` | **区域数：Isl 4 / Cen 6 / 其余 0** ⇒ 分组显隐判据 |
| `scanAge` | 「区域名单 N 秒前扫描」（**名单年龄**，非数据年龄） |
| `cached` / `live` | 名单是否复用；`live=1` ⇒ 数据本轮实时重读 —— **与新鲜度无关，不据此降级展示** |
| `probeTruncated` | `1` ⇒ 有区域缺明细 ⇒ 该区显示「暂无明细」 |
| `zones[]` | 区域数组 |

### 2.2 `zones[]` 每项（前端只用加粗项）

- **`idx`**（编号，0 起）、**`settings`**（核心渲染源）
- `weather.typeIndex`（**原始枚举索引，禁止当天气名展示** —— 无 id→名称映射）
- `temperature.offset`、`wind.direction` / `wind.apply`、`meta.*`（priority / transitionWidth 等）
- `probed`（字段命中数）、`probe`（**默认 null，禁止渲染**）、`state`（**实测为 `settings` 子集 ⇒ 不单独渲染**）

### 2.3 `settings` 结构（渲染主数据）

`{ class, propsTotal(23), nonZero, props:[{name,value}] }` —— **`props` 只列非零项 ⇒ 缺键即 0**

Isl 四区实测：`Cloud Coverage 3.8` ｜ `Fog`（z1/z2 = 1）｜ `Material Snow Coverage 1 / 0.5 / 1 / 1` ｜ **`Wind Intensity` 8 / 2 / 4 / 8** ｜ 固定小值 `SunColorTint` / `MoonColorMultiplier` / `SourceAngleMultiplier`

### 2.4 性能与缓存口径（决定前端策略）

| 项 | 值 |
|---|---|
| 冷调用（首次扫图） | 1.213 s |
| 热调用（复用名单） | 1.104 s |
| 响应体积 | ≈4.0 KB（Isl 4 区）／6 区 ≈6.7 KB |
| 后端建议 TTL | **60 s** |
| 前端策略 | **60 s 复用 + 切图/重开面板时重取** |

> 结论：zones 比 `weather`（1.3~1.45 s / 11 KB）更轻，但仍属**慢调用**（>1 s）⇒ 必须异步、失败静默、**不得阻塞主面板首屏**（玩家层与全局值先行渲染）。

---

## 3. 现状核对（2026-10-03 只读核对）

| 项 | 现状 | 影响 |
|---|---|---|
| 后端路由 | `独立后端\dino_backend.py` 已有 `worldprobe_weather`（TTL 10s），**无 `worldprobe_zones`** | **须先补路由（步骤 A）** |
| 前端面板 | v4304：玩家层（状态 + 5 卡）→ 静态 `LB_WX_REGIONS` 参考表 → 更新行 → 来源行 | 新分组插入位置 = 玩家层之后、静态表之前 |
| 开关窗生命周期 | v4304 已具备 `AbortController` + `lbFuncPanelPoll/Tick` + 关窗 `delete LB._funcPanels[key]` | zones **复用同一套机制**，不新建 |
| 触发入口 | 点击「时间位」`#lbFuncClock` → `lbWeatherClick()`（功能条按钮已取消） | zones 随天气面板开窗一并触发 |

---

## 4. 实施步骤

### A. 后端路由（前置，1 条路由）

1. `独立后端\dino_backend.py`：
   - 常量 `WP_ZONES_TTL_MS = 60000`（与 `worldprobe_weather` 同模式）
   - `def worldprobe_zones(server)`：复制 `worldprobe_weather` 的**短时缓存 + 同键并发合并（single-flight）**实现；`CMD_WORLDPROBE` 子命令 `zones`；**原样透传插件 JSON（禁止中间裁剪字段）**
   - 路由：`elif path.endswith('worldprobe_zones'):` → `self._send(200, worldprobe_zones(server))`
2. 部署：`tmp\_deploy_backend.py`（UNC 复制 + 备份 + MD5 校验）→ **用户重启后端服务** → 验证：`POST /api/worldprobe_zones {"server":"Isl"}` 返回 `ok:true / count:4`

### B. 前端数据层（`dino-import.html`）

1. 状态与常量：`LB_WXZ_TTL_MS = 60000`；`LB._wxz = { data:null, err:'', recvMs:0, abort:null }`
2. `lbWxZonesSync()`（照抄 v4304 `lbWeatherSync` 模板）：
   - `AbortController`：同一时刻只保留一个在途请求；**已关窗 / 被新请求替换的结果直接丢弃**
   - 失败静默：只记 `err`，**绝不覆盖**主面板的全局天气展示
   - 60 s TTL：`LB._wxz.recvMs` 在 60 s 内 ⇒ 直接复用，不发请求
3. 触达点：
   - 开窗：`lbWeatherOpen()` 内与 `lbFuncPanelPoll('weather', ...)` 同级触发（首帧立即拉一次）
   - 切图：`lbRenderFuncBar()`（换图/换页必跑）时，若面板仍打开则重取
4. 关窗回收：`lbWeatherClose()` 内追加 `LB._wxz.abort.abort()`（与 `LB._wx.abort` 并列；定时器仍由 `lbFuncPanelClose` 统一清理）

### C. 渲染层（新增分组，不动玩家层）

1. 位置：玩家层卡片之后、静态参考表之前
2. 显隐：`data && data.ok && data.count > 0` 才渲染；否则整块不出现（8 图）
3. 每区一行（示意）：`#{idx} ｜ 风 8 ｜ 云量 3.8 ｜ 雪覆盖 1 ｜ 雾 1 ｜ 风向 南（180°）`
   - **只渲染 `settings.props` 中存在的键**（缺键 = 0，禁止遍历固定键表）
   - 前端内置展示用中文映射（仅展示，不改数据）：`Wind Intensity`→风、`Cloud Coverage`→云量、`Fog`→雾、`Material Snow Coverage`→雪覆盖、`Rain`→雨（若出现）
   - `temperature.offset ≠ 0` ⇒ 追加「温度偏移 ±x」；`wind.apply = 0` ⇒ 风向后加「（未生效）」
4. 容错：`probeTruncated=1` 或该区无 `settings` / `props` 为空 ⇒ 该行显示「**暂无明细**」
5. 底部小字：`区域名单 {scanAge} 秒前扫描 · 每次调用实时重读`；来源行沿用「数据来自游戏内天气装置（插件权威数据）」
6. **禁止项**：不渲染 `probe`；不把 `weather.typeIndex` 当天气名

### D. 静态参考表（保留）

- `LB_WX_REGIONS` 原样保留，作为「区域气候参考（静态）」
- Isl / Cen：实时分组在上、静态参考在下（标题可区分）
- 其余 8 图：仅静态参考（现状不变）

### E. 部署与验收

1. `node --check` 抽取 3 个内联脚本块 ⇒ 全过（ALL_OK=True）
2. 版本递增（`LB_VERSION`）+ `pwa\sw.js` 的 `VER` 同步 ⇒ `tmp\_deploy_cf.py`
3. 线上 PW 验收（见 §6）
4. `fetch(no-store)` 复核线上版本（部署脚本可能因边缘缓存报「版本一致 False」假阴性）

---

## 5. 风险与回滚

| # | 风险 | 缓解 |
|---|---|---|
| 1 | zones 冷调用 1.2 s 拖慢面板 | **异步分离**：主面板先渲染，区域分组独立填充 |
| 2 | Cen 6 区明细缺失（旧预算 dll） | 「暂无明细」容错；待 6,800 预算 dll 换装后复验 |
| 3 | 区域无坐标/无名，玩家不知对应哪里 | 编号 + 关键值展示；tooltip 注明「区域为地图固有覆盖体积」 |
| 4 | 后端路由缺失导致 404 | 步骤 A 先落地并 HTTP 验证；前端对失败**静默隐藏**分组 |
| 5 | 关窗后仍在请求 | 沿用 v4304 abort 机制（实测控制台出现 `net::ERR_ABORTED`） |
| 回滚 | 前端：还原 `bak\dino-import_backup_pre_vXXXX_*.html` + 重新部署；后端：恢复 `.bak_*` 副本 + 重启服务 | |

---

## 6. 验收清单

1. [ ] `POST /api/worldprobe_zones`（Isl）返回 `ok:true / count:4`，含 `settings.props`
2. [ ] 线上 Isl：面板出现「区域实时」4 行，风值 **8 / 2 / 4 / 8** 与交接单实测样例一致
3. [ ] 线上 Cen：6 行（未换装 dll 时 z5 显示「暂无明细」；换装后复验全明细）
4. [ ] 其余 8 图：无「区域实时」分组，静态参考表照旧
5. [ ] 开窗/切图触发；关窗出现 `net::ERR_ABORTED`，重开正常（无重复定时器 / 无泄漏）
6. [ ] `node --check` 3/3 + 版本一致（`fetch(no-store)` 复核）+ 备份文件已生成

---

## 7. 参考资料

- 交接单：`报告\WorldProbe天气区域查询_前端调用文档_20261003.md`
- 插件侧方案：`计划\天气区域查询与Abe适配_合并方案_20261003.md`
- 前端现状实现：v4304（天气入口迁至「时间位」+ 开关窗查询回收）
- 后端现状：`独立后端\dino_backend.py`（`worldprobe_weather` 模式可照抄）
