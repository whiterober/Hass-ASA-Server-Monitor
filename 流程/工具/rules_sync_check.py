# -*- coding: utf-8 -*-
# 新增生物·双源一致性检查（dino-import.html 硬编码数组 vs dino_rules.json）
# 用法: python 流程\工具\rules_sync_check.py
# 背景: 页面加载 lbRulesMerge() 将 dino_rules.json 与 html 数组【并集合并】（_union 只加不减）
#       ⇒ 删除/移出清单项若只改 html，JSON 旧名单会在运行时「回灌」（v4667→v4668 血泪案例）；
#       本脚本列出差异供核对，重点：各数组「仅 JSON 独有」条目 = 回灌风险。
import io, os, re, sys, json, time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
OUT = os.path.join(HERE, '_last_rules_sync.txt')
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

# html 数组名 <-> JSON 键（对齐 lbRulesMerge 的 _union 调用）
MAP = [
    ('LB_UNTAMEABLE_SPECIAL', 'untameableSpecial'),
    ('LB_TAMEABLE_FORCE', 'tameableForce'),
    ('LB_STEAL_EGG', 'stealEgg'),
    ('LB_OWNED_UNITS', 'ownedUnits'),
    ('LB_CATCHABLE_FISH', 'catchableFish'),
    ('LB_HIDDEN_SPECIAL', 'hiddenSpecial'),
    ('LB_EXTRA_FORCE', 'extraForce'),
    ('LB_TEST_EXTRA', 'testExtra'),
    ('LB_HIDDEN_FORCE', 'hiddenForce'),
    ('LB_HIDDEN_DUP', 'hiddenDup'),
    ('LB_PUBFAC_PREFIX', 'pubfacPrefix'),
]

L = []


def w(s):
    L.append(s)
    print(s)


def dump():
    io.open(OUT, 'w', encoding='utf-8', newline='').write('\n'.join(L))


def html_array(html, name):
    """提取 var NAME = [ ... ]; 内的字符串元素（先剥离注释防误采）"""
    m = re.search(r'var\s+%s\s*=\s*\[(.*?)\];' % re.escape(name), html, re.S)
    if not m:
        return None
    blk = m.group(1)
    blk = re.sub(r'/\*.*?\*/', '', blk, flags=re.S)
    blk = re.sub(r'//[^\n]*', '', blk)
    return [a or b for a, b in re.findall(r"'([^']*)'|\"([^\"]*)\"", blk)]


def html_special_names(html):
    m = re.search(r'var\s+LB_SPECIAL_NAMES\s*=\s*\{(.*?)\n\};', html, re.S)
    if not m:
        return {}
    blk = re.sub(r'//[^\n]*', '', m.group(1))
    return dict(re.findall(r"'([^']+)'\s*:\s*'([^']*)'", blk))


def main():
    htmlp = os.path.join(ROOT, 'dino-import.html')
    jsonp = os.path.join(ROOT, 'dino_rules.json')
    w('== 双源一致性检查（html 硬编码数组 vs dino_rules.json）==')
    w('[时间] ' + time.strftime('%Y-%m-%d %H:%M:%S'))
    if not os.path.exists(htmlp) or not os.path.exists(jsonp):
        w('缺文件: %s / %s' % (htmlp, jsonp))
        dump()
        return
    html = io.open(htmlp, encoding='utf-8', errors='ignore').read()
    j = json.load(io.open(jsonp, encoding='utf-8'))
    w('[文件] html %dB | dino_rules.json %dB (ver=%s)' % (
        len(html.encode('utf-8')), os.path.getsize(jsonp), j.get('ver', '?')))
    w('')
    w('--- [1] 清单数组对比（union 语义：html ∪ JSON 均为运行时生效；重点=「仅JSON」条目）---')
    total_warn = 0
    for hname, jkey in MAP:
        ha = html_array(html, hname)
        if ha is None:
            w('  %-22s html 未找到（跳过）' % hname)
            continue
        ja = j.get(jkey)
        if ja is None:
            w('  %-22s JSON 无键 %s（仅 html 生效）' % (hname, jkey))
            continue
        only_j = [x for x in ja if x not in ha]
        only_h = [x for x in ha if x not in ja]
        note = []
        if only_j:
            note.append('⚠ 仅JSON=%d（回灌风险：html 已删但 JSON 未删 → 运行时仍生效）' % len(only_j))
            total_warn += 1
        if only_h:
            note.append('仅HTML=%d（仅 html 生效，可同步 JSON）' % len(only_h))
        w('  %-22s html=%-4d json=%-4d | %s' % (hname, len(ha), len(ja), '；'.join(note) if note else 'OK'))
        for x in only_j:
            w('      ⚠ 仅JSON: %s' % x)
        for x in only_h:
            w('      仅HTML: %s' % x)
    w('')
    w('--- [2] specialNames 值对比（显示名 html 优先；差异建议同步 JSON 防复活）---')
    hs = html_special_names(html)
    js = j.get('specialNames', {})
    diff = 0
    for k in sorted(set(hs) | set(js)):
        hv = hs.get(k)
        jv = js.get(k)
        if hv is not None and jv is not None and hv != jv:
            w('  ≠ %s: html=「%s」 json=「%s」' % (k, hv, jv))
            diff += 1
    w('  值差异: %d 处' % diff)
    w('')
    w('--- [3] 结论 ---')
    if total_warn == 0 and diff == 0:
        w('  双源一致 OK（无回灌风险）')
    else:
        w('  需核对: %d 个数组存在「仅JSON」条目（若为已删/移出项 → 必须从 dino_rules.json 删除）；specialNames 差异 %d 处' % (total_warn, diff))
    w('  [提示] 修复后：字符串级编辑 dino_rules.json（count==1 断言 + json.loads 校验 + 备份）→ bump LB_VERSION + pwa/sw.js VER → tmp\\_deploy_cf.py 部署')
    dump()


if __name__ == '__main__':
    main()
