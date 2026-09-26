"""Replace type=color inputs with color-dot + popup in cat-input-wrap"""
D = bytes([34])
N = bytes([13, 10])
path = r'B:\项目\Hass ASA Server Monitor\www\asa-admin.html'

with open(path, 'rb') as f:
    c = f.read()
org = len(c)

# === 1. CSS: position dot in input left edge ===
css_pos = c.find(b'.cat-input-wrap input[type=text]')
# Update input padding-left to make room for dot
old_pad = b'padding: 4px 24px 4px 24px;'
new_pad = b'padding: 4px 24px 4px 22px;'
c = c.replace(old_pad, new_pad)
print('1a. Input padding-left: 22px')

# Add dot positioning
dot_css_pos = c.find(b'.cat-input-wrap input[type=color]')
old_color_css = c[dot_css_pos:c.find(b'}', dot_css_pos) + 1]
new_dot_css = b'.cat-input-wrap > .cat-color-wrap { position:absolute; left:3px; top:50%; transform:translateY(-50%); z-index:1; }'
c = c[:dot_css_pos] + new_dot_css + N + c[dot_css_pos:]
print('1b. cat-color-wrap absolute left positioning')

# Remove the old color input CSS
c = c.replace(old_color_css + N, b'')
print('1c. Old color input CSS removed')

# === 2. Generalize toggleColorPopup: use data-target ===
# Update how toggleColorPopup finds the target
old_find = b"  var sel = pill.closest('.sr-cat-card').querySelector(" + D + b"select[id^=brCatMarkerColor]" + D + b");"
new_find = b"  var targetId = el.getAttribute('data-target');\r\n  var sel = document.getElementById(targetId);"
c = c.replace(old_find, new_find)
print('2. toggleColorPopup uses data-target')

# === 3. Update selectMarkerColor to use data-target ===
old_sel = b"  var sel = pill.closest('.sr-cat-card').querySelector(" + D + b"select[id^=brCatMarkerColor]" + D + b");"
new_sel = b"  var targetId = dot.getAttribute('data-target');\r\n  var sel = document.getElementById(targetId);"
c = c.replace(old_sel, new_sel)
print('3. selectMarkerColor uses data-target')

# === 4. mergeLabelInputs: replace color inputs with dots ===
# Find the first cat-input-wrap build section
old_lpop = b"  var clr = hdr.querySelector('[id^=brCatColor]');\r\n  if (clr) lpop.appendChild(clr);"
new_lpop = b"  var clr = hdr.querySelector('[id^=brCatColor]');\r\n  if (clr) {\r\n    var clrDot = document.createElement('span');\r\n    clrDot.className = 'cat-color-dot';\r\n    clrDot.style.background = clr.value || '#ffffff';\r\n    clrDot.setAttribute('data-target', clr.id);\r\n    clrDot.onclick = function(e){ e.stopPropagation(); toggleColorPopup(this); };\r\n    var clrWrap = document.createElement('span');\r\n    clrWrap.className = 'cat-color-wrap';\r\n    clrWrap.appendChild(clrDot);\r\n    lw.insertBefore(clrWrap, lw.firstChild);\r\n    clr.style.display = 'none';\r\n    lw.appendChild(clr);\r\n  }"
c = c.replace(old_lpop, new_lpop)
print('4a. Label color dot')

old_spop = b"  var sclr = hdr.querySelector('[id^=brCatSubLabelColor]');\r\n  if (sclr) spop.appendChild(sclr);"
new_spop = b"  var sclr = hdr.querySelector('[id^=brCatSubLabelColor]');\r\n  if (sclr) {\r\n    var sclrDot = document.createElement('span');\r\n    sclrDot.className = 'cat-color-dot';\r\n    sclrDot.style.background = sclr.value || '#ffffff';\r\n    sclrDot.setAttribute('data-target', sclr.id);\r\n    sclrDot.onclick = function(e){ e.stopPropagation(); toggleColorPopup(this); };\r\n    var sclrWrap = document.createElement('span');\r\n    sclrWrap.className = 'cat-color-wrap';\r\n    sclrWrap.appendChild(sclrDot);\r\n    sw.insertBefore(sclrWrap, sw.firstChild);\r\n    sclr.style.display = 'none';\r\n    sw.appendChild(sclr);\r\n  }"
c = c.replace(old_spop, new_spop)
print('4b. Sublabel color dot')

# === 5. Update enhanceBlockCollapse color creation ===
# Change from creating type=color input to creating hidden input + dot
old_ci2 = b"      ci2.type = 'color'; ci2.id = colorId; ci2.value = savedColor;\r\n      ci2.style.cssText = 'width:22px;height:20px;padding:1px;margin:0 2px';\r\n      el.parentElement.insertBefore(ci2, el.nextSibling);"
new_ci2 = b"      ci2.type = 'hidden'; ci2.id = colorId; ci2.value = savedColor;\r\n      el.parentElement.appendChild(ci2);"
c = c.replace(old_ci2, new_ci2)
print('5a. brCatColor → hidden')

old_sci = b"        sci2.type = 'color'; sci2.id = subColorId2; sci2.value = (cat?cat.sub_label_color:'') || '#ffffff';\r\n        sci2.style.cssText = 'width:22px;height:20px;padding:1px;margin:0 2px';\r\n        subEl2.parentElement.insertBefore(sci2, subEl2.nextSibling);"
new_sci = b"        sci2.type = 'hidden'; sci2.id = subColorId2; sci2.value = (cat?cat.sub_label_color:'') || '#ffffff';\r\n        subEl2.parentElement.appendChild(sci2);"
c = c.replace(old_sci, new_sci)
print('5b. brCatSubLabelColor → hidden')

# === 6. Update addStorageCat color enhancement ===
ac = c.find(b'function addStorageCat')
old_ac_ci = c.find(b"ci2.type = 'color'; ci2.id = colorId; ci2.value = '#ffffff';", ac)
if old_ac_ci > 0:
    old_ac_line = c[old_ac_ci:c.find(b"';", old_ac_ci + 100) + 2]
    new_ac_line = b"ci2.type = 'hidden'; ci2.id = colorId; ci2.value = '#ffffff';"
    c = c[:old_ac_ci] + new_ac_line + c[old_ac_ci + len(old_ac_line):]
    print('6a. AC brCatColor → hidden')

old_ac_sci = c.find(b"sci2.type = 'color'; sci2.id = subColorId2; sci2.value = '#ffffff';", ac)
if old_ac_sci > 0:
    old_ac_sci_line = c[old_ac_sci:c.find(b"';", old_ac_sci + 100) + 2]
    new_ac_sci_line = b"sci2.type = 'hidden'; sci2.id = subColorId2; sci2.value = '#ffffff';"
    c = c[:old_ac_sci] + new_ac_sci_line + c[old_ac_sci + len(old_ac_sci_line):]
    print('6b. AC brCatSubLabelColor → hidden')

# === 7. Update buildCatColBQPill dot creation: add data-target ===
old_bq_dot = b"dot.className = 'cat-color-dot'; dot.id = sel.id.replace('brCatCol','brCatCDot');"
new_bq_dot = b"dot.className = 'cat-color-dot'; dot.id = sel.id.replace('brCatCol','brCatCDot'); dot.setAttribute('data-target', 'brCatMarkerColor'+sel.id.replace('brCatCol',''));"
c = c.replace(old_bq_dot, new_bq_dot)
print('7. buildCatColBQPill data-target')

print('Braces:', c.count(b'{'), c.count(b'}'))
print('Size:', len(c), '(was', org, ')')

with open(path, 'wb') as f:
    f.write(c)
print('Done')
