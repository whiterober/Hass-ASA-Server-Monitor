# RCON 接口与 JSON 数据结构说明（前端调用参考）

> 插件：`TransferIdentityFixAPI` · 版本：0.3.0 · 更新：2026-08-06
> 用途：前端 / 脚本通过 RCON 调用插件接口、读取离线 JSON 数据。

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

> RCON 密码：各服务器一致（`1219wu1219`）。密码属敏感信息，前端应放在服务器端配置中，不写入前端代码/日志。

### 1.2 协议

标准 Source RCON（3 步）：
1. **认证**：`Type=3`，body 为密码 → 返回 `Type=2`（成功）或 `Type=-1`（失败）
2. **发命令**：`Type=2`，body 为命令字符串
3. **收响应**：`Type=0`，响应正文即 JSON（JSON 命令）或 `Keep Alive`（聊天回显命令）

实现参考项目内脚本 `TransferIdentityFixAPI/scripts/rcon_client.py`：
```python
from rcon_client import send_rcon_command_sync
ok, payload = send_rcon_command_sync("work.whiterober.cn", 32321, "1219wu1219",
                                     "TransferIdentityFix.ArkStatus")
# ok=True, payload='{"ok":true,...}'
```
命令行：`python rcon_client.py <host> <port> <password> <command>`

---

## 2. 命令总览

| # | RCON 命令 | 参数 | 返回 | 权限(设计) |
|---|-----------|------|------|-----------|
| 1 | `TransferIdentityFix.Ping` | 无 | 聊天回显（版本） | viewer |
| 2 | `TransferIdentityFix.DinoMutPing` | 无 | **JSON** | operator |
| 3 | `TransferIdentityFix.DinoMut` | `<dinoId1> <dinoId2>` | **JSON** | operator |
| 4 | `TransferIdentityFix.ArkGetDino` | `<dinoId1> <dinoId2>` | **JSON** | operator |
| 5 | `TransferIdentityFix.ArkTamedDinos` | 无 | **JSON** | operator |
| 6 | `TransferIdentityFix.ArkStatus` | 无 | **JSON** | viewer |
| 7 | `TransferIdentityFix.Status` | `[player]` | 聊天回显 | viewer |
| 8 | `TransferIdentityFix.Reconnect` | `[player]` | 聊天回显 | operator |
| 9 | `TransferIdentityFix.ReconnectTarget` | `[player]` | 聊天回显 | operator |
| 10 | `TransferIdentityFix.ReloadConfig` | 无 | 聊天回显 | operator |
| 11 | `TransferIdentityFix.CurrentMap` | `[player]` | 聊天回显 | viewer |
| 12 | `TransferIdentityFix.DebugChat` | `on\|off` | 聊天回显 | operator |
| 13 | `TransferIdentityFix.Trace` | `<message>` | 聊天回显 | operator |

> 说明：**JSON 命令**（3-6）通过 RCON 直接返回 JSON 响应体，适合前端调用。其余命令走**聊天回显**，RCON 客户端收到的是 `Keep Alive`（无 JSON 返回），主要用于运维手动操作。

> 权限现状：当前 `AsaBridge.h::HasPermission()` 恒返回 `true`（无条件放行），所有命令任何通道均可调用；设计上区分 `tif.viewer` / `tif.operator`。

---

## 3. JSON 命令详细说明

### 3.1 `TransferIdentityFix.DinoMutPing`（健康检查）

无参数。返回：

```json
{"ok": true, "plugin": "TransferIdentityFixAPI", "version": "0.3.0"}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| ok | bool | 是否成功 |
| plugin | string | 插件名（固定） |
| version | string | 插件版本 |

### 3.2 `TransferIdentityFix.DinoMut <dinoId1> <dinoId2>`（实时属性/突变查询）

查询**游戏中内存里的一只龙**（O(1) 按 ID 查询，不做全图扫描）。

**参数**：`dinoId1`（uint32）、`dinoId2`（uint32）—— 龙的 2 段 ID。

**成功返回**：
```json
{
  "requestId": "dinomut_1785xxxxxx",
  "dinoId": "123_456",
  "found": true,
  "tribeId": 1589589881,
  "gender": "FEMALE",
  "statPoints": {"health": 45, "stamina": 42, "torpidity": 0, "oxygen": 36, "food": 39, "water": 0, "temperature": 0, "weight": 42, "meleeDamage": 43, "movementSpeed": 0, "fortitude": 0, "craftingSpeed": 0},
  "statMutations": {"health": 10, "stamina": 0, "...": 0},
  "statValues": {"health": 5760, "stamina": 2600, "...": 0},
  "randomMutations": {"male": 96, "female": 6},
  "ancestors": [{"maleId": "100_200", "femaleId": "300_400"}],
  "error": null
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| requestId | string | 请求追踪 ID（`dinomut_` + 毫秒时间戳） |
| dinoId | string | `"<id1>_<id2>"` |
| found | bool | 是否找到 |
| tribeId | int | 龙的部落 ID |
| gender | string | `MALE` / `FEMALE` |
| statPoints | object | 12 属性加点数（key 为属性名） |
| statMutations | object | 12 属性变异数 |
| statValues | object | 12 属性 Max 面板值（`MaxStatusValues`，四舍五入为 int） |
| randomMutations | object | `{male, female}` 随机突变 |
| ancestors | array | 祖先链 `[{maleId, femaleId}]` |
| error | string/null | 出错信息；成功为 null |

**失败返回**：
```json
{"requestId":"dinomut_xxx","dinoId":"","found":false,"error":"missing dino1/dino2"}
{"requestId":"dinomut_xxx","dinoId":"123_456","found":false,"error":"dino not found"}
```

### 3.3 `TransferIdentityFix.ArkGetDino <dinoId1> <dinoId2>`（单龙实时查询）

查询**放出的龙**（live released dino，内存实时数据）。球内/宠物台龙不再由本接口服务（走 cryo JSON）。

**成功返回**（与 tamed sidecar 字段对齐）：
```json
{
  "found": true,
  "id": "123_456", "id1": 123, "id2": 456,
  "dinoId1": 123, "dinoId2": 456,
  "gender": "FEMALE",
  "colors": "13,32,0,35,22,32",
  "dinoClass": "Direbear_Character_BP_C",
  "name": "阿紫",
  "level": 262,
  "tribeId": 1589589881,
  "babyAge": 1.0,
  "isBaby": 0,
  "randomMutationsMale": 96,
  "randomMutationsFemale": 6,
  "ancestors": [{"maleId":"...","femaleId":"..."}],
  "saddle": "PrimalItemArmor_...",
  "downloadedAtWorldSec": 222956547.000,
  "tamedAtWorldSec": 219351000.000,
  "statValues": {"health":5760,"...":0},
  "statPoints": {"health":45,"...":0},
  "statMutations": {"health":10,"...":0}
}
```

> 注：`statValues/statPoints/statMutations` 此处为**对象**（key=属性名），与离线 JSON 的数组格式不同，前端需区分。

> 🕐 **`downloadedAtWorldSec`**：**下载进服时间（原始世界秒，`DinoDownloadedAtTime`）**。龙最后一次真·下载进这台服务器的时间；装球/带球转服/放出不更新。**仅用于排序**（世界秒跨服流速不同、不可换算墙钟时间；可靠绝对时间只在球内 `downloadedAtMs`）。

> 🕐 **`tamedAtWorldSec`**：**驯服时间（原始世界秒，`TamedAtTime`）**。龙被驯服/繁殖的时间；跨服下载的龙该字段为 0（用 `downloadedAtWorldSec`），本地驯养/繁殖的龙有值（`downloadedAtWorldSec` 为哨兵 0）。**仅用于排序**，跨服不可比、不可换算墙钟时间。

**未找到**：
```json
{"ok": false, "error": "dino not found"}
```

### 3.4 `TransferIdentityFix.ArkTamedDinos`（触发 tamed 快照）

触发插件扫描内存放出龙并写 `<缩写>_tamed.json`（sidecar）。有 20 秒冷却。

**正常返回**：
```json
{"ok": true, "triggered": true}
```

**冷却中返回**：
```json
{"ok": true, "cooldown": true, "count": 0}
```

### 3.5 `TransferIdentityFix.ArkStatus`（服务器 / 解析状态）

返回当前服务器的解析状态与 JSON 文件时间戳。

```json
{
  "ok": true,
  "serverId": "Sco",
  "pluginVersion": "0.3.0",
  "autoParseEnabled": true,
  "sidecarEnabled": true,
  "cryoJson": "D:\\ARK Server\\DinoData\\Sco_cryo.json",
  "tamedJson": "D:\\ARK Server\\DinoData\\Sco_tamed.json",
  "lastSaveMs": 1785992159672,
  "lastSaveIso": "2026-08-06T...",
  "tamedMs": 1785992159672,
  "tamedIso": "2026-08-06T...",
  "stats": {"inCryopod": 44, "objects": 44, "skipped": "0", "noClass": "0"}
}
```

| 字段 | 说明 |
|------|------|
| serverId | 服务器缩写（如 Sco/Isl） |
| cryoJson / tamedJson | 输出的 JSON 文件路径 |
| lastSaveMs / lastSaveIso | cryo JSON 最近写入时间 |
| tamedMs / tamedIso | tamed JSON 最近写入时间 |
| stats.inCryopod | cryo 球数量 |

---

## 4. 属性索引（12 stat）

`statPoints / statMutations / statValues` 的**数组下标**与 **RCON 对象 key** 对应：

| 下标 | key | 中文 |
|------|-----|------|
| 0 | health | 生命 |
| 1 | stamina | 耐力 |
| 2 | torpidity | 眩晕 |
| 3 | oxygen | 氧气 |
| 4 | food | 食物 |
| 5 | water | 水分 |
| 6 | temperature | 温度 |
| 7 | weight | 负重 |
| 8 | meleeDamage | 近战 |
| 9 | movementSpeed | 速度 |
| 10 | fortitude | 耐性 |
| 11 | craftingSpeed | 制作 |

---

## 5. 离线 JSON 数据结构（Qsync 同步到前端）

> 离线 JSON 由实服插件 / 离线读档 exe 生成，经 Qsync 同步到前端目录（如 `P:\私人共享\ASA\DinoData`），前端直接读取本地文件即可，无需实时 RCON。

### 5.1 tamed JSON（`<缩写>_tamed.json`，放出的龙）

由插件 `WriteDinoSidecar` 生成（RCON `ArkTamedDinos` 触发）。

```json
{
  "savedAt": "1785992159672",
  "count": 20,
  "dinos": [
    {
      "id": "397174429_187449547", "id1": 397174429, "id2": 187449547,
      "dinoId1": 397174429, "dinoId2": 187449547,
      "gender": "FEMALE", "colors": "13,32,0,35,22,32",
      "dinoClass": "Direbear_Character_BP_C", "name": "阿紫", "level": 262,
      "tribeId": 1589589881,
      "babyAge": 1.0, "isBaby": 0,
      "randomMutationsMale": 96, "randomMutationsFemale": 6,
      "ancestors": [{"maleId":"...","femaleId":"..."}],
      "saddle": "PrimalItemArmor_...",
      "downloadedAtWorldSec": 222956547.000,
      "tamedAtWorldSec": 219351000.000,
      "statValues": [5760, 2600, 0, 1242, 17640, 0, 0, 1492, 9.0, 0, 0, 0],
      "statPoints": [45, 42, 0, 36, 39, 0, 0, 42, 43, 0, 0, 0],
      "statMutations": [10, 0, 0, 0, 0, 0, 0, 0, 4, 0, 0, 0]
    }
  ]
}
```

| 字段 | 说明 |
|------|------|
| savedAt | 生成时间（毫秒时间戳，字符串） |
| count | dinos 数量 |
| dinos[].tribeId | 龙所属部落 ID（与 cryo 的 `tribes` 段对应） |
| babyAge | 成长比例（0-1，≥1 为成年） |
| **dinos[].downloadedAtWorldSec** | **下载进服时间**（原始世界秒，`DinoDownloadedAtTime`）。放出的龙才有此字段；野生龙/系统单位为 0。**仅用于排序**（世界秒跨服流速不同，不可换算成墙钟时间；可靠绝对时间只在球内 `downloadedAtMs`） |
| **dinos[].tamedAtWorldSec** | **驯服时间**（原始世界秒，`TamedAtTime`）。跨服下载的龙为 0（用 `downloadedAtWorldSec`）；本地驯养/繁殖的龙有值（`downloadedAtWorldSec` 为哨兵 0）。**仅用于排序**，跨服不可比 |
| statValues[] | 12 属性值（数组） |
| statPoints[] / statMutations[] | 12 属性加点 / 变异数 |

### 5.2 cryo JSON（`<缩写>_cryo.json`，球内 + 宠物台）

由离线读档 exe（`ark_save_reader.exe`）生成，服务器每次保存后自动重跑。

```json
{
  "serverId": "Sco",
  "arkPath": "D:\\ARK Server\\...\\ScorchedEarth_WP.ark",
  "elapsedMs": 208,
  "stats": {"objects": 53586, "spawned": 0, "inCryopod": 44, "skipped": 53542, "noClass": 0, "wildFiltered": 0},
  "tribes": {
    "1589589881": {"name": "北美狗鱼", "ownerName": "板板", "members": ["板板"]},
    "1364288197": {"name": "大表哥", "ownerName": "嘎巴丸", "members": ["嘎巴丸","蕈人王","老卵","人类","满穗","随意"]}
  },
  "cryopod": [
    {
      "podClass": "PrimalItem_WeaponEmptyCryopod",
      "podInstanceId": 12345,
      "dinoClass": "Direbear_Character_BP_C",
      "dinoInstanceId": 67890,
      "name": "阿紫", "level": 262,
      "babyAge": 1.0, "isBaby": 0,
      "saddle": "PrimalItemArmor_...",
      "gender": "FEMALE", "colors": "13,32,0,35,22,32",
      "statValues": [5760, 2600, 0, 1242, 17640, 0, 0, 1492, 9.0, 0, 0, 0],
      "statPoints": [45, 42, 0, 36, 39, 0, 0, 42, 43, 0, 0, 0],
      "statMutations": [10, 0, 0, 0, 0, 0, 0, 0, 4, 0, 0, 0],
      "ancestors": [{"generation":0,"name":"..."}],
      "dinoId1": 397174429, "dinoId2": 187449547,
      "randomMutationsMale": 96, "randomMutationsFemale": 6,
      "tribeId": 1589589881,
      "cryoVersion": 7,
      "downloadedAtMs": 1785682889465,
      "packedAtWorldSec": 222956547.000,
      "containerId": "63420bb18fd01a4c...",
      "containerType": "fridge",
      "containerName": "焦土常用",
      "containerClass": "PrimalInventoryBP_CryoFridge_C1",
      "containerTribe": 1589589881
    }
  ]
}
```

**`cryopod[]` 关键字段**：
| 字段 | 说明 |
|------|------|
| dinoId1 / dinoId2 | 龙 ID（`dinoId1=0` 为空球） |
| containerId | 容器（inventory）UUID（hex，32 字符） |
| containerType | `fridge`(冰箱) / `display`(展示台) / `stand`(宠物台) / `storage`(储物箱) / `player`(玩家背包) / `other` / `unknown` |
| containerName | 玩家给容器起的名字（BoxName） |
| **containerClass** | 容器真实类名（如 `PrimalInventoryBP_CryoFridge_C1`、`InventoryComponent_CryoHospital`），前端可据此识别未知容器 |
| containerTribe | 容器所属部落 ID |
| tribeId | 龙本身所属部落 ID |
| **downloadedAtMs** | **下载进服时间（可靠绝对时间）**（Unix 毫秒，球内 custom data `[02][timestamp]`）。**仅 v7 新格式球内有**；空球 / v6 老格式球 / 宠物台 / 系统单位为 0 |
| **packedAtWorldSec** | **原服收球/收纳时间（原始世界秒，排序用）**（`DinoDownloadedAtTime`，球内与宠物台都有）。球内=收球时间、宠物台=上架时间。**仅用于排序**，跨服不可比、不可换算墙钟时间 |

**`tribes` 段**（部落映射，`<tribeId>` 为字符串键）：
```json
"<tribeId>": {"name": "部落名", "ownerName": "部落长名", "members": ["成员1","成员2",...]}
```

> 前端过滤"部落长=XX"：遍历 `tribes`，取 `ownerName == "XX"` 的 tribeId 集合，再据此过滤 `dinos[].tribeId` / `cryopod[]`。

### 5.3 宠物台（stand）多宠物

一个宠物架可放多个宠物（每个宠物一个 zlib 流），`cryopod` 里会生成**多个记录**，共享同一 `containerId`，`containerClass = "ShoulderPetDisplayStand"`，`containerType = "stand"`。

### 5.4 时间戳语义（2026-08-06 定稿）

> 最终方案：**球内同时显示「可靠绝对时间」与「收纳/收球世界秒」；其他容器（宠物台）只显示「收纳世界秒」；tamed 只显示「下载/驯服世界秒」**（用于排序）。字段名：`downloadedAtMs`（Unix 毫秒，仅球内可靠）+ `packedAtWorldSec`（收纳世界秒，cryo 球内+宠物台）+ `downloadedAtWorldSec`/`tamedAtWorldSec`（tamed 放出龙）。

| 字段 | 所在数据 | 语义 | 何时更新 |
|------|---------|------|---------|
| `downloadedAtMs` | **仅 cryo.json 球内**（v7 新格式球，custom data `[02][timestamp]`） | **下载进服时间（可靠绝对时间，Unix 毫秒）** | 仅真·下载龙（upload/download transfer）时更新 |
| `packedAtWorldSec` | **仅 cryo.json 球内+宠物台** | **原服收球/收纳时间（原始世界秒，`DinoDownloadedAtTime`）**：球内=收球时间、宠物台=上架时间 | 龙在原服被收球/上架时更新（跨服携带不重写） |
| `downloadedAtWorldSec` | **仅 tamed.json 放出龙 / ArkGetDino** | **下载进服时间（原始世界秒，`DinoDownloadedAtTime`）** | 仅真·下载龙时更新 |
| `tamedAtWorldSec` | tamed.json 放出龙 / ArkGetDino | **驯服时间（原始世界秒，`TamedAtTime`）** | 驯服/繁殖时设置 |

**为什么世界秒不能换算成墙钟时间（重要）**：
- 世界秒是服务器自身的世界时钟（world clock），**不同服务器时间流速不同**，且基准（epoch）因存档继承不同而各异（本服从 ASE 时代继承，各龙换算出的 epoch 从 2017 到 2020 都有，证明不可靠）
- 因此 `packedAtWorldSec`（球内/宠物台）与 `downloadedAtWorldSec`（tamed）都**只用于排序**，不做任何墙钟换算；跨服不可比
- 唯一的**可靠绝对时间**是球内 custom data 的 Unix 秒（`downloadedAtMs`）——它是真实 Unix 时间戳，跨服可比、可直接格式化显示

**重要行为**（实服验证）：
- **装球 / 放出 / 带球转服（cryopod 当物品携带）都不更新**这个时间戳
- 只有**真·下载龙**（上传到方舟/从别服下载 dino 本体）才会刷新
- 例：大盗四 2025-03-25 下载进服，前天在 Ext 装球 + 带球转 Sco，时间戳仍为 2025-03-25；粉鲨是老龙但 2026-08-02 时间 = 最近真·下载进 Ext
- **系统单位**（HelperBot / Train / Oasisaur 等）时间戳无意义，前端应留空

**本地龙 vs 下载龙（放出龙）**：
- **跨服下载的龙**：`downloadedAtWorldSec` 有值（下载进服时间），`tamedAtWorldSec` 为 0
- **本地驯养/繁殖的龙**：`downloadedAtWorldSec` 为哨兵 0（从未跨服下载），`tamedAtWorldSec` **有值**（驯服/出生时间）
- 前端展示放出龙时间时：优先 `downloadedAtWorldSec`，为 0 则用 `tamedAtWorldSec`（两者都是世界秒，仅排序）
- ⚠️ **球内/宠物台读不到驯服时间**（2026-08-06 验证）：球内与宠物台的 DinoData 序列化都不携带 `TamedAtTime`（Sco+Ext 共 1987 球 6 宠物台全部 tamed=0、raw=0），只有 live 放出龙能读到。球内/宠物台只有 `downloadedAtMs` + `packedAtWorldSec`

> ⚠️ **ASE 遗留脏数据（重要）**：ASA（Ark: Survival Ascended）于 **2023-10-25** 上架。**早于此日期的 `downloadedAtMs` 均为 ASE 旧存档迁移的脏数据，无效**（例如存档中会出现 2017/2018 年的时间戳）。前端处理 `downloadedAtMs` 时必须加阈值：`ms < 2023-10-25` 视为无效，显示为空、不参与 24h 判断。`packedAtWorldSec` / `downloadedAtWorldSec` 是原始世界秒（数值量级远小于 Unix 秒），不适用此阈值，直接排序即可。

**`downloadedAtMs` 为 0 / 缺失 / 无效的情况**（无法判断时间，前端应跳过）：
1. **空球**（`dinoId1=0`）——无龙自然无时间
2. **v6 老格式球**（`cryoVersion=6`）——custom data 无 `[02][timestamp]` 结构
3. **宠物台**（`containerType=stand`）——走独立解析路径，只有 `packedAtWorldSec`（上架时间）
4. **早于 2023-10-25**——ASE 遗留脏数据，无效
5. **系统单位**（HelperBot / Train / Oasisaur）——非玩家驯养单位，无意义

> 💡 **建议**：前端筛「24h 新增下载进服的龙」时——**只能依据球内的 `downloadedAtMs`**（可靠绝对时间）；tamed 的世界秒 `downloadedAtWorldSec` / 球内、宠物台的 `packedAtWorldSec` 仅用于同一服务器内的新旧排序，不能跨服比较，也不参与「24h」判断。

---

## 6. 前端调用建议

1. **实时查询单龙**：RCON `TransferIdentityFix.ArkGetDino <id1> <id2>`（放出的龙）/ `DinoMut`（任意龙）
2. **批量清单**：直接读 Qsync 同步的 `<缩写>_tamed.json` + `<缩写>_cryo.json`（本地文件，快且不占 RCON）
3. **部落归属**：用 cryo 的 `tribes` 段建立 `tribeId → {部落名, 部落长, 成员}` 映射
4. **容器识别**：优先用 `containerClass`（真实类名），`containerType` 作分类兜底
5. **触发刷新**：RCON `ArkTamedDinos` 触发 tamed 重写；cryo 随服务器保存自动更新

---

## 7. 附：聊天命令（游戏内 /tif）

| 命令 | 权限 | 说明 |
|------|------|------|
| `/tif ping` | viewer | 连通测试 |
| `/tif status [player]` | viewer | 玩家身份链快照 |
| `/tif refresh [player]` | operator | 手动跑恢复链 |
| `/tif autorefresh [player]` | operator | 排队自动刷新 |
| `/tif probeuserpath [player]` | viewer | 门访问链探针 |
| `/tif autorecover` | operator | 重连模式恢复 |
| `/tif reload` | operator | 热重载配置 |
| `/tif trace <msg>` | operator | 记录 MOD 日志 |
| `/tif debug.chat on\|off` | operator | 聊天回显开关 |
