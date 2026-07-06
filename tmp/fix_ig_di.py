fp = r"b:\项目\Hass ASA Server Monitor\www\asa-admin.html"
with open(fp, "r", encoding="utf-8") as f:
    c = f.read()

# Fix: Add di to icon_group ctx in render code
# Pattern: {mode:\'icon_group\',bi:'+bi+',ii:'+ii+'}
# Need: {mode:\'icon_group\',bi:'+bi+',ii:'+ii+',di:'+di+'}
old = "{mode:\\'icon_group\\',bi:'+bi+',ii:'+ii+'}"
new = "{mode:\\'icon_group\\',bi:'+bi+',ii:'+ii+',di:'+di+'}"
cnt = c.count(old)
if cnt > 0:
    c = c.replace(old, new)
    print(f"Added di to icon_group ctx: {cnt}x")
else:
    print("Pattern not found")

# Also fix _igNext variant
old2 = "{mode:\\'icon_group\\',bi:'+bi+',ii:'+_igNext+'}"
new2 = "{mode:\\'icon_group\\',bi:'+bi+',ii:'+_igNext+',di:'+di+'}"
cnt2 = c.count(old2)
if cnt2 > 0:
    c = c.replace(old2, new2)
    print(f"Added di to _igNext ctx: {cnt2}x")

# Also fix seq variant
old3 = "{mode:\\'icon_group\\',bi:'+bi+',ii:'+seq+'}"
new3 = "{mode:\\'icon_group\\',bi:'+bi+',ii:'+seq+',di:'+di+'}"
cnt3 = c.count(old3)
if cnt3 > 0:
    c = c.replace(old3, new3)
    print(f"Added di to seq ctx: {cnt3}x")

# Also fix 0 variant
old4 = "{mode:\\'icon_group\\',bi:'+bi+',ii:0}"
new4 = "{mode:\\'icon_group\\',bi:'+bi+',ii:0,di:'+di+'}"
cnt4 = c.count(old4)
if cnt4 > 0:
    c = c.replace(old4, new4)
    print(f"Added di to 0 ctx: {cnt4}x")

with open(fp, "w", encoding="utf-8") as f:
    f.write(c)
print(f"DONE. {len(c)} bytes")
