# -*- coding: utf-8 -*-
import os

# Try both paths
paths = [
    r'B:\项目\Hass ASA Server Monitor\www\asa-admin.html',
    r'B:\項目\Hass ASA Server Monitor\www\asa-admin.html',
]
fpath = None
for p in paths:
    if os.path.exists(p):
        fpath = p
        break

if not fpath:
    print('File not found')
    exit(1)

with open(fpath, 'rb') as f:
    c = f.read()

changes = 0

# === 1. Render template: add brCatSubLabelBold after brCatBold ===
# Find: id="brCatBold'+si+'_...+'>B</label>';
search1 = b"id=\\brCatBold'+si+'_'+bi+'_'+ri+'_'+ci+'\\\" '+(cat.label_bold?'checked':'')+'>B</label>';"
idx1 = c.find(search1)
if idx1 > 0:
    end_of_line = idx1 + len(search1)
    # Next is \r\n, then more \r\n, then // Items
    new_line = b"\r\n                html += '<label style=\\\"font-size:0.6em;margin:0;display:flex;align-items:center;gap:1px;white-space:nowrap\\\"><input type=\\\"checkbox\\\" id=\\\"brCatSubLabelBold'+si+'_'+bi+'_'+ri+'_'+ci+'\\\" '+(cat.sub_label_bold?'checked':'')+'>B</label>';"
    c = c[:end_of_line] + new_line + c[end_of_line:]
    changes += 1
    print('1. Render template: brCatSubLabelBold added')
else:
    print('1. Render template NOT FOUND')
    idx = c.find(b"brCatBold'+si+'_'+bi+'_'+ri+'_'+ci+'\\")
    if idx > 0:
        print(f'   Found at {idx}: {c[idx:idx+120]!r}')

# === 2. addStorageCat: add brCatSubLabelBold after brCatBold ===
# Find second occurrence of brCatBold in addStorageCat
search2 = b"id=\\brCatBold'+si+'_'+bi+'_'+ri+'_'+ci+'\\\">B</label>';"
# Find after the 'h +=' version
pos_h = c.find(b"h += '<label style=\\\"font-size:0.6em")
idx2 = c.find(search2, pos_h) if pos_h > 0 else -1
if idx2 > 0:
    end_of_line2 = idx2 + len(search2)
    new_line2 = b"\r\n  h += '<label style=\\\"font-size:0.6em;margin:0;display:flex;align-items:center;gap:1px;white-space:nowrap\\\"><input type=\\\"checkbox\\\" id=\\\"brCatSubLabelBold'+si+'_'+bi+'_'+ri+'_'+ci+'\\\">B</label>';"
    c = c[:end_of_line2] + new_line2 + c[end_of_line2:]
    changes += 1
    print('2. addStorageCat: brCatSubLabelBold added')
else:
    print('2. addStorageCat NOT FOUND')
    if pos_h > 0:
        idx = c.find(b"brCatBold'+si+'_\", pos_h)
        if idx > 0:
            print(f'   Found at {idx}: {c[idx:idx+120]!r}')

# === 3. mergeLabelInputs ===
old_merge = b'// Label + color sub-wrapper'
pos3 = c.find(old_merge)
if pos3 > 0:
    # Find the closing } of mergeLabelInputs function
    # The function ends with: }
    # \nfunction initBQControls
    end3 = c.find(b'\n}\n\nfunction initBQControls', pos3)
    if end3 < 0:
        end3 = c.find(b'\n}\n\n\n\n\n\n\n\n\n\nfunction initBQControls', pos3)
    if end3 > 0:
        new_code = b'''// Label: bold + text input + color
  var lw = document.createElement('span');
  lw.className = 'cat-input-wrap';
  wrap.appendChild(lw);
  var bEl = hdr.querySelector('[id^=brCatBold]');
  if (bEl) { var blbl = bEl.closest('label') || bEl; lw.appendChild(blbl); }
  lw.appendChild(lbl);
  var clr = hdr.querySelector('[id^=brCatColor]');
  if (clr) lw.appendChild(clr);
  // Sublabel: bold + text input + color
  var sw = document.createElement('span');
  sw.className = 'cat-input-wrap';
  wrap.appendChild(sw);
  var sbEl = hdr.querySelector('[id^=brCatSubLabelBold]');
  if (sbEl) { var slbl = sbEl.closest('label') || sbEl; sw.appendChild(slbl); }
  sw.appendChild(sub);
  var sclr = hdr.querySelector('[id^=brCatSubLabelColor]');
  if (sclr) sw.appendChild(sclr);'''
        c = c[:pos3] + new_code + c[end3:]
        changes += 1
        print('3. mergeLabelInputs updated')
    else:
        print('3. end of mergeLabelInputs NOT FOUND')
else:
    print('3. mergeLabelInputs start NOT FOUND')

# === 4. CSS ===
css_marker = b'.cat-input-wrap input[type=text], .cat-input-wrap input:not([type])'
pos4 = c.find(css_marker)
if pos4 > 0:
    end4 = c.find(b'\n.sr-cat-card > .sr-items', pos4)
    if end4 > 0:
        new_css = b'''.cat-input-wrap input[type=text], .cat-input-wrap input:not([type]) { border: none !important; border-radius: 0 !important; margin: 0 !important; padding: 4px 24px 4px 24px; font-size: 0.75em; outline: none !important; box-shadow: none !important; height: 26px; box-sizing: border-box; }
.cat-input-wrap:first-child input[type=text], .cat-input-wrap:first-child input:not([type]) { width: 170px; font-weight: bold; }
.cat-input-wrap:last-child input[type=text], .cat-input-wrap:last-child input:not([type]) { width: 130px; font-size: 0.7em; }
.cat-input-wrap input[type=color] { position: absolute; right: 3px; top: 50%; transform: translateY(-50%); width: 18px !important; height: 18px !important; padding: 0 !important; border: 1px solid #888 !important; border-radius: 3px !important; cursor: pointer !important; background: transparent; z-index: 1; }
.cat-input-wrap > label { position: absolute; left: 3px; top: 50%; transform: translateY(-50%); font-size: 0.65em; margin: 0 !important; display: flex; align-items: center; gap: 1px; white-space: nowrap; z-index: 1; cursor: pointer; color: #999; user-select: none; }
.cat-input-wrap > label input[type=checkbox] { width: 11px; height: 11px; margin: 0; cursor: pointer; }
.cat-input-wrap > label:has(input:checked) { color: var(--primary-color, #2196F3); font-weight: bold; }
'''
        c = c[:pos4] + new_css + c[end4:]
        changes += 1
        print('4. CSS updated')
    else:
        print('4. CSS end NOT FOUND')
else:
    print('4. CSS start NOT FOUND')

# === 5. toggleBQControls - update to handle sub_label_bold ===
toggle_pos = c.find(b"var bEl = card.querySelector('[id^=brCatBold]');")
if toggle_pos > 0:
    after_line = c.find(b'\n', toggle_pos)
    # Find next line
    next_line = c.find(b'\n  var mkEl', toggle_pos)
    if next_line > 0:
        insert_code = b"\n  var sbEl = card.querySelector('[id^=brCatSubLabelBold]');\n  if (sbEl) { var sbl = sbEl.closest('label'); if (sbl) sbl.style.visibility = show; }"
        c = c[:next_line] + insert_code + c[next_line:]
        changes += 1
        print('5. toggleBQControls updated')
    else:
        print('5. next_line NOT FOUND')
else:
    print('5. toggleBQControls NOT FOUND')

# === 6. reorderCatCard order ===
order_pos = c.find(b'"brCatBold"')
if order_pos > 0:
    # The order array has: "brCatMarkerColor","brCatBold"
    # Replace with: "brCatMarkerColor","brCatBold","brCatSubLabelBold"
    end_quote = c.find(b'"', order_pos + len(b'"brCatBold"'))
    old_order = c[order_pos:end_quote]
    new_order = b'"brCatBold","brCatSubLabelBold"'
    if c[order_pos-1:order_pos] == b'"' and c[end_quote:end_quote+2] == b'"]':
        # The full segment is "brCatBold"] which means it's the last element
        c = c[:order_pos] + new_order + c[end_quote:]
        changes += 1
        print('6. reorderCatCard updated')
    else:
        print(f'6. order context: {c[order_pos-5:order_pos+20]!r}')
else:
    print('6. reorderCatCard order NOT FOUND')

with open(fpath, 'wb') as f:
    f.write(c)
print(f'Total changes: {changes}')
