# dino-import 键位数据契约（防错基准）

> 目的：把「键位改动」的隐性规则写成可核对的契约，避免反复出现
> 「以为加了 → 界面看起来像默认」「改了一层漏了另一层」这类错误。
> 任何键位相关改动完成后，**必须**在浏览器执行 `lbKeymapAudit()`，`ok === false` 时不得汇报完成。

---

## 一、三层结构（必须同时理解）

| 层 | 存储位置 | 作用 | 漏改的后果 |
|---|---|---|---|
| **① 动作定义层** | `LB_KEYMAP_CUSTOM.actions`（localStorage `lb_keymap_actions_<玩家>_<游戏>`） | 有哪些动作、默认键位、备注、`custom`（是否新增动作） | 动作不存在，界面无此行 |
| **② 玩家键位层** | `LB_KEYMAP.profiles[<game>].map[aid]`（localStorage `lb_keymap_<玩家>`） | 玩家对每条动作的**实际**绑定 + `_mark` | 界面无法区分「改过」与「没改过」 |
| **③ 展示层** | `lbKeymapRender()` / `lbKeymapRowHtml()` / `lbKeymapCellHtml()` / `lbKmChips()` | 表格、按键、图标、紫点、备注 | 数据对了但界面没刷新 / 渲染条件写窄了 |

> ⚠️ **用户口中的「默认动作 / 自定义动作」= 界面表现**（有无紫点、是否进「只看改动」）。
>
> 🔴 **v5438 语义定稿（用户口径「附件这种就是官方默认的键鼠键位，为啥要显示自定义样式」）：**
>
> | 概念 | 判定 | 用途 |
> |---|---|---|
> | **新增动作** | ① 层 `custom === 1` | 动作属性，与玩家操作无关（当前仅鼠标三键） |
> | **本列改动** | `lbKmColCustom(aid, col)`（真 diff，与默认不同才算） | **键帽底色**只认这个 |
> | **行级自定义** | `a.custom===1 \|\| 当前列真改动 \|\| 当前列标记` | 紫点 / 进「只看改动」/ 动作名变白 |
>
> **官方动作（`custom !== 1`）绝不允许带 `_mark` / `_markPad` / `_markKbm`** —— 否则官方默认键（如 内射 `J`）会被误染成自定义样式。
>
> 🔴 **v5439：标记必须列级** —— `_mark` 是**行级单份**，手柄列与键鼠列共用，动一边必然连带另一边（用户实测报障）。
> 现改用 `_markPad` / `_markKbm`；旧 `_mark` 仅当两列都未设时兼容回退。
>
> 🔴 **v5439：键名归一必须用 `lbKmStoreKey()`** —— 旧实现用 `lbKeymapSkinKey()` 比字符串，
> 而 `steamdeck_button_options` 与 `xbox_button_menu` 换算后**不相等** ⇒ 同一颗 Menu 键被误判成「改过」。

---

## 二、不变量（`lbKeymapAudit()` 会逐条检查）

| # | 规则 | 违反表现 |
|---|---|---|
| 1 | `LB_KEYMAP_CUSTOM.deleted` 里的 id **不得**仍存在于 `actions` | 已删动作又冒出来 |
| 2 | `_mark` / `_markPad` / `_markKbm` **只允许**长在「新增动作」（`custom === 1`）上；官方动作带任一种即 FAIL | 官方默认键位被显示成自定义样式（v5438/v5439 事故） |
| 3 | 主键位表格**不得**出现删除图标 `.lb-km-del` | 玩家界面误出删除入口 |
| 4 | SCUM 业务断言：鼠标左键→`mouse_left`、中键→`mouse_scroll`、右键→`mouse_right`；<br>陀螺仪必须做主键（不得出现在 `chord`）；<br>`scum_rpt` / `scum_mode_prev` / `scum_mode_next` 不得存在 | 键位错位、被删动作复活 |
| 5 | 键帽 `.lb-km-key.custom` 必须与 `lbKmColCustom(aid, 当前列)` 一致 | 键帽配色与「本列是否真改动」脱钩（v5438 事故直接原因） |

---

## 三、「新增自定义动作」标准流程（三件套，缺一不可）

1. **① 层**：`LB_KEYMAP_CUSTOM.actions` 加动作条目（`{id, g, zh, zhPad, pad, kbm, note, custom:1}`）
2. **② 层**：`profile.map[aid] = { pad, kbm, _mark: 1 }`
3. **验收**：`lbKeymapAudit().ok === true`

> 通过 **动作管理 UI** 保存新动作时，代码已自愈（v5438 起自动补 `custom:1` + ② 层 + `_mark:1`）；
> **编辑既有官方动作时不再写 `_mark`**（改动由列级 diff 自动识别）。
>
> 🔴 **`custom:1` 的含义 = 游戏官方没有这个动作（我们新增的）**，不是「玩家改过」。
> 官方动作即使被玩家改键，也**不得**打 `custom:1` / `_mark:1`。

---

## 四、常见错法（历史案例）

| 错法 | 现象 | 正确做法 |
|---|---|---|
| 只写 ① 层不写 ② 层 | 「为什么是默认动作？」 | 三件套 |
| 把用户删掉的动作「恢复」回来 | 「为啥非要恢复毫无关系的东西」 | 删了就是删了；`deleted` 只清记录不复活实体 |
| 用「改名既有动作」代替「新增动作」 | 「谁让你当成默认动作添加」 | 用户说"加 X"默认=新增自定义动作，不是改写既有动作 |
| 给未改过的行加图标 | 「未改过就不该有删除按钮」 | 右侧图标严格 `e.isCustom` 才出 |
| 红叉删除图标 | 已作废（v5427） | 主表格只有紫点；删除只在「动作管理」 |
| 单键 + `chord` 不写 `mode:'chord'` | 组合键被静默吞掉 | 显式 `mode:'chord'` |
| 陀螺仪放进 `k` 数组第 2 位 | 被当组合键 | `k:['steamdeck_gyro']` + `chord:实体键` |
| 用 `_ver_check_b.py` 判部署 | 读到 CF 边缘缓存旧版本 | 页面内 `fetch(url+'?t='+Date.now(), {cache:'no-store'})` |
| **键帽底色用行级 `e.isCustom`** | 官方默认键（内射 `J`）被染成自定义紫底（v5438） | 键帽只用列级 `lbKmColCustom(aid, col)` |
| **给官方动作批量写 `_mark:1`** | 整表显示成「已修改」，紫点泛滥（v5438） | `_mark` 只给 `custom:1` 的新增动作 |

---

## 五、验收命令

```js
// 浏览器控制台 / Playwright evaluate
lbKeymapAudit()          // → {ok:true/false, fails:[], warns:[], info:{}}
```

`info` 会给出：`profileId / acts / baseActs / customActs / mapLen / isCustomActs / dots / deleted`

---

## 六、数据文件同步四处（改 SCUM 动作表时）

1. `堕落玩偶_动作表_v1.json`（权威源）
2. `堕落玩偶_导入_全部39条_v4.json` / `堕落玩偶_导入_黑色36条_v4.json`（重跑 `tmp/_scum_export3.py`，**必须保留 `custom` 字段**）
3. 浏览器 localStorage：`lb_keymap_actions_<玩家>_scum`（① 层）+ `lb_keymap_<玩家>`（② 层）
4. `_preview_scum_actions.html`（重跑 `tmp/_gen_preview_scum3.py`）
