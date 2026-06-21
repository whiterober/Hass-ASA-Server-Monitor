import sys
# All strings using b'...' to avoid quote escaping
D = bytes([34])  # double quote
N = bytes([13, 10])  # CRLF

with open(r'B:\项目\Hass ASA Server Monitor\www\asa-admin.html', 'rb') as f:
    c = f.read()

changes = 0

# ========== 1. CSS ==========
css_pos = c.find(b'.cat-col-bq .cat-bq-seg.active')
css = N.join([
    b'.cat-color-dot { width:8px;height:8px;border-radius:50%;flex-shrink:0;cursor:pointer;margin-right:1px; }',
    b'.cat-color-popup { display:none;position:fixed;background:var(--card);border:1px solid var(--border);border-radius:6px;padding:4px 6px;z-index:99999;box-shadow:0 4px 16px rgba(0,0,0,0.45);gap:4px;align-items:center; }',
    b'.cat-color-popup.show { display:flex; }',
    b'.cat-color-opt { width:16px;height:16px;border-radius:50%;cursor:pointer;flex-shrink:0;border:2px solid transparent;transition:border-color .15s; }',
    b'.cat-color-opt:hover { border-color:var(--text); }',
    b'.cat-color-opt.active { border-color:var(--accent);box-shadow:0 0 0 1px var(--accent); }',
    b''
]) + N
c = c[:css_pos] + css + c[css_pos:]
print('1. CSS')

# ========== 2. JS functions ==========
rm_pos = c.find(b'function rmSrRow(el)')
js_parts = []
def L(s):
    js_parts.append(s + N)
L(b'var CAT_COLORS = [' + D + b'#ccc' + D + b',' + D + b'#ff9800' + D + b',' + D + b'#4caf50' + D + b',' + D + b'#f44336' + D + b',' + D + b'#2196f3' + D + b'];')
L(b'function toggleColorPopup(el) {')
L(b'  var pill = el.closest(' + D + b'.cat-col-bq' + D + b');')
L(b'  if (!pill) return;')
L(b'  var sel = pill.querySelector(' + D + b'select[id^=brCatMarkerColor]' + D + b');')
L(b'  var cur = sel ? sel.value : ' + D + b'#ccc' + D + b';')
L(b'  var existing = document.querySelector(' + D + b'.cat-color-popup.show' + D + b');')
L(b'  if (existing) { existing.classList.remove(' + D + b'show' + D + b'); if (existing.dataset.dotId === el.id) return; }')
L(b'  var popup = document.getElementById(' + D + b'catColorPopup' + D + b');')
L(b'  if (!popup) { popup = document.createElement(' + D + b'span' + D + b'); popup.id = ' + D + b'catColorPopup' + D + b'; popup.className = ' + D + b'cat-color-popup' + D + b'; document.body.appendChild(popup); }')
L(b'  popup.innerHTML = ' + D + D + b';')
L(b'  CAT_COLORS.forEach(function(clr){')
L(b'    var opt = document.createElement(' + D + b'span' + D + b');')
L(b'    opt.className = ' + D + b'cat-color-opt' + D + b' + (clr === cur ? ' + D + b' active' + D + b' : ' + D + D + b');')
L(b'    opt.style.background = clr;')
L(b'    opt.onclick = function(e){ e.stopPropagation(); selectMarkerColor(el, clr); };')
L(b'    popup.appendChild(opt);')
L(b'  });')
L(b'  var r = el.getBoundingClientRect();')
L(b'  popup.style.left = r.left + ' + D + b'px' + D + b';')
L(b'  popup.style.top = (r.bottom + 4) + ' + D + b'px' + D + b';')
L(b'  popup.dataset.dotId = el.id;')
L(b'  popup.classList.add(' + D + b'show' + D + b');')
L(b'}')
L(b'function selectMarkerColor(dot, clr) {')
L(b'  dot.style.background = clr;')
L(b'  var pill = dot.closest(' + D + b'.cat-col-bq' + D + b');')
L(b'  if (!pill) return;')
L(b'  var sel = pill.querySelector(' + D + b'select[id^=brCatMarkerColor]' + D + b');')
L(b'  if (sel) sel.value = clr;')
L(b'  var popup = document.getElementById(' + D + b'catColorPopup' + D + b');')
L(b'  if (popup) popup.classList.remove(' + D + b'show' + D + b');')
L(b'}')
js = b''.join(js_parts)
c = c[:rm_pos] + js + c[rm_pos:]
print('2. JS')

# ========== 3. Click-outside closer ==========
old_cl = b"    document.addEventListener('click', function(e){\r\n      if (!e.target.closest('.cat-input-wrap')) {\r\n        document.querySelectorAll('.cat-bc-popup.show').forEach(function(p){ p.classList.remove('show'); });\r\n      }\r\n    });\r\n  }"
new_cl = (
    b"    document.addEventListener('click', function(e){" + N +
    b"      if (!e.target.closest('.cat-input-wrap')) {" + N +
    b"        document.querySelectorAll('.cat-bc-popup.show').forEach(function(p){ p.classList.remove('show'); });" + N +
    b"      }" + N +
    b"      if (!e.target.closest('.cat-color-dot') && !e.target.closest('.cat-color-popup')) {" + N +
    b"        var cp = document.getElementById('catColorPopup');" + N +
    b"        if (cp) cp.classList.remove('show');" + N +
    b"      }" + N +
    b"    });" + N +
    b"  }"
)
if old_cl in c:
    c = c.replace(old_cl, new_cl)
    print('3. Closer')
    changes += 1

# ========== 4+5. Render + AC templates: color dot ==========
ac_func = c.find(b'function addStorageCat')
# Render template
ref1 = c.find(b'\xe5\xbc\x95\xe7\x94\xa8</span>', 0, ac_func)
if ref1 > 0:
    ls = c.rfind(b"html += '", 0, ref1)
    le = c.find(b"';", ref1) + 2
    old_line = c[ls:le]
    new_dot = (
        b"html += '<span class=" + D + b"cat-color-dot" + D + b" id=" + D + b"brCatCDot'+si+'_'+bi+'_'+ri+'_'+ci+" + D + b" style=" + D + b"background:'+ (cat.marker_color||'#ccc') +'" + D + b" onclick=" + D + b"toggleColorPopup(this)" + D + b"></span>';" + N +
        b"                " + old_line
    )
    c = c[:ls] + new_dot + c[le:]
    print('4. Render dot')
    changes += 1
# AddStorageCat
ref2 = c.find(b'\xe5\xbc\x95\xe7\x94\xa8</span>', ac_func)
if ref2 > 0:
    ls2 = c.rfind(b"h += '", 0, ref2)
    le2 = c.find(b"';", ref2) + 2
    old_line2 = c[ls2:le2]
    new_dot2 = (
        b"h += '<span class=" + D + b"cat-color-dot" + D + b" id=" + D + b"brCatCDot'+si+'_'+bi+'_'+ri+'_'+ci+" + D + b" style=" + D + b"background:#ccc" + D + b" onclick=" + D + b"toggleColorPopup(this)" + D + b"></span>';" + N +
        b"  " + old_line2
    )
    c = c[:ls2] + new_dot2 + c[le2:]
    print('5. AC dot')
    changes += 1

# ========== 6+7. buildCatColBQPill ==========
old_pill = b"var bqSeg = document.createElement('span');\r\n  bqSeg.className = 'cat-col-seg cat-bq-seg' + (checked?' active':'');\r\n  bqSeg.textContent = '\xe5\xbc\x95\xe7\x94\xa8'; bqSeg.onclick = function(){toggleCatBQ(this);};"
new_pill = (
    b"var dot = document.createElement('span');" + N +
    b"  dot.className = 'cat-color-dot'; dot.id = sel.id.replace('brCatCol','brCatCDot');" + N +
    b"  dot.style.background = '#ccc'; dot.onclick = function(e){ e.stopPropagation(); toggleColorPopup(this); };" + N +
    b"  var bqSeg = document.createElement('span');" + N +
    b"  bqSeg.className = 'cat-col-seg cat-bq-seg' + (checked?' active':'');" + N +
    b"  bqSeg.textContent = '\xe5\xbc\x95\xe7\x94\xa8'; bqSeg.onclick = function(){toggleCatBQ(this);};" + N
)
if old_pill in c:
    c = c.replace(old_pill, new_pill)
    print('6. buildPill dot')
    changes += 1
# Append order
old_app = b'pill.appendChild(s0); pill.appendChild(s1); pill.appendChild(div); pill.appendChild(bqSeg);'
new_app = b'pill.appendChild(s0); pill.appendChild(s1); pill.appendChild(div); pill.appendChild(dot); pill.appendChild(bqSeg);'
if old_app in c:
    c = c.replace(old_app, new_app)
    print('7. append dot')
    changes += 1

# ========== 8+9. Hide markerColor selects ==========
mc1 = c.find(b"html += '<select id=" + D + b"brCatMarkerColor", 0, ac_func)
if mc1 > 0:
    old_st = b"style=" + D + b"width:44px;padding:1px;font-size:0.6em;margin:0" + D
    new_st = b"style=" + D + b"display:none" + D
    before = c[:mc1]; after = c[mc1:]
    if old_st in after:
        after = after.replace(old_st, new_st, 1)
        c = before + after
        print('8. Render mc hidden')
        changes += 1
mc2 = c.find(b"h += '<select id=" + D + b"brCatMarkerColor", ac_func)
if mc2 > 0:
    before = c[:mc2]; after = c[mc2:]
    if old_st in after:
        after = after.replace(old_st, new_st, 1)
        c = before + after
        print('9. AC mc hidden')
        changes += 1

# ========== 10. Remove markerColor from order ==========
old_ord = b'["brCatColBQ","brCatMarkerColor","brCatLabel"'
new_ord = b'["brCatColBQ","brCatLabel"'
if old_ord in c:
    c = c.replace(old_ord, new_ord)
    print('10. Order')
    changes += 1

# Verify
print('Braces:', c.count(b'{'), c.count(b'}'))
print('cat-color-dot:', c.count(b'cat-color-dot'))
print('toggleColorPopup:', c.count(b'toggleColorPopup'))

with open(r'B:\项目\Hass ASA Server Monitor\www\asa-admin.html', 'wb') as f:
    f.write(c)
print('Total changes:', changes)
