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

### 🔴 铁律 2：SFTP 上传后必须立即重建 ASA 视图

**安全工作流（铁律）**：另一个会话改 lovelace → SFTP 上传 → **立即 SSH 执行 `python3 /config/build_lovelace.py`** → 完成。

这一行命令会用最新 `server_rules.json` 等数据文件重建 ASA 视图，同时保留其他视图的改动。**无需再重启 HA**（`build_lovelace` 已同步 `.storage`）。

### 🔴 铁律 3：改 YAML / lovelace 前必须拉取最新

**任何 HA 配置文件（`configuration.yaml`、`scripts.yaml`、lovelace）修改前，必须先从服务器拉取最新版本覆盖本地。** 禁止假设本地文件最新——HA 上可能存在手动编辑或其他会话的改动。

```powershell
# 拉取全部 HA 配置
python -c "
import paramiko
h='192.168.197.253';p=22;u='root';pw='1219Wu1219@'
c=paramiko.SSHClient();c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(h,port=p,username=u,password=pw,look_for_keys=False,allow_agent=False)
sftp=c.open_sftp()
for f in ['configuration.yaml','scripts.yaml','lovelace','lovelace.lovelace']:
    remote = '/config/'+f if f.endswith('.yaml') else '/homeassistant/.storage/'+f
    local = r'A:\\NetSarang\\Xftp 8\\Temporary\\'+f
    sftp.get(remote, local)
    print(f'✅ {f}')
sftp.close();c.close()
"
```
>
> 🔗 切屏底层方案详见 `docs/自动切屏方案.md`。本地已实现登录自动切屏（TV=SteamShell 集成 ✅，显示器=计划任务 VBS），HASS.Agent 提供**远程手动切屏**能力。

---

## 二、架构总览

```
                    Home Assistant (手机 Dashboard)
                              │
                              ▼
                      HASS.Agent (Windows 代理)
                              │
          ┌───────────────────┴───────────────────┐
          ▼                                       ▼
      远程切屏                                 游戏输入
          │                                       │
  DisplaySwitch.exe                        AutoHotkey v2
  (/external /internal)                    (剪贴板 → ^v)
          │                                       │
          ▼                                       ▼
  电视/显示器切换                           ARK 筛选框
```

> 💡 本地自动切屏已在 Windows 启动时处理（计划任务 + SteamShell），HASS 按钮提供手机端**手动远程切屏**。

---

## 三、第一部分：HASS 远程切屏

### 3.1 工具确认

`B:\DisplaySwitch\DisplaySwitch.exe` 已在游戏机上就绪（Windows 自带 `displayswitch.exe` 的副本，等同于 `Win+P`）。

| 命令 | 效果 |
|------|------|
| `B:\DisplaySwitch\DisplaySwitch.exe /external` | 仅电视 |
| `B:\DisplaySwitch\DisplaySwitch.exe /internal` | 仅显示器 |

### 3.2 复用现有 VBS

`B:\DisplaySwitch\` 目录已有：

| 文件 | 命令 |
|------|------|
| `一键切换电视.vbs` | `DisplaySwitch.exe /external` |
| `一键切换电脑.vbs` | `DisplaySwitch.exe /internal` |

> 无需新建脚本，直接复用。

### 3.3 HASS.Agent 配置

> **什么是 HASS.Agent？** 一个 Windows 服务程序，通过 MQTT 连接 Home Assistant，让 HA 能远程执行 Windows 命令。安装后自动将配置的 Command 注册为 HA 实体。
>
> 下载：[HASS.Agent GitHub](https://github.com/LAB02-Research/HASS.Agent) | 安装在游戏 PC 上，需要配置 MQTT 连接到 HA。

#### 3.3.1 安装 HASS.Agent

1. 在**游戏 PC** 上下载 [HASS.Agent 最新版](https://github.com/LAB02-Research/HASS.Agent/releases)（`.exe` 安装包）
2. 双击安装，一路「下一步」即可
3. 安装完成后，桌面右下角托盘会出现 HASS.Agent 图标

#### 3.3.2 配置 MQTT 连接

HASS.Agent 通过 MQTT 和 HA 通信。需要 HA 端先有 MQTT broker。

<details>
<summary>🔧 如果你的 HA 还没有 MQTT：先装 Mosquitto Broker</summary>

在 HA 的「设置 → 加载项 → 加载项商店」搜索 `Mosquitto broker`，安装并启动。记下你设置的 MQTT 用户名/密码。
</details>

HASS.Agent 端配置：

1. 右键托盘图标 → **Configuration**
2. 左侧选 **MQTT Broker**
3. 填入：

| 字段 | 值 |
|------|-----|
| Broker IP | `192.168.197.253`（你的 HA 地址） |
| Port | `1883` |
| Username | 你的 MQTT 用户名 |
| Password | 你的 MQTT 密码 |

4. 点击 **Test Connection** → 显示绿色 ✅ 即成功
5. 点击 **Save**

#### 3.3.3 添加切屏 Command

1. 左侧选 **Commands** → 点击 **Add**
2. 创建第 1 个：

| 字段 | 值 |
|------|-----|
| Name | `SwitchToTV` |
| Command | `wscript.exe` |
| Arguments | `//B //nologo B:\DisplaySwitch\一键切换电视.vbs` |

3. 点击 **Add** 再创建第 2 个：

| 字段 | 值 |
|------|-----|
| Name | `SwitchToGame` |
| Command | `wscript.exe` |
| Arguments | `//B //nologo B:\DisplaySwitch\一键切换电脑.vbs` |

4. 点击 **Save**

> 💡 保存后稍等几秒，HA 的「开发者工具 → 实体」里搜索 `button.switchto` 就能看到 `button.switchtotv` 和 `button.switchtogame`。

#### 3.3.4 添加游戏输入 Command

> 此步骤依赖第四节 TypeGameText.exe，做完第四节再回来添加。

| 字段 | 值 |
|------|-----|
| Name | `TypeGameText` |
| Command | `B:\AutoHotkey\Scripts\TypeGameText.exe` |
| Arguments | `{text}` |

> HA 中会注册为 `script.typegametext` 实体。

### 3.6 HA Lovelace 卡片

在「**玉林品上**」视图中新增 Grid section，添加屏幕切换 entities 卡片：

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
B:\AutoHotkey\Scripts\
├── TypeGameText.ahk    ← AHK 源码
└── TypeGameText.exe    ← 编译后 exe（HASS.Agent 调用）
```

### 4.3 AutoHotkey 脚本

**`B:\AutoHotkey\Scripts\TypeGameText.ahk`**：

```autohotkey
#Requires AutoHotkey v2
#Warn All, Off

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
| `TypeGameText` | `B:\AutoHotkey\Scripts\TypeGameText.exe` | `{text}` |

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

#### 游戏输入（玉林品上视图）

在「**玉林品上**」视图中新增 Grid section：

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

快捷按钮 Grid（**方舟**视图）：

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

Step 8: 🚨 重建 ASA 视图（铁律 2）
  └── ssh root@host "python3 /config/build_lovelace.py"
  └── 用最新数据文件重建 ASA 视图，保留其他视图改动
  └── 无需重启 HA（build_lovelace 已同步 .storage）

Step 9: 重启 HA（仅当卡片结构变更时）
  └── 需 askQuestions 用户确认后执行
  └── ssh root@host "ha core restart"

Step 10: 浏览器自验证
  └── open_browser_page 打开 HA 实页
  └── 截图/读页确认新卡片已出现、布局无异常
```

### 5.2 视图分配

| 视图 | 新增内容 |
|------|----------|
| **玉林品上** | 屏幕切换卡片 + 游戏输入卡片（搜索文本 + 发送） |
| **方舟** (views[3]) | 一键搜索快捷按钮（聚合物/金属/霸王龙/风神翼龙） |

```
玉林品上视图                           方舟视图 (views[3])
───────────                           ─────────────────
sections[]                            sections[]
├── ... (现有)                        ├── [0] 部落运维速查入口
├── 🆕 屏幕切换 (entities)             ├── ... (现有)
│   ├── 📺 电视模式                    ├── [8] 操作日志
│   └── 🖥️ 显示器模式                  └── [9] ← 🆕 一键搜索 (Grid)
├── 🆕 游戏快捷输入 (entities)             ├── 📦 聚合物
│   ├── 搜索文本 (input_text)              ├── 🔩 金属
│   └── 📤 发送到游戏                      ├── 🦖 霸王龙
│                                         └── 🪶 风神翼龙
```

> 💡 屏幕切换和游戏输入放玉林品上（手机常用视图），快捷按钮放方舟（游戏专属视图）。

---

## 六、验证清单

| # | 验证项 | 方法 |
|---|--------|------|
| 1 | DisplaySwitch 切屏正常 | 手动运行 `B:\DisplaySwitch\DisplaySwitch.exe /external` 和 `/internal` |
| 2 | HASS.Agent 实体注册 | HA 开发者工具 → 实体 → 搜索 `button.switchto` |
| 3 | 屏幕切换按钮生效 | 手机点击 → 电视/显示器主屏切换 |
| 4 | TypeGameText.exe 可用 | 命令行 `TypeGameText.exe "测试"` → 焦点应用收到粘贴 |
| 5 | input_text.game_text 可输入 | HA 前端 → 方舟视图 → 输入框可见可用 |
| 6 | 发送脚本生效 | 输入文字 → 点击发送 → ARK 筛选框收到文字 |
| 7 | 快捷按钮生效 | 点击 📦 聚合物 → ARK 筛选框出现"聚合物" |
| 8 | Lovelace 本地与远程 MD5 一致 | 本地 MD5 vs SSH md5sum 验证 |
| 9 | 实页渲染正确 | 浏览器打开 HA 玉林品上 + 方舟实页截图确认 |

---

## 七、注意事项

1. **切屏已自动处理**：登录时由计划任务/SteamShell 自动切屏，HASS 按钮为远程手动备用。
2. **AutoHotkey 依赖前台焦点**：发送文本时，ARK 游戏窗口必须是前台焦点（筛选框已点击激活）。
3. **中文输入法**：ARK 筛选框需处于英文输入模式，否则 `^v` 可能粘贴到输入法候选框。
4. **HASS.Agent 必须在 Windows 游戏机上运行**（非 HA 服务器）。
5. **快捷按钮可按需扩展**：根据实际游戏搜索习惯添加更多常用词（水泥、火花 powder、铁锭等）。
6. **权限**：TypeGameText.exe 可能需要管理员权限才能向游戏窗口发送按键（取决于游戏的反作弊保护）。

---

## 八、涉及文件清单

| 文件 | 位置 | 操作 |
|------|------|------|
| `TV.bat` | — | ❌ 无需新建（复用 B:\DisplaySwitch\一键切换电视.vbs） |
| `GAME.bat` | — | ❌ 无需新建（复用 B:\DisplaySwitch\一键切换电脑.vbs） |
| `TypeGameText.ahk` | `B:\AutoHotkey\Scripts\` | 🆕 新建 |
| `TypeGameText.exe` | `B:\AutoHotkey\Scripts\` | 🆕 编译生成 |
| `configuration.yaml` | `/config/` (HA) | ✏️ 追加 input_text + scripts |
| `lovelace` | `A:\NetSarang\Xftp 8\Temporary\` | ✏️ 方舟视图追加 1 个 Grid + 玉林品上追加 2 个 Grid |
| `lovelace.lovelace` | `A:\NetSarang\Xftp 8\Temporary\` | 🔄 同步自 lovelace |

---

> 📝 **小白总结**：这个方案让手机变成 ARK 的"遥控器"——点一下切屏幕、输入文字直接发到游戏搜索框，不需要键盘鼠标。先装工具、写脚本、配 HASS.Agent，最后改 lovelace 加按钮就行。
