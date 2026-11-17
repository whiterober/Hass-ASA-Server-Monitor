# `_item.json` 补 `containerOwnerPid` —— 插件端规格

- 日期：2026-11-12
- 需求方：前端「安全回档 · 背包内容差异」
- 执行方：插件端（ArkSaveReader / exe）
- 一句话：**`_item.json` 里 `containerType='player'` 的物品，请补 `containerOwnerPid` 字段。**

---

## 1. 为什么必须插件端补

| 数据源 | 是否带 pid |
|---|---|
| 同一 exe 产出的 `playerItems`（目标档，light 模式） | ✅ 有 `pid`（例：「人类」= 413776549） |
| `_item.json` 的 `containerType='player'` 物品（当前档） | ❌ **365/365 条全无** `containerOwnerPid` |

说明 exe 内部**知道**归属，只是 `_item.json` 这一路的导出没写该字段。

前端/后端 Python 都无法可靠补齐（见第 3 节实测）。

## 2. 为什么要 pid 而不是 playerName

`人类` 是 ARK 的**默认角色名**，会重名。当前按 `playerName` 分组会把不同玩家的背包合并成一组，导致：

- 格数统计错（多算/少算）
- 两个玩家之间互相对比，产生假差异

必须用 `containerOwnerPid` 做分组键，`playerName` 只用于显示。

## 3. 前端能否自救（实测：不行）

思路：用物品的 `containerId` 去容器记录 `recs` 反查 `containerOwnerPid`。

实测（Isl，365 条 player 物品）：

| 指标 | 结果 |
|---|---|
| `recs` 里 player 类容器去重 `containerId` | **仅 7 个** |
| 反查命中 | **193 / 365（53%）** |
| 反查正确性 | ❌ 同一 `containerId` 反查到不同 pid ⇒ **会错配** |

⇒ 反查不可用。

## 4. 需求（最小改动）

在 `_item.json` 的 `items[]` 中，对 `containerType === 'player'` 的条目：

```jsonc
{
  "class": "PrimalItem_StartingNote_C_2144923358",
  "containerType": "player",
  "containerId": "f7e65cad549bb547ad48b86ba288e63f",
  "playerName": "人类",
  "containerOwnerPid": 413776549,          // ← 新增：角色 pid（整数）
  "containerOwnerEosId": "000259b6..."     // ← 可选：EOS id，便于跨服/改名后仍能对上
}
```

- 类型：`containerOwnerPid` 用**整数**（与 `playerItems[].pid` 一致，便于前端直接比对）
- 非 player 容器不需要该字段
- 无法确定归属时请省略字段（前端会退回按名字分组），**不要填 0**（0 会被当成合法 pid）

## 5. 验收

| # | 项 | 通过标准 |
|---|---|---|
| V1 | 字段存在 | `_item.json` 中 `containerType='player'` 条目 ≥ 95% 带 `containerOwnerPid` |
| V2 | 与 playerItems 对齐 | 同一玩家同一件物品，`_item.json` 的 `containerOwnerPid` == `playerItems` 的 `pid` |
| V3 | 重名可区分 | 两个都叫「人类」的角色，其物品 `containerOwnerPid` 不同 |
| V4 | 不回归 | 现有消费方（容器视图/物品数量统计）读取行为不变（新增字段属纯增量） |

## 6. 前端侧待办（收到字段后）

`lbArkBkBagLoad()` 改为：

- 当前档 `per`：分组键 `String(it.containerOwnerPid || '')`，无该字段时退回 `playerName`
- 目标档 `tPer`：分组键 `String(x.pid || '')`
- 选角色：优先当前登录角色 `lbCurPid()`
