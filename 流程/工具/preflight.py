# -*- coding: utf-8 -*-
# 新增生物·一键体检（输入类名，六项状态一表出）
# 用法: python 流程\工具\preflight.py Boaratos_Character_BP_C
import io, os, re, sys, json, time, glob, gzip
from urllib.request import Request, urlopen

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
OUT = os.path.join(HERE, '_last_preflight.txt')
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

L = []
def w(s):
    L.append(s)
    print(s)

def raw_contains(path, needle, maxmb=300):
    try:
        if os.path.getsize(path) > maxmb * 1024 * 1024:
            return None
        t = io.open(path, 'rb').read().decode('utf-8', 'ignore')
        return needle.lower() in t.lower()
    except Exception:
        return False

def main():
    if len(sys.argv) < 2 or not sys.argv[1].strip():
        w('[用法] python preflight.py <类名，如 Boaratos_Character_BP_C>')
        dump()
        return
    cls = sys.argv[1].strip()
    stem = cls[:-2] if cls.endswith('_C') else cls
    species = stem.split('_')[0]
    w('[输入] %s | 词干=%s | 物种名=%s' % (cls, stem, species))
    w('[时间] ' + time.strftime('%Y-%m-%d %H:%M:%S'))
    w('--- ① 物种库（ASB）---')
    for p in [r'p:\私人共享\ASA\DinoExports\ASA-values.json',
              r'p:\私人共享\ASA\DinoExports\values.json',
              r'b:\项目\引用\ARKStatsExtractor-dev\ARKBreedingStats\json\values\ASA-values.json',
              r'b:\项目\引用\ARKStatsExtractor-dev\ARKBreedingStats\json\values\values.json']:
        if os.path.exists(p):
            c = raw_contains(p, species, 100)
            w('  %s | %s | mtime=%s' % (p, ('含 ' + species) if c else '不含', time.strftime('%m-%d %H:%M', time.localtime(os.path.getmtime(p)))))
        else:
            w('  缺失: %s' % p)

    html = os.path.join(ROOT, 'dino-import.html')
    htmltext = io.open(html, 'r', encoding='utf-8', errors='ignore').read() if os.path.exists(html) else ''
    q = "'%s'" % cls
    w('--- ② 翻译 ---')
    w('  html 含类名字面量 %s : %s' % (q, '是' if q in htmltext else '否'))
    sj = os.path.join(ROOT, '汉化', 'ShooterGame.json')
    if os.path.exists(sj):
        w('  ShooterGame.json 含 %s : %s' % (species, '是' if raw_contains(sj, species, 200) else '否'))
    izh = os.path.join(ROOT, '汉化', 'icon_zh_map.json')
    if os.path.exists(izh):
        w('  icon_zh_map.json 含 %s : %s' % (species, '是' if raw_contains(izh, species, 50) else '否'))

    w('--- ③ 图标键（icons2.json）---')
    icon_hits = []
    ic = os.path.join(ROOT, '汉化', 'icons2.json')
    if os.path.exists(ic):
        try:
            d = json.load(io.open(ic, 'r', encoding='utf-8-sig'))
            seq = d if isinstance(d, list) else list(d.values())
            for e in seq:
                if not isinstance(e, dict):
                    continue
                nm = str(e.get('name', ''))
                if species.lower() in nm.lower():
                    icon_hits.append((nm, str(e.get('url', ''))))
            w('  命中 %d 条' % len(icon_hits))
            for nm, u in icon_hits[:6]:
                w('    - %s | %s' % (nm, u))
        except Exception as ex:
            w('  读取失败: %r' % ex)
    else:
        w('  缺失: %s' % ic)

    w('--- ④ R2 源图（HTTP 校验）---')
    url = ''
    for nm, u in icon_hits:
        if 'biology' in u.lower():
            url = u
            break
    if not url:
        url = 'https://img.whiterober.ccwu.cc/ASA/biology/%s.png' % species
    try:
        req = Request(url, method='GET', headers={'User-Agent': 'Mozilla/5.0'})
        r = urlopen(req, timeout=8)
        data = r.read(64)
        w('  %s -> %s | %dB（前64字节）' % (url, r.status, len(data)))
    except Exception as ex:
        w('  %s -> 请求失败: %r' % (url, ex))

    w('--- ⑤ 缩略图（webp_map）---')
    for p in [os.path.join(ROOT, 'tmp', 'webp_map.json'), os.path.join(ROOT, '汉化', 'webp_map.json')]:
        if os.path.exists(p):
            w('  %s | 含 %s : %s' % (p, species, '是' if raw_contains(p, species, 50) else '否'))
        else:
            w('  缺失: %s' % p)

    w('--- ⑥ 归属（白名单/翻译表）---')
    for arr, span in [('LB_TAMEABLE_FORCE', 20000), ('LB_EXTRA_FORCE', 20000), ('LB_OWNED_UNITS', 12000), ('LB_TEST_EXTRA', 8000), ('LB_STEAL_EGG', 4000), ('LB_CATCHABLE_FISH', 6000), ('LB_SPECIAL_NAMES', 30000)]:
        i = htmltext.find(arr)
        seg = htmltext[i:i + span] if i >= 0 else ''
        w('  %s 含类名: %s' % (arr, '是' if (cls in seg or q in seg) else '否'))
    w('  归类判据（用户口径 2026-10-16）: ASB 无数据→「预览」组（LB_TEST_EXTRA）；有数据→按情况（偷蛋→LB_STEAL_EGG；载具→LB_OWNED_UNITS；渔获→LB_CATCHABLE_FISH）')

    w('--- ⑦ 导出数据（P:\\私人共享\\ASA\\DinoData）---')
    dd = r'p:\私人共享\ASA\DinoData'
    files = []
    if os.path.isdir(dd):
        for pat in ('*_cryo.json.gz', '*_tamed.json.gz'):
            files.extend(glob.glob(os.path.join(dd, pat)))
    files = sorted(set(files), key=os.path.getmtime, reverse=True)[:30]
    nb = species.encode('utf-8', 'ignore').lower()
    hits, scanned = [], 0
    for f in files:
        scanned += 1
        try:
            total = 0
            buf = b''
            with gzip.open(f, 'rb') as g:
                while True:
                    chunk = g.read(4 * 1024 * 1024)
                    if not chunk:
                        break
                    total += len(chunk)
                    buf = (buf[-64:] + chunk)
                    if nb in buf.lower():
                        hits.append('%s (%s)' % (os.path.basename(f), time.strftime('%m-%d %H:%M', time.localtime(os.path.getmtime(f)))))
                        break
                    if total > 100 * 1024 * 1024:
                        break
        except Exception:
            pass
    w('  扫描 %d 个文件（按 mtime 取最新 30），命中 %d 个：%s' % (scanned, len(hits), ', '.join(hits) if hits else '无'))
    w('--- 完成 ---')
    dump()

def dump():
    io.open(OUT, 'w', encoding='utf-8', newline='').write('\n'.join(L) + '\n')
    print('[结果文件] ' + OUT)

if __name__ == '__main__':
    main()
