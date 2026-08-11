# -*- coding: utf-8 -*-
"""5-server "部落长=板板" dino list HTML generator.

Reads <abbr>_tamed.json (released dinos) + <abbr>_cryo.json (in-cryopod +
pet-stand dinos) from the DinoData sync dir. Filters dinos whose tribe owner
is exactly "板板" (ownerName from the cryo 'tribes' block, produced by the new
ark_save_reader.exe with FTribeData parsing).

Usage: python gen_banban_tribes.py [data_dir] [out_dir] [server1 server2 ...]
Default data_dir = P:\\私人共享\\ASA\\DinoData
Default out_dir  = b:\\项目\\ASA Transfer Identity Fix
Default servers  = Abe Cen Ext Isl Sco
"""
import json, re, io, sys, os
from collections import Counter, defaultdict
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

SERVERS = ['Abe', 'Cen', 'Ext', 'Isl', 'Sco']
DATA_DIR = r'P:\私人共享\ASA\DinoData'
OUT_DIR = r'b:\项目\ASA Transfer Identity Fix'
OWNER = '板板'
MEMBER_PID = None      # 成员 pid 模式：输出该成员所属部落的生物 + 其背包球（默认 None=板板模式）
MEMBER_NAME = None     # 成员名（用于标题 + 背包球过滤）

args = sys.argv[1:]
# 可选 --member-pid <pid> --member-name <名>（从 server 列表前提取）
if '--member-pid' in args:
    i = args.index('--member-pid')
    if i + 1 < len(args):
        try:
            MEMBER_PID = int(args[i + 1])
        except ValueError:
            MEMBER_PID = None
        del args[i:i + 2]
if '--member-name' in args:
    i = args.index('--member-name')
    if i + 1 < len(args):
        MEMBER_NAME = args[i + 1]
        del args[i:i + 2]
if args:
    DATA_DIR = args.pop(0)
if args:
    OUT_DIR = args.pop(0)
if args:
    SERVERS = args

def load_json(path):
    with open(path, encoding='utf-8') as f:
        return json.load(f)

def stat_i(x, i):
    sv = x.get('statValues') or []
    if len(sv) > i and sv[i] and sv[i] > 0:
        v = sv[i]
        return ("%d" % round(v)) if v >= 10 else ("%.1f" % v)
    return "—"

def melee_i(x):
    sv = x.get('statValues') or []
    if len(sv) > 8 and sv[8] and sv[8] > 0:
        return "%d%%" % round(sv[8] * 100)
    return "—"

def pt_i(x, i):
    sp = x.get('statPoints') or []
    sm = x.get('statMutations') or []
    spv = sp[i] if len(sp) > i else 0
    smv = sm[i] if len(sm) > i else 0
    base = stat_i(x, i)
    return ("%s(%d/%d)" % (base, spv, smv)) if (spv or smv) else base

def melee_pt_i(x):
    sp = x.get('statPoints') or []
    sm = x.get('statMutations') or []
    spv = sp[8] if len(sp) > 8 else 0
    smv = sm[8] if len(sm) > 8 else 0
    m = melee_i(x)
    return ("%s(%d/%d)" % (m, spv, smv)) if (spv or smv) else m

def stand_cell(x, i):
    sp = x.get('statPoints') or []
    sm = x.get('statMutations') or []
    spv = sp[i] if len(sp) > i else 0
    smv = sm[i] if len(sm) > i else 0
    return ("%d/%d" % (spv, smv)) if (spv or smv) else "—"

def stand_melee_cell(x):
    sp = x.get('statPoints') or []
    sm = x.get('statMutations') or []
    spv = sp[8] if len(sp) > 8 else 0
    smv = sm[8] if len(sm) > 8 else 0
    return ("%d/%d" % (spv, smv)) if (spv or smv) else "—"

def growth(x):
    ba = x.get('babyAge')
    if ba is None or ba < 0 or ba >= 1.0:
        return "100%"
    if ba == 0:
        return "0%"
    pct = ba * 100
    if pct >= 1:
        return "%.0f%%" % pct
    return "%.3f%%" % pct

def is_default_name(nm):
    if not nm:
        return False
    if re.search(r'(等级|等級)\s*\d+', nm):
        return True
    if re.search(r'(?i)\blvl\s*\d+', nm):
        return True
    return False

def anc_count(x):
    a = x.get('ancestors') or []
    return len(a) if isinstance(a, list) else 0

def mut_str(x):
    mm = x.get('randomMutationsMale') or 0
    ff = x.get('randomMutationsFemale') or 0
    return ("%d/%d" % (mm, ff)) if (mm or ff) else "—"

import datetime
# ASA (Ark: Survival Ascended) 上架日期 2023-10-25；早于此的时间戳是 ASE 旧存档
# 迁移脏数据，无效 → 显示为空，不计入任何时间判断。
ASA_EPOCH_MS = int(datetime.datetime(2023, 10, 25).timestamp() * 1000)

# 系统单位（非玩家驯养的辅助/载具单位）：下载时间无意义，一律不显示。
SYS_UNITS = ('HelperBot', 'Train_Character', 'Oasisaur')
def is_sys_unit(cls):
    return any(s in (cls or '') for s in SYS_UNITS)

def fmt_ts_guard(ms, dino_class=''):
    """System units / invalid timestamps -> ''; else format the time."""
    if is_sys_unit(dino_class):
        return ""
    return fmt_ts(ms)

def fmt_world_sec(ws):
    """Format raw world-clock seconds with thousands separators; '' if 0/invalid."""
    try:
        w = float(ws)
    except (TypeError, ValueError):
        return ""
    if not w or w <= 0:
        return ""
    return format(w, ',.0f')

def dl_cell_ms(x):
    """下载进服时间（球内真实 Unix 墙钟，downloadedAtMs）。系统单位/ASE脏时间/无效 -> 空。"""
    cls = x.get('dinoClass', '')
    if is_sys_unit(cls):
        return ""
    ms = x.get('downloadedAtMs') or 0
    if ms and ms >= ASA_EPOCH_MS:
        return fmt_ts(ms)
    return ""

def dl_cell_ws(x, label):
    """原始世界秒（packedAtWorldSec，兼容旧字段名 downloadedAtWorldSec）。
    仅排序用，跨服不可比、不可当墙钟。
    label: 语义提示（球内=原服收球时间 / 宠物台=上架时间）。系统单位/0 -> 空。"""
    cls = x.get('dinoClass', '')
    if is_sys_unit(cls):
        return ""
    ws_s = fmt_world_sec(x.get('packedAtWorldSec') or x.get('downloadedAtWorldSec'))
    if ws_s:
        return "<span style='color:#888' title='%s(世界秒,仅排序)'>%s</span>" % (label, ws_s)
    return ""

def dl_cell_tamed(x):
    """驯服时间（放出龙 tamedAtWorldSec，原始世界秒）。仅排序用。系统单位/0 -> 空。"""
    cls = x.get('dinoClass', '')
    if is_sys_unit(cls):
        return ""
    tat_s = fmt_world_sec(x.get('tamedAtWorldSec'))
    if tat_s:
        return "<span style='color:#b8860b' title='驯服时间(世界秒,仅排序)'>%s</span>" % tat_s
    return ""

def fmt_ts(ms, tag=''):
    """Format a Unix-ms timestamp as local 'YYYY-MM-DD HH:MM' (+age). '' if invalid.
    Timestamps earlier than ASA launch (2023-10-25) are ASE leftovers -> empty."""
    if not ms:
        return ""
    if ms < ASA_EPOCH_MS:
        return ""
    try:
        t = datetime.datetime.fromtimestamp(ms / 1000.0)
        age_days = (datetime.datetime.now() - t).days
        age = ""
        if age_days <= 0:
            age = " (今日)"
        elif age_days == 1:
            age = " (昨天)"
        elif age_days < 30:
            age = " (%d天前)" % age_days
        elif age_days < 366:
            age = " (%d月前)" % (age_days // 30)
        else:
            age = " (%d年前)" % (age_days // 365)
        return "%s %s%s" % (tag, t.strftime("%Y-%m-%d %H:%M"), age)
    except Exception:
        return ""

CT = {"fridge": "低温冰箱", "display": "展示台", "stand": "宠物台",
      "storage": "储物箱", "player": "玩家背包", "hospital": "冷冻医院",
      "other": "其他"}
def cn_type(t):
    return CT.get(t, t or '?')

def container_label(x):
    x = x or {}
    # 玩家背包显示背包主人玩家名（PlayerPawnTest.PlayerName，离线可解析），
    # 归属判定靠 containerOwnerPid（PID 为主）；EOSID 仅展示供未来。
    if x.get('containerType') == 'player':
        pn = x.get('playerName') or ''
        pid = x.get('containerOwnerPid')
        eos = x.get('containerOwnerEosId') or ''
        lab = ('玩家背包(%s)' % pn) if pn else '玩家背包'
        tip = []
        if pid:
            tip.append('PID:%s' % pid)
        if eos:
            tip.append('EOS:%s' % eos)
        if tip:
            lab = "<span title='%s'>%s</span>" % (' '.join(tip), lab)
        return lab
    return x.get('containerClass') or ''

def render_server(abbr):
    cryo_path = os.path.join(DATA_DIR, abbr + '_cryo.json')
    tamed_path = os.path.join(DATA_DIR, abbr + '_tamed.json')
    if not os.path.exists(cryo_path):
        print("SKIP %s: 无 cryo json %s" % (abbr, cryo_path))
        return
    try:
        cryo = load_json(cryo_path)
    except Exception as e:
        print("SKIP %s: cryo json 不完整/正在同步（%s）" % (abbr, e))
        return
    try:
        if os.path.exists(tamed_path):
            tamed = load_json(tamed_path)
        else:
            tamed = {}
    except Exception as e:
        print("SKIP %s: tamed json 不完整/正在同步（%s）" % (abbr, e))
        return
    tribes = cryo.get('tribes')
    if not tribes:
        print("SKIP %s: cryo 无 tribes 段（旧数据，需新 exe 重跑后同步）" % abbr)
        return
    # 成员 pid 模式：输出该成员所属部落的生物（members 含 pid）+ 其背包球。
    # 例：人类 880859190 -> 基纽特战队（11 成员部落，生物最多）。
    if MEMBER_PID is not None:
        banban = {tid: info for tid, info in tribes.items()
                  if any((m or {}).get('pid') == MEMBER_PID for m in info.get('members', []))}
        if not banban:
            print("SKIP %s: 无成员 pid=%s 的部落" % (abbr, MEMBER_PID))
            return
    else:
        # 板板模式：只靠 PID 判定（角色唯一）。EOSID/名字仅展示不参与判定。
        owner_pid = None
        for _tid, _info in tribes.items():
            if _info.get('ownerName') == OWNER and _info.get('ownerPid'):
                owner_pid = _info.get('ownerPid')
                break
        if owner_pid is None:
            # fallback: players 段按 PlayerName 找板板的 pid（新数据必有 ownerPid）
            for _pl in (cryo.get('players') or []):
                if _pl.get('name') == OWNER and _pl.get('pid'):
                    owner_pid = _pl.get('pid')
                    break
        if owner_pid is None:
            print("SKIP %s: 无 ownerPid（需新 exe 重跑）" % abbr)
            return
        banban = {tid: info for tid, info in tribes.items()
                  if info.get('ownerPid') == owner_pid}
    if not banban:
        print("SKIP %s: 无部落长=%s 的部落" % (abbr, OWNER))
        return
    # tribes 段键是字符串（JSON 对象键），tamed/cryo 的 tribeId 是整数 -> 统一转 int
    tribe_ids = set()
    for tid in banban.keys():
        try:
            tribe_ids.add(int(tid))
        except (TypeError, ValueError):
            pass

    spawned = [s for s in tamed.get('dinos', []) if s.get('tribeId') in tribe_ids]
    # 球 = 容器属于本部落。成员模式：部落内排除其他成员玩家背包（只留部落公共容器
    # 冰箱/台/储物等 + 目标成员本人背包），避免出现他人背包（如"玩家背包(嘎巴丸)"）。
    allpods = [p for p in cryo.get('cryopod', [])
               if (p.get('containerTribe') in tribe_ids)]
    if MEMBER_PID is not None:
        # 部落球中：玩家背包仅保留目标成员本人（containerOwnerPid 判定），公共容器全留。
        allpods = [p for p in allpods
                   if p.get('containerType') != 'player'
                   or p.get('containerOwnerPid') == MEMBER_PID]
        # 额外纳入目标成员背包球（containerOwnerPid 判定，跨部落也纳入）。
        seen = {p.get('containerId') for p in allpods}
        for p in cryo.get('cryopod', []):
            if p.get('containerType') == 'player' and p.get('containerOwnerPid') == MEMBER_PID \
               and p.get('containerId') not in seen:
                allpods.append(p)
                seen.add(p.get('containerId'))
    empty_pods = [p for p in allpods if not (p.get('dinoId1') or 0)]
    pods = [p for p in allpods if (p.get('dinoId1') or 0)]

    bycon = defaultdict(list)
    for p in pods:
        bycon[p.get('containerId')].append(p)
    empty_by_con = defaultdict(int)
    for p in empty_pods:
        empty_by_con[p.get('containerId')] += 1
    cons = sorted(set(bycon) | set(empty_by_con),
                  key=lambda cid: -(len(bycon.get(cid, [])) + empty_by_con.get(cid, 0)))

    tnames = [v.get('name', '?') for v in banban.values()]
    if MEMBER_PID is not None:
        hdr_title = '%s 生物清单（成员=%s pid=%s）' % (abbr, MEMBER_NAME or '?', MEMBER_PID)
        hdr_h3 = '<h3>%s %s 部落 生物清单（成员=%s pid=%s）</h3>' % (
            abbr, '、'.join(tnames), MEMBER_NAME or '?', MEMBER_PID)
        file_tag = MEMBER_NAME or ('m%d' % MEMBER_PID)
    else:
        hdr_title = '%s 板板部落清单' % abbr
        hdr_h3 = '<h3>%s 板板部落 生物清单（部落长=板板）</h3>' % abbr
        file_tag = '板板'
    h = []
    h.append('<!DOCTYPE html><html><head><meta charset="utf-8"><title>%s</title><style>' % hdr_title)
    h.append('body{font-family:"Microsoft YaHei",Arial,sans-serif;font-size:11px;margin:8px;}')
    h.append('h3{font-size:15px;margin:6px 0;}h4{font-size:13px;margin:8px 0 3px;}p{font-size:11px;margin:2px 0;}')
    h.append('table{border-collapse:collapse;font-size:11px;margin-bottom:10px;}')
    h.append('td,th{border:1px solid #bbb;padding:1px 4px;white-space:nowrap;text-align:center;}')
    h.append('th{background:#e8e8e8;}')
    h.append('</style></head><body>')
    h.append(hdr_h3)
    h.append('<p>部落: %s（共 %d 个）</p>' % ('、'.join(tnames), len(banban)))
    h.append('<p>放出 %d 只（tamed）+ 球内 %d 只（%d 容器，含空球 %d）</p>' %
             (len(spawned), len(pods) + len(empty_pods), len(cons), len(empty_pods)))

    # 放出
    h.append('<h4>放出的龙（sidecar 合并，属性列=数值(点数/变异)）</h4>')
    h.append('<table><tr><th>#</th><th>名字</th><th>等级</th><th>性别</th><th>颜色</th><th>成长</th><th title="下载进服时间(原始世界秒,仅排序)">下载时间</th><th title="驯服时间(原始世界秒,仅排序)">驯服时间</th><th>DinoID1</th><th>DinoID2</th><th>突变♂/♀</th><th>祖先代</th><th title="数值(点数/变异)">生命</th><th title="数值(点数/变异)">耐力</th><th title="数值(点数/变异)">氧气</th><th title="数值(点数/变异)">食物</th><th title="数值(点数/变异)">负重</th><th title="数值(点数/变异)">近战</th><th>类名</th></tr>')
    def did(x):
        return (x.get('dinoId1') if x.get('dinoId1') is not None else x.get('id1')), \
               (x.get('dinoId2') if x.get('dinoId2') is not None else x.get('id2'))
    spawned.sort(key=lambda x: (x.get('dinoClass', ''), -(x.get('level') or 0), x.get('id1') or x.get('dinoId1') or 0))
    for j, s in enumerate(spawned, 1):
        nm = s.get('name') or ''
        if is_default_name(nm):
            nm = ''
        d1, d2 = did(s)
        h.append('<tr><td>%d</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>' % (
            j, nm, s.get('level', ''), s.get('gender', '') or '—', s.get('colors', '') or '—',
            growth(s), dl_cell_ws(s, '下载进服时间'), dl_cell_tamed(s), d1, d2, mut_str(s), anc_count(s),
            pt_i(s, 0), pt_i(s, 1), pt_i(s, 3), pt_i(s, 4), pt_i(s, 7), melee_pt_i(s), s.get('dinoClass', '')))
    h.append('</table>')

    # 球内（按容器）
    for i, cid in enumerate(cons, 1):
        lst = bycon.get(cid, [])
        emp = empty_by_con.get(cid, 0)
        tot = len(lst) + emp
        if lst:
            typ = container_label(lst[0])
            cname = lst[0].get('containerName') or ''
        else:
            rep = next((p for p in empty_pods if p.get('containerId') == cid), None)
            typ = container_label(rep)
            cname = (rep or {}).get('containerName') or ''
        lst.sort(key=lambda x: (x.get('dinoClass', ''), -(x.get('level') or 0), x.get('dinoId1') or 0))
        nametag = ('「%s」 ' % cname) if cname else ''
        is_stand = (lst[0].get('containerType') == 'stand') if lst else ((rep or {}).get('containerType') == 'stand')
        if is_stand:
            h.append('<h4>%s%s #%d<span style="color:#999;font-size:10px;"> (%s)</span>（%d 宠物%s）</h4>' % (nametag, typ, i, cid[:16], tot, ('，空位 %d' % emp) if emp else ''))
        else:
            h.append('<h4>%s%s #%d<span style="color:#999;font-size:10px;"> (%s)</span>（%d 球%s）</h4>' % (nametag, typ, i, cid[:16], tot, ('，空球 %d' % emp) if emp else ''))
        if not lst:
            continue
        if is_stand:
            # 宠物台：无 downloadedAtMs（不是球），只显示 ws 且语义=上架时间（放上展示架）
            h.append('<table><tr><th>#</th><th>名字</th><th>等级</th><th>性别</th><th>颜色</th><th>成长</th><th title="上架时间(放上展示架,原始世界秒,仅排序,跨服不可比)">上架时间</th><th>DinoID1</th><th>DinoID2</th><th>突变♂/♀</th><th>祖先代</th><th>生命</th><th>耐力</th><th>氧气</th><th>食物</th><th>负重</th><th>近战</th><th>类名</th><th>鞍</th></tr>')
            for j, p in enumerate(lst, 1):
                nm = p.get('name') or ''
                if is_default_name(nm):
                    nm = ''
                cells = [stand_cell(p, 0), stand_cell(p, 1), stand_cell(p, 3), stand_cell(p, 4), stand_cell(p, 7), stand_melee_cell(p)]
                h.append('<tr><td>%d</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>' % (
                    j, nm, p.get('level', ''), p.get('gender', '') or '—', p.get('colors', '') or '—',
                    growth(p), dl_cell_ws(p, '上架时间'), p.get('dinoId1', ''), p.get('dinoId2', ''),
                    mut_str(p), anc_count(p), cells[0], cells[1], cells[2], cells[3], cells[4], cells[5],
                    p.get('dinoClass', ''), p.get('saddle', '') or '—'))
            h.append('</table>')
            continue
        h.append('<table><tr><th>#</th><th>名字</th><th>等级</th><th>性别</th><th>颜色</th><th>成长</th><th title="下载进服时间(真实墙钟,Unix毫秒)">下载进服</th><th title="原服收球时间(原始世界秒,仅排序,跨服不可比)">原服收球</th><th>DinoID1</th><th>DinoID2</th><th>突变♂/♀</th><th>祖先代</th><th>生命</th><th>耐力</th><th>氧气</th><th>食物</th><th>负重</th><th>近战</th><th>类名</th><th>鞍</th></tr>')
        for j, p in enumerate(lst, 1):
            nm = p.get('name') or ''
            if is_default_name(nm):
                nm = ''
            if p.get('containerType') == 'stand':
                cells = [stand_cell(p, 0), stand_cell(p, 1), stand_cell(p, 3), stand_cell(p, 4), stand_cell(p, 7), stand_melee_cell(p)]
            else:
                cells = [pt_i(p, 0), pt_i(p, 1), pt_i(p, 3), pt_i(p, 4), pt_i(p, 7), melee_pt_i(p)]
            h.append('<tr><td>%d</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>' % (
                j, nm, p.get('level', ''), p.get('gender', '') or '—', p.get('colors', '') or '—',
                growth(p), dl_cell_ms(p), dl_cell_ws(p, '原服收球时间'), p.get('dinoId1', ''), p.get('dinoId2', ''),
                mut_str(p), anc_count(p), cells[0], cells[1], cells[2], cells[3], cells[4], cells[5],
                p.get('dinoClass', ''), p.get('saddle', '') or '—'))
        h.append('</table>')

    h.append('</body></html>')
    out = os.path.join(OUT_DIR, '%s部落清单_%s.html' % (abbr, file_tag))
    with open(out, 'w', encoding='utf-8') as f:
        f.write("\n".join(h))
    print("OK %s: %s spawned=%d pods=%d containers=%d tribes=%s" % (
        abbr, out, len(spawned), len(pods), len(cons), sorted(banban.keys())))

if __name__ == '__main__':
    print("data_dir=%s out_dir=%s servers=%s" % (DATA_DIR, OUT_DIR, SERVERS))
    for abbr in SERVERS:
        render_server(abbr)
