# item_zh.json 待裁决清单（极详版）

> 数据源：`汉化/item_zh.review.txt`（200 条未采纳）+ `汉化/item_zh.json`（248 条已采纳）+ `汉化/item_kind_all.json`（448 条类别映射）。
> 生成脚本：`tmp/_gen_item_review_md.py`（只读）。本文件仅用于人工校对，不参与构建。

## 📖 阅读指南

| 列 | 含义 |
|----|------|
| **#** | 与 `item_zh.review.txt` 行序一致的全局编号 |
| **base** | 类名基名（去 `PrimalItem*` 前缀、`_C` 后缀后的值） |
| **类别** | 后端 v4 权威细分 `kind`（10 值，来自 `item_kind_all.json`） |
| **icon** | 从 `icons2.json` 按 `基名_Icon` 反查到的图标键；`—` = 缺失 |
| **en 候选** | 三级匹配推得的英文名（含 camel 拆词，带「英文仅拆词」标记的为**推断值**） |
| **zh 候选** | 匹配到的中文候选；`—` = 未匹配到 |
| **问题** | 被排除的原因（多词拼接 / 冒号串行 / 鞍类错配 / 无图标键 / 无中文 / 英文仅拆词） |
| **建议** | 我给出的可直接采用的译名；「待你定名」= 我无法确认 |
| **置信** | 高 = 官方译名可查证；中 = 常见社区译名；低 = 推断值需复核 |

> **建议动作代码**：✅ 直接补录 / 🟡 需你定名 / 🔵 暂缓（保持英文回退）/ ⛔ 建议丢弃

## 📊 全局统计

| 分类 | 条数 | 说明 |
|------|:---:|------|
| 🅰 缺中文候选（无图标键） | 99 | 中文 + 英文都需补，成本最高 |
| 🅱 缺中文候选（图标已有） | 1 | 有图标，补中文即可 |
| 🅲 中文候选不可用 | 50 | 有候选但被过滤（多义/串行/错配），需重取中文 |
| 🅳 英文待核（中文可用） | 0 | 中文已正确，仅英文是推断值 |
| 🅴 整族低优先 | 50 | ApexDrop / LostColony / 载具 / 生成器 |
| **合计** | **200** | |

已给出建议译名：**高置信 111 条**、中置信 39 条、低置信 35 条，其余 15 条待你定名。

覆盖率预测（分母 448 个基名）：

| 阶段 | 表内条数 | 覆盖率 |
|------|:-------:|:------:|
| 当前（仅自动匹配） | 248 | 55.4% |
| + 高置信建议 | 359 | 80.1% |
| + 全部建议（含低置信） | 433 | 96.7% |

### 物品类别分布（后端 kind，10 类）

| 类别 | 已采纳 | 全部基名 |
|---|:---:|:---:|
| resource（资源/材料） | 72 | 137 |
| ammo（弹药/投掷物） | 20 | 30 |
| structure（建筑构件） | 23 | 31 |
| consumable（消耗品） | 3 | 7 |
| saddle（鞍具） | 36 | 106 |
| armor（服饰/护甲） | 61 | 79 |
| weapon（工具/武器） | 27 | 44 |
| attachment（武器配件） | 0 | 0 |
| tek（泰克装备） | 2 | 3 |
| other（其他/未归类） | 4 | 11 |
| **合计** | **248** | **448** |

---

## 🅰 A 类｜完全没有中文候选（100 条）

> 这类是「`icon_zh_map` / PO / ShooterGame.json」三级链都没命中。

### A1｜缺中文 + 缺图标（已给建议，85 条）

> 建议值可直接补录进 `item_zh.json`；图标键留空，前端按 de-dup 用通用类图标。

| # | 基名 | 类别 | icon | en 候选 | zh 候选 | 问题 | 建议 | 置信 |
|---|------|------|:----:|---------|---------|------|------|:---:|
| 2 | `AggroTranqDart` | ammo（弹药/投掷物） | - | Aggro | - | 无图标键;无中文 | 仇恨麻醉镖<br>需确认是否模组内容 | 低 |
| 37 | `ArcticBoots` | armor（服饰/护甲） | - | Arctic Boots | - | 无图标键;无中文 | 北极靴<br>Arctic 系列套装 | 中 |
| 38 | `ArcticHelmet` | armor（服饰/护甲） | - | Arctic Helmet | - | 无图标键;无中文 | 北极头盔 | 中 |
| 39 | `Armor_Archelon_Saddle_ASA` | other（其他/未归类） | - | Armor_Archelon_Saddle_ASA | - | 无图标键;无中文;英文仅拆词 | 古巨龟鞍<br>PO依据：古巨龟（Archelon） | 中 |
| 40 | `ArrowFlame` | ammo（弹药/投掷物） | - | Arrow Flame | - | 无图标键;无中文;英文仅拆词 | 火焰箭 | 高 |
| 41 | `ArrowTranq` | ammo（弹药/投掷物） | - | Arrow Tranq | - | 无图标键;无中文;英文仅拆词 | 麻醉箭 | 高 |
| 42 | `ArthroSaddle` | saddle（鞍具） | - | Arthro | - | 无图标键;无中文 | 节胸马陆鞍 | 高 |
| 43 | `AxolotlSaddle` | saddle（鞍具） | - | Axolotl Saddle | - | 无图标键;无中文;英文仅拆词 | 钝口螈鞍<br>新生物，需核对官方译名 | 低 |
| 45 | `BeaverSaddle` | saddle（鞍具） | - | Beaver | - | 无图标键;无中文 | 巨河狸鞍 | 高 |
| 46 | `Beer` | resource（资源/材料） | - | Beer | - | 无图标键;无中文 | 啤酒 | 高 |
| 47 | `BlueSap` | resource（资源/材料） | - | Blue | - | 无图标键;无中文 | 蓝色树液 | 中 |
| 56 | `ChainSaw_Cursed` | other（其他/未归类） | - | Chain | - | 无图标键;无中文 | 被诅咒的电锯 | 高 |
| 57 | `ChalicoSaddle` | saddle（鞍具） | - | Chalico | - | 无图标键;无中文 | 爪兽鞍 | 高 |
| 62 | `ClimbPick` | weapon（工具/武器） | - | Climb Pick | - | 无图标键;无中文;英文仅拆词 | 攀爬镐 | 高 |
| 63 | `CorruptedPolymer` | resource（资源/材料） | - | Corrupted Polymer | - | 无图标键;无中文;英文仅拆词 | 腐化聚合物 | 高 |
| 65 | `Crossbow_Fab` | weapon（工具/武器） | - | Crossbow_Fab | - | 无图标键;无中文;英文仅拆词 | 制式十字弩<br>Fab = Fabricated 制式 | 高 |
| 69 | `DinoCompanionSaddle_Doggo` | saddle（鞍具） | - | Dino | - | 无图标键;无中文 | 恐龙伙伴鞍（犬） | 中 |
| 70 | `DinoCompanion_Gear_AmmoBox` | armor（服饰/护甲） | - | Dino | - | 无图标键;无中文 | 恐龙伙伴·弹药箱 | 中 |
| 71 | `DinoCompanion_Gear_Medkit` | armor（服饰/护甲） | - | Dino | - | 无图标键;无中文 | 恐龙伙伴·医疗包 | 中 |
| 73 | `DoedSaddle` | saddle（鞍具） | - | Doed | - | 无图标键;无中文 | 星尾兽鞍 | 高 |
| 76 | `FasolaSaddle` | saddle（鞍具） | - | Fasola Saddle | - | 无图标键;无中文;英文仅拆词 | 法索拉鳄鞍<br>PO：Fasolasuchus Saddle → 法索拉鳄鞍 | 高 |
| 77 | `FracturedGem` | resource（资源/材料） | - | Fractured Gem | - | 无图标键;无中文;英文仅拆词 | 破碎宝石 | 高 |
| 79 | `Gasoline_Super` | resource（资源/材料） | - | Gasoline_Super | - | 无图标键;无中文;英文仅拆词 | 高级汽油 | 高 |
| 80 | `Gem_BioLum` | resource（资源/材料） | - | Gem_Bio Lum | - | 无图标键;无中文;英文仅拆词 | 生物荧光宝石 | 中 |
| 81 | `Gem_Element` | resource（资源/材料） | - | Gem_Element | - | 无图标键;无中文;英文仅拆词 | 元素宝石 | 中 |
| 82 | `Gem_Fertile` | resource（资源/材料） | - | Gem_Fertile | - | 无图标键;无中文;英文仅拆词 | 肥沃宝石 | 中 |
| 88 | `GigantSaddle` | saddle（鞍具） | - | Gigant | - | 无图标键;无中文 | 巨猿鞍<br>Gigantopithecus | 中 |
| 89 | `Glider` | armor（服饰/护甲） | - | Glider | - | 无图标键;无中文;英文仅拆词 | 滑翔翼 | 高 |
| 90 | `Grapeshot_ToF` | ammo（弹药/投掷物） | - | Grapeshot_To F | - | 无图标键;无中文;英文仅拆词 | 葡萄弹<br>ToF 待确认出处 | 中 |
| 92 | `Gun` | weapon（工具/武器） | - | Gun | - | 无图标键;无中文 | 枪<br>过于泛化，建议不收录或指定具体枪械 | 低 |
| 93 | `Harpoon` | weapon（工具/武器） | - | Harpoon | - | 无图标键;无中文;英文仅拆词 | 鱼叉 | 高 |
| 94 | `Harpoon_Cursed` | weapon（工具/武器） | - | Harpoon_Cursed | - | 无图标键;无中文;英文仅拆词 | 被诅咒的鱼叉 | 高 |
| 96 | `HexCoins` | resource（资源/材料） | - | Hex Coins | - | 无图标键;无中文;英文仅拆词 | 六角币 | 高 |
| 97 | `Horn` | resource（资源/材料） | - | Horn | - | 无图标键;无中文 | 兽角<br>过于泛化，建议核对具体来源 | 中 |
| 99 | `IceBox` | structure（建筑构件） | - | Ice | - | 无图标键;无中文 | 冰箱<br>与设施表同名同义 | 高 |
| 102 | `KeratinSpike` | resource（资源/材料） | - | KeratinSpike | - | 无图标键;无中文 | 角质尖刺 | 高 |
| 117 | `MachinedSniper` | weapon（工具/武器） | - | Machined Sniper | - | 无图标键;无中文;英文仅拆词 | 制式狙击步枪 | 高 |
| 118 | `MachinedSniper_Cursed` | weapon（工具/武器） | - | Machined Sniper_Cursed | - | 无图标键;无中文;英文仅拆词 | 被诅咒的制式狙击步枪 | 高 |
| 128 | `MinersHelmet` | armor（服饰/护甲） | - | Miners Helmet | - | 无图标键;无中文;英文仅拆词 | 矿工头盔 | 高 |
| 130 | `MosaSaddle` | saddle（鞍具） | - | Mosa | - | 无图标键;无中文 | 沧龙鞍 | 高 |
| 131 | `MosaSaddle_Platform` | saddle（鞍具） | - | Mosa | - | 无图标键;无中文 | 沧龙平台鞍 | 高 |
| 133 | `OneShotRifle` | weapon（工具/武器） | - | One Shot Rifle | - | 无图标键;无中文;英文仅拆词 | 单发步枪 | 高 |
| 134 | `OwlSaddle` | saddle（鞍具） | - | Owl Saddle | - | 无图标键;无中文;英文仅拆词 | 雪鸮鞍 | 高 |
| 135 | `PachyrhinoSaddle` | saddle（鞍具） | - | Pachyrhino | - | 无图标键;无中文 | 厚鼻龙鞍 | 高 |
| 136 | `ParaSaddle` | saddle（鞍具） | - | Para | - | 无图标键;无中文 | 副栉龙鞍 | 高 |
| 137 | `ParacerSaddle_Platform` | saddle（鞍具） | - | Paracer | - | 无图标键;无中文 | 巨犀平台鞍 | 高 |
| 138 | `PelaSaddle` | saddle（鞍具） | - | Pela | - | 无图标键;无中文 | 拟鹈鹕鞍<br>Pelagornis | 中 |
| 139 | `Pike_Cursed` | weapon（工具/武器） | - | Pike_Cursed | - | 无图标键;无中文;英文仅拆词 | 被诅咒的长矛 | 高 |
| 140 | `PlesiSaddle_Platform` | saddle（鞍具） | - | Plesi | - | 无图标键;无中文 | 蛇颈龙平台鞍 | 高 |
| 141 | `PlesiaSaddle` | saddle（鞍具） | - | Plesia Saddle | - | 无图标键;无中文;英文仅拆词 | 蛇颈龙鞍 | 高 |
| 143 | `Polymer_Organic` | resource（资源/材料） | - | Polymer_Organic | - | 无图标键;无中文;英文仅拆词 | 有机聚合物 | 高 |
| 144 | `PrimalItemC4Ammo` | ammo（弹药/投掷物） | - | Primal Item C4 Ammo | - | 无图标键;无中文;英文仅拆词 | C4 炸弹 | 高 |
| 145 | `PrimalItemConsumableMiracleGro` | consumable（消耗品） | - | Primal Item Consumable Miracle Gro | - | 无图标键;无中文;英文仅拆词 | 神奇肥料 | 高 |
| 146 | `PrimalItemConsumableSoap` | consumable（消耗品） | - | Primal Item Consumable Soap | - | 无图标键;无中文;英文仅拆词 | 肥皂 | 高 |
| 147 | `Prod` | weapon（工具/武器） | - | Prod | - | 无图标键;无中文;英文仅拆词 | 电击棒 | 高 |
| 148 | `PteroSaddle` | saddle（鞍具） | - | Ptero | - | 无图标键;无中文 | 无齿翼龙鞍 | 高 |
| 149 | `QuetzSaddle_Platform` | saddle（鞍具） | - | Quetz | - | 无图标键;无中文 | 风神翼龙平台鞍 | 高 |
| 150 | `RadioactiveLanternCharge` | weapon（工具/武器） | - | Radioactive Lantern Charge | - | 无图标键;无中文;英文仅拆词 | 放射性提灯电池 | 高 |
| 151 | `Ramp_Metal` | structure（建筑构件） | - | Ramp_Metal | - | 无图标键;无中文;英文仅拆词 | 金属斜坡 | 高 |
| 153 | `RedSap` | resource（资源/材料） | - | Red | - | 无图标键;无中文 | 红色树液 | 中 |
| 156 | `RhinoSaddle` | saddle（鞍具） | - | Rhino | - | 无图标键;无中文 | 披毛犀鞍 | 高 |
| 157 | `RhynioSaddle` | saddle（鞍具） | - | Rhynio Saddle | - | 无图标键;无中文;英文仅拆词 | 莱尼虫鞍<br>Rhyniognatha | 中 |
| 159 | `Rocket` | ammo（弹药/投掷物） | - | Rocket | - | 无图标键;无中文 | 火箭弹 | 高 |
| 160 | `SaberSaddle` | saddle（鞍具） | - | Saber | - | 无图标键;无中文 | 剑齿虎鞍 | 高 |
| 164 | `Seed_DefensePlant` | consumable（消耗品） | - | Seed_Defense Plant | - | 无图标键;无中文;英文仅拆词 | 防御植物种子 | 高 |
| 165 | `Seed_PlantSpeciesY` | consumable（消耗品） | - | Seed_Plant Species Y | - | 无图标键;无中文;英文仅拆词 | Y 类植物种子 | 高 |
| 167 | `Sickle` | weapon（工具/武器） | - | Sickle | - | 无图标键;无中文;英文仅拆词 | 镰刀 | 高 |
| 168 | `SimpleRifleBullet` | ammo（弹药/投掷物） | - | Simple Rifle Bullet | - | 无图标键;无中文;英文仅拆词 | 简易步枪子弹 | 高 |
| 169 | `SimpleShotgunBullet` | ammo（弹药/投掷物） | - | Simple Shotgun Bullet | - | 无图标键;无中文;英文仅拆词 | 简易霰弹枪子弹 | 高 |
| 170 | `SnailPaste` | resource（资源/材料） | - | Snail | - | 无图标键;无中文 | 蜗牛膏 | 中 |
| 175 | `Spear_Explosive` | weapon（工具/武器） | - | Spear_Explosive | - | 无图标键;无中文;英文仅拆词 | 爆炸长矛 | 高 |
| 186 | `ThylacoSaddle` | saddle（鞍具） | - | Thylaco Saddle | - | 无图标键;无中文;英文仅拆词 | 袋狮鞍<br>zhmap：thylacoleo = 袋狮 | 高 |
| 187 | `ToadSaddle` | saddle（鞍具） | - | Toad | - | 无图标键;无中文 | 巨型蟾蜍鞍 | 高 |
| 188 | `TransparentRiotShield` | armor（服饰/护甲） | - | Transparent Riot Shield | - | 无图标键;无中文;英文仅拆词 | 透明防暴盾牌 | 高 |
| 189 | `TriCeiling_Metal` | structure（建筑构件） | - | Tri Ceiling_Metal | - | 无图标键;无中文;英文仅拆词 | 金属三角天花板 | 高 |
| 190 | `TriCeiling_Thatch` | structure（建筑构件） | - | Tri Ceiling_Thatch | - | 无图标键;无中文;英文仅拆词 | 茅草三角天花板 | 高 |
| 191 | `TriRoof_Metal` | structure（建筑构件） | - | Tri Roof_Metal | - | 无图标键;无中文;英文仅拆词 | 金属三角屋顶 | 高 |
| 192 | `TripwireC4` | weapon（工具/武器） | - | Tripwire C4 | - | 无图标键;无中文;英文仅拆词 | 绊线 C4 | 高 |
| 194 | `UmbraScale` | resource（资源/材料） | - | Umbra Scale | - | 无图标键;无中文 | 暗影鳞片 | 中 |
| 195 | `ValMegaraptorSaddle` | saddle（鞍具） | - | Val Megaraptor Saddle | - | 无图标键;无中文;英文仅拆词 | 瓦尔盖罗巨盗龙鞍 | 中 |
| 196 | `WeapFlamethrower` | other（其他/未归类） | - | Weap Flamethrower | - | 无图标键;无中文;英文仅拆词 | 火焰喷射器 | 高 |
| 197 | `XenomorphPheromoneGland` | resource（资源/材料） | - | Xenomorph | - | 无图标键;无中文 | 异形信息素腺 | 中 |
| 198 | `XiphSaddle_ASA` | saddle（鞍具） | - | Xiph Saddle_ASA | - | 无图标键;无中文;英文仅拆词 | 剑射鱼鞍<br>Xiphactinus | 中 |
| 199 | `YutySaddle` | saddle（鞍具） | - | Yuty Saddle | - | 无图标键;无中文;英文仅拆词 | 羽暴龙鞍 | 高 |
| 200 | `Zipline` | ammo（弹药/投掷物） | - | Zipline | - | 无图标键;无中文;英文仅拆词 | 滑索 | 高 |


### A2｜缺中文 + 缺图标（待你定名，14 条）

> 我无法确认官方译名，需你给出中文（多为新生物 / 模组内容）。

| # | 基名 | 类别 | icon | en 候选 | zh 候选 | 问题 | 建议 | 置信 |
|---|------|------|:----:|---------|---------|------|------|:---:|
| 4 | `AngelFoxSaddle` | saddle（鞍具） | - | Angel Fox Saddle | - | 无图标键;无中文;英文仅拆词 | 待你定名 | 待定 |
| 58 | `Charcoal_ShoulderDragonCraftable` | resource（资源/材料） | - | Charcoal_Shoulder Dragon Craftable | - | 无图标键;无中文;英文仅拆词 | 待你定名 | — |
| 59 | `CherufeSaddle` | saddle（鞍具） | - | Cherufe Saddle | - | 无图标键;无中文;英文仅拆词 | 待你定名 | 待定 |
| 66 | `Deinosuchus_Saddle_ASA` | saddle（鞍具） | - | Deinosuchus_Saddle_ASA | - | 无图标键;无中文;英文仅拆词 | 待你定名 | — |
| 68 | `DevilFoxSaddle` | saddle（鞍具） | - | Devil Fox Saddle | - | 无图标键;无中文;英文仅拆词 | 待你定名 | 待定 |
| 75 | `DreadSaddle_Platform` | saddle（鞍具） | - | Dread Saddle_Platform | - | 无图标键;无中文;英文仅拆词 | 待你定名 | — |
| 100 | `IceJumperSaddle` | saddle（鞍具） | - | Ice Jumper | - | 无图标键;无中文 | 待你定名 | 待定 |
| 119 | `MaelizardSaddle` | saddle（鞍具） | - | Maelizard Saddle | - | 无图标键;无中文;英文仅拆词 | 待你定名 | 待定 |
| 161 | `SauroSaddle` | saddle（鞍具） | - | Sauro Saddle | - | 无图标键;无中文;英文仅拆词 | 待你定名 | — |
| 162 | `SauroSaddle_Platform` | saddle（鞍具） | - | Sauro Saddle_Platform | - | 无图标键;无中文;英文仅拆词 | 待你定名 | — |
| 166 | `ShastaSaddle_Submarine` | saddle（鞍具） | - | Shasta | - | 无图标键;无中文 | 待你定名 | 待定 |
| 171 | `SnowDragonSaddle` | saddle（鞍具） | - | Snow | - | 无图标键;无中文 | 待你定名 | 待定 |
| 172 | `SnowMonsterSaddle` | saddle（鞍具） | - | Snow | - | 无图标键;无中文 | 待你定名 | 待定 |
| 177 | `SpindlesSaddle` | saddle（鞍具） | - | Spindles Saddle | - | 无图标键;无中文;英文仅拆词 | 待你定名 | 待定 |


### A3｜缺中文，但图标键已有（已给建议，1 条）

> 只缺中文，补一行即可，成本最低。

| # | 基名 | 类别 | icon | en 候选 | zh 候选 | 问题 | 建议 | 置信 |
|---|------|------|:----:|---------|---------|------|------|:---:|
| 1 | `ARKBone` | resource（资源/材料） | ARKBone_Icon | ARKBone | - | 无中文;英文仅拆词 | ARK 骨架 | 低 |


---

## 🅱 B 类｜有中文候选但不可用（50 条）

> 这些项**真的匹配到了中文**，但匹配过程串行了（多义聚合），必须手工重取。

### B1｜鞍类错配（中文是物种名而非「XX 鞍」，17 条）

> 成因：`_Icon` 反查命中了**物种**图标而非鞍图标。建议值已补正。

| # | 基名 | 类别 | icon | en 候选 | zh 候选 | 问题 | 建议 | 置信 |
|---|------|------|:----:|---------|---------|------|------|:---:|
| 3 | `AlloSaddle` | saddle（鞍具） | AlloSaddle | Allo | X-异特龙 | 鞍类错配 | 异特龙鞍 | 高 |
| 44 | `BasiloSaddle` | saddle（鞍具） | - | Basilo | 龙王鲸 | 鞍类错配 | 龙王鲸鞍 | 高 |
| 50 | `CamelsaurusSaddle` | saddle（鞍具） | CamelsaurusSaddle_Icon | Camelsaurus | 驼峰龙 | 鞍类错配 | 驼峰龙鞍 | 高 |
| 55 | `CeratosaurusSaddle_ASA` | saddle（鞍具） | - | Ceratosaurus | 角鼻龙 | 鞍类错配 | 角鼻龙鞍 | 高 |
| 67 | `DeinotheriumSaddle_ASA` | saddle（鞍具） | - | Deinotherium | 恐象 | 鞍类错配 | 恐象鞍 | 高 |
| 78 | `GasBagsSaddle` | saddle（鞍具） | - | Gas | 瓦斯 | 鞍类错配 | 气囊虫鞍<br>PO：Gasbags Saddle → 气囊虫鞍（原推断瓦斯袋鞍作废） | 高 |
| 87 | `GiantTurtleSaddle` | saddle（鞍具） | - | Giant Turtle | 巨型乌龟 | 鞍类错配 | 碳龟鞍<br>需与原版 Carbonemys 名统一 | 中 |
| 98 | `HyaenodonSaddle` | saddle（鞍具） | - | Hyaenodon | 鬣齿兽 | 鞍类错配 | 鬣齿兽鞍 | 高 |
| 101 | `JackalopeSaddle` | saddle（鞍具） | - | Jackalope | 鹿角兔 | 鞍类错配 | 鹿角兔鞍 | 中 |
| 121 | `MegalodonSaddle_Tek` | saddle（鞍具） | - | Megalodon | 巨齿鲨 | 鞍类错配 | 巨齿鲨泰克鞍 | 高 |
| 129 | `MoleRatSaddle` | saddle（鞍具） | MoleRatSaddle_Icon | Mole Rat Saddle | 评价 | 鞍类错配 | 鼹鼠鞍 | 中 |
| 155 | `RexSaddle_Tek` | saddle（鞍具） | - | Rex | 霸王龙 | 鞍类错配 | 霸王龙泰克鞍 | 高 |
| 158 | `RockDrakeSaddle_Tek` | saddle（鞍具） | - | Rock Drake | 岩龙 | 鞍类错配 | 岩龙泰克鞍 | 高 |
| 179 | `SpinoSaddle` | saddle（鞍具） | SpinoSaddle | Spino Saddle | 棘龙 | 鞍类错配 | 棘龙鞍 | 高 |
| 180 | `StagSaddle` | saddle（鞍具） | StagSaddle | Stag | 二阶段 | 鞍类错配 | 大角鹿鞍 | 中 |
| 181 | `TapejaraSaddle` | saddle（鞍具） | TapejaraSaddle | Tapejara Saddle | VR 古神翼龙 | 多词拼接; 鞍类错配 | 古神翼龙鞍 | 高 |
| 183 | `TerrorBirdSaddle` | saddle（鞍具） | TerrorBirdSaddle | Terror Bird Saddle | VR 骇鸟 | 多词拼接; 鞍类错配 | 骇鸟鞍 | 高 |


### B2｜多词拼接 / 冒号串行 / 感叹句（33 条）

> 成因：同一数字 ID 下聚合了多个词条（如温度提示、成就文本），或图标名对应多个物品。

| # | 基名 | 类别 | icon | en 候选 | zh 候选 | 问题 | 建议 | 置信 |
|---|------|------|:----:|---------|---------|------|------|:---:|
| 48 | `Bow` | weapon（工具/武器） | Bow_Icon | Bow | 复合弓 泰克弓 弓 | 多词拼接 | 弓<br>原污染值「复合弓 泰克弓 弓」 | 高 |
| 49 | `CakeSlice` | resource（资源/材料） | CakeSlice_Icon | Cake Slice | 方舟周年庆惊喜蛋糕 白色湿地 能量 | 多词拼接 | 蛋糕块 | 中 |
| 53 | `CarnoSaddle` | saddle（鞍具） | CarnoSaddle | Carno Saddle | 温度: 披毛犀鞍 短面袋鼠鞍 | 冒号串行; 多词拼接 | 食肉牛龙鞍 | 高 |
| 54 | `CavewolfSaddle` | saddle（鞍具） | CaveWolfSaddle_Icon | Cavewolf | 温度: 披毛犀鞍 刺面龙鞍 | 冒号串行; 多词拼接 | 洞狼鞍 | 中 |
| 60 | `ChitinPants` | armor（服饰/护甲） | ChitinPants | Chitin | 落魄海盗长裤 甲壳素 军阀裤子 | 多词拼接 | 甲壳素裤子 | 高 |
| 61 | `ChitinShirt` | armor（服饰/护甲） | ChitinShirt | Chitin | 好战分子上衣 生日礼服上衣 华丽海盗上衣 | 多词拼接 | 甲壳素上衣 | 高 |
| 64 | `CrabSaddle` | saddle（鞍具） | CrabSaddle_Icon | Crab | 温度: 披毛犀鞍 刺面龙鞍 | 冒号串行; 多词拼接 | 巨蟹鞍<br>Karkinos | 中 |
| 72 | `DiplodocusSaddle` | saddle（鞍具） | DiplodocusSaddle | Diplodocus Saddle | 温度: 披毛犀鞍 短面袋鼠鞍 | 冒号串行; 多词拼接 | 梁龙鞍 | 高 |
| 74 | `DolphinSaddle` | saddle（鞍具） | DolphinSaddle | Dolphin | 温度: 披毛犀鞍 短面袋鼠鞍 | 冒号串行; 多词拼接 | 鱼龙鞍<br>Ichthyosaurus | 中 |
| 83 | `GhillieBoots` | armor（服饰/护甲） | GhillieBoots | Ghillie Boots | 吉利胸甲 吉利靴 防暴靴 | 多词拼接 | 吉利靴 | 高 |
| 84 | `GhillieGloves` | armor（服饰/护甲） | GhillieGloves | Ghillie | 龙裔手套 吉利胸甲 防护手套 | 多词拼接 | 吉利手套 | 高 |
| 85 | `GhilliePants` | armor（服饰/护甲） | GhilliePants | Ghillie | 落魄海盗长裤 吉利胸甲 军阀裤子 | 多词拼接 | 吉利裤子 | 高 |
| 86 | `GhillieShirt` | armor（服饰/护甲） | GhillieShirt | Ghillie | 吉利胸甲 好战分子上衣 生日礼服上衣 | 多词拼接 | 吉利上衣 | 高 |
| 91 | `Grenade` | weapon（工具/武器） | Grenade_Icon | Grenade | 烟雾弹 泰克手雷 集束手雷 | 多词拼接 | 手雷 | 高 |
| 95 | `HazardSuitGloves` | armor（服饰/护甲） | HazardSuitGloves_Icon | Hazard Suit Gloves | 龙裔手套 防护手套 荒地 | 多词拼接 | 防护服手套 | 高 |
| 120 | `MammothSaddle` | saddle（鞍具） | MammothSaddle | Mammoth Saddle | 温度: 披毛犀鞍 短面袋鼠鞍 | 冒号串行; 多词拼接 | 猛犸象鞍 | 高 |
| 122 | `MegatheriumSaddle` | saddle（鞍具） | MegatheriumSaddle | Megatherium Saddle | 温度: 披毛犀鞍 短面袋鼠鞍 | 冒号串行; 多词拼接 | 大地懒鞍 | 高 |
| 123 | `MetalBoots` | armor（服饰/护甲） | MetalBoots | Metal | 金属小屋顶 金属三角地基 吉利靴 | 多词拼接 | 金属靴 | 高 |
| 124 | `MetalFloor` | structure（建筑构件） | MetalFloor_Icon | Metal Floor | 金属小屋顶 金属镰刀 金属三角地基 | 多词拼接 | 金属地板 | 高 |
| 125 | `MetalGloves` | armor（服饰/护甲） | MetalGloves | Metal | 金属小屋顶 防护手套 金属三角地基 | 多词拼接 | 金属手套 | 高 |
| 126 | `MetalPants` | armor（服饰/护甲） | MetalPants | Metal | 落魄海盗长裤 金属小屋顶 金属镰刀 | 多词拼接 | 金属裤子 | 高 |
| 127 | `MetalShirt` | armor（服饰/护甲） | MetalShirt | Metal | 生日礼服上衣 金属小屋顶 金属镰刀 | 多词拼接 | 金属上衣 | 高 |
| 132 | `MothSaddle` | saddle（鞍具） | MothSaddle_Icon | Moth Saddle | 温度: 披毛犀鞍 沙蛾蛋 | 冒号串行; 多词拼接 | 沙蛾鞍 | 高 |
| 142 | `PoisonTrap` | weapon（工具/武器） | PoisonTrap_Icon | Poison Trap | 被困住了! | 感叹/问句 | 毒药陷阱<br>原污染值「被困住了!」 | 高 |
| 152 | `RaptorSaddle` | saddle（鞍具） | RaptorSaddle | Raptor Saddle | 温度: 披毛犀鞍 骨架迅猛龙 | 冒号串行; 多词拼接 | 迅猛龙鞍 | 高 |
| 154 | `RefinedTranqDart` | ammo（弹药/投掷物） | RefinedTranqDart_Icon | Tranquilizer Dart | 信息素镖 麻醉箭 麻醉镖 | 多词拼接 | 精炼麻醉镖 | 高 |
| 163 | `ScorpionSaddle` | saddle（鞍具） | ScorpionSaddle | Scorpion | 温度: 披毛犀鞍 短面袋鼠鞍 | 冒号串行; 多词拼接 | 帝王蝎鞍 | 高 |
| 176 | `SpiderSaddle` | saddle（鞍具） | SpiderSaddle | Spider | 温度: 披毛犀鞍 短面袋鼠鞍 | 冒号串行; 多词拼接 | 阿拉尼奥蜘蛛鞍 | 中 |
| 178 | `SpineyLizardSaddle` | saddle（鞍具） | SpineyLizardSaddle_Icon | Spiney Lizard Saddle | 温度: 披毛犀鞍 刺面龙鞍 | 冒号串行; 多词拼接 | 刺面龙鞍 | 高 |
| 182 | `TekSniper` | tek（泰克装备） | TekSniper_Icon | Tek | 泰克越野车 泰克栅栏地基 制式狙击步枪子弹 | 多词拼接 | 待你定名 | — |
| 184 | `ThatchFloor` | structure（建筑构件） | ThatchFloor_Icon | Thatch Floor | 茅草斜直角三角 茅草半截细柱子 茅草双开门框 | 多词拼接 | 茅草地基 | 高 |
| 185 | `ThatchRoof` | structure（建筑构件） | ThatchRoof_Icon | Thatch Roof | 茅草斜直角三角 茅草半截细柱子 茅草双开门框 | 多词拼接 | 茅草屋顶 | 高 |
| 193 | `TurtleSaddle` | saddle（鞍具） | TurtleSaddle | Turtle | 碳龟蛋 温度: 披毛犀鞍 | 冒号串行; 多词拼接 | 碳龟鞍 | 高 |


---

## 🅲 C 类｜中文可用、仅英文是推断值（0 条）

> **本次为空**：所有「中文可用」的项，英文也都命中了官方条目。

---

## 🅴 D 类｜整族低优先（50 条）

> 这些族**同质度极高**，建议整族统一策略而非逐条校对。

### ApexDrop 顶级掉落族（32 条）

> **建议：暂缓汉化。** 该族是顶级生物掉落物，官方中文译本不稳定且玩家习惯用英文；前端回退显示英文 + 通用图标即可。

| # | 基名 | 类别 | icon | en 候选 | zh 候选 | 问题 | 建议 | 置信 |
|---|------|------|:----:|---------|---------|------|------|:---:|
| 5 | `ApexDrop_Acro` | resource（资源/材料） | - | Apex Drop_Acro | - | 无图标键;无中文;英文仅拆词 | 顶级掉落·高棘龙 | 低 |
| 6 | `ApexDrop_Allo` | resource（资源/材料） | ApexDropAllo_Icon | Apex Drop_Allo | - | 无中文;英文仅拆词 | 顶级掉落·异特龙 | 低 |
| 7 | `ApexDrop_AlphaCarno` | resource（资源/材料） | - | Apex Drop_Alpha Carno | - | 无图标键;无中文;英文仅拆词 | 顶级掉落·食肉牛龙（精英） | 低 |
| 8 | `ApexDrop_AlphaLeeds` | resource（资源/材料） | - | Apex Drop_Alpha Leeds | - | 无图标键;无中文;英文仅拆词 | 精英利兹鱼战利品<br>zhmap：精英利兹鱼(Alpha Leedsichthys) | 中 |
| 9 | `ApexDrop_AlphaMegalodon` | resource（资源/材料） | - | Apex Drop_Alpha Megalodon | - | 无图标键;无中文;英文仅拆词 | 顶级掉落·巨齿鲨（精英） | 低 |
| 10 | `ApexDrop_AlphaMosasaur` | resource（资源/材料） | - | Apex Drop_Alpha Mosasaur | - | 无图标键;无中文;英文仅拆词 | 顶级掉落·沧龙（精英） | 低 |
| 11 | `ApexDrop_AlphaRaptor` | resource（资源/材料） | - | Apex Drop_Alpha Raptor | - | 无图标键;无中文;英文仅拆词 | 顶级掉落·迅猛龙（精英） | 低 |
| 12 | `ApexDrop_AlphaRex` | resource（资源/材料） | - | Apex Drop_Alpha Rex | - | 无图标键;无中文;英文仅拆词 | 顶级掉落·霸王龙（精英） | 低 |
| 13 | `ApexDrop_AlphaTuso` | resource（资源/材料） | - | Apex Drop_Alpha Tuso | - | 无图标键;无中文;英文仅拆词 | 顶级掉落·托斯特巨鱿（精英） | 低 |
| 14 | `ApexDrop_Argentavis` | resource（资源/材料） | ApexDrop_Argentavis_Icon | Apex Drop_Argentavis | VR 阿根廷鹫 | 英文仅拆词 | 顶级掉落·阿根廷巨鹰 | 低 |
| 15 | `ApexDrop_AstralSoul` | resource（资源/材料） | - | Apex Drop_Astral Soul | - | 无图标键;无中文;英文仅拆词 | 顶级掉落·星魂 | 低 |
| 16 | `ApexDrop_Basilisk` | resource（资源/材料） | - | Apex Drop_Basilisk | - | 无图标键;无中文;英文仅拆词 | 顶级掉落·蛇怪 | 低 |
| 17 | `ApexDrop_Basilisk_Alpha` | resource（资源/材料） | - | Apex Drop_Basilisk_Alpha | - | 无图标键;无中文;英文仅拆词 | 顶级掉落·蛇怪（精英） | 低 |
| 18 | `ApexDrop_Basilo` | resource（资源/材料） | ApexDropBasilo_Icon | Apex Drop_Basilo | - | 无中文;英文仅拆词 | 顶级掉落·龙王鲸 | 低 |
| 19 | `ApexDrop_Boaratos` | resource（资源/材料） | - | Apex Drop_Boaratos | - | 无图标键;无中文;英文仅拆词 | 焰鬃獠猪獠牙<br>PO：Boaratos Tusk → 焰鬃獠猪獠牙 | 高 |
| 20 | `ApexDrop_Boaratos_Flaming` | resource（资源/材料） | - | Apex Drop_Boaratos_Flaming | - | 无图标键;无中文;英文仅拆词 | 焰鬃獠猪燃焰獠牙<br>PO：Flaming Boaratos Tusk | 高 |
| 21 | `ApexDrop_Cerato_ASA` | resource（资源/材料） | - | Apex Drop_Cerato_ASA | - | 无图标键;无中文;英文仅拆词 | 顶级掉落·角鼻龙 | 低 |
| 22 | `ApexDrop_CrabClaw` | resource（资源/材料） | ApexDropCrabClaw_Icon | Apex Drop_Crab Claw | - | 无中文;英文仅拆词 | 精英巨蟹鳌<br>PO：Alpha Karkinos Claw → 精英巨蟹鳌 | 高 |
| 23 | `ApexDrop_FireWyvern` | resource（资源/材料） | - | Apex Drop_Fire Wyvern | - | 无图标键;无中文;英文仅拆词 | 顶级掉落·火龙 | 低 |
| 24 | `ApexDrop_GasBag` | resource（资源/材料） | - | Apex Drop_Gas Bag | - | 无图标键;无中文;英文仅拆词 | 顶级掉落·毒气囊 | 低 |
| 25 | `ApexDrop_Giga` | resource（资源/材料） | ApexDropGiga_Icon | Apex Drop_Giga | - | 无中文;英文仅拆词 | 顶级掉落·南方巨兽龙 | 低 |
| 26 | `ApexDrop_LightningWyvern` | resource（资源/材料） | - | Apex Drop_Lightning Wyvern | - | 无图标键;无中文;英文仅拆词 | 顶级掉落·闪电飞龙 | 低 |
| 27 | `ApexDrop_Neophyte` | resource（资源/材料） | - | Apex Drop_Neophyte | - | 无图标键;无中文;英文仅拆词 | 猎杀者之角<br>PO：Neophyte Horns → 猎杀者之角 | 高 |
| 28 | `ApexDrop_PoisonWyvern` | resource（资源/材料） | - | Apex Drop_Poison Wyvern | - | 无图标键;无中文;英文仅拆词 | 顶级掉落·毒飞龙 | 低 |
| 29 | `ApexDrop_RockDrake` | resource（资源/材料） | - | Apex Drop_Rock Drake | - | 无图标键;无中文;英文仅拆词 | 顶级掉落·岩龙 | 低 |
| 30 | `ApexDrop_Sarco` | resource（资源/材料） | - | Apex Drop_Sarco | - | 无图标键;无中文;英文仅拆词 | 顶级掉落·帝鳄 | 低 |
| 31 | `ApexDrop_Sauro` | resource（资源/材料） | ApexDrop_Sauro_Icon | Apex Drop_Sauro | - | 无中文;英文仅拆词 | 顶级掉落·蜥甲龙 | 低 |
| 32 | `ApexDrop_SnowMonster` | resource（资源/材料） | - | Apex Drop_Snow Monster | - | 无图标键;无中文;英文仅拆词 | 顶级掉落·雪怪 | 低 |
| 33 | `ApexDrop_Thylaco` | resource（资源/材料） | - | Apex Drop_Thylaco | - | 无图标键;无中文;英文仅拆词 | 顶级掉落·袋狮<br>zhmap：thylacoleo = 袋狮（原袋剑虎修正） | 中 |
| 34 | `ApexDrop_Tuso` | resource（资源/材料） | - | Apex Drop_Tuso | - | 无图标键;无中文;英文仅拆词 | 顶级掉落·托斯特巨鱿 | 低 |
| 35 | `ApexDrop_Yuty` | resource（资源/材料） | - | Apex Drop_Yuty | - | 无图标键;无中文;英文仅拆词 | 顶级掉落·羽暴龙 | 低 |
| 36 | `ApexDrop_Zombie` | resource（资源/材料） | - | Apex Drop_Zombie | - | 无图标键;无中文;英文仅拆词 | 顶级掉落·僵尸 | 低 |


### LostColony 失落殖民地族（14 条）

> **建议：按批次补录。** 红色元素系列可直译；符印系列建议统一为「异常符印 / 绯红符印 · 初级/高级/顶级」。

| # | 基名 | 类别 | icon | en 候选 | zh 候选 | 问题 | 建议 | 置信 |
|---|------|------|:----:|---------|---------|------|------|:---:|
| 103 | `LostColony_AberrantSigil_Greater` | resource（资源/材料） | - | Lost Colony_Aberrant Sigil_Greater | - | 无图标键;无中文;英文仅拆词 | 强力异常魔符<br>zhmap：greater_aberrant_sigil = 强力异常魔符 | 高 |
| 104 | `LostColony_AberrantSigil_Minor` | resource（资源/材料） | - | Lost Colony_Aberrant Sigil_Minor | - | 无图标键;无中文;英文仅拆词 | 微弱异常魔符<br>按 Greater/Prime 官方命名类比 | 中 |
| 105 | `LostColony_AberrantSigil_Prime` | resource（资源/材料） | - | Lost Colony_Aberrant Sigil_Prime | - | 无图标键;无中文;英文仅拆词 | 本源异常魔符<br>zhmap：prime_aberrant_sigil = 本源异常魔符 | 高 |
| 106 | `LostColony_CrimsonSigil_Greater` | resource（资源/材料） | - | Lost Colony_Crimson Sigil_Greater | - | 无图标键;无中文;英文仅拆词 | 绯红符印·高级 | 低 |
| 107 | `LostColony_CrimsonSigil_Minor` | resource（资源/材料） | - | Lost Colony_Crimson Sigil_Minor | - | 无图标键;无中文;英文仅拆词 | 绯红符印·初级 | 低 |
| 108 | `LostColony_CrimsonSigil_Prime` | resource（资源/材料） | - | Lost Colony_Crimson Sigil_Prime | - | 无图标键;无中文;英文仅拆词 | 绯红符印·顶级 | 低 |
| 109 | `LostColony_RedElement` | resource（资源/材料） | - | Lost Colony_Red Element | - | 无图标键;无中文;英文仅拆词 | 腥红元素<br>PO：官方用「腥红元素」而非红色元素 | 高 |
| 110 | `LostColony_RedElementDustFromRedElement` | resource（资源/材料） | - | Lost Colony_Red Element Dust From Red Element | - | 无图标键;无中文;英文仅拆词 | 腥红元素粉尘（元素研磨） | 中 |
| 111 | `LostColony_RedElementDustFromShards` | resource（资源/材料） | - | Lost Colony_Red Element Dust From Shards | - | 无图标键;无中文;英文仅拆词 | 腥红元素粉尘（碎片研磨）<br>PO：用腥红元素碎片磨制的粉尘 | 中 |
| 112 | `LostColony_RedElementFromShards` | resource（资源/材料） | - | Lost Colony_Red Element From Shards | - | 无图标键;无中文;英文仅拆词 | 腥红元素（碎片合成） | 低 |
| 113 | `LostColony_RedElementRefined` | resource（资源/材料） | - | Lost Colony_Red Element Refined | - | 无图标键;无中文;英文仅拆词 | 精炼腥红元素 | 中 |
| 114 | `LostColony_RedElementShard` | resource（资源/材料） | - | Lost Colony_Red Element Shard | - | 无图标键;无中文;英文仅拆词 | 腥红元素碎片<br>PO：Red Element Shards → 腥红元素碎片 | 高 |
| 115 | `LostColony_RedElement_ShardRefined` | resource（资源/材料） | - | Lost Colony_Red Element_Shard Refined | - | 无图标键;无中文;英文仅拆词 | 精炼腥红元素碎片 | 中 |
| 116 | `LostColony_RefinedRedElementFromDust` | resource（资源/材料） | - | Lost Colony_Refined Red Element From Dust | - | 无图标键;无中文;英文仅拆词 | 精炼腥红元素（粉尘合成） | 低 |


### 载具部件族（2 条）

> **建议：直译补录**，条目少、歧义低。

| # | 基名 | 类别 | icon | en 候选 | zh 候选 | 问题 | 建议 | 置信 |
|---|------|------|:----:|---------|---------|------|------|:---:|
| 51 | `Car_Turret_Flamethrower` | other（其他/未归类） | - | Car_Turret_Flamethrower | - | 无图标键;无中文;英文仅拆词 | 车载火焰喷射器 | 高 |
| 52 | `Car_Wheels_Racer` | other（其他/未归类） | - | Car_Wheels_Racer | - | 无图标键;无中文;英文仅拆词 | 赛车车轮 | 高 |


### 生成器族（2 条）

> **建议：直译补录**（生成器类，用于调试面板，可保留英文）。

| # | 基名 | 类别 | icon | en 候选 | zh 候选 | 问题 | 建议 | 置信 |
|---|------|------|:----:|---------|---------|------|------|:---:|
| 173 | `Spawner_Enforcer` | other（其他/未归类） | - | Spawner_Enforcer | - | 无图标键;无中文;英文仅拆词 | 执行者生成器 | 中 |
| 174 | `Spawner_Mek` | other（其他/未归类） | - | Spawner_Mek | - | 无图标键;无中文;英文仅拆词 | 机甲生成器 | 中 |


---

## 📎 附录 A｜已采纳 248 条（按类分组，组内按出现次数降序）

> `次数` = 该基名在 11 服离线数据中出现的总次数（越靠前越常见，优先校对收益越高）。
> 「其他／未归类」多为中文取到**物种名**或杂项，仍可按需复核。

### resource（资源/材料）（72 条）

| 基名 | 类别 | icon | en | zh | 次数 | src |
|------|------|------|----|----|:---:|-----|
| `ShardRefined` | resource（资源/材料） | — | Element Shard | 元素碎片 | 3089 | resource |
| `GigantoraptorFeather` | resource（资源/材料） | — | Gigantoraptor Feather | 巨盗龙羽毛 | 1541 | resource |
| `MetalIngot` | resource（资源/材料） | Metal_Ingot | Metal Ingot | 金属锭 | 1496 | resource |
| `Hide` | resource（资源/材料） | Hide | Hide | 兽皮 | 1425 | resource |
| `Gasoline` | resource（资源/材料） | Gasoline | Gasoline | 汽油 | 1112 | resource |
| `Wood` | resource（资源/材料） | Wood | Wood | 木头 | 820 | resource |
| `Chitin` | resource（资源/材料） | Chitin | Chitin | 甲壳素 | 786 | resource |
| `ScrapMetalIngot` | resource（资源/材料） | ScrapMetalIngot_Icon | Scrap Metal Ingot | 废金属锭 | 704 | resource |
| `Metal` | resource（资源/材料） | — | Metal | 金属 | 699 | resource |
| `Fibers` | resource（资源/材料） | — | Fiber | 纤维 | 697 | resource |
| `Thatch` | resource（资源/材料） | Thatch | Thatch | 茅草 | 663 | resource |
| `Stone` | resource（资源/材料） | Stone | Stone | 石头 | 630 | resource |
| `RareFlower` | resource（资源/材料） | Rare_Flower | Rare Flower | 稀有花朵 | 615 | resource |
| `Gas` | resource（资源/材料） | — | Congealed Gas Ball | 瓦斯 | 614 | resource |
| `Keratin` | resource（资源/材料） | Keratin | Keratin | 角质 | 528 | resource |
| `ElementShard` | resource（资源/材料） | — | Element Shard | 元素碎片 | 508 | resource |
| `Gunpowder` | resource（资源/材料） | Gunpowder | Gunpowder | 火药 | 508 | resource |
| `ChitinPaste` | resource（资源/材料） | — | Cementing Paste | 水泥 | 468 | resource |
| `Charcoal` | resource（资源/材料） | Charcoal | Charcoal | 煤炭 | 465 | resource |
| `Element` | resource（资源/材料） | Element | ELEMENT | 元素 | 463 | resource |
| `Sparkpowder` | resource（资源/材料） | Sparkpowder | Sparkpowder | 引火粉 | 459 | resource |
| `Oil` | resource（资源/材料） | — | Oil | 油 | 394 | resource |
| `Flint` | resource（资源/材料） | Flint | Flint | 燧石 | 393 | resource |
| `ElementDust` | resource（资源/材料） | ElementDust_Icon | Element Dust | 元素粉尘 | 317 | resource |
| `Pelt` | resource（资源/材料） | Pelt | Pelt | 毛皮 | 287 | resource |
| `AnglerGel` | resource（资源/材料） | AnglerGel | AnglerGel | 鮟鱇鱼油 | 280 | resource |
| `RareMushroom` | resource（资源/材料） | — | Rare Mushroom | 稀有蘑菇 | 272 | resource |
| `MetalIngot_FromMegaForge` | resource（资源/材料） | — | Metal Ingot | 金属锭 | 260 | resource |
| `Crystal` | resource（资源/材料） | Crystal | Crystal | 水晶 | 221 | resource |
| `Sap` | resource（资源/材料） | Sap | Sap | 树脂 | 200 | resource |
| `Silicon` | resource（资源/材料） | Silicon_Icon | Silica Pearls | 含硅珍珠 | 193 | resource |
| `Propellant` | resource（资源/材料） | Propellant_Icon | Propellant | 燃烧剂 | 159 | resource |
| `Electronics` | resource（资源/材料） | — | Electronics | 电路元件 | 154 | resource |
| `Clay` | resource（资源/材料） | Clay_Icon | Clay | 黏土 | 138 | resource |
| `RareDrop_CorruptHeart` | resource（资源/材料） | — | Rare | 稀有 | 128 | resource |
| `PeltOrHair` | resource（资源/材料） | — | Pelt | 毛皮 | 120 | resource |
| `Silk` | resource（资源/材料） | Silk_Icon | Silk | 蚕丝 | 119 | resource |
| `PreservingSalt` | resource（资源/材料） | PreservingSalt_Icon | Preserving Salt | 防腐盐 | 116 | resource |
| `Polymer` | resource（资源/材料） | Polymer | Polymer | 聚合物 | 112 | resource |
| `Obsidian` | resource（资源/材料） | Obsidian | Obsidian | 黑曜石 | 108 | resource |
| `Sulfur` | resource（资源/材料） | Sulfur_Icon | Sulfur | 硫磺 | 107 | resource |
| `SubstrateAbsorbent` | resource（资源/材料） | — | Absorbent Substrate | 吸附剂 | 102 | resource |
| `ElementPowerNode` | resource（资源/材料） | — | Element | 元素 | 101 | resource |
| `ApexDrop_Megalania` | resource（资源/材料） | ApexDropMegalania_Icon | Apex Drop_Megalania | 古巨蜥战利品 | 70 | resource |
| `CommonMushroom` | resource（资源/材料） | Common_Mushroom | Common Mushroom | 普通蘑菇 | 69 | resource |
| `ElementDustFromElement` | resource（资源/材料） | — | Element Dust | 元素粉尘 | 66 | resource |
| `ElementDustFromShards` | resource（资源/材料） | — | Element Dust | 元素粉尘 | 66 | resource |
| `ElementRefined` | resource（资源/材料） | — | Element | 元素 | 66 | resource |
| `Sand` | resource（资源/材料） | Sand_Icon | Sand | 沙 | 64 | resource |
| `ApexDrop_Megalodon` | resource（资源/材料） | ApexDrop_Megalodon_Icon | Apex Drop_Megalodon | 巨齿鲨颌骨标本战利品 | 60 | resource |
| `Gasoline_GasCrafted` | resource（资源/材料） | — | Gasoline | 瓦斯油 | 60 | resource |
| `BlackPearl` | resource（资源/材料） | Black_Pearl | Black Pearl | 黑珍珠 | 57 | resource |
| `ApexDrop_Rex` | resource（资源/材料） | ApexDrop_Rex_Icon | Apex Drop_Rex | 精英霸王龙战利品 | 45 | resource |
| `ElementOre` | resource（资源/材料） | — | Element Ore | 元素矿石 | 42 | resource |
| `FungalWood` | resource（资源/材料） | — | Fungal Wood | 真菌木头 | 34 | resource |
| `ScrapMetal` | resource（资源/材料） | ScrapMetal_Icon | Scrap Metal | 废金属 | 31 | resource |
| `CondensedGas` | resource（资源/材料） | CondensedGas_icon | Condensed Gas | 冷凝瓦斯 | 29 | resource |
| `ApexDrop_Boa` | resource（资源/材料） | ApexDropBoa_Icon | Apex Drop_Boa | 焰鬃獠猪 | 28 | resource |
| `ApexDrop_Spino` | resource（资源/材料） | ApexDropSpino_Icon | Apex Drop_Spino | 棘龙战利品 | 28 | resource |
| `ApexDrop_Theriz` | resource（资源/材料） | ApexDropTherizino_Icon | Apex Drop_Theriz | 镰刀龙 | 22 | resource |
| `SquidOil` | resource（资源/材料） | SquidOil_Icon | Squid Oil | 巨鱿油 | 21 | resource |
| `Wool` | resource（资源/材料） | Wool | Wool | 羊毛 | 18 | resource |
| `AmmoniteBlood` | resource（资源/材料） | — | Ammonite | 菊石 | 8 | resource |
| `CorruptedWood` | resource（资源/材料） | — | Corrupted Wood | 腐化木头 | 8 | resource |
| `RawSalt` | resource（资源/材料） | RawSalt_Icon | Raw Salt | 生盐 | 8 | resource |
| `LeechBlood` | resource（资源/材料） | Leech_Blood | Leech Blood | 水蛭血 | 7 | resource |
| `RareFlower_ShoulderDragonCraftable` | resource（资源/材料） | — | Rare | 稀有 | 6 | resource |
| `LuminaScale` | resource（资源/材料） | — | Lumina | 皎光仔 | 5 | resource |
| `Silicate` | resource（资源/材料） | — | Silicate | 硅酸盐 | 5 | resource |
| `ElementRefinedFromRedElement` | resource（资源/材料） | — | Element | 元素 | 4 | resource |
| `TurtleShell` | resource（资源/材料） | — | Turtle | 碳龟 | 3 | resource |
| `Resin` | resource（资源/材料） | — | Resin | 黏脂 | 2 | resource |


### ammo（弹药/投掷物）（20 条）

| 基名 | 类别 | icon | en | zh | 次数 | src |
|------|------|------|----|----|:---:|-----|
| `AdvancedRifleBullet` | ammo（弹药/投掷物） | — | Advanced Rifle Bullet | 高级步枪子弹 | 687 | ammo |
| `AdvancedBullet` | ammo（弹药/投掷物） | — | Advanced Bullet | 高级子弹 | 263 | ammo |
| `BallistaArrow` | ammo（弹药/投掷物） | BallistaArrow_Icon | Ballista | 箭 | 255 | ammo |
| `ArrowStone` | ammo（弹药/投掷物） | — | Stone Arrow | 石箭 | 254 | ammo |
| `TranqDart` | ammo（弹药/投掷物） | — | Tranquilizer Dart | 麻醉镖 | 239 | ammo |
| `CannonBall` | ammo（弹药/投掷物） | Cannon_Ball | Cannon Ball | 火炮弹丸 | 238 | ammo |
| `SimpleBullet` | ammo（弹药/投掷物） | — | Simple Bullet | 简易子弹 | 234 | ammo |
| `GrapplingHook` | ammo（弹药/投掷物） | Grappling_Hook | Grappling Hook | 爪钩 | 213 | ammo |
| `TranqSpearBolt` | ammo（弹药/投掷物） | TranqSpearBolt_Icon | Spear Bolt | 麻醉弩箭 | 196 | ammo |
| `ChainBola` | ammo（弹药/投掷物） | Chain_Bola | Chain Bola | 流星锁链 | 192 | ammo |
| `CannonBall_ToF_Corrosive` | ammo（弹药/投掷物） | — | Cannon | 火炮 | 153 | ammo |
| `CannonBall_ToF_Incendiary` | ammo（弹药/投掷物） | — | Cannon | 火炮 | 153 | ammo |
| `CannonBall_ToF_Reinforced` | ammo（弹药/投掷物） | — | Cannon | 火炮 | 153 | ammo |
| `AdvancedSniperBullet` | ammo（弹药/投掷物） | Advanced_Sniper_Bullet | Advanced Sniper Bullet | 制式狙击步枪子弹 | 95 | ammo |
| `CompoundBowArrow` | ammo（弹药/投掷物） | — | Compound Bow | 复合弓 | 95 | ammo |
| `RocketHomingMissile` | ammo（弹药/投掷物） | Rocket_Homing_Missile | Rocket Homing Missile | 制导火箭弹 | 86 | ammo |
| `Flamethrower` | ammo（弹药/投掷物） | Flamethrower | Flamethrower | 火焰喷射器 | 79 | ammo |
| `CannonShell` | ammo（弹药/投掷物） | — | Cannon Shell | 加农炮弹 | 57 | ammo |
| `RocketPod` | ammo（弹药/投掷物） | — | Rocket Pod | 火箭弹仓 | 57 | ammo |
| `Boulder` | ammo（弹药/投掷物） | Boulder | Boulder | 巨石 | 2 | ammo |


### structure（建筑构件）（23 条）

| 基名 | 类别 | icon | en | zh | 次数 | src |
|------|------|------|----|----|:---:|-----|
| `BearTrap_Large` | structure（建筑构件） | — | Bear | 捕兽夹 | 1 | blueprint |
| `CryoFridge` | structure（建筑构件） | Cryofridge | Cryofridge | 低温冰箱 | 1 | blueprint |
| `DedicatedStorage` | structure（建筑构件） | — | Dedicated Storage | 泰克专用储物箱 | 1 | blueprint |
| `ElevatorPlatformMedium` | structure（建筑构件） | — | Elevator Platform | 电梯平台 | 1 | blueprint |
| `ElevatorTrackBase` | structure（建筑构件） | — | Elevator Track | 电梯轨道 | 1 | blueprint |
| `MetalCeiling` | structure（建筑构件） | — | Metal Ceiling | 金属天花板 | 1 | blueprint |
| `MetalDoor` | structure（建筑构件） | — | Metal Door | 金属门 | 1 | blueprint |
| `MetalGate` | structure（建筑构件） | — | Metal Gate | 金属恐龙门 | 1 | blueprint |
| `MetalGateframe` | structure（建筑构件） | MetalGateFrame_Icon | Metal Gate | 金属恐龙门 | 1 | blueprint |
| `MetalGateframe_Large` | structure（建筑构件） | — | Metal | 金属恐龙门 | 1 | blueprint |
| `MetalPillar` | structure（建筑构件） | — | Metal Pillar | 金属柱子 | 1 | blueprint |
| `MetalRailing` | structure（建筑构件） | — | Metal Railing | 金属栏杆 | 1 | blueprint |
| `MetalWall` | structure（建筑构件） | — | Metal Wall | 金属墙 | 1 | blueprint |
| `StoneGate` | structure（建筑构件） | — | Stone | 石头 | 1 | blueprint |
| `StorageBox_Huge` | structure（建筑构件） | — | Storage | 储存 | 1 | blueprint |
| `TekGateframe_Large` | structure（建筑构件） | — | Tek | 泰克 | 1 | blueprint |
| `TekPillar` | structure（建筑构件） | Tek_Pillar | Tek Pillar | 泰克柱子 | 1 | blueprint |
| `TekWall` | structure（建筑构件） | Tek_Wall | Tek Wall | 泰克墙 | 1 | blueprint |
| `ThatchCeiling` | structure（建筑构件） | — | Thatch Ceiling | 茅草屋顶 | 1 | blueprint |
| `ThatchWall` | structure（建筑构件） | — | Thatch Wall | 茅草墙 | 1 | blueprint |
| `WoodCeiling` | structure（建筑构件） | WoodCeiling_Icon | Wood Ceiling | 木制天花板 | 1 | blueprint |
| `WoodRailing` | structure（建筑构件） | WoodRailing_Icon | Wood Railing | 木制栏杆 | 1 | blueprint |
| `WoodWall_Sloped_Left` | structure（建筑构件） | — | Wood | 木头 | 1 | blueprint |


### consumable（消耗品）（3 条）

| 基名 | 类别 | icon | en | zh | 次数 | src |
|------|------|------|----|----|:---:|-----|
| `Narcotic` | consumable（消耗品） | Narcotic | Narcotic | 麻醉药 | 6 | blueprint |
| `Stimulant` | consumable（消耗品） | Stimulant | Stimulant | 兴奋剂 | 5 | blueprint |
| `BeerJar` | consumable（消耗品） | Beer_Jar | Beer Jar | 扎啤 | 1 | blueprint |


### saddle（鞍具）（36 条）

| 基名 | 类别 | icon | en | zh | 次数 | src |
|------|------|------|----|----|:---:|-----|
| `DaeodonSaddle` | saddle（鞍具） | DaeodonSaddle | Daeodon Saddle | 凶齿豨鞍 | 38 | blueprint |
| `IguanodonSaddle` | saddle（鞍具） | IguanodonSaddle | Iguanodon Saddle | 禽龙鞍 | 36 | blueprint |
| `MegalosaurusSaddle` | saddle（鞍具） | MegalosaurusSaddle | Megalosaurus Saddle | 巨齿龙鞍 | 35 | blueprint |
| `Paracer_Saddle` | saddle（鞍具） | ParacerSaddle | Paracer Saddle | 巨犀鞍 | 34 | blueprint |
| `MegalaniaSaddle` | saddle（鞍具） | MegalaniaSaddle | Megalania Saddle | 古巨蜥鞍 | 32 | blueprint |
| `ArgentavisSaddle` | saddle（鞍具） | ArgentavisSaddle | Argentavis Saddle | 阿根廷鹫鞍 | 31 | blueprint |
| `AnkyloSaddle` | saddle（鞍具） | AnkyloSaddle | Ankylo Saddle | 甲龙鞍 | 28 | blueprint |
| `BaryonyxSaddle` | saddle（鞍具） | BaryonyxSaddle | Baryonyx Saddle | 重爪龙鞍 | 27 | blueprint |
| `TherizinosaurusSaddle` | saddle（鞍具） | TherizinosaurusSaddle | Therizinosaurus Saddle | 镰刀龙鞍 | 27 | blueprint |
| `DireBearSaddle` | saddle（鞍具） | Dire_Bear_Saddle | Dire Bear Saddle | 恐熊鞍 | 25 | blueprint |
| `GigantoraptorSaddle` | saddle（鞍具） | — | Gigantoraptor Saddle | 巨盗龙鞍 | 25 | blueprint |
| `KaprosuchusSaddle` | saddle（鞍具） | KaprosuchusSaddle | Kaprosuchus Saddle | 猪鳄鞍 | 22 | blueprint |
| `SarcoSaddle` | saddle（鞍具） | Sarco_Saddle | Sarco Saddle | 帝鳄鞍 | 22 | blueprint |
| `TrikeSaddle` | saddle（鞍具） | TrikeSaddle | Trike Saddle | 三角龙鞍 | 22 | blueprint |
| `DunkleosteusSaddle` | saddle（鞍具） | Dunkleosteus_Saddle | Dunkleosteus Saddle | 邓氏鱼鞍 | 21 | blueprint |
| `EquusSaddle` | saddle（鞍具） | Equus_Saddle | Equus Saddle | 庞马鞍 | 21 | blueprint |
| `QuetzSaddle` | saddle（鞍具） | Quetz_Saddle | Quetz Saddle | 风神翼龙鞍 | 20 | blueprint |
| `StegoSaddle` | saddle（鞍具） | — | Stego Saddle | 剑龙鞍 | 20 | blueprint |
| `RexSaddle` | saddle（鞍具） | RexSaddle | Rex Saddle | 霸王龙鞍 | 18 | blueprint |
| `MegalodonSaddle` | saddle（鞍具） | MegalodonSaddle | Megalodon Saddle | 巨齿鲨鞍 | 15 | blueprint |
| `TusoSaddle` | saddle（鞍具） | TusoSaddle | Tusoteuthis Saddle | 托斯特巨鱿鞍 | 13 | blueprint |
| `AcroSaddle` | saddle（鞍具） | Acro_Saddle | Acro Saddle | 高棘龙鞍 | 12 | blueprint |
| `MantisSaddle` | saddle（鞍具） | MantisSaddle_Icon | Mantis Saddle | 螳螂鞍 | 12 | blueprint |
| `CarchaSaddle` | saddle（鞍具） | — | Carcha Saddle | 鲨齿龙鞍 | 11 | blueprint |
| `MantaSaddle` | saddle（鞍具） | Manta_Saddle | Manta Saddle | 蝠鲼鞍 | 10 | blueprint |
| `ProcoptodonSaddle` | saddle（鞍具） | Procoptodon_Saddle | Procoptodon Saddle | 短面袋鼠鞍 | 10 | blueprint |
| `RockGolemSaddle` | saddle（鞍具） | RockGolemSaddle_Icon | Rock Golem Saddle | 岩石巨人鞍 | 10 | blueprint |
| `BisonSaddle` | saddle（鞍具） | Bison_Saddle | Bison Saddle | 野牛鞍 | 7 | blueprint |
| `PachySaddle` | saddle（鞍具） | Pachy_Saddle | Pachy Saddle | 肿头龙鞍 | 7 | blueprint |
| `PhiomiaSaddle` | saddle（鞍具） | PhiomiaSaddle | Phiomia Saddle | 法尤姆象鞍 | 7 | blueprint |
| `RockDrakeSaddle` | saddle（鞍具） | RockDrakeSaddle_Icon | Rock Drake Saddle | 岩龙鞍 | 6 | blueprint |
| `YiLingSaddle` | saddle（鞍具） | — | Yi Ling Saddle | 翎翼龙鞍 | 5 | blueprint |
| `DeinonychusSaddle` | saddle（鞍具） | Deinonychus_Saddle | Deinonychus Saddle | 恐爪龙鞍 | 3 | blueprint |
| `BasiliskSaddle` | saddle（鞍具） | Basilisk_Saddle | Basilisk Saddle | 帝蟒鞍 | 2 | blueprint |
| `DesmodusSaddle` | saddle（鞍具） | Desmodus_Saddle | Desmodus Saddle | 吸血蝠鞍 | 1 | blueprint |
| `UmbraSaddle` | saddle（鞍具） | — | Umbra Saddle | 幽影仔鞍 | 1 | blueprint |


### armor（服饰/护甲）（61 条）

| 基名 | 类别 | icon | en | zh | 次数 | src |
|------|------|------|----|----|:---:|-----|
| `TekHelmet` | armor（服饰/护甲） | — | Tek Helmet | 泰克头盔 | 87 | blueprint |
| `TekPants` | armor（服饰/护甲） | — | Tek | 泰克 | 85 | blueprint |
| `TekGloves` | armor（服饰/护甲） | TEKGloves | Tek | 泰克 | 82 | blueprint |
| `TekBoots` | armor（服饰/护甲） | Tek_Boots | Tek Boots | 泰克靴 | 81 | blueprint |
| `TekShirt` | armor（服饰/护甲） | — | Tek | 泰克 | 65 | blueprint |
| `FurShirt` | armor（服饰/护甲） | — | Fur | 毛皮 | 51 | blueprint |
| `MetalHelmet` | armor（服饰/护甲） | — | Metal | 金属 | 46 | blueprint |
| `FurHelmet` | armor（服饰/护甲） | — | Fur | 毛皮 | 44 | blueprint |
| `RiotBoots` | armor（服饰/护甲） | Riot_Boots | Riot Boots | 防暴靴 | 44 | blueprint |
| `RiotShirt` | armor（服饰/护甲） | — | Riot | 防暴 | 39 | blueprint |
| `FurBoots` | armor（服饰/护甲） | Fur_Boots | Fur Boots | 毛皮靴 | 38 | blueprint |
| `FurGloves` | armor（服饰/护甲） | — | Fur | 毛皮 | 37 | blueprint |
| `ChitinHelmet` | armor（服饰/护甲） | — | Chitin Helmet | 甲壳头盔 | 34 | blueprint |
| `FurPants` | armor（服饰/护甲） | — | Fur | 毛皮 | 34 | blueprint |
| `RiotHelmet` | armor（服饰/护甲） | Riot_Helmet | Riot Helmet | 防暴帽 | 32 | blueprint |
| `ChitinGloves` | armor（服饰/护甲） | ChitinGloves | Chitin | 甲壳素/角质 | 30 | blueprint |
| `ChitinBoots` | armor（服饰/护甲） | ChitinBoots | Chitin Boots | 甲壳靴 | 28 | blueprint |
| `RiotGloves` | armor（服饰/护甲） | RiotGloves | Riot | 防暴 | 27 | blueprint |
| `GhillieHelmet` | armor（服饰/护甲） | — | Ghillie | 吉利服 | 26 | blueprint |
| `RiotPants` | armor（服饰/护甲） | — | Riot | 防暴 | 26 | blueprint |
| `MetalShield` | armor（服饰/护甲） | Metal_Shield | Metal Shield | 金属盾牌 | 24 | blueprint |
| `HazardSuitPants` | armor（服饰/护甲） | HazardSuitPants_Icon | Hazard Suit Pants | 防护裤 | 19 | blueprint |
| `MekBackpack_Shield` | armor（服饰/护甲） | — | Mek | 机甲 | 19 | blueprint |
| `HazardSuitShirt` | armor（服饰/护甲） | Hazard_Suit_Shirt | Hazard Suit Shirt | 防护上衣 | 16 | blueprint |
| `WoodShield` | armor（服饰/护甲） | — | Wood | 木头 | 14 | blueprint |
| `Gallimimus` | armor（服饰/护甲） | Gallimimus | Gallimimus | 似鸡龙 | 13 | blueprint |
| `HazardSuitBoots` | armor（服饰/护甲） | Hazard_Suit_Boots | Hazard Suit Boots | 防护靴 | 13 | blueprint |
| `Helicoprion` | armor（服饰/护甲） | Helicoprion | Helicoprion | 旋齿鲨 | 12 | blueprint |
| `MekBackpack_MissilePod` | armor（服饰/护甲） | — | Mek | 机甲 | 12 | blueprint |
| `ClothHelmet` | armor（服饰/护甲） | — | Cloth | 粗布 | 11 | blueprint |
| `ClothShirt` | armor（服饰/护甲） | — | Cloth Shirt | 粗布衣服 | 11 | blueprint |
| `HideHelmet` | armor（服饰/护甲） | — | Hide | 兽皮 | 11 | blueprint |
| `HideGloves` | armor（服饰/护甲） | HideGloves | Hide Gloves | 兽皮手套 | 10 | blueprint |
| `HidePants` | armor（服饰/护甲） | — | Hide Pants | 兽皮裤 | 10 | blueprint |
| `HideShirt` | armor（服饰/护甲） | HideShirt | Hide Shirt | 兽皮上衣 | 10 | blueprint |
| `ClothBoots` | armor（服饰/护甲） | — | Cloth Boots | 粗布鞋 | 9 | blueprint |
| `ClothPants` | armor（服饰/护甲） | — | Cloth Pants | 粗布裤子 | 9 | blueprint |
| `HazardSuitHelmet` | armor（服饰/护甲） | — | Hazard | 防护 | 9 | blueprint |
| `ScubaShirt_SuitWithTank` | armor（服饰/护甲） | — | Scuba | 潜水服 | 9 | blueprint |
| `DesertClothGogglesHelmet` | armor（服饰/护甲） | — | Desert Cloth | 沙漠服 | 8 | blueprint |
| `DesertClothPants` | armor（服饰/护甲） | Desert_Cloth_Pants | Desert Cloth Pants | 沙漠裤子 | 8 | blueprint |
| `HideBoots` | armor（服饰/护甲） | HideBoots | Hide Boots | 兽皮靴 | 8 | blueprint |
| `ClothGloves` | armor（服饰/护甲） | — | Cloth Gloves | 粗布手套 | 7 | blueprint |
| `MekBackpack_SiegeCannon` | armor（服饰/护甲） | — | Mek | 机甲 | 6 | blueprint |
| `DesertClothGloves` | armor（服饰/护甲） | Desert_Cloth_Gloves | Desert Cloth Gloves | 沙漠手套 | 5 | blueprint |
| `DesertClothShirt` | armor（服饰/护甲） | Desert_Cloth_Shirt | Desert Cloth Shirt | 沙漠衣服 | 5 | blueprint |
| `DesertClothBoots` | armor（服饰/护甲） | Desert_Cloth_Boots | Desert Cloth Boots | 沙漠鞋 | 4 | blueprint |
| `ScubaHelmet_Goggles` | armor（服饰/护甲） | — | Scuba | 潜水服 | 4 | blueprint |
| `ArcticShirt` | armor（服饰/护甲） | — | Arctic | 北极 | 3 | blueprint |
| `ScubaBoots_Flippers` | armor（服饰/护甲） | — | Scuba | 潜水服 | 3 | blueprint |
| `RiotPants_Cursed` | armor（服饰/护甲） | — | Riot | 防暴 | 2 | blueprint |
| `ScubaPants` | armor（服饰/护甲） | — | Scuba | 潜水服 | 2 | blueprint |
| `TekGloves_Cursed` | armor（服饰/护甲） | — | Tek | 泰克 | 2 | blueprint |
| `TekPants_Cursed` | armor（服饰/护甲） | — | Tek | 泰克 | 2 | blueprint |
| `ArcticGloves` | armor（服饰/护甲） | — | Arctic | 北极 | 1 | blueprint |
| `ArcticPants` | armor（服饰/护甲） | — | Arctic | 北极 | 1 | blueprint |
| `GasMask` | armor（服饰/护甲） | Gas_Mask | Gas Mask | 防毒面具 | 1 | blueprint |
| `MetalPants_Cursed` | armor（服饰/护甲） | — | Metal | 金属 | 1 | blueprint |
| `MetalShirt_Cursed` | armor（服饰/护甲） | — | Metal | 金属 | 1 | blueprint |
| `RiotShirt_Cursed` | armor（服饰/护甲） | — | Riot | 防暴 | 1 | blueprint |
| `TekBoots_Cursed` | armor（服饰/护甲） | — | Tek | 泰克靴 | 1 | blueprint |


### weapon（工具/武器）（27 条）

| 基名 | 类别 | icon | en | zh | 次数 | src |
|------|------|------|----|----|:---:|-----|
| `Rifle` | weapon（工具/武器） | — | Rifle | 步枪 | 96 | blueprint |
| `CompoundBow` | weapon（工具/武器） | Compound_Bow | Compound Bow | 复合弓 | 49 | blueprint |
| `MachinedPistol` | weapon（工具/武器） | MachinedPistol_Icon | Machined Pistol | 手枪 | 48 | blueprint |
| `MachinedShotgun` | weapon（工具/武器） | MachinedShotgun_Icon | Shotgun | 霰弹枪 | 48 | blueprint |
| `Crossbow` | weapon（工具/武器） | — | Crossbow | 十字弩 | 47 | blueprint |
| `MetalHatchet` | weapon（工具/武器） | Metal_Hatchet | Metal Hatchet | 金属斧子 | 41 | blueprint |
| `MetalPick` | weapon（工具/武器） | Metal_Pick | Metal Pick | 金属镐 | 40 | blueprint |
| `Sword` | weapon（工具/武器） | Sword_Icon | Sword | 剑 | 38 | blueprint |
| `Pike` | weapon（工具/武器） | Pike_Icon | Pike | 金属矛 | 36 | blueprint |
| `Shotgun` | weapon（工具/武器） | Shotgun_Icon | Shotgun | 霰弹枪 | 34 | blueprint |
| `ScoutRemote` | weapon（工具/武器） | — | Scout Remote | 侦察机遥控器 | 27 | blueprint |
| `ScoutRemote_CityTerminal` | weapon（工具/武器） | — | Scout | 侦察机 | 27 | blueprint |
| `Torch` | weapon（工具/武器） | Torch | Torch | 火把 | 27 | blueprint |
| `StoneClub` | weapon（工具/武器） | — | Stone | 石头 | 20 | blueprint |
| `StonePick` | weapon（工具/武器） | Stone_Pick | Stone Pick | 石镐 | 20 | blueprint |
| `TekSword` | weapon（工具/武器） | TEKSword_Icon | Tek Sword | 泰克剑 | 16 | blueprint |
| `StoneHatchet` | weapon（工具/武器） | Stone_Hatchet | Stone Hatchet | 石制斧头 | 15 | blueprint |
| `Slingshot` | weapon（工具/武器） | Slingshot_Icon | Slingshot | 弹弓 | 13 | blueprint |
| `GooGun` | weapon（工具/武器） | Goo_Gun | Goo Gun | 黏液枪 | 11 | blueprint |
| `Whip` | weapon（工具/武器） | Whip | Whip | 鞭子 | 9 | blueprint |
| `Lance` | weapon（工具/武器） | Lance_Icon | Lance | 长枪 | 7 | blueprint |
| `MiningDrill` | weapon（工具/武器） | Mining_Drill | Mining Drill | 矿枪 | 4 | blueprint |
| `TekClaws` | weapon（工具/武器） | — | Tek Claws | 泰克光刃 | 2 | blueprint |
| `MetalHatchet_Cursed` | weapon（工具/武器） | — | Metal | 金属斧子 | 1 | blueprint |
| `OilJar` | weapon（工具/武器） | Oil_Jar | Oil Jar | 油罐 | 1 | blueprint |
| `Spear` | weapon（工具/武器） | Spear_Icon | Spear | 长矛 | 1 | blueprint |
| `TekSword_Cursed` | weapon（工具/武器） | — | Tek | 泰克剑 | 1 | blueprint |


### tek（泰克装备）（2 条）

| 基名 | 类别 | icon | en | zh | 次数 | src |
|------|------|------|----|----|:---:|-----|
| `TekRifle` | tek（泰克装备） | TEKRifle_Icon | Tek Rifle | 泰克步枪 | 72 | blueprint |
| `TekRifle_Cursed` | tek（泰克装备） | — | Tek | 泰克步枪 | 1 | blueprint |


### other（其他/未归类）（4 条）

| 基名 | 类别 | icon | en | zh | 次数 | src |
|------|------|------|----|----|:---:|-----|
| `ChainSaw` | other（其他/未归类） | Chainsaw | Chainsaw | 电锯 | 10 | blueprint |
| `GasGrenade` | other（其他/未归类） | — | Gas | 瓦斯 | 1 | blueprint |
| `PoisonGrenade` | other（其他/未归类） | Poison_Grenade | Poison Grenade | 毒气手雷 | 1 | blueprint |
| `OrganicPolymer` | other（其他/未归类） | Organic_Polymer | Organic Polymer | 有机聚合物 | 0 | — |


---

## 🔧 附录 B｜本批被排除的规则清单

| # | 规则 | 拦截内容 |
|---|------|---------|
| 1 | 中文含空格 | 多词拼接 / 同 ID 聚合了多个词条（如「复合弓 泰克弓 弓」） |
| 2 | 中文含冒号 | 温度提示串入（如「温度: 披毛犀鞍 短面袋鼠鞍」） |
| 3 | 中文含 `!?！？` | 成就 / 提示文本（如「被困住了!」） |
| 4 | `*Saddle` 但英文不含 `Saddle` | 图标键命中了物种图标 |
| 5 | `*Saddle` 但中文不含「鞍」 | 同上，中文取到物种名 |
| 6 | 无中文候选 | 三级链全部未命中 |
| 7 | 英文仅拆词 | 英文是 camel 拆词推断值，非官方条目 |

## 🔍 附录 C｜本批暴露的系统性问题（建议后续改进）

1. **图标键命名不统一**：`icons2.json` 中鞍类图标既有 `Acro_Saddle` 也有 `CarnoSaddle`，反查 `基名_Icon` 命中率低 → 建议在 `_build_item_zh.py` 增加「下划线/驼峰双写」两轮反查。
2. **鞍类专项**：`Saddle` 类可直接用「`基名[:-6]` + 物种中文」规则生成，比三级链更准 → 建议对 `*Saddle` 走专用分支。
3. **`ApexDrop_*` 无本地化词条**：官方 `.po` 里没有对应条目，属结构性缺失，非匹配 bug。
4. **`_ASA` / `_Flaming` / `_Alpha` 等后缀**：应为同一物品的变体，建议前端展示时剥离后缀再匹配。

## 🎯 下一步建议

| 方案 | 动作 | 预计收益 |
|------|------|---------|
| **① 低成本高收益** | 只补 A3 + A1 + B1/B2 中「高置信」条目（约 111 条） | 覆盖率明显提升，无需人工裁决 |
| ② 中等 | 追加 A2/A4 的人工定名 | 需你逐条给中文（可用本表批注后交我批量写入） |
| ③ 整族 | ApexDrop 族暂缓、LostColony 族按批补 | 数据完整性更好 |
| ④ 先上线 | 直接带着现有 248 条跑通 UI（未命中回退英文） | 最快看到效果，后续增量补表 |

> 无论选哪条，`item_zh.json` 的**未命中回退**都必须可用（英文名 + 通用图标），否则表不全就白屏。

---

## ⚡ 附录 D｜高置信建议快照（111 条）

> 这批译名可直接写入 `item_zh.json`。回一句「**采纳高置信**」我就批量补录并重新部署；也可直接在表里删掉不要的行后回复。

| 基名 | 建议中文 | 置信 |
|------|---------|:---:|
| `AlloSaddle` | 异特龙鞍 | 高 |
| `ApexDrop_Boaratos` | 焰鬃獠猪獠牙 | 高 |
| `ApexDrop_Boaratos_Flaming` | 焰鬃獠猪燃焰獠牙 | 高 |
| `ApexDrop_CrabClaw` | 精英巨蟹鳌 | 高 |
| `ApexDrop_Neophyte` | 猎杀者之角 | 高 |
| `ArrowFlame` | 火焰箭 | 高 |
| `ArrowTranq` | 麻醉箭 | 高 |
| `ArthroSaddle` | 节胸马陆鞍 | 高 |
| `BasiloSaddle` | 龙王鲸鞍 | 高 |
| `BeaverSaddle` | 巨河狸鞍 | 高 |
| `Beer` | 啤酒 | 高 |
| `Bow` | 弓 | 高 |
| `CamelsaurusSaddle` | 驼峰龙鞍 | 高 |
| `Car_Turret_Flamethrower` | 车载火焰喷射器 | 高 |
| `Car_Wheels_Racer` | 赛车车轮 | 高 |
| `CarnoSaddle` | 食肉牛龙鞍 | 高 |
| `CeratosaurusSaddle_ASA` | 角鼻龙鞍 | 高 |
| `ChainSaw_Cursed` | 被诅咒的电锯 | 高 |
| `ChalicoSaddle` | 爪兽鞍 | 高 |
| `ChitinPants` | 甲壳素裤子 | 高 |
| `ChitinShirt` | 甲壳素上衣 | 高 |
| `ClimbPick` | 攀爬镐 | 高 |
| `CorruptedPolymer` | 腐化聚合物 | 高 |
| `Crossbow_Fab` | 制式十字弩 | 高 |
| `DeinotheriumSaddle_ASA` | 恐象鞍 | 高 |
| `DiplodocusSaddle` | 梁龙鞍 | 高 |
| `DoedSaddle` | 星尾兽鞍 | 高 |
| `FasolaSaddle` | 法索拉鳄鞍 | 高 |
| `FracturedGem` | 破碎宝石 | 高 |
| `GasBagsSaddle` | 气囊虫鞍 | 高 |
| `Gasoline_Super` | 高级汽油 | 高 |
| `GhillieBoots` | 吉利靴 | 高 |
| `GhillieGloves` | 吉利手套 | 高 |
| `GhilliePants` | 吉利裤子 | 高 |
| `GhillieShirt` | 吉利上衣 | 高 |
| `Glider` | 滑翔翼 | 高 |
| `Grenade` | 手雷 | 高 |
| `Harpoon` | 鱼叉 | 高 |
| `Harpoon_Cursed` | 被诅咒的鱼叉 | 高 |
| `HazardSuitGloves` | 防护服手套 | 高 |
| `HexCoins` | 六角币 | 高 |
| `HyaenodonSaddle` | 鬣齿兽鞍 | 高 |
| `IceBox` | 冰箱 | 高 |
| `KeratinSpike` | 角质尖刺 | 高 |
| `LostColony_AberrantSigil_Greater` | 强力异常魔符 | 高 |
| `LostColony_AberrantSigil_Prime` | 本源异常魔符 | 高 |
| `LostColony_RedElement` | 腥红元素 | 高 |
| `LostColony_RedElementShard` | 腥红元素碎片 | 高 |
| `MachinedSniper` | 制式狙击步枪 | 高 |
| `MachinedSniper_Cursed` | 被诅咒的制式狙击步枪 | 高 |
| `MammothSaddle` | 猛犸象鞍 | 高 |
| `MegalodonSaddle_Tek` | 巨齿鲨泰克鞍 | 高 |
| `MegatheriumSaddle` | 大地懒鞍 | 高 |
| `MetalBoots` | 金属靴 | 高 |
| `MetalFloor` | 金属地板 | 高 |
| `MetalGloves` | 金属手套 | 高 |
| `MetalPants` | 金属裤子 | 高 |
| `MetalShirt` | 金属上衣 | 高 |
| `MinersHelmet` | 矿工头盔 | 高 |
| `MosaSaddle` | 沧龙鞍 | 高 |
| `MosaSaddle_Platform` | 沧龙平台鞍 | 高 |
| `MothSaddle` | 沙蛾鞍 | 高 |
| `OneShotRifle` | 单发步枪 | 高 |
| `OwlSaddle` | 雪鸮鞍 | 高 |
| `PachyrhinoSaddle` | 厚鼻龙鞍 | 高 |
| `ParaSaddle` | 副栉龙鞍 | 高 |
| `ParacerSaddle_Platform` | 巨犀平台鞍 | 高 |
| `Pike_Cursed` | 被诅咒的长矛 | 高 |
| `PlesiSaddle_Platform` | 蛇颈龙平台鞍 | 高 |
| `PlesiaSaddle` | 蛇颈龙鞍 | 高 |
| `PoisonTrap` | 毒药陷阱 | 高 |
| `Polymer_Organic` | 有机聚合物 | 高 |
| `PrimalItemC4Ammo` | C4 炸弹 | 高 |
| `PrimalItemConsumableMiracleGro` | 神奇肥料 | 高 |
| `PrimalItemConsumableSoap` | 肥皂 | 高 |
| `Prod` | 电击棒 | 高 |
| `PteroSaddle` | 无齿翼龙鞍 | 高 |
| `QuetzSaddle_Platform` | 风神翼龙平台鞍 | 高 |
| `RadioactiveLanternCharge` | 放射性提灯电池 | 高 |
| `Ramp_Metal` | 金属斜坡 | 高 |
| `RaptorSaddle` | 迅猛龙鞍 | 高 |
| `RefinedTranqDart` | 精炼麻醉镖 | 高 |
| `RexSaddle_Tek` | 霸王龙泰克鞍 | 高 |
| `RhinoSaddle` | 披毛犀鞍 | 高 |
| `RockDrakeSaddle_Tek` | 岩龙泰克鞍 | 高 |
| `Rocket` | 火箭弹 | 高 |
| `SaberSaddle` | 剑齿虎鞍 | 高 |
| `ScorpionSaddle` | 帝王蝎鞍 | 高 |
| `Seed_DefensePlant` | 防御植物种子 | 高 |
| `Seed_PlantSpeciesY` | Y 类植物种子 | 高 |
| `Sickle` | 镰刀 | 高 |
| `SimpleRifleBullet` | 简易步枪子弹 | 高 |
| `SimpleShotgunBullet` | 简易霰弹枪子弹 | 高 |
| `Spear_Explosive` | 爆炸长矛 | 高 |
| `SpineyLizardSaddle` | 刺面龙鞍 | 高 |
| `SpinoSaddle` | 棘龙鞍 | 高 |
| `TapejaraSaddle` | 古神翼龙鞍 | 高 |
| `TerrorBirdSaddle` | 骇鸟鞍 | 高 |
| `ThatchFloor` | 茅草地基 | 高 |
| `ThatchRoof` | 茅草屋顶 | 高 |
| `ThylacoSaddle` | 袋狮鞍 | 高 |
| `ToadSaddle` | 巨型蟾蜍鞍 | 高 |
| `TransparentRiotShield` | 透明防暴盾牌 | 高 |
| `TriCeiling_Metal` | 金属三角天花板 | 高 |
| `TriCeiling_Thatch` | 茅草三角天花板 | 高 |
| `TriRoof_Metal` | 金属三角屋顶 | 高 |
| `TripwireC4` | 绊线 C4 | 高 |
| `TurtleSaddle` | 碳龟鞍 | 高 |
| `WeapFlamethrower` | 火焰喷射器 | 高 |
| `YutySaddle` | 羽暴龙鞍 | 高 |
| `Zipline` | 滑索 | 高 |

