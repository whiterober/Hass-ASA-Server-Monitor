# `TargetingTeam` 字段修正说明（v135 定稿）

> 日期：2026-10-30 ｜ 影响：所有 `props=1` 输出中的 4 字节整数字段 ｜ 插件：**v135**
> 本文为最终版，取代此前按"声明类型"或"数值大小"判定的两版方案。

---

## 1. 问题

`TargetingTeam`（所属部落 ID）被当成浮点读，输出无意义大数：

```json
"TargetingTeam": 2.5341156975745992e+30     // 错，真值 1912594779
```

---

## 2. 为什么两条旧路都不行

| 方案 | 做法 | 结果 |
|---|---|---|
| v129 | 读 `FProperty` 类名判 int/float | ❌ 失败并回退：5 个 float 属性被按 int32 读成位模式（`1`→`1065353216`、`0.5`→`1056964608`） |
| v132/v133 | 按数值特征猜（次正规 / NaN / `|v|>1e15`） | ❌ 漏判：`1042358710` 按 float 读是 `0.157355`、`1228031745` 是 `730224.06`，与合法小数无法区分 |
| **v134/v135** | **让引擎自己把值导出成文本** | ✅ 定稿 |

结论：**4 字节槽仅凭 `ElementSize` 无法区分 int32 / float32，必须由引擎按声明类型格式化取值。**

---

## 3. 最终实现（v135）

`TifReadNumByRef()` 的 4 字节分支：

1. 调 `FProperty::ExportText_Direct()` 取该值的文本（int 出 `1912594779`，float 出 `0.5`），严格 `strtod` 解析 → 类型由引擎保证
2. 导出不可用（结构体/数组/FName 等非数字）→ 回退旧启发式（次正规/NaN/超大 → int32）
3. SEH 保护：`__try/__except` 叶子函数，取不到只返回 false，绝不崩服

同口径也用于天气语义通道（`TifFillWeatherSem`），保证两处取值一致。

---

## 4. 前端影响

| 字段 | 旧值（错） | 新值（对） |
|---|---|---|
| `TargetingTeam`（塔 `_2146585526`） | `2.5341156975745992e+30` | `1912594779` |
| `TargetingTeam`（塔 `_2146499346`） | `9.4614690808264e+19` | `1621369181` |
| `CustomTimeDilation` | `1` | `1`（不变） |
| `NetPriority` | `0.5` | `0.5`（不变） |
| `NetUpdateFrequency` | `0.01` | `0.01`（不变） |

建议保留一道校验（旧 dll 仍在线时有用）：

```js
function tribeIdOf(obj) {
  const v = obj.TargetingTeam;
  if (typeof v !== "number" || !Number.isFinite(v)) return -1;
  if (!Number.isInteger(v) || v < 0 || v > 2147483647) return -1;
  return v;
}
```

---

## 5. 生效前提

v135 dll：**2,048,000 B，md5 `c10f301c860c6d91c2fec6e896be579c`**（产物 2026-10-30 19:07:51）

- 🔴 判断某台是否已升级：只看 `TransferIdentityFix.DinoMutPing` 返回的 `build`
  （v135 = `Oct 30 2026 19:06:38`）；`config.json` 的 `version` 不可作判据
- 已实测（Isl）：`build` 命中、`TargetingTeam=1621369181`、浮点三项不变

---

## 6. 诊断参数（v135）

```
TransferIdentityFix.WorldProbe actor filter=<类名> props=1 ptype=1
```

`ptype=1` 每属性附：`off` / `sz` / `exp`（引擎导出的原文本，null 表示导出不可用）/ `bytes`(8B hex) / `u32` / `i32` / `f32` / `f64`。
> v132–v134 的 `rmode=` 参数与 `tname` / `pred` / `vt` 诊断已**移除**（实验期产物，勿再使用）。

---

## 7. 一句话总结

**不再猜类型，直接让引擎按它自己的声明类型把值格式化出来再解析** —— 大整数不会变科学计数法，浮点也不会被误读成整数。
