# MDI 输入框去重 + 标题/描述行内联 MDI 解析 — 实施计划

> 基线：v1171 | 日期：2026-07-08 | 不含向后兼容 | 含全量数据迁移

---

## 一、目标

1. 删除 icon_group / info_card 编辑器中独立的 MDI 输入框（`mcICMdi`）
2. 标题和描述行支持 **全文内联** `mdi:icon-name` 语法，可与文字混排（如 `mdi:sword 战斗 mdi:shield 防御`）
3. 不影响现有 `[徽章文字]` 样式渲染
4. 输入框不做实时 MDI 预览
5. 将现有所有 `mdi_icon` 数据迁移为新格式（`mdi:xxx ` 前缀写入 title 文本）

---

## 二、涉及文件

| # | 文件 | 路径 | 改动量 |
|---|------|------|--------|
| 1 | asa-admin-v1171.html | `/config/www/asa-data/` | ~10 行 |
| 2 | build_lovelace.py | `b:\项目\Hass ASA Server Monitor\` | ~20 行 |
| 3 | preview_server.py | 同上 | ~20 行 |

---

## 三、asa-admin.html 改动明细

### 3.1 删除 MDI 输入框渲染（L2956 附近）

**当前代码**（该行在 `mcICQuoteColor` hidden input 之后、图标预览之前）：
```html
<input id="mcICMdi'+bi+'" value="'+esc(b.mdi_icon||'')+'" placeholder="MDI" title="MDI 图标" style="...28x28...">
```

**改为**：删除整行。

### 3.2 删除 MDI 保存逻辑（L3549）

**当前代码**：
```javascript
b.mdi_icon = document.getElementById('mcICMdi'+bi)?.value || '';
```

**改为**：删除该行。

### 3.3 新增：一次性迁移旧 mdi_icon 数据

采用 **localStorage 标记** 确保迁移只执行一次：

```javascript
// 一次性迁移：仅在 localStorage 无标记时执行
function migrateMdiIconsOnce(tabs) {
  if (localStorage.getItem('_mdi_migrated_v1172')) return;  // 已迁移，跳过
  let migrated = 0;
  for (const tab of tabs) {
    for (const section of tab.sections || []) {
      for (const block of section.blocks || []) {
        if (block.type === 'info_card' && block.mdi_icon) {
          const mi = block.mdi_icon;
          if (mi.startsWith('mdi:') && !(block.title||'').startsWith('mdi:')) {
            block.title = mi + ' ' + (block.title||'');
            migrated++;
          }
          delete block.mdi_icon;
        }
      }
    }
  }
  if (migrated > 0) {
    localStorage.setItem('_mdi_migrated_v1172', '1');
    console.log('MDI 迁移完成：' + migrated + ' 个块');
  }
}
```

> ⚠️ 在页面首次加载数据后调用一次，之后各次加载均跳过。如需重新迁移，清除 localStorage 中的 `_mdi_migrated_v1172` 键。

---

## 四、build_lovelace.py 改动明细

### 4.1 删除 mdi_icon 读取（L2135）

**当前**：
```python
ic_mdi = block.get('mdi_icon', '')
```

**改为**：删除该行。

### 4.2 标题 MDI 解析（L2207-2210 替换）

**当前**：
```python
if ic_mdi:
    if ic_mdi.startswith('mdi:'):
        parts.append('<ha-icon icon="{}" class="{}"></ha-icon> '.format(ic_mdi, auto_cls))
    else:
        parts.append('<span class="ic-emoji">{}</span> '.format(esc(ic_mdi)))
```

**改为**：全文解析 `mdi:xxx` → `<ha-icon>`（支持混排）：
```python
import re
def _render_mdi_inline(text, extra_class=''):
    """将文本中所有 mdi:xxx 替换为 <ha-icon>，其余文本 escape"""
    result = []
    last = 0
    for m in re.finditer(r'mdi:([\w-]+)', text):
        if m.start() > last:
            result.append(esc(text[last:m.start()]))
        cls = ' class="{}"'.format(extra_class) if extra_class else ''
        result.append('<ha-icon icon="mdi:{}"{}></ha-icon>'.format(m.group(1), cls))
        last = m.end()
    if last < len(text):
        result.append(esc(text[last:]))
    return ''.join(result)

# 标题渲染
parts.append('<span{}>{}</span>'.format(title_color_style, _render_mdi_inline(ic_title, auto_cls)))
```

> `mdi:([\w-]+)` 不会匹配 `[徽章]` 内的内容（徽章不含 `mdi:` 前缀），天然兼容。

### 4.3 描述行 MDI 解析

描述文本同样用 `_render_mdi_inline()` 全文混排：
```python
_desc_text = desc.get('text', '') if isinstance(desc, dict) else str(desc)
parts.append(_render_mdi_inline(_desc_text))
```

### 4.4 图标组标题 MDI 解析（L2261-2271）

图标组标题当前只从 server_map 取图标。改为 `_render_mdi_inline()` 全文混排：
```python
if ig_title:
    # server_map 图标仅在没有显式 mdi: 时作为 fallback
    has_explicit_mdi = bool(re.search(r'mdi:([\w-]+)', ig_title))
    title_icon_html = ''
    if not has_explicit_mdi:
        if linear_maps:
            sm = _lookup_style(linear_maps[0])
            title_icon_html = '<ha-icon icon="{}" style="..."></ha-icon>'.format(sm.get('icon','mdi:map'))
        elif block_maps:
            sm = _lookup_style(block_maps[0])
            title_icon_html = '<ha-icon icon="{}" style="..."></ha-icon>'.format(sm.get('icon','mdi:map'))
    # 标题文本中的 mdi: 由 _render_mdi_inline 解析
    parts.append('<span>{}{}</span>'.format(title_icon_html, _render_mdi_inline(ig_title)))
```

---

## 五、preview_server.py 改动明细

与 build_lovelace.py 完全一致的 MDI 解析逻辑，涉及函数：
- info_card 标题渲染
- info_card 描述行渲染
- icon_group 标题渲染

---

## 六、数据迁移方案

### 6.1 迁移方式：localStorage 一次性标记

首次加载 v1172 时执行迁移，标记写入 `localStorage._mdi_migrated_v1172`，后续加载跳过。

### 6.2 迁移逻辑
```javascript
function migrateMdiIconsOnce(tabs) {
  if (localStorage.getItem('_mdi_migrated_v1172')) return;
  let migrated = 0;
  for (const tab of tabs) {
    for (const section of tab.sections || []) {
      for (const block of section.blocks || []) {
        if (block.type === 'info_card' && block.mdi_icon) {
          const mi = block.mdi_icon;
          if (mi.startsWith('mdi:') && !(block.title||'').startsWith('mdi:')) {
            block.title = mi + ' ' + (block.title||'');
            migrated++;
          }
          delete block.mdi_icon;
        }
      }
    }
  }
  if (migrated > 0) {
    localStorage.setItem('_mdi_migrated_v1172', '1');
    console.log('MDI 迁移完成：' + migrated + ' 个块');
  }
}
```

### 6.3 迁移验证
- 迁移后保存一次（点「💾 保存Tab」）
- 检查 lovelace 渲染结果：标题前的图标应与迁移前一致
- 刷新页面 → 控制台应无 "MDI 迁移完成" 日志（已跳过）

---

## 七、执行顺序

```
1. 备份 v1171 → asa-admin_baseline_v1171_20260708.html
2. 修改 asa-admin.html → v1172
3. _upload_v173.py 部署
4. 浏览器打开 → 验证迁移生效（旧 mdi_icon 自动转为 title 前缀）
5. 修改 build_lovelace.py + preview_server.py
6. 上传 py 文件到 /config/
7. ASA 后台「💾 保存Tab」→「应用」
8. 浏览器验证 HA 实页渲染
```

---

## 八、风险点

| 风险 | 缓解 |
|------|------|
| 迁移时 mdi_icon 非 `mdi:` 格式（emoji） | 跳过非 `mdi:` 前缀的值 |
| 标题已有 `mdi:` 前缀时重复迁移 | 检查 `!title.startsWith('mdi:')` |
| `[徽章]` 被误解析 | `mdi:([\w-]+)` 正则不含 `[ ]`，天然不冲突 |
| 描述行 MDI 在折叠模式下不显示 | `_render_mdi_inline()` 统一调用，折叠/展开两分支均生效 |
| `mdi:xxx` 中 xxx 含特殊字符 | `[\w-]+` 只匹配字母数字下划线连字符，安全 |
