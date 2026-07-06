# Fix querySelector bugs
fp = r"b:\项目\Hass ASA Server Monitor\www\asa-admin.html"
with open(fp, "r", encoding="utf-8") as f:
    c = f.read()
did = 0
# Bug 1
pos = c.find("openIconPicker({mode:,")
if pos >= 0:
    start = c.rfind("[onclick", 0, pos)
    end = c.find("]", pos) + 1
    old = c[start:end]
    new = old.replace('openIconPicker({mode:,",_bi+",",_di2+")', 'openIconPicker("')
    c = c[:start] + new + c[end:]
    print("Bug 1 FIXED")
    did += 1
# Bug 2
cnt = c.count('span[onclick*=\\"openIconPicker_desc\\"]')
if cnt > 0:
    c = c.replace('span[onclick*=\\"openIconPicker_desc\\"]', 'span[onclick*=\\"openIconPicker(\\"]')
    print(f"Bug 2 FIXED {cnt}x")
    did += 1
if did == 0: print("No bugs")
with open(fp, "w", encoding="utf-8") as f:
    f.write(c)
print(f"DONE {len(c)}")
