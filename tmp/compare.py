"""逐项对比新旧 picker HTML"""
old = open(r"b:\项目\Hass ASA Server Monitor\bak\asa-admin_backup_20260706_144138.html", encoding="utf-8").read()
new = open(r"b:\项目\Hass ASA Server Monitor\www\asa-admin.html", encoding="utf-8").read()

# Find all buttons in OLD picker header (desc version)
ops = []
idx = 0
while True:
    idx = old.find("openIconPicker_desc", idx)
    if idx < 0: break
    # Get the header area before the function
    start = old.rfind("openIconPicker_desc", 0, idx)
    fn_start = old.rfind("function ", 0, start)
    if fn_start > 0:
        fn_block = old[fn_start:fn_start+5000]
        # Find onclick patterns in the header
        import re
        btns_old = re.findall(r"onclick='([^']{5,80})'", fn_block)
        break
    idx += 1

print("=== OLD desc picker header buttons ===")
for b in btns_old:
    print(f"  {b}")

# Find buttons in NEW picker
pos = new.find("function openIconPicker(ctx)")
fn_new = new[pos:pos+5000]
btns_new = re.findall(r"onclick='([^']{5,80})'", fn_new)
print("\n=== NEW picker header buttons ===")
for b in btns_new:
    print(f"  {b}")
