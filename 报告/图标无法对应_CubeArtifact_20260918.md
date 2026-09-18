# 图标无法对应清单 · CubeArtifact_Icon

> 生成时间：2026-09-18
> 数据源：`/config/www/asa-data/item_zh.json`（字典 v20260918-3353，共 1156 条）
> 判定口径：`icon === 'CubeArtifact_Icon'` 的条目 = **当前无专属图标可用**，暂用立方神器图标占位

---

## 一、汇总

| 项 | 值 |
|---|---|
| 命中条目 | **14 条** |
| 涉及组 | 6 组（ApexDrop_Boaratos ×2、Trophy_Cyclops ×3、Trophy_Gorgon ×3、Trophy_Hydra ×3、Trophy_MasterController ×1、Artifact_11/12 ×2） |
| 图标键 | `CubeArtifact_Icon`（R2：`.../ASA/drops/CubeArtifact_Icon.png`） |
| 性质 | 其中 `Cyclops` / `Gorgon` / `Hydra` 三组为**用户指定统一使用**该图标；其余为**暂无机型图标**的占位 |

---

## 二、明细（14 条）

| # | 类名 | 中文 | 英文 | kind | 无专属图标原因 |
|---:|---|---|---|---|---|
| 1 | `ApexDrop_Boaratos` | 焰鬃獠猪獠牙 | Boaratos Tusk | trophy | 新生物掉落，R2 `drops` 目录无博阿拉托斯专属掉落图标 |
| 2 | `ApexDrop_Boaratos_Flaming` | 焰鬃獠猪 | Flaming Boaratos Tusk | trophy | 同上（火焰变体） |
| 3 | `PrimalItemArtifact_11` | 神秘笔记#11 | Mysterious Note #11 | trophy | 非神器，R2 无「笔记」类图标 |
| 4 | `PrimalItemArtifact_12` | 神秘笔记#12 | Mysterious Note #12 | trophy | 同上 |
| 5 | `PrimalItemTrophy_MasterController` | 主宰者 | Master Controller | trophy | ASA 新 Boss，R2 `drops` 无专属战利品图标 |
| 6 | `PrimalItemTrophy_Cyclops_Alpha` | 独眼巨人（精英） | Cyclops Alpha | trophy | 用户指定统一用 `CubeArtifact_Icon` |
| 7 | `PrimalItemTrophy_Cyclops_Beta` | 独眼巨人（困难） | Cyclops Beta | trophy | 同上 |
| 8 | `PrimalItemTrophy_Cyclops_Gamma` | 独眼巨人（普通） | Cyclops Gamma | trophy | 同上 |
| 9 | `PrimalItemTrophy_Gorgon_Alpha` | 蛇发女妖（精英） | Gorgon Alpha | trophy | 用户指定统一用 `CubeArtifact_Icon` |
| 10 | `PrimalItemTrophy_Gorgon_Beta` | 蛇发女妖（困难） | Gorgon Beta | trophy | 同上 |
| 11 | `PrimalItemTrophy_Gorgon_Gamma` | 蛇发女妖（普通） | Gorgon Gamma | trophy | 同上 |
| 12 | `PrimalItemTrophy_Hydra_Alpha` | 海德拉（精英） | Hydra Alpha | trophy | 用户指定统一用 `CubeArtifact_Icon` |
| 13 | `PrimalItemTrophy_Hydra_Beta` | 海德拉（困难） | Hydra Beta | trophy | 同上 |
| 14 | `PrimalItemTrophy_Hydra_Gamma` | 海德拉（普通） | Hydra Gamma | trophy | 同上 |

---

## 三、建议

1. **博阿拉托斯（Boaratos）**：若 R2 后续补充 `Boaratos_Icon` / `ApexDropBoaratos_Icon`，应立即替换 `ApexDrop_Boaratos*` 两条。
2. **主宰者（Master Controller）**：ASA 后续版本若提供专属战利品图标，替换 `PrimalItemTrophy_MasterController`。
3. **神秘笔记 #11 / #12**：属笔记类物品，建议补一条 `MysteriousNote_Icon`（或复用 `ExplorerNote_Icon`）。
4. **Cyclops / Gorgon / Hydra 三组**：当前为用户指定占位，一旦 R2 `drops` 目录出现对应图标（如 `TrophyCyclops_Icon`），应整组替换。

---

## 四、附：本轮同时纠正的相邻问题

| 类名 | 问题 | 处理 |
|---|---|---|
| `PrimalItemArtifactSE_01`（卫士） | 上轮误映射为 `ArtifactOfTheCrag_Icon` | 改为 **`ArtifactOfTheGatekeeper_Icon`**（Gatekeeper=卫士） |
| `PrimalItemArtifactSE_02`（岩壁） | 上轮误映射为 `ArtifactOfTheGatekeeper_Icon` | 改为 **`ArtifactOfTheCrag_Icon`**（Crag=岩壁） |
| `PrimalItemArtifactAB` | 英文为图标名残留 `HUD VRBoss Trophy` | 改为 **`Artifact of the Depths`** |
| `PrimalItemArtifact_11/_12` | 英文为 `Artifact1`（编号错） | 改为 **`Mysterious Note #11` / `#12`** |
| `PrimalItemArtifact_01`~`_09`、`AB_2/_3`、`SE_*`、`Extinction_*` | 英文为代号（`Artifact6` / `SE 01` / `AB 2` / `Extinction Ice Kaiju`） | 全部改为 **官方全称**（PO 来源） |
