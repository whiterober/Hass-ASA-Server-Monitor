# Los（失落土）温泉生物群系 —— 坐标与信息

> 交付日：20261015｜服：Los｜方式：**RCON（dll）直读**｜未做游戏内目视验证

## 一、结论

Los 的温泉（Hot Springs）是**生物群系**，其载体是关卡 Actor **`BiomeZoneVolume`**（全图 174 个），
因此**坐标与信息可直接用 RCON 读取，不需要离线读档**（biome volume 不入存档）。

- **温泉 = `BiomeZone = 4`**，共 **3 个地点 / 6 个 volume**：`Crater Hot-Springs`、`Warmveil Springs`、`Emberwater Springs`
- 另有同类热区 **`Snowveil Thermal Zone`**（属编号 20），单独列出
- ⚠️ **`BiomeZone` 是大区编号，`BiomeZoneName` 才是具体地点名**（编号 8 对应 30 个地点）

## 二、坐标（共 7 个）

| # | 地点 | 编号 | x | y | z | mapX* | mapY* |
|---|---|---|---|---|---|---|---|
| 1 | Crater Hot-Springs | 4 | -357604.0 | 273721.0 | -21680.0 | 37.12 | 71.73 |
| 2 | Crater Hot-Springs | 4 | -373537.0 | 321091.0 | -16916.9 | 36.05 | 74.67 |
| 3 | Emberwater Springs | 4 | 309735.0 | 363593.0 | -13456.3 | 82.07 | 77.31 |
| 4 | Snowveil Thermal Zone | 20 | 319577.0 | -200386.0 | 17983.7 | 82.73 | 42.34 |
| 5 | Warmveil Springs | 4 | -397168.0 | -314090.0 | -31128.0 | 34.46 | 35.29 |
| 6 | Warmveil Springs | 4 | -366855.0 | -322291.0 | -32893.4 | 36.5 | 34.78 |
| 7 | Warmveil Springs | 4 | -361684.0 | -277669.0 | -23608.0 | 36.85 | 37.55 |

\* 推算值，未经地标锚点校准：
```
mapX = (x + 908800) / 14848
mapY = (y + 883200) / 16128
```
前端若有更准校准，请用**原始 x/y/z 自行换算**。

## 三、Los biome 编号体系（全量 174 个 volume）

| `BiomeZone` | 实例数 | 地点名 |
|---|---|---|
| 0 | 1 | Ruins of the Ascendant Cavern |
| 2 | 10 | Spine Of The World Canyon |
| 3 | 2 | Frostwhisper Creeklands / Shiverrun Creeks |
| 4 ⭐ | 6 | Crater Hot-Springs / Emberwater Springs / Warmveil Springs |
| 8 | 87 | Ascension of Aetheros / Blackfrost Tower / Blightfall Entrance / Cave of The Whispering Needle / Cavern of The Saphire Cascades / Cryoguard Spire / Dragon's Breath Crossing / Hoarfrost Wildwood / Malachite's Peak / Mount Aetheros / Mount Krystallos / Mount Vastyr / Outpost Sentinel Tower / Ruins of the Ascendant Cavern / Shadow Cloak Ridge / Shatterhome Ruins / Shiverwind Bridge / Sky-Treader Bridge / Sleeper's Rib Passage / Sorrowfall Summit / Sovereign's Crown Mountain / The Divide-Binder Passway / The Frozen Eye / The Glimmering Ascent Bridge / The Glimmerpath Ridge / The Serpent's Back / The Shadow-Keeper's Walk / The Silent Watchtower / Vultuurn's Horn Mountain / Whispering Way Bridge / Whispers Of The Summit Trail / Whisperwind Crag |
| 11 | 5 | Titan's Cradle |
| 17 | 5 | City / Lost King's Palace / Plaguebound Hamlet |
| 18 | 3 | The Shattered Delta |
| 20 | 21 | Deadwind Peak / Frostwail Falls / Glassmere Lake / Glasswater Rills / Icewhisper Flats / Silvercascade / Snowveil Thermal Zone / Veil of Shattered Ice / Whispering Drop / Wintervein Falls |
| 21 | 3 | Frostgrave Forest / Frostpine Forest |
| 22 | 7 | Blizzardscar Reach / Frostwind Expanse / Iceleaf Timberland |
| 26 | 24 | The Aberrant Spread |

## 四、命令复现

```
# 逐实例取大区编号 + 地点名（需逐个 propsIdx，无分页）
TransferIdentityFix.WorldProbe actor filter=BiomeZoneVolume props=1 propsIdx=N probe=BiomeZoneName
# 按 objectName 精准取坐标
TransferIdentityFix.WorldProbe actor byname=1 filter=<objectName> props=1
```

## 五、口径与局限

1. `BiomeZoneVolume` **无 bounds/radius 字段**（258 项属性里没有）⇒ **本表只给中心点，未给半径/范围**
2. 每个点 = 一个 `BiomeZoneVolume` 实例；同一地点多个实例 = 该区域的多个子体积
3. 本次**未做游戏内目视验证**（编号与地点名已由实服属性实测确认）
4. 与前端 `biome_zh.json` 的「温泉 / hotspring」对应关系成立

## 六、附件

- 机读：`LostColony_hotsprings.json`（同目录，含 hotSprings[] + biomeZoneIndex[] + 算好的 mapX/mapY）

---
本报告由后端自动生成于 2026-10-15 23:57:19。
