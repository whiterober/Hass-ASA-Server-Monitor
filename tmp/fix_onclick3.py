# Fix onclick: convert variable names to concatenated values
fp = r"b:\项目\Hass ASA Server Monitor\www\asa-admin.html"
with open(fp, "r", encoding="utf-8") as f:
    c = f.read()

fixes = [
    # info_card_title
    ("{mode:'info_card_title',bi}", "{mode:'info_card_title',bi:'+bi+'}"),
    # desc_row
    ("{mode:'desc_row',bi,di}", "{mode:'desc_row',bi:'+bi+',di:'+di+'}"),
    # icon_group: bi:bi, ii:ii
    ("{mode:'icon_group',bi:bi,ii:ii}", "{mode:'icon_group',bi:'+bi+',ii:'+ii+'}"),
    # icon_group: _igNext
    ("{mode:'icon_group',bi:bi,ii:_igNext}", "{mode:'icon_group',bi:'+bi+',ii:'+_igNext+'}"),
    # icon_group: seq
    ("{mode:'icon_group',bi:bi,ii:seq}", "{mode:'icon_group',bi:'+bi+',ii:'+seq+'}"),
    # icon_group: 0
    ("{mode:'icon_group',bi:bi,ii:0}", "{mode:'icon_group',bi:'+bi+',ii:0}"),
    # base_row
    ("{mode:'base_row',si,bi,ri}", "{mode:'base_row',si:'+si+',bi:'+bi+',ri:'+ri+'}"),
    # base_item
    ("{mode:'base_item',si,bi,ri,ci,ii}", "{mode:'base_item',si:'+si+',bi:'+bi+',ri:'+ri+',ci:'+ci+',ii:'+ii+'}"),
]

total = 0
for old, new in fixes:
    cnt = c.count(old)
    if cnt > 0:
        c = c.replace(old, new)
        print(f"OK {cnt}x: {old[:50]}")
        total += cnt
    else:
        print(f"SKIP: {old[:50]}")

with open(fp, "w", encoding="utf-8") as f:
    f.write(c)
print(f"\nDONE. {total} fixes. {len(c)} bytes")
