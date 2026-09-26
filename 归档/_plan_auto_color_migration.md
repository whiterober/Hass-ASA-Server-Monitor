# 自动反色按钮迁移至选图浮窗 — 执行计划

> 创建时间：2026-06-30 | 状态：⏳ 待执行

---

## 📐 现状

| 项目 | 现状 |
|------|------|
| **按钮位置** | info_card 块图标预览右侧，`toggleAutoColor(bi, btn)` |
| **数据字段** | `icon_auto_color` (bool)，隐藏 checkbox `mcICAutoColor{bi}` |
| **亮度字段** | `icon_native_luminance` (float, 0-1)，Canvas 采样计算 |
| **CSS 类** | `ic-auto-color` / `ic-auto-light` / `ic-auto-dark` |
| **反色逻辑** | 亮度>0.5 → `ic-auto-light`，≤0.5 → `ic-auto-dark` |
| **选图浮窗** | `openIconPicker_ic(bi)`，已有按钮：组合、刷新、清空 |

---

## 🔧 执行步骤（共 7 步）

### 第 1 步：数据模型升级

- 新增字段 `icon_auto_color_mode`，取值 `"off"` / `"normal"` / `"reverse"`
- 兼容旧数据：`icon_auto_color===true` → `"normal"`，`false` → `"off"`
- 保留 `icon_auto_color` 字段向后兼容，但读/写以 `_mode` 为准
- 默认值：`icon_auto_color_mode: 'off'`（新增在 default block 模板中）

### 第 2 步：移除卡片行内按钮

- 删除 info_card 渲染模板中自动反色按钮的 HTML 生成代码（`toggleAutoColor` 按钮+SVG）
- 隐藏 checkbox `mcICAutoColor{bi}` 保留作为兼容过渡
- 预览图不再通过 inline button 控制反色类

### 第 3 步：选图浮窗新增三态切换器

在浮窗 header 的「清空」按钮右侧增加三态按钮：

| 状态 | 按钮文字 | 颜色 |
|------|---------|------|
| 关闭 | 反色：关 | 灰色半透明 |
| 正反色 | 正反色 | 强调色高亮（`var(--accent)`） |
| 逆反色 | 逆反色 | 警示色高亮（`var(--warning, orange)`） |

- 点击循环：关闭 → 正反色 → 逆反色 → 关闭
- 3 个浮窗（`openIconPicker`、`openIconPicker_ic`、`openIconPicker_desc`）均添加

### 第 3.5 步：卡片行内图标预览加模式角标

预览图右上角叠加小三角色块作为模式标识：

| 模式 | 角标颜色 | CSS |
|------|---------|-----|
| 关闭 | 无角标 | — |
| 正反色 | 强调色 | `border-color: var(--accent) transparent transparent var(--accent)` |
| 逆反色 | 警示色 | `border-color: var(--warning, orange) transparent transparent var(--warning)` |

- 实现：CSS `::after` 伪元素，0×0 方块 + border trick 画三角
- 定位：`top:0; right:0`，尺寸 6×6px
- JS 动态切换 class：`ic-mode-normal` / `ic-mode-reverse`

### 第 3.6 步：逆反色预览对比背景色

逆反色下图片朝与主题相同方向变化，可能融入背景。加对比底色：

| 模式 | 预览图背景 |
|------|-----------|
| 关闭 / 正反色 | 透明（现状） |
| 逆反色 | `background: color-mix(in oklch, var(--primary-text-color) 15%, transparent)` |

- 暗主题 → 浅灰底，亮主题 → 深灰底，始终与图片形成反差
- 通过 `.ic-mode-reverse` class 控制

### 第 4 步：反色逻辑改造（`toggleIconColorMode` 函数）

新增 `toggleIconColorMode(bi)` 函数，三态循环：

- **正反色 `"normal"`**：沿用现有 `detectImageBrightness` → `applyAutoColorClass` 逻辑
  - 亮度>0.5 → `ic-auto-light`（浅底图，暗主题反白）
  - 亮度≤0.5 → `ic-auto-dark`（深底图，亮主题反黑）
- **逆反色 `"reverse"`**：反转判断
  - 亮度>0.5 → `ic-auto-dark`（反转：浅底图故意用暗类）
  - 亮度≤0.5 → `ic-auto-light`（反转：深底图故意用亮类）
- **关闭**：清除 filter 和 class

### 第 5 步：预览即时反馈

- 切换模式后立即对 `mcICIconPreview{bi}` 应用对应 CSS 类 + 角标
- `selectInfoCardIcon` 确认选图时保持当前模式生效
- 保存数据（`collectBlockData`）时写入 `icon_auto_color_mode` 字段
- 初始渲染时根据 `icon_auto_color_mode` 设置预览 class + 角标

---

## 📁 涉及文件

| 阶段 | 文件 |
|------|------|
| **编辑器（本次）** | `www/asa-admin.html` |
| **渲染端（后续）** | `build_lovelace.py`、`preview_server.py` |
| **部署** | `_upload_v173.py` → ASA 后台「💾 保存Tab」→ 重启 HA |

---

## ⚠️ 注意事项

- 双端同步：编辑器改完后需同步 `build_lovelace.py` / `preview_server.py` 的 CSS 生成逻辑
- 向后兼容：旧卡片 `icon_auto_color: true` 自动映射为 `icon_auto_color_mode: "normal"`
- 3 个浮窗均需添加三态按钮（`openIconPicker`、`openIconPicker_ic`、`openIconPicker_desc`）
