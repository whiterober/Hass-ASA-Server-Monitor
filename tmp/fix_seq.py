fp = r"b:\项目\Hass ASA Server Monitor\www\asa-admin.html"
with open(fp, "r", encoding="utf-8") as f:
    c = f.read()

# In rebuildIGContainer, the variable is igRowDi not di
old = "{mode:\\'icon_group\\',bi:'+bi+',ii:'+seq+',di:'+di+'}"
new = "{mode:\\'icon_group\\',bi:'+bi+',ii:'+seq+',di:'+igRowDi+'}"
cnt = c.count(old)
if cnt > 0:
    c = c.replace(old, new)
    print(f"Fixed seq ctx: {cnt}x")
else:
    print("Pattern not found")

with open(fp, "w", encoding="utf-8") as f:
    f.write(c)
print(f"DONE. {len(c)} bytes")
