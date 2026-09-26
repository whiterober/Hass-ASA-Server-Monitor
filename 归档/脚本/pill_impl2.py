# -*- coding: utf-8 -*-
"""Implement unified Pill control for column + BQ"""
import sys

with open(r'B:\项目\Hass ASA Server Monitor\www\asa-admin.html', 'rb') as f:
    c = f.read()

changes = 0
D = b'"'  # double quote
BS = b'\\'  # backslash
EQ = BS + D  # escaped double quote: \"

# ============================================================
# 1. Add CSS
# ============================================================
css_marker = b'.sr-cat-card > .sr-items { flex: 1 1 100%; min-width: 100%; }'
pos = c.find(css_marker)
if pos > 0:
    new_css = (
        b'.cat-col-bq { display:inline-flex;align-items:center;border:1px solid var(--border);border-radius:6px;overflow:hidden;height:24px;font-size:0.65em;flex-shrink:0;user-select:none;background:var(--input-bg,transparent); }\r\n'
        b'.cat-col-bq .cat-col-seg { padding:1px 6px;cursor:pointer;color:var(--text);opacity:.45;white-space:nowrap;line-height:22px;transition:opacity .15s,background .15s,color .15s; }\r\n'
        b'.cat-col-bq .cat-col-seg:hover { opacity:.75; }\r\n'
        b'.cat-col-bq .cat-col-seg.active { opacity:1;background:var(--accent);color:#000;font-weight:bold; }\r\n'
        b'.cat-col-bq .cat-col-divider { width:1px;height:16px;background:var(--border);flex-shrink:0;align-self:center; }\r\n'
        b'.cat-col-bq .cat-col-seg.cat-bq-seg { padding:1px 8px; }\r\n'
        b'.cat-col-bq .cat-bq-seg.active { opacity:1;color:var(--accent);font-weight:bold;background:transparent; }\r\n'
    )
    c = c[:pos] + new_css + c[pos:]
    changes += 1
    print('1. CSS added')

# ============================================================
# 2. Replace render template brCatCol + brCatBQ with pill
# ============================================================
# Find brCatCol in render
idx_col = c.find(
    b"html += '<select id=" + EQ + b"brCatCol'+si+'_'+bi+'_'+ri+'_'+ci+" + EQ +
    b" style=" + EQ + b"width:38px;padding:1px;font-size:0.65em;margin:0" + EQ + b"><option value=" + EQ + b"0" + EQ + b"'+(cat.column===0?' selected':'')+'>"
)
if idx_col > 0:
    line_end = c.find(b"';", idx_col + 150) + 2
    # Find brCatBQ line after
    bq_start = c.find(
        b"html += '<label style=" + EQ + b"font-size:0.6em;margin:0;display:flex;align-items:center;gap:1px;white-space:nowrap" + EQ + b"><input type=" + EQ + b"checkbox" + EQ + b" id=" + EQ + b"brCatBQ'+si+'_'+bi+'_'+ri+'_'+ci+" + EQ + b" ",
        idx_col
    )
    if bq_start > 0:
        bq_end = c.find(b"';", bq_start + 150) + 2
        pill = (
            b"html += '<span class=" + EQ + b"cat-col-bq" + EQ + b" id=" + EQ + b"brCatColBQ'+si+'_'+bi+'_'+ri+'_'+ci+" + EQ + b"'>';\r\n"
            b"html += '<span class=" + EQ + b"cat-col-seg'+(cat.column===0?' active':'')+" + EQ + b" data-col=" + EQ + b"0" + EQ + b" onclick=" + EQ + b"setCatCol(this,0)" + EQ + b">\xe5\x88\x971</span>';\r\n"
            b"html += '<span class=" + EQ + b"cat-col-seg'+(cat.column===1?' active':'')+" + EQ + b" data-col=" + EQ + b"1" + EQ + b" onclick=" + EQ + b"setCatCol(this,1)" + EQ + b">\xe5\x88\x972</span>';\r\n"
            b"html += '<span class=" + EQ + b"cat-col-divider" + EQ + b"></span>';\r\n"
            b"html += '<span class=" + EQ + b"cat-col-seg cat-bq-seg'+(cat.use_blockquote!==false?' active':'')+" + EQ + b" onclick=" + EQ + b"toggleCatBQ(this)" + EQ + b">\xe5\xbc\x95\xe7\x94\xa8</span>';\r\n"
            b"html += '<input type=" + EQ + b"checkbox" + EQ + b" id=" + EQ + b"brCatBQ'+si+'_'+bi+'_'+ri+'_'+ci+" + EQ + b" '+(cat.use_blockquote!==false?'checked':'')+' onchange=" + EQ + b"toggleBQControls(this)" + EQ + b" style=" + EQ + b"display:none" + EQ + b">';\r\n"
            b"html += '<select id=" + EQ + b"brCatCol'+si+'_'+bi+'_'+ri+'_'+ci+" + EQ + b" style=" + EQ + b"display:none" + EQ + b"><option value=" + EQ + b"0" + EQ + b"'+(cat.column===0?' selected':'')+'>\xe5\x88\x971</option><option value=" + EQ + b"1" + EQ + b"'+(cat.column===1?' selected':'')+'>\xe5\x88\x972</option></select>';\r\n"
            b"html += '</span>';\r\n"
        )
        c = c[:idx_col] + pill + c[bq_end:]
        changes += 1
        print('2. Render template pill replaced')
    else:
        print('2. brCatBQ NOT FOUND')
else:
    print('2. brCatCol NOT FOUND in render')

# ============================================================
# 3. Replace addStorageCat brCatCol + brCatBQ
# ============================================================
ac_pos = c.find(b'function addStorageCat')
idx3 = c.find(
    b"h += '<select id=" + EQ + b"brCatCol'+si+'_'+bi+'_'+ri+'_'+ci+" + EQ +
    b" style=" + EQ + b"width:38px;padding:1px;font-size:0.65em;margin:0" + EQ + b"><option value=" + EQ + b"0" + EQ + b">",
    ac_pos
)
if idx3 > 0:
    le3 = c.find(b"';", idx3 + 150) + 2
    bq3 = c.find(
        b"h += '<label style=" + EQ + b"font-size:0.6em;margin:0;display:flex;align-items:center;gap:1px;white-space:nowrap" + EQ + b"><input type=" + EQ + b"checkbox" + EQ + b" id=" + EQ + b"brCatBQ'+si+'_'+bi+'_'+ri+'_'+ci+" + EQ + b" checked",
        idx3
    )
    if bq3 > 0:
        be3 = c.find(b"';", bq3 + 150) + 2
        pill3 = (
            b"h += '<span class=" + EQ + b"cat-col-bq" + EQ + b" id=" + EQ + b"brCatColBQ'+si+'_'+bi+'_'+ri+'_'+ci+" + EQ + b"'>';\r\n"
            b"h += '<span class=" + EQ + b"cat-col-seg active" + EQ + b" data-col=" + EQ + b"0" + EQ + b" onclick=" + EQ + b"setCatCol(this,0)" + EQ + b">\xe5\x88\x971</span>';\r\n"
            b"h += '<span class=" + EQ + b"cat-col-seg" + EQ + b" data-col=" + EQ + b"1" + EQ + b" onclick=" + EQ + b"setCatCol(this,1)" + EQ + b">\xe5\x88\x972</span>';\r\n"
            b"h += '<span class=" + EQ + b"cat-col-divider" + EQ + b"></span>';\r\n"
            b"h += '<span class=" + EQ + b"cat-col-seg cat-bq-seg active" + EQ + b" onclick=" + EQ + b"toggleCatBQ(this)" + EQ + b">\xe5\xbc\x95\xe7\x94\xa8</span>';\r\n"
            b"h += '<input type=" + EQ + b"checkbox" + EQ + b" id=" + EQ + b"brCatBQ'+si+'_'+bi+'_'+ri+'_'+ci+" + EQ + b" checked onchange=" + EQ + b"toggleBQControls(this)" + EQ + b" style=" + EQ + b"display:none" + EQ + b">';\r\n"
            b"h += '<select id=" + EQ + b"brCatCol'+si+'_'+bi+'_'+ri+'_'+ci+" + EQ + b" style=" + EQ + b"display:none" + EQ + b"><option value=" + EQ + b"0" + EQ + b" selected>\xe5\x88\x971</option><option value=" + EQ + b"1" + EQ + b">\xe5\x88\x972</option></select>';\r\n"
            b"h += '</span>';\r\n"
        )
        c = c[:idx3] + pill3 + c[be3:]
        changes += 1
        print('3. addStorageCat pill replaced')
    else:
        print('3. brCatBQ NOT FOUND in ac')
else:
    print('3. brCatCol NOT FOUND in ac')

# ============================================================
# 4. Update reorderCatCard order
# ============================================================
old_o = b'["brCatCol","brCatBQ","brCatMarkerColor"'
new_o = b'["brCatColBQ","brCatMarkerColor"'
c = c.replace(old_o, new_o)
if old_o in c:
    pass  # already replaced above
print('4. Order checked')

# ============================================================
# 5. New JS functions + toggleBQControls update
# ============================================================
tg_end = c.find(b'function rmSrRow(el)')
if tg_end > 0:
    new_funcs = (
        b'function setCatCol(el, col) {\r\n'
        b"  var pill = el.closest('.cat-col-bq');\r\n"
        b'  if (!pill) return;\r\n'
        b"  pill.querySelectorAll('.cat-col-seg:not(.cat-bq-seg)').forEach(function(s){\r\n"
        b"    s.classList.toggle('active', parseInt(s.dataset.col) === col);\r\n"
        b'  });\r\n'
        b"  var sel = pill.querySelector('select[id^=brCatCol]');\r\n"
        b'  if (sel) sel.value = col;\r\n'
        b'}\r\n'
        b'function toggleCatBQ(el) {\r\n'
        b"  var pill = el.closest('.cat-col-bq');\r\n"
        b'  if (!pill) return;\r\n'
        b"  var cb = pill.querySelector('input[type=checkbox][id^=brCatBQ]');\r\n"
        b'  if (!cb) return;\r\n'
        b'  cb.checked = !cb.checked;\r\n'
        b"  el.classList.toggle('active', cb.checked);\r\n"
        b"  if (typeof toggleBQControls === 'function') toggleBQControls(cb);\r\n"
        b'}\r\n'
        b'function buildCatColBQPill(card) {\r\n'
        b"  if (card.querySelector('.cat-col-bq')) return;\r\n"
        b"  var sel = card.querySelector('select[id^=brCatCol]');\r\n"
        b"  var cb = card.querySelector('input[type=checkbox][id^=brCatBQ]');\r\n"
        b'  if (!sel || !cb) return;\r\n'
        b'  var col = parseInt(sel.value)||0;\r\n'
        b'  var checked = cb.checked;\r\n'
        b"  var pill = document.createElement('span');\r\n"
        b"  pill.className = 'cat-col-bq';\r\n"
        b"  pill.id = sel.id.replace('brCatCol','brCatColBQ');\r\n"
        b"  var s0 = document.createElement('span');\r\n"
        b"  s0.className = 'cat-col-seg' + (col===0?' active':'');\r\n"
        b"  s0.dataset.col = '0'; s0.textContent = '\xe5\x88\x971'; s0.onclick = function(){setCatCol(this,0);};\r\n"
        b"  var s1 = document.createElement('span');\r\n"
        b"  s1.className = 'cat-col-seg' + (col===1?' active':'');\r\n"
        b"  s1.dataset.col = '1'; s1.textContent = '\xe5\x88\x972'; s1.onclick = function(){setCatCol(this,1);};\r\n"
        b"  var div = document.createElement('span');\r\n"
        b"  div.className = 'cat-col-divider';\r\n"
        b"  var bqSeg = document.createElement('span');\r\n"
        b"  bqSeg.className = 'cat-col-seg cat-bq-seg' + (checked?' active':'');\r\n"
        b"  bqSeg.textContent = '\xe5\xbc\x95\xe7\x94\xa8'; bqSeg.onclick = function(){toggleCatBQ(this);};\r\n"
        b'  pill.appendChild(s0); pill.appendChild(s1); pill.appendChild(div); pill.appendChild(bqSeg);\r\n'
        b"  sel.style.display = 'none'; pill.appendChild(sel);\r\n"
        b"  cb.style.display = 'none'; pill.appendChild(cb);\r\n"
        b'  if (sel.parentNode) sel.parentNode.insertBefore(pill, sel);\r\n'
        b'}\r\n'
    )
    c = c[:tg_end] + new_funcs + c[tg_end:]
    changes += 1
    print('5. New JS functions inserted')

# ============================================================
# 6. Update toggleBQControls
# ============================================================
old_tg = (
    b"function toggleBQControls(cb) {\r\n"
    b"  var card = cb.closest('.sr-cat-card');\r\n"
    b'  if (!card) return;\r\n'
    b"  var show = cb.checked ? 'visible' : 'hidden';\r\n"
)
new_tg = (
    b"function toggleBQControls(cb) {\r\n"
    b"  var card = cb.closest('.sr-cat-card');\r\n"
    b'  if (!card) return;\r\n'
    b"  var bqSeg = cb.closest('.cat-col-bq');\r\n"
    b"  if (bqSeg) { var span = bqSeg.querySelector('.cat-bq-seg'); if (span) span.classList.toggle('active', cb.checked); }\r\n"
    b"  var show = cb.checked ? 'visible' : 'hidden';\r\n"
)
if old_tg in c:
    c = c.replace(old_tg, new_tg)
    changes += 1
    print('6. toggleBQControls updated')
else:
    print('6. toggleBQControls NOT FOUND')

# ============================================================
# 7. Update initBQControls
# ============================================================
old_init = b"document.querySelectorAll('.sr-cat-card').forEach(function(card){ reorderCatCard(card); mergeLabelInputs(card); });"
new_init = b"document.querySelectorAll('.sr-cat-card').forEach(function(card){ buildCatColBQPill(card); });\r\n  document.querySelectorAll('.sr-cat-card').forEach(function(card){ reorderCatCard(card); mergeLabelInputs(card); });"
if old_init in c:
    c = c.replace(old_init, new_init)
    changes += 1
    print('7. initBQControls updated')
else:
    print('7. initBQControls NOT FOUND')

with open(r'B:\项目\Hass ASA Server Monitor\www\asa-admin.html', 'wb') as f:
    f.write(c)
print(f'\nTotal changes: {changes}')
sys.exit(0)
