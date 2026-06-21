"""Fix: 1. active highlight in popup, 2. B bold next to dot"""
D = bytes([34])
N = bytes([13, 10])
path = r'B:\项目\Hass ASA Server Monitor\www\asa-admin.html'

with open(path, 'rb') as f:
    c = f.read()
org = len(c)

# === 1. Fix active highlight: handle type=color input values ===
# The issue: type=color .value may return different format.
# Fix: in toggleColorPopup, normalize the comparison
old1 = b"    opt.className = " + D + b"cat-color-opt" + D + b" + (clr === cur ? " + D + b" active" + D + b" : " + D + D + b");"
new1 = b"    var isActive = clr.toLowerCase() === cur.toLowerCase();\r\n    opt.className = " + D + b"cat-color-opt" + D + b" + (isActive ? " + D + b" active" + D + b" : " + D + D + b");"
c = c.replace(old1, new1)
print('1. Case-insensitive comparison')

# === 2. Add .cat-bold-btn CSS ===
css_pos = c.find(b'.cat-color-dot {')
new_css = b'.cat-bold-btn { font-size:0.55em;font-weight:bold;cursor:pointer;color:var(--text);opacity:.4;user-select:none;margin-left:1px;line-height:1;transition:opacity .15s,color .15s; }\r\n.cat-bold-btn:hover { opacity:.7; }\r\n.cat-bold-btn.active { opacity:1;color:var(--accent); }\r\n'
c = c[:css_pos] + new_css + c[css_pos:]
print('2. B button CSS')

# === 3. mergeLabelInputs: move B out of popup, next to dot ===
# First, change the label (first) wrapper
old3 = b"  if (bEl) { var blbl = bEl.closest(" + D + b"label" + D + b") || bEl; lpop.appendChild(blbl); }"
new3 = b"  if (bEl) {\r\n    var blbl = bEl.closest(" + D + b"label" + D + b") || bEl;\r\n    var bSpan = document.createElement('span');\r\n    bSpan.className = 'cat-bold-btn';\r\n    bSpan.textContent = 'B';\r\n    if (bEl.checked) bSpan.classList.add('active');\r\n    bSpan.onclick = function(e){ e.stopPropagation(); bEl.checked = !bEl.checked; bSpan.classList.toggle('active', bEl.checked); };\r\n    lw.insertBefore(bSpan, lw.firstChild);\r\n    bEl.style.display = 'none';\r\n    lw.appendChild(bEl);\r\n  }"
c = c.replace(old3, new3)
print('3a. Label B moved')

# Sublabel wrapper
old3b = b"  if (sbEl) { var slbl = sbEl.closest(" + D + b"label" + D + b") || sbEl; spop.appendChild(slbl); }"
new3b = b"  if (sbEl) {\r\n    var slbl = sbEl.closest(" + D + b"label" + D + b") || sbEl;\r\n    var sbSpan = document.createElement('span');\r\n    sbSpan.className = 'cat-bold-btn';\r\n    sbSpan.textContent = 'B';\r\n    if (sbEl.checked) sbSpan.classList.add('active');\r\n    sbSpan.onclick = function(e){ e.stopPropagation(); sbEl.checked = !sbEl.checked; sbSpan.classList.toggle('active', sbEl.checked); };\r\n    sw.insertBefore(sbSpan, sw.firstChild);\r\n    sbEl.style.display = 'none';\r\n    sw.appendChild(sbEl);\r\n  }"
c = c.replace(old3b, new3b)
print('3b. Sublabel B moved')

# === 4. Update toggleBQControls: sync B span active state ===
old4 = b"  var bEl = card.querySelector('[id^=brCatBold]');\r\n  if (bEl) { var bl = bEl.closest('label'); if (bl) bl.style.visibility = show; }\r\n  var sbEl = card.querySelector('[id^=brCatSubLabelBold]');\r\n  if (sbEl) { var sbl = sbEl.closest('label'); if (sbl) sbl.style.visibility = show; }"
new4 = b"  var bEl = card.querySelector('[id^=brCatBold]');\r\n  if (bEl) { var bl = bEl.closest('label'); if (bl) bl.style.visibility = show; }\r\n  var sbEl = card.querySelector('[id^=brCatSubLabelBold]');\r\n  if (sbEl) { var sbl = sbEl.closest('label'); if (sbl) sbl.style.visibility = show; }\r\n  // Also sync cat-bold-btn visibility\r\n  card.querySelectorAll('.cat-bold-btn').forEach(function(bb){ bb.style.visibility = show; });"
c = c.replace(old4, new4)
print('4. toggleBQControls updated')

# === 5. initBQControls popup closer: hide color popup too ===
# (already handled by existing closer)

print('Braces:', c.count(b'{'), c.count(b'}'))
print('Size:', len(c), '(was', org, ')')
with open(path, 'wb') as f:
    f.write(c)
print('Done')
