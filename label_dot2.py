"""Replace type=color with dots - SAFE version"""
D = bytes([34])
N = bytes([13, 10])
path = r'B:\项目\Hass ASA Server Monitor\www\asa-admin.html'

with open(path, 'rb') as f:
    c = f.read()
org = len(c)

# === 1. CSS: position dot in input left ===
old_pad = b'padding: 4px 24px 4px 24px;'
new_pad = b'padding: 4px 24px 4px 22px;'
n1 = c.count(old_pad)
c = c.replace(old_pad, new_pad)
print(f'1a. Padding: {n1}')

# Add cat-input-wrap dot positioning before the old color input CSS
color_css_pos = c.find(b'.cat-input-wrap input[type=color]')
new_css = b'.cat-input-wrap > .cat-color-wrap { position:absolute;left:3px;top:50%;transform:translateY(-50%);z-index:1; }\r\n'
c = c[:color_css_pos] + new_css + c[color_css_pos:]
print('1b. Dot positioning CSS')

# === 2. toggleColorPopup: data-target ===
old2 = b"  var sel = pill.closest('.sr-cat-card').querySelector(" + D + b"select[id^=brCatMarkerColor]" + D + b");\r\n  var cur = sel ? sel.value : " + D + b"#ccc" + D + b";"
new2 = b"  var targetId = el.getAttribute('data-target');\r\n  var sel = document.getElementById(targetId);\r\n  var cur = sel ? sel.value : " + D + b"#ccc" + D + b";"
c = c.replace(old2, new2)
print('2. toggleColorPopup')

# === 3. selectMarkerColor: data-target ===
old3 = b"  var sel = pill.closest('.sr-cat-card').querySelector(" + D + b"select[id^=brCatMarkerColor]" + D + b");\r\n  if (sel) sel.value = clr;"
new3 = b"  var targetId = dot.getAttribute('data-target');\r\n  var sel = document.getElementById(targetId);\r\n  if (sel) sel.value = clr;"
c = c.replace(old3, new3)
print('3. selectMarkerColor')

# === 4. mergeLabelInputs: replace color inputs with dots ===
old4 = b"  var clr = hdr.querySelector('[id^=brCatColor]');\r\n  if (clr) lpop.appendChild(clr);"
new4 = b"  var clr = hdr.querySelector('[id^=brCatColor]');\r\n  if (clr) {\r\n    var clrDot = document.createElement('span');\r\n    clrDot.className = 'cat-color-dot';\r\n    clrDot.style.background = clr.value || '#ffffff';\r\n    clrDot.setAttribute('data-target', clr.id);\r\n    clrDot.onclick = function(e){ e.stopPropagation(); toggleColorPopup(this); };\r\n    var clrWrap = document.createElement('span');\r\n    clrWrap.className = 'cat-color-wrap';\r\n    clrWrap.appendChild(clrDot);\r\n    lw.insertBefore(clrWrap, lw.firstChild);\r\n    clr.style.display = 'none';\r\n    lw.appendChild(clr);\r\n  }"
c = c.replace(old4, new4)
print('4a. Label dot')

old4b = b"  var sclr = hdr.querySelector('[id^=brCatSubLabelColor]');\r\n  if (sclr) spop.appendChild(sclr);"
new4b = b"  var sclr = hdr.querySelector('[id^=brCatSubLabelColor]');\r\n  if (sclr) {\r\n    var sclrDot = document.createElement('span');\r\n    sclrDot.className = 'cat-color-dot';\r\n    sclrDot.style.background = sclr.value || '#ffffff';\r\n    sclrDot.setAttribute('data-target', sclr.id);\r\n    sclrDot.onclick = function(e){ e.stopPropagation(); toggleColorPopup(this); };\r\n    var sclrWrap = document.createElement('span');\r\n    sclrWrap.className = 'cat-color-wrap';\r\n    sclrWrap.appendChild(sclrDot);\r\n    sw.insertBefore(sclrWrap, sw.firstChild);\r\n    sclr.style.display = 'none';\r\n    sw.appendChild(sclr);\r\n  }"
c = c.replace(old4b, new4b)
print('4b. Sublabel dot')

# === 5. enhanceBlockCollapse: hidden instead of color inputs ===
old5 = b"      ci2.type = 'color'; ci2.id = colorId; ci2.value = savedColor;\r\n      ci2.style.cssText = 'width:22px;height:20px;padding:1px;margin:0 2px';\r\n      el.parentElement.insertBefore(ci2, el.nextSibling);"
new5 = b"      ci2.type = 'hidden'; ci2.id = colorId; ci2.value = savedColor;\r\n      el.parentElement.appendChild(ci2);"
c = c.replace(old5, new5)
print('5a. brCatColor hidden')

old5b = b"        sci2.type = 'color'; sci2.id = subColorId2; sci2.value = (cat?cat.sub_label_color:'') || '#ffffff';\r\n        sci2.style.cssText = 'width:22px;height:20px;padding:1px;margin:0 2px';\r\n        subEl2.parentElement.insertBefore(sci2, subEl2.nextSibling);"
new5b = b"        sci2.type = 'hidden'; sci2.id = subColorId2; sci2.value = (cat?cat.sub_label_color:'') || '#ffffff';\r\n        subEl2.parentElement.appendChild(sci2);"
c = c.replace(old5b, new5b)
print('5b. brCatSubLabelColor hidden')

# === 6. addStorageCat color enhancement ===
ac = c.find(b'function addStorageCat')
old6 = b"      ci2.type = 'color'; ci2.id = colorId; ci2.value = '#ffffff';\r\n      ci2.style.cssText = 'width:22px;height:20px;padding:1px;margin:0 2px';\r\n      el.parentElement.insertBefore(ci2, el.nextSibling);"
new6 = b"      ci2.type = 'hidden'; ci2.id = colorId; ci2.value = '#ffffff';\r\n      el.parentElement.appendChild(ci2);"
n6 = c.count(old6)
c = c.replace(old6, new6)
print(f'6a. AC brCatColor: {n6}')

old6b = b"        sci2.type = 'color'; sci2.id = subColorId2; sci2.value = '#ffffff';\r\n        sci2.style.cssText = 'width:22px;height:20px;padding:1px;margin:0 2px';\r\n        subEl2.parentElement.insertBefore(sci2, subEl2.nextSibling);"
new6b = b"        sci2.type = 'hidden'; sci2.id = subColorId2; sci2.value = '#ffffff';\r\n        subEl2.parentElement.appendChild(sci2);"
n6b = c.count(old6b)
c = c.replace(old6b, new6b)
print(f'6b. AC brCatSubLabelColor: {n6b}')

# === 7. build marker dot: data-target ===
old7 = b"dot.className = 'cat-color-dot'; dot.id = sel.id.replace('brCatCol','brCatCDot');"
new7 = b"dot.className = 'cat-color-dot'; dot.id = sel.id.replace('brCatCol','brCatCDot');\r\n  dot.setAttribute('data-target', 'brCatMarkerColor'+sel.id.replace('brCatCol',''));"
c = c.replace(old7, new7)
print('7. markerDot data-target')

# === 8. AC template: data-target on dot ===
ac2 = c.find(b'function addStorageCat')
dot_ac = c.find(b'cat-color-dot', ac2)
if dot_ac > 0:
    ls = c.rfind(b'\n', 0, dot_ac) + 1
    le = c.find(b'\n', dot_ac + 50)
    old_line = c[ls:le]
    # Add data-target attribute
    new_line = old_line.replace(
        b'onclick="toggleColorPopup(this)"',
        b'data-target="brCatMarkerColor'+b"'+si+'_'+bi+'_'+ri+'_'+ci+'"+b'" onclick="toggleColorPopup(this)"'
    )
    c = c[:ls] + new_line + c[le:]
    print('8. AC dot data-target')

print('Braces:', c.count(b'{'), c.count(b'}'))
print('Size:', len(c), '(was', org, ')')
with open(path, 'wb') as f:
    f.write(c)
print('Done')
