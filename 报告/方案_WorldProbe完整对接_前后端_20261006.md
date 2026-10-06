# WorldProbe 事件接口 · 前后端完整对接方案（dino-import）

> 生成时间：2026-10-06　｜　状态：**方案（待实施）**　｜　用户口径：**「配备后端接口的完整方案」+「Rag 沙尘暴机制」+「所有地图的天气概率」+「地图获取天气的新方法」**
> 🔄 **v2 修订（2026-10-06 晚）**：① 新增 **§9 全服天气概率对接**（10 图逐图概率：数据源/命令/后端聚合路由/前端显示）；② 新增 **§2.5 天气主路由升级**（`weather full=1 limit=1 slim=1` 新方法；前端零破坏已 grep 验证）；③ §1 矩阵表补 2 行；④ 已核对后端真身 `\\SERVER\dino_backend\dino_backend.py`（10-04 版）**未含任何本次新路由/新参数** ⇒ 后端工作全部待做
> 输入：`WorldProbe_全服事件对接文档_20261006.md`（插件 v121 → **v122b2 在线 / v122b3·b4 待覆盖**）
> 覆盖链路：**插件 dll（命令）→ 物理后端 dino_backend.py（HTTP 路由）→ 前端 dino-import.html（显示）** 三环全设计
> 本方案**取代**：《方案_雷暴区域名显示_20261006.md》《方案_区域天气显示层_Gen巨浪_20261006.md》（两者作为明细留存，内容已并入本方案 §3~§5）

---

## 1. 对接矩阵总表（全事件 × 三环现状 × 动作）

| # | 事件 | 插件命令（现状） | 后端路由 | 前端 | 动作 |
|---:|---|---|---|---|---|
| 1 | Sco 雷暴**区域名** | `weather`（已可用） | `/api/worldprobe_weather` ✅ | 角标已有；区域名未接 | **v4365**：角标追加「· 区域：X」（纯前端） |
| 2 | Sco 沙尘暴（尘墙） | `wxSemantics.sandstorm`；**v4392 起改用 UDS 属性直读**（slim=0 提取 21 属性修正，绕过插件判据） | ✅ | v4344 已接（图层扫掠+角标，仅模拟数据验证）；v4392 属性直读（实测插件 active 恒 false） | **已修 v4392**（待沙尘暴窗口实机验证） |
| 3 | Sco 热浪 | 同上（`heatWaveActive` 派生键已在线） | ✅ | 译名已改（v4364）；无独立状态显示 | 可选：不单列（主流程卡已含热浪名）；如需再议 |
| 4 | **Rag 沙尘暴（新机制）** | `sandstorm`（**v122b3，未覆盖**） | ❌ 需新增 `/api/worldprobe_sandstorm` | 未接 | 见 **§3**（后端+前端全设计；前置= dll 覆盖） |
| 5 | **Gen 巨浪** | `wave`（v118+ 已可用） | ❌ 需新增 `/api/worldprobe_wave` | 未接 | 见 **§4**（v4366） |
| 6 | Ext 陨石雨 | `meteor`（v117+ 已可用） | ❌ 需新增 `/api/worldprobe_meteor` | 未接 | 见 **§5.2**（phase 四态驱动） |
| 7 | Rag 火山 ETA | `actor filter=VolcanoManager` | ❌ 需新增 `/api/worldprobe_actor` | 未接 | 见 **§5.3**（Tnext−worldTime） |
| 8 | Gen 月球流星雨 | `actor filter=LunarMeteorController` | ❌ 同上 | 未接 | 见 **§5.4**（Last+Actual−worldTime） |
| 9 | 坏天气权重因子 | `badwx`（v122b2） | ❌ 需新增 `/api/worldprobe_badwx` | 未接 | 见 **§5.5**（低频；`sinceBad=null` 不读 factor） |
| 10 | Gen 雪崩 / Abe 地震 / Ext 王泰坦 | 可读但**不可预测** | — | 只文案 | **不接数据**（按文档口径） |
| 11 | zones 区域天气 / 热力图 | `zones` / `biometemps` | ✅ 已有 | 已接 | 维持 ✅ |
| 12 | **地图天气主取数（新方法）** | `weather full=1 limit=1 slim=1`（v122 起） | ⚠️ 现有路由**待升级**（当前发裸 `weather`，10-04 真身核实） | 已接（响应键全保留） | 见 **§2.5**（体积降 52~93%） |
| 13 | **全服天气概率（10 图）** | `actor … probe=WeatherWeights_*/WeatherChances`（§9.1） | ❌ 需新增 `/api/worldprobe_wprobs`（聚合） | 未接 | 见 **§9**（全设计） |
| 14 | **特殊事件浮窗化（Gen/Abe/Rag）** | 多源（现有 + `wave` + `actor` + 文案） | 复用现有 + §2 批次 | 部分已有（Gen 火山 / Abe 地表） | 见 **§10**（按钮改名 + 浮窗区块全设计） |

**显示层规范（用户口径）**：区域性质信息（区域名/区域状态/区域概率）**只进图层位**（角标/区域块/子图卡），**不进主流程卡**（天气事件/概览/基准温度）。

> 📌 概率属「**整图级**」信息（不受区域位约束），落位 = 面板底部**说明行区**（§9.4）——仍不进主流程卡。
>
> 🧭 **「区域性质」按图判定（2026-10-06 用户口径）**：Sco 雷暴 = 区域性质（区域名，走图层位）；**Rag / Val 的雷暴 = 全图事件，走主线显示**（与 ext_gen 主天气流程一致）——不得因名为「雷暴」而套用 Sco 的区域位规则。

---

## 2. ★ 后端接口设计（`独立后端\dino_backend.py`，新增 5 路由）

### 2.1 路由总表

| 路由（POST） | 透传命令 | 参数 | TTL 建议 | 说明 |
|---|---|---|---|---|
| `/api/worldprobe_wave` | `WorldProbe wave` | `server` | **60 s** | Gen 巨浪（§16）；响应 1~2 KB；与热力图同频 |
| `/api/worldprobe_sandstorm` | `WorldProbe sandstorm` | `server` | **60 s** | Rag 沙尘暴（§14）；**前置：dll v122b3 覆盖**（`build = Oct 6 12:58:34`）；未覆盖时返回"未知子命令"应答 → 前端按 `supported` 缺省静默 |
| `/api/worldprobe_meteor` | `WorldProbe meteor` | `server` | **2 s** | Ext 陨石预警；前端 1~2 s 轮询（响应 ≈770 B）→ 后端 TTL 2 s 合并多客户端 |
| `/api/worldprobe_actor` | `WorldProbe actor …` | `server` + `filter` + `propsIdx`(默认0) + `probe`(可选) + `top`(默认1) + `slim`(默认1) + `fields`(可选) | **30 s** | 通用 actor 读取：Rag 火山 / Gen 月球流星雨 /（雪崩调试）；命令拼装：`actor filter=<F> props=1 propsIdx=<N> top=<K> slim=1 [fields=…] [probe=…]` |
| `/api/worldprobe_badwx` | `WorldProbe badwx` | `server` + `filter`(可选，默认 WeatherSystem) | **300 s** | 坏天气权重因子；低频（与热力图同级） |
| **`/api/worldprobe_wprobs`** | **聚合**：按图族选命令（§9.1） | `server` | **300 s** | **全服天气概率聚合**：后端解析 `dataHex` → 归一化 → 返回 `slots[{i,weight,pct}]`（详细设计见 §9.3） |

> 与现有路由关系：`zones` / `biometemps` / `scan` / `class` **不动**；`weather` **升级**（支持 `full`/`limit`/`slim` 参数，见 §2.5）；新路由全部照抄现有实现模式（见 2.2）。

### 2.2 实现骨架（沿用现有 `_wp_rcon_json` + TTL 缓存 + 同键合并模式）

**常量与缓存**（加在 WP 常量区，L67-83 附近）：

```python
WP_WAVE_TTL_MS = 60000;      _WP_WAVE_CACHE = {}       # server -> {'ts': ms, 'data': {}}
WP_SAND_TTL_MS = 60000;      _WP_SAND_CACHE = {}
WP_METEOR_TTL_MS = 2000;     _WP_METEOR_CACHE = {}
WP_ACTOR_TTL_MS = 30000;     _WP_ACTOR_CACHE = {}      # (server,cmd) -> ...
WP_BADWX_TTL_MS = 300000;    _WP_BADWX_CACHE = {}
```

**无参三兄弟（wave / sandstorm / meteor 同构）**：

```python
def worldprobe_wave(server):
    """Gen 巨浪（WorldProbe wave）。TTL 60s + 同键并发合并。"""
    port = SERVERS.get(server)
    if not port:
        return {'ok': False, 'server': server, 'error': 'unknown server'}
    now_ms = int(time.time() * 1000)
    c = _WP_WAVE_CACHE.get(server)
    if c and (now_ms - c['ts'] < WP_WAVE_TTL_MS):
        d = dict(c['data']); d['cacheAgeMs'] = now_ms - c['ts']; d['serverNowMs'] = now_ms; return d
    with _wp_lock((server, 'wave')):
        now_ms = int(time.time() * 1000)
        c = _WP_WAVE_CACHE.get(server)
        if c and (now_ms - c['ts'] < WP_WAVE_TTL_MS):
            d = dict(c['data']); d['cacheAgeMs'] = now_ms - c['ts']; d['serverNowMs'] = now_ms; return d
        j, err = _wp_rcon_json(port, CMD_WORLDPROBE + ' wave', server, None, now_ms)
        if err:
            return err
        j['server'] = server
        _WP_WAVE_CACHE[server] = {'ts': now_ms, 'data': j}
        _wp_trim(_WP_WAVE_CACHE, now_ms)
        out = dict(j); out['cacheAgeMs'] = 0; out['serverNowMs'] = now_ms; return out
```

> `worldprobe_sandstorm` / `worldprobe_meteor` 同构（仅命令字与 TTL 不同）。

**带参两兄弟（actor / badwx）**——**参数白名单净化**（防命令注入，拼进 RCON 前过滤）：

```python
import re as _re_wp
def _wp_arg(s, maxlen=64):
    """RCON 参数净化：仅允许字母/数字/下划线/逗号/点/加减/空格（+ 由前端代空格，后端转回）"""
    s = str(s or '')[:maxlen]
    return _re_wp.sub(r'[^A-Za-z0-9_,\.\-\+ ]', '', s)

def worldprobe_actor(server, filt, propsidx='0', probe='', top='1', slim='1', fields=''):
    """通用 actor 读取（Rag 火山 / Gen 月球流星雨 / 调试）。
    命令：WorldProbe actor filter=<F> props=1 propsIdx=<N> top=<K> slim=1 [fields=A,B] [probe=A,B]"""
    port = SERVERS.get(server)
    if not port:
        return {'ok': False, 'server': server, 'error': 'unknown server'}
    f = _wp_arg(filt)
    if not f:
        return {'ok': False, 'server': server, 'error': 'missing filter'}
    parts = ['actor', 'filter=' + f, 'props=1',
             'propsIdx=' + _wp_arg(propsidx, 4), 'top=' + _wp_arg(top, 4)]
    if slim in ('0', '1'):
        parts.append('slim=' + slim)
    fl = _wp_arg(fields, 200)
    if fl:
        parts.append('fields=' + fl.replace(' ', ','))
    pr = _wp_arg(probe, 200)
    if pr:
        parts.append('probe=' + pr.replace(' ', '+'))
    cmd = CMD_WORLDPROBE + ' ' + ' '.join(parts)
    key = (server, cmd)
    now_ms = int(time.time() * 1000)
    # … 同款 TTL 缓存 + _wp_lock(key) + _wp_rcon_json(port, cmd, server, None, now_ms) …
```

> `badwx` 同构：命令 `badwx [filter=<F>]`；默认 `filter=WeatherSystem`。
> **路由注册**（`do_POST` 的 WorldProbe 段照抄现有 `elif path.endswith('worldprobe_weather'):` 结构，共 5 个新 `elif`）。
> **参数取法**：一律 `g('server')` / `g('filter', 'VolcanoManager')`（现有 `g()` 同时支持 body JSON 与 query）。

### 2.3 返回到前端的附加键（与现有一致）

每条新路由出参沿用现有约定：原样透传插件 JSON + `server` / `cacheAgeMs` / `serverNowMs`（便于前端做"数据新鲜度"与诊断）。

### 2.4 后端部署与验证（用户侧）

1. 本地改 `独立后端\dino_backend.py` → 上传物理服务器 → 重启后端
2. 验证（带 UA 的 curl / Python）：
   ```
   POST https://data.whiterober.ccwu.cc/api/worldprobe_wave      {"server":"Gen"}
   POST https://data.whiterober.ccwu.cc/api/worldprobe_sandstorm {"server":"Rag"}   # 需 dll v122b3
   POST https://data.whiterober.ccwu.cc/api/worldprobe_meteor    {"server":"Ext"}
   POST https://data.whiterober.ccwu.cc/api/worldprobe_actor     {"server":"Rag","filter":"VolcanoManager"}
   ```
3. 断言：`ok:true` + 关键键存在（wave→`verdict`；sandstorm→`active`；meteor→`phase`；actor→`actorProps.props` 白名单项）

### 2.5 天气主路由升级（`weather` → `full=1` + `slim=1` 新方法）

**背景**：对接文档已把「地图天气主取数」的推荐口径更新为 **`WorldProbe weather full=1 limit=1 slim=1`**（`slim=1` 为 v122 新增）；现有后端仍在发裸 `weather`（全量）——经核对**真身仍未变**（`\\SERVER\dino_backend\dino_backend.py`，10-04 版）。

**升级设计**（改 `worldprobe_weather`）：
- 命令改为：`weather full=1 limit=1` + （`slim=1` **默认开启**，可传 `slim=0` 关闭）
- 新增参数：`limit`（默认 1）；TTL 建议 10 s → **60 s**（与 zones/biometemps 对齐）

**收益（文档实测）**：响应 16~30 KB → **2.5~12.5 KB**（降 52~93%）。

**零破坏验证（本方案已核对）**：
- 前端引用键**全部在 slim 保留清单**（文档 §9.5.1-C）：`weatherState.*` / `wxSystems[]` / `wxSemantics.{enumIndices, electricalStorm, sandstorm, extWeather, presetTable, arrayProbe, weightsDay, weightsNight, eventLengths}` / `regionMap` / `actors[]`
- 前端**零引用**被裁块（已 grep 验证：`cloud` / `settingsScan` / `payloadProbe` / `dump[]` / `settingsRaw` 均无引用）
- ⇔ 升级后**前端无需同步改版**

---

## 3. ★ Rag 沙尘暴（新机制）—— 机制 + 接口 + 前端全设计

### 3.1 机制（文档 §13/§14 综合）

- **不是独立 Actor，也不是 Sco 的"尘墙扫图"**（`scan filter=Sand|Storm` = 0 命中；Rag 的 `wxSemantics.sandstorm` 为 `null`）
- 真实机制 = **三层结构**：
  1. **掷骰层** `BP_RAG_DayWeather_WeatherSystem_C`：6 预设全局抽签（沙尘暴 = 索引 **3**；实测实时概率 **7.32%**，每 1500~2500 s 掷一次、过渡 40~80 s）
  2. **区域层** `BP_RAG_DayWeather_Agent_C`：4 区域权重（`SeqWeight_Region0..3`）
  3. **效果层** `BP_RAG_WeatherEffects_C`：**`bInSandstormTrigger`（区域闸门）** + `SandstormAmount`（强度）
- ⇒ 「沙尘暴只在沙漠」= **全局抽中 + 效果层仅在触发卷（沙漠）内生效** —— **区域性质事件**（决定了显示归"区域位"）

### 3.2 接口（`WorldProbe sandstorm`，v122b3）

```
TransferIdentityFix.WorldProbe sandstorm       # 只读；响应 1~2 KB；30~60 s 轮询
```

| 前端关心的键 | 用途 |
|---|---|
| **`active`** | 派生总开关（`inSandstormTrigger=1` 或 `sandstormAmount>0`）→ **判"正在沙尘暴"** |
| `weights.sandstormPct` | 实时概率 %（Rag 实测 7.317） |
| `timer.secondsUntilChange` / `timer.nextAt` | 下次换天气倒计时 |
| `effect.sandstormAmount` / `effect.inSandstormTrigger` | 强度 / 区域闸门（细分判据） |
| `supported` + `layers.roll/region/effect.found` | 机制可用性（某层 `found:0` **不是错误**） |
| `presetTable.entries[]` / `sandstormPreset` | 预设表（idx3=Sandstorm） |

- **适用图（实测）**：Rag / Val / Los / Ast / Gen 有机制（Gen 无 Sandstorm 预设⇒`index:-1`）；**Sco 不走此命令**（用 `wxSemantics.sandstorm`）；Isl/Cen/Abe `supported:0`。
- 🔴 **前置**：dll 未覆盖前**勿调用**（返回"未知子命令"；以 `DinoMutPing.build == Oct 6 12:58:34` 为准）。

### 3.3 前端设计（分层落位——遵守区域位规范）

| 信息 | 显示位 | 设计 |
|---|---|---|
| **正在沙尘暴**（`active===1`） | **图层角标**（热力图右上，同 Sco 沙尘暴角标样式） | 「🌪️ 沙尘暴 · 沙漠区（触发卷内）」；无 event 时不显示 |
| **概率**（`weights.sandstormPct`） | **区域/事件说明行**（热力图图注位，非主流程卡） | 「沙尘暴概率 ≈7.3% · 距变天 ≈X 分」——仅 Rag/Val/Los/Ast 且 `supported===1` 时出现 |
| 倒计时（`timer.secondsUntilChange`） | 同上行内 | 与概率同行（文案再精修） |

- 前端取数：新增 `lbSandSync`（**60 s 复用** + 单飞 abort + 失败静默 + 开窗/切图钩子；与 `lbBioSync` 同范式）；路由未就绪 / `supported!==1` → 全部不显示（零残留）。
- 验收（PW）：Rag 面板出现概率行文案；Isl/Sco 面板**无**「沙尘暴概率」字样；`active` 窗口内角标出现（可用 §14 机制自然等待或后续受控手段）。

---

## 4. Gen 巨浪（`wave`）—— 完整设计（含后端）

### 4.1 机制与数据（文档 §16）

- 巨浪 = **ocean 子图的海况**（`BP_Waterline_Ocean_Gen_4_ASA_C` + `BP_GEN_DayWeather_WeatherSystem_C.WaveState`），**区域性质**（ocean 子图）
- 数据：`verdict`（实测 calm）/ `weather.WaveState`（0.35）/ `weather.TimerNextWeather`（≈1,327.6 s 后）/ 子图天气名 / `waterline.groups[]` 4 组（主海洋 = `oceanTile` 最大 60000：浪高 47.25 / 陡度 7 / 速度 1.5）

### 4.2 前端设计（修订：落位「生态圈事件」浮窗 —— 用户口径 2026-10-06，见 §10）

> 🔄 **v3 修订**：原设计（ocean 生态卡加"预警行/详情行"）改为**并入 Gen「生态圈事件」浮窗的「🌊 巨浪」区块**（详细展示统一入口）；ocean 生态卡**不加行**（避免重复占位）。

```
[🧬 生态圈事件 · 创世]
├─ 🌋 火山计时（现有内容）
├─ 🌊 巨浪          ← 本区块（§10.3-⓶）
│   海况：平静（0.35） · 距变化 ≈22 分
│   浪高 47.25 · 陡度 7 · 速度 1.5
├─ 🌀 漩涡（待数据源）
├─ 🏔️ 雪崩（说明文案）
└─ 🌠 流星雨（ETA 区块）
```

- `verdict` 中文化映射 `LB_WAVE_ZH`（`calm→平静`；未知回退原文）；`WaveState≥0.7` 橙色高亮为拟议（待实测校准，不阻塞首版）
- 取数：`lbWaveSync`（60 s 复用 + 单飞 abort + 失败静默）；路由未就绪 → 区块不输出

### 4.3 链路

插件 `wave`（**已可用**）→ 后端 **新增 `/api/worldprobe_wave`**（§2）→ 前端 **v4370「生态圈事件」浮窗**（§10）

---

## 5. 其余事件（设计要点）

### 5.1 Sco 雷暴区域名（v4365，纯前端，可立即实施）
- 数据：`wxSemantics.electricalStorm.regionNameProbe.asString`（通道已有，零后端改动）
- 显示：**仅图层角标**——`⚡ 全图雷暴` → 有区域名时 `⚡ 全图雷暴 · 区域：Center`；新增 `lbWxEsRegion()`（string/`.asString` 双兼容 + 白名单净化）
- **不进**面板卡（区域位规范）

### 5.2 Ext 陨石雨（P1）—— `meteor` + 后端新路由
- 判据：**`phase ∈ {incoming, active}` 才弹**（`leaving/none` 不弹——防"切回晴天"假预警；`warn` 单独不可靠）
- 前端：陨石预警浮窗/角标（phase 四态 + `volumeTrend` 渐入）+ 文案提前量 = 过渡窗 40~80 s
- 轮询：1~2 s（响应 770 B）→ 后端 TTL 2 s
- ⚠️ Ext 的 `weather` 全量实测 40 s 超时 ⇒ 陨石走 `meteor` 专用通道（不再依赖 weather）

### 5.3 Rag 火山 ETA（P2）—— `actor` 路由
- `ETA = TimeNextVolcanoEvent − weather.worldTime`；`Tnext=0` ⇒ 显示「空闲期·未排期」
- 显示位：**Rag「火山计时」浮窗**（§10.3-⓼）；⚠️ **不走 volcano_log**（该服务仅 Gen）

### 5.4 Gen 月球流星雨（P2）—— `actor` 路由
- `ETA = TimeLastEvent + ActualTimeBetweenEvents − worldClock`（实测误差 +0.225 s）；**空服不推进**（ETA 为负先确认玩家在 Gen）
- 显示位：**Gen「生态圈事件」浮窗 · 🌠 流星雨区块**（§10.3-⓹）

### 5.5 坏天气权重因子（P2，可选）—— `badwx`
- 仅 Ext 有曲线驱动（`factor=0.8`）；**`sinceBad=null` 一律不读 `factor`**（跨版本安全写法）；`probsPct[]` 始终精确

### 5.6 不接数据（口径固化）
- **Abe 地震 / Gen 雪崩 / Ext 王泰坦**：只显示规律文案（模板见文档 §0.1/§15.2/§13）；雪崩白名单（v122b4）仅调试用

---

## 6. 实施顺序（建议排期）

| 序 | 事项 | 依赖 | 版本/交付 |
|---:|---|---|---|
| 1 | Sco 雷暴角标（§5.1） | 无 | **v4365**（前端） |
| 2 | 后端路由批次（§2：**weather 升级** + wave/sandstorm/meteor/actor/badwx/**wprobs**） | 用户侧部署 | `dino_backend.py` 更新 |
| 3 | Gen 巨浪卡（§4） | 序 2 | **v4366**（前端） |
| 4 | Rag 沙尘暴落位（§3.3） | 序 2 + **dll v122b3 覆盖** | **v4367**（前端） |
| 5 | **全服天气概率行（§9.4）** | 序 2（wprobs 就绪） | **v4368**（前端） |
| 6 | Ext 陨石预警（§5.2） | 序 2 | v4369 |
| 7 | Rag 火山 / Gen 流星雨 / badwx（§5.3~5.5） | 序 2 | 待排 |
| 8 | **特殊事件浮窗化（§10）**：按钮改名（Gen 生态圈事件 / Abe 特殊事件 / Rag 火山计时）+ 三图浮窗区块 | 混合（文案区块无依赖；数据区块=序 2） | **v4370**（前端，分批点亮） |

> 📌 **执行记录（2026-10-06 晚更新）**：序 3 的「v4366 巨浪卡」已被 v3 修订架空（巨浪并入 §10 浮窗）；实际交付顺位为：**v4365**=Sco 雷暴区域角标 + 词典修订 + 前缀剥离；**v4366**=Sco 雷暴独立卡（用户口径：区域性质→独立卡片、不占主序列）；**v4367**=沙尘暴独立卡（Sco `/sandstorm/i` 判定 + Rag `sandstorm` 命令；同批完成**后端 6 路由 + weather 升级**并冒烟 10/10）；**v4368**=全服天气概率行（§9.4）；**v4369**=Ext 陨石独立卡（§5.2 phase 四态）；**v4370**=特殊事件浮窗化全套（§10：三图按钮改名 + 火山/巨浪/雪崩/流星雨/地震/Rag 火山/沙尘暴区块，共享 `lbFuncPanelOpen` 壳按图分派；漩涡数据源缺失暂不输出）。

---

## 7. 验收与回归清单（各步通用）

1. 修改文件前备份；改码脚本 `node --check` 门禁全绿；版本 + sw 递增；CF 部署线上验证一致
2. PW（清缓存）：目标图出现新文案/角标；**非适用图零残留**（如 Isl 无「沙尘暴概率」、无「海况」）
3. 断源回归：路由未就绪 / 数据为空 → 静默不显示、无报错
4. 进度写盘 + 记忆更新（每步）

## 8. 风险与前置

| # | 项 | 处置 |
|---|---|---|
| 1 | **dll v122b3/b4 未覆盖**（线上 v122b2） | `sandstorm` 命令**覆盖后再接**（`build = Oct 6 12:58:34` 为准）；其余接口 v122b2 即可 |
| 2 | 后端 5 路由尚不存在 | 前端全部 feature-detect 静默；后端就绪自动生效 |
| 3 | Ext `weather` 40 s 超时（实测） | 陨石改走 `meteor`；weather 仅保留既有面板 |
| 4 | `verdict` 值域仅知 `calm` / 巨浪阈值未定 | 映射表回退原文；高海况实测后补 |
| 5 | `badwx` 无驱动图假 factor | `sinceBad===null ⇒ 不读 factor` |
| 6 | 区域名/概率注入风险 | 前端白名单净化 `[A-Za-z0-9_\- ]`；后端 `_wp_arg()` 净化 |
| 7 | **uds 概率 `filter=` 类名**：Sco=`UDS_SE_Weather` 已实测；**Isl/Cen 待实测** | 实施第一步用 `scan filter=UDS_` 确认类名并固化映射（§9.1） |
| 8 | **wprobs 的 `dataHex` JSON 路径未固化** | 实施第一步先跑真实命令固化路径（`probes` 键名/`+` 还原形式），再写解析（§9.3） |
| 9 | Gen 概率：6 个 `DayWeather_WeatherSystem` 实例，`propsIdx` 顺序可能随加载变 | 以 `WeatherPresetList` objects 含 `_Ocean_` 者判定海洋图实例（低频 300 s，可接受） |
| 10 | **Gen 漩涡（气旋）数据源缺失**：文档仅提「气旋属另一套机制」（`Buff_CycloneBox_C` / `Buff_UnderwaterCyclone_C`），未给读取方法 | §10 漩涡区块首版不显示；**需插件侧补读取命令**（回执 §10.5） |
| 11 | Rag 火山日志服务 `volcano_log` 仅 Gen（`VOLCANO_SERVERS={'Gen'}`） | Rag 火山**勿走 volcano_log**——走 `actor`（VolcanoManager）自有通道（§10.3-⓼） |

---

## 9. ★ 全服天气概率对接（全图 10 服）—— v2 新增

> 数据基准：对接文档 **§12**（全服概率总表，2026-10-06 实测）；总原则（文档 §12.6）：**概率在服务端算，前端只展示结果**。
> 覆盖：Isl / Sco / Cen（uds）+ Ext / Ast / Rag / Val / Los / Gen（ext_gen）；Abe 无权重表（不做）。

### 9.0 📋 全地图天气 × 概率一览（基准快照；实测 2026-10-06）

> 口径：概率 = 槽权重 ÷ 同组正权重之和；**uds 分昼夜**、**ext_gen 动态**（每次重算，勿写死）；下表为**基准快照**，运行时以后端 `/api/worldprobe_wprobs`（§9.3）重算值为准。
> 中文名 = **展示口径**（2026-10-06 用户定稿；对应词典修订清单见 §9.6）。

**A. uds 家族（Isl / Sco / Cen）—— 昼 / 夜两套权重**

| 图 | 槽 | 天气（id） | 中文 | 白天 | 夜晚 | 单次时长 |
|---|---:|---|---|---:|---:|---:|
| **Isl** | 0 | ColdFront（5） | 冷锋 | 0.0% | 20.0% | 300 s |
| | 1 | Partly_Cloudy（1） | 晴转多云 | 10.0% | 0.0% | 300 s |
| | 2 | Rain（2） | 雨 | 30.0% | 0.0% | 300 s |
| | 3 | Foggy（3） | 雾 | 30.0% | 40.0% | 300 s |
| | 4 | HeatWave（4） | 热浪 | 30.0% | 40.0% | 300 s |
| **Sco** | 0 | ColdFront_SE（5） | 冷锋 | 0.0% | 29.4% | 800 s |
| | 1 | ElectricalStorm（7） | 雷暴¹ | 4.5% | 11.8% | 425 s |
| | 2 | Rain_SE（2） | 雨 | 15.9% | 5.9% | 750 s |
| | 3 | Foggy_SE（3） | 雾 | 6.8% | 11.8% | 650 s |
| | 4 | HeatWave_SE（4） | 热浪 | 31.8% | 0.0% | 700 s |
| | 5 | Clear_Skies_SE（0） | 晴 | 22.7% | 29.4% | 1200 s |
| | 6 | Sand_Dust_Storm（6） | 沙尘暴 | 11.4% | 11.8% | 425 s |
| | 7 | Superheat（8） | 焚风 | 6.8% | 0.0% | 750 s |
| **Cen** | 0 | ColdFront_TheCenter（5） | 冷锋 | 12.5% | 12.5% | 550 s |
| | 1 | Rain_TheCenter（2） | 雨 | 12.5% | 12.5% | 550 s |
| | 2 | Foggy_TheCenter（3） | 雾 | 12.5% | 25.0% | 550 s |
| | 3 | HeatWave_TheCenter（4） | 热浪 | 12.5% | 0.0% | 550 s |
| | 4 | Clear_Skies_TheCenter（0） | 晴 | 50.0% | 50.0% | 800 s |

> ¹ **Sco 雷暴 = 区域性质**（区域名走图层位，§1）；**Rag / Val 的雷暴 = 全图事件，走主线**（见表 B ★ 注）。

**B. ext_gen 家族（Ext / Ast / Rag / Val / Los）—— 单套动态权重**

| 图 | 槽 | 天气 | 中文 | 概率（快照） |
|---|---:|---|---|---:|
| **Ext** | 0 | —（未定义） | — | 0.0% |
| | 1 | Cloudy | 多云 | 21.7% |
| | 2 | Overcast | 阴 | 21.7% |
| | 3 | Spooky | 晦 | 17.4% |
| | 4 | —（未定义） | — | 0.0% |
| | 5 | ClearSky | 晴 | 21.7% |
| | 6 | **MeteorRain** | **陨石雨** | 17.4% |
| **Ast** | 0 | ClearSky | 晴 | 34.5% |
| | 1 | Fog | 雾 | 20.7% |
| | 2 | Rain | 雨 | 13.8% |
| | 3 | Heatwave | 热浪 | 20.7% |
| | 4 | Sandstorm | 沙尘暴 | 3.4% |
| | 5 | ClearSky_Fog | 晴雾 | 3.4% |
| | 6 | Rain_Fog | 雨雾 | 3.4% |
| **Rag** | 0 | ClearSky | 晴 | 48.8% |
| | 1 | Fog | 雾 | 9.8% |
| | 2 | Rain | 雨 | 17.1% |
| | 3 | **Sandstorm** | **沙尘暴** | 7.3% |
| | 4 | ElectricalStorm ★ | 雷暴 | 9.8% |
| | 5 | Superheat | 焚风 | 7.3% |
| **Val** | 0 | ClearSky | 晴 | 64.5% |
| | 1 | Fog | 雾 | 12.9% |
| | 2 | Rain | 雨 | 12.9% |
| | 3 | ElectricalStorm ★ | 雷暴 | 9.7% |
| **Los** | 0 | ClearSkyV2 | 晴² | 41.7% |
| | 1 | ClearSkyV3 | 晴³ | 41.7% |
| | 2 | SnowFluery | 小雪 | 8.3% |
| | 3 | Blizzard | 暴风雪 | 8.3% |
| | 4 | ClearSky | 晴 | 0.0% |

> ★ **Rag / Val 的雷暴 = 全图事件，走主线显示**（2026-10-06 用户口径；不套用 Sco 的区域位规则）。
> ※ **Los 三种 ClearSky 用角标区分（用户定稿）**：基础「晴」· V2「**晴²**」· V3「**晴³**」；`²`/`³` 为**上标字符**（U+00B2 / U+00B3），**显示层同此口径**（词典清单见 §9.6）。

**C. Gen —— 每子图独立（按 `miniMapType` 对齐；`propsIdx` 顺序可能漂移）**

| 子图 | 槽数 | 天气 × 概率 |
|---|---:|---|
| arctic 雪山 | 1 | ClearSky 晴 **100%** |
| bog 沼泽 | 2 | ClearSky 晴 50% · 50%（同预设两槽） |
| **ocean 海洋** | 7 | ClearSky 晴 52.6% · Rain 雨 10.5% · ElectricalStorm 雷暴 10.5% · Heatwave 热浪 10.5% · ClearSky_Fog 晴雾 5.3% · Rain_Fog 雨雾 5.3% · ElectricalStorm_Fog 雷暴雾 5.3% |
| volcanic 火山 | 2 | ClearSky 晴 50% · 50% |
| lunar 月球 | 2 | ClearSky 晴 50% · 50% |
| （第 6 系统） | 2 | ClearSky 晴 50% · 50% |

> ⚠️ 雪山 / 沼泽 / 火山 / 月球的预设表仅 `*_ClearSky` ⇒ 天气由**序列 / 蓝图**驱动（非权重抽签）⇒ **概率展示仅海洋图有效**，其余子图只做"当前天气"展示（与 §9.4 一致）。

**D. Abe**：❌ 无权重表（`WeatherWeights_Day/Night` = `null`）⇒ **无概率可算**；其事件（地震）不接数据（§5.6）。

### 9.1 逐图概率来源（命令 + 权重 + 名称）

| 图 | 族 | 概率命令（`probe=`） | 权重数组 | 名称来源 |
|---|---|---|---|---|
| Isl / Sco / Cen | uds | `actor filter=UDS_<?>_Weather props=1 probe=WeatherWeights_Day,WeatherWeights_Night,WeatherEventLengths top=1` | 日/夜两套（各 num=5~8，`asArray.dataHex` 有效槽=`num`） | `weather` 响应 `wxSemantics.arrayProbe.presetTable`（顺序下标对齐） |
| Ext / Ast / Rag / Val / Los | ext_gen | `actor filter=<EXT_WeatherSystem / AST_DayWeather_WeatherSystem / RAG_DayWeather_WeatherSystem / LC_DayWeather_WeatherSystem> props=1 propsIdx=0 probe=WeatherChances,PossibleWeatherChances top=1` | `WeatherChances`（num 4~7，**动态**） | 固化表（文档 §12.2 抄录）+ `lbWxNameZh` 中文化 |
| Gen | ext_gen | `actor filter=DayWeather_WeatherSystem props=1 propsIdx=<0..5> probe=WeatherChances,WeatherPresetList top=1` | 各图独立（1/2/7 槽）；**仅 ocean 图有多样天气** | `WeatherPresetList` objects（含 `_Ocean_` 标识的实例 = 海洋图） |

- uds 的 `filter=` 因图而异：Sco=`UDS_SE_Weather`（已实测）；**Isl/Cen 类名待实测**（`scan filter=UDS_` 一次确认）。
- 全部只读、低频（300 s 缓存，与热力图同级；参考体积：UDS ~21 KB / ext_gen ~16 KB / Gen ~18 KB，未 slim）。
- 文档实测基准值见 §12.2（如 Sco 白天：热浪 31.8% / 晴 22.7% / 雨 15.9% / 沙尘暴 11.4% / 雾 6.8% / 焚风 6.8% / 雷暴 4.5%）。

### 9.2 归一化算法（统一口径）

`pct[i] = w[i] ÷ Σ(w 中正值) × 100`（一位小数）；`w[i] ≤ 0` 的槽不显示。

- **uds 分昼夜**：按游戏内时间取昼/夜那一套（前端已有游戏钟 `lbIg`；Sco 昼夜界 05:30–20:30 口径已有，Isl/Cen 同法）
- ext_gen 单套（`WeatherChances` 已含曲线下调后的实时值）
- **不写死概率**（每 300 s 重取重算）

### 9.3 后端聚合路由 `/api/worldprobe_wprobs`（设计）

- 入参：`server`；出参：`{ok, server, family, slots:[{i, weight, pct}], num, worldTime, cacheAgeMs, serverNowMs}`
- 内部实现（示意）：
  1. 按 §9.1 映射选命令（`family` 依服务器静态映射：Isl/Sco/Cen→uds …）
  2. `_wp_rcon_json(port, cmd, …)` → 取 `probes.<名>.asArray.dataHex`
  3. 解析：`struct.unpack('<16d', bytes.fromhex(hexStr))[:num]`
  4. 归一化（§9.2 算法在**后端**执行；uds 昼夜**两套都返回**并标注 `day`/`night`，由前端按时段取用）
  5. TTL 300 s + `_wp_lock` 同键合并 + `_wp_trim`
- ⚠️ `dataHex` 需 v119+（线上 v122b2 ✅）；解析失败返回 `{ok:false, reason}`（前端静默）
- ⚠️ `probes` JSON 精确路径以真实响应为准——**实施第一步先跑一次真实命令固化路径**（见 §9.5）

### 9.4 前端显示设计（概率行）

- 位置：**面板底部说明行区**（「数据来自游戏内天气装置…」上方一行；灰字小字，**非卡片、不进主流程卡**）
- 文案：`📊 下一轮天气概率：热浪 31.8% · 晴 22.7% · 雨 15.9% · 沙尘暴 11.4% · 雾 6.8% · 焚风 6.8%`（降序 · 仅 >0% · 一位小数；超宽自动换行）
- 时段：uds 按当前昼夜取一套；ext_gen 单套；**Gen 仅海洋图**（同款行）
- 名称：`presetTable` / 固化表 → `lbWxNameZh` 中文化（`_SE`/`_TC` 后缀剥离已有能力；**Los 三种 ClearSky 按角标区分显示（晴 / 晴² / 晴³）**——与 §9.0 ※ / §9.6 口径一致）
- 取数：新增 `lbProbSync`（300 s 复用 + 单飞 abort + 失败静默 + 开窗/切图钩子；与 `lbBioSync` 同范式）
- 静默：路由未就绪 / 数据空 → **整行不输出**（零残留）

### 9.5 验收（PW）

1. **实施第一步（后端）**：真实调一次各图命令，固化 `probes` 路径 + `num` 切片（Sco / Isl / Ext / Rag / Gen 各一）
2. 前端上线后：Sco 面板概率行数值 = 文档 §12.2 口径重算值（±四舍五入）；Isl = 5 槽口径；Rag = 6 槽口径；Gen = 海洋图 7 槽口径
3. Abe 面板零残留；断源静默；非对应图无「概率」字样

### 9.6 词典修订清单（实施 v4365+ 时同步；2026-10-06 用户口径）

> 目的：概率行/角标等一切显示与 §9.0 中文列一致。现行值经 `tmp\_dict_probe.py` 实测（HTML `LB_WX_ZH`/`TOK` + `weather_zh.json`）。

**A. 改值（现值 → 新值）**

| 键 | 现值 | 新值 | 改动位置 |
|---|---|---|---|
| `Superheat` | 极热 | **焚风** | `LB_WX_ZH` + `weather_zh.json` + `TOK` |
| `Foggy` | 雾天 | **雾** | `LB_WX_ZH` + `weather_zh.json` |
| `Clear_Skies` | 晴天 | **晴** | `LB_WX_ZH` + `weather_zh.json` |
| `ClearSky` | 晴空 | **晴** | `LB_WX_ZH` + `weather_zh.json` + `TOK` |
| `ClearSkyV2` / `ClearSky_V2` | 晴空 V2 | **晴²** | `LB_WX_ZH` + `weather_zh.json` |
| `Partly_Cloudy` | 晴间多云 | **晴转多云** | `LB_WX_ZH` + `weather_zh.json` + `TOK`（词元 `Partly:'晴间'`→`'晴转'`） |
| `HeatWave` / `Heatwave` | 热浪 | 保持（v4364 已改） | — |
| `MeteorShower` | 流星雨 | 保持（**Gen 月球事件名**；词典已有） | — |

**B. 新增键（当前无键 ⇒ 显示英文原名）**

| 键 | 新值 | 备注 |
|---|---|---|
| `Overcast` | **阴** | Ext |
| `Spooky` | **晦** | Ext |
| `ClearSkyV3` | **晴³** | Los |
| `MeteorRain` | **陨石雨** | **Ext 事件名**（本次新增；与 Gen 月球「流星雨」严格区分） |

> 📌 **Los 三种 ClearSky 角标区分口径（用户定稿）**：基础 `ClearSky` → 「**晴**」· `ClearSkyV2`/`ClearSky_V2` → 「**晴²**」· `ClearSkyV3` → 「**晴³**」——`²`/`³` 用**上标字符**（U+00B2 / U+00B3）；在**一切显示层**（概率行 / 当前天气卡 / 角标等所有走 `lbWxNameZh` 的位置）同此口径；**显示层代码无需逐图特判**（词典层统一覆盖）。

> ⚡ **「流星雨 / 陨石雨」两雨区分（用户定稿）**：**Gen 月球 = 「流星雨」**（`MeteorShower`，词典已有·保持）；**Ext = 「陨石雨」**（`MeteorRain`，本次新增）——两者**不得混用**。

**C. 实施要点（前缀名）**

- Ast / Rag / Val / Los 的预设名带前缀（`DA_WeatherPreset_AST_*` / `WeatherPreset_RAG_*` / `WeatherPreset_LC_*` 等）：现 `lbWxNameZh` 对整名/词元均不命中 ⇒ 概率行会显英文原名。
- 处置（**推荐 ②**）：① 词典加完整键；② `lbWxNameZh` 增**前缀剥离**（剥掉 `WeatherPreset_` / `DA_WeatherPreset_` 后再走现查询链）。
- `Cloudy` 现由 `TOK` 词元兜底为「多云」✅（可选：在 `LB_WX_ZH`/`weather_zh.json` 补显式键，防词元链变动）。

---

## 10. ★ 特殊事件浮窗化（Gen / Abe / Rag）—— v3 新增（2026-10-06 用户口径）

> 用户口径：「Abe 灼烧（已实现）与地震；Rag 火山喷发；Gen 火山、巨浪、漩涡、雪崩、流星雨——**都应该放进类似 Gen 火山计时的浮窗里**」；按钮改名：**Gen「生态圈事件」/ Abe「特殊事件」/ Rag「火山计时」**。

### 10.1 按钮与浮窗总览

| 图 | 按钮（新） | 原按钮 | 浮窗区块 | 数据源 |
|---|---|---|---|---|
| **Gen** | 「🧬 生态圈事件」 | 「🌋 火山计时」 | ①🌋 火山计时 ②🌊 巨浪 ③🌀 漩涡 ④🏔️ 雪崩 ⑤🌠 流星雨 | 现有火山 + `wave` + `actor`（LunarMeteor）+ 文案 |
| **Abe** | 「🌓 特殊事件」 | 「🌓 地表计时」 | ①🌓 地表灼烧计时（现有全量） ②🌎 地震 | 本地推算（现有）+ 文案 |
| **Rag** | 「🌋 火山计时」（**新增**） | —（原无） | ①🌋 火山喷发 | `actor`（VolcanoManager） |

- 浮窗标题：同按钮名 + 「 · 图名」（如「🧬 生态圈事件 · 创世」）
- 图标为建议值（可调）；Abe 沿用 🌓、火山系列沿用 🌋

### 10.2 实现结构（复用现有壳，统一入口）

- **按钮注册**（`LB_SRV_FUNCS`）：Gen `['sve','weather']` / Abe `['sve','weather']` / Rag `['sve','weather']`（Rag 为新增图项）
- **按图 label 映射**（新增 `LB_FUNC_ALT_LABEL = { Gen:'🧬 生态圈事件', Abe:'🌓 特殊事件', Rag:'🌋 火山计时' }`，`lbRenderFuncBar` 取用）
- **统一入口**：`lbSveOpen()` → `lbFuncPanelOpen('sve', title, 'lbSveClose')`；`lbSveRender()` 按 `lbVolcServer()` 分派渲染区块列表
- **区块化**：现有 `lbVolcRender`（Gen 火山）与 `lbSurfRender`（Abe 地表）改造为**区块函数**（内容不动，外层并入浮窗）；新增巨浪/雪崩/流星雨/地震区块（漩涡留待数据源）
- **tick/poll**：共享壳 Poll/Tick 按图挂数据刷新（Gen：wave 60 s + 流星雨 actor 30 s + 火山现有；Rag：火山 actor 30 s；Abe：游戏钟自走）；关窗 abort（同现有范式）
- **降级**：某区块数据未就绪（路由缺 / 字段空）→ 该区块不输出（零残留）；全空显示「暂无事件数据」

### 10.3 各区块设计（数据 → 显示）

**⓵ 🌋 火山计时（Gen）**：现有实现整体迁移（数据源与台账逻辑不动）；仅外层按钮名/标题改。

**⓶ 🌊 巨浪（Gen）**：`wave`（§4 修订版）——显示「海况：平静（0.35） · 距变化 ≈22 分」+「浪高 47.25 · 陡度 7 · 速度 1.5」（主海洋组 = `oceanTile` 最大）；`WaveState≥0.7` 橙色高亮为拟议（待实测校准）。

**⓷ 🌀 漩涡（Gen）**：**数据源待插件补充**（文档仅提示气旋 `Buff_CycloneBox_C` / `Buff_UnderwaterCyclone_C` 属另一套机制，未给读取方法）——首版**不显示该区块**；回执见 §10.5。

**⓸ 🏔️ 雪崩（Gen）**：说明文案（文档 §15.3）：「雪崩是雪山区域的地形随机事件：走进积雪坡面 / 谷地时约 25% 触发；同一处反复经过概率逐次 +5%（最多 15 次必触发），两次之间至少间隔 3 分钟。触发前有约 10~15 秒预警，听到预警请立刻离开坡面——滑体速度约 750 单位/秒，直线跑离通常可躲开。」

**⓹ 🌠 流星雨（Gen）**：`actor filter=LunarMeteorController`——「距下次流星雨 ≈X 分」（ETA = Last+Actual−worldTime）；进行中（ETA≤0<ETA+240 s 区间）显示「流星雨进行中 · 剩 ≈X 分」；⚠️ 空服不推进 ⇒ ETA 持续为负时显示「等待玩家上线后计时恢复」。

**⓺ 🌓 地表灼烧计时（Abe）**：现有实现整体迁移（紫/绿区、红区、双倒计时、时长、死神活跃/退场、MDI 图标等**全量不动**）。

**⓻ 🌎 地震（Abe）**：说明文案（文档 §2.5）：「地震为随机事件，服务器不定期发生；发生时屏幕剧烈抖动，洞穴内可能落石，请注意躲避。」+ 征兆补充（相机抖动 / 落石尘土 / 音效——§2.5.1）。

**⓼ 🌋 火山喷发（Rag）**：`actor filter=VolcanoManager`——① 喷发中（`VolcanoActive=1`）：「喷发中 · 强度 xx% · 剩 ≈X 分」（`TimeVolcanoEventEnds−worldTime`）；② 已排期（`Tnext>0`）：「距下次喷发 ≈X 分」；③ `Tnext=0`：「空闲期·未排期」（重启后需等一次事件结束才会排期）；⚠️ **不走 volcano_log**（该服务仅 Gen，见 §8）。

### 10.4 数据链与依赖

| 区块 | 依赖 | 状态 |
|---|---|---|
| Gen 火山 / Abe 地表 | 现有链路 | ✅ 就绪 |
| Gen 巨浪 | 后端 `/api/worldprobe_wave`（§2） | 待后端 |
| Gen 流星雨 / Rag 火山 | 后端 `/api/worldprobe_actor`（§2） | 待后端 |
| Gen 雪崩 / Abe 地震 | 仅文案（无数据） | ✅ 可先做 |
| Gen 漩涡 | **插件侧数据源缺失** | ⛔ 待补读取方法 |

### 10.5 回执（给后端/插件侧）

- 🌀 **Gen 漩涡（气旋）**：请在下轮插件文档补充气旋的读取命令与字段（如 `Buff_CycloneBox_C` / `Buff_UnderwaterCyclone_C` 的位置 / 强度 / 倒计时）；前端「生态圈事件」已预留该区块。
- （其余依赖已在 §2 路由批次覆盖。）

### 10.6 实施顺序

随 §6 序 8（**v4370**）：先做**纯前端部分**（三图按钮改名 + 浮窗壳统一 + 雪崩/地震文案区块 + 现有两浮窗迁移），随后按后端路由就绪逐个点亮巨浪 / 流星雨 / Rag 火山区块；漩涡待数据源。

---

## 附：三环职责与不变量

- **插件（dll）**：唯一真源；只读命令 + 秒级时钟 + `slim=1` 瘦身
- **后端（dino_backend.py）**：**唯一 RCON 出口**（每命令独立连接；TTL 缓存 + 同键合并 ⇒ N 客户端不放大 RCON 压力）；对前端只暴露稳定 HTTP 声明
- **前端（dino-import.html）**：只展示；区域位规范（§1）；feature-detect + 静默降级；世界钟一律用 `weather.worldTime`
