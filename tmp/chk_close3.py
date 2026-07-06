c=open(r"b:\项目\Hass ASA Server Monitor\bak\asa-admin_backup_20260706_144138.html",encoding="utf-8").read()
# Find ALL occurrences of icon-picker-header
positions = []
idx = 0
while True:
    idx = c.find("icon-picker-header", idx)
    if idx < 0: break
    positions.append(idx)
    idx += 1
print(f"Found {len(positions)} occurrences of icon-picker-header")
for i, p in enumerate(positions):
    chunk = c[p:p+500]
    print(f"\n--- Occurrence {i} at offset {p} ---")
    print(chunk[:300])
    if i >= 2: break
