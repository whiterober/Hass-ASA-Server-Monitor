# -*- coding: utf-8 -*-
# 精简打包：只部署 dino 实际用到的 WebP 缩略图（icons2.json URL ∩ webp_map）
# 2026-09-20：静态表（9 表 + values/ASA-values）全部改为【本地供给】，不再连接 HA（不拉、不兜底）
import shutil, os, zipfile, io, json

BASE = r'b:\项目\Hass ASA Server Monitor'
shutil.copy2(os.path.join(BASE, 'dino-import.html'), os.path.join(BASE, 'dino-import-new.html'))

flat = os.path.join(BASE, r'tmp\dino-flat')
if os.path.exists(flat):
    shutil.rmtree(flat)
os.makedirs(flat, exist_ok=True)
shutil.copy2(os.path.join(BASE, 'dino-import-new.html'), os.path.join(flat, 'index.html'))

# 2026-08-29 PWA 文件（manifest / sw.js / 图标 → flat 根目录 + icons/）
_pwa = os.path.join(BASE, 'pwa')
shutil.copy2(os.path.join(_pwa, 'manifest.webmanifest'), os.path.join(flat, 'manifest.webmanifest'))
shutil.copy2(os.path.join(_pwa, 'sw.js'), os.path.join(flat, 'sw.js'))
os.makedirs(os.path.join(flat, 'icons'), exist_ok=True)
shutil.copy2(os.path.join(_pwa, 'icon-192.png'), os.path.join(flat, 'icons', 'icon-192.png'))
shutil.copy2(os.path.join(_pwa, 'icon-512.png'), os.path.join(flat, 'icons', 'icon-512.png'))
# 2026-09-11 v978：MDI 图标字体本地化（消除 cdn.jsdelivr.net 外链 —— 该 CSS 阻塞渲染，链路抖动时整页 JS 不执行）
_mdi = os.path.join(_pwa, 'mdi')
if os.path.isdir(_mdi):
    shutil.copytree(_mdi, os.path.join(flat, 'mdi'), dirs_exist_ok=True)
    print('MDI files copied')
else:
    print('WARN: pwa/mdi missing')
print('PWA files copied')

# 2026-08-28 地图 WebP（新架构 maps/ 目录，随 CF Pages 打包）：缩略 *_s.webp + 高清 *.webp（坐标浮窗用，去掉 _s）
# 源目录 tmp/dino-flat 会被 rmtree 重建，故每次打包前先由 _map_webp2.py + _map_hi2.py 生成到 tmp/dino-flat/maps，
# 这里直接复制 tmp/_map_assets/（统一源）确保可重复
_map_src = os.path.join(BASE, r'tmp\_map_assets')
if os.path.isdir(_map_src):
    shutil.copytree(_map_src, os.path.join(flat, 'maps'), dirs_exist_ok=True)
    print('maps copied from _map_assets')
else:
    # 兼容旧路径：直接从已生成的 maps 复制
    _map_existing = os.path.join(BASE, r'tmp\dino-flat\maps')
    if os.path.isdir(_map_existing):
        print('maps already in dino-flat')
    else:
        print('WARN: no maps source (_map_assets or dino-flat/maps)')

# ----------------------------------------------------------------
# 静态表：本地供给（2026-09-20 起，不再连 HA）
# 规则：缺任何一个立刻中止（不静默、不从 HA 兜底）
# 本地路径均已与 HA 现行版本核对 md5 一致；icon_anti_color.json 于 2026-09-20 从 HA 校准一次后本地为准
STATIC_SRC = {
    'icon_zh_map.json':     r'汉化\_upload\icon_zh_map.json',
    'gene_traits_zh.json':  r'tmp\gene_traits_zh.json',
    'dino_prefix_zh.json':  r'tmp\dino_prefix_zh.json',
    'dino_colors.json':     r'tmp\dino_colors.json',
    'icon_anti_color.json': r'icon_anti_color.json',
    'icons2.json':          r'汉化\icons2.json',
    'facility_zh.json':     r'汉化\facility_zh.json',
    'facility_official.json': r'汉化\facility_official.json',   # v3556：容器自带官中名（PO InventoryNameOverride/DescriptiveName 溯源）
    'item_zh.json':         r'汉化\item_zh.json',
    'itemstats.json':       r'汉化\itemstats.json',
    'values.json':          r'..\引用\ARKStatsExtractor-dev\values.json',
    'ASA-values.json':      r'..\引用\ARKStatsExtractor-dev\ASA-values.json',
    'lb_material.json':     r'lb_material.json',   # 2026-09-24 v3966：材质【唯一数据源】（332 项：材质/关键材料用量/来源/配方明细）
    'dino_rules.json':      r'dino_rules.json',    # 2026-09-25 v3996：规则名单【唯一数据源】（设施图标特例 116 + 生物判定 10 名单）
    'dino_rank_alias.json': r'dino_rank_alias.json', # 2026-10-01 v4217：装备榜鞍类名词干别名【唯一数据源】（stemFix 20 组；用户要求数据化、HTML 零硬编码）
}
_missing = []
for _f, _rel in STATIC_SRC.items():
    _sp = os.path.join(BASE, _rel)
    if not os.path.isfile(_sp):
        _missing.append('%s <- %s' % (_f, _rel))
        continue
    shutil.copy2(_sp, os.path.join(flat, _f))
    print('LOCAL %s <- %s' % (_f, _rel))
if _missing:
    raise SystemExit('ABORT: 缺少本地静态表（不兜底、不连 HA）: ' + '; '.join(_missing))
print('static tables: %d/%d from LOCAL' % (len(STATIC_SRC), len(STATIC_SRC)))

# 版本自检文件：dino-import.version（内容 = 当前 LB_VERSION；部署时自动生成，前端对比发现新版提示刷新）
import re
html = io.open(os.path.join(BASE, 'dino-import-new.html'), encoding='utf-8').read()
m = re.search(r"var LB_VERSION = '([^']+)'", html)
ver = m.group(1) if m else 'unknown'
io.open(os.path.join(flat, 'dino-import.version'), 'w', encoding='utf-8').write(ver)
print('version file: %s' % ver)

# 1. icons2.json URL 集合
icons = json.load(io.open(os.path.join(flat, 'icons2.json'), encoding='utf-8'))
urls = set()
for it in icons:
    if it.get('url'):
        urls.add(it['url'])
print('icons2 urls=%d' % len(urls))

# 2. webp_map 交集
webp_map = json.load(io.open(os.path.join(BASE, r'tmp\webp_map.json'), encoding='utf-8'))
need = {u: v for u, v in webp_map.items() if u in urls}
print('needed thumbs=%d' % len(need))

# 3. 复制需要的缩略图（webp_map 回 CF Pages）
thumb_src = os.path.join(BASE, r'tmp\webp96')
thumb_dst = os.path.join(flat, 'thumbs', 'webp96')
os.makedirs(thumb_dst, exist_ok=True)
copied = 0
for v in need.values():
    fname = v.split('/')[-1]
    sp = os.path.join(thumb_src, fname)
    if os.path.exists(sp):
        shutil.copy2(sp, os.path.join(thumb_dst, fname))
        copied += 1
print('copied=%d' % copied)

# 4. 精简 webp_map.json
io.open(os.path.join(flat, 'webp_map.json'), 'w', encoding='utf-8').write(json.dumps(need, ensure_ascii=False))

# 4.5 v1119：按类型生成资源包（packs/*.bin + assets.idx）——必须在 zip 之前（flat 目录每次 rmtree 重建，所以每次都要重新生成）
try:
    import subprocess, sys
    _pk = os.path.join(BASE, r'tmp\_pack_assets_v3.py')   # v1121：必拉集优先分包（thumbs part0=717、其余按需）
    if os.path.exists(_pk):
        _r = subprocess.run([sys.executable, _pk], capture_output=True, text=True, encoding='utf-8', errors='replace')
        print('PACK rc=%d' % _r.returncode)
        for _l in (('' + (_r.stdout or '')).splitlines()[:8]):
            print('  ' + _l)
        if _r.returncode != 0:
            print('  ERR: ' + ('' + (_r.stderr or ''))[:300])
    else:
        print('WARN: _pack_assets_v3.py missing')
except Exception as _e:
    print('PACK failed: %s' % _e)

# 5. 打包
zp = os.path.join(BASE, r'tmp\dino-flat.zip')
if os.path.exists(zp): os.remove(zp)
z = zipfile.ZipFile(zp, 'w', zipfile.ZIP_DEFLATED)
for root, dirs, files in os.walk(flat):
    for f in files:
        full = os.path.join(root, f)
        rel = os.path.relpath(full, flat)
        z.write(full, rel.replace('\\', '/'))
z.close()
io.open('b:/项目/Hass ASA Server Monitor/tmp/_repack_done.txt','w',encoding='utf-8').write('size=%d' % os.path.getsize(zp))
print('DONE size=%d' % os.path.getsize(zp))
