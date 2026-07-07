# HASS 切屏 + 游戏文本发送 — 落地实施方案

> 📅 2026-07-07 | 基于《HASS切屏，发送方案.md》细化
> 🔗 关联项目：Hass ASA Server Monitor — 方舟视图

---

## 一、前置铁律

### 🔴 铁律 1：改 lovelace 前必须先拉取 .sto 基线

任何 lovelace 修改前，**必须**从 HA 服务器拉取最新的 `lovelace.lovelace` 覆盖本地副本：

```powershell
# SSH 拉取 .sto lovelace.lovelace → 覆盖本地
python -c "
import paramiko
h='192.168.197.253';p=22;u='root';pw='1219Wu1219@'
c=paramiko.SSHClient();c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(h,port=p,username=u,password=pw,look_for_keys=False,allow_agent=False)
sftp=c.open_sftp()
# 拉取 .storage 中的 lovelace.lovelace（HA 运行态真源）
sftp.get('/homeassistant/.storage/lovelace.lovelace', r'A:\NetSarang\Xftp 8\Temporary\lovelace.lovelace')
# 同步为 lovelace（编辑用副本）
sftp.get('/homeassistant/.storage/lovelace.lovelace', r'A:\NetSarang\Xftp 8\Temporary\lovelace')
sftp.close();c.close()
print('✅ 基线拉取完成')
"
```

> ⚠️ 禁止假设本地最新。HA 上可能有其他人/进程修改过 lovelace。

> 📝 **说明**：本次计划修改的是「方舟」主视图（views[3]）的原生 lovelace 卡片，不涉及 ASA `build_lovelace.py` 生成的信息卡片页面。因此走标准 lovelace 编辑流程（编辑 → 同步 → SFTP 上传 → 重启 HA），无需 ASA 后台保存流程。

---

## 二、架构总览

```
Home Assistant (手机 Dashboard)
    │
    ▼
HASS.Agent (Windows 代理)
    │
    ┌──────────────┴──────────────┐
    ▼                              ▼
切屏                              游戏输入
    │                              │
MultiMonitorTool              AutoHotkey v2
    │                              │
    ▼                              ▼
电视/显示器主屏切换            当前焦点输入框 (ARK 筛选框)
```

---

## 三、第一部分：HASS 切屏

### 3.1 工具安装

| 工具 | 下载 | 安装路径 |
|------|------|----------|
| MultiMonitorTool | https://www.nirsoft.net/utils/multi_monitor_tool.html | `C:\Tools\MultiMonitorTool\` |

### 3.2 目录结构

```
C:\Tools\MultiMonitorTool\
├── MultiMonitorTool.exe
├── TV.cfg          ← 电视模式配置（电视=主屏）
└── GAME.cfg        ← 显示器模式配置（显示器=主屏）
```

### 3.3 创建配置文件

**步骤**：
1. 手动调整 Windows 显示设置：电视 = 主屏、显示器 = 副屏
2. 执行：`MultiMonitorTool.exe /SaveConfig C:\Tools\MultiMonitorTool\TV.cfg`
3. 手动调整：显示器 = 主屏、电视 = 副屏
4. 执行：`MultiMonitorTool.exe /SaveConfig C:\Tools\MultiMonitorTool\GAME.cfg`

### 3.4 创建批处理脚本

**`C:\Scripts\TV.bat`**：
```batch
@echo off
C:\Tools\MultiMonitorTool\MultiMonitorTool.exe /LoadConfig C:\Tools\MultiMonitorTool\TV.cfg
```

**`C:\Scripts\GAME.bat`**：
```batch
@echo off
C:\Tools\MultiMonitorTool\MultiMonitorTool.exe /LoadConfig C:\Tools\MultiMonitorTool\GAME.cfg
```

### 3.5 HASS.Agent 配置

在 HASS.Agent 中新增 2 个 Command：

| 名称 | 程序 | 参数 |
|------|------|------|
| `SwitchToTV` | `C:\Scripts\TV.bat` | （无） |
| `SwitchToGame` | `C:\Scripts\GAME.bat` | （无） |

> HASS.Agent 会自动将这两个 Command 注册为 HA 的 `button.switchtotv` 和 `button.switchtogame` 实体。

### 3.6 HA Lovelace 卡片

在「方舟」视图中新增一个 Grid section，添加 entities 卡片：

```json
{
  "type": "entities",
  "title": "🖥️ 屏幕切换",
  "entities": [
    {
      "entity": "button.switchtotv",
      "name": "📺 电视模式",
      "icon": "mdi:television"
    },
    {
      "entity": "button.switchtogame",
      "name": "🖥️ 显示器模式",
      "icon": "mdi:monitor"
    }
  ]
}
```

---

## 四、第二部分：手机输入文字直发游戏

### 4.1 工具安装

| 工具 | 下载 | 安装路径 |
|------|------|----------|
| AutoHotkey v2 | https://www.autohotkey.com/ | 默认安装路径 |

### 4.2 目录结构

```
C:\Scripts\
├── TypeGameText.ahk    ← AHK 源码
└── TypeGameText.exe    ← 编译后 exe（HASS.Agent 调用）
```

### 4.3 AutoHotkey 脚本

**`C:\Scripts\TypeGameText.ahk`**：

```autohotkey
#Requires AutoHotkey v2

if A_Args.Length > 0
{
    text := A_Args[1]
    A_Clipboard := text
    Sleep 100
    Send("^v")
}
```

### 4.4 编译

右键 `TypeGameText.ahk` → **Compile Script** → 生成 `TypeGameText.exe`。

### 4.5 HASS.Agent 配置

新增 1 个 Command：

| 名称 | 程序 | 参数 |
|------|------|------|
| `TypeGameText` | `C:\Scripts\TypeGameText.exe` | `{text}` |

> `{text}` 为 HASS.Agent 动态参数占位符，调用时替换为实际文本。

### 4.6 HA 配置

#### 4.6.1 `configuration.yaml` — 添加 input_text

```yaml
input_text:
  game_text:
    name: 游戏输入
    max: 200
```

#### 4.6.2 `scripts.yaml` — 添加发送脚本

```yaml
send_to_game:
  alias: 发送到游戏
  sequence:
    - service: hass_agent.command
      data:
        command: TypeGameText
        arguments:
          text: "{{ states('input_text.game_text') }}"

# 快捷按钮 — 常用搜索词
search_polymer:
  alias: 📦 聚合物
  sequence:
    - service: hass_agent.command
      data:
        command: TypeGameText
        arguments:
          text: "聚合物"

search_metal:
  alias: 🔩 金属
  sequence:
    - service: hass_agent.command
      data:
        command: TypeGameText
        arguments:
          text: "金属"

search_rex:
  alias: 🦖 霸王龙
  sequence:
    - service: hass_agent.command
      data:
        command: TypeGameText
        arguments:
          text: "霸王龙"

search_quetz:
  alias: 🪶 风神翼龙
  sequence:
    - service: hass_agent.command
      data:
        command: TypeGameText
        arguments:
          text: "风神翼龙"
```

### 4.7 HA Lovelace 卡片

在「方舟」视图中新增 Grid section，添加：

```json
{
  "type": "entities",
  "title": "🎮 游戏快捷输入",
  "entities": [
    {
      "entity": "input_text.game_text",
      "name": "搜索文本"
    },
    {
      "entity": "script.send_to_game",
      "name": "📤 发送到游戏"
    }
  ]
}
```

快捷按钮 Grid：

```json
{
  "type": "entities",
  "title": "⚡ 一键搜索",
  "entities": [
    { "entity": "script.search_polymer", "name": "📦 聚合物" },
    { "entity": "script.search_metal", "name": "🔩 金属" },
    { "entity": "script.search_rex", "name": "🦖 霸王龙" },
    { "entity": "script.search_quetz", "name": "🪶 风神翼龙" }
  ]
}
```

---

## 五、Lovelace 修改执行流程

### 5.1 完整步骤（不可跳步）

```
Step 1: 拉取基线
  └── SSH SFTP get /homeassistant/.storage/lovelace.lovelace → 本地 lovelace + lovelace.lovelace

Step 2: 备份当前版本
  └── Copy-Item 本地 lovelace → bak/lovelace_backup_YYYYMMDD_HHMMSS.json

Step 3: 编辑本地 lovelace
  └── 在「方舟」视图 (views[3]) 的 sections[] 中新增 Grid section
  └── 添加屏幕切换 + 游戏输入 + 快捷按钮卡片

Step 4: JSON 格式校验
  └── python -c "import json; json.load(open(r'A:\...\lovelace')); print('OK')"

Step 5: 同步本地 lovelace.lovelace
  └── Copy-Item lovelace → lovelace.lovelace -Force

Step 6: SFTP 上传到 HA 服务器
  └── python SSH sftp.put lovelace → /config/lovelace
  └── python SSH sftp.put lovelace.lovelace → /homeassistant/.storage/lovelace.lovelace

Step 7: MD5 验证（本地 vs 远程）
  └── 本地 MD5 vs SSH md5sum /homeassistant/.storage/lovelace.lovelace
  └── 两个 MD5 必须一致

Step 8: 重启 HA
  └── 需 askQuestions 用户确认后执行
  └── ssh root@host "ha core restart"

Step 9: 浏览器自验证
  └── open_browser_page 打开 HA 实页
  └── 截图/读页确认新卡片已出现、布局无异常
```

### 5.2 「方舟」视图新增 Section 插入位置

当前「方舟」视图 sections 结构（从末尾倒推）：

```
sections[]
├── [0] 部落运维速查入口 (Grid)
├── [1] ASA 服务器操作主卡片 (Grid)
├── [2] 服务器规则标题 (Grid)
├── [3] 服务器选择网格 (Grid)
├── [4] 操作系统选择 (Grid)
├── [5] 快速操作按钮 (Grid)
├── [6] 补丁信息入口 (Grid)
├── [7] 服务器状态显示 (Grid)
├── [8] 操作日志 (Grid)
└── [9] ← 🆕 屏幕切换 (Grid)        ← 新增
    [10]← 🆕 游戏快捷输入 (Grid)     ← 新增
    [11]← 🆕 一键搜索 (Grid)         ← 新增
```

---

## 六、验证清单

| # | 验证项 | 方法 |
|---|--------|------|
| 1 | MultiMonitorTool 配置正确 | 手动运行 TV.bat / GAME.bat，确认屏幕切换 |
| 2 | HASS.Agent 实体注册 | HA 开发者工具 → 实体 → 搜索 `button.switchto` |
| 3 | 屏幕切换按钮生效 | 手机点击 → 电视/显示器主屏切换 |
| 4 | TypeGameText.exe 可用 | 命令行 `TypeGameText.exe "测试"` → 焦点应用收到粘贴 |
| 5 | input_text.game_text 可输入 | HA 前端 → 方舟视图 → 输入框可见可用 |
| 6 | 发送脚本生效 | 输入文字 → 点击发送 → ARK 筛选框收到文字 |
| 7 | 快捷按钮生效 | 点击 📦 聚合物 → ARK 筛选框出现"聚合物" |
| 8 | Lovelace 本地与远程 MD5 一致 | 本地 MD5 vs SSH md5sum 验证 |
| 9 | 实页渲染正确 | 浏览器打开 HA lovelace 实页截图确认 |

---

## 七、注意事项

1. **AutoHotkey 依赖前台焦点**：发送文本时，ARK 游戏窗口必须是前台焦点（筛选框已点击激活）。
2. **中文输入法**：ARK 筛选框需处于英文输入模式，否则 `^v` 可能粘贴到输入法候选框。
3. **HASS.Agent 必须在 Windows 游戏机上运行**（非 HA 服务器）。当前 HASS.Agent 部署位置需确认。
4. **快捷按钮可按需扩展**：根据实际游戏搜索习惯添加更多常用词（水泥、火花 powder、铁锭等）。
5. **权限**：TypeGameText.exe 可能需要管理员权限才能向游戏窗口发送按键（取决于游戏的反作弊保护）。

---

## 八、涉及文件清单

| 文件 | 位置 | 操作 |
|------|------|------|
| `TV.cfg` | `C:\Tools\MultiMonitorTool\` | 🆕 新建 |
| `GAME.cfg` | `C:\Tools\MultiMonitorTool\` | 🆕 新建 |
| `TV.bat` | `C:\Scripts\` | 🆕 新建 |
| `GAME.bat` | `C:\Scripts\` | 🆕 新建 |
| `TypeGameText.ahk` | `C:\Scripts\` | 🆕 新建 |
| `TypeGameText.exe` | `C:\Scripts\` | 🆕 编译生成 |
| `configuration.yaml` | `/config/` (HA) | ✏️ 追加 input_text + scripts |
| `lovelace` | `A:\NetSarang\Xftp 8\Temporary\` | ✏️ 方舟视图追加 3 个 Grid section |
| `lovelace.lovelace` | `A:\NetSarang\Xftp 8\Temporary\` | 🔄 同步自 lovelace |

---

> 📝 **小白总结**：这个方案让手机变成 ARK 的"遥控器"——点一下切屏幕、输入文字直接发到游戏搜索框，不需要键盘鼠标。先装工具、写脚本、配 HASS.Agent，最后改 lovelace 加按钮就行。
