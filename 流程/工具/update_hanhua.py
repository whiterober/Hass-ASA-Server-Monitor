# -*- coding: utf-8 -*-
# 新增生物·S0b 前置：更新汉化数据（FModel 导出 → zh JSON + en PO → icon_zh_map.json → 部署源 + HA）
# 半自动引导流程（参考 汉化\ARK汉化更新流程.md）：
#   【手动】FModel 导出 ShooterGame.locres → JSON（A:\Output\Exports\...\zh\）
#   【自动】新鲜度检测 → 复制 zh JSON + en PO → 构建 icon_zh_map.json → 与 _upload 现行版合并
#           （保留人工补丁）→ 备份 → 写回 _upload → SFTP 上传 HA → 关键词搜索官方中文
# 用法: python 流程\工具\update_hanhua.py [附加搜索词...]
import io, os, re, sys, json, time, shutil, subprocess

BASE = r'b:\项目\Hass ASA Server Monitor'
H = os.path.join(BASE, '汉化')
TOOL_DIR = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(TOOL_DIR, '_last_hanhua_update.txt')
VENV_PY = os.path.join(BASE, '.venv-1', 'Scripts', 'python.exe')

SRC_ZH = r'A:\Output\Exports\ShooterGame\Content\Localization\ShooterGame\zh\ShooterGame.json'
SRC_PO = r'B:\Epic Games\ARKDevkit\Projects\ShooterGame\Content\Localization\ShooterGame\en\ShooterGame.po'
DST_ZH = os.path.join(H, 'ShooterGame.json')
DST_PO = os.path.join(H, 'ShooterGame.po')
BUILD = os.path.join(H, '_build_icon_zh_map.py')
BUILD_OUT = os.path.join(H, 'icon_zh_map.json')
UPLOAD = os.path.join(H, '_upload', 'icon_zh_map.json')
HA_PATH = '/config/www/asa-data/icon_zh_map.json'
HA_HOST, HA_USER, HA_PW = '192.168.197.253', 'root', '1219Wu1219@'
FORCE = '--force' in sys.argv
_args = [a for a in sys.argv[1:] if not a.startswith('--')]
SEARCH = (_args if _args else ['Gargantar', 'Cerberus', 'Cerberax'])

ts = time.strftime('%Y%m%d_%H%M%S')
L = []

def w(s):
    L.append(str(s))
    try:
        print(s)
    except Exception:
        pass

def mt(p):
    return os.path.getmtime(p) if os.path.exists(p) else 0

def fmt(m):
    return time.strftime('%Y-%m-%d %H:%M', time.localtime(m)) if m else '—'

w('=== 汉化数据更新（S0b） %s ===' % time.strftime('%Y-%m-%d %H:%M:%S'))
w('')
w('[输入检查]')
w('  FModel 导出 zh : %s' % (os.path.exists(SRC_ZH) and ('%s mtime=%s' % (SRC_ZH, fmt(mt(SRC_ZH)))) or '缺失（%s）' % SRC_ZH))
w('  项目 zh 现行   : %s' % fmt(mt(DST_ZH)))
w('  DevKit en PO   : %s' % (os.path.exists(SRC_PO) and ('%s mtime=%s' % (SRC_PO, fmt(mt(SRC_PO)))) or '缺失（%s）' % SRC_PO))
w('  项目 PO 现行   : %s' % fmt(mt(DST_PO)))

need_zh = os.path.exists(SRC_ZH) and mt(SRC_ZH) > mt(DST_ZH)
need_po = os.path.exists(SRC_PO) and mt(SRC_PO) > mt(DST_PO)

if not (need_zh or need_po) and not FORCE:
    w('')
    w('[结果] 未检测到更新的导出（FModel 输出 / DevKit PO 均不新于项目现行版）')
    w('')
    w('── 请在 FModel 手动导出（完整流程见 汉化\\ARK汉化更新流程.md）──')
    w('  1. 双击打开 FModel.exe')
    w('  2. 浏览并选择 ARK 汉化补丁（.pak / .ucas）所在文件夹')
    w('  3. 引擎版本选择 UE5_2（ARK ASA 所用版本）')
    w('  4. 导航到: ShooterGame/Content/Localization/ShooterGame/zh/ShooterGame.locres')
    w('  5. 右键 ShooterGame.locres → 保存为 JSON')
    w('  6. 确认导出位置: A:\\Output\\Exports\\ShooterGame\\Content\\Localization\\ShooterGame\\zh\\')
    w('  7. 回到本任务重新运行（python 流程\\工具\\update_hanhua.py）')
    w('')
    w('[说明] 若汉化补丁内也有新的 en（英文）导出需要更新，流程相同（语言文件夹换 en）。')
else:
    if FORCE:
        # 强制模式：源存在即重走复制+构建链（用于「导出已完成但 mtime 相同」或复验场景）
        need_zh = need_zh or os.path.exists(SRC_ZH)
        need_po = need_po or os.path.exists(SRC_PO)
    w('')
    w('[复制输入]' + ('（--force 强制模式）' if FORCE else ''))
    if need_zh:
        if os.path.exists(DST_ZH):
            shutil.copy2(DST_ZH, DST_ZH + '.bak_' + ts)
        shutil.copy2(SRC_ZH, DST_ZH)
        w('  zh: 已复制 → %s（旧版备份 .bak_%s）' % (DST_ZH, ts))
    else:
        w('  zh: 无需更新')
    if need_po:
        if os.path.exists(DST_PO):
            shutil.copy2(DST_PO, DST_PO + '.bak_' + ts)
        shutil.copy2(SRC_PO, DST_PO)
        w('  PO: 已复制 → %s（旧版备份 .bak_%s）' % (DST_PO, ts))
    else:
        w('  PO: 无需更新')

    w('')
    w('[构建 icon_zh_map.json]（%s）' % VENV_PY)
    build_ok = False
    if not os.path.exists(VENV_PY):
        w('  ✗ venv python 缺失: %s' % VENV_PY)
    else:
        env = dict(os.environ, PYTHONIOENCODING='utf-8')
        try:
            r = subprocess.run([VENV_PY, BUILD], capture_output=True, cwd=BASE, env=env, timeout=900)
            bout = (r.stdout or b'').decode('utf-8', 'replace')
            berr = (r.stderr or b'').decode('utf-8', 'replace')
            w('  返回码 %d；stdout 尾 500 字:' % r.returncode)
            w('  ' + bout[-500:].replace('\n', '\n  '))
            if r.returncode == 0:
                build_ok = True
            else:
                w('  构建失败！stderr 尾 800 字:')
                w('  ' + berr[-800:].replace('\n', '\n  '))
        except Exception as e:
            w('  构建异常: %r' % e)

    if not build_ok:
        w('')
        w('[中止] 构建未成功 —— _upload/icon_zh_map.json 未改动（输入文件已复制到项目）')
    else:
        build = json.load(io.open(BUILD_OUT, encoding='utf-8'))
        old = {}
        if os.path.exists(UPLOAD):
            old = json.load(io.open(UPLOAD, encoding='utf-8'))
            shutil.copy2(UPLOAD, UPLOAD + '.bak_' + ts)
        # 合并：构建为底 + _upload 现行版覆盖（保留人工补丁/清洗；新键自动带上）
        merged = dict(build)
        merged.update(old)
        new_keys = sorted(k for k in build if k not in old)
        val_diff = sorted(k for k in build if k in old and build[k] != old[k])
        w('')
        w('[合并 _upload 现行版]')
        w('  构建键数 %d；_upload 旧键数 %d；新增键 %d；值差异(保留 _upload 旧值) %d' % (len(build), len(old), len(new_keys), len(val_diff)))
        w('  新增键（前 30）: %s' % json.dumps(new_keys[:30], ensure_ascii=False))
        if val_diff:
            w('  值差异清单（前 20，均保留 _upload 旧值——属历史人工清洗；如含官方修正需人工确认）:')
            for k in val_diff[:20]:
                w('      %s: 构建="%s" / 现行="%s"' % (k, build[k], old[k]))
        with io.open(UPLOAD, 'w', encoding='utf-8') as f:
            json.dump(merged, f, ensure_ascii=False, separators=(',', ':'))
        w('  已写回 %s（%d 键，旧版备份 .bak_%s）' % (UPLOAD, len(merged), ts))

        w('')
        w('[上传 HA（供 ASA 后台）]')
        try:
            import paramiko
            t = paramiko.Transport((HA_HOST, 22))
            t.connect(username=HA_USER, password=HA_PW)
            s = paramiko.SFTPClient.from_transport(t)
            s.put(UPLOAD, HA_PATH)
            s.close()
            t.close()
            w('  已上传 %s' % HA_PATH)
        except Exception as e:
            w('  ⚠️ HA 上传失败（本地已写好，另行处理）: %r' % e)

# 关键词搜索（官方中文）——公共尾段（更新与否都执行）
#   源1 = ShooterGame.json 官方导出（权威；值形如「中文[英文]」，不依赖 en PO）
#   源2 = icon_zh_map（提取映射；依赖 PO 双侧匹配——PO 落后于游戏版本时新词条会缺，以源1 为准补录小写键）
w('')
w('[关键词搜索（官方中文，供词典补录）]')
if os.path.exists(DST_ZH):
    try:
        dzh = json.load(io.open(DST_ZH, encoding='utf-8')).get('Content', {})
        for kw in SEARCH:
            hits = sorted((k, v) for k, v in dzh.items() if isinstance(v, str) and kw.lower() in v.lower())
            w('  ▸ [官方导出] %s：命中 %d' % (kw, len(hits)))
            for k, v in hits[:20]:
                w('      %s = %s' % (k, v))
    except Exception as e:
        w('  [官方导出] 读取失败: %r' % e)
target = UPLOAD if os.path.exists(UPLOAD) else (BUILD_OUT if os.path.exists(BUILD_OUT) else None)
if not target:
    w('  [icon_zh_map] 无可用数据文件')
else:
    d = json.load(io.open(target, encoding='utf-8'))
    for kw in SEARCH:
        low = kw.lower()
        hit_k = sorted(k for k in d if low in k.lower())
        hit_v = sorted((k, v) for k, v in d.items() if isinstance(v, str) and low in v.lower())
        w('  ▸ [icon_zh_map] %s：键命中 %d / 值命中 %d' % (kw, len(hit_k), len(hit_v)))
        for k in hit_k[:12]:
            w('      [键] %s = %s' % (k, d[k]))
        for k, v in hit_v[:12]:
            w('      [值] %s = %s' % (k, v))
w('')
w('[完成] 下一步：用上述官方中文补录 汉化\\item_zh.json → bump LB_VERSION + pwa/sw.js → tmp\\_deploy_cf.py')

io.open(OUT, 'w', encoding='utf-8', newline='').write('\n'.join(L) + '\n')
print('DONE')
