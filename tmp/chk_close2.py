c=open(r"b:\项目\Hass ASA Server Monitor\bak\asa-admin_backup_20260706_144138.html",encoding="utf-8").read()
pos=c.find("icon-picker-header")
chunk=c[pos:pos+3000]
# Just print raw bytes around buttons
import re
# Find all <button> elements
btns = re.findall(r'<button[^>]*>', chunk)
print(f"Found {len(btns)} <button> tags:")
for i,b in enumerate(btns):
    print(f"  [{i}] {b[:120]}")
