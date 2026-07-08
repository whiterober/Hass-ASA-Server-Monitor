# 基地速查：方案A — 每服独立视图

> 创建时间：2026-07-08 | 修订：2026-07-08
> 数据源：`asa_base_quick_ref.json` → `servers.{Isl|Sco|Cen|...}.tabs[]`

## 核心铁律

**ASA 只修改以下视图，其余一律不动：**

```
ASA 管理范围：views[6:19]（服务器规则/部落速查/11基地）+ views[19:21]（原版）
禁止触动：   views[0:6]
```

> 全部使用 path 查找，索引 [6:21] 无预留空格。

## 完整视图布局

| 视图索引 | 标题 | path | 管理者 |
|----------|------|------|:---:|
| 0 | 家 | - | HA 手动 |
| 1 | 电视遥控器 | - | HA 手动 |
| 2 | 工作室 | - | HA 手动 |
| 3 | 方舟 | - | HA 手动 |
| 4 | 服务器操作 | asa-server-ops | HA 手动 |
| 5 | 资讯广场 | ark_patch | HA 手动 |
| **6** | **服务器规则** | **asa-server-rules** | **ASA** |
| **7** | **部落运维速查** | **info_whiterober** | **ASA** |
| **8** | **孤岛基地速查** | **base_isl** | **ASA** |
| **9** | **焦土基地速查** | **base_sco** | **ASA** |
| **10** | **核心岛基地速查** | **base_cen** | **ASA** |
| **11** | **畸变基地速查** | **base_abe** | **ASA** |
| **12** | **灭绝基地速查** | **base_ext** | **ASA** |
| **13** | **繁星基地速查** | **base_ast** | **ASA** |
| **14** | **仙境基地速查** | **base_rag** | **ASA** |
| **15** | **瓦尔盖罗基地速查** | **base_val** | **ASA** |
| **16** | **俱乐部基地速查** | **base_bob** | **ASA** |
| **17** | **创世模拟基地速查** | **base_gen** | **ASA** |
| **18** | **失落地基地速查** | **base_los** | **ASA** |
| 19 | 部落运维速查（原版） | info_whiterober_old | HA 手动 |
| 20 | 基地速查（原版） | base_whiterober_old | HA 手动 |

## 生成策略

`build_lovelace.py` 流程：

```
1. 读取现有 lovelace → 取 views[0:6] 保留 + 提取旧原版视图
2. 重建干净 views 数组（丢弃旧 ASA 残留和 padding）
3. 生成 ASA 视图：
   views[6] = 服务器规则
   views[7] = 部落运维速查
   views[8:19] = 11基地视图
4. 追加原版视图到 views[19:21]
5. 写入全部 4 个输出文件
```

关键：**ASA 不读不写非 ASA 视图内容**；使用 `_find_view(path, default)` 按 path 查找。

## 数据结构

`asa_base_quick_ref.json` → `servers.{Isl|Sco|...}.tabs[]` → `{name, sections: [{name, html}]}`

## build_lovelace.py 已实现要点

- `BASE_SERVER_MAP`：11 服，默认索引 8-18
- `_find_view(path, default)`：按 path 查找，支持索引位移
- 视图重建：`views = views[0:6] + keep_after`，丢弃所有残留
- ASA 只写 views[6:21]

## 实施状态

- [x] build_lovelace.py：BASE_SERVER_MAP + path 查找 + 干净重建
- [ ] preview_server.py：同步适配
- [ ] asa-admin.html：基地编辑器 11 服适配
- [ ] 测试验证
