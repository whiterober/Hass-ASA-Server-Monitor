# 补录方案：Blood Sap / Aureliax Egg（失落地 Lost Colony）

> 日期：2026-10-02 · 状态：**方案已定，待执行**（未改动任何文件）

## 一、结论速览

| 物品 | 中文名（游戏实锤） | 类名 | 词典 key | 图标 | 三链体检 |
|------|------|------|------|------|:---:|
| **Blood Sap** | 血色树液 | `PrimalItemConsumable_BloodSap_C` ※推理 | `BloodSap` | `Blood_Sap` ✅已有 | 词典❌ 图标✅ |
| **Aureliax Egg** | 寒辉雪龙蛋 | `PrimalItemConsumable_Egg_SnowDragon_C` ✅实锤 | `Egg_SnowDragon` | `HUD_AureliaxEgg_Icon` ✅已有 | 词典❌ 图标✅ |
| （受精版） | 受精的寒辉雪龙蛋 | `..._Fertilized_C` ✅实锤 | `Egg_SnowDragon_Fertilized` | `HUD_AureliaxEgg_Icon` ※复用 | 词典❌ 图标✅ |

**补录动作 = 仅往 `汉化\item_zh.json` 加 2~3 条词典条目，无需动图标、无需动后端。**

## 二、证据链（4 项）

1. **类名实锤**（wiki blueprintpath 原文）：
   - Aureliax Egg：`/Game/LostColony/Dinos/SnowDragon/Egg/PrimalItemConsumable_Egg_SnowDragon.PrimalItemConsumable_Egg_SnowDragon_C`
   - 受精版：`..._SnowDragon_Fertilized_C`
   - Blood Sap：wiki 页为 Stub（无 ID 字段）→ **同族推理**：替代对象 Cactus Sap（仙人掌汁）类名 = `PrimalItemConsumable_CactusSap_C`（wiki 实锤），前缀规律一致 → `PrimalItemConsumable_BloodSap_C`；备选 `PrimalItemResource_BloodSap_C`

2. **中文名实锤**（游戏内资源表 `汉化\icon_zh_map.json`）：
   - `"blood sap": "血色树液[Blood Sap]"`（含 `blood_sap` 双写）
   - `"hud_aureliaxegg_icon": "寒辉雪龙蛋[Aureliax Egg]"`
   - `"aureliax": "寒辉雪龙(Aureliax)"`

3. **图标实锤**（`汉化\icons2.json` 已收录，无需新增）：
   - `Blood_Sap` → `https://img.whiterober.ccwu.cc/ASA/resources/Blood_Sap.png`
   - `HUD_AureliaxEgg_Icon` → `https://img.whiterober.ccwu.cc/ASA/eggs/HUD_AureliaxEgg_Icon.png`

4. **前端匹配规则**（dino-import.html 现版）：
   - `lbItemBaseCands()`：剥 `PrimalItemConsumable_` → 候选 `Egg_SnowDragon` / `BloodSap`
   - `lbCanonBase()`：canon 归一 = `Egg_SnowDragon` / `BloodSap`
   - 结论：**key 直填 canon 名即可命中**（与现有 84 条 `kind=egg` 条目格式 `Egg_XXX` 一致）

## 三、执行清单（拟写入 `汉化\item_zh.json`）

```json
"BloodSap":{"icon":"Blood_Sap","en":"Blood Sap","zh":"血色树液","n":0,"kind":"consumable","src":"game_official","alias":"PrimalItemConsumable_BloodSap"}
"Egg_SnowDragon":{"icon":"HUD_AureliaxEgg_Icon","en":"Aureliax Egg","zh":"寒辉雪龙蛋","n":0,"kind":"egg","src":"game_official","alias":"PrimalItemConsumable_Egg_SnowDragon"}
"Egg_SnowDragon_Fertilized":{"icon":"HUD_AureliaxEgg_Icon","en":"Fertilized Aureliax Egg","zh":"受精的寒辉雪龙蛋","n":0,"kind":"egg","src":"game_official","alias":"PrimalItemConsumable_Egg_SnowDragon_Fertilized"}
```

> `src:"game_official"` = 中文名来源"游戏内资源表"（对照现有惯例：`resource`/`blueprint`/`facility_zh` 等，来源标签自由）。`alias` 存长类名，配合 canon 反查双保险。
> 受精版条目若不需要可省略（等驯服/交配实例出现再补也行）。

## 四、验证方式（执行后）

1. `node --check` 语法 3/3 → `_deploy_cf.py` 部署
2. 浏览器控制台抽查：
   - `lbItemMeta('PrimalItemConsumable_Egg_SnowDragon_C')` → 应返回 `{zh:'寒辉雪龙蛋', icon:'HUD_AureliaxEgg_Icon', ...}`
   - `lbItemMeta('PrimalItemConsumable_BloodSap_C')` → 应返回 `{zh:'血色树液', ...}`
3. 存档实测：等 Los 出现该类物品实例（当前 Los `_item.json.gz` 3717 条**实测无此两物**，故线上暂无实例可验，属"提前补录"）

## 五、残留风险

| 风险 | 说明 | 对策 |
|------|------|------|
| Blood Sap 类名未 100% 实锤 | wiki Stub 无 ID；推理依据为同族 Cactus Sap | alias 写推理名；若未来命中失败，用存档真实类名一改即好 |
| 受精版图标复用 | 未单独确认受精蛋图标名 | 复用主蛋图标；若有独立图标（`..._Fertilized`）再替换 |
| `src` 标签 | `game_official` 为新标签，无先例 | 不影响前端逻辑，仅溯源用；可改 `manual` |

## 六、附：本件相关核查记录

- `汉化\item_zh.json`（3065 条）现无 `BloodSap` / `SnowDragon Egg` 任何条目（仅 `SnowDragonSaddle`=寒辉雪龙鞍）
- `汉化\icons_all.json` / `icons2.json` 中**无** BloodSap 物品图标之"缺"——`Blood_Sap` 已在（`/ASA/resources/`）
- 前端 `LB_ITEM_PRES` 前缀表**不含** `Egg` → 候选链仅 2 级，key 用 `Egg_SnowDragon` 最稳
