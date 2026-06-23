# 🔥 强制执行规则（每轮自动加载）

以下规则不依赖 skill 判断，每轮自动执行：

## 📋 Skill 与 Token 报告（每轮第一步，必须输出）
每轮回复开头，必须先读 `/memories/session/token-tracker.json` 更新累计 token，然后用以下格式输出报告：
> 📋 已加载：通用指令 | 智能体: ASA服务器监控 | 激活：进度追踪, Token审计 | Token: {当前K}/{上限K} (+{上轮K}) @{HH:MM}

**输出此报告即证明已完成读→算→写回全流程。** 不完成不得输出其他内容。
```
示例：📋 已加载：通用指令 | 智能体: ASA服务器监控 | 激活：进度追踪, Token审计 | Token: 95K/1000K (+2K) @14:30
```
- `{当前K}` = tracker.total ÷ 1000 取整（写回后）
- `{上轮K}` = (tracker.total - tracker.prevTotal) ÷ 1000 取整，即上一轮对话的实际消耗
- `@{HH:MM}` = tracker.lastUpdated 的时分（写回后），**未写回则此值不变 → 用户一眼识破**
- `{上限K}` = 模型上下文上限
- 写回时同步更新：`prevTotal = total`, `total = newTotal`, `lastUpdated`
- **`lastUpdated` 必须用 `+08:00` 时区（北京时间），格式 `2026-06-23T17:50:00+08:00`**
- **若 {上轮K} 计算为 0，必须重新估算，直到 >0 为止**

## 🤖 Token 追踪（与报告绑定执行，不依赖 skill）
> **Token 追踪不依赖 token-audit skill 是否激活。本段即为权威规则，每轮强制执行。**

1. 读 `/memories/session/token-tracker.json`
1. 读 `/memories/session/token-tracker.json`
2. 用户输入 + 本答案，各 `chars ÷ 2.5` 估算 token，累加
3. 写回，不输出给用户
4. `total >= criticalAt(800K)` → 🔴 强制警告；`total >= warnAt(600K)` → 🟡 警告
5. DeepSeek V4 Pro = 1M 上下文 / 384K 输出

## 🗣️ 复述+确认（动手前第二步）
任何任务/改动，**必须先**：
1. 复述理解
2. `#vscode/askQuestions` 确认
> 禁止跳过复述直接执行。

## 💾 改前必备份
修改任何文件前，先 `Copy-Item` 备份到 `www/`，命名 `*_backup_YYYYMMDD_HHMMSS.*`

## � 禁止直接修改 lovelace JSON
`/config/lovelace`、`/config/lovelace.lovelace`、`/homeassistant/.storage/lovelace.lovelace` 等 lovelace JSON 文件**禁止直接编辑**，除非用户明确要求。修改 lovelace 输出应通过 `build_lovelace.py` 源码进行。`build_lovelace.py` 明确豁免，不受此限。

## �📝 进度写盘（结论后最后一步）
顺序：结论 → 告知"接下来将写进度" → 写入 → 写完即止。复用同一文件。

## 💬 小白总结（每次最终报告末尾）
每次最终报告末尾，必须追加 1 句"小白解释"，用非术语语言说明当前现况与下一步。

## ⚠️ 安全审批（改前、执行前必须）
### 核心流程
1. 自动检测操作是否涉及系统操作
2. 风险分析（低/中/高/严重）
3. 低/中风险 → 自动执行并报告；高/严重 → `#vscode/askQuestions` 确认
4. 确认后二次校验参数再执行

### 审批状态机（硬约束）
- 高/严重风险动作须绑定唯一 `operationId`
- 用户选择取消 → 标记 `Denied`（终态），禁止执行
- 新动作必须新 `operationId`，禁止复用已拒绝的旧 ID
- 执行报告记录：operationId、用户选择、审批状态、结果

## 🗑️ 删除操作安全审计（强制）
> **任何删除操作（文件/目录/批量清理）执行前，必须调用 safety-approval skill 完成安全审计并提交报告。**

### 审计流程（不可跳过）
1. **触发条件**：任何 `Remove-Item`、`rm`、`del`、`rmdir`、robocopy `/MIR`（镜像覆盖）、清空目录等操作
2. **审计内容**（必须逐项报告）：
   - 删除目标清单（绝对路径 + 大小）
   - 备份状态（是否已有备份？位置？）
   - Git 状态（是否在版本控制中？`git status` 确认）
   - GitHub 风险（是否会导致仓库膨胀？是否有 `.gitignore` 覆盖？）
   - 依赖检查（其他文件/配置是否引用这些路径？）
3. **审计报告格式**：
   ```
   🗑️ 删除安全审计报告
   - operationId: <唯一ID>
   - 目标清单: <N> 项
   - 备份状态: ✅ 已备份 / ⚠️ 部分 / ❌ 无
   - Git 风险: 🟢/🟡/🔴
   - 依赖风险: 🟢/🟡/🔴
   - 结论: ✅ 可安全删除 / ⚠️ 需确认 / 🔴 禁止
   ```
4. **批准门槛**：🔴 禁止 → 立即停止；⚠️ 需确认 → `#vscode/askQuestions`；✅ 安全 → 可执行
