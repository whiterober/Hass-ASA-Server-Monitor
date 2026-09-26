# "复制自..." → "复制TAB" 重构方案

> 日期：2026-07-18 | 基准版本：v1418

---

## 现状分析

### 已有基础设施
- `_blockClipboard` — 板块级剪贴板（`duplicateBlock` / `pasteBlock`）
- `_descClipboard` — 行级剪贴板（`copyDesc` / `pasteDesc`）
- `addTab()`（L1875）— 创建空 TAB（含弹窗询问名称）
- `editorData.tabs[]` — 所有 TAB 数据（`.name`, `.content_blocks[]`）
- `editorSelectedTab` — 当前激活 TAB 索引

### 当前 "复制自..." 按钮
- 位置：L1566（`renderLeftExtras`）
- 调用：`copyBRFrom()`（L5318）
- 现状：**空壳** — 只弹窗选服务器，不实际复制数据

---

## 方案设计

### 新增全局变量
```javascript
var _tabClipboard = null; // {name, content_blocks[]} — 全局跨菜单持久化
```
> 深拷贝后独立于 `editorData`，切换菜单（服务器规则↔部落运维↔部落基地）不清空。

### 修改点

#### 1. 全局变量声明（~L1550，靠近 `_blockClipboard`）
```javascript
var _tabClipboard = null; // TAB级复制剪贴板
```

#### 2. 按钮 UI 改造（L1566）
**改前**：
```javascript
return '<button ... onclick="copyBRFrom()">复制自...</button>';
```
**改后**：
```javascript
return '<button ... onclick="copyTab()">📋 复制TAB</button>' +
  '<button ... onclick="pasteTab()" ' + (_tabClipboard?'':'style="display:none"') + '>📌 黏贴TAB</button>';
```

#### 3. 新增 `copyTab()` 函数（靠近 L1885，~addTab 附近）
```javascript
function copyTab() {
  var tab = editorData.tabs[editorSelectedTab];
  if (!tab) return;
  _tabClipboard = JSON.parse(JSON.stringify(tab));
  // 刷新黏贴按钮可见性
  document.querySelectorAll('.ic-tab-paste-btn').forEach(function(b){ b.style.display = ''; });
  WS.toast('已复制TAB: ' + (_tabClipboard.name || '(未命名)'), 'success');
}
```

#### 4. 新增 `pasteTab()` 函数
```javascript
function pasteTab() {
  if (!_tabClipboard) return;
  // 深拷贝插入当前活动的 editorData（无论哪个菜单）
  editorData.tabs.push(JSON.parse(JSON.stringify(_tabClipboard)));
  editorSelectedTab = editorData.tabs.length - 1;
  reRender();
  setTimeout(showPreview, 200);
}
```
> `editorData` 由当前菜单决定（服务器规则/部落运维/部落基地），TAB 结构 `{name, content_blocks[]}` 三菜单统一。

### 复用关系
| 函数 | 复用来源 | 改动 |
|------|---------|------|
| `copyTab()` | 仿 `duplicateBlock()`（L2924） | 复制整个 `editorData.tabs[sel]` 而非单块 |
| `pasteTab()` | 仿 `pasteBlock()`（L2931）+ `addTab()`后半 | 推送完整 TAB 对象并切标签 |
| `JSON.parse(JSON.stringify(...))` | 沿用现有深拷贝模式 | 无 |

### `copyBRFrom()` 处理
- 保留函数定义（兼容性），改为调用 `copyTab()`
```javascript
function copyBRFrom() { copyTab(); }
```

---

## 影响范围
- 仅新增 2 个函数 + 1 个变量 + 1 行 UI 改动
- 不修改任何现有 `content_blocks` 或 `descriptions` 逻辑
- 不影响保存/加载/预览流程
- `_tabClipboard` 独立于 `_blockClipboard` / `_descClipboard`
- **跨菜单兼容**：TAB 结构 `{name, content_blocks[]}` 三菜单统一，无需额外适配

---

## 验证清单
- [ ] 点击「📋 复制TAB」→ 弹出 Toast 提示
- [ ] 「📌 黏贴TAB」按钮出现
- [ ] 点击黏贴 → 新增 TAB 出现在列表末尾 → 自动切换到新 TAB
- [ ] 新 TAB 的 `content_blocks` 与源 TAB 完全一致（深拷贝）
- [ ] **跨菜单**：服务器规则复制 → 切换到部落运维 → 黏贴（反之亦然）
- [ ] **跨菜单**：部落基地复制 → 切换到服务器规则 → 黏贴
- [ ] 修改新 TAB 不影响源 TAB（验证深拷贝有效性）
- [ ] 预览正常
- [ ] 保存后数据持久化
