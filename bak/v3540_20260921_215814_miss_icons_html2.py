# -*- coding: utf-8 -*-
"""A/B 缺图标物品 对照表 v2（候选深挖）→ tmp/_miss_icons.html
深挖点：
  1) 候选来源 = 汉化/icons2.json 全量 5140（即线上可用图标）
  2) 词集匹配：驼峰/下划线拆分 + 噪声词（icon/icons/the…）剔除 → RawMeat ↔ Meat_Icon 可命中
  3) 中文匹配：读 icon_zh_map.json（图标键→"中文[English]"）做 zh/en 交叉匹配
  4) 按用户口径**剔除 misc / GUI 分类**（这俩不是物品图标）
  5) 每行给出 匹配依据 徽章 + 分类标签
"""
import io, json, os, re, html
BASE = r'b:\项目\Hass ASA Server Monitor'
OUTP = os.path.join(BASE, 'tmp', '_miss_icons.html')
OUTT = os.path.join(BASE, 'tmp', '_miss_icons2_out.txt')

A = [
    ('RawMeat', 2594), ('GachaPod', 597), ('TaxidermyDermis_Gargoyle', 327), ('EmptyCryopod_Gargoyle', 327),
    ('RawPrimeMeat', 214), ('ForSBear', 208), ('Crafted_AnniversaryCandy', 158), ('PowerNodeCharge', 101),
    ('DinoPoopSmall', 74), ('CookedLambChop', 47), ('DinoPoopMedium', 44), ('Saddle_FireLion', 37),
    ('DinoPoopMedium_OnFire', 30), ('GeneInfuser', 29), ('IcedCanteenRefill', 24), ('MekBackpack_Shield', 20),
    ('DinoPoopMassive', 20), ('CakeSlice_Harvest', 20), ('StaminaSoup', 18), ('UnderwaterEgg_Helicoprion', 18),
    ('CactusBuffSoup', 17), ('WaterJarCraftable', 16), ('CakeSlice_Experience', 16), ('FlareGun', 14),
    ('CakeSlice_Imprint', 14), ('SprayPaint', 12), ('FishingNet', 11), ('FE_Crafted_CandyCorn', 9),
    ('CakeSlice_Breeding', 8), ('TekTeleporterSmall', 7), ('RecipeNote_Measurements', 7), ('MasterController', 7),
    ('Ramp_Wood', 6), ('CavewolfPromoSaddle', 6), ('Egg_Maelizard_Special', 6), ('CakeSlice_Taming', 6),
    ('WoodSpikeWall', 5), ('TurretRocket', 5), ('WaterskinRefill', 5), ('Seed_SBear_Wild', 5),
    ('TriCeiling_Wood', 5), ('WoodCage', 5)
]
B = [
    ('AnvilBench', 4), ('ShoulderCannon', 4), ('Wall_Scaffolding', 4), ('CookingPot', 4),
    ('Ceiling_Door_XL_Tek', 3), ('LostColony_MedicalStand', 3), ('TekGrenadeLauncher', 3), ('Market', 3),
    ('Furniture_Rug', 3), ('ToF_Lights', 3), ('DeathEssence_BP', 3), ('PlantSpeciesZ_Grenade', 3),
    ('DinoPoopLarge', 3), ('Flag_IceWyvern', 3),
    ('TekCruiseMissile', 2), ('UnderwaterEgg_Axolotl', 2), ('Egg_Griffin', 2), ('Glider_Thrall', 2),
    ('BountyBoard', 2), ('Wood_CliffPlatform', 2), ('DinoSpawner_Zeppelin', 2), ('CargoLedger_ToF', 2),
    ('Railing_Thatch', 2), ('TriRoof_Tek', 2), ('IcedWaterJarRefill', 2), ('Spawner_HelperBot', 2),
    ('CarSaved', 2), ('LoveTap_Club', 2), ('AdobePillar', 2), ('TriRoof_Adobe', 2), ('TrainCar_Platform', 2),
    ('TreasureMap', 2), ('TreasureMap_WildSupplyDrop', 2),
    ('MortarAndPestle', 1), ('DrakeClaw', 1), ('Egg_Kentro', 1), ('Egg_Rex_Bionic', 1), ('Egg_Boa', 1),
    ('ShieldTek', 1), ('StorageBox_Barrel', 1), ('BountyPage', 1), ('TemplateTablet', 1), ('Egg_Trike', 1),
    ('Eatable_RhynioPheromone', 1), ('UnderwaterEgg_Xiphactinus_ASA', 1), ('Flag_KingKaiju', 1),
    ('LostColony_Bloodforge', 1), ('Egg_Para', 1), ('SpaceWhaleSaddle_Tek', 1), ('RawMutton', 1),
    ('LargeWall_Wood', 1), ('AdobeFenceFoundation', 1), ('TrainTrack_Auto_Wood', 1), ('Ceiling_Door_XL_Metal', 1)
]

zh_tbl = json.loads(io.open(os.path.join(BASE, '汉化', 'item_zh.json'), encoding='utf-8').read())
ic2 = json.loads(io.open(os.path.join(BASE, '汉化', 'icons2.json'), encoding='utf-8').read())
izm = json.loads(io.open(os.path.join(BASE, '汉化', 'icon_zh_map.json'), encoding='utf-8').read())
fac_tbl = json.loads(io.open(os.path.join(BASE, '汉化', 'facility_zh.json'), encoding='utf-8').read())
FAC = fac_tbl if isinstance(fac_tbl, dict) else {}

ICONS = []            # (name, url, cat)
seen_url = set()
for e in (ic2 if isinstance(ic2, list) else []):
    n = str((e or {}).get('name') or '').strip()
    u = str((e or {}).get('url') or '').strip()
    if not n or not u or u in seen_url: continue
    seen_url.add(u)
    m = re.search(r'/ASA/([^/]+)/', u)
    cat = (m.group(1) if m else '?')
    ICONS.append((n, u, cat))

NOISE = {'icon', 'icons', 'the', 'a', 'of', 'bc', 'png'}
def words(s):
    s = str(s).replace('_', ' ').replace('-', ' ')
    parts = re.findall(r'[A-Z]?[a-z0-9]+|[A-Z]+(?![a-z])|\d+', s)
    return [p.lower() for p in parts if p and p.lower() not in NOISE]
def norm(s): return re.sub(r'[^a-z0-9]', '', str(s).lower())

def common_sub_len(a, b):
    a = str(a); b = str(b)
    best = 0
    for i in range(len(a)):
        for j in range(i + 3, len(a) + 1):
            if a[i:j] in b and (j - i) > best:
                best = j - i
    return best

# icon_zh_map：{图标名变体(lower)} → "中文[English]"
IZ = {}
for k, v in (izm.items() if isinstance(izm, dict) else []):
    kk = norm(k)
    if not kk: continue
    s = str(v or '')
    mm = re.match(r'^\s*([^\[\r\n]+?)\s*(\[([^\]]+)\])?\s*$', s)
    zh = (mm.group(1) if mm else s).strip()
    en = (mm.group(3) if mm and mm.group(3) else '').strip()
    if kk not in IZ: IZ[kk] = (zh, en)

def zh_of(base):
    v = zh_tbl.get(base) or {}
    if v.get('zh'): return v['zh']
    for k, t in zh_tbl.items():
        if k.endswith('_' + base) and (t or {}).get('zh'): return t['zh']
    return ''

EXCLUDE_CAT = ('misc', 'gui')

def cands_for(base, zh):
    nb = norm(base); wb = set(words(base))
    fac_ic = ''
    fv = FAC.get(base) or FAC.get(base + '_Icon')
    if isinstance(fv, dict) and fv.get('icon'): fac_ic = str(fv['icon'])
    res = []
    for n, u, cat in ICONS:
        if cat.lower() in EXCLUDE_CAT: continue
        nn = norm(n); wn = set(words(n)); sc = 0; why = ''
        inter = len(wb & wn)
        if nn == nb: sc, why = 100, '名称一致'
        elif wb and wn == wb: sc, why = 96, '词集一致'
        elif wn and wn <= wb: sc, why = 94 + len(wn), '图标词⊂物品词'
        elif wb and wb <= wn: sc, why = 80 - 3 * len(wn - wb), '词⊃'
        elif nb and len(nb) >= 5 and (nb in nn or nn in nb): sc, why = 76, '名称包含'
        elif inter >= 2: sc, why = 66, '多词重叠'
        elif inter == 1 and len(wb) == 1: sc, why = 60, '单词重叠'
        zv = IZ.get(nn) or IZ.get(norm(n.replace('_icon', '')))
        _sub2 = bool(wn and wb and wn <= wb)
        if zv:
            izh, ien = zv
            if zh and izh and izh == zh:
                if _sub2: sc, why = max(sc + 4, 98), '中文一致+词⊂'
                else: sc, why = max(sc, 92), why or '中文一致'
            elif zh and izh and inter >= 1 and (zh in izh or izh in zh):
                sc = max(sc, 84); why = why or '中文相近'
            elif zh and izh and common_sub_len(zh, izh) >= 3:
                sc = max(sc, 82); why = why or '中文共同片段'
            iw = set(words(ien))
            if iw and iw == wb:
                if _sub2: sc, why = max(sc + 2, 97), why or '英文一致'
                else: sc, why = max(sc, 92), why or '英文一致'
        if fac_ic and nn == norm(fac_ic): sc = max(sc, 96); why = '设施表命中'
        if sc > 99: sc = 99
        if sc > 0: res.append((sc, why, n, u, cat))
    res.sort(key=lambda x: (-x[0], len(x[2]), x[2]))
    out, seen = [], set()
    for sc, why, n, u, cat in res:
        if u in seen: continue
        seen.add(u); out.append((sc, why, n, u, cat))
        if len(out) >= 8: break
    return out

def row_html(i, base, n, tag):
    zh = zh_of(base)
    cards = cands_for(base, zh)
    if cards:
        parts = []
        for sc, why, nm2, u, cat in cards:
            parts.append('<label class="cand" title="%s | %s分 | %s | %s">'
                         '<input type="radio" name="r%s%d" data-base="%s" data-icon="%s" onchange="pick(this)">'
                         '<img src="%s" loading="lazy" onerror="this.style.opacity=.2">'
                         '<em>%s</em><i>%s</i><s>%s</s></label>' % (
                             html.escape(nm2), sc, html.escape(why), html.escape(cat),
                             tag, i, html.escape(base), html.escape(nm2),
                             html.escape(u), html.escape(nm2), html.escape(why), html.escape(cat)))
        ch = ''.join(parts)
    else:
        ch = '<span class="none">无候选（需人工指定 → 右侧手填）</span>'
    return ('<tr data-base="%s"><td class="idx">%d</td><td class="zh">%s</td><td class="base">%s</td>'
            '<td class="tag">%s</td><td class="n">%d</td><td class="cands">%s</td>'
            '<td class="man"><input type="text" placeholder="图标名 / URL" data-base="%s" oninput="manIn(this)"></td></tr>'
            ) % (html.escape(base), i, html.escape(zh or '—'), html.escape(base), tag, n, ch, html.escape(base))

rowsA = ''.join(row_html(i + 1, b, n, 'A') for i, (b, n) in enumerate(A))
rowsB = ''.join(row_html(i + 1, b, n, 'B') for i, (b, n) in enumerate(B))

htmlout = """<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>缺图标物品 对照表（A/B）· 候选深挖版</title>
<style>
 body{margin:0;background:#0f0f13;color:#e0e0e0;font:13px/1.5 -apple-system,'Segoe UI',Roboto,sans-serif}
 header{position:sticky;top:0;z-index:5;background:#16161f;border-bottom:1px solid #2a2a3a;padding:10px 14px}
 h1{margin:0 0 6px;font-size:15px}
 .sub{color:#999;font-size:12px}
 .sub b{color:#c4b5fd}
 input#q{margin-top:8px;width:300px;max-width:80vw;background:#0f0f13;border:1px solid #333;border-radius:6px;color:#e0e0e0;padding:4px 8px}
 table{width:100%;border-collapse:collapse}
 th,td{border-bottom:1px solid #22222e;padding:6px 10px;vertical-align:middle;text-align:left}
 th{background:#12121a;color:#8b8b9a;font-weight:600;position:sticky;top:132px;z-index:4}
 tr:hover td{background:#161620}
 tr.picked td{background:#191428}
 .idx{color:#555;width:34px}
 .zh{color:#fff;white-space:nowrap}
 .base{color:#8a8a99;font-size:12px}
 .tag{color:#a78bfa;font-size:11px;width:34px}
 .n{color:#fbbf24;width:54px;text-align:right}
 .cands{display:flex;flex-wrap:wrap;gap:6px}
 .cand{display:inline-flex;align-items:center;gap:4px;background:#1a1a24;border:1px solid #2a2a3a;border-radius:6px;padding:2px 6px;cursor:pointer}
 .cand input{width:auto;margin:0;accent-color:#a78bfa}
 .cand img{width:22px;height:22px;object-fit:contain;background:#0f0f13;border-radius:4px}
 .cand em{font-style:normal;color:#cfe;font-size:11px;max-width:170px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
 .cand i{font-style:normal;color:#f59e0b;font-size:10px}
 .cand s{text-decoration:none;color:#7c8394;font-size:10px}
 .cand.sel{background:#2b1f4d;border-color:#a78bfa}
 .none{color:#f87171;font-size:12px}
 .man{width:150px}
 .man input{width:134px;background:#0f0f13;border:1px solid #333;border-radius:6px;color:#e0e0e0;padding:3px 6px;font-size:11px}
 .bar{display:flex;align-items:center;gap:8px;margin-top:6px}
 .bar button,.foot button{background:#2a2a3a;border:1px solid #3a3a4a;color:#e0e0e0;border-radius:6px;padding:4px 10px;font-size:12px;cursor:pointer}
 .bar button:hover,.foot button:hover{background:#3a3a4a}
 .cnt{color:#a78bfa;font-size:12px;white-space:nowrap}
 .foot{position:fixed;left:0;right:0;bottom:0;background:#16161f;border-top:1px solid #2a2a3a;padding:6px 14px;display:flex;gap:10px;align-items:center;z-index:9}
 .foot textarea{flex:1;height:78px;background:#0f0f13;border:1px solid #333;border-radius:6px;color:#9fe;font:11px/1.35 Consolas,monospace;padding:4px 6px}
 body{padding-bottom:126px}
 h2{font-size:14px;color:#c4b5fd;margin:16px 14px 6px}
</style></head><body>
<header>
 <h1>缺图标物品对照表（A/B）· 候选深挖 + <span style="color:#a78bfa">勾选确认版</span> · dino v20260921-3539</h1>
 <div class="sub">A 42 + B 54；候选来源 = icons2 全量（已剔除 <b>misc / GUI</b>）+ <b>facility_zh 设施表</b> + <b>icon_zh_map 中/英文</b>；依据 = 名称一致 / 词集一致 / <b>图标词⊂物品词</b> / 中文一致 / 中文共同片段 / 设施表命中。→ <b>点左例圆点选中正确图标</b>（或右侧手填图标名/URL），底部实时生成 JSON，点「复制/下载」发我即写库。</div>
 <div class="bar">
  <button onclick="top1()">✅ 全选第一候选</button>
  <button onclick="clr()">🧹 清除全部</button>
  <span class="cnt" id="cnt">已选 0 / __T__</span>
  <span class="cnt" id="flash" style="color:#7ee787;transition:opacity .3s"></span>
 </div>
 <input id="q" placeholder="过滤：中文名 / 基名 / 图标名…" oninput="flt()">
</header>
<h2>▍A 类 · 重点（会显示且数量多）</h2>
<table id="tA"><thead><tr><th>#</th><th>中文名</th><th>基名(class)</th><th>类</th><th>数量</th><th>候选图标（点圆点选中）</th><th>✍ 手动</th></tr></thead>
<tbody>__A__</tbody></table>
<h2>▍B 类 · 其余散件</h2>
<table id="tB"><thead><tr><th>#</th><th>中文名</th><th>基名(class)</th><th>类</th><th>数量</th><th>候选图标（点圆点选中）</th><th>✍ 手动</th></tr></thead>
<tbody>__B__</tbody></table>
<div class="foot">
 <textarea id="out" readonly placeholder="勾选候选后这里实时生成 { 物品基名: 图标名 } …"></textarea>
 <div style="display:flex;flex-direction:column;gap:6px">
  <button onclick="copyJSON()">📋 复制 JSON</button>
  <button onclick="dl()">💾 下载 JSON</button>
 </div>
</div>
<script>
var TOTAL=__T__, sel={}, man={};
function pick(el){
 var b=el.getAttribute('data-base');
 sel[b]=el.getAttribute('data-icon');
 var tr=el.closest('tr'), cs=tr.querySelectorAll('.cand');
 for(var i=0;i<cs.length;i++) cs[i].classList.toggle('sel', cs[i].contains(el));
 tr.classList.add('picked'); refresh();
}
function manIn(el){
 var b=el.getAttribute('data-base'), v=el.value.trim();
 if(v) man[b]=v; else delete man[b];
 el.closest('tr').classList.toggle('picked', !!v); refresh();
}
function top1(){
 var rows=document.querySelectorAll('tbody tr');
 for(var i=0;i<rows.length;i++){
  var tr=rows[i]; if(tr.querySelector('.cand input:checked')) continue;
  var mm=tr.querySelector('.man input'); if(mm && mm.value.trim()) continue;
  var f=tr.querySelector('.cand input'); if(f){ f.checked=true; pick(f); }
 }
}
function clr(){
 sel={}; man={};
 document.querySelectorAll('.cand input').forEach(function(x){x.checked=false;});
 document.querySelectorAll('.man input').forEach(function(x){x.value='';});
 document.querySelectorAll('.cand').forEach(function(c){c.classList.remove('sel');});
 document.querySelectorAll('tbody tr').forEach(function(t){t.classList.remove('picked');});
 refresh();
}
function outObj(){ var o={},k; for(k in sel) o[k]=sel[k]; for(k in man) o[k]=man[k]; return o; }
function refresh(){
 var o=outObj(), n=0,k; for(k in o) n++;
 document.getElementById('out').value=JSON.stringify(o,null,1);
 document.getElementById('cnt').textContent='已选 '+n+' / '+TOTAL;
}
function copyJSON(){
 var t=document.getElementById('out');
 try{ navigator.clipboard.writeText(t.value); }catch(e){}
 t.select(); try{ document.execCommand('copy'); }catch(e){}
 flash('✓ 已复制到剪贴板，直接粘贴发我');
}
function dl(){
 var blob=new Blob([document.getElementById('out').value],{type:'application/json'});
 var a=document.createElement('a');
 a.href=URL.createObjectURL(blob); a.download='miss_icons_pick.json';
 document.body.appendChild(a); a.click(); a.remove();
 flash('✓ 已下载 miss_icons_pick.json');
}
var ft=null;
function flash(m){
 var b=document.getElementById('flash'); b.textContent=m; b.style.opacity=1;
 if(ft) clearTimeout(ft); ft=setTimeout(function(){ b.style.opacity=0; },2400);
}
function flt(){var q=document.getElementById('q').value.trim().toLowerCase();
 ['tA','tB'].forEach(function(id){var tb=document.getElementById(id).tBodies[0];
  for(var i=0;i<tb.rows.length;i++){var r=tb.rows[i];var t=r.textContent.toLowerCase();
   r.style.display=(!q||t.indexOf(q)>=0)?'':'none';}});}
refresh();
</script></body></html>""".replace('__A__', rowsA).replace('__B__', rowsB).replace('__T__', str(len(A) + len(B)))

io.open(OUTP, 'w', encoding='utf-8').write(htmlout)

# 输出核验信息
lines = []
lines.append('icons_total=%d（已剔 misc/GUI 后参与匹配）' % len([i for i in ICONS if i[2].lower() not in EXCLUDE_CAT]))
noC = 0
for tag, arr in (('A', A), ('B', B)):
    for b, n in arr:
        cs = cands_for(b, zh_of(b))
        if not cs: noC += 1
        top3 = ' | '.join('%s(%s,%s,%d)' % (c[2], c[1], c[4], c[0]) for c in cs[:3])
        lines.append('%s %-30s -> %s' % (tag, b, top3 or '(无)'))
lines.insert(1, 'rows_without_candidate=%d' % noC)
io.open(OUTT, 'w', encoding='utf-8').write('\n'.join(lines))
print('OK rows_without_candidate=%d' % noC)
