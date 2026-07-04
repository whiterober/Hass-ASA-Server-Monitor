# CONTEXT MODE: CONTINUED SESSION

历史摘要：
## 2026-07-02 数据事故+采集速查回填

### 事故恢复
- 本地旧版覆盖服务器 tribe_ops.json 致全部 Tab 丢失
- 从 VS Code 浏览器缓存 f_0013fa (136949B) 找回原始版

### 固化规则
- 改前必须先 SFTP get 拉服务器最新版

### 采集速查回填 7->20张
- 图片: icons2.json -> img.whiterober.ccwu.cc CDN, 18种资源图标
- 板块级色块态: card级 server_states: {X:2} + highlight, 描述行无server
- 结构: map_filter + 20 info_card, 行间 {type:br} 无末尾br
- 分布: Isl*4 Sco*1 Abe*5 Ext*6 全图/除畸变*4

### 文件
server: /config/www/asa-data/tribe_ops.json
local: data/tribe_ops.json
backup: tribe_ops_backup_20260702_182243.json

当前任务：
🟢 待命
