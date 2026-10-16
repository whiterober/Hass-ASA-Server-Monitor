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

---

## dino_rules.json 编辑规范（2026-10-16 v4668 固化）

> 教训来源：v4667 只改 dino-import.html 归类数组、部署后页面无变化 —— `dino_rules.json` 经页面 `lbRulesMerge()` **并集合并**把旧名单**回灌**（`_union` 只加不减）。

- **双源意识**：归类清单 = `dino-import.html` 硬编码数组 + `dino_rules.json`；**删除/移出清单项必须改 dino_rules.json**；新增任一即可；改名双端同步（`_obj` 补键不覆盖）
- **格式**：手工混合风格（indent 1、短数组单行、中文原文）⇒ **禁止 `json.dump()` 全量重写**（格式爆炸、diff 巨大）
- **编辑三件套**（Python 字符串级）：
  1. 每处锚点 `raw.count(old) == 1` 断言（失败即中止、不写回）
  2. 替换后 `json.loads()` 整体校验
  3. `shutil.copy2` 备份到 `bak/dino_rules_backup_*.json` 后才写回
- **改后链条**：bump `LB_VERSION`（URL 带 `?v=`）+ `pwa/sw.js` VER 同步 → `tmp\_deploy_cf.py` 部署 → 运行时验证（`LB_TEST_EXTRA.length` 等）
- **机械检查**：任务「新生物:⑥ 双源一致性检查」（`流程\工具\rules_sync_check.py`，输出 `_last_rules_sync.txt`）
