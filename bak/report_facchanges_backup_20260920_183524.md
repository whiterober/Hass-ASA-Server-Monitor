# 后端设施清单变更（`isPublic` + 漏采修复）— 前端配合改动报告

> 日期：**2026-09-20**
> 后端输入文档：`报告/设施清单漏采修复与isPublic字段_前端调用文档_20260920.md`
> 前端版本基线：`dino-import.html` = **v20260920-3427**
> 本报告数据来源：**局域网直读实服产物** `\\SERVER\ARK Server\DinoData\<Abbr>_cryo.json.gz`（只读），
> 加前端源码逐处核对（行号以 v3427 为准）。
> 结论一句话：**后端是纯追加式（无破坏性）改动；前端"恰好"没被污染，但存在 3 处必须补的配合项（语义、缓存、汉化），以及 1 处口径待定（公共设施是否展示）。**

---

## 一、后端这次到底改了什么（分析）

### 1.1 变更本体

| 项 | 内容 |
|---|---|
| 生成器 | `DinoData\ark_save_reader.exe` = **1,547,776 B**，mtime **2026-09-20 16:07:47** |
| 字段 | **新增 `isPublic`**（int 0/1，追加在 `isPlayerStructure` 之前），旧字段全部保留 |
| 数据量 | 10 图 `facilities[]` 合计 **4000 → 6454（+61%）** |
| 公共设施 | 10 图合计 **190 条** `isPublic=1` |
| 命令/接口 | **无删除、无改名、无改语义** |

### 1.2 判定口径（源码事实）

```
FACILITY_DICT_NAMES[]（玩家设施 114 条，含今日新增耕地/船体/蜂巢…）  ★优先
        ↓ 未命中
FACILITY_PUBLIC_NAMES[]（公共设施 6 条：ArtifactCrate / CityTerminal / PowerNode /
                         SupplyCrate / PrimalStructure_CityTerminal / PrimalStructurePowerNode）
判定顺序保证：命中玩家设施字典 ⇒ 一律 isPublic=0（例：BeeHive_PlayerOwned）
```

### 1.3 本次补采的家族（此前被整体丢弃）

耕地 `CropPlot*`（279）、船体 `*ShipBP`（16）、`GasCollecter_ASA`（6）、
电力节点 `PrimalStructurePowerNode*`（101，公共）、城市终端 `PrimalStructure_CityTerminal_BP*`（27，公共）、
神器箱 `ArtifactCrate_*`（62，公共）、`BeeHive_PlayerOwned`（5）、`SM_Vessel_BP`（9）、
`OilPump`（10）、`StructureTurretCatapult`（1）。

### 1.4 独立复现（本报告实测，**与文档完全一致**）

| 图 | `facilities[]` | 文档值 | `isPublic=1` | 文档值 | 一致性 |
|---|---:|---:|---:|---:|:---:|
| Isl | **1437** | 1437 | **10** | 10 | ✅ |
| Abe | **793** | 793 | **104** | 104 | ✅ |
| Ast | **1214** | 1214 | **12** | 12 | ✅ |

> 复现方式：`gzip.open(r'\\SERVER\ARK Server\DinoData\<Abbr>_cryo.json.gz')` → `json['facilities']`
> （脚本：`tmp/_cryoprobe2.py`，产物：`tmp/_cryoprobe2.txt`）

### 1.5 ⭐ 关键实测：公共设施的字段形态（文档未给出，已补上）

| 分组 | 条数（抽样 3 图） | `tribeId` | `isPlayerStructure` |
|---|---:|---|---|
| `isPublic=1` | 126 | **全部 `0/无`** | 全部 `0` |
| `isPublic=0`（Abe/Isl） | 2116 | 全部**有值** | 全部 `1` |
| `isPublic=0`（Ast 异常组） | **6** | `0/无` | 含 **2 条 `0`** |

样例（Abe）：`PrimalStructurePowerNode_Damaged_7` / `tribeId=0` / `isPlayerStructure=0`
样例（Isl）：`ArtifactCrate_2_C_2147143156` / `tribeId=0` / `isPlayerStructure=0`

**两条重要推论**：

1. **"公共 ⇒ tribeId=0" 在实服数据里成立**（126/126），因此前端现有那句隐式过滤
   `if(!f.tribeId) return;` **目前恰好**把公共设施挡在外面（这也是为什么至今没人发现公共设施混进聚落）。
2. 但 **`tribeId=0` ≠ 公共**：Ast 的 6 条 `isPublic=0 且 tribeId=0` 正是文档说的
   **自然生成物**（如 `BeaverDam`）。⇒ 现有隐式过滤**语义不完整**：
   - 它会把自然物一起丢掉（当前无害，但不可控）；
   - 一旦后端给某类公共设施带上 `tribeId`（例如未来把"玩家占领的神器箱"标注归属），
     **公共设施就会直接混进聚落设施清单**，而前端没有任何开关能拦。

---

## 二、前端现状盘点（逐处代码定位）

| # | 位置（v3427） | 现状行为 | 与本次后端变更的关系 |
|---|---|---|---|
| 1 | `dino-import.html` **L4285–L4299** `cryo.facilities.forEach` | 生成 `facility` rec。过滤链：无 `class` → 丢；`_decorRe` 装饰 → 丢；**无坐标 → 丢**；**`!f.tribeId` → 丢**。落字段：`containerId=f.key`、`containerClass=f.class`、`containerName=f.name`、`containerTribe/ownerTribeId=f.tribeId`、`colorRegions`、`x/y/z` | **未读取 `isPublic` / `isPlayerStructure`** ← 本次要补 |
| 2 | L4290 注释 | 原文：`// 无部落跳过（野生/公共设施不归属玩家聚落）` | 设计意图就是排除公共 ⇒ 新字段可**替换**这段隐式逻辑 |
| 3 | **L494** `var LB_SCHEMA_VER = 16;` | IndexedDB 缓存版本闸门（`_schemaVer !== LB_SCHEMA_VER` ⇒ 全量重拉） | **不 bump ⇒ 用户看到的仍是旧 cryo（无新设施/无 isPublic）** |
| 4 | **L12960+** `lbSettleFacMeta(cls)` | ① `def[]` 正则表 → ② `facility_zh` 查表 → ③ 通用英文基名。**键归一化链**：剥 `PrimalItemStructure_` / `StructureBP_` / `Structure_` / `Structure` / `BP_` / `PrimalInventory(BP)_` / `PrimalItem_` / `PrimalStructure_` + 去尾 `_C_\d+$` / `_C\d*$` / 前导 `_` | **不剥 `_\d+$`** ⇒ `PrimalStructurePowerNode_2951` 归一化后为 `PowerNode_2951`，**即使补了 `PowerNode` 键也命中不了** ← 要补 |
| 5 | **L12281** `LB_FACILITY_ZH` 加载 | `authFetch(LB_ASA + '/facility_zh.json?v=' + LB_VERSION)`（CF 静态） | 新类名需补表，否则 chip 显示英文类名 |
| 6 | **L8539** `LB_CONTAINER_DISP._cls` | 类型/图标正则表（冰箱/展示柜/储物箱…） | 无耕地/船体/电力节点/神器箱 ⇒ 只影响图标回退，不影响识别 |
| 7 | **L8613** `LB_FAC_RENAMEABLE` | 改名白名单（容器 + 床/棺/睡眠舱 + 牌/碑） | 新家族**无官方改名通道** ⇒ **无需**加入（保持现状正确） |
| 8 | 聚落/区域算法（`_fList` 组装 L11828+ → `lbFacAreasBuild`） | `_fList` = `s.beds` + `s.facilityList` + 下沉空容器；**进入后参与分层/聚类/区域命名** | 新补采的**玩家设施**（耕地/船体/蜂巢/油泵/陶罐/投石机）**会直接进入 chips 与区域几何** ← 需评估 |
| 9 | 全景 | 前端**完全没有"公共设施"概念**（全库 grep：仅 1 处注释提到） | 公共设施若将来要显示，需新增一套渲染/归区口径 |

---

## 三、影响矩阵（变更 → 现状 → 风险 → 处置）

| # | 变更 | 前端当前表现 | 风险等级 | 处置 |
|---|---|---|---|---|
| 3.1 | 新增 `isPublic` | 未读取；靠 `!tribeId` 隐式排除公共 | 🟡 中 | **P0**：显式读取并落字段；保留 `!tribeId` 作兜底 |
| 3.2 | facilities 总量 +61% | 装饰/无坐标/无部落三重过滤后**净增的都是玩家设施**（耕地 279、船体 16、蜂巢 5、油泵 10、陶罐 9、投石机 1）⇒ 直接进聚落 chips 与区域划分 | 🔴 高 | **P1**：评估耕地等大数量设施是否参与区域几何（见 4.4） |
| 3.3 | 出现全新 `class` | `facility_zh` 未命中 ⇒ chip 显示英文/类名 | 🟠 中高 | **P0**：键归一化补丁 + `def[]` 正则兜底；**P1**：重跑生成器补表 |
| 3.4 | 缓存 | `LB_SCHEMA_VER=16` 未变 ⇒ 旧 IndexedDB 缓存继续命中，新数据永不出现 | 🔴 高 | **P0**：`16 → 17` |
| 3.5 | `isPlayerStructure` 语义（易误用） | 前端目前未使用（无历史包袱） | 🟢 低 | 文档明确"**禁止**用 `isPlayerStructure=0` 反推公共" ⇒ 落到代码注释里防回归 |
| 3.6 | 公共设施（190 条） | 被 `!tribeId` 丢弃 ⇒ 页面上看不到神器箱/电力节点/城市终端位置 | 🟡 中（产品口径） | **口径待定**（见第五节，本次不改） |

---

## 四、建议改动清单（精确落点 + 补丁片段）

### 4.1 P0-① 显式读取 `isPublic`（语义对齐）

**落点**：`dino-import.html` L4285 起 `(cryo.facilities||[]).forEach(function(f){ ... })` 内。

```js
(cryo.facilities||[]).forEach(function(f){
  if(!f || !f.class) return;
  var _cc = f.class || '';
  // v3428：后端 2026-09-20 新增 isPublic（旧缓存缺字段 ⇒ 按 0 处理）
  //   ⚠ 禁止用 isPlayerStructure===0 反推公共：isPlayerStructure=0 有两种可能（公共 / 自然生成物，如实测 Ast 的 BeaverDam）
  var _pub = (f.isPublic === 1) ? 1 : 0;
  // （口径待定）当前先显式排除公共设施，等价替换原先的隐式 !tribeId 过滤
  if(_pub) return;
  if(_decorRe.test(_cc) && !_decorKeepRe.test(_cc)) return;
  if(!(Number(f.x)||Number(f.y))) return;
  if(!f.tribeId) return;          // 保留：自然生成物 / 数据异常兜底
  ...
  lbAddRec({ ..., isPublic:_pub, isPlayerStruct:(f.isPlayerStructure === 1) ? 1 : 0, ... });
```

> 说明：`isPublic/isPlayerStruct` 落到 rec 是**为将来展示/筛选留口**（rec 会进 IndexedDB，配合 schema bump 一起生效）。

### 4.2 P0-② 缓存版本闸门

**落点**：L494。

```js
var LB_SCHEMA_VER = 17;   // v3428：16→17 —— facilities 新增 isPublic / 补采家族 + rec 新增 isPublic/isPlayerStruct；
                          //   不升版 ⇒ 旧 IndexedDB 缓存继续命中，新设施与新字段永不出现
```

### 4.3 P0-③ 键归一化 + 中文/图标兜底

**落点 A**：`lbSettleFacMeta` 的归一化链（L12992），在去 `_C` 后补一条：

```js
.replace(/_\d+$/, '')     // v3428：数字后缀 —— PrimalStructurePowerNode_2951 → PowerNode（实服 Abe 101 条）
```

**落点 B**：`lbSettleFacMeta` 的 `def[]` 正则表（L12960 段）追加（免发版兜底，即使 `facility_zh.json` 未更新也能显示中文）：

```js
{re:/ArtifactCrate/i, key:'artifact_crate', zh:'神器箱',   icon:'ArtifactCrate_Icon', en:'Artifact Crate'},
{re:/PowerNode/i,     key:'power_node',     zh:'电力节点', icon:'PowerNode_Icon',     en:'Power Node'},
{re:/CityTerminal/i,  key:'city_terminal',  zh:'城市终端', icon:'CityTerminal_Icon',  en:'City Terminal'},
{re:/CropPlot/i,      key:'crop_plot',      zh:'耕地',     icon:'CropPlot_Icon',      en:'Crop Plot'},
{re:/(Galleon|Trireme|Sloop|Brig)Ship/i, key:'boat', zh:'船体', icon:'Vessel_Icon', en:'Ship'},
{re:/GasCollect/i,    key:'gas_collector',  zh:'气体收集器', icon:'GasCollector_Icon', en:'Gas Collector'},
{re:/BeeHive/i,       key:'beehive',        zh:'蜂巢',     icon:'Beehive_Icon',       en:'Bee Hive'},
{re:/Vessel/i,        key:'vessel',         zh:'陶罐',     icon:'Vessel_Icon',        en:'Vessel'},
{re:/OilPump/i,       key:'oil_pump',       zh:'油泵',     icon:'OilPump_Icon',       en:'Oil Pump'},
{re:/Catapult/i,      key:'catapult',       zh:'投石机',   icon:'Catapult_Turret',    en:'Catapult Turret'}
```

> ⚠️ `icon` 必须在 `icons2.json`（`LB_ICON_BY_NAME`）存在，否则走 `lbFacilityIconFind` 强查找或 MDI 齿轮兜底 —— **落地前用页面内 `LB_ICON_BY_NAME[key]` 逐一校验**。

### 4.4 P1-① 大数量新设施对区域算法的影响（**必须先量再改**）

实服玩家设施净增（耕地为主）：

| 新家族 | 实服条数 | 是否进 `_fList` | 影响 |
|---|---:|---|---|
| `CropPlot*_SM` | **279**（Isl 114、Abe 53…） | 是（有 tribeId + 坐标） | 可能**显著改变区域数量/形状**（此前这些点不存在） |
| 船体 `*ShipBP` | 16 | 是 | 船是"移动结构"，坐标随位置 ⇒ 可能形成孤立小区域 |
| `OilPump`/`SM_Vessel_BP`/`BeeHive_PlayerOwned`/`StructureTurretCatapult` | 25 | 是 | 量小，影响有限 |

**建议动作（按序）**：
1. 用同一份 cryo 在页面内**对比改动前后**：`facilities` 过滤后条数、区域数量、区域命名变化（可复用 v3425 的只读 evaluate 手法）；
2. 若耕地导致区域碎裂/命名漂移 ⇒ 二选一：
   - **A**：耕地**参与显示但不参与区域几何**（在 `_fList` 组装处打 `_silent:true` 类似标记，使其只出现为 chip，不进分区点集）；
   - **B**：耕地**按类型聚合**为"耕地 ×N"单条 chip（复用现有 `_grp`/`×N` 合并逻辑）。
3. 结论写回本报告附录并再发一版。

### 4.5 P1-② 补表（服务器维护，免发版）

```powershell
Push-Location "b:\项目\Hass ASA Server Monitor"
.\.venv-1\Scripts\python.exe "汉化\_build_facility_zh.py" --fetch   # 并入 11 服真实在用 class
# 审阅 汉化/facility_zh.review.txt ⇒ 手工补别名后重跑
# 上传：汉化/facility_zh.json → /config/www/asa-data/facility_zh.json （流程见 汉化/ARK设施汉化生成流程.md）
# 前端接入：确认 tmp\_sync_repack2.py 的 STATIC 清单已含 facility_zh.json ⇒ 重跑 tmp\_deploy_cf.py
```

### 4.6 实测未命中清单（本报告新增，**文档未列**）

| 图 | 命中 | 未命中 | 未命中主要键（实服实测） |
|---|---:|---:|---|
| Abe | 630 | **163** | `CropPlotMedium_SM`×26、`CropPlotSmall_SM`×19、`CropPlotLarge_SM`×8、`GasCollecter_ASA`×6、`PrimalStructurePowerNode_*`（含 `_Damaged_`）各 1 |
| Isl | 1316 | **121** | `CropPlotSmall_SM`×63、`CropPlotMedium_SM`×34、`CropPlotLarge_SM`×12、`SM_Vessel_BP`×2、`ArtifactCrate_{1,2,3,5,6,7,8,9,10,11}` 各 1 |
| Ast | 1175 | **39** | `CropPlotLarge_SM`×15、`TriremeShipPlayerFollowingBP`×4、`CropPlotMedium_SM`×4、`OilPump`、`BeeHive_PlayerOwned`、`GalleonShipBP`、`TriremeShipBP`、`ArtifactCrate_{2,3,5,6,7,8,10,11}[_SE]` |

> 🔎 **文档缺口 1**：**焦土（SM）耕地是独立类名** `CropPlotSmall_SM / CropPlotMedium_SM / CropPlotLarge_SM`
> （文档只写了 `CropPlot*`，实服 279 块里绝大多数是 `_SM` 变体）⇒ 补表/补正则必须覆盖。
> 🔎 **文档缺口 2**：`TriremeShipPlayerFollowingBP`（三列桨战船·跟随态）同样未在文档表格出现。

---

## 五、公共设施展示方案对比（**口径待定，本轮不改**）

| 方案 | 做法 | 优点 | 代价 / 风险 |
|---|---|---|---|
| **A 显式排除**（最小改动） | `if(_pub) return;` | 语义清晰、零副作用；顺带修掉"自然物被误丢"的不可控 | 页面上仍看不到神器箱/电力节点/城市终端的位置 |
| **B 独立「公共设施」分组** | rec 带 `isPublic`；聚落详情新增一组灰底 chip（**不参与**命名、**不进**区域几何点集），或走独立"分布地图"点层 | 能定位神器箱（实用）；不污染区域算法 | 需新增渲染分支 + 归区口径（就近聚落？固定半径？还是只按地图点列出） |
| **C 只显示神器箱** | 只对 `ArtifactCrate*` 落 B | 神器箱最实用（找神器） | 电力节点（Abe 101 条）/城市终端（Ext 27 条）仍不可见 |

> **推荐**：**B**，并采用"**不进区域算法 + 按坐标就近附到聚落**（超出半径则进独立地图点层）"的折中；
> 若你更看重"地图找神器箱"，也可选 C 先行、B 后续扩展。
> 无论选哪个，**`isPublic` 都必须先显式读取**（P0-①），否则口径无法落地。

---

## 六、验证清单（改动后逐项执行）

- [x] **数据层**：10 图 `facilities[]` 条数与实测一致（Isl 1437 / Abe 793 / Ast 1214 …） ⇒ ✅ **2026-09-20 实测一致**（10 图合计 6454；Bob 产物缺失待查）
- [x] **公共设施**：抽样 3 图 126 条 `isPublic=1` ⇒ 按选定口径处理（未污染聚落/区域） ⇒ ✅ **实测 `pub 且 tribe≠0` = 0**（Isl 10 / Abe 104 / Ast 14）；展示口径仍待第五节拍板
- [x] **缓存**：`LB_SCHEMA_VER` 升级后，**旧用户强刷即见新家族**（不清缓存也能自动重建） ⇒ ✅ **线上 `LB_SCHEMA_VER=17`**（v20260920-3433）
- [x] **汉化**：新家族 chip 全中文、无英文类名裸露（重点抽查耕地 `_SM`、电力节点、城市终端） ⇒ ✅ **P1-② 补表后 11 服归一化基名 123 个全覆盖（未覆盖=0，facility_zh 185→215 键）**；34 条核对表已由用户确认
- [x] **图标**：`LB_ICON_BY_NAME` 命中验证（未命中的走 MDI 齿轮，需确认可接受） ⇒ ✅ **def[] 关键图标 11/11 命中 icons2 且全部有 96px 缩略图**（全库覆盖 5016/5118 = 98.0%）
- [ ] **区域算法**：改动前后区域数量 / 命名对照（Isl 与 Abe 必做） ⇒ ⏳ **待人工实测**：需「选服 → 载入 cryo」重交互，10s 硬约束下 PW 不宜排队等待
- [ ] **回归**：容器手风琴无重复项（facility 与容器 rec 同源）；床/牌/碑改名入口不受影响 ⇒ ⏳ **待人工实测**（代码路径已静态确认：v3426 两类 rec 同走 `_rec` 通道）
- [ ] **性能**：首屏 CJK 无卡顿（Isl recs 体量增长后 `lbBuildSettlements` 耗时对比） ⇒ ⏳ **待人工实测**（线上 index 1190KB / HTTP 1.8s 已测）

---

## 七、风险与兼容性小结

| 项 | 结论 |
|---|:---:|
| 后端破坏性变更 | **无** ✅（纯追加字段 + 补采） |
| 前端当前是否已被破坏 | **否** ✅（隐式 `!tribeId` 恰好挡住公共设施） |
| 前端必须改 | **是** —— P0 三项（isPublic 语义、schema 版本、键归一化+汉化兜底） |
| 可不改但建议改 | P1（补表、耕地参与区域几何的取舍） |
| 需产品口径决策 | 公共设施是否展示（第五节） |

---

## 八、附录：复现命令与原始数据

### 8.1 复现脚本（只读）

```python
# tmp/_cryoprobe2.py 关键片段
UNC = [r'\\SERVER\ARK Server\DinoData']          # 实服产物（Qsync 同步目录）
with gzip.open(os.path.join(root, ab + '_cryo.json.gz'), 'rb') as f:
    data = json.loads(f.read().decode('utf-8'))
fac = data.get('facilities') or []
pub = [x for x in fac if x.get('isPublic') == 1]
```

### 8.2 原始实测输出（`tmp/_cryoprobe2.txt` 摘要）

```
==== Abe ====  793 条  isPublic=1 104
  公共: tribeId {'0/无': 104} | isPlayerStructure {'0': 104}
  非公共: tribeId {'有值': 689} | isPlayerStructure {'1': 689}
  facility_zh 命中 630 / 未命中 163
==== Isl ====  1437 条  isPublic=1 10   （ArtifactCrate_2/11/9/6… 全 tribeId=0）
  facility_zh 命中 1316 / 未命中 121
==== Ast ====  1214 条  isPublic=1 12
  非公共: tribeId {'有值': 1196, '0/无': 6} | isPlayerStructure {'1': 1200, '0': 2}   ← 自然生成物
  facility_zh 命中 1175 / 未命中 39
```

### 8.3 前端落点索引（v3427 行号）

| 项 | 行号 |
|---|---|
| `LB_SCHEMA_VER` | L494 |
| `cryo.facilities.forEach` 生成 rec | L4285–4299（过滤在 L4290） |
| `structures` 过滤 | L4788 |
| `LB_CONTAINER_DISP._cls` | L8539 |
| `LB_FAC_RENAMEABLE` | L8613 |
| `_fList` 组装（beds / facilityList / 下沉空容器） | L11828–L11935 |
| `lbFacAreasBuild`（区域分层/聚类/命名） | L12673+ |
| `lbSettleFacMeta`（汉化/图标解析 + 键归一化） | L12960+（归一化链 L12992） |
| `LB_FACILITY_ZH` 加载 | L12281 |
