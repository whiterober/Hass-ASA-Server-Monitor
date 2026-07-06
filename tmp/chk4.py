with open(r"b:\项目\Hass ASA Server Monitor\www\asa-admin.html", "rb") as f:
    data = f.read()
# Check at one specific location for icon_group
idx = data.find(b"openIconPicker({mode:")
# Get 15 bytes starting at mode:
mode_start = idx + len(b"openIconPicker({")
chunk = data[mode_start:mode_start+30]
print("Raw bytes hex:", chunk.hex())
print("Chars:", [chr(b) for b in chunk])
# Check if there's a backslash (0x5C) before the first single quote
sq_pos = chunk.find(b"'")
if sq_pos > 0:
    before = chunk[sq_pos-1]
    print(f"Byte before first ': 0x{before:02x} = {chr(before)!r}")
    if before == 0x5C:
        print("BACKSLASH FOUND - escaping is correct!")
    else:
        print("NO BACKSLASH - escaping is BROKEN!")
