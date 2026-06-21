# 后台管理 — 分步执行清单

> **基于**：[backend_management_plan.md](backend_management_plan.md)
> **方案**：方案 B — 外部 Web 编辑器 + HA API
> **创建日期**：2026-06-10

---

## 阶段一：HA 存储层搭建

### 1.1 var 实体创建

- [x] 在 `configuration.yaml` 新增 `var.asa_server_rules`
  - name: "ASA 服务器规则"
  - initial: `{"sections":[]}`（占位，实际数据将在阶段二填入）

- [x] 在 `configuration.yaml` 新增 `var.asa_tribe_ops_ref`
  - name: "ASA 部落运维速查"
  - initial: `{"tabs":[]}`（占位，实际数据将在阶段二填入）

- [x] 在 `configuration.yaml` 新增 `var.asa_base_quick_ref`
  - name: "ASA 部落基地速查"
  - initial: `{"servers":{"*":...}}`（含默认 fallback 结构）

- [x] 重启 HA 加载新 entity，验证 3 个 var 实体在开发者工具中可见

### 1.2 input_select 扩展

- [x] 修改 `input_select.info_tribe_tab` 的 options，从 2 项扩展到 7 项：
  ```
  - "经验获取速查"
  - "无线传送箱速查"
  - "泰克套部署速查"
  - "畸变发光肩宠速查"
  - "铠护犬功能速查"
  - "持续消耗速查"
  - "高效产出速查"
  ```

### 1.3 Template Sensor 创建

- [x] 创建 `sensor.asa_server_rules_html`
  - unique_id: asa_server_rules_html
  - 从 `var.asa_server_rules` 读取 JSON
  - 按 4 个 section type 分别渲染 HTML
  - 渲染模板覆盖：config_list / toggle_list / crafting_list / loot_list

- [x] 创建 `sensor.asa_tribe_ops_html`
  - unique_id: asa_tribe_ops_html
  - 从 `var.asa_tribe_ops_ref` 读取 JSON
  - 渲染 7 个 tab 的完整 HTML（含 tab bar + 全部 tab 内容）
  - 前端 JS 实现 tab 切换（同页内，无需 conditional card）
  - 渲染模板覆盖：reference_table / server_list / card_grid / mixed_content / server_grid / farming_table

- [x] 创建 `sensor.asa_base_quick_ref_html`
  - unique_id: asa_base_quick_ref_html
  - 从 `var.asa_base_quick_ref` 读取 JSON
  - 读取 `input_select.selected_server` 当前值
  - 实现 `servers[selected] ?? servers["*"]` fallback 逻辑
  - 渲染该服务器的 tabs + 地点表格

- [x] 验证 3 个 sensor 在开发者工具 → 状态中正常显示

---

## 阶段二：数据提取与录入

### 2.1 服务器规则数据

- [x] 从 `速查表.md`「板服配置速查」提取数据，录入为 JSON
  - [x] 基础倍率设置（9 项）
  - [x] 附加配置项（7 项）
  - [x] 制造调整项（4 项：血精鸡尾酒、火车轨道、精炼元素、精炼碎片）
  - [x] 拾取调整项（5 项：畸变地下宝箱、灭绝洞穴宝箱、灭绝三守护、灭绝中高君王、灭绝空投）

- [x] 将 JSON 写入 `var.asa_server_rules`，验证 sensor 渲染正确

### 2.2 部落运维数据 — 已迁入部分

- [x] 持续消耗速查：从 lovelace 现有 HTML 表格提取数据，转为 server_grid JSON
  - [x] 提取全部 12+ 个消耗品的图标 URL、名称
  - [x] 提取每个消耗品在各服务器的地点名称、图像 URL、badge
  - [x] 写入 `var.asa_tribe_ops_ref` 对应 tab

- [x] 高效产出速查：从 lovelace 现有 HTML 提取数据，转为 farming_table JSON
  - [x] 提取全部产出行的图标、地图、采集点、流程文本
  - [x] 写入 `var.asa_tribe_ops_ref` 对应 tab

### 2.3 部落运维数据 — 未迁入部分（速查表.md）

- [x] 经验获取速查：录入为 reference_table JSON
  - [x] 3 条经验分配规则

- [x] 无线传送箱速查：录入为 server_list JSON
  - [x] 孤岛（2 位置）、焦土（1 位置）、核心岛（0）、畸变（2 位置）、灭绝（0）

- [x] 泰克套部署速查：录入为 server_list JSON
  - [x] 孤岛（码头）、焦土（焦土号）、核心岛（巨鱼深水基地）、畸变（俯瞰地×5 图）、灭绝（俯瞰地×5 图）

- [x] 畸变发光肩宠速查：录入为 card_grid JSON
  - [x] 4 张卡片：灯泡犬、轻羽鸟、耀尾兽、闪角鹿

- [x] 铠护犬功能速查：录入为 mixed_content JSON
  - [x] 3 条 text block（伴随模式说明、六角污染物地图说明、传图警告）
  - [x] 命令表（6 行 × 4 列）
  - [x] 装备表（12 行 × 2 列）

### 2.4 部落基地数据

- [x] 从 lovelace `base_whiterober` 现有 HTML 提取数据
  - [x] 孤岛 → 英灵殿 → 地点列表（含分类、名称、坐标、图像、特性）
  - [x] 孤岛 → 龙舍 → 地点列表
  - [x] 按新 JSON 结构重组织（`servers.Isl.tabs[yingling, longshe]`）

- [x] 添加默认 fallback `servers["*"]` 占位数据

---

## 阶段三：Lovelace 改造

### 3.1 方舟视图（服务器规则区域）

- [x] 在「服务器规则 ➥」标题下方添加 markdown card
  - content 引用 `states['sensor.asa_server_rules_html'].attributes.rendered_rules`
  - 保留 card_mod 透明样式

- [x] 添加后台管理入口按钮（导航到 `/local/asa-admin.html`）

### 3.2 info_whiterober（部落运维速查）

- [x] 重构 tab 切换逻辑
  - 方案 A：保留 7 个 conditional card，每个引用 sensor 对应 tab 的渲染片段
  - 方案 B（推荐）：改为单一 markdown card，sensor 渲染完整 HTML（含 tab bar + 内容），前端 JS 切换
  - 选择方案 ___

- [x] 删除所有硬编码 HTML markdown card
- [x] 替换为引用 `sensor.asa_tribe_ops_html` 的 content
- [x] 验证 7 个 tab 切换正常，内容显示正确

### 3.3 base_whiterober（部落基地速查）

- [x] 删除现有硬编码 HTML markdown card
- [x] 替换为引用 `sensor.asa_base_quick_ref_html` 的 content
- [x] 验证切换服务器后基地内容正确变化
- [x] 验证未配置服务器的 fallback 提示正常

### 3.4 同步

- [x] `lovelace` → `lovelace.lovelace` 同步
- [x] XFtp 同步到 HA 服务器
- [x] HA 前端刷新全量验证

---

## 阶段四：后台编辑器开发（asa-admin.html）

### 4.1 框架搭建

- [x] 创建 `www/asa-admin.html` 基础骨架
  - HTML 结构：顶部导航 + 主内容区
  - CSS：响应式布局（桌面端 + 移动端基础适配）
  - JS：HA WebSocket 连接模块（连接、认证、重连）

- [x] 实现 HA WebSocket 读写工具函数
  - `connect()` — 建立 WebSocket，发送 auth
  - `getEntityState(entityId)` — 读取 entity 的 state
  - `setVarValue(entityId, jsonData)` — 调用 var.set_value
  - 错误处理：网络断开提示、保存失败提示

- [x] 实现顶部三 tab 导航
  - 「服务器规则」「部落运维」「部落基地」
  - 切换时加载对应 editor 模块

### 4.2 服务器规则编辑器

- [x] 实现 4 个子节的 tab 切换（基础倍率 / 附加配置 / 制造调整 / 拾取调整）

- [x] 实现 config_list 编辑器
  - 配置项列表展示
  - 添加/编辑表单：emoji 输入、名称、值、配置文件下拉、配置代码
  - 删除确认

- [x] 实现 toggle_list 编辑器
  - 开关列表展示
  - 添加/编辑表单：启用开关、名称、配置文件、配置代码

- [x] 实现 crafting_list 编辑器
  - 配方列表展示（含原料子列表）
  - 添加/编辑表单：配方名、原料列表（+/- 原料行）、配置文件、代码 textarea

- [x] 实现 loot_list 编辑器
  - 按地图的调整列表展示
  - 添加/编辑表单：地图下拉、分类、调整内容、备注

- [x] 实现保存：校验 JSON → WebSocket 写入 `var.asa_server_rules`

### 4.3 部落运维速查编辑器

- [x] 实现左侧 tab 列表 + 右侧编辑面板的布局
  - tab 可拖拽排序
  - 点击 tab 切换右侧编辑面板

- [x] 实现 tab 通用编辑器（名称、描述、type 选择、排序）

- [x] 按 type 实现 6 种编辑面板：

  - [x] **reference_table 编辑器**
    - 列定义（列名列表）
    - 行列表，每行多字段输入

  - [x] **server_list 编辑器**
    - 服务器选择折叠面板
    - 每个服务器下地点列表：名称 + 图片 URL + 预览

  - [x] **card_grid 编辑器**
    - 列数设置
    - 卡片列表：名称 + 图片 URL + 特性标签

  - [x] **mixed_content 编辑器**
    - 内容块列表（可排序）
    - 添加 block：选择类型（text / table / image）
    - text block：样式选择 + 文本输入
    - table block：列定义 + 行编辑
    - 每个 block 可编辑/删除

  - [x] **server_grid 编辑器**
    - 列管理（绑定服务器 ProfileName）
    - 物品列表（搜索、排序）
    - 物品编辑弹窗：名称、图标 URL、分类 + 按服务器的地点列表
    - 每个地点：名称、图像 URL（预览）、badge 下拉

  - [x] **farming_table 编辑器**
    - 列定义
    - 行列表，每行多字段（产出图标、地图、采集点、流程文本）

- [x] 实现保存：全量 JSON 写入 `var.asa_tribe_ops_ref`

### 4.4 部落基地速查编辑器

- [x] 实现顶部服务器选择器
  - 从 `sensor.asa_server_details` 获取服务器列表
  - 含「默认*」选项

- [x] 实现「复制自其他服务器」功能
  - 弹窗选择源服务器
  - 深拷贝 tabs 数据到目标服务器

- [x] 实现 Tab 列表 + Tab 编辑面板
  - 添加/删除/重命名 Tab
  - Tab 描述编辑

- [x] 实现地点编辑器（在选中的 Tab 内）
  - 地点列表展示
  - 添加/编辑地点：分类下拉、名称、坐标、图像 URL（预览）、特性标签列表
  - 特性标签：添加/删除（自由文本 + 常用预设下拉）

- [x] 实现保存
  - 「保存当前服务器」：仅更新当前编辑的服务器数据
  - 「保存全部」：全量写入 `var.asa_base_quick_ref`

### 4.5 通用功能

- [x] 图片 URL 输入框带即时预览缩略图
- [x] 确认对话框组件（删除确认、未保存离开确认）
- [x] 操作结果 Toast 提示（成功/失败）
- [x] JSON 实时预览面板（可展开/折叠）
- [x] 数据导出按钮（下载 JSON 文件备份）
- [x] 移动端响应式适配（至少保证基础编辑可用）

### 4.6 编辑器入口

- [x] 在方舟视图添加导航按钮 → `/local/asa-admin.html`
- [x] （可选）在 HA 侧边栏注册面板入口

---

## 阶段五：验证与清理

### 5.1 功能验证

- [ ] 服务器规则：3 个 sensor HTML 渲染与速查表.md 原始内容对比
- [ ] 部落运维：7 个 tab 全部内容核对，图片加载正常
- [ ] 部落基地：切换 10 台服务器，每台显示正确基地或 fallback 提示
- [ ] 编辑器：添加/编辑/删除数据 → 保存 → HA 前端刷新看到更新
- [ ] 编辑器：从 HA 读取最新数据（打开编辑器时加载当前 entity state）

### 5.2 清理

- [ ] lovelace 中删除所有旧的硬编码 HTML markdown card
- [ ] 删除 lovelace 中不再使用的 conditional card（如原有 2-tab 的旧版）
- [ ] 确认 `lovelace.lovelace` 已同步
- [ ] 备份：lovelace / configuration.yaml / www/asa-admin.html

### 5.3 文档

- [ ] 更新 `CLAUDE.md` 中的 lovelace 结构描述（新增 sensor 引用说明）
- [ ] 编写 `asa-admin.html` 使用说明（简要操作指南）

---

## 阶段六：优化扩展（可选）

- [ ] 图片管理优化：URL 别名快捷选择
- [ ] 图片上传功能（对接 HA media_source 或图床 API）
- [ ] 编辑器操作日志（记录谁在何时修改了什么）
- [ ] 数据版本回滚（保留最近 N 次 JSON 快照）
- [ ] 移动端编辑器深度适配

---

## 进度总览

| 阶段 | 内容 | 状态 |
|------|------|:---:|
| 一 | HA 存储层搭建 | ✅ |
| 二 | 数据提取与录入 | ✅ |
| 三 | Lovelace 改造 | ✅ |
| 四 | 后台编辑器开发 | ✅ |
| 五 | 验证与清理 | ⬜ |
| 六 | 优化扩展（可选） | ⬜ |

---

> 勾选标记：将 `- [ ]` 改为 `- [ ]` 表示完成
