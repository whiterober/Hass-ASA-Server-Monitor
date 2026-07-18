# ASA JSON 配置文件修改铁律（2026-07-18 固化）

> 教训来源：直接服务器写 `server_rules.json` 多次失败，文件被未知进程还原。

## 铁律：绝不允许服务器端 Python 写 JSON 数据文件

- **禁止**：在服务器上执行 `json.dump()` 写入 `/config/www/asa-data/*.json`
- **原因**：文件可能在秒级内被 HA 进程或缓存机制还原
- **唯一可靠方式**：本地修改 → SFTP put 直接覆盖

## 强制流程（8 步，不可跳步）

1. **拉取** — `sftp.get(服务器路径, 本地路径)`
2. **本地修改** — Python 脚本处理 JSON
3. **本地保存** — 确认本地文件正确
4. **服务器备份** — `cp 文件 文件.bak`
5. **SFTP 上传** — `sftp.put(本地, 服务器)` 直接覆盖
6. **SSH 验证** — `python3 -c "import json;..."` 读关键字段确认
7. **浏览器验证** — 重载页面 → 切菜单 → 确认新数据加载
8. **ASA 保存** — 点「💾 保存TAB」→ build_lovelace

## 验证命令模板
```python
# 步骤6
c.exec_command("python3 -c \"import json;d=json.load(open('文件'));print(验证字段)\"")
```
