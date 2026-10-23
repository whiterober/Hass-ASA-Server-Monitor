# 手柄键位配置系统 · 实施计划 v1

> 立项日期：2026-10-23
> 需求原话：「我需要一个同流程一样按玩家存储的手柄按键配置系统以及展示界面（默认手柄键位+对应的键盘按键+玩家修改键位）」
> 追加口径：「展示 / 改键界面 改成放到 角色浮窗内」
> 当前基线版本：`v20261023-5167`

---

## 1. 目标

1. **玩家级键位表**：动作 ↔ 手柄键 ↔ 键盘键 的映射，按玩家存储、跨端同步（与采集流程同等级）。
2. **展示界面**：三列同屏 —— 默认手柄键位 / 对应键盘键 / 玩家改过的键位（改过的行有标记）。
3. **可改键**：点键位格子改键，支持冲突检测、单行还原、一键恢复默认。
4. **零后端改动**：复用现有 `/api/user_prefs` 存储通道。

**非目标（本期不做）**
- 不做游戏内实际改键（只做玩家自己的查阅/记录表）
- 不改采集流程的 key token 语义（联动列入期 3，可选）

---

## 2. 现有可复用资产（已核实）

| 资产 | 位置 | 说明 |
|---|---|---|
| 键位图标 CDN | `lbHfKeySrc(v)` → `https://img.whiterober.ccwu.cc/ASA/keys/<键名>.png` | **直接用**，无需新图 |
| 键位全集（76 个 / 5 组） | `LB_HF_KEY_GROUPS`（约 L33526） | 鼠标 3 / 键盘 13 / Xbox 23 / PS 20 / Switch 14 |
| 键位扁平表 | `LB_HF_KEYS`（`LB_HF_KEY_GROUPS` 派生） | 冲突检测/搜索用 |
| 键位选择器 UI | 流程编辑器的 key token 选择器（`lbHfPop` + 分组网格） | 改键弹层直接复用样式 |
| 玩家级存储 + 跨端同步 | `/api/user_prefs` + `LB_PREFS_KEYS`（约 L34614） | 现成的按类时间戳 `kts` 冲突解决 |
| 角色浮窗 | `lbOpenRolePicker()`（约 L3863） | 键位界面宿主 |
| 浮窗通用样式 | `.lb-picker-overlay` / `.lb-picker-panel` / `.lb-picker-grid` / `.lb-picker-item` | 直接套用 |

---

## 3. 数据模型

### 3.1 默认键位（静态，写在 `dino-import.html` 内）

```js
// 动作 id 一旦发布不得改名（玩家 map 以此为主键）
var LB_KEYMAP_ACTIONS = [
  { g:'通用', id:'interact',     zh:'使用 / 互动',      pad:'XB_btn_X',        kbm:'PC_btn_E' },
  ...
];
```

> 放在 html 内（不新增部署文件）：改默认值本来就要发版，避免再维护一份静态 JSON。

### 3.2 玩家自定义（增量 diff，按玩家存）

```js
// localStorage['lb_keymap_<user>']  +  云端 user_prefs.keys.lb_keymap
{
  v: 1,
  layout: 'xbox',        // xbox | ps | switch —— 只影响手柄列的图标皮肤
  updatedAt: 1792761976793,
  map: {                 // 只存改过的动作；未出现的动作走默认表
    'interact': { pad:'XB_btn_Y', kbm:'PC_btn_F' }
  }
}
```

**要点**
- 只存 diff ⇒ 以后修正默认值不会覆盖玩家自定义
- `pad` 存的是「语义键名」，用同一套 `LB_HF_KEYS` 命名；PS/Switch 的图标差异在渲染层做映射（见 §4.3）
- 结构性校验：`map` 里未知的动作 id 在加载时忽略（防旧数据残留）

---

## 4. 界面设计（角色浮窗内二级视图）

### 4.1 入口与切换

`lbOpenRolePicker()` 增加视图状态 `LB._roleView`（`'roles'` | `'keys'`）：

| 位置 | 改动 |
|---|---|
| header 图标按钮组 | 新增 1 个 🎮 按钮（`mdi:gamepad-variant`，与 ⚙ 自助配置同排，`title="手柄键位"`）→ `lbRoleView('keys')` |
| 键位视图 header | 左侧「← 返回」（`lbRoleView('roles')`），标题「🎮 手柄键位」，右侧保留「恢复默认」「关闭」 |
| 浮窗宽度 | `roles` 视图 `max-width:400px`；`keys` 视图 `max-width:560px`（切视图时改 `panle.style.maxWidth`） |
| 关闭/返回 | 返回只切视图**不关浮窗**；关闭才移除 overlay |

### 4.2 键位视图线框

```
┌─ 🎮 手柄键位 ─────────────────────────────────┐
│ ← 返回   布局 [Xbox][PS][Switch]   [恢复默认]  │
│ 搜索 [__________]       已改 2 项      [关闭]  │
├──────────────┬──────────┬────────────────────┤
│ 动作          │ 手柄      │ 键盘                │
├──────────────┼──────────┼────────────────────┤
│ ● 使用 / 互动 │ [Y]      │ [F]                │  ← 紫点 = 与默认不同，点紫点单行还原
│   跳跃        │ [A]      │ [Space]            │
│   蹲下        │ [R3]     │ [C]                │
│  … 按组小标题  │          │                    │
└──────────────┴──────────┴────────────────────┘
```

- **分组小标题**：通用 / 战斗 / 移动 / 界面（沿用 `.lb-picker-subhead` 样式）
- **动作列**：中文名 + 小字英文 id（可选）
- **键位格**：`<img src="https://img.whiterober.ccwu.cc/ASA/keys/<键>.png">` + 键名小字；空格未设为虚线框「未设置」
- **搜索**：按动作中文名/id/键名过滤（复用 `lbPickerFilter` 思路，独立 id）

### 4.3 改键交互

1. 点键位格 → `lbKeymapPick(actionId, col, anchorEl)` 弹出键位网格（复用 `LB_HF_KEY_GROUPS` 分组，仅显示该列可用键：`col='pad'` 只显示手柄三组，`col='kbm'` 只显示鼠标+键盘）
2. 选中后写 `map[actionId][col]` → 立即重渲染该行
3. **冲突检测**（同列范围）：该键已被另一动作占用 ⇒ 该行琥珀色边框 + 提示条「X 已被『使用 / 互动』占用，仍要替换？」→ 确认后清空对方（置空而非删键，避免默认值回填歧义），并在对方行显示「未设置」
4. **单行还原**：点紫点 → 删除 `map[actionId]`
5. **恢复默认**：清空 `map` + `layout='xbox'`，二次确认浮窗
6. **保存**：切视图/关闭/改键后 800ms 防抖自动保存（沿用 `lbPrefsPush` 防抖），footer 显示「已保存 / 同步失败」

### 4.4 布局（Xbox / PS / Switch）

- 只改**手柄列**图标：`pad` 的语义键名统一（如 `pad_a`、`pad_b`、`pad_trigger_r`）
- 渲染层映射表：

```js
var LB_KEYMAP_PAD_SKIN = {
  xbox:  { pad_a:'XB_btn_A', pad_b:'XB_btn_B', pad_x:'XB_btn_X', pad_y:'XB_btn_Y', pad_lb:'XB_btn_LB', pad_rb:'XB_btn_RB', pad_lt:'XB_btn_LT', pad_rt:'XB_btn_RT', pad_menu:'XB_btn_Menu', pad_view:'XB_btn_View', pad_l3:'XB_btn_L_stick_Press', pad_r3:'XB_btn_R_stick_Press', pad_dpad:'XB_btn_Dpad' },
  ps:    { pad_a:'button_a_playstation', ... },
  switch:{ pad_a:'switch_button_a', ... }
};
```

> ⚠️ 若采「语义键名」会改变 `LB_HF_KEY_GROUPS` 现存的原始键名用法（流程 token 存的是 `XB_btn_A` 这类原始名）。
> **决策：不改现有体系** —— `map.pad` 直接存原始键名（`XB_btn_A` / `button_a_playstation` / `switch_button_a`），布局切换时按「同语义组」自动换皮（一张 `LB_KEYMAP_SEMANTIC` 映射表把三平台同义键归一组），改键时只允许同平台组的键。

---

## 5. 存储与同步（零后端改动）

| 步 | 动作 |
|---|---|
| 1 | `LB_PREFS_KEYS`（约 L34614）数组追加 `'lb_keymap'` |
| 2 | 改键 → 写 `localStorage['lb_keymap_<user>']` → `lbPrefsPush()`（800ms 防抖 → `POST /api/user_prefs`） |
| 3 | 打开页面 → `lbPrefsPull()` 已自动拉取，按 `kts['lb_keymap']` 与 `updatedAt` 判新旧覆盖 |
| 4 | guest / 未绑昵称 → 只存本地 + toast「已存本地，未登录不同步」 |
| 5 | 冲突（两端同时改）→ 沿用现有按类时间戳规则，较新者覆盖 |

---

## 6. 代码改动清单

### 6.1 新增（`dino-import.html`）

| 名称 | 说明 |
|---|---|
| `LB_KEYMAP_ACTIONS` | 20 项动作定义（含默认 pad / kbm） |
| `LB_KEYMAP_SEMANTIC` | 三平台同义键分组（换皮用） |
| `LB_KEYMAP` | 运行时状态 `{ v, layout, updatedAt, map }` |
| `lbKeymapLoad()` / `lbKeymapSave(debounce)` | 读/写 localStorage + 结构校验 |
| `lbKeymapEffective(actionId)` | 合并默认 + `map` ⇒ `{pad, kbm, isCustom}` |
| `lbKeymapSet(actionId, col, keyName)` | 改键 + 冲突处理 |
| `lbKeymapResetRow(actionId)` / `lbKeymapResetAll()` | 单行还原 / 全部还原 |
| `lbKeymapKeyBtnHtml(keyName)` | 键位格（图标 + 名称） |
| `lbKeymapPick(actionId, col, anchorEl)` | 键位选择弹层（复用 `LB_HF_KEY_GROUPS`） |
| `lbKeymapViewHtml()` | 键位视图 HTML |
| `lbKeymapRender()` | 视图渲染 + 事件绑定 |
| `lbRoleView(view)` | 角色浮窗视图切换（roles ↔ keys） |

### 6.2 修改

| 位置 | 改动 |
|---|---|
| `lbOpenRolePicker()`（约 L3863） | header 加 🎮 按钮；content 区按 `LB._roleView` 渲染；宽度按视图切换 |
| `LB_PREFS_KEYS`（约 L34614） | 追加 `'lb_keymap'` |
| `lbPrefsAfterApply()`（约 L34645） | 应用后调 `lbKeymapLoad()` + 若键位视图打开则 `lbKeymapRender()` |
| `<style>` 区块 | 新增 `.lb-km-*` 样式（表格行、键位格、冲突态、紫点、分组小标题） |

### 6.3 明确不动

- `LB_HF_KEY_GROUPS` / `LB_HF_KEYS` / `lbHfKeySrc`：只读复用
- 流程 key token 渲染逻辑（期 3 再谈）
- 后端 `dino_backend.py`：**零改动**

---

## 7. 分期与验收

### 期 1 · 骨架与只读展示

- [ ] `LB_KEYMAP_ACTIONS` 20 项 + `lbKeymapLoad/Effective/ViewHtml/Render`
- [ ] 角色浮窗 🎮 入口 + 视图切换 + 宽度自适应
- [ ] 三列只读表格（分组 / 键位图标 / 键名）
- [ ] 布局切换（Xbox/PS/Switch）只读生效

**验收**：点「角色」→ 🎮 → 看到 20 行动作，手柄+键盘图标全部加载成功（无 404）；切布局图标正确换肤；「返回」回到角色列表。

### 期 2 · 改键与存储

- [ ] `lbKeymapPick` 改键弹层（分列过滤可用键）
- [ ] 冲突检测 + 确认替换
- [ ] 单行紫点还原 / 恢复默认
- [ ] `LB_PREFS_KEYS` 接入 + 防抖保存 + 跨端拉取
- [ ] 未登录提示

**验收**：
1. 改「使用/互动」手柄键为 Y → 刷新页面仍是 Y，紫点仍在
2. 换另一浏览器/设备登录同账号 → 拉到同一份改动
3. 把「跳跃」键盘键改成与「使用/互动」相同的 E → 出现冲突提示，确认后对方变「未设置」
4. 恢复默认 → 全部回到默认、紫点消失、localStorage 与云端 `map` 为 `{}`

### 期 3（可选）· 流程卡联动

- [ ] key token 支持动作引用 `{"t":"key","v":"@interact"}`，渲染时查玩家键位
- [ ] AI 提示词 key token 清单追加可选写法

**验收**：流程卡里 `@interact` 渲染成玩家当前绑定的键；改键后卡片立即跟着变。

---

## 8. 风险与回滚

| 风险 | 应对 |
|---|---|
| 默认键位不准确（我按 ASA 常见默认填） | 默认值集中在 `LB_KEYMAP_ACTIONS` 一处，改表即可；界面提供「恢复默认」；实施时逐项核对 |
| 键位图标 404 | 渲染 `<img onerror>` 回退为键名文字（沿用 `lbImgRetry` 思路） |
| `user_prefs` 容量 | 单玩家 map 约 <2KB，远低于限制 |
| 与流程编辑器键位选择器耦合 | 两者互不影响：流程存原始键名，键位表只读默认+玩家 map |
| 破坏角色浮窗现有功能 | 视图切换用 `LB._roleView` 状态，默认 `'roles'` 行为与现在完全一致；回滚只需删 🎮 按钮与 keys 分支 |

**回滚方案**：`bak/dino-import.html.bak_<时间戳>` 覆盖 + 重新部署；数据侧删除 `lb_keymap` 键即可（其他数据不受影响）。

---

## 9. 待确认事项

1. **动作清单**：当前 20 项（通用 7 / 战斗 4 / 移动 4 / 界面 5），够用吗？要增删哪些？
2. **默认键位取值**：先用草案（标「待核对」）上，还是你先给一份准确表？
3. **布局切换的必要性**：你玩的是手柄（Xbox 布局）还是也在 PS/Switch 间切换？若只用一种，期 1 可省掉切布局、只做 Xbox 皮肤。
4. **期 3 是否要做**：流程卡里按玩家键位显示，需要改 AI 提示词与 token 渲染。

---

## 10. 附：默认键位草案（20 项）

| 组 | id | 动作 | 手柄（Xbox） | 键盘 |
|---|---|---|---|---|
| 通用 | `interact` | 使用 / 互动 | X | E |
| 通用 | `mount` | 骑乘 / 上下坐骑 | Y | E |
| 通用 | `harvest` | 采集 | RT | 鼠标左键 |
| 通用 | `transfer` | 转移 / 装入 | A | E |
| 通用 | `pickup` | 拾取 | X | E |
| 通用 | `drop` | 丢弃 | D-pad 下 | O |
| 通用 | `whistle` | 吹哨（跟随 / 停） | D-pad 左 | `;` |
| 战斗 | `attack` | 主攻击 | RT | 鼠标左键 |
| 战斗 | `aim` | 瞄准 / 副攻击 | LT | 鼠标右键 |
| 战斗 | `reload` | 装填 | X（长按） | R |
| 战斗 | `switchWeapon` | 切换武器 | RB | 1~0 / 滚轮 |
| 移动 | `jump` | 跳跃 | A | Space |
| 移动 | `crouch` | 蹲下 | R3 | C |
| 移动 | `sprint` | 冲刺 | LB | Left Shift |
| 移动 | `lookBack` | 回身 / 视角 | R3 长按 | 鼠标中键 |
| 界面 | `inventory` | 背包 | View | I |
| 界面 | `map` | 地图 | Menu | M |
| 界面 | `wheel` | 交互轮盘 | LB（长按） | 长按 E |
| 界面 | `chat` | 语音 / 聊天 | D-pad 右 | Enter |
| 界面 | `freeCam` | 自由视角 | 摇杆组合 | 未设置 |

> 表中「长按」「组合」类无法用单键图标表达，本期内一律记为**单键主键位**，长按/组合写在 `note` 字段（工具提示显示），不参与冲突检测。
