# 拖拽排序实现分析

## 现有实现：服务器规则 / 部落运维

### 全局变量
| 变量 | 类型 | 说明 |
|------|------|------|
| `dragSrcIndex` | number | 拖拽源的索引（初始 -1） |
| `dragInsertIdx` | number | 插入目标位置的索引（初始 -1） |
| `dragScrollTimer` | number | 自动滚动的定时器 ID |

### 模板（sub-section div）

```html
<div class="sub-section" 
     data-bi="'+bi+'"                    <!-- 块索引 → 读取为 dragSrcIndex -->
     style="border-left:4px solid ..."
     draggable="true"                    <!-- 可拖拽 -->
     ondragstart="dragMCBlock(event,'+bi+')"   <!-- 拖拽开始 -->
     ondragover="dragOverMCBlock(event)"       <!-- 拖拽经过 -->
     ondrop="dropMCBlock(event)">              <!-- 放手 -->
```

**关键点：整个 sub-section 是拖拽单元。`data-bi` 存储块在 `content_blocks` 数组中的索引。**

### 拖拽函数

#### 1. dragMCBlock(e, idx)
```
1. dragSrcIndex = idx（记录源索引）
2. e.dataTransfer.effectAllowed = 'move'
3. e.dataTransfer.setData('text/plain', idx)  ← 浏览器要求！没有这行 drop 不触发
4. setTimeout: 源 sub-section 变半透明（opacity: 0.4）
```

#### 2. dragOverMCBlock(e)
```
1. e.preventDefault()  ← 必须！否则 drop 事件不触发
2. e.dataTransfer.dropEffect = 'move'
3. 找到 e.currentTarget.closest('.sub-section') → 读 data-bi → idx
4. 清除其他 .drop-after
5. 当前 sub-section 加 .drop-after（预览线）
6. dragInsertIdx = idx + 1（插入到该块之后）
7. 自动滚动（仅当 mcBlocks 容器存在时）
```

#### 3. dropMCBlock(e)
```
1. e.preventDefault()
2. 清除所有 .drop-after 和 opacity
3. 验证：srcIndex < 0? insertIdx < 0? 相同? 相邻? → 任一成立则放弃
4. blocks = editorData.tabs[editorSelectedTab].content_blocks
5. blocks.splice(dragSrcIndex, 1) → 移除源
6. insertAt = (insertIdx > srcIdx ? insertIdx-1 : insertIdx)
7. blocks.splice(insertAt, 0, item) → 插入
8. dragSrcIndex = -1; dragInsertIdx = -1（重置）
9. renderTribeOps()  → 全量重渲染 DOM
10. 恢复滚动位置
```

### 数据流

```
用户拖拽
  → dragMCBlock: dragSrcIndex = 源的 data-bi
  → dragOverMCBlock: dragInsertIdx = 目标的 data-bi + 1
  → 放开
  → dropMCBlock: 
      blocks = editorData.tabs[...].content_blocks  ← 直接引用内存数据
      blocks.splice(源, 1)  ← 修改数据
      blocks.splice(目标, 0, 元素)  ← 修改数据
      renderTribeOps()  ← 重渲染（读 editorData 生成 DOM）
```

**数据修改是就地 splice，renderTribeOps() 是全局可用的重渲染函数。**

---

## 部落基地对比分析

### 结构差异

| | 服务器规则/部落运维 | 部落基地 |
|---|---|---|
| 拖拽单元 | sub-section（整块） | 无（未实现） |
| 数据源 | `editorData.tabs[...].content_blocks` | `baseData.servers[...].tabs[...].sections[...].content_blocks` |
| 重渲染函数 | `renderTribeOps()`（全局） | `enhanceStorageEditor()`（需验证） |
| data 属性 | `data-bi`（块索引） | `data-si`（section 索引） |
| 滚动容器 | `mcBlocks` | 无独立容器 |
| DOM 结构 | sub-section = 1 个块 | sub-section 含多个块（block-title-row + block-body 交错排列） |

### 部落基地 DOM 结构

```
sub-section[data-si="0"]
  DIV (header + toggle)
  DIV.br-sec-body
    DIV (inner sub-section, 无 data-si)
      block-title-row
    block-body
    DIV (inner sub-section, 无 data-si)
      block-title-row
    block-body
    ...
```

**每个块被嵌套的 inner sub-section 包裹，block-title-row 和 block-body 是 inner sub-section 的直接子元素，但不是同一容器的兄弟。**

### 部落基地实现难点

1. **无独立块容器**：block-title-row 和 block-body 找不到共同父容器
2. **嵌套 sub-section**：`row.closest('.sub-section')` 可能找到 inner（无 data-si）
3. **数据路径深**：`baseData.servers[server].tabs[tab].sections[section].content_blocks`
4. **无全局重渲染函数**：需要找到或创建对应的渲染函数
5. **多 section**：需要 `data-si` + `data-bi` 两级索引定位

### 正确实现方案

1. **给每个 inner sub-section 加 `data-bi` 和拖拽属性**
   - `innerSub.setAttribute('draggable', 'true')`
   - `innerSub.setAttribute('data-bi', bi)`
   - `innerSub.setAttribute('data-si', si)`
   - 设置 `ondragstart`, `ondragover`, `ondrop`

2. **修改 dropMCBlock 支持 baseData**
   - 检测 `typeof baseData !== 'undefined'`
   - 路径：`baseData.servers[brSelectedServer].tabs[brSelectedTab].sections[si].content_blocks`
   - 调用正确的重渲染函数

3. **重渲染函数**
   - 部落运维：`renderTribeOps()`
   - 部落基地：需要找到或创建对应的渲染函数（当前 v162 中不存在全局可用的 base 重渲染函数）

4. **注意浏览器 HTML Drag API 要求**
   - `dragstart` 必须调用 `e.dataTransfer.setData()`（否则 drop 不触发）
   - `dragover` 必须调用 `e.preventDefault()`（否则 drop 不触发）
   - `dragenter`/`dragover` 才能设置 `dropEffect`

---

## 通用化改造计划（基于 SortableJS）

### 目标

引入 SortableJS 替代 HTML5 Drag API，统一所有子页面拖拽逻辑，同时自然修复首位 BUG + 获得移动端触摸支持。

### 引入方式

CDN（放在 `<style>` 和 `<script>` 之间）：

```html
<script src="https://cdn.jsdelivr.net/npm/sortablejs@1.15.6/Sortable.min.js"></script>
```

备选：将 `Sortable.min.js` 下载后放到 `/config/www/asa-data/Sortable.min.js`，本地引用。

### SortableJS 能力一览

| 能力 | HTML5 DnD（旧） | SortableJS（新） |
|------|----------------|-------------------|
| 桌面鼠标拖拽 | ✅ | ✅ |
| 移动端触摸 | ❌ | ✅ |
| 自动滚动 | 需手写 (~30行) | ✅ 内置 `scroll` 选项 |
| 首位可达 | ❌ (insertIdx = idx+1) | ✅ `evt.newIndex` 自然可为 0 |
| 幽灵/占位元素 | 需手写 CSS + JS | ✅ 内置 `ghostClass` / `dragClass` |
| 跨容器拖拽 | 极复杂 | ✅ `group` 选项 |
| 包体积 | 0 | ~10KB gzip / ~30KB raw |
| 外部依赖 | 无 | 1 个 `<script>` 标签 |

### 新架构

#### 核心函数：`dragRegister(opts)`

```javascript
// 创建 Sortable 实例，封装数据操作
function dragRegister(opts) {
  // opts.container    — HTMLElement, 拖拽容器（子元素的直接父节点）
  // opts.itemSelector — string, 可拖拽的选择器 (e.g. '.sub-section')
  // opts.getList      — function(): Array, 返回数据列表引用
  // opts.onReorder    — function(): void, splice 后的重渲染回调
  // opts.group        — string (可选), 跨容器拖拽分组名
  // opts.onStart      — function(evt) (可选)
  // 
  // 返回值: Sortable 实例 (可 destroy / 重新创建)

  var sortable = new Sortable(opts.container, {
    draggable: opts.itemSelector,
    group: opts.group || null,
    ghostClass: 'drag-ghost',
    chosenClass: 'drag-chosen',
    dragClass: 'drag-dragging',
    scroll: true,
    scrollSensitivity: 60,
    scrollSpeed: 8,

    // 拖动开始：清除上次可能残留的 glow
    onStart: function(evt) {
      document.querySelectorAll('.drag-target-glow').forEach(function(s) {
        s.classList.remove('drag-target-glow');
      });
    },

    // 拖动中经过元素：给当前目标加外发光，移除旧目标的
    onMove: function(evt) {
      var related = evt.related;  // 当前光标下的目标元素
      // 清除所有旧 glow
      document.querySelectorAll('.drag-target-glow').forEach(function(s) {
        if (s !== related) s.classList.remove('drag-target-glow');
      });
      // 给新目标加 glow
      if (related && !related.classList.contains('drag-target-glow')) {
        related.classList.add('drag-target-glow');
      }
    },

    // 松手：清除 glow，执行数据操作
    onEnd: function(evt) {
      document.querySelectorAll('.drag-target-glow').forEach(function(s) {
        s.classList.remove('drag-target-glow');
      });
      if (evt.oldIndex === evt.newIndex) return;
      var list = opts.getList();
      if (!list) return;
      var item = list.splice(evt.oldIndex, 1)[0];
      list.splice(evt.newIndex, 0, item);
      if (opts.onReorder) opts.onReorder();
    }
  });

  return sortable;
}
```

**关键改动**：
- `onStart`：拖拽开始时清除任何残留 glow
- `onMove`：拖动中，给光标下的目标元素加 `.drag-target-glow`（外发光 + outline），同时清除其他元素的 glow
- `onEnd`：松手后清除所有 glow，然后执行 splice 排序

#### CSS（新增）

```css
.drag-ghost { opacity: 0.4 !important; }
.drag-chosen { opacity: 0.6; }

/* 放置目标外发光 — 拖动中松手前的高亮指示 */
.drag-target-glow {
  outline: 2px solid var(--accent);
  outline-offset: 2px;
  box-shadow: 0 0 12px 3px var(--accent);
  z-index: 1;
  position: relative;
}
```

SortableJS 自动创建 ghost 元素（跟随鼠标的克隆体）并给原始元素加 `drag-chosen`。`.drag-target-glow` 在 `onMove` 回调中手动追加/清除，标记当前光标下的目标元素。

#### 各子页面注册方式

**服务器规则 / 部落运维：**

```javascript
dragRegister({
  container: document.getElementById('mcBlocks'),
  itemSelector: '.sub-section',
  getList: function(){ return editorData.tabs[editorSelectedTab].content_blocks; },
  onReorder: function(){ renderTribeOps(); }
});
```

**部落基地 — Section 级（阶段 2）：**

```javascript
dragRegister({
  container: sectionContainerEl,
  itemSelector: '.sub-section[data-si]',
  getList: function(){ return (baseData.servers[brSelectedServer].tabs||[])[brSelectedTab].sections; },
  onReorder: function(){ /* 重渲染 → 重建 Sortable */ }
});
```

**部落基地 — Block 级（阶段 3），每个 section 独立实例：**

```javascript
document.querySelectorAll('.br-sec-body').forEach(function(body, sectionIndex){
  dragRegister({
    container: body,
    itemSelector: '.sub-section:not([data-si])',  // inner sub-section
    getList: function(){
      return (baseData.servers[brSelectedServer].tabs||[])[brSelectedTab].sections[sectionIndex].content_blocks;
    },
    onReorder: function(){ /* 重渲染 + 重建所有 Sortable */ }
  });
});
```

#### HTML 模板改动

**不再需要**：`draggable="true"`、`ondragstart`、`ondragover`、`ondrop`、`data-bi`（拖拽用）。

只需保证子元素是容器的直接子节点。SortableJS 通过 `itemSelector` 自动识别它们。

#### 模板示例（renderTribeOps 中的 sub-section）

```html
<!-- 旧（硬编码拖拽属性，一坨） -->
<div class="sub-section" data-bi="'+bi+'" draggable="true"
     ondragstart="dragMCBlock(event,'+bi+')"
     ondragover="dragOverMCBlock(event)"
     ondrop="dropMCBlock(event)" style="...">

<!-- 新（只有数据和样式） -->
<div class="sub-section" style="...">
```

### 首位 BUG — 自动修复

SortableJS 的 `evt.newIndex` 直接表示目标在列表中的位置索引，天然可为 0（首位）。不再需要半区判断、"插入到之前"语义转换、容器级 dragover 等手段。

### 不变的部分

- 数据修改逻辑不变（splice + 重渲染 — 现在封装在 `onEnd` 回调中）
- 重渲染后需**重新创建 Sortable 实例**（DOM 重建后旧实例失效）
- 视图切换时需重新创建 Sortable

### 删除清单

| 删除项 | 原因 |
|--------|------|
| 函数 `dragMCBlock` | SortableJS 替代 |
| 函数 `dragOverMCBlock` | SortableJS 替代 |
| 函数 `dropMCBlock` | SortableJS 替代 |
| 全局变量 `dragSrcIndex`, `dragInsertIdx`, `dragScrollTimer` | SortableJS 内部管理 |
| CSS `.sub-section.drop-after` | 改用 `.drag-ghost` |
| HTML 属性 `draggable`, `ondragstart`, `ondragover`, `ondrop` | SortableJS 自动处理 |

---

## 实施步骤

### 阶段 0：引入 SortableJS

1. 在 `<style>` 和 `<script>` 之间添加 SortableJS CDN `<script>` 标签
2. 添加 CSS `.drag-ghost` / `.drag-chosen`
3. 验证：`typeof Sortable !== 'undefined'`，0 错误

---

### 阶段 1：替换现有拖拽方法（服务器规则/部落运维）

**目标**：用 SortableJS 替换服务器规则和部落运维的硬编码拖拽。

**步骤**：
1. 新增 `dragRegister()` 函数
2. 在 `renderTribeOps()` 结尾调用 `dragRegister(...)`（传入 `mcBlocks` 容器）
3. 从 HTML 模板中移除 `draggable`、`ondragstart`、`ondragover`、`ondrop` 属性
4. 删除旧函数 `dragMCBlock` / `dragOverMCBlock` / `dropMCBlock`
5. 删除旧全局变量 `dragSrcIndex` / `dragInsertIdx` / `dragScrollTimer`
6. 删除旧 CSS `.sub-section.drop-after`
7. 验证：
   - 服务器规则拖拽正常，可拖到任意位置（含首位和末尾）
   - 部落运维拖拽正常
   - 0 JS 错误

---

### 阶段 2：部署到部落基地 — Section 级（模块级）

**目标**：部落基地的大模块（outer sub-section）可拖拽排序。

**步骤**：
1. 确定 section 容器元素（tab 内容区的外层 div）
2. `dragRegister({ container: ..., itemSelector: '.sub-section[data-si]', getList: ..., onReorder: ... })`
3. 验证：sub-section 间可拖拽排序，保存后顺序正确

---

### 阶段 3：部署到部落基地 — Block 级（板块级）

**目标**：同一 section 内的板块（inner sub-section）可拖拽排序。

**步骤**：
1. 遍历所有 `.br-sec-body`，为每个创建独立 Sortable 实例
2. `itemSelector: '.sub-section:not([data-si])'`（仅匹配 inner sub-section）
3. 每个实例的 `getList` 闭包捕获对应的 `sectionIndex`
4. `onReorder` 重渲染 + 重建所有 Sortable
5. 验证：同一 section 内板块可排序，跨 section 不混乱

---

### 阶段 4：部署到部落基地 — 存储行级

**目标**：使用 `dragRegister` 统一封装，存储行（`.sr-row`）可拖拽排序。自动继承 glow + cursor + handle + click 抑制。

**DOM**：`.sr-row` 是 `#brStorageRows*` 的直接子元素。

**实施**：
1. 每行 `.sr-row-header` 注入 `⋮⋮` 把手（复用 `.drag-handle` 类）
2. 每个 `#brStorageRows*` 容器调用 `dragRegister({ container, itemSelector: '.sr-row', handle: '.drag-handle', getList, onReorder })`
3. 数据路径：待确认（纯 DOM 排序或 row 数据列表）
4. 懒加载：跟随阶段 3，`toggleBRSection` → `_initBlockSortable` 内部一并初始化
5. CSS 全部复用已有

---

### 交互规范：服务器规则 / 部落运维板块

适用于「服务器规则」和「部落运维」两个标签页中 `mcBlocks` 容器内的 `.sub-section` 板块元素。

#### 规则

| # | 动作 | 行为 | 视觉反馈 |
|---|------|------|---------|
| 1 | **拖动板块本身** | 拖拽排序（SortableJS 管理） | 幽灵元素跟随鼠标 + **目标元素外发光** |
| 2 | **点击板块本身** | 展开/折叠板块（不触发拖拽） | 无额外反馈 |
| 3 | **光标样式** | 静止时 `grab`（手型张开），拖动时 `grabbing`（手型握紧） | 鼠标指针变化 |

#### 外发光特效

拖拽过程中（未松手），光标所在的**目标放置元素**显示醒目的外发光：

```css
.drag-target-glow {
  outline: 2px solid var(--accent);
  outline-offset: 2px;
  box-shadow: 0 0 12px 3px var(--accent);
  z-index: 1;
  position: relative;
}
```

- **触发时机**：`onMove` 回调（拖动中每经过一个元素触发一次）
- **清除时机**：`onStart`（新拖拽开始）+ `onEnd`（松手）
- **实现方式**：`evt.related` 指向当前光标下的目标元素，给该元素加 `.drag-target-glow`，同时移除其他元素的 glow

#### 实现要点

**拖拽 vs 点击的区分**：SortableJS 原生支持。在 `onEnd` 中 `evt.oldIndex === evt.newIndex` 时跳过（未移动 = 点击），不会阻止 click 事件冒泡。板块的展开/折叠 click handler 照常工作。

**CSS 光标**：

```css
/* 普通状态 — 张开的手 */
.sub-section { cursor: grab; }

/* 拖动中 — 握紧的手（SortableJS 自动添加 dragClass） */
.drag-dragging { cursor: grabbing !important; }
```

**dragRegister 配置补充**：

| 配置项 | 用途 |
|--------|------|
| `dragClass: 'drag-dragging'` | 拖拽中给被拖元素加 class，触发 cursor: grabbing |
| `onStart` | 清除上次可能残留的 `.drag-target-glow` |
| `onMove(evt)` | 给 `evt.related`（当前光标下元素）加 `.drag-target-glow`，清除旧目标的 glow |
| `onEnd` | 清除所有 glow，执行 splice 排序 |

**延迟选项（可选）**：如需防止误触（轻触即触发拖拽），可在 `dragRegister` 的 Sortable 选项中增加 `delay: 100`（100ms 按住后才开始拖拽）。默认不加，保持即时响应。

---

### 阶段 5：部署到部落基地 — 分类级（存储行内分类条目）

**目标**：使用 `dragRegister` 统一封装。存储行内部的分类条目可拖拽排序。

**DOM 结构**：
```
.sr-row
  .sr-row-header          ← 行标题（⋮⋮ 把手）
  .sr-row-body
    分类条目 0             ← 拖拽单元
    分类条目 1
    ...
```

**统一方案**：`dragRegister` 自动继承 glow / cursor / handle / click 抑制。

**实施**：
1. 待确认：分类条目的 CSS 选择器和直接父容器、数据路径（`row.categories[]`）
2. 每个条目注入把手（独立类名 `.drag-handle-cat`，样式复用 `.drag-handle`）
3. `dragRegister({ container, itemSelector, handle: '.drag-handle-cat', getList, onReorder })`
4. `onReorder` 中 splice 数据 + 重渲染
5. 懒加载：行展开（`toggleSRBody`）时创建 Sortable

**CSS**：新增 `.drag-handle-cat { /* 复用 .drag-handle 全部属性 */ }`；glow / ghost / chosen 复用已有。

---

### 阶段 6：部署到部落基地 — 物品级（分类内物品条目）

**目标**：使用 `dragRegister` 统一封装。每个分类条目内部的物品可拖拽排序。物品为**流式布局**。

**DOM 结构**：
```
分类条目
  .sr-cat-header           ← 分类标题
  .sr-items                 ← 物品容器（流式/网格布局）
    物品 0                  ← 拖拽单元
    物品 1
    ...
```

**统一方案**：`dragRegister` 自动继承 glow / cursor / handle / click 抑制。

**流式布局说明**：SortableJS 根据 `getBoundingClientRect` 坐标排序，流式/网格布局下自动检测方向，`swapThreshold` 默认即可，无需额外配置。

**实施**：
1. 待确认：物品条目的 CSS 选择器和直接父容器、数据路径（`category.items[]`）
2. 每个物品注入把手（独立类名 `.drag-handle-item`，样式复用 `.drag-handle`）
3. `dragRegister({ container, itemSelector, handle: '.drag-handle-item', getList, onReorder })`
4. `onReorder` 中 splice 数据 + 重渲染
5. 懒加载：分类展开时创建 Sortable

**CSS**：新增 `.drag-handle-item { /* 复用 .drag-handle 全部属性 */ }`；glow / ghost / chosen 复用已有。

---

### 验证检查清单

- [ ] 阶段 0：`Sortable` 全局可用，0 JS 错误
- [ ] 阶段 1：服务器规则拖拽正常（桌面上任意位置包括首位）
- [ ] 阶段 1：部落运维拖拽正常
- [ ] 阶段 1：板块 cursor 为 `grab`，拖动时为 `grabbing`
- [ ] 阶段 1：点击板块 = 展开/折叠，拖动板块 = 排序，不冲突
- [ ] 阶段 2：部落基地 sub-section 拖拽排序
- [ ] 阶段 3：部落基地板块拖拽排序（同一 section 内）
- [ ] 阶段 3：不同 section 的板块不会混淆
- [ ] 阶段 3：拖拽后数据保存正确
- [ ] 阶段 4：存储行拖拽排序
- [ ] 阶段 5：分类条目拖拽排序（同一行内）
- [ ] 阶段 6：物品条目拖拽排序（同一分类内）
- [ ] 移动端：iOS Safari / Android Chrome 触摸拖拽可用
- [ ] 全程 0 JS 错误
- [ ] 不影响现有的 Pill/颜色浮窗/B加粗等功能
