with open(r'B:\项目\Hass ASA Server Monitor\www\asa-admin.html', 'r', encoding='utf-8') as f:
    c = f.read()

print("=== Starting big refactor ===")

# ============================================================
# 1. CSS - merged label container
# ============================================================
css_old = '.sr-cat-card [id^=brCatColor], .sr-cat-card [id^=brCatSubLabelColor]'
css_new = '''.cat-label-group { display: flex; border: 1px solid var(--border); border-radius: 6px; overflow: hidden; }
.cat-label-wrap, .cat-sublabel-wrap { position: relative; display: flex; align-items: center; }
.cat-sublabel-wrap { border-left: 1px solid var(--border); }
.cat-label-wrap input, .cat-sublabel-wrap input { border: none !important; border-radius: 0 !important; margin: 0 !important; }
.cat-label-wrap input[type=text], .cat-sublabel-wrap input[type=text] { width: 70px; padding: 4px 22px 4px 8px; font-size: 0.75em; }
.cat-sublabel-wrap input[type=text] { width: 55px; }
.cat-label-wrap input[type=color], .cat-sublabel-wrap input[type=color] { position: absolute; right: 2px; width: 14px !important; height: 14px !important; padding: 0 !important; border: none !important; border-radius: 50% !important; cursor: pointer !important; }
.sr-cat-card [id^=brCatColor], .sr-cat-card [id^=brCatSubLabelColor]'''
c = c.replace(css_old, css_new)
print("1. CSS added")

# ============================================================
# 2. Render template - replace the marker label + color select section
# Remove: ■ checkbox (brCatMarker), marker color select
# Add: merged label+sublabel container
# ============================================================

# Remove brCatMarker label
old_marker = "<label style=\"font-size:0.6em;margin:0;display:flex;align-items:center;gap:1px;white-space:nowrap\"><input type=\"checkbox\" id=\"brCatMarker'+si+'_'+bi+'_'+ri+'_'+ci+'\" '+(cat.show_marker?'checked':'')+'>■</label>"
c = c.replace(old_marker, '')
print(f"2. brCatMarker removed: {old_marker not in c}")

# Remove brCatMarkerColor select
old_mkcolor = "<select id=\"brCatMarkerColor'+si+'_'+bi+'_'+ri+'_'+ci+'\" style=\"width:44px;padding:1px;font-size:0.6em;margin:0\">'+mkOpts+'</select>"
c = c.replace(old_mkcolor, '')
print(f"2b. MarkerColor select removed: {old_mkcolor not in c}")

# Wrap brCatLabel+brCatColor in cat-label-wrap
old_lbl_start = "<input id=\"brCatLabel'+si+'_'+bi+'_'+ri+'_'+ci+'\" value=\"'+esc(cat.label||'')+'\" placeholder=\"分类名\" style=\"width:90px;padding:4px 8px;font-size:0.75em;font-weight:bold;margin:0\">"
new_lbl_wrap = '''<span class="cat-label-group"><span class="cat-label-wrap"><input id="brCatLabel'+si+'_'+bi+'_'+ri+'_'+ci+'\" value="'+esc(cat.label||'')+'" placeholder="分类名"><input type="color" id="brCatColor'+si+'_'+bi+'_'+ri+'_'+ci+'\" value="'+((cat.label_color||cat.color||'')===''?'%23444':esc(cat.label_color||cat.color||'%23444'))+'" title="分类名颜色"></span><span class="cat-sublabel-wrap"><input id="brCatSubLabel'+si+'_'+bi+'_'+ri+'_'+ci+'\" value="'+esc(cat.sub_label||'')+'" placeholder="副标签"><input type="color" id="brCatSubLabelColor'+si+'_'+bi+'_'+ri+'_'+ci+'\" value="'+((cat.sub_label_color||'')===''?'%23444':esc(cat.sub_label_color||'%23444'))+'" title="副标签颜色"></span></span>'''
c = c.replace(old_lbl_start, new_lbl_wrap)
print(f"3. Label+sublabel merged: {'cat-label-group' in c}")

# Remove the old standalone brCatColor and brCatSubLabel inputs (were added by earlier scripts)
# Search for the generated lines after the label input
old_after_lbl = "html += '<input type=\"color\" id=\"brCatColor'+si+'_'+bi+'_'+ri+'_'+ci+'\""
idx = c.find(old_after_lbl)
if idx > 0:
    endline = c.find('\n', idx)
    c = c[:idx] + c[endline:]
    print(f"3b. Removed old color input line")

# Remove old sublabel line
old_sublabel_line = "html += '<input id=\"brCatSubLabel'+si+'_'+bi+'_'+ri+'_'+ci+'\""
idx2 = c.find(old_sublabel_line)
if idx2 > 0:
    endline2 = c.find('\n', idx2)
    c = c[:idx2] + c[endline2:]
    print(f"3c. Removed old sublabel line")

# Remove old sublabel color line
old_slcolor_line = "html += '<input type=\"hidden\" id=\"brCatSubLabelColor'+si+'_'+bi+'_'+ri+'_'+ci+'\""
idx3 = c.find(old_slcolor_line)
if idx3 > 0:
    endline3 = c.find('\n', idx3)
    c = c[:idx3] + c[endline3:]
    print(f"3d. Removed old sublabel color line")
elif 'brCatSubLabelColor' in c:
    # Hidden input version
    pass
    print(f"3d. sublabel color exists")

# ============================================================
# 4. Update saveBaseTab - remove show_marker, add sub_label_color
# ============================================================
old_save = "show_marker: mkEl?.checked||false, marker_color: (mkCEl?.value)||'#ff9800'"
new_save = "marker_color: (mkCEl?.value)||'#ff9800'"
c = c.replace(old_save, new_save)
print(f"4. Save updated: {'show_marker' not in c[c.find('function saveBaseTab'):c.find('function saveBaseTab')+5000]}")

# Remove mkEl reading line
old_mk = "var mkEl = catDiv.querySelector('[id^=brCatMarker]');\n                    var mkCEl = catDiv.querySelector('[id^=brCatMarkerColor]');"
new_mk = "var mkCEl = catDiv.querySelector('[id^=brCatMarkerColor]');"
c = c.replace(old_mk, new_mk)
print(f"4b. mkEl removed: {old_mk not in c}")

# ============================================================
# 5. Update reorderCatCard order array
# ============================================================
old_order = '"brCatCol","brCatBQ","brCatLabel","brCatSubLabel","brCatSubLabelColor","brCatColor","brCatMarker","brCatMarkerColor","brCatBold"'
new_order = '"brCatCol","brCatBQ","brCatBold"'
c = c.replace(old_order, new_order)
print(f"5. Reorder simplified: {new_order in c}")

# Update reorderCatCard body - simplified since most elements are now in the merged container
old_reorder_body = '''  order.forEach(function(prefix){
    var el = header.querySelector("[id^="+prefix+"]") || card.querySelector("[id^="+prefix+"]");
    if (el) { var parent = el.closest("label") || el; header.appendChild(parent); }
  });'''
new_reorder_body = '''  // Col, BQ first
  var colEl = header.querySelector("[id^=brCatCol]"); if (colEl) header.insertBefore(colEl, header.firstChild);
  var bqEl = header.querySelector("[id^=brCatBQ]")?.closest("label"); if (bqEl) { header.insertBefore(bqEl, colEl?.nextSibling); }
  // B before delete
  var bEl = header.querySelector("[id^=brCatBold]")?.closest("label"); if (bEl) { var delBtn2 = header.querySelector("button"); if (delBtn2) header.insertBefore(bEl, delBtn2); }'''
c = c.replace(old_reorder_body, new_reorder_body)
print(f"5b. Reorder body updated")

# ============================================================
# 6. Update toggleBQControls
# ============================================================
old_toggle = '''function toggleBQControls(cb) {
  var card = cb.closest('.sr-cat-card');
  if (!card) return;
  var show = cb.checked ? 'visible' : 'hidden';
  var labelEl = card.querySelector('[id^=brCatLabel]');
  var markerRow = card.querySelector(':scope > div:nth-child(2)');
  var colorInput = card.querySelector('[id^=brCatColor]');
  if (labelEl) labelEl.style.visibility = show;
  if (colorInput) colorInput.style.visibility = show;
  var mkEl = card.querySelector('[id^=brCatMarker]');
  var bEl = card.querySelector('[id^=brCatBold]');
  var mcEl = card.querySelector('[id^=brCatMarkerColor]');
  if (mkEl) { var ml = mkEl.closest('label'); if (ml) ml.style.visibility = show; }
  if (bEl) { var bl = bEl.closest('label'); if (bl) bl.style.visibility = show; }
  if (mcEl) mcEl.style.visibility = show;
  var subEl = card.querySelector("[id^=brCatSubLabel]"); if (subEl) { subEl.style.visibility = show; var scEl = card.querySelector("[id^=brCatSubLabelColor]"); if (scEl) scEl.style.visibility = show; }
}'''

new_toggle = '''function toggleBQControls(cb) {
  var card = cb.closest('.sr-cat-card');
  if (!card) return;
  var show = cb.checked ? 'visible' : 'hidden';
  var group = card.querySelector('.cat-label-group');
  if (group) group.style.visibility = show;
  var bEl = card.querySelector('[id^=brCatBold]');
  if (bEl) { var bl = bEl.closest('label'); if (bl) bl.style.visibility = show; }
}'''
c = c.replace(old_toggle, new_toggle)
print(f"6. Toggle simplified: {new_toggle in c}")

# ============================================================
# 7. buildStorageBody - remove ■, use marker_color for border-left
# ============================================================
# Remove ■ from label rendering
old_bq = '''if (cat.show_marker && cat.marker_color && cm[cat.marker_color]) {
            h += '<div><span class="'+cm[cat.marker_color]+'">■ </span>';
            h += '<span class="'+(lc&&cm[lc]?cm[lc]+' ':'')+(lb?'text-bold':'')+'">'+cat.label+'</span>';\n          } else if (lc && cm[lc]) {\n            h += '<div><span class="'+cm[lc]+'">■ </span><span class="'+(cm[lc]||'')+(lb?' text-bold':'')+'">'+cat.label+'</span>';\n          } else {\n            h += '<div>'+(lb?'<span class=\"text-bold\">'+cat.label+'</span>':cat.label);\n          }'''
new_bq = '''if (lb) {
            h += '<div><span class="text-bold">'+cat.label+'</span>';\n          } else {\n            h += '<div>'+cat.label+'</div>';\n          }'''
# Actually, let me keep the label_color rendering
# Simplest: just remove the ■ spans, keep the rest
c = c.replace(old_bq, new_bq)
print(f"7. ■ removed from buildStorageBody: {new_bq in c}")

# Add border-left-color based on marker_color
# Find: h += useBQ ? '<blockquote class="quote">' : '<div>';
old_blockquote = "h += useBQ ? '<blockquote class=\"quote\">' : '<div>';"
new_blockquote = "h += useBQ ? '<blockquote class=\"quote\" style=\"border-left-color:'+(cat.marker_color||'#ccc')+'\" >' : '<div>';"
c = c.replace(old_blockquote, new_blockquote)
print(f"7b. Blockquote border color: {new_blockquote in c}")

# ============================================================
# 8. addStorageCat - also update
# ============================================================
# Remove ■ and markerColor from addStorageCat
old_ac_marker = "<label style=\"font-size:0.6em;margin:0;display:flex;align-items:center;gap:1px;white-space:nowrap\"><input type=\"checkbox\" id=\"brCatMarker'+si+'_'+bi+'_'+ri+'_'+ci+'\">■</label>"
c = c.replace(old_ac_marker, '')
old_ac_mkcolor = "<select id=\"brCatMarkerColor'+si+'_'+bi+'_'+ri+'_'+ci+'\" style=\"width:44px;padding:1px;font-size:0.6em;margin:0\">'+mkOpts+'</select>"
c = c.replace(old_ac_mkcolor, '')

# Update addStorageCat label to use merged container
old_ac_lbl = "<input id=\"brCatLabel'+si+'_'+bi+'_'+ri+'_'+ci+'\" value=\"\" placeholder=\"分类名\" style=\"width:90px;padding:4px 8px;font-size:0.75em;font-weight:bold;margin:0\">"
new_ac_lbl = '''<span class="cat-label-group"><span class="cat-label-wrap"><input id="brCatLabel'+si+'_'+bi+'_'+ri+'_'+ci+'\" value="" placeholder="分类名"><input type="color" id="brCatColor'+si+'_'+bi+'_'+ri+'_'+ci+'\" value="%23444" title="分类名颜色"></span><span class="cat-sublabel-wrap"><input id="brCatSubLabel'+si+'_'+bi+'_'+ri+'_'+ci+'\" value="" placeholder="副标签"><input type="color" id="brCatSubLabelColor'+si+'_'+bi+'_'+ri+'_'+ci+'\" value="%23444" title="副标签颜色"></span></span>'''
c = c.replace(old_ac_lbl, new_ac_lbl)

# Remove old addStorageCat color and sublabel lines
for pattern in ["h += '<input type=\"hidden\" id=\"brCatColor", "h += '<input type=\"color\" id=\"brCatColor", "h += '<input type=\"hidden\" id=\"brCatSubLabelColor", "h += '<input type=\"color\" id=\"brCatSubLabelColor", "h += '<input id=\"brCatSubLabel"]:
    idx = c.find(pattern)
    if idx > 0:
        endline = c.find('\n', idx)
        if endline > 0 and (endline - idx) < 500:
            c = c[:idx] + c[endline:]
            print(f"  Removed addStorageCat line: {pattern[:40]}")

with open(r'B:\项目\Hass ASA Server Monitor\www\asa-admin.html', 'w', encoding='utf-8') as f:
    f.write(c)
print("=== Done ===")
