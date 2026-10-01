# -*- coding: utf-8 -*-
# v4155 对照表：所有含 Costume 的可见项抽取单独列（⑥）
import io, json, re, time

B = r'b:\项目\Hass ASA Server Monitor'
OUT = B + r'\_preview_icons_unused.html'
TS = time.strftime('%Y-%m-%d %H:%M')

ic = json.load(io.open(B + r'\汉化\icons2.json', encoding='utf-8'))
URL = {}
for x in ic:
    URL[x.get('name')] = x.get('url')

U2 = json.load(io.open(B + r'\tmp\_v4147_unused2.json', encoding='utf-8'))
cats = U2['cats']
gray = U2['gray']
SK = json.load(io.open(B + r'\tmp\_v4147_skins_final.json', encoding='utf-8'))
IZ = json.loads(io.open(B + r'\汉化\item_zh.json', encoding='utf-8').read())
try:
    ZH_MAP = json.loads(io.open(B + r'\汉化\icon_zh_map.json', encoding='utf-8'))
except Exception:
    ZH_MAP = {}
ZH_LOW = {}
for k, v in ZH_MAP.items():
    ZH_LOW[str(k).lower()] = v

CATNAME = {u'ammo': u'弹药', u'facility': u'设施', u'units': u'单位/载具', u'tools': u'工具', u'armor': u'护甲', u'weapons': u'武器'}
ORDER = [u'ammo', u'facility', u'units', u'tools', u'armor', u'weapons']
DIRTY = re.compile(u'^\\d{13}-|\\.png$|DevKit|Species_X|WeirdPlant|^1734848')

def dirty(n):
    return u' <span class="tag">疑似脏数据</span>' if DIRTY.search(n) else u''

# v4152/v4153（用户口径）：_Animated/_Human 与部位件后缀全不显示
# v4164（用户口径）：+ _Sweater/_Bottoms/_Top/_Underwear/Hat/_Helm（服装部位件类无需显示）
_HIDE_SUF = (u'_Animated', u'_Human', u'_Boots', u'_Gloves', u'_Helmet', u'_Pants', u'_Shirt', u'_Shoes', u'_Hat', u'_Sweater', u'_Bottoms', u'_Top', u'_Underwear', u'Hat', u'_Helm')
def _hid(s):
    n = s['name']
    for _w in _HIDE_SUF:
        if _w in n:
            return True
    return False

# ---------- 区① ----------
RETIRED = set([
    u'Large_Storage_Box', u'Mirror', u'Oil_Jar', u'Chainsaw', u'Climbing_Pick', u'Mining_Drill', u'Whip',
    u'Desert_Cloth_Boots', u'Desert_Cloth_Gloves', u'Desert_Cloth_Pants', u'Desert_Cloth_Shirt', u'Desert_Goggles_and_Hat',
    u'Ghillie_Mask', u'Hazard_Suit_Hat', u'Hazard_Suit_Shirt', u'Hazard_Suit_Boots', u'Flamethrower', u'SCUBAShirt',
    u'Grappling_Hook', u'T_TribeTower_Icon', u'Tranq_Arrow',
    u'HomingMissileAmmo_Icon', u'HUD_TEKGrenadeLauncher_BC_Icon', u'HUD_TEKClaws_Icon',
])
EXCL1 = set([
    u'Cluster_Grenade', u'1734848252458-13dd2f61-0316-40ac-9e5d-3a1fa1429daf', u'Artifact_Pedestal', u'Dino_Leash', u'Element Node.png',
    u'GraveStone2_Icon', u'GraveStone3_Icon', u'HUD_GenesisWarMap_Icon', u'HUD_LargeDecorBox_Icon', u'HUD_LostColony_CeilingLight_Icon',
    u'HUD_LostColony_TableLight_Icon', u'HUD_LostColony_WallLight_Icon', u'HUD_PetDisplayStand_Wall_Thatch_Icon', u'HUD_PetDisplayStand_Wall_Wood_Icon',
    u'HUD_PetDisplayStand_Wood_Icon', u'HUD_Steampunk_CeilingLight_Icon', u'HUD_Steampunk_PlasmaLamp_Icon', u'HUD_Steampunk_WallLight_Icon',
    u'HUD_TekAlarm_Icon_BC', u'HUD_WastelandWallLight_Icon', u'Industrial_Grill', u'Species_X_plant_icon', u'Tek_Sensor', u'ScoutGrenade_Icon',
    u'Tek_ATV', u'Tek_Remote_Camera', u'Unassembled_TEK_Hover_Skiff',
    u'Cruise_Missile', u'HUD_CruiseMissile_BC_Icon',
    u'Cosmo_Wrist-Shooter', u'Cryopod', u'Fish_Net', u'Flare_Gun', u'HUD_GloonWeapon_Icon',
    u'Ghillie_Boots', u'Ghillie_Chestpiece', u'Ghillie_Gauntlets', u'Ghillie_Leggings', u'Hazard_Suit_Gloves', u'Hazard_Suit_Pants', u'ScubaBreather', u'Assault_Rifle',
    u'C4_Remote_Detonator', u'Carving_Knife', u'Charge_Lantern', u'Large_Bear_Trap',
    u'Rocket_Launcher', u'Tek_Grenade_Launcher', u'Tek_Railgun', u'Tek_Shoulder_Cannon',
])
r1 = []
retired = []
i = 0
for cat in ORDER:
    for n, u in cats.get(cat, []):
        if n in RETIRED:
            retired.append((n, u))
            continue
        if n in EXCL1:
            continue
        i += 1
        r1.append(u'<tr><td>%d</td><td><img src="%s" alt=""></td><td><b>%s</b>%s</td><td>%s</td></tr>' % (i, u, n, dirty(n), CATNAME.get(cat, cat)))
RET_HTML = u''   # （组装移至区②循环后：并含区②来源的退休图）

# ---------- 区② ----------
r2 = []
retired2 = []
i = 0
EXCL2 = set([
    u'HUD_Frontier_PlantPot_cropPlotCombo_Filled_Icon', u'HUD_Frontier_PlantPot_cropPlotCombo_Icon',
    u'HUD_TOF_Pirate_TableLamp_Icon', u'HUD_TOF_Pirate_WallLamp_Icon', u'HUD_WastelandTableLamp_Icon',
    u'Icon_Hyperchamber', u'HUD_TEKHoverSkiff_Icon_BC',
    u'ChargeStick_25_Icon', u'ChargeStick_50_Icon', u'ChargeStick_75_Icon', u'ChargeStick_Empty_Icon',
    u'ElectronicTracker_Icon',
])
for g in gray:
    if g['name'] in RETIRED:
        retired2.append((g['name'], g['url']))
        continue
    if g['name'] in EXCL2:
        continue
    i += 1
    r2.append(u'<tr><td>%d</td><td><img src="%s" alt=""></td><td><b>%s</b>%s</td><td>%s</td></tr>' % (i, g['url'], g['name'], dirty(g['name']), CATNAME.get(g['cat'], g['cat'])))
EXCL2_HTML = u'<p class="sum">另有 %d 项经用户判定移除（区②不显示）。</p>' % len(EXCL2)
RET_ALL = list(retired) + list(retired2)
if RET_ALL:
    RET_HTML = u'<details><summary>v4148~v4154 替换后退休的旧图标（%d 枚，已从区①/区②剔除）</summary><p>%s</p></details>' % (
        len(RET_ALL), u' '.join(u'<span class="chip">%s</span>' % n for n, u in RET_ALL))
RET_HTML += u'<p class="sum">另有 %d 项经用户判定移除（「确定不用显示」，不出现在列表）。</p>' % len(EXCL1)

# ---------- 区③ ----------
byg = {}
for s in SK:
    byg.setdefault(s['group'], []).append(s)

def deal_def(s):
    n = s['name']
    if 'ARKWCDev' in n:
        return u'✅ 已定 v4149：不补录（无游戏物品证据，判定为管理/调试用途）'
    if '10thAnniversaryCake' in n:
        return u'✅ 已补录 v4148：AnniversaryCake_10th（十周年蛋糕）'
    if 'AnniversaryCake' in n:
        return u'✅ 已补录 v4148：AnniversaryCake（周年蛋糕）'
    return u'词典已引用为他类（无需补录）'

def rows_of(lst):
    out = []
    j = 0
    for s in lst:
        j += 1
        out.append(u'<tr><td>%d</td><td><img src="%s" alt=""></td><td>%s</td><td>%s</td><td>%s</td></tr>' % (j, s['url'], s['name'], (s.get('ev') or u'')[:120], deal_def(s)))
    return out

ns_def = []
for s in byg.get(u'非皮肤·词典引用为他类', []):
    ns_def.append(s)
for s in byg.get(u'非皮肤·活动/管理', []):
    if re.search(u'ARKWCDev', s['name']) or re.search(u'(?i)anniversarycake', s['name']):
        ns_def.append(s)
ns_soft = []
for s in byg.get(u'非皮肤·他类物品', []):
    ns_soft.append(s)
for s in byg.get(u'非皮肤·活动/管理', []):
    if s not in ns_def and s not in ns_soft:
        ns_soft.append(s)
# v4162（用户要求）：「非皮肤·疑似」7 项已确认皮肤类并落地 → 结案移入④区
NS_SOFT_DONE_NAMES = (u'Lost_Drakeling_Costume', u'Megaloceros_Reindeer_Costume', u'Modern_Canoe_Costume',
                      u'Reaper_Ghost_Costume', u'Snow_Owl_Ghost_Costume', u'Tek_Canoe_Costume', u'Viking_Canoe_Costume')
NS_SOFT_DONE = [s for s in ns_soft if s['name'] in NS_SOFT_DONE_NAMES]
ns_soft = [s for s in ns_soft if s['name'] not in NS_SOFT_DONE_NAMES]
skin_hard = byg.get(u'真皮肤·PO/Beacon', []) + byg.get(u'真皮肤·动画剧集', []) + byg.get(u'真皮肤·词典skin标记', []) + byg.get(u'真皮肤?·动画剧集', [])
pend = byg.get(u'待核·未识别', [])
WEAR = re.compile(u'(?i)swim|underwear|bra|panty|short|shirt|pants|glove|boot|shoe|hat|mask|helmet|suit|sweater|costume|glasses|bracelet|anklet|slipper|visor|dress|skirt|jacket|cape|wings|ears|antler|wreath|flower|jelly|fuzzy|tattoo|skin|scarf|beanie|beard|helmet')
pw = [s for s in pend if WEAR.search(s['name'])]
po = [s for s in pend if not WEAR.search(s['name'])]
chips = lambda lst: u' '.join(u'<span class="chip">%s</span>' % s['name'] for s in lst)
chips_hid = lambda lst: u' '.join(u'<span class="chip">%s</span>' % s['name'] for s in lst if not _hid(s))
# v4153：非皮肤·确定 15 项结案（13 归档 + 2 已落地）
NS_REF = len(byg.get(u'非皮肤·词典引用为他类', []))
NS_DONE_NAMES = (u'ASA_Icon_10thAnniversaryCake', u'ASA_Icon_AnniversaryCake')
NS_DONE = [s for s in ns_def if s['name'] in NS_DONE_NAMES]
NS_REST = [s for s in ns_def if s['name'] not in NS_DONE_NAMES]
NS_MGR = len(ns_def) - NS_REF - len(NS_DONE)
ARCH_HTML = u'<details><summary>已归档 · 非皮肤（%d 枚）—— 词典引用为他类 %d / 管理调试 %d / 已落地 %d（蛋糕 → 见④区）</summary><p>%s</p><p><b>已落地（%d，④区有记录）</b></p><p>%s</p></details>' % (
    len(ns_def), NS_REF, NS_MGR, len(NS_DONE), chips(NS_REST), len(NS_DONE), chips(NS_DONE))
NS_CLOSE = u'<p class="sum">✅ %d 项已全部结案：%d 项归档（词典引用为他类 %d / 管理调试 %d）+ %d 项已落地（周年蛋糕/十周年蛋糕 → 见④区）。</p>' % (len(ns_def), len(NS_REST), NS_REF, NS_MGR, len(NS_DONE))
ns_soft_show = [s for s in ns_soft if not _hid(s)]
def _refs_of(nm):
    rr = []
    for _k2, _v2 in IZ.items():
        if isinstance(_v2, dict) and _v2.get('icon') == nm:
            rr.append(_k2)
    if not rr and nm in IZ:
        rr.append(nm)
    return (u'被引用：' + u'、'.join(rr[:3])) if rr else u'（未检出引用）'
if ns_soft_show:
    r_ns_soft = u'\n'.join(u'<tr><td>%d</td><td><img src="%s" alt=""></td><td>%s</td><td>%s</td><td>%s</td></tr>' % (j + 1, s['url'], s['name'], (s.get('ev') or u'')[:120], _refs_of(s['name'])) for j, s in enumerate(ns_soft_show))
else:
    # v4162（用户要求）：7 项服装类已结案（→④区）
    r_ns_soft = u'<tr><td colspan="5">✅ 服装类 7 项已结案（v4162 → 见④区）；活动类项目（Corrupt 套等）已隐藏</td></tr>'

# ---------- 区④ ----------
done_rows = []
DONE41 = [
    (u'Lovely_Fishing_Rod', u'Lovely_Fishing_Rod', u'工具(tools)', u'补录为工具（tool:1 → 器械栏·工具段）；中文「可爱钓鱼竿」直译待核'),
    (u'Lesser_Antidote', u'PrimalItemConsumable_CureLow', u'消耗品(料理)', u'归料理族，排序 3.1'),
    (u'Beer_Jar', u'BeerJar', u'消耗品(料理)', u'归料理族，排序 3.2'),
    (u'Sanguine_Elixir', u'Sanguine_Elixir', u'消耗品(料理)', u'归料理族，排序 3.3'),
]
k = 0
done_rows.append(u'<tr class="grp"><td colspan="5">v4147（4 项）</td></tr>')
for icon, label, cat, note in DONE41:
    k += 1
    img = URL.get(icon) or u''
    done_rows.append(u'<tr class="ok"><td>%d</td><td><img src="%s" alt=""></td><td><b>%s</b></td><td>%s</td><td>%s</td></tr>' % (k, img, label, cat, note))

def parse_apply(fname):
    agg = {}
    try:
        txt = io.open(B + r'\tmp\\' + fname, encoding='utf-8').read()
    except Exception:
        return agg
    for line in txt.split('\n'):
        m = re.match(u'^(\\S.*?) \\[(.*?)\\]: icon (\\S+) -> (\\S+)$', line)
        if m:
            e = agg.setdefault(m.group(1), {u'zh': m.group(2), u'ops': [], u'icon': u''})
            e['ops'].append(u'图标 %s → %s' % (m.group(3), m.group(4)))
            e['icon'] = m.group(4)
            continue
        m = re.match(u'^(\\S.*?) \\[(.*?)\\]: en (.*?) -> (.*)$', line)
        if m:
            e = agg.setdefault(m.group(1), {u'zh': m.group(2), u'ops': [], u'icon': u''})
            e['ops'].append(u'英文「%s」→「%s」' % (m.group(3), m.group(4)))
    return agg

agg48 = parse_apply(u'_v4148_apply_out.txt')
done_rows.append(u'<tr class="grp"><td colspan="5">v4148 · 图标替换与英文修正（%d 键）</td></tr>' % len(agg48))
for kk, e in agg48.items():
    k += 1
    u2 = URL.get(e['icon']) or u''
    done_rows.append(u'<tr class="ok"><td>%d</td><td><img src="%s" alt=""></td><td><b>%s</b><br><span class="sub">%s</span></td><td>%s</td><td>%s</td></tr>' % (k, u2, kk, e['zh'], u'图标/en', u'；'.join(e['ops'])))

DONE48_NEW = [
    (u'MachinedBow', u'制式弓', u'武器', u'MachinedBow_Icon'), (u'Pet_Display', u'宠物展示台', u'设施', u'Pet_Display'),
    (u'PrimalItemStructure_LostColony_ShoulderPetDisplayStand', u'宠物展示台', u'设施', u'Pet_Display'),
    (u'Birthday_Cake', u'生日蛋糕', u'设施', u'Birthday_Cake'), (u'Underwater_Crop_Plot', u'水下耕地', u'设施', u'Underwater_Crop_Plot'),
    (u'Submarine', u'潜艇', u'模块(attachment)', u'Item_Submarine_Icon'), (u'Tek_Thalassian_Hoversail', u'泰克塔拉萨悬停帆', u'模块(attachment)', u'Tek_Thalassian_Hoversail'),
    (u'CannonBall_ToF_HarvestLines', u'收割渔线', u'弹药', u'ASA_Icons_TOF_HarvestLineAmmo'),
    (u'PrimalItemAmmo_CannonBall_ToF_HarvestLines', u'收割渔线', u'弹药', u'ASA_Icons_TOF_HarvestLineAmmo'),
    (u'AnniversaryCake', u'周年蛋糕', u'设施', u'ASA_Icon_AnniversaryCake'), (u'AnniversaryCake_10th', u'十周年蛋糕', u'设施', u'ASA_Icon_10thAnniversaryCake'),
]
done_rows.append(u'<tr class="grp"><td colspan="5">v4148 · 补录（%d 键）</td></tr>' % len(DONE48_NEW))
for kk, zh, cat, icon in DONE48_NEW:
    k += 1
    u2 = URL.get(icon) or u''
    done_rows.append(u'<tr class="ok"><td>%d</td><td><img src="%s" alt=""></td><td><b>%s</b><br><span class="sub">%s</span></td><td>%s</td><td>补录</td></tr>' % (k, u2, kk, zh, cat))
done_rows.append(u'<tr class="grp"><td colspan="5">v4148 · ASE 过滤标记（2 键）</td></tr>')
for kk in (u'TransGPS', u'PrimalItemStructure_TransGPS'):
    k += 1
    done_rows.append(u'<tr class="ok"><td>%d</td><td><img src="%s" alt=""></td><td><b>%s</b></td><td>ASE 旧物</td><td>打 ase:1 标记（旧定位器过滤）</td></tr>' % (k, URL.get(u'Transponder_Tracker') or u'', kk))

agg49 = parse_apply(u'_v4149_apply_out.txt')
done_rows.append(u'<tr class="grp"><td colspan="5">v4149 · 图标替换（%d 键）</td></tr>' % len(agg49))
for kk, e in agg49.items():
    k += 1
    u2 = URL.get(e['icon']) or u''
    done_rows.append(u'<tr class="ok"><td>%d</td><td><img src="%s" alt=""></td><td><b>%s</b><br><span class="sub">%s</span></td><td>图标替换</td><td>%s</td></tr>' % (k, u2, kk, e['zh'], u'；'.join(e['ops'])))

DONE49_NEW = [
    (u'Snowball', u'雪球', u'弹药', u'Snowball_Icon'), (u'Carnivorous_Plant_Seed', u'食肉植物种子', u'消耗品', u'Carnivorous_Plant_Seed_Icon'),
    (u'Thalassian_Pistol', u'塔拉萨手枪', u'武器', u'Thalassian_Pistol'), (u'Thalassian_Rifle', u'塔拉萨步枪', u'武器', u'Thalassian_Rifle'),
    (u'Thalassian_Ammo', u'塔拉萨弹药', u'弹药', u'Thalassian_Ammo'), (u'Tranq_Thalassian_Ammo', u'塔拉萨麻醉弹药', u'弹药', u'Tranq_Thalassian_Ammo'),
    (u'ARK_Anniversary_Surprise_Cake', u'方舟周年庆惊喜蛋糕', u'设施', u'ARK_Anniversary_Surprise_Cake'), (u'Birthday_Candle', u'生日蜡烛', u'资源', u'Birthday_Candle'),
    (u'CryoHospital', u'低温护理站', u'设施', u'HUD_CryoHospital_Icon'), (u'PrimalItemStructure_LostColony_CryoHospital', u'低温护理站', u'设施', u'HUD_CryoHospital_Icon'),
    (u'Netgun', u'网枪', u'武器', u'NetgunAmmo_Icon'),
]
done_rows.append(u'<tr class="grp"><td colspan="5">v4149 · 补录（%d 键）</td></tr>' % len(DONE49_NEW))
for kk, zh, cat, icon in DONE49_NEW:
    k += 1
    u2 = URL.get(icon) or u''
    done_rows.append(u'<tr class="ok"><td>%d</td><td><img src="%s" alt=""></td><td><b>%s</b><br><span class="sub">%s</span></td><td>%s</td><td>补录</td></tr>' % (k, u2, kk, zh, cat))

LAND26 = [x[0] for x in [
    (u'BoneGigaCostume_Icon', u'骨骼南巨服装'), (u'CustomCreatureCostumeSkin_Icon', u'自定义生物服装'),
    (u'HUD_GhostAnglerfishCostume_Icon', u'幽灵鮟鱇鱼服装'), (u'HUD_GhostAnkyloCostume_Icon', u'幽灵甲龙服装'),
    (u'HUD_GhostArgentavisCostume_Icon', u'幽灵阿根廷巨鹰服装'), (u'HUD_GhostCatCostume_Icon', u'幽灵猫服装'),
    (u'HUD_GhostCeratosaurusCostume_Icon', u'幽灵角鼻龙服装'), (u'HUD_GhostDeinonychusCostume_Icon', u'幽灵恐爪龙服装'),
    (u'HUD_GhostGigantoraptorCostume_Icon', u'幽灵巨盗龙服装'), (u'HUD_GhostMegalodonCostume_Icon', u'幽灵巨齿鲨服装'),
    (u'HUD_GhostOtterCostume_Icon', u'幽灵水獭服装'), (u'HUD_GhostSpinoCostume_Icon', u'幽灵棘龙服装'),
    (u'HUD_GhostVeilwynCostume_Icon', u'幽灵帷翼龙服装'), (u'HUD_GhostYiLingCostume_Icon', u'幽灵翼灵服装'),
    (u'HUD_July4th_TrexCostume_Icon_BC', u'独立日霸王龙服装'), (u'HUD_LoveAscended_GloonCostume_Icon', u'格鲁恩服装'),
    (u'Inflatable_Rex_Costume_Skin', u'充气霸王龙服装'), (u'Megaloceros_Reindeer_Costume', u'驯鹿服装'),
    (u'Modern_Canoe_Costume', u'现代独木舟皮肤'), (u'Tek_Canoe_Costume', u'泰克独木舟皮肤'),
    (u'Viking_Canoe_Costume', u'维京独木舟皮肤'), (u'Reaper_Ghost_Costume', u'幽灵死神国王服装'),
    (u'Rex_Bionic_Costume', u'生化霸王龙服装'), (u'Rex_Bone_Costume', u'骨骼霸王龙服装'),
    (u'Snow_Owl_Ghost_Costume', u'幽灵雪鸮服装'), (u'Trike_Bone_Costume', u'骨骼三角龙服装'),
]]
done_rows.append(u'<tr class="grp"><td colspan="5">v4150 · 生物外观族落地（生物外观服装 %d 键 → 模块>生物外观，排模块段最末）</td></tr>' % len(LAND26))
for icon in LAND26:
    k += 1
    v = IZ.get(icon) or {}
    u2 = URL.get(icon) or u''
    done_rows.append(u'<tr class="ok"><td>%d</td><td><img src="%s" alt=""></td><td><b>%s</b><br><span class="sub">%s</span></td><td>模块(attachment)</td><td>补录 + 族「生物外观」</td></tr>' % (k, u2, icon, v.get('zh', u'')))

# v4151：换图 + 补录
agg51 = {}
try:
    txt51 = io.open(B + r'\tmp\_v4151_land_out.txt', encoding='utf-8').read()
except Exception:
    txt51 = ''
for line in txt51.split('\n'):
    m = re.match(u'^(\\S+): icon (\\S+) -> (\\S+)$', line)
    if m:
        agg51[m.group(1)] = (m.group(2), m.group(3))
done_rows.append(u'<tr class="grp"><td colspan="5">v4151 · 图标替换（%d 键）</td></tr>' % len(agg51))
for kk, (o1, n1) in agg51.items():
    k += 1
    u2 = URL.get(n1) or u''
    v = IZ.get(kk) or {}
    done_rows.append(u'<tr class="ok"><td>%d</td><td><img src="%s" alt=""></td><td><b>%s</b><br><span class="sub">%s</span></td><td>图标替换</td><td>图标 %s → %s</td></tr>' % (k, u2, kk, v.get('zh', u''), o1, n1))
DONE51_NEW = [
    (u'TripFlare', u'绊线照明弹陷阱', u'设施', u'TripFlare_Icon'),
    (u'Tek_Trident', u'泰克三叉戟', u'武器', u'Tek_Trident'),
    (u'Tek_Spear', u'泰克长矛', u'武器', u'HUD_TekSpear_Icon'),
    (u'C4Remote', u'C4遥控起爆器', u'武器', u'C4Remote_Icon'),
]
done_rows.append(u'<tr class="grp"><td colspan="5">v4151 · 补录（%d 键）</td></tr>' % len(DONE51_NEW))
for kk, zh, cat, icon in DONE51_NEW:
    k += 1
    u2 = URL.get(icon) or u''
    done_rows.append(u'<tr class="ok"><td>%d</td><td><img src="%s" alt=""></td><td><b>%s</b><br><span class="sub">%s</span></td><td>%s</td><td>补录</td></tr>' % (k, u2, kk, zh, cat))

# ---------- 区⑤ ----------
HUMAN = re.compile(u'(?i)helena|\\bjohn\\b|\\bbob\\b|alasie|\\bkor\\b|gladiatrix|chava|\\bjane\\b|survivor|player')
EQUIP = re.compile(u'(?i)weapon|sword|pike|spear|shield|\\bbow\\b|_bow|axe|club\\b|hatchet|pitchfork|rake|whip')
DINORE = re.compile(u'(?i)\\brex\\b|raptor|giga|thyla|wyvern|drake|reaper|owl|mosa|quetz|argy|ptera|spino|trike|stego|bronto|dilo(?![a-z])|carno|allosa|theri|yuty|doedi|anky|beaver|otter|sheep|ovis|horse|griffin|karkino|mantis|phoenix|golem|scorpion|dung|bulbdog|glowtail|featherlight|shinehorn|gasbag|velona|troodon|microraptor|dimorph|onych|megalania|basilisk|amarga|desmodus|dinopithecus|fasola|tusoteuthis|liopleurodon|achatina|anglerfish|archaeopteryx|arthropluera|basilosaurus|bee|boa|coelacanth|compy|daeodon|dimetrodon|diplocaulus|diplodocus|dodo|dolphin|eel|equus|gallimimus|hyaenodon|ichthyo|iguanodon|kairuku|kaprosuchus|kentro|lystro|mammoth|manta|megalodon|megalosaurus|megatherium|paracer|sauropod|jerboa|procoptodon|titanoboa|titanomyrma|pulmonoscorpius|castoroides|direwolf|direbear|dilophosaurus|electrophorus|onyc|rockelemental|thylacoleo')
GHOSTBONE = re.compile(u'(?i)ghost|bone|skeletal|skeleton')
PLAYER5 = set([u'HUD_Icon_Human_WinterWonderland21_SantaCostume_BC', u'HUD_FearEvolved_WerewolfCostume_Icon', u'KrampusCostume_Icon', u'Skeleton_Costume_Skin', u'TrikeHelmet_Icon'])
LAND26S = set(LAND26)

def cls5(s):
    n = s['name']
    ev = s.get('ev') or u''
    t = n + u' ' + ev
    if n in PLAYER5:
        return u'EX_player'
    if re.search(u'(?i)saddle', t):
        return u'EX_saddle'
    if re.search(u'(?i)structureskin|structure_skin|structurecosmetic', t):
        return u'EX_struct'
    if re.search(u'(?i)chibi', t):
        return u'B_chibi'
    if re.search(u'(?i)costume', t):
        if HUMAN.search(t):
            return u'EX_human'
        if EQUIP.search(t):
            return u'EX_equip'
        return u'A_costume'
    if EQUIP.search(t):
        return u'EX_equip'
    if DINORE.search(t) and GHOSTBONE.search(t):
        return u'A_costume'
    if DINORE.search(t):
        return u'C_probable'
    return u'REST'

buckets = {}
for s in SK:
    buckets.setdefault(cls5(s), []).append(s)
# v4152/v4153（用户口径）：_Animated/_Human/部位后缀 全不显示
for _k in list(buckets.keys()):
    buckets[_k] = [s for s in buckets[_k] if not _hid(s)]
# v4155（用户口径）：含 Costume 的可见项抽出单独列（排除组不动）
COSTUME = []
for _k in (u'A_costume', u'B_chibi', u'C_probable', u'REST'):
    _keep = []
    for s in buckets.get(_k, []):
        if u'Costume' in s['name']:
            COSTUME.append(s)
        else:
            _keep.append(s)
    buckets[_k] = _keep
A = buckets.get(u'A_costume', [])
A_AAA = [s for s in A if re.search(u'(?i)animated series|PrimalItemCostume_AAA', (s.get('ev') or u'') + u' ' + s['name'])]
A_LAND = [s for s in A if s not in A_AAA and s['name'] in LAND26S]
Bc = buckets.get(u'B_chibi', [])
C = buckets.get(u'C_probable', [])
EXH = buckets.get(u'EX_human', [])
EXE = buckets.get(u'EX_equip', [])
EXS = buckets.get(u'EX_saddle', [])
EXST = buckets.get(u'EX_struct', [])
EXPL = buckets.get(u'EX_player', [])
REST = buckets.get(u'REST', [])
# v4164（用户要求）：无特征项中**已落地**（词典已引用）的拆分 → 移入④区
def _landed_key(nm):
    for _kk, _vv in IZ.items():
        if isinstance(_vv, dict) and _vv.get('icon') == nm:
            return _kk
    return None
REST_DONE = []
REST_TODO = []
for _s in REST:
    _lk = _landed_key(_s['name'])
    if _lk:
        REST_DONE.append((_s, _lk))
    else:
        REST_TODO.append(_s)
REST = REST_TODO

def backname(nm):
    v = ZH_MAP.get(nm)
    if v is None:
        v = ZH_LOW.get(str(nm).lower())
    v = v or u''
    m = re.match(u'^(.*?)\\[(.*?)\\]\\s*$', v)
    if m:
        return m.group(1).strip(), m.group(2).strip()
    return v.strip(), u''

def dictinfo(nm):
    for kk, vv in IZ.items():
        if isinstance(vv, dict) and vv.get('icon') == nm:
            return (vv.get('en') or u''), (vv.get('zh') or u''), kk
    return u'', u'', u''

def param_table(lst, land=None):
    out = []
    j = 0
    for s in lst:
        j += 1
        zh2, en2 = backname(s['name'])
        en3, zh3, key = dictinfo(s['name'])
        zh_f = zh3 or zh2 or u'—'
        en_f = en3 or en2 or u'—'
        src = (s.get('ev') or u'')
        if land and s['name'] in land:
            src = u'✅ 已落地（v4150 模块>生物外观）；' + src
        if key:
            src = (u'词典键 %s' % key) + ((u'；' + src) if src else u'')
        if not src:
            src = u'（无对照记录）'
        out.append(u'<tr><td>%d</td><td><img src="%s" alt=""></td><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>' % (j, s['url'], s['name'], zh_f, en_f, src[:130]))
    return u'\n'.join(out)

# v4159（用户要求）：已落地的移入「已处理」折叠，⑥ 区只留未落地
COST_DONE = [s for s in COSTUME if IZ.get(s['name'])]
COST_TODO = [s for s in COSTUME if not IZ.get(s['name'])]
COST_DONE_HTML = u''
if COST_DONE:
    COST_DONE_HTML = u'<details><summary>⑥ 已落地 · 含 Costume 项（%d 枚，v4150/v4159 已补录 → 见④区）</summary><p>%s</p></details>' % (
        len(COST_DONE), u' '.join(u'<span class="chip">%s</span>' % s['name'] for s in COST_DONE))
r5_stats = [
    u'<tr><td><b>A · 生物外观服装</b></td><td>%d</td><td>动画剧集已隐藏；其余已并入 ⑥</td></tr>' % len(A),
    u'<tr><td><b>B · Chibi 肩宠</b></td><td>%d</td><td>迷你玩偶（挂肩宠物，非覆盖皮肤）</td></tr>' % len(Bc),
    u'<tr><td><b>C · 待核候选</b></td><td>%d</td><td>含生物名但无 PO/Beacon 证据（下表全参数）</td></tr>' % len(C),
    u'<tr><td>已排除 · 玩家皮肤</td><td>%d</td><td>圣诞老人/狼人/坎卜斯/骷髅装/三角龙头盔（用户口径：不录）</td></tr>' % len(EXPL),
    u'<tr><td>已排除 · 人类角色服装</td><td>%d</td><td>动画剧集人物、自定义幸存者</td></tr>' % len(EXH),
    u'<tr><td>已排除 · 装备皮肤</td><td>%d</td><td>武器皮肤</td></tr>' % len(EXE),
    u'<tr><td>已排除 · 鞍皮肤</td><td>%d</td><td>能覆盖鞍的（生物装备栏槽位）</td></tr>' % len(EXS),
    u'<tr><td>已排除 · 建筑皮肤</td><td>%d</td><td>StructureSkin 系列</td></tr>' % len(EXST),
    u'<tr><td><b>⑥ _Costume 单独列</b></td><td>%d</td><td>未落地 %d / 已落地 %d（已落地移入④区折叠）</td></tr>' % (len(COSTUME), len(COST_TODO), len(COST_DONE)),
    u'<tr><td><b>无特征项</b></td><td>%d</td><td>未识别/无生物证据（已落地 %d 项 → ④区；余下表全参数，默认折叠）</td></tr>' % (len(REST), len(REST_DONE)),
]

r5_details = []
if A_AAA:
    r5_details.append(u'<details><summary>A1 · 动画剧集生物服装（%d）</summary><p>%s</p></details>' % (len(A_AAA), chips(A_AAA)))
if A_LAND:
    r5_details.append(u'<details><summary>A2 · 已落地生物外观（%d，v4150 补录 → 模块>生物外观族，排模块段最末）</summary><p>%s</p></details>' % (len(A_LAND), chips(A_LAND)))
if Bc:
    r5_details.append(u'<details><summary>B · Chibi 肩宠系列（%d）</summary><p>%s</p></details>' % (len(Bc), chips(Bc)))
if EXPL:
    r5_details.append(u'<details><summary>已排除 · 玩家皮肤（%d）</summary><p>%s</p></details>' % (len(EXPL), chips(EXPL)))
if EXE:
    r5_details.append(u'<details><summary>已排除 · 装备皮肤（%d）</summary><p>%s</p></details>' % (len(EXE), chips(EXE)))
if EXH:
    r5_details.append(u'<details><summary>已排除 · 人类角色服装（%d）</summary><p>%s</p></details>' % (len(EXH), chips(EXH)))
if EXS:
    r5_details.append(u'<details><summary>已排除 · 鞍皮肤（%d）</summary><p>%s</p></details>' % (len(EXS), chips(EXS)))

# v4162（用户要求）：「非皮肤·疑似」7 项结案 → 移入已处理
done_rows.append(u'<tr class="grp"><td colspan="5">v4162 · 非皮肤·疑似结案（%d 项：确认为皮肤类并落地）</td></tr>' % len(NS_SOFT_DONE))
for _s in NS_SOFT_DONE:
    k += 1
    _key, _zh2, _en2 = u'', u'', u''
    for _kk, _vv in IZ.items():
        if isinstance(_vv, dict) and _vv.get('icon') == _s['name']:
            _key, _zh2, _en2 = _kk, (_vv.get('zh') or u''), (_vv.get('en') or u''); break
    done_rows.append(u'<tr class="ok"><td>%d</td><td><img src="%s" alt=""></td><td><b>%s</b></td><td>%s</td><td>%s</td></tr>' % (k, _s['url'], _key or _s['name'], u'皮肤类 Costume', u'✅ v4162 结案：确认皮肤类并落地词典（%s / %s）' % (_zh2 or u'—', _en2 or u'—')))

# v4164（用户要求）：无特征项中已落地项 → 移入已处理
if REST_DONE:
    done_rows.append(u'<tr class="grp"><td colspan="5">v4164 · 无特征项中已落地（%d 项：词典已引用 → 从「无特征项」移出）</td></tr>' % len(REST_DONE))
    for _s, _kk in REST_DONE:
        k += 1
        u2 = _s.get('url') or u''
        done_rows.append(u'<tr class="ok"><td>%d</td><td><img src="%s" alt=""></td><td><b>%s</b></td><td>%s</td><td>%s</td></tr>' % (k, u2, _s['name'], u'已落地', u'词典键 %s' % _kk))

# v4168/v4169 + v4170（台账登记）
done_rows.append(u'<tr class="grp"><td colspan="5">v4168/v4169 · 制导火箭弹/巡航导弹图标交换 + 咒缚武器贴合本体（16/16）</td></tr>')
k += 1
done_rows.append(u'<tr class="ok"><td>%d</td><td><span class="sub">—</span></td><td><b>RocketHomingMissile → HomingMissileAmmo_Icon ｜ TekCruiseMissile → Cruise_Missile</b></td><td>图标</td><td>%s</td></tr>' % (k, u'咒缚 16 对齐（武装 13 + 工具 3；本体在前、咒缚紧跟；含跨块全局兜底修复）'))
DONE170 = [u'PepperMask', u'Air_Jar', u'Air_Bladder', u'Sea_Dragon_Soup', u'Prime_Fish_Jerky', u'Fish_Jerky',
           u'Oryraise_Ball', u'Infected_Tooth', u'Infected_Stomach', u'Infected_Scale', u'Infected_Liver',
           u'Infected_Fin', u'Infected_Blubber', u'Dried_Seaweed', u'Daco_Sushi', u'Broth_of_Atlan',
           u'Azulberry Juice (Primitive Plus)', u'ValentinesChocolate']
done_rows.append(u'<tr class="grp"><td colspan="5">v4170 · 消耗品补录 18 键 + 新族「感染」（7 项：6 新 + 感染藤壶）+ 泰克三叉戟归「矛」</td></tr>')
k += 1
done_rows.append(u'<tr class="ok"><td>%d</td><td><span class="sub">17/18</span></td><td><b>%s</b></td><td>补录</td><td>%s</td></tr>' % (
    k, u' / '.join(DONE170),
    u'图标已配 17/18（情人节巧克力=无图标空占位；蓝莓汁=P+ 标记）；族：料理×8 / 消耗品×3 / 感染×6 / 节日×1；详见进度 050 v4170 段'))
done_rows.append(u'<tr class="grp"><td colspan="5">v4173 · 巧克力正名+配图（Box o\' Chocolates / VDay_icon）+ WormGum（虫胶）+ Air 两项→工具·水容器族 + 巡航图标结案</td></tr>')
k += 1
done_rows.append(u'<tr class="ok"><td>%d</td><td><img src="%s" alt=""></td><td><b>WormGum / 盒装巧克力 / Air_Jar / Air_Bladder</b></td><td>补录+排序</td><td>%s</td></tr>' % (
    k, URL.get(u'Worm_Gum') or u'', u'料理子序：亚特兰汤18→虫胶19；水容器：空气罐400/气囊401；种子族新建：植物种子R→食肉植物种子；巡航俩图标移出区①（现用图 HUD_TEKCruiseMissile_Icon）'))

# ---------- v4167：恐龙装备栏外观 · 官方全集（12 款）----------
DINO12 = [
    (u'可爱恐龙帽子', u'Cute Dino Helmet', u'PrimalItemSkin_DinoCute', u'ASA + ASE', u'DinoHelmet_Icon', u'ok', u'3275392805', u''),
    (u'恐龙兔耳朵', u'Dino Bunny Ears', u'PrimalItemSkin_DinoBunnyHat', u'ASA + ASE', None, None, u'2021301336', u'可改变鞍外观，让坐骑看起来棒极了'),
    (u'恐龙巫师帽', u'Dino Witch Hat', u'PrimalItemSkin_DinoWitchHat', u'ASA + ASE', None, None, u'302900601', u'女巫帽子让你的坐骑看起来具有魔力'),
    (u'恐龙圣诞帽', u'Dino Santa Hat', u'PrimalItemSkin_DinoSantaHat', u'ASA + ASE', None, None, u'1780346630', u'喜庆（ASA 版类名后缀 _Craftable）'),
    (u'恐龙眼镜', u'Dino Glasses', u'PrimalItemSkin_DinoSpecs', u'ASE', None, None, u'1203181700', u''),
    (u'恐龙圆形太阳镜', u'Dino Round Sunglasses', u'PrimalItemSkin_DinoSpecs_RoundGlasses', u'ASE', u'HUD_RoundSunglasses_Icon', u'cand', u'2816203811', u'图标候选（字面 Round Sunglasses）'),
    (u'恐龙复活节小鸡帽', u'Dino Easter Chick Hat', u'PrimalItemSkin_DinoChickHat', u'ASE', None, None, u'2713995952', u'像一只可爱的小黄鸡'),
    (u'恐龙复活节彩蛋帽', u'Dino Easter Egg Hat', u'PrimalItemSkin_DinoEasterEggHat', u'ASE', None, None, u'628803384', u'让坐骑看起来像是刚孵出来的'),
    (u'恐龙棉花糖帽', u'Dino Marshmallow Hat', u'PrimalItemSkin_DinoMarshmallowHat', u'ASE', u'HUD_Hat_Marshmallow_Icon', u'cand', u'590319322', u'图标候选（字面 Marshmallow）'),
    (u'恐龙派对帽', u'Dino Party Hat', u'PrimalItemSkin_DinoPartyHat', u'ASE', None, None, u'1673995299', u'戴着这个帽子让坐骑看起来很欢乐'),
    (u'恐龙山姆大叔帽', u'Dino Uncle Sam Hat', u'PrimalItemSkin_TopHat_Summer_Dino', u'ASE', u'HUD_Hat_July4th_Icon', u'cand', u'1085005727', u'图标候选（July4th 活动同源）；玩家版=PrimalItemSkin_TopHat_Summer'),
    (u'恐龙的恐怖南瓜头套', u'Scary Dino Pumpkin Helmet', u'PrimalItemSkin_FE_PumpkinHat_Dino', u'ASE', None, None, u'3410746485', u'Beacon 实锤；玩家版=PrimalItemSkin_FE_PumpkinHat'),
]
r_dino12 = []
for _j, (_zh, _en, _cls, _plat, _icon, _ist, _key, _note) in enumerate(DINO12):
    if _icon and _icon in URL:
        _img = u'<img src="%s" alt="">' % URL[_icon]
    else:
        _img = u'<span class="sub">未收录</span>'
    if not _icon:
        _ic = u'&#10007; 未收录（全库已核）'
    elif _ist == u'cand':
        _ic = u'&#10003; %s <span class="tag">候选待核</span>' % _icon
    else:
        _ic = u'&#10003; %s' % _icon
    r_dino12.append(u'<tr><td>%d</td><td>%s</td><td><b>%s</b></td><td>%s</td><td><code>%s</code></td><td>%s</td><td>%s</td><td>%s</td><td class="sub">%s</td></tr>' % (
        _j + 1, _img, _zh, _en, _cls, _plat, _ic, _key, (_note or u'—')))

# ---------- v4167：节日消耗品缺口 ----------
FEST1 = [
    (u'节日恐龙糖（官方）', u'Festive Dino Candy', u'PrimalItemConsumable_WW_Crafted_WWCandy（+ WW_Craftable 无品质对偶）', u'ASA + ASE', u'ChristmasCandy_Icon', u'Beacon ArkSA 实锤 + 官方中文 2311506781', u'词典未录；v4165 已录 ChristmasCandy_Icon（疑同物）'),
    (u'情人节蛋糕（自拟）', u"Valentine's Cake", u'（类名 WIKI 未载：blueprint 空）', u'ASE', u'Valentine27s_Cake', u'ARK Wiki 实锤：Valentine\'s Day 3（2018）活动 5% 掉落；图标=本库 Valentine27s_Cake（红蛋糕图已核）', u'未录；WIKI 证其真实存在（此前「疑似未实装」判断撤销）'),
    (u'周年蛋糕切片（自拟）', u'ARK Anniversary Cake Slice', u'PrimalItemCustomFoodRecipe_Type_BdayCake', u'ASE', u'ARK_Anniversary_Cake_Slice', u'PO 实锤（CustomFoodRecipe）+ icons2 consumables', u'未录；类名 v4167 深挖补全'),
    (u'复活节糖果（自拟）', u'(EasterEgg Candy)', u'（WIKI 无独立物品）', u'待核', u'HUD_EasterEgg_Candy_Icon', u'icons2 eggs；WIKI 无此物页（推断对应复活节版恐龙糖果 EasterDinoCandy 的 HUD 图标）', u'未录；待核（候选对应=EasterDinoCandy）'),
    (u'能量蛋糕（自拟）', u'Energy Cake', u'（全库无类名；WIKI 实查无此物品）', u'待核', u'Energy Cake', u'icons2 consumables；WIKI 搜 EnergyCake/Energy Cake 均无此物（仅 Energy Brew）', u'未录；核证：WIKI 无此物品（图标或为遗留资源）'),
    (u'万圣节活动图标（自拟）', u'（HUD_Event_Halloween_BC）', u'（全库无类名）', u'待核', u'HUD_Event_Halloween_BC', u'icons2 skins；WIKI 搜 HUD_Event_Halloween 0 命中（UI 资源名）；用户指示：按万圣节活动图标直接补录', u'未录；本批仅表内呈现'),
    (u'盒装巧克力（官方名）', u"Box o' Chocolates", u'PrimalItemConsumable_ValentinesChocolate', u'ASA + ASE', u'VDay_icon', u'ARK Wiki 实锤官方名+gfi；官方中文库 903703564；Love Ascended 2024（ASA）有', u'✅ v4173 正名+配图（VDay_icon 心形礼盒）'),
]
r_fest1 = []
for _j, (_zh, _en, _cls, _plat, _icon, _ev, _st) in enumerate(FEST1):
    _img = (u'<img src="%s" alt="">' % URL[_icon]) if (_icon and _icon in URL) else u'<span class="sub">未收录</span>'
    r_fest1.append(u'<tr><td>%d</td><td>%s</td><td><b>%s</b></td><td>%s</td><td><code>%s</code></td><td>%s</td><td class="sub">%s</td><td class="sub">%s</td></tr>' % (
        _j + 1, _img, _zh, _en, _cls, _plat, _ev, _st))

FEST2 = [
    (u'情人节恐龙糖果', u"Valentine's Dino Candy", u'PrimalItemConsumable_ValentinesDinoCandy', u'ASE', u'官方中文 456199239 + Beacon Ark 实锤', u'未录'),
    (u'情人节恐龙糖果', u'Love Ascended Dino Candy', u'（PO/Beacon 均无收录）', u'ASA（Love Ascended 活动）', u'官方中文 2635060601', u'未录'),
    (u'情人节恐龙糖果', u'Love Evolved Dino Candy', u'（PO/Beacon 均无收录）', u'ASE（Love Evolved 活动）', u'官方中文 3759433122', u'未录'),
    (u'夏日漩涡太妃糖', u'Summer Swirl Taffy', u'PrimalItemConsumable_Crafted_FourthOfJulyDinoCandy（+ Craftable 对偶）', u'ASE', u'官方中文 1977946177 + Beacon Ark 实锤', u'未录'),
    (u'感恩节糖果', u'Thanksgiving Candy', u'PrimalItemConsumable_TT_Crafted_ThanksgivingCandy（+ Craftable 对偶）', u'ASE', u'官方中文 2228662427 + Beacon Ark 实锤', u'未录'),
    (u'节日恐龙颜色糖果效果（非物品）', u'Candy Effect', u'Buff_FestiveDinoColors（Buff，非独立物品）', u'ASA', u'PO 实锤（ModifierName）+ 官中 615578059', u'核证排除：615578059「恐龙糖果」= Buff 效果名，非物品'),
]
r_fest2 = []
for _j, (_zh, _en, _cls, _plat, _ev, _st) in enumerate(FEST2):
    r_fest2.append(u'<tr><td>%d</td><td><span class="sub">未收录（全库已核）</span></td><td><b>%s</b></td><td>%s</td><td><code>%s</code></td><td>%s</td><td class="sub">%s</td><td class="sub">%s</td></tr>' % (
        _j + 1, _zh, _en, _cls, _plat, _ev, _st))

C_TABLE = param_table(C)
REST_TABLE = param_table(REST)
COST_TABLE = param_table(COST_TODO, LAND26S)

html = u'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>图标未录对照表 v4171（恐龙外观 12 款 + 节日缺口 + v4170 台账 + 六分类）</title>
<style>
body{font:13px/1.6 "Microsoft YaHei",sans-serif;background:#0f1115;color:#d8dee9;margin:24px}
h2{margin:0 0 6px}
h3{margin:26px 0 8px;color:#cbd5e1;border-bottom:1px solid #2a2f3a;padding-bottom:4px}
p{margin:4px 0}
.sum{color:#93a1b5;margin:0 0 14px}
table{border-collapse:collapse;width:100&#37;;background:#161a22;margin-bottom:10px}
th,td{border:1px solid #2a2f3a;padding:5px 8px;vertical-align:middle}
th{background:#1d2430;color:#aab8cc;text-align:left;white-space:nowrap}
img{width:40px;height:40px;object-fit:contain;background:#0b0d11;border-radius:6px;display:block}
tr:hover{background:#1a2029}
tr.grp td{background:#1d2430;color:#cbd5e1;font-weight:bold}
.sub{color:#7c8a9e;font-size:11px}
.tag{display:inline-block;background:#3b2b00;color:#fbbf24;border:1px solid #7c5a00;border-radius:4px;padding:0 5px;font-size:11px;margin-left:6px}
.chip{display:inline-block;background:#1a2029;border:1px solid #2a2f3a;border-radius:4px;padding:1px 6px;margin:2px;font-size:12px;color:#aab8cc}
details{margin:8px 0;border:1px solid #2a2f3a;border-radius:8px;padding:6px 10px;background:#131820}
summary{cursor:pointer;color:#cbd5e1}
.ok td:nth-child(4){color:#34d399}
.note{margin-top:14px;padding:10px 12px;border:1px solid #2a2f3a;border-radius:8px;background:#131820;color:#93a1b5;font-size:12px}
.note b{color:#cbd5e1}
</style>
</head>
<body>
<h2>图标未录对照表 v4171</h2>
<p class="sum">生成时间：{TS} ｜ 判据：词典 icon / 设施表 / icon_anti_color 引用扫描（icons2 共 5198 图）</p>
<p class="sum">区① 完全未录（{N1B}，已剔除退休旧图与用户判定项）；区② 仅兜底名（{N2}）；区⑤ 非人生物皮肤清单（_Animated/_Human 已隐藏）</p>

<h3>&#11088; 恐龙装备栏外观 · 官方全集（12 款）</h3>
<p class="sum">官方全集 = ASA 4 款（Cute/Bunny/Witch/Santa）+ ASE 独有 8 款；中文/英文/官方 Key 取自官方中文库（ShooterGame.json），类名为 v4167 深挖补全的完整类名（PO SourceLocation / Beacon 实锤），平台取自 Beacon 双库。图标：1 实锤 + 3 候选（已标注）；其余 8 款经 icons2 全库核证无独立图标。另：DinoMask_Icon 图标在库（对应物品待核）。</p>
<table>
<tr><th>#</th><th>图标</th><th>中文（官方）</th><th>英文（官方）</th><th>类名</th><th>平台</th><th>图标情况</th><th>官方 Key</th><th>备注</th></tr>
{DINO12}
</table>

<h3>&#11088; 节日消耗品缺口（v4167 深挖补全，本批仅表内呈现 · 未部署）</h3>
<p><b>B1 · 用户指定候选（7 项；中文=官方或自拟，自拟标注于括号）</b></p>
<table>
<tr><th>#</th><th>图标</th><th>中文</th><th>英文</th><th>类名</th><th>平台</th><th>证据</th><th>现状/建议</th></tr>
{FEST1}
</table>
<p><b>B2 · 补充发现（6 项；含核证排除 1 项）</b></p>
<table>
<tr><th>#</th><th>图标</th><th>中文（官方）</th><th>英文（官方）</th><th>类名</th><th>平台</th><th>证据</th><th>现状</th></tr>
{FEST2}
</table>

<h3>① 六分类 · 完全未录（{N1B} 项）</h3>
<table>
<tr><th>#</th><th>图标</th><th>名称</th><th>分类</th></tr>
{R1}
</table>
{RET}

<h3>② 六分类 · 仅兜底名（词典未录，{N2} 项）</h3>
<table>
<tr><th>#</th><th>图标</th><th>名称</th><th>分类</th></tr>
{R2}
</table>
{EXCL2H}

<h3>③ skins 分类甄别（689 图）</h3>
<p class="sum">判据：PO ＋ Beacon ArkSA 库双源匹配 ＋ 词典 skin 标记</p>
<table>
<tr><th>判定</th><th>数量</th><th>说明</th></tr>
<tr><td><b>真皮肤（有据）</b></td><td>{NSK}</td><td>PO/Beacon 双源匹配到真实皮肤类目（含 ARK 动画剧集服装 38）</td></tr>
<tr><td><b>非皮肤 · 确定</b></td><td>{NDEF}</td><td>✅ 全部结案：13 项归档（词典引用 11 / 管理 2）+ 2 项已落地（蛋糕）</td></tr>
<tr><td><b>非皮肤 · 疑似</b></td><td>{NSOFT}</td><td>✅ 服装类 7 项已结案（v4162 → ④区）；活动类（Corrupt 套等）已隐藏</td></tr>
<tr><td><b>待核 · 服装外观类</b></td><td>{NPW}</td><td>名称含外观关键词，本地无对照记录（大概率皮肤）</td></tr>
<tr><td><b>待核 · 其它</b></td><td>{NPO}</td><td>无外观关键词、本地无对照记录，建议人工核对</td></tr>
</table>

<p><b>非皮肤 · 确定（{NDEF} · 已结案）</b></p>
{CLOSE}

<p><b>非皮肤 · 疑似（{NSOFT}）</b></p>
<table>
<tr><th>#</th><th>图标</th><th>名称</th><th>证据</th><th>处理</th></tr>
{RNS}
</table>

<details><summary>待核 · 服装外观类（{NPW}，已隐藏 _Animated/_Human）</summary><p>{CPW}</p></details>
<details><summary>待核 · 其它（{NPO}，已隐藏 _Animated/_Human）</summary><p>{CPO}</p></details>
<details><summary>真皮肤 · 有据（{NSK}，已隐藏 _Animated/_Human）</summary><p>{CSK}</p></details>

<h3>④ 已处理（v4147 ~ v4162）</h3>
<details><summary>点击展开已处理明细（{NDONE} 行：换图/英文/补录/ASE/生物外观落地）</summary>
<table>
<tr><th>#</th><th>图标</th><th>名称</th><th>类型</th><th>处理</th></tr>
{RDONE}
</table>
</details>
{COSTDONE}

<h3>⑤ 非人生物皮肤清单（v4150 口径）</h3>
<p class="sum">口径：只列非人生物（恐龙等）本体外观皮肤；玩家皮肤、装备皮肤、能覆盖鞍的鞍皮肤、建筑皮肤均不列（各排除组折叠备查）。</p>
<table>
<tr><th>分组</th><th>数量</th><th>说明</th></tr>
{R5S}
</table>

<p><b>C · 待核候选（{NC}，全参数）</b></p>
<table>
<tr><th>#</th><th>图标</th><th>完整名称</th><th>中文</th><th>英文</th><th>来源/证据</th></tr>
{CT}
</table>

<details><summary><b>无特征项（{NREST}）全参数表 —— 点击展开</b></summary>
<table>
<tr><th>#</th><th>图标</th><th>完整名称</th><th>中文</th><th>英文</th><th>来源/证据</th></tr>
{RT}
</table>
</details>

<p><b>⑥ _Costume 单独列 —— 未落地（{NCOST}，全参数；已落地入④区折叠）</b></p>
<table>
<tr><th>#</th><th>图标</th><th>完整名称</th><th>中文</th><th>英文</th><th>来源/证据</th></tr>
{COST}
</table>

<div class="note"><b>说明：</b>区② 已按用户判定移除 12 项；区⑤ 已隐藏 _Animated/_Human 皮肤（用户口径：无需显示）；A2 已落地（v4150 补录为模块>生物外观族，整族排模块段最末）；C 与无特征项均为全参数表（图标/完整名称/中文/英文/来源），其中中文英文优先取词典、其次取图标兜底名，均无则显示「—」。<br>
排除组：玩家皮肤、人类角色服装、装备皮肤、鞍皮肤、建筑皮肤 —— 均折叠备查。</div>
</body>
</html>'''.replace(u'{R1}', u'\n'.join(r1)).replace(u'{R2}', u'\n'.join(r2)).replace(u'{EXCL2H}', EXCL2_HTML) \
   .replace(u'{CLOSE}', NS_CLOSE).replace(u'{RNS}', r_ns_soft) \
   .replace(u'{RDONE}', u'\n'.join(done_rows)) \
   .replace(u'{CPW}', chips_hid(pw)).replace(u'{CPO}', chips_hid(po)).replace(u'{CSK}', chips_hid(skin_hard)) \
   .replace(u'{R5S}', u'\n'.join(r5_stats)).replace(u'{R5D}', u'\n'.join(r5_details)) \
   .replace(u'{CT}', C_TABLE).replace(u'{RT}', REST_TABLE) \
   .replace(u'{NCOST}', str(len(COST_TODO))).replace(u'{COST}', COST_TABLE) \
   .replace(u'{COSTDONE}', COST_DONE_HTML) \
   .replace(u'{RET}', RET_HTML + ARCH_HTML) \
   .replace(u'{N1B}', str(len(r1))) \
   .replace(u'{N2}', str(len(gray))) \
   .replace(u'{NSK}', str(len(skin_hard))).replace(u'{NDEF}', str(len(ns_def))).replace(u'{NSOFT}', str(len(ns_soft_show))) \
   .replace(u'{NPW}', str(len(pw))).replace(u'{NPO}', str(len(po))) \
   .replace(u'{NDONE}', str(k)).replace(u'{NC}', str(len(C))).replace(u'{NREST}', str(len(REST))) \
   .replace(u'{DINO12}', u'\n'.join(r_dino12)) \
   .replace(u'{FEST1}', u'\n'.join(r_fest1)).replace(u'{FEST2}', u'\n'.join(r_fest2)) \
   .replace(u'{TS}', TS)
html = html.replace(u'dock 兜底名', u'图标兜底名')
html = re.sub(r'\n{3,}', u'\n\n', html)
io.open(OUT, 'w', encoding='utf-8', newline='').write(html)
io.open(B + r'\tmp\_v4150_table_out.txt', 'w', encoding='utf-8', newline='').write(
    u'OK r1=%d retired=%d r2=%d done=%d A=%d AAA=%d ALAND=%d B=%d C=%d EXPL=%d EXH=%d EXE=%d EXS=%d EXST=%d REST=%d bytes=%d blanks=%d' % (
        len(r1), len(retired), len(r2), k, len(A), len(A_AAA), len(A_LAND), len(Bc), len(C), len(EXPL), len(EXH), len(EXE), len(EXS), len(EXST), len(REST), len(html), len(re.findall(r'\n{3,}', html))))
print('OK')
