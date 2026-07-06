# Fix picker HTML in openIconPicker(ctx) - v2
fp = r"b:\项目\Hass ASA Server Monitor\www\asa-admin.html"
with open(fp, "r", encoding="utf-8") as f:
    c = f.read()

did = 0

# Fix 2: Color button - find by the toggleColorMode pattern
pos = c.find('toggleColorMode(this)')
if pos >= 0:
    # Find the full line containing this
    line_start = c.rfind('\n', 0, pos) + 1
    line_end = c.find('\n', pos)
    old_line = c[line_start:line_end]
    
    new_line = '''    // Color mode button (mode-specific, matching old proven HTML)
    if (ctx.mode === "desc_row" || ctx.mode === "icon_group") {
      html += "<button id=\\""+colorBtnId+"\\" data-mode=\\"off\\" style=\\"width:auto;height:28px;padding:0 6px;display:inline-flex;align-items:center;justify-content:center;border:1px solid var(--border);border-radius:4px;background:var(--input-bg);cursor:pointer;flex-shrink:0;font-size:0.75em;opacity:0.5\\" onclick=\\"event.stopPropagation();toggleIconColorModeDesc("+ctx.bi+","+(ctx.di||ctx.ii||0)+",this)\\" title=\\"\\u53cd\\u8272\\u6a21\\u5f0f\\uff1a\\u5173\\u95ed\\">\\u53cd\\u8272\\uff1a\\u5173</button>";
    } else if (ctx.mode === "info_card_title") {
      html += "<button id=\\""+colorBtnId+"\\" data-mode=\\"off\\" style=\\"width:auto;height:28px;padding:0 6px;display:inline-flex;align-items:center;justify-content:center;border:1px solid var(--border);border-radius:4px;background:var(--input-bg);cursor:pointer;flex-shrink:0;font-size:0.75em;opacity:0.5\\" onclick=\\"event.stopPropagation();toggleIconColorMode("+ctx.bi+",this)\\" title=\\"\\u53cd\\u8272\\u6a21\\u5f0f\\uff1a\\u5173\\u95ed\\">\\u53cd\\u8272\\uff1a\\u5173</button>";
    } else {
      html += "<button id=\\""+colorBtnId+"\\" data-mode=\\"off\\" style=\\"width:auto;height:28px;padding:0 6px;display:inline-flex;align-items:center;gap:3px;border:1px solid var(--border);border-radius:4px;background:var(--input-bg);cursor:pointer;flex-shrink:0;font-size:0.8em\\" onclick=\\"event.stopPropagation();toggleIconColorMode("+ctx.bi+",this)\\" title=\\"\\u53cd\\u8272\\u6a21\\u5f0f\\"><svg width=\\'12\\' height=\\'12\\' viewBox=\\'0 0 24 24\\' fill=\\'none\\' stroke=\\'currentColor\\' stroke-width=\\'2\\'><circle cx=\\'12\\' cy=\\'12\\' r=\\'10\\'/><path d=\\'M12 2a10 10 0 000 20V2z\\'/></svg> \\u53cd\\u8272</button>";
    }'''
    c = c[:line_start] + new_line + '\n' + c[line_end+1:]
    print("Fix 2: Color button FIXED")
    did += 1

# Fix 3: Icon grid onclick - find selectIcon pattern
pos3 = c.find("selectIcon(this,")
if pos3 >= 0:
    line_start3 = c.rfind('\n', 0, pos3) + 1
    line_end3 = c.find('\n', pos3)
    old_line3 = c[line_start3:line_end3]
    
    new_line3 = '''    // Mode-specific icon onclick (matching old proven HTML)
    var iconOnclick;
    if (ctx.mode === "info_card_title") {
      iconOnclick = "selectInfoCardIcon(this,"+ctx.bi+")";
    } else if (ctx.mode === "desc_row") {
      iconOnclick = "selectDescImage(this,"+ctx.bi+","+ctx.di+")";
    } else if (ctx.mode === "icon_group") {
      iconOnclick = "selectDescImage(this,"+ctx.bi+","+(ctx.ii||0)+")";
    } else {
      iconOnclick = "selectBaseIcon(this,"+ctxJsonEsc+")";
    }
    list.forEach(function(item){
      var parts2 = item.url.split("ASA/")[1]?item.url.split("ASA/")[1].split("/"):null;
      var cat2 = (parts2 && parts2.length > 1) ? parts2[0] : "\\u5176\\u4ed6";
      html += "<div class='icon-picker-item' data-url='"+item.url+"' data-cat='"+cat2+"' onclick='if(comboMode){toggleComboSelect(this)}else{"+iconOnclick+"}' title='"+item.name+"'><img src='"+thumbUrl(item.url,96)+"' loading='lazy' decoding='async' class='icon-picker-img' onload='this.classList.add(\\"loaded\\")' onerror='this.src=this.getAttribute(\\"data-src\\")||\\"\\";this.hidden=true' data-src='"+item.url+"'><span>"+item.name+"</span></div>";'''
    c = c[:line_start3] + new_line3 + '\n' + c[line_end3+1:]
    print("Fix 3: Grid onclick FIXED")
    did += 1

# Fix 4: _igRowDi
old4 = "if (cfg.igRowDi) { overlay._igRowDi = ctx.rowDi != null ? ctx.rowDi : (ctx.ii != null ? ctx.ii : 0); }"
new4 = "if (cfg.igRowDi) { overlay._igRowDi = ctx.di != null ? ctx.di : (ctx.rowDi != null ? ctx.rowDi : (ctx.ii != null ? ctx.ii : 0)); }"
if old4 in c:
    c = c.replace(old4, new4)
    print("Fix 4: _igRowDi FIXED")
    did += 1
else:
    print("Fix 4: NOT FOUND")

if did == 0:
    print("NO FIXES APPLIED")
else:
    with open(fp, "w", encoding="utf-8") as f:
        f.write(c)
    print(f"DONE. {did} fixes. {len(c)} bytes")
