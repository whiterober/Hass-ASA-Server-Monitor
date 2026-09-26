# 部落基地预览渲染改造计划

> 基线：`baseline_20260706_201509` | 部署版本：v1112

## 核心思路

**不动 `preview_server.py`**。利用已有的 `buildStorageBody` + `buildBadgeHTML`（asa-admin.html），增强它们生成完整 HTML 的能力。用户保存时自动重建 body → 预览 `if b.get('body'):` 读取 → 全部正确。

## 当前保存→预览链路（已验证可用）

```
saveBaseTab()
  → 读 DOM 输入 → 构建 block.rows / block.badges
  → buildStorageBody(rows) → block.body（存储板块）✅
  → buildBadgeHTML(badges) → block.body（徽章板块）✅
  → 写入 JSON
  → 预览 if b.get('body'): 读取 body → 渲染
```

## 需要补充的内容

| 功能 | `buildStorageBody` 现状 | 需补充 |
|------|------------------------|--------|
| 设备图标反色 | 裸 `<img>` 无 CSS 类 | 读 `_dev_icon_mode` / `_dev_icon_lum`，加 `ic-auto-*` 类 |
| 物品级图标 | 只显示 `item.name` 文本 | 有 `item.icon_url` 时加 `<img>` 标签 |
| 分类子标签 | ❌ 缺失 | 读 `cat.sub_label` + `sub_label_color` |
| 分类列布局 | 简单 `<br>` 分隔 | ✅ 已有 column 分列逻辑 |

## 实施步骤

| 步骤 | 文件 | 改什么 |
|------|------|--------|
| ① | `asa-admin.html` | `buildStorageBody`：设备图标加 `image_auto_color_mode` 读取 + `ic-auto-*` CSS 类 |
| ② | `asa-admin.html` | `buildStorageBody`：物品有 `icon_url` 时渲染 `<img>` 标签 |
| ③ | `asa-admin.html` | `buildStorageBody`：分类子标签 `sub_label` + 颜色 |
| ④ | 无需改 | `buildBadgeHTML`：已完整 |
| ⑤ | 无需改 | `preview_server.py`：保持 `if b.get('body'):`，不动 |

## 不需要做的

- ❌ 不修改 `preview_server.py` 结构化渲染
- ❌ 不迁移 JS 逻辑到 Python
- ❌ 不动 `build_lovelace.py`

## 附带效果

一旦 `buildStorageBody` 生成完整 HTML，不仅预览正确——HA 端的 lovelace 卡片也会同步正确（因为 `build_lovelace.py` 的 `build_section_html` 也走 `sec.get("html")` 路径读取 body）。

## 相关文件

| 文件 | 位置 |
|------|------|
| 编辑器 | `www/asa-admin.html` |
| 预览服务器 | `ssh://hass/config/preview_server.py` |
| 数据文件 | `ssh://hass/config/www/asa-data/asa_base_quick_ref.json` |
| buildStorageBody | `www/asa-admin.html` 第 5454 行 |
| buildBadgeHTML | `www/asa-admin.html` 第 5356 行 |
| saveBaseTab | `www/asa-admin.html` 第 5036 行 |
| 基线备份 | `tmp/baseline_20260706_201509_*` |
