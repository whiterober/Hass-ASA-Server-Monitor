# item_zh 三段表（溯源版：①已采信 / ②有出处 / ③待裁决）

> **口径**：每条中文必须来自 `ShooterGame.po` 或 `icon_zh_map.json`（禁止推断）。①②段全部可溯源；③段为拼装/近似/无出处。
> 三段互斥无遗漏：257 + 253 + 0 = **510** 基名。生成脚本 `tmp/_gen_item_3sec_v2.py`（只读）。

## 📊 总览

| 段 | 条数 | 出处口径 | 动作 |
|---|:---:|------|------|
| ① 已采信 | 257 | zhmap 英文/键、PO、PO·战利品、物种+战利品 | 已写入 `item_zh.json`（含 `zsrc`/`zev`） |
| ② 有权威出处 | 253 | zhmap·英文 / zhmap·键 / PO / PO·战利品 / zhmap·掉落 | 回「**采纳有出处**」即批量写入 |
| ③ 待裁决 | 0 | 物种+战利品 0 · PO近似 0 · 无出处 0 | 需你定名或回退英文 |
| **合计** | **510** | | |

---

## ① 已采信（257 条，按后端 kind 分组，组内按出现次数降序）

### resource（资源/材料）（73 条）

| <sub>基名</sub> | <sub>完整类名</sub> | <sub>icon</sub> | <sub>en</sub> | <sub>zh</sub> | <sub>出处</sub> | <sub>次数</sub> |
|------|------|------|----|----|------|:---:|
| <sub>`ShardRefined`</sub> | <sub>PrimalItemResource_ShardRefined</sub> | <sub>—</sub> | <sub>Unstable Element Shard</sub> | <sub>不稳定的元素碎片</sub> | <sub>人工修正</sub> | <sub>3089</sub> |
| <sub>`GigantoraptorFeather`</sub> | <sub>PrimalItemResource_GigantoraptorFeather</sub> | <sub>—</sub> | <sub>Gigantoraptor Feather</sub> | <sub>巨盗龙羽毛</sub> | <sub>zhmap·英文</sub> | <sub>1541</sub> |
| <sub>`MetalIngot`</sub> | <sub>PrimalItemResource_MetalIngot</sub> | <sub>Metal_Ingot</sub> | <sub>Metal Ingot</sub> | <sub>金属锭</sub> | <sub>zhmap·英文</sub> | <sub>1496</sub> |
| <sub>`Hide`</sub> | <sub>PrimalItemResource_Hide</sub> | <sub>Hide</sub> | <sub>Hide</sub> | <sub>兽皮</sub> | <sub>zhmap·英文</sub> | <sub>1425</sub> |
| <sub>`Gasoline`</sub> | <sub>PrimalItemResource_Gasoline</sub> | <sub>Gasoline</sub> | <sub>Gasoline</sub> | <sub>汽油</sub> | <sub>zhmap·英文</sub> | <sub>1112</sub> |
| <sub>`Wood`</sub> | <sub>PrimalItemResource_Wood</sub> | <sub>Wood</sub> | <sub>wood</sub> | <sub>木头</sub> | <sub>PO</sub> | <sub>820</sub> |
| <sub>`Chitin`</sub> | <sub>PrimalItemResource_Chitin</sub> | <sub>Chitin</sub> | <sub>Chitin</sub> | <sub>甲壳素</sub> | <sub>zhmap·英文</sub> | <sub>786</sub> |
| <sub>`ScrapMetalIngot`</sub> | <sub>PrimalItemResource_ScrapMetalIngot</sub> | <sub>ScrapMetalIngot_Icon</sub> | <sub>Scrap Metal Ingot</sub> | <sub>废金属锭</sub> | <sub>zhmap·英文</sub> | <sub>704</sub> |
| <sub>`Metal`</sub> | <sub>PrimalItemResource_Metal</sub> | <sub>—</sub> | <sub>metal</sub> | <sub>金属</sub> | <sub>zhmap·英文</sub> | <sub>699</sub> |
| <sub>`Fibers`</sub> | <sub>PrimalItemResource_Fibers</sub> | <sub>—</sub> | <sub>Fiber</sub> | <sub>纤维</sub> | <sub>zhmap·英文</sub> | <sub>697</sub> |
| <sub>`Thatch`</sub> | <sub>PrimalItemResource_Thatch</sub> | <sub>Thatch</sub> | <sub>Thatch</sub> | <sub>茅草</sub> | <sub>zhmap·英文</sub> | <sub>663</sub> |
| <sub>`Stone`</sub> | <sub>PrimalItemResource_Stone</sub> | <sub>Stone</sub> | <sub>Stone</sub> | <sub>石头</sub> | <sub>zhmap·英文</sub> | <sub>630</sub> |
| <sub>`RareFlower`</sub> | <sub>PrimalItemResource_RareFlower</sub> | <sub>Rare_Flower</sub> | <sub>rare flower</sub> | <sub>稀有花朵</sub> | <sub>PO</sub> | <sub>615</sub> |
| <sub>`Gas`</sub> | <sub>PrimalItemResource_Gas</sub> | <sub>—</sub> | <sub>Gas</sub> | <sub>瓦斯</sub> | <sub>PO</sub> | <sub>614</sub> |
| <sub>`Keratin`</sub> | <sub>PrimalItemResource_Keratin</sub> | <sub>Keratin</sub> | <sub>Keratin</sub> | <sub>角质</sub> | <sub>zhmap·英文</sub> | <sub>528</sub> |
| <sub>`ElementShard`</sub> | <sub>PrimalItemResource_ElementShard</sub> | <sub>—</sub> | <sub>Element Shard</sub> | <sub>元素碎片</sub> | <sub>PO</sub> | <sub>508</sub> |
| <sub>`Gunpowder`</sub> | <sub>PrimalItemResource_Gunpowder</sub> | <sub>Gunpowder</sub> | <sub>Gunpowder</sub> | <sub>火药</sub> | <sub>zhmap·英文</sub> | <sub>508</sub> |
| <sub>`ChitinPaste`</sub> | <sub>PrimalItemResource_ChitinPaste</sub> | <sub>—</sub> | <sub>Cementing Paste</sub> | <sub>水泥</sub> | <sub>人工修正</sub> | <sub>468</sub> |
| <sub>`Charcoal`</sub> | <sub>PrimalItemResource_Charcoal</sub> | <sub>Charcoal</sub> | <sub>Charcoal</sub> | <sub>煤炭</sub> | <sub>zhmap·英文</sub> | <sub>465</sub> |
| <sub>`Element`</sub> | <sub>PrimalItemResource_Element</sub> | <sub>Element</sub> | <sub>ELEMENT</sub> | <sub>元素</sub> | <sub>zhmap·英文</sub> | <sub>463</sub> |
| <sub>`Sparkpowder`</sub> | <sub>PrimalItemResource_Sparkpowder</sub> | <sub>Sparkpowder</sub> | <sub>Sparkpowder</sub> | <sub>引火粉</sub> | <sub>zhmap·英文</sub> | <sub>459</sub> |
| <sub>`Oil`</sub> | <sub>PrimalItemResource_Oil</sub> | <sub>—</sub> | <sub> Oil</sub> | <sub>油</sub> | <sub>zhmap·英文</sub> | <sub>394</sub> |
| <sub>`Flint`</sub> | <sub>PrimalItemResource_Flint</sub> | <sub>Flint</sub> | <sub>Flint</sub> | <sub>燧石</sub> | <sub>zhmap·英文</sub> | <sub>393</sub> |
| <sub>`ElementDust`</sub> | <sub>PrimalItemResource_ElementDust</sub> | <sub>ElementDust_Icon</sub> | <sub>Element Dust</sub> | <sub>元素粉尘</sub> | <sub>zhmap·英文</sub> | <sub>317</sub> |
| <sub>`Pelt`</sub> | <sub>PrimalItemResource_Pelt</sub> | <sub>Pelt</sub> | <sub>Pelt</sub> | <sub>毛皮</sub> | <sub>zhmap·英文</sub> | <sub>287</sub> |
| <sub>`AnglerGel`</sub> | <sub>PrimalItemResource_AnglerGel</sub> | <sub>AnglerGel</sub> | <sub>AnglerGel</sub> | <sub>鮟鱇鱼油</sub> | <sub>zhmap·英文</sub> | <sub>280</sub> |
| <sub>`RareMushroom`</sub> | <sub>PrimalItemResource_RareMushroom</sub> | <sub>—</sub> | <sub>rare mushroom</sub> | <sub>稀有蘑菇</sub> | <sub>PO</sub> | <sub>272</sub> |
| <sub>`MetalIngot_FromMegaForge`</sub> | <sub>PrimalItemResource_MetalIngot_FromMegaForge</sub> | <sub>—</sub> | <sub>Metal Ingot</sub> | <sub>金属锭</sub> | <sub>PO词集包含</sub> | <sub>260</sub> |
| <sub>`Crystal`</sub> | <sub>PrimalItemResource_Crystal</sub> | <sub>Crystal</sub> | <sub>Crystal</sub> | <sub>水晶</sub> | <sub>zhmap·英文</sub> | <sub>221</sub> |
| <sub>`Sap`</sub> | <sub>PrimalItemResource_Sap</sub> | <sub>Sap</sub> | <sub>Sap</sub> | <sub>树脂</sub> | <sub>zhmap·英文</sub> | <sub>200</sub> |
| <sub>`Silicon`</sub> | <sub>PrimalItemResource_Silicon</sub> | <sub>Silicon_Icon</sub> | <sub>Silica Pearls</sub> | <sub>含硅珍珠</sub> | <sub>人工修正</sub> | <sub>193</sub> |
| <sub>`Propellant`</sub> | <sub>PrimalItemResource_Propellant</sub> | <sub>Propellant_Icon</sub> | <sub>Propellant</sub> | <sub>燃烧剂</sub> | <sub>zhmap·英文</sub> | <sub>159</sub> |
| <sub>`Electronics`</sub> | <sub>PrimalItemResource_Electronics</sub> | <sub>Electronic_Icon</sub> | <sub>Electronics</sub> | <sub>电路元件</sub> | <sub>zhmap·英文</sub> | <sub>154</sub> |
| <sub>`Clay`</sub> | <sub>PrimalItemResource_Clay</sub> | <sub>Clay_Icon</sub> | <sub>Clay</sub> | <sub>黏土</sub> | <sub>zhmap·英文</sub> | <sub>138</sub> |
| <sub>`RareDrop_CorruptHeart`</sub> | <sub>PrimalItemResource_RareDrop_CorruptHeart</sub> | <sub>—</sub> | <sub>Corrupt Heart</sub> | <sub>腐化心脏</sub> | <sub>人工修正</sub> | <sub>128</sub> |
| <sub>`PeltOrHair`</sub> | <sub>PrimalItemResource_PeltOrHair</sub> | <sub>Pelt</sub> | <sub>Pelt, Hair, or Wool</sub> | <sub>毛皮、头发或羊毛</sub> | <sub>人工修正</sub> | <sub>120</sub> |
| <sub>`Silk`</sub> | <sub>PrimalItemResource_Silk</sub> | <sub>Silk_Icon</sub> | <sub>Silk</sub> | <sub>蚕丝</sub> | <sub>zhmap·英文</sub> | <sub>119</sub> |
| <sub>`PreservingSalt`</sub> | <sub>PrimalItemResource_PreservingSalt</sub> | <sub>PreservingSalt_Icon</sub> | <sub>Preserving Salt</sub> | <sub>防腐盐</sub> | <sub>zhmap·英文</sub> | <sub>116</sub> |
| <sub>`Polymer`</sub> | <sub>PrimalItemResource_Polymer</sub> | <sub>Polymer</sub> | <sub>Polymer</sub> | <sub>聚合物</sub> | <sub>zhmap·英文</sub> | <sub>112</sub> |
| <sub>`Obsidian`</sub> | <sub>PrimalItemResource_Obsidian</sub> | <sub>Obsidian</sub> | <sub>Obsidian</sub> | <sub>黑曜石</sub> | <sub>zhmap·英文</sub> | <sub>108</sub> |
| <sub>`Sulfur`</sub> | <sub>PrimalItemResource_Sulfur</sub> | <sub>Sulfur_Icon</sub> | <sub>Sulfur</sub> | <sub>硫磺</sub> | <sub>zhmap·英文</sub> | <sub>107</sub> |
| <sub>`SubstrateAbsorbent`</sub> | <sub>PrimalItemResource_SubstrateAbsorbent</sub> | <sub>—</sub> | <sub>Absorbent Substrate</sub> | <sub>吸附剂</sub> | <sub>wiki英文名→PO</sub> | <sub>102</sub> |
| <sub>`ElementPowerNode`</sub> | <sub>PrimalItemResource_ElementPowerNode</sub> | <sub>—</sub> | <sub>Element</sub> | <sub>元素矿脉</sub> | <sub>PO词集包含</sub> | <sub>101</sub> |
| <sub>`ApexDrop_Megalania`</sub> | <sub>PrimalItemResource_ApexDrop_Megalania</sub> | <sub>ApexDropMegalania_Icon</sub> | <sub>Megalania</sub> | <sub>古巨蜥毒素</sub> | <sub>人工修正</sub> | <sub>70</sub> |
| <sub>`CommonMushroom`</sub> | <sub>PrimalItemResource_CommonMushroom</sub> | <sub>Common_Mushroom</sub> | <sub>Common Mushroom</sub> | <sub>普通蘑菇</sub> | <sub>zhmap·英文</sub> | <sub>69</sub> |
| <sub>`ElementDustFromElement`</sub> | <sub>PrimalItemResource_ElementDustFromElement</sub> | <sub>—</sub> | <sub>Element Dust</sub> | <sub>元素粉尘</sub> | <sub>PO词集包含</sub> | <sub>66</sub> |
| <sub>`ElementDustFromShards`</sub> | <sub>PrimalItemResource_ElementDustFromShards</sub> | <sub>—</sub> | <sub>Element Dust</sub> | <sub>磨制的元素粉尘</sub> | <sub>wiki英文名→PO</sub> | <sub>66</sub> |
| <sub>`ElementRefined`</sub> | <sub>PrimalItemResource_ElementRefined</sub> | <sub>—</sub> | <sub>Unstable Element</sub> | <sub>不稳定的能量元素</sub> | <sub>人工修正</sub> | <sub>66</sub> |
| <sub>`Sand`</sub> | <sub>PrimalItemResource_Sand</sub> | <sub>Sand_Icon</sub> | <sub>Sand</sub> | <sub>沙</sub> | <sub>zhmap·英文</sub> | <sub>64</sub> |
| <sub>`ApexDrop_Megalodon`</sub> | <sub>PrimalItemResource_ApexDrop_Megalodon</sub> | <sub>ApexDrop_Megalodon_Icon</sub> | <sub>Megalodon</sub> | <sub>巨齿鲨颌骨标本</sub> | <sub>PO·战利品条目</sub> | <sub>60</sub> |
| <sub>`Gasoline_GasCrafted`</sub> | <sub>PrimalItemResource_Gasoline_GasCrafted</sub> | <sub>—</sub> | <sub>Gasoline (Gas-Crafted)</sub> | <sub>瓦斯油</sub> | <sub>PO</sub> | <sub>60</sub> |
| <sub>`BlackPearl`</sub> | <sub>PrimalItemResource_BlackPearl</sub> | <sub>Black_Pearl</sub> | <sub>Black Pearl</sub> | <sub>黑珍珠</sub> | <sub>zhmap·英文</sub> | <sub>57</sub> |
| <sub>`ApexDrop_Rex`</sub> | <sub>PrimalItemResource_ApexDrop_Rex</sub> | <sub>ApexDrop_Rex_Icon</sub> | <sub>Skeletal Rex</sub> | <sub>精英霸王龙战利品</sub> | <sub>zhmap·掉落键</sub> | <sub>45</sub> |
| <sub>`ElementOre`</sub> | <sub>PrimalItemResource_ElementOre</sub> | <sub>—</sub> | <sub>Element Ore</sub> | <sub>元素矿石</sub> | <sub>PO</sub> | <sub>42</sub> |
| <sub>`FungalWood`</sub> | <sub>PrimalItemResource_FungalWood</sub> | <sub>—</sub> | <sub>Fungal Wood</sub> | <sub>真菌木头</sub> | <sub>PO</sub> | <sub>34</sub> |
| <sub>`ScrapMetal`</sub> | <sub>PrimalItemResource_ScrapMetal</sub> | <sub>ScrapMetal_Icon</sub> | <sub>Scrap Metal</sub> | <sub>废金属</sub> | <sub>zhmap·英文</sub> | <sub>31</sub> |
| <sub>`CondensedGas`</sub> | <sub>PrimalItemResource_CondensedGas</sub> | <sub>CondensedGas_icon</sub> | <sub>Condensed Gas</sub> | <sub>冷凝瓦斯</sub> | <sub>zhmap·英文</sub> | <sub>29</sub> |
| <sub>`ApexDrop_Boa`</sub> | <sub>PrimalItemResource_ApexDrop_Boa</sub> | <sub>ApexDropBoa_Icon</sub> | <sub>Boaratos</sub> | <sub>焰鬃獠猪獠牙</sub> | <sub>PO·物种+部位</sub> | <sub>28</sub> |
| <sub>`ApexDrop_Spino`</sub> | <sub>PrimalItemResource_ApexDrop_Spino</sub> | <sub>ApexDropSpino_Icon</sub> | <sub>Spino</sub> | <sub>棘龙背鳍</sub> | <sub>PO·物种+部位</sub> | <sub>28</sub> |
| <sub>`ApexDrop_Theriz`</sub> | <sub>PrimalItemResource_ApexDrop_Theriz</sub> | <sub>ApexDropTherizino_Icon</sub> | <sub>Apex Drop_Theriz</sub> | <sub>镰刀龙爪子</sub> | <sub>PO·物种+部位</sub> | <sub>22</sub> |
| <sub>`SquidOil`</sub> | <sub>PrimalItemResource_SquidOil</sub> | <sub>SquidOil_Icon</sub> | <sub>Squid Oil</sub> | <sub>巨鱿油</sub> | <sub>PO</sub> | <sub>21</sub> |
| <sub>`Wool`</sub> | <sub>PrimalItemResource_Wool</sub> | <sub>Wool</sub> | <sub>Wool</sub> | <sub>羊毛</sub> | <sub>zhmap·英文</sub> | <sub>18</sub> |
| <sub>`AmmoniteBlood`</sub> | <sub>PrimalItemResource_AmmoniteBlood</sub> | <sub>—</sub> | <sub>Ammonite</sub> | <sub>菊石</sub> | <sub>zhmap键桥接</sub> | <sub>8</sub> |
| <sub>`CorruptedWood`</sub> | <sub>PrimalItemResource_CorruptedWood</sub> | <sub>—</sub> | <sub>Corrupted Wood</sub> | <sub>腐化木头</sub> | <sub>PO</sub> | <sub>8</sub> |
| <sub>`RawSalt`</sub> | <sub>PrimalItemResource_RawSalt</sub> | <sub>RawSalt_Icon</sub> | <sub>Raw Salt</sub> | <sub>生盐</sub> | <sub>zhmap·英文</sub> | <sub>8</sub> |
| <sub>`LeechBlood`</sub> | <sub>PrimalItemResource_LeechBlood</sub> | <sub>Leech_Blood</sub> | <sub>Leech Blood</sub> | <sub>水蛭血</sub> | <sub>zhmap·英文</sub> | <sub>7</sub> |
| <sub>`RareFlower_ShoulderDragonCraftable`</sub> | <sub>PrimalItemResource_RareFlower_ShoulderDragonCraftable</sub> | <sub>—</sub> | <sub>Rare</sub> | <sub>稀有花朵</sub> | <sub>PO词集包含</sub> | <sub>6</sub> |
| <sub>`LuminaScale`</sub> | <sub>PrimalItemResource_LuminaScale</sub> | <sub>—</sub> | <sub>Lumina Scale</sub> | <sub>皎光仔鳞片</sub> | <sub>人工修正</sub> | <sub>5</sub> |
| <sub>`Silicate`</sub> | <sub>PrimalItemResource_Silicate</sub> | <sub>Silicon_Icon</sub> | <sub>Silicate</sub> | <sub>硅酸盐</sub> | <sub>zhmap·英文</sub> | <sub>5</sub> |
| <sub>`ElementRefinedFromRedElement`</sub> | <sub>PrimalItemResource_ElementRefinedFromRedElement</sub> | <sub>—</sub> | <sub>Unstable Red Element</sub> | <sub>不稳定的腥红能量元素</sub> | <sub>人工修正</sub> | <sub>4</sub> |
| <sub>`TurtleShell`</sub> | <sub>PrimalItemResource_TurtleShell</sub> | <sub>—</sub> | <sub>Shell Fragment</sub> | <sub>甲壳碎片</sub> | <sub>人工修正</sub> | <sub>3</sub> |
| <sub>`Resin`</sub> | <sub>PrimalItemResource_Resin</sub> | <sub>—</sub> | <sub>Resin</sub> | <sub>黏脂</sub> | <sub>zhmap·英文</sub> | <sub>2</sub> |
| <sub>`UmbraScale`</sub> | <sub>PrimalItemResource_UmbraScale</sub> | <sub>—</sub> | <sub>Umbra Scale</sub> | <sub>幽影仔鳞片</sub> | <sub>人工修正</sub> | <sub>0</sub> |

### ammo（弹药/投掷物）（20 条）

| <sub>基名</sub> | <sub>完整类名</sub> | <sub>icon</sub> | <sub>en</sub> | <sub>zh</sub> | <sub>出处</sub> | <sub>次数</sub> |
|------|------|------|----|----|------|:---:|
| <sub>`AdvancedRifleBullet`</sub> | <sub>PrimalItemAmmo_AdvancedRifleBullet</sub> | <sub>—</sub> | <sub>Advanced Rifle Bullet</sub> | <sub>高级步枪子弹</sub> | <sub>PO</sub> | <sub>687</sub> |
| <sub>`AdvancedBullet`</sub> | <sub>PrimalItemAmmo_AdvancedBullet</sub> | <sub>—</sub> | <sub>Advanced Bullet</sub> | <sub>高级子弹</sub> | <sub>PO</sub> | <sub>263</sub> |
| <sub>`BallistaArrow`</sub> | <sub>PrimalItemAmmo_BallistaArrow</sub> | <sub>BallistaArrow_Icon</sub> | <sub>Spear Bolt</sub> | <sub>弩箭</sub> | <sub>人工修正</sub> | <sub>255</sub> |
| <sub>`ArrowStone`</sub> | <sub>PrimalItemAmmo_ArrowStone</sub> | <sub>Arrow_icon</sub> | <sub>Stone Arrow</sub> | <sub>石箭</sub> | <sub>wiki英文名→PO</sub> | <sub>254</sub> |
| <sub>`TranqDart`</sub> | <sub>PrimalItemAmmo_TranqDart</sub> | <sub>TranqDart3_Icon</sub> | <sub>Tranquilizer Dart</sub> | <sub>麻醉镖</sub> | <sub>人工修正</sub> | <sub>239</sub> |
| <sub>`CannonBall`</sub> | <sub>PrimalItemAmmo_CannonBall</sub> | <sub>Cannon_Ball</sub> | <sub>Cannon Ball</sub> | <sub>火炮弹丸</sub> | <sub>zhmap·英文</sub> | <sub>238</sub> |
| <sub>`SimpleBullet`</sub> | <sub>PrimalItemAmmo_SimpleBullet</sub> | <sub>Simple</sub> | <sub>Simple Bullet</sub> | <sub>简易子弹</sub> | <sub>PO</sub> | <sub>234</sub> |
| <sub>`GrapplingHook`</sub> | <sub>PrimalItemAmmo_GrapplingHook</sub> | <sub>Grappling_Hook</sub> | <sub>Grappling Hook</sub> | <sub>爪钩</sub> | <sub>zhmap·英文</sub> | <sub>213</sub> |
| <sub>`TranqSpearBolt`</sub> | <sub>PrimalItemAmmo_TranqSpearBolt</sub> | <sub>TranqSpearBolt_Icon</sub> | <sub>Spear Bolt</sub> | <sub>麻醉弩箭</sub> | <sub>PO</sub> | <sub>196</sub> |
| <sub>`ChainBola`</sub> | <sub>PrimalItemAmmo_ChainBola</sub> | <sub>Chain_Bola</sub> | <sub>Chain Bola</sub> | <sub>流星锁链</sub> | <sub>zhmap·英文</sub> | <sub>192</sub> |
| <sub>`CannonBall_ToF_Corrosive`</sub> | <sub>PrimalItemAmmo_CannonBall_ToF_Corrosive</sub> | <sub>—</sub> | <sub>Corrosive Cannon Ball</sub> | <sub>腐蚀炮弹</sub> | <sub>人工修正</sub> | <sub>153</sub> |
| <sub>`CannonBall_ToF_Incendiary`</sub> | <sub>PrimalItemAmmo_CannonBall_ToF_Incendiary</sub> | <sub>—</sub> | <sub>Incendiary Cannon Ball</sub> | <sub>燃烧炮弹</sub> | <sub>人工修正</sub> | <sub>153</sub> |
| <sub>`CannonBall_ToF_Reinforced`</sub> | <sub>PrimalItemAmmo_CannonBall_ToF_Reinforced</sub> | <sub>—</sub> | <sub>Reinforced Cannon Ball</sub> | <sub>火炮弹丸</sub> | <sub>人工修正</sub> | <sub>153</sub> |
| <sub>`AdvancedSniperBullet`</sub> | <sub>PrimalItemAmmo_AdvancedSniperBullet</sub> | <sub>Advanced_Sniper_Bullet</sub> | <sub>Advanced Sniper Bullet</sub> | <sub>制式狙击步枪子弹</sub> | <sub>zhmap·英文</sub> | <sub>95</sub> |
| <sub>`CompoundBowArrow`</sub> | <sub>PrimalItemAmmo_CompoundBowArrow</sub> | <sub>Compound_Bow</sub> | <sub>Compound Bow</sub> | <sub>金属箭</sub> | <sub>wiki英文名→PO</sub> | <sub>95</sub> |
| <sub>`RocketHomingMissile`</sub> | <sub>PrimalItemAmmo_RocketHomingMissile</sub> | <sub>Rocket_Homing_Missile</sub> | <sub>Rocket Homing Missile</sub> | <sub>制导火箭弹</sub> | <sub>zhmap·英文</sub> | <sub>86</sub> |
| <sub>`Flamethrower`</sub> | <sub>PrimalItemAmmo_Flamethrower</sub> | <sub>Flamethrower</sub> | <sub>Flamethrower</sub> | <sub>火焰喷射器</sub> | <sub>zhmap·英文</sub> | <sub>79</sub> |
| <sub>`CannonShell`</sub> | <sub>PrimalItemAmmo_CannonShell</sub> | <sub>—</sub> | <sub>Cannon Shell</sub> | <sub>加农炮弹</sub> | <sub>PO</sub> | <sub>57</sub> |
| <sub>`RocketPod`</sub> | <sub>PrimalItemAmmo_RocketPod</sub> | <sub>—</sub> | <sub>Rocket Pod</sub> | <sub>火箭弹仓</sub> | <sub>PO</sub> | <sub>57</sub> |
| <sub>`Boulder`</sub> | <sub>PrimalItemAmmo_Boulder</sub> | <sub>Boulder</sub> | <sub>Boulder</sub> | <sub>巨石</sub> | <sub>zhmap·英文</sub> | <sub>2</sub> |

### structure（建筑构件）（23 条）

| <sub>基名</sub> | <sub>完整类名</sub> | <sub>icon</sub> | <sub>en</sub> | <sub>zh</sub> | <sub>出处</sub> | <sub>次数</sub> |
|------|------|------|----|----|------|:---:|
| <sub>`BearTrap_Large`</sub> | <sub>PrimalItemStructure_BearTrap_Large</sub> | <sub>Bear_Trap</sub> | <sub>Bear Trap</sub> | <sub>捕兽夹</sub> | <sub>zhmap·英文</sub> | <sub>1</sub> |
| <sub>`CryoFridge`</sub> | <sub>PrimalItemStructure_CryoFridge</sub> | <sub>Cryofridge</sub> | <sub>Cryofridge</sub> | <sub>低温冰箱</sub> | <sub>zhmap·英文</sub> | <sub>1</sub> |
| <sub>`DedicatedStorage`</sub> | <sub>PrimalItemStructure_DedicatedStorage</sub> | <sub>—</sub> | <sub>Dedicated Storage</sub> | <sub>泰克专用储物箱</sub> | <sub>zhmap·英文</sub> | <sub>1</sub> |
| <sub>`ElevatorPlatformMedium`</sub> | <sub>PrimalItemStructure_ElevatorPlatformMedium</sub> | <sub>ElevatorPlatform_Icon</sub> | <sub>Elevator Platform</sub> | <sub>电梯平台</sub> | <sub>PO词集包含</sub> | <sub>1</sub> |
| <sub>`ElevatorTrackBase`</sub> | <sub>PrimalItemStructure_ElevatorTrackBase</sub> | <sub>Elevator_Track</sub> | <sub>Elevator Track</sub> | <sub>电梯轨道</sub> | <sub>wiki英文名→PO</sub> | <sub>1</sub> |
| <sub>`MetalCeiling`</sub> | <sub>PrimalItemStructure_MetalCeiling</sub> | <sub>—</sub> | <sub>Metal Ceiling</sub> | <sub>金属天花板</sub> | <sub>zhmap·英文</sub> | <sub>1</sub> |
| <sub>`MetalDoor`</sub> | <sub>PrimalItemStructure_MetalDoor</sub> | <sub>MetalDoorway_Icon</sub> | <sub>Metal Door</sub> | <sub>金属门</sub> | <sub>zhmap·英文</sub> | <sub>1</sub> |
| <sub>`MetalGate`</sub> | <sub>PrimalItemStructure_MetalGate</sub> | <sub>—</sub> | <sub>Metal Gate</sub> | <sub>金属恐龙门</sub> | <sub>zhmap·英文</sub> | <sub>1</sub> |
| <sub>`MetalGateframe`</sub> | <sub>PrimalItemStructure_MetalGateframe</sub> | <sub>MetalGateFrame_Icon</sub> | <sub>Metal Gate</sub> | <sub>金属恐龙门</sub> | <sub>zhmap·键</sub> | <sub>1</sub> |
| <sub>`MetalGateframe_Large`</sub> | <sub>PrimalItemStructure_MetalGateframe_Large</sub> | <sub>MetalGateFrame_Icon</sub> | <sub>Metal Gate</sub> | <sub>金属恐龙门</sub> | <sub>zhmap·键</sub> | <sub>1</sub> |
| <sub>`MetalPillar`</sub> | <sub>PrimalItemStructure_MetalPillar</sub> | <sub>—</sub> | <sub>Metal Pillar</sub> | <sub>金属柱子</sub> | <sub>zhmap·英文</sub> | <sub>1</sub> |
| <sub>`MetalRailing`</sub> | <sub>PrimalItemStructure_MetalRailing</sub> | <sub>—</sub> | <sub>Metal Railing</sub> | <sub>金属栏杆</sub> | <sub>PO</sub> | <sub>1</sub> |
| <sub>`MetalWall`</sub> | <sub>PrimalItemStructure_MetalWall</sub> | <sub>—</sub> | <sub>Metal Wall</sub> | <sub>金属墙</sub> | <sub>PO</sub> | <sub>1</sub> |
| <sub>`StoneGate`</sub> | <sub>PrimalItemStructure_StoneGate</sub> | <sub>—</sub> | <sub>Stone Gateway</sub> | <sub>石制恐龙门框</sub> | <sub>人工修正</sub> | <sub>1</sub> |
| <sub>`StorageBox_Huge`</sub> | <sub>PrimalItemStructure_StorageBox_Huge</sub> | <sub>—</sub> | <sub>Vault</sub> | <sub>保险柜</sub> | <sub>人工修正</sub> | <sub>1</sub> |
| <sub>`TekGateframe_Large`</sub> | <sub>PrimalItemStructure_TekGateframe_Large</sub> | <sub>TEKGateFrame_Icon</sub> | <sub>Behemoth Tek Gateway</sub> | <sub>泰克巨兽恐龙门框</sub> | <sub>人工修正</sub> | <sub>1</sub> |
| <sub>`TekPillar`</sub> | <sub>PrimalItemStructure_TekPillar</sub> | <sub>Tek_Pillar</sub> | <sub>Tek Pillar</sub> | <sub>泰克柱子</sub> | <sub>zhmap·英文</sub> | <sub>1</sub> |
| <sub>`TekWall`</sub> | <sub>PrimalItemStructure_TekWall</sub> | <sub>Tek_Wall</sub> | <sub>Tek Wall</sub> | <sub>泰克墙</sub> | <sub>PO</sub> | <sub>1</sub> |
| <sub>`ThatchCeiling`</sub> | <sub>PrimalItemStructure_ThatchCeiling</sub> | <sub>—</sub> | <sub>Thatch Ceiling</sub> | <sub>茅草屋顶</sub> | <sub>zhmap·英文</sub> | <sub>1</sub> |
| <sub>`ThatchWall`</sub> | <sub>PrimalItemStructure_ThatchWall</sub> | <sub>Thatch</sub> | <sub>Thatch Wall</sub> | <sub>茅草墙</sub> | <sub>PO</sub> | <sub>1</sub> |
| <sub>`WoodCeiling`</sub> | <sub>PrimalItemStructure_WoodCeiling</sub> | <sub>WoodCeiling_Icon</sub> | <sub>Wood Ceiling</sub> | <sub>木制天花板</sub> | <sub>PO</sub> | <sub>1</sub> |
| <sub>`WoodRailing`</sub> | <sub>PrimalItemStructure_WoodRailing</sub> | <sub>WoodRailing_Icon</sub> | <sub>Wood Railing</sub> | <sub>木制栏杆</sub> | <sub>PO</sub> | <sub>1</sub> |
| <sub>`WoodWall_Sloped_Left`</sub> | <sub>PrimalItemStructure_WoodWall_Sloped_Left</sub> | <sub>—</sub> | <sub>Wood</sub> | <sub>木制左斜墙</sub> | <sub>wiki英文名→PO</sub> | <sub>1</sub> |

### consumable（消耗品）（3 条）

| <sub>基名</sub> | <sub>完整类名</sub> | <sub>icon</sub> | <sub>en</sub> | <sub>zh</sub> | <sub>出处</sub> | <sub>次数</sub> |
|------|------|------|----|----|------|:---:|
| <sub>`Narcotic`</sub> | <sub>PrimalItemConsumable_Narcotic</sub> | <sub>Narcotic</sub> | <sub>Narcotic</sub> | <sub>麻醉药</sub> | <sub>zhmap·英文</sub> | <sub>6</sub> |
| <sub>`Stimulant`</sub> | <sub>PrimalItemConsumable_Stimulant</sub> | <sub>Stimulant</sub> | <sub>Stimulant</sub> | <sub>兴奋剂</sub> | <sub>zhmap·英文</sub> | <sub>5</sub> |
| <sub>`BeerJar`</sub> | <sub>PrimalItemConsumable_BeerJar</sub> | <sub>Beer_Jar</sub> | <sub>Beer Jar</sub> | <sub>扎啤</sub> | <sub>zhmap·英文</sub> | <sub>1</sub> |

### saddle（鞍具）（43 条）

| <sub>基名</sub> | <sub>完整类名</sub> | <sub>icon</sub> | <sub>en</sub> | <sub>zh</sub> | <sub>出处</sub> | <sub>次数</sub> |
|------|------|------|----|----|------|:---:|
| <sub>`DaeodonSaddle`</sub> | <sub>PrimalItemArmor_DaeodonSaddle</sub> | <sub>DaeodonSaddle</sub> | <sub>Daeodon Saddle</sub> | <sub>凶齿豨鞍</sub> | <sub>zhmap·英文</sub> | <sub>38</sub> |
| <sub>`IguanodonSaddle`</sub> | <sub>PrimalItemArmor_IguanodonSaddle</sub> | <sub>IguanodonSaddle</sub> | <sub>Iguanodon Saddle</sub> | <sub>禽龙鞍</sub> | <sub>zhmap·英文</sub> | <sub>36</sub> |
| <sub>`MegalosaurusSaddle`</sub> | <sub>PrimalItemArmor_MegalosaurusSaddle</sub> | <sub>MegalosaurusSaddle</sub> | <sub>Megalosaurus Saddle</sub> | <sub>巨齿龙鞍</sub> | <sub>zhmap·英文</sub> | <sub>35</sub> |
| <sub>`Paracer_Saddle`</sub> | <sub>PrimalItemArmor_Paracer_Saddle</sub> | <sub>ParacerSaddle</sub> | <sub>Paracer Saddle</sub> | <sub>巨犀鞍</sub> | <sub>zhmap·英文</sub> | <sub>34</sub> |
| <sub>`MegalaniaSaddle`</sub> | <sub>PrimalItemArmor_MegalaniaSaddle</sub> | <sub>MegalaniaSaddle</sub> | <sub>Megalania Saddle</sub> | <sub>古巨蜥鞍</sub> | <sub>zhmap·英文</sub> | <sub>32</sub> |
| <sub>`ArgentavisSaddle`</sub> | <sub>PrimalItemArmor_ArgentavisSaddle</sub> | <sub>ArgentavisSaddle</sub> | <sub>Argentavis Saddle</sub> | <sub>阿根廷鹫鞍</sub> | <sub>zhmap·英文</sub> | <sub>31</sub> |
| <sub>`AnkyloSaddle`</sub> | <sub>PrimalItemArmor_AnkyloSaddle</sub> | <sub>AnkyloSaddle</sub> | <sub>Ankylo Saddle</sub> | <sub>甲龙鞍</sub> | <sub>zhmap·英文</sub> | <sub>28</sub> |
| <sub>`BaryonyxSaddle`</sub> | <sub>PrimalItemArmor_BaryonyxSaddle</sub> | <sub>BaryonyxSaddle</sub> | <sub>Baryonyx Saddle</sub> | <sub>重爪龙鞍</sub> | <sub>zhmap·英文</sub> | <sub>27</sub> |
| <sub>`TherizinosaurusSaddle`</sub> | <sub>PrimalItemArmor_TherizinosaurusSaddle</sub> | <sub>TherizinosaurusSaddle</sub> | <sub>Therizinosaurus Saddle</sub> | <sub>镰刀龙鞍</sub> | <sub>zhmap·英文</sub> | <sub>27</sub> |
| <sub>`DireBearSaddle`</sub> | <sub>PrimalItemArmor_DireBearSaddle</sub> | <sub>Dire_Bear_Saddle</sub> | <sub>Dire Bear Saddle</sub> | <sub>恐熊鞍</sub> | <sub>zhmap·英文</sub> | <sub>25</sub> |
| <sub>`GigantoraptorSaddle`</sub> | <sub>PrimalItemArmor_GigantoraptorSaddle</sub> | <sub>HUD_GigantoraptorSaddle_Icon</sub> | <sub>Gigantoraptor Saddle</sub> | <sub>巨盗龙鞍</sub> | <sub>zhmap·英文</sub> | <sub>25</sub> |
| <sub>`KaprosuchusSaddle`</sub> | <sub>PrimalItemArmor_KaprosuchusSaddle</sub> | <sub>KaprosuchusSaddle</sub> | <sub>Kaprosuchus Saddle</sub> | <sub>猪鳄鞍</sub> | <sub>zhmap·英文</sub> | <sub>22</sub> |
| <sub>`SarcoSaddle`</sub> | <sub>PrimalItemArmor_SarcoSaddle</sub> | <sub>Sarco_Saddle</sub> | <sub>Sarco Saddle</sub> | <sub>帝鳄鞍</sub> | <sub>zhmap·英文</sub> | <sub>22</sub> |
| <sub>`TrikeSaddle`</sub> | <sub>PrimalItemArmor_TrikeSaddle</sub> | <sub>TrikeSaddle</sub> | <sub>Trike Saddle</sub> | <sub>三角龙鞍</sub> | <sub>zhmap·英文</sub> | <sub>22</sub> |
| <sub>`DunkleosteusSaddle`</sub> | <sub>PrimalItemArmor_DunkleosteusSaddle</sub> | <sub>Dunkleosteus_Saddle</sub> | <sub>Dunkleosteus Saddle</sub> | <sub>邓氏鱼鞍</sub> | <sub>zhmap·英文</sub> | <sub>21</sub> |
| <sub>`EquusSaddle`</sub> | <sub>PrimalItemArmor_EquusSaddle</sub> | <sub>Equus_Saddle</sub> | <sub>Equus Saddle</sub> | <sub>庞马鞍</sub> | <sub>zhmap·英文</sub> | <sub>21</sub> |
| <sub>`QuetzSaddle`</sub> | <sub>PrimalItemArmor_QuetzSaddle</sub> | <sub>Quetz_Saddle</sub> | <sub>Quetz Saddle</sub> | <sub>风神翼龙鞍</sub> | <sub>zhmap·英文</sub> | <sub>20</sub> |
| <sub>`StegoSaddle`</sub> | <sub>PrimalItemArmor_StegoSaddle</sub> | <sub>—</sub> | <sub>Stego Saddle</sub> | <sub>剑龙鞍</sub> | <sub>zhmap·英文</sub> | <sub>20</sub> |
| <sub>`RexSaddle`</sub> | <sub>PrimalItemArmor_RexSaddle</sub> | <sub>RexSaddle</sub> | <sub>Rex Saddle</sub> | <sub>霸王龙鞍</sub> | <sub>zhmap·英文</sub> | <sub>18</sub> |
| <sub>`MegalodonSaddle`</sub> | <sub>PrimalItemArmor_MegalodonSaddle</sub> | <sub>MegalodonSaddle</sub> | <sub>Megalodon Saddle</sub> | <sub>巨齿鲨鞍</sub> | <sub>zhmap·英文</sub> | <sub>15</sub> |
| <sub>`TusoSaddle`</sub> | <sub>PrimalItemArmor_TusoSaddle</sub> | <sub>TusoSaddle</sub> | <sub>Tusoteuthis Saddle</sub> | <sub>托斯特巨鱿鞍</sub> | <sub>zhmap·键</sub> | <sub>13</sub> |
| <sub>`AcroSaddle`</sub> | <sub>PrimalItemArmor_AcroSaddle</sub> | <sub>Acro_Saddle</sub> | <sub>Acro Saddle</sub> | <sub>高棘龙鞍</sub> | <sub>zhmap·英文</sub> | <sub>12</sub> |
| <sub>`MantisSaddle`</sub> | <sub>PrimalItemArmor_MantisSaddle</sub> | <sub>MantisSaddle_Icon</sub> | <sub>Mantis Saddle</sub> | <sub>螳螂鞍</sub> | <sub>zhmap·英文</sub> | <sub>12</sub> |
| <sub>`CarchaSaddle`</sub> | <sub>PrimalItemArmor_CarchaSaddle</sub> | <sub>—</sub> | <sub>Carcha Saddle</sub> | <sub>鲨齿龙鞍</sub> | <sub>PO</sub> | <sub>11</sub> |
| <sub>`MantaSaddle`</sub> | <sub>PrimalItemArmor_MantaSaddle</sub> | <sub>Manta_Saddle</sub> | <sub>Manta Saddle</sub> | <sub>蝠鲼鞍</sub> | <sub>zhmap·英文</sub> | <sub>10</sub> |
| <sub>`ProcoptodonSaddle`</sub> | <sub>PrimalItemArmor_ProcoptodonSaddle</sub> | <sub>Procoptodon_Saddle</sub> | <sub>Procoptodon Saddle</sub> | <sub>短面袋鼠鞍</sub> | <sub>zhmap·英文</sub> | <sub>10</sub> |
| <sub>`RockGolemSaddle`</sub> | <sub>PrimalItemArmor_RockGolemSaddle</sub> | <sub>RockGolemSaddle_Icon</sub> | <sub>Rock Golem Saddle</sub> | <sub>岩石巨人鞍</sub> | <sub>zhmap·英文</sub> | <sub>10</sub> |
| <sub>`BisonSaddle`</sub> | <sub>PrimalItemArmor_BisonSaddle</sub> | <sub>Bison_Saddle</sub> | <sub>Bison Saddle</sub> | <sub>野牛鞍</sub> | <sub>zhmap·英文</sub> | <sub>7</sub> |
| <sub>`PachySaddle`</sub> | <sub>PrimalItemArmor_PachySaddle</sub> | <sub>Pachy_Saddle</sub> | <sub>Pachy Saddle</sub> | <sub>肿头龙鞍</sub> | <sub>zhmap·英文</sub> | <sub>7</sub> |
| <sub>`PhiomiaSaddle`</sub> | <sub>PrimalItemArmor_PhiomiaSaddle</sub> | <sub>PhiomiaSaddle</sub> | <sub>Phiomia Saddle</sub> | <sub>法尤姆象鞍</sub> | <sub>zhmap·英文</sub> | <sub>7</sub> |
| <sub>`RockDrakeSaddle`</sub> | <sub>PrimalItemArmor_RockDrakeSaddle</sub> | <sub>RockDrakeSaddle_Icon</sub> | <sub>Rock Drake Saddle</sub> | <sub>岩龙鞍</sub> | <sub>zhmap·英文</sub> | <sub>6</sub> |
| <sub>`YiLingSaddle`</sub> | <sub>PrimalItemArmor_YiLingSaddle</sub> | <sub>HUD_YiLing_Saddle_Icon</sub> | <sub>Yi Ling Saddle</sub> | <sub>翎翼龙鞍</sub> | <sub>zhmap·英文</sub> | <sub>5</sub> |
| <sub>`DeinonychusSaddle`</sub> | <sub>PrimalItemArmor_DeinonychusSaddle</sub> | <sub>Deinonychus_Saddle</sub> | <sub>Deinonychus Saddle</sub> | <sub>恐爪龙鞍</sub> | <sub>zhmap·英文</sub> | <sub>3</sub> |
| <sub>`BasiliskSaddle`</sub> | <sub>PrimalItemArmor_BasiliskSaddle</sub> | <sub>Basilisk_Saddle</sub> | <sub>Basilisk Saddle</sub> | <sub>帝蟒鞍</sub> | <sub>zhmap·英文</sub> | <sub>2</sub> |
| <sub>`DesmodusSaddle`</sub> | <sub>PrimalItemArmor_DesmodusSaddle</sub> | <sub>Desmodus_Saddle</sub> | <sub>Desmodus Saddle</sub> | <sub>吸血蝠鞍</sub> | <sub>zhmap·英文</sub> | <sub>1</sub> |
| <sub>`UmbraSaddle`</sub> | <sub>PrimalItemArmor_UmbraSaddle</sub> | <sub>HUD_UmbraSaddle_Icon</sub> | <sub>Umbra Saddle</sub> | <sub>幽影仔鞍</sub> | <sub>zhmap·英文</sub> | <sub>1</sub> |
| <sub>`BasiloSaddle`</sub> | <sub>PrimalItemArmor_BasiloSaddle</sub> | <sub>—</sub> | <sub>Basilo</sub> | <sub>龙王鲸鞍</sub> | <sub>物种(zhmap)+鞍</sub> | <sub>0</sub> |
| <sub>`CamelsaurusSaddle`</sub> | <sub>PrimalItemArmor_CamelsaurusSaddle</sub> | <sub>CamelsaurusSaddle_Icon</sub> | <sub>Camelsaurus</sub> | <sub>驼峰龙鞍</sub> | <sub>物种(zhmap·键)+鞍</sub> | <sub>0</sub> |
| <sub>`HyaenodonSaddle`</sub> | <sub>PrimalItemArmor_HyaenodonSaddle</sub> | <sub>—</sub> | <sub>Hyaenodon</sub> | <sub>鬣齿兽鞍</sub> | <sub>物种(zhmap)+鞍</sub> | <sub>0</sub> |
| <sub>`JackalopeSaddle`</sub> | <sub>PrimalItemArmor_JackalopeSaddle</sub> | <sub>—</sub> | <sub>Jackalope</sub> | <sub>鹿角兔鞍</sub> | <sub>物种(PO)+鞍</sub> | <sub>0</sub> |
| <sub>`ScorpionSaddle`</sub> | <sub>PrimalItemArmor_ScorpionSaddle</sub> | <sub>ScorpionSaddle</sub> | <sub>Scorpion</sub> | <sub>蝎子鞍</sub> | <sub>物种(PO)+鞍</sub> | <sub>0</sub> |
| <sub>`SpiderSaddle`</sub> | <sub>PrimalItemArmor_SpiderSaddle</sub> | <sub>SpiderSaddle</sub> | <sub>Spider</sub> | <sub>蜘蛛鞍</sub> | <sub>物种(PO)+鞍</sub> | <sub>0</sub> |
| <sub>`TurtleSaddle`</sub> | <sub>PrimalItemArmor_TurtleSaddle</sub> | <sub>TurtleSaddle</sub> | <sub>Turtle</sub> | <sub>碳龟鞍</sub> | <sub>物种(PO)+鞍</sub> | <sub>0</sub> |

### armor（服饰/护甲）（61 条）

| <sub>基名</sub> | <sub>完整类名</sub> | <sub>icon</sub> | <sub>en</sub> | <sub>zh</sub> | <sub>出处</sub> | <sub>次数</sub> |
|------|------|------|----|----|------|:---:|
| <sub>`TekHelmet`</sub> | <sub>PrimalItemArmor_TekHelmet</sub> | <sub>TEK_Icon</sub> | <sub>Tek Helmet</sub> | <sub>泰克头盔</sub> | <sub>zhmap·英文</sub> | <sub>87</sub> |
| <sub>`TekPants`</sub> | <sub>PrimalItemArmor_TekPants</sub> | <sub>TEK_Icon</sub> | <sub>Tek</sub> | <sub>泰克护腿</sub> | <sub>wiki英文名→PO</sub> | <sub>85</sub> |
| <sub>`TekGloves`</sub> | <sub>PrimalItemArmor_TekGloves</sub> | <sub>TEKGloves</sub> | <sub>Tek</sub> | <sub>泰克手套</sub> | <sub>wiki英文名→PO</sub> | <sub>82</sub> |
| <sub>`TekBoots`</sub> | <sub>PrimalItemArmor_TekBoots</sub> | <sub>Tek_Boots</sub> | <sub>Tek Boots</sub> | <sub>泰克靴</sub> | <sub>zhmap·英文</sub> | <sub>81</sub> |
| <sub>`TekShirt`</sub> | <sub>PrimalItemArmor_TekShirt</sub> | <sub>TEK_Icon</sub> | <sub>Tek</sub> | <sub>泰克胸甲</sub> | <sub>wiki英文名→PO</sub> | <sub>65</sub> |
| <sub>`FurShirt`</sub> | <sub>PrimalItemArmor_FurShirt</sub> | <sub>—</sub> | <sub>Fur</sub> | <sub>毛皮胸甲</sub> | <sub>wiki英文名→PO</sub> | <sub>51</sub> |
| <sub>`MetalHelmet`</sub> | <sub>PrimalItemArmor_MetalHelmet</sub> | <sub>—</sub> | <sub>Metal</sub> | <sub>防弹头盔</sub> | <sub>wiki英文名→PO</sub> | <sub>46</sub> |
| <sub>`FurHelmet`</sub> | <sub>PrimalItemArmor_FurHelmet</sub> | <sub>—</sub> | <sub>Fur</sub> | <sub>毛皮帽</sub> | <sub>wiki英文名→PO</sub> | <sub>44</sub> |
| <sub>`RiotBoots`</sub> | <sub>PrimalItemArmor_RiotBoots</sub> | <sub>Riot_Boots</sub> | <sub>Riot Boots</sub> | <sub>防暴靴</sub> | <sub>zhmap·英文</sub> | <sub>44</sub> |
| <sub>`RiotShirt`</sub> | <sub>PrimalItemArmor_RiotShirt</sub> | <sub>—</sub> | <sub>Riot</sub> | <sub>防暴胸甲</sub> | <sub>wiki英文名→PO</sub> | <sub>39</sub> |
| <sub>`FurBoots`</sub> | <sub>PrimalItemArmor_FurBoots</sub> | <sub>Fur_Boots</sub> | <sub>Fur Boots</sub> | <sub>毛皮靴</sub> | <sub>zhmap·英文</sub> | <sub>38</sub> |
| <sub>`FurGloves`</sub> | <sub>PrimalItemArmor_FurGloves</sub> | <sub>—</sub> | <sub>Fur</sub> | <sub>毛皮手套</sub> | <sub>wiki英文名→PO</sub> | <sub>37</sub> |
| <sub>`ChitinHelmet`</sub> | <sub>PrimalItemArmor_ChitinHelmet</sub> | <sub>—</sub> | <sub>Chitin Helmet</sub> | <sub>甲壳头盔</sub> | <sub>PO</sub> | <sub>34</sub> |
| <sub>`FurPants`</sub> | <sub>PrimalItemArmor_FurPants</sub> | <sub>—</sub> | <sub>Fur</sub> | <sub>毛皮护腿</sub> | <sub>wiki英文名→PO</sub> | <sub>34</sub> |
| <sub>`RiotHelmet`</sub> | <sub>PrimalItemArmor_RiotHelmet</sub> | <sub>Riot_Helmet</sub> | <sub>Riot Helmet</sub> | <sub>防暴帽</sub> | <sub>zhmap·英文</sub> | <sub>32</sub> |
| <sub>`ChitinGloves`</sub> | <sub>PrimalItemArmor_ChitinGloves</sub> | <sub>ChitinGloves</sub> | <sub>Chitin Gauntlets</sub> | <sub>甲壳手套</sub> | <sub>人工修正</sub> | <sub>30</sub> |
| <sub>`ChitinBoots`</sub> | <sub>PrimalItemArmor_ChitinBoots</sub> | <sub>ChitinBoots</sub> | <sub>Chitin Boots</sub> | <sub>甲壳靴</sub> | <sub>zhmap·英文</sub> | <sub>28</sub> |
| <sub>`RiotGloves`</sub> | <sub>PrimalItemArmor_RiotGloves</sub> | <sub>RiotGloves</sub> | <sub>Riot Gauntlets</sub> | <sub>防暴手套</sub> | <sub>人工修正</sub> | <sub>27</sub> |
| <sub>`GhillieHelmet`</sub> | <sub>PrimalItemArmor_GhillieHelmet</sub> | <sub>—</sub> | <sub>Ghillie</sub> | <sub>吉利面具</sub> | <sub>wiki英文名→PO</sub> | <sub>26</sub> |
| <sub>`RiotPants`</sub> | <sub>PrimalItemArmor_RiotPants</sub> | <sub>—</sub> | <sub>Riot</sub> | <sub>防暴裤</sub> | <sub>wiki英文名→PO</sub> | <sub>26</sub> |
| <sub>`MetalShield`</sub> | <sub>PrimalItemArmor_MetalShield</sub> | <sub>Metal_Shield</sub> | <sub>Metal Shield</sub> | <sub>金属盾牌</sub> | <sub>zhmap·英文</sub> | <sub>24</sub> |
| <sub>`HazardSuitPants`</sub> | <sub>PrimalItemArmor_HazardSuitPants</sub> | <sub>HazardSuitPants_Icon</sub> | <sub>Hazard Suit Pants</sub> | <sub>防护裤</sub> | <sub>zhmap·英文</sub> | <sub>19</sub> |
| <sub>`MekBackpack_Shield`</sub> | <sub>PrimalItemArmor_MekBackpack_Shield</sub> | <sub>—</sub> | <sub>Mek</sub> | <sub>机甲护盾模块</sub> | <sub>wiki英文名→PO</sub> | <sub>19</sub> |
| <sub>`HazardSuitShirt`</sub> | <sub>PrimalItemArmor_HazardSuitShirt</sub> | <sub>Hazard_Suit_Shirt</sub> | <sub>Hazard Suit Shirt</sub> | <sub>防护上衣</sub> | <sub>zhmap·英文</sub> | <sub>16</sub> |
| <sub>`WoodShield`</sub> | <sub>PrimalItemArmor_WoodShield</sub> | <sub>Wood</sub> | <sub>Wood</sub> | <sub>木制盾牌</sub> | <sub>wiki英文名→PO</sub> | <sub>14</sub> |
| <sub>`Gallimimus`</sub> | <sub>PrimalItemArmor_Gallimimus</sub> | <sub>Gallimimus</sub> | <sub>Gallimimus</sub> | <sub>似鸡龙</sub> | <sub>zhmap·英文</sub> | <sub>13</sub> |
| <sub>`HazardSuitBoots`</sub> | <sub>PrimalItemArmor_HazardSuitBoots</sub> | <sub>Hazard_Suit_Boots</sub> | <sub>Hazard Suit Boots</sub> | <sub>防护靴</sub> | <sub>zhmap·英文</sub> | <sub>13</sub> |
| <sub>`Helicoprion`</sub> | <sub>PrimalItemArmor_Helicoprion</sub> | <sub>Helicoprion</sub> | <sub>Helicoprion</sub> | <sub>旋齿鲨</sub> | <sub>zhmap·英文</sub> | <sub>12</sub> |
| <sub>`MekBackpack_MissilePod`</sub> | <sub>PrimalItemArmor_MekBackpack_MissilePod</sub> | <sub>—</sub> | <sub>Mek</sub> | <sub>机甲火箭模块</sub> | <sub>wiki英文名→PO</sub> | <sub>12</sub> |
| <sub>`ClothHelmet`</sub> | <sub>PrimalItemArmor_ClothHelmet</sub> | <sub>—</sub> | <sub>Cloth</sub> | <sub>粗布帽子</sub> | <sub>wiki英文名→PO</sub> | <sub>11</sub> |
| <sub>`ClothShirt`</sub> | <sub>PrimalItemArmor_ClothShirt</sub> | <sub>—</sub> | <sub>Cloth Shirt</sub> | <sub>粗布衣服</sub> | <sub>PO</sub> | <sub>11</sub> |
| <sub>`HideHelmet`</sub> | <sub>PrimalItemArmor_HideHelmet</sub> | <sub>Hide</sub> | <sub>Hide Hat</sub> | <sub>隐藏头盔</sub> | <sub>人工修正</sub> | <sub>11</sub> |
| <sub>`HideGloves`</sub> | <sub>PrimalItemArmor_HideGloves</sub> | <sub>HideGloves</sub> | <sub>Hide Gloves</sub> | <sub>兽皮手套</sub> | <sub>zhmap·英文</sub> | <sub>10</sub> |
| <sub>`HidePants`</sub> | <sub>PrimalItemArmor_HidePants</sub> | <sub>Hide</sub> | <sub>Hide Pants</sub> | <sub>兽皮裤</sub> | <sub>PO</sub> | <sub>10</sub> |
| <sub>`HideShirt`</sub> | <sub>PrimalItemArmor_HideShirt</sub> | <sub>HideShirt</sub> | <sub>Hide Shirt</sub> | <sub>兽皮上衣</sub> | <sub>zhmap·英文</sub> | <sub>10</sub> |
| <sub>`ClothBoots`</sub> | <sub>PrimalItemArmor_ClothBoots</sub> | <sub>—</sub> | <sub>Cloth Boots</sub> | <sub>粗布鞋</sub> | <sub>PO</sub> | <sub>9</sub> |
| <sub>`ClothPants`</sub> | <sub>PrimalItemArmor_ClothPants</sub> | <sub>—</sub> | <sub>Cloth Pants</sub> | <sub>粗布裤子</sub> | <sub>PO</sub> | <sub>9</sub> |
| <sub>`HazardSuitHelmet`</sub> | <sub>PrimalItemArmor_HazardSuitHelmet</sub> | <sub>—</sub> | <sub>Hazard</sub> | <sub>防护头盔</sub> | <sub>wiki英文名→PO</sub> | <sub>9</sub> |
| <sub>`ScubaShirt_SuitWithTank`</sub> | <sub>PrimalItemArmor_ScubaShirt_SuitWithTank</sub> | <sub>—</sub> | <sub>Scuba</sub> | <sub>潜水服</sub> | <sub>wiki英文名→PO</sub> | <sub>9</sub> |
| <sub>`DesertClothGogglesHelmet`</sub> | <sub>PrimalItemArmor_DesertClothGogglesHelmet</sub> | <sub>—</sub> | <sub>Desert Cloth</sub> | <sub>沙漠眼镜和帽子</sub> | <sub>wiki英文名→PO</sub> | <sub>8</sub> |
| <sub>`DesertClothPants`</sub> | <sub>PrimalItemArmor_DesertClothPants</sub> | <sub>Desert_Cloth_Pants</sub> | <sub>Desert Cloth Pants</sub> | <sub>沙漠裤子</sub> | <sub>zhmap·英文</sub> | <sub>8</sub> |
| <sub>`HideBoots`</sub> | <sub>PrimalItemArmor_HideBoots</sub> | <sub>HideBoots</sub> | <sub>Hide Boots</sub> | <sub>兽皮靴</sub> | <sub>zhmap·英文</sub> | <sub>8</sub> |
| <sub>`ClothGloves`</sub> | <sub>PrimalItemArmor_ClothGloves</sub> | <sub>—</sub> | <sub>Cloth Gloves</sub> | <sub>粗布手套</sub> | <sub>PO</sub> | <sub>7</sub> |
| <sub>`MekBackpack_SiegeCannon`</sub> | <sub>PrimalItemArmor_MekBackpack_SiegeCannon</sub> | <sub>—</sub> | <sub>Mek</sub> | <sub>机甲重炮模块</sub> | <sub>wiki英文名→PO</sub> | <sub>6</sub> |
| <sub>`DesertClothGloves`</sub> | <sub>PrimalItemArmor_DesertClothGloves</sub> | <sub>Desert_Cloth_Gloves</sub> | <sub>Desert Cloth Gloves</sub> | <sub>沙漠手套</sub> | <sub>zhmap·英文</sub> | <sub>5</sub> |
| <sub>`DesertClothShirt`</sub> | <sub>PrimalItemArmor_DesertClothShirt</sub> | <sub>Desert_Cloth_Shirt</sub> | <sub>Desert Cloth Shirt</sub> | <sub>沙漠衣服</sub> | <sub>zhmap·英文</sub> | <sub>5</sub> |
| <sub>`DesertClothBoots`</sub> | <sub>PrimalItemArmor_DesertClothBoots</sub> | <sub>Desert_Cloth_Boots</sub> | <sub>Desert Cloth Boots</sub> | <sub>沙漠鞋</sub> | <sub>zhmap·英文</sub> | <sub>4</sub> |
| <sub>`ScubaHelmet_Goggles`</sub> | <sub>PrimalItemArmor_ScubaHelmet_Goggles</sub> | <sub>—</sub> | <sub>Scuba</sub> | <sub>潜水面具</sub> | <sub>wiki英文名→PO</sub> | <sub>4</sub> |
| <sub>`ArcticShirt`</sub> | <sub>PrimalItemArmor_ArcticShirt</sub> | <sub>—</sub> | <sub>Arctic</sub> | <sub>极地侦察胸甲</sub> | <sub>miss_en</sub> | <sub>3</sub> |
| <sub>`ScubaBoots_Flippers`</sub> | <sub>PrimalItemArmor_ScubaBoots_Flippers</sub> | <sub>—</sub> | <sub>Scuba</sub> | <sub>潜水脚蹼</sub> | <sub>wiki英文名→PO</sub> | <sub>3</sub> |
| <sub>`RiotPants_Cursed`</sub> | <sub>PrimalItemArmor_RiotPants_Cursed</sub> | <sub>—</sub> | <sub>Cursed Riot Leggings</sub> | <sub>咒缚防暴裤</sub> | <sub>人工修正</sub> | <sub>2</sub> |
| <sub>`ScubaPants`</sub> | <sub>PrimalItemArmor_ScubaPants</sub> | <sub>—</sub> | <sub>Scuba</sub> | <sub>潜水裤</sub> | <sub>wiki英文名→PO</sub> | <sub>2</sub> |
| <sub>`TekGloves_Cursed`</sub> | <sub>PrimalItemArmor_TekGloves_Cursed</sub> | <sub>TEKGloves</sub> | <sub>Cursed Tek Gauntlets</sub> | <sub>咒缚泰克手套</sub> | <sub>人工修正</sub> | <sub>2</sub> |
| <sub>`TekPants_Cursed`</sub> | <sub>PrimalItemArmor_TekPants_Cursed</sub> | <sub>—</sub> | <sub>Cursed Tek Leggings</sub> | <sub>咒缚泰克护腿</sub> | <sub>人工修正</sub> | <sub>2</sub> |
| <sub>`ArcticGloves`</sub> | <sub>PrimalItemArmor_ArcticGloves</sub> | <sub>—</sub> | <sub>Arctic</sub> | <sub>极地侦察护手</sub> | <sub>miss_en</sub> | <sub>1</sub> |
| <sub>`ArcticPants`</sub> | <sub>PrimalItemArmor_ArcticPants</sub> | <sub>—</sub> | <sub>Arctic</sub> | <sub>极地侦察护腿</sub> | <sub>miss_en</sub> | <sub>1</sub> |
| <sub>`GasMask`</sub> | <sub>PrimalItemArmor_GasMask</sub> | <sub>Gas_Mask</sub> | <sub>Gas Mask</sub> | <sub>防毒面具</sub> | <sub>zhmap·英文</sub> | <sub>1</sub> |
| <sub>`MetalPants_Cursed`</sub> | <sub>PrimalItemArmor_MetalPants_Cursed</sub> | <sub>MetalPants</sub> | <sub>Cursed Flak Leggings</sub> | <sub>咒缚防弹护腿</sub> | <sub>人工修正</sub> | <sub>1</sub> |
| <sub>`MetalShirt_Cursed`</sub> | <sub>PrimalItemArmor_MetalShirt_Cursed</sub> | <sub>MetalShirt</sub> | <sub>Cursed Flak Chestpiece</sub> | <sub>咒缚防弹胸甲</sub> | <sub>人工修正</sub> | <sub>1</sub> |
| <sub>`RiotShirt_Cursed`</sub> | <sub>PrimalItemArmor_RiotShirt_Cursed</sub> | <sub>—</sub> | <sub>Cursed Riot Chestpiece</sub> | <sub>咒缚防暴胸甲</sub> | <sub>人工修正</sub> | <sub>1</sub> |
| <sub>`TekBoots_Cursed`</sub> | <sub>PrimalItemArmor_TekBoots_Cursed</sub> | <sub>Tek_Boots</sub> | <sub>Tek Boots</sub> | <sub>咒缚泰克靴</sub> | <sub>人工修正</sub> | <sub>1</sub> |

### weapon（工具/武器）（28 条）

| <sub>基名</sub> | <sub>完整类名</sub> | <sub>icon</sub> | <sub>en</sub> | <sub>zh</sub> | <sub>出处</sub> | <sub>次数</sub> |
|------|------|------|----|----|------|:---:|
| <sub>`Rifle`</sub> | <sub>PrimalItem_WeaponRifle</sub> | <sub>—</sub> | <sub>Rifle</sub> | <sub>步枪</sub> | <sub>PO</sub> | <sub>96</sub> |
| <sub>`CompoundBow`</sub> | <sub>PrimalItem_WeaponCompoundBow</sub> | <sub>Compound_Bow</sub> | <sub>Compound Bow</sub> | <sub>复合弓</sub> | <sub>zhmap·英文</sub> | <sub>49</sub> |
| <sub>`MachinedPistol`</sub> | <sub>PrimalItem_WeaponMachinedPistol</sub> | <sub>MachinedPistol_Icon</sub> | <sub>Machined Pistol</sub> | <sub>手枪</sub> | <sub>zhmap·键</sub> | <sub>48</sub> |
| <sub>`MachinedShotgun`</sub> | <sub>PrimalItem_WeaponMachinedShotgun</sub> | <sub>MachinedShotgun_Icon</sub> | <sub>Shotgun</sub> | <sub>霰弹枪</sub> | <sub>zhmap·键</sub> | <sub>48</sub> |
| <sub>`Crossbow`</sub> | <sub>PrimalItem_WeaponCrossbow</sub> | <sub>—</sub> | <sub>Crossbow</sub> | <sub>十字弩</sub> | <sub>zhmap·英文</sub> | <sub>47</sub> |
| <sub>`MetalHatchet`</sub> | <sub>PrimalItem_WeaponMetalHatchet</sub> | <sub>Metal_Hatchet</sub> | <sub>Metal Hatchet</sub> | <sub>金属斧子</sub> | <sub>zhmap·英文</sub> | <sub>41</sub> |
| <sub>`MetalPick`</sub> | <sub>PrimalItem_WeaponMetalPick</sub> | <sub>Metal_Pick</sub> | <sub>Metal Pick</sub> | <sub>金属镐</sub> | <sub>zhmap·英文</sub> | <sub>40</sub> |
| <sub>`Sword`</sub> | <sub>PrimalItem_WeaponSword</sub> | <sub>Sword_Icon</sub> | <sub>Sword</sub> | <sub>剑</sub> | <sub>zhmap·英文</sub> | <sub>38</sub> |
| <sub>`Pike`</sub> | <sub>PrimalItem_WeaponPike</sub> | <sub>Pike_Icon</sub> | <sub>Pike</sub> | <sub>金属矛</sub> | <sub>zhmap·英文</sub> | <sub>36</sub> |
| <sub>`Shotgun`</sub> | <sub>PrimalItem_WeaponShotgun</sub> | <sub>Shotgun_Icon</sub> | <sub>Shotgun</sub> | <sub>霰弹枪</sub> | <sub>zhmap·英文</sub> | <sub>34</sub> |
| <sub>`ScoutRemote`</sub> | <sub>PrimalItem_WeaponScoutRemote</sub> | <sub>scout</sub> | <sub>Scout Remote</sub> | <sub>侦察机遥控器</sub> | <sub>PO</sub> | <sub>27</sub> |
| <sub>`ScoutRemote_CityTerminal`</sub> | <sub>PrimalItem_WeaponScoutRemote_CityTerminal</sub> | <sub>—</sub> | <sub>Scout</sub> | <sub>城市终端</sub> | <sub>PO词集包含</sub> | <sub>27</sub> |
| <sub>`Torch`</sub> | <sub>PrimalItem_WeaponTorch</sub> | <sub>Torch</sub> | <sub>Torch</sub> | <sub>火把</sub> | <sub>zhmap·英文</sub> | <sub>27</sub> |
| <sub>`StoneClub`</sub> | <sub>PrimalItem_WeaponStoneClub</sub> | <sub>Stone</sub> | <sub>Wooden Club</sub> | <sub>木制球棒</sub> | <sub>人工修正</sub> | <sub>20</sub> |
| <sub>`StonePick`</sub> | <sub>PrimalItem_WeaponStonePick</sub> | <sub>Stone_Pick</sub> | <sub>Stone Pick</sub> | <sub>石镐</sub> | <sub>zhmap·英文</sub> | <sub>20</sub> |
| <sub>`TekSword`</sub> | <sub>PrimalItem_WeaponTekSword</sub> | <sub>TEKSword_Icon</sub> | <sub>Tek Sword</sub> | <sub>泰克剑</sub> | <sub>PO</sub> | <sub>16</sub> |
| <sub>`StoneHatchet`</sub> | <sub>PrimalItem_WeaponStoneHatchet</sub> | <sub>Stone_Hatchet</sub> | <sub>Stone Hatchet</sub> | <sub>石制斧头</sub> | <sub>zhmap·英文</sub> | <sub>15</sub> |
| <sub>`Slingshot`</sub> | <sub>PrimalItem_WeaponSlingshot</sub> | <sub>Slingshot_Icon</sub> | <sub>Slingshot</sub> | <sub>弹弓</sub> | <sub>zhmap·英文</sub> | <sub>13</sub> |
| <sub>`GooGun`</sub> | <sub>PrimalItem_WeaponGooGun</sub> | <sub>Goo_Gun</sub> | <sub>Goo Gun</sub> | <sub>黏液枪</sub> | <sub>zhmap·英文</sub> | <sub>11</sub> |
| <sub>`Whip`</sub> | <sub>PrimalItem_WeaponWhip</sub> | <sub>Whip</sub> | <sub>Whip</sub> | <sub>鞭子</sub> | <sub>zhmap·英文</sub> | <sub>9</sub> |
| <sub>`Lance`</sub> | <sub>PrimalItem_WeaponLance</sub> | <sub>Lance_Icon</sub> | <sub>Lance</sub> | <sub>长枪</sub> | <sub>zhmap·英文</sub> | <sub>7</sub> |
| <sub>`MiningDrill`</sub> | <sub>PrimalItem_WeaponMiningDrill</sub> | <sub>Mining_Drill</sub> | <sub>Mining Drill</sub> | <sub>矿枪</sub> | <sub>zhmap·英文</sub> | <sub>4</sub> |
| <sub>`TekClaws`</sub> | <sub>PrimalItem_WeaponTekClaws</sub> | <sub>HUD_TEKClaws_Icon</sub> | <sub>Tek Claws</sub> | <sub>泰克光刃</sub> | <sub>PO</sub> | <sub>2</sub> |
| <sub>`MetalHatchet_Cursed`</sub> | <sub>PrimalItem_WeaponMetalHatchet_Cursed</sub> | <sub>Metal_Hatchet</sub> | <sub>Metal Hatchet</sub> | <sub>咒缚金属斧子</sub> | <sub>人工修正</sub> | <sub>1</sub> |
| <sub>`OilJar`</sub> | <sub>PrimalItem_WeaponOilJar</sub> | <sub>Oil_Jar</sub> | <sub>Oil Jar</sub> | <sub>油罐</sub> | <sub>zhmap·英文</sub> | <sub>1</sub> |
| <sub>`Spear`</sub> | <sub>PrimalItem_WeaponSpear</sub> | <sub>Spear_Icon</sub> | <sub>Spear</sub> | <sub>长矛</sub> | <sub>zhmap·英文</sub> | <sub>1</sub> |
| <sub>`TekSword_Cursed`</sub> | <sub>PrimalItem_WeaponTekSword_Cursed</sub> | <sub>TEKSword_Icon</sub> | <sub>Tek Sword</sub> | <sub>咒缚泰克剑</sub> | <sub>人工修正</sub> | <sub>1</sub> |
| <sub>`Grenade`</sub> | <sub>PrimalItem_WeaponGrenade</sub> | <sub>Grenade_Icon</sub> | <sub>Grenade</sub> | <sub>手雷</sub> | <sub>人工修正</sub> | <sub>0</sub> |

### tek（泰克装备）（2 条）

| <sub>基名</sub> | <sub>完整类名</sub> | <sub>icon</sub> | <sub>en</sub> | <sub>zh</sub> | <sub>出处</sub> | <sub>次数</sub> |
|------|------|------|----|----|------|:---:|
| <sub>`TekRifle`</sub> | <sub>PrimalItem_TekRifle</sub> | <sub>TEKRifle_Icon</sub> | <sub>Tek Rifle</sub> | <sub>泰克步枪</sub> | <sub>PO</sub> | <sub>72</sub> |
| <sub>`TekRifle_Cursed`</sub> | <sub>PrimalItem_TekRifle_Cursed</sub> | <sub>TEKRifle_Icon</sub> | <sub>Tek Rifle</sub> | <sub>咒缚泰克步枪</sub> | <sub>人工修正</sub> | <sub>1</sub> |

### other（其他/未归类）（4 条）

| <sub>基名</sub> | <sub>完整类名</sub> | <sub>icon</sub> | <sub>en</sub> | <sub>zh</sub> | <sub>出处</sub> | <sub>次数</sub> |
|------|------|------|----|----|------|:---:|
| <sub>`ChainSaw`</sub> | <sub>PrimalItem_ChainSaw</sub> | <sub>Chainsaw</sub> | <sub>Chainsaw</sub> | <sub>电锯</sub> | <sub>zhmap·英文</sub> | <sub>10</sub> |
| <sub>`GasGrenade`</sub> | <sub>PrimalItem_GasGrenade</sub> | <sub>—</sub> | <sub>Smoke Grenade</sub> | <sub>烟雾弹</sub> | <sub>人工修正</sub> | <sub>1</sub> |
| <sub>`PoisonGrenade`</sub> | <sub>PrimalItem_PoisonGrenade</sub> | <sub>Poison_Grenade</sub> | <sub>Poison Grenade</sub> | <sub>毒气手雷</sub> | <sub>zhmap·英文</sub> | <sub>1</sub> |
| <sub>`OrganicPolymer`</sub> | <sub>—</sub> | <sub>Organic_Polymer</sub> | <sub>Organic Polymer</sub> | <sub>有机聚合物</sub> | <sub>zhmap·英文</sub> | <sub>0</sub> |

---

## ② 有权威出处（253 条，可直接采纳）

> 回一句「**采纳有出处**」→ 写入 `item_zh.json` 并重跑表。`出处证据` 列即该中文的原始依据。

| <sub>#</sub> | <sub>基名</sub> | <sub>完整类名</sub> | <sub>icon</sub> | <sub>类别</sub> | <sub>溯源中文</sub> | <sub>出处</sub> | <sub>出处证据</sub> |
|:--:|------|------|------|------|---------|------|---------|
| <sub>1</sub> | <sub>`ARKBone`</sub> | <sub>PrimalItemResource_ARKBone</sub> | <sub>ARKBone_Icon</sub> | <sub>resource（资源/材料）</sub> | <sub>**恐龙骸骨**</sub> | <sub>miss_en</sub> | <sub>缺口英文名 "Dinosaur Bone"〔wiki〕→ PO#3278634328</sub> |
| <sub>2</sub> | <sub>`AggroTranqDart`</sub> | <sub>PrimalItemAmmo_AggroTranqDart</sub> | <sub>—</sub> | <sub>ammo（弹药/投掷物）</sub> | <sub>**信息素镖**</sub> | <sub>miss_en</sub> | <sub>缺口英文名 "Pheromone Dart"〔wiki〕→ PO#4204102110</sub> |
| <sub>3</sub> | <sub>`AlloSaddle`</sub> | <sub>PrimalItemArmor_AlloSaddle</sub> | <sub>AlloSaddle</sub> | <sub>saddle（鞍具）</sub> | <sub>**异特龙鞍**</sub> | <sub>wiki英文名→PO</sub> | <sub>wiki 英文名 "Allosaurus Saddle" → PO#1333417161</sub> |
| <sub>4</sub> | <sub>`AngelFoxSaddle`</sub> | <sub>PrimalItemArmor_AngelFoxSaddle</sub> | <sub>HUD_AngelFoxSaddle_Icon</sub> | <sub>saddle（鞍具）</sub> | <sub>**霄光狐鞍**</sub> | <sub>miss_en</sub> | <sub>缺口英文名 "Solwyn Saddle"〔wiki~〕→ PO#2346737208</sub> |
| <sub>5</sub> | <sub>`ApexDrop_Acro`</sub> | <sub>PrimalItemResource_ApexDrop_Acro</sub> | <sub>—</sub> | <sub>resource（资源/材料）</sub> | <sub>**高棘龙肾上腺体**</sub> | <sub>PO·物种+部位</sub> | <sub>PO#4080189680 "Acro Adrenal Gland"（物种+部位）</sub> |
| <sub>6</sub> | <sub>`ApexDrop_Allo`</sub> | <sub>PrimalItemResource_ApexDrop_Allo</sub> | <sub>ApexDropAllo_Icon</sub> | <sub>resource（资源/材料）</sub> | <sub>**异特龙大脑**</sub> | <sub>PO·物种+部位</sub> | <sub>PO#1842416241 "Allosaurus Brain"（物种+部位）</sub> |
| <sub>7</sub> | <sub>`ApexDrop_AlphaCarno`</sub> | <sub>PrimalItemResource_ApexDrop_AlphaCarno</sub> | <sub>—</sub> | <sub>resource（资源/材料）</sub> | <sub>**精英肉食牛龙手臂**</sub> | <sub>PO·物种+部位</sub> | <sub>PO#1783435283 "Alpha Carnotaurus Arm"（物种+部位）</sub> |
| <sub>8</sub> | <sub>`ApexDrop_AlphaLeeds`</sub> | <sub>PrimalItemResource_ApexDrop_AlphaLeeds</sub> | <sub>—</sub> | <sub>resource（资源/材料）</sub> | <sub>**精英利兹鱼脂肪**</sub> | <sub>PO·物种+部位</sub> | <sub>PO#411396327 "Alpha Leedsichthys Blubber"（物种+部位）</sub> |
| <sub>9</sub> | <sub>`ApexDrop_AlphaMegalodon`</sub> | <sub>PrimalItemResource_ApexDrop_AlphaMegalodon</sub> | <sub>—</sub> | <sub>resource（资源/材料）</sub> | <sub>**精英巨齿鲨鳍**</sub> | <sub>PO·物种+部位</sub> | <sub>PO#2654186894 "Alpha Megalodon Fin"（物种+部位）</sub> |
| <sub>10</sub> | <sub>`ApexDrop_AlphaMosasaur`</sub> | <sub>PrimalItemResource_ApexDrop_AlphaMosasaur</sub> | <sub>—</sub> | <sub>resource（资源/材料）</sub> | <sub>**精英沧龙牙齿**</sub> | <sub>PO·物种+部位</sub> | <sub>PO#1829898102 "Alpha Mosasaur Tooth"（物种+部位）</sub> |
| <sub>11</sub> | <sub>`ApexDrop_AlphaRaptor`</sub> | <sub>PrimalItemResource_ApexDrop_AlphaRaptor</sub> | <sub>—</sub> | <sub>resource（资源/材料）</sub> | <sub>**精英迅猛龙爪**</sub> | <sub>PO·物种+部位</sub> | <sub>PO#1340854979 "Alpha Raptor Claw"（物种+部位）</sub> |
| <sub>12</sub> | <sub>`ApexDrop_AlphaRex`</sub> | <sub>PrimalItemResource_ApexDrop_AlphaRex</sub> | <sub>—</sub> | <sub>resource（资源/材料）</sub> | <sub>**精英霸王龙战利品**</sub> | <sub>PO·战利品条目</sub> | <sub>PO#2855118979 "Alpha Rex Trophy"（Trophy 条目·物种精确）</sub> |
| <sub>13</sub> | <sub>`ApexDrop_AlphaTuso`</sub> | <sub>PrimalItemResource_ApexDrop_AlphaTuso</sub> | <sub>—</sub> | <sub>resource（资源/材料）</sub> | <sub>**精英托斯特巨鱿眼睛**</sub> | <sub>PO·物种+部位</sub> | <sub>PO#1256044846 "Alpha Tusoteuthis Eye"（物种+部位）</sub> |
| <sub>14</sub> | <sub>`ApexDrop_Argentavis`</sub> | <sub>PrimalItemResource_ApexDrop_Argentavis</sub> | <sub>ApexDrop_Argentavis_Icon</sub> | <sub>resource（资源/材料）</sub> | <sub>**阿根廷鹫爪**</sub> | <sub>PO·物种+部位</sub> | <sub>PO#427648309 "Argentavis Talon"（物种+部位）</sub> |
| <sub>15</sub> | <sub>`ApexDrop_AstralSoul`</sub> | <sub>PrimalItemResource_ApexDrop_AstralSoul</sub> | <sub>—</sub> | <sub>resource（资源/材料）</sub> | <sub>**星界之魂**</sub> | <sub>人工修正</sub> | <sub>人工修正（直填官方原文）：wiki blueprintpath = PrimalItemResource_ApexDrop_AstralSo</sub> |
| <sub>16</sub> | <sub>`ApexDrop_Basilisk`</sub> | <sub>PrimalItemResource_ApexDrop_Basilisk</sub> | <sub>ApexDropBasilo_Icon</sub> | <sub>resource（资源/材料）</sub> | <sub>**帝蟒鳞片**</sub> | <sub>PO·物种+部位</sub> | <sub>PO#3596157197 "Basilisk Scale"（物种+部位）</sub> |
| <sub>17</sub> | <sub>`ApexDrop_Basilisk_Alpha`</sub> | <sub>PrimalItemResource_ApexDrop_Basilisk_Alpha</sub> | <sub>—</sub> | <sub>resource（资源/材料）</sub> | <sub>**精英帝蟒毒牙**</sub> | <sub>wiki英文名→PO</sub> | <sub>wiki 英文名 "Alpha Basilisk Fang" → PO#688798967</sub> |
| <sub>18</sub> | <sub>`ApexDrop_Basilo`</sub> | <sub>PrimalItemResource_ApexDrop_Basilo</sub> | <sub>ApexDropBasilo_Icon</sub> | <sub>resource（资源/材料）</sub> | <sub>**龙王鲸脂肪**</sub> | <sub>PO·物种+部位</sub> | <sub>PO#690836253 "Basilosaurus Blubber"（物种+部位）</sub> |
| <sub>19</sub> | <sub>`ApexDrop_Boaratos`</sub> | <sub>PrimalItemResource_ApexDrop_Boaratos</sub> | <sub>ApexDropBoa_Icon</sub> | <sub>resource（资源/材料）</sub> | <sub>**焰鬃獠猪獠牙**</sub> | <sub>PO·物种+部位</sub> | <sub>PO#20168012 "Boaratos Tusk"（物种+部位）</sub> |
| <sub>20</sub> | <sub>`ApexDrop_Boaratos_Flaming`</sub> | <sub>PrimalItemResource_ApexDrop_Boaratos_Flaming</sub> | <sub>—</sub> | <sub>resource（资源/材料）</sub> | <sub>**焰鬃獠猪**</sub> | <sub>权威英文→PO</sub> | <sub>权威英文 Boaratos〔zhmap_en〕→ PO#2597014499 "Boaratos"</sub> |
| <sub>21</sub> | <sub>`ApexDrop_Cerato_ASA`</sub> | <sub>PrimalItemResource_ApexDrop_Cerato_ASA</sub> | <sub>—</sub> | <sub>resource（资源/材料）</sub> | <sub>**角鼻龙毒脊刺**</sub> | <sub>人工修正</sub> | <sub>人工修正：英文 "Cerato Venom Spine" → PO#811636799</sub> |
| <sub>22</sub> | <sub>`ApexDrop_CrabClaw`</sub> | <sub>PrimalItemResource_ApexDrop_CrabClaw</sub> | <sub>ApexDropCrabClaw_Icon</sub> | <sub>resource（资源/材料）</sub> | <sub>**精英巨蟹鳌**</sub> | <sub>人工修正</sub> | <sub>人工修正：英文 "Alpha Karkinos Claw" → PO#3534536494</sub> |
| <sub>23</sub> | <sub>`ApexDrop_FireWyvern`</sub> | <sub>PrimalItemResource_ApexDrop_FireWyvern</sub> | <sub>—</sub> | <sub>resource（资源/材料）</sub> | <sub>**火焰勾爪**</sub> | <sub>人工修正</sub> | <sub>人工修正：英文 "Fire Talon" → PO#763397312</sub> |
| <sub>24</sub> | <sub>`ApexDrop_GasBag`</sub> | <sub>PrimalItemResource_ApexDrop_GasBag</sub> | <sub>—</sub> | <sub>resource（资源/材料）</sub> | <sub>**气囊虫气泡**</sub> | <sub>PO·物种+部位</sub> | <sub>PO#4072400994 "Gasbags bladder"（物种+部位）</sub> |
| <sub>25</sub> | <sub>`ApexDrop_Giga`</sub> | <sub>PrimalItemResource_ApexDrop_Giga</sub> | <sub>ApexDropGiga_Icon</sub> | <sub>resource（资源/材料）</sub> | <sub>**南方巨兽龙心脏**</sub> | <sub>人工修正</sub> | <sub>人工修正：英文 "Giganotosaurus Heart" → PO#3790189354</sub> |
| <sub>26</sub> | <sub>`ApexDrop_LightningWyvern`</sub> | <sub>PrimalItemResource_ApexDrop_LightningWyvern</sub> | <sub>—</sub> | <sub>resource（资源/材料）</sub> | <sub>**闪电勾爪**</sub> | <sub>人工修正</sub> | <sub>人工修正：英文 "Lightning Talon" → PO#4196769698</sub> |
| <sub>27</sub> | <sub>`ApexDrop_Neophyte`</sub> | <sub>PrimalItemResource_ApexDrop_Neophyte</sub> | <sub>—</sub> | <sub>resource（资源/材料）</sub> | <sub>**猎杀者之角**</sub> | <sub>PO·物种+部位</sub> | <sub>PO#1244349384 "Neophyte Horns"（物种+部位）</sub> |
| <sub>28</sub> | <sub>`ApexDrop_PoisonWyvern`</sub> | <sub>PrimalItemResource_ApexDrop_PoisonWyvern</sub> | <sub>—</sub> | <sub>resource（资源/材料）</sub> | <sub>**剧毒勾爪**</sub> | <sub>人工修正</sub> | <sub>人工修正：英文 "Poison Talon" → PO#124658151</sub> |
| <sub>29</sub> | <sub>`ApexDrop_RockDrake`</sub> | <sub>PrimalItemResource_ApexDrop_RockDrake</sub> | <sub>—</sub> | <sub>resource（资源/材料）</sub> | <sub>**岩龙羽毛**</sub> | <sub>PO·物种+部位</sub> | <sub>PO#3585043228 "Rock Drake Feather"（物种+部位）</sub> |
| <sub>30</sub> | <sub>`ApexDrop_Sarco`</sub> | <sub>PrimalItemResource_ApexDrop_Sarco</sub> | <sub>—</sub> | <sub>resource（资源/材料）</sub> | <sub>**帝鳄**</sub> | <sub>权威英文→PO</sub> | <sub>权威英文 Sarco〔base〕→ PO#389783044 "Sarco"</sub> |
| <sub>31</sub> | <sub>`ApexDrop_Sauro`</sub> | <sub>PrimalItemResource_ApexDrop_Sauro</sub> | <sub>ApexDrop_Sauro_Icon</sub> | <sub>resource（资源/材料）</sub> | <sub>**蜥脚类恐龙脊椎**</sub> | <sub>PO·物种+部位</sub> | <sub>PO#1524558284 "Sauropod Vertebra"（物种+部位）</sub> |
| <sub>32</sub> | <sub>`ApexDrop_SnowMonster`</sub> | <sub>PrimalItemResource_ApexDrop_SnowMonster</sub> | <sub>—</sub> | <sub>resource（资源/材料）</sub> | <sub>**精英奥西顿颅骨**</sub> | <sub>人工修正</sub> | <sub>人工修正：英文 "Alpha Ossidon Skull" → PO#2987147989</sub> |
| <sub>33</sub> | <sub>`ApexDrop_Thylaco`</sub> | <sub>PrimalItemResource_ApexDrop_Thylaco</sub> | <sub>ApexDropThylacoleo_Icon</sub> | <sub>resource（资源/材料）</sub> | <sub>**袋狮钩爪**</sub> | <sub>PO·物种+部位</sub> | <sub>PO#3600406732 "Thylacoleo Hook-Claw"（物种+部位）</sub> |
| <sub>34</sub> | <sub>`ApexDrop_Tuso`</sub> | <sub>PrimalItemResource_ApexDrop_Tuso</sub> | <sub>—</sub> | <sub>resource（资源/材料）</sub> | <sub>**托斯特巨鱿触手**</sub> | <sub>PO·物种+部位</sub> | <sub>PO#1157847459 "Tusoteuthis Tentacle"（物种+部位）</sub> |
| <sub>35</sub> | <sub>`ApexDrop_Yuty`</sub> | <sub>PrimalItemResource_ApexDrop_Yuty</sub> | <sub>ApexDropYutyranus_Icon</sub> | <sub>resource（资源/材料）</sub> | <sub>**羽王龙肺**</sub> | <sub>人工修正</sub> | <sub>人工修正：英文 "Yutyrannus Lungs" → PO#444932635</sub> |
| <sub>36</sub> | <sub>`ApexDrop_Zombie`</sub> | <sub>PrimalItemResource_ApexDrop_Zombie</sub> | <sub>—</sub> | <sub>resource（资源/材料）</sub> | <sub>**精英丧尸大脑**</sub> | <sub>PO·物种+部位</sub> | <sub>PO#1665872065 "Alpha Zombie Brains"（物种+部位）</sub> |
| <sub>37</sub> | <sub>`ArcticBoots`</sub> | <sub>PrimalItemArmor_ArcticBoots</sub> | <sub>—</sub> | <sub>armor（服饰/护甲）</sub> | <sub>**极地侦察靴**</sub> | <sub>miss_en</sub> | <sub>缺口英文名 "Arctic Scout Boots"〔wiki~〕→ PO#3879112422</sub> |
| <sub>38</sub> | <sub>`ArcticHelmet`</sub> | <sub>PrimalItemArmor_ArcticHelmet</sub> | <sub>—</sub> | <sub>armor（服饰/护甲）</sub> | <sub>**极地侦察头盔**</sub> | <sub>miss_en</sub> | <sub>缺口英文名 "Arctic Scout Helmet"〔wiki~〕→ PO#878325163</sub> |
| <sub>39</sub> | <sub>`Armor_Archelon_Saddle_ASA`</sub> | <sub>PrimalItem_Armor_Archelon_Saddle_ASA</sub> | <sub>—</sub> | <sub>saddle（鞍具）</sub> | <sub>**古巨龟鞍**</sub> | <sub>PO词集包含</sub> | <sub>PO#845425771 "Archelon Saddle"（词集包含）</sub> |
| <sub>40</sub> | <sub>`ArrowFlame`</sub> | <sub>PrimalItemAmmo_ArrowFlame</sub> | <sub>Arrow_icon</sub> | <sub>ammo（弹药/投掷物）</sub> | <sub>**火箭**</sub> | <sub>wiki英文名→PO</sub> | <sub>wiki 英文名 "Flame Arrow" → PO#114294021</sub> |
| <sub>41</sub> | <sub>`ArrowTranq`</sub> | <sub>PrimalItemAmmo_ArrowTranq</sub> | <sub>Arrow_icon</sub> | <sub>ammo（弹药/投掷物）</sub> | <sub>**麻醉箭**</sub> | <sub>wiki英文名→PO</sub> | <sub>wiki 英文名 "Tranq Arrow" → PO#2465582888</sub> |
| <sub>42</sub> | <sub>`ArthroSaddle`</sub> | <sub>PrimalItemArmor_ArthroSaddle</sub> | <sub>—</sub> | <sub>saddle（鞍具）</sub> | <sub>**节胸虫鞍**</sub> | <sub>wiki英文名→PO</sub> | <sub>wiki 英文名 "Arthropluera Saddle" → PO#2781599527</sub> |
| <sub>43</sub> | <sub>`AxolotlSaddle`</sub> | <sub>PrimalItemArmor_AxolotlSaddle</sub> | <sub>—</sub> | <sub>saddle（鞍具）</sub> | <sub>**潮佑螈鞍**</sub> | <sub>miss_en</sub> | <sub>缺口英文名 "Tidepup Saddle"〔wiki~〕→ PO#1755310013</sub> |
| <sub>44</sub> | <sub>`BeaverSaddle`</sub> | <sub>PrimalItemArmor_BeaverSaddle</sub> | <sub>—</sub> | <sub>saddle（鞍具）</sub> | <sub>**巨河狸鞍**</sub> | <sub>wiki英文名→PO</sub> | <sub>wiki 英文名 "Castoroides Saddle" → PO#4251950154</sub> |
| <sub>45</sub> | <sub>`Beer`</sub> | <sub>PrimalItemResource_Beer</sub> | <sub>—</sub> | <sub>resource（资源/材料）</sub> | <sub>**酒水**</sub> | <sub>miss_en</sub> | <sub>缺口英文名 "Beer Liquid"〔wiki〕→ PO#1383652799</sub> |
| <sub>46</sub> | <sub>`BlueSap`</sub> | <sub>PrimalItemResource_BlueSap</sub> | <sub>—</sub> | <sub>resource（资源/材料）</sub> | <sub>**蓝色晶化树脂**</sub> | <sub>miss_en</sub> | <sub>缺口英文名 "Blue Crystalized Sap"〔wiki〕→ PO#3133587865</sub> |
| <sub>47</sub> | <sub>`Bow`</sub> | <sub>PrimalItem_WeaponBow</sub> | <sub>Bow_Icon</sub> | <sub>weapon（工具/武器）</sub> | <sub>**弓**</sub> | <sub>PO</sub> | <sub>PO#1487848754 "Bow"</sub> |
| <sub>48</sub> | <sub>`CakeSlice`</sub> | <sub>PrimalItemResource_CakeSlice</sub> | <sub>CakeSlice_Icon</sub> | <sub>resource（资源/材料）</sub> | <sub>**一块蛋糕**</sub> | <sub>zhmap·英文</sub> | <sub>icon_zh_map[cakeslice_yellow_icon] 英文=CakeSlice</sub> |
| <sub>49</sub> | <sub>`Car_Turret_Flamethrower`</sub> | <sub>PrimalItem_Car_Turret_Flamethrower</sub> | <sub>HUD_Car_Turret_Flamethrower_icon</sub> | <sub>other（其他/未归类）</sub> | <sub>**火焰喷射器炮台**</sub> | <sub>PO词集包含</sub> | <sub>PO#2465803433 "Flamethrower Turret"（词集包含）</sub> |
| <sub>50</sub> | <sub>`Car_Wheels_Racer`</sub> | <sub>PrimalItem_Car_Wheels_Racer</sub> | <sub>—</sub> | <sub>other（其他/未归类）</sub> | <sub>**战车车轮·竞速**</sub> | <sub>人工修正</sub> | <sub>人工修正（直填官方原文）：wiki Engram 表 BattleRig Wheels: Racer → PO#1432815879；官方原</sub> |
| <sub>51</sub> | <sub>`CarnoSaddle`</sub> | <sub>PrimalItemArmor_CarnoSaddle</sub> | <sub>CarnoSaddle</sub> | <sub>saddle（鞍具）</sub> | <sub>**肉食牛龙鞍**</sub> | <sub>zhmap·英文</sub> | <sub>icon_zh_map[hud_thrallcarnosaddle_icon] 英文=CarnoSaddle</sub> |
| <sub>52</sub> | <sub>`CavewolfSaddle`</sub> | <sub>PrimalItemArmor_CavewolfSaddle</sub> | <sub>CaveWolfSaddle_Icon</sub> | <sub>saddle（鞍具）</sub> | <sub>**劫掠者鞍**</sub> | <sub>miss_en</sub> | <sub>缺口英文名 "Ravager Saddle"〔wiki〕→ PO#3020227895</sub> |
| <sub>53</sub> | <sub>`CeratosaurusSaddle_ASA`</sub> | <sub>PrimalItemArmor_CeratosaurusSaddle_ASA</sub> | <sub>Ceratosaurus_Saddle</sub> | <sub>saddle（鞍具）</sub> | <sub>**角鼻龙鞍**</sub> | <sub>zhmap·英文</sub> | <sub>icon_zh_map[ceratosaurus saddle] 英文=CeratosaurusSaddle</sub> |
| <sub>54</sub> | <sub>`ChainSaw_Cursed`</sub> | <sub>PrimalItem_ChainSaw_Cursed</sub> | <sub>—</sub> | <sub>other（其他/未归类）</sub> | <sub>**咒缚电锯**</sub> | <sub>人工修正</sub> | <sub>人工修正：英文 "Cursed Chainsaw" → PO#115776394</sub> |
| <sub>55</sub> | <sub>`ChalicoSaddle`</sub> | <sub>PrimalItemArmor_ChalicoSaddle</sub> | <sub>—</sub> | <sub>saddle（鞍具）</sub> | <sub>**爪兽鞍**</sub> | <sub>wiki英文名→PO</sub> | <sub>wiki 英文名 "Chalicotherium Saddle" → PO#940456464</sub> |
| <sub>56</sub> | <sub>`Charcoal_ShoulderDragonCraftable`</sub> | <sub>PrimalItemResource_Charcoal_ShoulderDragonCraftable</sub> | <sub>—</sub> | <sub>resource（资源/材料）</sub> | <sub>**煤炭**</sub> | <sub>miss_en</sub> | <sub>缺口英文名 "Charcoal"〔po~〕→ PO#2294449264</sub> |
| <sub>57</sub> | <sub>`CherufeSaddle`</sub> | <sub>PrimalItemArmor_CherufeSaddle</sub> | <sub>HUD_CherufeSaddle_Icon</sub> | <sub>saddle（鞍具）</sub> | <sub>**熔岩龙鞍**</sub> | <sub>wiki英文名→PO</sub> | <sub>wiki 英文名 "Magmasaur Saddle" → PO#4051512508</sub> |
| <sub>58</sub> | <sub>`ChitinPants`</sub> | <sub>PrimalItemArmor_ChitinPants</sub> | <sub>ChitinPants</sub> | <sub>armor（服饰/护甲）</sub> | <sub>**甲壳腿**</sub> | <sub>wiki英文名→PO</sub> | <sub>wiki 英文名 "Chitin Leggings" → PO#1489043677</sub> |
| <sub>59</sub> | <sub>`ChitinShirt`</sub> | <sub>PrimalItemArmor_ChitinShirt</sub> | <sub>ChitinShirt</sub> | <sub>armor（服饰/护甲）</sub> | <sub>**甲壳胸甲**</sub> | <sub>wiki英文名→PO</sub> | <sub>wiki 英文名 "Chitin Chestpiece" → PO#2133775597</sub> |
| <sub>60</sub> | <sub>`ClimbPick`</sub> | <sub>PrimalItem_WeaponClimbPick</sub> | <sub>—</sub> | <sub>weapon（工具/武器）</sub> | <sub>**登山镐**</sub> | <sub>miss_en</sub> | <sub>缺口英文名 "Climbing Pick"〔wiki〕→ PO#2080980815</sub> |
| <sub>61</sub> | <sub>`CorruptedPolymer`</sub> | <sub>PrimalItemResource_CorruptedPolymer</sub> | <sub>—</sub> | <sub>resource（资源/材料）</sub> | <sub>**腐化瘤**</sub> | <sub>miss_en</sub> | <sub>缺口英文名 "Corrupted Nodule"〔wiki〕→ PO#2579690850</sub> |
| <sub>62</sub> | <sub>`CrabSaddle`</sub> | <sub>PrimalItemArmor_CrabSaddle</sub> | <sub>CrabSaddle_Icon</sub> | <sub>saddle（鞍具）</sub> | <sub>**巨蟹鞍**</sub> | <sub>wiki英文名→PO</sub> | <sub>wiki 英文名 "Karkinos Saddle" → PO#1679099542</sub> |
| <sub>63</sub> | <sub>`Crossbow_Fab`</sub> | <sub>PrimalItem_WeaponCrossbow_Fab</sub> | <sub>—</sub> | <sub>weapon（工具/武器）</sub> | <sub>**十字弩**</sub> | <sub>zhmap·英文</sub> | <sub>icon_zh_map[statusicon_bustedcross] 英文=Crossbow</sub> |
| <sub>64</sub> | <sub>`Deinosuchus_Saddle_ASA`</sub> | <sub>PrimalItemArmor_Deinosuchus_Saddle_ASA</sub> | <sub>HUD_DeinosuchusSaddle_Icon</sub> | <sub>saddle（鞍具）</sub> | <sub>**恐鳄鞍**</sub> | <sub>zhmap·英文</sub> | <sub>icon_zh_map[hud_deinosuchussaddle_icon] 英文=Deinosuchus_Saddle</sub> |
| <sub>65</sub> | <sub>`DeinotheriumSaddle_ASA`</sub> | <sub>PrimalItemArmor_DeinotheriumSaddle_ASA</sub> | <sub>Deinotherium_Saddle</sub> | <sub>saddle（鞍具）</sub> | <sub>**恐象鞍**</sub> | <sub>zhmap·英文</sub> | <sub>icon_zh_map[deinotherium saddle] 英文=DeinotheriumSaddle</sub> |
| <sub>66</sub> | <sub>`DevilFoxSaddle`</sub> | <sub>PrimalItemArmor_DevilFoxSaddle</sub> | <sub>HUD_DevilFoxSaddle_Icon</sub> | <sub>saddle（鞍具）</sub> | <sub>**诡狱狐鞍**</sub> | <sub>miss_en</sub> | <sub>缺口英文名 "Malwyn Saddle"〔wiki~〕→ PO#1302227265</sub> |
| <sub>67</sub> | <sub>`DinoCompanionSaddle_Doggo`</sub> | <sub>PrimalItemArmor_DinoCompanionSaddle_Doggo</sub> | <sub>—</sub> | <sub>saddle（鞍具）</sub> | <sub>**铠护犬护甲**</sub> | <sub>人工修正</sub> | <sub>人工修正（直填官方原文）：wiki Engram 表 Armadoggo Armor → PO#3867906477；官方名不含「鞍」→ 直</sub> |
| <sub>68</sub> | <sub>`DinoCompanion_Gear_AmmoBox`</sub> | <sub>PrimalItemArmor_DinoCompanion_Gear_AmmoBox</sub> | <sub>—</sub> | <sub>armor（服饰/护甲）</sub> | <sub>**随伴的弹药箱**</sub> | <sub>PO词集包含</sub> | <sub>PO#1856556997 "Companion Ammo Box"（词集包含）</sub> |
| <sub>69</sub> | <sub>`DinoCompanion_Gear_Medkit`</sub> | <sub>PrimalItemArmor_DinoCompanion_Gear_Medkit</sub> | <sub>—</sub> | <sub>armor（服饰/护甲）</sub> | <sub>**随伴的医疗包**</sub> | <sub>miss_en</sub> | <sub>缺口英文名 "Companion Medpack"〔wiki~〕→ PO#1412001096</sub> |
| <sub>70</sub> | <sub>`DiplodocusSaddle`</sub> | <sub>PrimalItemArmor_DiplodocusSaddle</sub> | <sub>DiplodocusSaddle</sub> | <sub>saddle（鞍具）</sub> | <sub>**梁龙鞍**</sub> | <sub>zhmap·英文</sub> | <sub>icon_zh_map[diplodocus saddle] 英文=DiplodocusSaddle</sub> |
| <sub>71</sub> | <sub>`DoedSaddle`</sub> | <sub>PrimalItemArmor_DoedSaddle</sub> | <sub>—</sub> | <sub>saddle（鞍具）</sub> | <sub>**星尾兽鞍**</sub> | <sub>wiki英文名→PO</sub> | <sub>wiki 英文名 "Doedicurus Saddle" → PO#3037103986</sub> |
| <sub>72</sub> | <sub>`DolphinSaddle`</sub> | <sub>PrimalItemArmor_DolphinSaddle</sub> | <sub>DolphinSaddle</sub> | <sub>saddle（鞍具）</sub> | <sub>**鱼龙鞍**</sub> | <sub>人工修正</sub> | <sub>人工修正：英文 "Ichthyosaurus Saddle" → PO#523661452</sub> |
| <sub>73</sub> | <sub>`DreadSaddle_Platform`</sub> | <sub>PrimalItemArmor_DreadSaddle_Platform</sub> | <sub>—</sub> | <sub>saddle（鞍具）</sub> | <sub>**无畏巨龙平台鞍**</sub> | <sub>miss_en</sub> | <sub>缺口英文名 "Dreadnoughtus Platform Saddle"〔wiki~〕→ PO#3623615537</sub> |
| <sub>74</sub> | <sub>`FasolaSaddle`</sub> | <sub>PrimalItemArmor_FasolaSaddle</sub> | <sub>—</sub> | <sub>saddle（鞍具）</sub> | <sub>**法索拉鳄鞍**</sub> | <sub>学名重组→PO</sub> | <sub>学名重组 Fasolasuchus + Saddle → PO#2415986226 "Fasolasuchus Saddle"</sub> |
| <sub>75</sub> | <sub>`FracturedGem`</sub> | <sub>PrimalItemResource_FracturedGem</sub> | <sub>—</sub> | <sub>resource（资源/材料）</sub> | <sub>**碎裂的绿宝石**</sub> | <sub>miss_en</sub> | <sub>缺口英文名 "Fragmented Green Gem"〔wiki〕→ PO#3450708307</sub> |
| <sub>76</sub> | <sub>`GasBagsSaddle`</sub> | <sub>PrimalItemArmor_GasBagsSaddle</sub> | <sub>HUD_GasBagsSaddle_Icon</sub> | <sub>saddle（鞍具）</sub> | <sub>**气囊虫鞍**</sub> | <sub>zhmap·英文</sub> | <sub>icon_zh_map[hud_gasbagssaddle_icon (2)] 英文=GasBagsSaddle</sub> |
| <sub>77</sub> | <sub>`Gasoline_Super`</sub> | <sub>PrimalItemResource_Gasoline_Super</sub> | <sub>Gasoline</sub> | <sub>resource（资源/材料）</sub> | <sub>**汽油**</sub> | <sub>zhmap·英文</sub> | <sub>icon_zh_map[gasoline] 英文=Gasoline</sub> |
| <sub>78</sub> | <sub>`Gem_BioLum`</sub> | <sub>PrimalItemResource_Gem_BioLum</sub> | <sub>Gem_Icon</sub> | <sub>resource（资源/材料）</sub> | <sub>**蓝宝石**</sub> | <sub>miss_en</sub> | <sub>缺口英文名 "Blue Gem"〔wiki〕→ PO#1297948651</sub> |
| <sub>79</sub> | <sub>`Gem_Element`</sub> | <sub>PrimalItemResource_Gem_Element</sub> | <sub>—</sub> | <sub>resource（资源/材料）</sub> | <sub>**元素矿石**</sub> | <sub>人工修正</sub> | <sub>人工修正：英文 "Element Ore" → PO#225063773</sub> |
| <sub>80</sub> | <sub>`Gem_Fertile`</sub> | <sub>PrimalItemResource_Gem_Fertile</sub> | <sub>—</sub> | <sub>resource（资源/材料）</sub> | <sub>**绿宝石**</sub> | <sub>miss_en</sub> | <sub>缺口英文名 "Green Gem"〔wiki〕→ PO#928914563</sub> |
| <sub>81</sub> | <sub>`GhillieBoots`</sub> | <sub>PrimalItemArmor_GhillieBoots</sub> | <sub>GhillieBoots</sub> | <sub>armor（服饰/护甲）</sub> | <sub>**吉利靴**</sub> | <sub>zhmap·英文</sub> | <sub>icon_zh_map[ghillie boots] 英文=GhillieBoots</sub> |
| <sub>82</sub> | <sub>`GhillieGloves`</sub> | <sub>PrimalItemArmor_GhillieGloves</sub> | <sub>GhillieGloves</sub> | <sub>armor（服饰/护甲）</sub> | <sub>**吉利手套**</sub> | <sub>wiki英文名→PO</sub> | <sub>wiki 英文名 "Ghillie Gauntlets" → PO#215941634</sub> |
| <sub>83</sub> | <sub>`GhilliePants`</sub> | <sub>PrimalItemArmor_GhilliePants</sub> | <sub>GhilliePants</sub> | <sub>armor（服饰/护甲）</sub> | <sub>**吉利护腿**</sub> | <sub>wiki英文名→PO</sub> | <sub>wiki 英文名 "Ghillie Leggings" → PO#2007378845</sub> |
| <sub>84</sub> | <sub>`GhillieShirt`</sub> | <sub>PrimalItemArmor_GhillieShirt</sub> | <sub>GhillieShirt</sub> | <sub>armor（服饰/护甲）</sub> | <sub>**吉利胸甲**</sub> | <sub>wiki英文名→PO</sub> | <sub>wiki 英文名 "Ghillie Chestpiece" → PO#3446275153</sub> |
| <sub>85</sub> | <sub>`GiantTurtleSaddle`</sub> | <sub>PrimalItemArmor_GiantTurtleSaddle</sub> | <sub>HUD_GiantTurtleSaddle_Icon</sub> | <sub>saddle（鞍具）</sub> | <sub>**古巨龟鞍**</sub> | <sub>人工修正</sub> | <sub>人工修正：英文 "Archelon Saddle" → PO#845425771</sub> |
| <sub>86</sub> | <sub>`GigantSaddle`</sub> | <sub>PrimalItemArmor_GigantSaddle</sub> | <sub>—</sub> | <sub>saddle（鞍具）</sub> | <sub>**南方巨兽龙鞍**</sub> | <sub>wiki英文名→PO</sub> | <sub>wiki 英文名 "Giganotosaurus Saddle" → PO#4029543187</sub> |
| <sub>87</sub> | <sub>`Glider`</sub> | <sub>PrimalItemArmor_Glider</sub> | <sub>—</sub> | <sub>armor（服饰/护甲）</sub> | <sub>**滑翔翼**</sub> | <sub>miss_en</sub> | <sub>缺口英文名 "Glider Suit"〔wiki~〕→ PO#2641584737</sub> |
| <sub>88</sub> | <sub>`Grapeshot_ToF`</sub> | <sub>PrimalItemAmmo_Grapeshot_ToF</sub> | <sub>—</sub> | <sub>ammo（弹药/投掷物）</sub> | <sub>**霰弹炮弹**</sub> | <sub>miss_en</sub> | <sub>缺口英文名 "Grapeshot"〔po~〕→ PO#2740374280</sub> |
| <sub>89</sub> | <sub>`Gun`</sub> | <sub>PrimalItem_WeaponGun</sub> | <sub>—</sub> | <sub>weapon（工具/武器）</sub> | <sub>**简易手枪**</sub> | <sub>miss_en</sub> | <sub>缺口英文名 "Simple Pistol"〔wiki〕→ PO#2445226388</sub> |
| <sub>90</sub> | <sub>`Harpoon`</sub> | <sub>PrimalItem_WeaponHarpoon</sub> | <sub>—</sub> | <sub>weapon（工具/武器）</sub> | <sub>**鱼叉枪**</sub> | <sub>miss_en</sub> | <sub>缺口英文名 "Harpoon Launcher"〔wiki〕→ PO#3522260907</sub> |
| <sub>91</sub> | <sub>`Harpoon_Cursed`</sub> | <sub>PrimalItem_WeaponHarpoon_Cursed</sub> | <sub>—</sub> | <sub>weapon（工具/武器）</sub> | <sub>**咒缚鱼叉枪**</sub> | <sub>人工修正</sub> | <sub>人工修正（直填官方原文）：PO 无 Cursed Harpoon 条目；按 Cursed 系列官方统一译法「咒缚」（共 28 条）+ 基础名</sub> |
| <sub>92</sub> | <sub>`HazardSuitGloves`</sub> | <sub>PrimalItemArmor_HazardSuitGloves</sub> | <sub>HazardSuitGloves_Icon</sub> | <sub>armor（服饰/护甲）</sub> | <sub>**防护手套**</sub> | <sub>zhmap·英文</sub> | <sub>icon_zh_map[hazard suit gloves] 英文=HazardSuitGloves</sub> |
| <sub>93</sub> | <sub>`HexCoins`</sub> | <sub>PrimalItemResource_HexCoins</sub> | <sub>—</sub> | <sub>resource（资源/材料）</sub> | <sub>**六角币**</sub> | <sub>miss_en</sub> | <sub>缺口英文名 "Hexagons"〔wiki~〕→ PO#3460530355</sub> |
| <sub>94</sub> | <sub>`Horn`</sub> | <sub>PrimalItemResource_Horn</sub> | <sub>—</sub> | <sub>resource（资源/材料）</sub> | <sub>**披毛犀角**</sub> | <sub>miss_en</sub> | <sub>缺口英文名 "Woolly Rhino Horn"〔wiki〕→ PO#4154522713</sub> |
| <sub>95</sub> | <sub>`IceBox`</sub> | <sub>PrimalItemStructure_IceBox</sub> | <sub>—</sub> | <sub>structure（建筑构件）</sub> | <sub>**冰箱**</sub> | <sub>miss_en</sub> | <sub>缺口英文名 "Refrigerator"〔wiki〕→ PO#3002947083</sub> |
| <sub>96</sub> | <sub>`IceJumperSaddle`</sub> | <sub>PrimalItemArmor_IceJumperSaddle</sub> | <sub>HUD_IceJumperSaddle_Icon</sub> | <sub>saddle（鞍具）</sub> | <sub>**玛纳加尔姆鞍**</sub> | <sub>人工修正</sub> | <sub>人工修正：英文 "Managarmr Saddle" → PO#3722005927</sub> |
| <sub>97</sub> | <sub>`KeratinSpike`</sub> | <sub>PrimalItemResource_KeratinSpike</sub> | <sub>—</sub> | <sub>resource（资源/材料）</sub> | <sub>**死亡蠕虫角**</sub> | <sub>wiki英文名→PO</sub> | <sub>wiki 英文名 "Deathworm Horn" → PO#1074591884</sub> |
| <sub>98</sub> | <sub>`LostColony_AberrantSigil_Greater`</sub> | <sub>PrimalItemResource_LostColony_AberrantSigil_Greater</sub> | <sub>—</sub> | <sub>resource（资源/材料）</sub> | <sub>**强力异常魔符**</sub> | <sub>PO词集包含</sub> | <sub>PO#3464824013 "Greater Aberrant Sigil"（词集包含）</sub> |
| <sub>99</sub> | <sub>`LostColony_AberrantSigil_Minor`</sub> | <sub>PrimalItemResource_LostColony_AberrantSigil_Minor</sub> | <sub>—</sub> | <sub>resource（资源/材料）</sub> | <sub>**弱效异常魔符**</sub> | <sub>PO词集包含</sub> | <sub>PO#3075242502 "Minor Aberrant Sigil"（词集包含）</sub> |
| <sub>100</sub> | <sub>`LostColony_AberrantSigil_Prime`</sub> | <sub>PrimalItemResource_LostColony_AberrantSigil_Prime</sub> | <sub>—</sub> | <sub>resource（资源/材料）</sub> | <sub>**本源异常魔符**</sub> | <sub>PO词集包含</sub> | <sub>PO#4194110584 "Prime Aberrant Sigil"（词集包含）</sub> |
| <sub>101</sub> | <sub>`LostColony_CrimsonSigil_Greater`</sub> | <sub>PrimalItemResource_LostColony_CrimsonSigil_Greater</sub> | <sub>—</sub> | <sub>resource（资源/材料）</sub> | <sub>**强力绯红魔符**</sub> | <sub>PO词集包含</sub> | <sub>PO#820366753 "Greater Crimson Sigil"（词集包含）</sub> |
| <sub>102</sub> | <sub>`LostColony_CrimsonSigil_Minor`</sub> | <sub>PrimalItemResource_LostColony_CrimsonSigil_Minor</sub> | <sub>—</sub> | <sub>resource（资源/材料）</sub> | <sub>**弱效绯红魔符**</sub> | <sub>PO词集包含</sub> | <sub>PO#2782338524 "Minor Crimson Sigil"（词集包含）</sub> |
| <sub>103</sub> | <sub>`LostColony_CrimsonSigil_Prime`</sub> | <sub>PrimalItemResource_LostColony_CrimsonSigil_Prime</sub> | <sub>—</sub> | <sub>resource（资源/材料）</sub> | <sub>**本源绯红魔符**</sub> | <sub>PO词集包含</sub> | <sub>PO#3238216647 "Prime Crimson Sigil"（词集包含）</sub> |
| <sub>104</sub> | <sub>`LostColony_RedElement`</sub> | <sub>PrimalItemResource_LostColony_RedElement</sub> | <sub>—</sub> | <sub>resource（资源/材料）</sub> | <sub>**腥红能量元素**</sub> | <sub>人工修正</sub> | <sub>人工修正：英文 "Red Element" → PO#1046621605</sub> |
| <sub>105</sub> | <sub>`LostColony_RedElementDustFromRedElement`</sub> | <sub>PrimalItemResource_LostColony_RedElementDustFromRedElement</sub> | <sub>—</sub> | <sub>resource（资源/材料）</sub> | <sub>**磨制的腥红元素粉尘**</sub> | <sub>人工修正</sub> | <sub>人工修正：英文 "Crafted Red Element Dust" → PO#429374680</sub> |
| <sub>106</sub> | <sub>`LostColony_RedElementDustFromShards`</sub> | <sub>PrimalItemResource_LostColony_RedElementDustFromShards</sub> | <sub>—</sub> | <sub>resource（资源/材料）</sub> | <sub>**腥红元素粉尘**</sub> | <sub>人工修正</sub> | <sub>人工修正：英文 "Red Element Dust" → PO#1156378742</sub> |
| <sub>107</sub> | <sub>`LostColony_RedElementFromShards`</sub> | <sub>PrimalItemResource_LostColony_RedElementFromShards</sub> | <sub>—</sub> | <sub>resource（资源/材料）</sub> | <sub>**不稳定的腥红能量元素**</sub> | <sub>人工修正</sub> | <sub>人工修正：英文 "Unstable Red Element" → PO#695169902</sub> |
| <sub>108</sub> | <sub>`LostColony_RedElementRefined`</sub> | <sub>PrimalItemResource_LostColony_RedElementRefined</sub> | <sub>—</sub> | <sub>resource（资源/材料）</sub> | <sub>**不稳定的腥红能量元素**</sub> | <sub>人工修正</sub> | <sub>人工修正：英文 "Unstable Red Element" → PO#695169902</sub> |
| <sub>109</sub> | <sub>`LostColony_RedElementShard`</sub> | <sub>PrimalItemResource_LostColony_RedElementShard</sub> | <sub>—</sub> | <sub>resource（资源/材料）</sub> | <sub>**腥红元素碎片**</sub> | <sub>人工修正</sub> | <sub>人工修正：英文 "Red Element Shard" → PO#625541412</sub> |
| <sub>110</sub> | <sub>`LostColony_RedElement_ShardRefined`</sub> | <sub>PrimalItemResource_LostColony_RedElement_ShardRefined</sub> | <sub>—</sub> | <sub>resource（资源/材料）</sub> | <sub>**不稳定的腥红元素碎片**</sub> | <sub>人工修正</sub> | <sub>人工修正：英文 "Unstable Red Element Shard" → PO#4248662073</sub> |
| <sub>111</sub> | <sub>`LostColony_RefinedRedElementFromDust`</sub> | <sub>PrimalItemResource_LostColony_RefinedRedElementFromDust</sub> | <sub>—</sub> | <sub>resource（资源/材料）</sub> | <sub>**不稳定的腥红能量元素**</sub> | <sub>人工修正</sub> | <sub>人工修正：英文 "Unstable Red Element" → PO#695169902</sub> |
| <sub>112</sub> | <sub>`MachinedSniper`</sub> | <sub>PrimalItem_WeaponMachinedSniper</sub> | <sub>—</sub> | <sub>weapon（工具/武器）</sub> | <sub>**制式狙击步枪**</sub> | <sub>miss_en</sub> | <sub>缺口英文名 "Fabricated Sniper Rifle"〔wiki〕→ PO#3598536060</sub> |
| <sub>113</sub> | <sub>`MachinedSniper_Cursed`</sub> | <sub>PrimalItem_WeaponMachinedSniper_Cursed</sub> | <sub>—</sub> | <sub>weapon（工具/武器）</sub> | <sub>**咒缚制式狙击步枪**</sub> | <sub>人工修正</sub> | <sub>人工修正：英文 "Cursed Fabricated Sniper Rifle" → PO#215826814</sub> |
| <sub>114</sub> | <sub>`MaelizardSaddle`</sub> | <sub>PrimalItemArmor_MaelizardSaddle</sub> | <sub>—</sub> | <sub>saddle（鞍具）</sub> | <sub>**风行蜥鞍**</sub> | <sub>miss_en</sub> | <sub>缺口英文名 "Maeguana Saddle"〔wiki~〕→ PO#1176090794</sub> |
| <sub>115</sub> | <sub>`MammothSaddle`</sub> | <sub>PrimalItemArmor_MammothSaddle</sub> | <sub>MammothSaddle</sub> | <sub>saddle（鞍具）</sub> | <sub>**猛犸象鞍**</sub> | <sub>zhmap·英文</sub> | <sub>icon_zh_map[mammoth saddle] 英文=MammothSaddle</sub> |
| <sub>116</sub> | <sub>`MegalodonSaddle_Tek`</sub> | <sub>PrimalItemArmor_MegalodonSaddle_Tek</sub> | <sub>MegalodonSaddle</sub> | <sub>saddle（鞍具）</sub> | <sub>**巨齿鲨鞍**</sub> | <sub>zhmap·英文</sub> | <sub>icon_zh_map[megalodonsaddle] 英文=MegalodonSaddle</sub> |
| <sub>117</sub> | <sub>`MegatheriumSaddle`</sub> | <sub>PrimalItemArmor_MegatheriumSaddle</sub> | <sub>MegatheriumSaddle</sub> | <sub>saddle（鞍具）</sub> | <sub>**大地懒鞍**</sub> | <sub>zhmap·英文</sub> | <sub>icon_zh_map[hud_thrallmegatheriumsaddle_icon] 英文=MegatheriumSaddle</sub> |
| <sub>118</sub> | <sub>`MetalBoots`</sub> | <sub>PrimalItemArmor_MetalBoots</sub> | <sub>MetalBoots</sub> | <sub>armor（服饰/护甲）</sub> | <sub>**防弹靴**</sub> | <sub>wiki英文名→PO</sub> | <sub>wiki 英文名 "Flak Boots" → PO#3970840742</sub> |
| <sub>119</sub> | <sub>`MetalFloor`</sub> | <sub>PrimalItemStructure_MetalFloor</sub> | <sub>MetalFloor_Icon</sub> | <sub>structure（建筑构件）</sub> | <sub>**金属地板**</sub> | <sub>PO</sub> | <sub>PO#2011022361 "Metal Floor"</sub> |
| <sub>120</sub> | <sub>`MetalGloves`</sub> | <sub>PrimalItemArmor_MetalGloves</sub> | <sub>MetalGloves</sub> | <sub>armor（服饰/护甲）</sub> | <sub>**防弹手套**</sub> | <sub>wiki英文名→PO</sub> | <sub>wiki 英文名 "Flak Gauntlets" → PO#3197291869</sub> |
| <sub>121</sub> | <sub>`MetalPants`</sub> | <sub>PrimalItemArmor_MetalPants</sub> | <sub>MetalPants</sub> | <sub>armor（服饰/护甲）</sub> | <sub>**防弹护腿**</sub> | <sub>wiki英文名→PO</sub> | <sub>wiki 英文名 "Flak Leggings" → PO#1552565199</sub> |
| <sub>122</sub> | <sub>`MetalShirt`</sub> | <sub>PrimalItemArmor_MetalShirt</sub> | <sub>MetalShirt</sub> | <sub>armor（服饰/护甲）</sub> | <sub>**防弹胸甲**</sub> | <sub>wiki英文名→PO</sub> | <sub>wiki 英文名 "Flak Chestpiece" → PO#2756497712</sub> |
| <sub>123</sub> | <sub>`MinersHelmet`</sub> | <sub>PrimalItemArmor_MinersHelmet</sub> | <sub>—</sub> | <sub>armor（服饰/护甲）</sub> | <sub>**沉重的矿工安全帽**</sub> | <sub>wiki英文名→PO</sub> | <sub>wiki 英文名 "Heavy Miner's Helmet" → PO#1040790786</sub> |
| <sub>124</sub> | <sub>`MoleRatSaddle`</sub> | <sub>PrimalItemArmor_MoleRatSaddle</sub> | <sub>MoleRatSaddle_Icon</sub> | <sub>saddle（鞍具）</sub> | <sub>**翻滚鼠鞍**</sub> | <sub>人工修正</sub> | <sub>人工修正：英文 "Roll Rat Saddle" → PO#2127308872</sub> |
| <sub>125</sub> | <sub>`MosaSaddle`</sub> | <sub>PrimalItemArmor_MosaSaddle</sub> | <sub>—</sub> | <sub>saddle（鞍具）</sub> | <sub>**沧龙鞍**</sub> | <sub>miss_en</sub> | <sub>缺口英文名 "Mosasaur Saddle"〔wiki〕→ PO#847096388</sub> |
| <sub>126</sub> | <sub>`MosaSaddle_Platform`</sub> | <sub>PrimalItemArmor_MosaSaddle_Platform</sub> | <sub>—</sub> | <sub>saddle（鞍具）</sub> | <sub>**沧龙平台鞍**</sub> | <sub>miss_en</sub> | <sub>缺口英文名 "Mosasaur Platform Saddle"〔wiki〕→ PO#1943117669</sub> |
| <sub>127</sub> | <sub>`MothSaddle`</sub> | <sub>PrimalItemArmor_MothSaddle</sub> | <sub>MothSaddle_Icon</sub> | <sub>saddle（鞍具）</sub> | <sub>**沙蛾鞍**</sub> | <sub>wiki英文名→PO</sub> | <sub>wiki 英文名 "Lymantria Saddle" → PO#630720760</sub> |
| <sub>128</sub> | <sub>`OneShotRifle`</sub> | <sub>PrimalItem_WeaponOneShotRifle</sub> | <sub>—</sub> | <sub>weapon（工具/武器）</sub> | <sub>**长管步枪**</sub> | <sub>miss_en</sub> | <sub>缺口英文名 "Longneck Rifle"〔wiki〕→ PO#4084757226</sub> |
| <sub>129</sub> | <sub>`OwlSaddle`</sub> | <sub>PrimalItemArmor_OwlSaddle</sub> | <sub>HUD_OwlSaddle_Icon</sub> | <sub>saddle（鞍具）</sub> | <sub>**雪鸮鞍**</sub> | <sub>miss_en</sub> | <sub>缺口英文名 "Snow Owl Saddle"〔wiki〕→ PO#697481476</sub> |
| <sub>130</sub> | <sub>`PachyrhinoSaddle`</sub> | <sub>PrimalItemArmor_PachyrhinoSaddle</sub> | <sub>—</sub> | <sub>saddle（鞍具）</sub> | <sub>**厚鼻龙鞍**</sub> | <sub>wiki英文名→PO</sub> | <sub>wiki 英文名 "Pachyrhinosaurus Saddle" → PO#790898238</sub> |
| <sub>131</sub> | <sub>`ParaSaddle`</sub> | <sub>PrimalItemArmor_ParaSaddle</sub> | <sub>—</sub> | <sub>saddle（鞍具）</sub> | <sub>**副栉龙鞍**</sub> | <sub>wiki英文名→PO</sub> | <sub>wiki 英文名 "Parasaur Saddle" → PO#1444062004</sub> |
| <sub>132</sub> | <sub>`ParacerSaddle_Platform`</sub> | <sub>PrimalItemArmor_ParacerSaddle_Platform</sub> | <sub>—</sub> | <sub>saddle（鞍具）</sub> | <sub>**巨犀鞍**</sub> | <sub>zhmap·英文</sub> | <sub>icon_zh_map[paracersaddle] 英文=ParacerSaddle</sub> |
| <sub>133</sub> | <sub>`PelaSaddle`</sub> | <sub>PrimalItemArmor_PelaSaddle</sub> | <sub>—</sub> | <sub>saddle（鞍具）</sub> | <sub>**伪齿鸟鞍**</sub> | <sub>wiki英文名→PO</sub> | <sub>wiki 英文名 "Pelagornis Saddle" → PO#2404987875</sub> |
| <sub>134</sub> | <sub>`Pike_Cursed`</sub> | <sub>PrimalItem_WeaponPike_Cursed</sub> | <sub>Pike_Icon</sub> | <sub>weapon（工具/武器）</sub> | <sub>**咒缚金属矛**</sub> | <sub>人工修正</sub> | <sub>人工修正：英文 "Cursed Pike" → PO#29509946</sub> |
| <sub>135</sub> | <sub>`PlesiSaddle_Platform`</sub> | <sub>PrimalItemArmor_PlesiSaddle_Platform</sub> | <sub>—</sub> | <sub>saddle（鞍具）</sub> | <sub>**蛇颈龙平台鞍**</sub> | <sub>miss_en</sub> | <sub>缺口英文名 "Plesiosaur Platform Saddle"〔wiki〕→ PO#3965605178</sub> |
| <sub>136</sub> | <sub>`PlesiaSaddle`</sub> | <sub>PrimalItemArmor_PlesiaSaddle</sub> | <sub>—</sub> | <sub>saddle（鞍具）</sub> | <sub>**蛇颈龙鞍**</sub> | <sub>wiki英文名→PO</sub> | <sub>wiki 英文名 "Plesiosaur Saddle" → PO#339785845</sub> |
| <sub>137</sub> | <sub>`PoisonTrap`</sub> | <sub>PrimalItem_WeaponPoisonTrap</sub> | <sub>PoisonTrap_Icon</sub> | <sub>weapon（工具/武器）</sub> | <sub>**绊线麻醉陷阱**</sub> | <sub>miss_en</sub> | <sub>缺口英文名 "Tripwire Narcotic Trap"〔wiki〕→ PO#2805580840</sub> |
| <sub>138</sub> | <sub>`Polymer_Organic`</sub> | <sub>PrimalItemResource_Polymer_Organic</sub> | <sub>Polymer</sub> | <sub>resource（资源/材料）</sub> | <sub>**有机聚合物**</sub> | <sub>wiki英文名→PO</sub> | <sub>wiki 英文名 "Organic Polymer" → PO#105127878</sub> |
| <sub>139</sub> | <sub>`PrimalItemC4Ammo`</sub> | <sub>PrimalItemC4Ammo</sub> | <sub>—</sub> | <sub>ammo（弹药/投掷物）</sub> | <sub>**C4炸药**</sub> | <sub>miss_en</sub> | <sub>缺口英文名 "C4 Charge"〔wiki~〕→ PO#419208884</sub> |
| <sub>140</sub> | <sub>`PrimalItemConsumableMiracleGro`</sub> | <sub>PrimalItemConsumableMiracleGro</sub> | <sub>—</sub> | <sub>consumable（消耗品）</sub> | <sub>**稀土肥料**</sub> | <sub>miss_en</sub> | <sub>缺口英文名 "Re-Fertilizer"〔wiki~〕→ PO#849107519</sub> |
| <sub>141</sub> | <sub>`PrimalItemConsumableSoap`</sub> | <sub>PrimalItemConsumableSoap</sub> | <sub>—</sub> | <sub>consumable（消耗品）</sub> | <sub>**肥皂**</sub> | <sub>miss_en</sub> | <sub>缺口英文名 "Soap"〔po〕→ PO#546489347</sub> |
| <sub>142</sub> | <sub>`Prod`</sub> | <sub>PrimalItem_WeaponProd</sub> | <sub>—</sub> | <sub>weapon（工具/武器）</sub> | <sub>**电击棒**</sub> | <sub>miss_en</sub> | <sub>缺口英文名 "Electric Prod"〔wiki〕→ PO#3738309459</sub> |
| <sub>143</sub> | <sub>`PteroSaddle`</sub> | <sub>PrimalItemArmor_PteroSaddle</sub> | <sub>—</sub> | <sub>saddle（鞍具）</sub> | <sub>**无齿翼龙鞍**</sub> | <sub>wiki英文名→PO</sub> | <sub>wiki 英文名 "Pteranodon Saddle" → PO#2381472651</sub> |
| <sub>144</sub> | <sub>`QuetzSaddle_Platform`</sub> | <sub>PrimalItemArmor_QuetzSaddle_Platform</sub> | <sub>—</sub> | <sub>saddle（鞍具）</sub> | <sub>**风神翼龙鞍**</sub> | <sub>zhmap·英文</sub> | <sub>icon_zh_map[quetz saddle] 英文=QuetzSaddle</sub> |
| <sub>145</sub> | <sub>`RadioactiveLanternCharge`</sub> | <sub>PrimalItem_WeaponRadioactiveLanternCharge</sub> | <sub>—</sub> | <sub>weapon（工具/武器）</sub> | <sub>**探照灯枪**</sub> | <sub>wiki英文名→PO</sub> | <sub>wiki 英文名 "Charge Lantern" → PO#2979165569</sub> |
| <sub>146</sub> | <sub>`Ramp_Metal`</sub> | <sub>PrimalItemStructure_Ramp_Metal</sub> | <sub>—</sub> | <sub>structure（建筑构件）</sub> | <sub>**金属楼梯**</sub> | <sub>wiki英文名→PO</sub> | <sub>wiki 英文名 "Metal Stairs" → PO#1013187507</sub> |
| <sub>147</sub> | <sub>`RaptorSaddle`</sub> | <sub>PrimalItemArmor_RaptorSaddle</sub> | <sub>RaptorSaddle</sub> | <sub>saddle（鞍具）</sub> | <sub>**迅猛龙鞍**</sub> | <sub>zhmap·英文</sub> | <sub>icon_zh_map[hud_thrallraptorsaddle_icon] 英文=RaptorSaddle</sub> |
| <sub>148</sub> | <sub>`RedSap`</sub> | <sub>PrimalItemResource_RedSap</sub> | <sub>—</sub> | <sub>resource（资源/材料）</sub> | <sub>**红色晶化树脂**</sub> | <sub>miss_en</sub> | <sub>缺口英文名 "Red Crystalized Sap"〔wiki〕→ PO#2005115298</sub> |
| <sub>149</sub> | <sub>`RefinedTranqDart`</sub> | <sub>PrimalItemAmmo_RefinedTranqDart</sub> | <sub>RefinedTranqDart_Icon</sub> | <sub>ammo（弹药/投掷物）</sub> | <sub>**强效麻醉镖**</sub> | <sub>miss_en</sub> | <sub>缺口英文名 "Shocking Tranquilizer Dart"〔wiki〕→ PO#2050344170</sub> |
| <sub>150</sub> | <sub>`RexSaddle_Tek`</sub> | <sub>PrimalItemArmor_RexSaddle_Tek</sub> | <sub>RexSaddle</sub> | <sub>saddle（鞍具）</sub> | <sub>**霸王龙鞍**</sub> | <sub>zhmap·英文</sub> | <sub>icon_zh_map[rexsaddle] 英文=RexSaddle</sub> |
| <sub>151</sub> | <sub>`RhinoSaddle`</sub> | <sub>PrimalItemArmor_RhinoSaddle</sub> | <sub>—</sub> | <sub>saddle（鞍具）</sub> | <sub>**披毛犀鞍**</sub> | <sub>wiki英文名→PO</sub> | <sub>wiki 英文名 "Woolly Rhino Saddle" → PO#1461737112</sub> |
| <sub>152</sub> | <sub>`RhynioSaddle`</sub> | <sub>PrimalItemArmor_RhynioSaddle</sub> | <sub>—</sub> | <sub>saddle（鞍具）</sub> | <sub>**莱尼颚虫鞍**</sub> | <sub>wiki英文名→PO</sub> | <sub>wiki 英文名 "Rhyniognatha Saddle" → PO#3885073566</sub> |
| <sub>153</sub> | <sub>`RockDrakeSaddle_Tek`</sub> | <sub>PrimalItemArmor_RockDrakeSaddle_Tek</sub> | <sub>RockDrakeSaddle_Icon</sub> | <sub>saddle（鞍具）</sub> | <sub>**岩龙鞍**</sub> | <sub>zhmap·英文</sub> | <sub>icon_zh_map[rockdrakesaddle_icon] 英文=RockDrakeSaddle</sub> |
| <sub>154</sub> | <sub>`Rocket`</sub> | <sub>PrimalItemAmmo_Rocket</sub> | <sub>—</sub> | <sub>ammo（弹药/投掷物）</sub> | <sub>**火箭助推榴弹**</sub> | <sub>miss_en</sub> | <sub>缺口英文名 "Rocket Propelled Grenade"〔wiki〕→ PO#1005865161</sub> |
| <sub>155</sub> | <sub>`SaberSaddle`</sub> | <sub>PrimalItemArmor_SaberSaddle</sub> | <sub>—</sub> | <sub>saddle（鞍具）</sub> | <sub>**刃齿虎鞍**</sub> | <sub>wiki英文名→PO</sub> | <sub>wiki 英文名 "Sabertooth Saddle" → PO#1963221141</sub> |
| <sub>156</sub> | <sub>`SauroSaddle`</sub> | <sub>PrimalItemArmor_SauroSaddle</sub> | <sub>—</sub> | <sub>saddle（鞍具）</sub> | <sub>**雷龙鞍**</sub> | <sub>miss_en</sub> | <sub>缺口英文名 "Bronto Saddle"〔wiki〕→ PO#735110025</sub> |
| <sub>157</sub> | <sub>`SauroSaddle_Platform`</sub> | <sub>PrimalItemArmor_SauroSaddle_Platform</sub> | <sub>—</sub> | <sub>saddle（鞍具）</sub> | <sub>**雷龙平台鞍**</sub> | <sub>miss_en</sub> | <sub>缺口英文名 "Bronto Platform Saddle"〔wiki〕→ PO#1822686567</sub> |
| <sub>158</sub> | <sub>`Seed_DefensePlant`</sub> | <sub>PrimalItemConsumable_Seed_DefensePlant</sub> | <sub>—</sub> | <sub>consumable（消耗品）</sub> | <sub>**X异种植物种子**</sub> | <sub>miss_en</sub> | <sub>缺口英文名 "Plant Species X Seed"〔wiki〕→ PO#1567307060</sub> |
| <sub>159</sub> | <sub>`Seed_PlantSpeciesY`</sub> | <sub>PrimalItemConsumable_Seed_PlantSpeciesY</sub> | <sub>—</sub> | <sub>consumable（消耗品）</sub> | <sub>**Y异种植物种子**</sub> | <sub>wiki英文名→PO</sub> | <sub>wiki 英文名 "Plant Species Y Seed" → PO#3696119827</sub> |
| <sub>160</sub> | <sub>`ShastaSaddle_Submarine`</sub> | <sub>PrimalItemArmor_ShastaSaddle_Submarine</sub> | <sub>—</sub> | <sub>saddle（鞍具）</sub> | <sub>**沙斯塔鱼龙潜艇鞍**</sub> | <sub>miss_en</sub> | <sub>缺口英文名 "Shastasaurus Submarine Saddle"〔wiki~〕→ PO#487009765</sub> |
| <sub>161</sub> | <sub>`Sickle`</sub> | <sub>PrimalItem_WeaponSickle</sub> | <sub>—</sub> | <sub>weapon（工具/武器）</sub> | <sub>**金属镰刀**</sub> | <sub>miss_en</sub> | <sub>缺口英文名 "Metal Sickle"〔wiki〕→ PO#489373341</sub> |
| <sub>162</sub> | <sub>`SimpleRifleBullet`</sub> | <sub>PrimalItemAmmo_SimpleRifleBullet</sub> | <sub>—</sub> | <sub>ammo（弹药/投掷物）</sub> | <sub>**简易步枪子弹**</sub> | <sub>wiki英文名→PO</sub> | <sub>wiki 英文名 "Simple Rifle Ammo" → PO#3179262985</sub> |
| <sub>163</sub> | <sub>`SimpleShotgunBullet`</sub> | <sub>PrimalItemAmmo_SimpleShotgunBullet</sub> | <sub>—</sub> | <sub>ammo（弹药/投掷物）</sub> | <sub>**简易霰弹枪子弹**</sub> | <sub>wiki英文名→PO</sub> | <sub>wiki 英文名 "Simple Shotgun Ammo" → PO#1281060293</sub> |
| <sub>164</sub> | <sub>`SnailPaste`</sub> | <sub>PrimalItemResource_SnailPaste</sub> | <sub>—</sub> | <sub>resource（资源/材料）</sub> | <sub>**玛瑙螺分泌物**</sub> | <sub>miss_en</sub> | <sub>缺口英文名 "Achatina Paste"〔wiki〕→ PO#765884418</sub> |
| <sub>165</sub> | <sub>`SnowDragonSaddle`</sub> | <sub>PrimalItemArmor_SnowDragonSaddle</sub> | <sub>HUD_SnowDragonSaddle_Icon</sub> | <sub>saddle（鞍具）</sub> | <sub>**寒辉雪龙鞍**</sub> | <sub>miss_en</sub> | <sub>缺口英文名 "Aureliax Saddle"〔wiki~〕→ PO#3994703988</sub> |
| <sub>166</sub> | <sub>`SnowMonsterSaddle`</sub> | <sub>PrimalItemArmor_SnowMonsterSaddle</sub> | <sub>HUD_SnowMonsterSaddle_Icon</sub> | <sub>saddle（鞍具）</sub> | <sub>**奥西顿鞍**</sub> | <sub>miss_en</sub> | <sub>缺口英文名 "Ossidon Saddle"〔wiki~〕→ PO#2913120029</sub> |
| <sub>167</sub> | <sub>`Spawner_Enforcer`</sub> | <sub>PrimalItem_Spawner_Enforcer</sub> | <sub>—</sub> | <sub>other（其他/未归类）</sub> | <sub>**未组装的执行者**</sub> | <sub>miss_en</sub> | <sub>缺口英文名 "Unassembled Enforcer"〔wiki〕→ PO#918984419</sub> |
| <sub>168</sub> | <sub>`Spawner_Mek`</sub> | <sub>PrimalItem_Spawner_Mek</sub> | <sub>—</sub> | <sub>other（其他/未归类）</sub> | <sub>**未组装的机甲**</sub> | <sub>miss_en</sub> | <sub>缺口英文名 "Unassembled Mek"〔wiki〕→ PO#2616044668</sub> |
| <sub>169</sub> | <sub>`Spear_Explosive`</sub> | <sub>PrimalItem_WeaponSpear_Explosive</sub> | <sub>—</sub> | <sub>weapon（工具/武器）</sub> | <sub>**爆炸长矛**</sub> | <sub>PO词集包含</sub> | <sub>PO#3641243491 "Explosive Spear"（词集包含）</sub> |
| <sub>170</sub> | <sub>`SpindlesSaddle`</sub> | <sub>PrimalItemArmor_SpindlesSaddle</sub> | <sub>HUD_SpindlesSaddle_Icon</sub> | <sub>saddle（鞍具）</sub> | <sub>**刺面龙鞍**</sub> | <sub>wiki英文名→PO</sub> | <sub>wiki 英文名 "Velonasaur Saddle" → PO#1936543023</sub> |
| <sub>171</sub> | <sub>`SpineyLizardSaddle`</sub> | <sub>PrimalItemArmor_SpineyLizardSaddle</sub> | <sub>SpineyLizardSaddle_Icon</sub> | <sub>saddle（鞍具）</sub> | <sub>**棘蜥鞍**</sub> | <sub>miss_en</sub> | <sub>缺口英文名 "Thorny Dragon Saddle"〔wiki〕→ PO#1405578901</sub> |
| <sub>172</sub> | <sub>`SpinoSaddle`</sub> | <sub>PrimalItemArmor_SpinoSaddle</sub> | <sub>SpinoSaddle</sub> | <sub>saddle（鞍具）</sub> | <sub>**棘龙鞍**</sub> | <sub>zhmap·英文</sub> | <sub>icon_zh_map[hud_thrallspinosaddle_icon] 英文=SpinoSaddle</sub> |
| <sub>173</sub> | <sub>`StagSaddle`</sub> | <sub>PrimalItemArmor_StagSaddle</sub> | <sub>StagSaddle</sub> | <sub>saddle（鞍具）</sub> | <sub>**大角鹿鞍**</sub> | <sub>人工修正</sub> | <sub>人工修正：英文 "Megaloceros Saddle" → PO#813774403</sub> |
| <sub>174</sub> | <sub>`TapejaraSaddle`</sub> | <sub>PrimalItemArmor_TapejaraSaddle</sub> | <sub>TapejaraSaddle</sub> | <sub>saddle（鞍具）</sub> | <sub>**古神翼龙鞍**</sub> | <sub>PO</sub> | <sub>PO#153020943 "Tapejara Saddle"</sub> |
| <sub>175</sub> | <sub>`TekSniper`</sub> | <sub>PrimalItem_TekSniper</sub> | <sub>TekSniper_Icon</sub> | <sub>tek（泰克装备）</sub> | <sub>**泰克狙击枪**</sub> | <sub>miss_en</sub> | <sub>缺口英文名 "Tek Railgun"〔wiki〕→ PO#1156211592</sub> |
| <sub>176</sub> | <sub>`TerrorBirdSaddle`</sub> | <sub>PrimalItemArmor_TerrorBirdSaddle</sub> | <sub>TerrorBirdSaddle</sub> | <sub>saddle（鞍具）</sub> | <sub>**骇鸟鞍**</sub> | <sub>PO</sub> | <sub>PO#3029616885 "Terror Bird Saddle"</sub> |
| <sub>177</sub> | <sub>`ThatchFloor`</sub> | <sub>PrimalItemStructure_ThatchFloor</sub> | <sub>ThatchFloor_Icon</sub> | <sub>structure（建筑构件）</sub> | <sub>**茅草地板**</sub> | <sub>PO</sub> | <sub>PO#3632471096 "Thatch Floor"</sub> |
| <sub>178</sub> | <sub>`ThatchRoof`</sub> | <sub>PrimalItemStructure_ThatchRoof</sub> | <sub>ThatchRoof_Icon</sub> | <sub>structure（建筑构件）</sub> | <sub>**茅草屋顶**</sub> | <sub>PO</sub> | <sub>PO#2495265121 "Thatch Roof"</sub> |
| <sub>179</sub> | <sub>`ThylacoSaddle`</sub> | <sub>PrimalItemArmor_ThylacoSaddle</sub> | <sub>—</sub> | <sub>saddle（鞍具）</sub> | <sub>**袋狮鞍**</sub> | <sub>wiki英文名→PO</sub> | <sub>wiki 英文名 "Thylacoleo Saddle" → PO#2643710264</sub> |
| <sub>180</sub> | <sub>`ToadSaddle`</sub> | <sub>PrimalItemArmor_ToadSaddle</sub> | <sub>—</sub> | <sub>saddle（鞍具）</sub> | <sub>**魔鬼蛙鞍**</sub> | <sub>wiki英文名→PO</sub> | <sub>wiki 英文名 "Beelzebufo Saddle" → PO#1339971047</sub> |
| <sub>181</sub> | <sub>`TransparentRiotShield`</sub> | <sub>PrimalItemArmor_TransparentRiotShield</sub> | <sub>—</sub> | <sub>armor（服饰/护甲）</sub> | <sub>**防暴盾**</sub> | <sub>wiki英文名→PO</sub> | <sub>wiki 英文名 "Riot Shield" → PO#3610286077</sub> |
| <sub>182</sub> | <sub>`TriCeiling_Metal`</sub> | <sub>PrimalItemStructure_TriCeiling_Metal</sub> | <sub>—</sub> | <sub>structure（建筑构件）</sub> | <sub>**金属三角天花板**</sub> | <sub>wiki英文名→PO</sub> | <sub>wiki 英文名 "Metal Triangle Ceiling" → PO#3471096854</sub> |
| <sub>183</sub> | <sub>`TriCeiling_Thatch`</sub> | <sub>PrimalItemStructure_TriCeiling_Thatch</sub> | <sub>—</sub> | <sub>structure（建筑构件）</sub> | <sub>**茅草屋顶**</sub> | <sub>PO词集包含</sub> | <sub>PO#1433304803 "Thatch Ceiling"（词集包含）</sub> |
| <sub>184</sub> | <sub>`TriRoof_Metal`</sub> | <sub>PrimalItemStructure_TriRoof_Metal</sub> | <sub>—</sub> | <sub>structure（建筑构件）</sub> | <sub>**金属三角屋顶**</sub> | <sub>wiki英文名→PO</sub> | <sub>wiki 英文名 "Metal Triangle Roof" → PO#2658541595</sub> |
| <sub>185</sub> | <sub>`TripwireC4`</sub> | <sub>PrimalItem_WeaponTripwireC4</sub> | <sub>Tripwire_Icon</sub> | <sub>weapon（工具/武器）</sub> | <sub>**简易爆炸装置**</sub> | <sub>miss_en</sub> | <sub>缺口英文名 "Improvised Explosive Device"〔wiki〕→ PO#907111696</sub> |
| <sub>186</sub> | <sub>`ValMegaraptorSaddle`</sub> | <sub>PrimalItemArmor_ValMegaraptorSaddle</sub> | <sub>—</sub> | <sub>saddle（鞍具）</sub> | <sub>**大盗龙鞍**</sub> | <sub>学名重组→PO</sub> | <sub>学名重组 Megaraptor + Saddle → PO#1478860490 "Megaraptor Saddle"</sub> |
| <sub>187</sub> | <sub>`WeapFlamethrower`</sub> | <sub>PrimalItem_WeapFlamethrower</sub> | <sub>—</sub> | <sub>weapon（工具/武器）</sub> | <sub>**火焰喷射器**</sub> | <sub>wiki英文名→PO</sub> | <sub>wiki 英文名 "Flamethrower" → PO#3378503066</sub> |
| <sub>188</sub> | <sub>`XenomorphPheromoneGland`</sub> | <sub>PrimalItemResource_XenomorphPheromoneGland</sub> | <sub>—</sub> | <sub>resource（资源/材料）</sub> | <sub>**死神信息素腺体**</sub> | <sub>miss_en</sub> | <sub>缺口英文名 "Reaper Pheromone Gland"〔wiki〕→ PO#2764303838</sub> |
| <sub>189</sub> | <sub>`XiphSaddle_ASA`</sub> | <sub>PrimalItemArmor_XiphSaddle_ASA</sub> | <sub>—</sub> | <sub>saddle（鞍具）</sub> | <sub>**剑射鱼鞍**</sub> | <sub>miss_en</sub> | <sub>缺口英文名 "Xiphactinus Saddle"〔wiki~〕→ PO#384389107</sub> |
| <sub>190</sub> | <sub>`YutySaddle`</sub> | <sub>PrimalItemArmor_YutySaddle</sub> | <sub>—</sub> | <sub>saddle（鞍具）</sub> | <sub>**羽王龙鞍**</sub> | <sub>wiki英文名→PO</sub> | <sub>wiki 英文名 "Yutyrannus Saddle" → PO#1041789082</sub> |
| <sub>191</sub> | <sub>`Zipline`</sub> | <sub>PrimalItemAmmo_Zipline</sub> | <sub>—</sub> | <sub>ammo（弹药/投掷物）</sub> | <sub>**滑索锚具**</sub> | <sub>miss_en</sub> | <sub>缺口英文名 "Zip-Line Anchor"〔wiki〕→ PO#4128035162</sub> |
| <sub>192</sub> | <sub>`AmargaSpike`</sub> | <sub>PrimalItemResource_AmargaSpike</sub> | <sub>—</sub> | <sub>resource（资源/材料）</sub> | <sub>**阿马加龙尖刺**</sub> | <sub>ShooterGame.json·官方中文</sub> | <sub>ShooterGame.json[PO#3421107077] "Amargasaurus Spike" → "阿马加龙尖刺"</sub> |
| <sub>193</sub> | <sub>`Ambergris`</sub> | <sub>PrimalItemResource_Ambergris</sub> | <sub>HUD_Ambergris_Icon</sub> | <sub>resource（资源/材料）</sub> | <sub>**龙涎香**</sub> | <sub>ShooterGame.json·官方中文</sub> | <sub>ShooterGame.json[PO#937147570] "Ambergris" → "龙涎香[Ambergris]"</sub> |
| <sub>194</sub> | <sub>`ApexDrop_AlphaCrystalWyvern`</sub> | <sub>PrimalItemResource_ApexDrop_AlphaCrystalWyvern</sub> | <sub>—</sub> | <sub>resource（资源/材料）</sub> | <sub>**精英水晶飞龙勾爪**</sub> | <sub>ShooterGame.json·官方中文</sub> | <sub>ShooterGame.json[PO#919019130] "Alpha Crystal Talon" → "精英水晶飞龙勾爪[Alpha</sub> |
| <sub>195</sub> | <sub>`ApexDrop_CrystalWyvern`</sub> | <sub>PrimalItemResource_ApexDrop_CrystalWyvern</sub> | <sub>—</sub> | <sub>resource（资源/材料）</sub> | <sub>**水晶勾爪**</sub> | <sub>ShooterGame.json·官方中文</sub> | <sub>ShooterGame.json[PO#1206254564] "Crystal Talon" → "水晶勾爪[Crystal Talon]</sub> |
| <sub>196</sub> | <sub>`ApexDrop_ReaperBarb`</sub> | <sub>PrimalItemResource_ApexDrop_ReaperBarb</sub> | <sub>ApexDropReaper_Icon</sub> | <sub>resource（资源/材料）</sub> | <sub>**精英死神国王倒钩**</sub> | <sub>ShooterGame.json·官方中文</sub> | <sub>ShooterGame.json[PO#727557612] "Alpha Reaper King Barb" → "精英死神国王倒钩[Al</sub> |
| <sub>197</sub> | <sub>`Boulder_Fire`</sub> | <sub>PrimalItemAmmo_Boulder_Fire</sub> | <sub>—</sub> | <sub>ammo（弹药/投掷物）</sub> | <sub>**沥青罐**</sub> | <sub>ShooterGame.json·官方中文</sub> | <sub>ShooterGame.json[PO#186707479] "Jar of Pitch" → "沥青罐[Jar of Pitch]"</sub> |
| <sub>198</sub> | <sub>`Car_Bed_Racer`</sub> | <sub>PrimalItem_Car_Bed_Racer</sub> | <sub>—</sub> | <sub>other（其他/未归类）</sub> | <sub>**战车后车厢·竞速**</sub> | <sub>ShooterGame.json·官方中文</sub> | <sub>ShooterGame.json[PO#1154361138] "BattleRig Bed: Racer" → "战车后车厢: 竞速"</sub> |
| <sub>199</sub> | <sub>`Car_Bed_Rollcage`</sub> | <sub>PrimalItem_Car_Bed_Rollcage</sub> | <sub>—</sub> | <sub>other（其他/未归类）</sub> | <sub>**战车后车厢·防滚**</sub> | <sub>ShooterGame.json·官方中文</sub> | <sub>ShooterGame.json[PO#4156340697] "BattleRig Bed: Rollcage" → "战车后车厢: 防滚</sub> |
| <sub>200</sub> | <sub>`Car_Bed_Truck`</sub> | <sub>PrimalItem_Car_Bed_Truck</sub> | <sub>—</sub> | <sub>other（其他/未归类）</sub> | <sub>**战车后车厢·皮卡**</sub> | <sub>ShooterGame.json·官方中文</sub> | <sub>ShooterGame.json[PO#123300101] "BattleRig Bed: Truck" → "战车后车厢: 皮卡"</sub> |
| <sub>201</sub> | <sub>`Car_Cab_Racer`</sub> | <sub>PrimalItem_Car_Cab_Racer</sub> | <sub>—</sub> | <sub>other（其他/未归类）</sub> | <sub>**战车驾驶室·竞速**</sub> | <sub>ShooterGame.json·官方中文</sub> | <sub>ShooterGame.json[PO#2593520349] "BattleRig Cab: Racer" → "战车驾驶室: 竞速"</sub> |
| <sub>202</sub> | <sub>`Car_Cab_Rollcage`</sub> | <sub>PrimalItem_Car_Cab_Rollcage</sub> | <sub>—</sub> | <sub>other（其他/未归类）</sub> | <sub>**战车驾驶室·防滚**</sub> | <sub>ShooterGame.json·官方中文</sub> | <sub>ShooterGame.json[PO#2487707624] "BattleRig Cab: Rollcage" → "战车驾驶室: 防滚</sub> |
| <sub>203</sub> | <sub>`Car_Cab_Truck`</sub> | <sub>PrimalItem_Car_Cab_Truck</sub> | <sub>—</sub> | <sub>other（其他/未归类）</sub> | <sub>**战车驾驶室·皮卡**</sub> | <sub>ShooterGame.json·官方中文</sub> | <sub>ShooterGame.json[PO#3640833258] "BattleRig Cab: Truck" → "战车驾驶室: 皮卡"</sub> |
| <sub>204</sub> | <sub>`Car_Chassis_Main`</sub> | <sub>PrimalItem_Car_Chassis_Main</sub> | <sub>—</sub> | <sub>other（其他/未归类）</sub> | <sub>**底盘**</sub> | <sub>ShooterGame.json·官方中文</sub> | <sub>ShooterGame.json[PO#3168871593] "Chassis" → "底盘"</sub> |
| <sub>205</sub> | <sub>`Car_Engine_Racer`</sub> | <sub>PrimalItem_Car_Engine_Racer</sub> | <sub>—</sub> | <sub>other（其他/未归类）</sub> | <sub>**战车发动机·竞速**</sub> | <sub>ShooterGame.json·官方中文</sub> | <sub>ShooterGame.json[PO#2047090713] "BattleRig Engine: Racer" → "战车发动机: 竞速</sub> |
| <sub>206</sub> | <sub>`Car_Engine_Rollcage`</sub> | <sub>PrimalItem_Car_Engine_Rollcage</sub> | <sub>—</sub> | <sub>other（其他/未归类）</sub> | <sub>**战车发动机·防滚**</sub> | <sub>ShooterGame.json·官方中文</sub> | <sub>ShooterGame.json[PO#1045059204] "BattleRig Engine: Rollcage" → "战车发动机:</sub> |
| <sub>207</sub> | <sub>`Car_Engine_Truck`</sub> | <sub>PrimalItem_Car_Engine_Truck</sub> | <sub>—</sub> | <sub>other（其他/未归类）</sub> | <sub>**战车发动机·皮卡**</sub> | <sub>ShooterGame.json·官方中文</sub> | <sub>ShooterGame.json[PO#965963310] "BattleRig Engine: Truck" → "战车发动机: 皮卡"</sub> |
| <sub>208</sub> | <sub>`Car_Frontmod_Armor`</sub> | <sub>PrimalItem_Car_Frontmod_Armor</sub> | <sub>—</sub> | <sub>other（其他/未归类）</sub> | <sub>**战车前端模块·附加装甲**</sub> | <sub>ShooterGame.json·官方中文</sub> | <sub>ShooterGame.json[PO#2217225727] "BattleRig FrontEnd-Mod: Extra Armor" </sub> |
| <sub>209</sub> | <sub>`Car_Frontmod_Buzzsaw`</sub> | <sub>PrimalItem_Car_Frontmod_Buzzsaw</sub> | <sub>—</sub> | <sub>other（其他/未归类）</sub> | <sub>**战车前端模块·收割锯**</sub> | <sub>ShooterGame.json·官方中文</sub> | <sub>ShooterGame.json[PO#1399969068] "BattleRig FrontEnd-Mod: Harvest Saw" </sub> |
| <sub>210</sub> | <sub>`Car_Frontmod_CowCatcher`</sub> | <sub>PrimalItem_Car_Frontmod_CowCatcher</sub> | <sub>—</sub> | <sub>other（其他/未归类）</sub> | <sub>**战车前端模块·排障导板**</sub> | <sub>ShooterGame.json·官方中文</sub> | <sub>ShooterGame.json[PO#2372844357] "BattleRig FrontEnd-Mod: Cowcatcher" →</sub> |
| <sub>211</sub> | <sub>`Car_Frontmod_Spikes`</sub> | <sub>PrimalItem_Car_Frontmod_Spikes</sub> | <sub>—</sub> | <sub>other（其他/未归类）</sub> | <sub>**战车前端模块·尖刺格栅**</sub> | <sub>ShooterGame.json·官方中文</sub> | <sub>ShooterGame.json[PO#3933776713] "BattleRig FrontEnd-Mod: Spiked Grill"</sub> |
| <sub>212</sub> | <sub>`Car_Rearmod_Afterburner`</sub> | <sub>PrimalItem_Car_Rearmod_Afterburner</sub> | <sub>—</sub> | <sub>other（其他/未归类）</sub> | <sub>**战车后端模块·后燃器**</sub> | <sub>ShooterGame.json·官方中文</sub> | <sub>ShooterGame.json[PO#1532058727] "BattleRig RearEnd-Mod: Afterburner" →</sub> |
| <sub>213</sub> | <sub>`Car_Rearmod_Hook`</sub> | <sub>PrimalItem_Car_Rearmod_Hook</sub> | <sub>—</sub> | <sub>other（其他/未归类）</sub> | <sub>**战车后端模块·牵引钩**</sub> | <sub>ShooterGame.json·官方中文</sub> | <sub>ShooterGame.json[PO#2808419466] "BattleRig RearEnd-Mod: TowHook" → "战车</sub> |
| <sub>214</sub> | <sub>`Car_Rearmod_Jump`</sub> | <sub>PrimalItem_Car_Rearmod_Jump</sub> | <sub>—</sub> | <sub>other（其他/未归类）</sub> | <sub>**战车后端模块·跳跃式喷气装置**</sub> | <sub>ShooterGame.json·官方中文</sub> | <sub>ShooterGame.json[PO#3931380558] "BattleRig RearEnd-Mod: Jump Jets" → "</sub> |
| <sub>215</sub> | <sub>`Car_Rearmod_Mines`</sub> | <sub>PrimalItem_Car_Rearmod_Mines</sub> | <sub>—</sub> | <sub>other（其他/未归类）</sub> | <sub>**战车后端模块·地雷**</sub> | <sub>ShooterGame.json·官方中文</sub> | <sub>ShooterGame.json[PO#1492473209] "BattleRig RearEnd-Mod: Mines" → "战车后端</sub> |
| <sub>216</sub> | <sub>`Car_Rearmod_Sludge`</sub> | <sub>PrimalItem_Car_Rearmod_Sludge</sub> | <sub>—</sub> | <sub>other（其他/未归类）</sub> | <sub>**战车后端模块·淤泥**</sub> | <sub>ShooterGame.json·官方中文</sub> | <sub>ShooterGame.json[PO#2257562709] "BattleRig RearEnd-Mod: Sludgetrail" →</sub> |
| <sub>217</sub> | <sub>`Car_Rearmod_Smoke`</sub> | <sub>PrimalItem_Car_Rearmod_Smoke</sub> | <sub>—</sub> | <sub>other（其他/未归类）</sub> | <sub>**战车后端模块·烟幕装置**</sub> | <sub>ShooterGame.json·官方中文</sub> | <sub>ShooterGame.json[PO#556030096] "BattleRig RearEnd-Mod: Smokescreen" → </sub> |
| <sub>218</sub> | <sub>`Car_Turret_Cannon`</sub> | <sub>PrimalItem_Car_Turret_Cannon</sub> | <sub>—</sub> | <sub>other（其他/未归类）</sub> | <sub>**战车炮台·加农炮**</sub> | <sub>ShooterGame.json·官方中文</sub> | <sub>ShooterGame.json[PO#2487649154] "BattleRig Turret: Cannon" → "战车炮台: 加农</sub> |
| <sub>219</sub> | <sub>`Car_Turret_FlightSeeker`</sub> | <sub>PrimalItem_Car_Turret_FlightSeeker</sub> | <sub>—</sub> | <sub>other（其他/未归类）</sub> | <sub>**战车炮台·制导火箭弹**</sub> | <sub>ShooterGame.json·官方中文</sub> | <sub>ShooterGame.json[PO#3833786356] "BattleRig Turret: Flightseeker Missil</sub> |
| <sub>220</sub> | <sub>`Car_Turret_Minigun`</sub> | <sub>PrimalItem_Car_Turret_Minigun</sub> | <sub>HUD_Car_Turret_Minigun_icon</sub> | <sub>other（其他/未归类）</sub> | <sub>**战车炮台·机枪**</sub> | <sub>ShooterGame.json·官方中文</sub> | <sub>ShooterGame.json[PO#266682997] "BattleRig Turret: Minigun" → "战车炮台: 机枪</sub> |
| <sub>221</sub> | <sub>`Car_Turret_Shotgun`</sub> | <sub>PrimalItem_Car_Turret_Shotgun</sub> | <sub>HUD_Car_Turret_Shotgun_icon</sub> | <sub>other（其他/未归类）</sub> | <sub>**战车炮台·霰弹式麻醉弹**</sub> | <sub>ShooterGame.json·官方中文</sub> | <sub>ShooterGame.json[PO#3146118739] "BattleRig Turret: Tranq-Shotgun" → "战</sub> |
| <sub>222</sub> | <sub>`Car_Wheels_Rollcage`</sub> | <sub>PrimalItem_Car_Wheels_Rollcage</sub> | <sub>—</sub> | <sub>other（其他/未归类）</sub> | <sub>**战车车轮·防滚**</sub> | <sub>ShooterGame.json·官方中文</sub> | <sub>ShooterGame.json[PO#1093282613] "BattleRig Wheels: Rollcage" → "战车车轮: </sub> |
| <sub>223</sub> | <sub>`Car_Wheels_Truck`</sub> | <sub>PrimalItem_Car_Wheels_Truck</sub> | <sub>—</sub> | <sub>other（其他/未归类）</sub> | <sub>**战车车轮·皮卡**</sub> | <sub>ShooterGame.json·官方中文</sub> | <sub>ShooterGame.json[PO#384845616] "BattleRig Wheels: Truck" → "战车车轮: 皮卡"</sub> |
| <sub>224</sub> | <sub>`CodeKey`</sub> | <sub>PrimalItemResource_CodeKey</sub> | <sub>—</sub> | <sub>resource（资源/材料）</sub> | <sub>**码钥**</sub> | <sub>ShooterGame.json·官方中文</sub> | <sub>ShooterGame.json[PO#2469185644] "Code-Key" → "码钥"</sub> |
| <sub>225</sub> | <sub>`Crystal_IslesPrimal`</sub> | <sub>PrimalItemResource_Crystal_IslesPrimal</sub> | <sub>—</sub> | <sub>resource（资源/材料）</sub> | <sub>**原始水晶**</sub> | <sub>ShooterGame.json·官方中文</sub> | <sub>ShooterGame.json[PO#2632733319] "Primal Crystal" → "原始水晶"</sub> |
| <sub>226</sub> | <sub>`DinoCompanion_Gear`</sub> | <sub>PrimalItemArmor_DinoCompanion_Gear</sub> | <sub>—</sub> | <sub>armor（服饰/护甲）</sub> | <sub>**铠护犬护甲**</sub> | <sub>ShooterGame.json·官方中文</sub> | <sub>ShooterGame.json[PO#3867906477] "Armadoggo Armor" → "铠护犬护甲[Armadoggo A</sub> |
| <sub>227</sub> | <sub>`DinoCompanion_Gear_Bag`</sub> | <sub>PrimalItemArmor_DinoCompanion_Gear_Bag</sub> | <sub>—</sub> | <sub>armor（服饰/护甲）</sub> | <sub>**随伴的背包**</sub> | <sub>ShooterGame.json·官方中文</sub> | <sub>ShooterGame.json[PO#469667260] "Companion Rucksack" → "随伴的背包"</sub> |
| <sub>228</sub> | <sub>`DinoCompanion_Gear_ChibiBasket`</sub> | <sub>PrimalItemArmor_DinoCompanion_Gear_ChibiBasket</sub> | <sub>—</sub> | <sub>armor（服饰/护甲）</sub> | <sub>**随伴的袖珍宠物鞍座**</sub> | <sub>ShooterGame.json·官方中文</sub> | <sub>ShooterGame.json[PO#3653431611] "Companion Chibi-carrier" → "随伴的袖珍宠物鞍座</sub> |
| <sub>229</sub> | <sub>`DinoCompanion_Gear_ExtraArmor`</sub> | <sub>PrimalItemArmor_DinoCompanion_Gear_ExtraArmor</sub> | <sub>—</sub> | <sub>armor（服饰/护甲）</sub> | <sub>**随伴的附加护甲**</sub> | <sub>ShooterGame.json·官方中文</sub> | <sub>ShooterGame.json[PO#317699269] "Companion Extra Armor" → "随伴的附加护甲"</sub> |
| <sub>230</sub> | <sub>`DinoCompanion_Gear_FoodBasket`</sub> | <sub>PrimalItemArmor_DinoCompanion_Gear_FoodBasket</sub> | <sub>—</sub> | <sub>armor（服饰/护甲）</sub> | <sub>**随伴的野餐套件**</sub> | <sub>ShooterGame.json·官方中文</sub> | <sub>ShooterGame.json[PO#3379530732] "Companion Picnic Set" → "随伴的野餐套件"</sub> |
| <sub>231</sub> | <sub>`DinoCompanion_Gear_MeatSack`</sub> | <sub>PrimalItemArmor_DinoCompanion_Gear_MeatSack</sub> | <sub>—</sub> | <sub>armor（服饰/护甲）</sub> | <sub>**随伴的诱饵陷阱**</sub> | <sub>ShooterGame.json·官方中文</sub> | <sub>ShooterGame.json[PO#485167168] "Companion Bait Trap" → "随伴的诱饵陷阱"</sub> |
| <sub>232</sub> | <sub>`DinoCompanion_Gear_Movespeed`</sub> | <sub>PrimalItemArmor_DinoCompanion_Gear_Movespeed</sub> | <sub>—</sub> | <sub>armor（服饰/护甲）</sub> | <sub>**随伴的助推器**</sub> | <sub>ShooterGame.json·官方中文</sub> | <sub>ShooterGame.json[PO#4053904995] "Companion Speed Booster" → "随伴的助推器"</sub> |
| <sub>233</sub> | <sub>`DinoCompanion_Gear_OxygenTank`</sub> | <sub>PrimalItemArmor_DinoCompanion_Gear_OxygenTank</sub> | <sub>—</sub> | <sub>armor（服饰/护甲）</sub> | <sub>**随伴的氧气罐**</sub> | <sub>ShooterGame.json·官方中文</sub> | <sub>ShooterGame.json[PO#608281074] "Companion Oxygen Tank" → "随伴的氧气罐"</sub> |
| <sub>234</sub> | <sub>`DinoCompanion_Gear_RolledUpSleepingBag`</sub> | <sub>PrimalItemArmor_DinoCompanion_Gear_RolledUpSleepingBag</sub> | <sub>—</sub> | <sub>armor（服饰/护甲）</sub> | <sub>**随伴的露营套件**</sub> | <sub>ShooterGame.json·官方中文</sub> | <sub>ShooterGame.json[PO#1474928242] "Companion Camping Gear" → "随伴的露营套件"</sub> |
| <sub>235</sub> | <sub>`DinoCompanion_Gear_Spikes`</sub> | <sub>PrimalItemArmor_DinoCompanion_Gear_Spikes</sub> | <sub>—</sub> | <sub>armor（服饰/护甲）</sub> | <sub>**随伴的战斗尖刺**</sub> | <sub>ShooterGame.json·官方中文</sub> | <sub>ShooterGame.json[PO#128972942] "Companion Battle-spikes" → "随伴的战斗尖刺"</sub> |
| <sub>236</sub> | <sub>`DinoCompanion_Gear_Spyglass`</sub> | <sub>PrimalItemArmor_DinoCompanion_Gear_Spyglass</sub> | <sub>—</sub> | <sub>armor（服饰/护甲）</sub> | <sub>**随伴的侦查套件**</sub> | <sub>ShooterGame.json·官方中文</sub> | <sub>ShooterGame.json[PO#243143361] "Companion Spykit" → "随伴的侦查套件"</sub> |
| <sub>237</sub> | <sub>`DinoCompanion_Whistle_Base_BP`</sub> | <sub>PrimalItem_DinoCompanion_Whistle_Base_BP</sub> | <sub>—</sub> | <sub>other（其他/未归类）</sub> | <sub>**铠护犬哨子**</sub> | <sub>ShooterGame.json·官方中文</sub> | <sub>ShooterGame.json[PO#3487680480] "Armadoggo Whistle" → "铠护犬哨子"</sub> |
| <sub>238</sub> | <sub>`DinoCompanion_Whistle_YoungIceFox`</sub> | <sub>PrimalItem_DinoCompanion_Whistle_YoungIceFox</sub> | <sub>—</sub> | <sub>other（其他/未归类）</sub> | <sub>**霜灵狐哨子**</sub> | <sub>ShooterGame.json·官方中文</sub> | <sub>ShooterGame.json[PO#553121190] "Veilwyn Whistle" → "霜灵狐哨子"</sub> |
| <sub>239</sub> | <sub>`Furball`</sub> | <sub>PrimalItemResource_Furball</sub> | <sub>—</sub> | <sub>resource（资源/材料）</sub> | <sub>**毛球**</sub> | <sub>ShooterGame.json·官方中文</sub> | <sub>ShooterGame.json[PO#2692925070] "Hairball" → "毛球[Hairball]"</sub> |
| <sub>240</sub> | <sub>`GasRefined`</sub> | <sub>PrimalItemResource_GasRefined</sub> | <sub>—</sub> | <sub>resource（资源/材料）</sub> | <sub>**冷凝的瓦斯球**</sub> | <sub>ShooterGame.json·官方中文</sub> | <sub>ShooterGame.json[PO#317093939] "Congealed Gas Ball" → "冷凝的瓦斯球[Congeale</sub> |
| <sub>241</sub> | <sub>`GoldenNugget`</sub> | <sub>PrimalItemResource_GoldenNugget</sub> | <sub>Golden_Nugget</sub> | <sub>resource（资源/材料）</sub> | <sub>**金块**</sub> | <sub>ShooterGame.json·官方中文</sub> | <sub>ShooterGame.json[PO#3907058207] "Golden Nugget" → "金块"</sub> |
| <sub>242</sub> | <sub>`Hair`</sub> | <sub>PrimalItemResource_Hair</sub> | <sub>Hair_Icon</sub> | <sub>resource（资源/材料）</sub> | <sub>**人类毛发**</sub> | <sub>ShooterGame.json·官方中文</sub> | <sub>ShooterGame.json[PO#2797396545] "Human Hair" → "人类毛发[Human Hair]"</sub> |
| <sub>243</sub> | <sub>`HighQualityPollen`</sub> | <sub>PrimalItemResource_HighQualityPollen</sub> | <sub>High_Quality_Pollen</sub> | <sub>resource（资源/材料）</sub> | <sub>**高品质花粉**</sub> | <sub>ShooterGame.json·官方中文</sub> | <sub>ShooterGame.json[PO#165683385] "High Quality Pollen" → "高品质花粉"</sub> |
| <sub>244</sub> | <sub>`LC_Outpost_LootStructureKey`</sub> | <sub>PrimalItemResource_LC_Outpost_LootStructureKey</sub> | <sub>—</sub> | <sub>resource（资源/材料）</sub> | <sub>**失落密钥**</sub> | <sub>ShooterGame.json·官方中文</sub> | <sub>ShooterGame.json[PO#3340757848] "Loot-Key" → "失落密钥"</sub> |
| <sub>245</sub> | <sub>`LC_Outpost_RepairMaterials`</sub> | <sub>PrimalItemResource_LC_Outpost_RepairMaterials</sub> | <sub>—</sub> | <sub>resource（资源/材料）</sub> | <sub>**维修材料**</sub> | <sub>ShooterGame.json·官方中文</sub> | <sub>ShooterGame.json[PO#4251964902] "Repair Materials" → "维修材料"</sub> |
| <sub>246</sub> | <sub>`PalaeoctopusInk`</sub> | <sub>PrimalItemResource_PalaeoctopusInk</sub> | <sub>—</sub> | <sub>resource（资源/材料）</sub> | <sub>**棱彩墨汁**</sub> | <sub>ShooterGame.json·官方中文</sub> | <sub>ShooterGame.json[PO#2680248292] "Prismatic Ink" → "棱彩墨汁"</sub> |
| <sub>247</sub> | <sub>`RedElementDust`</sub> | <sub>PrimalItemResource_RedElementDust</sub> | <sub>—</sub> | <sub>resource（资源/材料）</sub> | <sub>**腥红元素粉尘**</sub> | <sub>ShooterGame.json·官方中文</sub> | <sub>ShooterGame.json[PO#1156378742] "Red Element Dust" → "腥红元素粉尘[Red Eleme</sub> |
| <sub>248</sub> | <sub>`RetrieveMegTooth`</sub> | <sub>PrimalItemResource_RetrieveMegTooth</sub> | <sub>RetrieveMegTooth_Icon</sub> | <sub>resource（资源/材料）</sub> | <sub>**金纹巨齿鲨牙齿**</sub> | <sub>ShooterGame.json·官方中文</sub> | <sub>ShooterGame.json[PO#1317053058] "Golden Striped Megalodon Tooth" → "金纹</sub> |
| <sub>249</sub> | <sub>`RetrieveReaperGland`</sub> | <sub>PrimalItemResource_RetrieveReaperGland</sub> | <sub>—</sub> | <sub>resource（资源/材料）</sub> | <sub>**死神国王信息素腺体**</sub> | <sub>ShooterGame.json·官方中文</sub> | <sub>ShooterGame.json[PO#2804615677] "Reaper King Pheromone Gland" → "死神国王信</sub> |
| <sub>250</sub> | <sub>`TankFuel`</sub> | <sub>PrimalItemAmmo_TankFuel</sub> | <sub>—</sub> | <sub>ammo（弹药/投掷物）</sub> | <sub>**潜艇燃料**</sub> | <sub>ShooterGame.json·官方中文</sub> | <sub>ShooterGame.json[PO#4174338369] "Submarine Fuel" → "潜艇燃料[Submarine Fue</sub> |
| <sub>251</sub> | <sub>`TreasureMap_DinoCompanion_Doggo`</sub> | <sub>PrimalItem_TreasureMap_DinoCompanion_Doggo</sub> | <sub>—</sub> | <sub>other（其他/未归类）</sub> | <sub>**受浸蚀的弃物**</sub> | <sub>ShooterGame.json·官方中文</sub> | <sub>ShooterGame.json[PO#220256614] "Hex-infected Junk" → "受浸蚀的弃物[Hex-infec</sub> |
| <sub>252</sub> | <sub>`WebBall_WeapJumpingSpider`</sub> | <sub>PrimalItemAmmo_WebBall_WeapJumpingSpider</sub> | <sub>—</sub> | <sub>ammo（弹药/投掷物）</sub> | <sub>**蛛网**</sub> | <sub>ShooterGame.json·官方中文</sub> | <sub>ShooterGame.json[PO#1649535366] "Web Ball" → "蛛网"</sub> |
| <sub>253</sub> | <sub>`Whistle_DinoCompanion`</sub> | <sub>PrimalItem_Whistle_DinoCompanion</sub> | <sub>—</sub> | <sub>other（其他/未归类）</sub> | <sub>**随伴哨子**</sub> | <sub>ShooterGame.json·官方中文</sub> | <sub>ShooterGame.json[PO#1229005984] "Companion Whistle" → "随伴哨子"</sub> |

---

## ③ 待裁决（0 条）

> ③-1 用「有出处的物种名 + 鞍/战利品」拼装（**非官方原文**，但零件均有出处）；③-2 PO 近似匹配（可能是别的物品）；③-3 完全无出处 → 建议前端回退英文。

### ③-1 拼装类（物种名+鞍/战利品，0 条）

| <sub>#</sub> | <sub>基名</sub> | <sub>完整类名</sub> | <sub>icon</sub> | <sub>类别</sub> | <sub>溯源中文</sub> | <sub>出处</sub> | <sub>证据/备注</sub> |
|:--:|------|------|------|------|---------|------|---------|

### ③-2 PO 近似（0 条）

| <sub>#</sub> | <sub>基名</sub> | <sub>完整类名</sub> | <sub>icon</sub> | <sub>类别</sub> | <sub>溯源中文</sub> | <sub>出处</sub> | <sub>证据/备注</sub> |
|:--:|------|------|------|------|---------|------|---------|

### ③-3 无出处（0 条，需定名或回退英文）

| <sub>#</sub> | <sub>基名</sub> | <sub>完整类名</sub> | <sub>icon</sub> | <sub>类别</sub> | <sub>溯源中文</sub> | <sub>出处</sub> | <sub>证据/备注</sub> |
|:--:|------|------|------|------|---------|------|---------|

