# 风力发电机耐久接口对接说明

> 面向：前端 / 后端（`独立后端`）
> 日期：2026-10-16 ｜ 数据来源：实服 Isl（RCON 32320）只读实测
> 插件版本：**无需改动**（现有能力已足够）

---

## 1. 结论先说

| 问题 | 答案 |
|---|---|
| 前端能直接查风机耐久吗？ | ❌ 不能直连 RCON，必须经**后端代理** |
| 需要改插件（dll）吗？ | ✅ **不需要**，现有 `actor` + `fields=` 白名单已够用 |
| 需要新增什么？ | 后端加 **1 个接口** + 前端加 **1 张卡片** |
| 「掉耐久时间」是游戏字段吗？ | ❌ 不是，是**算出来的**（见 §5） |

---

## 2. 数据来源：一条 RCON 命令

```
TransferIdentityFix.WorldProbe actor filter=WindTrubine props=1 fields=Health,MaxHealth,PoweredBatteryDurabilityToDecreasePerSecond top=1
```

### 2.1 ⚠️ 三个必须知道的坑

1. **类名是官方错拼的 `WindTrubine`**（少一个 `r`）
   - 用正确拼写 `WindTurbine` ⇒ `matched=0`，查不到任何风机
2. **`fields=` 必须和 `props=1` 同时给**
   - 只给 `fields=` 不给 `props=1` ⇒ 白名单**静默失效**，返回默认清单字段（实测确认）
3. **一次调用只 dump 一台**（`props=1` 只对 `propsIdx` 指定的那一台生效）
   - 8 台风机 = **8 次调用**；但每次仅 ~1 KB、服务端净耗时 ~0.1 s ⇒ 总耗时 <1 s

### 2.2 体积实测（同一台，Isl）

| 写法 | 响应体积 |
|---|---|
| `actor filter=WindTrubine props=1` | **20,170 B**（570 项属性全 dump，截断到 400 条） |
| `actor filter=WindTrubine props=1 fields=<3字段>` | **1,056 B** ✅（降 95%） |
| `actor byname=1 filter=<对象名> props=1 fields=Health` | **936 B** |

> **推荐**：拉清单用 `actor filter=WindTrubine top=60`（8 台仅 1,760 B），再逐台用 `byname=1` + `fields=` 精确取数。

---

## 3. 后端接口设计

### 3.1 接口定义

```
POST /api/wind_status
Content-Type: application/json
```

**请求体**

```json
{
  "server": "Isl",
  "fresh": 1
}
```

| 字段 | 必填 | 说明 |
|---|---|---|
| `server` | ✅ | 图名（`Isl` / `Sco` / `Cen` / `Abe` / `Ext` / `Ast` / `Rag` / `Val` / `Los` / `Gen`） |
| `fresh` | ❌ | `1` = 跳过服务端缓存强制重读；不传则走缓存（建议 TTL **60 s**） |

### 3.2 响应体

```json
{
  "ok": true,
  "server": "Isl",
  "worldTime": 287377058.83,
  "count": 8,
  "generatedAt": "2026-10-16T17:58:12+08:00",
  "cacheAgeMs": 0,
  "turbines": [
    {
      "objectName": "WindTrubine_C_2146405356",
      "x": -268350,
      "y": -262998,
      "z": -6762.5,
      "health": 3642.11,
      "maxHealth": 6000,
      "perSecond": 0.01389,
      "pct": 60.70,
      "depleteHours": 72.85,
      "decayHours": 96.0,
      "wind": 3
    }
  ]
}
```

---

## 4. 字段语义

| 字段 | 类型 | 来源 | 说明 |
|---|---|---|---|
| `objectName` | string | RCON `actors[].objectName` | 实体唯一名，前端 key |
| `x` / `y` / `z` | number | RCON `actors[].x/y/z` | 世界坐标（**游戏单位，非经纬度**） |
| `health` | number | 属性 `Health` | **当前耐久度** |
| `maxHealth` | number | 属性 `MaxHealth` | 耐久上限（风机固定 **6000**） |
| `perSecond` | number | 属性 `PoweredBatteryDurabilityToDecreasePerSecond` | **每秒消耗耐久**（实测 **0.01389**） |
| `pct` | number(%) | 后端算 | `health / maxHealth * 100` |
| `depleteHours` | number | 后端算 | **预计多少小时后耗尽**（见 §5） |
| `decayHours` | number | 属性 `DecayDestructionPeriod` ÷ 3600 | 腐朽倒计时（风机 = **96 h**） |
| `wind` | number | 属性 `CurrentWind` | 当前风力档（可选） |

---

## 5. 计算公式（后端做）

```
pct           = health / maxHealth * 100
depleteHours  = health / perSecond / 3600
decayHours    = DecayDestructionPeriod / 3600          // 风机 = 345600 s = 96 h
```

**判据**：两者取**较小者**才是真正的「剩余寿命」——
> 风机实测 `depleteHours ≈ 12~73 h` **<** `decayHours = 96 h` ⇒ **耐久先坏，腐朽在后**。
> 前端提示应基于 `depleteHours`。

**可信度说明**：`perSecond` 是**真实生效的速率**（非静态配置），已用两次采样交叉验证：
- 采样 1：`Health = 3651.27`
- 采样 2（3 分钟后）：`Health = 3648.65`
- 差 2.62 ÷ 0.01389 = **189 s ≈ 3 min** ⇒ 与采样间隔吻合 ✅

---

## 6. 建议实现流程（后端）

```
1. 查缓存（key = server，TTL 60 s）→ fresh=1 则跳过
2. RCON: actor filter=WindTrubine top=60           → 拿 objectName + 坐标清单
3. 对每个 objectName:
     RCON: actor byname=1 filter=<objectName> props=1 \
           fields=Health,MaxHealth,PoweredBatteryDurabilityToDecreasePerSecond \
           ,DecayDestructionPeriod,CurrentWind top=1
     （参数字符串拼接时用逗号，勿多空格）
4. 按 §5 计算 pct / depleteHours / decayHours
5. 按 depleteHours 升序排序（最危险的排最前）
6. 落盘响应 + 写缓存
```

**服务端新键**：建议在插件响应里零改动 —— 全部计算放后端。

### 6.1 ⚠️ RCON 参数上限提醒（重要）

`actor` 子命令只解析 **a1..a4 共 4 个 token**，第 5 个起**静默丢弃**，且**不报错**。

| 写法 | token 数 | 结果 |
|---|---|---|
| `actor filter=X props=1 fields=A,B,C` | 3 | ✅ 安全 |
| `actor byname=1 filter=X props=1 fields=A,B,C` | **4** | ✅ 正好到上限 |
| `actor byname=1 filter=X props=1 fields=A,B,C top=1` | 5 | ⚠️ `top=1` 被丢弃（实测无副作用，因默认即 top=1） |

**结论**：逐台查询走 4 token 写法（`byname=1` + `filter=` + `props=1` + `fields=`），
**绝不要再追加第 5 个参数**（例如 `slim=1`、`top=`），否则 `fields=` 会被挤掉、响应瞬间涨回 20 KB。

---

## 7. 前端展示建议

| 元素 | 建议 |
|---|---|
| 列表项 | `objectName` 短名（取末尾 10 位数字） |
| 进度条 | `pct` 宽度；`< 20%` 橙色、`< 10%` 红色闪烁 |
| 关键文案 | 「约 **72.9 小时**后耗尽」（取 `depleteHours`） |
| 排序 | 按 `depleteHours` 升序，最紧急的置顶 |
| 地图点 | 用 `x`/`y` 画点（注意：需与现有地图的坐标换算口径一致） |
| 刷新 | 60 s 自动轮询；或手动「刷新」按钮传 `fresh:1` |
| 空态 | `count === 0` ⇒ 显示「本图暂无风力发电机」 |

---

## 8. 实测样例数据（Isl，2026-10-16）

```json
{
  "ok": true, "server": "Isl", "count": 8,
  "turbines": [
    {"objectName":"WindTrubine_C_2146405356","x":-268350,"y":-262998,"z":-6762.5,
     "health":3642.11,"maxHealth":6000,"perSecond":0.01389,"pct":60.7,"depleteHours":72.85,"decayHours":96.0},
    {"objectName":"WindTrubine_C_2146814415","x":-266958,"y":-270939,"z":-13662.5,
     "health":3648.73,"maxHealth":6000,"perSecond":0.01389,"pct":60.8,"depleteHours":73.0,"decayHours":96.0},
    {"objectName":"WindTrubine_C_2146468411","x":-274917,"y":-260873,"z":-7962.5,
     "health":3646.48,"maxHealth":6000,"perSecond":0.01389,"pct":60.8,"depleteHours":72.9,"decayHours":96.0},
    {"objectName":"WindTrubine_C_2145162270","x":-320089,"y":-167734,"z":-8686.5,
     "health":599.70,"maxHealth":6000,"perSecond":0.01389,"pct":10.0,"depleteHours":12.0,"decayHours":96.0},
    {"objectName":"WindTrubine_C_2146843231","x":-319415,"y":-150948,"z":-13205.8,
     "health":599.89,"maxHealth":6000,"perSecond":0.01389,"pct":10.0,"depleteHours":12.0,"decayHours":96.0},
    {"objectName":"WindTrubine_C_2146549330","x":302.502,"y":-406.075,"z":916.399,
     "health":599.98,"maxHealth":6000,"perSecond":0.01389,"pct":10.0,"depleteHours":12.0,"decayHours":96.0},
    {"objectName":"WindTrubine_C_2139489481","x":-168819,"y":50945.5,"z":-14074.6,
     "health":599.85,"maxHealth":6000,"perSecond":0.01389,"pct":10.0,"depleteHours":12.0,"decayHours":96.0},
    {"objectName":"WindTrubine_C_2146705702","x":299553,"y":-29967.4,"z":-14436.1,
     "health":599.90,"maxHealth":6000,"perSecond":0.01389,"pct":10.0,"depleteHours":12.0,"decayHours":96.0}
  ]
}
```

> ⚠️ 上表中 **5 台只剩 10%（~12 小时寿命）**，是真实线上状态，非测试造数。

---

## 9. 其它可用属性（如需扩展）

以下字段也存在于风机上，可并入 `fields=`（注意 token 总数 ≤ 3 个参数）：

| 属性 | 实测值 | 用途 |
|---|---|---|
| `ReplicatedHealth` | 3651.27 | 同步副本（与 `Health` 一致） |
| `LastHealthPercentage` | 1 | 上次记录百分比（**注意实测恒为 1，勿直接当 pct 用**） |
| `ContainerActiveDecreaseHealthSpeed` | 0 | 附加消耗速度 |
| `DecayDestructionPeriodMultiplier` | 1 | 腐朽周期倍率 |
| `MinWind` / `WindUpdateInterval` | 0 / 15 | 风力下限 / 风力刷新秒 |
| `CurrentFuelQuantity` | 0 | 燃油（风机用风，通常 0） |

---

## 10. 一句话总结

**不用碰插件。** 后端加一个 `POST /api/wind_status`（内部 9 条 RCON 命令、约 30 行），返回上面的 JSON，前端按 `pct` 画进度条、按 `depleteHours` 排序提示即可。
