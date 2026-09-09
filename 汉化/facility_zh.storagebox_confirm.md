# StorageBox_ 前缀组合类补收验证表（漏收 4 实 + 3 防患 · 全服 facility 数据）

> 背景：数据源把「泰克/工业带库存容器」蓝图记成 `StorageBox_<真实设施>` 前缀组合类。`facility_zh` 权威表只有真实名（如 `TekGenerator`），`StorageBox_TekGenerator` 匹配不上 → 设施区显示英文 camel 拆词 fallback。
> 现状：v922 已上线；StorageBox_Huge/Large/Small/Barrel/Balloon/ChristmasGift_WW（真储物箱）已在表内，**无需处理**。
> 表格列：**数据 class**（去 _C 尾缀）｜**全服数**（Ext=你在看的服）｜**当前显示（fallback）**｜**应映射词条**（→ 表内权威内容）｜**处理建议**

---

## ✅ 数据实际存在（4 个，需补词条）

| # | 数据 class | 全服数 | 分服(Ext) | 当前显示 | 应映射 | 权威词条(en/zh/icon) |
|---|-----------|:---:|:---:|---|---|---|---|
| 1 | `StorageBox_TekTransmitter` | 30 | Cen1 Isl5 Abe5 Ast9 **Ext5** Los3 Val2 | Storage Box Tek Transmitter ⚠️图标错 | `TekTransmitter` | Tek Transmitter / 泰克传送器 / icon 待定 |
| 2 | `StorageBox_TekGenerator` | 80 | Cen2 Isl10 Abe13 Ast16 **Ext13** Los7 Val4 Rag6 Gen9 | Storage Box Tek Generator | `TekGenerator` | Tek Generator / 泰克发电机 / Tek_Generator ✓ |
| 3 | `StorageBox_TekReplicator` | 16 | Isl3 Abe4 Ast3 **Ext4** Los1 Val1 | Storage Box Tek Replicator | `TekReplicator` | Tek Replicator / 泰克复制器 / Tek_Replicator ✓ |
| 4 | `StorageBox_Fabricator` | 29 | Sco1 Cen1 Isl7 Abe6 Ast2 **Ext5** Los2 Val1 Rag3 Gen1 | Storage Box Fabricator ⚠️图标空 | `Fabricator` | Fabricator / 机床 / Forge2_Icon ✓ |

## 🛡️ 防患（当前数据 0，但用户清单提及——建议一并补，未来出现即正确）

| # | 数据 class | 当前数据 | 应映射 | 权威词条(en/zh/icon) | 备注 |
|---|-----------|:---:|---|---|---|---|
| 5 | `StorageBox_ChemBench_Tek` | 0 | `ChemBench_Tek` | Tek Chemistry Bench / 泰克化学实验桌 / Chemistry_Bench | 用户列 Ext=4，当前 recs 无（可能聚落数据差异/未刷） |
| 6 | `StorageBox_AnvilBench` | 0 | `AnvilBench` | Smithy / 铁匠台 / Smithy | 用户列 Ext=10 |
| 7 | `StorageBox_IndustrialGrinder` | 0 | `Grinder` | Industrial Grinder / 工业研磨机 / Industrial_Grinder | 用户列 Ext=4；表内键是 `Grinder`（无 IndustrialGrinder） |

---

## ❓ 待你确认：StorageBox_TekTransmitter 图标（页面左上角 A/B 已展示）

| 选项 | icon 键 | 源文件 | 说明 |
|---|---|---:|---|
| **A** | `TEKPortal_Icon` | facility/TEKPortal_Icon.png | 容器视图(L5711 TekTransmitter 规则)同款；facility 分类 |
| **B** | `Tek Transmitter` | misc/Tek Transmitter.png | 当前 facility_zh 用的键（misc 分类），你判为错 |

> ⚠️ 若选 A：需同时修正 facility_zh `TekTransmitter` 词条 icon（当前 B），并给 `StorageBox_TekTransmitter` 补词条时 icon 用 A。

## 📋 补收后预期效果（以 Ext 泰克传送器 chip 为例）

```
Storage Box Tek Transmitter  ──修复后──▶  🖼[A/B图标] 泰克传送器 Tek Transmitter
```

## 📁 涉及改动（你验证确认后执行）

1. `tmp/_final_confirm.py` FINAL 增 7 条（StorageBox_TekX → 同义权威 en/zh，source 同目标词条）
2. `汉化/facility_zh.json` 由 `_merge_fac.py` 重建（icon 由 SPECIAL 保证）
3. `dino-import.html` `LB_FACILITY_ICON_SPECIAL` 补 `StorageBox_TekTransmitter`(→A或B) + 其余对应 iconKey
4. bump v923 + `pwa/sw.js` CACHE
5. `_up_fac2.py` 上传 → `_deploy_cf.py` 部署 → 浏览器验证
