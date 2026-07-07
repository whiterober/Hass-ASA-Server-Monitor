基于你的现状：

- ✅ Win11 游戏专用账号
- ✅ Steam Shell 已基本完成
- ✅ HASS 已部署
- ✅ 只需要：
    - 手机切换电视/显示器
    - 手机输入文本直接进入游戏筛选框（无需 Ctrl+V）

我建议最终方案如下。

---

# 架构图

Home Assistant

        │

        ▼

    HASS.Agent

        │

┌──────┴──────┐

▼             ▼

  

切屏         游戏输入

  

▼             ▼

  

MultiMonitorTool

             AutoHotkey

  

▼             ▼

  

电视/显示器    当前焦点输入框

---

# 第一部分：HASS 切屏

## 目录结构

C:\Tools\MultiMonitorTool

│

├─ MultiMonitorTool.exe

├─ TV.cfg

├─ WORK.cfg

---

## 创建配置

### 游戏模式

调整：

电视 = 主屏

显示器 = 副屏

执行：

MultiMonitorTool.exe /SaveConfig TV.cfg

---

### 办公模式

调整：

显示器 = 主屏

电视 = 副屏

执行：

MultiMonitorTool.exe /SaveConfig WORK.cfg

---

## 创建脚本

### TV.bat

@echo off

  

C:\Tools\MultiMonitorTool\MultiMonitorTool.exe /LoadConfig C:\Tools\MultiMonitorTool\TV.cfg

---

### WORK.bat

@echo off

  

C:\Tools\MultiMonitorTool\MultiMonitorTool.exe /LoadConfig C:\Tools\MultiMonitorTool\WORK.cfg

``

---

## HASS.Agent

创建 Command：

### 命令1

名称:

SwitchToTV

程序:

C:\Scripts\TV.bat

---

### 命令2

名称:

SwitchToWork

程序:

C:\Scripts\WORK.bat

---

## HA Dashboard

type: entities

entities:

  - entity: button.switchtotv

    name: 🎮 游戏模式

  

  - entity: button.switchtowork

    name: 💼 办公模式

效果：

手机点一下

↓

电视切主屏

  

再点一下

↓

显示器切主屏

---

# 第二部分：手机输入文字直接进入游戏

这个方案比剪贴板更适合你。

---

## 安装 AutoHotkey v2

下载：

[https://www.autohotkey.com/](https://www.autohotkey.com/)

---

## 创建脚本

路径：

C:\Scripts\TypeGameText.ahk

内容：

#Requires AutoHotkey v2

  

if A_Args.Length > 0

{

    text := A_Args[1]

  

    A_Clipboard := text

  

    Sleep 100

  

    Send("^v")

}

---

## 编译

右键：

Compile Script

``

生成：

TypeGameText.exe

``

---

# HASS.Agent 配置

新增 Command：

名称：

TypeGameText

程序：

C:\Scripts\TypeGameText.exe

参数：

{text}

---

# Home Assistant

创建输入框：

input_text:

  game_text:

    name: 游戏输入

    max: 200

---

创建脚本：

script:

  send_to_game:

    alias: 发送到游戏

    sequence:

      - service: hass_agent.command

        data:

          command: TypeGameText

          arguments:

            text: "{{ states('input_text.game_text') }}"

---

# Dashboard

type: entities

entities:

  - input_text.game_text

  - script.send_to_game

显示：

┌────────────┐

│ 游戏输入   │

├────────────┤

│ 聚合物     │

└────────────┘

  

[发送]

---

# 实际使用

ARK：

打开箱子

↓

点击筛选框

↓

焦点停留在搜索框

手机：

输入

  

聚合物

点击：

发送

结果：

ARK筛选框

↓

自动出现

  

聚合物

无需：

Ctrl+V

无需键盘。

无需鼠标。

---

# 推荐再加两个快捷按钮

script:

  search_polymer:

    alias: 聚合物

  

  search_metal:

    alias: 金属

执行对应：

TypeGameText.exe "聚合物"

TypeGameText.exe "金属"

以后直接点：

📦 聚合物

🔩 金属

🦖 霸王龙

🪶 风神翼龙

比输入还快。

---

# 最终效果

你的客厅系统会变成：

扫脸

↓

Steam Shell

↓

Gamepad UI

↓

ARK

  

手机面板:

  

🎮 游戏模式

💼 办公模式

  

📝 文本输入框

📤 发送

  

📦 聚合物

🔩 金属

🦖 霸王龙

整个过程中完全不需要键盘、鼠标，也不需要手动 Ctrl+V。