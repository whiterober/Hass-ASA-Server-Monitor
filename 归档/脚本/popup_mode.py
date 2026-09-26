# -*- coding: utf-8 -*-
"""Restructure cat-input-wrap for floating popup on click"""
import os

d = r'B:\项目\Hass ASA Server Monitor\www'
fpath = os.path.join(d, 'asa-admin.html')
if not os.path.exists(fpath):
    # Try alternate path
    import glob
    files = glob.glob(r'B:\项目\Hass ASA Server Monitor\www\asa-admin*.html')
    if files:
        fpath = files[0]
    else:
        print('File not found')
        exit(1)

with open(fpath, 'rb') as f:
    c = f.read()

changes = 0

# ============================================================
# 1. Update CSS: cat-input-wrap simplified, add popup styles
# ============================================================
css_old = b'.cat-input-wrap input[type=text], .cat-input-wrap input:not([type]) { border: none !important; border-radius: 0 !important; margin: 0 !important; padding: 4px 24px 4px 24px; font-size: 0.75em; outline: none !important; box-shadow: none !important; height: 26px; box-sizing: border-box; }\r\n.cat-input-wrap:first-child input[type=text], .cat-input-wrap:first-child input:not([type]) { width: 170px; font-weight: bold; }\r\n.cat-input-wrap:last-child input[type=text], .cat-input-wrap:last-child input:not([type]) { width: 130px; font-size: 0.7em; }\r\n.cat-input-wrap input[type=color] { position: absolute; right: 3px; top: 50%; transform: translateY(-50%); width: 18px !important; height: 18px !important; padding: 0 !important; border: 1px solid #888 !important; border-radius: 3px !important; cursor: pointer !important; background: transparent; z-index: 1; }\r\n.cat-input-wrap > label { position: absolute; left: 3px; top: 50%; transform: translateY(-50%); font-size: 0.65em; margin: 0 !important; display: flex; align-items: center; gap: 1px; white-space: nowrap; z-index: 1; cursor: pointer; color: #999; user-select: none; }\r\n.cat-input-wrap > label input[type=checkbox] { width: 11px; height: 11px; margin: 0; cursor: pointer; }\r\n.cat-input-wrap > label:has(input:checked) { color: var(--primary-color, #2196F3); font-weight: bold; }\r\n'

css_new = b'''.cat-input-wrap { position: relative; }
.cat-input-wrap input[type=text], .cat-input-wrap input:not([type]) { border: none !important; border-radius: 0 !important; margin: 0 !important; padding: 4px 8px; font-size: 0.75em; outline: none !important; box-shadow: none !important; height: 26px; box-sizing: border-box; width: 100% !important; }
.cat-input-wrap:first-child { width: 170px; }
.cat-input-wrap:last-child { width: 130px; }
.cat-input-wrap:first-child input[type=text], .cat-input-wrap:first-child input:not([type]) { font-weight: bold; }
.cat-input-wrap:last-child input[type=text], .cat-input-wrap:last-child input:not([type]) { font-size: 0.7em; }
/* Floating popup for bold + color */
.cat-bc-popup {
  display: none;
  position: absolute;
  top: 100%;
  left: 0;
  margin-top: 2px;
  background: var(--card-background, #2a2a2a);
  border: 1px solid var(--primary-color, #2196F3);
  border-radius: 6px;
  padding: 5px 8px;
  z-index: 999;
  box-shadow: 0 4px 16px rgba(0,0,0,0.35);
  gap: 6px;
  align-items: center;
  white-space: nowrap;
}
.cat-bc-popup.show { display: flex; }
.cat-bc-popup label { font-size: 0.65em; margin: 0; display: flex; align-items: center; gap: 2px; cursor: pointer; color: #aaa; user-select: none; }
.cat-bc-popup label:has(input:checked) { color: var(--primary-color, #2196F3); font-weight: bold; }
.cat-bc-popup label input[type=checkbox] { width: 12px; height: 12px; margin: 0; cursor: pointer; }
.cat-bc-popup input[type=color] { width: 20px !important; height: 20px !important; padding: 0 !important; border: 1px solid #555 !important; border-radius: 3px !important; cursor: pointer !important; background: transparent; }
'''

if css_old in c:
    c = c.replace(css_old, css_new)
    changes += 1
    print('1. CSS updated for popup mode')
else:
    print('1. CSS block NOT FOUND')
    # Try to find partial
    idx = c.find(b'.cat-input-wrap input[type=text], .cat-input-wrap input:not([type]) {')
    print(f'   Found at {idx}')

# ============================================================
# 2. Update mergeLabelInputs - restructure DOM for popup
# ============================================================
merge_old = b'// Label: bold + text input + color'
merge_pos = c.find(merge_old)
if merge_pos > 0:
    close_brace = c.find(b'}\r\n', merge_pos + 400)
    if close_brace > 0:
        new_merge = (
            b'// Label: text input + popup(bold+color)\r\n'
            b"  var lw = document.createElement('span');\r\n"
            b"  lw.className = 'cat-input-wrap';\r\n"
            b'  wrap.appendChild(lw);\r\n'
            b'  lw.appendChild(lbl);\r\n'
            b'  // Build popup for label\r\n'
            b"  var lpop = document.createElement('span');\r\n"
            b"  lpop.className = 'cat-bc-popup';\r\n"
            b'  lw.appendChild(lpop);\r\n'
            b"  var bEl = hdr.querySelector('[id^=brCatBold]') || card.querySelector('[id^=brCatBold]');\r\n"
            b'  if (bEl) { var blbl = bEl.closest(\"label\") || bEl; lpop.appendChild(blbl); }\r\n'
            b"  var clr = hdr.querySelector('[id^=brCatColor]');\r\n"
            b'  if (clr) lpop.appendChild(clr);\r\n'
            b'  // Sublabel: text input + popup(bold+color)\r\n'
            b"  var sw = document.createElement('span');\r\n"
            b"  sw.className = 'cat-input-wrap';\r\n"
            b'  wrap.appendChild(sw);\r\n'
            b'  sw.appendChild(sub);\r\n'
            b"  var spop = document.createElement('span');\r\n"
            b"  spop.className = 'cat-bc-popup';\r\n"
            b'  sw.appendChild(spop);\r\n'
            b"  var sbEl = hdr.querySelector('[id^=brCatSubLabelBold]') || card.querySelector('[id^=brCatSubLabelBold]');\r\n"
            b'  if (sbEl) { var slbl = sbEl.closest(\"label\") || sbEl; spop.appendChild(slbl); }\r\n'
            b"  var sclr = hdr.querySelector('[id^=brCatSubLabelColor]');\r\n"
            b'  if (sclr) spop.appendChild(sclr);'
        )
        c = c[:merge_pos] + new_merge + c[close_brace+3:]
        changes += 1
        print('2. mergeLabelInputs restructured for popup')
    else:
        print('2. close_brace not found')
else:
    print('2. merge_old not found')

# ============================================================
# 3. Add click-to-show-popup JS logic
# ============================================================
init_pos = c.find(b'function initBQControls() {')
if init_pos > 0:
    # Find the line after initBQControls starts where we can add popup logic
    # Add after the existing initBQControls code
    init_body_start = c.find(b'{\r\n', init_pos) + 3  # skip past opening brace

    popup_js = (
        b'\r\n  // Click-to-show B+color popup on text inputs\r\n'
        b"  document.querySelectorAll('.cat-input-wrap input[type=text], .cat-input-wrap input:not([type])').forEach(function(inp){\r\n"
        b'    if (inp.dataset.popupReady) return;\r\n'
        b"    inp.dataset.popupReady = '1';\r\n"
        b"    inp.addEventListener('click', function(e){\r\n"
        b'      e.stopPropagation();\r\n'
        b'      // Hide all other popups first\r\n'
        b"      document.querySelectorAll('.cat-bc-popup.show').forEach(function(p){ p.classList.remove('show'); });\r\n"
        b"      var popup = inp.parentElement.querySelector('.cat-bc-popup');\r\n"
        b"      if (popup) popup.classList.add('show');\r\n"
        b'    });\r\n'
        b'  });\r\n'
        b'  // Click outside hides popup\r\n'
        b"  if (!document.body.dataset.popupCloser) {\r\n"
        b"    document.body.dataset.popupCloser = '1';\r\n"
        b"    document.addEventListener('click', function(e){\r\n"
        b"      if (!e.target.closest('.cat-input-wrap')) {\r\n"
        b"        document.querySelectorAll('.cat-bc-popup.show').forEach(function(p){ p.classList.remove('show'); });\r\n"
        b'      }\r\n'
        b'    });\r\n'
        b'  }\r\n'
    )

    c = c[:init_body_start] + popup_js + c[init_body_start:]
    changes += 1
    print('3. Popup click logic added to initBQControls')
else:
    print('3. initBQControls not found')

# ============================================================
# 4. Update toggleBQControls - hide/show popup instead
# ============================================================
# The toggleBQControls shows/hides elements based on blockquote checkbox
# With popup mode, we should hide the popup when blockquote is off
# But the .cat-merged wrapper already handles visibility
# Let's keep toggleBQControls as-is for now (targeting .cat-merged)

with open(fpath, 'wb') as f:
    f.write(c)
print(f'Total changes: {changes}')
