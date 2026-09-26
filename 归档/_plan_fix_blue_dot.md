# 蓝点不稳定修复 + 失败红色圆点 — 实施计划

> 版本：v6 | 创建：2026-07-01 | 更新：2026-07-01 | 状态：⏳ 等待确认

---

## 问题根因

| 问题 | 根因 |
|------|------|
| 蓝点不出现 | `detectImageBrightness` 异步回调未完成前用户已保存/切换 Tab |
| 蓝点消失 | `selectInfoCardIcon` / `selectDescImage` 替换 DOM 时清除 wrapper class |
| 亮度检测失败 | 网络超时/CORS/图片 404 → 回调永远不触发 → 计数器永不归零 |

---

## 方案概述（5 项改动）

### 1. 全局 pending 计数器

```js
let _pendingBrightnessChecks = 0;
let _failedBrightnessChecks = 0;  // 新增：失败计数
```

- `toggleIconColorMode(bi, btn)` / `toggleIconColorModeDesc(bi, di, btn)` 切换反色时 +1
- `detectImageBrightness(url, cb)` 回调中 -1（成功/失败都 -1）
- 失败时额外 `_failedBrightnessChecks++`

### 2. 亮度检测重试机制（新增）

```js
function detectImageBrightness(url, cb, retries = 2) {
  // 原有 fetch + canvas 逻辑
  // 失败时 if (retries > 0) → setTimeout 1s 后重试 detectImageBrightness(url, cb, retries - 1)
  // 全部重试耗尽 → 标记失败，圆点变红
}
```

- 默认重试 **2 次**（共 3 次尝试）
- 每次间隔 1s
- 3 次全失败 → callback 中标记 `failed=true`

### 3. 失败红色圆点（新增）

编辑器 CSS 新增：

```css
.ic-mode-failed::after {
  content: '';
  position: absolute;
  top: 2px; right: 2px;
  width: 4px; height: 4px;
  border-radius: 50%;
  background: #ef4444;  /* 红色 */
}
```

- 检测成功 → `ic-mode-normal`（蓝色圆点 `background: var(--accent-color)`）
- 检测失败 → `ic-mode-failed`（红色圆点）
- 检测中 → 无圆点（pending 状态）

### 4. 保存 TAB 按钮联动（二态：检测中 / 可保存）+ 共用提示区显示失败

保存按钮仅做检测中禁用，不干涉保存决策。失败原因通过共用 toast 提示区（与「已保存」「保存失败」同一位置）展示。

#### 保存按钮状态

| 状态 | 条件 | 按钮样式 | 按钮文案 |
|------|------|---------|---------|
| 🔵 检测中 | `_pendingBrightnessChecks > 0` | `disabled + opacity:0.5` | 保存Tab |
| 🟢 可保存 | `_pendingBrightnessChecks === 0` | 正常 | 保存Tab |

> 不区分失败/成功，有失败项不阻止保存、不改变按钮颜色。

#### 共用提示区显示失败原因

利用页面已有的 toast 提示区（与「已保存」「保存失败」共用同一 DOM 元素），保存成功后自动弹出：

```
✅ 已保存 — 2 项亮度检测失败
   🏝 孤岛 · 板块图标（超时）
   🌋 焦土 · 描述行 #3（CORS 错误）
```

#### 提示状态表

| 场景 | 提示类型 | 样式 | 内容 |
|------|---------|------|------|
| 全部成功 | 成功 | 绿色 `✅` | 「已保存」 |
| 部分失败 | 警告 | 黄色 `⚠️` | 「已保存 — N 项亮度检测失败」+ 失败列表 |
| 全部失败 | 警告 | 黄色 `⚠️` | 「已保存 — 全部 N 项亮度检测失败」+ 失败列表 |
| 检测未完成 | 错误 | 红色 `❌` | 「还有 N 项亮度检测未完成，请稍候再保存」 |

#### 数据结构

```js
let _pendingBrightnessChecks = 0;
let _failedItems = [];  // [{bi, di, url, reason, serverName}]
```

#### `_showSaveResult()` 在保存完成后调用

```js
function _showSaveResult() {
  var failed = _failedItems.length;
  var toast = document.getElementById('saveToast'); // 共用提示区元素

  if (_pendingBrightnessChecks > 0) {
    // 不应到达（保存按钮已禁用），防御性处理
    toast.className = 'toast toast-error';
    toast.innerHTML = '❌ 还有 ' + _pendingBrightnessChecks + ' 项亮度检测未完成，请稍候再保存';
  } else if (failed === 0) {
    toast.className = 'toast toast-success';
    toast.innerHTML = '✅ 已保存';
  } else {
    var lines = _failedItems.map(function(item) {
      return item.serverName + ' · ' + (item.di != null ? '描述行 #' + item.di : '板块图标') + '（' + item.reason + '）';
    });
    toast.className = 'toast toast-warning';
    toast.innerHTML = '⚠️ 已保存 — ' + failed + ' 项亮度检测失败<br>' + lines.join('<br>');
  }

  // 显示 toast（复用现有显示/隐藏逻辑）
  toast.style.display = 'block';
  clearTimeout(toast._timer);
  toast._timer = setTimeout(function() { toast.style.display = 'none'; }, 5000);

  // 重置失败计数（下次保存重新统计）
  _failedItems = [];
}
```

#### 调用时机

在 `saveMCBlocks` / `saveMixedEditor` 保存成功回调末尾调用 `_showSaveResult()`，替代原有简单的「已保存」提示。

### 5. select 函数保留 mode class

- `selectInfoCardIcon` / `selectDescImage` 不再清除 wrapper 上的 `ic-mode-*` class
- 仅替换 `<img>` 的 `src`，保留 wrapper 现有 class

### 6. 按钮文案

- 板块级：`反色：关` ↔ `反色：开`
- 描述行：同上

---

## 检测完成后需实时更新 class 的编辑区位置

> 亮度检测回调中更新**编辑器 DOM 中可见**的图标 class。色块态 desc 图片不在编辑器 DOM 中——它由渲染端在保存后生成。

### 编辑器实时更新（4 处 + 2 浮窗）

| # | 位置 | DOM 元素 | 更新方式 |
|---|------|----------|---------|
| 1 | **板块级图标预览**（info_card 编辑器行内） | `#block-{bi} .ic-wrapper` span | 回调中 `querySelector` 定位 + 替换 class |
| 2 | **描述行图片预览**（普通态/线性态 inline img） | `#block-{bi} .ic-desc-wrap[data-di="{di}"]` span | 回调中 `querySelector` 定位 + 替换 class |
| 3 | **板块图标选图浮窗**（openIconPicker_ic 内预览） | 浮窗 header 的图标预览区域 | 浮窗打开时从 editorData / DOM 同步 class |
| 4 | **描述行选图浮窗**（openIconPicker_desc 内预览） | 浮窗 header 的图标预览区域 | 同上 |
| — | **设备图标选图浮窗** | 同上 | 同上 |
| — | **组合图标缩略图** | `.combo-thumbs img` | 拼图结果，非原始图标，无需角标 |

### 渲染端处理（编辑器不实时更新）

| # | 位置 | 谁处理 | 何时 |
|---|------|--------|------|
| A | **色块态 desc 图片**（实页） | `build_lovelace.py` 的 `IC_CSS` + Jinja2 模板 | ASA 后台「💾 保存Tab」后重建 |
| B | **色块态 desc 图片**（预览区） | `preview_server.py` 的 `IC_CSS` | 同上 |

> 色块态 desc 的 `ic-mode-*` class 由渲染端根据 `editorData` 中的 `image_auto_color_mode` + `image_native_luminance` 字段生成，与编辑器 DOM 无关。`saveMCBlocks` 中已正确保存这两个字段（v896 修复），渲染端从 `server_rules.json` 读取后即可正确显示反色/红点。

### ⚠️ 编辑器 vs 渲染端显示逻辑差异（重点）

色块态 desc 在编辑器和渲染端使用**不同的反色逻辑**：

| 端 | 模式值 | CSS class | 视觉含义 |
|----|--------|-----------|---------|
| **编辑器预览**（asa-admin） | 用户选择的原始 mode（`normal`） | `ic-mode-normal` | **正反色**：按用户选择显示，所见即所得 |
| **渲染端**（build_lovelace / preview_server） | `saveMCBlocks` 翻转后的 mode（`normal`→`reverse`） | `ic-mode-reverse` | **逆反色**：色块态深色背景需反转显示 |

> 渲染端的翻转逻辑已在 v896 的 `saveMCBlocks` 中实现（`desc.server` 存在时 `normal`↔`reverse` 互换），**无需修改**。本次修复仅需确保编辑器中色块态 desc 的预览 wrapper 使用 `ic-mode-normal`（正反色），与用户操作一致。

### 更新函数 `_syncIconModeClass(bi, di, mode)`

```js
function _syncIconModeClass(bi, di, mode) {
  // mode: 'normal' | 'reverse' | 'failed' | 'off'
  // 仅更新编辑器 DOM 中可见的元素，不涉及色块态（渲染端处理）
  var cls = mode === 'off' ? '' : 'ic-mode-' + mode;

  // 1. 板块级 wrapper
  var icWrap = document.querySelector('#block-' + bi + ' .ic-wrapper');
  if (icWrap) { icWrap.className = 'ic-wrapper ' + cls; }

  // 2. 描述行 wrapper（普通态/线性态，编辑器 DOM 中存在）
  var descWrap = document.querySelector('#block-' + bi + ' .ic-desc-wrap[data-di="' + di + '"]');
  if (descWrap) { descWrap.className = 'ic-desc-wrap ' + cls; }

  // 3-4. 浮窗预览（如果浮窗当前打开且展示的是同一图标）
  _syncPopupPreviews(bi, di, mode);
}
```

### 回调中调用

`detectImageBrightness` 成功后 → `_syncIconModeClass(bi, di, 'normal')`
`detectImageBrightness` 失败后 → `_syncIconModeClass(bi, di, 'failed')`

---

## 修改文件

| 文件 | 改动 |
|------|------|
| `www/asa-admin.html` | JS + CSS（计数器、重试、红点、保存按钮、select、文案、编辑器 4 处实时更新） |
| `build_lovelace.py` | 渲染端：色块态 desc `ic-mode-*` class 生成（从 editorData 读 mode/lum）+ 实页 CSS 反色规则 |
| `preview_server.py` | 渲染端：同上（预览区） |

---

## 执行顺序

1. 备份 `asa-admin.html`
2. 修改 `asa-admin.html`（5 项）
3. 上传 `_upload_v173.py` → 浏览器验证
4. 修改 `build_lovelace.py` + `preview_server.py`
5. 部署 + ASA 后台保存 + 重建
6. 端到端验证：选图→切换反色→等检测→保存→切换 Tab 回来确认

---

## 状态机

```
关 ──[点击反色]──→ pending（无圆点）──[检测成功]──→ 正常（蓝点）
                   │
                   └──[检测失败+重试]──→ 重试1 ──→ 重试2 ──→ 失败（红点）
```

---

## 风险

- 低风险：仅修改 JS/CSS，不涉及数据结构变更
- 回滚：备份文件名 `asa-admin_backup_YYYYMMDD_HHMMSS.html`
