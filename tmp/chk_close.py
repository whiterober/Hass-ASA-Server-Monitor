import re
c=open(r"b:\项目\Hass ASA Server Monitor\bak\asa-admin_backup_20260706_144138.html",encoding="utf-8").read()
pos=c.find("icon-picker-header")
if pos>=0:
    chunk=c[pos:pos+2500]
    end=chunk.find("</div>",chunk.find("icon-picker-header"))
    header=chunk[:end+6]
    btns=re.findall(r"onclick='([^']+)'",header)
    print(f"Found {len(btns)} buttons:")
    for b in btns:
        print(f"  onclick: {b[:80]}")
    has_close = "close" in header.lower() or "\u2715" in header or "\u00d7" in header
    print(f"\nClose button in header: {has_close}")
    # Show full header
    print(f"\nHeader length: {len(header)} chars")
    print("Header preview:", header[:500])
