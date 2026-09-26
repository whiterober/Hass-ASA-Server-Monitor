"""Implement unified Pill control for column + BQ"""
with open(r'B:\项目\Hass ASA Server Monitor\www\asa-admin.html', 'rb') as f:
    c = f.read()

changes = 0

# ============================================================
# 1. Add CSS before .sr-cat-card > .sr-items
# ============================================================
css_insert_marker = b'.sr-cat-card > .sr-items { flex: 1 1 100%; min-width: 100%; }'
pos = c.find(css_insert_marker)
if pos > 0:
    new_css = b'''.cat-col-bq { display:inline-flex;align-items:center;border:1px solid var(--border);border-radius:6px;overflow:hidden;height:24px;font-size:0.65em;flex-shrink:0;user-select:none;background:var(--input-bg,transparent); }
.cat-col-bq .cat-col-seg { padding:1px 6px;cursor:pointer;color:var(--text);opacity:.45;white-space:nowrap;line-height:22px;transition:opacity .15s,background .15s,color .15s; }
.cat-col-bq .cat-col-seg:hover { opacity:.75; }
.cat-col-bq .cat-col-seg.active { opacity:1;background:var(--accent);color:#000;font-weight:bold; }
.cat-col-bq .cat-col-divider { width:1px;height:16px;background:var(--border);flex-shrink:0;align-self:center; }
.cat-col-bq .cat-col-seg.cat-bq-seg { padding:1px 8px; }
.cat-col-bq .cat-bq-seg.active { opacity:1;color:var(--accent);font-weight:bold;background:transparent; }
'''
    c = c[:pos] + new_css + c[pos:]
    changes += 1
    print('1. CSS added')
else:
    print('1. CSS marker NOT FOUND')

# ============================================================
# 2. Replace render template brCatCol + brCatBQ with pill
# ============================================================
# Find the brCatCol line in render template (offset 316487)
idx = c.find(b\"html += '<select id=\\\"brCatCol'+si+'_'+bi+'_'+ri+'_'+ci+'\\\" style=\\\"width:38px;padding:1px;font-size:0.65em;margin:0\\\"><option value=\\\"0\\\"'+(cat.column===0?' selected':'')+'>\")
if idx > 0:
    # Find end of this line
    line_end = c.find(b\"';\", idx + 150) + 2  # past ';
    # Find start of brCatBQ line
    bq_start = c.find(b\"html += '<label style=\\\"font-size:0.6em;margin:0;display:flex;align-items:center;gap:1px;white-space:nowrap\\\"><input type=\\\"checkbox\\\" id=\\\"brCatBQ'+si+'_'+bi+'_'+ri+'_'+ci+'\\\" \", idx)
    if bq_start > 0:
        bq_end = c.find(b\"';\", bq_start + 150) + 2  # past ';
        # Build replacement pill HTML
        pill = b\"\"\"html += '<span class=\\\"cat-col-bq\\\" id=\\\"brCatColBQ'+si+'_'+bi+'_'+ri+'_'+ci+'\\\">';
html += '<span class=\\\"cat-col-seg'+(cat.column===0?' active':'')+'\\\" data-col=\\\"0\\\" onclick=\\\"setCatCol(this,0)\\\">\xe5\x88\x971</span>';
html += '<span class=\\\"cat-col-seg'+(cat.column===1?' active':'')+'\\\" data-col=\\\"1\\\" onclick=\\\"setCatCol(this,1)\\\">\xe5\x88\x972</span>';
html += '<span class=\\\"cat-col-divider\\\"></span>';
html += '<span class=\\\"cat-col-seg cat-bq-seg'+(cat.use_blockquote!==false?' active':'')+'\\\" onclick=\\\"toggleCatBQ(this)\\\">\xe5\xbc\x95\xe7\x94\xa8</span>';
html += '<input type=\\\"checkbox\\\" id=\\\"brCatBQ'+si+'_'+bi+'_'+ri+'_'+ci+'\\\" '+(cat.use_blockquote!==false?'checked':'')+' onchange=\\\"toggleBQControls(this)\\\" style=\\\"display:none\\\">';
html += '<select id=\\\"brCatCol'+si+'_'+bi+'_'+ri+'_'+ci+'\\\" style=\\\"display:none\\\"><option value=\\\"0\\\"'+(cat.column===0?' selected':'')+'>\xe5\x88\x971</option><option value=\\\"1\\\"'+(cat.column===1?' selected':'')+'>\xe5\x88\x972</option></select>';
html += '</span>';
\"\"\"
        c = c[:idx] + pill + c[bq_end:]
        changes += 1
        print('2. Render template pill replaced')
    else:
        print('2. brCatBQ NOT FOUND in render')
else:
    print('2. brCatCol NOT FOUND in render')

# ============================================================
# 3. Replace addStorageCat brCatCol + brCatBQ with pill
# ============================================================
ac_pos = c.find(b'function addStorageCat')
# Find brCatCol in addStorageCat
idx3 = c.find(b\"h += '<select id=\\\"brCatCol'+si+'_'+bi+'_'+ri+'_'+ci+'\\\" style=\\\"width:38px;padding:1px;font-size:0.65em;margin:0\\\"><option value=\\\"0\\\">\", ac_pos)
if idx3 > 0:
    line_end3 = c.find(b\"';\", idx3 + 150) + 2
    # Find brCatBQ after this
    bq_start3 = c.find(b\"h += '<label style=\\\"font-size:0.6em;margin:0;display:flex;align-items:center;gap:1px;white-space:nowrap\\\"><input type=\\\"checkbox\\\" id=\\\"brCatBQ'+si+'_'+bi+'_'+ri+'_'+ci+'\\\" checked\", idx3)
    if bq_start3 > 0:
        bq_end3 = c.find(b\"';\", bq_start3 + 150) + 2
        pill3 = b\"\"\"h += '<span class=\\\"cat-col-bq\\\" id=\\\"brCatColBQ'+si+'_'+bi+'_'+ri+'_'+ci+'\\\">';
h += '<span class=\\\"cat-col-seg active\\\" data-col=\\\"0\\\" onclick=\\\"setCatCol(this,0)\\\">\xe5\x88\x971</span>';
h += '<span class=\\\"cat-col-seg\\\" data-col=\\\"1\\\" onclick=\\\"setCatCol(this,1)\\\">\xe5\x88\x972</span>';
h += '<span class=\\\"cat-col-divider\\\"></span>';
h += '<span class=\\\"cat-col-seg cat-bq-seg active\\\" onclick=\\\"toggleCatBQ(this)\\\">\xe5\xbc\x95\xe7\x94\xa8</span>';
h += '<input type=\\\"checkbox\\\" id=\\\"brCatBQ'+si+'_'+bi+'_'+ri+'_'+ci+'\\\" checked onchange=\\\"toggleBQControls(this)\\\" style=\\\"display:none\\\">';
h += '<select id=\\\"brCatCol'+si+'_'+bi+'_'+ri+'_'+ci+'\\\" style=\\\"display:none\\\"><option value=\\\"0\\\" selected>\xe5\x88\x971</option><option value=\\\"1\\\">\xe5\x88\x972</option></select>';
h += '</span>';
\"\"\"
        c = c[:idx3] + pill3 + c[bq_end3:]
        changes += 1
        print('3. addStorageCat pill replaced')
    else:
        print('3. brCatBQ NOT FOUND in addStorageCat')
else:
    print('3. brCatCol NOT FOUND in addStorageCat')

# ============================================================
# 4. Update reorderCatCard order array
# ============================================================
old_order = b'[\"brCatCol\",\"brCatBQ\",\"brCatMarkerColor\"'
new_order = b'[\"brCatColBQ\",\"brCatMarkerColor\"'
if old_order in c:
    c = c.replace(old_order, new_order)
    changes += 1
    print('4. reorderCatCard order updated')
else:
    print('4. Order NOT FOUND')

# ============================================================
# 5. Add new JS functions + update toggleBQControls
# ============================================================
# Find toggleBQControls function end (before 'function rmSrRow')
tg_end = c.find(b'function rmSrRow(el)')
if tg_end > 0:
    # Insert new functions + updated toggleBQControls before rmSrRow
    new_funcs = b'''function setCatCol(el, col) {
  var pill = el.closest('.cat-col-bq');
  if (!pill) return;
  pill.querySelectorAll('.cat-col-seg:not(.cat-bq-seg)').forEach(function(s){
    s.classList.toggle('active', parseInt(s.dataset.col) === col);
  });
  var sel = pill.querySelector('select[id^=brCatCol]');
  if (sel) sel.value = col;
}
function toggleCatBQ(el) {
  var pill = el.closest('.cat-col-bq');
  if (!pill) return;
  var cb = pill.querySelector('input[type=checkbox][id^=brCatBQ]');
  if (!cb) return;
  cb.checked = !cb.checked;
  el.classList.toggle('active', cb.checked);
  if (typeof toggleBQControls === 'function') toggleBQControls(cb);
}
function buildCatColBQPill(card) {
  if (card.querySelector('.cat-col-bq')) return;
  var sel = card.querySelector('select[id^=brCatCol]');
  var cb = card.querySelector('input[type=checkbox][id^=brCatBQ]');
  if (!sel || !cb) return;
  var col = parseInt(sel.value)||0;
  var checked = cb.checked;
  var pill = document.createElement('span');
  pill.className = 'cat-col-bq';
  pill.id = sel.id.replace('brCatCol','brCatColBQ');
  var s0 = document.createElement('span');
  s0.className = 'cat-col-seg' + (col===0?' active':'');
  s0.dataset.col = '0'; s0.textContent = '列1'; s0.onclick = function(){setCatCol(this,0);};
  var s1 = document.createElement('span');
  s1.className = 'cat-col-seg' + (col===1?' active':'');
  s1.dataset.col = '1'; s1.textContent = '列2'; s1.onclick = function(){setCatCol(this,1);};
  var div = document.createElement('span');
  div.className = 'cat-col-divider';
  var bqSeg = document.createElement('span');
  bqSeg.className = 'cat-col-seg cat-bq-seg' + (checked?' active':'');
  bqSeg.textContent = '引用'; bqSeg.onclick = function(){toggleCatBQ(this);};
  pill.appendChild(s0); pill.appendChild(s1); pill.appendChild(div); pill.appendChild(bqSeg);
  sel.style.display = 'none'; pill.appendChild(sel);
  cb.style.display = 'none'; pill.appendChild(cb);
  if (sel.parentNode) sel.parentNode.insertBefore(pill, sel);
}
'''
    c = c[:tg_end] + new_funcs + c[tg_end:]
    changes += 1
    print('5. New JS functions inserted')
else:
    print('5. rmSrRow NOT FOUND')

# ============================================================
# 6. Update toggleBQControls to sync pill .active class
# ============================================================
old_tg = b\"function toggleBQControls(cb) {\n  var card = cb.closest('.sr-cat-card');\n  if (!card) return;\n  var show = cb.checked ? 'visible' : 'hidden';\"
new_tg = b\"function toggleBQControls(cb) {\n  var card = cb.closest('.sr-cat-card');\n  if (!card) return;\n  var bqSeg = cb.closest('.cat-col-bq')?.querySelector('.cat-bq-seg');\n  if (bqSeg) bqSeg.classList.toggle('active', cb.checked);\n  var show = cb.checked ? 'visible' : 'hidden';\"
if old_tg in c:
    c = c.replace(old_tg, new_tg)
    changes += 1
    print('6. toggleBQControls updated')
else:
    print('6. toggleBQControls NOT FOUND')

# ============================================================
# 7. Update initBQControls to build pills first
# ============================================================
old_init = b\"document.querySelectorAll('.sr-cat-card').forEach(function(card){ reorderCatCard(card); mergeLabelInputs(card); });\"
new_init = b\"document.querySelectorAll('.sr-cat-card').forEach(function(card){ buildCatColBQPill(card); });\n  document.querySelectorAll('.sr-cat-card').forEach(function(card){ reorderCatCard(card); mergeLabelInputs(card); });\"
if old_init in c:
    c = c.replace(old_init, new_init)
    changes += 1
    print('7. initBQControls updated')
else:
    print('7. initBQControls NOT FOUND')

with open(r'B:\项目\Hass ASA Server Monitor\www\asa-admin.html', 'wb') as f:
    f.write(c)
print(f'\nTotal changes: {changes}')
