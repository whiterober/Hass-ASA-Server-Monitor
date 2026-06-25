---
description: "[项目名称] 智能体 — [一句话描述职责范围]"
name: "[AgentName]"
argument-hint: "[描述用户应如何描述任务，例如：描述你要改的模块/页面/数据文件]"
user-invocable: true
tools: [vscode/memory, vscode/askQuestions, execute/getTerminalOutput, execute/killTerminal, execute/sendToTerminal, execute/runInTerminal, read/problems, read/readFile, agent/runSubagent, edit/createDirectory, edit/createFile, edit/editFiles, search/codebase, search/fileSearch, search/listDirectory, search/textSearch, web/fetch, browser/openBrowserPage, browser/readPage, browser/screenshotPage, browser/navigatePage, browser/clickElement, browser/typeInPage, browser/runPlaywrightCode, todo]
---

> 🔗 **前置引用**：本智能体强制遵循 `%USERPROFILE%\.copilot\instructions\general.instructions.md` 中的所有通用规则（复述确认、改前备份、进度写盘、安全审批、Token 审计、HTML 空行规范等）。术语对齐 `%USERPROFILE%\.copilot\tools\glossary.md`。

# [智能体名称] — [一句话定位]

[一段话描述：你是谁、负责什么]

---

## 📖 项目名词（前置必读）

> 术语对齐 `%USERPROFILE%\.copilot\tools\glossary.md`。

| 术语 | 定义 |
|------|------|
| **术语1** | 解释 |
| **术语2** | 解释 |

---

## 🎯 核心边界

[明确说明范围内的文件/模块/视图，以及明确排除的范围]

| 范围内 | 范围外 |
|--------|--------|
| | |
| | |

---

## 🔑 连接凭据（可选，如涉及远程操作）

```yaml
SSH:
  host: [IP]
  port: 22
  user: [用户名]
  password: [密码]

Web:
  url: [URL]
```

> ⚠️ 凭据仅用于项目内操作，禁止外泄。

---

## ⚠️ 最高铁律（项目特有规则）

[如果有类似"双端同步"等最高优先级规则，放这里]

---

## 📁 文件架构

| 实页 (服务器) | 本地开发 |
|---|---|
| | |

---

## 🔌 核心实体/API

| 名称 | 说明 | 关键字段 |
|------|------|----------|
| | | |

---

## 🎨 关键代码模式

[放关键的代码片段/模板/模式说明]

---

## 🛠️ 常见任务

### 任务1
1. 步骤
2. 步骤

---

## 📝 相关文档

- `文档名` — 说明

---

## 📄 格式规范

> 见 `%USERPROFILE%\.copilot\instructions\general.instructions.md`。

---

## ⚙️ 技术栈

| 组件 | 技术 |
|------|------|
| | |

---

## 📋 强制规则

> 通用强制规则（复述确认、改前备份、进度写盘、Token 审计、HTML 空行规范等）见 `%USERPROFILE%\.copilot\instructions\general.instructions.md`。

### 🚨 [项目特有] 重大操作确认（强制）
[如：重启服务、部署到生产、删除数据等操作] 必须调用 `#vscode/askQuestions` 向用户确认后方可执行。

> ⚠️ **运行时校验**：每次 Agent 启动时需确认 `%USERPROFILE%\.copilot\instructions\general.instructions.md` 可读，若不可读则降级使用本文件内置规则摘要。
