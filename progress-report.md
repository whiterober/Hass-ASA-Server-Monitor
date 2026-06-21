# ASA Admin 进度报告

> 最后更新：2026-06-21 凌晨
> 当前版本：**v364**
> 文件：`www/asa-admin.html`（~484KB 单文件应用）

---

## 一、项目概览

ASA Admin 是一个 ASA（方舟生存进化）服务器后台管理单页应用，通过 Home Assistant 的 Lovelace 仪表板提供服务。版本通过 `_upload_v173.py` 上传到 `/config/www/asa-data/asa-admin-v{N}.html`，服务器保留最近 10 个版本。

### 核心文件

| 文件 | 说明 |
|------|------|
| `www/asa-admin.html` | 主应用（~484KB，单文件 HTML+CSS+JS） |
| `_upload_v173.py` | SFTP 上传脚本（自动版本号递增 + 旧版清理） |
| `CLAUDE.md` | 项目智能体配置与规则 |

### 部署地址

```
https://hass.whiterober.com/local/asa-data/asa-admin-v{N}.html
```

---

## 二、版本基线记录

| 版本 | 日期 | 里程碑 |
|------|------|--------|
| v162 | — | 早期基线 |
| v179 | — | — |
| v207 | — | — |
| v213 | — | 用户评为"完美版本"，6级拖拽全部正常工作 |
| v215 | — | — |
| v218 | — | — |
| v232 | — | — |
| v239 | — | — |
| v241 | — | — |
| v250 | — | — |
| v254 | — | — |
| v257 | — | — |
| v276 | — | — |
| v287 | — | — |
| v288 | — | — |
| v301 | — | 图标选择器修复后版本 |
| v343 | — | 从 v341 文件崩溃恢复后的稳定基线 |
| v343b | — | 补充：移动端 server-tabs 隐藏滚动条 + 部落基地删除 TAB 按钮 |
| v353 | — | 保存/删除按钮整合到保存行之前稳定版 |
| v362 | 2026-06-20 | Linter 自动修正 mobile-tab-btn CSS（去掉圆角、字色改强调色） |
| **v363** | 2026-06-20 | ❌ 回退版本：overflow:hidden 导致保存按钮行消失 |
| **v364** | 2026-06-21 | ⚠️ 当前版本：修复 v363 回归 + shell 去重 + 位置调整（但有新问题） |

---

## 三、已完成功能

### 3.1 拖拽系统（SortableJS）

- ✅ **6 级拖拽**：Section → Block → Row → Category → Item（全部实现）
- ✅ **拖拽手柄**：把手图标（⋮⋮）在各层级垂直居中
- ✅ **光标规则**：手柄区 `grab`/`grabbing`，内容区 `pointer`，分类行整行不再误触发
- ✅ **外发光特效**：拖动时预览放置位置有醒目描边（placeholder 样式）
- ✅ **展开状态保持**：`_restoreExpandState()` 在 `renderBaseRef()` 后恢复 section/row/block 展开
- ✅ **Sortable 懒初始化**：仅在 section 展开时创建 Sortable 实例（避免 display:none 容器上的失效实例）
- ✅ **物品级**：不显示把手，直接拖动物品图标触发拖动
- ✅ **Block 级拖动根因**：SortableJS `draggable` 只匹配容器的直接子元素，需用 `.sub-section` 的父级作为容器

### 3.2 部落基地编辑器（Base Reference）

- ✅ 完整 CRUD：Section → Block → Row → Category → Item 五级数据模型
- ✅ 拖拽排序全部实现
- ✅ `renderBaseRef()` 数据驱动渲染模式
- ✅ 展开/折叠状态在拖拽和增删后保持

### 3.3 计数徽章

- ✅ Section/Block/Row 三级徽章从旧 label 迁移到 CSS `.count-badge` 格式
- ✅ 徽章紧跟标题（h3 后），旧独立 label 已删除

### 3.4 删除按钮统一

- ✅ 服务器规则、部落运维、部落基地三页删除按钮统一风格
- ✅ 使用辅助函数 `_delSRTab()` / `_delTOTab()` / `rmBRTab()` 避免中文引号转义问题
- ✅ 删除按钮移至保存行内，与保存按钮同框架

### 3.5 移动端响应式

- ✅ `@media (max-width: 768px)` 适配
- ✅ 侧边栏隐藏：`.grid-2 > .tab-sidebar, .grid-2 > .resize-handle { display: none !important }`
- ✅ `server-tabs` 横向滚动（`overflow-x: auto`，隐藏滚动条 `scrollbar-width: none`）
- ✅ 卡片透明化：`.card { background: transparent; border: none; }`
- ✅ 移动端 TAB 浮窗选择器（`mobile-tab-popup` + `mobile-tab-btn`）
- ✅ 预览区自动折叠
- ✅ 预览按钮文字切换："+预览" → "折叠预览" → "跳转预览"（移动端改为新窗口打开）

### 3.6 "添加"函数重构

- ✅ `addStorageItem` / `addStorageCat` 从硬编码 HTML 模板改为 `data.push() + renderBaseRef()` 模式
- ✅ `selectDeviceIcon` 图标选择器：选中图标后更新数据模型 + `renderBaseRef()`
- ✅ 展开状态通过 `_restoreExpandState()` 保持

### 3.7 Tab 配置 UX

- ✅ 名称和描述的"标题 label"移除，改为输入框内 `placeholder` 提示文字

---

## 四、当前版本（v364）变更明细

### 4.1 修复：移动端纵向滚动条（已分析，部分修复）

**根因**：`#main` 元素有 `.editor-panel` 类，该类设置 `overflow-y: auto`。移动端 outer wrapper 的 `min-height: 100%` 使内容超出 `#main` 约 1-2px，触发滚动条。

**v363 尝试**：`overflow: hidden !important` → ❌ 导致保存按钮行被裁剪消失（因为 outer wrapper 吃满 100% 高度，grid-2 被挤出可视区）。

**v364 修复**：改为 `overflow-y: visible !important`（覆盖 `.editor-panel` 的 auto，但不裁剪内容）。

### 4.2 修复：2 个 mobile-tab-shell

**根因**：`_initMobileTabSelect()` 被调用 7 处（多处 setTimeout），旧清理逻辑只删除 `.mobile-tab-btn` 和 `.mobile-tab-popup`，未删除 `.mobile-tab-shell` 壳子，导致每次调用残留一个空壳。

**修复**：清理区新增 `document.querySelector('.mobile-tab-shell')?.remove()`。

### 4.3 调整：mobile-tab-shell 位置

**需求**：shell 应在 server-tabs card（孤岛/焦土… 选择行）下方。

**v364 实现**：遍历 `#main` 直接子元素，找到 `minHeight === '100%'` 的 outer wrapper，在其后插入 shell。

### 4.4 ⚠️ 已知问题

- **mobile-tab-shell 在 v364 中完全消失**：outer wrapper 检测逻辑（`c.style.minHeight === '100%'`）在某些渲染路径下可能匹配失败，导致插入未执行。用户确认明天继续排查。

---

## 五、待办任务

| # | 任务 | 状态 | 优先级 |
|---|------|------|--------|
| 1 | 修复 mobile-tab-shell 消失问题 | ⚠️ v364 回归 | 🔴 最高 |
| 2 | 预览按钮文字切换 + 删除按钮重设计 | 待实施 | 🟡 |
| 3 | markerColor 浮窗改造（计划已有） | 待实施 | 🟢 |
| 4 | `togglePreview` 在 `_initMobileTabSelect` 中的副作用 | 已注释掉，需正式修复 | 🟡 |
| 5 | mobile-tab-btn 自动创建 200ms setTimeout 偶发失败 | 待排查 | 🟡 |
| 6 | 服务器规则/部落运维编辑器框架与部落基地对齐 | 部分完成 | 🟢 |
| 7 | `add-block-panel` 在 renderTribeOps 中跟随 blocks 自然排列 | 待实施 | 🟢 |

---

## 六、技术债与注意事项

### 6.1 CSS 架构问题

- `#main` 没有独立 CSS 规则，样式来自 `.editor-panel` 类
- Outer wrapper 使用内联样式（无 class/id），难以用 CSS 选择器定位
- 多处 `!important` 正在积累，增加维护难度
- 移动端 `.grid-2` 的 `min-height: 100%`（CSS）与内联 `min-height: 0` 存在潜在冲突

### 6.2 JavaScript 架构问题

- `_initMobileTabSelect()` 在 7 处调用，每次渲染都触发，应改为事件驱动或单次初始化
- `innerHTML` 替换会销毁所有 Sortable 实例，需要 `_restoreExpandState()` 补偿
- HTML 模板字符串中单引号转义问题需要通过辅助函数规避

### 6.3 DOM 结构注意事项

- 许多 HTML 模板中的 `<div>` 是"开而不闭"的（闭合在很远处的 `</div></div></div>` 链），修改时极易破坏布局
- `#main` 是 `.grid-2` 的兄弟节点，不是子节点（原始架构）
- Flex 布局中 `flex-shrink: 0` 的标签和 `margin` 间距元素不能随意删除

### 6.4 文件截断

- `asa-admin.html` 内容在对话上下文中被截断/压缩，大量函数体显示为空行
- 编辑前需先 Read 目标区域确认实际内容

---

## 七、已知崩溃与恢复记录

| 事件 | 版本 | 恢复方式 |
|------|------|----------|
| v341 反斜杠编辑导致文件损坏（1行） | v341 | 从 v301 基线恢复 |
| v347 card 框架对齐破坏布局 | v347 | 保留 `.card` class，只改内联 style |
| v363 overflow:hidden 导致保存行消失 | v363 | v364 改为 overflow-y: visible |
| v364 shell 检测逻辑导致按钮消失 | v364 | 待修复 |

---

## 八、关键 CSS 代码段（当前 v364）

### 移动端媒体查询（L3460-3475）

```css
@media (max-width: 768px) {
  .grid-2 { grid-template-columns: 1fr !important; }
  .grid-2 > .tab-sidebar, .grid-2 > .resize-handle { display: none !important; }
  .mobile-tab-shell { display: block !important; background: var(--card); border-top: 1px solid var(--border); width: 100%; }
  .mobile-tab-btn { display: flex !important; width: 100% !important; margin-bottom: 0 !important; }
  header { padding: 8px 12px; gap: 8px; }
  header h1 { font-size: 1em; }
  header span, header button, header label { font-size: 0.75em; }
  nav button { padding: 6px 10px; font-size: 0.75em; }
  .server-tabs { flex-wrap: nowrap !important; overflow-x: auto; -webkit-overflow-scrolling: touch; margin-bottom: 4px !important; scrollbar-width: none; -ms-overflow-style: none; }
  .server-tabs::-webkit-scrollbar { display: none; }
  .server-tab { flex-shrink: 0; }
  .card { background: transparent !important; border: none !important; padding: 8px !important; margin-bottom: 0 !important; border-radius: 0 !important; }
  .grid-2 { background: var(--card); width: 100% !important; min-height: 100%; }
  .workspace { align-items: stretch; }
  #main.editor-panel { padding: 0 !important; overflow-y: visible !important; }
}
```

### 移动端组件样式（L3477-3483）

```css
.mobile-tab-shell { display: none; }
.mobile-tab-btn { display: none; padding: 8px 12px; font-size: 0.9em; color: var(--accent); border: none; background: transparent; cursor: pointer; align-items: center; gap: 4px; white-space: nowrap; font-weight: bold; }
.mobile-tab-popup { display: none; position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.5); z-index: 99999; justify-content: center; align-items: flex-start; padding-top: 15vh; }
.mobile-tab-popup.show { display: flex; }
.mobile-tab-popup-inner { background: var(--card); border: 1px solid var(--border); border-radius: 8px; padding: 12px; max-width: 280px; width: 90%; max-height: 60vh; overflow-y: auto; }
.mobile-tab-popup-inner .item-entry { display: block !important; padding: 8px 12px; cursor: pointer; border-radius: 4px; margin: 2px 0; white-space: nowrap; }
.mobile-tab-popup-inner .item-entry.active { background: var(--accent); color: #fff; }
.mobile-tab-popup-inner .item-entry:hover:not(.active) { background: var(--input-bg); }
```

---

## 九、DOM 结构参考

### 桌面端

```
body (display:flex; flex-direction:column)
├── header
└── .workspace (display:flex; flex:1; min-height:0; overflow:hidden)
    └── #main.editor-panel (overflow-y:auto)
        ├── div (outer wrapper: min-height:100%)
        │   └── .card > .server-tabs (孤岛 焦土…)
        └── .grid-2 (display:grid; 两列)
            ├── 侧边栏（TAB 列表）
            ├── .resize-handle（拖拽调整分栏）
            └── 内容区（编辑器卡片 + 保存行）
```

### 移动端（目标）

```
body (display:flex; flex-direction:column)
├── header
└── .workspace
    └── #main.editor-panel (overflow-y:visible)
        ├── div (outer wrapper)
        │   └── .card > .server-tabs（横向滚动）
        ├── .mobile-tab-shell ← 在此处，紧贴 card 下方
        │   └── .mobile-tab-btn
        └── .grid-2 (单列)
            └── 内容区
```

---

## 十、配色方案与变量

| 变量 | 用途 |
|------|------|
| `--bg` | 页面背景 |
| `--card` | 卡片/面板背景（白色） |
| `--text` | 主文字色 |
| `--accent` | 强调色（mobile-tab-btn 字色） |
| `--border` | 边框色（mobile-tab-shell 顶部描边） |
| `--danger` | 删除按钮色 |
| `--input-bg` | 输入框/浮窗选项悬停背景 |

---

## 十一、上传脚本说明

`_upload_v173.py`：
- 自动检测服务器最新版本号 `asa-admin-v{N}.html`
- 递增版本号上传
- 保留最近 **10** 个版本，自动删除旧版
- SFTP 凭证硬编码在脚本中（`192.168.197.253:22 root`）

---

*报告由 Claude Code 智能体根据对话历史生成。*
