fp = r"b:\项目\Hass ASA Server Monitor\www\asa-admin.html"
with open(fp, "r", encoding="utf-8") as f:
    c = f.read()

# Fix base_row img: wrap in span with CSS class
old_row = '''              if (row.device_icon_url) {

                html += '<img src=\"'+esc(thumbUrl(row.device_icon_url,56))+'\" style=\"width:22px;height:22px;object-fit:contain;cursor:pointer\" onerror=\"this.hidden=true\" onclick=\"event.stopPropagation();openIconPicker({mode:\\'base_row\\',si:'+si+',bi:'+bi+',ri:'+ri+'})\" title=\"点击更换图标\">';

              } else {'''

new_row = '''              if (row.device_icon_url) {
                var _brm = row._dev_icon_mode || 'off';
                var _brl = row._dev_icon_lum;
                var _brisRev = (_brm === 'reverse');
                var _brlum = (_brl != null && _brl !== 0.5) ? _brl : null;
                var _brac = _brlum != null ? (_brlum > 0.5 ? 'ic-auto-light' : 'ic-auto-dark') : 'ic-auto-color';
                var _brbadge = (_brm === 'normal' || _brm === 'reverse') ? ' ic-mode-normal' : '';
                var _brcls = _brac + _brbadge;
                html += '<span class=\"'+_brcls+'\" style=\"position:relative;display:inline-flex;flex-shrink:0\"' + (_brlum != null ? ' data-lum=\"'+_brlum.toFixed(3)+'\"' : '') + '><img src=\"'+esc(thumbUrl(row.device_icon_url,56))+'\" style=\"width:22px;height:22px;object-fit:contain;cursor:pointer\" onerror=\"this.hidden=true\" onclick=\"event.stopPropagation();openIconPicker({mode:\\'base_row\\',si:'+si+',bi:'+bi+',ri:'+ri+'})\" title=\"点击更换图标\"></span>';

              } else {'''

cnt1 = c.count(old_row)
if cnt1 > 0:
    c = c.replace(old_row, new_row)
    print(f"Row fix: {cnt1}x")
else:
    print("Row pattern NOT FOUND")

# Fix base_item img: wrap in span with CSS class
old_item = '''                if (item.icon_url) {

                  html += '<img src=\"'+esc(thumbUrl(item.icon_url,56))+'\" style=\"width:28px;height:28px;object-fit:contain;cursor:pointer;flex-shrink:0\" onclick=\"event.stopPropagation();openIconPicker({mode:\\'base_item\\',si:'+si+',bi:'+bi+',ri:'+ri+',ci:'+ci+',ii:'+ii+'})\" title=\"点击换图标\" onerror=\"this.hidden=true\">';

                } else {'''

new_item = '''                if (item.icon_url) {
                var _bim = item._item_icon_mode || 'off';
                var _bil = item._item_icon_lum;
                var _biisRev = (_bim === 'reverse');
                var _bilum = (_bil != null && _bil !== 0.5) ? _bil : null;
                var _biac = _bilum != null ? (_bilum > 0.5 ? 'ic-auto-light' : 'ic-auto-dark') : 'ic-auto-color';
                var _bibadge = (_bim === 'normal' || _bim === 'reverse') ? ' ic-mode-normal' : '';
                var _bicls = _biac + _bibadge;
                html += '<span class=\"'+_bicls+'\" style=\"position:relative;display:inline-flex;flex-shrink:0\"' + (_bilum != null ? ' data-lum=\"'+_bilum.toFixed(3)+'\"' : '') + '><img src=\"'+esc(thumbUrl(item.icon_url,56))+'\" style=\"width:28px;height:28px;object-fit:contain;cursor:pointer;flex-shrink:0\" onclick=\"event.stopPropagation();openIconPicker({mode:\\'base_item\\',si:'+si+',bi:'+bi+',ri:'+ri+',ci:'+ci+',ii:'+ii+'})\" title=\"点击换图标\" onerror=\"this.hidden=true\"></span>';

                } else {'''

cnt2 = c.count(old_item)
if cnt2 > 0:
    c = c.replace(old_item, new_item)
    print(f"Item fix: {cnt2}x")
else:
    print("Item pattern NOT FOUND")

with open(fp, "w", encoding="utf-8") as f:
    f.write(c)
print(f"DONE. {len(c)} bytes")
