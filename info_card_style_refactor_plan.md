# 卡片配置项样式重构计划

> 目标：将 `info_card`（卡片）编辑器的所有配置项，迁移为部落基地编辑器已有的控件样式和结构。

---

## 📊 现状对比

### info_card 现状（要淘汰的）

| 控件 | 当前样式 | 问题 |
|------|---------|------|
| 标题输入 | `<input>` + `form-group` 包装 | 无统一视觉规范 |
| MDI 图标 | `<input>` + `form-group` 包装 | 同上 |
| 图标 URL | `<input>` + `form-group` 包装 | 同上 |
| 高亮地图 | `<select>` + `form-group` 包装 | 同上 |
| 描述列表 | `sub-section` 卡片 + 内联 `style=` | 样式零散不统一 |
| 图标跟随主题 | `<input type="checkbox">` + `label` | 同上 |

关键特征：大量使用 `form-group` / `row` 类 + 内联 `style=`，无 DaisyUI 组件，无统一输入框样式。

### 部落基地现状（要参照的）

| 控件 | 样式 | 特征 |
|------|------|------|
| 设备图标 | 22x22 img + 虚线边框占位 + onclick 图标选择器 | 可点击交互 |
| 容量输入 | 30px 宽 input + `/` 分隔 + `font-size:0.75em` | 紧凑内联 |
| 分类标签 | `font-size:0.75em;max-width:200px` input | 统一字号 |
| 复选框 | `<label><input type="checkbox"> 文字</label>` | 内联 label |
| 卡片容器 | `sr-row` / `sr-cat-card` + `border:1px solid var(--border)` | 统一边框 |
| 折叠 | `sr-toggle` (20x20 圆角方块 + `+`/`−` 文字) | 可折叠行 |
| 删除按钮 | `btn-small btn-danger` + `position:absolute`（分类级） | 统一样式 |

关键特征：紧凑压缩布局，用内联 `style=` 控制微调，有成熟的 `sr-*` 类系统。

---

## 🎯 重构目标

1. **所有 info_card 输入框**统一为部落基地风格：`padding:4px 8px;font-size:0.85em;border-radius:4px` + DaisyUI `input` 基础样式
2. **图标选择**用部落基地已有的图标选择器（`openIconPicker` 模式）
3. **描述列表**改为 `sr-row` / `sr-cat-card` 结构的折叠卡片
4. **高亮地图**改为紧凑 `<select>`
5. **移除冗余包装**：去掉 `form-group` / `row` 类，改用 flex 布局
6. **复选框**统一为 `label` 内联模式

---

## 📋 逐项改动清单

### 1. 首行：[MDI][选图片][标题] 并排紧凑行

> **顺序**: MDI 正方形输入框 → 图标选择器 → 标题输入框
> **MDI 宽高** = 标题输入框的高度（同 padding/font-size，约 30px 见方）
> **图标选择器** = 与存储行选图标完全一致的样式：22×22 img/span+虚线占位 + onclick openIconPicker

```
改前：
<div class="row">
  <div class="form-group"><input id="mcICTitle"></div>
  <div class="form-group"><input id="mcICMdi"></div>
</div>
<div class="row">
  <div class="form-group"><input id="mcICIcon"></div>
</div>

改后：
<div style="display:flex;gap:8px;align-items:center;margin-bottom:6px">
  <input id="mcICMdi" placeholder="mdi"
         style="width:32px;height:32px;padding:2px;font-size:0.75em;border-radius:4px;text-align:center;flex-shrink:0">
  <!-- 图标选择器（完全参照存储行 22x22 样式） -->
  <!-- 有图标时 -->
  <img id="mcICIconPreview" src=""
       style="width:22px;height:22px;object-fit:contain;cursor:pointer;flex-shrink:0"
       onclick="event.stopPropagation();openIconPicker_ic(bi)" title="点击换图标"
       onerror="this.hidden=true">
  <!-- 无图标时 -->
  <span id="mcICIconPlaceholder"
        style="width:22px;height:22px;display:flex;align-items:center;justify-content:center;cursor:pointer;flex-shrink:0;font-size:0.65em;opacity:0.4;border:1px dashed var(--border);border-radius:3px"
        onclick="event.stopPropagation();openIconPicker_ic(bi)" title="选择图标">+</span>
  <input type="hidden" id="mcICIcon">
  <input id="mcICTitle" placeholder="标题"
         style="flex:1;padding:4px 8px;font-size:0.85em;border-radius:4px">
</div>
```

### 2. 高亮地图 → 紧凑 select

```
改前：
<div class="form-group">
  <select id="mcICHL">...</select>
</div>

改后：
<div style="display:flex;align-items:center;gap:6px">
  <label style="font-size:0.8em;white-space:nowrap">高亮地图</label>
  <select id="mcICHL" style="padding:4px 8px;font-size:0.85em;border-radius:4px">...</select>
</div>
```

### 3. 描述列表 → sr-card 折叠结构

```
改前：
<div class="sub-section" style="margin-bottom:4px;padding:8px">
  <input id="mcICDescText" placeholder="描述文字">
  <label><input type="checkbox" id="mcICDescBold"> 加粗</label>
  <label><input type="checkbox" id="mcICDescCollapsed"> 折叠</label>
  <label>透明 <input type="number" style="width:50px"></label>
  <button class="btn-small btn-danger">✕</button>
</div>

改后：
<div class="sr-cat-card" style="border:1px solid var(--border);border-radius:3px;padding:4px 6px;margin-bottom:3px">
  <div style="display:flex;align-items:center;gap:6px;flex-wrap:wrap">
    <input id="mcICDescText" placeholder="描述文字"
           style="flex:1;min-width:120px;padding:4px 8px;font-size:0.85em;border-radius:4px">
    <label style="display:flex;align-items:center;gap:2px;font-size:0.75em;margin:0">
      <input type="checkbox" id="mcICDescBold"> B
    </label>
    <label style="display:flex;align-items:center;gap:2px;font-size:0.75em;margin:0">
      <input type="checkbox" id="mcICDescCollapsed"> 折叠
    </label>
    <input type="number" id="mcICDescOpacity"
           min="0.1" max="1" step="0.1"
           style="width:42px;padding:2px 6px;font-size:0.75em;border-radius:4px"
           placeholder="1.0">
    <button class="btn-small btn-danger"
            style="padding:2px 6px;font-size:0.6em">✕</button>
  </div>
</div>
```

### 4. 图标跟随主题 → 内联 label

```
改前：
<label><input type="checkbox" id="mcICAutoColor"> 图标跟随主题</label>

改后（不变，已经与部落基地一致）：
<label style="display:flex;align-items:center;gap:4px;font-size:0.8em">
  <input type="checkbox" id="mcICAutoColor"> 图标跟随主题
</label>
```

### 5. 添加描述按钮 → btn-small

```
改前：
<button class="btn-small btn-primary" onclick="addICDesc(bi)">+ 添加描述</button>

改后：
<button class="btn-small btn-primary" style="font-size:0.75em;padding:4px 10px"
        onclick="addICDesc(bi)">+ 添加描述</button>
```

---

## 🔧 实施步骤

| 步骤 | 内容 | 影响范围 |
|------|------|---------|
| 1 | 定位 `renderMixedContent` 中 `info_card` 渲染代码 | ~99031-101580 行 |
| 2 | 替换首行为 [MDI][图标选择器][标题] | 合并原标题/MDI/图标URL三行 |
| 3 | 替换高亮地图为紧凑 select | 加 label 前缀 |
| 4 | 重构描述列表为 sr-cat-card 结构 | 改 sub-section 容器 |
| 5 | 统一所有 input 内联样式 | `padding:4px 8px;font-size:0.85em;border-radius:4px` |
| 6 | 部署验证 | 上传+重建预览 |

---

## ⚠️ 风险点

- **图标选择器**：参考存储行已有的 `openIconPicker` 模式（22×22 img/span+），为 info_card 新建 `openIconPicker_ic(bi)` 适配函数
- **描述 JSON 结构不变**：只改 HTML 渲染，不动数据模型
- **保存/回读逻辑不变**：`saveMixedEditor()` 和 `renderMixedContent` 的保存/读取逻辑无需修改

---

> 最后更新：2026-06-22
> 状态：已确认，待实施

---

## ✅ 分步实施清单

### 阶段一：基线准备

- [x] 0.1 确认基线文件 `asa-admin-v544-baseline.html` 可用
- [x] 0.2 复制基线到工作文件 `asa-admin.html`

### 阶段二：首行重构 [MDI][选图片][标题]

- [x] 1.1 定位 `info_card` 渲染块（`else if (bt === 'info_card')`）
- [x] 1.2 合并原标题/MDI/图标URL 三行为一行 flex 布局
- [x] 1.3 MDI 输入框：32×32 正方形 + `text-align:center`
- [x] 1.4 图标选择器：参照存储行 22×22 img/span+ 虚线占位
- [x] 1.5 标题输入框：`flex:1` + 统一内联样式

### 阶段三：高亮地图

- [x] 2.1 去掉 `form-group` 包装，改为 flex + label 前缀
- [x] 2.2 select 统一内联样式

### 阶段四：描述列表

- [x] 3.1 描述卡片从 `sub-section` 改为 `sr-cat-card`
- [x] 3.2 描述控件改为 flex-wrap 内联布局
- [x] 3.3 "加粗" 标签缩为 "B"
- [x] 3.4 透明度 input 统一 `width:42px`
- [x] 3.5 删除按钮 ✕→X + 统一 `padding:2px 6px;font-size:0.6em`

### 阶段五：关联函数适配

- [x] 4.1 更新 `addICDesc()` 动态模板（同步 sr-cat-card 样式）
- [x] 4.2 新建 `openIconPicker_ic(bi)` 图标选择器适配函数
- [x] 4.3 更新 `saveMixedEditor()` 中图标 URL 读取逻辑（无需改动）

### 阶段六：统一内联样式收尾

- [x] 5.1 所有 input 统一：`padding:4px 8px;font-size:0.85em;border-radius:4px`
- [x] 5.2 所有 select 统一：同上
- [x] 5.3 所有 checkbox label 统一：内联 flex + `font-size:0.8em`

### 阶段七：部署验证

- [x] 6.1 脚本校验：`<script>` 2 开 4 闭平衡
- [x] 6.2 代码泄露检查：无可见 `WS.onConnect` / `WS.init` 字符
- [x] 6.3 部署到服务器（paramiko SFTP）
- [x] 6.4 浏览器打开验证页面渲染
- [ ] 6.5 测试：打开 info_card 编辑器，确认首行布局、图标选择器、描述卡片交互正常
