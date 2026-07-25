# ARK 汉化更新流程

> 目的：从 ARK 游戏文件中提取最新的中英对照文本，用于更新 `icon_zh_map.json` 等翻译数据。

---

## 准备工作

| 工具/文件 | 路径/来源 |
|-----------|----------|
| **FModel** | 需自行下载（UE5 .locres 提取工具） |
| **汉化补丁** | 用户自行准备的 ARK 汉化文件所在文件夹 |
| **英文对照源** | `B:\Epic Games\ARKDevkit\Projects\ShooterGame\Content\Localization\ShooterGame\en\ShooterGame.po` |

---

## 操作步骤

### 第 1 步：启动 FModel

```
双击 FModel.exe
```

### 第 2 步：选择汉化补丁所在文件夹

FModel 界面中，浏览并选择汉化补丁（`.pak` / `.ucas` 等 ARK 资源文件）所在的文件夹。

### 第 3 步：设置引擎版本

在 FModel 的引擎版本选择中，选择 **`UE5_2`**（Unreal Engine 5.2，ARK ASA 所用版本）。

### 第 4 步：定位 `ShooterGame.locres`

在 FModel 中浏览已加载的资源，导航到以下路径找到本地化文件：

```
ShooterGame/Content/Localization/ShooterGame/zh/ShooterGame.locres
```

> ⚠️ 注意：`zh` 表示中文语言包。若需要其他语言，选择对应文件夹（`en`=英文, `ja`=日文等）。

### 第 5 步：导出为 JSON

右键 `ShooterGame.locres` → **保存为 JSON**

### 第 6 步：确认输出路径

导出后的 JSON 文件位于：

```
A:\Output\Exports\ShooterGame\Content\Localization\ShooterGame\zh\
```

将该文件复制到项目开发文件夹：

```powershell
Copy-Item "A:\Output\Exports\ShooterGame\Content\Localization\ShooterGame\zh\*" "b:\项目\Hass ASA Server Monitor\汉化\" -Force
```

### 第 7 步：对照英文源

英文对照文件路径：

```
B:\Epic Games\ARKDevkit\Projects\ShooterGame\Content\Localization\ShooterGame\en\ShooterGame.po
```

`.po` 文件格式为 GNU gettext 标准，可直接用文本编辑器打开查看英文字符串及其 msgid。

将英文源复制到同一目录：

```powershell
Copy-Item "B:\Epic Games\ARKDevkit\Projects\ShooterGame\Content\Localization\ShooterGame\en\ShooterGame.po" "b:\项目\Hass ASA Server Monitor\汉化\" -Force
```

---

## 输出文件说明

| 文件 | 格式 | 说明 |
|------|------|------|
| `ShooterGame.locres`（源） | UE5 二进制 | ARK 游戏内的本地化资源 |
| 导出 JSON | JSON | 键值对：`{ "ItemName_XXX": "中文翻译" }` |
| `ShooterGame.po`（英） | GNU PO | 英文原文对照 |

---

## 构建并部署

### 第 8 步：运行构建脚本

```powershell
Push-Location "b:\项目\Hass ASA Server Monitor"; .\.venv-1\Scripts\python.exe "汉化\_build_icon_zh_map.py"
```

### 第 9 步：上传到服务器

```powershell
Push-Location "b:\项目\Hass ASA Server Monitor"; .\.venv-1\Scripts\python.exe -c "import paramiko;h='192.168.197.253';t=paramiko.Transport((h,22));t.connect(username='root',password='1219Wu1219@');s=paramiko.SFTPClient.from_transport(t);s.put('汉化/icon_zh_map.json','/config/www/asa-data/icon_zh_map.json');s.close();t.close();print('OK')"
```

---

## 常见问题

| 问题 | 解决 |
|------|------|
| FModel 无法打开 .pak 文件 | 确认选择 `UE5_2` 引擎版本；检查 .pak 文件完整性 |
| 找不到 `ShooterGame.locres` | 确认汉化补丁包含本地化文件；尝试在其他 `.pak` 中查找 |
| JSON 导出的 key 与英文 `.po` 不一致 | 部分汉化补丁使用自定义 key，需手动匹配 |
| `.po` 文件乱码 | 确保以 UTF-8 编码打开 |

---

## 一键准备（拉取输入文件）

从项目根目录执行，一次性完成 3 个输入文件的拉取/复制：

```powershell
python -c "
import paramiko,shutil,os
h='192.168.197.253';u='root';pw='1219Wu1219@'
# 1. 拉取服务器 icons2.json
t=paramiko.Transport((h,22));t.connect(username=u,password=pw)
s=paramiko.SFTPClient.from_transport(t)
s.get('/config/www/asa-data/icons2.json',r'b:\项目\Hass ASA Server Monitor\汉化\icons2.json')
s.close();t.close()
print('1/3 拉取 icons2.json OK')
# 2. 步骤6：zh JSON
shutil.copy2(r'A:\Output\Exports\ShooterGame\Content\Localization\ShooterGame\zh\ShooterGame.json',r'b:\项目\Hass ASA Server Monitor\汉化\ShooterGame.json')
print('2/3 复制 ShooterGame.json OK')
# 3. 步骤7：en PO
shutil.copy2(r'B:\Epic Games\ARKDevkit\Projects\ShooterGame\Content\Localization\ShooterGame\en\ShooterGame.po',r'b:\项目\Hass ASA Server Monitor\汉化\ShooterGame.po')
print('3/3 复制 ShooterGame.po OK')
print('全部就绪，可运行: python 汉化/_build_icon_zh_map.py')
"

# 构建后上传（第8-9步合并）
Push-Location "b:\项目\Hass ASA Server Monitor"; .\.venv-1\Scripts\python.exe "汉化\_build_icon_zh_map.py"
```

构建完成后再上传：

```powershell
Push-Location "b:\项目\Hass ASA Server Monitor"; .\.venv-1\Scripts\python.exe -c "import paramiko;h='192.168.197.253';t=paramiko.Transport((h,22));t.connect(username='root',password='1219Wu1219@');s=paramiko.SFTPClient.from_transport(t);s.put('汉化/icon_zh_map.json','/config/www/asa-data/icon_zh_map.json');s.close();t.close();print('OK')"
```
