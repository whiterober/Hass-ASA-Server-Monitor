# -*- coding: utf-8 -*-
# 新增生物·S0 前置：更新最新 ASB 相关文件（values.json / ASA-values.json，dev 分支）
# 规则：raw 直下 -> 版本对比防降级（远端不新则跳过）-> 备份 -> 覆盖（打包源 + 仓库镜像）
import io, os, re, sys, json, time, shutil
from urllib.request import Request, urlopen

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))          # b:\项目\Hass ASA Server Monitor
DEV = os.path.join(os.path.dirname(ROOT), '引用', 'ARKStatsExtractor-dev')
OUT = os.path.join(HERE, '_last_asb_update.txt')
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

BASE_URL = 'https://raw.githubusercontent.com/cadon/ARKStatsExtractor/dev/ARKBreedingStats/json/values/'
FILES = ['values.json', 'ASA-values.json']
ts = time.strftime('%Y%m%d_%H%M%S')
L = []
def w(s):
    L.append(s)
    print(s)

def ver_tuple(v):
    if not isinstance(v, str):
        return None
    parts = re.findall(r'\d+', v)
    if not parts:
        return None
    return tuple(int(x) for x in parts[:4])

def fetch(name):
    url = BASE_URL + name
    req = Request(url, method='GET', headers={'User-Agent': 'Mozilla/5.0', 'Accept': 'application/json'})
    with urlopen(req, timeout=25) as r:
        return r.read()

def stats(raw):
    try:
        d = json.loads(raw.decode('utf-8-sig'))
        sp = d.get('species')
        return d.get('version'), (len(sp) if isinstance(sp, list) else None)
    except Exception:
        return None, None

w('[时间] ' + time.strftime('%Y-%m-%d %H:%M:%S'))
w('[源] ' + BASE_URL)
updated = 0
for name in FILES:
    local_p = os.path.join(DEV, name)
    lb = io.open(local_p, 'rb').read() if os.path.exists(local_p) else None
    lv, lc = stats(lb) if lb else (None, None)
    w('--- %s ---' % name)
    if lb:
        w('  本地: version=%s species=%s mtime=%s' % (lv, lc, time.strftime('%Y-%m-%d %H:%M', time.localtime(os.path.getmtime(local_p)))))
    else:
        w('  本地: 缺失 %s' % local_p)
    try:
        rb = fetch(name)
    except Exception as e:
        w('  远端: 下载失败 %r -> 保持本地不变' % e)
        continue
    rv, rc = stats(rb)
    w('  远端: version=%s species=%s (%dB)' % (rv, rc, len(rb)))
    lvt, rvt = ver_tuple(lv), ver_tuple(rv)
    if lb is None:
        do, reason = True, '本地缺失'
    elif rvt is None or lvt is None:
        do, reason = False, '版本字段缺失，保守跳过（人工核对）'
    elif rvt > lvt:
        do, reason = True, '远端更新'
    else:
        do, reason = False, '远端不新（防降级）'
    if not do:
        w('  动作: 跳过 —— %s' % reason)
        continue
    if lb:
        shutil.copy2(local_p, local_p + '.bak_' + ts)
    io.open(local_p, 'wb').write(rb)
    w('  写入: %s（%dB，旧版备份 .bak_%s）' % (local_p, len(rb), ts))
    mirror = os.path.join(DEV, 'ARKBreedingStats', 'json', 'values', name)
    if os.path.isdir(os.path.dirname(mirror)):
        if os.path.exists(mirror):
            shutil.copy2(mirror, mirror + '.bak_' + ts)
        io.open(mirror, 'wb').write(rb)
        w('  镜像: %s' % mirror)
    updated += 1
w('')
w('[结果] 更新 %d 个文件；%s' % (updated, '请随下次部署（S6）使前端生效' if updated else '本地已是最新或未变更'))
io.open(OUT, 'w', encoding='utf-8', newline='').write('\n'.join(L) + '\n')
print('[结果文件] ' + OUT)
