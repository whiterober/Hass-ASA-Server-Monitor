# 设备图标选择器 — 实施方案

## 安全架构：HA 代理 S3 API

```
浏览器 ──fetch──→ HA 服务器 ──S3 API──→ CloudFlare R2
(f12看不到Key)    (Key存在磁盘)       (真实图标)
```

**Key 永远不出 HA 服务器。**

---

## R2 配置（可在编辑器中修改）

存储位置：HA 服务器 `/config/www/asa-data/r2_config.json`
```json
{
  "access_key": "756f9ff275e87aa214bf724ece0e8ef6",
  "secret_key": "42f606caf5f06bbaecd152ffe8e498bfa31fa164d4b0e999049056219f231da0",
  "bucket": "eagle-img",
  "endpoint": "https://c07d1eafa8cf05e0d751a81b673b8e89.r2.cloudflarestorage.com",
  "prefix": "ASA/",
  "public_base": "https://img.whiterober.ccwu.cc"
}
```

Shell 脚本从此 JSON 读取参数，不在脚本中硬编码。

---

## 编辑器中的 R2 配置面板

在 ASA 后台管理页面新增一个 Tab 或设置入口（如导航栏加 `⚙️ R2`），面板内容：

```
┌─ R2 存储桶配置 ──────────────────────────┐
│ Access Key:  [_______________________]    │
│ Secret Key:  [_______________________]    │
│ Bucket:      [_______________________]    │
│ Endpoint:    [_______________________]    │
│ 前缀:        [_______________________]    │
│ 公开域名:    [_______________________]    │
│                                            │
│ [🔄 测试连接]  [💾 保存配置]              │
└──────────────────────────────────────────┘
```

- 「🔄 测试连接」：调用 `shell_command.list_r2_icons` 验证配置
- 「💾 保存配置」：写入 `r2_config.json` 到 HA 服务器
- 保存方式：通过 HA WebSocket `shell_command` 或小文件写入脚本

---

## 后端：Shell 脚本（HA 服务器上）

**`/config/www/asa-data/list_icons.sh`**（权限 600）：
```bash
#!/bin/bash
CONFIG="/config/www/asa-data/r2_config.json"
ACCESS_KEY=$(python3 -c "import json;print(json.load(open('$CONFIG'))['access_key'])")
SECRET_KEY=$(python3 -c "import json;print(json.load(open('$CONFIG'))['secret_key'])")
BUCKET=$(python3 -c "import json;print(json.load(open('$CONFIG'))['bucket'])")
ENDPOINT=$(python3 -c "import json;print(json.load(open('$CONFIG'))['endpoint'])")
PREFIX=$(python3 -c "import json;print(json.load(open('$CONFIG'))['prefix'])")
BASE=$(python3 -c "import json;print(json.load(open('$CONFIG'))['public_base'])")

aws s3api list-objects-v2 \
  --bucket "$BUCKET" \
  --endpoint-url "$ENDPOINT" \
  --prefix "$PREFIX" \
  --aws-access-key-id "$ACCESS_KEY" \
  --aws-secret-access-key "$SECRET_KEY" \
  --query "Contents[?contains(Key,'.png')||contains(Key,'.webp')||contains(Key,'.svg')||contains(Key,'.jpg')].[Key]" \
  --output json | \
python3 -c "
import json,sys
data = json.load(sys.stdin)
result = []
for item in data:
    key = item[0] if isinstance(item,list) else item
    name = key.rsplit('/',1)[-1].rsplit('.',1)[0]
    result.append({'name':name,'url':'$BASE/'+key})
print(json.dumps(result,ensure_ascii=False))
"
```

**`configuration.yaml` 加 shell_command**：
```yaml
shell_command:
  list_r2_icons: "/bin/bash /config/www/asa-data/list_icons.sh > /config/www/asa-data/icons.json"
```

新增图标后：点浮窗里的「🔄 刷新」按钮，触发 shell_command 重新拉取并刷新列表。

---

## 前端：数据加载 + 实时刷新

### 首次加载
浏览器 fetch `/local/asa-data/icons.json`。

### 浮窗内「🔄 刷新」按钮
点击后调用 HA WebSocket API 触发 `shell_command.list_r2_icons`，等待 2 秒后重新 fetch JSON 并更新浮窗网格。

```javascript
// 通过 HA WebSocket 触发刷新
function refreshIconList() {
  // HA WebSocket call: call_service('shell_command', 'list_r2_icons')
  // 等待完成后重新 fetch icons.json
}
```

### 浮窗布局更新

```
┌────────────────────────────────────┐
│ 🔍 [搜索...]    [🔄 刷新] [✕ 关闭]│
├────────────────────────────────────┤
│         图标网格...                 │
└────────────────────────────────────┘
```

---

## 实施计划

### 1. 后端搭建
- 写 `list_icons.sh` 到 HA 服务器（chmod 600）
- 加 `shell_command.list_r2_icons` 到 `configuration.yaml`
- 首次执行生成 `icons.json`

### 2. 数据加载

`asa-admin.html` 页面加载时 fetch `/local/asa-data/icons.json`，缓存全局 `deviceIconList`。

### 3. 图标浮窗

点击存储行头部的设备缩略图 → 弹出 `position:fixed` 浮窗：

```
┌────────────────────────────────────┐
│ 🔍 [搜索...]           [✕ 关闭]  │
├────────────────────────────────────┤
│ ┌──────┐ ┌──────┐ ┌──────┐ ┌─────┐│
│ │ 🖼   │ │ 🖼   │ │ 🖼   │ │ 🖼  ││
│ │Cryo  │ │Refrig│ │Vault │ │ ... ││
│ └──────┘ └──────┘ └──────┘ └─────┘│
└────────────────────────────────────┘
```

- 每行 4~6 个图标，每个 56×56px，object-fit:contain
- 文件名显示在图下方（截断+title tooltip）
- 搜索框实时过滤
- 选中项高亮边框 + 自动关闭浮窗
- 点击外部关闭

### 4. 选中后

更新 `brSRIcon` 输入框 → 行头缩略图刷新 → 预览更新。

### 5. 代码改动范围

| 文件 | 改动 |
|------|------|
| `asa-admin.html` CSS | 浮窗+网格+搜索框样式 + R2配置面板样式 |
| `asa-admin.html` JS | `loadIconList()`、`openIconPicker()`、R2配置CRUD、搜索过滤 |
| `asa-admin.html` 模板 | 存储行头部 `<img>` 加 `onclick` + 导航栏 R2 配置入口 |
| `asa-admin.html` 导航 | 新增 `⚙️ R2` Tab（或设置面板入口） |
| HA `configuration.yaml` | 加 `shell_command.list_r2_icons` + `shell_command.save_r2_config` |
| HA `/config/www/asa-data/list_icons.sh` | S3 list 脚本（600 权限，读 r2_config.json） |
| HA `/config/www/asa-data/r2_config.json` | R2 配置存储（初始值预置） |

不改数据模型、保存逻辑、build_lovelace.py。

### 6. 编辑器中两处显示缩略图都要加 onclick

- `renderBaseRef` 存储行头部 `<img>`
- `addStorageRow` 同理

### 2. 图标浮窗

点击存储行头部的设备缩略图（`<img src="...">`）→ 弹出 `position:fixed` 浮窗：

```
┌────────────────────────────────────┐
│ 🔍 [搜索...]           [✕ 关闭]  │
├────────────────────────────────────┤
│ ┌──────┐ ┌──────┐ ┌──────┐ ┌─────┐│
│ │ 🖼   │ │ 🖼   │ │ 🖼   │ │ 🖼  ││
│ │Cryo  │ │Refrig│ │Vault │ │ ... ││
│ └──────┘ └──────┘ └──────┘ └─────┘│
│ ┌──────┐ ┌──────┐ ┌──────┐ ┌─────┐│
│ │ 🖼   │ │ 🖼   │ │ 🖼   │ │ 🖼  ││
│ └──────┘ └──────┘ └──────┘ └─────┘│
└────────────────────────────────────┘
```

- 每行 4~6 个图标，每个 56×56px
- 文件名显示在图下方（截断）
- 搜索框实时过滤
- 选中项高亮 + 自动关闭浮窗
- 点击外部关闭

### 3. 选中后

更新 `brSRIcon` 输入框 → 缩写略图刷新 → 预览自动更新（`showPreview()`）。

### 4. 代码改动范围

| 文件 | 改动 |
|------|------|
| `asa-admin.html` CSS | 浮窗+网格+搜索框样式 |
| `asa-admin.html` JS | `loadIconList()`、`openIconPicker()`、搜索过滤 |
| `asa-admin.html` 模板 | 缩略图加 `onclick` |

不改数据模型，不改保存逻辑，不改 build_lovelace.py。

### 5. 编辑器中两处显示缩略图的位置都要加 onclick

- `renderBaseRef` 中存储行头部的 `<img>`
- 展开 body 中的图标 URL 旁边可以放个缩略图预览（可选增强）

---

## 待你确认

1. 选方案 A 还是 B？
2. 确认后再实施
