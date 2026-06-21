import os, sys

# Find asa-admin.html
d = r'B:\项目\Hass ASA Server Monitor\www'
fpath = os.path.join(d, 'asa-admin.html')
if not os.path.exists(fpath):
    print('NOT FOUND:', fpath)
    sys.exit(1)

with open(fpath, 'rb') as f:
    c = f.read()

changes = 0
DQUOTE = b'\x22'  # double quote byte
BS = b'\x5c'      # backslash byte

# Escaped double-quote in JS/HTML templates: \"
EQ = BS + DQUOTE  # \"

# === 1. Render template ===
# Find: id=\"brCatBold'+si+'_'+bi+'_'+ri+'_'+ci+'\" '+(cat.label_bold?'checked':'')+'>B</label>';
search1 = b'id=' + EQ + b'brCatBold' + b"'+si+'_'+bi+'_'+ri+'_'+ci+'" + EQ + b" '+(cat.label_bold?'checked':'')+'>B</label>';"
idx1 = c.find(search1)
if idx1 > 0:
    end1 = idx1 + len(search1)
    new1 = b'\r\n                html += ' + b"'" + b'<label style=' + EQ + b'font-size:0.6em;margin:0;display:flex;align-items:center;gap:1px;white-space:nowrap' + EQ + b'><input type=' + EQ + b'checkbox' + EQ + b' id=' + EQ + b'brCatSubLabelBold' + b"'+si+'_'+bi+'_'+ri+'_'+ci+'" + EQ + b" '+(cat.sub_label_bold?'checked':'')+'>B</label>';"
    c = c[:end1] + new1 + c[end1:]
    changes += 1
    print('1. Render: brCatSubLabelBold added')
else:
    print('1. NOT FOUND - searching for partial')
    p = c.find(b"brCatBold'+si+'_'+bi+'_'+ri+'_'+ci+'")
    if p > 0:
        print(f'  Found at {p}: {c[p:p+200]!r}')

# === 2. addStorageCat ===
# Find: id=\"brCatBold'+si+'_'+bi+'_'+ri+'_'+ci+'\">B</label>';
search2 = b'id=' + EQ + b'brCatBold' + b"'+si+'_'+bi+'_'+ri+'_'+ci+'" + EQ + b'>B</label>'
pos_ac = c.find(b"h += '<label style=", c.find(b'addStorageCat'))
if pos_ac > 0:
    idx2 = c.find(search2, pos_ac)
    if idx2 > 0:
        end2 = idx2 + len(search2) + 2  # include ';
        new2 = b'\r\n  h += ' + b"'" + b'<label style=' + EQ + b'font-size:0.6em;margin:0;display:flex;align-items:center;gap:1px;white-space:nowrap' + EQ + b'><input type=' + EQ + b'checkbox' + EQ + b' id=' + EQ + b'brCatSubLabelBold' + b"'+si+'_'+bi+'_'+ri+'_'+ci+'" + EQ + b'>B</label>' + b"';"
        c = c[:end2] + new2 + c[end2:]
        changes += 1
        print('2. addStorageCat: brCatSubLabelBold added')
    else:
        print('2. search2 not found')
else:
    print('2. addStorageCat pos_ac not found')

# === 3. mergeLabelInputs ===
old3 = b'// Label + color sub-wrapper'
pos3 = c.find(old3)
if pos3 > 0:
    # Find function end
    end3 = c.find(b'\n}\n\nfunction initBQControls', pos3)
    if end3 < 0:
        end3 = c.find(b'\n}\r\n\r\nfunction initBQControls', pos3)
    if end3 > 0:
        # Include the closing } at end3+1
        end3 += 2  # skip \n}
        new3 = (
            b'// Label: bold + text input + color\r\n'
            b"  var lw = document.createElement('span');\r\n"
            b"  lw.className = 'cat-input-wrap';\r\n"
            b'  wrap.appendChild(lw);\r\n'
            b"  var bEl = hdr.querySelector('[id^=brCatBold]');\r\n"
            b'  if (bEl) { var blbl = bEl.closest(\"label\") || bEl; lw.appendChild(blbl); }\r\n'
            b'  lw.appendChild(lbl);\r\n'
            b"  var clr = hdr.querySelector('[id^=brCatColor]');\r\n"
            b'  if (clr) lw.appendChild(clr);\r\n'
            b'  // Sublabel: bold + text input + color\r\n'
            b"  var sw = document.createElement('span');\r\n"
            b"  sw.className = 'cat-input-wrap';\r\n"
            b'  wrap.appendChild(sw);\r\n'
            b"  var sbEl = hdr.querySelector('[id^=brCatSubLabelBold]');\r\n"
            b'  if (sbEl) { var slbl = sbEl.closest(\"label\") || sbEl; sw.appendChild(slbl); }\r\n'
            b'  sw.appendChild(sub);\r\n'
            b"  var sclr = hdr.querySelector('[id^=brCatSubLabelColor]');\r\n"
            b'  if (sclr) sw.appendChild(sclr);'
        )
        c = c[:pos3] + new3 + c[end3:]
        changes += 1
        print('3. mergeLabelInputs updated')
    else:
        print('3. end3 not found')
else:
    print('3. mergeLabelInputs not found')

# === 4. CSS ===
css4 = b'.cat-input-wrap input[type=text], .cat-input-wrap input:not([type])'
pos4 = c.find(css4)
if pos4 > 0:
    end4 = c.find(b'\n.sr-cat-card > .sr-items', pos4)
    if end4 > 0:
        new4 = (
            b'.cat-input-wrap input[type=text], .cat-input-wrap input:not([type]) { border: none !important; border-radius: 0 !important; margin: 0 !important; padding: 4px 24px 4px 24px; font-size: 0.75em; outline: none !important; box-shadow: none !important; height: 26px; box-sizing: border-box; }\r\n'
            b'.cat-input-wrap:first-child input[type=text], .cat-input-wrap:first-child input:not([type]) { width: 170px; font-weight: bold; }\r\n'
            b'.cat-input-wrap:last-child input[type=text], .cat-input-wrap:last-child input:not([type]) { width: 130px; font-size: 0.7em; }\r\n'
            b'.cat-input-wrap input[type=color] { position: absolute; right: 3px; top: 50%; transform: translateY(-50%); width: 18px !important; height: 18px !important; padding: 0 !important; border: 1px solid #888 !important; border-radius: 3px !important; cursor: pointer !important; background: transparent; z-index: 1; }\r\n'
            b'.cat-input-wrap > label { position: absolute; left: 3px; top: 50%; transform: translateY(-50%); font-size: 0.65em; margin: 0 !important; display: flex; align-items: center; gap: 1px; white-space: nowrap; z-index: 1; cursor: pointer; color: #999; user-select: none; }\r\n'
            b'.cat-input-wrap > label input[type=checkbox] { width: 11px; height: 11px; margin: 0; cursor: pointer; }\r\n'
            b'.cat-input-wrap > label:has(input:checked) { color: var(--primary-color, #2196F3); font-weight: bold; }\r\n'
        )
        c = c[:pos4] + new4 + c[end4:]
        changes += 1
        print('4. CSS updated')
    else:
        print('4. CSS end not found')
else:
    print('4. CSS start not found')

# === 5. toggleBQControls ===
pos5 = c.find(b"var bEl = card.querySelector('[id^=brCatBold]');")
if pos5 > 0:
    next5 = c.find(b'\n  var mkEl = card.querySelector', pos5)
    if next5 > 0:
        ins5 = b"\r\n  var sbEl = card.querySelector('[id^=brCatSubLabelBold]');\r\n  if (sbEl) { var sbl = sbEl.closest('label'); if (sbl) sbl.style.visibility = show; }"
        c = c[:next5] + ins5 + c[next5:]
        changes += 1
        print('5. toggleBQControls updated')
    else:
        print('5. next5 not found')
else:
    print('5. toggleBQControls not found')

# === 6. saveBaseTab already done previously (sub_label_bold) ===
# Verify it's there
if b'sub_label_bold' in c:
    print('6. saveBaseTab already has sub_label_bold')
    changes += 1
else:
    # Add it
    p6 = c.find(b'label_bold: lbEl?.checked||false')
    if p6 > 0:
        end6 = p6 + len(b'label_bold: lbEl?.checked||false')
        ins6 = b', sub_label_bold: (catDiv.querySelector("[id^=brCatSubLabelBold]")?.checked)||false'
        c = c[:end6] + ins6 + c[end6:]
        changes += 1
        print('6. saveBaseTab: sub_label_bold added')
    else:
        print('6. saveBaseTab: label_bold not found')

with open(fpath, 'wb') as f:
    f.write(c)
print(f'Total changes: {changes}')
