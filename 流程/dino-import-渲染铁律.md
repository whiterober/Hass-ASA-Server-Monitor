# dino-import 渲染铁律（2026-09-15 事故复盘固化）

> 来源：v1181–v1185 连发导致 Isl「聚落全不见」事故 + v1190 越界改动事件。
> 适用范围：`b:\项目\Hass ASA Server Monitor\dino-import.html` 及其打包/部署链路。

## 一、渲染热路径禁令（最高优先级）

- **禁止**把「全量扫描类计算」放进渲染热路径（`lbRenderView` / `lbClusterSettles` / `renderSeg` / `lbSettleBtnHtml` / tab 构建等）。
  - 反面案例：v1181/v1182 把 `lbSaddleBpMyIdx()`（全量扫描 `itemsByServer[*].byPos` 数万条物品）塞进「每条聚落按钮」「每服 hasContent」「每个聚落 key」⇒ 最大服 Isl（413 生物 / 55 聚落）首屏聚落区长时间空白，用户看到「聚落全不见了」。
- 判定类需求一律走 **「过滤」**：复用现有 rec 数据 + 现成函数（如 `lbGroupItems` / `lbSpeciesMatch` / `lbSaddleBpSet`），命中即停。
- 需要统计/聚合时，放到**构建期**（`lbBuildSettlements` / `lbEnsureSettlements` 覆盖层期间）或**按需 + 定向查询**，并把结果写回 `data._*` 或按 key 缓存，渲染只读。
- 缓存键必须含**数据指纹**（如 `recs.length + itemsByServer 服数`），数据刷新自动失效。

## 二、性能验收门槛（不可跳步）

- 任何改动上线前**必须**在**最大数据集（Isl）**上量首屏：聚落区可交互时间相对基线 **Δ ≤ +10%**，否则不上线。
- 禁止凭"小服看起来很快"判断性能。
- 5 个以上版本**禁止叠加连发**：逐版部署 + 逐版验证（tab → 聚落 → 容器 → 内容），出问题才能定位到版本。

## 三、方案级变更必须先问（v1190 越界教训）

- 改动**判定数据源**（如 `settle.containers` → 坐标归属）、**新增索引/缓存表**、**新增合成结构（如合成 rec）** ⇒ 属于**方案级变更**，必须先向用户复述 + 用 askQuestions 确认，禁止"顺手就改"。
- 仅"加一条判定/一行布尔"级别的小改动，才可在既有批准方案内直接实施。

## 四、断言前先确认访问路径（本次"没有 rec"误判）

- 书柜（`StructureBP_LibraryStorage_C_*`）**本来就有 facility rec**（`src='facility'`），未选物种时正常显示。
- `settle.containers` 表 ≠ rec 归属；判断"某容器有没有 rec"必须走 rec 集合，不能拿聚落容器表当依据。
- 结论必须自证：函数级验证（判定函数 true/false + 反例对照）+ UI 级验证（tab → 聚落 → 容器 → 内容）双证据。

## 五、口径统一

- 新增判定必须与既有同类判定**共用同一函数/同一口径**（如蓝图判定统一走 `lbSpItemIsBp`；"我的部落"用 `lbPlayerTribes`/`lbMemberIsMy`），避免同一概念两套实现。
- 逐层判定（tab / 聚落 / 容器）应同源：若某层用"成员集"、另一层用"全量 rec"，会出现 `Isl=true/false` 这类不一致（v1191 遗留，待用户定夺）。

## 六、安全与流程

- 改前必备份：`bak/dino-import_backup_<YYYYmmdd_HHMMSS>.html`（补丁脚本自动生成）。
- 部署：`tmp/_deploy_cf.py` → 线上验证（若报 `版本一致: False` 属边缘缓存延迟，用浏览器 `cache:'no-store'` 复核，勿据此误判失败）。
- 紧急回滚：`tmp/_rollback_*.py`（已演练有效，v1185→v1180 全程 ~4 分钟）。
- **禁止替用户登录**（页面出现自动填充凭据时不得代为提交）；验证需登录态时，改用函数级验证或内存临时身份（`LB.curPid`），并在验证后恢复原状态。
