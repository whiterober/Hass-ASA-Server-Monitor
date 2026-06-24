# 🔥 强制执行规则（每回合自动加载）

> 📖 **名词表**：本文件及所有 `.github` 子文件的术语均对齐 `.github/glossary.md`。修改前先查表。

以下规则不依赖 skill 判断，每回合自动执行：

## 🗣️ 复述+确认（动手前第二步）
任何任务/改动，**必须先**：
1. 复述理解
2. #vscode/askQuestions 确认
> 禁止跳过复述直接执行。**askQuestions 后必须等待用户选择，不可自行结束回合。**

## 二选一确认（不可口头问完就结束回合）
任何需要用户决策或确认的问题（包括但不限于："要不要…""对吗？""确认…""可以吗…""行不行…""要我动手吗？""开始改吗？""执行吗？"等），**必须**调用 `#vscode/askQuestions` 弹出可点击选项。禁止纯文本提问后直接结束回合。

## 💾 改前必备份
修改任何文件前，先 Copy-Item 备份到 bak/，命名 *_backup_YYYYMMDD_HHMMSS.*

## 📝 进度写盘（结论后最后一步）
> 必须调用 `progress-tracking` skill 写入进度。具体流程见 `.github/skills/progress-tracking/SKILL.md`。

## 💬 小白总结（每次最终报告末尾）
每次最终报告末尾，必须追加 1 句小白解释，用非术语语言说明当前现况与下一步。

## 🔢 Token 审计（风险预测触发）
> 预测到大量 token 消耗风险时调用。禁止全文回读，3-6 行摘要。详见 `.github/skills/token-audit/SKILL.md`。


## � 脚本替换（大文件编辑优先）
> 编辑 >10KB 的文件时，优先用 `python .github/_replace.py <文件> '[{"o":"旧","n":"新"},...]'` 替代 `multi_replace_string_in_file`。脚本自动校验唯一性、备份、仅返回 `{"ok":N,"fail":N}`，体积压缩 99%+。替换后仍需检查空行规范。

## �📄 HTML 空行规范
> `www/asa-admin.html` 禁止连续空行（`\n{3,}`）。编辑后检查：`python -c "import re;c=open('www/asa-admin.html').read();print(len(re.findall(r'\n{3,}',c)))"` → 必须为 0。

## ⚠️ 安全审批（改前、执行前必须）
> 自动检测风险等级，高/严重需 `#vscode/askQuestions` 确认。详细流程见 `.github/skills/safety-approval/SKILL.md`。

## 🗑️ 删除操作安全审计（强制）
> **任何删除操作执行前，必须调用 `safety-approval` skill 完成安全审计。** 具体审计流程、报告格式、批准门槛详见 `.github/skills/safety-approval/SKILL.md`。