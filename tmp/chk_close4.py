c=open(r"b:\项目\Hass ASA Server Monitor\bak\asa-admin_backup_20260706_144138.html",encoding="utf-8").read()
# Get occurrence 2 - the actual picker HTML
p = 299830
# Find the closing </div> of the header
header_end = c.find("</div>", p + 200)
header_full = c[p:header_end+6]
# Count button tags
import re
btns = re.findall(r'<button[^>]*?>[^<]*</button>', header_full)
print(f"Found {len(btns)} buttons in picker header:")
for i, b in enumerate(btns):
    # Extract onclick
    onclick_m = re.search(r"onclick='([^']*)'", b)
    onclick = onclick_m.group(1) if onclick_m else "NO ONCLICK"
    # Extract title
    title_m = re.search(r"title='([^']*)'", b)
    title = title_m.group(1) if title_m else ""
    print(f"  [{i}] title='{title}' onclick='{onclick[:60]}'")
    # Check for close
    if any(kw in b.lower() for kw in ['close','\u2715','\u00d7','关闭']):
        print(f"    ^^^ CLOSE BUTTON FOUND!")
