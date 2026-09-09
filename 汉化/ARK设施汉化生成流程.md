# ARK 设施汉化生成流程（facility_zh.json）

> 目的：参照 `icon_zh_map.json` 生成流程（`ARK汉化更新流程.md`），从 ARK 游戏文件的中英对照文本中，单独提取**设施/结构**名映射，生成 `facility_zh.json`（设施权威中文表，供 dino-import 聚落设施 chips 汉化）。
> 输出：`汉化/facility_zh.json` + `汉化/facility_zh.review.txt`（未命中待补名单）。

---

## 0. 数据源（与 icon_zh_map 同一套，游戏更新后同步刷新）

| 源 | 说明 | 获取方式 |
|---|---|---|
| `ShooterGame.po` | 英文原文（含 msgctxt `Content,<数字ID>`） | `ARK汉化更新流程.md` 第 4~5 步（从 Devkit `en/ShooterGame.po` 复制到 `汉化/`） |
| `ShooterGame.json` | 中文键值（`{Content:{数字ID: 中文}}`） | 同上（`ShooterGame.locres` 用 FModel 导出 JSON 后复制到 `汉化/`） |
| （可选）真实设施 | 11 服 `cryo facilities` class | 脚本 `--fetch` 自动拉线上，无需手工 |

> 两个源文件通常已在 `汉化/` 目录就绪（与 `_build_icon_zh_map.py` 共用）。

## 1. 运行生成脚本

```powershell
Push-Location "b:\项目\Hass ASA Server Monitor"

# 仅内置核心设施（快速，约 50 条，秒级）
.\.venv-1\Scripts\python.exe "汉化\_build_facility_zh.py"

# 并入 11 服真实在用设施（推荐，覆盖玩家实际放置的 class，约 30~60s）
.\.venv-1\Scripts\python.exe "汉化\_build_facility_zh.py" --fetch
```

输出样例（`facility_zh.json`）：
```json
{
  "IndustrialForge": { "en": "Industrial Forge", "zh": "工业熔炉[Industrial Forge]" },
  "Fabricator":      { "en": "Fabricator", "zh": "机床" },
  "ChemBench":       { "en": "Chemistry Bench", "zh": "化学实验桌[Chemistry Bench]" }
}
```

> 说明：`zh` 保留 `[英文]` 后缀是刻意的——与 `icon_zh_map.json` 高质量键同款，前端 `zhName` 的正则会截取 `[` 之前的中文，多留信息无害。

## 2. 审阅未命中名单（每次必做）

打开 `汉化/facility_zh.review.txt`，逐条处理（未命中一般两类）：
- **英文名对不上**（游戏内另有叫法，如 `Bed_Modern` → PO 里是别的名）：在脚本 `BASE_FACILITIES` 加正确别名后重跑；
- **中文缺失/同英文**（PO 有词条但中文源空）：直接手工补 `facility_zh.json` 或确认该设施在游戏中可忽略。

## 3. 上传服务器 + 打包

```powershell
# ① 上传到 asa-data（供 HA 旧架构/后台与 dino 拉取）
.\.venv-1\Scripts\python.exe -c "import paramiko;h='192.168.197.253';t=paramiko.Transport((h,22));t.connect(username='root',password='1219Wu1219@');s=paramiko.SFTPClient.from_transport(t);s.put('汉化/facility_zh.json','/config/www/asa-data/facility_zh.json');s.close();t.close();print('OK')"

# ② 若前端已接入：把 facility_zh.json 加入打包拉取清单（_sync_repack2.py 的 STATIC 列表加一行）→ 部署 CF
C:\Python312\python.exe "b:\项目\Hass ASA Server Monitor\tmp\_deploy_cf.py"
```

> 前端接入方案见 `20260909_设施汉化方案.md`（`lbFacilityName(cls)` 查询 + chip 中英同排），表本身不发版即可维护——改词条只重跑本流程上传。

## 4. 常见问题

| 问题 | 处理 |
|---|---|
| 找不到 `ShooterGame.po/.json` | 先按 `ARK汉化更新流程.md` 第 4~5 步获取游戏本地化源 |
| `--fetch` 拉取失败 | 网络问题，忽略即可（仍用内置清单）；或改日重试 |
| 命中但中文带多义词串 | 取 `[ ]` 前主名即可；仍不佳则手工修正该条 |
| 游戏大更新新增结构 | 先刷新 `.po/.json` 源 → 重跑本脚本 → review 补新条目 → 上传 |

## 5. 更新时机
与 `icon_zh_map.json` 同步：**ARK 游戏每次大版本更新后**刷新 `.po/.json` 源并重跑本流程一次（约 5 分钟），保持设施表与游戏同步。
