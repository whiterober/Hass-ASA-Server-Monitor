# WorldProbe 公共设施全面改造 · 完整实施计划

> 生成：2026-09-30 ｜ 目标项目：dino-import（CF Worker 纯 Assets 架构）
> 依据：《WorldProbe 前端交接单》（插件 v9，dll 1,594,368 B，2026-09-26，10 图已全量部署）
> 修订：v2（2026-09-30）：SupplyCrate/BeaverDam/BeeHive 改**纯实时**；实时区**前置** + 样式对齐静态 + 低可视化 MDI 标记
> 修订：v3（2026-09-30）：**去块内服务器选择器 → 候选图遍历 + 后端聚合路由**；低可视标记**复用页面现有刷新图标**（不新增资源）；新增本地预览页（P0.5）
> 修订：v4（2026-09-30）：**样式修正为格子版**——实时条目逐字复用现状 `.lb-picker-item` 格子（多列网格；**非行式列表**）；坐标入 tooltip
> 修订：v5（2026-09-30，**最终口径**）：① 现状**原样保留**（仅蜂巢/河狸坝/补给箱 3 类迁入实时区、神器箱过滤，其余 27 类一个不动）；② **补全 19 格实时设施置前**；③ **图标一律 webp 缩略图**（`thumbs/webp96`，禁用 PNG 直链）；④ 补给箱 = 6 品质 Beacon 图、洞穴补给箱 = 6 品质 Crate 图；⑤ 预览页 v5 已产出并本地验证；⑥ **单一网格不分段**（无分隔线/小标题），现状区排序**照抄线上真实顺序（禁止重排）**；⑦ 方尖碑/神器箱**过滤**（用户用不到）；⑧ 河狸坝按 3 实体**分 3 格**（河狸坝/大型河狸坝/河狸巢穴）；⑨ 洞穴补给箱/补给箱 = 权威六档**品质前置**（原始/普通/优秀/精良/史诗/传说，去括号不着色）；`LB_BP_STAGE_COL` 注释已按官中修正
> 修订：v6（2026-09-30）：**探险者笔记箱 20 系列全格化**——全服 10 图普查（Gen 重查成功）确认并集 **20 个箱子系列**（Isl 仅 7 类）；实时补全区 **+20 格**（#20~#39；中文=官中、英文=wiki/PO 权威、图标=drops/GUI 现成图）；预览升级 **66 格**；wiki「21 类作者」交叉核对（6 类无独立箱：海莲娜/涅尔瓦/伊玛目/斯凯/妮达/加百列；Leddica/Dmika 为服务器类名独有，待补）
> 修订：**v6.1（2026-09-30，wiki 权威校正）**：抓取 wiki「Explorer Notes/Locations」原始表格（1106 行，列：Type/Topic/Author/坐标/ID）核验——**分类=Type 列**（Note 376/Dossier 150/Glitch Discovery 150/Voice line 114/Record 95/Log 80/Tablet 30/Journal 26/Chronicles 25/Discovery 15…）；**20 格英文名全部改为 game 原文**（去所有格：Rockwell **Record**/Mei Yin **Note**/Dahkeya **Note**/Raia **Tablet**/Diana **Log**/Grad Journal X/Glitch **Discovery**/Darius Archival Audio）；**图鉴图标改用 `HelenaNote_Icon`**（`6e527e1b906f`，Dossier 为 Helena 的作品，用户指定）
> 修订：**v6.3（2026-09-30，归属修正）**：用户指正——**Genesis 2 Chronicles 属于 Santiago**（wiki：Santiago 段下含该项）→ 预览格名改为「**圣地亚哥的创世纪2编年史 / Santiago's Genesis 2 Chronicles**」；图标核对：达瑞斯档案（`Darius_note_icon`）/ 罗克韦尔档案（`Rockwell_LC`）经用户对照候选页确认**保持现状**（无误）
> 修订：**v6.4（2026-09-30，全量对账）**：新增 §1.3.2「21 作者 × 20 格对齐审计」——wiki Locations 表全量（1106 行）Topic 原文逐类比对 + 跨作者 Type（Note/Log/Chronicles）分析 + LC・Darius 页面勘察，**结论：全部对齐**（19 位有格 / Skye 并入 Rusty / Nida・Gabriel 待 Gen2 上线；无第二处归属不明项）
> 修订：**v6.7（2026-09-30，藏宝箱迁入实时）**：**埋藏藏宝箱**（`treasurecache`）自现状区**迁入实时区**（用户口径“变成实时”；全服实测 **15** 个：Isl4/Sco5/Cen1/Abe3/Ast1/Gen1）——实时区 **39 格**（**20 设施含藏宝箱 + 19 笔记箱**）、现状区 **26 格**；预览同步重建（65 格 = 39+26，`rt_marks=39`）
> > 修订：**v6.8（2026-09-30，实施启动）**：用户批准实施（预览验收 ✅）。**新约束（用户口径）：刷新功能 CD + 服务端短时缓存共用**——落地：P0 预检 ✅（types `ok:true`；**字典实测 13 类**，含 `explorerchest`/`treasurecache`）；后端 `CMD_WORLDPROBE` + 4 路由（types 600s / query 5s / weather 10s / scan 聚合 10s + 同键并发合并 single-flight）✅ 已落真身（备份 `.bak_20260930_183458`，md5 一致，**待重启**）；前端改造进行中
状态：**实施中**（2026-09-30 起）｜ P0 ✅ ｜ P1 后端 ✅（待重启）・前端 🔄 ｜ 涉及文件：`独立后端\dino_backend.py`（真身 `\\SERVER\dino_backend\dino_backend.py`）、`dino-import.html`

---

## 1. 目标与范围

### 1.1 一句话目标

把 dino-import 物品浮窗「公共设施」块，升级为「**实时补全 39 格置前 + 现状 26 格原样接续**」的**单一网格**（同一个 `.lb-picker-grid` 盒子、不分段、无分隔线）：

- **实时补全 39 格**（网格最前）：可实时查询的设施——元素节点、野生河狸、轨道空投、洞穴补给箱 ×6、补给箱 ×6、野生巨型蜂巢、河狸坝 ×3（普通坝/大型坝/巢穴）、**埋藏藏宝箱**、**探险者笔记箱 ×19 格**（见 §1.3.1）；
- **现状 26 格**（接续其后）：21 个台座、城市终端 ×4、电力节点（图标/名称/**顺序**全部照旧；神器箱按用户口径**过滤**；藏宝箱 v6.7 迁入实时）。

> 与 v2~v4 的差异：v2 曾设想"静态白名单 4 类 + 三类转纯实时"；**v5 推翻该口径**——静态区不再做白名单删减，改为"仅迁出 4 类（蜂巢/河狸坝/补给箱/藏宝箱）+ 其余原样"（藏宝箱为 v6.7 追加）。

### 1.2 现状区（原样保留，26 类）

| 类别 | 数量 | 说明 |
|---|---|---|
| 上古神器之 X 台座 | 21 | 各有独立图标（真实 webp hash，见 §3.4） |
| 神器箱（已过滤） | — | 用户用不到，2026-09-30 从列表移除 |
| 城市终端（普通/沙漠/雪地/废土） | 4 | `CityTerminal` |
| 电力节点 | 1 | `PowerNode` |

> **迁出 4 类**：`BeeHive`、`BeaverDam`、`SupplyCrate`（用户口径 2026-09-30："静态里的蜂巢/河狸坝/补给箱 在实时里有即可"）+ `TreasureCache` 埋藏藏宝箱（v6.7 用户口径"变成实时"）——从现状区移除，改由实时补全区展示（不重复）。

### 1.3 实时补全区（20 格，列表最前；笔记箱另见 §1.3.1）

| # | 中文 | 英文 | 来源 | 图标（thumbs/webp96） |
|---|---|---|---|---|
| 1 | 元素节点 | Element Node | 新增（`elementnode`） | `b3ac9fe58e22` |
| 2 | 野生河狸 | Wild Beaver | 新增（`beaver`） | `194a36a3086e`（用户指定，与河狸坝同图） |
| 3 | 轨道空投 | Orbital Supply Drop | 新增（`osd`） | `af53e0ecebc5` |
| 4-9 | **原始/普通/优秀/精良/史诗/传说** + 洞穴补给箱（品质前置） | White/Green/Blue/Purple/Yellow/Red Crate | 新增（`cavecrate`） | `33133525392b` / `5ff0e1ac69cb` / `bb7f8b7d7d2e` / `2851a9781f54` / `bc4aba61997f` / `e6887c39223f` |
| 10-15 | **原始/普通/优秀/精良/史诗/传说** + 补给箱（品质前置） | White/Green/Blue/Purple/Yellow/Red Beacon | 迁入（原静态「补给箱」1 格升级为 6 品质；`beacon`） | `3bdcad95af87` / `4869c2a521a2` / `e2f607b93446` / `bc28cb801b67` / `032f2e11efec` / `4576c3b020f3` |

> **品质口径（2026-09-30 定稿）**：六档**权威中英文** = 官中（ShooterGame.json/.po，`HordeCrate GetQualityInfo` 组 + TOF 废弃货箱实证）：**原始 Primitive / 普通 Ramshackle / 优秀 Apprentice / 精良 Journeyman / 史诗 Mastercraft / 传说 Ascendant**；**品质色统一源** = `dino-import.html` 的 `LB_BP_STAGE_COL`（注释已按官中修正）；显示 = **品质前置、去括号、不着色**。
| 16 | 野生巨型蜂巢 | Bee Hive | 迁入（`beehive`） | `0670c71beb56` |
| 17 | 河狸坝 | Beaver Dam | 迁入（`beaverdam` → `BeaverDam_C`） | `194a36a3086e` |
| 18 | 大型河狸坝 | Giant Beaver Dam | 迁入（`beaverdam` → `BP_BeaverDam_C`，规格差异） | `194a36a3086e`（暂无专用图，暂共用） |
| 19 | 河狸巢穴 | Beaver Lodge | 迁入（`beaverdam` → `SupplyCrateBaseBP_Instantaneous_DenLogs_Child2_C`） | `194a36a3086e`（暂无专用图，暂共用） |
| 20 | 埋藏藏宝箱 | Buried Treasure Cache | 迁入（`treasurecache`；全服实测 15） | `fac85e3d78f3` |

> **河狸坝三分的原因**（2026-09-30 查明）：`beaverdam` 类别用**子串匹配**（`BeaverDam` / `DamLogs` / `DenLogs`）收录，实测命中**三个不同实体类**——普通坝 / 大型坝（规格）/ 巢穴（lodge，`DenLogs` 系，非坝）；三者均为**野生自然生成**（无玩家版）。用户口径（2026-09-30）：**分 3 格展示**。

**不展示**：`obelisk` 方尖碑（用户用不到，2026-09-30 过滤）；`horde`（OSD 部落设施，用户不明其指——后端保留查询能力，前端不展示）；`weather`（本期不接）。

### 1.3.1 探险者笔记箱（19 格；v6「20 系列」经 v6.5 Gen2 拆分并入后为 19 格）

| # | 中文（官中） | 英文（wiki/游戏原文） | 类名后缀 | 图标 hash | 全服计数 |
|---|---|---|---|---|---|
| 21 | 图鉴 | Dossiers | `DinoDossiers` | `6e527e1b906f` | 260 |
| 22 | 罗克韦尔的笔记 | Rockwell Record | `Rockwell` | `2e849ec26929` | 89 |
| 23 | 美盈的笔记 | Mei Yin Note | `Li` | `55d486ce87f9` | 91 |
| 24 | 守望者 | The One Who Waits | `SheWhoWaits` | `5cf5a25b89a1` | 45 |
| 25 | 故障调查 | Glitch Discovery | `Glitch` | `ae4571ff6ac6` | 93 |
| 26 | 亲爱的简妮 | Dear Jane | `DearJane` | `6c501b025f62` | 7 |
| 27 | 涅尔瓦的笔记 | Nerva Note | `Leddica` | `136362c23a9d` | 30 |
| 28 | 达奇亚的笔记 | Dahkeya Note | `Dahkeya` | `096dccec1dd0` | 30 |
| 29 | 莱雅的石板 | Raia Tablet | `Raia` | `f6a6b29a21ca` | 31 |
| 30 | 鲍勃的故事 | Bob's Tall Tales | `BobsTallTales` | `d77406f9d2a0` | 30 |
| 31 | 鲍里斯的毕业日记 | Grad Journal Boris | `Boris` | `e850d3c1d1d3` | 5 |
| 32 | 戴安娜的日志 | Diana Log | `Dianna` | `e277182d55a6` | 50 |
| 33 | 伊玛目的毕业日记 | Grad Journal Imamu | `Dmika` | `e850d3c1d1d3` | 5 |
| 34 | 伊米莉亚的毕业日记 | Grad Journal Emilia | `Emilia` | `e850d3c1d1d3` | 5 |
| 35 | 罗斯提的毕业日记 | Grad Journal Rusty | `Rusty` | `e850d3c1d1d3` | 6 |
| 36 | 特伦特的毕业日记 | Grad Journal Trent | `Trent` | `e850d3c1d1d3` | 5 |
| 37 | 圣地亚哥的日志 | Santiago's Log | `Santiago` + `Santiago_Gen2Chronicles` | `b7ad7d99448f` | 39 |
| 38 | 达瑞斯档案 | Darius Archival Audio | `LostColony_Darius` | `fcc7bb9fb242` | 18 |
| 39 | 罗克韦尔档案 | Rockwell's Archives | `LostColony_Rockwell` | `0b1ce652f5a9` | 12 |

> **Genesis 2 Chronicles 按作者拆分（2026-09-30，v6.5，用户定稿）**：wiki 全表类型「Genesis 2 Chronicles」共 **25 条** = **HLN-A 20 条**（孤岛 5 / 焦土 5 / 畸变 4 / 灭绝 1 / 创世1 5，**均分布在已上线图，与 Gen2 未上线无关**）+ **Santiago 5 条**（畸变 #15 + 灭绝 #17-20）。**处理：该类型不设独立格，25 条全部拆开并入所属作者格**——**Santiago 5 条 → 并入「圣地亚哥的日志」（34+5=39）**；**HLN-A 20 条 → 并入「故障调查」（73+20=93）**。箱类 `Santiago_Gen2Chronicles_C` 实测 畸变 1 + 灭绝 4 = 5 箱，与 wiki 100% 吻合。

> **来源（2026-09-30 全服普查，v6.2 闭环）**：RCON 逐图实测——Isl 7 / Sco 7 / Abe 13 / Ext 8 / Los 2 / Gen 1（仅 Glitch）；Cen/Ast/Rag/Val 0；**全服并集 20 系列**（用户判断“远不止 7”正确）。与 wiki「Canonical notes by author」21 类作者**全员闭环**：**Leddica = Nerva**（30=30，用户判定）、**Dmika = Imamu**（5=5，用户确认）、**Skye 并入 Rusty 类第 6 箱**（总账 26=26 排除法）；**Nida / Gabriel 因 Genesis 2 尚未上线，暂无可查实例**（上线后由后端补录类名）；海莲娜 = Dossier 类、HLN-A = Glitch 类（均已收录）。
> **命名口径（v6.1，按 wiki 权威核验）**：**英文 = wiki「Explorer Notes/Locations」表格术语**——系列名用游戏原文（Type 分类：Dossier/Note/Record/Log/Tablet/Journal/Chronicles/Glitch Discovery…，如 Rockwell Record / Mei Yin Note / Dahkeya Note / Raia Tablet / Diana Log / Grad Journal X，**不带所有格 's**；唯 Santiago's Log 原文即带 's）；**中文 = 官中游戏文本**（海莲娜/美盈/达奇亚/莱雅/戴安娜/罗斯提/伊米莉亚/鲍里斯/特伦特/守望者/圣地亚哥/HLN-A/鲍勃/达瑞斯；「莱雅」非「拉亚」、「伊米莉亚」非「艾米莉亚」、「罗斯提」非「拉斯蒂」、「创世纪2」含“世”）；**图鉴 = Dossier（Type），图标 `HelenaNote_Icon`**（作者 Helena 的笔记图标）；图标=drops/GUI 现成 webp（18 格真实图标；达瑞斯档案暂无合意图，暂为空格）。

> **全服实测计数（2026-09-30，RCON `scan filter=ExplorerChest top=500`，10 图，合计 831）**：
> DinoDossiers 260 / Mei Yin Note 91 / Rockwell Record 89 / Glitch Discovery 73 / Diana Log 50 / The One Who Waits 45 / Santiago's Log 34 / Raia Tablet 31 / **Nerva Note（=Leddica 类）30** / Dahkeya Note 30 / Bob's Tall Tales 30 / Darius Archival Audio 18 / Rockwell's Archives(LC) 12 / Dear Jane 7 / Grad Journal Rusty 6 / Boris 5 / **Grad Journal Imamu** 5 / Emilia 5 / Trent 5 / **Santiago's Genesis 2 Chronicles** 5。
> **「1 箱 ≙ 1 条笔记」强规律**：Mei Yin 91=91 / Rockwell 89=89 / Diana Log 50=50 / Nerva(Leddica) 30=30 / Dahkeya 30=30 / Raia 31≈30 / **Dmika 5 = Imamu 毕业日记 5 条**（**用户 2026-09-30 确认 Dmika=Imamu** → 格名已转正「伊玛目的毕业日记 / Grad Journal Imamu」）。
> **Skye 真身（2026-09-30 定案）**：wiki 毕业生日志 ID 连续段 447-472 = Rusty 447-451 / Emilia 452-456 / Boris 457-461 / Trent 462-466 / Imamu 467-471 / **Skye 472**（共 26 条）；实测 Abe 毕业生箱 26 = Boris 5 + **Dmika(=Imamu) 5** + Emilia 5 + **Rusty 6** + Trent 5 —— **唯一多出的 1（Rusty 类的第 6 箱）⇔ Skye 的 1 条**（总账 26=26，其余 4 类精确 5=5，排除法唯一解）。z 值旁证：Rusty 类采样 4 箱中 1 箱 z=49461 显著高于其余（36955-40656）——Skye 笔记位于 The Overlook（眺望台，高台地形）。**结论：游戏把 Skye 的笔记归入 `ExplorerChest_Rusty_C` 蓝图（开发时复用/合并），世界查询层面无法单独拆出 Skye**。
> **Leddica 类 = Nerva**（用户判定 2026-09-30 + 计数 30=30 吻合）→ 格名已转正「涅尔瓦的笔记 / Nerva Note」（图标 `136362c23a9d`）。

### 1.3.2 21 作者 × 19 格对齐审计（2026-09-30 全量核验 v6.4；格数 v6.7 校正）

> 核验方法：wiki「Explorer Notes/Locations」全表（1106 行）Topic 原文逐类比对 + 跨作者 Type 分析 + 「Lost Colony / Darius Anthom」页面勘察 + RCON scan 计数交叉印证。

| # | wiki 作者 | 我方格（中文 / 英文） | 类名后缀 | 状态 |
|---|---|---|---|---|
| 1 | Helena Walker | 图鉴 / Dossiers | `DinoDossiers` | ✅（图标 HelenaNote，用户指定） |
| 2 | Gaius Marcellus Nerva | 涅尔瓦的笔记 / Nerva Note | `Leddica` | ✅（映射修正 30=30） |
| 3 | Sir Edmund Rockwell | 罗克韦尔的笔记 / Rockwell Record + 罗克韦尔档案 / Rockwell's Archives | `Rockwell` + `LostColony_Rockwell` | ✅（2 格） |
| 4 | Mei-Yin Li | 美盈的笔记 / Mei Yin Note | `Li` | ✅（wiki Topic="Mei Yin Note"） |
| 5 | John Dahkeya | 达奇亚的笔记 / Dahkeya Note | `Dahkeya` | ✅ |
| 6 | Raia | 莱雅的石板 / Raia Tablet | `Raia` | ✅ |
| 7 | Diana Altaras | 戴安娜的日志 / Diana Log | `Dianna` | ✅ |
| 8 | Rusty Stafford | 罗斯提的毕业日记 / Grad Journal Rusty | `Rusty` | ✅（含 Skye 第 6 箱） |
| 9 | Emilia Müller | 伊米莉亚的毕业日记 / Grad Journal Emilia | `Emilia` | ✅ |
| 10 | Boris | 鲍里斯的毕业日记 / Grad Journal Boris | `Boris` | ✅ |
| 11 | Trent | 特伦特的毕业日记 / Grad Journal Trent | `Trent` | ✅ |
| 12 | Imamu | 伊玛目的毕业日记 / Grad Journal Imamu | `Dmika` | ✅（映射修正 5=5） |
| 13 | Skye | —（并入 Rusty 类第 6 箱） | `Rusty` | ⚠️ 结构如此（总账 26=26 排除法） |
| 14/15 | ??? / The One Who Waits | 守望者 / The One Who Waits | `SheWhoWaits` | ✅ |
| 16 | Santiago | 圣地亚哥的日志 / Santiago's Log + 圣地亚哥的创世纪2编年史 / Santiago's Genesis 2 Chronicles | `Santiago` + `Santiago_Gen2Chronicles` | ✅（2 格，归属修正） |
| 17 | HLN-A | 故障调查 / Glitch Discovery | `Glitch` | ✅（Type 全属 HLN-A，无歧义） |
| 18 | Nida Akhtar | —（Genesis 2 未上线） | — | ⏳ 待上线 |
| 19 | Gabriel | —（Genesis 2 未上线） | — | ⏳ 待上线 |
| 20 | Bob | 亲爱的简妮 / Dear Jane + 鲍勃的故事 / Bob's Tall Tales | `DearJane` + `BobsTallTales` | ✅（2 格） |
| 21 | Darius Anthom | 达瑞斯档案 / Darius Archival Audio | `LostColony_Darius` | ✅ |

> **二级分类 × 数量精确对账（2026-09-30，v6.6 终审）**：wiki 全表交叉表（Type×Author）vs 我方格实测——**12 格 100% 精确吻合**：

| 我方格 | 我数字 | wiki 二级分类构成 |
|---|---|---|
| 罗克韦尔的笔记 | 89 | Record×Rockwell 89 |
| 美盈的笔记 | 91 | Note×Mei Yin 91 |
| **守望者** | **45** | **（空类型）×One Who Waits 30 + Note×??? 15** |
| 涅尔瓦的笔记 | 30 | Note×Nerva 30 |
| 达奇亚的笔记 | 30 | Note×Dahkeya 30 |
| 戴安娜的日志 | 50 | Log×Diana 50 |
| 鲍里斯/伊玛目/伊米莉亚/特伦特 | 各 5 | Journal×同名 5 |
| **罗斯提的毕业日记** | **6** | **Journal×Rusty 5 + Skye 1** |
| **圣地亚哥的日志** | **39** | **Log×Santiago 30 + Manual×Santiago 4 + Chronicles×Santiago 5**（Note×Santiago 30 = "Genesis: Part 2 notes"，Gen2 未上线未计入） |

> 近似两处：**图鉴 260**（箱子数）vs Dossier×Helena 143+N/A 7=150（条数，箱/条定义不同）；**莱雅 31** vs Tablet×Raia 30（全服多 1 箱）。**已定案（2026-09-30）**：HLN-A 的 Discovery 15 / Voice line 114 / Hologram 11 **不并入**（分属 HLN-A 名下其它组，非"故障调查"组；用户确认保持 93）；Bob（Dear Jane/Tales）与 Lost Colony 组不在 wiki 主表（无从核，以服务器实测为准）。

> **结论**：21 作者全部对齐（19 位有格 / Skye 并入 Rusty / Nida·Gabriel 待 Gen2 上线）；**跨作者 Type 检查**（Note 376/Log 80/Chronicles 25 为多作者共用）——我方格名均带作者标识，无第二处"归属不明"项。

### 1.4 图标规范（v5 新增，强制）

- 所有格子图标**一律使用 `thumbs/webp96/<hash>_w96.webp` webp 缩略图**（域名 `https://dino.whiterober.ccwu.cc/`）
- **禁止**直接引用 PNG 原图（`img.whiterober.ccwu.cc/ASA/...`）——用户在 2026-09-30 明确要求
- 映射源：`tmp/webp_map.json`（`{png_url: webp_rel_path}`，5101 条全量映射；新图标可随时从中查得对应 webp）

---

## 2. 现状盘点

### 2.1 前端「公共设施」块（v3933~v3982 建设，现状基线）

- **位置**：物品浮窗内 `#lbPubFacHead` + `#lbPubFacGrid`（构建于物品页构建函数内，`dino-import.html` L16201 区；渲染/折叠联动 L16906/L18086 区）
- **数据源**：存档设施数据 `f.isPublic===1` → `lbPubFacAdd(abbr, f)` 织入 `LB._pubFac`（L4450~4467 调用点；L17549+ 实现）
- **口径**：`lbIsPubFacKey()`（L17589+）= 前缀匹配 `LB_PUBFAC_PREFIX`（9 前缀）+ 后缀 `LB_PUBFAC_SUFFIX`（空）+ 排除 `_PlayerOwned`/quest/规则隐藏
- **展示**：`lbPubFacRender()`（L17648+）词典全量 + 实例并入（`_canon` 归并）→ 排序（`_ORD`）→ 格子渲染（`.lb-picker-grid` + `.lb-picker-item`）
- **局限（本次要解决的）**：无坐标、无实时性、无档位、无"当前世界是否存在"判断

### 2.2 后端 RCON 基础设施（`独立后端\dino_backend.py`，已就绪）

- RCON 链路：`rcon_command()` / `_rcon_str()`（v13 分包截断修复 / KeepAlive 免疫 / 控制字符剥离）；`PORTS` 表（Isl 32320 ~ Gen 32329）；`RCON_HOST=192.168.199.3`
- 路由模式：`do_GET`/`do_POST` 按 path 分支；POST JSON `{server, ...}` → RCON → 直接返回或写状态文件
- 现成先例：`/api/refresh_eggs`、`/api/volcano_state`（**3s TTL 单点缓存**——插件文档 §4 约束"多客户端不得直连狂查"）、`/api/volcano_log`、`/api/inv_probe`
- 命令常量区（L135~141）：`CMD_EGG_PROBE` / `CMD_VOLCANO` / `CMD_INV_PROBE` …（新增即加一行）

### 2.3 WorldProbe（插件 v9，摘要）

`TransferIdentityFix.WorldProbe <types|query|scan|weather>`；字典 **13 类**（2026-09-30 实测；含 `explorerchest`/`treasurecache`）；`query` 返回 `matched/returned/truncated/actors[{class,difficulty,hasLoc,x,y,z}]`；实测命令极快（types 0.04s / query 0.12s）；三大坑（按需加载 / (0,0,0) 幽灵坐标 / scan top≤500）。详见附件交接单。

---

## 3. 映射与展示

### 3.1 类别映射表（静态 ↔ 实时，v5 定稿）

| WorldProbe 类别 | 中文标签（前端用） | 现状静态口径 | 行动 |
|---|---|---|---|
| `beacon` | 补给箱（白/绿/蓝/紫/黄/红） | SupplyCrate（原 1 格） | **迁入实时**：1 格 → 6 格（六品质 Beacon 图） |
| `osd` | 轨道空投 | （无） | **新增实时** |
| `cavecrate` | 洞穴补给箱（六品质） | （无） | **新增实时**：6 格（六品质 Crate 图） |
| `horde` | OSD 部落设施 | （无） | **不补**（用户不明其指；后端保留） |
| `artifactcrate` | 神器箱 | ArtifactCrate | **过滤**（用户用不到，2026-09-30） |
| `elementnode` | 元素节点 | （无，勿与 PowerNode 混淆） | **新增实时**；PowerNode 电力节点仍静态 |
| `beehive` | 野生巨型蜂巢 | BeeHive | **迁入实时** |
| `obelisk` | 方尖碑 | （无） | **不展示**（用户用不到） |
| `beaverdam` | 河狸坝/大型河狸坝/河狸巢穴 | BeaverDam | **迁入实时**（3 实体分 3 格，见 §1.3） |
| `beaver` | 野生河狸 | （无） | **新增实时** |
| `treasurecache` | 埋藏藏宝箱 | TreasureCache（原静态 1 格） | **迁入实时**（v6.7；全服实测 15） |
| `weather` | 天气 | （无） | 本期仅后端路由预置，**UI 不接入** |

### 3.2 展示原则（v5 定稿）

- **单一网格不分段（用户口径 2026-09-30）**：全部 65 格同放**一个 `.lb-picker-grid`**——实时补全 39 格在前（20 设施 + 19 笔记箱，"排序上靠前"），现状 26 格接续；**无分隔线、无小标题**
- **现状排序铁律（2026-09-30 用户指正）**：现状 26 类**逐字照抄线上 DOM 真实顺序**（城市终端 → 废土城市终端 → 沙漠城市终端 → 雪地城市终端 → 电力节点 → 21 台座拼音序；神器箱已过滤移除，藏宝箱 v6.7 迁出）——**禁止任何重排**
- **样式完全一致**：全部条目**逐字复用**现状格子结构——`.lb-picker-grid`（`repeat(auto-fill,minmax(92px,1fr))`、gap 6px）+ `.lb-picker-item`（48px 图标 + 12px 中文名 + 10px sub 行 + 9px 英文名）
- **实时区标记**：格子右上角**低可视化刷新图标**（复用页面现有 MDI 填充款 path `M17.65,6.35…`；12px、`opacity≈0.42`、色 `#93c5fd`；**不新增图标资源**）
- **实时条目差异**：sub 行显示实时数量/档位（如 `L25 ×2`）；坐标进 tooltip（点击弹坐标明细为 P2 增强）
- **现状区零改动**：26 类数据源/排序/图标与改造前逐字一致（剔除迁出 4 类 + 神器箱）

### 3.3 预览页（P0.5 产物，已产出）

- 文件：`_preview_pubfac_worldprobe_v5.html`（项目根；v3/v4 为历史版本）
- 内容：**单一网格 65 格**（实时 39 置前 + 现状 26 接续，无分隔线；已过滤方尖碑/神器箱；20 设施 + 19 笔记箱格）；全部真实 webp 图标（64 张）；现状顺序 = 线上 DOM 真实顺序
- 验证（2026-09-30 藏宝箱迁入版）：`imgs=64 / items=65 / rt_marks=39 / png_refs=0 / blank_runs=0 / sec_head=0`；浏览器渲染通过

### 3.4 现状区 26 类图标 hash 清单（实施核对用）

| 中文 | hash |
|---|---|
| 台座（暗影/卫士/潜行/岩壁/深渊/混沌/增长/虚空/灭世） | `b80c1a4fc6b1` / `94108b07dbdc` / `32163c3f96cf` / `9d69abe4492f` / `0f9ae5c400e3` / `f8438ba452e3` / `cf84269cf198` / `4fe7bf786d91` / `dd24f56b7b1a` |
| 城市终端（普通/沙漠/雪地/废土） | `94034504c2aa`（四终端同图） |
| 电力节点 | `f2fbcfe49a07` |
| 台座（猎手/团结/稳重/狡诈/智慧/天主/吞噬/免疫/强壮/机敏/残暴/迷失） | `f75bb77610fb` / `253db1d46ec4` / `e9dbc815ca72` / `4e918644c2df` / `77e016b3bd48` / `e1241418a19c` / `357ee81fa216` / `b85513f3e742` / `248f17b58cb6` / `72e967cc65ad` / `5d0f179c751f` / `eaa95c23f415` |

---

## 4. 架构设计

### 4.1 后端（`独立后端\dino_backend.py`；改真身流程见 §7.3）

**新增常量**：

- `CMD_WORLDPROBE = 'TransferIdentityFix.WorldProbe'`

**新增 4 条路由**（全 POST JSON；通道路由透传插件 JSON、聚合路由按图分组）：

| 路由 | body | RCON 命令 | 缓存策略 |
|---|---|---|---|
| `/api/worldprobe_types` | `{server}` | `WorldProbe types` | 内存 TTL 600s（字典极稳定） |
| `/api/worldprobe_query` | `{server, type, limit}` | `WorldProbe query <type> limit=<N>` | 内存 TTL 5s，键 `server\|type\|limit`；同键并发合并（单点取数） |
| `/api/worldprobe_weather` | `{server}` | `WorldProbe weather` | 内存 TTL 10s（本期仅预置） |
| `/api/worldprobe_scan` | `{type, servers[], limit}` | 逐图并行 `query` | **聚合路由**：ThreadPool 并行（并发 ≤4）、单图子缓存 5s、聚合 TTL 10s；按图分组返回 |

> **实施状态（v6.8，2026-09-30）**：✅ 4 路由已实施并落真身（备份 `.bak_20260930_183458`、md5 校验一致、`py_compile` 通过）——**待服务器机重启生效**；「同键并发合并」实现 = **single-flight**（后到请求等锁 → 双检缓存 → 复用同一次 RCON 结果）。

**约束与实现要点**：

- `limit` 默认 **20**、上限 **100**（RCON 响应约 8KB 上限）；超限截断由插件 `truncated` 透传
- 超时 `timeout=8`（对齐 Volcano；单命令 1.1–1.3s，留裕量）
- 失败返回范式对齐现有：`{ok:false, server, error:'rcon: ...'}`
- **并发闸**：同 (server,type) 同时只发 1 条 RCON（其余请求挂在缓存 Promise 上）——对齐 Volcano"后端单点轮询"原则
- **聚合限流**：scan 路由并发 ≤4 张图（ThreadPool 上限），聚合响应预计 ≤100KB

### 4.2 前端（`dino-import.html`）

**改造点**（`lbPubFacRender()` 内）：

1. **实时补全 39 格置于最前**（同一网格内）：**20 设施格（新补/迁入，含 v6.7 藏宝箱）** + **19 探险者笔记箱格**；
2. **接续现状 26 格**：现 31 类中剔除 `BeeHive`/`BeaverDam`/`SupplyCrate`/`TreasureCache`（`_canon` 后键名匹配）、过滤神器箱，其余 **26 类**沿用线上实测真实渲染顺序（DOM 顺序）与渲染逻辑**逐字不动**（禁止重排）；
3. 实时格子的 sub 行接后端数据（数量/档位），未查询/无数据时可用静态占位（口径待 P1 联调定）；
4. 实时标记：右上角低可视刷新图标（§3.2）；
5. 查询交互（v3 保留）：**无块内服务器选择器**——一键遍历候选图清单（每类一份"有可能存在"的图列表，代码内常量表，P0 实测校准）；结果按图分组；类别 chips 11 类中文标签；查询中禁用防连点。

### 4.3 缓存与并发

- 前端：会话级 LRU `{type → {ts, data}}`（聚合结果），TTL 10s；切换类别命中缓存即秒显
- **刷新 CD（v6.8 用户约束）**：刷新/查询动作最短间隔 **10s**——冷却期内按钮禁用 + 倒计时显示，期间点击不发请求（防连点、防超发 RCON 的最终防线）
- 后端：§4.1 表格；聚合路由**并发 ≤4 图**、单图单点合并；(server,type) 子缓存 5s；**短时缓存共用（v6.8 用户约束）**：内存 TTL 缓存为全客户端共享（键 `server|type|limit`），同键并发请求合并为 1 次 RCON（single-flight）——多客户端/多标签页短时内只产生一次查询
- **性能红线**：前端防连点（查询中禁用）；**任何情况下不得连点批量 11 类**（全类遍历属 P4 评估项，且必须串行队列）

### 4.4 UI 线框（文字版）

```
「公共设施」块（v5：单一网格 · 不分段）
┌────┬────┬────┬────┐   （一个 .lb-picker-grid 多列网格，65 格连续排布）
│元素节点│野生河狸│轨道空投│   ← 前 20 格：实时补全（右上角低可视刷新标记）
│洞穴补给箱（白/绿/蓝/紫/黄/红）│  ← 6 格
│补给箱（白/绿/蓝/紫/黄/红）│      ← 6 格（Beacon 图）
│野生巨型蜂巢│河狸坝│大型河狸坝│河狸巢穴│埋藏藏宝箱│
│探险者笔记箱 ×19（图鉴/罗克韦尔/美盈/守望者/故障调查/简妮/涅尔瓦/达奇亚/莱雅/鲍勃/毕业日记×5/戴安娜/圣地亚哥/达瑞斯档案/罗克韦尔档案）│
│城市终端│废土│沙漠│雪地│电力节点│台座×21│   ← 接续 26 格：现状原样（真实顺序）
└────┴────┴────┴────┘
```

---

## 5. 坑适配清单（必读，来自附件 + 本项目经验）

| # | 坑 | 对策 |
|---|---|---|
| 1 | 「扫不到」≠「不存在」（按需加载） | UI 常驻提示条；多轮/多点采样属运维动作，前端不承诺"全图总数" |
| 2 | `hasLoc=1` 但坐标 (0,0,0) | 前端**必须过滤** + 尾部备注过滤计数 |
| 3 | `scan` top≤500 | 前端**不使用 scan**（仅 types+query）；运维用字母分片，方案留存 |
| 4 | RCON 8KB 响应上限 | `limit` 默认 20/上限 100；truncated 提示 |
| 5 | 每类查询 1.1–1.3s、RCON 挤占游戏主线程 | 后端 TTL + 单点并发合并；前端防连点；全查须串行队列 |
| 6 | Abe 天气 `weatherState=null` | 不解析 `fields` 原始列表；按"无数据"展示（本期 UI 不接天气） |
| 7 | 图标误用 PNG 直链（大图） | **一律 webp 缩略图**（§1.4；`tmp/webp_map.json` 查映射） |

---

## 6. 分阶段实施

### P0 · 联通性预检（✅ 完成 2026-09-30）

- [✓] RCON 直连实测 `WorldProbe types`：`ok:true`；**字典实为 13 类**（交接单 11 类之外多出 `explorerchest`、`treasurecache` 两类的权威定义，正为本改造所需）
- [✓] 抽测 `query beaverdam`（Isl）：0.12s 返回、JSON 可解析（matched=0 属世界加载状态偏差，符合 P0 预期）
- **候选图清单校准**：按实测修正每类"有可能存在"的图列表（默认全 11 服保守起步；河狸窝参照附件实测 = Ast/Rag/Val/Ext/Isl）
- **验收**：连续两条命令均 1.1–1.3s 返回且 JSON 可解析

### P0.5 · 本地独立预览页（已完成，2026-09-30）

- 产出 `_preview_pubfac_worldprobe_v5.html`：18 格实时区（真实 webp 图标、低可视标记）+ 28 格现状区（原样）
- **验收**：本地渲染通过（46 张 webp 全载、无 PNG 引用、无空行违规）；用户认可后进 P1

### P1 · 后端路由 + 前端最小可用（2~3h）｜🔄 进行中（2026-09-30 启动）

- [✓] 后端：`CMD_WORLDPROBE` + **4 路由**（types/query/weather/scan）+ TTL 缓存共用 + 同键并发合并；`py_compile` ✅；已覆盖真身（备份 `.bak_20260930_183458`、md5 一致）——**待服务器机重启生效**
- [ ] 前端：块内「实时补全区」（39 格置前 + **刷新 CD 10s** + 后端对接；候选图遍历（聚合路由） + 样式对齐 + 低可视刷新标记）
- **验收**：指定服 `query beacon` 返回列表带坐标；连续点击不超发 RCON（后端日志单次）

### P2 · 整合（2~3h）

- 类别 chips 全套；档位/形态标签；复制坐标；truncated/过滤统计；**现状区剔除 3 类迁出项**（蜂巢/河狸坝/补给箱）后复测建筑栏无回归
- **验收**：现状区 = 28 类（与改造前该 28 类逐字一致）；实时区 18 格逐类可查，条目为**同款格子**

### P3 · 打磨（1~2h）

- 缓存命中优化、错误态文案、移动端布局（≤768px 行内换行）
- **验收**：清 SW+缓存后全流程复测；文档同步（本计划勾选完成项）

### P4 · 预留（不在本期）

- 天气卡（weather → 底部功能条）；beacon 等级颜色映射表；地图打点（需先确认 `报告\*_coord_calib.json` 坐标体系的复用性）

---

## 7. 验证与部署

### 7.1 后端验证

- 路由存在性判定（铁律）：`POST https://data.whiterober.ccwu.cc/api/worldprobe_types` 不带鉴权 ⇒ **401 login required = 路由存在**；404 = 未重载
- 功能抽查：`types.typeCount==11`；`query` 的 `actors[].class` 与游戏内实物对照（抽 1~2 个点）

### 7.2 前端验证

- 清 SW + caches 后 `?t=` 强刷；现状区对照改造前截图/条目清单（28 类逐字一致）；实时区逐类抽查（含 (0,0,0) 过滤场景）

### 7.3 部署流程

- 前端：`python tmp\_deploy_cf.py`（版本递增 vXXXX；打包→wrangler→线上校验）
- 后端：备份真身（`\\SERVER\dino_backend\` 同目录 `.bak_时间戳` + 工作区 `bak/`）→ 工作区镜像覆盖真身 → 校验关键字 + `py_compile` → 在 **服务器机**执行 `restart_dino_backend.bat` → 用户确认重启

### 7.4 回滚

- 前端：CF 控制台回退上一 Version ID（或重新部署旧 `dino-import.html`）
- 后端：用 `.bak_` 快照还原 + 重启

---

## 8. 风险登记

| 风险 | 等级 | 缓解 |
|---|---|---|
| RCON 高频查询挤占游戏主线程 | 中 | TTL 缓存 + 单点合并 + 前端防连点（§4.3） |
| 大响应截断（>8KB） | 低 | limit 上限 + truncated 明示 |
| 现状区被误改（迁出 3 类时误伤其他） | 中 | 迁出仅按 `_canon` 键名精确匹配 3 类；改造前/后条目清单对照验证 |
| 图标引用 PNG 直链回归 | 低 | §1.4 强制 webp；验收脚本统计 `png_refs=0` |
| 后端重启窗口内查询失败 | 低 | 错误态文案；重启用户确认后复测 |

---

## 9. 开放问题（待用户定夺）

1. 实时格子 sub 行的口径：未查询时显示什么（静态占位数量？"待查询"？空？）
2. ~~神器箱（ArtifactCrate）是否也迁入实时区~~（已按用户口径过滤，2026-09-30 关闭）
3. ~~`limit` 默认值（建议 20）与上限（建议 100）~~（✅ v6.8 定稿：默认 20 / 上限 100，已实施）
4. 每类候选图清单的最终版（P0 实测后敲定；默认全 11 服保守起步）
5. 是否需要"全查"按钮（全部类别逐一遍历候选图；默认不做，P4 再议）
