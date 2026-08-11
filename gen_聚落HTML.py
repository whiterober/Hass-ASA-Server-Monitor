# -*- coding: utf-8 -*-
"""第二部分：聚落分组 HTML v2（分层：部落 -> 聚落 -> 容器 -> 生物）

改进（用户要求）：
  1. 只看指定部落（--tribe，默认基纽特战队）
  2. 聚落标题标注留痕者(owner)最多的前三名（差距太大者不显示）
  3. 聚落底下按容器分组（每个容器一个表）+ 放出生物一组

输入：--settle <聚类结果> --cryo <exe输出> --tamed <dll输出> --out <html>
"""
import json, sys, argparse, os
from collections import defaultdict

def is_default_name(nm):
    return not nm or (len(nm) <= 2 and all(c.isdigit() or c in 'wshaL' for c in nm))

def pt_cell(x, i):
    x = x or {}
    v = x.get('statValues') or []
    p = x.get('statPoints') or []
    if i < len(v):
        s = str(int(v[i]))
        if i < len(p) and p[i]:
            s += '(%d)' % p[i]
        return s
    return '—'

def melee_cell(x):
    x = x or {}
    v = x.get('statValues') or []
    p = x.get('statPoints') or []
    if len(v) > 7:
        s = str(int(v[7]))
        if len(p) > 7 and p[7]:
            s += '(%d)' % p[7]
        return s
    return '—'

def row_cells(d):
    d = d or {}
    nm = d.get('name') or ''
    if is_default_name(nm):
        nm = ''
    return nm, d.get('gender') or '—', d.get('level', ''), (d.get('dinoClass') or '')[:36]

def top_owners(stats, max_show=3, ratio=0.05, min_count=50):
    """聚落成员判定：留痕者前 3 名；数量 < 第一名*ratio 且 < min_count 的不算成员。
    占比低但绝对数量 >= min_count 的仍算成员（不受 5% 比例约束）。"""
    items = sorted(stats.items(), key=lambda kv: -kv[1])
    if not items:
        return []
    mx = items[0][1]
    out = []
    for name, cnt in items:
        if cnt < mx * ratio and cnt < min_count:
            break
        out.append('%s×%d' % (name, cnt))
        if len(out) >= max_show:
            break
    return out

def pod_table_header():
    return '<table><tr><th>#</th><th>名字</th><th>性别</th><th>等级</th><th>距中心</th><th>生命</th><th>耐力</th><th>氧气</th><th>食物</th><th>负重</th><th>近战</th><th>类名</th></tr>'

def pod_row(j, p, d):
    nm, gender, lvl, cls = row_cells(d or p)
    return '<tr><td>%d</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>' % (
        j, nm, gender, lvl, p.get('distance', ''), pt_cell(d, 0), pt_cell(d, 1), pt_cell(d, 3), pt_cell(d, 4), pt_cell(d, 7), melee_cell(d), cls)

def tamed_row(j, t, d):
    nm, gender, lvl, cls = row_cells(d or t)
    owner = '%s(%s)' % (t.get('ownerName', ''), t.get('ownerPid', '')) if t.get('ownerPid') else ''
    return '<tr><td>%d</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>' % (
        j, nm, gender, lvl, t.get('distance', ''), owner, pt_cell(d, 0), pt_cell(d, 1), pt_cell(d, 3), pt_cell(d, 4), pt_cell(d, 7), melee_cell(d), cls)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--settle', required=True)
    ap.add_argument('--cryo', required=True)
    ap.add_argument('--tamed', default='', help='dll 输出放出生物（可缺省）')
    ap.add_argument('--out', required=True)
    ap.add_argument('--tribe', default='基纽特战队', help='只看该部落')
    args = ap.parse_args()

    settle = json.load(open(args.settle, encoding='utf-8'))
    cryo = json.load(open(args.cryo, encoding='utf-8'))
    tamed = {}
    if args.tamed and os.path.exists(args.tamed):
        tamed = json.load(open(args.tamed, encoding='utf-8'))

    # dinoId -> cryo 球详情（含容器信息）
    pod_by_id = {}
    for p in cryo.get('cryopod', []):
        key = '%s_%s' % (p.get('dinoId1', 0), p.get('dinoId2', 0))
        pod_by_id.setdefault(key, p)
    tamed_by_id = {}
    for d in tamed.get('dinos', []):
        key = str(d.get('id') or '%s_%s' % (d.get('dinoId1', 0), d.get('dinoId2', 0)))
        tamed_by_id[key] = d

    # 聚落 -> 球/放出
    settle_pods = defaultdict(list)
    for p in settle.get('pods', []):
        settle_pods[p['settlementId']].append(p)
    settle_tamed = defaultdict(list)
    for t in settle.get('tamed', []):
        settle_tamed[t['settlementId']].append(t)

    # 留痕者统计：聚落 -> 印痕者(角色名+pid) -> count
    # 综合判断：imprinterName 匹配 characterName（角色级）+ imprinterEosId 匹配
    # eosId（账户级）——重名角色用 EOS 区分，小号（同 EOS 不同角色）用角色名区分。
    players = cryo.get('players', [])

    def resolve_imprinter(name, eos):
        cands = [p for p in players if (p.get('characterName') or '') == name]
        if len(cands) == 1:
            return cands[0]
        if eos:
            for p in cands:
                if (p.get('eosId') or '') == eos:
                    return p
        return cands[0] if cands else None

    owner_stat = defaultdict(lambda: defaultdict(int))
    # 印痕者仅限本部落：只统计本部落成员（反查到 pid 则按成员 pid；未反查到 pid 则按成员名）
    tribe_member_pids = {}
    tribe_member_names = {}
    for _tid, _t in (cryo.get('tribes') or {}).items():
        tid_i = int(_tid)
        tribe_member_pids[tid_i] = {m.get('pid') for m in _t.get('members', []) if m.get('pid')}
        tribe_member_names[tid_i] = {m.get('name') for m in _t.get('members', []) if m.get('name')}
    settle_tribe = {s['id']: s.get('tribeId', 0) for s in settle.get('settlements', {}).values()}

    def count_imprinter(sid, imp_name, imp_eos):
        tribe = settle_tribe.get(sid, 0)
        pl = resolve_imprinter(imp_name, imp_eos)
        if pl and pl.get('pid'):
            if pl['pid'] in tribe_member_pids.get(tribe, set()):
                owner_stat[sid]['%s(%s)' % (pl.get('characterName'), pl.get('pid'))] += 1
        elif imp_name in tribe_member_names.get(tribe, set()):
            owner_stat[sid][imp_name] += 1  # 未反查到 pid 但名字是本部落成员（如跨服板板）

    # 放出生物（tamed）印痕者
    for t in settle.get('tamed', []):
        d = tamed_by_id.get(t['dinoId'], {})
        if d.get('imprinterName'):
            count_imprinter(t['settlementId'], d.get('imprinterName'), d.get('imprinterEosId') or '')
    # 球内（cryo）印痕者
    for p in settle.get('pods', []):
        d = pod_by_id.get(p['dinoId'], {})
        if d.get('imprinterName'):
            count_imprinter(p['settlementId'], d.get('imprinterName'), d.get('imprinterEosId') or '')

    tribe_names = {}
    for tid, t in (cryo.get('tribes') or {}).items():
        tribe_names[int(tid)] = t.get('name', tid)

    settlements = settle.get('settlements', {})
    tribe_settles = defaultdict(list)
    for s in settlements.values():
        tribe_settles[s.get('tribeId', 0)].append(s)

    # 只看目标部落（支持多个同名部落，如两个「北境游骑兵」）
    target_tribes = {tid for tid, nm in tribe_names.items() if nm == args.tribe}

    h = []
    h.append('<!DOCTYPE html><html><head><meta charset="utf-8"><title>聚落分组 - %s</title><style>' % args.tribe)
    h.append('body{font-family:"Microsoft YaHei",Arial,sans-serif;font-size:11px;margin:8px;}')
    h.append('h2{font-size:16px;margin:10px 0 4px;}h3{font-size:14px;margin:10px 0 3px;}h4{font-size:12px;margin:8px 0 3px;}h5{font-size:11px;margin:6px 0 2px;color:#333;}p{font-size:11px;margin:2px 0;}')
    h.append('table{border-collapse:collapse;font-size:11px;margin-bottom:10px;}')
    h.append('td,th{border:1px solid #bbb;padding:1px 4px;white-space:nowrap;text-align:center;}')
    h.append('th{background:#e8e8e8;}')
    h.append('.owner{color:#a04a00;font-weight:bold;}')
    h.append('.scat{color:#888;font-style:italic;}')
    h.append('</style></head><body>')
    h.append('<h2>聚落分组 - %s</h2>' % args.tribe)
    h.append('<p>eps=%s | 聚落 %d 个 | 球 %d + 放出 %d</p>' % (
        settle.get('eps'), len(settlements), len(settle.get('pods', [])), len(settle.get('tamed', []))))

    if not target_tribes:
        h.append('<p>未找到部落 %s</p>' % args.tribe)
        h.append('</body></html>')
        with open(args.out, 'w', encoding='utf-8') as f:
            f.write('\n'.join(h))
        return

    ss = []
    for tt in target_tribes:
        ss.extend(tribe_settles.get(tt, []))
    ss.sort(key=lambda s: -s['pods'])
    h.append('<h2>部落 %s（%d 个聚落）</h2>' % (args.tribe, len(ss)))
    for s in ss:
        owners = top_owners(owner_stat[s['id']])
        # 聚落以留痕者冠名（只取名字，多个共同冠名；去掉明显过少的）；无留痕者回退 S 编号
        sname = '、'.join(o.split('×')[0] for o in owners) if owners else s['id']
        h.append('<h3>聚落<span class="owner">%s</span><span style="color:#999;font-size:11px;"> 中心(%s,%s) 半径%s 容器%d 球%d</span></h3>' % (
            sname, s['center']['x'], s['center']['y'], s['radius'], s['containers'], s['pods']))

        # 聚落内按容器分组（球）
        pods = settle_pods.get(s['id'], [])
        by_con = defaultdict(list)
        con_info = {}
        for p in pods:
            d = pod_by_id.get(p['dinoId'], {})
            cid = d.get('containerId') or '?'
            by_con[cid].append(p)
            if cid not in con_info:
                con_info[cid] = {
                    'type': d.get('containerType', ''),
                    'name': d.get('containerName', ''),
                }
        for cid, lst in sorted(by_con.items(), key=lambda kv: -len(kv[1])):
            ci = con_info[cid]
            typ = ci['type']
            cname = ('「%s」' % ci['name']) if ci['name'] else ''
            h.append('<details><summary><b>%s %s</b> <span style="color:#999;font-size:10px;">(%s) %d 球</span></summary>' % (cname, typ, cid[:16], len(lst)))
            h.append(pod_table_header())
            for j, p in enumerate(lst, 1):
                d = pod_by_id.get(p['dinoId'])
                h.append(pod_row(j, p, d))
            h.append('</table></details>')

        # 放出（折叠）
        tds = settle_tamed.get(s['id'], [])
        if tds:
            h.append('<details><summary><b>放出 %d 只</b></summary>' % len(tds))
            h.append('<table><tr><th>#</th><th>名字</th><th>性别</th><th>等级</th><th>距中心</th><th>主人</th><th>生命</th><th>耐力</th><th>氧气</th><th>食物</th><th>负重</th><th>近战</th><th>类名</th></tr>')
            for j, t in enumerate(tds, 1):
                d = tamed_by_id.get(t['dinoId'])
                h.append(tamed_row(j, t, d))
            h.append('</table></details>')

    # 离散（仅本部落？离散 tamed 有 tribeId，球无 -> 离散单独显示）
    scat_tamed = settle_tamed.get('scattered', [])
    if scat_tamed:
        st = [t for t in scat_tamed if (tamed_by_id.get(t['dinoId']) or {}).get('tribeId') in target_tribes]
        if st:
            h.append('<h2 class="scat">离散（未归聚落，本部落放出）</h2>')
            h.append('<details><summary><b>放出 %d 只</b></summary>' % len(st))
            h.append('<table><tr><th>#</th><th>名字</th><th>性别</th><th>等级</th><th>主人</th><th>生命</th><th>近战</th><th>类名</th></tr>')
            for j, t in enumerate(st, 1):
                d = tamed_by_id.get(t['dinoId'])
                nm, gender, lvl, cls = row_cells(d or t)
                owner = '%s(%s)' % (t.get('ownerName', ''), t.get('ownerPid', '')) if t.get('ownerPid') else ''
                h.append('<tr><td>%d</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>' % (
                    j, nm, gender, lvl, owner, pt_cell(d, 0), melee_cell(d), cls))
            h.append('</table></details>')

    h.append('</body></html>')
    with open(args.out, 'w', encoding='utf-8') as f:
        f.write('\n'.join(h))
    print('OK -> %s' % args.out)


if __name__ == '__main__':
    main()
