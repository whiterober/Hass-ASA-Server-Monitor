# 编辑器 → 页面实时同步方案

## 现状分析

```
编辑器 (asa-admin.html)
  ├─ 编辑结构化数据 (reference_table, server_list, card_grid 等)
  ├─ 编辑 raw_html (最后两个Tab：补给速查、采集速查)
  └─ 保存 → /config/www/asa-data/tribe_ops.json
                ↓ shell_command.save_asa_data
              render_asa.py → 生成 /config/www/asa-data/tribe_tab_*.html
                ↓
              ✗ 断点：lovelace 不会自动更新（HTML 是 build_lovelace.py 预嵌入的）
```

**关键问题：** lovelace 页面中的内容是 `build_lovelace.py` **构建时嵌入**的，不是动态加载。编辑器改了 JSON → `render_asa.py` 生成 HTML → 但 lovelace 不知道。

## 方案：服务端自动构建流水线

核心思路：把 `build_lovelace.py` 部署到 HA 服务器上，编辑器保存后自动触发重建 → 重载。

### 架构

```
编辑器 (asa-admin.html)
  ├─ 保存 → /config/www/asa-data/tribe_ops.json
  └─ WS 调用:
       ├─ shell_command.render_asa     (生成 HTML 文件，已有)
       ├─ shell_command.build_lovelace (新增：重建 lovelace 嵌入内容)
       └─ shell_command.reload_lovelace (新增：重载 lovelace，无需重启)
```

### 详细步骤

#### 1. 创建 `/config/build_lovelace.py`（服务端版）

与本地版 `build_lovelace.py` 对比：

| | 本地版 | 服务端版 |
|---|---|---|
| 数据来源 | `B:\...\data\*.json` | `/config/www/asa-data/*.json` |
| lovelace 路径 | `A:\...\Temporary\lovelace` | `/config/.storage/lovelace` |
| 输出 | 写本地 + lovelace.lovelace | 写 `/config/lovelace`, `/config/lovelace.lovelace`, `/config/.storage/lovelace` |
| 最后两个Tab | `copy.deepcopy` 从旧页复制 | `render_tab_html()` 读取 JSON 中的 raw_html，用 `make_content_card()` 生成（结构匹配旧页） |

**为什么最后两个Tab不能继续 deep copy：**
- 旧页面的内容是固定的，如果编辑器改了 JSON 数据，deep copy 不会反映变化
- 改为：从 JSON 的 `tab.html` 字段读取（编辑器 textarea 编辑的内容）
- 卡片结构（conditional → mod-card → tailwindcss-template-card + grid_options）由 `make_content_card()` 生成，与旧页面完全一致

#### 2. 添加 shell_command

```yaml
# configuration.yaml
shell_command:
  build_lovelace: "python3 /config/build_lovelace.py"
  reload_lovelace: "ha core reload"
```

#### 3. 更新编辑器保存流程

在 `asa-admin.html` 的 `saveJSON()` 函数中，保存后追加调用：

```javascript
// 原有
await WS.callService('shell_command', 'save_asa_data', {...});
await WS.callService('shell_command', 'render_asa', {...});

// 新增
await WS.callService('shell_command', 'build_lovelace', {});
// 等待 2 秒让文件写入完成
await new Promise(r => setTimeout(r, 2000));
await WS.callService('shell_command', 'reload_lovelace', {});
```

#### 4. 最后两个 Tab 的卡片生成

`build_lovelace.py` 中，对于最后两个 Tab（`raw_html` 类型），用以下结构生成：

```python
# 不再从旧页 deep copy，而是从 JSON 数据生成
for t in tabs[5:]:  # 补给速查、采集速查
    tname = t['name']
    t_html = render_tab_html(t)  # raw_html 类型直接返回 tab['html']
    cond = {
        "type": "conditional",
        "conditions": [{"condition": "state", "entity": "input_select.info_tribe_tab", "state": tname}],
        "card": make_content_card(t_html),
        "grid_options": {"columns": 24, "rows": "auto"}  # 匹配旧页
    }
    tab_cards.append(cond)
```

这样：
- ✅ 卡片结构（mod-card + tailwindcss-template-card + grid_options）与旧页一致
- ✅ HTML 内容来自 JSON → 编辑器可修改
- ✅ 编辑器改了 → JSON 更新 → build_lovelace 重新嵌入 → 页面更新

#### 5. 保持本地 build_lovelace.py 可用

- 本地版保留 `data/` 目录作为数据源
- 本地版保持 `deep copy` 最后两个Tab（数据来自本地 JSON）
- 本地版用于离线开发和初始部署

### 影响范围

| 文件 | 改动 |
|------|------|
| `/config/build_lovelace.py` | **新增** — 服务端构建脚本 |
| `/config/www/asa-admin.html` | 修改 — 保存流程增加 build + reload |
| `configuration.yaml` | 新增 2 个 shell_command |
| 本地 `data/asa_tribe_ops.json` | 不变（数据源保持一致） |
| 本地 `build_lovelace.py` | 小改：最后两个Tab从 deep copy 改为 render_tab_html（保持数据一致） |
| lovelace 页面 | 不变（结构/样式完全保持） |

### 不做什么

- ❌ 不改动 lovelace 卡片结构
- ❌ 不改最后两个Tab的样式
- ❌ 不用 iframe
- ❌ 不用动态模板 sensor

### 同步流程（执行顺序）

1. 部署 `/config/build_lovelace.py` 到服务器
2. 更新 `configuration.yaml`（加 shell_command）
3. 更新 `asa-admin.html`（加保存后调用）
4. 更新本地 `build_lovelace.py`（deep copy → render）
5. 手动执行一次完整流程验证
