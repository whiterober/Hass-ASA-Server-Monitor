# 方案：本机 MOD / 汉化包状态动态显示 + 部署入口门控

> 版本：**v2**（2026-11-10）
> 状态：**待你选样式，代码未动**
> 基线代码：`app_core.js`（v20261110-6486）
> 样式原型：`_preview_local_status_styles2.html`（6 个候选，双击浏览器打开）
> 旧版原型：`_preview_local_status_styles.html`（仅 A/B 两种，保留备查）

---

## 0. 两个需求的最终口径（已与你确认）

| 需求 | 口径 |
|---|---|
| **需求 1 · 本机状态动态显示** | 检测到本机信息就显示在卡片上；**显示粒度 = 已装 fid + 大小 + 旧版个数和占用** |
| **需求 2 · 部署入口门控** | **非 Windows，或浏览器不支持目录 API ⇒ 都隐藏**这两个「部署到本机」<br>（此前我误读成"非 Win 也要显示"，已纠正） |

---

## 1. 静默探测能否省掉手动选目录？

**结论：能省掉大部分，但有两条硬边界省不掉。**

### 1.1 现状：免选目录**已经实现了**

`lbLocalEnsure()`（`app_core.js:54920` 附近）：

```
读 IndexedDB(lbLocalDeploy / asaLib) 拿回句柄
  → queryPermission({mode:'readwrite'})
      → 若非 granted：requestPermission(...)
          → 若仍非 granted：lbLocalForget()（删记忆）→ 弹 showDirectoryPicker
      → 若 granted：reused = true，直接复用
```

所以「同浏览器、权限还在」时点「部署到本机」**不会弹目录框**。

### 1.2 省不掉的两种情况

| 场景 | 原因 |
|---|---|
| 首次 / 换设备 / 换浏览器 profile / 换域名 | `showDirectoryPicker()` 需要用户激活（user activation），无手势必抛错。浏览器硬限制 |
| 清过站点数据 / 撤销了文件系统权限 | 重新 `requestPermission()` 需要手势 |

### 1.3 静默探测的真实收益

不是「省掉选目录」，而是：

1. **提前可见**：打开页面就知道本机装了哪些 MOD、汉化包是否最新
2. **减少误点**：一眼看出「已是最新」
3. **明确指引**：无授权时直接显示「点一次「部署到本机」授权」

### 1.4 核心约束（最容易踩的坑）

**静默探测绝不能调用 `lbLocalEnsure()`。**

它对权限失败的处理是 `lbLocalForget()` —— **删除 IndexedDB 里记住的句柄**。
在无手势的页面加载时机调用，等于**自毁记忆**，反而导致下次必须重新选目录。

⇒ 必须新写只读探测：**只 `queryPermission`，绝不 `requestPermission`，绝不 `lbLocalForget`**。

---

## 2. 需求 1：本机状态动态显示

### 2.1 现有能力（可直接复用）

| 能力 | 函数 | 位置 |
|---|---|---|
| 句柄持久化 | `lbLocalIdbGet('asaLib')` / `lbLocalIdbSet` | 54841-54865 |
| 定位 ASA 根 | `lbLocalLocate(h)` | 54900 附近 |
| 找 `.pak`（深度已修到 6） | `lbLocalAnyPak(dir, 0)` | 55990 |
| 某 pid 的版本目录 | `lbLocalModDirs(gid, pid)` | 56005 |
| 目录大小统计 | `lbLocalDirStat(dirH, 0)` | 55900 附近 |
| 汉化 3 文件比对 | `lbLocalZhPaksSame(g, files)` | 55220 附近 |
| 策略内 MOD 清单 | `lbLocalModsPolicyPids(base, hd)` | 56020 附近 |
| 大小格式化 | `lbLocalFmt(n)` | — |

**缺口：**

1. `LB_LOCAL.game` 只在点「部署到本机」时才赋值 ⇒ **页面打开时不知道本机状态**
2. 没有任何 UI 承载
3. 无「重新检测」入口

### 2.2 新增只读探测 `lbLocalProbe(base, hd)`

```js
/* 只读探测。绝不 requestPermission、绝不 lbLocalForget。
   返回 { ok, why, game, mods, zh }
   ok=false 的 why：
     'api_unsupported'  浏览器不支持 showDirectoryPicker
     'no_handle'        从未授权过
     'perm_lost'        有记忆但权限已失效
     'bad_root'         记住的目录已不是 ASA 根
     'no_net'           拿不到策略清单（网络/鉴权） */
```

**流程：**

```
1) 能力/平台检测失败 → { ok:false, why:'api_unsupported' }
2) h = await lbLocalIdbGet('asaLib')        只读
   !h → { ok:false, why:'no_handle' }
3) p = await h.queryPermission({mode:'readwrite'})   只查，不请求
   p !== 'granted' → { ok:false, why:'perm_lost' }
4) g = await lbLocalLocate(h)
   !g → { ok:false, why:'bad_root' }        ← 不调用 lbLocalForget
5) pids = await lbLocalModsPolicyPids(base, hd)
   失败 → 汉化区块照常、MOD 区块 { ok:false, why:'no_net' }
6) 逐 pid：lbLocalModDirs → 逐目录 lbLocalAnyPak + lbLocalDirStat
7) 汉化：读 Content/Paks 下 LB_ZH_PKG_NAMES 三个文件（存在性 + 大小）
8) return { ok:true, game:g, mods, zh }
```

### 2.3 数据结构

```js
mods = [{
  pid: '877752',
  name: 'Fear Ascended',
  expectFid: '9411566',
  dirs: ['877752_9349437', '877752_9411566'],
  curInstalled: true,
  curBytes: 62400000,
  oldDirs: ['877752_9349437'],
  oldBytes: 812000000
}]

zh = {
  have: 3, need: 3,
  same: true,          // 三文件大小与本地包一致（本地包不可用时为 null）
  missing: [], diff: [],
  bytes: 129600000
}
```

### 2.4 UI 样式（6 个候选，**等你选**）

| 变体 | 形态 | 卡片增高 | 适合 |
|---|---|---|---|
| **A** | 底部整行，每 MOD 一行 | +50~70px | 一眼看全，MOD 少时最直观 |
| **B** | 标题行胶囊 + 点开明细 | ≈0 | 不想改变卡片高度 |
| **C** | 底部单行横排 | +28px | 极省空间，MOD 多时会挤 |
| **D** | 两列表格 | +50~70px | 对齐最整齐，宽屏最好看 |
| **E** | 徽章组（每 MOD 一个） | +34px | 最紧凑，适合 MOD 多 |
| **F** | 塞进底栏「部署到本机」后面 | ≈0 | 完全不新增行（但底栏会变长） |

**原型里每个变体都渲染了同一份示例数据，直接对比即可。**

**通用要求（无论选哪个）：**

- 状态色：正常 `#4ade80` / 警示 `#fbbf24` / 灰 `#6b7280`
- **禁止 `✓` `✗` 符号**，一律文字或 MDI 图标
- **只更新状态容器的 `innerHTML`**，不整卡重渲染（见 4.1 #1）

### 2.5 各状态文案（共用）

| 状态 | 文案 |
|---|---|
| 已授权正常 | `877752 · 已装 9411566（62.4 MB）· 另有旧版 1 个（774.4 MB）` |
| 未安装 | `本机未安装` |
| 从未授权 | `点一次「部署到本机」后可显示本机状态` |
| 权限已失效 | `权限已失效，点一次「部署到本机」重新授权` |
| 目录已失效 | `记住的目录已失效，按住 Shift 点「部署到本机」重新选择` |
| 网络异常 | `无法获取策略清单（网络问题），点「重新检测」重试` |
| 检测超时 | `检测超时，点「重新检测」重试` |
| 不支持 ASA | （按钮已隐藏，无需显示状态） |

### 2.6 刷新时机

| 时机 | 动作 |
|---|---|
| 卡片渲染后 | 异步探测（不阻塞首屏，`setTimeout 0`） |
| 部署成功 / 失败后 | 重探 |
| 清理旧版目录完成后 | 重探 |
| 用户点「重新检测」 | 重探（无需手势，只读操作） |

**防抖**：结果指纹（`pids + fid` 组合）相同且 60s 内不重复扫描；`LB_LOCAL_PROBE.busy` 保证并发 1 个。

---

## 3. 需求 2：部署入口门控（非 Windows / 不支持 API ⇒ 隐藏）

### 3.1 判定函数

```js
/* 当前设备是否支持「部署到本机」（ASA 客户端仅 Windows） */
function lbLocalSupported(){
  try {
    if (typeof window.showDirectoryPicker !== 'function') return false;   // 浏览器不支持目录 API
    var p = '';
    try { p = String((navigator.userAgentData && navigator.userAgentData.platform) || ''); } catch (e) {}
    if (!p) {
      var ua = String(navigator.userAgent || '');
      if (/Windows NT|Win64|WOW64/i.test(ua)) p = 'Windows';
    }
    return /^Windows/i.test(p);
  } catch (e) { return false; }
}
```

**说明：**
- `navigator.userAgentData.platform` 在 Chromium 系可靠；取不到时回退 UA 正则
- **VS Code 内置浏览器（Electron）UA 含 `Windows NT 10.0` ⇒ 判定为 Windows，正常显示**
- Mac / Linux / Android / iOS ⇒ `false` ⇒ 隐藏

### 3.2 实施位置

| 卡片 | 函数 | 行 |
|---|---|---|
| MOD | `lbUpdModsCardHtml()` | 7405 |
| 汉化包 | `lbUpdRender()` | 8352 |

**做法**：把这两个 `<a ... onclick="lbDeployLocal('mods'|'zh',this)">` 包进 `(lbLocalSupported() ? '...' : '')`。

**必须在渲染时判断**（不能等探测完再隐藏，否则按钮会闪一下）。

### 3.3 布局影响

隐藏后，`lb-upd-foot` 里的 `.lb-foot-left`（`margin-right:auto`）消失 ⇒ 右侧按钮会靠右。
功能正常，视觉上底栏左侧留空 —— 可接受；若你觉得空，可加一行灰色小字
`当前设备不支持 ASA 客户端`（**默认不加**，按你的要求「看不到」）。

---

## 4. 全面复核：9 个补充点

### 4.1 必须修（否则出 bug）

| # | 问题 | 影响 / 对策 |
|---|---|---|
| **1** | **不能整卡重渲染** —— `lbUpdRender()` 会重建整个卡片 | 刷新状态时会**丢失滚动位置、折叠状态、输入内容**。⇒ 状态块放在独立容器，只更新它的 `innerHTML` |
| **2** | **汉化比对依赖服务端本地包清单** —— `lbLocalZhPaksSame(g, files)` 的 `files` 来自 `/api/pkg/local/list?kind=zh` | 本地包没下载时 `files` 为空 ⇒ **降级为「只查 3 个文件是否存在 + 大小」**，`same` 置 `null` |
| **3** | **平台门控必须在渲染时判断** | 否则按钮先显示、后消失（闪一下）。见 3.2 |
| **4** | **探测时机要防抖** | `lbUpdRender` 因任何状态变化都会被调用，每次探测会卡 ⇒ 结果指纹 + 60s 节流 + `busy` 锁 |

### 4.2 建议修

| # | 问题 | 对策 |
|---|---|---|
| **5** | **旧版大小统计有成本**（每个旧版目录递归算大小） | MOD 目录文件少（9~10 个）很快；但策略 MOD 多时会累加 ⇒ 总超时 20s，单 pid 失败不中断整体 |
| **6** | **token 可能未就绪**，`lbLocalProbe(base, hd)` 需要鉴权头 | MOD 区块降级为「无法获取策略清单（请稍后重试）」；**汉化区块不受影响**（不需要网络） |
| **7** | **隐藏按钮后底栏布局变化** | 见 3.3，可接受；如需可加灰色小字说明 |

### 4.3 可选

| # | 问题 | 对策 |
|---|---|---|
| **8** | 探测结果是否缓存 | 不缓存最准；若要缓存建议 TTL 30s，避免权限失效时显示旧数据误导 |
| **9** | 多标签页并发 | 已有 `LB_LOCAL.busy`，探测另加 `LB_LOCAL_PROBE.busy` |

---

## 5. 顺带修正：2 处过时 tooltip

MOD 卡「部署到本机」悬浮提示里有两句已与现状不符：

| 过时文案 | 实际（新）行为 |
|---|---|
| `自动跳过开场视频，再省约 740 MB` | **v6485 起客户端不再跳过**，完整写入 `Content/Movies/LoadingScreen.bk2` |
| `旧 <pid>_* 目录不会自动删除` | **v6481 起**先「干跑预演」列清单，用户点「确认清理」才删 |

**建议改为：**

```
· 完整写入包内所有文件（含开场视频 LoadingScreen.bk2）
· 旧 <pid>_* 目录：部署结束后弹出干跑清单，
  点「确认清理」才删除（浏览器删除不进回收站）
```

---

## 6. 实施步骤（**等你确认样式后执行**）

| # | 内容 | 文件 |
|---|---|---|
| 1 | `lbLocalSupported()` 门控函数 + 两处按钮条件渲染 | `app_core.js` |
| 2 | `LB_LOCAL_PROBE` 状态 + `lbLocalProbe()` 只读探测 | `app_core.js` |
| 3 | `lbLocalProbeRender(kind, res)` 渲染状态块（按选定样式） | `app_core.js` |
| 4 | MOD 卡 / 汉化卡插入状态容器（**不整卡重渲染**） | `app_core.js` |
| 5 | 卡片渲染后异步探测 + 「重新检测」链接 + 防抖 | `app_core.js` |
| 6 | 部署 / 清理完成后自动重探 | `app_core.js` |
| 7 | 修正 2 处过时 tooltip | `app_core.js` |

**验证清单：**

1. **有授权** → 打开页面自动显示「已装 xxx」，全程不点按钮
2. **无记忆**（清 IndexedDB `lbLocalDeploy`）→ 显示「点一次「部署到本机」」
3. **权限失效**（站点设置撤销文件系统权限）→ 显示「权限已失效」，**且 IndexedDB 里的句柄仍在**（证明没被 `lbLocalForget` 误删）
4. **非 Windows**（或改 UA 模拟）→ 两个按钮**都不显示**，页面其他功能正常
5. **部署后** → 状态自动刷新为新版本
6. **探测全程零写操作**：只 `queryPermission` + 读目录

---

## 7. 风险与限制

| 风险 | 说明 | 缓解 |
|---|---|---|
| **误删记忆** | 误用 `lbLocalEnsure` 做探测会 `lbLocalForget()` | 强制走独立 `lbLocalProbe`，代码评审把关 |
| **遍历耗时** | 多 MOD × 多版本目录递归 | 深度上限 6（已修）；总超时 20s；并发 1 |
| **权限提示时机** | 静默探测无法申请权限 | 明确提示「需点一次授权」，不强行 request |
| **旧版多时统计慢** | 每个旧版都要算大小 | 超时保护；失败只影响该行 |
| **非 Windows 误判** | UA 可能被改动 | 用 `userAgentData.platform` 优先，UA 兜底 |

---

## 8. 待你确认

1. **样式选哪个？**（A / B / C / D / E / F，或组合/微调意见）
2. **过时 tooltip 改不改？**（建议改）
3. 确认后按第 6 节 7 步实施，一次部署完成
