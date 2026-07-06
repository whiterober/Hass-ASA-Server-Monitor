with open(r"b:\项目\Hass ASA Server Monitor\www\asa-admin.html", "rb") as f:
    data = f.read()
# Find ALL occurrences and check each
pos = 0
count = 0
while True:
    idx = data.find(b"openIconPicker({mode:", pos)
    if idx < 0: break
    chunk = data[idx:idx+80]
    has_bs = b"\\'" in chunk
    count += 1
    print(f"#{count} at {idx}: has_bs={has_bs} | {chunk[:70]}")
    pos = idx + 1
    if count > 15: break
