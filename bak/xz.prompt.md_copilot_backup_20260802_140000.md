# CONTEXT MODE: CONTINUED SESSION

历史摘要：
v1174 基线 (20260708)。

## MDI 去重
- 删除 mcICMdi 输入框（ASA 编辑器 L2956/L3550）
- build_lovelace.py: _render_mdi_inline() 全文 re.finditer 解析 mdi:([\w-]+) → ha-icon
- 标题/描述/图标组标题均用 _render_mdi_inline 渲染
- esc() 不处理 emoji，天然支持混排
- preview_server.py import build_lovelace，无需独立修改

## 数据迁移
- 服务器端脚本直接读写 JSON（asa_server_rules.json, server_rules.json）
- 44 块迁移：mdi_icon 值 (emoji/mdi:) → title 前缀
