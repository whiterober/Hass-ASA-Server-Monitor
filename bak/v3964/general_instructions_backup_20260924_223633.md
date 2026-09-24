---
name: General Rules
description: 通用强制执行规则：复述确认、改前备份、进度写盘、安全审批、Token 审计等
applyTo: '**'
---

# 🔥 强制执行规则

> 📖 **名词表**：本文件及所有规则的术语均对齐 `%USERPROFILE%\.copilot\tools\glossary.md`。修改前先查表。

以下规则不依赖 skill 判断，每回合自动执行：

## 🛑 复述+确认（动手前第一步，最高优先级）
> ⚠️ **本规则优先级最高，覆盖所有其他规则。任何情况下不得跳过。**

**用户任何需求/任务/改动请求，必须严格执行以下三步，缺一不可：**

### 第 1 步：复述理解（必须先输出）
用自己的话向用户复述：你要做什么、改什么、预期结果是什么。
**禁止在此步骤调用任何修改类工具（写入/删除/执行/部署）。**
**禁止复述末尾带问号/问句（如"是这样吗？""对吗？""可以吗？"等），复述必须是陈述句。**
> 格式示例：「我理解你的需求是：<复述内容>。」（句号结尾，陈述句）

### 第 2 步：弹窗确认（必须用 askQuestions，与第 1 步在同一回合完成）
调用 `#vscode/askQuestions` 弹出可点击选项，至少包含「✅ 确认执行」和「❌ 取消」两个选项。
> **复述和 askQuestions 必须同回合连续完成，禁止复述完就结束回合等用户回应。**
> **askQuestions 后必须等待用户选择，不可自行结束回合、不可跳过等待直接执行。**
> **任何确认性问题（复述确认、方案确认、参数确认等）一律用 askQuestions，禁止以纯文本"对吗？""可以吗？""是这样吗？"等方式提问。**


### 第 3 步：收到确认后才可动手
用户点击「✅ 确认执行」后方可开始实际修改/执行操作。

### 🚫 严禁行为
- 跳过复述直接执行任何操作
- 复述后不弹窗，口头问一句就结束回合
- 复述后直接动手不等用户确认
- **输出复述后直接结束回合（未调用 askQuestions）**
- 把"那我开始改了"当作确认信号
- 用户说"对"/"好"/"行"等口头确认后不弹 askQuestions 直接执行
- **复述末尾带问号（?）或疑问语气词（"对吗""是吧""可以吗"等）**

## 二选一确认（不可口头问完就结束回合）
任何需要用户决策或确认的问题（包括但不限于："要不要…""对吗？""确认…""可以吗…""行不行…""要我动手吗？""开始改吗？""执行吗？"等），**必须**调用 `#vscode/askQuestions` 弹出可点击选项。禁止纯文本提问后直接结束回合。

## 🔘 执行邀请确认（禁止口头问"要我执行吗？"）
凡以"要我执行吗？""要我开始吗？""需要我…吗？"等句式结束回合，**必须替换为 askQuestions 弹窗**，选项至少包含「✅ 确认执行」和「❌ 取消」。禁止"口头邀请→结束回合→等下轮回应"。

## ⏳ 等待/延迟确认（等待类操作必须 askQuestions）
凡涉及"等待启动完成""等待编译""等待部署"等需用户被动等待的操作，**执行前必须 askQuestions 确认**。禁止自行决定等待后不弹窗直接执行。

## 🚨 异常中断确认（禁止强行重试）
推理、验证、部署等过程中发生未预期事件（SSH 连不上、页面打不开、API 超时、文件缺失、权限不足等），**禁止自行重试**。必须立即停止，调用 `#vscode/askQuestions` 报告异常 + 给出选项，等待用户决策。
## 🔄 重试上限（同一操作最多 2 次）
任何自动化操作（SSH 连接、API 调用、文件读写、页面操作等），同一操作最多重试 **2 次**。2 次后仍未成功，必须停止，调用 `#vscode/askQuestions` 报告失败原因 + 给出选项，等待用户决策。禁止无限重试。
## 🔴 SSH 命令构造规范（禁止 PowerShell heredoc）
> PowerShell 中 SSH heredoc（`<<EOF` / `<<'EOF'`）引号转义极易爆炸，三层嵌套几乎必败。

- **禁止**在任何 `run_in_terminal` SSH 命令中使用 heredoc 多行字符串
- **强制**：多行脚本内容一律先 SFTP 上传到远程 `/tmp/`，再 `ssh root@host "python3 /tmp/script.py"` 执行
- 单行命令可用 `-c` 直接传参，但代码 >5 行必须走 SFTP
- 首次 heredoc 失败后**禁止重试**，立即切换 SFTP 路线
## 🔴 SSH 脚本嵌入禁令（>5 行必须 SFTP）
> 大段 Python/Shell 代码直接嵌入 `paramiko` 或 `run_in_terminal` SSH 命令行，每条语句都产生转义开销，且错误输出充满终端、token 消耗线性增长。

- **阈值**：代码内容 >5 行或 >200 字符 → 必须 SFTP 写入临时文件再远程执行
- 正确流程：`SFTP put → ssh exec python3 /tmp/_xxx.py → ssh rm /tmp/_xxx.py`
- 禁止在 `exec_command()` 参数中拼接完整脚本源码
## 🔧 Maven Wrapper 短命令规避
> Maven Wrapper 3.6.x 不识别 `spring-boot:run` 短前缀，必须使用完整坐标：`org.springframework.boot:spring-boot-maven-plugin:<版本>:run`。Spring Boot 2.3.x 版本号为 `2.3.12.RELEASE`。
## 🔧 工具新增确认（禁止降级凑合）
推理、验证、部署等过程中，若判断当前任务**用新工具明显优于现有工具**（如现有工具只能拐弯抹角模拟、降级凑合），**禁止硬用旧工具替代**。必须调用 `#vscode/askQuestions` 说明新工具的必要性 + 给出选项，用户同意后方可勾选新工具并执行。
## 🔍 推理方法改进上报（A失败→B成功后强制）
推理过程中，若先用方法 A 无效（或效果差），改用方法 B 后成功，**成功后必须**调用 `#vscode/askQuestions`：
1. 简述 A 为何失败、B 为何成功
2. 给出选项：是否将 B 方法写入指令/规则文件固化

> 目的：避免下次重复踩坑，将有效方法沉淀为智能体知识。

## 🔍 终端并发限制（强制）
> `run_in_terminal` 同时最多存在 **2 个**终端。超过 2 个时必须先等待现有命令完成或 kill 旧终端后再新建。禁止同时开 3 个或以上终端。
> **async 命令完成后必须调用 `kill_terminal` 清理**，失效终端不可残留。新建终端前先检查现有终端数，>=2 时先杀旧再开新。

## 🔍 终端开新关旧方案（2026-08-18 实测固化）
> **实测结论**：
> - `run_in_terminal` **sync 模式自动复用同一终端**（进程数恒定，命令正常执行，不累积新进程）→ **默认优先用 sync**，无需每次开新终端。
> - `run_in_terminal` **async 模式创建独立终端**，返回 terminal ID，用 `kill_terminal <id>` 可成功清理（已验证 kill 闭环有效）。
> - VS Code 集成终端进程（powershell/pwsh）常驻属正常现象，非 run_in_terminal 累积，勿误判。
> **标准操作流（固化）**：
> 1. 一次性命令（构建/测试/脚本）→ 一律 `run_in_terminal` **sync 模式**，自动复用终端。
> 2. 仅长驻进程（服务器/watcher/daemon）→ async 模式，记下 terminal ID。
> 3. 长驻进程结束后 → **立即 `kill_terminal <id>` 清理**，不留失效终端。
> 4. 需要与旧终端隔离时 → 先 `kill_terminal <旧id>`，再开新 async 终端。
> 5. 报 `No active terminal execution found` 的旧 ID → 直接忽略（已自动回收），无需重试。

## 🔍 终端 ^U/拼接污染根因与根治（2026-08-18 实测固化）
> **症状**：`run_in_terminal` 长输出命令（构建/打包）后，下一条命令被拼接污染，如 `Format-ListmGet-Item`（上一条命令尾部 + 本条命令粘连）或 `Write-Output 无法识别`；偶发无输出。
> **根因（已确认）**：长输出命令（cmake 构建数百行 / Write-Host）未完全消费，**终端缓冲区残留控制序列/残字节混入下一条命令** → 命令拼接解析失败。非持久性，短命令正常。
> **根治方案（固化，不可绕路）**：
> 1. **短命令**（<50 行输出）→ 直接 `run_in_terminal` sync，正常。
> 2. **长输出命令**（构建/打包/测试）→ **重定向到文件**：`cmd /c "... > tmp\build_out.txt 2>&1"` 或 powershell `*> tmp\out.txt`，避免缓冲残留。
> 3. **关键状态检查**（dll 产物 / RCON 结果 / 文件存在）→ **一律 Python 脚本写文件 + `read_file` 读取**，绕开终端输出被吞。
> 4. 需要交互或长驻 → **async 模式 + `send_to_terminal`**（已验证不注入 ^U）。
> 5. 污染一旦出现 → **不重试同一命令**，改用 Python 写文件方案验证结果。
> ⚠️ 主终端偶发 `cmdlet 无法识别`（Write-Output / Get-ChildItem 报 ObjectNotFound）→ 改用 `C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe -NoProfile -Command "..."` 子进程执行。
> 🆕 **终端命令标准前置（2026-08-26 修订固化：clear 已弃用 → 直接重置终端）**：
> 1. **每回合所有 `run_in_terminal` 命令前，一律先 `run_vscode_command` 执行 `workbench.action.terminal.kill`**（直接重置终端 = 标准前置动作；run_in_terminal 下次自动新建干净会话，消除 ^U/残字节残留；`terminal.clear` 已弃用）
> 2. **统一用 `python`（PATH 版）执行脚本文件**，关键结果一律脚本写文件 + `read_file` 读取（绕开终端输出被吞/中文乱码）
> 3. **`cmd /c` 中文路径不可靠（多次实测失败）→ 标记弃用**，禁止用于中文路径命令；改用 `python '脚本路径'` 或 `python -c "..."`（PATH 版，经 python 自身解析中文路径）
> 4. **终端污染恢复优先级（2026-08-26 修订固化，新建终端作为最后手段）**：主终端被 `^U` 严重污染（连 `powershell.exe` 路径、`Get-Content` 都不识别）时，**按以下顺序恢复，禁止一开始就新建终端**：
> 5. **首选** `run_vscode_command` 执行 `workbench.action.terminal.kill`（直接重置终端，run_in_terminal 下次自动新建干净会话）→ 实测有效（Python 3.12.5 恢复）
> 6. **次选** `python`（PATH 版）直接执行脚本（`python '脚本路径'` 或 `python -c "..."`，经 python 解析中文路径，绕开 PS 解析器）→ 实测可靠
> 7. 仍异常 → `C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe -NoProfile -Command "..."` 子进程包装
> 8. **最后手段**（以上全部无效）→ 才 `run_vscode_command` 执行 `workbench.action.terminal.new`（新建干净终端）+ `terminal.focus`，然后 `run_in_terminal` 执行
> 9. 新建终端后若 `C:\Python312\python.exe` 不识别 → 用 `python`（PATH 版）或 `where.exe python` 找路径
> ⚠️ `run_vscode_command` 是 VS Code 命令接口（commandId），不是 shell 执行器——它负责清空/开聚焦终端，实际命令仍由 `run_in_terminal` 发。

## 🔍 新建干净终端未识别 Python 路径（2026-08-18 实测固化）
> **症状**：按「终端污染恢复优先级」最后手段新建+聚焦干净终端后，`run_in_terminal` 执行 `C:\Python312\python.exe ...` 报 `无法将"..."项识别为 cmdlet`，但 `python` 命令可用。
> **根因（已确认）**：新终端（workbench.action.terminal.new）不继承主终端的 PATH 解析环境，直接写 `C:\Python312\python.exe` 绝对路径可能解析失败；`python`（where 指向同一 exe）反而可用。
> **根治方案（固化）**：
> 1. 新建干净终端后，**优先用 `python` 命令**（实测 `python --version` → Python 3.12.5，`where.exe python` 确认指向 `C:\Python312\python.exe`）。
> 2. 若 `python` 也不识别 → 先 `where.exe python` 找可用路径，再改用该路径。
> 3. 仍异常 → 命令前加 `C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe -NoProfile -Command "..."` 子进程包装。
> 4. 判断标准：新终端首条命令先 `python --version` 验证，成功后再执行实际脚本。

## 🔍 终端环境不一致根治：统一子进程包装（2026-08-18 实测固化，强制）
> **症状**：同一命令有时成功、下次报 `无法识别`（`C:\Python312\python.exe` / `python` 随机失效）；命令"无输出"但脚本实际执行成功（结果文件已写好）。
> **根因（已确认）**：`run_in_terminal` **不在固定终端执行**，在多个终端间切换，不同终端 PATH 解析环境不同（A 终端有 `python`、B 终端识别绝对路径）。已有规则（新建干净终端、新终端用 python）只覆盖单一终端场景，无法应对终端切换。
> **根治方案（固化，不可绕路）**：
> 1. **所有 Python/命令一律 PowerShell 子进程包装**，不依赖 run_in_terminal 的终端环境：
>    `C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe -NoProfile -Command "C:\Python312\python.exe 'b:\项目\...\tmp\_xxx.py'"`
>    （外层双引号 + 内部单引号包裹脚本路径，路径含中文安全；仅限单行无复杂引号命令）
> 2. 命令内**禁止多层引号嵌套**（见「嵌套引号根除」）；含复杂引号/多行代码 → 先写脚本文件 `tmp/_xxx.py`，再子进程包装执行。
> 3. 关键结果**一律脚本写文件 + `read_file` 读取**（绕开输出被吞/中文乱码）。
> 4. 子进程包装仍报"无法识别" → 改 `python`（PATH 版）再试；最多重试 2 次，仍失败停止报告（不无限重试）。

## 🔍 嵌套引号根除（2026-08-18 实测固化，强制）
> **症状**：`powershell.exe -NoProfile -Command "C:\Python312\python.exe -c \"...\""` 多层嵌套时，PowerShell 解析器层层剥引号，Python 代码含中文路径/单双引号/转义必报 `ParserError`（如 `参数列表中缺少参量`、`意外的属性`、`表达式或语句中包含意外的标记`）。
> **根因**：三层引号嵌套（PS 外层 `"` + python -c 的 `"` + 代码内引号）在 PowerShell 5.1 下必然爆炸，每层转义都产生解析歧义。
> **根治方案（固化，不可绕路）**：
> 1. **禁止** `powershell -Command "python -c \"...\""` 内联嵌套。任何 Python 代码 >1 行或含引号/中文 → **必须写脚本文件**（`tmp/_xxx.py`）+ `run_in_terminal` 执行 `python '脚本路径'`。
> 2. **脚本文件 + 写文件读结果**：脚本内 `io.open(...).write(...)` 结果到 `tmp/_out.txt`，再用 `read_file` 读取——绕开终端输出被吞 + 中文乱码。
> 3. 需要参数（如摘要文本、JSON）→ 脚本内直接写常量或从文件读，**不通过命令行参数传**（避免引号转义）。
> 4. 单行无引号命令可直接执行；含中文路径的脚本路径用**单引号**包裹：`python 'b:\项目\...\tmp\_xxx.py'`。
> 5. 一次性脚本用完即删（`Remove-Item tmp\_xxx.py`），不留残留。
> ⚠️ 判断标准：命令中出现 `\"` 或 `\\` 或 `python -c` 且代码含中文/引号 → 立即改脚本文件方案，禁止硬凑。

## 🔍 Python REPL 卡终端（2026-08-26 实测固化，强制）
> **症状**：`run_in_terminal` 返回 `>>> ` / `>>`（Python 交互提示符），命令被回显但不执行；`Write-Output`、`python --version`、`exit()` 全被吞掉。
> **根因链**：终端 ^U/残字节污染 → `python '脚本'` 命令参数丢失/路径截断，真正落到终端的只剩裸 `python`（stdin 为 TTY）→ 进入 Python 交互 REPL 持有终端 → 后续所有命令被当 Python 代码接收（报 SyntaxError 后继续 `>>> ` 等待），`exit()` 也常因通道污染失效。
> **诊断**：`>>> ` 是 Python REPL 提示符（不是 PowerShell 提示符）；界面其他终端正常 ≠ 工具连接的持久会话正常。
> **恢复流程（先重置主终端，禁止放着不管 / 禁止直接新建终端绕路）**：
> 1. **直接 `workbench.action.terminal.kill`** 重置主终端（2026-08-26 实测：run_in_terminal 下次自动新建干净会话，`python --version` 恢复正常）——首选有效手段，不再先试 clear
> 3. 探测 `python --version` 确认恢复
> 4. 重置无效（极端）→ 才用 `run_in_terminal` **async 模式**独立干净终端（拿 terminal ID）→ `send_to_terminal` 发命令（绕 ^U）→ 完成后 `kill_terminal <id>` 清理
> **预防**：命令前一律直接重置终端（`workbench.action.terminal.kill`）；python 调用必带脚本路径（禁止裸 `python` 无参数）；主终端异常优先重置（kill）而非换新终端。

## 🔍 改前必备份
修改任何文件前，先 Copy-Item 备份到 bak/，命名 *_backup_YYYYMMDD_HHMMSS.*

## 🔍 生成器输出编码固化（Python 包装写 UTF-8，2026-09-24 实测固化，强制）
> **症状**：`python 脚本 *> out.txt`（PowerShell 重定向）产出文件为 **UTF-16LE**，`read_file` 读到乱码/binary，无法核对生成器输出（v3905–v3913 反复踩坑）。
> **根因**：PowerShell 5.1 的 `>` / `*>` 重定向默认按 UTF-16LE 写入（Out-File 默认 Unicode），与 UTF-8 读取不匹配。
> **根治（固化，不可绕路）**：凡需把脚本 stdout/stderr 落盘供核对 → **一律用 Python 包装**，禁止 PowerShell `*>` 重定向：
> ```python
> ENV = dict(os.environ, PYTHONIOENCODING='utf-8')
> r = subprocess.run([sys.executable, SCRIPT], capture_output=True, cwd=WORKDIR, env=ENV)
> txt = (r.stdout or b'').decode('utf-8', 'replace') + u'\n--- STDERR ---\n' + (r.stderr or b'').decode('utf-8', 'replace')
> io.open(OUT, 'w', encoding='utf-8', newline='').write(txt)
> ```
> - 子进程必须带 `env=PYTHONIOENCODING=utf-8`（否则子脚本自身 print 中文会因 GBK 崩溃/乱码）
> - 已封装样例：`b:\项目\Hass ASA Server Monitor\tmp\_v3915_gen.py`
> - 判断标准：命令中出现 `*>` 或 `>` 且目标是 txt → 立即改 Python 包装

## 📁 临时产物规范
临时产物（`_tmp*`）不要放在项目根目录，统一放到项目临时子目录（如 `tmp/`）。

## 📝 进度写盘（结论后最后一步）
> 必须调用 `progress-tracking` skill 写入进度。详见相关 skill 文档。

## 💬 小白总结（每次最终报告末尾）
每次最终报告末尾，必须追加 1 句小白解释，用非术语语言说明当前现况与下一步。

## ✅ 计划任务自动勾选（每回合结束时校验）
> 每回合结束写入进度后，检查当前活跃开发计划中本回合已完成的任务步骤，将对应复选框从 `- [ ]` 自动改为 `- [x]`。
> **判断依据**：本回合实际创建/修改的文件是否匹配计划中步骤的 📁 涉及文件。若完全匹配则自动勾选，若不确定则跳过（不猜）。
> **操作方式**：使用 `multi_replace_string_in_file` 精确替换对应行（需包含足够上下文确保唯一匹配）。
> **仅勾选**：不修改计划文件的其他任何内容，不新增步骤，不调整顺序。

## 🚫 连续执行铁律（仅用户明确「全量连续/不要停」时启用，2026-09-08 固化）
> **适用范围**：本规则仅在用户明确下达「全量实施/不要停/一口气做到完成/迭代到完成」类指令时强制；普通回合（无此指令）不受限，可正常结束回合。
> 来源：dino-import 全量实施 v877→v882 时，用户反复要求"不要停/一口气做到完成"，我却在 async 部署等待处结束回合，每步都停、反复被质问。

- **触发条件成立时：任务全部收尾（逐项部署、验证、进度写盘、结算）之前，禁止主动结束回合。**
- async 部署/长任务等待期间：禁止"结束回合等自动通知"；改为回合内持续推进（`get_terminal_output` 查进度 / 读码 / 改下一处 / 准备验证）。"async 完成自动通知勿轮询"规范在用户连续执行指令下降级。
- 能合并的部署尽量合并（一次部署承载多版本/多功能），减少等待点。
- **每回合结束前自检**：是否存在用户要求但未完成的步骤？有则**不结束回合**，继续执行。
- 被用户质问"又停了"：立即自查剩余步骤并连续执行，禁止再次口头保证后仍停在等待点。

## �🔢 Token 审计（风险预测触发）
> 预测到大量 token 消耗风险时调用。禁止全文回读，3-6 行摘要。详见 `token-audit` skill。

## 🔍 DeepSeek Token 日志定位（_token_report.py 数据源）
> `_token_report.py` 真实数据源是扩展 `Vizards.deepseek-v4-for-copilot` 写入的 `DeepSeek.log`，路径：`%APPDATA%\Code\logs\<时间戳>\window*\exthost\Vizards.deepseek-v4-for-copilot\DeepSeek.log`。不是 Copilot Chat 的 `main.jsonl`（2026-07-15 曾误判，导致脚本失效）。
> 行格式：`[cache-trace #N] ... roles(user=M,assistant=..,tool=..,system=..)` 与 `tokens #N: model=deepseek-v4-pro prompt=P completion=C | cache: hit=H miss=M rate=R% | chars/tok=X`；旧正则仍兼容。修改 `discover_log()` 时只按最新 mtime 定位 `DeepSeek.log`，勿再选 main.jsonl。

## 🔍 Token 报告无输出根因（PYTHONIOENCODING=utf-8，2026-08-18 固化）
> **症状**：终端执行 `python c:\Users\white\.copilot\tools\_token_report.py end` 无任何输出（含 `*>` 重定向到文件也为空）。
> **根因**：脚本 print 含 emoji（📋/💰），Windows 终端默认 GBK(cp936) 编码，Python stdout 抛 `UnicodeEncodeError: 'gbk' codec can't encode character '\U0001f4cb'`，进程崩溃于打印前，故无输出、state 文件也不更新。
> **正确姿势（固化）**：运行前必须设 `$env:PYTHONIOENCODING='utf-8'`：
> ```powershell
> $env:PYTHONIOENCODING='utf-8'; C:\Python312\python.exe c:\Users\white\.copilot\tools\_token_report.py end
> ```
> 或重定向到文件用 UTF-8 读取：`cmd /c "set PYTHONIOENCODING=utf-8&& C:\Python312\python.exe c:\Users\white\.copilot\tools\_token_report.py end > tmp\out.txt 2>&1"`。
> **验证成功标志**：`_token_state.json` 中 `last_reported` 单调递增（如 77→88→98），`user=N` 即结算监控的回合号 N。
> ⚠️ 遇到无输出先查 `UnicodeEncodeError` / 终端编码，勿反复重跑同一命令。

## 脚本替换（大文件编辑优先）
> 编辑 >10KB 的文件时，优先用 `python %USERPROFILE%\.copilot\tools\_replace.py <文件> '[{"o":"旧","n":"新"},...]'` 替代 `multi_replace_string_in_file`。脚本自动校验唯一性、备份、仅返回 `{"ok":N,"fail":N}`，体积压缩 99%+。替换后仍需检查空行规范。

## 📄 HTML 空行规范
> HTML 文件禁止连续空行（`\n{3,}`）。编辑后检查：`python -c "import re;c=open('目标.html').read();print(len(re.findall(r'\n{3,}',c)))"` → 必须为 0。

## 📦 文件迁移规范
迁移后工作区文件需放在项目根目录可见位置，不要仅保留在 dev 等子目录中。

## ⚠️ 安全审批（改前、执行前必须）
> 自动检测风险等级，高/严重需 `#vscode/askQuestions` 确认。详细流程见 `safety-approval` skill。

## 🗑️ 删除操作安全审计（强制）
> **任何删除操作执行前，必须调用 `safety-approval` skill 完成安全审计。** 具体审计流程、报告格式、批准门槛详见 `safety-approval` skill。

## 📱 小程序自动化测试前置检查（强制）
> 每次小程序 MCP 测试前，必须先验证数据是否成功加载。若页面无数据、API 无响应或出现"登录态失效"等错误，**必须先确认微信开发者工具中已勾选以下选项**：
> - ✅ 不校验合法域名、web-view（业务域名）、TLS 版本以及 HTTPS 证书
> 未经此确认不可断言"测试通过"。

## 👻 MCP 原生弹窗不可见规则
> 微信小程序原生弹窗（`wx.showModal`、`wx.showToast`、`wx.showLoading` 等）在 webview 外渲染，MCP 的 `mp_screenshot` 和 `page_getElements` **均无法捕获**。
> - **禁止**仅凭 `getData` + `getLogs` 为空就断言"无错误"
> - 用户口头反馈的弹窗内容即为真实错误，直接采信
> - 诊断优先用 `mp_getLogs`（不清空）读控制台 + `mp_callWx` 直连后端 API 验证


## 🔍 异步构建 UI：禁止「一次查不到元素」即断言「元素不存在」（2026-09-24 v3938 固化）
> **症状**：验证 dino-import 浮窗时，调用打开函数后**立即** `getElementById('lbPubFacGrid')` 得 null ⇒ 误判「元素根本不在 DOM」→ 差点改错方向（去改浮窗构建位置）。
> **根因**：浮窗构建是**异步**的（`Promise.all([...]).then(...)` 构建 DOM + 120ms `setTimeout` 后才跑布局/空白清理），此刻元素尚未建出。
> **正确姿势（固化）**：
> 1. 断言前先确认**构建完成**：查父容器（如 `.lb-picker-overlay`）的 `querySelectorAll('[id]')` 里是否已有目标 id，或直接等一次 DOM 变更后再读。
> 2. 「元素缺失」这类否定结论**必须二次确认**（换时机/换入口/查源码拼接处），禁止单次判空即下结论。
> 3. 「查不到」优先怀疑**时机**，其次才是「代码没跑到」。
> 4. 渲染类函数遵循「**谁渲染谁复原**」：填充内容后必须自行恢复自身 `display`（`g.style.display=''; g.removeAttribute('data-blank-hide')`），不能依赖「别人会管」的清理逻辑（dino-import 的 `lbPickerHideBlankZones()` 对已隐藏元素直接跳过 ⇒ 块永久隐藏、只剩标题）。
