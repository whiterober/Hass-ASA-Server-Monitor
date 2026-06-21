"""Add markerColor floating popup to Pill"""
D = b'"'
BS = b'\\'
EQ = BS + D  # \"

with open(r'B:\项目\Hass ASA Server Monitor\www\asa-admin.html', 'rb') as f:
    c = f.read()

changes = 0

# ============================================================
# 1. Add CSS for color dot + popup
# ============================================================
css_marker = b'.cat-col-bq .cat-bq-seg.active'
pos = c.find(css_marker)
# Find end of the cat-col-bq CSS block
end_css = c.find(b'\r\n.sr-cat-card > .sr-items', pos)

new_css = (
    b'.cat-color-dot { width:8px;height:8px;border-radius:50%;flex-shrink:0;cursor:pointer;margin-right:1px; }\r\n'
    b'.cat-color-popup { display:none;position:fixed;background:var(--card);border:1px solid var(--border);border-radius:6px;padding:4px 6px;z-index:99999;box-shadow:0 4px 16px rgba(0,0,0,0.45);gap:4px;align-items:center; }\r\n'
    b'.cat-color-popup.show { display:flex; }\r\n'
    b'.cat-color-opt { width:16px;height:16px;border-radius:50%;cursor:pointer;flex-shrink:0;border:2px solid transparent;transition:border-color .15s; }\r\n'
    b'.cat-color-opt:hover { border-color:var(--text); }\r\n'
    b'.cat-color-opt.active { border-color:var(--accent);box-shadow:0 0 0 1px var(--accent); }\r\n'
)
c = c[:pos] + new_css + c[pos:]
changes += 1
print('1. CSS added')

# ============================================================
# 2. Add JS functions
# ============================================================
rm_pos = c.find(b'function rmSrRow(el)')
if rm_pos > 0:
    js = (
        b'var CAT_COLORS = [\"#ccc\",\"#ff9800\",\"#4caf50\",\"#f44336\",\"#2196f3\"];\r\n'
        b'function toggleColorPopup(el) {\r\n'
        b'  var pill = el.closest(\".cat-col-bq\");\r\n'
        b'  if (!pill) return;\r\n'
        b'  var sel = pill.querySelector(\"select[id^=brCatMarkerColor]\");\r\n'
        b'  var cur = sel ? sel.value : \"#ccc\";\r\n'
        b'  // Close existing popup\r\n'
        b'  var existing = document.querySelector(\".cat-color-popup.show\");\r\n'
        b'  if (existing) { existing.classList.remove(\"show\"); if (existing.dataset.dotId === el.id) return; }\r\n'
        b'  // Build popup\r\n'
        b'  var popup = document.getElementById(\"catColorPopup\");\r\n'
        b'  if (!popup) {\r\n'
        b'    popup = document.createElement(\"span\");\r\n'
        b'    popup.id = \"catColorPopup\";\r\n'
        b'    popup.className = \"cat-color-popup\";\r\n'
        b'    document.body.appendChild(popup);\r\n'
        b'  }\r\n'
        b'  popup.innerHTML = \"\";\r\n'
        b'  CAT_COLORS.forEach(function(clr){\r\n'
        b'    var opt = document.createElement(\"span\");\r\n'
        b'    opt.className = \"cat-color-opt\" + (clr === cur ? \" active\" : \"\");\r\n'
        b'    opt.style.background = clr;\r\n'
        b'    opt.onclick = function(e){ e.stopPropagation(); selectMarkerColor(el, clr); };\r\n'
        b'    popup.appendChild(opt);\r\n'
        b'  });\r\n'
        b'  var r = el.getBoundingClientRect();\r\n'
        b'  popup.style.left = r.left + \"px\";\r\n'
        b'  popup.style.top = (r.bottom + 4) + \"px\";\r\n'
        b'  popup.dataset.dotId = el.id;\r\n'
        b'  popup.classList.add(\"show\");\r\n'
        b'}\r\n'
        b'function selectMarkerColor(dot, clr) {\r\n'
        b'  dot.style.background = clr;\r\n'
        b'  var pill = dot.closest(\".cat-col-bq\");\r\n'
        b'  if (!pill) return;\r\n'
        b'  var sel = pill.querySelector(\"select[id^=brCatMarkerColor]\");\r\n'
        b'  if (sel) sel.value = clr;\r\n'
        b'  // Close popup\r\n'
        b'  var popup = document.getElementById(\"catColorPopup\");\r\n'
        b'  if (popup) popup.classList.remove(\"show\");\r\n'
        b'}\r\n'
    )
    c = c[:rm_pos] + js + c[rm_pos:]
    changes += 1
    print('2. JS functions added')

# ============================================================
# 3. Global click-outside for color popup
# ============================================================
closer_marker = b"if (!document.body.dataset.popupCloser) {\"
closer_pos = c.find(closer_marker)
if closer_pos > 0:
    # Find the end of the existing popup closer block (the close-brace and line)
    old_closer = b"    document.addEventListener('click', function(e){\\r\\n      if (!e.target.closest('.cat-input-wrap')) {\\r\\n        document.querySelectorAll('.cat-bc-popup.show').forEach(function(p){ p.classList.remove('show'); });\\r\\n      }\\r\\n    });\\r\\n  }\"
    new_closer = b"    document.addEventListener('click', function(e){\\r\\n      if (!e.target.closest('.cat-input-wrap')) {\\r\\n        document.querySelectorAll('.cat-bc-popup.show').forEach(function(p){ p.classList.remove('show'); });\\r\\n      }\\r\\n      if (!e.target.closest('.cat-color-dot') && !e.target.closest('.cat-color-popup')) {\\r\\n        var p = document.getElementById('catColorPopup');\\r\\n        if (p) p.classList.remove('show');\\r\\n      }\\r\\n    });\\r\\n  }\"
    if old_closer in c:
        c = c.replace(old_closer, new_closer)
        changes += 1
        print('3. Click-outside updated for color popup')
    else:
        print('3. old_closer NOT FOUND')
else:
    print('3. popupCloser NOT FOUND')

# ============================================================
# 4. Update render template pill: add color dot before 引用
# ============================================================
# Find the pill template in render (with cat-column===0)
# Pattern: ...toggleCatBQ(this)\">引用</span>
old_ref = b"toggleCatBQ(this)\\\">\xe5\xbc\x95\xe7\x94\xa8</span>'\"
new_ref = (
    b"toggleCatBQ(this)\\\">';\r\n"
    b"                html += '<span class=\\\"cat-color-dot\\\" id=\\\"brCatCDot'+si+'_'+bi+'_'+ri+'_'+ci+'\\\" style=\\\"background:'+ (cat.marker_color||'#ccc') +'\\\" onclick=\\\"toggleColorPopup(this)\\\"></span>';\r\n"
    b"                html += '<span class=\\\"cat-col-seg cat-bq-seg'+(cat.use_blockquote!==false?' active':'')+'\\\" onclick=\\\"toggleCatBQ(this)\\\">\xe5\xbc\x95\xe7\x94\xa8</span>';\r\n"
)
# Actually this is complex. Let me use position-based replacement.
# Find the 引用 span in render template (first occurrence before addStorageCat)
ac_func = c.find(b'function addStorageCat')
ref_pos = c.find(b'\xe5\xbc\x95\xe7\x94\xa8</span>', 0, ac_func)
if ref_pos > 0:
    # Go back to find start of this html += line
    ls = c.rfind(b"html += '\", 0, ref_pos)
    le = c.find(b"';\", ref_pos) + 2
    old_line = c[ls:le]
    # Build new lines: color dot line + modified 引用 line
    new_lines = (
        b"html += '<span class=\\\"cat-color-dot\\\" id=\\\"brCatCDot'+si+'_'+bi+'_'+ri+'_'+ci+'\\\" style=\\\"background:'+ (cat.marker_color||'#ccc') +'\\\" onclick=\\\"toggleColorPopup(this)\\\"></span>';\r\n"
        b"                \" + old_line  # keep the original 引用 line
    )
    c = c[:ls] + new_lines + c[le:]
    changes += 1
    print('4. Render template: color dot added')
else:
    print('4. Render 引用 NOT FOUND')

# ============================================================
# 5. Update addStorageCat pill: add color dot
# ============================================================
ref_pos2 = c.find(b'\xe5\xbc\x95\xe7\x94\xa8</span>', ac_func)
if ref_pos2 > 0:
    ls2 = c.rfind(b"h += '\", 0, ref_pos2)
    le2 = c.find(b"';\", ref_pos2) + 2
    old_line2 = c[ls2:le2]
    new_lines2 = (
        b"h += '<span class=\\\"cat-color-dot\\\" id=\\\"brCatCDot'+si+'_'+bi+'_'+ri+'_'+ci+'\\\" style=\\\"background:#ccc\\\" onclick=\\\"toggleColorPopup(this)\\\"></span>';\r\n"
        b"  \" + old_line2
    )
    c = c[:ls2] + new_lines2 + c[le2:]
    changes += 1
    print('5. addStorageCat: color dot added')
else:
    print('5. AC 引用 NOT FOUND')

# ============================================================
# 6. Update buildCatColBQPill: add color dot
# ============================================================
old_pill = b"var bqSeg = document.createElement('span');\r\n  bqSeg.className = 'cat-col-seg cat-bq-seg' + (checked?' active':'');\r\n  bqSeg.textContent = '\xe5\xbc\x95\xe7\x94\xa8'; bqSeg.onclick = function(){toggleCatBQ(this);};\"
new_pill = (
    b"var dot = document.createElement('span');\r\n"
    b"  dot.className = 'cat-color-dot'; dot.id = sel.id.replace('brCatCol','brCatCDot');\r\n"
    b"  dot.style.background = sel.value || '#ccc'; dot.onclick = function(e){ e.stopPropagation(); toggleColorPopup(this); };\r\n"
    b"  var bqSeg = document.createElement('span');\r\n"
    b"  bqSeg.className = 'cat-col-seg cat-bq-seg' + (checked?' active':'');\r\n"
    b"  bqSeg.textContent = '\xe5\xbc\x95\xe7\x94\xa8'; bqSeg.onclick = function(){toggleCatBQ(this);};\r\n"
)
if old_pill in c:
    c = c.replace(old_pill, new_pill)
    changes += 1
    print('6. buildCatColBQPill: color dot added')
else:
    print('6. buildCatColBQPill NOT FOUND')

# ============================================================
# 7. Update buildCatColBQPill: include dot in append order
# ============================================================
old_append = b'pill.appendChild(s0); pill.appendChild(s1); pill.appendChild(div); pill.appendChild(bqSeg);'
new_append = b'pill.appendChild(s0); pill.appendChild(s1); pill.appendChild(div); pill.appendChild(dot); pill.appendChild(bqSeg);'
if old_append in c:
    c = c.replace(old_append, new_append)
    changes += 1
    print('7. buildCatColBQPill: dot appended')
else:
    print('7. append NOT FOUND')

# ============================================================
# 8. Hide brCatMarkerColor in render template + add to pill
# ============================================================
# The render template has a separate brCatMarkerColor select line.
# We need to: change its style to display:none, and move it INSIDE the pill closing tag
# Actually easier: just hide it and leave it where it is. saveBaseTab queries by id^= prefix so it'll find it anywhere.
# But it's cleaner to put it in the pill. Let me just hide it for now.

# Find brCatMarkerColor select in render template
mc_render = c.find(b"html += '<select id=\\\"brCatMarkerColor\", 0, ac_func)
if mc_render > 0:
    # Change style to display:none
    old_mc_style = b"style=\\\"width:44px;padding:1px;font-size:0.6em;margin:0\\\"\"
    new_mc_style = b"style=\\\"display:none\\\"\"
    before = c[:mc_render]
    after = c[mc_render:]
    if old_mc_style in after:
        after = after.replace(old_mc_style, new_mc_style, 1)
        c = before + after
        changes += 1
        print('8. Render markerColor hidden')
    else:
        print('8. Render mc style NOT FOUND')
else:
    print('8. Render mc NOT FOUND')

# ============================================================
# 9. Hide brCatMarkerColor in addStorageCat
# ============================================================
mc_ac = c.find(b"h += '<select id=\\\"brCatMarkerColor\", ac_func)
if mc_ac > 0:
    before = c[:mc_ac]
    after = c[mc_ac:]
    old_mc_style2 = b"style=\\\"width:44px;padding:1px;font-size:0.6em;margin:0\\\"\"
    if old_mc_style2 in after:
        after = after.replace(old_mc_style2, new_mc_style, 1)
        c = before + after
        changes += 1
        print('9. AC markerColor hidden')
    else:
        print('9. AC mc style NOT FOUND')
else:
    print('9. AC mc NOT FOUND')

# ============================================================
# 10. Remove brCatMarkerColor from reorderCatCard order
# ============================================================
old_order = b'[\"brCatColBQ\",\"brCatMarkerColor\",\"brCatLabel\"'
new_order = b'[\"brCatColBQ\",\"brCatLabel\"'
if old_order in c:
    c = c.replace(old_order, new_order)
    changes += 1
    print('10. reorderCatCard: markerColor removed')
else:
    print('10. Order NOT FOUND')

# ============================================================
# 11. Also hide markerColor in buildCatColBQPill (it moves the select)
# ============================================================
# buildCatColBQPill moves the old brCatMarkerColor select? No, it only handles brCatCol and brCatBQ.
# The markerColor select stays where it is but is now hidden by inline style.

with open(r'B:\项目\Hass ASA Server Monitor\www\asa-admin.html', 'wb') as f:
    f.write(c)

print(f'\nTotal changes: {changes}')
