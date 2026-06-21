with open(r'B:\项目\Hass ASA Server Monitor\www\asa-admin.html', 'r', encoding='utf-8') as f:
    c = f.read()

# 1. Add hidden brCatSubLabelColor after brCatSubLabel in render template
old1 = "placeholder=\"副标签\" style=\"width:60px;padding:4px 8px;font-size:0.7em;margin:0\">';"
new1 = "placeholder=\"副标签\" style=\"width:60px;padding:4px 8px;font-size:0.7em;margin:0\">';\n                html += '<input type=\"hidden\" id=\"brCatSubLabelColor'+si+'_'+bi+'_'+ri+'_'+ci+'\" value=\"'+esc(cat.sub_label_color||'')+'\">';"
c = c.replace(old1, new1)
print('Step 1:', c.count('brCatSubLabelColor'))

# 2. Same for addStorageCat
old2 = "placeholder=\"副标签\" style=\"width:60px;padding:4px 8px;font-size:0.7em;margin:0\">';"
# This already matched step 1, so it won't find another one...
# Actually they're the same pattern. After step 1, the first occurrence is already replaced.
# The addStorageCat version has the SAME pattern. Let me check how many remain
print('Remaining occurrences:', c.count(old2))
# Replace the second occurrence
if old2 in c:
    new2 = "placeholder=\"副标签\" style=\"width:60px;padding:4px 8px;font-size:0.7em;margin:0\">';\n  h += '<input type=\"hidden\" id=\"brCatSubLabelColor'+si+'_'+bi+'_'+ri+'_'+ci+'\" value=\"\">';"
    c = c.replace(old2, new2)
    print('Step 2:', c.count('brCatSubLabelColor'))

# 3. Add sub_label_color to saveBaseTab
old_save = "sub_label: (catDiv.querySelector('[id^=brCatSubLabel]')?.value)||''"
new_save = "sub_label: (catDiv.querySelector('[id^=brCatSubLabel]')?.value)||'', sub_label_color: (catDiv.querySelector('[id^=brCatSubLabelColor]')?.value)||''"
c = c.replace(old_save, new_save)
print('Step 3:', c.count('sub_label_color'))

# 4. Add to reorderCatCard order array
old_order = '"brCatSubLabel","brCatColor"'
new_order = '"brCatSubLabel","brCatSubLabelColor","brCatColor"'
c = c.replace(old_order, new_order)
print('Step 4:', c.count('brCatSubLabelColor'))

# 5. Add to toggleBQControls
old_tog = 'var subEl = card.querySelector("[id^=brCatSubLabel]"); if (subEl) subEl.style.visibility = show;'
new_tog = 'var subEl = card.querySelector("[id^=brCatSubLabel]"); if (subEl) { subEl.style.visibility = show; var scEl = card.querySelector("[id^=brCatSubLabelColor]"); if (scEl) scEl.style.visibility = show; }'
c = c.replace(old_tog, new_tog)
print('Step 5:', 'brCatSubLabelColor' in new_tog)

with open(r'B:\项目\Hass ASA Server Monitor\www\asa-admin.html', 'w', encoding='utf-8') as f:
    f.write(c)
print('Done')
