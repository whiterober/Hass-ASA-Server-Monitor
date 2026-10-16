# -*- coding: utf-8 -*-
# 新增生物·类名查询 —— 权威链: PO -> ShooterGame.json -> wiki/存档 -> ArkKit 兜底
# 用法: python 流程\工具\class_lookup.py <生物名(中文或英文，如 焰鬃野猪 / Boaratos)>
import io, os, re, sys, json, time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
OUT = os.path.join(HERE, '_last_class_lookup.txt')
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

L = []
def w(s):
    L.append(s)
    print(s)

def _unq(s):
    m = re.match(r'^"(.*)"\s*$', s.strip())
    return m.group(1) if m else s

def raw_contains(path, needle, maxmb=300):
    try:
        if os.path.getsize(path) > maxmb * 1024 * 1024:
            return None
        t = io.open(path, 'rb').read().decode('utf-8', 'ignore')
        return needle.lower() in t.lower()
    except Exception:
        return False

def parse_po(path):
    entries = []
    cur = None
    field = None
    def flush():
        if cur and (cur['key'] or cur['src'] or cur['msgid'] or cur['msgstr']):
            entries.append(dict(cur))
    with io.open(path, 'r', encoding='utf-8-sig', errors='replace') as f:
        for line in f:
            s = line.rstrip('\n')
            if s.startswith('#. Key:'):
                if cur is None:
                    cur = {'key': '', 'src': '', 'msgid': '', 'msgstr': ''}
                cur['key'] = s.split('Key:', 1)[1].strip()
                field = None
            elif s.startswith('#. SourceLocation:'):
                if cur is None:
                    cur = {'key': '', 'src': '', 'msgid': '', 'msgstr': ''}
                cur['src'] = s.split('SourceLocation:', 1)[1].strip()
                field = None
            elif s.startswith('msgid '):
                if cur is None:
                    cur = {'key': '', 'src': '', 'msgid': '', 'msgstr': ''}
                cur['msgid'] = _unq(s[6:])
                field = 'msgid'
            elif s.startswith('msgstr '):
                if cur is None:
                    cur = {'key': '', 'src': '', 'msgid': '', 'msgstr': ''}
                cur['msgstr'] = _unq(s[7:])
                field = 'msgstr'
            elif s.startswith('"') and cur is not None and field:
                cur[field] += _unq(s)
            elif s.strip() == '':
                flush()
                cur = None
                field = None
    flush()
    return entries

def cls_of(src):
    if not src:
        return ''
    seg = src.split('/')[-1]
    seg = seg.split('..')[0]
    seg = re.sub(r'\.(uasset|umap)$', '', seg)
    return seg

def main():
    t0 = time.time()
    if len(sys.argv) < 2 or not sys.argv[1].strip():
        w('[用法] python class_lookup.py <生物名(中文或英文)>')
        dump()
        return
    needle = sys.argv[1].strip()
    nl = needle.lower()
    w('[输入] ' + needle)
    w('[时间] ' + time.strftime('%Y-%m-%d %H:%M:%S'))

    po = os.path.join(ROOT, '汉化', 'ShooterGame.po')
    sj = os.path.join(ROOT, '汉化', 'ShooterGame.json')
    zhmap = {}
    if os.path.exists(sj):
        try:
            zhmap = json.load(io.open(sj, 'r', encoding='utf-8-sig'))
        except Exception as e:
            w('[警告] ShooterGame.json 读取失败: %r' % e)

    ents = []
    if os.path.exists(po):
        ents = parse_po(po)
        w('[PO] 条目 %d（耗时 %.1fs）' % (len(ents), time.time() - t0))
    else:
        w('[警告] PO 缺失: ' + po)

    hit1, hit2 = [], []
    for e in ents:
        if nl in e['msgid'].lower() or nl in e['msgstr'].lower():
            hit1.append(e)
        elif nl in e['src'].lower():
            hit2.append(e)
        if len(hit1) >= 400:
            break
    # 中文/描述通道：ShooterGame.csv（汉化 + 根目录 两份）-> Key 回查 PO
    keys = set()
    for csvp in (os.path.join(ROOT, '汉化', 'ShooterGame.csv'), os.path.join(ROOT, 'ShooterGame.csv')):
        if not os.path.exists(csvp):
            continue
        try:
            with io.open(csvp, 'r', encoding='utf-8-sig', errors='replace') as f:
                for line in f:
                    if needle in line:
                        for m in re.finditer(r'(\d{5,})', line.split(',')[0]):
                            keys.add(m.group(1))
                        if len(keys) >= 200:
                            break
        except Exception as e:
            w('[警告] CSV 读取失败: %r' % e)
    if keys:
        w('[CSV] 命中 Key x%d，回查 PO ...' % len(keys))
        for e in ents:
            if e['key'] in keys:
                hit1.append(e)
    # 词典通道：ShooterGame.json（嵌套 分类->{Key: 中文}）递归搜索
    json_hits = []
    if zhmap:
        try:
            for cat, sub in zhmap.items():
                if isinstance(sub, dict):
                    for k2, v2 in sub.items():
                        if isinstance(v2, str) and needle in v2:
                            json_hits.append((cat, str(k2), v2))
                            if len(json_hits) >= 20:
                                break
                elif isinstance(sub, str) and needle in sub:
                    json_hits.append(('(top)', str(cat), sub[:120]))
                if len(json_hits) >= 20:
                    break
        except Exception:
            pass
    if json_hits:
        w('[词典] ShooterGame.json 命中 %d 条：' % len(json_hits))
        for cat, k2, v2 in json_hits[:8]:
            ccls = ''
            for e in ents:
                if e['key'] == k2 and cls_of(e['src']):
                    ccls = ' | 类名: ' + cls_of(e['src'])
                    break
            w('  - [%s] Key=%s | %s%s' % (cat, k2, v2.strip()[:90], ccls))

    # ASB 通道：引用\ARKStatsExtractor-dev\{ASA-values,values}.json（S0 更新后的物种库，直出 blueprintPath 类名）
    asb_hits = []
    for af in ('ASA-values.json', 'values.json'):
        p = os.path.join(os.path.dirname(ROOT), '引用', 'ARKStatsExtractor-dev', af)
        if not os.path.exists(p):
            continue
        try:
            d0 = json.load(io.open(p, 'r', encoding='utf-8-sig'))
            for sp in (d0.get('species') or []):
                nm = str(sp.get('name', ''))
                bp = str(sp.get('blueprintPath', ''))
                if nl in nm.lower() or nl in bp.lower():
                    asb_hits.append((af, nm, bp))
                    if len(asb_hits) >= 20:
                        break
        except Exception as e:
            w('[警告] ASB 读取失败 %s: %r' % (af, e))
        if len(asb_hits) >= 20:
            break
    if asb_hits:
        w('[ASB] 命中 %d 条（物种库 %s）:' % (len(asb_hits), asb_hits[0][0]))
        for af, nm, bp in asb_hits[:10]:
            obj = bp.split('/')[-1].split('.')[-1] if bp else ''
            cls2 = (obj + '_C') if obj and not obj.endswith('_C') else obj
            w('  - [%s] %s | blueprintPath=%s | 类名≈%s' % (af, nm, bp[:110], cls2))

    for wf in ['wiki_item_ids.json', 'wiki_class_en.json']:
        p = os.path.join(ROOT, '汉化', wf)
        if os.path.exists(p):
            rc = raw_contains(p, nl, 200)
            if rc:
                w('[wiki] %s 含该名' % wf)

    html = os.path.join(ROOT, 'dino-import.html')
    htmltext = ''
    if os.path.exists(html):
        htmltext = io.open(html, 'r', encoding='utf-8', errors='ignore').read()

    # 补充通道 1：dino-import.html 手动表（LB_SPECIAL_NAMES 等）精确键值对
    html_hits = []
    if htmltext and needle in htmltext:
        pos = htmltext.find(needle)
        win = htmltext[max(0, pos - 800):pos + 400]
        for m in re.finditer(r"'([A-Za-z0-9_]{3,80})'\s*:\s*'([^']{0,200})'", win):
            c, v = m.group(1), m.group(2)
            if needle in v and ('Character' in c or c.endswith('_C') or c.endswith('_BP')) and c not in html_hits:
                html_hits.append(c)
    # 补充通道 2：icon_zh_map.json（图标名 -> 中文）
    izh_hits = []
    izp = os.path.join(ROOT, '汉化', 'icon_zh_map.json')
    if os.path.exists(izp):
        try:
            iz = json.load(io.open(izp, 'r', encoding='utf-8-sig'))
            for k, v in iz.items():
                if isinstance(v, str) and needle in v:
                    izh_hits.append((str(k), v))
                    if len(izh_hits) >= 10:
                        break
        except Exception:
            pass

    ranked = hit1 + hit2
    seen = set()
    out = []
    for e in ranked:
        c = cls_of(e['src'])
        if not c or c in seen:
            continue
        if not re.match(r'^[A-Za-z0-9_]+$', c) or len(c) > 64:
            continue
        seen.add(c)
        zh = zhmap.get(str(e['key']), '')
        inh = (("'%s'" % c) in htmltext) or (("'%s'" % (c if c.endswith('_C') else c + '_C')) in htmltext)
        cc = c if c.endswith('_C') else c + '_C'
        out.append('- 类名: %s | 带_C: %s | Key=%s | 官方中文=%s | dino-import 已含: %s | %s'
                   % (c, cc, e['key'], zh or '(无)', '是' if inh else '否', e['src'][:110]))
        if len(out) >= 15:
            break

    out.sort(key=lambda x: 0 if '_Character_BP' in x else 1)
    extra = []
    for c in html_hits:
        if not any(('类名: %s ' % c) in x for x in out):
            note = '' if c.endswith('_C') else '（BP 名缺 _C 请补）'
            extra.append('  - [html 表] %s%s' % (c, note))
    for k, v in izh_hits:
        tok = re.split(r'[ _]', k)[0]
        extra.append('  - [icon_zh_map] %s = %s（推断: %s_Character_BP_C，需核对）' % (k, v, tok))

    if out:
        w('[命中] %d 个候选（共 %d 条原始命中）:' % (len(out), len(ranked)))
        for x in out:
            w(x)
        if extra:
            w('[补充通道] %d 条:' % len(extra))
            for x in extra:
                w(x)
    elif extra or json_hits or ranked or asb_hits:
        if ranked:
            w('[PO原始命中] %d 条（可提取类名 0 条，多为宣传/文案）：' % len(ranked))
            for e in ranked[:5]:
                w('  - Key=%s | %s' % (e['key'], (e['msgid'] or e['msgstr'])[:110]))
        if extra:
            w('[补充通道] %d 条:' % len(extra))
            for x in extra:
                w(x)
        if asb_hits:
            w('[结论] 采用上方 [ASB] blueprintPath 的类名（<BP对象名>_C）；若与游戏内不一致，以游戏内 class 为准')
        else:
            w('[结论] 有命名/词典线索但 PO 无类名 —— ① 真身蓝图不在本地源（kit/PO 需更新）② 官方新内容待入库 ③ 可按规则推断类名 <Name>_Character_BP_C，需核对')
    else:
        w('[命中] PO/CSV/词典/wiki/html 均无 —— 尝试 ArkKit(DevKit) 兜底 ...')
        ark = r'B:\Epic Games\ARKDevkit'
        done = False
        if os.path.isdir(ark):
            cands = []
            rel = os.path.join(ark, 'Releases')
            if os.path.isdir(rel):
                for d in os.listdir(rel):
                    p = os.path.join(rel, d, 'Windows', 'AssetRegistry.bin')
                    if os.path.exists(p):
                        cands.append(p)
            nb = needle.encode('utf-8', 'ignore').lower()
            for p in cands:
                try:
                    b = io.open(p, 'rb').read()
                    idx = b.lower().find(nb)
                    if idx >= 0:
                        ctx = b[max(0, idx - 80):idx + 120].decode('utf-8', 'ignore')
                        w('[ArkKit] %s 命中 @%d: ...%s...' % (p, idx, ctx))
                        done = True
                except Exception as ex:
                    w('[ArkKit] 读取失败 %s: %r' % (p, ex))
        if not done:
            w('[ArkKit] 未命中。若为模组生物（如 Astraeos），类名在模组文件/服务器 Mods 目录，不在 DevKit —— 请提供模组线索。')
    w('[耗时] %.1fs' % (time.time() - t0))
    dump()

def dump():
    io.open(OUT, 'w', encoding='utf-8', newline='').write('\n'.join(L) + '\n')
    print('[结果文件] ' + OUT)

if __name__ == '__main__':
    main()
