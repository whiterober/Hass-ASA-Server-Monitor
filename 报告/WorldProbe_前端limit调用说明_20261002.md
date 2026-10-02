# WorldProbe 前端调用说明：`limit` 与 `truncated`（2026-10-02）

> **面向对象**：前端开发
> **背景**：反馈「数据不全 / 只拿到一部分」，曾拟向后端申请 `offset` 分页
> **结论**：**后端无需任何改动** —— 问题在前端默认 `limit` 太小，请看下方两项改动

---

## 一、实测证据（Isl:32320，类别 `explorerchest` 共 246 个）

| 调用 | 响应字节 | `matched` | `returned` | `truncated` |
|---|---|---:|---:|---:|
| `query explorerchest`（默认） | 2,391 | 246 | **20** | **1** ⚠️ |
| `query explorerchest limit=200` | 20,333 | 246 | 200 | **1** ⚠️ |
| **`query explorerchest limit=500`** | 24,897 | 246 | **246** | **0** ✅ |
| `query explorerchest limit=2000` | 24,898 | 246 | 246 | 0 ✅ |

**关键事实**：

1. **`limit` 上限早已是 2000**（源码：`if (limit > 2000) limit = 2000;`），默认 200 —— **无需后端提高上限**；
2. **RCON 通道可完整承载约 25 KB 响应**，`limit=500` 时 `truncated=0`，**无截断**；
3. **全服最大的类别也只有 246 条**（`explorerchest`），**一次 `limit=500` 就能取全** → **不需要 offset 分页**。

> 📌 易混淆点：`scan` 的 `top` 上限是 **500**；`query` 的 `limit` 上限是 **2000**。两者不同。

---

## 二、前端需要改的两件事（二选一或都做）

### 改法 A（推荐，最简单）：把 `limit` 提到 500

```
TransferIdentityFix.WorldProbe query <type> limit=500
```

各服各类别的实际规模（Isl 实测，供参考）：

| 类别 | `matched` |
|---|---:|
| `explorerchest` | **246**（全服最大） |
| `beehive` | 77 |
| `cavecrate` | 28 |
| `beacon` | 25 |
| `treasurecache` | 4 |
| `seacrate` | 2 |
| `beaverdam` | 0 |

⇒ **`limit=500` 对当前所有类别都足够**。

### 改法 B（更严谨）：读 `truncated` 字段

响应里已有该字段：

| 值 | 含义 | 前端动作 |
|---|---|---|
| `0` | 已取全 | 正常展示 |
| `1` | **还有数据未返回** | ⚠️ **必须**重新以更大 `limit` 请求，否则会漏数据 |

> 当前**没有 `offset`**，无法分页续取；只能**一次把 `limit` 调大**。建议：`limit=500` + 若 `truncated=1` 则自动升到 `2000` 重试一次。

---

## 三、回答「为什么以前看起来没问题」

`limit` 默认值是 **200**，而多数类别（`beacon` / `cavecrate` / `seacrate` 等）实例数都远小于 200 → 一直正常。
**只有 `explorerchest`（246 个）会超过 200** → 出现 `truncated=1`，表现为「数据不全」。
