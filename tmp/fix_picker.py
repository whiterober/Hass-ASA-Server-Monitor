# Fix picker HTML in openIconPicker(ctx)
fp = r"b:\项目\Hass ASA Server Monitor\www\asa-admin.html"
with open(fp, "r", encoding="utf-8") as f:
    c = f.read()

# === Fix 1: Add di/rowDi to icon_group ctx in render code ===
# Pattern: {mode:\'icon_group\',bi:'+bi+',ii:'+ii+'}
# Need: {mode:\'icon_group\',bi:'+bi+',ii:'+ii+',di:'+di+'}
# But di is not always available - let me check the context
# Actually, let me fix this differently: in openIconPicker, derive _igRowDi from ctx.di

# === Fix 2: Color button - replace toggleColorMode → toggleIconColorMode/toggleIconColorModeDesc ===
old_color_btn = 'html += "<button id=\""+colorBtnId+"\" data-mode=\"off\" style=\"width:auto;height:28px;padding:0 6px;display:inline-flex;align-items:center;gap:3px;border:1px solid var(--border);border-radius:4px;background:var(--input-bg);cursor:pointer;flex-shrink:0;font-size:0.8em\" onclick=\"event.stopPropagation();toggleColorMode(this)\" title=\"反色模式\"><svg width=\'12\' height=\'12\' viewBox=\'0 0 24 24\' fill=\'none\' stroke=\'currentColor\' stroke-width=\'2\'><circle cx=\'12\' cy=\'12\' r=\'10\'/><path d=\'M12 2a10 10 0 000 20V2z\'/></svg> 反色</button>"'

new_color_btn = '''// Color mode button (mode-specific, matching old proven HTML)
    if (ctx.mode === "desc_row" || ctx.mode === "icon_group") {
      html += "<button id=\\""+colorBtnId+"\\" data-mode=\\"off\\" style=\\"width:auto;height:28px;padding:0 6px;display:inline-flex;align-items:center;justify-content:center;border:1px solid var(--border);border-radius:4px;background:var(--input-bg);cursor:pointer;flex-shrink:0;font-size:0.75em;opacity:0.5\\" onclick=\\"event.stopPropagation();toggleIconColorModeDesc("+ctx.bi+","+(ctx.di||ctx.ii||0)+",this)\\" title=\\"\\u53cd\\u8272\\u6a21\\u5f0f\\uff1a\\u5173\\u95ed\\">\\u53cd\\u8272\\uff1a\\u5173</button>";
    } else if (ctx.mode === "info_card_title") {
      html += "<button id=\\""+colorBtnId+"\\" data-mode=\\"off\\" style=\\"width:auto;height:28px;padding:0 6px;display:inline-flex;align-items:center;justify-content:center;border:1px solid var(--border);border-radius:4px;background:var(--input-bg);cursor:pointer;flex-shrink:0;font-size:0.75em;opacity:0.5\\" onclick=\\"event.stopPropagation();toggleIconColorMode("+ctx.bi+",this)\\" title=\\"\\u53cd\\u8272\\u6a21\\u5f0f\\uff1a\\u5173\\u95ed\\">\\u53cd\\u8272\\uff1a\\u5173</button>";
    } else {
      html += "<button id=\\""+colorBtnId+"\\" data-mode=\\"off\\" style=\\"width:auto;height:28px;padding:0 6px;display:inline-flex;align-items:center;gap:3px;border:1px solid var(--border);border-radius:4px;background:var(--input-bg);cursor:pointer;flex-shrink:0;font-size:0.8em\\" onclick=\\"event.stopPropagation();toggleIconColorMode("+ctx.bi+",this)\\" title=\\"\\u53cd\\u8272\\u6a21\\u5f0f\\"><svg width=\\'12\\' height=\\'12\\' viewBox=\\'0 0 24 24\\' fill=\\'none\\' stroke=\\'currentColor\\' stroke-width=\\'2\\'><circle cx=\\'12\\' cy=\\'12\\' r=\\'10\\'/><path d=\\'M12 2a10 10 0 000 20V2z\\'/></svg> \\u53cd\\u8272</button>";
    }'''

if old_color_btn in c:
    c = c.replace(old_color_btn, new_color_btn)
    print("Fix 2: Color button FIXED")
else:
    print("Fix 2: NOT FOUND")

# === Fix 3: Icon grid onclick - use direct handler calls ===
old_onclick = 'selectIcon(this,'+ctxJsonEsc+')'
new_onclick = 'selectIcon(this,' + ctxJsonEsc + ')'

# Actually the issue is the onclick uses selectIcon. Let me replace with mode-specific direct calls
# The code is: onclick='if(comboMode){toggleComboSelect(this)}else{selectIcon(this,CTX)}'
# Need to change to mode-specific direct calls
old_grid = '''html += "<div class='icon-picker-item' data-url='"+item.url+"' data-cat='"+cat2+"' onclick='if(comboMode){toggleComboSelect(this)}else{selectIcon(this,"+ctxJsonEsc+")}' title='"+item.name+"'><img src='"+thumbUrl(item.url,96)+"' loading='lazy' decoding='async' class='icon-picker-img' onload='this.classList.add(\\"loaded\\")' onerror='this.src=this.getAttribute(\\"data-src\\")||\\"\\";this.hidden=true' data-src='"+item.url+"'><span>"+item.name+"</span></div>"'''

new_grid = '''// Mode-specific icon onclick (matching old proven HTML)
    var iconOnclick;
    if (ctx.mode === "info_card_title") {
      iconOnclick = "selectInfoCardIcon(this,"+ctx.bi+")";
    } else if (ctx.mode === "desc_row") {
      iconOnclick = "selectDescImage(this,"+ctx.bi+","+ctx.di+")";
    } else if (ctx.mode === "icon_group") {
      iconOnclick = "selectDescImage(this,"+ctx.bi+","+(ctx.ii||0)+")";
    } else if (ctx.mode === "base_row") {
      iconOnclick = "selectBaseIcon(this,"+ctxJsonEsc+")";
    } else {
      iconOnclick = "selectBaseIcon(this,"+ctxJsonEsc+")";
    }
    html += "<div class='icon-picker-item' data-url='"+item.url+"' data-cat='"+cat2+"' onclick='if(comboMode){toggleComboSelect(this)}else{"+iconOnclick+"}' title='"+item.name+"'><img src='"+thumbUrl(item.url,96)+"' loading='lazy' decoding='async' class='icon-picker-img' onload='this.classList.add(\\"loaded\\")' onerror='this.src=this.getAttribute(\\"data-src\\")||\\"\\";this.hidden=true' data-src='"+item.url+"'><span>"+item.name+"</span></div>"'''

if old_grid in c:
    c = c.replace(old_grid, new_grid)
    print("Fix 3: Grid onclick FIXED")
else:
    print("Fix 3: NOT FOUND")
    # Try to find it
    pos = c.find('selectIcon(this,'+ctxJsonEsc+')')
    if pos >= 0:
        print(f"  Found 'selectIcon(this,' at offset {pos}")
    
# === Fix 4: _igRowDi extraction - use ctx.di if available ===
old_igrow = "if (cfg.igRowDi) { overlay._igRowDi = ctx.rowDi != null ? ctx.rowDi : (ctx.ii != null ? ctx.ii : 0); }"
new_igrow = "if (cfg.igRowDi) { overlay._igRowDi = ctx.di != null ? ctx.di : (ctx.rowDi != null ? ctx.rowDi : (ctx.ii != null ? ctx.ii : 0)); }"
if old_igrow in c:
    c = c.replace(old_igrow, new_igrow)
    print("Fix 4: _igRowDi FIXED")
else:
    print("Fix 4: NOT FOUND")

with open(fp, "w", encoding="utf-8") as f:
    f.write(c)
print(f"DONE. {len(c)} bytes")
