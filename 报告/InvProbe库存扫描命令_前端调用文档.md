# InvProbe 库存扫描命令 给前端看的调用文档

> 插件：`TransferIdentityFixAPI` · 版本：0.3.0 · 更新：2026-09-04
> 用途：前端 / 脚本通过 RCON **实时扫描指定服务器上建筑容器、驯服生物背包、玩家背包**内的物品清单，RCON 直接返回 JSON（不落盘）。

---

## 1. RCON 连接

### 1.1 服务器地址与端口

| 服务器 | 缩写 | 端口 | 地址 |
|--------|------|------|------|
| 孤岛 | Isl | 32320 | work.whiterober.cn |
| 焦土 | Sco | 32321 | work.whiterober.cn |
| 中心岛 | Cen | 32322 | work.whiterober.cn |
| 艾伯 | Abe | 32323 | work.whiterober.cn |
| 灭绝 | Ext | 32324 | work.whiterober.cn |
| 仙境 | Ast | 32325 | work.whiterober.cn |
| 拉格纳 | Rag | 32326 | work.whiterober.cn |
| 瓦尔盖罗 | Val | 32327 | work.whiterober.cn |
| 迷失 | Los | 32328 | work.whiterober.cn |
| 创世纪2 | Gen | 32329 | work.whiterober.cn |

> RCON 密码各服务器一致（`1219wu1219`）。属敏感信息，前端应放在服务器端配置中，不写入前端代码/日志。

### 1.2 协议

标准 Source RCON：认证（Type=3）→ 发命令（Type=2）→ 收响应（Type=0，正文为 JSON）。

实现参考项目内脚本 `TransferIdentityFixAPI/scripts/rcon_client.py`：

```python
from rcon_client import send_rcon_command_sync
ok, payload = send_rcon_command_sync("work.whiterober.cn", 32322, "1219wu1219",
                                     "TransferIdentityFix.InvProbe _C 1228031745 5")
# ok=True, payload=见下方 JSON 结构
```

命令行：`python rcon_client.py <host> <port> <password> <command>`

---

## 2. 命令格式

| 项 | 值 |
|----|----|
| 命令 | `TransferIdentityFix.InvProbe <filter> <tribeId> <maxContainers>` |
| 权限 | RCON 命令级 `tif.operator` |
| 返回 | **RCON 直接返回 JSON**，不写任何数据文件 |

### 2.1 参数说明

| 参数 | 必填 | 默认 | 说明 |
|------|:---:|------|------|
| `<filter>` | 否 | 空串=全部 | 容器 class 名**大小写不敏感子串**匹配。例 `Trough` 匹配饲料槽类、`Grill` 匹配烤架、`_Character_BP` 匹配驯服生物。**注意**：RCON 命令按空格分词，真正"空 filter"无法用 `""` 表达（`""` 会被当成字面两个引号字符），因此**扫全部时不要传 filter 而是靠 tribeId / maxContainers 控量**，或传宽泛子串（如 `_C`） |
| `<tribeId>` | 否 | `0`=全部 | 只扫某部落（`TargetingTeam`）的容器；`0` 扫所有部落 |
| `<maxContainers>` | 否 | `30` | 返回的容器数上限（遍历到该数量即停）；每容器物品数上限固定 **250** |

### 2.2 扫描范围（type）

| type | 对象 | 示例 |
|------|------|------|
| `structure` | 建筑容器（含洞穴/空投补给箱） | 烤架 `Grill_C`、饲料槽、储物箱、`SupplyCrate_*` |
| `dino` | 驯服生物背包 | `Shastasaurus_Character_BP_C`、驮兽 |
| `player` | 玩家背包（在线玩家） | `AShooterCharacter` |

---

## 3. 返回 JSON 结构（实测字段）

```json
{
  "ok": true,
  "filter": "_C",
  "tribeId": 1228031745,
  "containers": 36,
  "items": 1243,
  "list": [
    {
      "type": "structure",
      "class": "Grill_C",
      "id": "Grill_C_2144755403",
      "team": 1228031745,
      "itemCount": 5,
      "items": [
        { "slot": 0, "class": "PrimalItemConsumable_CookedLambChop_C", "qty": 1, "dur": 0.0, "name": "" }
      ]
    }
  ]
}
```

### 3.1 顶层字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `ok` | bool | 是否成功（false 时含 `error` 字段） |
| `filter` | string | 回显请求的 filter（原样） |
| `tribeId` | number | 回显请求的部落 ID（0=全部） |
| `containers` | number | 命中的容器数（`list.length`） |
| `items` | number | 命中的物品总数 |
| `list` | array | 容器数组 |

### 3.2 `list[]` 每条容器

| 字段 | 类型 | 说明 |
|------|------|------|
| `type` | string | `structure` / `dino` / `player` |
| `class` | string | 容器完整类名（如 `Grill_C`、`Shastasaurus_Character_BP_C`） |
| `id` | string | 容器 actor 名（形如 `<class>_<序号>`，可用于去重/跳转定位） |
| `team` | number | 所属部落 ID（洞穴/空投补给箱为 `0`） |
| `itemCount` | number | 该容器物品槽总数（**含空槽**，见 §4 注意） |
| `items` | array | 物品数组（只含非空槽） |

### 3.3 `items[]` 每条物品

| 字段 | 类型 | 说明 |
|------|------|------|
| `slot` | number | 槽位下标（0 起） |
| `class` | string | 物品完整类名（如 `PrimalItemConsumable_CookedLambChop_C`） |
| `qty` | number | 堆叠数量 |
| `dur` | number | 耐久值（可损耗物品为剩余耐久，消耗品/不可损耗为 `0`） |
| `name` | string | **玩家自定义名**（无自定义名为空串 `""`） |

---

## 4. ⚠️ 调用注意（实测踩坑）

1. **RCON 响应有大小上限（约 8KB）**：`maxContainers` 调大 + 空 filter 时响应会**被截断**（JSON 不完整、无法解析）。实测：`InvProbe _C 0 40` 返回 36 容器即截断。**前端务必**：
   - 单次查询用小 `maxContainers`（建议 ≤5）或带 `filter` / `tribeId` 精确缩小范围；
   - 对 `payload` 做 `JSON.parse` 容错，解析失败提示"结果过大，请缩小范围"。
2. **`itemCount` 含空槽**：它是容器 `InventoryItems.Num()`，实际物品数以 `items.length` 为准（实测 55 槽容器 `itemCount=55` 但物品数可能更少）。
3. **`tribeId` 是单部落（team）过滤，不是联盟**：联盟由多个部落组成，查联盟需分别传成员部落 ID（可从联盟数据取）。
4. **洞穴/空投补给箱也在扫描范围**（`team=0`、type=structure），空 filter 时它们会先占满返回列表，要找玩家建筑请用 `tribeId` 或精确 `filter`。
5. **duration（dur）字段**：如 `-1` 表示读取失败（不应出现，正常为 0 或正数）。
6. **空 filter 传参**：不要传 `""`（会被当作字面 `""` 过滤导致 0 结果），见 §2.1。

---

## 5. 调用示例

### 5.1 查某部落全部有物品的容器（含建筑+生物+玩家）

```
TransferIdentityFix.InvProbe _C 1228031745 10
```
> 部落 1228031745 属「魔戒咕噜」联盟；实测返回烤架/水龙头/生物背包等。

### 5.2 按建筑类型查（全图饲料槽）

```
TransferIdentityFix.InvProbe Trough 0 10
```

### 5.3 查某部落驯服生物背包

```
TransferIdentityFix.InvProbe _Character_BP 1228031745 5
```
> 返回该部落所有带非空背包的驯服生物（type=dino）。

### 5.4 失败返回

```json
{ "ok": false, "error": "world not ready" }
```
> `world` / `level` 未就绪（服务器刚启动/换图）时返回；前端可稍后重试。

---

## 6. 常见用途

- 查部落"饲料槽/烤架/储物箱存了什么"（补给审计、借建筑归还核对）；
- 查驯服生物（驮兽/战宠）背包里放了什么（防私藏、盘点）；
- 查玩家背包当前物品（需玩家在线）；
- 与 `EggProbe` / `CryoProbe` 配合做全服资产盘点。
